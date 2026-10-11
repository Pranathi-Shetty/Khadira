"""Financial summary service: Accrual vs Cash views, lot-based costing, machine output.

Rules:
- Accrual view: Invoiced revenue minus (cost of yarn consumed, wages earned, overhead).
- Cash view: Payments received from buyers minus (payments made to suppliers + wages paid).
- Strictly read-only: does not modify database state.
- Does not treat supplier bills as costs (yarn bought is inventory until consumed).
"""

import calendar
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    AttendanceEntry, Invoice, Machine, Order, OrderCost, Payment,
    ProductionRun, Roll, Setting, Worker
)
from ..models.purchasing import PurchaseOrderLine, YarnLot
from ..models.production import RunMaterial
from ..models.workforce import WageRun, WageRunLine
from .pricing import (
    compute_yarn_line_total, compute_fabric_line_total, compute_tax,
    meters_decimal_to_cm, kg_decimal_to_g
)


def get_invoice_total_paise(inv: Invoice) -> int:
    """Calculate total amount in paise including tax for an invoice from its lines."""
    subtotal = 0
    tax = 0
    for l in inv.lines:
        if inv.invoice_type == "sale":
            cm = meters_decimal_to_cm(l.qty)
            line_base = compute_fabric_line_total(cm, l.unit_price_paise)
        else:
            g = kg_decimal_to_g(l.qty)
            line_base = compute_yarn_line_total(g, l.unit_price_paise)
        line_tax = compute_tax(line_base, l.tax_pct)
        subtotal += line_base
        tax += line_tax
    return subtotal + tax


def get_lot_rate_per_kg_paise(db: Session, lot: YarnLot) -> int:
    """Determine purchase rate in paise per kg for a lot.
    Uses actual PO receipt rate if available, or average receipt rate for that yarn,
    or setting 'default_yarn_rate_per_kg_paise' (default ₹250.00/kg).
    """
    if lot.receipt and lot.receipt.po_line and lot.receipt.po_line.rate_per_kg_paise:
        return int(lot.receipt.po_line.rate_per_kg_paise)

    avg_rate = db.scalar(
        select(func.avg(PurchaseOrderLine.rate_per_kg_paise))
        .where(PurchaseOrderLine.item_id == lot.item_id)
    )
    if avg_rate is not None and avg_rate > 0:
        return int(avg_rate)

    setting = db.get(Setting, "default_yarn_rate_per_kg_paise")
    if setting and setting.value:
        try:
            return int(setting.value)
        except ValueError:
            pass
    return 25000  # Default ₹250.00 / kg (25000 paise)


def calculate_order_yarn_cost(db: Session, order_id: int) -> tuple[int, int]:
    """Calculate total yarn consumed (grams) and total yarn cost (paise) for an order."""
    runs = db.scalars(select(ProductionRun).where(ProductionRun.order_id == order_id)).all()
    total_g = 0
    total_cost_paise = 0
    for run in runs:
        if run.materials:
            for rm in run.materials:
                total_g += rm.issued_g
                rate = get_lot_rate_per_kg_paise(db, rm.lot)
                total_cost_paise += compute_yarn_line_total(rm.issued_g, rate)
        elif run.yarn_used_g and run.yarn_used_g > 0:
            total_g += run.yarn_used_g
            total_cost_paise += compute_yarn_line_total(run.yarn_used_g, 25000)
    return total_g, total_cost_paise


