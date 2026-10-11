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

    # Consume yarn if provided (FIFO across batches)
    if yarn_kg and yarn_kg > 0:
        yarn_g = int(yarn_kg * 1000)
        issue_yarn_to_run(db, run_id=run.id, qty_g=yarn_g, user_id=user_id)

    if idx + 1 >= len(stages):
        # Final stage complete
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        if run.order_id:
            from .orders import calculate_order_progress
            calculate_order_progress(db, run.order_id)
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
    if run.order_id:
        from .orders import calculate_order_progress
        calculate_order_progress(db, run.order_id)
    return roll


def issue_yarn_to_run(db: Session, *, run_id: int, qty_g: int,
                      item_id: int | None = None,
                      user_id: int | None = None) -> list["RunMaterial"]:
    """Issue yarn to a run from active yarn batches using FIFO (oldest first).
    Draws across multiple batches if necessary.
    Decrements each lot's remaining_g and posts stock movements.
    """
    from sqlalchemy import select
    from ..models.core import Item
    from ..models.production import RunMaterial, RunReconciliation
    from ..models.purchasing import YarnLot

    if qty_g <= 0:
        raise DomainError("Quantity must be positive.")
    run = db.get(ProductionRun, run_id)
    if not run:
        raise DomainError("Production run not found.", 404)
    if run.status != "active":
        raise DomainError("Run is not active.")

    stmt = (
        select(YarnLot)
        .join(Item, YarnLot.item_id == Item.id)
        .where(
            YarnLot.is_active.is_(True),
            YarnLot.remaining_g > 0,
            Item.item_type == "yarn",
        )
    )
    if item_id:
        stmt = stmt.where(YarnLot.item_id == item_id)
    elif run.item and run.item.item_type == "yarn":
        stmt = stmt.where(YarnLot.item_id == run.item.id)

    # FIFO: oldest batch first
    stmt = stmt.order_by(YarnLot.created_at.asc(), YarnLot.id.asc())
    lots = db.scalars(stmt).all()

    total_avail = sum(lot.remaining_g for lot in lots)
    if total_avail < qty_g:
        raise DomainError(f"Insufficient yarn stock across batches. Available: {total_avail}g, requested: {qty_g}g.")

    from sqlalchemy import select
    raw_loc = db.scalar(select(Location).where(Location.code == "RAW"))
    if not raw_loc:
        raise DomainError("Location 'RAW' not found.")

    remaining_needed = qty_g
    created_materials: list[RunMaterial] = []
    for lot in lots:
        if remaining_needed <= 0:
            break
        take = min(lot.remaining_g, remaining_needed)
        lot.remaining_g -= take

        move = post_move(
            db,
            item_id=lot.item_id,
            location_id=raw_loc.id,
            delta_g=-take,
            ref=f"RUN-{run.id}",
            note=f"Issued from lot {lot.lot_number}",
            movement_type="yarn_issue",
            user_id=user_id,
        )
        rm = RunMaterial(
            run_id=run.id,
            lot_id=lot.id,
            stock_move_id=move.id,
            issued_g=take,
        )
        db.add(rm)
        created_materials.append(rm)
        remaining_needed -= take

    run.yarn_used_g = (run.yarn_used_g or 0) + qty_g
    recon = run.reconciliation
    if not recon:
        recon = RunReconciliation(run_id=run.id)
        db.add(recon)
    recon.issued_g = (recon.issued_g or 0) + qty_g

    audit(db, entity="ProductionRun", entity_id=run.id, action="issue_yarn", user_id=user_id)
    return created_materials


