"""Step 5 Tests: Yarn traceability, batch consumption (FIFO), and roll tracing."""

from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from mill.models import (
    Item, Location, Machine, Order, OrderLine, ProductionRun, Roll,
    StockLevel, Supplier, PurchaseOrder, PurchaseOrderLine,
    YarnLot, YarnReceipt, RunMaterial
)
from mill.services.common import DomainError
from mill.services.production import (
    start_run, advance_stage, create_roll, issue_yarn_to_run,
    issue_material, get_roll_trace
)
from mill.services.purchasing import receive_yarn
from mill.services.orders import create_order, confirm_order
from tests.conftest import login


@pytest.fixture
def auth_client(client: TestClient):
    login(client, "admin")
    return client


@pytest.fixture
def test_setup(db_session: Session):
    # Setup supplier, yarn item, fabric item, machine, and locations
    sup = db_session.query(Supplier).filter_by(name="Test Yarn Mills").first()
    if not sup:
        sup = Supplier(name="Test Yarn Mills", phone="9876543210")
        db_session.add(sup)

    sup2 = db_session.query(Supplier).filter_by(name="Spinning Stars").first()
    if not sup2:
        sup2 = Supplier(name="Spinning Stars", phone="9876543211")
        db_session.add(sup2)

    yarn = db_session.query(Item).filter_by(sku="YRN-TRACE-TEST").first()
    if not yarn:
        yarn = Item(sku="YRN-TRACE-TEST", name="Traceability Yarn 30s", item_type="yarn", unit="kg")
        db_session.add(yarn)

    fabric = db_session.query(Item).filter_by(sku="FAB-TRACE-TEST").first()
    if not fabric:
        fabric = Item(
            sku="FAB-TRACE-TEST", name="Traceability Poplin",
            item_type="fabric", unit="meters", gsm=120, width_cm=110,
            yarn_kg_per_meter=0.200
        )
        db_session.add(fabric)

    machine = db_session.query(Machine).filter_by(code="WL-TRACE").first()
    if not machine:
        machine = Machine(code="WL-TRACE", name="Trace Loom", machine_type="weaving")
        db_session.add(machine)

    from mill.models.partners import Buyer
    buyer = db_session.query(Buyer).filter_by(name="Trace Buyer").first()
    if not buyer:
        buyer = Buyer(name="Trace Buyer", credit_days=30)
        db_session.add(buyer)

    db_session.commit()
    return {
        "sup": sup,
        "sup2": sup2,
        "buyer": buyer,
        "yarn": yarn,
        "fabric": fabric,
        "machine": machine,
    }


