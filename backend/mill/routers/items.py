"""Items (yarn & fabric catalogue) router."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mill.auth import can
from mill.database import get_db
from mill.models import Item, ItemType, StockLevel

router = APIRouter(prefix="/api/items", tags=["items"])


class ItemIn(BaseModel):
    sku: str
    name: str
    item_type: ItemType
    yarn_type: Optional[str] = None
    colour: Optional[str] = None
    unit: str
    yarn_grams_per_metre: Optional[int] = None
    reorder_point_grams: int = 0
    sale_price_paise_per_metre: int = 0


class ItemOut(BaseModel):
    id: int
    sku: str
    name: str
    item_type: str
    yarn_type: Optional[str]
    colour: Optional[str]
    unit: str
    yarn_grams_per_metre: Optional[int]
    average_cost_paise: int
    reorder_point_grams: int
    sale_price_paise_per_metre: int
    is_active: bool
    stock_quantity: Optional[int] = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[ItemOut])
def list_items(
    item_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(can("items.read")),
):
    q = db.query(Item).filter(Item.is_active == True)
    if item_type:
        q = q.filter(Item.item_type == item_type)
    items = q.all()
    result = []
    for item in items:
        d = ItemOut.model_validate(item)
        if item.stock_level:
            d.stock_quantity = item.stock_level.quantity
        result.append(d)
    return result


@router.post("/", response_model=ItemOut)
def create_item(
    body: ItemIn,
    db: Session = Depends(get_db),
    _=Depends(can("items.write")),
):
    existing = db.query(Item).filter(Item.sku == body.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")
    item = Item(**body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db), _=Depends(can("items.read"))):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    d = ItemOut.model_validate(item)
    if item.stock_level:
        d.stock_quantity = item.stock_level.quantity
    return d


@router.patch("/{item_id}")
def update_item(
    item_id: int,
    body: dict,
    db: Session = Depends(get_db),
    _=Depends(can("items.write")),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    allowed = {"name", "yarn_type", "colour", "reorder_point_grams", "sale_price_paise_per_metre", "is_active"}
    for k, v in body.items():
        if k in allowed:
            setattr(item, k, v)
    db.commit()
    return {"ok": True}
