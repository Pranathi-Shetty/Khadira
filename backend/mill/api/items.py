"""Items (yarn & fabric catalogue) router."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..models import ITEM_FABRIC, ITEM_YARN, Item
from .deps import Db, Params, can, paginate, like

router = APIRouter(prefix="/api/items", tags=["items"])


class ItemIn(BaseModel):
    sku: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=200)
    item_type: str  # yarn | fabric
    unit: str = "kg"
    count_denier: str | None = None
    gsm: int | None = None
    width_cm: int | None = None
    yarn_kg_per_meter: float | None = None
    reorder_point_kg: float = 0.0


def _out(i: Item) -> dict:
    return {
        "id": i.id, "sku": i.sku, "name": i.name,
        "item_type": i.item_type, "unit": i.unit,
        "count_denier": i.count_denier, "gsm": i.gsm,
        "width_cm": i.width_cm,
        "yarn_kg_per_meter": float(i.yarn_kg_per_meter) if i.yarn_kg_per_meter else None,
        "reorder_point_kg": round((i.reorder_point_kg or 0) / 1000, 3),
        "is_active": i.is_active,
    }


@router.get("")
def list_items(db: Db, _: can("items.read"), params: Params,
               item_type: str | None = None) -> dict:
    stmt = select(Item).where(Item.is_active.is_(True))
    if item_type:
        stmt = stmt.where(Item.item_type == item_type)
    if params.q:
        stmt = stmt.where(Item.name.ilike(like(params.q)) | Item.sku.ilike(like(params.q)))
    return paginate(db, stmt, params, _out,
                    sortable={"name": Item.name, "sku": Item.sku},
                    default_sort=[Item.name])


@router.post("", status_code=201)
def create_item(body: ItemIn, db: Db, _: can("items.write")) -> dict:
    from ..services.common import DomainError
    if body.item_type not in (ITEM_YARN, ITEM_FABRIC):
        raise DomainError("item_type must be 'yarn' or 'fabric'.")
    if body.item_type == ITEM_FABRIC and body.yarn_kg_per_meter is None:
        raise DomainError("yarn_kg_per_meter is required for fabric items.")
    existing = db.scalar(select(Item).where(Item.sku == body.sku))
    if existing:
        raise DomainError(f"SKU '{body.sku}' already exists.")
    item = Item(
        sku=body.sku, name=body.name, item_type=body.item_type, unit=body.unit,
        count_denier=body.count_denier, gsm=body.gsm, width_cm=body.width_cm,
        yarn_kg_per_meter=body.yarn_kg_per_meter,
        reorder_point_kg=int(body.reorder_point_kg * 1000),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _out(item)


@router.get("/{item_id}")
def get_item(item_id: int, db: Db, _: can("items.read")) -> dict:
    from ..services.common import DomainError
    item = db.get(Item, item_id)
    if item is None:
        raise DomainError("Item not found.", 404)
    return _out(item)


@router.patch("/{item_id}")
def update_item(item_id: int, body: dict, db: Db, _: can("items.write")) -> dict:
    from ..services.common import DomainError
    item = db.get(Item, item_id)
    if item is None:
        raise DomainError("Item not found.", 404)
    allowed = {"name", "count_denier", "gsm", "width_cm", "yarn_kg_per_meter",
               "reorder_point_kg", "is_active"}
    for k, v in body.items():
        if k in allowed:
            if k == "reorder_point_kg":
                setattr(item, k, int(v * 1000))
            else:
                setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return _out(item)
