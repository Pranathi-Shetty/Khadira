"""Seed demo data for Khadira."""

from datetime import date

from .db import make_session_factory
from .config import get_settings
from .models import Base, Item, Location, ITEM_YARN, ITEM_FABRIC
from .models.core import User
from .models.partners import Buyer, Supplier
from .models.production import Machine
from .models.settings import Setting
from .services.auth import hash_password
from .services.common import set_setting

PASSWORD = "khadira2026!"


def seed():
    # Respect the selected environment so `backend:seed` refreshes the active
    # demo database instead of silently writing to a different normal database.
    database_url = get_settings().database_url
    factory = make_session_factory(database_url)
    from sqlalchemy import create_engine
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    db = factory()
    try:
        # Settings
        for k, v in [
            ("company_name", "Khadira"),
            ("currency", "INR"),
            ("low_stock_threshold_kg", "500"),
        ]:
            s = db.get(Setting, k)
            if s is None:
                db.add(Setting(key=k, value=v))
            else:
                s.value = v

        # Locations
        locs = {}
        for code, name in [("RAW", "Raw Material Store"), ("FIN", "Finished Goods Store")]:
            loc = db.query(Location).filter_by(code=code).first()
            if loc is None:
                loc = Location(code=code, name=name)
                db.add(loc)
                db.flush()
            locs[code] = loc

        # Users
        users_data = [
            ("admin",            "Admin User",        "admin@khadira.in",          "admin"),
            ("owner",            "Owner",             "owner@khadira.in",          "owner"),
            ("store",            "Store Keeper",      "store@khadira.in",          "store"),
            ("floor_supervisor", "Floor Supervisor",  "supervisor@khadira.in",     "floor_supervisor"),
            ("qc",               "QC Inspector",      "qc@khadira.in",             "qc"),
            ("office",           "Office Staff",      "office@khadira.in",         "office"),
        ]
        users = {}
        for username, full_name, email, role in users_data:
            u = db.query(User).filter_by(username=username).first()
            if u is None:
                u = User(username=username, full_name=full_name, email=email,
                         role=role, hashed_password=hash_password(PASSWORD))
                db.add(u)
            else:
                u.hashed_password = hash_password(PASSWORD)
                u.email = email
                u.full_name = full_name
                db.flush()
            users[username] = u

        # Suppliers
        sup_data = [
            ("Himalayan Yarn Co.", "Rajesh Sharma", "+91-9876543210", "himalayan@yarn.in", "27AABCH1234A1Z5"),
            ("Deccan Fibres Ltd.", "Priya Nair",   "+91-8765432109", "deccan@fibres.in",  "29AABCD5678A1Z3"),
        ]
        suppliers = []
        for name, contact, phone, email, gstin in sup_data:
            s = db.query(Supplier).filter_by(name=name).first()
            if s is None:
                s = Supplier(name=name, contact_name=contact, phone=phone,
                             email=email, gstin=gstin)
                db.add(s)
                db.flush()
            suppliers.append(s)

        # Yarn items
        yarn_data = [
            ("YRN-20-W",  "Cotton Yarn 20s White",   "20s",  500_000),   # reorder 500kg
            ("YRN-30-W",  "Cotton Yarn 30s White",   "30s",  300_000),
            ("YRN-40-C",  "Cotton Yarn 40s Coloured","40s",  200_000),
            ("YRN-PC-65", "Poly-Cotton Yarn 65/35",  "65/35",400_000),
        ]
        yarn_items = []
        for sku, name, count, reorder_g in yarn_data:
            it = db.query(Item).filter_by(sku=sku).first()
            if it is None:
                it = Item(sku=sku, name=name, item_type=ITEM_YARN, unit="kg",
                          count_denier=count, reorder_point_kg=reorder_g)
                db.add(it)
                db.flush()
            yarn_items.append(it)

        # Fabric items
        fabric_data = [
            ("FAB-POP-WH",  "Poplin Fabric White",      120, 110, 0.185),
            ("FAB-TWL-BL",  "Twill Fabric Blue",        200, 150, 0.240),
            ("FAB-SLB-MIX", "Slub Fabric Mixed",        160, 140, 0.210),
        ]
        fabric_items = []
        for sku, name, gsm, width, ykpm in fabric_data:
            it = db.query(Item).filter_by(sku=sku).first()
            if it is None:
                it = Item(sku=sku, name=name, item_type=ITEM_FABRIC, unit="meters",
                          gsm=gsm, width_cm=width, yarn_kg_per_meter=ykpm)
                db.add(it)
                db.flush()
            fabric_items.append(it)

        # Buyers
        buyer_data = [
            ("Sunrise Garments Pvt. Ltd.", "Arun Kumar",  "+91-9123456789", "sunrise@garments.in", 45),
            ("Metro Fashion House",        "Deepa Singh", "+91-8234567890", "metro@fashion.in",    30),
            ("Textile Exports Corp.",      "Sanjay Mehta","+91-7345678901", "exports@textile.in",  60),
        ]
        buyers = []
        for name, contact, phone, email, credit in buyer_data:
            b = db.query(Buyer).filter_by(name=name).first()
            if b is None:
                b = Buyer(name=name, contact_name=contact, phone=phone,
                          email=email, credit_days=credit)
                db.add(b)
                db.flush()
            buyers.append(b)

        # Machines
        machine_data = [
            ("SP-01", "Spinning Machine 1",  "spinning"),
            ("WL-01", "Weaving Loom 1",      "weaving"),
            ("DJ-01", "Dyeing Jet 1",        "dyeing"),
        ]
        machines = []
        for code, name, mtype in machine_data:
            m = db.query(Machine).filter_by(code=code).first()
            if m is None:
                m = Machine(code=code, name=name, machine_type=mtype)
                db.add(m)
                db.flush()
            machines.append(m)

        # Seed some yarn stock in RAW
        from .models.core import StockLevel
        raw_loc = locs["RAW"]
        for yarn_item in yarn_items:
            sl = db.query(StockLevel).filter_by(item_id=yarn_item.id, location_id=raw_loc.id).first()
            if sl is None:
                sl = StockLevel(item_id=yarn_item.id, location_id=raw_loc.id, qty_g=2_000_000)  # 2000 kg each
                db.add(sl)

        # Seed orders
        from .models.orders import Order, OrderLine
        order_data = [
            (buyers[0].id, "confirmed",     date(2026, 10, 1),  date(2026, 11, 1)),
            (buyers[1].id, "in_production", date(2026, 10, 5),  date(2026, 11, 15)),
            (buyers[2].id, "draft",         date(2026, 10, 10), None),
        ]
        orders = []
        for i, (buyer_id, status, odate, ddate) in enumerate(order_data):
            ref = f"ORD-2026-{i+1:05d}"
            o = db.query(Order).filter_by(ref=ref).first()
            if o is None:
                o = Order(ref=ref, buyer_id=buyer_id, order_date=odate,
                          delivery_date=ddate, status=status)
                db.add(o)
                db.flush()
                db.add(OrderLine(order_id=o.id, item_id=fabric_items[i % len(fabric_items)].id,
                                 qty_meters=500, rate_per_meter_paise=8500_00))
            orders.append(o)

        # Seed rolls
        from .models.production import ProductionRun, Roll, RollEvent
        run = db.query(ProductionRun).first()
        if run is None:
            run = ProductionRun(machine_id=machines[1].id, order_id=orders[1].id,
                                item_id=fabric_items[0].id, current_stage="inspection",
                                status="active")
            db.add(run)
            db.flush()

        fin_loc = locs["FIN"]
        roll_data = [
            ("ROLL-000001", 5000, "in_store",    "A"),
            ("ROLL-000002", 4800, "passed",      "A"),
            ("ROLL-000003", 5200, "awaiting_qc", None),
        ]
        for roll_number, length_cm, status, grade in roll_data:
            r = db.query(Roll).filter_by(roll_number=roll_number).first()
            if r is None:
                r = Roll(roll_number=roll_number, run_id=run.id,
                         item_id=fabric_items[0].id, length_cm=length_cm,
                         status=status, qc_grade=grade)
                db.add(r)
                db.flush()
                if status == "in_store":
                    # Post fabric_in stock move
                    sl = db.query(StockLevel).filter_by(item_id=r.item_id, location_id=fin_loc.id).first()
                    if sl is None:
                        sl = StockLevel(item_id=r.item_id, location_id=fin_loc.id, qty_g=length_cm)
                        db.add(sl)
                    else:
                        sl.qty_g += length_cm

        db.commit()
        print("[OK] Seed complete.")
        print(f"   Locations : {', '.join(locs)}")
        print(f"   Users     : {', '.join(users)}  (password: {PASSWORD})")
        print(f"   Suppliers : {', '.join(s.name for s in suppliers)}")
        print(f"   Yarn items: {len(yarn_items)}  |  Fabric items: {len(fabric_items)}")
        print(f"   Buyers    : {', '.join(b.name for b in buyers)}")
        print(f"   Machines  : {', '.join(m.code for m in machines)}")
        print(f"   Orders    : {', '.join(o.ref + ' (' + o.status + ')' for o in orders)}")
        rolls_out = db.query(Roll).all()
        print(f"   Rolls     : {', '.join(r.roll_number + ' (' + r.status + ')' for r in rolls_out)}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
