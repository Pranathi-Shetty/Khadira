"""Order & roll costing service."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from mill.models import (
    Order, OrderCost, ProductionRun, Roll, RollCost, RollStatus, Setting,
)


def _overhead_per_metre_paise(db: Session) -> int:
    """Return configured overhead per passed metre in paise."""
    s = db.query(Setting).filter(Setting.key == "overhead_per_metre_paise").first()
    return int(s.value) if s else 0


def compute_order_cost(db: Session, order_id: int, user_id: int) -> OrderCost:
    """
    Compute or recompute cost for an order:
      total_cost = yarn_cost + allocated_wages + overhead
      cost_per_passed_metre = total_cost / passed_metres
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise ValueError("Order not found")

    # --- Yarn cost: sum of (issued_grams × cost_per_gram) across all runs ---
    runs = db.query(ProductionRun).filter(ProductionRun.order_id == order_id).all()
    yarn_cost_paise = sum(
        r.yarn_issued_grams * r.yarn_cost_paise_per_gram
        for r in runs
    )

    # --- Passed metres ---
    passed_rolls = (
        db.query(Roll)
        .filter(
            Roll.order_id == order_id,
            Roll.status.in_([RollStatus.passed, RollStatus.in_store, RollStatus.dispatched]),
        )
        .all()
    )
    passed_metres = sum(r.length_cm for r in passed_rolls) // 100   # cm → m

    # --- Overhead ---
    overhead_per_m = _overhead_per_metre_paise(db)
    overhead_paise = overhead_per_m * passed_metres

    # --- Wages: allocate by direct order linkage (placeholder — full allocation in next phase) ---
    allocated_wage_paise = 0  # TODO: sum WageRunLines linked to this order's runs

    total_cost_paise = yarn_cost_paise + allocated_wage_paise + overhead_paise
    cost_per_passed_metre = (total_cost_paise // passed_metres) if passed_metres > 0 else 0

    # Upsert OrderCost
    oc = db.query(OrderCost).filter(OrderCost.order_id == order_id).first()
    if oc is None:
        oc = OrderCost(order_id=order_id)
        db.add(oc)

    oc.yarn_cost_paise = yarn_cost_paise
    oc.allocated_wage_paise = allocated_wage_paise
    oc.overhead_paise = overhead_paise
    oc.total_cost_paise = total_cost_paise
    oc.passed_metres = passed_metres
    oc.cost_per_passed_metre_paise = cost_per_passed_metre
    oc.calculated_at = datetime.utcnow()
    db.flush()

    # --- Roll allocation: proportional to roll length ---
    # Remove old roll costs
    db.query(RollCost).filter(RollCost.order_cost_id == oc.id).delete()

    for roll in passed_rolls:
        roll_metres = roll.length_cm // 100
        roll_cost = (
            (total_cost_paise * roll_metres // passed_metres)
            if passed_metres > 0 else 0
        )
        rc = RollCost(
            roll_id=roll.id,
            order_cost_id=oc.id,
            allocated_cost_paise=roll_cost,
            metres=roll_metres,
            cost_per_metre_paise=(roll_cost // roll_metres) if roll_metres > 0 else 0,
            cost_type="allocated",
            calculated_at=datetime.utcnow(),
        )
        db.add(rc)

    return oc
