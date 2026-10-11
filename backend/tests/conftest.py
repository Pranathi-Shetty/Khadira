"""Pytest fixtures: file-based SQLite test DB + seeded data."""

import os
import sys
import tempfile
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mill.main import create_app
from mill.models import Base
from mill.config import Settings
from mill.models.core import User, Location
from mill.models.settings import Setting
from mill.services.auth import hash_password

# Use a per-run file in the system temporary directory.  A fixed path makes
# the suite fail on Windows when a previous test process still owns its SQLite
# handle (for example after an interrupted run).
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"khadira_test_{uuid.uuid4().hex}.db")
TEST_DB_URL  = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Create a fresh test database for the whole session, then clean up."""
    # Remove stale DB from a previous run
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragmas(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")

    from alembic.config import Config
    from alembic import command
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
    command.upgrade(cfg, "head")

    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = factory()
    try:
        # Settings
        for k, v in [("company_name", "Khadira"), ("currency", "INR")]:
            if db.get(Setting, k) is None:
                db.add(Setting(key=k, value=v))

        # Locations
        for code, name in [("RAW", "Raw Material Store"), ("FIN", "Finished Goods Store"), ("WIP", "Work In Progress"), ("WASTE", "Waste Store")]:
            if db.query(Location).filter_by(code=code).first() is None:
                db.add(Location(code=code, name=name))

        # Users
        for username, role in [
            ("admin",            "admin"),
            ("owner",            "owner"),
            ("store",            "store"),
            ("floor_supervisor", "floor_supervisor"),
            ("qc",               "qc"),
            ("office",           "office"),
        ]:
            if db.query(User).filter_by(username=username).first() is None:
                db.add(User(
                    username=username, role=role,
                    hashed_password=hash_password("khadira2026!"),
                    email=f"{username}@test.in", full_name=username.title(),
                ))

        db.commit()
    finally:
        db.close()

    yield engine

    engine.dispose()
    for f in [TEST_DB_PATH, TEST_DB_PATH + "-shm", TEST_DB_PATH + "-wal"]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError:
            pass  # Windows file lock guard

@pytest.fixture(scope="session")
def app(test_database):
    settings = Settings(
        database_url=TEST_DB_URL,
        secret_key="test-secret",
        session_hours=8,
        cors_origins=["http://localhost:3000"],
        cookie_secure=False,
    )
    return create_app(settings=settings)


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def db_session(test_database):
    """Provide a dedicated SQLAlchemy session bound to the test database."""
    session_factory = sessionmaker(bind=test_database, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def login(client: TestClient, username: str = "admin", password: str = "khadira2026!") -> TestClient:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed for {username}: {r.text}"
    return client
