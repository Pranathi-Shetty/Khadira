"""Seed script: loads demo data for all roles and a complete mill scenario.

Usage:
    cd backend
    python -m mill.seed
"""
from datetime import date, timedelta

from mill.database import SessionLocal
from mill.auth import hash_password
from mill.models import (
    Buyer, Item, ItemType, Machine, MachineStatus, MachineType,
    Setting, StockLevel, Supplier, User, UserRole, WageBasis, Worker,
)


def seed():
    from mill.database import Base, engine
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed_settings(db)
        _seed_users(db)
        _seed_partners(db)
        _seed_items(db)
        _seed_machines(db)
        _seed_workers(db)
        db.commit()
        print("Seed complete. Open http://127.0.0.1:8000/docs to explore the API.")
    finally:
        db.close()


def _seed_settings(db):
    defaults = {
        "company_name": "Everest Textile Mills",
        "currency": "INR",
        "overhead_per_metre_paise": "200",   # ₹2/m overhead
        "reorder_alert_enabled": "true",
    }
    from mill.models import Setting
    for k, v in defaults.items():
        if not db.query(Setting).filter(Setting.key == k).first():
            db.add(Setting(key=k, value=v))
    db.flush()


def _seed_users(db):
    users = [
        ("admin",      "Admin User",       UserRole.admin,            "admin123"),
        ("owner",      "Ramesh Gupta",     UserRole.owner,            "owner123"),
        ("store",      "Meena Sharma",     UserRole.store,            "store123"),
        ("supervisor", "Vikram Patil",     UserRole.floor_supervisor, "super123"),
        ("qc_officer", "Priya Nair",       UserRole.qc,               "qc1234"),
        ("office",     "Anita Joshi",      UserRole.office,           "office123"),
    ]
    for username, full_name, role, password in users:
        if not db.query(User).filter(User.username == username).first():
            db.add(User(
                username=username,
                full_name=full_name,
                role=role,
                hashed_password=hash_password(password),
            ))
    db.flush()


def _seed_partners(db):
    suppliers = [
        ("Rajasthan Yarn Co.", "Suresh Kumar", "+91-9876543210"),
        ("Gujarat Cotton Mills", "Harish Patel", "+91-9812345678"),
    ]
    for name, contact, phone in suppliers:
        if not db.query(Supplier).filter(Supplier.name == name).first():
            db.add(Supplier(name=name, contact_name=contact, phone=phone, payment_terms_days=30))

    buyers = [
        ("Delhi Fashion House", "Neha Mehta", "+91-9123456789"),
        ("Mumbai Textile Traders", "Arun Shah", "+91-9234567890"),
        ("Chennai Garments Ltd.", "Kavitha Rajan", "+91-9345678901"),
    ]
    for name, contact, phone in buyers:
        if not db.query(Buyer).filter(Buyer.name == name).first():
            db.add(Buyer(name=name, contact_name=contact, phone=phone, payment_terms_days=45))
    db.flush()


def _seed_items(db):
    items = [
        # Yarn items
        {
            "sku": "YRN-CTN-WHT",
            "name": "Cotton Yarn - White",
            "item_type": ItemType.yarn,
            "yarn_type": "cotton",
            "colour": "white",
            "unit": "kg",
            "average_cost_paise": 18000,   # ₹180/kg
            "reorder_point_grams": 500_000,  # 500 kg
        },
        {
            "sku": "YRN-CTN-BLU",
            "name": "Cotton Yarn - Blue",
            "item_type": ItemType.yarn,
            "yarn_type": "cotton",
            "colour": "blue",
            "unit": "kg",
            "average_cost_paise": 19000,
            "reorder_point_grams": 300_000,
        },
        {
            "sku": "YRN-PLY-WHT",
            "name": "Polyester Yarn - White",
            "item_type": ItemType.yarn,
            "yarn_type": "polyester",
            "colour": "white",
            "unit": "kg",
            "average_cost_paise": 12000,
            "reorder_point_grams": 400_000,
        },
        # Fabric items
        {
            "sku": "FAB-CTN-PLAIN",
            "name": "Plain Cotton Fabric",
            "item_type": ItemType.fabric,
            "yarn_type": "cotton",
            "colour": "white",
            "unit": "m",
            "yarn_grams_per_metre": 200,    # 200g yarn per metre of fabric
            "sale_price_paise_per_metre": 35000,  # ₹350/m
        },
        {
            "sku": "FAB-CTN-DENIM",
            "name": "Cotton Denim Fabric",
            "item_type": ItemType.fabric,
            "yarn_type": "cotton",
            "colour": "blue",
            "unit": "m",
            "yarn_grams_per_metre": 350,
            "sale_price_paise_per_metre": 55000,
        },
    ]
    for item_data in items:
        if not db.query(Item).filter(Item.sku == item_data["sku"]).first():
            db.add(Item(**item_data))
    db.flush()

    # Seed initial stock levels
    from mill.models import StoreLocation
    raw_loc = db.query(StoreLocation).filter(StoreLocation.code == "RAW").first()
    if raw_loc is None:
        raw_loc = StoreLocation(code="RAW", name="Raw Material Store")
        db.add(raw_loc)
        fin_loc = StoreLocation(code="FIN", name="Finished Goods Store")
        db.add(fin_loc)
        db.flush()

    yarn_items = db.query(Item).filter(Item.item_type == ItemType.yarn).all()
    for item in yarn_items:
        if not db.query(StockLevel).filter(StockLevel.item_id == item.id).first():
            db.add(StockLevel(
                item_id=item.id,
                location_id=raw_loc.id,
                quantity=1_000_000,   # 1000 kg initial stock
            ))
    db.flush()


def _seed_machines(db):
    machines = [
        ("SPM-01", "Spinning Machine 1", MachineType.spinning),
        ("SPM-02", "Spinning Machine 2", MachineType.spinning),
        ("WVR-01", "Weaving Loom 1", MachineType.weaving),
        ("WVR-02", "Weaving Loom 2", MachineType.weaving),
        ("WVR-03", "Weaving Loom 3", MachineType.weaving),
        ("DYE-01", "Dyeing Vat 1", MachineType.dyeing),
        ("DYE-02", "Dyeing Vat 2", MachineType.dyeing),
    ]
    for code, name, mtype in machines:
        if not db.query(Machine).filter(Machine.code == code).first():
            db.add(Machine(code=code, name=name, machine_type=mtype, status=MachineStatus.idle))
    db.flush()


def _seed_workers(db):
    workers = [
        ("EMP-001", "Raju Mehta",    WageBasis.hourly,     1000_00, 0),      # ₹100/hr
        ("EMP-002", "Sunita Devi",   WageBasis.piece_rate, 0, 3_00),         # ₹3/piece
        ("EMP-003", "Mohan Lal",     WageBasis.hourly,     80_00, 0),        # ₹80/hr
        ("EMP-004", "Kaveri Bai",    WageBasis.piece_rate, 0, 4_00),         # ₹4/piece
        ("EMP-005", "Ashok Kumar",   WageBasis.hourly,     120_00, 0),       # ₹120/hr
    ]
    for emp_id, name, basis, hourly, piece in workers:
        if not db.query(Worker).filter(Worker.employee_id == emp_id).first():
            db.add(Worker(
                employee_id=emp_id,
                full_name=name,
                wage_basis=basis,
                hourly_rate_paise=hourly,
                piece_rate_paise=piece,
            ))
    db.flush()


if __name__ == "__main__":
    seed()
