"""Dispatch service: draft -> add rolls -> confirm -> invoice generation.

Enforces:
- One dispatch serves one order and one buyer (when linked), generating one invoice.
- Integrity: no double dispatch (service check + DB UniqueConstraint on roll_id).
- Refusals: empty roll list, duplicate rolls, rolls from different orders, rolls not in store, rejected rolls.
- Strict integer / Decimal pricing via shared helper.
- Integer equality: int(invoice_qty * 100) == sum(roll_length_cm).
- Atomic transaction: entire operation rolls back on any error.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import (
    Dispatch, DispatchRoll, Invoice, InvoiceLine, Location, Order,
    Roll, RollEvent,
)
from .common import DomainError, audit
from .inventory import post_move
from .pricing import (
    cm_to_meters_decimal, compute_fabric_line_total, compute_tax,
    invoice_matches_dispatch,
)


def _next_dispatch_number(db: Session, year: int) -> str:
    count = db.scalar(select(func.count()).select_from(Dispatch)) or 0
    return f"DSP-{year}-{count + 1:05d}"


def _next_invoice_ref(db: Session, year: int) -> str:
    count = db.scalar(select(func.count()).select_from(Invoice).where(Invoice.invoice_type == "sale")) or 0
    return f"SINV-{year}-{count + 1:05d}"


def dispatch_rolls(
    db: Session,
    roll_ids: list[int],
    dispatch_date: date,
    order_id: int | None = None,
    buyer_id: int | None = None,
    vehicle_no: str | None = None,
    notes: str | None = None,
    user_id: int | None = None,
) -> tuple[Dispatch, Invoice, list[Roll]]:
    """Confirm dispatch of a set of in_store rolls in a single atomic transaction.

    Validates all business rules, creates Dispatch and DispatchRoll records,
    deducts inventory, records roll events, and generates the customer invoice.
    """
    if not roll_ids:
        raise DomainError("At least one roll must be specified for dispatch.", 400)

    if len(roll_ids) != len(set(roll_ids)):
        raise DomainError("Duplicate roll in dispatch request.", 400)

    # 1. Location check
    loc = db.scalar(select(Location).where(Location.code == "FIN"))
    if loc is None:
        raise DomainError("Finished goods location (FIN) not found.", 404)

    # 2. Load and validate all rolls
    rolls: list[Roll] = []
    for roll_id in roll_ids:
        roll = db.get(Roll, roll_id)
        if roll is None:
            raise DomainError(f"Roll {roll_id} not found.", 404)
        if roll.status != "in_store":
            raise DomainError(
                f"Roll {roll.roll_number} is not in store (status: {roll.status}).",
                400,
            )

        # Check existing dispatch record
        already_dispatched = db.scalar(
            select(DispatchRoll).where(DispatchRoll.roll_id == roll.id)
        )
        if already_dispatched is not None:
            raise DomainError(
                f"Roll {roll.roll_number} has already been dispatched.", 400
            )

        rolls.append(roll)

    # 3. Determine and validate Order
    order: Order | None = None
    if order_id is not None:
        order = db.get(Order, order_id)
        if order is None:
            raise DomainError(f"Order {order_id} not found.", 404)
        target_buyer_id = buyer_id or order.buyer_id
        target_order_id = order.id
    else:
        # Infer order from rolls if present
        first_run = rolls[0].run
        if first_run is not None and first_run.order_id is not None:
            order = db.get(Order, first_run.order_id)
            target_buyer_id = buyer_id or (order.buyer_id if order else None)
            target_order_id = order.id if order else None
        else:
            target_buyer_id = buyer_id
            target_order_id = None

    if order is not None:
        # Verify every roll belongs to this order
        for roll in rolls:
            if roll.run is None or roll.run.order_id != order.id:
                raise DomainError(
                    f"Roll {roll.roll_number} does not belong to order {order.ref}.",
                    400,
                )
        if buyer_id is not None and buyer_id != order.buyer_id:
            raise DomainError("Buyer does not match the order's buyer.", 400)

    year = dispatch_date.year
    dsp_number = _next_dispatch_number(db, year)

    try:
        # 4. Create Dispatch record
        dispatch = Dispatch(
            dispatch_number=dsp_number,
            order_id=target_order_id,
            buyer_id=target_buyer_id,
            dispatch_date=dispatch_date,
            status="confirmed",
            vehicle_no=vehicle_no,
            notes=notes,
            created_by_id=user_id or 1,
        )
        db.add(dispatch)
        db.flush()

        # 5. Process each roll
        total_cm = 0
        for roll in rolls:
            total_cm += roll.length_cm
            db.add(DispatchRoll(
                dispatch_id=dispatch.id,
                roll_id=roll.id,
                length_cm=roll.length_cm,
            ))

            # Stock deduction (fabric_out)
            post_move(
                db,
                item_id=roll.item_id,
                location_id=loc.id,
                delta_g=-roll.length_cm,
                ref=dispatch.dispatch_number,
                note=f"Dispatched roll {roll.roll_number}",
                movement_type="fabric_out",
                user_id=user_id,
            )

            # Update roll status
            roll.status = "dispatched"
            db.add(RollEvent(
                roll_id=roll.id,
                event_type="dispatched",
                note=f"Dispatch {dsp_number}, vehicle {vehicle_no or '-'}",
                created_by_id=user_id,
            ))
            audit(db, entity="Roll", entity_id=roll.id, action="dispatch", user_id=user_id)

        # 6. Pricing & Invoice Generation
        # Convert total centimetres to Decimal metres
        inv_qty_m = cm_to_meters_decimal(total_cm)

        # Verification of Condition 3: integer comparison
        if not invoice_matches_dispatch(inv_qty_m, total_cm):
            raise DomainError(
                f"Invoice quantity mismatch: {int(inv_qty_m * 100)} cm != {total_cm} cm.",
                500,
            )

        # Determine rate from order line if order exists
        rate_paise = 0
        if order is not None and order.lines:
            order_line = next(
                (line for line in order.lines if line.item_id == rolls[0].item_id),
                order.lines[0],
            )
            rate_paise = order_line.rate_per_meter_paise if order_line else 0

        # Calculate line total and tax with shared integer helper
        line_total_paise = compute_fabric_line_total(total_cm, rate_paise)
        tax_pct = Decimal("5.00")
        tax_paise = compute_tax(line_total_paise, tax_pct)

        inv_ref = _next_invoice_ref(db, year)
        invoice = Invoice(
            ref=inv_ref,
            invoice_type="sale",
            buyer_id=target_buyer_id,
            order_id=target_order_id,
            dispatch_id=dispatch.id,
            invoice_date=dispatch_date,
            status="sent",
            notes=f"Auto-generated for dispatch {dsp_number}",
        )
        db.add(invoice)
        db.flush()

        inv_line = InvoiceLine(
            invoice_id=invoice.id,
            description=f"Fabric Dispatch {dsp_number} ({len(rolls)} rolls)",
            qty=inv_qty_m,
            unit_price_paise=rate_paise,
            tax_pct=tax_pct,
        )
        db.add(inv_line)
        if target_order_id:
            from .orders import calculate_order_progress
            calculate_order_progress(db, target_order_id)

        return dispatch, invoice, rolls

    except IntegrityError as exc:
        db.rollback()
        raise DomainError("Roll has already been dispatched.", 400) from exc


def create_dispatch_draft(
    db: Session,
    buyer_id: int | None = None,
    order_id: int | None = None,
    dispatch_date: date = date.today(),
    vehicle_no: str | None = None,
    notes: str | None = None,
    user_id: int | None = None,
) -> Dispatch:
    """Create a new dispatch in draft status."""
    if order_id is not None:
        order = db.get(Order, order_id)
        if order is None:
            raise DomainError(f"Order {order_id} not found.", 404)
        if buyer_id is not None and order.buyer_id != buyer_id:
            raise DomainError("Buyer does not match order's buyer.", 400)
        target_buyer_id = order.buyer_id
    else:
        target_buyer_id = buyer_id

    year = dispatch_date.year
    dsp_number = _next_dispatch_number(db, year)
    dispatch = Dispatch(
        dispatch_number=dsp_number,
        order_id=order_id,
        buyer_id=target_buyer_id,
        dispatch_date=dispatch_date,
        status="draft",
        vehicle_no=vehicle_no,
        notes=notes,
        created_by_id=user_id or 1,
    )
    db.add(dispatch)
    db.flush()
    return dispatch


def add_rolls_to_dispatch(
    db: Session,
    dispatch_id: int,
    roll_ids: list[int],
    user_id: int | None = None,
) -> list[DispatchRoll]:
    """Add rolls to an existing draft dispatch."""
    dispatch = db.get(Dispatch, dispatch_id)
    if dispatch is None:
        raise DomainError(f"Dispatch {dispatch_id} not found.", 404)
    if dispatch.status != "draft":
        raise DomainError(f"Cannot add rolls to dispatch with status {dispatch.status}.", 400)

    if not roll_ids:
        raise DomainError("At least one roll must be specified.", 400)
    if len(roll_ids) != len(set(roll_ids)):
        raise DomainError("Duplicate roll in request.", 400)

    added = []
    for roll_id in roll_ids:
        roll = db.get(Roll, roll_id)
        if roll is None:
            raise DomainError(f"Roll {roll_id} not found.", 404)
        if roll.status != "in_store":
            raise DomainError(f"Roll {roll.roll_number} is not in store (status: {roll.status}).", 400)
        if dispatch.order_id and (roll.run is None or roll.run.order_id != dispatch.order_id):
            raise DomainError(f"Roll {roll.roll_number} does not belong to dispatch order.", 400)

        existing = db.scalar(select(DispatchRoll).where(DispatchRoll.roll_id == roll.id))
        if existing is not None:
            raise DomainError(f"Roll {roll.roll_number} has already been dispatched.", 400)

        try:
            dr = DispatchRoll(
                dispatch_id=dispatch.id,
                roll_id=roll.id,
                length_cm=roll.length_cm,
            )
            db.add(dr)
            db.flush()
            added.append(dr)
        except IntegrityError as exc:
            db.rollback()
            raise DomainError(f"Roll {roll.roll_number} has already been dispatched.", 400) from exc

    return added


def confirm_dispatch(
    db: Session,
    dispatch_id: int,
    user_id: int | None = None,
) -> tuple[Dispatch, Invoice]:
    """Confirm a draft dispatch: deducts stock, sets rolls to dispatched, and creates the invoice."""
    dispatch = db.get(Dispatch, dispatch_id)
    if dispatch is None:
        raise DomainError(f"Dispatch {dispatch_id} not found.", 404)
    if dispatch.status == "confirmed":
        raise DomainError("Dispatch has already been confirmed.", 400)

    if not dispatch.rolls:
        raise DomainError("Dispatch has no rolls attached.", 400)

    loc = db.scalar(select(Location).where(Location.code == "FIN"))
    if loc is None:
        raise DomainError("Finished goods location (FIN) not found.", 404)

    order = dispatch.order
    total_cm = 0
    for dr in dispatch.rolls:
        roll = dr.roll
        total_cm += dr.length_cm
        post_move(
            db,
            item_id=roll.item_id,
            location_id=loc.id,
            delta_g=-dr.length_cm,
            ref=dispatch.dispatch_number,
            note=f"Dispatched roll {roll.roll_number}",
            movement_type="fabric_out",
            user_id=user_id,
        )
        roll.status = "dispatched"
        db.add(RollEvent(
            roll_id=roll.id,
            event_type="dispatched",
            note=f"Dispatch {dispatch.dispatch_number}, vehicle {dispatch.vehicle_no or '-'}",
            created_by_id=user_id,
        ))
        audit(db, entity="Roll", entity_id=roll.id, action="dispatch", user_id=user_id)

    dispatch.status = "confirmed"

    inv_qty_m = cm_to_meters_decimal(total_cm)
    if not invoice_matches_dispatch(inv_qty_m, total_cm):
        raise DomainError(
            f"Invoice quantity mismatch: {int(inv_qty_m * 100)} cm != {total_cm} cm.",
            500,
        )

    rate_paise = 0
    if order and order.lines:
        order_line = next(
            (line for line in order.lines if line.item_id == dispatch.rolls[0].roll.item_id),
            order.lines[0],
        )
        rate_paise = order_line.rate_per_meter_paise if order_line else 0

    line_total_paise = compute_fabric_line_total(total_cm, rate_paise)
    tax_pct = Decimal("5.00")

    inv_ref = _next_invoice_ref(db, dispatch.dispatch_date.year)
    invoice = Invoice(
        ref=inv_ref,
        invoice_type="sale",
        buyer_id=dispatch.buyer_id,
        order_id=dispatch.order_id,
        dispatch_id=dispatch.id,
        invoice_date=dispatch.dispatch_date,
        status="sent",
        notes=f"Auto-generated for dispatch {dispatch.dispatch_number}",
    )
    db.add(invoice)
    db.flush()

    inv_line = InvoiceLine(
        invoice_id=invoice.id,
        description=f"Fabric Dispatch {dispatch.dispatch_number} ({len(dispatch.rolls)} rolls)",
        qty=inv_qty_m,
        unit_price_paise=rate_paise,
        tax_pct=tax_pct,
    )
    db.add(inv_line)
    db.flush()

    if dispatch.order_id:
        from .orders import calculate_order_progress
        calculate_order_progress(db, dispatch.order_id)

    return dispatch, invoice
