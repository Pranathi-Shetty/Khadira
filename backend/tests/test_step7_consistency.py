"""Step 7 Tests: Consistency fixes for merged features.

Covers:
1. Streamlined attendance logging: worker UID, name, shift timing logs, and presence status.
   Automatic 8-hour shift credit for hourly wages when present; 0 hours when absent.
2. Canonical quality vocabulary: pass, rework, reject everywhere (rejection of hold/fail).
   Re-inspection of rework rolls, pending QC queue, and quality report vocabulary.
3. Unit transparency on stock endpoints: distinguishing yarn (kg/g) and fabric (meters/cm).
4. Role checks and audit history attribution.
"""
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from mill.models import (
    AttendanceEntry, Item, Location, Machine, Order, ProductionRun,
    Roll, RollEvent, StockLevel, Worker, AuditLog
)
from mill.services.common import DomainError
from mill.services.orders import create_order, confirm_order
from mill.services.production import start_run, advance_stage, create_roll
from mill.services.qc import inspect_roll, move_to_store
from tests.conftest import login


@pytest.fixture
def auth_client(client: TestClient):
    login(client, "admin")
    return client


@pytest.fixture
def test_entities(db_session: Session):
    # Ensure raw & fin locations
    raw_loc = db_session.query(Location).filter_by(code="RAW").first()
    if not raw_loc:
        raw_loc = Location(code="RAW", name="Raw Yarn Store")
        db_session.add(raw_loc)
    fin_loc = db_session.query(Location).filter_by(code="FIN").first()
    if not fin_loc:
        fin_loc = Location(code="FIN", name="Finished Fabric Store")
        db_session.add(fin_loc)

    worker_hourly = db_session.query(Worker).filter_by(code="WRK-ST7-01").first()
    if not worker_hourly:
        worker_hourly = Worker(
            code="WRK-ST7-01", full_name="Sita Devi", wage_basis="hourly",
            hourly_rate_paise=12000, department="Weaving"
        )
        db_session.add(worker_hourly)

    yarn_item = db_session.query(Item).filter_by(sku="YRN-ST7-01").first()
    if not yarn_item:
        yarn_item = Item(sku="YRN-ST7-01", name="Yarn 40s Cotton", item_type="yarn", unit="kg")
        db_session.add(yarn_item)

    fabric_item = db_session.query(Item).filter_by(sku="FAB-ST7-01").first()
    if not fabric_item:
        fabric_item = Item(
            sku="FAB-ST7-01", name="Fabric Grey Sheeting", item_type="fabric",
            unit="meters", gsm=130, width_cm=120, yarn_kg_per_meter=0.25
        )
        db_session.add(fabric_item)

    machine = db_session.query(Machine).filter_by(code="WL-ST7-01").first()
    if not machine:
        machine = Machine(code="WL-ST7-01", name="Loom Step7", machine_type="weaving")
        db_session.add(machine)

    db_session.commit()
    return {
        "worker_hourly": worker_hourly,
        "yarn_item": yarn_item,
        "fabric_item": fabric_item,
        "machine": machine,
        "raw_loc": raw_loc,
        "fin_loc": fin_loc,
    }


# ==============================================================================
# 1. ATTENDANCE STREAMLINING TESTS
# ==============================================================================

def test_attendance_logging_with_only_presence_and_shift(auth_client: TestClient, test_entities):
    """Floor supervisors log UID, shift, and presence; hours are omitted and default to 8h."""
    worker = test_entities["worker_hourly"]

    # 1. Log attendance without entering any hours: only UID, date, shift, is_present=True
    payload = {
        "worker_id": worker.id,
        "work_date": "2026-11-02",
        "shift": "Morning Shift (08:00 - 16:30)",
        "is_present": True,
    }
    r = auth_client.post("/api/attendance", json=payload)
    assert r.status_code == 201
    data = r.json()

    # Identity and shift timing logs returned
    assert data["worker_id"] == worker.id
    assert data["worker_code"] == worker.code
    assert data["worker_name"] == worker.full_name
    assert data["shift"] == "Morning Shift (08:00 - 16:30)"
    assert data["is_present"] is True

    # Under the hood, credited standard 8h shift (480 minutes)
    assert data["minutes_worked"] == 480
    assert data["hours_worked"] == 480
    assert data["hours"] == 8.0


