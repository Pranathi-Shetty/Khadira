"""SQLAlchemy models for Khadira."""

from .base import Base
from .core import (
    AuditLog, Item, Location, Notification, Session, StockCountLine, StockCountSession, StockLevel, StockMove, User, UserRole,
    ITEM_YARN, ITEM_FABRIC,
)
from .partners import Buyer, Supplier
from .purchasing import PurchaseOrder, PurchaseOrderLine, YarnLot, YarnReceipt
from .orders import Order, OrderLine
from .production import Machine, MachineDowntime, ProductionRun, Roll, RollDefect, RollEvent, RunMaterial, RunReconciliation
from .finance import Invoice, InvoiceLine, Payment
from .settings import Setting
from .workforce import Worker, AttendanceEntry, WageRun, WageRunLine
from .costing import OrderCost

__all__ = [
    "Base",
    "AuditLog", "Item", "Location", "Notification", "Session", "StockCountLine", "StockCountSession", "StockLevel", "StockMove", "User", "UserRole",
    "ITEM_YARN", "ITEM_FABRIC",
    "Buyer", "Supplier",
    "PurchaseOrder", "PurchaseOrderLine", "YarnLot", "YarnReceipt",
    "Order", "OrderLine",
    "Machine", "MachineDowntime", "ProductionRun", "Roll", "RollDefect", "RollEvent", "RunMaterial", "RunReconciliation",
    "Invoice", "InvoiceLine", "Payment",
    "Setting",
    "Worker", "AttendanceEntry", "WageRun", "WageRunLine",
    "OrderCost",
]

# Re-export enums and models from models.py for backward compatibility with test_erp.py
import importlib.util
from pathlib import Path

_models_py = Path(__file__).parent.parent / "models.py"
if _models_py.exists():
    _spec = importlib.util.spec_from_file_location("mill._legacy_models", _models_py)
    if _spec and _spec.loader:
        _legacy = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_legacy)
        for _k in dir(_legacy):
            if not _k.startswith("_") and _k not in globals():
                globals()[_k] = getattr(_legacy, _k)

