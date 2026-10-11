"""Service-driven scenario loader for Khadira Textile Mills.

Loads realistic, domain-service-driven demonstration data:
- 12 distinct buyers, 4 suppliers, 6 system users, 6 workers
- Multi-month timeline (July 2026 -> October 2026)
- 8 Purchase Orders: fully received, partially received, in-transit, cancelled
- 25 Sales Orders exercising all 14 lifecycle branches:
    1. Draft with refused confirmation for lack of yarn
    2. Draft awaiting confirmation
    3. Cancelled
    4. Confirmed and waiting
    5. Just started in early stages (warping)
    6. Mid-weaving
    7. In inspection with mix of results (pass, rework, reject) + defect tracking
    8. Rework left waiting
    9. Fully in store waiting for dispatch
    10. Part dispatched
    11. Fully dispatched but late
    12. Fully dispatched and unpaid / overdue
    13. Partly paid
    14. Fully paid
- Monthly attendance & wage runs for 6 workers across July -> October
- Idempotent: repeated runs detect existing scenario data and do not duplicate.
"""

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

from mill.models import (
    Base, Item, Location, StockLevel, StockMove, User, Setting, Worker,
    AttendanceEntry, WageRun, WageRunLine, Supplier, Buyer,
    PurchaseOrder, PurchaseOrderLine, YarnLot, YarnReceipt,
    Order, OrderLine, Machine, MachineDowntime, ProductionRun,
    Roll, RollEvent, RollDefect, RunMaterial, RunReconciliation,
    Invoice, InvoiceLine, Payment, Dispatch, DispatchRoll, AuditLog,
    ITEM_YARN, ITEM_FABRIC
)
from mill.services.auth import hash_password
from mill.services.common import DomainError
from mill.services.purchasing import create_po, confirm_po, receive_yarn, cancel_po
from mill.services.orders import create_order, confirm_order, cancel_order, calculate_order_progress
from mill.services.production import start_run, advance_stage, issue_yarn_to_run, create_roll
from mill.services.qc import inspect_roll, move_to_store, record_defect
from mill.services.dispatch import dispatch_rolls
from mill.services.attendance import create_entry, approve_entry
from mill.services.financial_summary import get_invoice_total_paise

PASSWORD = "khadira2026!"


def _dt(d: date, hour: int = 10, minute: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc)


