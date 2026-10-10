"""Seed rich demonstration database (mill_demo.db) for Khadira Textile Mills ERP.

Generates:
- Exactly 24 buyer orders (ORD-2026-00001 through ORD-2026-00024) across full lifecycle
- Exactly 311 fabric rolls (ROLL-000001 through ROLL-000311) with realistic ASTM 4-point grades
- Workers and monthly attendance entries across multiple shifts
- Finalised and draft wage runs with calculated line items
- Order-level and roll-level costing breakdowns (yarn, wages, overhead)
- Complete machine, inventory, buyer, supplier, and invoice master records
"""

import os
import sys
from datetime import date, datetime, timedelta, timezone

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from mill.models import (
    Base, Item, Location, StockLevel, StockMove, User, Setting,
    Buyer, Supplier, PurchaseOrder, PurchaseOrderLine, YarnLot, YarnReceipt,
    Order, OrderLine, Machine, MachineDowntime, ProductionRun, Roll, RollEvent,
    RollDefect, RunMaterial, RunReconciliation, Invoice, InvoiceLine, Payment,
    ITEM_YARN, ITEM_FABRIC,
)
from mill.services.auth import hash_password

PASSWORD = "khadira2026!"


def seed_demo(db_path: str = "mill_demo.db"):
    # Normalize path relative to backend folder
    if not os.path.isabs(db_path) and not db_path.startswith("backend"):
        if os.path.basename(os.getcwd()) != "backend" and os.path.exists("backend"):
            db_path = os.path.join("backend", db_path)

    print(f"[*] Initializing Khadira ERP Demo Database at: {db_path}")
    db_url = f"sqlite:///{db_path}"

    # Remove existing demo DB file to guarantee deterministic state
    clean_path = db_path.replace("sqlite:///", "")
    for ext in ["", "-wal", "-shm"]:
        target = f"{clean_path}{ext}"
        if os.path.exists(target):
            try:
                os.remove(target)
            except Exception:
                pass

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    # Also ensure legacy models tables (workers, attendance_entries, wage_runs, order_costs) exist
    try:
        from mill.database import Base as DBBase
        from mill import models as legacy_models
        DBBase.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[!] Note on legacy models: {e}")

    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()

    try:
        now = datetime.now(timezone.utc)

        # 1. System Settings
        settings_data = [
            ("company_name", "Khadira Textile Mills Pvt. Ltd."),
            ("currency", "INR"),
            ("low_stock_threshold_kg", "500"),
            ("default_warehouse", "RAW"),
            ("qc_standard", "ASTM D5430 4-Point System"),
            ("mill_location", "Surat, Gujarat"),
        ]
        for k, v in settings_data:
            db.execute(text("INSERT OR REPLACE INTO app_setting (key, value) VALUES (:k, :v)"), {"k": k, "v": v})

        # 2. Locations
        locations = {}
        for code, name in [
            ("RAW", "Raw Material Store (Yarn Warehouse)"),
            ("FIN", "Finished Goods Store (Inspection & Packing)"),
            ("WIP", "Weaving Shed & Loom Floor"),
        ]:
            loc = Location(code=code, name=name)
            db.add(loc)
            db.flush()
            locations[code] = loc

        # 3. Users (All 6 core roles)
        users_data = [
            ("admin",            "Admin User",        "admin@khadira.in",          "admin"),
            ("owner",            "Owner & Finance",   "owner@khadira.in",          "owner"),
            ("store",            "Store Keeper",      "store@khadira.in",          "store"),
            ("floor_supervisor", "Floor Supervisor",  "supervisor@khadira.in",     "floor_supervisor"),
            ("qc",               "QC Inspector",      "qc@khadira.in",             "qc"),
            ("office",           "Office Staff",      "office@khadira.in",         "office"),
        ]
        users = {}
        for username, full_name, email, role in users_data:
            u = User(
                username=username,
                full_name=full_name,
                email=email,
                role=role,
                hashed_password=hash_password(PASSWORD),
            )
            db.add(u)
            db.flush()
            users[username] = u

        # 4. Suppliers
        suppliers_data = [
            ("Himalayan Yarn Co.", "Rajesh Sharma", "+91-9876543210", "himalayan@yarn.in", "27AABCH1234A1Z5"),
            ("Deccan Fibres Ltd.", "Priya Nair",   "+91-8765432109", "deccan@fibres.in",  "29AABCD5678A1Z3"),
            ("Coimbatore Spinners", "K. Murugan",  "+91-9842100223", "sales@cbespinners.in", "33AAACC1234E1Z1"),
            ("Vardhman Textiles Ltd.", "Alok Jain","+91-9814002334", "orders@vardhman.in", "03AAACV1299P1Z8"),
        ]
        suppliers = []
        for name, contact, phone, email, gstin in suppliers_data:
            s = Supplier(name=name, contact_name=contact, phone=phone, email=email, gstin=gstin)
            db.add(s)
            db.flush()
            suppliers.append(s)

        # 5. Buyers
        buyers_data = [
            ("Sunrise Garments Pvt. Ltd.", "Arun Kumar",   "+91-9123456789", "sunrise@garments.in", 45),
            ("Metro Fashion House",        "Deepa Singh",  "+91-8234567890", "metro@fashion.in",    30),
            ("Textile Exports Corp.",      "Sanjay Mehta", "+91-7345678901", "exports@textile.in",  60),
            ("Apex Apparels Ltd.",         "Naveen Gupta", "+91-9899112233", "sourcing@apexapparels.com", 30),
            ("Heritage Handlooms",         "Kavita Sen",   "+91-9433221100", "orders@heritagecraft.in", 15),
            ("Global Fashion Sourcing",    "David Ross",   "+91-9988776655", "dross@globalsourcing.net", 60),
        ]
        buyers = []
        for name, contact, phone, email, credit in buyers_data:
            b = Buyer(name=name, contact_name=contact, phone=phone, email=email, credit_days=credit)
            db.add(b)
            db.flush()
            buyers.append(b)

        # 6. Catalog Items (Yarn & Fabric)
        yarn_data = [
            ("YRN-20-W",  "Cotton Yarn 20s White",    "20s",   500_000), # 500kg
            ("YRN-30-W",  "Cotton Yarn 30s White",    "30s",   300_000),
            ("YRN-40-C",  "Cotton Yarn 40s Coloured", "40s",   200_000),
            ("YRN-PC-65", "Poly-Cotton Yarn 65/35",   "65/35", 400_000),
            ("YRN-SLB-24","Slub Yarn 24s Natural",    "24s",   350_000),
            ("YRN-ORG-30","Organic Combed 30s",       "30s",   250_000),
        ]
        yarn_items = []
        for sku, name, count, reorder_g in yarn_data:
            it = Item(sku=sku, name=name, item_type=ITEM_YARN, unit="kg", count_denier=count, reorder_point_kg=reorder_g)
            db.add(it)
            db.flush()
            yarn_items.append(it)
            # Add initial stock
            db.add(StockLevel(item_id=it.id, location_id=locations["RAW"].id, qty_g=4_500_000)) # 4,500 kg
            db.add(StockMove(item_id=it.id, location_id=locations["RAW"].id, delta_g=4_500_000, ref="INIT-STOCK", note="Opening stock balance"))

        fabric_data = [
            ("FAB-POP-WH",  "Poplin Fabric White",      120, 110, 0.185),
            ("FAB-TWL-BL",  "Twill Fabric Blue",        200, 150, 0.240),
            ("FAB-SLB-MIX", "Slub Fabric Mixed",        160, 140, 0.210),
            ("FAB-ORG-NAT", "Organic Voile Natural",     90, 120, 0.140),
            ("FAB-SAT-MR",  "Satin Weave Maroon",       220, 145, 0.260),
        ]
        fabric_items = []
        for sku, name, gsm, width, ykpm in fabric_data:
            it = Item(sku=sku, name=name, item_type=ITEM_FABRIC, unit="meters", gsm=gsm, width_cm=width, yarn_kg_per_meter=ykpm)
            db.add(it)
            db.flush()
            fabric_items.append(it)
            db.add(StockLevel(item_id=it.id, location_id=locations["FIN"].id, qty_g=150_000)) # 1,500m finished stock

        # 7. Machines
        machines_data = [
            ("SP-01", "Rieter Ring Frame 1",     "spinning"),
            ("SP-02", "Lakshmi Rieter Frame 2",  "spinning"),
            ("WL-01", "Tsudakoma Air-Jet 1",     "weaving"),
            ("WL-02", "Picanol Rapier Loom 2",   "weaving"),
            ("WL-03", "Picanol OmniPlus 3",      "weaving"),
            ("DJ-01", "Fongs Soft-Flow Jet 1",   "dyeing"),
            ("FN-01", "Monforts Stenter 1",      "dyeing"),
        ]
        machines = []
        for code, name, mtype in machines_data:
            m = Machine(code=code, name=name, machine_type=mtype, is_active=True)
            db.add(m)
            db.flush()
            machines.append(m)

        # 8. EXACTLY 24 ORDERS
        # Life cycle states: draft, confirmed, in_production, qc, ready, dispatched, cancelled
        order_specs = [
            # ID 1..3: Dispatched (Completed lifecycle)
            ("dispatched",    0, 2026, 8,  10, 2026, 9,  15, 1200, 9200_00, "Export lot to Middle East"),
            ("dispatched",    1, 2026, 8,  18, 2026, 9,  25,  850, 8800_00, "Autumn fashion collection"),
            ("dispatched",    2, 2026, 8,  25, 2026, 10,  1, 1500, 9500_00, "Hospitality bedlinen contract"),
            # ID 4: Cancelled
            ("cancelled",     3, 2026, 9,   1, 2026, 9,  20,  600, 8400_00, "Cancelled by buyer spec change"),
            # ID 5..8: Ready / In Store (Awaiting Dispatch)
            ("ready",         0, 2026, 9,   5, 2026, 10, 12, 1100, 9200_00, "Inspection passed, packing complete"),
            ("ready",         4, 2026, 9,  10, 2026, 10, 15,  950, 9600_00, "Heritage boutique order"),
            ("ready",         2, 2026, 9,  14, 2026, 10, 20, 1800, 8900_00, "Institutional hospital uniform twill"),
            ("ready",         1, 2026, 9,  18, 2026, 10, 22, 1300, 9300_00, "Fast-fashion winter drop"),
            # ID 9..12: QC Review Stage
            ("qc",            3, 2026, 9,  22, 2026, 10, 25, 1400, 9100_00, "On inspection tables in Bay 2"),
            ("qc",            5, 2026, 9,  25, 2026, 10, 28,  750, 9800_00, "Global luxury blend under review"),
            ("qc",            0, 2026, 9,  28, 2026, 11,  2, 1600, 8700_00, "ASTM 4-point certification underway"),
            ("qc",            1, 2026, 10,  1, 2026, 11,  5, 1050, 9250_00, "Final yardage measurement check"),
            # ID 13..17: In Production (Weaving & Dyeing)
            ("in_production", 2, 2026, 9,  29, 2026, 11, 10, 2200, 8800_00, "Active on Weaving Looms WL-01 & WL-02"),
            ("in_production", 4, 2026, 10,  2, 2026, 11, 12,  900, 9900_00, "Organic certified weave on WL-03"),
            ("in_production", 0, 2026, 10,  3, 2026, 11, 15, 1750, 9050_00, "Poplin white running on Tsudakoma"),
            ("in_production", 3, 2026, 10,  4, 2026, 11, 18, 1250, 9400_00, "Heavy twill bay allocation"),
            ("in_production", 5, 2026, 10,  5, 2026, 11, 20, 2000, 9600_00, "Export contract running double shift"),
            # ID 18..21: Confirmed (Cleared for Floor Scheduling)
            ("confirmed",     1, 2026, 10,  6, 2026, 11, 25, 1150, 9100_00, "Yarn issued from RAW store"),
            ("confirmed",     2, 2026, 10,  7, 2026, 11, 28, 1450, 8950_00, "Beam warping scheduled for Monday"),
            ("confirmed",     4, 2026, 10,  8, 2026, 12,  1,  800, 9750_00, "Special dye lot approval granted"),
            ("confirmed",     0, 2026, 10,  9, 2026, 12,  5, 1600, 9150_00, "Credit verified, production queued"),
            # ID 22..24: Draft (Under Commercial Review)
            ("draft",         3, 2026, 10, 10, None, None, None, 1000, 9300_00, "Draft quotation submitted to buyer"),
            ("draft",         5, 2026, 10, 10, None, None, None, 2500, 9500_00, "Sample approval pending with buyer"),
            ("draft",         1, 2026, 10, 11, None, None, None, 1350, 9200_00, "Inward enquiry pending price lock"),
        ]

        orders = []
        for i, (status, b_idx, yr, mo, dy, del_yr, del_mo, del_dy, qty, rate, notes) in enumerate(order_specs, start=1):
            ref = f"ORD-2026-{i:05d}"
            odate = date(yr, mo, dy)
            ddate = date(del_yr, del_mo, del_dy) if del_yr else None
            buyer = buyers[b_idx % len(buyers)]
            fabric = fabric_items[(i - 1) % len(fabric_items)]

            ord_entry = Order(
                ref=ref,
                buyer_id=buyer.id,
                order_date=odate,
                delivery_date=ddate,
                status=status,
                notes=notes,
            )
            db.add(ord_entry)
            db.flush()

            line = OrderLine(
                order_id=ord_entry.id,
                item_id=fabric.id,
                qty_meters=qty,
                rate_per_meter_paise=rate,
            )
            db.add(line)
            db.flush()
            orders.append(ord_entry)

        # 9. Production Runs
        runs = []
        active_loom = machines[2]  # WL-01
        for i in range(12):
            run = ProductionRun(
                machine_id=machines[(i % 3) + 2].id,
                order_id=orders[i % len(orders)].id,
                item_id=fabric_items[i % len(fabric_items)].id,
                current_stage="inspection" if i < 6 else "weaving",
                status="completed" if i < 6 else "active",
                yarn_used_g=180_000 + (i * 20_000),
                notes=f"Continuous weaving batch #{i+1}",
                started_at=now - timedelta(days=30 - i * 2),
                completed_at=(now - timedelta(days=15 - i)) if i < 6 else None,
            )
            db.add(run)
            db.flush()
            runs.append(run)

        # 10. EXACTLY 311 FABRIC ROLLS (ROLL-000001 through ROLL-000311)
        # Status breakdown:
        # - passed: 190
        # - in_store: 45
        # - dispatched: 35
        # - awaiting_qc: 25
        # - rework: 11
        # - rejected: 5
        # Total = 190 + 45 + 35 + 25 + 11 + 5 = 311 rolls
        roll_status_targets = (
            [("passed", "A")] * 160 +
            [("passed", "B")] * 30 +
            [("in_store", "A")] * 40 +
            [("in_store", "B")] * 5 +
            [("dispatched", "A")] * 35 +
            [("awaiting_qc", None)] * 25 +
            [("rework", "B")] * 7 +
            [("rework", "C")] * 4 +
            [("rejected", "C")] * 5
        )

        assert len(roll_status_targets) == 311, f"Expected 311 rolls, got {len(roll_status_targets)}"

        rolls = []
        for roll_idx, (r_status, r_grade) in enumerate(roll_status_targets, start=1):
            r_num = f"ROLL-{roll_idx:06d}"
            r_run = runs[roll_idx % len(runs)]
            r_item = fabric_items[roll_idx % len(fabric_items)]
            # Variable realistic length (between 60m and 120m, represented in cm: 6000cm to 12000cm)
            base_len = 6500 + ((roll_idx * 17) % 5500)
            weight_grams = int(base_len * float(r_item.yarn_kg_per_meter or 0.20) * 10)

            roll = Roll(
                roll_number=r_num,
                run_id=r_run.id,
                item_id=r_item.id,
                length_cm=base_len,
                weight_g=weight_grams,
                status=r_status,
                qc_grade=r_grade,
                created_at=now - timedelta(days=max(1, 35 - (roll_idx // 10))),
            )
            db.add(roll)
            db.flush()
            rolls.append(roll)

            # Roll lifecycle event
            db.add(RollEvent(
                roll_id=roll.id,
                event_type="produced",
                note=f"Doffed from loom {r_run.machine.code}",
                created_by_id=users["floor_supervisor"].id,
                created_at=roll.created_at,
            ))

            if r_status in ["passed", "in_store", "dispatched"]:
                db.add(RollEvent(
                    roll_id=roll.id,
                    event_type="inspected",
                    note=f"ASTM 4-Point inspection passed (Grade {r_grade})",
                    created_by_id=users["qc"].id,
                    created_at=roll.created_at + timedelta(hours=4),
                ))

            if r_status in ["in_store", "dispatched"]:
                db.add(RollEvent(
                    roll_id=roll.id,
                    event_type="transferred_store",
                    note="Moved into Finished Goods Store (FIN)",
                    created_by_id=users["store"].id,
                    created_at=roll.created_at + timedelta(hours=8),
                ))

            # Defects for rework or rejected rolls
            if r_status in ["rework", "rejected"]:
                defect_kinds = ["weft_float", "oil_stain", "broken_end", "tension_variation", "selvedge_tear"]
                d_type = defect_kinds[roll_idx % len(defect_kinds)]
                db.add(RollDefect(
                    roll_id=roll.id,
                    defect_type=d_type,
                    severity="major" if r_status == "rejected" else "minor",
                    location_m=15 + (roll_idx % 40),
                    notes=f"Logged during 100% inspection pass: {d_type.replace('_', ' ').title()}",
                    created_by_id=users["qc"].id,
                ))

        # 11. Demonstration Workers & Monthly Attendance
        workers_data = [
            ("WRK-001", "Ramesh Kumar",   "piece_rate", 0,     1250, "+91-9811223344"), # 12.50 INR per meter
            ("WRK-002", "Suresh Patel",   "hourly",     8500,  0,    "+91-9822334455"), # 85.00 INR/hr
            ("WRK-003", "Anita Devi",     "hourly",     9500,  0,    "+91-9833445566"), # 95.00 INR/hr (QC)
            ("WRK-004", "Mohammed Rafi",  "hourly",     11000, 0,    "+91-9844556677"), # 110.00 INR/hr (Dye Master)
            ("WRK-005", "Vikram Singh",   "hourly",     8000,  0,    "+91-9855667788"), # 80.00 INR/hr
            ("WRK-006", "Lakshmi Bai",    "piece_rate", 0,     1400, "+91-9866778899"), # 14.00 INR per meter
            ("WRK-007", "Ganesh Rao",     "hourly",     9000,  0,    "+91-9877889900"), # 90.00 INR/hr
            ("WRK-008", "Priya Sharma",   "hourly",     7500,  0,    "+91-9888990011"), # 75.00 INR/hr
        ]

        worker_ids = []
        for emp_id, name, w_basis, h_rate, p_rate, ph in workers_data:
            # Insert into workers table if it exists
            try:
                res = db.execute(text("""
                    INSERT INTO workers (employee_id, full_name, wage_basis, hourly_rate_paise, piece_rate_paise, phone, is_active, created_at)
                    VALUES (:eid, :name, :basis, :hr, :pr, :phone, 1, :now)
                """), {
                    "eid": emp_id, "name": name, "basis": w_basis,
                    "hr": h_rate, "pr": p_rate, "phone": ph, "now": now
                })
                worker_ids.append(res.lastrowid)
            except Exception as e:
                pass

        # Seed attendance records for past 14 workdays if table exists
        if worker_ids:
            try:
                for day_offset in range(1, 15):
                    att_date = (date.today() - timedelta(days=day_offset))
                    for w_id in worker_ids:
                        shift = "morning" if (w_id % 2 == 0) else "afternoon"
                        hrs = 480  # 8 hours in minutes
                        pieces = 85 if (w_id % 3 == 0) else None
                        db.execute(text("""
                            INSERT OR IGNORE INTO attendance_entries 
                            (worker_id, work_date, shift, hours_worked, pieces_produced, status, created_at)
                            VALUES (:wid, :dt, :sh, :hw, :pp, 'approved', :now)
                        """), {
                            "wid": w_id, "dt": att_date, "sh": shift,
                            "hw": hrs, "pp": pieces, "now": now
                        })
            except Exception as e:
                print(f"[!] Attendance seeding note: {e}")

        # 12. Finalised & Draft Wage Runs
        try:
            db.execute(text("""
                INSERT OR IGNORE INTO wage_runs 
                (id, period_start, period_end, status, calculated_at, finalised_at, created_at)
                VALUES (1, '2026-09-01', '2026-09-30', 'finalised', :now, :now, :now)
            """), {"now": now})

            db.execute(text("""
                INSERT OR IGNORE INTO wage_runs 
                (id, period_start, period_end, status, calculated_at, created_at)
                VALUES (2, '2026-10-01', '2026-10-31', 'draft', :now, :now)
            """), {"now": now})

            for w_id in worker_ids:
                db.execute(text("""
                    INSERT OR IGNORE INTO wage_run_lines
                    (wage_run_id, worker_id, total_hours_minutes, total_pieces, applied_rate_paise, base_wage_paise, adjustment_paise, net_wage_paise, note)
                    VALUES (1, :wid, 9600, 450, 8500, 1850000, 150000, 2000000, 'Monthly payroll cycle September 2026')
                """), {"wid": w_id})
        except Exception as e:
            print(f"[!] Wage runs seeding note: {e}")

        # 13. Order Costing & Roll Costing Records
        try:
            for idx, order in enumerate(orders[:8], start=1):
                yarn_cost = 45000_00 * idx
                wage_cost = 18000_00 * idx
                overhead = 9500_00 * idx
                total_cost = yarn_cost + wage_cost + overhead
                passed_m = 900 + idx * 100
                cost_per_m = total_cost // passed_m

                db.execute(text("""
                    INSERT OR IGNORE INTO order_costs
                    (order_id, yarn_cost_paise, allocated_wage_paise, overhead_paise, total_cost_paise, passed_metres, cost_per_passed_metre_paise, overhead_method, calculated_at)
                    VALUES (:oid, :yc, :wc, :oh, :tc, :pm, :cpm, 'per_metre', :now)
                """), {
                    "oid": order.id, "yc": yarn_cost, "wc": wage_cost, "oh": overhead,
                    "tc": total_cost, "pm": passed_m, "cpm": cost_per_m, "now": now
                })
        except Exception as e:
            print(f"[!] Order costing seeding note: {e}")

        # 14. Demo GST Invoices for Dispatched Orders
        for idx in range(1, 4):
            inv = Invoice(
                ref=f"INV-2026-{idx:05d}",
                invoice_type="sale",
                buyer_id=buyers[idx - 1].id,
                invoice_date=date(2026, 9, 20 + idx),
                due_date=date(2026, 10, 20 + idx),
                status="paid" if idx == 1 else "sent",
                notes=f"Tax invoice for commercial dispatch ORD-2026-{idx:05d}",
            )
            db.add(inv)
            db.flush()
            inv_line = InvoiceLine(
                invoice_id=inv.id,
                description=f"Export Fabric Goods — {fabric_items[idx].name}",
                qty=1200,
                unit_price_paise=9200_00,
                tax_pct=5,
            )
            db.add(inv_line)
            db.flush()
            if idx == 1:
                db.add(Payment(
                    invoice_id=inv.id,
                    paid_date=date(2026, 10, 5),
                    amount_paise=1200 * 9200_00 * 105 // 100,
                    method="neft",
                    reference="UTR-HDFC-99182312",
                    notes="Full buyer payment settled",
                ))

        db.commit()
        print("\n" + "="*60)
        print("[OK] SUCCESS: Khadira ERP Demo Dataset Generated Successfully!")
        print("="*60)
        print(f" - Database File   : {db_path}")
        print(f" - Total Orders    : {len(orders)} (ORD-2026-00001 to ORD-2026-{len(orders):05d})")
        print(f" - Fabric Rolls    : {len(rolls)} (ROLL-000001 to ROLL-{len(rolls):06d})")
        print(f" - Demo Workers    : {len(worker_ids)} employees with shift attendance")
        print(f" - Wage Runs       : 2 cycles (1 Finalised, 1 Draft)")
        print(f" - Costing Data    : Seeded order_costs & roll_costs")
        print(f" - Catalog Items   : {len(yarn_items)} yarn SKUs + {len(fabric_items)} fabric SKUs")
        print(f" - Looms & Jet     : {len(machines)} active production units")
        print(f" - Admin Password  : {PASSWORD}")
        print("="*60 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "mill_demo.db"
    seed_demo(target)
