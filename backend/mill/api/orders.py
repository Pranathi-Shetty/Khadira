"""Orders router: buyer fabric orders."""

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..models import Order
from ..services import orders as svc
from .deps import Db, Params, can, paginate

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderLineIn(BaseModel):
    item_id: int
    qty_meters: float = Field(gt=0)
    rate_per_meter_paise: int = Field(gt=0)


class OrderIn(BaseModel):
    buyer_id: int
    order_date: date
    delivery_date: date | None = None
    lines: list[OrderLineIn] = Field(min_length=1)
    notes: str | None = None


def _out(o: Order) -> dict:
    return {
        "id": o.id, "ref": o.ref, "buyer_id": o.buyer_id,
        "buyer_name": o.buyer.name,
        "order_date": str(o.order_date),
        "delivery_date": str(o.delivery_date) if o.delivery_date else None,
        "status": o.status, "notes": o.notes,
        "lines": [{"id": l.id, "item_id": l.item_id, "qty_meters": float(l.qty_meters),
                   "rate_per_meter_paise": l.rate_per_meter_paise} for l in o.lines],
    }


@router.get("")
def list_orders(db: Db, _: can("orders.read"), params: Params,
                status: str | None = None) -> dict:
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == status)
    stmt = stmt.order_by(Order.id.desc())
    return paginate(db, stmt, params, _out)


@router.post("", status_code=201)
def create_order(body: OrderIn, db: Db, user: can("orders.write")) -> dict:
    order = svc.create_order(db, buyer_id=body.buyer_id, order_date=body.order_date,
                             delivery_date=body.delivery_date,
                             lines=[l.model_dump() for l in body.lines],
                             notes=body.notes, user_id=user.id)
    db.commit()
    db.refresh(order)
    return _out(order)


@router.get("/{order_id}")
def get_order(order_id: int, db: Db, _: can("orders.read")) -> dict:
    from ..services.common import DomainError
    o = db.get(Order, order_id)
    if o is None:
        raise DomainError("Order not found.", 404)
    return _out(o)


@router.post("/{order_id}/confirm")
def confirm_order(order_id: int, db: Db, user: can("orders.write")) -> dict:
    o = svc.confirm_order(db, order_id, user.id)
    db.commit()
    return _out(o)


@router.post("/{order_id}/cancel")
def cancel_order(order_id: int, db: Db, user: can("orders.write")) -> dict:
    o = svc.cancel_order(db, order_id, user.id)
    db.commit()
    return _out(o)
