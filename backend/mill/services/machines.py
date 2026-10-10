"""Machines service."""

from sqlalchemy.orm import Session

from ..models import Machine
from .common import DomainError, audit


def create_machine(db: Session, *, code: str, name: str,
                   machine_type: str, user_id: int | None) -> Machine:
    from sqlalchemy import select
    existing = db.scalar(select(Machine).where(Machine.code == code))
    if existing:
        raise DomainError(f"Machine code '{code}' already exists.")
    m = Machine(code=code, name=name, machine_type=machine_type)
    db.add(m)
    db.flush()
    audit(db, entity="Machine", entity_id=m.id, action="create", user_id=user_id)
    return m
