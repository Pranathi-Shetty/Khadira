"""Notification service: create, list, and mark notifications as read."""
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from ..models.core import Notification


def create_notification(
    db: Session,
    message: str,
    event_type: str,
    recipient_role: str | None = None,
    recipient_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> Notification:
    """Create and persist a new in-app notification."""
    notif = Notification(
        message=message,
        event_type=event_type,
        recipient_role=recipient_role,
        recipient_id=recipient_id,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
    )
    db.add(notif)
    db.flush()
    return notif


def list_notifications(
    db: Session,
    user_id: int | None = None,
    role: str | None = None,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    """List notifications matching user, role, or broadcast."""
    stmt = select(Notification)
    conditions = []
    if user_id is not None:
        conditions.append(Notification.recipient_id == user_id)
    if role is not None:
        conditions.append(Notification.recipient_role == role)

    if conditions:
        conditions.append(
            (Notification.recipient_id.is_(None)) & (Notification.recipient_role.is_(None))
        )
        stmt = stmt.where(or_(*conditions))

    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))

    stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def mark_as_read(db: Session, notification_id: int) -> bool:
    """Mark a specific notification as read."""
    notif = db.get(Notification, notification_id)
    if notif:
        notif.is_read = True
        db.flush()
        return True
    return False


def mark_all_read(db: Session, user_id: int | None = None, role: str | None = None) -> int:
    """Mark all matching notifications as read."""
    stmt = update(Notification).where(Notification.is_read.is_(False)).values(is_read=True)
    if user_id is not None or role is not None:
        conds = []
        if user_id is not None:
            conds.append(Notification.recipient_id == user_id)
        if role is not None:
            conds.append(Notification.recipient_role == role)
        stmt = stmt.where(or_(*conds))
    result = db.execute(stmt)
    db.flush()
    return result.rowcount
