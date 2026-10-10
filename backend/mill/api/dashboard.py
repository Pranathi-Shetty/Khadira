"""Dashboard router: order counts + low-stock yarn alerts."""

from fastapi import APIRouter
from sqlalchemy import func, select

from ..models import Order
from ..services.inventory import low_stock_yarn
from .deps import Db, can

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Db, _: can("reports.read")) -> dict:
    order_counts = {
        status: db.scalar(select(func.count()).where(Order.status == status))
        for status in ("draft", "confirmed", "in_production", "completed", "cancelled")
    }
    alerts = low_stock_yarn(db)
    return {"order_counts": order_counts, "low_stock_alerts": alerts}
