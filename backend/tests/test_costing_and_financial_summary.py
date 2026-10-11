"""Step 6 Tests: Lot-based costing and Monthly Financial Summary (Accrual vs Cash views)."""

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from mill.models import (
    AttendanceEntry, Buyer, Item, Invoice, InvoiceLine, Location, Machine,
    Order, OrderCost, OrderLine, Payment, ProductionRun, Roll, RollEvent,
    Setting, Supplier, PurchaseOrder, PurchaseOrderLine, Worker,
    YarnLot, YarnReceipt, RunMaterial
)
from mill.models.workforce import WageRun, WageRunLine
from mill.services.common import DomainError
from mill.services.orders import create_order, confirm_order
from mill.services.production import start_run, advance_stage, create_roll, issue_yarn_to_run
from mill.services.purchasing import receive_yarn
from mill.services.financial_summary import get_financial_summary, calculate_order_yarn_cost
from tests.conftest import login


@pytest.fixture
def auth_client(client: TestClient):
    login(client, "admin")
    return client


@pytest.fixture
def base_entities(db_session: Session):
    # Ensure overhead setting
    ov = db_session.get(Setting, "overhead_per_metre_paise")
    if not ov:
        db_session.add(Setting(key="overhead_per_metre_paise", value="1000")) # ₹10/m
    else:
        ov.value = "1000"

    sup = db_session.query(Supplier).filter_by(name="Costing Supplier Ltd").first()
    if not sup:
        sup = Supplier(name="Costing Supplier Ltd", phone="9988776655")
        db_session.add(sup)

    buyer = db_session.query(Buyer).filter_by(name="Costing Buyer Corp").first()
    if not buyer:
        buyer = Buyer(name="Costing Buyer Corp", credit_days=30)
        db_session.add(buyer)

    yarn = db_session.query(Item).filter_by(sku="YRN-COST-30").first()
    if not yarn:
        yarn = Item(sku="YRN-COST-30", name="Costing Yarn 30s", item_type="yarn", unit="kg")
        db_session.add(yarn)

    fabric = db_session.query(Item).filter_by(sku="FAB-COST-100").first()
    if not fabric:
        fabric = Item(
            sku="FAB-COST-100", name="Costing Fabric Poplin",
            item_type="fabric", unit="meters", gsm=120, width_cm=110,
            yarn_kg_per_meter=0.200
        )
        db_session.add(fabric)

    machine = db_session.query(Machine).filter_by(code="WL-COST-01").first()
    if not machine:
        machine = Machine(code="WL-COST-01", name="Costing Loom 1", machine_type="weaving")
        db_session.add(machine)

    worker_hourly = db_session.query(Worker).filter_by(code="WRK-H-01").first()
    if not worker_hourly:
        worker_hourly = Worker(
            code="WRK-H-01", full_name="Hourly Weaver", wage_basis="hourly",
            hourly_rate_paise=10000, department="Weaving" # ₹100/hr
        )
        db_session.add(worker_hourly)

    worker_piece = db_session.query(Worker).filter_by(code="WRK-P-01").first()
    if not worker_piece:
        worker_piece = Worker(
            code="WRK-P-01", full_name="Piece Worker", wage_basis="piece_rate",
            piece_rate_paise=2000, department="Weaving" # ₹20/piece
        )
        db_session.add(worker_piece)

    db_session.commit()
    return {
        "sup": sup,
        "buyer": buyer,
        "yarn": yarn,
        "fabric": fabric,
        "machine": machine,
        "worker_hourly": worker_hourly,
        "worker_piece": worker_piece,
    }


