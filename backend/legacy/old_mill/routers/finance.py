"""Finance router: invoices, buyer payments, supplier bills and payments."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mill.auth import can, get_current_user
from mill.database import get_db
from mill.models import (
    BuyerPayment, Buyer, Invoice, InvoiceStatus,
    NumberSequence, SupplierBill, SupplierPayment, User,
)
from mill.services.dispatch import record_buyer_payment, record_supplier_payment

router = APIRouter(prefix="/api/finance", tags=["finance"])


class PaymentIn(BaseModel):
    amount_paise: int
    payment_date: date
    method: Optional[str] = None
    reference: Optional[str] = None


class BillIn(BaseModel):
    supplier_id: int
    purchase_order_id: int
    amount_paise: int
    bill_date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None


def _next_bill_no(db: Session) -> str:
    seq = db.query(NumberSequence).filter(NumberSequence.name == "bill_no").with_for_update().first()
    if seq is None:
        seq = NumberSequence(name="bill_no", last_value=0)
        db.add(seq)
    seq.last_value += 1
    return f"BILL-{seq.last_value:06d}"


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

@router.get("/invoices")
def list_invoices(
    buyer_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(can("finance.read")),
):
    q = db.query(Invoice)
    if buyer_id:
        q = q.filter(Invoice.buyer_id == buyer_id)
    if status:
        q = q.filter(Invoice.status == status)
    invoices = q.order_by(Invoice.id.desc()).all()
    return [
        {
            "id": inv.id, "doc_no": inv.doc_no, "buyer": inv.buyer.name,
            "amount_paise": inv.amount_paise, "invoice_date": inv.invoice_date,
            "due_date": inv.due_date, "status": inv.status,
            "paid_paise": sum(p.amount_paise for p in inv.payments),
            "outstanding_paise": inv.amount_paise - sum(p.amount_paise for p in inv.payments),
        }
        for inv in invoices
    ]


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db), _=Depends(can("finance.read"))):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return {
        "id": inv.id, "doc_no": inv.doc_no, "buyer_id": inv.buyer_id,
        "buyer": inv.buyer.name, "dispatch_id": inv.dispatch_id,
        "amount_paise": inv.amount_paise, "invoice_date": inv.invoice_date,
        "due_date": inv.due_date, "status": inv.status,
        "paid_paise": sum(p.amount_paise for p in inv.payments),
        "outstanding_paise": inv.amount_paise - sum(p.amount_paise for p in inv.payments),
        "payments": [
            {
                "id": p.id, "amount_paise": p.amount_paise,
                "payment_date": p.payment_date, "method": p.method,
                "reference": p.reference,
            }
            for p in inv.payments
        ],
    }


@router.post("/invoices/{invoice_id}/payments")
def add_buyer_payment(
    invoice_id: int,
    body: PaymentIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("finance.write")),
):
    try:
        payment = record_buyer_payment(
            db,
            invoice_id=invoice_id,
            amount_paise=body.amount_paise,
            payment_date=body.payment_date,
            method=body.method,
            reference=body.reference,
            user_id=user.id,
        )
        db.commit()
        return {"id": payment.id, "ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# Supplier Bills
# ---------------------------------------------------------------------------

@router.get("/bills")
def list_bills(
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(can("finance.read")),
):
    q = db.query(SupplierBill)
    if supplier_id:
        q = q.filter(SupplierBill.supplier_id == supplier_id)
    if status:
        q = q.filter(SupplierBill.status == status)
    bills = q.order_by(SupplierBill.id.desc()).all()
    return [
        {
            "id": b.id, "doc_no": b.doc_no, "supplier": b.supplier.name,
            "amount_paise": b.amount_paise, "bill_date": b.bill_date,
            "due_date": b.due_date, "status": b.status,
            "paid_paise": sum(p.amount_paise for p in b.payments),
            "outstanding_paise": b.amount_paise - sum(p.amount_paise for p in b.payments),
        }
        for b in bills
    ]


@router.post("/bills")
def create_bill(
    body: BillIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("finance.write")),
):
    bill = SupplierBill(
        doc_no=_next_bill_no(db),
        supplier_id=body.supplier_id,
        purchase_order_id=body.purchase_order_id,
        amount_paise=body.amount_paise,
        bill_date=body.bill_date,
        due_date=body.due_date,
        notes=body.notes,
        created_by=user.id,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return {"id": bill.id, "doc_no": bill.doc_no}


@router.post("/bills/{bill_id}/payments")
def add_supplier_payment(
    bill_id: int,
    body: PaymentIn,
    db: Session = Depends(get_db),
    user: User = Depends(can("finance.write")),
):
    try:
        payment = record_supplier_payment(
            db,
            bill_id=bill_id,
            amount_paise=body.amount_paise,
            payment_date=body.payment_date,
            method=body.method,
            reference=body.reference,
            user_id=user.id,
        )
        db.commit()
        return {"id": payment.id, "ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# Receivables / Payables summary
# ---------------------------------------------------------------------------

@router.get("/receivables")
def receivables_summary(db: Session = Depends(get_db), _=Depends(can("finance.read"))):
    invoices = db.query(Invoice).filter(Invoice.status != InvoiceStatus.paid).all()
    total_outstanding = sum(
        inv.amount_paise - sum(p.amount_paise for p in inv.payments)
        for inv in invoices
    )
    return {
        "total_outstanding_paise": total_outstanding,
        "count": len(invoices),
        "invoices": [
            {
                "id": inv.id, "doc_no": inv.doc_no, "buyer": inv.buyer.name,
                "outstanding_paise": inv.amount_paise - sum(p.amount_paise for p in inv.payments),
                "due_date": inv.due_date, "status": inv.status,
            }
            for inv in invoices
        ],
    }


@router.get("/payables")
def payables_summary(db: Session = Depends(get_db), _=Depends(can("finance.read"))):
    from mill.models import BillStatus
    bills = db.query(SupplierBill).filter(SupplierBill.status != BillStatus.paid).all()
    total_outstanding = sum(
        b.amount_paise - sum(p.amount_paise for p in b.payments)
        for b in bills
    )
    return {
        "total_outstanding_paise": total_outstanding,
        "count": len(bills),
        "bills": [
            {
                "id": b.id, "doc_no": b.doc_no, "supplier": b.supplier.name,
                "outstanding_paise": b.amount_paise - sum(p.amount_paise for p in b.payments),
                "due_date": b.due_date, "status": b.status,
            }
            for b in bills
        ],
    }
