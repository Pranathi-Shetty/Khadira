"""Tests for Step 4: Derived Order Progress, Tolerance, and Order Tracking.

Verifies:
1. Tolerance handling (default 5%, customizable per order).
2. Single progress calculation function derived from actual physical rolls.
3. Separate states: production_complete (passed >= order - tolerance) vs delivered (dispatched >= order - tolerance).
4. Finishing a production run does NOT complete an order if passed meters are short.
5. Hand-calculated examples:
   - Exactly at boundary (95.0m passed for 100m order @ 5% tolerance -> production_complete).
   - Just inside boundary (95.01m passed -> production_complete).
   - Just outside boundary (94.99m passed -> in_production).
   - Order with rejected rolls (100m produced, 10m rejected, 90m passed -> in_production).
   - Partly dispatched order (98m passed, 50m dispatched -> production_complete, not delivered).
   - Fully dispatched order (98m dispatched -> delivered).
6. "Where is my order?" tracking endpoint GET /api/orders/{id}/tracking reporting stage, meters, roll counts, and timeliness (on_time vs late).
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from mill.models import (
    Buyer, Item, Location, Machine, Order, OrderLine, ProductionRun,
    Roll, StockLevel, User,
)
from mill.services.orders import calculate_order_progress, create_order
from mill.services.production import advance_stage, create_roll
from mill.services.qc import inspect_roll, move_to_store
from mill.services.dispatch import dispatch_rolls
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


def _get_or_create_buyer(session) -> Buyer:
    buyer = session.scalar(select(Buyer).where(Buyer.name == "Global Textiles"))
    if buyer is None:
        buyer = Buyer(name="Global Textiles", email="gt@test.com")
        session.add(buyer)
        session.commit()
    return buyer


def _get_or_create_fabric(session) -> Item:
    item = session.scalar(select(Item).where(Item.sku == "FAB-STEP4"))
    if item is None:
        item = Item(
            sku="FAB-STEP4",
            name="Step 4 Fabric",
            item_type="fabric",
            unit="m",
            yarn_kg_per_meter=0.20,
        )
        session.add(item)
        session.commit()
    return item


def _get_or_create_machine(session) -> Machine:
    machine = session.scalar(select(Machine).where(Machine.code == "LOOM-S4"))
    if machine is None:
        machine = Machine(code="LOOM-S4", name="Step 4 Loom", machine_type="weaving")
        session.add(machine)
        session.commit()
    return machine


def _setup_test_order(db_session, qty_meters: float = 100.0, tolerance_pct: float = 5.0, delivery_days: int = 7):
    buyer = _get_or_create_buyer(db_session)
    fabric = _get_or_create_fabric(db_session)
    machine = _get_or_create_machine(db_session)
    admin = db_session.scalar(select(User).where(User.username == "admin"))
    fin_loc = db_session.scalar(select(Location).where(Location.code == "FIN"))

    uid = uuid.uuid4().hex[:6]
    delivery_date = date.today() + timedelta(days=delivery_days)
    order = create_order(
        db_session,
        buyer_id=buyer.id,
        order_date=date.today(),
        delivery_date=delivery_date,
        tolerance_pct=Decimal(str(tolerance_pct)),
        lines=[{"item_id": fabric.id, "qty_meters": qty_meters, "rate_per_meter_paise": 35000}],
        user_id=admin.id,
    )
    order.status = "confirmed"
    db_session.flush()

    run = ProductionRun(
        machine_id=machine.id,
        order_id=order.id,
        item_id=fabric.id,
        current_stage="inspection",
        status="active",
    )
    db_session.add(run)
    db_session.commit()

    return buyer, order, run, fabric, machine, admin, fin_loc


# ============================================================================
# 1. Hand-Calculated Tolerance Boundary Tests
# ============================================================================

def test_tolerance_boundary_exact(db_session):
    """Hand-calculated test: exactly at the 5% tolerance boundary.

    Order: 100.00 m. Tolerance: 5.00%.
    Minimum acceptable: 100 * 0.95 = 95.000 m (9,500 cm).
    Passed: 9,500 cm = 95.000 m.
    Result: production_complete.
    """
    buyer, order, run, fabric, machine, admin, _ = _setup_test_order(db_session, 100.0, 5.0)

    # Produce roll of exactly 9,500 cm
    roll = create_roll(db_session, run_id=run.id, length_cm=9500, weight_g=18000, user_id=admin.id)
    assert order.status == "in_production"

    # QC pass
    inspect_roll(db_session, roll_id=roll.id, verdict="passed", grade="A", note=None, user_id=admin.id)
    db_session.commit()

    progress = calculate_order_progress(db_session, order.id)
    assert progress["ordered_meters"] == 100.0
    assert progress["min_acceptable_meters"] == 95.0
    assert progress["meters_by_stage"]["passed"] == 95.0
    assert progress["percentages"]["passed_pct"] == 95.0
    assert order.status == "production_complete"
    assert progress["status"] == "production_complete"


def test_tolerance_boundary_just_inside(db_session):
    """Hand-calculated test: just inside the 5% tolerance boundary (95.010 m).

    Order: 100.00 m. Tolerance: 5.00%.
    Minimum acceptable: 95.000 m.
    Passed: 9,501 cm = 95.010 m.
    Result: production_complete.
    """
    buyer, order, run, fabric, machine, admin, _ = _setup_test_order(db_session, 100.0, 5.0)

    roll = create_roll(db_session, run_id=run.id, length_cm=9501, weight_g=18000, user_id=admin.id)
    inspect_roll(db_session, roll_id=roll.id, verdict="passed", grade="A", note=None, user_id=admin.id)
    db_session.commit()

    progress = calculate_order_progress(db_session, order.id)
    assert progress["meters_by_stage"]["passed"] == 95.01
    assert progress["meters_by_stage"]["passed"] >= progress["min_acceptable_meters"]
    assert order.status == "production_complete"


def test_tolerance_boundary_just_outside(db_session):
    """Hand-calculated test: just outside the 5% tolerance boundary (94.990 m).

    Order: 100.00 m. Tolerance: 5.00%.
    Minimum acceptable: 95.000 m.
    Passed: 9,499 cm = 94.990 m.
    Result: in_production (short by 1 cm).
    """
    buyer, order, run, fabric, machine, admin, _ = _setup_test_order(db_session, 100.0, 5.0)

    roll = create_roll(db_session, run_id=run.id, length_cm=9499, weight_g=18000, user_id=admin.id)
    inspect_roll(db_session, roll_id=roll.id, verdict="passed", grade="A", note=None, user_id=admin.id)
    db_session.commit()

    progress = calculate_order_progress(db_session, order.id)
    assert progress["meters_by_stage"]["passed"] == 94.99
    assert progress["meters_by_stage"]["passed"] < progress["min_acceptable_meters"]
    assert order.status == "in_production"
    assert progress["status"] == "in_production"


# ============================================================================
# 2. Rejected Rolls and Production Run Completion Tests
# ============================================================================

def test_order_with_rejected_rolls(db_session):
    """Test order with rejected rolls: 100m produced, but 10m rejected -> passed is 90m -> remains in_production."""
    buyer, order, run, fabric, machine, admin, _ = _setup_test_order(db_session, 100.0, 5.0)

    # Roll 1: 50m passed
    r1 = create_roll(db_session, run_id=run.id, length_cm=5000, weight_g=10000, user_id=admin.id)
    inspect_roll(db_session, roll_id=r1.id, verdict="passed", grade="A", note=None, user_id=admin.id)

    # Roll 2: 40m passed
    r2 = create_roll(db_session, run_id=run.id, length_cm=4000, weight_g=8000, user_id=admin.id)
    inspect_roll(db_session, roll_id=r2.id, verdict="passed", grade="A", note=None, user_id=admin.id)

    # Roll 3: 10m rejected
    r3 = create_roll(db_session, run_id=run.id, length_cm=1000, weight_g=2000, user_id=admin.id)
    inspect_roll(db_session, roll_id=r3.id, verdict="reject", grade="C", note="Broken warp threads", user_id=admin.id)
    db_session.commit()

    progress = calculate_order_progress(db_session, order.id)
    assert progress["meters_by_stage"]["produced"] == 100.0
    assert progress["meters_by_stage"]["passed"] == 90.0
    assert progress["meters_by_stage"]["rejected"] == 10.0
    assert progress["roll_counts_by_stage"]["passed"] == 2
    assert progress["roll_counts_by_stage"]["rejected"] == 1
    # 90m is less than 95m tolerance threshold
    assert order.status == "in_production"


def test_production_run_completion_does_not_complete_short_order(db_session):
    """Finishing a production run does NOT mark the order complete if passed meters are short."""
    buyer, order, run, fabric, machine, admin, _ = _setup_test_order(db_session, 100.0, 5.0)

    # Produce only 50m (5,000 cm)
    roll = create_roll(db_session, run_id=run.id, length_cm=5000, weight_g=10000, user_id=admin.id)
    inspect_roll(db_session, roll_id=roll.id, verdict="passed", grade="A", note=None, user_id=admin.id)

    # Advance run to final inspection stage and complete it
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=admin.id)
    db_session.commit()

    db_session.refresh(run)
    db_session.refresh(order)
    assert run.status == "completed"
    # Order must NOT be completed directly by run finish!
    assert order.status == "in_production"


# ============================================================================
# 3. Delivered vs Production Complete (Separate States)
# ============================================================================

def test_partly_dispatched_vs_delivered(db_session):
    """Separate states: production_complete (passed >= 95m) vs delivered (dispatched >= 95m)."""
    buyer, order, run, fabric, machine, admin, fin_loc = _setup_test_order(db_session, 100.0, 5.0)

    # Produce two rolls: 50m and 48m (total 98m >= 95m)
    r1 = create_roll(db_session, run_id=run.id, length_cm=5000, weight_g=10000, user_id=admin.id)
    inspect_roll(db_session, roll_id=r1.id, verdict="passed", grade="A", note=None, user_id=admin.id)
    move_to_store(db_session, roll_id=r1.id, user_id=admin.id)

    r2 = create_roll(db_session, run_id=run.id, length_cm=4800, weight_g=9600, user_id=admin.id)
    inspect_roll(db_session, roll_id=r2.id, verdict="passed", grade="A", note=None, user_id=admin.id)
    move_to_store(db_session, roll_id=r2.id, user_id=admin.id)
    db_session.commit()

    db_session.refresh(order)
    assert order.status == "production_complete"

    # Part-dispatch Roll 1 (50.0m dispatched < 95m)
    dispatch_rolls(db_session, roll_ids=[r1.id], dispatch_date=date.today(), user_id=admin.id)
    db_session.commit()

    db_session.refresh(order)
    # Still production_complete (not delivered, because only 50m of 95m delivered)
    assert order.status == "production_complete"

    progress = calculate_order_progress(db_session, order.id)
    assert progress["meters_by_stage"]["dispatched"] == 50.0
    assert progress["meters_by_stage"]["in_store"] == 48.0
    assert progress["status"] == "production_complete"

    # Dispatch remaining Roll 2 (48.0m -> total 98.0m dispatched >= 95m)
    dispatch_rolls(db_session, roll_ids=[r2.id], dispatch_date=date.today(), user_id=admin.id)
    db_session.commit()

    db_session.refresh(order)
    # Now order status is delivered!
    assert order.status == "delivered"
    progress = calculate_order_progress(db_session, order.id)
    assert progress["meters_by_stage"]["dispatched"] == 98.0
    assert progress["percentages"]["dispatched_pct"] == 98.0
    assert progress["schedule_status"] == "delivered"


# ============================================================================
# 4. "Where Is My Order?" Tracking Endpoint Tests
# ============================================================================

def test_order_tracking_endpoint_on_time_and_late(client, db_session):
    """Test GET /api/orders/{id}/tracking answers stage, meters, roll counts, and schedule timeliness."""
    login(client, "admin")

    # 1. On-time order in production (delivery date 5 days ahead)
    buyer, order, run, fabric, machine, admin, _ = _setup_test_order(db_session, 100.0, 5.0, delivery_days=5)
    r1 = create_roll(db_session, run_id=run.id, length_cm=4000, weight_g=8000, user_id=admin.id)
    inspect_roll(db_session, roll_id=r1.id, verdict="passed", grade="A", note=None, user_id=admin.id)
    move_to_store(db_session, roll_id=r1.id, user_id=admin.id)

    r2 = create_roll(db_session, run_id=run.id, length_cm=2000, weight_g=4000, user_id=admin.id)
    db_session.commit()

    res = client.get(f"/api/orders/{order.id}/tracking")
    assert res.status_code == 200
    data = res.json()

    assert data["order_id"] == order.id
    assert data["order_ref"] == order.ref
    assert data["status"] == "in_production"
    assert data["current_stage"] == "in_store"
    assert data["ordered_meters"] == 100.0
    assert data["tolerance_pct"] == 5.0
    assert data["min_acceptable_meters"] == 95.0
    assert data["meters_by_stage"]["passed"] == 40.0
    assert data["meters_by_stage"]["awaiting_qc"] == 20.0
    assert data["roll_counts_by_stage"]["produced"] == 2
    assert data["roll_counts_by_stage"]["passed"] == 1
    assert data["roll_counts_by_stage"]["awaiting_qc"] == 1
    assert data["is_late"] is False
    assert data["schedule_status"] == "on_time"
    assert data["days_remaining"] == 5

    # 2. Late order (delivery date set in the past)
    order.delivery_date = date.today() - timedelta(days=3)
    db_session.commit()

    res_late = client.get(f"/api/orders/{order.id}/tracking")
    assert res_late.status_code == 200
    data_late = res_late.json()
    assert data_late["is_late"] is True
    assert data_late["schedule_status"] == "late"
    assert data_late["days_overdue"] == 3
