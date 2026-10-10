"""All SQLAlchemy models for Everest Textile Mills ERP."""
from __future__ import annotations

import enum
from datetime import datetime, date

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, Date, DateTime,
    Enum, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from mill.database import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_utc():
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ItemType(str, enum.Enum):
    yarn = "yarn"
    fabric = "fabric"

class WageBasis(str, enum.Enum):
    hourly = "hourly"
    piece_rate = "piece_rate"

class AttendanceStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    voided = "voided"

class WageRunStatus(str, enum.Enum):
    draft = "draft"
    finalised = "finalised"

class MachineType(str, enum.Enum):
    spinning = "spinning"
    weaving = "weaving"
    dyeing = "dyeing"

class MachineStatus(str, enum.Enum):
    idle = "idle"
    running = "running"
    breakdown = "breakdown"
    maintenance = "maintenance"

class PurchaseOrderStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    received = "received"
    cancelled = "cancelled"

class OrderStatus(str, enum.Enum):
    pending = "pending"
    in_production = "in_production"
    qc = "qc"
    ready = "ready"
    dispatched = "dispatched"
    cancelled = "cancelled"

class RunStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"

class RollStatus(str, enum.Enum):
    produced = "produced"
    awaiting_qc = "awaiting_qc"
    passed = "passed"
    rework = "rework"
    rejected = "rejected"
    in_store = "in_store"
    dispatched = "dispatched"

class QCResult(str, enum.Enum):
    passed = "passed"
    rework = "rework"
    rejected = "rejected"

class DispatchStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"

class InvoiceStatus(str, enum.Enum):
    unpaid = "unpaid"
    partial = "partial"
    paid = "paid"

class BillStatus(str, enum.Enum):
    unpaid = "unpaid"
    partial = "partial"
    paid = "paid"

class StockMoveKind(str, enum.Enum):
    receipt = "receipt"
    yarn_issue = "yarn_issue"
    fabric_in = "fabric_in"
    fabric_out = "fabric_out"
    adjustment = "adjustment"

class UserRole(str, enum.Enum):
    admin = "admin"
    owner = "owner"
    store = "store"
    floor_supervisor = "floor_supervisor"
    qc = "qc"
    office = "office"


# ---------------------------------------------------------------------------
# Core / Auth
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    full_name = Column(String(128), nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=now_utc)


class Activity(Base):
    """Append-only audit log."""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(128), nullable=False)
    entity = Column(String(64), nullable=True)
    entity_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    user = relationship("User")


class NumberSequence(Base):
    __tablename__ = "number_sequences"

    name = Column(String(64), primary_key=True)
    last_value = Column(Integer, default=0, nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False)


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    item_type = Column(Enum(ItemType), nullable=False)
    yarn_type = Column(String(64), nullable=True)   # cotton, polyester, etc.
    colour = Column(String(64), nullable=True)
    unit = Column(String(16), nullable=False)        # "kg" or "m"
    # grams per metre of fabric (for yarn requirement calc); null for yarn items
    yarn_grams_per_metre = Column(Integer, nullable=True)
    # Moving-average cost stored in paise; updated on each receipt
    average_cost_paise = Column(BigInteger, default=0, nullable=False)
    reorder_point_grams = Column(Integer, default=0, nullable=False)
    sale_price_paise_per_metre = Column(BigInteger, default=0, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)

    stock_level = relationship("StockLevel", back_populates="item", uselist=False)


class StoreLocation(Base):
    __tablename__ = "store_locations"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(128), nullable=False)


# ---------------------------------------------------------------------------
# Partners
# ---------------------------------------------------------------------------

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    contact_name = Column(String(128), nullable=True)
    phone = Column(String(32), nullable=True)
    email = Column(String(128), nullable=True)
    address = Column(Text, nullable=True)
    payment_terms_days = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)


class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    contact_name = Column(String(128), nullable=True)
    phone = Column(String(32), nullable=True)
    email = Column(String(128), nullable=True)
    address = Column(Text, nullable=True)
    payment_terms_days = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)


