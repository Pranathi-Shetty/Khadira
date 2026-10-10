"""Calculated order cost snapshot; material valuation may be incomplete."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class OrderCost(Base):
    __tablename__ = "order_cost"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("sale_order.id"), unique=True, nullable=False)
    yarn_used_g: Mapped[int] = mapped_column(Integer, default=0)
    material_cost_paise: Mapped[int | None] = mapped_column(Integer)
    allocated_wage_paise: Mapped[int] = mapped_column(Integer, default=0)
    overhead_paise: Mapped[int] = mapped_column(Integer, default=0)
    known_cost_paise: Mapped[int] = mapped_column(Integer, default=0)
    passed_metres: Mapped[int] = mapped_column(Integer, default=0)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
