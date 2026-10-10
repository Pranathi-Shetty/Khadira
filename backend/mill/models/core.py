"""Core domain models: users, items, locations, stock, audit."""

import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

ITEM_YARN = "yarn"
import enum

ITEM_FABRIC = "fabric"


class UserRole(str, enum.Enum):
    admin = "admin"
    owner = "owner"
    store = "store"
    floor_supervisor = "floor_supervisor"
    qc = "qc"
    office = "office"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    full_name: Mapped[str | None] = mapped_column(String(200))
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="office")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "user_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, default=lambda: secrets.token_hex(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="sessions")


class Item(Base):
    """Yarn or fabric catalogue entry."""
    __tablename__ = "item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # yarn | fabric
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    # For yarn: count/denier. For fabric: gsm, width_cm, yarn_kg_per_meter
    count_denier: Mapped[str | None] = mapped_column(String(40))
    gsm: Mapped[int | None] = mapped_column(Integer)
    width_cm: Mapped[int | None] = mapped_column(Integer)
    yarn_kg_per_meter: Mapped[float | None] = mapped_column(Numeric(10, 4))
    reorder_point_kg: Mapped[int] = mapped_column(Integer, default=0)  # grams
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Location(Base):
    __tablename__ = "location"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class StockLevel(Base):
    __tablename__ = "stock_level"
    __table_args__ = (UniqueConstraint("item_id", "location_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), nullable=False)
    qty_g: Mapped[int] = mapped_column(BigInteger, default=0)  # grams for yarn; cm for fabric

    item: Mapped[Item] = relationship()
    location: Mapped[Location] = relationship()


class StockMove(Base):
    __tablename__ = "stock_move"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), nullable=False)
    delta_g: Mapped[int] = mapped_column(BigInteger, nullable=False)  # positive=in, negative=out
    ref: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    item: Mapped[Item] = relationship()
    location: Mapped[Location] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(60))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

class StockCountSession(Base):
    __tablename__ = "stock_count_session"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft") # draft | pending_approval | approved | rejected
    counter_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    location: Mapped[Location] = relationship()
    lines: Mapped[list["StockCountLine"]] = relationship(back_populates="session", cascade="all, delete-orphan")

class StockCountLine(Base):
    __tablename__ = "stock_count_line"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("stock_count_session.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    system_qty_g: Mapped[int] = mapped_column(BigInteger, nullable=False)
    counted_qty_g: Mapped[int] = mapped_column(BigInteger, nullable=False)
    variance_g: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200))
    
    session: Mapped[StockCountSession] = relationship(back_populates="lines")
    item: Mapped[Item] = relationship()


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_role: Mapped[str | None] = mapped_column(String(40))
    recipient_id: Mapped[int | None] = mapped_column(ForeignKey("user_account.id"))
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

