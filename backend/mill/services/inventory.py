"""Inventory service: stock moves and low-stock alerts."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ITEM_YARN, Item, Location, StockLevel, StockMove, VALID_MOVEMENT_TYPES
from .common import DomainError


def _get_or_create_level(db: Session, item_id: int, location_id: int) -> StockLevel:
    level = db.scalar(
        select(StockLevel).where(
            StockLevel.item_id == item_id,
            StockLevel.location_id == location_id,
        )
    )
    if level is None:
        level = StockLevel(item_id=item_id, location_id=location_id, qty_g=0)
        db.add(level)
        db.flush()
    return level


def post_move(
    db: Session,
    *,
    item_id: int | None = None,
    location_id: int | None = None,
    item_sku: str | None = None,
    location_code: str | None = None,
    delta_g: int,
    ref: str | None = None,
    note: str | None = None,
    movement_type: str = "adjustment",
    user_id: int | None = None,
) -> StockMove:
    """Post a stock movement. Resolves item/location by id or by sku/code."""
    if user_id is None:
        raise DomainError("user_id is required for recording stock movements.")

    if movement_type not in VALID_MOVEMENT_TYPES:
        raise DomainError(f"Invalid movement_type '{movement_type}'. Must be one of {sorted(VALID_MOVEMENT_TYPES)}.")

    if movement_type in ("receipt", "fabric_in", "yarn_return", "opening_balance") and delta_g <= 0:
        raise DomainError(f"Stock movement type '{movement_type}' must add stock (delta_g > 0), got {delta_g}.")
    if movement_type in ("yarn_issue", "fabric_out") and delta_g >= 0:
        raise DomainError(f"Stock movement type '{movement_type}' must remove stock (delta_g < 0), got {delta_g}.")
    if delta_g == 0:
        raise DomainError("Stock movement delta_g cannot be zero.")

    if item_id is None:
        if item_sku is None:
            raise ValueError("Provide item_id or item_sku")
        item = db.scalar(select(Item).where(Item.sku == item_sku))
        if item is None:
            raise DomainError(f"Item SKU {item_sku!r} not found.")
        item_id = item.id

    if location_id is None:
        if location_code is None:
            raise ValueError("Provide location_id or location_code")
        loc = db.scalar(select(Location).where(Location.code == location_code))
        if loc is None:
            raise DomainError(f"Location code {location_code!r} not found.")
        location_id = loc.id

    level = _get_or_create_level(db, item_id, location_id)
    new_qty = level.qty_g + delta_g
    if new_qty < 0:
        raise DomainError("Stock would go negative.")
    level.qty_g = new_qty

    move = StockMove(
        item_id=item_id,
        location_id=location_id,
        delta_g=delta_g,
        ref=ref,
        note=note,
        movement_type=movement_type,
        user_id=user_id,
    )
    db.add(move)
    
    # Check for low stock alert
    if delta_g < 0:
        # We need the item to get the reorder point
        item = db.get(Item, item_id)
        if item and item.reorder_point_kg > 0:
            total_stock = sum(sl.qty_g for sl in db.scalars(select(StockLevel).where(StockLevel.item_id == item.id)).all())
            # total_stock has just been updated since level is attached to session
            if total_stock <= item.reorder_point_kg:
                from .notifications import create_notification
                create_notification(
                    db,
                    message=f"Low stock alert for {item.name} ({item.sku}). Current: {total_stock/1000}kg, Reorder at: {item.reorder_point_kg/1000}kg.",
                    event_type="low_stock",
                    recipient_role="store",
                    entity_type="Item",
                    entity_id=item.id
                )

    return move


def stock_for(db: Session, item_id: int, location_id: int) -> int:
    level = db.scalar(
        select(StockLevel).where(
            StockLevel.item_id == item_id,
            StockLevel.location_id == location_id,
        )
    )
    return level.qty_g if level else 0


def low_stock_yarn(db: Session) -> list[dict]:
    items = db.scalars(
        select(Item).where(Item.item_type == ITEM_YARN, Item.is_active.is_(True))
    ).all()
    alerts = []
    for item in items:
        total = sum(
            sl.qty_g
            for sl in db.scalars(select(StockLevel).where(StockLevel.item_id == item.id)).all()
        )
        if total <= item.reorder_point_kg:
            alerts.append({
                "item_id": item.id,
                "sku": item.sku,
                "name": item.name,
                "stock_kg": round(total / 1000, 3),
                "reorder_kg": round(item.reorder_point_kg / 1000, 3),
            })
    return alerts

def create_stock_count(db: Session, location_id: int, counts: list[dict], user_id: int | None):
    from ..models.core import StockCountSession, StockCountLine
    session = StockCountSession(location_id=location_id, counter_id=user_id)
    db.add(session)
    db.flush()
    
    for c in counts:
        item_id = c["item_id"]
        counted_qty = c["counted_qty_g"]
        reason = c.get("reason")
        sys_qty = stock_for(db, item_id, location_id)
        variance = counted_qty - sys_qty
        
        line = StockCountLine(
            session_id=session.id,
            item_id=item_id,
            system_qty_g=sys_qty,
            counted_qty_g=counted_qty,
            variance_g=variance,
            reason=reason
        )
        db.add(line)
    
    from .common import audit
    audit(db, entity="StockCountSession", entity_id=session.id, action="create", user_id=user_id)
    return session


def approve_stock_count(db: Session, session_id: int, user_id: int | None):
    from ..models.core import StockCountSession
    from datetime import datetime, timezone
    from .common import audit
    
    session = db.get(StockCountSession, session_id)
    if not session:
        raise DomainError("Stock count session not found.")
    if session.status != "draft":
        raise DomainError("Only draft sessions can be approved.")
        
    session.status = "approved"
    session.approver_id = user_id
    session.approved_at = datetime.now(timezone.utc)
    
    # Apply variances through ledger
    for line in session.lines:
        if line.variance_g != 0:
            post_move(
                db,
                item_id=line.item_id,
                location_id=session.location_id,
                delta_g=line.variance_g,
                ref=f"STOCKCOUNT-{session.id}",
                note=line.reason or "Stock count variance",
                movement_type="adjustment",
                user_id=user_id,
            )
            
    audit(db, entity="StockCountSession", entity_id=session.id, action="approve", user_id=user_id)
    return session

