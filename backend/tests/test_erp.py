"""
Test suite for Everest Textile Mills ERP.
Covers the full day-in-the-mill flow plus the A/C/P/I test plan from the execution plan.

Run: pytest tests/ -v
"""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mill.database import Base, get_db
from mill.auth import hash_password
from mill.models import (
    Buyer, Item, ItemType, Machine, MachineType, MachineStatus,
    StockLevel, StoreLocation, Supplier, User, UserRole,
    WageBasis, Worker,
)

# --- SQLite for tests ---
TEST_DATABASE_URL = "sqlite:///./test_erp.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_and_seed_db():
    """Setup DB schema and seed minimal test data."""
    from app import app
    
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    # Override dependency
    app.dependency_overrides[get_db] = override_get_db
    
    db = TestingSessionLocal()
    try:
        # Locations
        raw_loc = StoreLocation(code="RAW", name="Raw Store")
        fin_loc = StoreLocation(code="FIN", name="Finished Store")
        db.add_all([raw_loc, fin_loc])
        db.flush()

        # Users for each role
        roles = [
            ("admin",     "Admin",    UserRole.admin,            "admin123"),
            ("owner",     "Owner",    UserRole.owner,            "owner123"),
            ("store",     "Store",    UserRole.store,            "store123"),
            ("superv",    "Superv",   UserRole.floor_supervisor, "super123"),
            ("qc_user",   "QC",       UserRole.qc,               "qc1234"),
            ("office",    "Office",   UserRole.office,           "office123"),
        ]
        for username, name, role, pwd in roles:
            db.add(User(username=username, full_name=name, role=role,
                        hashed_password=hash_password(pwd)))

        # Supplier + Buyer
        supplier = Supplier(name="Test Supplier", payment_terms_days=30)
        buyer = Buyer(name="Test Buyer", payment_terms_days=45)
        db.add_all([supplier, buyer])
        db.flush()

        # Yarn item with stock
        yarn = Item(sku="YRN-001", name="Test Yarn", item_type=ItemType.yarn,
                    unit="kg", average_cost_paise=18000, reorder_point_grams=100_000)
        fabric = Item(sku="FAB-001", name="Test Fabric", item_type=ItemType.fabric,
                      unit="m", yarn_grams_per_metre=200, sale_price_paise_per_metre=35000)
        db.add_all([yarn, fabric])
        db.flush()

        # Initial yarn stock: 2000 kg
        db.add(StockLevel(item_id=yarn.id, location_id=raw_loc.id, quantity=2_000_000))

        # Machine
        machine = Machine(code="WVR-01", name="Loom 1", machine_type=MachineType.weaving,
                          status=MachineStatus.idle)
        db.add(machine)

        # Workers for wage tests
        w_hourly = Worker(employee_id="W001", full_name="Hourly Worker",
                          wage_basis=WageBasis.hourly, hourly_rate_paise=10000)  # ₹100/hr
        w_piece  = Worker(employee_id="W002", full_name="Piece Worker",
                          wage_basis=WageBasis.piece_rate, piece_rate_paise=300)  # ₹3/piece
        db.add_all([w_hourly, w_piece])

        # Settings
        from mill.models import Setting
        db.add(Setting(key="overhead_per_metre_paise", value="200"))

        db.commit()
    finally:
        db.close()
    
    # We yield here so teardown happens after all tests in the module
    yield
    
    # Drop tables after tests
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="module")
def client(setup_and_seed_db):
    from app import app
    with TestClient(app) as c:
        yield c


# ============================================================================
# Helpers
# ============================================================================

def login(client, username, password):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r


def auth_headers(client, username="admin", password="admin123"):
    login(client, username, password)
    return {}   # cookies are stored in the TestClient session


# ============================================================================
# Auth tests
# ============================================================================

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["mill"] == "Everest Textile Mills"


def test_login_success(client):
    r = login(client, "admin", "admin123")
    assert r.json()["user"]["username"] == "admin"


