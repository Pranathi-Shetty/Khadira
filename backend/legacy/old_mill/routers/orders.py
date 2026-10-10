"""Orders router."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mill.auth import can, get_current_user
from mill.database import get_db
from mill.models import Item, NumberSequence, Order, OrderStatus, Roll, RollStatus, User

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _next_order_no(db: Session) -> str:
    seq = db.query(NumberSequence).filter(NumberSequence.name == "order_no").with_for_update().first()
    if seq is None:
        seq = NumberSequence(name="order_no", last_value=0)
        db.add(seq)
    seq.last_value += 1
    return f"ORD-{seq.last_value:06d}"


class OrderIn(BaseModel):
    buyer_id: int
    item_id: int
    quantity_metres: int
    deadline: date
    tolerance_pct: int = 5
    price_paise_per_metre: int
    notes: Optional[str] = None


@router.get("/")
def list_orders(
    status: Optional[str] = None,
    buyer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(can("orders.read")),
):
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    if buyer_id:
        q = q.filter(Order.buyer_id == buyer_id)
    orders = q.order_by(Order.id.desc()).all()
    result = []
    for o in orders:
        passed_cm = sum(
            r.length_cm for r in o.rolls
            if r.status in (RollStatus.passed, RollStatus.in_store, RollStatus.dispatched)
        )
        progress = round((passed_cm / 100) / o.quantity_metres * 100, 1) if o.quantity_metres else 0
        result.append({
            "id": o.id, "doc_no": o.doc_no, "buyer": o.buyer.name,
            "item": o.item.name, "quantity_metres": o.quantity_metres,
            "deadline": o.deadline, "status": o.status,
            "price_paise_per_metre": o.price_paise_per_metre,
            "progress_pct": min(progress, 100),
        })
    return result


@router.post("/")
def create_order(
    body: OrderIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("orders.write")),
):
    order = Order(
        doc_no=_next_order_no(db),
        buyer_id=body.buyer_id,
        item_id=body.item_id,
        quantity_metres=body.quantity_metres,
        deadline=body.deadline,
        tolerance_pct=body.tolerance_pct,
        price_paise_per_metre=body.price_paise_per_metre,
        notes=body.notes,
        created_by=user.id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return {"id": order.id, "doc_no": order.doc_no}


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db), _=Depends(can("orders.read"))):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    roll_summary: dict[str, int] = {}
    for r in order.rolls:
        roll_summary[r.status] = roll_summary.get(r.status, 0) + 1

    passed_cm = sum(
        r.length_cm for r in order.rolls
        if r.status in (RollStatus.passed, RollStatus.in_store, RollStatus.dispatched)
    )
    progress = round((passed_cm / 100) / order.quantity_metres * 100, 1) if order.quantity_metres else 0

    return {
        "id": order.id,
        "doc_no": order.doc_no,
        "buyer_id": order.buyer_id,
        "buyer": order.buyer.name,
        "item_id": order.item_id,
        "item": order.item.name,
        "quantity_metres": order.quantity_metres,
        "deadline": order.deadline,
        "tolerance_pct": order.tolerance_pct,
        "price_paise_per_metre": order.price_paise_per_metre,
        "status": order.status,
        "progress_pct": min(progress, 100),
        "passed_metres": passed_cm // 100,
        "roll_summary": roll_summary,
        "notes": order.notes,
    }


@router.get("/{order_id}/yarn-check")
def yarn_check(order_id: int, db: Session = Depends(get_db), _=Depends(can("orders.read"))):
    """Check if sufficient yarn is available to start this order."""
    from mill.models import StockLevel
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    item = order.item
    if not item.yarn_grams_per_metre:
        return {"sufficient": True, "note": "No yarn requirement configured for this fabric"}

    required_grams = order.quantity_metres * item.yarn_grams_per_metre
    
    from mill.models import Item, ItemType
    yarns = db.query(Item).filter(
        Item.item_type == ItemType.yarn,
        Item.yarn_type == item.yarn_type,
        Item.colour == item.colour
    ).all()
    yarn_ids = [y.id for y in yarns]
    
    levels = db.query(StockLevel).filter(StockLevel.item_id.in_(yarn_ids)).all()
    available = sum(l.quantity for l in levels)
    
    shortfall = max(0, required_grams - available)
    return {
        "required_grams": required_grams,
        "available_grams": available,
        "sufficient": shortfall == 0,
        "shortfall_grams": shortfall,
    }


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    body: dict,
    db: Session = Depends(get_db),
    _=Depends(can("orders.write")),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    order.status = body.get("status", order.status)
    db.commit()
    return {"ok": True}
