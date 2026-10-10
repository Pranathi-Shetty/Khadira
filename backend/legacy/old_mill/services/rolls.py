"""Roll lifecycle and QC service."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from mill.models import (
    Machine, MachineStatus, MachineStatusLog, NumberSequence,
    QCInspection, QCResult, Roll, RollEvent, RollStatus,
)
from mill.services import stock as stock_svc
from mill.models import StockMoveKind

# Valid transitions
ALLOWED_TRANSITIONS: dict[RollStatus, set[RollStatus]] = {
    RollStatus.produced:     {RollStatus.awaiting_qc},
    RollStatus.awaiting_qc:  {RollStatus.passed, RollStatus.rework, RollStatus.rejected},
    RollStatus.passed:       {RollStatus.in_store},
    RollStatus.rework:       {RollStatus.awaiting_qc},
    RollStatus.in_store:     {RollStatus.dispatched},
    RollStatus.rejected:     set(),
    RollStatus.dispatched:   set(),
}

FABRIC_STORE_LOCATION_ID = 2   # fixed: finished store


def next_roll_no(db: Session) -> str:
    seq = db.query(NumberSequence).filter(NumberSequence.name == "roll_no").with_for_update().first()
    if seq is None:
        seq = NumberSequence(name="roll_no", last_value=0)
        db.add(seq)
    seq.last_value += 1
    return f"ROLL-{seq.last_value:06d}"


def transition_roll(
    db: Session,
    roll_id: int,
    to_status: RollStatus,
    user_id: int,
    note: Optional[str] = None,
) -> Roll:
    roll = db.query(Roll).filter(Roll.id == roll_id).first()
    if roll is None:
        raise ValueError("Roll not found")
    if to_status not in ALLOWED_TRANSITIONS.get(roll.status, set()):
        raise ValueError(f"Transition {roll.status} → {to_status} is not allowed")

    from_status = roll.status
    roll.status = to_status

    event = RollEvent(
        roll_id=roll.id,
        from_status=from_status,
        to_status=to_status,
        changed_by=user_id,
        note=note,
    )
    db.add(event)

    # Trigger stock move when roll moves into finished store
    if to_status == RollStatus.in_store:
        stock_svc.post_move(
            db,
            item_id=roll.order.item_id,
            location_id=FABRIC_STORE_LOCATION_ID,
            quantity_delta=roll.length_cm,
            unit_cost_paise=0,
            kind=StockMoveKind.fabric_in,
            reference_id=roll.id,
            reference_type="roll",
            user_id=user_id,
            note=f"Roll {roll.roll_no} into finished store",
        )

    return roll


def record_qc(
    db: Session,
    roll_id: int,
    inspector_id: int,
    result: QCResult,
    defects: Optional[list[str]] = None,
    notes: Optional[str] = None,
) -> QCInspection:
    import json
    roll = db.query(Roll).filter(Roll.id == roll_id).first()
    if roll is None:
        raise ValueError("Roll not found")
    if roll.status != RollStatus.awaiting_qc:
        raise ValueError(f"Roll must be in awaiting_qc state, currently {roll.status}")

    inspection = QCInspection(
        roll_id=roll_id,
        inspector_id=inspector_id,
        result=result,
        defects=json.dumps(defects or []),
        notes=notes,
    )
    db.add(inspection)

    # Transition based on result
    target = {
        QCResult.passed: RollStatus.passed,
        QCResult.rework: RollStatus.rework,
        QCResult.rejected: RollStatus.rejected,
    }[result]
    transition_roll(db, roll_id, target, inspector_id, note=f"QC: {result}")

    return inspection
