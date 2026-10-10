"""Unit/integration tests for auth, items, purchasing, orders, dashboard."""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import login


# ─── Health ──────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_checks_database(self, client: TestClient):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "app": "Khadira"}

    def test_health_reports_database_failure(self):
        from mill.main import create_app
        from sqlalchemy.exc import OperationalError

        class BrokenSession:
            def execute(self, statement):
                raise OperationalError(statement, {}, OSError("database unavailable"))

            def close(self):
                pass

        app = create_app(session_factory=lambda: BrokenSession())
        with TestClient(app) as test_client:
            r = test_client.get("/api/health")
        assert r.status_code == 503
        assert r.json() == {"detail": "Database unavailable"}


# ─── Auth ────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_login_and_me(self, client: TestClient):
        login(client, "admin")
        r = client.get("/api/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert "reports.read" in data["permissions"]

    def test_login_wrong_password(self, client: TestClient):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401

    def test_role_guard(self, client: TestClient):
        # qc role cannot access purchasing
        login(client, "qc")
        r = client.post("/api/purchasing", json={
            "supplier_id": 1, "order_date": "2026-01-01",
            "lines": [{"item_id": 1, "qty_kg": 10, "rate_per_kg_paise": 100}],
        })
        assert r.status_code == 403
        login(client, "admin")  # restore


# ─── Items ───────────────────────────────────────────────────────────────────

class TestItems:
    def test_create_yarn_item(self, client: TestClient):
        login(client)
        r = client.post("/api/items", json={
            "sku": "TEST-YRN-A", "name": "Test Yarn A", "item_type": "yarn",
            "count_denier": "30s", "reorder_point_kg": 200,
        })
        assert r.status_code == 201
        assert r.json()["item_type"] == "yarn"

    def test_create_fabric_item(self, client: TestClient):
        r = client.post("/api/items", json={
            "sku": "TEST-FAB-A", "name": "Test Fabric A", "item_type": "fabric",
            "gsm": 140, "width_cm": 120, "yarn_kg_per_meter": 0.22,
        })
        assert r.status_code == 201
        assert r.json()["yarn_kg_per_meter"] == 0.22

    def test_fabric_requires_yarn_kg_per_meter(self, client: TestClient):
        r = client.post("/api/items", json={
            "sku": "TEST-FAB-BAD", "name": "Bad Fabric", "item_type": "fabric",
        })
        assert r.status_code == 400

    def test_duplicate_sku_rejected(self, client: TestClient):
        r = client.post("/api/items", json={
            "sku": "TEST-YRN-A", "name": "Duplicate", "item_type": "yarn",
        })
        assert r.status_code == 400

    def test_list_items(self, client: TestClient):
        r = client.get("/api/items")
        assert r.status_code == 200
        assert "items" in r.json()
        assert r.json()["total"] >= 2

    def test_list_filter_by_type(self, client: TestClient):
        r = client.get("/api/items?item_type=yarn")
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["item_type"] == "yarn"


# ─── Purchasing ──────────────────────────────────────────────────────────────

class TestPurchasing:
    @pytest.fixture(autouse=True)
    def _login(self, client):
        login(client, "admin")

    def _make_yarn(self, client, sku):
        r = client.post("/api/items", json={
            "sku": sku, "name": f"Yarn {sku}", "item_type": "yarn",
        })
        return r.json()["id"]

    def _make_supplier(self, client, name):
        r = client.post("/api/partners/suppliers", json={"name": name})
        return r.json()["id"]

    def test_create_and_confirm_po(self, client: TestClient):
        yarn_id = self._make_yarn(client, "PO-TEST-Y1")
        sup_id  = self._make_supplier(client, "PO Test Supplier")
        r = client.post("/api/purchasing", json={
            "supplier_id": sup_id, "order_date": "2026-09-01",
            "lines": [{"item_id": yarn_id, "qty_kg": 300, "rate_per_kg_paise": 25000_00}],
        })
        assert r.status_code == 201
        po_id = r.json()["id"]

        r = client.post(f"/api/purchasing/{po_id}/confirm")
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_full_yarn_receipt_flow(self, client: TestClient):
        yarn_id = self._make_yarn(client, "PO-TEST-Y2")
        sup_id  = self._make_supplier(client, "Receipt Test Supplier")
        r = client.post("/api/purchasing", json={
            "supplier_id": sup_id, "order_date": "2026-09-05",
            "lines": [{"item_id": yarn_id, "qty_kg": 100, "rate_per_kg_paise": 30000_00}],
        })
        po_id      = r.json()["id"]
        po_line_id = r.json()["lines"][0]["id"]
        client.post(f"/api/purchasing/{po_id}/confirm")

        r = client.post(f"/api/purchasing/{po_id}/receive", json={
            "po_line_id": po_line_id, "received_date": "2026-09-07",
            "qty_kg": 100, "lot_number": "LOT-RC-001", "location_code": "RAW",
        })
        assert r.status_code == 201

    def test_no_negative_stock(self, client: TestClient):
        """Dispatching more fabric than in stock should fail."""
        # Create a fabric roll in store with only 1000 cm
        yarn_id = self._make_yarn(client, "NEG-TEST-Y1")
        r = client.post("/api/items", json={
            "sku": "NEG-FAB-01", "name": "Neg Test Fab", "item_type": "fabric",
            "gsm": 120, "width_cm": 100, "yarn_kg_per_meter": 0.15,
        })
        fabric_id = r.json()["id"]
        r = client.post("/api/machines", json={
            "code": "NEG-M1", "name": "Neg Machine", "machine_type": "weaving",
        })
        machine_id = r.json()["id"]
        r = client.post("/api/production", json={
            "machine_id": machine_id, "item_id": fabric_id,
        })
        run_id = r.json()["id"]
        # Advance to final stage
        client.post(f"/api/production/{run_id}/advance", json={})
        client.post(f"/api/production/{run_id}/advance", json={})
        # Create roll (1000 cm)
        r = client.post("/api/rolls", json={"run_id": run_id, "length_cm": 1000})
        roll_id = r.json()["id"]
        client.post(f"/api/rolls/{roll_id}/inspect", json={"verdict": "passed"})
        client.post(f"/api/rolls/{roll_id}/store")
        # Try to dispatch twice — second should fail
        from datetime import date
        client.post("/api/dispatch", json={"roll_ids": [roll_id], "dispatch_date": str(date.today())})
        r = client.post("/api/dispatch", json={"roll_ids": [roll_id], "dispatch_date": str(date.today())})
        assert r.status_code == 400  # already dispatched

    def test_yarn_only_po_guard(self, client: TestClient):
        r = client.post("/api/items", json={
            "sku": "GUARD-FAB", "name": "Guard Fabric", "item_type": "fabric",
            "gsm": 100, "width_cm": 100, "yarn_kg_per_meter": 0.1,
        })
        fabric_id = r.json()["id"]
        sup_id = self._make_supplier(client, "Guard Supplier")
        r = client.post("/api/purchasing", json={
            "supplier_id": sup_id, "order_date": "2026-09-10",
            "lines": [{"item_id": fabric_id, "qty_kg": 10, "rate_per_kg_paise": 1000}],
        })
        assert r.status_code == 400


# ─── Orders ──────────────────────────────────────────────────────────────────

class TestOrders:
    @pytest.fixture(autouse=True)
    def _login(self, client):
        login(client, "admin")

    def _make_buyer(self, client, name):
        r = client.post("/api/partners/buyers", json={"name": name})
        return r.json()["id"]

    def _make_fabric(self, client, sku):
        r = client.post("/api/items", json={
            "sku": sku, "name": f"Fabric {sku}", "item_type": "fabric",
            "gsm": 150, "width_cm": 120, "yarn_kg_per_meter": 0.20,
        })
        return r.json()["id"]

    def _stock_up(self, client, yarn_sku):
        """Receive some yarn to satisfy sufficiency check."""
        r = client.post("/api/items", json={
            "sku": yarn_sku, "name": f"Yarn {yarn_sku}", "item_type": "yarn",
        })
        yarn_id = r.json()["id"]
        r = client.post("/api/partners/suppliers", json={"name": f"Sup {yarn_sku}"})
        sup_id = r.json()["id"]
        r = client.post("/api/purchasing", json={
            "supplier_id": sup_id, "order_date": "2026-01-01",
            "lines": [{"item_id": yarn_id, "qty_kg": 5000, "rate_per_kg_paise": 2000_00}],
        })
        po_id = r.json()["id"]
        line_id = r.json()["lines"][0]["id"]
        client.post(f"/api/purchasing/{po_id}/confirm")
        client.post(f"/api/purchasing/{po_id}/receive", json={
            "po_line_id": line_id, "received_date": "2026-01-02",
            "qty_kg": 5000, "lot_number": f"LOT-{yarn_sku}", "location_code": "RAW",
        })

    def test_create_and_confirm_order(self, client: TestClient):
        self._stock_up(client, "ORD-YARN-1")
        buyer_id  = self._make_buyer(client, "Order Buyer 1")
        fabric_id = self._make_fabric(client, "ORD-FAB-1")
        r = client.post("/api/orders", json={
            "buyer_id": buyer_id, "order_date": "2026-10-01",
            "lines": [{"item_id": fabric_id, "qty_meters": 50, "rate_per_meter_paise": 8000_00}],
        })
        assert r.status_code == 201
        order_id = r.json()["id"]
        r = client.post(f"/api/orders/{order_id}/confirm")
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_fabric_only_guard(self, client: TestClient):
        buyer_id = self._make_buyer(client, "Fab Guard Buyer")
        r = client.post("/api/items", json={
            "sku": "GUARD-YARN-ORD", "name": "Guard Yarn", "item_type": "yarn",
        })
        yarn_id = r.json()["id"]
        r = client.post("/api/orders", json={
            "buyer_id": buyer_id, "order_date": "2026-10-01",
            "lines": [{"item_id": yarn_id, "qty_meters": 10, "rate_per_meter_paise": 500_00}],
        })
        assert r.status_code == 400

    def test_cancel_confirmed_order(self, client: TestClient):
        self._stock_up(client, "ORD-YARN-2")
        buyer_id  = self._make_buyer(client, "Cancel Buyer")
        fabric_id = self._make_fabric(client, "ORD-FAB-CANCEL")
        r = client.post("/api/orders", json={
            "buyer_id": buyer_id, "order_date": "2026-10-02",
            "lines": [{"item_id": fabric_id, "qty_meters": 20, "rate_per_meter_paise": 7000_00}],
        })
        order_id = r.json()["id"]
        client.post(f"/api/orders/{order_id}/confirm")
        r = client.post(f"/api/orders/{order_id}/cancel")
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    def test_cannot_edit_confirmed_order(self, client: TestClient):
        """Confirming an already-confirmed order should fail."""
        self._stock_up(client, "ORD-YARN-3")
        buyer_id  = self._make_buyer(client, "Double Confirm Buyer")
        fabric_id = self._make_fabric(client, "ORD-FAB-DC")
        r = client.post("/api/orders", json={
            "buyer_id": buyer_id, "order_date": "2026-10-03",
            "lines": [{"item_id": fabric_id, "qty_meters": 30, "rate_per_meter_paise": 8500_00}],
        })
        order_id = r.json()["id"]
        client.post(f"/api/orders/{order_id}/confirm")
        r = client.post(f"/api/orders/{order_id}/confirm")
        assert r.status_code == 400


# ─── Yarn sufficiency ─────────────────────────────────────────────────────────

class TestYarnSufficiency:
    @pytest.fixture(autouse=True)
    def _login(self, client):
        login(client, "admin")

    def test_enough_yarn(self, client: TestClient):
        # stock up 1000 kg of yarn
        r = client.post("/api/items", json={
            "sku": "SUFF-YARN-OK", "name": "Suff Yarn OK", "item_type": "yarn",
        })
        yarn_id = r.json()["id"]
        r = client.post("/api/partners/suppliers", json={"name": "Suff Sup OK"})
        sup_id = r.json()["id"]
        r = client.post("/api/purchasing", json={
            "supplier_id": sup_id, "order_date": "2026-01-01",
            "lines": [{"item_id": yarn_id, "qty_kg": 1000, "rate_per_kg_paise": 2000_00}],
        })
        po_id = r.json()["id"]
        line_id = r.json()["lines"][0]["id"]
        client.post(f"/api/purchasing/{po_id}/confirm")
        client.post(f"/api/purchasing/{po_id}/receive", json={
            "po_line_id": line_id, "received_date": "2026-01-02",
            "qty_kg": 1000, "lot_number": "SUFF-OK", "location_code": "RAW",
        })
        r = client.post("/api/items", json={
            "sku": "SUFF-FAB-OK", "name": "Suff Fab OK", "item_type": "fabric",
            "gsm": 130, "width_cm": 110, "yarn_kg_per_meter": 0.1,
        })
        fabric_id = r.json()["id"]
        r = client.post("/api/partners/buyers", json={"name": "Suff Buyer OK"})
        buyer_id = r.json()["id"]
        r = client.post("/api/orders", json={
            "buyer_id": buyer_id, "order_date": "2026-10-01",
            "lines": [{"item_id": fabric_id, "qty_meters": 100, "rate_per_meter_paise": 5000_00}],
        })
        order_id = r.json()["id"]
        r = client.post(f"/api/orders/{order_id}/confirm")
        assert r.status_code == 200

    def test_short_yarn(self, client: TestClient):
        """Order requiring more yarn than available should be rejected."""
        r = client.post("/api/items", json={
            "sku": "SUFF-FAB-SHORT", "name": "Suff Fab Short", "item_type": "fabric",
            "gsm": 300, "width_cm": 200, "yarn_kg_per_meter": 999.0,  # huge requirement
        })
        fabric_id = r.json()["id"]
        r = client.post("/api/partners/buyers", json={"name": "Suff Buyer Short"})
        buyer_id = r.json()["id"]
        r = client.post("/api/orders", json={
            "buyer_id": buyer_id, "order_date": "2026-10-01",
            "lines": [{"item_id": fabric_id, "qty_meters": 10000, "rate_per_meter_paise": 5000_00}],
        })
        order_id = r.json()["id"]
        r = client.post(f"/api/orders/{order_id}/confirm")
        assert r.status_code == 400
        assert "yarn" in r.json()["detail"].lower()


# ─── Dashboard ────────────────────────────────────────────────────────────────

class TestDashboard:
    @pytest.fixture(autouse=True)
    def _login(self, client):
        login(client, "admin")

    def test_dashboard_returns(self, client: TestClient):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "order_counts" in data
        assert "low_stock_alerts" in data

    def test_low_stock_alert(self, client: TestClient):
        r = client.post("/api/items", json={
            "sku": "LOW-YARN-X", "name": "Low Stock Yarn",
            "item_type": "yarn", "reorder_point_kg": 999999,
        })
        assert r.status_code == 201
        r = client.get("/api/dashboard")
        alerts = r.json()["low_stock_alerts"]
        skus = [a["sku"] for a in alerts]
        assert "LOW-YARN-X" in skus
