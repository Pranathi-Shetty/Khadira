"""Database engine + session helpers."""

from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker


def make_session_factory(url: str, serverless: bool = False) -> sessionmaker:
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(url, connect_args=connect_args)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_wal(conn, _):
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


_factory: sessionmaker | None = None


def init_db(url: str, serverless: bool = False) -> sessionmaker:
    global _factory
    _factory = make_session_factory(url, serverless)
    return _factory


def get_db():
    """FastAPI dependency that yields a DB session."""
    from fastapi import Request
    # Will be overridden by the request's app state in the dependency
    raise NotImplementedError("Use the app-state session factory via deps.py")


@contextmanager
def session_scope(factory: sessionmaker):
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
