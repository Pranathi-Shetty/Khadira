"""Stock ledger service — all stock changes go through post_move."""
from __future__ import annotations

from sqlalchemy.orm import Session

from mill.models import Item, StockLevel, StockMove, StockMoveKind


def post_move(
    db: Session,
    *,
    item_id: int,
    location_id: int,
    quantity_delta: int,   # positive = in, negative = out (grams or cm)
    unit_cost_paise: int = 0,
    kind: StockMoveKind,
    reference_id: int | None = None,
    reference_type: str | None = None,
    user_id: int | None = None,
    note: str | None = None,
) -> StockMove:
    """
    Write a StockMove row and update StockLevel.
    The CHECK constraint on stock_levels.quantity prevents going negative.
    If the item has no StockLevel yet, one is created here.
    """
    level = db.query(StockLevel).filter(StockLevel.item_id == item_id).first()
    if level is None:
        level = StockLevel(item_id=item_id, location_id=location_id, quantity=0)
        db.add(level)
        db.flush()

    level.quantity += quantity_delta
    if level.quantity < 0:
        raise ValueError(f"Stock would go negative for item_id={item_id}")

    move = StockMove(
        item_id=item_id,
        location_id=location_id,
        quantity_delta=quantity_delta,
        unit_cost_paise=unit_cost_paise,
        kind=kind,
        reference_id=reference_id,
        reference_type=reference_type,
        user_id=user_id,
        note=note,
    )
    db.add(move)
    return move


def update_average_cost(db: Session, item_id: int, new_qty_grams: int, new_cost_paise: int) -> None:
    """Recalculate moving-average cost after a yarn receipt."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        return
    level = db.query(StockLevel).filter(StockLevel.item_id == item_id).first()
    old_qty = (level.quantity - new_qty_grams) if level else 0
    old_cost = item.average_cost_paise
    total_qty = old_qty + new_qty_grams
    if total_qty > 0:
        item.average_cost_paise = (old_qty * old_cost + new_qty_grams * new_cost_paise) // total_qty
