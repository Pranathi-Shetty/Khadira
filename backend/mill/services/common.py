"""Shared service helpers and domain error."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import AuditLog, Setting


class DomainError(HTTPException):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        super().__init__(status_code=status_code, detail=message)


def audit(db: Session, *, entity: str, entity_id: int | None, action: str,
          user_id: int | None = None, note: str | None = None) -> None:
    db.add(AuditLog(entity=entity, entity_id=entity_id, action=action,
                    user_id=user_id, note=note))


def all_settings(db: Session) -> dict[str, str]:
    from sqlalchemy import select
    rows = db.scalars(select(Setting)).all()
    return {r.key: r.value for r in rows}


def get_setting(db: Session, key: str, default: str = "") -> str:
    s = db.get(Setting, key)
    return s.value if s and s.value is not None else default


def set_setting(db: Session, key: str, value: str) -> None:
    s = db.get(Setting, key)
    if s is None:
        s = Setting(key=key, value=value)
        db.add(s)
    else:
        s.value = value
