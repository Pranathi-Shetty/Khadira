"""Partners router: suppliers and buyers."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mill.auth import can, get_current_user
from mill.database import get_db
from mill.models import Buyer, Supplier, User

router = APIRouter(prefix="/api/partners", tags=["partners"])


class SupplierIn(BaseModel):
    name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    payment_terms_days: int = 30


class BuyerIn(BaseModel):
    name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    payment_terms_days: int = 30


@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db), _=Depends(can("partners.read"))):
    return db.query(Supplier).filter(Supplier.is_active == True).all()


@router.post("/suppliers")
def create_supplier(
    body: SupplierIn,
    db: Session = Depends(get_db),
    _=Depends(can("partners.write")),
):
    s = Supplier(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "name": s.name}


@router.get("/buyers")
def list_buyers(db: Session = Depends(get_db), _=Depends(can("partners.read"))):
    return db.query(Buyer).filter(Buyer.is_active == True).all()


@router.post("/buyers")
def create_buyer(
    body: BuyerIn,
    db: Session = Depends(get_db),
    _=Depends(can("partners.write")),
):
    b = Buyer(**body.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)
    return {"id": b.id, "name": b.name}