# ---------------------------------------------------------------------------
# Purchasing / Yarn Intake
# ---------------------------------------------------------------------------

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True)
    doc_no = Column(String(32), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity_grams = Column(BigInteger, nullable=False)
    unit_cost_paise = Column(BigInteger, nullable=False)
    status = Column(Enum(PurchaseOrderStatus), default=PurchaseOrderStatus.draft)
    expected_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    supplier = relationship("Supplier")
    item = relationship("Item")
    receipts = relationship("YarnReceipt", back_populates="purchase_order")
    bills = relationship("SupplierBill", back_populates="purchase_order")


class YarnReceipt(Base):
    __tablename__ = "yarn_receipts"

    id = Column(Integer, primary_key=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    received_grams = Column(BigInteger, nullable=False)
    unit_cost_paise = Column(BigInteger, nullable=False)   # snapshot at receipt time
    received_date = Column(Date, nullable=False)
    lot_no = Column(String(64), nullable=True)
    received_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    purchase_order = relationship("PurchaseOrder", back_populates="receipts")
    yarn_lot = relationship("YarnLot", back_populates="receipt", uselist=False)


class YarnLot(Base):
    __tablename__ = "yarn_lots"

    id = Column(Integer, primary_key=True)
    lot_no = Column(String(64), unique=True, nullable=False)
    receipt_id = Column(Integer, ForeignKey("yarn_receipts.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity_grams = Column(BigInteger, nullable=False)
    cost_paise = Column(BigInteger, nullable=False)  # snapshot
    receipt_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=now_utc)

    receipt = relationship("YarnReceipt", back_populates="yarn_lot")
    supplier = relationship("Supplier")
    item = relationship("Item")


# ---------------------------------------------------------------------------
# Supplier Bills & Payments
# ---------------------------------------------------------------------------

class SupplierBill(Base):
    __tablename__ = "supplier_bills"

    id = Column(Integer, primary_key=True)
    doc_no = Column(String(32), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    amount_paise = Column(BigInteger, nullable=False)
    bill_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(Enum(BillStatus), default=BillStatus.unpaid)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    supplier = relationship("Supplier")
    purchase_order = relationship("PurchaseOrder", back_populates="bills")
    payments = relationship("SupplierPayment", back_populates="bill")


class SupplierPayment(Base):
    __tablename__ = "supplier_payments"

    id = Column(Integer, primary_key=True)
    bill_id = Column(Integer, ForeignKey("supplier_bills.id"), nullable=False)
    amount_paise = Column(BigInteger, nullable=False)
    payment_date = Column(Date, nullable=False)
    method = Column(String(32), nullable=True)
    reference = Column(String(128), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    bill = relationship("SupplierBill", back_populates="payments")

    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_supplier_payment_positive"),
    )


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------

class StockLevel(Base):
    __tablename__ = "stock_levels"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), unique=True, nullable=False)
    location_id = Column(Integer, ForeignKey("store_locations.id"), nullable=False)
    # yarn: grams; fabric: centimetres
    quantity = Column(BigInteger, default=0, nullable=False)

    item = relationship("Item", back_populates="stock_level")
    location = relationship("StoreLocation")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_stock_non_negative"),
    )


class StockMove(Base):
    __tablename__ = "stock_moves"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("store_locations.id"), nullable=False)
    # positive = in, negative = out (grams or cm)
    quantity_delta = Column(BigInteger, nullable=False)
    # cost snapshot in paise per gram / per cm at time of move
    unit_cost_paise = Column(BigInteger, default=0, nullable=False)
    kind = Column(Enum(StockMoveKind), nullable=False)
    reference_id = Column(Integer, nullable=True)
    reference_type = Column(String(64), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    item = relationship("Item")


# ---------------------------------------------------------------------------
# Machines
# ---------------------------------------------------------------------------

class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    machine_type = Column(Enum(MachineType), nullable=False)
    status = Column(Enum(MachineStatus), default=MachineStatus.idle)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    status_logs = relationship("MachineStatusLog", back_populates="machine")


class MachineStatusLog(Base):
    __tablename__ = "machine_status_logs"

    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    from_status = Column(Enum(MachineStatus), nullable=True)
    to_status = Column(Enum(MachineStatus), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    machine = relationship("Machine", back_populates="status_logs")


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    doc_no = Column(String(32), unique=True, nullable=False)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity_metres = Column(Integer, nullable=False)         # metres
    deadline = Column(Date, nullable=False)
    tolerance_pct = Column(Integer, default=5, nullable=False)
    price_paise_per_metre = Column(BigInteger, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.pending)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    buyer = relationship("Buyer")
    item = relationship("Item")
    runs = relationship("ProductionRun", back_populates="order")
    rolls = relationship("Roll", back_populates="order")
    dispatches = relationship("Dispatch", back_populates="order")
    costing = relationship("OrderCost", back_populates="order", uselist=False)


# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------

class ProductionRun(Base):
    __tablename__ = "production_runs"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    stage = Column(String(32), nullable=False)   # spinning | weaving | dyeing
    shift = Column(String(16), nullable=False)   # morning | afternoon | night
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    yarn_lot_id = Column(Integer, ForeignKey("yarn_lots.id"), nullable=True)
    yarn_issued_grams = Column(BigInteger, default=0, nullable=False)
    # cost snapshot at time of issue (paise per gram)
    yarn_cost_paise_per_gram = Column(BigInteger, default=0, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(Enum(RunStatus), default=RunStatus.active)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    order = relationship("Order", back_populates="runs")
    machine = relationship("Machine")
    yarn_lot = relationship("YarnLot")
    rolls = relationship("Roll", back_populates="run")


# ---------------------------------------------------------------------------
# Rolls
# ---------------------------------------------------------------------------

class Roll(Base):
    __tablename__ = "rolls"

    id = Column(Integer, primary_key=True)
    roll_no = Column(String(32), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=False)
    shift = Column(String(16), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    yarn_lot_id = Column(Integer, ForeignKey("yarn_lots.id"), nullable=True)
    length_cm = Column(Integer, nullable=False)          # centimetres
    weight_grams = Column(Integer, nullable=True)
    status = Column(Enum(RollStatus), default=RollStatus.produced)
    created_at = Column(DateTime, default=now_utc)

    order = relationship("Order", back_populates="rolls")
    machine = relationship("Machine")
    run = relationship("ProductionRun", back_populates="rolls")
    yarn_lot = relationship("YarnLot")
    events = relationship("RollEvent", back_populates="roll")
    qc_inspections = relationship("QCInspection", back_populates="roll")
    costing = relationship("RollCost", back_populates="roll", uselist=False)

    __table_args__ = (
        UniqueConstraint("roll_no", name="uq_roll_no"),
    )


class RollEvent(Base):
    """Append-only status-change log for each roll."""
    __tablename__ = "roll_events"

    id = Column(Integer, primary_key=True)
    roll_id = Column(Integer, ForeignKey("rolls.id"), nullable=False)
    from_status = Column(Enum(RollStatus), nullable=True)
    to_status = Column(Enum(RollStatus), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    roll = relationship("Roll", back_populates="events")


# ---------------------------------------------------------------------------
# Quality Control
# ---------------------------------------------------------------------------

class QCInspection(Base):
    __tablename__ = "qc_inspections"

    id = Column(Integer, primary_key=True)
    roll_id = Column(Integer, ForeignKey("rolls.id"), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    result = Column(Enum(QCResult), nullable=False)
    defects = Column(Text, nullable=True)    # JSON list: ["hole","colour_mismatch",...]
    notes = Column(Text, nullable=True)
    inspected_at = Column(DateTime, default=now_utc)

    roll = relationship("Roll", back_populates="qc_inspections")
    inspector = relationship("User")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

class Dispatch(Base):
    __tablename__ = "dispatches"

    id = Column(Integer, primary_key=True)
    doc_no = Column(String(32), unique=True, nullable=False)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dispatch_date = Column(Date, nullable=False)
    vehicle_no = Column(String(32), nullable=True)
    driver_name = Column(String(128), nullable=True)
    status = Column(Enum(DispatchStatus), default=DispatchStatus.draft)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    buyer = relationship("Buyer")
    order = relationship("Order", back_populates="dispatches")
    dispatch_rolls = relationship("DispatchRoll", back_populates="dispatch")
    invoice = relationship("Invoice", back_populates="dispatch", uselist=False)


class DispatchRoll(Base):
    __tablename__ = "dispatch_rolls"

    id = Column(Integer, primary_key=True)
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), nullable=False)
    roll_id = Column(Integer, ForeignKey("rolls.id"), nullable=False)

    dispatch = relationship("Dispatch", back_populates="dispatch_rolls")
    roll = relationship("Roll")

    __table_args__ = (
        UniqueConstraint("roll_id", name="uq_dispatch_roll"),   # no double dispatch
    )


# ---------------------------------------------------------------------------
# Finance – Buyer Side
# ---------------------------------------------------------------------------

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    doc_no = Column(String(32), unique=True, nullable=False)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=False)
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), nullable=True)
    amount_paise = Column(BigInteger, nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.unpaid)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    buyer = relationship("Buyer")
    dispatch = relationship("Dispatch", back_populates="invoice")
    payments = relationship("BuyerPayment", back_populates="invoice")


class BuyerPayment(Base):
    __tablename__ = "buyer_payments"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount_paise = Column(BigInteger, nullable=False)
    payment_date = Column(Date, nullable=False)
    method = Column(String(32), nullable=True)
    reference = Column(String(128), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    invoice = relationship("Invoice", back_populates="payments")

    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_buyer_payment_positive"),
    )


# ---------------------------------------------------------------------------
# Workers & Attendance
# ---------------------------------------------------------------------------

class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True)
    employee_id = Column(String(32), unique=True, nullable=False)
    full_name = Column(String(128), nullable=False)
    wage_basis = Column(Enum(WageBasis), nullable=False)
    hourly_rate_paise = Column(BigInteger, default=0, nullable=False)
    piece_rate_paise = Column(BigInteger, default=0, nullable=False)
    phone = Column(String(32), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)

    attendance_entries = relationship("AttendanceEntry", back_populates="worker")


