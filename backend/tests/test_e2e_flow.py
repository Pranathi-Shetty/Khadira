"""End-to-end lifecycle test: PO → receipt → order → production → QC → dispatch."""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import login


def test_full_textile_mill_lifecycle(client: TestClient):
    # ── Auth ──────────────────────────────────────────────────────────────────
    login(client, "admin")
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["role"] == "admin"

    # ── Supplier ──────────────────────────────────────────────────────────────
    r = client.post("/api/partners/suppliers", json={
        "name": "E2E Yarn Supplier", "phone": "9000000001",
    })
    assert r.status_code == 201
    supplier_id = r.json()["id"]

    # ── Yarn item ─────────────────────────────────────────────────────────────
    r = client.post("/api/items", json={
        "sku": "E2E-YARN-01", "name": "E2E Test Yarn",
        "item_type": "yarn", "reorder_point_kg": 100,
    })
    assert r.status_code == 201
    yarn_id = r.json()["id"]

    # ── Fabric item ───────────────────────────────────────────────────────────
    r = client.post("/api/items", json={
        "sku": "E2E-FAB-01", "name": "E2E Test Fabric",
        "item_type": "fabric", "gsm": 130, "width_cm": 115,
        "yarn_kg_per_meter": 0.2,
    })
    assert r.status_code == 201
    fabric_id = r.json()["id"]

    # ── Buyer ─────────────────────────────────────────────────────────────────
    r = client.post("/api/partners/buyers", json={
        "name": "E2E Buyer Co.", "credit_days": 30,
    })
    assert r.status_code == 201
    buyer_id = r.json()["id"]

    # ── Purchase Order ────────────────────────────────────────────────────────
    r = client.post("/api/purchasing", json={
        "supplier_id": supplier_id,
        "order_date": "2026-10-01",
        "lines": [{"item_id": yarn_id, "qty_kg": 500, "rate_per_kg_paise": 28000_00}],
    })
    assert r.status_code == 201
    po_id = r.json()["id"]
    po_line_id = r.json()["lines"][0]["id"]

    # Confirm PO
    r = client.post(f"/api/purchasing/{po_id}/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    # Receive yarn
    r = client.post(f"/api/purchasing/{po_id}/receive", json={
        "po_line_id": po_line_id, "received_date": "2026-10-03",
        "qty_kg": 500, "lot_number": "LOT-E2E-001", "location_code": "RAW",
    })
    assert r.status_code == 201

    # ── Sale Order ────────────────────────────────────────────────────────────
    r = client.post("/api/orders", json={
        "buyer_id": buyer_id, "order_date": "2026-10-05",
        "lines": [{"item_id": fabric_id, "qty_meters": 100, "rate_per_meter_paise": 9000_00}],
    })
    assert r.status_code == 201
    order_id = r.json()["id"]

    r = client.post(f"/api/orders/{order_id}/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    # ── Machine ───────────────────────────────────────────────────────────────
    r = client.post("/api/machines", json={
        "code": "WL-E2E", "name": "E2E Weaving Loom", "machine_type": "weaving",
    })
    assert r.status_code == 201
    machine_id = r.json()["id"]

    # ── Production Run ────────────────────────────────────────────────────────
    r = client.post("/api/production", json={
        "machine_id": machine_id, "order_id": order_id, "item_id": fabric_id,
    })
    assert r.status_code == 201
    run_id = r.json()["id"]
    assert r.json()["current_stage"] == "warping"

    # Advance: warping → weaving (consume yarn)
    r = client.post(f"/api/production/{run_id}/advance", json={"yarn_kg": 20})
    assert r.status_code == 200
    assert r.json()["current_stage"] == "weaving"

    # Advance: weaving → inspection (final stage)
    r = client.post(f"/api/production/{run_id}/advance", json={"yarn_kg": 0})
    assert r.status_code == 200
    assert r.json()["current_stage"] == "inspection"

    # ── Create Roll ───────────────────────────────────────────────────────────
    r = client.post("/api/rolls", json={"run_id": run_id, "length_cm": 5000, "weight_g": 9000})
    assert r.status_code == 201
    roll_id = r.json()["id"]
    assert r.json()["status"] == "awaiting_qc"

    # ── QC ────────────────────────────────────────────────────────────────────
    r = client.post(f"/api/rolls/{roll_id}/inspect",
                    json={"verdict": "passed", "grade": "A", "note": "looks good"})
    assert r.status_code == 200
    assert r.json()["status"] == "passed"

    # Move to store
    r = client.post(f"/api/rolls/{roll_id}/store")
    assert r.status_code == 200
    assert r.json()["status"] == "in_store"

    # ── Dispatch ──────────────────────────────────────────────────────────────
    from datetime import date
    r = client.post("/api/dispatch", json={
        "roll_ids": [roll_id],
        "dispatch_date": str(date.today()),
        "buyer_id": buyer_id,
        "vehicle_no": "KA-01-AB-1234",
    })
    assert r.status_code == 201
    assert r.json()["dispatched"] == 1

    # ── Invoice & Payment ────────────────────────────────────────────────────
    r = client.post("/api/finance/invoices", json={
        "invoice_type": "sale", "buyer_id": buyer_id,
        "invoice_date": "2026-10-10",
        "lines": [{"description": "Fabric supply", "qty": 50, "unit_price_paise": 9000_00, "tax_pct": 5}],
    })
    assert r.status_code == 201
    inv_id = r.json()["id"]
    assert r.json()["balance_paise"] > 0

    r = client.post(f"/api/finance/invoices/{inv_id}/pay", json={
        "paid_date": "2026-10-12", "amount_paise": 500_000_00, "method": "neft",
    })
    assert r.status_code == 201

    # ── Dashboard ─────────────────────────────────────────────────────────────
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "order_counts" in data
    assert "low_stock_alerts" in data