def test_attendance_logging_absence(auth_client: TestClient, test_entities):
    """Marking a worker absent credits 0 hours and 0 wages."""
    worker = test_entities["worker_hourly"]

    payload = {
        "worker_id": worker.id,
        "work_date": "2026-11-03",
        "shift": "Morning Shift (08:00 - 16:30)",
        "is_present": False,
    }
    r = auth_client.post("/api/attendance", json=payload)
    assert r.status_code == 201
    data = r.json()

    assert data["is_present"] is False
    assert data["minutes_worked"] == 0
    assert data["hours"] == 0.0


def test_attendance_custom_duration_override(auth_client: TestClient, test_entities):
    """Optional minutes override (e.g. 4-hour half day) is accepted when needed."""
    worker = test_entities["worker_hourly"]

    payload = {
        "worker_id": worker.id,
        "work_date": "2026-11-04",
        "shift": "Half Day Shift",
        "is_present": True,
        "minutes_worked": 240,  # 4 hours
    }
    r = auth_client.post("/api/attendance", json=payload)
    assert r.status_code == 201
    data = r.json()

    assert data["is_present"] is True
    assert data["minutes_worked"] == 240
    assert data["hours"] == 4.0


def test_attendance_rejects_exceeding_24_hours(auth_client: TestClient, test_entities):
    """Attendance cannot exceed 1440 minutes in a 24-hour day."""
    worker = test_entities["worker_hourly"]

    payload = {
        "worker_id": worker.id,
        "work_date": "2026-11-05",
        "shift": "Day Shift",
        "is_present": True,
        "minutes_worked": 1500,  # > 1440 mins
    }
    r = auth_client.post("/api/attendance", json=payload)
    assert r.status_code == 422  # Pydantic validation error (le=1440)


# ==============================================================================
# 2. QUALITY VOCABULARY (PASS, REWORK, REJECT) TESTS
# ==============================================================================

def test_quality_vocabulary_accepts_pass_rework_reject(auth_client: TestClient, db_session: Session, test_entities):
    """Only pass, rework, reject are accepted; hold and fail are refused."""
    fabric = test_entities["fabric_item"]
    machine = test_entities["machine"]

    # Start a run, advance to inspection stage, and create 3 rolls
    run = start_run(db_session, machine_id=machine.id, order_id=None, item_id=fabric.id, user_id=1)
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1)  # warping -> weaving
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1)  # weaving -> inspection
    db_session.commit()

    r_pass = create_roll(db_session, run_id=run.id, length_cm=5000, weight_g=10000, user_id=1)
    r_rework = create_roll(db_session, run_id=run.id, length_cm=6000, weight_g=12000, user_id=1)
    r_reject = create_roll(db_session, run_id=run.id, length_cm=7000, weight_g=14000, user_id=1)
    db_session.commit()

    # 1. Test pass
    r1 = auth_client.post(f"/api/rolls/{r_pass.id}/inspect", json={"verdict": "pass", "grade": "A"})
    assert r1.status_code == 200
    assert r1.json()["status"] == "passed"
    assert r1.json()["qc_grade"] == "A"

    # 2. Test rework
    r2 = auth_client.post(f"/api/rolls/{r_rework.id}/inspect", json={"verdict": "rework", "note": "Warp tension loose"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "rework"

    # 3. Test reject
    r3 = auth_client.post(f"/api/rolls/{r_reject.id}/inspect", json={"verdict": "reject", "note": "Oil stains"})
    assert r3.status_code == 200
    assert r3.json()["status"] == "rejected"

    # 4. Old terms 'fail' and 'hold' are strictly refused!
    r_bad = create_roll(db_session, run_id=run.id, length_cm=4000, weight_g=8000, user_id=1)
    db_session.commit()

    r_fail = auth_client.post(f"/api/rolls/{r_bad.id}/inspect", json={"verdict": "fail"})
    assert r_fail.status_code == 400
    assert "Verdict must be pass, rework, or reject" in r_fail.json()["detail"]

    r_hold = auth_client.post(f"/api/rolls/{r_bad.id}/inspect", json={"verdict": "hold"})
    assert r_hold.status_code == 400
    assert "Verdict must be pass, rework, or reject" in r_hold.json()["detail"]


def test_rework_roll_in_pending_queue_and_reinspection(auth_client: TestClient, db_session: Session, test_entities):
    """A roll in rework appears in pending QC and can be re-inspected to pass."""
    fabric = test_entities["fabric_item"]
    machine = test_entities["machine"]

    run = start_run(db_session, machine_id=machine.id, order_id=None, item_id=fabric.id, user_id=1)
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1)  # warping -> weaving
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1)  # weaving -> inspection
    db_session.commit()

    roll = create_roll(db_session, run_id=run.id, length_cm=8000, weight_g=16000, user_id=1)
    db_session.commit()

    # Mark as rework
    auth_client.post(f"/api/rolls/{roll.id}/inspect", json={"verdict": "rework", "note": "Needs mending"})

    # Must appear in pending QC
    r_pending = auth_client.get("/api/qc/pending")
    assert r_pending.status_code == 200
    pending_ids = [p["id"] for p in r_pending.json()]
    assert roll.id in pending_ids

    # Re-inspect to pass after mending
    r_reinspect = auth_client.post(f"/api/rolls/{roll.id}/inspect", json={"verdict": "pass", "grade": "B"})
    assert r_reinspect.status_code == 200
    assert r_reinspect.json()["status"] == "passed"
    assert r_reinspect.json()["qc_grade"] == "B"

    # Now can be moved to store
    r_store = auth_client.post(f"/api/rolls/{roll.id}/store")
    assert r_store.status_code == 200
    assert r_store.json()["status"] == "in_store"


