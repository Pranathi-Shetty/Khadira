"""Purchasing router: POs, yarn receipts."""

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..models import PurchaseOrder
from ..services import purchasing as svc
from .deps import Db, Params, can, paginate

router = APIRouter(prefix="/api/purchasing", tags=["purchasing"])


class POLineIn(BaseModel):
    item_id: int
    qty_kg: float = Field(gt=0)
    rate_per_kg_paise: int = Field(gt=0)


class POIn(BaseModel):
    supplier_id: int
    order_date: date
    expected_date: date | None = None
    lines: list[POLineIn] = Field(min_length=1)
    notes: str | None = None


class ReceiptIn(BaseModel):
    po_line_id: int
    received_date: date
    qty_kg: float = Field(gt=0)
    vehicle_no: str | None = None
    notes: str | None = None
    lot_number: str
    location_code: str = "RAW"


def _po_out(po: PurchaseOrder) -> dict:
    return {
        "id": po.id, "ref": po.ref, "supplier_id": po.supplier_id,
        "supplier_name": po.supplier.name,
        "order_date": str(po.order_date), "expected_date": str(po.expected_date) if po.expected_date else None,
        "status": po.status, "notes": po.notes,
        "lines": [{"id": l.id, "item_id": l.item_id, "qty_kg": float(l.qty_kg),
                   "rate_per_kg_paise": l.rate_per_kg_paise,
                   "received_kg": float(l.received_kg or 0)} for l in po.lines],
    }


@router.get("")
def list_pos(db: Db, _: can("purchasing.read"), params: Params) -> dict:
    stmt = select(PurchaseOrder).order_by(PurchaseOrder.id.desc())
    return paginate(db, stmt, params, _po_out)


@router.post("", status_code=201)
def create_po(body: POIn, db: Db, user: can("purchasing.write")) -> dict:
    po = svc.create_po(db, supplier_id=body.supplier_id, order_date=body.order_date,
                       expected_date=body.expected_date,
                       lines=[l.model_dump() for l in body.lines],
                       notes=body.notes, user_id=user.id)
    db.commit()
    db.refresh(po)
    return _po_out(po)


@router.get("/{po_id}")
def get_po(po_id: int, db: Db, _: can("purchasing.read")) -> dict:
    from ..services.common import DomainError
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise DomainError("PO not found.", 404)
    return _po_out(po)


@router.post("/{po_id}/confirm")
def confirm_po(po_id: int, db: Db, user: can("purchasing.write")) -> dict:
    po = svc.confirm_po(db, po_id, user.id)
    db.commit()
    return _po_out(po)


@router.post("/{po_id}/cancel")
def cancel_po(po_id: int, db: Db, user: can("purchasing.write")) -> dict:
    po = svc.cancel_po(db, po_id, user.id)
    db.commit()
    return _po_out(po)


@router.post("/{po_id}/receive", status_code=201)
def receive_yarn(po_id: int, body: ReceiptIn, db: Db, user: can("purchasing.write")) -> dict:
    receipt = svc.receive_yarn(
        db, po_id=po_id, po_line_id=body.po_line_id,
        received_date=body.received_date, qty_kg=body.qty_kg,
        vehicle_no=body.vehicle_no, notes=body.notes,
        lot_number=body.lot_number, location_code=body.location_code,
        user_id=user.id,
    )
    db.commit()
    return {"id": receipt.id, "po_id": po_id, "qty_kg": float(receipt.qty_kg),
            "lot_number": body.lot_number}
