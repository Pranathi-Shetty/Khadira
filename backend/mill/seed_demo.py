"""Seed rich demonstration database (mill_demo.db) for Khadira Textile Mills ERP.

All demonstration data is generated exclusively through real domain services
via mill.scenario_loader.load_scenario.
"""

import os
import sys

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mill.models import Base
from mill.scenario_loader import load_scenario


def seed_demo(db_path: str = "mill_demo.db", force_reset: bool = False):
    # Normalize path relative to backend folder
    if not os.path.isabs(db_path) and not db_path.startswith("backend"):
        if os.path.basename(os.getcwd()) != "backend" and os.path.exists("backend"):
            db_path = os.path.join("backend", db_path)

    print(f"[*] Initializing Khadira ERP Demo Database at: {db_path}")
    db_url = f"sqlite:///{db_path}"

    if force_reset:
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

    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()

    try:
        results = load_scenario(db, force_reset=False)
        return results
    finally:
        db.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "mill_demo.db"
    reset_flag = "--reset" in sys.argv
    seed_demo(target, force_reset=reset_flag)
