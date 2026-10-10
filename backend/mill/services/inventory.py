"""Inventory service: stock moves and low-stock alerts."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ITEM_YARN, Item, Location, StockLevel, StockMove
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
) -> StockMove:
    """Post a stock movement. Resolves item/location by id or by sku/code."""
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

    move = StockMove(item_id=item_id, location_id=location_id, delta_g=delta_g, ref=ref, note=note)
    db.add(move)
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
