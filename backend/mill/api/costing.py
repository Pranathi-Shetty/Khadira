"""Order cost snapshots from production, passed rolls, attendance, and settings."""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from ..models import AttendanceEntry, Order, OrderCost, ProductionRun, Roll, Setting, Worker
from ..services.common import DomainError, audit
from .deps import Db, can

router = APIRouter(prefix="/api/costing", tags=["costing"])


def _calculate(db: Db, order_id: int, user_id: int) -> dict:
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError("Order not found.", 404)
    runs = db.scalars(select(ProductionRun).where(ProductionRun.order_id == order_id)).all()
    run_ids = [run.id for run in runs]
    yarn_used_g = sum(run.yarn_used_g or 0 for run in runs)
    passed_rolls = []
    if run_ids:
        passed_rolls = db.scalars(select(Roll).where(
            Roll.run_id.in_(run_ids), Roll.status.in_(["passed", "in_store", "dispatched"]))).all()
    passed_metres = sum(roll.length_cm for roll in passed_rolls) // 100
    overhead = db.get(Setting, "overhead_per_metre_paise")
    overhead_paise = (int(overhead.value) if overhead and overhead.value else 0) * passed_metres
    wage_entries = db.scalars(select(AttendanceEntry).where(
        AttendanceEntry.status == "approved",
        (AttendanceEntry.order_id == order_id) |
        (AttendanceEntry.run_id.in_(run_ids) if run_ids else False))).all()
    allocated_wages = 0
    for entry in wage_entries:
        worker = db.get(Worker, entry.worker_id)
        if not worker:
            continue
        allocated_wages += ((entry.hours_worked or 0) * worker.hourly_rate_paise // 60
                            if worker.wage_basis == "hourly"
                            else (entry.pieces_produced or 0) * worker.piece_rate_paise)
    snapshot = db.scalar(select(OrderCost).where(OrderCost.order_id == order_id))
    if snapshot is None:
        snapshot = OrderCost(order_id=order_id)
        db.add(snapshot)
    snapshot.yarn_used_g = yarn_used_g
    snapshot.material_cost_paise = None  # No raw-material valuation exists in the active inventory ledger yet.
    snapshot.allocated_wage_paise = allocated_wages
    snapshot.overhead_paise = overhead_paise
    snapshot.known_cost_paise = allocated_wages + overhead_paise
    snapshot.passed_metres = passed_metres
    snapshot.calculated_at = datetime.now(timezone.utc)
    db.flush()
    audit(db, entity="OrderCost", entity_id=snapshot.id, action="calculate", user_id=user_id)
    db.commit()
    db.refresh(snapshot)
    return _out(snapshot)


def _out(cost: OrderCost) -> dict:
    return {"id": cost.id, "order_id": cost.order_id,
            "yarn_used_g": cost.yarn_used_g,
            "material_cost_paise": cost.material_cost_paise,
            "material_cost_status": "unpriced" if cost.yarn_used_g else "not_applicable",
            "allocated_wage_paise": cost.allocated_wage_paise,
            "overhead_paise": cost.overhead_paise,
            "known_cost_paise": cost.known_cost_paise,
            "passed_metres": cost.passed_metres,
            "cost_per_passed_metre_paise": (cost.known_cost_paise // cost.passed_metres
                                           if cost.passed_metres else None),
            "status": "incomplete_material_valuation" if cost.yarn_used_g else "partial",
            "calculated_at": cost.calculated_at.isoformat()}


@router.get("/orders/{order_id}")
def get_order_cost(order_id: int, db: Db, _: can("costing.read")) -> dict:
    cost = db.scalar(select(OrderCost).where(OrderCost.order_id == order_id))
    if cost is None:
        raise DomainError("No costing snapshot exists yet; calculate it first.", 404)
    return _out(cost)


@router.post("/orders/{order_id}/calculate")
def calculate_order_cost(order_id: int, db: Db, user: can("costing.write")) -> dict:
    return _calculate(db, order_id, user.id)