class AttendanceEntry(Base):
    __tablename__ = "attendance_entries"

    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    work_date = Column(Date, nullable=False)
    shift = Column(String(16), nullable=False)        # morning | afternoon | night
    hours_worked = Column(Integer, nullable=True)     # in minutes (for hourly)
    pieces_produced = Column(Integer, nullable=True)  # for piece-rate
    # order/run linkage for direct labour costing
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=True)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.draft)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    void_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    worker = relationship("Worker", back_populates="attendance_entries")

    __table_args__ = (
        CheckConstraint("hours_worked IS NULL OR hours_worked > 0", name="ck_att_hours_positive"),
        CheckConstraint("pieces_produced IS NULL OR pieces_produced > 0", name="ck_att_pieces_positive"),
        UniqueConstraint("worker_id", "work_date", "shift", name="uq_attendance_per_shift"),
    )


# ---------------------------------------------------------------------------
# Wage Runs
# ---------------------------------------------------------------------------

class WageRun(Base):
    __tablename__ = "wage_runs"

    id = Column(Integer, primary_key=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(Enum(WageRunStatus), default=WageRunStatus.draft)
    calculated_at = Column(DateTime, nullable=True)
    finalised_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    finalised_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_utc)

    lines = relationship("WageRunLine", back_populates="wage_run")

    __table_args__ = (
        UniqueConstraint("period_start", "period_end", name="uq_wage_run_period"),
    )