def test_issuing_yarn_across_two_batches_splits_fifo(db_session: Session, test_setup):
    """Proof 1: Issuing yarn across two batches splits correctly (FIFO) and leaves correct remainders."""
    sup = test_setup["sup"]
    yarn = test_setup["yarn"]
    machine = test_setup["machine"]
    raw_loc = db_session.scalar(select(Location).where(Location.code == "RAW"))

    # Reset any existing stock for clean math
    sl = db_session.query(StockLevel).filter_by(item_id=yarn.id, location_id=raw_loc.id).first()
    if sl:
        sl.qty_g = 0
        db_session.commit()

    # Create PO 1: 30 kg (30,000g)
    po1 = PurchaseOrder(ref="PO-TRACE-01", supplier_id=sup.id, order_date=date(2026, 10, 1), status="confirmed")
    db_session.add(po1)
    db_session.flush()
    line1 = PurchaseOrderLine(po_id=po1.id, item_id=yarn.id, qty_kg=30, rate_per_kg_paise=25000_00)
    db_session.add(line1)
    db_session.commit()

    # Receive PO 1 (older batch)
    rec1 = receive_yarn(
        db_session, po_id=po1.id, po_line_id=line1.id, received_date=date(2026, 10, 2),
        qty_kg=30, vehicle_no="TRUCK-01", notes="First batch", lot_number="LOT-TRACE-A",
        location_code="RAW", user_id=1
    )
    db_session.commit()

    # Create PO 2: 50 kg (50,000g)
    po2 = PurchaseOrder(ref="PO-TRACE-02", supplier_id=sup.id, order_date=date(2026, 10, 3), status="confirmed")
    db_session.add(po2)
    db_session.flush()
    line2 = PurchaseOrderLine(po_id=po2.id, item_id=yarn.id, qty_kg=50, rate_per_kg_paise=26000_00)
    db_session.add(line2)
    db_session.commit()

    # Receive PO 2 (newer batch)
    rec2 = receive_yarn(
        db_session, po_id=po2.id, po_line_id=line2.id, received_date=date(2026, 10, 4),
        qty_kg=50, vehicle_no="TRUCK-02", notes="Second batch", lot_number="LOT-TRACE-B",
        location_code="RAW", user_id=1
    )
    db_session.commit()

    lot_a = db_session.query(YarnLot).filter_by(lot_number="LOT-TRACE-A").one()
    lot_b = db_session.query(YarnLot).filter_by(lot_number="LOT-TRACE-B").one()
    assert lot_a.remaining_g == 30_000
    assert lot_b.remaining_g == 50_000

    # Start run and issue 45,000g (should take all 30,000g from LOT-TRACE-A, and 15,000g from LOT-TRACE-B)
    run = start_run(db_session, machine_id=machine.id, order_id=None, item_id=yarn.id, user_id=1)
    db_session.commit()

    materials = issue_yarn_to_run(db_session, run_id=run.id, qty_g=45_000, item_id=yarn.id, user_id=1)
    db_session.commit()

    assert len(materials) == 2
    # Material from oldest batch LOT-A
    assert materials[0].lot_id == lot_a.id
    assert materials[0].issued_g == 30_000

    # Material from newer batch LOT-B
    assert materials[1].lot_id == lot_b.id
    assert materials[1].issued_g == 15_000

    # Verify remainders on lots
    db_session.refresh(lot_a)
    db_session.refresh(lot_b)
    assert lot_a.remaining_g == 0
    assert lot_b.remaining_g == 35_000

    # Total issued to run
    assert run.yarn_used_g == 45_000


def test_issuing_more_than_available_is_refused(db_session: Session, test_setup):
    """Proof 2: Issuing more than is available in batches is refused."""
    yarn = test_setup["yarn"]
    machine = test_setup["machine"]

    # Check total available remaining across lots for this yarn
    lots = db_session.query(YarnLot).filter(YarnLot.item_id == yarn.id, YarnLot.remaining_g > 0).all()
    avail = sum(l.remaining_g for l in lots)

    run = start_run(db_session, machine_id=machine.id, order_id=None, item_id=yarn.id, user_id=1)
    db_session.commit()

    # Attempt to issue more than available
    with pytest.raises(DomainError) as exc:
        issue_yarn_to_run(db_session, run_id=run.id, qty_g=avail + 10_000, item_id=yarn.id, user_id=1)
    assert "Insufficient yarn stock" in str(exc.value)

    # Attempt to issue specific lot more than its remainder
    if lots:
        target_lot = lots[0]
        with pytest.raises(DomainError) as exc_lot:
            issue_material(db_session, run_id=run.id, lot_id=target_lot.id, qty_g=target_lot.remaining_g + 1_000, user_id=1)
        assert "Insufficient yarn in batch" in str(exc_lot.value)


