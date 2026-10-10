"""Finance router: invoices and payments."""

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..models import Invoice, InvoiceLine, Payment
from .deps import Db, can

router = APIRouter(prefix="/api/finance", tags=["finance"])


class InvoiceLineIn(BaseModel):
    description: str
    qty: float
    unit_price_paise: int
    tax_pct: float = 0.0


class InvoiceIn(BaseModel):
    invoice_type: str  # sale|purchase
    buyer_id: int | None = None
    supplier_id: int | None = None
    invoice_date: date
    due_date: date | None = None
    lines: list[InvoiceLineIn] = Field(min_length=1)
    notes: str | None = None


class PaymentIn(BaseModel):
    paid_date: date
    amount_paise: int = Field(gt=0)
    method: str | None = None
    reference: str | None = None
    notes: str | None = None


def _inv_out(inv: Invoice) -> dict:
    subtotal = sum(int(l.qty) * l.unit_price_paise for l in inv.lines)
    tax = sum(int(int(l.qty) * l.unit_price_paise * l.tax_pct / 100) for l in inv.lines)
    paid = sum(p.amount_paise for p in inv.payments)
    return {
        "id": inv.id, "ref": inv.ref, "invoice_type": inv.invoice_type,
        "buyer_id": inv.buyer_id, "supplier_id": inv.supplier_id,
        "invoice_date": str(inv.invoice_date),
        "due_date": str(inv.due_date) if inv.due_date else None,
        "status": inv.status,
        "subtotal_paise": subtotal, "tax_paise": tax,
        "total_paise": subtotal + tax, "paid_paise": paid,
        "balance_paise": subtotal + tax - paid,
        "lines": [{"id": l.id, "description": l.description,
                   "qty": l.qty, "unit_price_paise": l.unit_price_paise,
                   "tax_pct": l.tax_pct} for l in inv.lines],
    }


def _next_ref(db, inv_type: str) -> str:
    from sqlalchemy import func
    year = date.today().year
    prefix = "SINV" if inv_type == "sale" else "PINV"
    count = db.scalar(select(func.count()).select_from(Invoice)
                      .where(Invoice.invoice_type == inv_type)) or 0
    return f"{prefix}-{year}-{count + 1:05d}"


@router.get("/invoices")
def list_invoices(db: Db, _: can("finance.read"),
                  inv_type: str | None = None) -> list:
    stmt = select(Invoice)
    if inv_type:
        stmt = stmt.where(Invoice.invoice_type == inv_type)
    stmt = stmt.order_by(Invoice.id.desc())
    return [_inv_out(i) for i in db.scalars(stmt).all()]


@router.post("/invoices", status_code=201)
def create_invoice(body: InvoiceIn, db: Db, _: can("finance.write")) -> dict:
    inv = Invoice(
        ref=_next_ref(db, body.invoice_type),
        invoice_type=body.invoice_type,
        buyer_id=body.buyer_id, supplier_id=body.supplier_id,
        invoice_date=body.invoice_date, due_date=body.due_date,
        notes=body.notes,
    )
    db.add(inv)
    db.flush()
    for l in body.lines:
        db.add(InvoiceLine(invoice_id=inv.id, **l.model_dump()))
    db.commit()
    db.refresh(inv)
    return _inv_out(inv)


@router.post("/invoices/{inv_id}/pay", status_code=201)
def add_payment(inv_id: int, body: PaymentIn, db: Db, _: can("finance.write")) -> dict:
    from ..services.common import DomainError
    inv = db.get(Invoice, inv_id)
    if inv is None:
        raise DomainError("Invoice not found.", 404)
    p = Payment(invoice_id=inv_id, **body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(inv)
    return _inv_out(inv)