def test_hand_calculated_financial_summary_month(auth_client: TestClient, db_session: Session, base_entities):
    """Proof 1: Hand-calculated month in both Accrual and Cash views.
    Month: 2026-11
    """
    sup = base_entities["sup"]
    buyer = base_entities["buyer"]
    yarn = base_entities["yarn"]
    fabric = base_entities["fabric"]
    machine = base_entities["machine"]
    w_hourly = base_entities["worker_hourly"]
    w_piece = base_entities["worker_piece"]

    # 1. Purchase and receive yarn: 100 kg at ₹250/kg (25000_00 paise)
    po = PurchaseOrder(ref="PO-NOV-01", supplier_id=sup.id, order_date=date(2026, 11, 1), status="confirmed")
    db_session.add(po)
    db_session.flush()
    poline = PurchaseOrderLine(po_id=po.id, item_id=yarn.id, qty_kg=100, rate_per_kg_paise=25000)
    db_session.add(poline)
    db_session.commit()

    rec = receive_yarn(
        db_session, po_id=po.id, po_line_id=poline.id, received_date=date(2026, 11, 2),
        qty_kg=100, vehicle_no="TR-01", notes="", lot_number="LOT-NOV-100",
        location_code="RAW", user_id=1
    )
    db_session.commit()

    # 2. Supplier purchase bill: ₹25,000.00 (2500000 paise)
    sup_inv = Invoice(
        ref="SUP-INV-NOV-01", invoice_type="purchase", supplier_id=sup.id,
        invoice_date=date(2026, 11, 3), status="posted"
    )
    sup_inv.lines.append(InvoiceLine(
        description="Yarn 100kg", qty=Decimal("100.000"), unit_price_paise=25000
    ))
    db_session.add(sup_inv)
    db_session.commit()

    # 3. Create Order and Run
    order = create_order(
        db_session, buyer_id=buyer.id, order_date=date(2026, 11, 5),
        delivery_date=date(2026, 11, 30),
        lines=[{"item_id": fabric.id, "qty_meters": 150, "rate_per_meter_paise": 15000}],
        user_id=1
    )
    confirm_order(db_session, order.id, user_id=1)
    db_session.commit()

    run = start_run(db_session, machine_id=machine.id, order_id=order.id, item_id=fabric.id, user_id=1)
    run.started_at = datetime(2026, 11, 8, 10, 0, tzinfo=timezone.utc)
    db_session.commit()

    # Issue yarn: 35 kg total across run (35,000g at ₹250/kg = 875,000 paise = ₹8,750.00)
    materials = issue_yarn_to_run(db_session, run_id=run.id, qty_g=35_000, item_id=yarn.id, user_id=1)
    for rm in materials:
        rm.created_at = datetime(2026, 11, 8, 10, 30, tzinfo=timezone.utc)
    db_session.commit()

    # Advance and create rolls in Nov: Roll 1 (100m) and Roll 2 (50m) = 150m total passed
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1) # warping -> weaving
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1) # weaving -> inspection
    r1 = create_roll(db_session, run_id=run.id, length_cm=10000, weight_g=20000, user_id=1)
    r2 = create_roll(db_session, run_id=run.id, length_cm=5000, weight_g=10000, user_id=1)
    r1.status = "passed"
    r2.status = "passed"
    r1.created_at = datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)
    r2.created_at = datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)
    db_session.commit()

    # 4. Sale Invoices in Nov:
    # Inv 1: 100m at ₹120.00/m = 1,200,000 paise (₹12,000.00)
    # Inv 2: 50m at ₹160.00/m = 800,000 paise (₹8,000.00)
    # Total Invoiced Revenue = 2,000,000 paise (₹20,000.00)
    sale_inv1 = Invoice(
        ref="INV-NOV-01", invoice_type="sale", buyer_id=buyer.id, order_id=order.id,
        invoice_date=date(2026, 11, 15), status="posted"
    )
    sale_inv1.lines.append(InvoiceLine(
        description="Poplin 100m", qty=Decimal("100.000"), unit_price_paise=12000
    ))
    sale_inv2 = Invoice(
        ref="INV-NOV-02", invoice_type="sale", buyer_id=buyer.id, order_id=order.id,
        invoice_date=date(2026, 11, 16), status="posted"
    )
    sale_inv2.lines.append(InvoiceLine(
        description="Poplin 50m", qty=Decimal("50.000"), unit_price_paise=16000
    ))
    db_session.add_all([sale_inv1, sale_inv2])
    db_session.commit()

    # 5. Attendance entries in Nov:
    # Hourly worker: 8 hrs (480 min) * 10000 // 60 = 80,000 paise (₹800.00)
    # Piece worker: 50 pieces * 2000 = 100,000 paise (₹1,000.00)
    # Total Wages = 180,000 paise (₹1,800.00)
    att1 = AttendanceEntry(
        worker_id=w_hourly.id, work_date=date(2026, 11, 10), shift="Day",
        hours_worked=480, status="approved", created_by_id=1, order_id=order.id, run_id=run.id
    )
    att2 = AttendanceEntry(
        worker_id=w_piece.id, work_date=date(2026, 11, 11), shift="Day",
        pieces_produced=50, status="approved", created_by_id=1, order_id=order.id, run_id=run.id
    )
    db_session.add_all([att1, att2])
    db_session.commit()

    # 6. Cash Payments in Nov:
    # Buyer pays ₹15,000.00 (1,500,000 paise) towards sale_inv1 on Nov 20
    p_buyer = Payment(
        invoice_id=sale_inv1.id, paid_date=date(2026, 11, 20),
        amount_paise=1500000, method="neft"
    )
    # Mill pays ₹10,000.00 (1,000,000 paise) towards supplier bill on Nov 22
    p_sup = Payment(
        invoice_id=sup_inv.id, paid_date=date(2026, 11, 22),
        amount_paise=1000000, method="neft"
    )
    db_session.add_all([p_buyer, p_sup])

    # Finalised Wage Run in Nov paying ₹1,800.00 (180,000 paise)
    wr = WageRun(
        period_start=date(2026, 11, 1), period_end=date(2026, 11, 30),
        status="finalised", created_by_id=1
    )
    db_session.add(wr)
    db_session.flush()
    wrl = WageRunLine(
        wage_run_id=wr.id, worker_id=w_hourly.id, net_wage_paise=180000
    )
    db_session.add(wrl)
    db_session.commit()

    # ── VERIFY ACCRUAL & CASH VIEWS VIA API ────────────────────────────────────
    r = auth_client.get("/api/reports/financial-summary?period=2026-11")
    assert r.status_code == 200
    res = r.json()

    # Accrual view verification:
    # Revenue: 2,000,000 paise
    # Yarn Cost: 35kg * 250 = 875,000 paise
    # Wages: 180,000 paise
    # Overhead: 150m * 10 = 150,000 paise
    # Total Expenses: 875,000 + 180,000 + 150,000 = 1,205,000 paise
    # Net Profit: 2,000,000 - 1,205,000 = 795,000 paise (₹7,950.00)
    acc = res["accrual_view"]
    assert acc["invoiced_revenue_paise"] == 2000000
    assert acc["yarn_cost_paise"] == 875000
    assert acc["wages_earned_paise"] == 180000
    assert acc["overhead_paise"] == 150000
    assert acc["total_expenses_paise"] == 1205000
    assert acc["net_profit_paise"] == 795000
    assert acc["margin_pct"] == 39.75

    # Cash view verification:
    # Buyer receipts: 1,500,000 paise
    # Supplier disbursements: 1,000,000 paise (NOT 2,500,000 of bill!)
    # Wages paid: 180,000 paise
    # Net cash flow: 1,500,000 - 1,000,000 - 180,000 = 320,000 paise (₹3,200.00)
    cash = res["cash_view"]
    assert cash["buyer_payments_received_paise"] == 1500000
    assert cash["supplier_payments_made_paise"] == 1000000
    assert cash["wages_paid_paise"] == 180000
    assert cash["net_cash_flow_paise"] == 320000

    # Machine output verification:
    mach = [m for m in res["machine_output"] if m["machine_code"] == machine.code][0]
    assert mach["rolls_count"] == 2
    assert mach["meters_produced"] == 150.0
    assert mach["passed_meters"] == 150.0