def test_total_batch_remainders_equal_stock_level(db_session: Session, test_setup):
    """Proof 3: Total batch remainders for an item equal that item's stock level."""
    sup = test_setup["sup2"]
    machine = test_setup["machine"]
    raw_loc = db_session.scalar(select(Location).where(Location.code == "RAW"))

    # Create fresh yarn item
    yarn = Item(sku="YRN-BAL-CHECK", name="Balance Check Yarn", item_type="yarn", unit="kg")
    db_session.add(yarn)
    db_session.commit()

    # Receive 2 batches: 40kg and 60kg
    po = PurchaseOrder(ref="PO-BAL-01", supplier_id=sup.id, order_date=date(2026, 10, 1), status="confirmed")
    db_session.add(po)
    db_session.flush()
    p_line = PurchaseOrderLine(po_id=po.id, item_id=yarn.id, qty_kg=100, rate_per_kg_paise=20000_00)
    db_session.add(p_line)
    db_session.commit()

    receive_yarn(db_session, po_id=po.id, po_line_id=p_line.id, received_date=date(2026, 10, 1),
                 qty_kg=40, vehicle_no="T1", notes="", lot_number="LOT-BAL-1", location_code="RAW", user_id=1)
    receive_yarn(db_session, po_id=po.id, po_line_id=p_line.id, received_date=date(2026, 10, 2),
                 qty_kg=60, vehicle_no="T2", notes="", lot_number="LOT-BAL-2", location_code="RAW", user_id=1)
    db_session.commit()

    # Stock level before issue: 100,000g
    sl = db_session.query(StockLevel).filter_by(item_id=yarn.id, location_id=raw_loc.id).one()
    lots = db_session.query(YarnLot).filter_by(item_id=yarn.id).all()
    assert sum(l.remaining_g for l in lots) == sl.qty_g == 100_000

    # Issue 25,000g to run 1
    run1 = start_run(db_session, machine_id=machine.id, order_id=None, item_id=yarn.id, user_id=1)
    issue_yarn_to_run(db_session, run_id=run1.id, qty_g=25_000, item_id=yarn.id, user_id=1)
    db_session.commit()

    db_session.refresh(sl)
    lots = db_session.query(YarnLot).filter_by(item_id=yarn.id).all()
    assert sum(l.remaining_g for l in lots) == sl.qty_g == 75_000

    # Issue 35,000g to run 2 (crosses remainder of LOT-BAL-1 (15k) and draws from LOT-BAL-2 (20k))
    run2 = start_run(db_session, machine_id=machine.id, order_id=None, item_id=yarn.id, user_id=1)
    issue_yarn_to_run(db_session, run_id=run2.id, qty_g=35_000, item_id=yarn.id, user_id=1)
    db_session.commit()

    db_session.refresh(sl)
    lots = db_session.query(YarnLot).filter_by(item_id=yarn.id).all()
    assert sum(l.remaining_g for l in lots) == sl.qty_g == 40_000


def test_tracing_roll_returns_batches_and_suppliers(auth_client: TestClient, db_session: Session, test_setup):
    """Proof 4: Tracing a roll returns its run, machine, order, yarn batches, and suppliers."""
    sup = test_setup["sup"]
    fabric = test_setup["fabric"]
    yarn = test_setup["yarn"]
    machine = test_setup["machine"]

    # Create order
    buyer = test_setup["buyer"]
    order = create_order(
        db_session, buyer_id=buyer.id, order_date=date(2026, 10, 5),
        delivery_date=date(2026, 11, 5),
        lines=[{"item_id": fabric.id, "qty_meters": 50, "rate_per_meter_paise": 10000_00}],
        user_id=1
    )
    confirm_order(db_session, order.id, user_id=1)
    db_session.commit()

    # Start run for order
    run = start_run(db_session, machine_id=machine.id, order_id=order.id, item_id=fabric.id, user_id=1)
    db_session.commit()

    # Issue yarn from LOT-TRACE-B (from test_setup)
    lot_b = db_session.query(YarnLot).filter_by(lot_number="LOT-TRACE-B").one()
    if lot_b.remaining_g < 10_000:
        lot_b.remaining_g = 20_000
        db_session.commit()

    issue_material(db_session, run_id=run.id, lot_id=lot_b.id, qty_g=10_000, user_id=1)
    db_session.commit()

    # Advance to inspection and produce roll
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1)  # warping -> weaving
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1)  # weaving -> inspection
    roll = create_roll(db_session, run_id=run.id, length_cm=5000, weight_g=10000, user_id=1)
    db_session.commit()

    # Call API trace endpoint: GET /api/rolls/{roll_id}/trace
    r = auth_client.get(f"/api/rolls/{roll.id}/trace")
    assert r.status_code == 200
    trace = r.json()

    # Assert roll details
    assert trace["roll"]["id"] == roll.id
    assert trace["roll"]["roll_number"] == roll.roll_number
    assert trace["roll"]["length_m"] == 50.0

    # Assert run, machine, order
    assert trace["run"]["id"] == run.id
    assert trace["machine"]["code"] == machine.code
    assert trace["order"]["id"] == order.id
    assert trace["order"]["buyer_id"] == buyer.id

    # Assert yarn batches and suppliers
    assert len(trace["yarn_batches"]) == 1
    batch = trace["yarn_batches"][0]
    assert batch["lot_number"] == "LOT-TRACE-B"
    assert batch["issued_g"] == 10_000
    assert batch["supplier"]["name"] == sup.name

    assert len(trace["suppliers"]) == 1
    assert trace["suppliers"][0]["name"] == sup.name