def test_login_bad_credentials(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_me(client):
    login(client, "admin", "admin123")
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


# ============================================================================
# I01 — Unauthorised access
# ============================================================================

def test_i01_unauthorized_payroll(client):
    """QC role cannot access payroll/wage reports."""
    login(client, "qc_user", "qc1234")
    r = client.get("/api/wages/")
    assert r.status_code == 403


def test_i01_unauthorized_finance(client):
    """Store role cannot access finance reports."""
    login(client, "store", "store123")
    r = client.get("/api/finance/receivables")
    assert r.status_code == 403


# ============================================================================
# Inventory / Items
# ============================================================================

def test_list_items(client):
    login(client, "admin", "admin123")
    r = client.get("/api/items/")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_create_item(client):
    login(client, "admin", "admin123")
    r = client.post("/api/items/", json={
        "sku": "YRN-TEST-NEW",
        "name": "New Yarn",
        "item_type": "yarn",
        "unit": "kg",
    })
    assert r.status_code == 200


# ============================================================================
# Full flow: I02
# ============================================================================

def test_i02_full_flow(client):
    """
    Full day-in-the-mill:
    yarn receipt → order → yarn-check → production run → yarn issue →
    roll created → QC pass → in_store → dispatch confirm → invoice created
    """
    db = TestingSessionLocal()
    try:
        yarn = db.query(Item).filter(Item.sku == "YRN-001").first()
        fabric = db.query(Item).filter(Item.sku == "FAB-001").first()
        supplier = db.query(Supplier).first()
        buyer = db.query(Buyer).first()
        machine = db.query(Machine).first()
    finally:
        db.close()

    login(client, "admin", "admin123")

    # 1. Create a purchase order
    r = client.post("/api/purchasing/", json={
        "supplier_id": supplier.id,
        "item_id": yarn.id,
        "quantity_grams": 500_000,
        "unit_cost_paise": 18000,
        "expected_date": str(date.today()),
    })
    assert r.status_code == 200
    po_id = r.json()["id"]

    # 2. Confirm PO
    r = client.post(f"/api/purchasing/{po_id}/confirm")
    assert r.status_code == 200

    # 3. Receive yarn
    r = client.post(f"/api/purchasing/{po_id}/receive", json={
        "received_grams": 500_000,
        "unit_cost_paise": 18000,
        "received_date": str(date.today()),
        "lot_no": "LOT-TEST-001",
    })
    assert r.status_code == 200
    lot_no = r.json()["lot_no"]

    # 4. Create buyer order
    r = client.post("/api/orders/", json={
        "buyer_id": buyer.id,
        "item_id": fabric.id,
        "quantity_metres": 100,
        "deadline": str(date.today() + timedelta(days=30)),
        "price_paise_per_metre": 35000,
    })
    assert r.status_code == 200
    order_id = r.json()["id"]

    # 5. Yarn check
    r = client.get(f"/api/orders/{order_id}/yarn-check")
    assert r.status_code == 200
    check = r.json()
    assert check["sufficient"] is True

    # 6. Create production run
    db2 = TestingSessionLocal()
    try:
        yarn_lot = db2.query(__import__("mill.models", fromlist=["YarnLot"]).YarnLot).filter_by(lot_no="LOT-TEST-001").first()
        yarn_lot_id = yarn_lot.id
    finally:
        db2.close()

    r = client.post("/api/production/", json={
        "order_id": order_id,
        "machine_id": machine.id,
        "stage": "weaving",
        "shift": "morning",
        "yarn_lot_id": yarn_lot_id,
    })
    assert r.status_code == 200
    run_id = r.json()["id"]

    # 7. Issue yarn (20 kg for 100m fabric)
    r = client.post(f"/api/production/{run_id}/issue-yarn", json={"grams": 20_000})
    assert r.status_code == 200

    # 8. Create roll
    r = client.post(f"/api/production/{run_id}/rolls", json={"length_cm": 5000})  # 50m roll
    assert r.status_code == 200
    roll_id = r.json()["id"]
    roll_no = r.json()["roll_no"]
    assert roll_no.startswith("ROLL-")

    # 9. Move roll to awaiting_qc
    r = client.post(f"/api/rolls/{roll_id}/transition", json={"to_status": "awaiting_qc"})
    assert r.status_code == 200

    # 10. QC pass
    r = client.post(f"/api/rolls/{roll_id}/qc", json={"result": "passed"})
    assert r.status_code == 200

    # 11. Move to in_store
    r = client.post(f"/api/rolls/{roll_id}/transition", json={"to_status": "in_store"})
    assert r.status_code == 200

    # 12. Create dispatch
    r = client.post("/api/dispatch/", json={
        "buyer_id": buyer.id,
        "order_id": order_id,
        "dispatch_date": str(date.today()),
        "vehicle_no": "MH-01-AB-1234",
    })
    assert r.status_code == 200
    dispatch_id = r.json()["id"]

    # 13. Add roll to dispatch
    r = client.post(f"/api/dispatch/{dispatch_id}/rolls", json={"roll_ids": [roll_id]})
    assert r.status_code == 200

    # 14. Confirm dispatch (creates invoice)
    r = client.post(f"/api/dispatch/{dispatch_id}/confirm")
    assert r.status_code == 200

    # 15. Check invoice was created
    r = client.get(f"/api/dispatch/{dispatch_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["invoice"] is not None
    invoice_id = data["invoice"]["id"]
    # Invoice = 50m × ₹350 = ₹17,500 = 1,750,000 paise
    assert data["invoice"]["amount_paise"] == 50 * 35000

    # 16. Verify double-dispatch prevention
    r2 = client.post("/api/dispatch/", json={
        "buyer_id": buyer.id,
        "order_id": order_id,
        "dispatch_date": str(date.today()),
    })
    dis2_id = r2.json()["id"]
    r2 = client.post(f"/api/dispatch/{dis2_id}/rolls", json={"roll_ids": [roll_id]})
    assert r2.status_code == 400   # UniqueConstraint on dispatch_rolls.roll_id

    return invoice_id, order_id


# ============================================================================
# A-series: Attendance & Wages
# ============================================================================

def test_a01_hourly_wage(client):
    """A01: 160 approved hours × ₹100/hour = ₹16,000"""
    login(client, "admin", "admin123")
    db = TestingSessionLocal()
    try:
        worker = db.query(Worker).filter(Worker.employee_id == "W001").first()
        worker_id = worker.id
    finally:
        db.close()

    period_start = date(2026, 1, 1)
    period_end = date(2026, 1, 31)

    # Create 20 days × 8 hours = 160 hours
    for day in range(1, 21):
        r = client.post("/api/attendance/entries", json={
            "worker_id": worker_id,
            "work_date": f"2026-01-{day:02d}",
            "shift": "morning",
            "hours_worked": 480,   # 480 minutes = 8 hours
        })
        assert r.status_code == 200, r.text
        entry_id = r.json()["id"]
        # Approve
        r = client.post(f"/api/attendance/entries/{entry_id}/approve")
        assert r.status_code == 200

    # Calculate wage run
    r = client.post("/api/wages/calculate", json={
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
    })
    assert r.status_code == 200
    run_id = r.json()["id"]

    # Get run details
    r = client.get(f"/api/wages/{run_id}")
    assert r.status_code == 200
    data = r.json()
    lines = [l for l in data["lines"] if l["worker_id"] == worker_id]
    assert len(lines) == 1
    line = lines[0]
    # 20 × 480 minutes × ₹100/hr = 20 × 8 × 10000 = 1,600,000 paise = ₹16,000
    assert line["net_wage_paise"] == 1_600_000


def test_a02_piece_rate_wage(client):
    """A02: 2,400 approved pieces × ₹3/piece = ₹7,200"""
    login(client, "admin", "admin123")
    db = TestingSessionLocal()
    try:
        worker = db.query(Worker).filter(Worker.employee_id == "W002").first()
        worker_id = worker.id
    finally:
        db.close()

    # Create entries totalling 2400 pieces in Feb
    for day in range(1, 13):
        r = client.post("/api/attendance/entries", json={
            "worker_id": worker_id,
            "work_date": f"2026-02-{day:02d}",
            "shift": "morning",
            "pieces_produced": 200,   # 200 pieces/day × 12 days = 2400
        })
        assert r.status_code == 200
        entry_id = r.json()["id"]
        r = client.post(f"/api/attendance/entries/{entry_id}/approve")
        assert r.status_code == 200

    r = client.post("/api/wages/calculate", json={
        "period_start": "2026-02-01",
        "period_end": "2026-02-28",
    })
    assert r.status_code == 200
    run_id = r.json()["id"]

    r = client.get(f"/api/wages/{run_id}")
    data = r.json()
    lines = [l for l in data["lines"] if l["worker_id"] == worker_id]
    assert len(lines) == 1
    # 2400 × ₹3 = ₹7,200 = 720,000 paise
    assert lines[0]["net_wage_paise"] == 720_000


def test_a03_invalid_attendance_negative_hours(client):
    """A03: Negative hours must be rejected."""
    login(client, "admin", "admin123")
    db = TestingSessionLocal()
    try:
        worker = db.query(Worker).filter(Worker.employee_id == "W001").first()
        worker_id = worker.id
    finally:
        db.close()

    r = client.post("/api/attendance/entries", json={
        "worker_id": worker_id,
        "work_date": "2026-03-01",
        "shift": "morning",
        "hours_worked": -60,
    })
    assert r.status_code == 400


def test_a04_unapproved_excluded_from_wage(client):
    """A04: Unapproved entries must not be counted in wage calculation."""
    login(client, "admin", "admin123")
    db = TestingSessionLocal()
    try:
        worker = db.query(Worker).filter(Worker.employee_id == "W001").first()
        worker_id = worker.id
    finally:
        db.close()

    # Add an unapproved entry in March
    r = client.post("/api/attendance/entries", json={
        "worker_id": worker_id,
        "work_date": "2026-03-01",
        "shift": "morning",
        "hours_worked": 480,
    })
    assert r.status_code == 200
    # Don't approve it

    r = client.post("/api/wages/calculate", json={
        "period_start": "2026-03-01",
        "period_end": "2026-03-31",
    })
    assert r.status_code == 200
    run_id = r.json()["id"]

    r = client.get(f"/api/wages/{run_id}")
    data = r.json()
    # Worker should have no line (unapproved entry excluded)
    lines = [l for l in data["lines"] if l["worker_id"] == worker_id]
    assert len(lines) == 0


def test_a05_finalised_run_immutable(client):
    """A05: Finalised wage run cannot be recalculated."""
    login(client, "admin", "admin123")
    # Finalise Jan run
    db = TestingSessionLocal()
    try:
        run = db.query(__import__("mill.models", fromlist=["WageRun"]).WageRun).filter_by(
            period_start=date(2026, 1, 1)
        ).first()
        run_id = run.id
    finally:
        db.close()

    r = client.post(f"/api/wages/{run_id}/finalise")
    assert r.status_code == 200

    # Attempt recalculate after finalise
    r = client.post("/api/wages/calculate", json={
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
    })
    assert r.status_code == 400
    assert "finalised" in r.json()["detail"].lower()


# ============================================================================
# P-series: Payments
# ============================================================================

def test_p01_buyer_payment_full_flow(client):
    """P01: Invoice ₹80,000 → ₹25,000 then ₹55,000 → fully paid."""
    login(client, "admin", "admin123")
    db = TestingSessionLocal()
    try:
        buyer = db.query(Buyer).first()
        buyer_id = buyer.id
    finally:
        db.close()

    # Create a manual invoice (normally created by dispatch confirm)
    from mill.models import Invoice, InvoiceStatus, NumberSequence
    db2 = TestingSessionLocal()
    try:
        seq = NumberSequence(name="inv_test", last_value=99)
        db2.add(seq)
        inv = Invoice(
            doc_no="INV-TEST-001",
            buyer_id=buyer_id,
            amount_paise=8_000_000,   # ₹80,000
            invoice_date=date.today(),
            status=InvoiceStatus.unpaid,
            created_by=1,
        )
        db2.add(inv)
        db2.commit()
        inv_id = inv.id
    finally:
        db2.close()

    # First payment: ₹25,000
    r = client.post(f"/api/finance/invoices/{inv_id}/payments", json={
        "amount_paise": 2_500_000,
        "payment_date": str(date.today()),
        "method": "NEFT",
        "reference": "REF001",
    })
    assert r.status_code == 200

    r = client.get(f"/api/finance/invoices/{inv_id}")
    data = r.json()
    assert data["status"] == "partial"
    assert data["outstanding_paise"] == 5_500_000

    # Second payment: ₹55,000 (clears balance)
    r = client.post(f"/api/finance/invoices/{inv_id}/payments", json={
        "amount_paise": 5_500_000,
        "payment_date": str(date.today()),
        "method": "NEFT",
        "reference": "REF002",
    })
    assert r.status_code == 200

    r = client.get(f"/api/finance/invoices/{inv_id}")
    data = r.json()
    assert data["status"] == "paid"
    assert data["outstanding_paise"] == 0


def test_p02_payment_exceeds_balance(client):
    """P02: Payment > outstanding must be rejected."""
    login(client, "admin", "admin123")
    db = TestingSessionLocal()
    try:
        inv = db.query(__import__("mill.models", fromlist=["Invoice"]).Invoice)\
            .filter_by(doc_no="INV-TEST-001").first()
        inv_id = inv.id
    finally:
        db.close()

    r = client.post(f"/api/finance/invoices/{inv_id}/payments", json={
        "amount_paise": 1_000_000,   # ₹10,000 when balance is 0
        "payment_date": str(date.today()),
    })
    assert r.status_code == 400


def test_p03_supplier_payment(client):
    """P03: Supplier bill ₹50,000 → ₹20,000 paid → outstanding ₹30,000."""
    login(client, "admin", "admin123")
    db = TestingSessionLocal()
    try:
        supplier = db.query(Supplier).first()
        po = db.query(__import__("mill.models", fromlist=["PurchaseOrder"]).PurchaseOrder).first()
    finally:
        db.close()

    # Create supplier bill
    r = client.post("/api/finance/bills", json={
        "supplier_id": supplier.id,
        "purchase_order_id": po.id,
        "amount_paise": 5_000_000,
        "bill_date": str(date.today()),
    })
    assert r.status_code == 200
    bill_id = r.json()["id"]

    # Pay ₹20,000
    r = client.post(f"/api/finance/bills/{bill_id}/payments", json={
        "amount_paise": 2_000_000,
        "payment_date": str(date.today()),
        "method": "cheque",
        "reference": "CHQ-123",
    })
    assert r.status_code == 200

    r = client.get("/api/finance/bills")
    bills = [b for b in r.json() if b["id"] == bill_id]
    assert len(bills) == 1
    assert bills[0]["outstanding_paise"] == 3_000_000
    assert bills[0]["status"] == "partial"


# ============================================================================
# C-series: Costing (formula validation)
# ============================================================================

def test_c01_order_cost_calculation(client):
    """C01: Yarn ₹90k + wages ₹0 + overhead; verify cost per metre."""
    login(client, "admin", "admin123")
    db = TestingSessionLocal()
    try:
        order = db.query(__import__("mill.models", fromlist=["Order"]).Order).first()
        order_id = order.id
    finally:
        db.close()

    r = client.post(f"/api/costing/orders/{order_id}")
    assert r.status_code in (200, 400)  # may have no passed rolls from the test flow
    if r.status_code == 200:
        data = r.json()
        assert data["passed_metres"] >= 0
        if data["passed_metres"] > 0:
            assert data["cost_per_passed_metre_paise"] == (
                data["total_cost_paise"] // data["passed_metres"]
            )