def test_order_costing_with_no_passed_meters_returns_not_available(auth_client: TestClient, db_session: Session, base_entities):
    """Proof 2: A test with no passed meters returns a clear 'not_available', NOT zero."""
    buyer = base_entities["buyer"]
    fabric = base_entities["fabric"]
    yarn = base_entities["yarn"]
    machine = base_entities["machine"]

    # Order with no completed inspection yet
    order = create_order(
        db_session, buyer_id=buyer.id, order_date=date(2026, 11, 20),
        delivery_date=date(2026, 12, 20),
        lines=[{"item_id": fabric.id, "qty_meters": 100, "rate_per_meter_paise": 8000_00}],
        user_id=1
    )
    confirm_order(db_session, order.id, user_id=1)
    db_session.commit()

    run = start_run(db_session, machine_id=machine.id, order_id=order.id, item_id=fabric.id, user_id=1)
    db_session.commit()

    # Calculate cost via API
    r = auth_client.post(f"/api/costing/orders/{order.id}/calculate")
    assert r.status_code == 200
    data = r.json()

    assert data["passed_metres"] == 0
    # Must return clear "not_available", NOT zero!
    assert data["cost_per_passed_metre_paise"] == "not_available"
    assert data["cost_per_passed_metre_status"] == "not_available"

    # Also check read-only GET returns "not_available"
    r_get = auth_client.get(f"/api/costing/orders/{order.id}")
    assert r_get.status_code == 200
    get_data = r_get.json()
    assert get_data["passed_metres"] == 0
    assert get_data["cost_per_passed_metre_paise"] == "not_available"
    assert get_data["cost_per_passed_metre_status"] == "not_available"


def test_financial_summary_endpoint_is_strictly_read_only(auth_client: TestClient, db_session: Session):
    """Calling financial summary changes nothing in database (read-only invariance)."""
    # Record row counts before
    counts_before = {
        "invoice": db_session.scalar(select(func.count(Invoice.id))),
        "payment": db_session.scalar(select(func.count(Payment.id))),
        "run_material": db_session.scalar(select(func.count(RunMaterial.id))),
        "attendance": db_session.scalar(select(func.count(AttendanceEntry.id))),
        "order_cost": db_session.scalar(select(func.count(OrderCost.id))),
    }

    # Call endpoint twice
    r1 = auth_client.get("/api/reports/financial-summary?period=2026-11")
    assert r1.status_code == 200
    r2 = auth_client.get("/api/reports/financial-summary?period=2026-11")
    assert r2.status_code == 200

    # Record row counts after
    counts_after = {
        "invoice": db_session.scalar(select(func.count(Invoice.id))),
        "payment": db_session.scalar(select(func.count(Payment.id))),
        "run_material": db_session.scalar(select(func.count(RunMaterial.id))),
        "attendance": db_session.scalar(select(func.count(AttendanceEntry.id))),
        "order_cost": db_session.scalar(select(func.count(OrderCost.id))),
    }

    assert counts_before == counts_after