class WageRunLine(Base):
    __tablename__ = "wage_run_lines"

    id = Column(Integer, primary_key=True)
    wage_run_id = Column(Integer, ForeignKey("wage_runs.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    total_hours_minutes = Column(Integer, default=0, nullable=False)
    total_pieces = Column(Integer, default=0, nullable=False)
    applied_rate_paise = Column(BigInteger, nullable=False)   # snapshot of rate used
    base_wage_paise = Column(BigInteger, nullable=False)
    adjustment_paise = Column(BigInteger, default=0, nullable=False)
    net_wage_paise = Column(BigInteger, nullable=False)
    note = Column(Text, nullable=True)

    wage_run = relationship("WageRun", back_populates="lines")
    worker = relationship("Worker")


# ---------------------------------------------------------------------------
# Costing
# ---------------------------------------------------------------------------

class OrderCost(Base):
    """Computed cost breakdown for one order."""
    __tablename__ = "order_costs"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    yarn_cost_paise = Column(BigInteger, default=0, nullable=False)
    allocated_wage_paise = Column(BigInteger, default=0, nullable=False)
    overhead_paise = Column(BigInteger, default=0, nullable=False)
    total_cost_paise = Column(BigInteger, default=0, nullable=False)
    passed_metres = Column(Integer, default=0, nullable=False)
    cost_per_passed_metre_paise = Column(BigInteger, default=0, nullable=False)
    # overhead method used: per_metre | pool
    overhead_method = Column(String(32), default="per_metre")
    calculated_at = Column(DateTime, default=now_utc)

    order = relationship("Order", back_populates="costing")
    roll_costs = relationship("RollCost", back_populates="order_cost")


class RollCost(Base):
    """Allocated cost breakdown for one roll."""
    __tablename__ = "roll_costs"

    id = Column(Integer, primary_key=True)
    roll_id = Column(Integer, ForeignKey("rolls.id"), unique=True, nullable=False)
    order_cost_id = Column(Integer, ForeignKey("order_costs.id"), nullable=False)
    allocated_cost_paise = Column(BigInteger, default=0, nullable=False)
    metres = Column(Integer, default=0, nullable=False)
    cost_per_metre_paise = Column(BigInteger, default=0, nullable=False)
    # "direct" if roll-level consumption recorded, else "allocated"
    cost_type = Column(String(16), default="allocated")
    calculated_at = Column(DateTime, default=now_utc)

    roll = relationship("Roll", back_populates="costing")
    order_cost = relationship("OrderCost", back_populates="roll_costs")
