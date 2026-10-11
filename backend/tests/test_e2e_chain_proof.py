"""Step 8: End-to-End Automated Proof of the Entire Textile Mill Lifecycle.

Runs a complete order through the whole chain:
1. Yarn purchase order and confirmation
2. Yarn receipt with YarnLot batch creation and stock increase in RAW
3. Order creation and confirmation with yarn sufficiency check
4. Production run and yarn issue across lots (FIFO batch consumption)
5. Roll creation at final production stage
6. QC inspection with canonical results: at least one pass, one rework, one reject
7. Passed roll moved to finished goods store (FIN)
8. Atomic dispatch and automatic matching sale invoice creation
9. Verification that invoice equals dispatch (exact integer cm and paise match)
10. Storage-level double-dispatch refusal
11. Buyer payment against invoice
12. Order costing calculation (material, wages, overhead, cost per passed metre)
13. Final stock levels assertion (RAW and FIN match movements)
14. Roll traceability (tracing roll back to run, machine, order, yarn lots, and supplier)
"""
from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from mill.models import (
    Buyer, Dispatch, DispatchRoll, Invoice, Item, Location, Machine,
    Order, OrderCost, Payment, ProductionRun, PurchaseOrder, PurchaseOrderLine,
    Roll, RollEvent, Setting, StockLevel, Supplier, Worker, YarnLot
)
from mill.services.common import DomainError
from mill.services.orders import create_order, confirm_order
from mill.services.pricing import compute_fabric_line_total, compute_yarn_line_total
from mill.services.production import start_run, advance_stage, create_roll, issue_yarn_to_run, get_roll_trace
from mill.services.purchasing import receive_yarn
from mill.services.qc import inspect_roll, move_to_store
from mill.services.dispatch import dispatch_rolls
from mill.services.financial_summary import get_invoice_total_paise
from tests.conftest import login


@pytest.fixture
def auth_client(client: TestClient):
    login(client, "admin")
    return client


