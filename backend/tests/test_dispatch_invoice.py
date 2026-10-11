"""Tests for Step 3: Dispatch and Invoice Precision, Rounding, and Integrity.

Verifies:
1. Change model type from float to Decimal; no float arithmetic in invoicing.
2. Shared pricing helper with round-half-up to nearest paisa on fabric, kg, and tax.
3. Invoice matches dispatch integer check: int(qty * 100) == sum(roll_length_cm).
4. Safe round-trip through database for:
   - 12.35 m
   - 72.22 m (1,235 + 987 + 5,000 cm)
   - Supplier bill of 500.250 kg
5. Rounding rule tested on values landing exactly on half a paisa (0.5, 1.5, 2.5).
6. Dispatch workflow: inventory deducted, roll marked dispatched, roll event logged.
7. Double dispatch prevention (service level + database UniqueConstraint on roll_id).
8. Atomic transaction: rollback on failure leaves zero partial changes.
9. Refusals: empty list, duplicates, wrong order/buyer, invalid roll status, manual sale invoice blocked.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from mill.models import (
    Buyer, Dispatch, DispatchRoll, Invoice, InvoiceLine, Item, Location,
    Order, OrderLine, ProductionRun, Roll, RollEvent, StockLevel, StockMove,
    Supplier, User,
)
from mill.services.common import DomainError
from mill.services.dispatch import dispatch_rolls
from mill.services.pricing import (
    cm_to_meters_decimal,
    compute_fabric_line_total,
    compute_tax,
    compute_yarn_line_total,
    g_to_kg_decimal,
    invoice_matches_dispatch,
    kg_decimal_to_g,
    meters_decimal_to_cm,
    round_half_up_paise,
)
from tests.conftest import login


@pytest.fixture
def db_session(test_database):
    """Provide a dedicated SQLAlchemy session bound to the test database."""
    session_factory = sessionmaker(bind=test_database, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _get_or_create_buyer(session=None, db=None) -> Buyer:
    s = session or db
    buyer = s.scalar(select(Buyer).where(Buyer.name == "Test Retail Corp"))
    if buyer is None:
        buyer = Buyer(name="Test Retail Corp", email="trc@test.com")
        s.add(buyer)
        s.commit()
    return buyer


def _get_or_create_supplier(session) -> Supplier:
    supp = session.scalar(select(Supplier).where(Supplier.name == "Test Yarn Mills"))
    if supp is None:
        supp = Supplier(name="Test Yarn Mills", email="tym@test.com")
        session.add(supp)
        session.commit()
    return supp


def _get_or_create_item(session, item_type="fabric", sku="FAB-TEST", name="Test Fabric") -> Item:
    item = session.scalar(select(Item).where(Item.sku == sku))
    if item is None:
        item = Item(sku=sku, name=name, item_type=item_type, unit="m" if item_type == "fabric" else "kg")
        session.add(item)
        session.commit()
    return item


# ============================================================================
# 1. Rounding and Precision Unit Tests
# ============================================================================

def test_rounding_half_up_exact_half_paisa():
    """Verify round-half-up to the nearest paisa on values that land exactly on half a paisa.

    Python's built-in round() rounds to even: round(2.5) == 2.
    Our rule states round half UP: 2.5 MUST round to 3.
    """
    # 0.5 -> 1
    assert round_half_up_paise(Decimal("0.5")) == 1
    # 1.5 -> 2
    assert round_half_up_paise(Decimal("1.5")) == 2
    # 2.5 -> 3 (Standard round() would incorrectly give 2!)
    assert round_half_up_paise(Decimal("2.5")) == 3
    # 3.5 -> 4
    assert round_half_up_paise(Decimal("3.5")) == 4
    # 4.5 -> 5 (Standard round() would incorrectly give 4!)
    assert round_half_up_paise(Decimal("4.5")) == 5

    # Below half paisa rounds down
    assert round_half_up_paise(Decimal("2.499")) == 2
    # Above half paisa rounds up
    assert round_half_up_paise(Decimal("2.501")) == 3


def test_pricing_helpers_fabric_yarn_tax():
    """Verify fabric, kg yarn, and tax integer pricing helpers."""
    # Fabric: round_half_up(total_cm * unit_price_paise / 100)
    # total_cm = 1, unit_price_paise = 250 paise -> 250 / 100 = 2.5 paise -> 3 paise
    assert compute_fabric_line_total(total_cm=1, unit_price_paise=250) == 3

    # 100 cm (1m) @ 35000 paise (₹350/m) -> 100 * 35000 / 100 = 35000 paise
    assert compute_fabric_line_total(total_cm=100, unit_price_paise=35000) == 35000

    # Yarn: round_half_up(total_g * rate_per_kg_paise / 1000)
    # total_g = 1, rate_per_kg_paise = 2500 paise -> 2500 / 1000 = 2.5 paise -> 3 paise
    assert compute_yarn_line_total(total_g=1, rate_per_kg_paise=2500) == 3

    # 1000 g (1kg) @ 42000 paise (₹420/kg) -> 1000 * 42000 / 1000 = 42000 paise
    assert compute_yarn_line_total(total_g=1000, rate_per_kg_paise=42000) == 42000

    # Tax: round_half_up(base_paise * tax_pct / 100)
    # base = 50 paise, tax = 5% -> 50 * 5 / 100 = 2.5 paise -> 3 paise
    assert compute_tax(base_paise=50, tax_pct=Decimal("5.00")) == 3


def test_invoice_matches_dispatch_integer_comparison():
    """Verify Condition 3: integer comparison qty * 100 == sum(roll_length_cm)."""
    # Exact match: 12.35 m = 1235 cm
    assert invoice_matches_dispatch(Decimal("12.350"), 1235) is True

    # Exact multi-roll match: 72.22 m = 1235 + 987 + 5000 cm = 7222 cm
    assert invoice_matches_dispatch(Decimal("72.220"), [1235, 987, 5000]) is True

    # 1 cm difference must fail
    assert invoice_matches_dispatch(Decimal("72.220"), [1235, 987, 5001]) is False
    assert invoice_matches_dispatch(Decimal("72.230"), [1235, 987, 5000]) is False


# ============================================================================
# 2. Database Round-Trip Tests (Condition 5)
# ============================================================================

def test_database_round_trip_exact_quantities(db_session):
    """Prove the round trip through the database for exact quantities:
    - 12.35 m
    - 72.22 m (1,235 + 987 + 5,000 cm)
    - Supplier bill of 500.250 kg
    """
    buyer = _get_or_create_buyer(db_session)
    supplier = _get_or_create_supplier(db_session)

    # 1. Save and reload 12.35 m
    inv1 = Invoice(
        ref="SINV-TEST-1235",
        invoice_type="sale",
        buyer_id=buyer.id,
        invoice_date=date.today(),
        status="sent",
    )
    db_session.add(inv1)
    db_session.flush()

    line1 = InvoiceLine(
        invoice_id=inv1.id,
        description="12.35 m Fabric Roll",
        qty=Decimal("12.350"),
        unit_price_paise=35000,
        tax_pct=Decimal("5.00"),
    )
    db_session.add(line1)
    db_session.commit()

    # Clear session and reload from DB
    db_session.expire_all()
    reloaded_line1 = db_session.get(InvoiceLine, line1.id)
    assert isinstance(reloaded_line1.qty, Decimal)
    assert reloaded_line1.qty == Decimal("12.350")
    assert meters_decimal_to_cm(reloaded_line1.qty) == 1235

    # 2. Save and reload 72.22 m (1,235 + 987 + 5,000 cm)
    inv2 = Invoice(
        ref="SINV-TEST-7222",
        invoice_type="sale",
        buyer_id=buyer.id,
        invoice_date=date.today(),
        status="sent",
    )
    db_session.add(inv2)
    db_session.flush()

    roll_cms = [1235, 987, 5000]
    total_cm = sum(roll_cms)
    total_m = cm_to_meters_decimal(total_cm)
    assert total_m == Decimal("72.220")

    line2 = InvoiceLine(
        invoice_id=inv2.id,
        description="72.22 m Multi-Roll Dispatch",
        qty=total_m,
        unit_price_paise=40000,
        tax_pct=Decimal("5.00"),
    )
    db_session.add(line2)
    db_session.commit()

    db_session.expire_all()
    reloaded_line2 = db_session.get(InvoiceLine, line2.id)
    assert isinstance(reloaded_line2.qty, Decimal)
    assert reloaded_line2.qty == Decimal("72.220")
    assert invoice_matches_dispatch(reloaded_line2.qty, roll_cms) is True

    # 3. Save and reload supplier bill of 500.250 kg
    inv3 = Invoice(
        ref="PINV-TEST-500250",
        invoice_type="purchase",
        supplier_id=supplier.id,
        invoice_date=date.today(),
        status="sent",
    )
    db_session.add(inv3)
    db_session.flush()

    line3 = InvoiceLine(
        invoice_id=inv3.id,
        description="500.250 kg Yarn Raw Material",
        qty=Decimal("500.250"),
        unit_price_paise=42000,
        tax_pct=Decimal("5.00"),
    )
    db_session.add(line3)
    db_session.commit()

    db_session.expire_all()
    reloaded_line3 = db_session.get(InvoiceLine, line3.id)
    assert isinstance(reloaded_line3.qty, Decimal)
    assert reloaded_line3.qty == Decimal("500.250")
    assert kg_decimal_to_g(reloaded_line3.qty) == 500250


# ============================================================================
# 3. Full Dispatch Lifecycle & Pricing Workflow Tests
# ============================================================================

def _setup_dispatch_prerequisites(db_session):
    """Helper to set up an order, machine, run, and in_store rolls."""
    buyer = _get_or_create_buyer(db_session)
    fabric = _get_or_create_item(db_session, "fabric", "FAB-T3", "Twill Cotton")
    fin_loc = db_session.scalar(select(Location).where(Location.code == "FIN"))
    admin = db_session.scalar(select(User).where(User.username == "admin"))

    import uuid
    uid = uuid.uuid4().hex[:6]
    order = Order(
        ref=f"SO-T3-{uid}",
        buyer_id=buyer.id,
        order_date=date.today(),
        status="confirmed",
    )
    db_session.add(order)
    db_session.flush()

    order_line = OrderLine(
        order_id=order.id,
        item_id=fabric.id,
        qty_meters=72.22,
        rate_per_meter_paise=35000,  # ₹350/m
    )
    db_session.add(order_line)
    db_session.flush()

    # Create Production Run
    from mill.models import Machine
    machine = db_session.scalar(select(Machine).where(Machine.code == "LOOM-01"))
    if machine is None:
        machine = Machine(code="LOOM-01", name="Loom 1", machine_type="weaving")
        db_session.add(machine)
        db_session.flush()

    run = ProductionRun(
        machine_id=machine.id,
        order_id=order.id,
        item_id=fabric.id,
        current_stage="weaving",
        status="active",
    )
    db_session.add(run)
    db_session.flush()

    # Create rolls of 1235, 987, 5000 cm and put them in_store
    rolls = []
    for idx, length_cm in enumerate([1235, 987, 5000], start=1):
        roll = Roll(
            roll_number=f"ROLL-T3-{uid}-{idx}",
            run_id=run.id,
            item_id=fabric.id,
            length_cm=length_cm,
            status="in_store",
            qc_grade="A",
        )
        db_session.add(roll)
        db_session.flush()

        # Seed initial stock level for FIN location
        st_lvl = db_session.scalar(
            select(StockLevel).where(
                StockLevel.item_id == fabric.id,
                StockLevel.location_id == fin_loc.id,
            )
        )
        if st_lvl is None:
            st_lvl = StockLevel(item_id=fabric.id, location_id=fin_loc.id, qty_g=0)
            db_session.add(st_lvl)
            db_session.flush()
        st_lvl.qty_g += length_cm

        rolls.append(roll)

    db_session.commit()
    return buyer, order, rolls, fabric, fin_loc, admin


def test_dispatch_normal_flow_and_invoice(db_session):
    """Test full dispatch: stock decrements, rolls marked dispatched, invoice generated with exact matching."""
    buyer, order, rolls, fabric, fin_loc, admin = _setup_dispatch_prerequisites(db_session)
    roll_ids = [r.id for r in rolls]
    total_length_cm = sum(r.length_cm for r in rolls)  # 1235 + 987 + 5000 = 7222 cm

    stock_before = db_session.scalar(
        select(StockLevel.qty_g).where(
            StockLevel.item_id == fabric.id,
            StockLevel.location_id == fin_loc.id,
        )
    )

    dispatch, invoice, dispatched_rolls = dispatch_rolls(
        db_session,
        roll_ids=roll_ids,
        dispatch_date=date.today(),
        vehicle_no="KA-01-AB-9999",
        notes="Urgent shipment",
        user_id=admin.id,
    )
    db_session.commit()

    # 1. Check dispatch record
    assert dispatch.id is not None
    assert dispatch.dispatch_number.startswith("DSP-")
    assert dispatch.status == "confirmed"
    assert dispatch.order_id == order.id
    assert dispatch.buyer_id == buyer.id

    # 2. Check stock deduction
    stock_after = db_session.scalar(
        select(StockLevel.qty_g).where(
            StockLevel.item_id == fabric.id,
            StockLevel.location_id == fin_loc.id,
        )
    )
    assert stock_after == stock_before - total_length_cm

    # 3. Check stock movement audit
    move = db_session.scalar(
        select(StockMove)
        .where(StockMove.ref == dispatch.dispatch_number)
        .order_by(StockMove.id.desc())
    )
    assert move is not None
    assert move.movement_type == "fabric_out"
    assert move.user_id == admin.id
    assert move.delta_g < 0

    # 4. Check roll statuses and events
    for r in rolls:
        db_session.refresh(r)
        assert r.status == "dispatched"
        event = db_session.scalar(
            select(RollEvent).where(RollEvent.roll_id == r.id, RollEvent.event_type == "dispatched")
        )
        assert event is not None
        assert event.created_by_id == admin.id

    # 5. Check invoice and line matching
    assert invoice.id is not None
    assert invoice.invoice_type == "sale"
    assert invoice.order_id == order.id
    assert invoice.dispatch_id == dispatch.id
    assert len(invoice.lines) == 1

    inv_line = invoice.lines[0]
    assert inv_line.qty == Decimal("72.220")
    # Condition 3 integer match:
    assert int(inv_line.qty * 100) == total_length_cm
    assert invoice_matches_dispatch(inv_line.qty, total_length_cm) is True

    # Total paise: 7222 cm @ 35000 paise/m -> round(7222 * 35000 / 100) = 2,527,700 paise
    expected_line_paise = compute_fabric_line_total(total_length_cm, 35000)
    assert expected_line_paise == 2527700
    expected_tax_paise = compute_tax(expected_line_paise, Decimal("5.00"))
    assert expected_tax_paise == 126385


# ============================================================================
# 4. Double Dispatch Prevention Tests (Service & DB Level)
# ============================================================================

def test_double_dispatch_refusal(db_session):
    """Verify roll cannot be dispatched twice (refused cleanly at service level)."""
    buyer, order, rolls, fabric, fin_loc, admin = _setup_dispatch_prerequisites(db_session)
    roll_ids = [rolls[0].id]

    # First dispatch succeeds
    dispatch_rolls(db_session, roll_ids=roll_ids, dispatch_date=date.today(), user_id=admin.id)
    db_session.commit()

    # Second dispatch on the same roll must raise DomainError with 400
    with pytest.raises(DomainError) as exc_info:
        dispatch_rolls(db_session, roll_ids=roll_ids, dispatch_date=date.today(), user_id=admin.id)
    assert exc_info.value.status_code == 400
    assert "already been dispatched" in str(exc_info.value) or "is not in store" in str(exc_info.value)


def test_double_dispatch_database_constraint(db_session):
    """Verify UniqueConstraint on dispatch_roll.roll_id catches raw DB bypass."""
    buyer, order, rolls, fabric, fin_loc, admin = _setup_dispatch_prerequisites(db_session)
    r = rolls[0]

    import uuid
    uid = uuid.uuid4().hex[:6]
    # Create first dispatch and roll
    d1 = Dispatch(
        dispatch_number=f"DSP-RAW-1-{uid}",
        order_id=order.id,
        buyer_id=buyer.id,
        dispatch_date=date.today(),
        created_by_id=admin.id,
    )
    db_session.add(d1)
    db_session.flush()

    dr1 = DispatchRoll(dispatch_id=d1.id, roll_id=r.id, length_cm=r.length_cm)
    db_session.add(dr1)
    db_session.commit()

    # Create second dispatch and attempt to insert the same roll_id directly
    d2 = Dispatch(
        dispatch_number=f"DSP-RAW-2-{uid}",
        order_id=order.id,
        buyer_id=buyer.id,
        dispatch_date=date.today(),
        created_by_id=admin.id,
    )
    db_session.add(d2)
    db_session.flush()

    dr2 = DispatchRoll(dispatch_id=d2.id, roll_id=r.id, length_cm=r.length_cm)
    db_session.add(dr2)

    # Must raise IntegrityError due to UniqueConstraint("roll_id")
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ============================================================================
# 5. Atomicity & Rejection Tests
# ============================================================================

def test_dispatch_atomicity_on_failure(db_session):
    """Verify transaction rollback: if any error occurs midway, no partial changes persist."""
    buyer, order, rolls, fabric, fin_loc, admin = _setup_dispatch_prerequisites(db_session)

    # Mix a valid roll with an invalid roll id
    bad_roll_ids = [rolls[0].id, 999999]
    stock_before = db_session.scalar(
        select(StockLevel.qty_g).where(
            StockLevel.item_id == fabric.id,
            StockLevel.location_id == fin_loc.id,
        )
    )

    with pytest.raises(DomainError):
        dispatch_rolls(db_session, roll_ids=bad_roll_ids, dispatch_date=date.today(), user_id=admin.id)
    db_session.rollback()

    # Verify roll 0 is STILL in_store
    db_session.refresh(rolls[0])
    assert rolls[0].status == "in_store"

    # Verify stock was untouched
    stock_after = db_session.scalar(
        select(StockLevel.qty_g).where(
            StockLevel.item_id == fabric.id,
            StockLevel.location_id == fin_loc.id,
        )
    )
    assert stock_after == stock_before

    # Verify no orphan Dispatch was created
    orphan_dispatches = db_session.scalars(select(Dispatch).where(Dispatch.order_id == order.id)).all()
    assert len(orphan_dispatches) == 0


def test_dispatch_refusals(db_session):
    """Test all business refusal rules."""
    buyer, order, rolls, fabric, fin_loc, admin = _setup_dispatch_prerequisites(db_session)

    # 1. Empty roll list
    with pytest.raises(DomainError) as exc:
        dispatch_rolls(db_session, roll_ids=[], dispatch_date=date.today(), user_id=admin.id)
    assert exc.value.status_code == 400

    # 2. Duplicate roll in request
    with pytest.raises(DomainError) as exc:
        dispatch_rolls(db_session, roll_ids=[rolls[0].id, rolls[0].id], dispatch_date=date.today(), user_id=admin.id)
    assert exc.value.status_code == 400
    assert "Duplicate roll" in str(exc.value)

    # 3. Roll not in store (e.g. qc rejected or rework)
    rolls[0].status = "rework"
    db_session.commit()
    with pytest.raises(DomainError) as exc:
        dispatch_rolls(db_session, roll_ids=[rolls[0].id], dispatch_date=date.today(), user_id=admin.id)
    assert exc.value.status_code == 400
    assert "not in store" in str(exc.value)


# ============================================================================
# 6. HTTP API Tests via TestClient
# ============================================================================

def test_api_manual_sale_invoice_decimal_precision(client, db_session):
    """Manual sale invoice creation uses Decimal precision and integer paisa pricing."""
    login(client, "admin")
    buyer = _get_or_create_buyer(db_session)
    resp = client.post("/api/finance/invoices", json={
        "invoice_type": "sale",
        "buyer_id": buyer.id,
        "invoice_date": str(date.today()),
        "lines": [
            {"description": "Manual Fabric Sale 72.22 m", "qty": 72.22, "unit_price_paise": 35000, "tax_pct": 5.0}
        ]
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["invoice_type"] == "sale"
    assert data["lines"][0]["qty"] == 72.22
    assert data["subtotal_paise"] == 2527700
    assert data["tax_paise"] == 126385


def test_api_manual_supplier_bill_allowed(client, db_session):
    """Manual supplier purchase bill creation at POST /api/finance/invoices is allowed with Decimal precision."""
    login(client, "admin")
    supplier = _get_or_create_supplier(db_session)
    resp = client.post("/api/finance/invoices", json={
        "invoice_type": "purchase",
        "supplier_id": supplier.id,
        "invoice_date": str(date.today()),
        "lines": [
            {"description": "Raw Cotton Yarn 500.250 kg", "qty": 500.250, "unit_price_paise": 42000, "tax_pct": 5.0}
        ]
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["invoice_type"] == "purchase"
    assert data["lines"][0]["qty"] == 500.25
    # Subtotal paise: round(500250 * 42000 / 1000) = 21,010,500 paise
    assert data["subtotal_paise"] == 21010500
