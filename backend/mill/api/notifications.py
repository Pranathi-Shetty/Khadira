"""Notifications router."""
from fastapi import APIRouter

from ..services import notifications as notif_svc
from .deps import CurrentUser, Db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _out(n) -> dict:
    return {
        "id": n.id,
        "recipient_role": n.recipient_role,
        "recipient_id": n.recipient_id,
        "entity_type": n.entity_type,
        "entity_id": n.entity_id,
        "event_type": n.event_type,
        "message": n.message,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
def list_notifications(db: Db, user: CurrentUser, unread_only: bool = False) -> list:
    items = notif_svc.list_notifications(
        db, user_id=user.id, role=user.role, unread_only=unread_only
    )
    return [_out(n) for n in items]


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, db: Db, _: CurrentUser) -> dict:
    ok = notif_svc.mark_as_read(db, notification_id)
    db.commit()
    return {"ok": ok}


@router.post("/read-all")
def mark_all_read(db: Db, user: CurrentUser) -> dict:
    count = notif_svc.mark_all_read(db, user_id=user.id, role=user.role)
    db.commit()
    return {"updated": count}
