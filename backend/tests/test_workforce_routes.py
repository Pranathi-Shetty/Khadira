"""Coverage for the role-protected workforce, wages and costing API routes."""

from datetime import date

from mill.permissions import permissions_for


def test_workforce_api_permissions_and_wage_flow(client):
    assert "attendance.write" in permissions_for("floor_supervisor")
    assert "attendance.approve" in permissions_for("floor_supervisor")
    assert "wages.write" in permissions_for("office")
    assert "costing.write" in permissions_for("office")
    assert "attendance.read" not in permissions_for("office")

    today = date.today().isoformat()
    worker_code = f"WF-{today.replace('-', '')}"
    client.post("/api/auth/login", json={"username": "admin", "password": "khadira2026!"})
    created = client.post("/api/attendance/workers", json={
        "code": worker_code, "full_name": "Test Loom Operator",
        "department": "Weaving", "wage_basis": "hourly", "hourly_rate_paise": 9000,
    })
    assert created.status_code == 201, created.text
    worker_id = created.json()["id"]
    buyer = client.post("/api/partners/buyers", json={"name": f"Costing QA {worker_code}"})
    assert buyer.status_code == 201, buyer.text
    fabric = client.post("/api/items", json={
        "sku": f"FAB-{today.replace('-', '')}", "name": "QA Cotton Fabric",
        "item_type": "fabric", "unit": "m", "yarn_kg_per_meter": 0.1,
    })
    assert fabric.status_code == 201, fabric.text

    client.post("/api/auth/login", json={"username": "floor_supervisor", "password": "khadira2026!"})
    assert client.get("/api/wages").status_code == 403
    attendance = client.post("/api/attendance", json={
        "worker_id": worker_id, "work_date": today, "shift": "A", "hours_worked": 480,
    })
    assert attendance.status_code == 201, attendance.text
    approved = client.post(f"/api/attendance/{attendance.json()['id']}/approve")
    assert approved.status_code == 200, approved.text

    client.post("/api/auth/login", json={"username": "office", "password": "khadira2026!"})
    run = client.post("/api/wages/calculate", json={"period_start": today, "period_end": today})
    assert run.status_code == 201, run.text
    assert run.json()["total_wage_paise"] == 72000
    assert client.get("/api/attendance").status_code == 403

    order = client.post("/api/orders", json={
        "buyer_id": buyer.json()["id"], "order_date": today,
        "lines": [{"item_id": fabric.json()["id"], "qty_meters": 100, "rate_per_meter_paise": 5000}],
    })
    assert order.status_code == 201, order.text
    costing = client.post(f"/api/costing/orders/{order.json()['id']}/calculate")
    assert costing.status_code == 200, costing.text
    assert costing.json()["material_cost_status"] == "not_applicable"
    assert client.get(f"/api/costing/orders/{order.json()['id']}").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/costing/orders/{order_id}/calculate" in paths


def test_office_can_read_live_order_material_progress(client):
    client.post("/api/auth/login", json={"username": "office", "password": "khadira2026!"})

    for endpoint in ("/api/orders", "/api/production", "/api/rolls", "/api/machines"):
        response = client.get(endpoint)
        assert response.status_code == 200, f"{endpoint}: {response.text}"

    assert "production.write" not in permissions_for("office")
    assert "rolls.write" not in permissions_for("office")
    assert "machines.write" not in permissions_for("office")
