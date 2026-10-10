"""Purchasing router: purchase orders and yarn receipts."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mill.auth import can, get_current_user
from mill.database import get_db
from mill.models import (
    Item, NumberSequence, PurchaseOrder, PurchaseOrderStatus,
    StockMoveKind, SupplierBill, User, YarnLot, YarnReceipt,
)
from mill.services import stock as stock_svc

router = APIRouter(prefix="/api/purchasing", tags=["purchasing"])

RAW_STORE_LOCATION_ID = 1


def _next_po_no(db: Session) -> str:
    seq = db.query(NumberSequence).filter(NumberSequence.name == "po_no").with_for_update().first()
    if seq is None:
        seq = NumberSequence(name="po_no", last_value=0)
        db.add(seq)
    seq.last_value += 1
    return f"PO-{seq.last_value:06d}"


class POIn(BaseModel):
    supplier_id: int
    item_id: int
    quantity_grams: int
    unit_cost_paise: int
    expected_date: Optional[date] = None
    notes: Optional[str] = None


class ReceiptIn(BaseModel):
    received_grams: int
    unit_cost_paise: int
    received_date: date
    lot_no: Optional[str] = None


@router.get("/")
def list_pos(db: Session = Depends(get_db), _=Depends(can("purchasing.read"))):
    pos = db.query(PurchaseOrder).order_by(PurchaseOrder.id.desc()).all()
    return [
        {
            "id": p.id, "doc_no": p.doc_no, "supplier": p.supplier.name,
            "item": p.item.name, "quantity_kg": p.quantity_grams / 1000,
            "unit_cost_paise": p.unit_cost_paise, "status": p.status,
            "expected_date": p.expected_date,
        }
        for p in pos
    ]


@router.post("/")
def create_po(
    body: POIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("purchasing.write")),
):
    po = PurchaseOrder(
        doc_no=_next_po_no(db),
        supplier_id=body.supplier_id,
        item_id=body.item_id,
        quantity_grams=body.quantity_grams,
        unit_cost_paise=body.unit_cost_paise,
        expected_date=body.expected_date,
        notes=body.notes,
        status=PurchaseOrderStatus.draft,
        created_by=user.id,
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    return {"id": po.id, "doc_no": po.doc_no}


@router.post("/{po_id}/confirm")
def confirm_po(po_id: int, db: Session = Depends(get_db), _=Depends(can("purchasing.write"))):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "PO not found")
    if po.status != PurchaseOrderStatus.draft:
        raise HTTPException(400, f"Cannot confirm PO in status {po.status}")
    po.status = PurchaseOrderStatus.confirmed
    db.commit()
    return {"ok": True}


@router.post("/{po_id}/receive")
def receive_yarn(
    po_id: int,
    body: ReceiptIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("purchasing.write")),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "PO not found")
    if po.status not in (PurchaseOrderStatus.confirmed, PurchaseOrderStatus.received):
        raise HTTPException(400, "PO must be confirmed before receiving")

    # Create receipt
    receipt = YarnReceipt(
        purchase_order_id=po.id,
        received_grams=body.received_grams,
        unit_cost_paise=body.unit_cost_paise,
        received_date=body.received_date,
        lot_no=body.lot_no,
        received_by=user.id,
    )
    db.add(receipt)
    db.flush()

    # Create yarn lot
    import uuid
    lot_no = body.lot_no or f"LOT-{receipt.id:06d}"
    yarn_lot = YarnLot(
        lot_no=lot_no,
        receipt_id=receipt.id,
        supplier_id=po.supplier_id,
        item_id=po.item_id,
        quantity_grams=body.received_grams,
        cost_paise=body.unit_cost_paise,
        receipt_date=body.received_date,
    )
    db.add(yarn_lot)
    db.flush()

    # Post stock move
    stock_svc.post_move(
        db,
        item_id=po.item_id,
        location_id=RAW_STORE_LOCATION_ID,
        quantity_delta=body.received_grams,
        unit_cost_paise=body.unit_cost_paise,
        kind=StockMoveKind.receipt,
        reference_id=receipt.id,
        reference_type="yarn_receipt",
        user_id=user.id,
        note=f"Yarn receipt for PO {po.doc_no}",
    )

    # Update moving average cost
    stock_svc.update_average_cost(
        db, po.item_id, body.received_grams, body.unit_cost_paise
    )

    po.status = PurchaseOrderStatus.received
    db.commit()
    return {"receipt_id": receipt.id, "lot_no": lot_no}


@router.get("/{po_id}/receipts")
def list_receipts(po_id: int, db: Session = Depends(get_db), _=Depends(can("purchasing.read"))):
    receipts = db.query(YarnReceipt).filter(YarnReceipt.purchase_order_id == po_id).all()
    return [
        {
            "id": r.id, "received_grams": r.received_grams,
            "unit_cost_paise": r.unit_cost_paise, "received_date": r.received_date,
            "lot_no": r.lot_no,
        }
        for r in receipts
    ]
