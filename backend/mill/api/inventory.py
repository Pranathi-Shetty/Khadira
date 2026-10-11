"""Inventory & stock count router."""
from fastapi import APIRouter
from pydantic import BaseModel

from ..models import Item
from ..services import inventory as inv_svc
from .deps import CurrentUser, Db, can

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


class CountLineIn(BaseModel):
    item_id: int
    counted_qty_g: int
    reason: str | None = None


class StockCountIn(BaseModel):
    location_id: int
    counts: list[CountLineIn]


@router.get("/low-stock")
def low_stock_alerts(db: Db, _: can["items.read"]) -> list:
    return inv_svc.low_stock_yarn(db)


@router.get("/stock/{item_id}/{location_id}")
def get_stock(item_id: int, location_id: int, db: Db, _: can["items.read"]) -> dict:
    qty_raw = inv_svc.stock_for(db, item_id, location_id)
    item = db.get(Item, item_id)
    is_fabric = (item and item.item_type != "yarn")
    res = {
        "item_id": item_id,
        "location_id": location_id,
        "qty_g": qty_raw,  # Underlying DB column: stores grams for yarn, cm for fabric
        "qty_raw": qty_raw,
    }
    if is_fabric:
        res["unit"] = "meters"
        res["qty_cm"] = qty_raw
        res["quantity_m"] = round(qty_raw / 100, 2)
    else:
        res["unit"] = "kg"
        res["qty_kg"] = round(qty_raw / 1000, 3)
    return res


@router.post("/counts", status_code=201)
def create_count_session(body: StockCountIn, db: Db, user: can["items.write"]) -> dict:
    counts_data = [line.model_dump() for line in body.counts]
    session = inv_svc.create_stock_count(db, location_id=body.location_id, counts=counts_data, user_id=user.id)
    db.commit()
    return {
        "id": session.id,
        "location_id": session.location_id,
        "status": session.status,
        "line_count": len(session.lines),
    }


@router.post("/counts/{session_id}/approve")
def approve_count_session(session_id: int, db: Db, user: can["items.write"]) -> dict:
    session = inv_svc.approve_stock_count(db, session_id=session_id, user_id=user.id)
    db.commit()
    return {
        "id": session.id,
        "location_id": session.location_id,
        "status": session.status,
        "approved_at": session.approved_at.isoformat() if session.approved_at else None,
    }
