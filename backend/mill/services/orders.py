"""Orders service: buyer orders, yarn sufficiency check."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ITEM_FABRIC, ITEM_YARN, Item, Location, Order, OrderLine, StockLevel
from .common import DomainError, audit


def _next_order_ref(db: Session) -> str:
    from sqlalchemy import func
    count = db.scalar(select(func.count()).select_from(Order)) or 0
    return f"ORD-{date.today().year}-{count + 1:05d}"


def create_order(db: Session, *, buyer_id: int, order_date: date,
                 delivery_date: date | None, lines: list[dict],
                 notes: str | None, user_id: int | None) -> Order:
    for line in lines:
        item = db.get(Item, line["item_id"])
        if item is None or item.item_type != ITEM_FABRIC:
            raise DomainError("Orders may only contain fabric items.")

    order = Order(
        ref=_next_order_ref(db),
        buyer_id=buyer_id,
        order_date=order_date,
        delivery_date=delivery_date,
        notes=notes,
        status="draft",
    )
    db.add(order)
    db.flush()
    for line in lines:
        db.add(OrderLine(
            order_id=order.id,
            item_id=line["item_id"],
            qty_meters=line["qty_meters"],
            rate_per_meter_paise=line["rate_per_meter_paise"],
        ))
    audit(db, entity="Order", entity_id=order.id, action="create", user_id=user_id)
    return order


def yarn_needed_g(db: Session, order: Order) -> int:
    """Total yarn grams needed for all fabric lines in the order."""
    total = 0
    for line in order.lines:
        item = db.get(Item, line.item_id)
        if item and item.yarn_kg_per_meter:
            total += int(float(item.yarn_kg_per_meter) * float(line.qty_meters) * 1000)
    return total


def yarn_available_g(db: Session) -> int:
    """Total yarn in all locations."""
    from ..models import ITEM_YARN
    yarn_items = db.scalars(select(Item).where(Item.item_type == ITEM_YARN)).all()
    ids = {i.id for i in yarn_items}
    if not ids:
        return 0
    levels = db.scalars(select(StockLevel).where(StockLevel.item_id.in_(ids))).all()
    return sum(l.qty_g for l in levels)


def confirm_order(db: Session, order_id: int, user_id: int | None) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError("Order not found.", 404)
    if order.status != "draft":
        raise DomainError(f"Cannot confirm an order in status '{order.status}'.")

    needed = yarn_needed_g(db, order)
    available = yarn_available_g(db)
    if needed > available:
        raise DomainError(
            f"Insufficient yarn. Need {needed/1000:.1f} kg, have {available/1000:.1f} kg."
        )

    order.status = "confirmed"
    audit(db, entity="Order", entity_id=order.id, action="confirm", user_id=user_id)
    return order


def cancel_order(db: Session, order_id: int, user_id: int | None) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError("Order not found.", 404)
    if order.status not in ("draft", "confirmed"):
        raise DomainError(f"Cannot cancel an order in status '{order.status}'.")
    order.status = "cancelled"
    audit(db, entity="Order", entity_id=order.id, action="cancel", user_id=user_id)
    return order