def issue_material(db: Session, run_id: int, lot_id: int, qty_g: int, user_id: int | None):
    from sqlalchemy import select
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
    if lot.remaining_g < qty_g:
        raise DomainError(f"Insufficient yarn in batch {lot.lot_number}. Available: {lot.remaining_g}g, requested: {qty_g}g.")

    lot.remaining_g -= qty_g
    raw_loc = db.scalar(select(Location).where(Location.code == "RAW"))
    if not raw_loc:
        raise DomainError("Location 'RAW' not found.")

    move_out = post_move(
        db,
        item_id=lot.item_id,
        location_id=raw_loc.id,
        delta_g=-qty_g,
        ref=f"RUN-{run.id}",
        note=f"Issued from lot {lot.lot_number}",
        movement_type="yarn_issue",
        user_id=user_id,
    )

    rm = RunMaterial(run_id=run_id, lot_id=lot_id, stock_move_id=move_out.id, issued_g=qty_g)
    db.add(rm)
    run.yarn_used_g = (run.yarn_used_g or 0) + qty_g

    recon = run.reconciliation
    if not recon:
        recon = RunReconciliation(run_id=run_id)
        db.add(recon)
    recon.issued_g = (recon.issued_g or 0) + qty_g

    audit(db, entity="ProductionRun", entity_id=run_id, action="issue_material", user_id=user_id)
    return rm


def get_roll_trace(db: Session, roll_id: int) -> dict:
    """Trace a roll back to its run, machine, order, yarn batches and suppliers."""
    roll = db.get(Roll, roll_id)
    if roll is None:
        raise DomainError("Roll not found.", 404)
    run = roll.run
    machine = run.machine if run else None
    order = run.order if run else None

    yarn_batches = []
    suppliers_dict = {}

    if run and run.materials:
        for rm in run.materials:
            lot = rm.lot
            supplier_info = None
            if lot.receipt and lot.receipt.po and lot.receipt.po.supplier:
                s = lot.receipt.po.supplier
                supplier_info = {"id": s.id, "name": s.name}
                suppliers_dict[s.id] = supplier_info
            elif lot.receipt_id is None:
                supplier_info = {"id": None, "name": "Opening Balance"}
                suppliers_dict["opening"] = supplier_info

            yarn_batches.append({
                "run_material_id": rm.id,
                "lot_id": lot.id,
                "lot_number": lot.lot_number,
                "item_id": lot.item_id,
                "item_sku": lot.item.sku if lot.item else None,
                "item_name": lot.item.name if lot.item else None,
                "issued_g": rm.issued_g,
                "remaining_g": lot.remaining_g,
                "supplier": supplier_info,
            })

    return {
        "roll": {
            "id": roll.id,
            "roll_number": roll.roll_number,
            "length_cm": roll.length_cm,
            "length_m": round(roll.length_cm / 100, 2),
            "status": roll.status,
            "qc_grade": roll.qc_grade,
        },
        "run": {
            "id": run.id,
            "status": run.status,
            "current_stage": run.current_stage,
            "yarn_used_g": run.yarn_used_g,
        } if run else None,
        "machine": {
            "id": machine.id,
            "code": machine.code,
            "name": machine.name,
            "machine_type": machine.machine_type,
        } if machine else None,
        "order": {
            "id": order.id,
            "ref": order.ref,
            "order_number": order.ref,
            "buyer_id": order.buyer_id,
            "buyer_name": order.buyer.name if (order and order.buyer) else None,
            "status": order.status,
        } if order else None,
        "yarn_batches": yarn_batches,
        "suppliers": list(suppliers_dict.values()),
    }


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
        post_move(db, item_id=run.item_id, location_code="WIP", delta_g=-recon.returned_g, ref=f"RUN-{run.id}", note="reconciliation return", movement_type="yarn_issue", user_id=user_id)
        post_move(db, item_id=run.item_id, location_code="RAW", delta_g=recon.returned_g, ref=f"RUN-{run.id}", note="reconciliation return", movement_type="yarn_return", user_id=user_id)
        
    if recon.process_waste_g > 0:
        post_move(db, item_id=run.item_id, location_code="WIP", delta_g=-recon.process_waste_g, ref=f"RUN-{run.id}", note="process waste", movement_type="adjustment", user_id=user_id)
        post_move(db, item_id=run.item_id, location_code="WASTE", delta_g=recon.process_waste_g, ref=f"RUN-{run.id}", note="process waste", movement_type="adjustment", user_id=user_id)
        
    if recon.consumed_g > 0:
        post_move(db, item_id=run.item_id, location_code="WIP", delta_g=-recon.consumed_g, ref=f"RUN-{run.id}", note="consumed", movement_type="yarn_issue", user_id=user_id)
        
    audit(db, entity="RunReconciliation", entity_id=recon.id, action="finalize", user_id=user_id)
    return recon