def test_complete_textile_mill_chain(auth_client: TestClient, db_session: Session):
    """One automated test proving the complete chain end-to-end."""
    # ── 0. SETUP BASELINE SETTINGS & LOCATIONS ────────────────────────────────
    ov_setting = db_session.get(Setting, "overhead_per_metre_paise")
    if not ov_setting:
        db_session.add(Setting(key="overhead_per_metre_paise", value="1500"))  # ₹15.00 / metre
    else:
        ov_setting.value = "1500"

    raw_loc = db_session.query(Location).filter_by(code="RAW").first()
    if not raw_loc:
        raw_loc = Location(code="RAW", name="Raw Yarn Store")
        db_session.add(raw_loc)

    fin_loc = db_session.query(Location).filter_by(code="FIN").first()
    if not fin_loc:
        fin_loc = Location(code="FIN", name="Finished Fabric Store")
        db_session.add(fin_loc)

    # Supplier & Buyer
    supplier = Supplier(name="Apex Cotton Spinning Mills", phone="9876543210")
    buyer = Buyer(name="Global Garments Export Ltd", credit_days=30)
    db_session.add_all([supplier, buyer])
    db_session.flush()

    # Yarn & Fabric items
    yarn = Item(sku="YRN-E2E-40S", name="40s Combed Cotton Yarn", item_type="yarn", unit="kg")
    fabric = Item(
        sku="FAB-E2E-POPLIN", name="Poplin Shirting 120 GSM", item_type="fabric",
        unit="meters", gsm=120, width_cm=112, yarn_kg_per_meter=0.200  # 200g per metre
    )
    db_session.add_all([yarn, fabric])

    # Weaving Machine
    machine = Machine(code="WL-E2E-101", name="Tsudakoma Airjet 101", machine_type="weaving")
    db_session.add(machine)
    db_session.commit()

    # ── 1. YARN PURCHASE & CONFIRMATION ───────────────────────────────────────
    # Purchase 100 kg at ₹250.00/kg (25000 paise per kg)
    po = PurchaseOrder(
        ref="PO-CHAIN-001", supplier_id=supplier.id,
        order_date=date(2026, 11, 1), status="draft"
    )
    db_session.add(po)
    db_session.flush()

    po_line = PurchaseOrderLine(
        po_id=po.id, item_id=yarn.id, qty_kg=100, rate_per_kg_paise=25000
    )
    db_session.add(po_line)
    db_session.commit()

    # Confirm PO via API
    r_po_conf = auth_client.post(f"/api/purchasing/{po.id}/confirm")
    assert r_po_conf.status_code == 200
    assert r_po_conf.json()["status"] == "confirmed"
    db_session.refresh(po)

    # ── 2. YARN RECEIPT & LOT CREATION ────────────────────────────────────────
    # Receive 100 kg yarn into RAW store
    receipt = receive_yarn(
        db_session, po_id=po.id, po_line_id=po_line.id, received_date=date(2026, 11, 2),
        qty_kg=100, vehicle_no="KA-04-TR-9988", notes="Inspected clean cones",
        lot_number="LOT-APEX-40S-01", location_code="RAW", user_id=1
    )
    db_session.commit()

    # Verify YarnLot created with full remaining quantity
    lot = db_session.query(YarnLot).filter_by(lot_number="LOT-APEX-40S-01").first()
    assert lot is not None
    assert lot.qty_g == 100_000  # 100 kg = 100,000 g
    assert lot.remaining_g == 100_000

    # Verify RAW stock level
    raw_stock_before = db_session.query(StockLevel).filter_by(item_id=yarn.id, location_id=raw_loc.id).first()
    assert raw_stock_before.qty_g == 100_000

    # ── 3. ORDER CREATION & CONFIRMATION (YARN CHECK) ─────────────────────────
    # Order for 150 metres of fabric at ₹140.00/m (14000 paise/m)
    # Required yarn: 150m * 0.200 kg/m = 30 kg (30,000 g). Available: 100 kg.
    order = create_order(
        db_session, buyer_id=buyer.id, order_date=date(2026, 11, 5),
        delivery_date=date(2026, 11, 25),
        lines=[{"item_id": fabric.id, "qty_meters": 150, "rate_per_meter_paise": 14000}],
        tolerance_pct=5.0, user_id=1
    )
    db_session.commit()

    # Confirm order (verifies yarn sufficiency in storage layer)
    order = confirm_order(db_session, order.id, user_id=1)
    db_session.commit()
    assert order.status == "confirmed"

    # ── 4. PRODUCTION RUN & FIFO YARN ISSUE ───────────────────────────────────
    run = start_run(db_session, machine_id=machine.id, order_id=order.id, item_id=fabric.id, user_id=1)
    db_session.commit()
    assert run.current_stage == "warping"

    # Issue 30 kg yarn to run (30,000 g)
    run_materials = issue_yarn_to_run(db_session, run_id=run.id, qty_g=30_000, item_id=yarn.id, user_id=1)
    db_session.commit()
    assert len(run_materials) == 1
    assert run_materials[0].lot_id == lot.id
    assert run_materials[0].issued_g == 30_000

    # Assert lot remaining decreased accurately
    db_session.refresh(lot)
    assert lot.remaining_g == 70_000  # 100,000 - 30,000 = 70,000 g

    # Advance stages: warping -> weaving -> inspection
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1)  # warping -> weaving
    advance_stage(db_session, run_id=run.id, yarn_kg=0, user_id=1)  # weaving -> inspection
    db_session.commit()
    assert run.current_stage == "inspection"

    # ── 5. ROLLS CREATED ──────────────────────────────────────────────────────
    # Create 3 rolls:
    # - Roll 1: 100m (10,000 cm), 20 kg
    # - Roll 2: 30m (3,000 cm), 6 kg
    # - Roll 3: 20m (2,000 cm), 4 kg
    r1 = create_roll(db_session, run_id=run.id, length_cm=10000, weight_g=20000, user_id=1)
    r2 = create_roll(db_session, run_id=run.id, length_cm=3000, weight_g=6000, user_id=1)
    r3 = create_roll(db_session, run_id=run.id, length_cm=2000, weight_g=4000, user_id=1)
    db_session.commit()

    # ── 6. QC INSPECTION: PASS, REWORK, REJECT ────────────────────────────────
    # Roll 1 passes inspection (Grade A)
    inspect_roll(db_session, roll_id=r1.id, verdict="pass", grade="A", note="Clear weave", user_id=1)

    # Roll 2 needs rework
    inspect_roll(db_session, roll_id=r2.id, verdict="rework", grade=None, note="Selvedge loose", user_id=1)

    # Roll 3 is rejected
    inspect_roll(db_session, roll_id=r3.id, verdict="reject", grade="C", note="Contamination streak", user_id=1)
    db_session.commit()

    assert r1.status == "passed"
    assert r2.status == "rework"
    assert r3.status == "rejected"

    # ── 7. PASSED ROLLS STORED (FIN LOCATION) ─────────────────────────────────
    move_to_store(db_session, roll_id=r1.id, user_id=1)
    db_session.commit()
    assert r1.status == "in_store"

    # Verify FIN stock holds the 100m (10,000 cm)
    fin_stock = db_session.query(StockLevel).filter_by(item_id=fabric.id, location_id=fin_loc.id).first()
    assert fin_stock.qty_g == 10000  # 10,000 cm stored

    # ── 8. ATOMIC DISPATCH & MATCHING INVOICE CREATION ────────────────────────
    disp, inv, moves = dispatch_rolls(
        db_session, roll_ids=[r1.id], dispatch_date=date(2026, 11, 20),
        buyer_id=buyer.id, order_id=order.id, vehicle_no="KA-05-EX-4421",
        notes="Export dispatch lot 1", user_id=1
    )
    db_session.commit()

    assert r1.status == "dispatched"
    assert disp is not None
    assert inv is not None
    assert inv.dispatch_id == disp.id
    assert inv.order_id == order.id

    # ── 9. ASSERT: INVOICE EQUALS DISPATCH ────────────────────────────────────
    # Dispatched roll centimetres: 10,000 cm (100 m)
    # Invoice line quantities in metres: Decimal('100.000') = 10,000 cm
    inv_line = inv.lines[0]
    inv_cm = int(inv_line.qty * 100)
    assert inv_cm == r1.length_cm == 10000

    # Invoice line total in paise equals integer formula
    expected_line_base = compute_fabric_line_total(10000, 14000)  # 100m * 14000 = 1,400,000 paise (₹14,000)
    actual_line_base = compute_fabric_line_total(inv_cm, inv_line.unit_price_paise)
    assert actual_line_base == expected_line_base == 1400000
    assert inv_line.unit_price_paise == 14000

    # ── 10. ASSERT: DOUBLE-DISPATCH REFUSAL ───────────────────────────────────
    with pytest.raises(DomainError) as exc_dd:
        dispatch_rolls(
            db_session, roll_ids=[r1.id], dispatch_date=date(2026, 11, 21),
            buyer_id=buyer.id, order_id=order.id, user_id=1
        )
    assert "not in store" in str(exc_dd.value)

    # ── 11. BUYER PAYMENT ─────────────────────────────────────────────────────
    # Buyer pays the ₹14,000 invoice (1,400,000 paise + 5% tax = 1,470,000 paise)
    total_due = get_invoice_total_paise(inv)
    r_pay = auth_client.post(f"/api/finance/invoices/{inv.id}/pay", json={
        "paid_date": "2026-11-22",
        "amount_paise": total_due,
        "method": "neft",
    })
    assert r_pay.status_code in (200, 201)
    assert r_pay.json()["balance_paise"] == 0
    assert r_pay.json()["status"] == "paid"

    # ── 12. ORDER COSTING CALCULATION ─────────────────────────────────────────
    r_cost = auth_client.post(f"/api/costing/orders/{order.id}/calculate")
    assert r_cost.status_code == 200
    cost_data = r_cost.json()

    # Material cost: 30,000g @ ₹250/kg = 750,000 paise (₹7,500.00)
    assert cost_data["yarn_used_g"] == 30_000
    assert cost_data["material_cost_paise"] == 750000
    assert cost_data["material_cost_status"] == "priced"

    # Passed metres: 100m (from passed roll)
    assert cost_data["passed_metres"] == 100

    # Overhead: 100m * 1500 = 150,000 paise (₹1,500.00)
    assert cost_data["overhead_paise"] == 150000

    # Known cost: material (750k) + overhead (150k) + wages (0) = 900,000 paise (₹9,000.00)
    assert cost_data["known_cost_paise"] == 900000

    # Cost per passed metre: 900,000 // 100 = 9,000 paise (₹90.00/m)
    assert cost_data["cost_per_passed_metre_paise"] == 9000
    assert cost_data["cost_per_passed_metre_status"] == "available"

    # ── 13. ASSERT: STOCK LEVELS AT THE END ───────────────────────────────────
    # RAW stock: initial (100,000 g) - issued (30,000 g) = 70,000 g (70.0 kg)
    db_session.refresh(raw_stock_before)
    assert raw_stock_before.qty_g == 70_000

    # FIN stock: received to store (10,000 cm) - dispatched (10,000 cm) = 0 cm (0 m)
    db_session.refresh(fin_stock)
    assert fin_stock.qty_g == 0

    # Yarn lot remaining: 100,000 - 30,000 = 70,000 g
    assert lot.remaining_g == 70_000

    # ── 14. ASSERT: TRACEABILITY OF A ROLL ─────────────────────────────────────
    # Trace Roll 1 back to run, machine, order, yarn lots, and supplier
    trace = get_roll_trace(db_session, r1.id)
    assert trace["roll"]["id"] == r1.id
    assert trace["roll"]["roll_number"] == r1.roll_number
    assert trace["run"]["id"] == run.id
    assert trace["machine"]["code"] == machine.code
    assert trace["order"]["id"] == order.id
    assert trace["order"]["ref"] == order.ref

    # Batches used
    assert len(trace["yarn_batches"]) == 1
    batch = trace["yarn_batches"][0]
    assert batch["lot_number"] == lot.lot_number
    assert batch["issued_g"] == 30_000
    assert batch["supplier"]["name"] == supplier.name

    # Suppliers list
    supplier_names = [s["name"] for s in trace["suppliers"]]
    assert supplier.name in supplier_names
