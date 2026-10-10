"""Dashboard and costing routers."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from mill.auth import can, get_current_user
from mill.database import get_db
from mill.models import (
    Invoice, InvoiceStatus, Item, Machine, Order, OrderCost,
    OrderStatus, Roll, RollStatus, Setting, StockLevel, User,
    WageRun, WageRunStatus,
)
from mill.services.costing import compute_order_cost

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
costing_router = APIRouter(prefix="/api/costing", tags=["costing"])
settings_router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@dashboard_router.get("/")
def dashboard(db: Session = Depends(get_db), _=Depends(can("orders.read"))):
    order_counts = {}
    for status in OrderStatus:
        order_counts[status] = db.query(Order).filter(Order.status == status).count()

    # Low stock alerts
    low_stock_items = []
    items = db.query(Item).filter(Item.is_active == True).all()
    for item in items:
        level = db.query(StockLevel).filter(StockLevel.item_id == item.id).first()
        qty = level.quantity if level else 0
        if qty <= item.reorder_point_grams:
            low_stock_items.append({
                "id": item.id, "sku": item.sku, "name": item.name,
                "stock_quantity": qty, "reorder_point": item.reorder_point_grams,
                "unit": item.unit,
            })

    # Machine status summary
    machine_summary = {}
    machines = db.query(Machine).all()
    for m in machines:
        machine_summary[m.status] = machine_summary.get(m.status, 0) + 1

    # Outstanding receivables
    invoices = db.query(Invoice).filter(Invoice.status != InvoiceStatus.paid).all()
    outstanding_receivables = sum(
        inv.amount_paise - sum(p.amount_paise for p in inv.payments)
        for inv in invoices
    )

    # Rolls awaiting QC
    qc_pending = db.query(Roll).filter(Roll.status == RollStatus.awaiting_qc).count()

    return {
        "order_counts": order_counts,
        "machine_summary": machine_summary,
        "low_stock_alerts": low_stock_items,
        "outstanding_receivables_paise": outstanding_receivables,
        "qc_pending_rolls": qc_pending,
        "total_machines": len(machines),
    }


# ---------------------------------------------------------------------------
# Costing
# ---------------------------------------------------------------------------

@costing_router.post("/orders/{order_id}")
def compute_cost(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(can("costing.write")),
):
    try:
        oc = compute_order_cost(db, order_id, user.id)
        db.commit()
        return {
            "order_id": order_id,
            "yarn_cost_paise": oc.yarn_cost_paise,
            "allocated_wage_paise": oc.allocated_wage_paise,
            "overhead_paise": oc.overhead_paise,
            "total_cost_paise": oc.total_cost_paise,
            "passed_metres": oc.passed_metres,
            "cost_per_passed_metre_paise": oc.cost_per_passed_metre_paise,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@costing_router.get("/orders/{order_id}")
def get_order_cost(order_id: int, db: Session = Depends(get_db), _=Depends(can("costing.read"))):
    oc = db.query(OrderCost).filter(OrderCost.order_id == order_id).first()
    if not oc:
        raise HTTPException(404, "Cost not computed yet. POST to /api/costing/orders/{id} first.")
    return {
        "order_id": order_id,
        "yarn_cost_paise": oc.yarn_cost_paise,
        "allocated_wage_paise": oc.allocated_wage_paise,
        "overhead_paise": oc.overhead_paise,
        "total_cost_paise": oc.total_cost_paise,
        "passed_metres": oc.passed_metres,
        "cost_per_passed_metre_paise": oc.cost_per_passed_metre_paise,
        "calculated_at": oc.calculated_at,
        "roll_costs": [
            {
                "roll_id": rc.roll_id,
                "metres": rc.metres,
                "allocated_cost_paise": rc.allocated_cost_paise,
                "cost_per_metre_paise": rc.cost_per_metre_paise,
                "cost_type": rc.cost_type,
            }
            for rc in oc.roll_costs
        ],
    }


# ---------------------------------------------------------------------------
# Owner report
# ---------------------------------------------------------------------------

@dashboard_router.get("/owner-report")
def owner_report(
    month: int,
    year: int,
    db: Session = Depends(get_db),
    _=Depends(can("reports.read")),
):
    from datetime import date
    from calendar import monthrange

    period_start = date(year, month, 1)
    period_end = date(year, month, monthrange(year, month)[1])

    # Wage totals
    wage_run = db.query(WageRun).filter(
        WageRun.period_start == period_start,
        WageRun.status == WageRunStatus.finalised,
    ).first()
    total_wages_paise = sum(l.net_wage_paise for l in wage_run.lines) if wage_run else 0

    # Invoice totals for the month
    month_invoices = db.query(Invoice).filter(
        Invoice.invoice_date >= period_start,
        Invoice.invoice_date <= period_end,
    ).all()
    total_invoiced = sum(inv.amount_paise for inv in month_invoices)
    total_collected = sum(
        sum(p.amount_paise for p in inv.payments)
        for inv in month_invoices
    )

    # Order costs
    orders = db.query(Order).all()
    order_costs = []
    for o in orders:
        if o.costing:
            order_costs.append({
                "order_id": o.id,
                "doc_no": o.doc_no,
                "buyer": o.buyer.name,
                "total_cost_paise": o.costing.total_cost_paise,
                "passed_metres": o.costing.passed_metres,
                "cost_per_passed_metre_paise": o.costing.cost_per_passed_metre_paise,
            })

    return {
        "period": f"{year}-{month:02d}",
        "total_wages_paise": total_wages_paise,
        "total_invoiced_paise": total_invoiced,
        "total_collected_paise": total_collected,
        "outstanding_paise": total_invoiced - total_collected,
        "order_costs": order_costs,
        "wage_run_id": wage_run.id if wage_run else None,
    }


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@settings_router.get("/")
def get_settings(db: Session = Depends(get_db), _=Depends(can("settings.manage"))):
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}


@settings_router.put("/{key}")
def set_setting(
    key: str,
    body: dict,
    db: Session = Depends(get_db),
    _=Depends(can("settings.manage")),
):
    s = db.query(Setting).filter(Setting.key == key).first()
    if s is None:
        s = Setting(key=key, value=str(body.get("value", "")))
        db.add(s)
    else:
        s.value = str(body.get("value", ""))
    db.commit()
    return {"ok": True}
