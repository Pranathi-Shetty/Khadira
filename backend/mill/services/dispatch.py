"""Dispatch service: draft → confirm → dispatched."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Location, Roll, RollEvent
from .common import DomainError, audit
from .inventory import post_move


# We store dispatch drafts as simple dicts in a lightweight table.
# For now we handle dispatch as a service-level operation on rolls directly.

def dispatch_rolls(db: Session, roll_ids: list[int],
                   dispatch_date: date, buyer_id: int | None,
                   vehicle_no: str | None, notes: str | None,
                   user_id: int | None) -> list[Roll]:
    """Confirm dispatch of a set of in_store rolls."""
    loc = db.scalar(select(Location).where(Location.code == "FIN"))
    if loc is None:
        raise DomainError("Location FIN not found.")

    dispatched = []
    for roll_id in roll_ids:
        roll = db.get(Roll, roll_id)
        if roll is None:
            raise DomainError(f"Roll {roll_id} not found.", 404)
        if roll.status != "in_store":
            raise DomainError(f"Roll {roll.roll_number} is not in_store (status: {roll.status}).")

        # fabric_out: deduct length_cm
        post_move(db, item_id=roll.item_id, location_id=loc.id,
                  delta_g=-roll.length_cm, ref=roll.roll_number, note="fabric_out")

        roll.status = "dispatched"
        db.add(RollEvent(
            roll_id=roll.id,
            event_type="dispatched",
            note=f"vehicle={vehicle_no or '-'} date={dispatch_date}",
            created_by_id=user_id,
        ))
        audit(db, entity="Roll", entity_id=roll.id, action="dispatch", user_id=user_id)
        dispatched.append(roll)

    return dispatched