def get_financial_summary(db: Session, *, year: int, month: int) -> dict:
    """Compute financial summary for a chosen month (read-only).
    Provides strictly segregated Accrual view and Cash view.
    """
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    # ── 1. ACCRUAL VIEW ────────────────────────────────────────────────────────
    # Invoiced Revenue: sale invoices dated in the month
    sale_invoices = db.scalars(
        select(Invoice).where(
            Invoice.invoice_type == "sale",
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
        )
    ).all()
    invoiced_revenue_paise = sum(get_invoice_total_paise(inv) for inv in sale_invoices)

    # Cost of Yarn Consumed: materials issued to runs in this month
    materials = db.scalars(
        select(RunMaterial).where(
            func.date(RunMaterial.created_at) >= start_date,
            func.date(RunMaterial.created_at) <= end_date,
        )
    ).all()
    yarn_consumed_g = 0
    yarn_cost_paise = 0
    for rm in materials:
        yarn_consumed_g += rm.issued_g
        rate = get_lot_rate_per_kg_paise(db, rm.lot)
        yarn_cost_paise += compute_yarn_line_total(rm.issued_g, rate)

    # Wages earned (approved attendance for work in this month)
    attendance = db.scalars(
        select(AttendanceEntry).where(
            AttendanceEntry.status == "approved",
            AttendanceEntry.work_date >= start_date,
            AttendanceEntry.work_date <= end_date,
        )
    ).all()
    wages_earned_paise = 0
    for a in attendance:
        worker = db.get(Worker, a.worker_id)
        if worker:
            if worker.wage_basis == "hourly":
                wages_earned_paise += ((a.hours_worked or 0) * worker.hourly_rate_paise) // 60
            else:
                wages_earned_paise += (a.pieces_produced or 0) * worker.piece_rate_paise

    # Overhead for passed meters produced in the month
    month_passed_rolls = db.scalars(
        select(Roll).where(
            Roll.status.in_(["passed", "in_store", "dispatched"]),
            func.date(Roll.created_at) >= start_date,
            func.date(Roll.created_at) <= end_date,
        )
    ).all()
    passed_meters = sum(r.length_cm for r in month_passed_rolls) // 100
    overhead_setting = db.get(Setting, "overhead_per_metre_paise")
    overhead_rate = int(overhead_setting.value) if overhead_setting and overhead_setting.value else 0
    overhead_paise = overhead_rate * passed_meters

    accrual_expenses_paise = yarn_cost_paise + wages_earned_paise + overhead_paise
    accrual_net_profit_paise = invoiced_revenue_paise - accrual_expenses_paise
    accrual_margin_pct = (
        round((accrual_net_profit_paise / invoiced_revenue_paise) * 100, 2)
        if invoiced_revenue_paise > 0 else 0.0
    )

    # ── 2. CASH VIEW ───────────────────────────────────────────────────────────
    # Payments received from buyers
    buyer_payments = db.scalars(
        select(Payment)
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .where(
            Invoice.invoice_type == "sale",
            Payment.paid_date >= start_date,
            Payment.paid_date <= end_date,
        )
    ).all()
    buyer_payments_received_paise = sum(p.amount_paise for p in buyer_payments)

    # Payments made to suppliers
    supplier_payments = db.scalars(
        select(Payment)
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .where(
            Invoice.invoice_type == "purchase",
            Payment.paid_date >= start_date,
            Payment.paid_date <= end_date,
        )
    ).all()
    supplier_payments_made_paise = sum(p.amount_paise for p in supplier_payments)

    # Wages actually paid (from finalised wage runs in this month)
    wage_runs = db.scalars(
        select(WageRun).where(
            WageRun.status == "finalised",
            WageRun.period_start >= start_date,
            WageRun.period_start <= end_date,
        )
    ).all()
    wage_run_ids = [wr.id for wr in wage_runs]
    wages_paid_paise = 0
    if wage_run_ids:
        wages_paid_paise = db.scalar(
            select(func.sum(WageRunLine.net_wage_paise))
            .where(WageRunLine.wage_run_id.in_(wage_run_ids))
        ) or 0

    net_cash_flow_paise = buyer_payments_received_paise - supplier_payments_made_paise - wages_paid_paise

    # ── 3. MACHINE OUTPUT ──────────────────────────────────────────────────────
    machines = db.scalars(select(Machine).where(Machine.is_active.is_(True)).order_by(Machine.code.asc())).all()
    machine_output = []
    for m in machines:
        m_runs = db.scalars(
            select(ProductionRun).where(
                ProductionRun.machine_id == m.id,
                func.date(ProductionRun.started_at) >= start_date,
                func.date(ProductionRun.started_at) <= end_date,
            )
        ).all()
        m_run_ids = [r.id for r in m_runs]
        m_rolls = []
        if m_run_ids:
            m_rolls = db.scalars(select(Roll).where(Roll.run_id.in_(m_run_ids))).all()
        total_length_cm = sum(r.length_cm for r in m_rolls)
        passed_length_cm = sum(r.length_cm for r in m_rolls if r.status in ("passed", "in_store", "dispatched"))
        machine_output.append({
            "machine_id": m.id,
            "machine_code": m.code,
            "machine_name": m.name,
            "machine_type": m.machine_type,
            "runs_count": len(m_runs),
            "rolls_count": len(m_rolls),
            "meters_produced": round(total_length_cm / 100, 2),
            "passed_meters": round(passed_length_cm / 100, 2),
        })

    return {
        "period": f"{year:04d}-{month:02d}",
        "year": year,
        "month": month,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "accrual_view": {
            "invoiced_revenue_paise": invoiced_revenue_paise,
            "invoiced_revenue_inr": round(invoiced_revenue_paise / 100, 2),
            "yarn_consumed_kg": round(yarn_consumed_g / 1000, 3),
            "yarn_cost_paise": yarn_cost_paise,
            "yarn_cost_inr": round(yarn_cost_paise / 100, 2),
            "wages_earned_paise": wages_earned_paise,
            "wages_earned_inr": round(wages_earned_paise / 100, 2),
            "overhead_paise": overhead_paise,
            "overhead_inr": round(overhead_paise / 100, 2),
            "total_expenses_paise": accrual_expenses_paise,
            "total_expenses_inr": round(accrual_expenses_paise / 100, 2),
            "net_profit_paise": accrual_net_profit_paise,
            "net_profit_inr": round(accrual_net_profit_paise / 100, 2),
            "margin_pct": accrual_margin_pct,
        },
        "cash_view": {
            "buyer_payments_received_paise": buyer_payments_received_paise,
            "buyer_payments_received_inr": round(buyer_payments_received_paise / 100, 2),
            "supplier_payments_made_paise": supplier_payments_made_paise,
            "supplier_payments_made_inr": round(supplier_payments_made_paise / 100, 2),
            "wages_paid_paise": wages_paid_paise,
            "wages_paid_inr": round(wages_paid_paise / 100, 2),
            "net_cash_flow_paise": net_cash_flow_paise,
            "net_cash_flow_inr": round(net_cash_flow_paise / 100, 2),
        },
        "machine_output": machine_output,
        "wages_summary": {
            "approved_attendance_entries": len(attendance),
            "wages_earned_paise": wages_earned_paise,
            "wages_earned_inr": round(wages_earned_paise / 100, 2),
            "wages_paid_paise": wages_paid_paise,
            "wages_paid_inr": round(wages_paid_paise / 100, 2),
        },
    }
