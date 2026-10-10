"""Partners (suppliers & buyers) router."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from ..models import Buyer, Supplier
from .deps import Db, Params, can, paginate, like

router = APIRouter(prefix="/api/partners", tags=["partners"])


class SupplierIn(BaseModel):
    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    gstin: str | None = None


class BuyerIn(BaseModel):
    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    gstin: str | None = None
    credit_days: int = 30


def _sup_out(s: Supplier) -> dict:
    return {"id": s.id, "name": s.name, "contact_name": s.contact_name,
            "phone": s.phone, "email": s.email, "gstin": s.gstin, "is_active": s.is_active}


def _buy_out(b: Buyer) -> dict:
    return {"id": b.id, "name": b.name, "contact_name": b.contact_name,
            "phone": b.phone, "email": b.email, "gstin": b.gstin,
            "credit_days": b.credit_days, "is_active": b.is_active}


@router.get("/suppliers")
def list_suppliers(db: Db, _: can("partners.read"), params: Params) -> dict:
    stmt = select(Supplier).where(Supplier.is_active.is_(True))
    if params.q:
        stmt = stmt.where(Supplier.name.ilike(like(params.q)))
    return paginate(db, stmt, params, _sup_out, default_sort=[Supplier.name])


@router.post("/suppliers", status_code=201)
def create_supplier(body: SupplierIn, db: Db, _: can("partners.write")) -> dict:
    s = Supplier(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return _sup_out(s)


@router.get("/buyers")
def list_buyers(db: Db, _: can("partners.read"), params: Params) -> dict:
    stmt = select(Buyer).where(Buyer.is_active.is_(True))
    if params.q:
        stmt = stmt.where(Buyer.name.ilike(like(params.q)))
    return paginate(db, stmt, params, _buy_out, default_sort=[Buyer.name])


@router.post("/buyers", status_code=201)
def create_buyer(body: BuyerIn, db: Db, _: can("partners.write")) -> dict:
    b = Buyer(**body.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)
    return _buy_out(b)