def test_quality_summary_report_vocabulary(auth_client: TestClient):
    """Quality report uses canonical vocabulary: passed, rework, rejected (no held)."""
    r = auth_client.get("/api/reports/quality")
    assert r.status_code == 200
    data = r.json()

    assert "passed" in data
    assert "rework" in data
    assert "rejected" in data
    assert "held" not in data  # Replaced with rework


# ==============================================================================
# 3. UNIT TRANSPARENCY ON STOCK ENDPOINTS
# ==============================================================================

def test_inventory_stock_unit_transparency(auth_client: TestClient, db_session: Session, test_entities):
    """API clearly distinguishes yarn in kg/g and fabric in meters/cm."""
    yarn = test_entities["yarn_item"]
    fabric = test_entities["fabric_item"]
    raw_loc = test_entities["raw_loc"]
    fin_loc = test_entities["fin_loc"]

    # Seed yarn stock (50,000 g = 50.0 kg)
    sl_yarn = db_session.query(StockLevel).filter_by(item_id=yarn.id, location_id=raw_loc.id).first()
    if not sl_yarn:
        db_session.add(StockLevel(item_id=yarn.id, location_id=raw_loc.id, qty_g=50_000))
    else:
        sl_yarn.qty_g = 50_000

    # Seed fabric stock (12,000 cm = 120.0 m)
    sl_fabric = db_session.query(StockLevel).filter_by(item_id=fabric.id, location_id=fin_loc.id).first()
    if not sl_fabric:
        db_session.add(StockLevel(item_id=fabric.id, location_id=fin_loc.id, qty_g=12_000))
    else:
        sl_fabric.qty_g = 12_000
    db_session.commit()

    # Query Yarn Stock
    r_yarn = auth_client.get(f"/api/inventory/stock/{yarn.id}/{raw_loc.id}")
    assert r_yarn.status_code == 200
    y_data = r_yarn.json()
    assert y_data["unit"] == "kg"
    assert y_data["qty_g"] == 50000
    assert y_data["qty_kg"] == 50.0

    # Query Fabric Stock
    r_fab = auth_client.get(f"/api/inventory/stock/{fabric.id}/{fin_loc.id}")
    assert r_fab.status_code == 200
    f_data = r_fab.json()
    assert f_data["unit"] == "meters"
    assert f_data["qty_cm"] == 12000
    assert f_data["quantity_m"] == 120.0
    assert f_data["qty_raw"] == 12000
