"""Orders service: buyer orders, yarn sufficiency check, and derived progress tracking."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    ITEM_FABRIC, ITEM_YARN, Item, Location, Order, OrderLine,
    ProductionRun, Roll, StockLevel,
)
from .common import DomainError, audit
from .pricing import cm_to_meters_decimal


def _next_order_ref(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(Order)) or 0
    return f"ORD-{date.today().year}-{count + 1:05d}"


def create_order(
    db: Session,
    *,
    buyer_id: int,
    order_date: date,
    delivery_date: date | None,
    lines: list[dict],
    tolerance_pct: Decimal | float | None = Decimal("5.00"),
    notes: str | None = None,
    user_id: int | None = None,
) -> Order:
    for line in lines:
        item = db.get(Item, line["item_id"])
        if item is None or item.item_type != ITEM_FABRIC:
            raise DomainError("Orders may only contain fabric items.")

    order = Order(
        ref=_next_order_ref(db),
        buyer_id=buyer_id,
        order_date=order_date,
        delivery_date=delivery_date,
        tolerance_pct=Decimal(str(tolerance_pct if tolerance_pct is not None else 5.00)),
        notes=notes,
        status="draft",
    )
    db.add(order)
    db.flush()
    for line in lines:
        db.add(OrderLine(
            order_id=order.id,
            item_id=line["item_id"],
            qty_meters=line["qty_meters"],
            rate_per_meter_paise=line["rate_per_meter_paise"],
        ))
    audit(db, entity="Order", entity_id=order.id, action="create", user_id=user_id)
    return order


def yarn_needed_g(db: Session, order: Order) -> int:
    """Total yarn grams needed for all fabric lines in the order."""
    total = 0
    for line in order.lines:
        item = db.get(Item, line.item_id)
        if item and item.yarn_kg_per_meter:
            total += int(float(item.yarn_kg_per_meter) * float(line.qty_meters) * 1000)
    return total


def yarn_available_g(db: Session) -> int:
    """Total yarn in all locations."""
    yarn_items = db.scalars(select(Item).where(Item.item_type == ITEM_YARN)).all()
    ids = {i.id for i in yarn_items}
    if not ids:
        return 0
    levels = db.scalars(select(StockLevel).where(StockLevel.item_id.in_(ids))).all()
    return sum(l.qty_g for l in levels)


def confirm_order(db: Session, order_id: int, user_id: int | None) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError("Order not found.", 404)
    if order.status != "draft":
        raise DomainError(f"Cannot confirm an order in status '{order.status}'.")

    needed = yarn_needed_g(db, order)
    available = yarn_available_g(db)
    if needed > available:
        raise DomainError(
            f"Insufficient yarn. Need {needed/1000:.1f} kg, have {available/1000:.1f} kg."
        )

    order.status = "confirmed"
    audit(db, entity="Order", entity_id=order.id, action="confirm", user_id=user_id)
    return order


def cancel_order(db: Session, order_id: int, user_id: int | None) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError("Order not found.", 404)
    if order.status not in ("draft", "confirmed"):
        raise DomainError(f"Cannot cancel an order in status '{order.status}'.")
    order.status = "cancelled"
    audit(db, entity="Order", entity_id=order.id, action="cancel", user_id=user_id)
    return order


def calculate_order_progress(db: Session, order_id: int) -> dict:
    """Calculate an order's progress from its actual physical rolls and update order status.

    Rules:
    - tolerance: default 5% (from order.tolerance_pct or 5.00)
    - production_complete: passed meters >= ordered_meters * (1 - tolerance_pct / 100)
    - delivered: dispatched meters >= ordered_meters * (1 - tolerance_pct / 100)
    - in_production: when production has started or rolls produced, but passed meters < threshold
    - status only updates via this function, called after roll or dispatch mutations.
    """
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError(f"Order {order_id} not found.", 404)

    # 1. Total ordered meters
    total_ordered_meters = sum(Decimal(str(l.qty_meters)) for l in order.lines)
    tolerance_pct = Decimal(str(order.tolerance_pct if order.tolerance_pct is not None else "5.00"))

    # Completion threshold (e.g. 100m with 5% tolerance -> 95m)
    min_acceptable_meters = (total_ordered_meters * (Decimal("100.00") - tolerance_pct) / Decimal("100.00")).quantize(Decimal("0.001"))
    max_acceptable_meters = (total_ordered_meters * (Decimal("100.00") + tolerance_pct) / Decimal("100.00")).quantize(Decimal("0.001"))

    # 2. Query all rolls across all production runs linked to this order
    runs = db.scalars(select(ProductionRun).where(ProductionRun.order_id == order.id)).all()
    run_ids = [r.id for r in runs]

    rolls: list[Roll] = []
    if run_ids:
        rolls = db.scalars(
            select(Roll).where(Roll.run_id.in_(run_ids)).order_by(Roll.id.asc())
        ).all()

    # 3. Sum centimetre totals by roll status
    produced_cm = sum(r.length_cm for r in rolls)
    passed_cm = sum(r.length_cm for r in rolls if r.status in ("passed", "in_store", "dispatched"))
    in_store_cm = sum(r.length_cm for r in rolls if r.status == "in_store")
    dispatched_cm = sum(r.length_cm for r in rolls if r.status == "dispatched")
    awaiting_qc_cm = sum(r.length_cm for r in rolls if r.status == "awaiting_qc")
    rework_cm = sum(r.length_cm for r in rolls if r.status in ("rework", "held"))
    rejected_cm = sum(r.length_cm for r in rolls if r.status in ("rejected", "reject", "failed"))

    # Convert cm to Decimal metres
    produced_m = cm_to_meters_decimal(produced_cm)
    passed_m = cm_to_meters_decimal(passed_cm)
    in_store_m = cm_to_meters_decimal(in_store_cm)
    dispatched_m = cm_to_meters_decimal(dispatched_cm)
    awaiting_qc_m = cm_to_meters_decimal(awaiting_qc_cm)
    rework_m = cm_to_meters_decimal(rework_cm)
    rejected_m = cm_to_meters_decimal(rejected_cm)

    # 4. Roll counts by stage
    roll_counts = {
        "produced": len(rolls),
        "passed": len([r for r in rolls if r.status in ("passed", "in_store", "dispatched")]),
        "awaiting_qc": len([r for r in rolls if r.status == "awaiting_qc"]),
        "rework": len([r for r in rolls if r.status in ("rework", "held")]),
        "in_store": len([r for r in rolls if r.status == "in_store"]),
        "dispatched": len([r for r in rolls if r.status == "dispatched"]),
        "rejected": len([r for r in rolls if r.status in ("rejected", "reject", "failed")]),
    }

    # 5. Percentages against ordered
    def _pct(m: Decimal) -> float:
        if total_ordered_meters <= 0:
            return 0.0
        return round(float(m / total_ordered_meters * 100), 2)

    produced_pct = _pct(produced_m)
    passed_pct = _pct(passed_m)
    in_store_pct = _pct(in_store_m)
    dispatched_pct = _pct(dispatched_m)

    # 6. Status determination (Separate states: delivered, production_complete, in_production, confirmed)
    if order.status not in ("draft", "cancelled"):
        if total_ordered_meters > 0 and dispatched_m >= min_acceptable_meters:
            order.status = "delivered"
        elif total_ordered_meters > 0 and passed_m >= min_acceptable_meters:
            order.status = "production_complete"
        elif rolls or runs:
            order.status = "in_production"
        else:
            order.status = "confirmed"

    # 7. Timeliness & Schedule
    today = date.today()
    if order.status == "delivered":
        is_late = False
        schedule_status = "delivered"
        days_remaining = None
        days_overdue = None
    elif order.delivery_date:
        if today > order.delivery_date:
            is_late = True
            schedule_status = "late"
            days_overdue = (today - order.delivery_date).days
            days_remaining = None
        else:
            is_late = False
            schedule_status = "on_time"
            days_overdue = None
            days_remaining = (order.delivery_date - today).days
    else:
        is_late = False
        schedule_status = "on_time"
        days_remaining = None
        days_overdue = None

    # 8. Current Stage description
    if order.status == "delivered":
        current_stage = "delivered"
    elif order.status == "production_complete":
        current_stage = "in_store" if in_store_m > 0 else "production_complete"
    elif order.status == "in_production":
        if in_store_m > 0:
            current_stage = "in_store"
        elif awaiting_qc_m > 0:
            current_stage = "inspection"
        else:
            stages = [r.current_stage for r in runs if r.current_stage]
            current_stage = stages[0] if stages else "production"
    else:
        current_stage = order.status

    db.flush()

    return {
        "order_id": order.id,
        "order_ref": order.ref,
        "buyer_id": order.buyer_id,
        "buyer_name": order.buyer.name if order.buyer else None,
        "status": order.status,
        "current_stage": current_stage,
        "ordered_meters": float(total_ordered_meters),
        "tolerance_pct": float(tolerance_pct),
        "min_acceptable_meters": float(min_acceptable_meters),
        "max_acceptable_meters": float(max_acceptable_meters),
        "meters_by_stage": {
            "produced": float(produced_m),
            "passed": float(passed_m),
            "awaiting_qc": float(awaiting_qc_m),
            "in_store": float(in_store_m),
            "dispatched": float(dispatched_m),
            "rejected": float(rejected_m),
        },
        "roll_counts_by_stage": roll_counts,
        "percentages": {
            "produced_pct": produced_pct,
            "passed_pct": passed_pct,
            "in_store_pct": in_store_pct,
            "dispatched_pct": dispatched_pct,
        },
        "delivery_date": str(order.delivery_date) if order.delivery_date else None,
        "schedule_status": schedule_status,
        "is_late": is_late,
        "days_remaining": days_remaining,
        "days_overdue": days_overdue,
        "rolls": [
            {
                "id": r.id,
                "roll_number": r.roll_number,
                "length_m": float(cm_to_meters_decimal(r.length_cm)),
                "length_cm": r.length_cm,
                "status": r.status,
                "qc_grade": r.qc_grade,
            }
            for r in rolls
        ],
        "runs": [
            {
                "id": r.id,
                "machine_code": r.machine.code if r.machine else f"M-{r.machine_id}",
                "machine_name": r.machine.name if r.machine else None,
                "current_stage": r.current_stage,
                "status": r.status,
                "yarn_used_kg": round(r.yarn_used_g / 1000.0, 2) if r.yarn_used_g else 0.0,
            }
            for r in runs
        ],
    }
