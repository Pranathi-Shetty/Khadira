"""Tests for storage-level data integrity, direction consistency, and multi-role audit attribution."""

import pytest
import sqlite3
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from mill.models import StockLevel, StockMove, User
from mill.services.common import DomainError
from mill.services.inventory import post_move
from tests.conftest import login


class TestStorageIntegrity:
    """Verify database-level constraints, direction rules, and stock movement audit fields."""

    def test_storage_layer_refuses_negative_stock(self, client: TestClient, app):
        """Taking stock below zero directly in the DB bypassing business logic must be refused."""
        SessionLocal = app.state.session_factory
        db = SessionLocal()
        try:
            level = db.query(StockLevel).first()
            if not level:
                level = StockLevel(item_id=1, location_id=1, qty_g=5000)
                db.add(level)
                db.commit()

            # Attempt 1: Raw SQL UPDATE directly in the storage layer
            with pytest.raises((IntegrityError, sqlite3.IntegrityError)) as exc_info:
                db.execute(text("UPDATE stock_level SET qty_g = -500 WHERE id = :id"), {"id": level.id})
                db.commit()
            assert "CHECK constraint failed: ck_stock_level_qty_non_negative" in str(exc_info.value)

            db.rollback()

            # Attempt 2: Direct raw SQL INSERT of negative stock
            with pytest.raises((IntegrityError, sqlite3.IntegrityError)) as exc_info:
                db.execute(text("INSERT INTO stock_level (item_id, location_id, qty_g) VALUES (9999, 9999, -1)"))
                db.commit()
            assert "CHECK constraint failed: ck_stock_level_qty_non_negative" in str(exc_info.value)
        finally:
            db.rollback()
            db.close()

    def test_storage_layer_refuses_invalid_movement_type(self, client: TestClient, app):
        """Invalid movement_type must be refused at the storage layer."""
        SessionLocal = app.state.session_factory
        db = SessionLocal()
        try:
            with pytest.raises((IntegrityError, sqlite3.IntegrityError)) as exc_info:
                db.execute(text(
                    "INSERT INTO stock_move (item_id, location_id, delta_g, movement_type, user_id, created_at) "
                    "VALUES (1, 1, 100, 'unauthorized_type', 1, datetime('now'))"
                ))
                db.commit()
            assert "CHECK constraint failed" in str(exc_info.value)
        finally:
            db.rollback()
            db.close()

    def test_storage_layer_enforces_type_direction_consistency(self, client: TestClient, app):
        """Receipts/fabric-in must be positive; yarn_issue/fabric-out must be negative; user_id is required."""
        SessionLocal = app.state.session_factory
        db = SessionLocal()
        try:
            # 1. Receipt cannot be negative
            with pytest.raises((IntegrityError, sqlite3.IntegrityError)) as exc_info:
                db.execute(text(
                    "INSERT INTO stock_move (item_id, location_id, delta_g, movement_type, user_id, created_at) "
                    "VALUES (1, 1, -100, 'receipt', 1, datetime('now'))"
                ))
                db.commit()
            assert "ck_stock_move_type_direction" in str(exc_info.value)
            db.rollback()

            # 2. Yarn issue cannot be positive
            with pytest.raises((IntegrityError, sqlite3.IntegrityError)) as exc_info:
                db.execute(text(
                    "INSERT INTO stock_move (item_id, location_id, delta_g, movement_type, user_id, created_at) "
                    "VALUES (1, 1, 100, 'yarn_issue', 1, datetime('now'))"
                ))
                db.commit()
            assert "ck_stock_move_type_direction" in str(exc_info.value)
            db.rollback()

            # 3. Fabric out cannot be positive
            with pytest.raises((IntegrityError, sqlite3.IntegrityError)) as exc_info:
                db.execute(text(
                    "INSERT INTO stock_move (item_id, location_id, delta_g, movement_type, user_id, created_at) "
                    "VALUES (1, 1, 500, 'fabric_out', 1, datetime('now'))"
                ))
                db.commit()
            assert "ck_stock_move_type_direction" in str(exc_info.value)
            db.rollback()

            # 4. Fabric in cannot be negative
            with pytest.raises((IntegrityError, sqlite3.IntegrityError)) as exc_info:
                db.execute(text(
                    "INSERT INTO stock_move (item_id, location_id, delta_g, movement_type, user_id, created_at) "
                    "VALUES (1, 1, -500, 'fabric_in', 1, datetime('now'))"
                ))
                db.commit()
            assert "ck_stock_move_type_direction" in str(exc_info.value)
            db.rollback()

            # 5. Missing user_id (NULL) is refused
            with pytest.raises((IntegrityError, sqlite3.IntegrityError)) as exc_info:
                db.execute(text(
                    "INSERT INTO stock_move (item_id, location_id, delta_g, movement_type, user_id, created_at) "
                    "VALUES (1, 1, 500, 'receipt', NULL, datetime('now'))"
                ))
                db.commit()
            assert "NOT NULL constraint failed: stock_move.user_id" in str(exc_info.value)
            db.rollback()

            # 6. Valid yarn_return (positive) and opening_balance (positive) are accepted
            db.execute(text(
                "INSERT INTO stock_move (item_id, location_id, delta_g, movement_type, user_id, created_at) "
                "VALUES (1, 1, 300, 'yarn_return', 1, datetime('now'))"
            ))
            db.execute(text(
                "INSERT INTO stock_move (item_id, location_id, delta_g, movement_type, user_id, created_at) "
                "VALUES (1, 1, 400, 'opening_balance', 1, datetime('now'))"
            ))
            db.commit()
        finally:
            db.rollback()
            db.close()

    def test_movement_function_refuses_missing_user(self, app):
        """Business logic function post_move must refuse recording a movement without a user."""
        SessionLocal = app.state.session_factory
        db = SessionLocal()
        try:
            with pytest.raises(DomainError) as exc_info:
                post_move(
                    db,
                    item_id=1,
                    location_code="RAW",
                    delta_g=100,
                    movement_type="receipt",
                    user_id=None,
                )
            assert "user_id is required" in str(exc_info.value)
        finally:
            db.close()

    def test_multi_role_operations_and_authentic_attribution(self, client: TestClient, app):
        """Operations performed as different roles must attribute each movement to the authentic actor."""
        SessionLocal = app.state.session_factory

        # Create master data as admin
        login(client, "admin")
        r_sup = client.post("/api/partners/suppliers", json={"name": "Attribution Sup", "payment_terms_days": 30})
        sup_id = r_sup.json()["id"]

        r_yarn = client.post("/api/items", json={
            "sku": "ATTR-YARN-01", "name": "Attribution Yarn", "item_type": "yarn",
            "count_denier": "40s", "reorder_point_kg": 10,
        })
        yarn_id = r_yarn.json()["id"]

        r_po = client.post("/api/purchasing", json={
            "supplier_id": sup_id, "order_date": "2026-10-01",
            "lines": [{"item_id": yarn_id, "qty_kg": 80, "rate_per_kg_paise": 28000}],
        })
        po_id = r_po.json()["id"]
        po_line_id = r_po.json()["lines"][0]["id"]
        client.post(f"/api/purchasing/{po_id}/confirm")

        r_fab = client.post("/api/items", json={
            "sku": "ATTR-FAB-01", "name": "Attribution Fabric", "item_type": "fabric",
            "gsm": 140, "width_cm": 110, "yarn_kg_per_meter": 0.18,
        })
        fabric_id = r_fab.json()["id"]

        r_mac = client.post("/api/machines", json={
            "code": "ATTR-M1", "name": "Attribution Loom", "machine_type": "weaving",
        })
        mac_id = r_mac.json()["id"]

        # --- OPERATION 1: RECEIVE YARN AS STORE KEEPER ---
        login(client, "store")
        r_recv = client.post(f"/api/purchasing/{po_id}/receive", json={
            "po_line_id": po_line_id, "received_date": "2026-10-02",
            "qty_kg": 80, "lot_number": "LOT-ATTR-01", "location_code": "RAW",
        })
        assert r_recv.status_code == 201

        db = SessionLocal()
        try:
            store_user = db.query(User).filter_by(username="store").one()
            recv_move = db.query(StockMove).filter(
                StockMove.item_id == yarn_id,
                StockMove.movement_type == "receipt",
            ).order_by(StockMove.id.desc()).first()
            assert recv_move is not None
            assert recv_move.delta_g == 80_000
            assert recv_move.user_id == store_user.id
            assert recv_move.user.username == "store"
        finally:
            db.close()

        # --- OPERATION 2: START RUN & ADVANCE AS FLOOR SUPERVISOR ---
        login(client, "floor_supervisor")
        r_run = client.post("/api/production", json={"machine_id": mac_id, "item_id": fabric_id})
        run_id = r_run.json()["id"]

        r_adv = client.post(f"/api/production/{run_id}/advance", json={"yarn_kg": 10.0})
        assert r_adv.status_code == 200

        db = SessionLocal()
        try:
            sup_user = db.query(User).filter_by(username="floor_supervisor").one()
            issue_move = db.query(StockMove).filter(
                StockMove.ref == f"RUN-{run_id}",
                StockMove.movement_type == "yarn_issue",
            ).first()
            assert issue_move is not None
            assert issue_move.delta_g == -10_000
            assert issue_move.user_id == sup_user.id
            assert issue_move.user.username == "floor_supervisor"
        finally:
            db.close()

        # Advance to completion and create roll
        client.post(f"/api/production/{run_id}/advance", json={})
        r_roll = client.post("/api/rolls", json={"run_id": run_id, "length_cm": 3000})
        roll_id = r_roll.json()["id"]

        # --- OPERATION 3: INSPECT ROLL AS QC INSPECTOR ---
        login(client, "qc")
        r_insp = client.post(f"/api/rolls/{roll_id}/inspect", json={"verdict": "passed"})
        assert r_insp.status_code == 200

        # Move to store as floor_supervisor
        login(client, "floor_supervisor")
        r_store = client.post(f"/api/rolls/{roll_id}/store")
        assert r_store.status_code == 200

        db = SessionLocal()
        try:
            sup_user = db.query(User).filter_by(username="floor_supervisor").one()
            fab_in_move = db.query(StockMove).filter(
                StockMove.item_id == fabric_id,
                StockMove.movement_type == "fabric_in",
            ).first()
            assert fab_in_move is not None
            assert fab_in_move.delta_g == 3000
            assert fab_in_move.user_id == sup_user.id
            assert fab_in_move.user.username == "floor_supervisor"
        finally:
            db.close()

        # --- OPERATION 4: DISPATCH AS OFFICE STAFF ---
        login(client, "office")
        r_disp = client.post("/api/dispatch", json={
            "roll_ids": [roll_id],
            "dispatch_date": str(date.today()),
        })
        assert r_disp.status_code == 201

        db = SessionLocal()
        try:
            office_user = db.query(User).filter_by(username="office").one()
            disp_move = db.query(StockMove).filter(
                StockMove.item_id == fabric_id,
                StockMove.movement_type == "fabric_out",
            ).first()
            assert disp_move is not None
            assert disp_move.delta_g == -3000
            assert disp_move.user_id == office_user.id
            assert disp_move.user.username == "office"
        finally:
            db.close()
