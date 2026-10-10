"""Dispatch and invoice service."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from mill.models import (
    Dispatch, DispatchRoll, DispatchStatus, Invoice, InvoiceStatus,
    NumberSequence, Roll, RollStatus, StockMoveKind,
)
from mill.services import stock as stock_svc

FABRIC_STORE_LOCATION_ID = 2


def _next_seq(db: Session, name: str, prefix: str) -> str:
    seq = db.query(NumberSequence).filter(NumberSequence.name == name).with_for_update().first()
    if seq is None:
        seq = NumberSequence(name=name, last_value=0)
        db.add(seq)
    seq.last_value += 1
    return f"{prefix}-{seq.last_value:06d}"


def confirm_dispatch(db: Session, dispatch_id: int, user_id: int) -> Dispatch:
    """
    Atomic confirmation:
    1. Check every roll is in_store
    2. Post fabric_out stock moves
    3. Mark rolls dispatched
    4. Create invoice from roll lengths × price_per_metre
    """
    dispatch = db.query(Dispatch).filter(Dispatch.id == dispatch_id).first()
    if dispatch is None:
        raise ValueError("Dispatch not found")
    if dispatch.status == DispatchStatus.confirmed:
        raise ValueError("Dispatch already confirmed")

    drolls = dispatch.dispatch_rolls
    if not drolls:
        raise ValueError("No rolls on this dispatch")

    total_cm = 0
    for dr in drolls:
        roll = dr.roll
        if roll.status != RollStatus.in_store:
            raise ValueError(f"Roll {roll.roll_no} is not in_store (status: {roll.status})")
        total_cm += roll.length_cm

    # Post stock-out and mark dispatched
    for dr in drolls:
        roll = dr.roll
        stock_svc.post_move(
            db,
            item_id=roll.order.item_id,
            location_id=FABRIC_STORE_LOCATION_ID,
            quantity_delta=-roll.length_cm,
            kind=StockMoveKind.fabric_out,
            reference_id=dispatch_id,
            reference_type="dispatch",
            user_id=user_id,
            note=f"Dispatched roll {roll.roll_no}",
        )
        roll.status = RollStatus.dispatched

    # Create invoice
    total_metres = total_cm // 100
    price_per_m = dispatch.order.price_paise_per_metre
    amount_paise = total_metres * price_per_m

    invoice = Invoice(
        doc_no=_next_seq(db, "invoice_no", "INV"),
        buyer_id=dispatch.buyer_id,
        dispatch_id=dispatch.id,
        amount_paise=amount_paise,
        invoice_date=dispatch.dispatch_date,
        status=InvoiceStatus.unpaid,
        created_by=user_id,
    )
    db.add(invoice)
    dispatch.status = DispatchStatus.confirmed
    return dispatch


def record_buyer_payment(
    db: Session,
    invoice_id: int,
    amount_paise: int,
    payment_date: date,
    method: Optional[str],
    reference: Optional[str],
    user_id: int,
):
    from mill.models import BuyerPayment
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        raise ValueError("Invoice not found")

    paid_so_far = sum(p.amount_paise for p in invoice.payments)
    outstanding = invoice.amount_paise - paid_so_far
    if amount_paise > outstanding:
        raise ValueError(
            f"Payment ₹{amount_paise/100:.2f} exceeds outstanding ₹{outstanding/100:.2f}"
        )

    payment = BuyerPayment(
        invoice_id=invoice_id,
        amount_paise=amount_paise,
        payment_date=payment_date,
        method=method,
        reference=reference,
        created_by=user_id,
    )
    db.add(payment)

    new_paid = paid_so_far + amount_paise
    if new_paid >= invoice.amount_paise:
        invoice.status = InvoiceStatus.paid
    elif new_paid > 0:
        invoice.status = InvoiceStatus.partial

    return payment


def record_supplier_payment(
    db: Session,
    bill_id: int,
    amount_paise: int,
    payment_date: date,
    method: Optional[str],
    reference: Optional[str],
    user_id: int,
):
    from mill.models import BillStatus, SupplierBill, SupplierPayment
    bill = db.query(SupplierBill).filter(SupplierBill.id == bill_id).first()
    if bill is None:
        raise ValueError("Supplier bill not found")

    paid_so_far = sum(p.amount_paise for p in bill.payments)
    outstanding = bill.amount_paise - paid_so_far
    if amount_paise > outstanding:
        raise ValueError(
            f"Payment exceeds outstanding ₹{outstanding/100:.2f}"
        )

    payment = SupplierPayment(
        bill_id=bill_id,
        amount_paise=amount_paise,
        payment_date=payment_date,
        method=method,
        reference=reference,
        created_by=user_id,
    )
    db.add(payment)

    new_paid = paid_so_far + amount_paise
    if new_paid >= bill.amount_paise:
        bill.status = BillStatus.paid
    elif new_paid > 0:
        bill.status = BillStatus.partial

    return payment
