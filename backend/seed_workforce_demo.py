"""Seed workforce, attendance, wages, and costing for the demo database."""
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from mill.models import (
    Base, User, Worker, AttendanceEntry, WageRun, WageRunLine, OrderCost,
    Order, ProductionRun, Roll, Setting
)
from mill.services.auth import hash_password, DEMO_PASSWORDS

def seed_demo_database(db_path: str = "mill_demo.db"):
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 1. Update user passwords to match the 1-click demo buttons
        user_passwords = {
            "admin": "admin123",
            "owner": "owner123",
            "store": "store123",
            "floor_supervisor": "super123",
            "qc": "qc1234",
            "office": "office123",
        }
        for username, password in user_passwords.items():
            user = db.scalar(select(User).where(User.username == username))
            if user:
                user.hashed_password = hash_password(password)
        db.flush()

        # 2. Add overhead setting
        overhead_setting = db.get(Setting, "overhead_per_metre_paise")
        if not overhead_setting:
            db.add(Setting(key="overhead_per_metre_paise", value="1500"))
        else:
            overhead_setting.value = "1500"
        db.flush()

        admin = db.scalar(select(User).where(User.username == "admin"))
        supervisor = db.scalar(select(User).where(User.username == "floor_supervisor"))
        office = db.scalar(select(User).where(User.username == "office"))
        admin_id = admin.id if admin else 1
        super_id = supervisor.id if supervisor else admin_id
        office_id = office.id if office else admin_id

        # 3. Seed Workers
        workers_data = [
            ("WF-101", "Ramesh Varma",   "Weaving",         "hourly",     12000, 0),
            ("WF-102", "Sunita Patil",   "Spinning",        "hourly",     11500, 0),
            ("WF-103", "Anand Hegde",    "Weaving",         "piece_rate", 0,     2500),
            ("WF-104", "Kavita Devi",    "Quality Control", "hourly",     13000, 0),
            ("WF-105", "Murugan S",      "Finishing",       "hourly",     10500, 0),
            ("WF-106", "Deepak Rao",     "Maintenance",     "hourly",     11000, 0),
        ]
        worker_objs = {}
        for code, name, dept, basis, h_rate, p_rate in workers_data:
            w = db.scalar(select(Worker).where(Worker.code == code))
            if not w:
                w = Worker(
                    code=code, full_name=name, department=dept,
                    wage_basis=basis, hourly_rate_paise=h_rate, piece_rate_paise=p_rate,
                    is_active=True
                )
                db.add(w)
                db.flush()
            worker_objs[code] = w

        # 4. Seed Attendance entries
        orders = db.scalars(select(Order).limit(10)).all()
        runs = db.scalars(select(ProductionRun).limit(10)).all()

        dates = [
            date(2026, 10, 8),
            date(2026, 10, 9),
            date(2026, 10, 10),
        ]
        
        for i, d in enumerate(dates):
            for j, (code, w) in enumerate(worker_objs.items()):
                shift = "Shift A" if j % 2 == 0 else "Shift B"
                existing = db.scalar(select(AttendanceEntry).where(
                    AttendanceEntry.worker_id == w.id,
                    AttendanceEntry.work_date == d,
                    AttendanceEntry.shift == shift
                ))
                if not existing:
                    ord_obj = orders[(i + j) % len(orders)] if orders else None
                    run_obj = runs[(i + j) % len(runs)] if runs else None
                    is_draft = (i == len(dates) - 1 and j < 2)
                    entry = AttendanceEntry(
                        worker_id=w.id,
                        work_date=d,
                        shift=shift,
                        hours_worked=480 if w.wage_basis == "hourly" else None,
                        pieces_produced=24 if w.wage_basis == "piece_rate" else None,
                        order_id=ord_obj.id if ord_obj else None,
                        run_id=run_obj.id if run_obj else None,
                        notes=f"Completed production batch for {ord_obj.ref if ord_obj else 'General'}",
                        status="draft" if is_draft else "approved",
                        created_by_id=super_id,
                        approved_by_id=None if is_draft else super_id,
                        approved_at=None if is_draft else datetime.now(timezone.utc)
                    )
                    db.add(entry)
        db.flush()

        # 5. Seed Wage Runs
        wr_finalised = db.scalar(select(WageRun).where(WageRun.period_start == date(2026, 10, 1)))
        if not wr_finalised:
            wr_finalised = WageRun(
                period_start=date(2026, 10, 1),
                period_end=date(2026, 10, 7),
                status="finalised",
                created_by_id=office_id,
                finalised_by_id=office_id,
                finalised_at=datetime.now(timezone.utc)
            )
            db.add(wr_finalised)
            db.flush()
            for w in worker_objs.values():
                line = WageRunLine(
                    wage_run_id=wr_finalised.id,
                    worker_id=w.id,
                    total_hours_minutes=2400 if w.wage_basis == "hourly" else 0,
                    total_pieces=120 if w.wage_basis == "piece_rate" else 0,
                    applied_rate_paise=w.hourly_rate_paise or w.piece_rate_paise,
                    net_wage_paise=480000 if w.wage_basis == "hourly" else 300000
                )
                db.add(line)

        wr_draft = db.scalar(select(WageRun).where(WageRun.period_start == date(2026, 10, 8)))
        if not wr_draft:
            wr_draft = WageRun(
                period_start=date(2026, 10, 8),
                period_end=date(2026, 10, 14),
                status="draft",
                created_by_id=office_id
            )
            db.add(wr_draft)
            db.flush()
            for w in worker_objs.values():
                line = WageRunLine(
                    wage_run_id=wr_draft.id,
                    worker_id=w.id,
                    total_hours_minutes=1440 if w.wage_basis == "hourly" else 0,
                    total_pieces=72 if w.wage_basis == "piece_rate" else 0,
                    applied_rate_paise=w.hourly_rate_paise or w.piece_rate_paise,
                    net_wage_paise=288000 if w.wage_basis == "hourly" else 180000
                )
                db.add(line)
        db.flush()

        # 6. Precalculate order costs for orders 1..10
        from mill.api.costing import _calculate
        for ord_item in orders[:10]:
            try:
                _calculate(db, ord_item.id, admin_id)
            except Exception as e:
                pass

        # 7. Seed Notifications
        from mill.models import Notification
        notif_count = db.scalar(select(Notification.id).limit(1))
        if not notif_count:
            demo_notifications = [
                Notification(
                    recipient_role="admin",
                    entity_type="stock",
                    entity_id=1,
                    event_type="low_stock",
                    message="Yarn Stock Alert: Cotton 40s Combed below minimum safety threshold (420 kg remaining)",
                    is_read=False
                ),
                Notification(
                    recipient_role="qc",
                    entity_type="roll",
                    entity_id=1042,
                    event_type="qc_rejection",
                    message="QC Alert: Roll R-1042 flagged with warp tension defect during 4-point inspection",
                    is_read=False
                ),
                Notification(
                    recipient_role="floor_supervisor",
                    entity_type="order",
                    entity_id=18,
                    event_type="order_ready",
                    message="Order SO-2026-018: 100% of rolls inspected and ready for packing/dispatch",
                    is_read=False
                ),
                Notification(
                    recipient_role="admin",
                    entity_type="machine",
                    entity_id=4,
                    event_type="maintenance_due",
                    message="Preventive Maintenance: Loom LM-04 reached 1,200 operating hours",
                    is_read=True
                )
            ]
            db.add_all(demo_notifications)

        db.commit()
        print(f"[OK] Demo database {db_path} seeded successfully with workforce, attendance, wages, costing, and notifications!")
    finally:
        db.close()

if __name__ == "__main__":
    db_target = sys.argv[1] if len(sys.argv) > 1 else "mill_demo.db"
    seed_demo_database(db_target)
