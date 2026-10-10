"""Purchasing service: PO lifecycle, yarn receipts, stock updates."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ITEM_YARN, Item, Location, PurchaseOrder, PurchaseOrderLine, YarnLot, YarnReceipt
from .common import DomainError, audit
from .inventory import post_move


def _next_po_ref(db: Session) -> str:
    from sqlalchemy import func
    count = db.scalar(select(func.count()).select_from(PurchaseOrder)) or 0
    return f"PO-{date.today().year}-{count + 1:05d}"


def create_po(db: Session, *, supplier_id: int, order_date: date,
              expected_date: date | None, lines: list[dict],
              notes: str | None, user_id: int | None) -> PurchaseOrder:
    for line in lines:
        item = db.get(Item, line["item_id"])
        if item is None or item.item_type != ITEM_YARN:
            raise DomainError("Purchase orders may only contain yarn items.")

    po = PurchaseOrder(
        ref=_next_po_ref(db),
        supplier_id=supplier_id,
        order_date=order_date,
        expected_date=expected_date,
        notes=notes,
        status="draft",
    )
    db.add(po)
    db.flush()
    for line in lines:
        db.add(PurchaseOrderLine(
            po_id=po.id,
            item_id=line["item_id"],
            qty_kg=line["qty_kg"],
            rate_per_kg_paise=line["rate_per_kg_paise"],
        ))
    audit(db, entity="PurchaseOrder", entity_id=po.id, action="create", user_id=user_id)
    return po


def confirm_po(db: Session, po_id: int, user_id: int | None) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise DomainError("Purchase order not found.", 404)
    if po.status != "draft":
        raise DomainError(f"Cannot confirm a PO in status '{po.status}'.")
    po.status = "confirmed"
    audit(db, entity="PurchaseOrder", entity_id=po.id, action="confirm", user_id=user_id)
    return po


def cancel_po(db: Session, po_id: int, user_id: int | None) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise DomainError("Purchase order not found.", 404)
    if po.status not in ("draft", "confirmed"):
        raise DomainError(f"Cannot cancel a PO in status '{po.status}'.")
    po.status = "cancelled"
    audit(db, entity="PurchaseOrder", entity_id=po.id, action="cancel", user_id=user_id)
    return po


def receive_yarn(db: Session, *, po_id: int, po_line_id: int,
                 received_date: date, qty_kg: float,
                 vehicle_no: str | None, notes: str | None,
                 lot_number: str, location_code: str,
                 user_id: int | None) -> YarnReceipt:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise DomainError("PO not found.", 404)
    if po.status not in ("confirmed", "received"):
        raise DomainError("Can only receive against a confirmed PO.")

    line = db.get(PurchaseOrderLine, po_line_id)
    if line is None or line.po_id != po_id:
        raise DomainError("PO line not found.")

    receipt = YarnReceipt(
        po_id=po_id,
        po_line_id=po_line_id,
        received_date=received_date,
        qty_kg=qty_kg,
        vehicle_no=vehicle_no,
        notes=notes,
    )
    db.add(receipt)
    db.flush()

    qty_g = int(qty_kg * 1000)
    loc = db.scalar(select(Location).where(Location.code == location_code))
    if loc is None:
        raise DomainError(f"Location '{location_code}' not found.")

    db.add(YarnLot(
        receipt_id=receipt.id,
        item_id=line.item_id,
        lot_number=lot_number,
        qty_g=qty_g,
    ))

    post_move(db, item_id=line.item_id, location_id=loc.id,
              delta_g=qty_g, ref=po.ref, note=f"Receipt #{receipt.id}")

    line.received_kg = float(line.received_kg or 0) + qty_kg
    po.status = "received"
    audit(db, entity="YarnReceipt", entity_id=receipt.id, action="receive", user_id=user_id)
    return receipt