def test_tracing_roll_with_opening_balance_batch(auth_client: TestClient, db_session: Session, test_setup):
    """Trace a roll made from an opening-balance batch (no receipt/PO)."""
    fabric = test_setup["fabric"]
    machine = test_setup["machine"]

    # Create opening balance lot
    opening_lot = YarnLot(
        receipt_id=None,
        item_id=test_setup["yarn"].id,
        lot_number="LOT-OPENING-SPECIAL",
        qty_g=50_000,
        remaining_g=50_000,
    )
    db_session.add(opening_lot)
    db_session.commit()

    run = start_run(db_session, machine_id=machine.id, order_id=None, item_id=fabric.id, user_id=1)
    db_session.commit()

    issue_material(db_session, run_id=run.id, lot_id=opening_lot.id, qty_g=5_000, user_id=1)
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1)
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1)
    roll = create_roll(db_session, run_id=run.id, length_cm=2500, weight_g=5000, user_id=1)
    db_session.commit()

    r = auth_client.get(f"/api/rolls/{roll.id}/trace")
    assert r.status_code == 200
    trace = r.json()

    assert len(trace["yarn_batches"]) == 1
    assert trace["yarn_batches"][0]["lot_number"] == "LOT-OPENING-SPECIAL"
    assert trace["yarn_batches"][0]["supplier"]["name"] == "Opening Balance"
    assert trace["suppliers"][0]["name"] == "Opening Balance"


def test_storage_layer_enforces_remaining_non_negative_and_lte_qty(db_session: Session, test_setup):
    """Storage-level proof: SQLite check constraints refuse remaining_g < 0 and remaining_g > qty_g."""
    yarn = test_setup["yarn"]

    lot = YarnLot(
        receipt_id=None,
        item_id=yarn.id,
        lot_number="LOT-CK-TEST",
        qty_g=10_000,
        remaining_g=10_000,
    )
    db_session.add(lot)
    db_session.commit()

    # 1. Direct SQL update trying to set remaining_g < 0
    with pytest.raises(Exception) as exc1:
        db_session.execute(text(f"UPDATE yarn_lot SET remaining_g = -1 WHERE id = {lot.id}"))
        db_session.commit()
    db_session.rollback()
    assert "CHECK constraint failed" in str(exc1.value)

    # 2. Direct SQL update trying to set remaining_g > qty_g
    with pytest.raises(Exception) as exc2:
        db_session.execute(text(f"UPDATE yarn_lot SET remaining_g = 15000 WHERE id = {lot.id}"))
        db_session.commit()
    db_session.rollback()
    assert "CHECK constraint failed" in str(exc2.value)
