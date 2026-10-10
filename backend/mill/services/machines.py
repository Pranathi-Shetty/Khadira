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

def log_downtime(db: Session, machine_id: int, reason: str, description: str | None,
                 run_id: int | None, user_id: int | None):
    from ..models.production import MachineDowntime, Machine
    m = db.get(Machine, machine_id)
    if not m:
        raise DomainError("Machine not found.", 404)
        
    dt = MachineDowntime(
        machine_id=machine_id,
        reason=reason,
        description=description,
        run_id=run_id,
        reporter_id=user_id
    )
    db.add(dt)
    db.flush()
    audit(db, entity="Machine", entity_id=machine_id, action="downtime_logged", user_id=user_id)
    return dt

def resolve_downtime(db: Session, downtime_id: int, resolution: str, user_id: int | None):
    from ..models.production import MachineDowntime
    from datetime import datetime, timezone
    dt = db.get(MachineDowntime, downtime_id)
    if not dt:
        raise DomainError("Downtime record not found.", 404)
    if dt.end_time:
        raise DomainError("Downtime is already resolved.")
    
    dt.end_time = datetime.now(timezone.utc)
    dt.resolution = resolution
    audit(db, entity="Machine", entity_id=dt.machine_id, action="downtime_resolved", user_id=user_id)
    return dt
