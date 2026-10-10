"""QC service: inspect rolls."""

from sqlalchemy.orm import Session

from ..models import Roll, RollEvent
from .common import DomainError, audit


def inspect_roll(db: Session, roll_id: int, verdict: str,
                 grade: str | None, note: str | None,
                 user_id: int | None) -> Roll:
    roll = db.get(Roll, roll_id)
    if roll is None:
        raise DomainError("Roll not found.", 404)
    if roll.status not in ("awaiting_qc", "held"):
        raise DomainError(f"Roll is not awaiting QC (status: {roll.status}).")
    if verdict not in ("passed", "failed", "held"):
        raise DomainError("Verdict must be passed, failed or held.")

    roll.status = verdict
    if grade:
        roll.qc_grade = grade
    db.add(RollEvent(roll_id=roll.id, event_type=f"qc_{verdict}",
                     note=note, created_by_id=user_id))
    audit(db, entity="Roll", entity_id=roll.id, action=f"qc_{verdict}", user_id=user_id)
    return roll


def move_to_store(db: Session, roll_id: int, user_id: int | None) -> Roll:
    """Move a QC-passed roll to in_store and post a fabric_in stock move."""
    from sqlalchemy import select
    from ..models import Location
    from .inventory import post_move

    roll = db.get(Roll, roll_id)
    if roll is None:
        raise DomainError("Roll not found.", 404)
    if roll.status != "passed":
        raise DomainError("Only QC-passed rolls can be moved to store.")

    loc = db.scalar(select(Location).where(Location.code == "FIN"))
    if loc is None:
        raise DomainError("Location FIN not found.")

    post_move(db, item_id=roll.item_id, location_id=loc.id,
              delta_g=roll.length_cm, ref=roll.roll_number, note="fabric_in")

    roll.status = "in_store"
    db.add(RollEvent(roll_id=roll.id, event_type="moved_to_store", created_by_id=user_id))
    audit(db, entity="Roll", entity_id=roll.id, action="in_store", user_id=user_id)
    return roll


def record_defect(db: Session, roll_id: int, defect_type: str, severity: str,
                  location_m: int | None, notes: str | None,
                  user_id: int | None):
    from ..models.production import RollDefect
    
    roll = db.get(Roll, roll_id)
    if roll is None:
        raise DomainError("Roll not found.", 404)
        
    defect = RollDefect(
        roll_id=roll.id,
        defect_type=defect_type,
        severity=severity,
        location_m=location_m,
        notes=notes,
        created_by_id=user_id
    )
    db.add(defect)
    db.add(RollEvent(roll_id=roll.id, event_type="defect_recorded",
                     note=f"{severity} {defect_type}", created_by_id=user_id))
    audit(db, entity="Roll", entity_id=roll.id, action="defect_recorded", user_id=user_id)
    return defect