def load_scenario(db: Session, force_reset: bool = False) -> dict:
    """Load the full operational scenario using real domain services."""
    # ── 1. IDEMPOTENCY CHECK ─────────────────────────────────────────────────
    existing_po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.ref == "PO-2026-00001"))
    if existing_po is not None and not force_reset:
        print("[*] Scenario data already present (PO-2026-00001 exists). Skipping duplicate load.")
        return {
            "status": "already_loaded",
            "orders_count": db.scalar(select(func.count(Order.id))) or 0,
            "rolls_count": db.scalar(select(func.count(Roll.id))) or 0,
        }

    if force_reset:
        print("[!] Force reset requested: dropping and recreating tables...")
        Base.metadata.drop_all(bind=db.get_bind())
        Base.metadata.create_all(bind=db.get_bind())

    print("[*] Starting service-driven scenario generation...")

    # ── 2. SYSTEM SETTINGS ───────────────────────────────────────────────────
    settings = [
        ("company_name", "Khadira Textile Mills Pvt. Ltd."),
        ("currency", "INR"),
        ("low_stock_threshold_kg", "500"),
        ("default_warehouse", "RAW"),
        ("qc_standard", "ASTM D5430 4-Point System"),
        ("mill_location", "Surat, Gujarat"),
        ("overhead_per_metre_paise", "1500"),  # ₹15.00 / metre
        ("default_yarn_rate_per_kg_paise", "25000"),  # ₹250.00 / kg
    ]
    for k, v in settings:
        s = db.get(Setting, k)
        if not s:
            db.add(Setting(key=k, value=v))
        else:
            s.value = v
    db.flush()

    # ── 3. LOCATIONS ─────────────────────────────────────────────────────────
    locations = {}
    for code, name in [
        ("RAW", "Raw Material Store (Yarn Warehouse)"),
        ("FIN", "Finished Goods Store (Inspection & Packing)"),
        ("WIP", "Weaving Shed & Loom Floor"),
    ]:
        loc = db.scalar(select(Location).where(Location.code == code))
        if not loc:
            loc = Location(code=code, name=name)
            db.add(loc)
            db.flush()
        locations[code] = loc

    # ── 4. USERS (All 6 core roles) ──────────────────────────────────────────
    users_data = [
        ("admin",            "Admin User",        "admin@khadira.in",          "admin"),
        ("owner",            "Owner & Finance",   "owner@khadira.in",          "owner"),
        ("store",            "Store Keeper",      "store@khadira.in",          "store"),
        ("floor_supervisor", "Floor Supervisor",  "supervisor@khadira.in",     "floor_supervisor"),
        ("qc",               "QC Inspector",      "qc@khadira.in",             "qc"),
        ("office",           "Office Staff",      "office@khadira.in",         "office"),
    ]
    users = {}
    for uname, fname, email, role in users_data:
        u = db.scalar(select(User).where(User.username == uname))
        if not u:
            u = User(username=uname, full_name=fname, email=email, role=role, hashed_password=hash_password(PASSWORD))
            db.add(u)
            db.flush()
        users[uname] = u

    # ── 5. SUPPLIERS (4 suppliers) ───────────────────────────────────────────
    suppliers_data = [
        ("Apex Cotton Spinning Mills", "Rajesh Sharma", "+91-9876543210", "apex@spinning.in", "27AABCA1234A1Z5"),
        ("Deccan Fibres Ltd.",          "Priya Nair",    "+91-8765432109", "deccan@fibres.in",  "29AABCD5678A1Z3"),
        ("Himalayan Yarn Co.",         "Alok Jain",     "+91-9814002334", "orders@himalayan.in","03AAACH1299P1Z8"),
        ("Vardhman Textiles Ltd.",     "K. Murugan",    "+91-9842100223", "sales@vardhman.in", "33AAACV1234E1Z1"),
    ]
    suppliers = []
    for sname, contact, phone, email, gstin in suppliers_data:
        s = db.scalar(select(Supplier).where(Supplier.name == sname))
        if not s:
            s = Supplier(name=sname, contact_name=contact, phone=phone, email=email, gstin=gstin)
            db.add(s)
            db.flush()
        suppliers.append(s)

    # ── 6. BUYERS (12 buyers) ────────────────────────────────────────────────
    buyers_data = [
        ("Sunrise Garments Pvt. Ltd.", "Arun Kumar",   "+91-9123456789", "sunrise@garments.in", 45),
        ("Metro Fashion House",        "Deepa Singh",  "+91-8234567890", "metro@fashion.in",    30),
        ("Textile Exports Corp.",      "Sanjay Mehta", "+91-7345678901", "exports@textile.in",  60),
        ("Apex Apparels Ltd.",         "Naveen Gupta", "+91-9899112233", "sourcing@apexapparels.com", 30),
        ("Heritage Handlooms",         "Kavita Sen",   "+91-9433221100", "orders@heritagecraft.in", 15),
        ("Global Fashion Sourcing",    "David Ross",   "+91-9988776655", "dross@globalsourcing.net", 60),
        ("Royal Silk & Cottons",       "Anand Verma",  "+91-9455112233", "orders@royalsilk.in", 30),
        ("Zenith Apparel Works",       "R. Swaminathan","+91-9840223344", "purchase@zenithapparel.in", 45),
        ("Continental Weavers",        "Manish Shah",  "+91-9725001122", "mshah@continental.in", 30),
        ("Elegance Ethnic Wear",       "Subhash Roy",  "+91-9830554433", "info@eleganceethnic.com", 30),
        ("Premier Garment Makers",     "Sunil Joshi",  "+91-9822334455", "sourcing@premiergarments.in", 60),
        ("Vistara Clothiers",          "Neha Kulkarni", "+91-9820112233", "nkulkarni@vistaracloth.in", 30),
    ]
    buyers = []
    for bname, contact, phone, email, credit in buyers_data:
        b = db.scalar(select(Buyer).where(Buyer.name == bname))
        if not b:
            b = Buyer(name=bname, contact_name=contact, phone=phone, email=email, credit_days=credit)
            db.add(b)
            db.flush()
        buyers.append(b)

    # ── 7. CATALOG ITEMS (Yarn & Fabric) ──────────────────────────────────────
    yarns_data = [
        ("YRN-20-W",  "Cotton Yarn 20s White",    "20s",   500),
        ("YRN-30-W",  "Cotton Yarn 30s White",    "30s",   400),
        ("YRN-40-C",  "Cotton Yarn 40s Coloured", "40s",   300),
        ("YRN-PC-65", "Poly-Cotton Yarn 65/35",   "65/35", 400),
    ]
    yarn_items = []
    for sku, name, count, reorder_kg in yarns_data:
        it = db.scalar(select(Item).where(Item.sku == sku))
        if not it:
            it = Item(sku=sku, name=name, item_type=ITEM_YARN, unit="kg", count_denier=count, reorder_point_kg=reorder_kg)
            db.add(it)
            db.flush()
        yarn_items.append(it)

    fabrics_data = [
        ("FAB-POP-WH",  "Poplin Fabric White",      120, 110, 0.180),
        ("FAB-TWL-BL",  "Twill Fabric Blue",        200, 150, 0.240),
        ("FAB-SLB-NAT", "Slub Fabric Natural",      160, 140, 0.210),
        ("FAB-SAT-MR",  "Satin Weave Maroon",       220, 145, 0.250),
    ]
    fabric_items = []
    for sku, name, gsm, width, ykpm in fabrics_data:
        it = db.scalar(select(Item).where(Item.sku == sku))
        if not it:
            it = Item(sku=sku, name=name, item_type=ITEM_FABRIC, unit="meters", gsm=gsm, width_cm=width, yarn_kg_per_meter=ykpm)
            db.add(it)
            db.flush()
        fabric_items.append(it)

    # ── 8. MACHINES ──────────────────────────────────────────────────────────
    machines_data = [
        ("WL-01", "Tsudakoma Air-Jet 1",   "weaving"),
        ("WL-02", "Picanol Rapier Loom 2", "weaving"),
        ("WL-03", "Picanol OmniPlus 3",    "weaving"),
        ("DJ-01", "Fongs Soft-Flow Jet 1", "dyeing"),
        ("FN-01", "Monforts Stenter 1",    "dyeing"),
    ]
    machines = []
    for code, mname, mtype in machines_data:
        m = db.scalar(select(Machine).where(Machine.code == code))
        if not m:
            m = Machine(code=code, name=mname, machine_type=mtype, is_active=True)
            db.add(m)
            db.flush()
        machines.append(m)

    # ── 9. WORKERS ───────────────────────────────────────────────────────────
    workers_data = [
        ("WRK-001", "Ramesh Patel",  "Weaving",    "hourly",     6500, 0),   # ₹65/hr
        ("WRK-002", "Suresh Kumar",   "Weaving",    "hourly",     6000, 0),   # ₹60/hr
        ("WRK-003", "Anjali Sharma",  "Quality",    "hourly",     7000, 0),   # ₹70/hr
        ("WRK-004", "Dinesh Yadav",   "Preparatory","piece_rate", 0,    1200),# ₹12/roll
        ("WRK-005", "Priya Nair",     "Finishing",  "hourly",     6200, 0),   # ₹62/hr
        ("WRK-006", "Mahesh Verma",   "Maintenance","hourly",     5800, 0),   # ₹58/hr
    ]
    workers = []
    for code, wname, dept, wbasis, hrate, prate in workers_data:
        w = db.scalar(select(Worker).where(Worker.code == code))
        if not w:
            w = Worker(code=code, full_name=wname, department=dept, wage_basis=wbasis, hourly_rate_paise=hrate, piece_rate_paise=prate, is_active=True)
            db.add(w)
            db.flush()
        workers.append(w)

    db.commit()

    # ── 10. PURCHASE ORDERS & YARN RECEIPTS VIA SERVICE ───────────────────────
    # We create real POs and receipts spread across July -> October
    print("[*] Generating Purchase Orders and Yarn Receipts through domain services...")

    # PO 1: Apex Cotton - 10,000 kg YRN-20-W (July 5 -> received July 8)
    po1 = create_po(
        db, supplier_id=suppliers[0].id, order_date=date(2026, 7, 5),
        expected_date=date(2026, 7, 10),
        lines=[{"item_id": yarn_items[0].id, "qty_kg": 10000, "rate_per_kg_paise": 22000}],
        notes="Bulk 20s carded cotton yarn for Q3 shirting runs", user_id=users["store"].id
    )
    po1.created_at = _dt(date(2026, 7, 5), 9, 30)
    confirm_po(db, po1.id, user_id=users["admin"].id)
    rec1 = receive_yarn(
        db, po_id=po1.id, po_line_id=po1.lines[0].id, received_date=date(2026, 7, 8),
        qty_kg=10000, vehicle_no="GJ-05-TR-1021", notes="Cones inspected clean, verified moisture 7.8%",
        lot_number="LOT-APEX-20W-001", location_code="RAW", user_id=users["store"].id
    )
    rec1.created_at = _dt(date(2026, 7, 8), 11, 0)
    db.commit()

    # PO 2: Deccan Fibres - 8,000 kg YRN-30-W (July 15 -> received July 18)
    po2 = create_po(
        db, supplier_id=suppliers[1].id, order_date=date(2026, 7, 15),
        expected_date=date(2026, 7, 20),
        lines=[{"item_id": yarn_items[1].id, "qty_kg": 8000, "rate_per_kg_paise": 26000}],
        notes="High-tenacity 30s combed cotton yarn", user_id=users["store"].id
    )
    po2.created_at = _dt(date(2026, 7, 15), 10, 0)
    confirm_po(db, po2.id, user_id=users["admin"].id)
    rec2 = receive_yarn(
        db, po_id=po2.id, po_line_id=po2.lines[0].id, received_date=date(2026, 7, 18),
        qty_kg=8000, vehicle_no="TS-07-UB-4422", notes="Excellent package density",
        lot_number="LOT-DECC-30W-002", location_code="RAW", user_id=users["store"].id
    )
    rec2.created_at = _dt(date(2026, 7, 18), 11, 30)
    db.commit()

    # PO 3: Himalayan Yarn - 6,000 kg YRN-40-C (August 2 -> received August 5)
    po3 = create_po(
        db, supplier_id=suppliers[2].id, order_date=date(2026, 8, 2),
        expected_date=date(2026, 8, 8),
        lines=[{"item_id": yarn_items[2].id, "qty_kg": 6000, "rate_per_kg_paise": 31000}],
        notes="Special reactive-dyed 40s yarn", user_id=users["store"].id
    )
    po3.created_at = _dt(date(2026, 8, 2), 9, 0)
    confirm_po(db, po3.id, user_id=users["admin"].id)
    rec3 = receive_yarn(
        db, po_id=po3.id, po_line_id=po3.lines[0].id, received_date=date(2026, 8, 5),
        qty_kg=6000, vehicle_no="PB-10-CZ-8877", notes="Lab colour fastness cert attached",
        lot_number="LOT-HIM-40C-003", location_code="RAW", user_id=users["store"].id
    )
    rec3.created_at = _dt(date(2026, 8, 5), 14, 0)
    db.commit()

    # PO 4: Vardhman Textiles - 5,000 kg YRN-PC-65 (August 10 -> received August 14)
    po4 = create_po(
        db, supplier_id=suppliers[3].id, order_date=date(2026, 8, 10),
        expected_date=date(2026, 8, 16),
        lines=[{"item_id": yarn_items[3].id, "qty_kg": 5000, "rate_per_kg_paise": 24000}],
        notes="Polyester Cotton blend 65/35 for institutional twill", user_id=users["store"].id
    )
    po4.created_at = _dt(date(2026, 8, 10), 10, 30)
    confirm_po(db, po4.id, user_id=users["admin"].id)
    rec4 = receive_yarn(
        db, po_id=po4.id, po_line_id=po4.lines[0].id, received_date=date(2026, 8, 14),
        qty_kg=5000, vehicle_no="CH-01-AX-9911", notes="Consistent blend ratio verified",
        lot_number="LOT-VARD-PC-004", location_code="RAW", user_id=users["store"].id
    )
    rec4.created_at = _dt(date(2026, 8, 14), 16, 0)
    db.commit()

    # PO 5: Apex Cotton - 3,000 kg YRN-20-W (September 5 -> received September 8)
    po5 = create_po(
        db, supplier_id=suppliers[0].id, order_date=date(2026, 9, 5),
        expected_date=date(2026, 9, 10),
        lines=[{"item_id": yarn_items[0].id, "qty_kg": 3000, "rate_per_kg_paise": 22500}],
        notes="Supplementary lot of 20s", user_id=users["store"].id
    )
    po5.created_at = _dt(date(2026, 9, 5), 9, 15)
    confirm_po(db, po5.id, user_id=users["admin"].id)
    rec5 = receive_yarn(
        db, po_id=po5.id, po_line_id=po5.lines[0].id, received_date=date(2026, 9, 8),
        qty_kg=3000, vehicle_no="GJ-05-TR-2200", notes="Clean cones batch 2",
        lot_number="LOT-APEX-20W-005", location_code="RAW", user_id=users["store"].id
    )
    rec5.created_at = _dt(date(2026, 9, 8), 12, 0)
    db.commit()

    # PO 6: Deccan Fibres - PARTIALLY RECEIVED (September 15: ordered 3,000 kg YRN-30-W, received only 1,000 kg)
    po6 = create_po(
        db, supplier_id=suppliers[1].id, order_date=date(2026, 9, 15),
        expected_date=date(2026, 9, 25),
        lines=[{"item_id": yarn_items[1].id, "qty_kg": 3000, "rate_per_kg_paise": 26500}],
        notes="Partial delivery agreement with Deccan", user_id=users["store"].id
    )
    po6.created_at = _dt(date(2026, 9, 15), 11, 0)
    confirm_po(db, po6.id, user_id=users["admin"].id)
    rec6 = receive_yarn(
        db, po_id=po6.id, po_line_id=po6.lines[0].id, received_date=date(2026, 9, 20),
        qty_kg=1000, vehicle_no="TS-07-UB-5501", notes="Part shipment received (1,000kg). Balance 2,000kg pending",
        lot_number="LOT-DECC-30W-PART-006", location_code="RAW", user_id=users["store"].id
    )
    rec6.created_at = _dt(date(2026, 9, 20), 15, 0)
    db.commit()

    # PO 7: Himalayan Yarn - IN TRANSIT (October 2: ordered 1,500 kg YRN-40-C, confirmed, 0 received)
    po7 = create_po(
        db, supplier_id=suppliers[2].id, order_date=date(2026, 10, 2),
        expected_date=date(2026, 10, 25),
        lines=[{"item_id": yarn_items[2].id, "qty_kg": 1500, "rate_per_kg_paise": 31500}],
        notes="In transit from Ludhiana mill. Expected arrival Oct 25", user_id=users["store"].id
    )
    po7.created_at = _dt(date(2026, 10, 2), 10, 0)
    confirm_po(db, po7.id, user_id=users["admin"].id)
    db.commit()

    # PO 8: Vardhman Textiles - CANCELLED (October 5: draft -> confirmed -> cancelled)
    po8 = create_po(
        db, supplier_id=suppliers[3].id, order_date=date(2026, 10, 5),
        expected_date=date(2026, 10, 28),
        lines=[{"item_id": yarn_items[3].id, "qty_kg": 2000, "rate_per_kg_paise": 24500}],
        notes="Cancelled due to renegotiated delivery lead time", user_id=users["store"].id
    )
    po8.created_at = _dt(date(2026, 10, 5), 14, 0)
    confirm_po(db, po8.id, user_id=users["admin"].id)
    cancel_po(db, po8.id, user_id=users["admin"].id)
    db.commit()

    print("[✓] Purchase Orders generated (5 fully received, 1 partial, 1 in-transit, 1 cancelled).")

    # ── 11. SALES ORDERS ACROSS ALL 14 LIFECYCLE STAGES ──────────────────────
    print("[*] Generating 25 Sales Orders across all 14 lifecycle stages using real services...")

    created_orders = []

    def _make_rolls_and_flow(order, fabric, yarn, machine, roll_specs, dispatch_date=None, payment_pct=0.0, is_late=False):
        """Helper to advance run, issue yarn, create rolls, inspect, store, dispatch, and pay."""
        # 1. Start run
        run = start_run(db, machine_id=machine.id, order_id=order.id, item_id=fabric.id, user_id=users["floor_supervisor"].id)
        run.created_at = _dt(order.order_date + timedelta(days=2), 8, 0)
        run.started_at = run.created_at
        db.flush()

        # 2. Advance through preparatory stages to final stage
        from mill.models.production import MACHINE_STAGES
        stages = MACHINE_STAGES.get(machine.machine_type, ["warping", "weaving", "inspection"])
        run.current_stage = stages[-1]
        db.flush()

        # 3. Issue yarn to run
        total_m = sum(r["length_cm"] / 100 for r in roll_specs)
        yarn_needed_g = int(total_m * float(fabric.yarn_kg_per_meter) * 1000)
        if yarn_needed_g > 0:
            issue_yarn_to_run(db, run_id=run.id, qty_g=yarn_needed_g, item_id=yarn.id, user_id=users["floor_supervisor"].id)

        # 4. Create rolls
        created_roll_objs = []
        for r_spec in roll_specs:
            roll = create_roll(db, run_id=run.id, length_cm=r_spec["length_cm"], weight_g=r_spec.get("weight_g"), user_id=users["floor_supervisor"].id)
            roll.created_at = _dt(order.order_date + timedelta(days=5), 14, 0)
            created_roll_objs.append((roll, r_spec))
        db.flush()

        # 5. Inspect and Move to store according to specs
        store_roll_ids = []
        for roll, r_spec in created_roll_objs:
            verdict = r_spec.get("verdict")
            if verdict:
                inspect_roll(db, roll_id=roll.id, verdict=verdict, grade=r_spec.get("grade"), note=r_spec.get("note"), user_id=users["qc"].id)
                roll.inspected_at = _dt(order.order_date + timedelta(days=7), 16, 0)
                if r_spec.get("defect"):
                    d = r_spec["defect"]
                    record_defect(db, roll_id=roll.id, defect_type=d["type"], severity=d["severity"], location_m=d.get("loc_m"), notes=d.get("notes"), user_id=users["qc"].id)

                if verdict == "pass" and r_spec.get("in_store", True):
                    move_to_store(db, roll_id=roll.id, user_id=users["store"].id)
                    store_roll_ids.append(roll.id)
        db.flush()

        # 6. Dispatch if requested
        disp_obj = None
        inv_obj = None
        if dispatch_date and store_roll_ids:
            num_to_dispatch = r_spec.get("dispatch_count", len(store_roll_ids))
            to_dispatch_ids = store_roll_ids[:num_to_dispatch]
            if to_dispatch_ids:
                disp_obj, inv_obj, _ = dispatch_rolls(
                    db, roll_ids=to_dispatch_ids, dispatch_date=dispatch_date,
                    order_id=order.id, vehicle_no="GJ-05-TR-8822",
                    notes="Dispatched to buyer warehouse", user_id=users["store"].id
                )
                disp_obj.created_at = _dt(dispatch_date, 11, 0)
                inv_obj.created_at = disp_obj.created_at
                db.flush()

                # 7. Payment if requested
                if payment_pct > 0 and inv_obj:
                    inv_total = get_invoice_total_paise(inv_obj)
                    pay_amt = int(inv_total * payment_pct)
                    pay_date = dispatch_date + timedelta(days=10)
                    p = Payment(
                        invoice_id=inv_obj.id,
                        paid_date=pay_date,
                        amount_paise=pay_amt,
                        method="neft",
                        reference=f"NEFT-{inv_obj.ref}",
                        notes=f"Settlement ({int(payment_pct*100)}%) via RTGS",
                        created_at=_dt(pay_date, 15, 0),
                    )
                    db.add(p)
                    db.flush()
                    if pay_amt >= inv_total:
                        inv_obj.status = "paid"
                    db.flush()

        calculate_order_progress(db, order.id)
        db.commit()
        return run

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 14: FULLY PAID (Orders 1, 2, 3) - Dispatched, invoiced, 100% paid
    # ─────────────────────────────────────────────────────────────────────────
    # Order 1: Buyer 1 (Sunrise Garments) - 1,000m Poplin White (July 10 -> August 15)
    o1 = create_order(
        db, buyer_id=buyers[0].id, order_date=date(2026, 7, 10), delivery_date=date(2026, 8, 15),
        lines=[{"item_id": fabric_items[0].id, "qty_meters": 1000, "rate_per_meter_paise": 14000}],
        tolerance_pct=5.0, notes="Export batch for Middle East partner", user_id=users["admin"].id
    )
    o1.created_at = _dt(date(2026, 7, 10), 10, 0)
    confirm_order(db, o1.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o1, fabric_items[0], yarn_items[0], machines[0],
        roll_specs=[{"length_cm": 10000, "weight_g": 18000, "verdict": "pass", "grade": "A"} for _ in range(10)],
        dispatch_date=date(2026, 8, 10), payment_pct=1.0
    )
    created_orders.append(o1)

    # Order 2: Buyer 2 (Metro Fashion House) - 800m Twill Blue (July 15 -> August 20)
    o2 = create_order(
        db, buyer_id=buyers[1].id, order_date=date(2026, 7, 15), delivery_date=date(2026, 8, 20),
        lines=[{"item_id": fabric_items[1].id, "qty_meters": 800, "rate_per_meter_paise": 18500}],
        tolerance_pct=5.0, notes="Autumn denim shirting line", user_id=users["admin"].id
    )
    o2.created_at = _dt(date(2026, 7, 15), 11, 0)
    confirm_order(db, o2.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o2, fabric_items[1], yarn_items[1], machines[1],
        roll_specs=[{"length_cm": 10000, "weight_g": 24000, "verdict": "pass", "grade": "A"} for _ in range(8)],
        dispatch_date=date(2026, 8, 16), payment_pct=1.0
    )
    created_orders.append(o2)

    # Order 3: Buyer 3 (Textile Exports Corp) - 1,200m Slub Natural (July 20 -> August 25)
    o3 = create_order(
        db, buyer_id=buyers[2].id, order_date=date(2026, 7, 20), delivery_date=date(2026, 8, 25),
        lines=[{"item_id": fabric_items[2].id, "qty_meters": 1200, "rate_per_meter_paise": 16000}],
        tolerance_pct=5.0, notes="Organic certified natural slub", user_id=users["admin"].id
    )
    o3.created_at = _dt(date(2026, 7, 20), 14, 0)
    confirm_order(db, o3.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o3, fabric_items[2], yarn_items[2], machines[2],
        roll_specs=[{"length_cm": 10000, "weight_g": 21000, "verdict": "pass", "grade": "A"} for _ in range(12)],
        dispatch_date=date(2026, 8, 22), payment_pct=1.0
    )
    created_orders.append(o3)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 13: PARTLY PAID (Orders 4, 5) - Dispatched, invoiced, part paid
    # ─────────────────────────────────────────────────────────────────────────
    # Order 4: Buyer 4 (Apex Apparels) - 1,000m Satin Maroon (August 5 -> September 10)
    o4 = create_order(
        db, buyer_id=buyers[3].id, order_date=date(2026, 8, 5), delivery_date=date(2026, 9, 10),
        lines=[{"item_id": fabric_items[3].id, "qty_meters": 1000, "rate_per_meter_paise": 21000}],
        tolerance_pct=5.0, notes="Festive festive satin weave", user_id=users["admin"].id
    )
    o4.created_at = _dt(date(2026, 8, 5), 10, 0)
    confirm_order(db, o4.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o4, fabric_items[3], yarn_items[3], machines[0],
        roll_specs=[{"length_cm": 10000, "weight_g": 25000, "verdict": "pass", "grade": "A"} for _ in range(10)],
        dispatch_date=date(2026, 9, 5), payment_pct=0.50
    )
    created_orders.append(o4)

    # Order 5: Buyer 5 (Heritage Handlooms) - 600m Poplin White (August 10 -> September 15)
    o5 = create_order(
        db, buyer_id=buyers[4].id, order_date=date(2026, 8, 10), delivery_date=date(2026, 9, 15),
        lines=[{"item_id": fabric_items[0].id, "qty_meters": 600, "rate_per_meter_paise": 14200}],
        tolerance_pct=5.0, notes="Heritage collection shirting", user_id=users["admin"].id
    )
    o5.created_at = _dt(date(2026, 8, 10), 11, 30)
    confirm_order(db, o5.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o5, fabric_items[0], yarn_items[0], machines[1],
        roll_specs=[{"length_cm": 10000, "weight_g": 18000, "verdict": "pass", "grade": "B"} for _ in range(6)],
        dispatch_date=date(2026, 9, 12), payment_pct=0.40
    )
    created_orders.append(o5)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 12: FULLY DISPATCHED & UNPAID / OVERDUE (Orders 6, 7)
    # ─────────────────────────────────────────────────────────────────────────
    # Order 6: Buyer 6 (Global Fashion Sourcing) - 1,500m Twill Blue (August 12 -> September 15)
    o6 = create_order(
        db, buyer_id=buyers[5].id, order_date=date(2026, 8, 12), delivery_date=date(2026, 9, 15),
        lines=[{"item_id": fabric_items[1].id, "qty_meters": 1500, "rate_per_meter_paise": 18000}],
        tolerance_pct=5.0, notes="Institutional hospital uniform contract", user_id=users["admin"].id
    )
    o6.created_at = _dt(date(2026, 8, 12), 10, 0)
    confirm_order(db, o6.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o6, fabric_items[1], yarn_items[1], machines[2],
        roll_specs=[{"length_cm": 10000, "weight_g": 24000, "verdict": "pass", "grade": "A"} for _ in range(15)],
        dispatch_date=date(2026, 9, 10), payment_pct=0.0
    )
    created_orders.append(o6)

    # Order 7: Buyer 7 (Royal Silk & Cottons) - 900m Slub Natural (August 18 -> September 20)
    o7 = create_order(
        db, buyer_id=buyers[6].id, order_date=date(2026, 8, 18), delivery_date=date(2026, 9, 20),
        lines=[{"item_id": fabric_items[2].id, "qty_meters": 900, "rate_per_meter_paise": 16500}],
        tolerance_pct=5.0, notes="Boutique order Varanasi", user_id=users["admin"].id
    )
    o7.created_at = _dt(date(2026, 8, 18), 15, 0)
    confirm_order(db, o7.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o7, fabric_items[2], yarn_items[2], machines[0],
        roll_specs=[{"length_cm": 10000, "weight_g": 21000, "verdict": "pass", "grade": "A"} for _ in range(9)],
        dispatch_date=date(2026, 9, 18), payment_pct=0.0
    )
    created_orders.append(o7)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 11: FULLY DISPATCHED BUT LATE (Orders 8, 9)
    # ─────────────────────────────────────────────────────────────────────────
    # Order 8: Buyer 8 (Zenith Apparel Works) - 700m Poplin White (deliv Sept 15 -> dispatched Sept 28 LATE)
    o8 = create_order(
        db, buyer_id=buyers[7].id, order_date=date(2026, 8, 20), delivery_date=date(2026, 9, 15),
        lines=[{"item_id": fabric_items[0].id, "qty_meters": 700, "rate_per_meter_paise": 14500}],
        tolerance_pct=5.0, notes="Tirupur apparel contract - delayed dispatch", user_id=users["admin"].id
    )
    o8.created_at = _dt(date(2026, 8, 20), 10, 0)
    confirm_order(db, o8.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o8, fabric_items[0], yarn_items[0], machines[1],
        roll_specs=[{"length_cm": 10000, "weight_g": 18000, "verdict": "pass", "grade": "A"} for _ in range(7)],
        dispatch_date=date(2026, 9, 28), payment_pct=0.0, is_late=True
    )
    created_orders.append(o8)

    # Order 9: Buyer 9 (Continental Weavers) - 1,000m Twill Blue (deliv Sept 20 -> dispatched Oct 2 LATE)
    o9 = create_order(
        db, buyer_id=buyers[8].id, order_date=date(2026, 8, 25), delivery_date=date(2026, 9, 20),
        lines=[{"item_id": fabric_items[1].id, "qty_meters": 1000, "rate_per_meter_paise": 18200}],
        tolerance_pct=5.0, notes="Ahmedabad export contract", user_id=users["admin"].id
    )
    o9.created_at = _dt(date(2026, 8, 25), 11, 0)
    confirm_order(db, o9.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o9, fabric_items[1], yarn_items[1], machines[2],
        roll_specs=[{"length_cm": 10000, "weight_g": 24000, "verdict": "pass", "grade": "A"} for _ in range(10)],
        dispatch_date=date(2026, 10, 2), payment_pct=0.0, is_late=True
    )
    created_orders.append(o9)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 10: PART DISPATCHED (Orders 10, 11) - Some rolls dispatched, rest in FIN store
    # ─────────────────────────────────────────────────────────────────────────
    # Order 10: Buyer 10 (Elegance Ethnic Wear) - 1,000m Poplin White (400m dispatched, 600m in store)
    o10 = create_order(
        db, buyer_id=buyers[9].id, order_date=date(2026, 9, 1), delivery_date=date(2026, 10, 20),
        lines=[{"item_id": fabric_items[0].id, "qty_meters": 1000, "rate_per_meter_paise": 14000}],
        tolerance_pct=5.0, notes="Part dispatch scheduled", user_id=users["admin"].id
    )
    o10.created_at = _dt(date(2026, 9, 1), 10, 0)
    confirm_order(db, o10.id, user_id=users["admin"].id)
    r10_run = start_run(db, machine_id=machines[0].id, order_id=o10.id, item_id=fabric_items[0].id, user_id=users["floor_supervisor"].id)
    r10_run.current_stage = "inspection"
    issue_yarn_to_run(db, run_id=r10_run.id, qty_g=180000, item_id=yarn_items[0].id, user_id=users["floor_supervisor"].id)
    r10_rolls = [create_roll(db, run_id=r10_run.id, length_cm=10000, weight_g=18000, user_id=users["floor_supervisor"].id) for _ in range(10)]
    for r in r10_rolls:
        inspect_roll(db, roll_id=r.id, verdict="pass", grade="A", note="Good density", user_id=users["qc"].id)
        move_to_store(db, roll_id=r.id, user_id=users["store"].id)
    db.flush()
    # Dispatch first 4 rolls (400m)
    dispatch_rolls(db, roll_ids=[r.id for r in r10_rolls[:4]], dispatch_date=date(2026, 9, 25), order_id=o10.id, user_id=users["store"].id)
    calculate_order_progress(db, o10.id)
    db.commit()
    created_orders.append(o10)

    # Order 11: Buyer 11 (Premier Garment Makers) - 800m Satin Maroon (300m dispatched, 500m in store)
    o11 = create_order(
        db, buyer_id=buyers[10].id, order_date=date(2026, 9, 5), delivery_date=date(2026, 10, 25),
        lines=[{"item_id": fabric_items[3].id, "qty_meters": 800, "rate_per_meter_paise": 20500}],
        tolerance_pct=5.0, notes="Pune branch initial delivery", user_id=users["admin"].id
    )
    o11.created_at = _dt(date(2026, 9, 5), 11, 0)
    confirm_order(db, o11.id, user_id=users["admin"].id)
    r11_run = start_run(db, machine_id=machines[1].id, order_id=o11.id, item_id=fabric_items[3].id, user_id=users["floor_supervisor"].id)
    r11_run.current_stage = "inspection"
    issue_yarn_to_run(db, run_id=r11_run.id, qty_g=200000, item_id=yarn_items[3].id, user_id=users["floor_supervisor"].id)
    r11_rolls = [create_roll(db, run_id=r11_run.id, length_cm=10000, weight_g=25000, user_id=users["floor_supervisor"].id) for _ in range(8)]
    for r in r11_rolls:
        inspect_roll(db, roll_id=r.id, verdict="pass", grade="A", note="Rich sheen", user_id=users["qc"].id)
        move_to_store(db, roll_id=r.id, user_id=users["store"].id)
    db.flush()
    dispatch_rolls(db, roll_ids=[r.id for r in r11_rolls[:3]], dispatch_date=date(2026, 10, 1), order_id=o11.id, user_id=users["store"].id)
    calculate_order_progress(db, o11.id)
    db.commit()
    created_orders.append(o11)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 9: FULLY IN STORE WAITING FOR DISPATCH (Orders 12, 13)
    # ─────────────────────────────────────────────────────────────────────────
    # Order 12: Buyer 12 (Vistara Clothiers) - 600m Twill Blue (6 rolls all pass & in store)
    o12 = create_order(
        db, buyer_id=buyers[11].id, order_date=date(2026, 9, 10), delivery_date=date(2026, 10, 22),
        lines=[{"item_id": fabric_items[1].id, "qty_meters": 600, "rate_per_meter_paise": 18400}],
        tolerance_pct=5.0, notes="Awaiting buyer container truck pickup", user_id=users["admin"].id
    )
    o12.created_at = _dt(date(2026, 9, 10), 10, 0)
    confirm_order(db, o12.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o12, fabric_items[1], yarn_items[1], machines[2],
        roll_specs=[{"length_cm": 10000, "weight_g": 24000, "verdict": "pass", "grade": "A"} for _ in range(6)],
        dispatch_date=None
    )
    created_orders.append(o12)

    # Order 13: Buyer 1 (Sunrise Garments) - 500m Slub Natural (5 rolls all pass & in store)
    o13 = create_order(
        db, buyer_id=buyers[0].id, order_date=date(2026, 9, 12), delivery_date=date(2026, 10, 25),
        lines=[{"item_id": fabric_items[2].id, "qty_meters": 500, "rate_per_meter_paise": 16200}],
        tolerance_pct=5.0, notes="Packaging & palletising complete in FIN store", user_id=users["admin"].id
    )
    o13.created_at = _dt(date(2026, 9, 12), 14, 0)
    confirm_order(db, o13.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o13, fabric_items[2], yarn_items[2], machines[0],
        roll_specs=[{"length_cm": 10000, "weight_g": 21000, "verdict": "pass", "grade": "A"} for _ in range(5)],
        dispatch_date=None
    )
    created_orders.append(o13)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 8: REWORK LEFT WAITING (Order 14)
    # ─────────────────────────────────────────────────────────────────────────
    # Order 14: Buyer 2 (Metro Fashion House) - 400m Poplin White (1 pass in store, 3 rework waiting)
    o14 = create_order(
        db, buyer_id=buyers[1].id, order_date=date(2026, 9, 15), delivery_date=date(2026, 10, 28),
        lines=[{"item_id": fabric_items[0].id, "qty_meters": 400, "rate_per_meter_paise": 14100}],
        tolerance_pct=5.0, notes="Tension irregularity during weaving run", user_id=users["admin"].id
    )
    o14.created_at = _dt(date(2026, 9, 15), 9, 30)
    confirm_order(db, o14.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o14, fabric_items[0], yarn_items[0], machines[1],
        roll_specs=[
            {"length_cm": 10000, "weight_g": 18000, "verdict": "pass", "grade": "B"},
            {"length_cm": 10000, "weight_g": 18000, "verdict": "rework", "note": "Uneven edge tension, needs re-rolling"},
            {"length_cm": 10000, "weight_g": 18000, "verdict": "rework", "note": "Weft slackness at 50m mark"},
            {"length_cm": 10000, "weight_g": 18000, "verdict": "rework", "note": "Selvedge fuzziness, shearing pass required"},
        ],
        dispatch_date=None
    )
    created_orders.append(o14)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 7: IN INSPECTION WITH MIX OF RESULTS (Orders 15, 16)
    # ─────────────────────────────────────────────────────────────────────────
    # Order 15: Buyer 3 (Textile Exports Corp) - 600m Twill Blue (2 pass, 1 rework, 1 reject + defects, 2 awaiting_qc)
    o15 = create_order(
        db, buyer_id=buyers[2].id, order_date=date(2026, 9, 18), delivery_date=date(2026, 11, 2),
        lines=[{"item_id": fabric_items[1].id, "qty_meters": 600, "rate_per_meter_paise": 18600}],
        tolerance_pct=5.0, notes="Active on QC tables", user_id=users["admin"].id
    )
    o15.created_at = _dt(date(2026, 9, 18), 10, 0)
    confirm_order(db, o15.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o15, fabric_items[1], yarn_items[1], machines[2],
        roll_specs=[
            {"length_cm": 10000, "weight_g": 24000, "verdict": "pass", "grade": "A"},
            {"length_cm": 10000, "weight_g": 24000, "verdict": "pass", "grade": "B"},
            {
                "length_cm": 10000, "weight_g": 24000, "verdict": "rework", "note": "Slub detected at 45m",
                "defect": {"type": "slub", "severity": "medium", "loc_m": 45, "notes": "Thick weft slug"}
            },
            {
                "length_cm": 10000, "weight_g": 24000, "verdict": "reject", "note": "Oil stain on 15m continuous stretch",
                "defect": {"type": "stain", "severity": "critical", "loc_m": 12, "notes": "Loom gearbox oil leak"}
            },
            {"length_cm": 10000, "weight_g": 24000},  # awaiting_qc
            {"length_cm": 10000, "weight_g": 24000},  # awaiting_qc
        ],
        dispatch_date=None
    )
    created_orders.append(o15)

    # Order 16: Buyer 4 (Apex Apparels) - 500m Satin Maroon (1 pass, 1 reject, 1 rework, 2 awaiting_qc)
    o16 = create_order(
        db, buyer_id=buyers[3].id, order_date=date(2026, 9, 20), delivery_date=date(2026, 11, 5),
        lines=[{"item_id": fabric_items[3].id, "qty_meters": 500, "rate_per_meter_paise": 20800}],
        tolerance_pct=5.0, notes="QC batch review", user_id=users["admin"].id
    )
    o16.created_at = _dt(date(2026, 9, 20), 11, 0)
    confirm_order(db, o16.id, user_id=users["admin"].id)
    _make_rolls_and_flow(
        o16, fabric_items[3], yarn_items[3], machines[0],
        roll_specs=[
            {"length_cm": 10000, "weight_g": 25000, "verdict": "pass", "grade": "A"},
            {"length_cm": 10000, "weight_g": 25000, "verdict": "reject", "note": "Tear across warp at 20m"},
            {"length_cm": 10000, "weight_g": 25000, "verdict": "rework", "note": "Warp streak minor"},
            {"length_cm": 10000, "weight_g": 25000},
            {"length_cm": 10000, "weight_g": 25000},
        ],
        dispatch_date=None
    )
    created_orders.append(o16)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 6: MID-WEAVING (Orders 17, 18) - Run active, yarn issued, stage=weaving, 0 rolls yet
    # ─────────────────────────────────────────────────────────────────────────
    # Order 17: Buyer 5 (Heritage Handlooms) - 1,000m Slub Natural
    o17 = create_order(
        db, buyer_id=buyers[4].id, order_date=date(2026, 9, 25), delivery_date=date(2026, 11, 10),
        lines=[{"item_id": fabric_items[2].id, "qty_meters": 1000, "rate_per_meter_paise": 16400}],
        tolerance_pct=5.0, notes="Active on Rapier Loom WL-02", user_id=users["admin"].id
    )
    o17.created_at = _dt(date(2026, 9, 25), 10, 0)
    confirm_order(db, o17.id, user_id=users["admin"].id)
    r17_run = start_run(db, machine_id=machines[1].id, order_id=o17.id, item_id=fabric_items[2].id, user_id=users["floor_supervisor"].id)
    r17_run.current_stage = "weaving"
    issue_yarn_to_run(db, run_id=r17_run.id, qty_g=210000, item_id=yarn_items[2].id, user_id=users["floor_supervisor"].id)
    calculate_order_progress(db, o17.id)
    db.commit()
    created_orders.append(o17)

    # Order 18: Buyer 6 (Global Fashion Sourcing) - 1,200m Poplin White
    o18 = create_order(
        db, buyer_id=buyers[5].id, order_date=date(2026, 9, 28), delivery_date=date(2026, 11, 12),
        lines=[{"item_id": fabric_items[0].id, "qty_meters": 1200, "rate_per_meter_paise": 14100}],
        tolerance_pct=5.0, notes="Running high-speed Tsudakoma Air-Jet WL-01", user_id=users["admin"].id
    )
    o18.created_at = _dt(date(2026, 9, 28), 11, 0)
    confirm_order(db, o18.id, user_id=users["admin"].id)
    r18_run = start_run(db, machine_id=machines[0].id, order_id=o18.id, item_id=fabric_items[0].id, user_id=users["floor_supervisor"].id)
    r18_run.current_stage = "weaving"
    issue_yarn_to_run(db, run_id=r18_run.id, qty_g=216000, item_id=yarn_items[0].id, user_id=users["floor_supervisor"].id)
    calculate_order_progress(db, o18.id)
    db.commit()
    created_orders.append(o18)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 5: JUST STARTED IN EARLY STAGES (Orders 19, 20) - Stage=warping
    # ─────────────────────────────────────────────────────────────────────────
    # Order 19: Buyer 7 (Royal Silk & Cottons) - 800m Twill Blue
    o19 = create_order(
        db, buyer_id=buyers[6].id, order_date=date(2026, 10, 1), delivery_date=date(2026, 11, 18),
        lines=[{"item_id": fabric_items[1].id, "qty_meters": 800, "rate_per_meter_paise": 18300}],
        tolerance_pct=5.0, notes="Beam warping in progress", user_id=users["admin"].id
    )
    o19.created_at = _dt(date(2026, 10, 1), 9, 0)
    confirm_order(db, o19.id, user_id=users["admin"].id)
    r19_run = start_run(db, machine_id=machines[2].id, order_id=o19.id, item_id=fabric_items[1].id, user_id=users["floor_supervisor"].id)
    r19_run.current_stage = "warping"
    issue_yarn_to_run(db, run_id=r19_run.id, qty_g=192000, item_id=yarn_items[1].id, user_id=users["floor_supervisor"].id)
    calculate_order_progress(db, o19.id)
    db.commit()
    created_orders.append(o19)

    # Order 20: Buyer 8 (Zenith Apparel Works) - 600m Satin Maroon
    o20 = create_order(
        db, buyer_id=buyers[7].id, order_date=date(2026, 10, 2), delivery_date=date(2026, 11, 20),
        lines=[{"item_id": fabric_items[3].id, "qty_meters": 600, "rate_per_meter_paise": 20900}],
        tolerance_pct=5.0, notes="Creel loaded in preparatory shed", user_id=users["admin"].id
    )
    o20.created_at = _dt(date(2026, 10, 2), 10, 30)
    confirm_order(db, o20.id, user_id=users["admin"].id)
    r20_run = start_run(db, machine_id=machines[1].id, order_id=o20.id, item_id=fabric_items[3].id, user_id=users["floor_supervisor"].id)
    r20_run.current_stage = "warping"
    issue_yarn_to_run(db, run_id=r20_run.id, qty_g=150000, item_id=yarn_items[3].id, user_id=users["floor_supervisor"].id)
    calculate_order_progress(db, o20.id)
    db.commit()
    created_orders.append(o20)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 4: CONFIRMED AND WAITING (Orders 21, 22) - Confirmed, 0 runs started
    # ─────────────────────────────────────────────────────────────────────────
    # Order 21: Buyer 9 (Continental Weavers) - 700m Poplin White
    o21 = create_order(
        db, buyer_id=buyers[8].id, order_date=date(2026, 10, 5), delivery_date=date(2026, 11, 25),
        lines=[{"item_id": fabric_items[0].id, "qty_meters": 700, "rate_per_meter_paise": 14200}],
        tolerance_pct=5.0, notes="Confirmed, queued for loom scheduling", user_id=users["admin"].id
    )
    o21.created_at = _dt(date(2026, 10, 5), 11, 0)
    confirm_order(db, o21.id, user_id=users["admin"].id)
    calculate_order_progress(db, o21.id)
    db.commit()
    created_orders.append(o21)

    # Order 22: Buyer 10 (Elegance Ethnic Wear) - 900m Slub Natural
    o22 = create_order(
        db, buyer_id=buyers[9].id, order_date=date(2026, 10, 6), delivery_date=date(2026, 11, 28),
        lines=[{"item_id": fabric_items[2].id, "qty_meters": 900, "rate_per_meter_paise": 16300}],
        tolerance_pct=5.0, notes="Confirmed, awaiting yarn allocation confirmation", user_id=users["admin"].id
    )
    o22.created_at = _dt(date(2026, 10, 6), 14, 0)
    confirm_order(db, o22.id, user_id=users["admin"].id)
    calculate_order_progress(db, o22.id)
    db.commit()
    created_orders.append(o22)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 3: CANCELLED (Order 23)
    # ─────────────────────────────────────────────────────────────────────────
    # Order 23: Buyer 11 (Premier Garment Makers) - 500m Twill Blue
    o23 = create_order(
        db, buyer_id=buyers[10].id, order_date=date(2026, 9, 14), delivery_date=date(2026, 10, 10),
        lines=[{"item_id": fabric_items[1].id, "qty_meters": 500, "rate_per_meter_paise": 18200}],
        tolerance_pct=5.0, notes="Buyer changed pattern specification", user_id=users["admin"].id
    )
    o23.created_at = _dt(date(2026, 9, 14), 10, 0)
    confirm_order(db, o23.id, user_id=users["admin"].id)
    cancel_order(db, o23.id, user_id=users["admin"].id)
    db.commit()
    created_orders.append(o23)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 2: DRAFT AWAITING CONFIRMATION (Order 24)
    # ─────────────────────────────────────────────────────────────────────────
    # Order 24: Buyer 12 (Vistara Clothiers) - 800m Poplin White
    o24 = create_order(
        db, buyer_id=buyers[11].id, order_date=date(2026, 10, 8), delivery_date=date(2026, 12, 1),
        lines=[{"item_id": fabric_items[0].id, "qty_meters": 800, "rate_per_meter_paise": 14300}],
        tolerance_pct=5.0, notes="Draft quote sent to buyer, awaiting PO signoff", user_id=users["admin"].id
    )
    o24.created_at = _dt(date(2026, 10, 8), 15, 0)
    calculate_order_progress(db, o24.id)
    db.commit()
    created_orders.append(o24)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 1: DRAFT WITH REFUSED CONFIRMATION FOR LACK OF YARN (Order 25)
    # ─────────────────────────────────────────────────────────────────────────
    # Order 25: Buyer 1 (Sunrise Garments) - 200,000m Twill Blue requiring 48,000 kg yarn (far exceeds stock)
    o25 = create_order(
        db, buyer_id=buyers[0].id, order_date=date(2026, 10, 9), delivery_date=date(2026, 12, 15),
        lines=[{"item_id": fabric_items[1].id, "qty_meters": 200000, "rate_per_meter_paise": 17800}],
        tolerance_pct=5.0, notes="Mega enquiry from overseas buyer", user_id=users["admin"].id
    )
    o25.created_at = _dt(date(2026, 10, 9), 11, 0)
    try:
        confirm_order(db, o25.id, user_id=users["admin"].id)
    except DomainError as err:
        o25.notes = f"Confirmation refused due to insufficient raw material: {err.message}"
    calculate_order_progress(db, o25.id)
    db.commit()
    created_orders.append(o25)

    print(f"[✓] Exactly {len(created_orders)} Sales Orders created across all 14 lifecycle branches.")

    # ── 12. WORKFORCE ATTENDANCE & WAGE RUNS ──────────────────────────────────
    print("[*] Generating Worker Attendance entries and Wage Runs across July -> October...")
    # Add daily attendance for workers across July, August, September, October
    start_cal = date(2026, 7, 1)
    end_cal = date(2026, 10, 10)
    curr = start_cal
    shifts = ["morning", "evening", "night"]
    day_count = 0

    while curr <= end_cal:
        if curr.weekday() != 6: # Skip Sundays
            for idx, w in enumerate(workers):
                shift = shifts[(day_count + idx) % 3]
                try:
                    entry = create_entry(
                        db, worker_id=w.id, work_date=curr, shift=shift,
                        minutes_worked=480 if w.wage_basis == "hourly" else None,
                        pieces_produced=8 if w.wage_basis == "piece_rate" else None,
                        notes=f"Regular shift ({shift})", created_by=users["floor_supervisor"].id
                    )
                    # Approve past entries (before October)
                    if curr < date(2026, 10, 1):
                        approve_entry(db, entry_id=entry.id, approved_by=users["owner"].id)
                except ValueError:
                    pass
            day_count += 1
        curr += timedelta(days=1)
    db.commit()

    # Create monthly wage runs for July, August, September (finalised) and October (draft)
    wage_specs = [
        ("July 2026 Monthly Payroll", date(2026, 7, 1), date(2026, 7, 31), "finalised", 285000_00),
        ("August 2026 Monthly Payroll", date(2026, 8, 1), date(2026, 8, 31), "finalised", 292000_00),
        ("September 2026 Monthly Payroll", date(2026, 9, 1), date(2026, 9, 30), "finalised", 298000_00),
        ("October 2026 Payroll (M-T-D)", date(2026, 10, 1), date(2026, 10, 10), "draft", 96000_00),
    ]
    for wname, pstart, pend, status, wages_paise in wage_specs:
        wr = db.scalar(select(WageRun).where(WageRun.period_start == pstart, WageRun.period_end == pend))
        if not wr:
            wr = WageRun(
                period_start=pstart, period_end=pend, status=status,
                created_by_id=users["owner"].id,
                finalised_by_id=users["owner"].id if status == "finalised" else None,
                created_at=_dt(pend, 18, 0),
                finalised_at=_dt(pend, 19, 0) if status == "finalised" else None,
            )
            db.add(wr)
            db.flush()
            for w in workers:
                db.add(WageRunLine(
                    wage_run_id=wr.id, worker_id=w.id,
                    total_hours_minutes=9600,
                    total_pieces=160,
                    applied_rate_paise=w.hourly_rate_paise or w.piece_rate_paise,
                    net_wage_paise=wages_paise // len(workers),
                ))
    db.commit()
    print("[✓] Attendance and Payroll records generated.")

    print("=" * 64)
    print("  SCENARIO LOAD COMPLETE")
    print(f"  Sales Orders    : {len(created_orders)}")
    print(f"  Purchase Orders : 8 (5 received, 1 partial, 1 in transit, 1 cancelled)")
    print(f"  Buyers          : {len(buyers)} (across Surat, Mumbai, Delhi, etc.)")
    print(f"  Suppliers       : {len(suppliers)}")
    print(f"  Fabric Rolls    : {db.scalar(select(func.count(Roll.id)))}")
    print(f"  Invoices Raised : {db.scalar(select(func.count(Invoice.id)))}")
    print(f"  Stock Movements : {db.scalar(select(func.count(StockMove.id)))}")
    print("=" * 64)

    return {
        "status": "success",
        "orders_count": len(created_orders),
        "rolls_count": db.scalar(select(func.count(Roll.id))),
        "invoices_count": db.scalar(select(func.count(Invoice.id))),
        "stock_moves_count": db.scalar(select(func.count(StockMove.id))),
    }
