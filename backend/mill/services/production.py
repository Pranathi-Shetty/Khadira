"""Production service: runs, stage transitions, roll creation."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import Location, Machine, ProductionRun, Roll, RollEvent
from ..models.production import MACHINE_STAGES
from .common import DomainError, audit
from .inventory import post_move


def start_run(db: Session, *, machine_id: int, order_id: int | None,
              item_id: int, user_id: int | None) -> ProductionRun:
    machine = db.get(Machine, machine_id)
    if machine is None:
        raise DomainError("Machine not found.", 404)
    stages = MACHINE_STAGES.get(machine.machine_type)
    if not stages:
        raise DomainError(f"Unknown machine type '{machine.machine_type}'.")
    run = ProductionRun(
        machine_id=machine_id,
        order_id=order_id,
        item_id=item_id,
        current_stage=stages[0],
        status="active",
    )
    db.add(run)
    db.flush()
    if order_id:
        from ..models import Order
        order = db.get(Order, order_id)
        if order and order.status == "confirmed":
            order.status = "in_production"
    audit(db, entity="ProductionRun", entity_id=run.id, action="start", user_id=user_id)
    return run


def advance_stage(db: Session, run_id: int, yarn_kg: float | None,
                  user_id: int | None) -> ProductionRun:
    run = db.get(ProductionRun, run_id)
    if run is None:
        raise DomainError("Production run not found.", 404)
    if run.status != "active":
        raise DomainError("Run is not active.")

    machine = db.get(Machine, run.machine_id)
    stages = MACHINE_STAGES.get(machine.machine_type, [])
    idx = stages.index(run.current_stage)

    # Consume yarn if provided
    if yarn_kg and yarn_kg > 0:
        yarn_g = int(yarn_kg * 1000)
        run.yarn_used_g = (run.yarn_used_g or 0) + yarn_g
        # Deduct from RAW location
        from sqlalchemy import select
        from ..models import StockLevel
        loc = db.scalar(select(Location).where(Location.code == "RAW"))
        if loc:
            levels = db.scalars(
                select(StockLevel).where(
                    StockLevel.location_id == loc.id,
                    StockLevel.qty_g > 0,
                )
            ).all()
            remaining = yarn_g
            for level in levels:
                if remaining <= 0:
                    break
                take = min(level.qty_g, remaining)
                post_move(db, item_id=level.item_id, location_id=loc.id,
                          delta_g=-take, ref=f"RUN-{run.id}", note="yarn consumed")
                remaining -= take

    if idx + 1 >= len(stages):
        # Final stage complete
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        if run.order_id:
            from ..models import Order
            order = db.get(Order, run.order_id)
            if order:
                order.status = "completed"
    else:
        run.current_stage = stages[idx + 1]

    audit(db, entity="ProductionRun", entity_id=run.id, action="advance_stage", user_id=user_id)
    return run


def create_roll(db: Session, *, run_id: int, length_cm: int,
                weight_g: int | None, user_id: int | None) -> Roll:
    run = db.get(ProductionRun, run_id)
    if run is None:
        raise DomainError("Production run not found.", 404)

    machine = db.get(Machine, run.machine_id)
    stages = MACHINE_STAGES.get(machine.machine_type, [])
    if run.current_stage != stages[-1] and run.status != "completed":
        raise DomainError("Rolls can only be created at the final production stage.")

    from sqlalchemy import func, select
    count = db.scalar(select(func.count()).select_from(Roll)) or 0
    roll_number = f"ROLL-{count + 1:06d}"

    roll = Roll(
        roll_number=roll_number,
        run_id=run_id,
        item_id=run.item_id,
        length_cm=length_cm,
        weight_g=weight_g,
        status="awaiting_qc",
    )
    db.add(roll)
    db.flush()
    db.add(RollEvent(roll_id=roll.id, event_type="created", created_by_id=user_id))
    audit(db, entity="Roll", entity_id=roll.id, action="create", user_id=user_id)
    return roll


def issue_material(db: Session, run_id: int, lot_id: int, qty_g: int, user_id: int | None):
    from ..models.production import RunMaterial, RunReconciliation
    from ..models.purchasing import YarnLot
    if qty_g <= 0:
        raise DomainError("Quantity must be positive.")
    run = db.get(ProductionRun, run_id)
    if not run:
        raise DomainError("Run not found.", 404)
    if run.status != "active":
        raise DomainError("Run is not active.")
    
    lot = db.get(YarnLot, lot_id)
    if not lot:
        raise DomainError("Lot not found.", 404)
    
    move_out = post_move(db, item_id=lot.item_id, location_code="RAW", delta_g=-qty_g, ref=f"RUN-{run.id}", note="issue to run")
    post_move(db, item_id=lot.item_id, location_code="WIP", delta_g=qty_g, ref=f"RUN-{run.id}", note="issue to run")
    
    rm = RunMaterial(run_id=run_id, lot_id=lot_id, stock_move_id=move_out.id, issued_g=qty_g)
    db.add(rm)
    
    recon = run.reconciliation
    if not recon:
        recon = RunReconciliation(run_id=run_id)
        db.add(recon)
    recon.issued_g = (recon.issued_g or 0) + qty_g
    
    audit(db, entity="ProductionRun", entity_id=run_id, action="issue_material", user_id=user_id)
    return rm


def save_reconciliation(db: Session, run_id: int, data: dict, user_id: int | None):
    from ..models.production import RunReconciliation
    run = db.get(ProductionRun, run_id)
    if not run:
        raise DomainError("Run not found.", 404)
    recon = run.reconciliation
    if not recon:
        recon = RunReconciliation(run_id=run_id)
        db.add(recon)
    if recon.status == "finalized":
        raise DomainError("Reconciliation already finalized.")
        
    for k in ["planned_g", "consumed_g", "returned_g", "process_waste_g", "usable_output_cm", "qc_rejected_cm"]:
        if k in data:
            if data[k] < 0:
                raise DomainError(f"{k} cannot be negative.")
            setattr(recon, k, data[k])
    
    if "reason" in data:
        recon.reason = data["reason"]
        
    audit(db, entity="RunReconciliation", entity_id=recon.id, action="save_draft", user_id=user_id)
    return recon


def finalize_reconciliation(db: Session, run_id: int, user_id: int | None):
    from ..models.production import RunReconciliation
    run = db.get(ProductionRun, run_id)
    recon = run.reconciliation if run else None
    if not recon:
        raise DomainError("Reconciliation not found.", 404)
    if recon.status == "finalized":
        raise DomainError("Reconciliation already finalized.")
        
    recon.status = "finalized"
    recon.finalized_at = datetime.now(timezone.utc)
    recon.actor_id = user_id
    
    if recon.returned_g > 0:
        post_move(db, item_id=run.item_id, location_code="WIP", delta_g=-recon.returned_g, ref=f"RUN-{run.id}", note="reconciliation return")
        post_move(db, item_id=run.item_id, location_code="RAW", delta_g=recon.returned_g, ref=f"RUN-{run.id}", note="reconciliation return")
        
    if recon.process_waste_g > 0:
        post_move(db, item_id=run.item_id, location_code="WIP", delta_g=-recon.process_waste_g, ref=f"RUN-{run.id}", note="process waste")
        post_move(db, item_id=run.item_id, location_code="WASTE", delta_g=recon.process_waste_g, ref=f"RUN-{run.id}", note="process waste")
        
    if recon.consumed_g > 0:
        post_move(db, item_id=run.item_id, location_code="WIP", delta_g=-recon.consumed_g, ref=f"RUN-{run.id}", note="consumed")
        
    audit(db, entity="RunReconciliation", entity_id=recon.id, action="finalize", user_id=user_id)
    return recon
