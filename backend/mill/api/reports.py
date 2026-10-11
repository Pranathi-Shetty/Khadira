"""Reports router: production, inventory, and QC reporting."""
from fastapi import APIRouter
from sqlalchemy import func, select

from ..models import Item, Machine, ProductionRun, Roll, StockLevel
from .deps import Db, can

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/production")
def production_summary(db: Db, _: can["reports.read"]) -> dict:
    total_runs = db.scalar(select(func.count(ProductionRun.id))) or 0
    active_runs = db.scalar(select(func.count(ProductionRun.id)).where(ProductionRun.status == "in_progress")) or 0
    completed_runs = db.scalar(select(func.count(ProductionRun.id)).where(ProductionRun.status == "completed")) or 0
    total_rolls = db.scalar(select(func.count(Roll.id))) or 0
    total_length_cm = db.scalar(select(func.sum(Roll.length_cm))) or 0
    total_weight_g = db.scalar(select(func.sum(Roll.weight_g))) or 0

    return {
        "total_runs": total_runs,
        "active_runs": active_runs,
        "completed_runs": completed_runs,
        "total_rolls": total_rolls,
        "total_meters": round(total_length_cm / 100, 2),
        "total_weight_kg": round(total_weight_g / 1000, 3),
    }


@router.get("/inventory")
def inventory_summary(db: Db, _: can["reports.read"]) -> dict:
    items_count = db.scalar(select(func.count(Item.id)).where(Item.is_active.is_(True))) or 0
    total_stock_g = db.scalar(select(func.sum(StockLevel.qty_g))) or 0
    return {
        "active_items": items_count,
        "total_stock_kg": round(total_stock_g / 1000, 3),
    }


@router.get("/quality")
def quality_summary(db: Db, _: can["reports.read"]) -> dict:
    total_rolls = db.scalar(select(func.count(Roll.id))) or 0
    passed = db.scalar(select(func.count(Roll.id)).where(Roll.status.in_(["passed", "in_store", "dispatched"]))) or 0
    rejected = db.scalar(select(func.count(Roll.id)).where(Roll.status.in_(["rejected", "reject"]))) or 0
    rework = db.scalar(select(func.count(Roll.id)).where(Roll.status == "rework")) or 0
    awaiting_qc = db.scalar(select(func.count(Roll.id)).where(Roll.status == "awaiting_qc")) or 0
    return {
        "total_inspected": total_rolls,
        "passed": passed,
        "rejected": rejected,
        "rework": rework,
        "awaiting_qc": awaiting_qc,
        "pass_rate_pct": round((passed / total_rolls) * 100, 1) if total_rolls else 100.0,
    }


@router.get("/financial-summary")
def financial_summary(
    db: Db,
    _: can["reports.read"],
    period: str | None = None,
    year: int | None = None,
    month: int | None = None,
) -> dict:
    """Monthly financial summary with segregated Accrual and Cash views."""
    from datetime import date
    from ..services.financial_summary import get_financial_summary

    if period:
        parts = period.strip().split("-")
        y, m = int(parts[0]), int(parts[1])
    elif year is not None and month is not None:
        y, m = int(year), int(month)
    else:
        today = date.today()
        y, m = today.year, today.month

    return get_financial_summary(db, year=y, month=m)
