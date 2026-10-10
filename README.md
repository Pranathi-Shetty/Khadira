# 🏭 Khadira Textile Mills ERP

![Status](https://img.shields.io/badge/Status-MVP_Complete-green)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)

A unified, high-performance ERP system designed specifically for Khadira Textile Mills. This platform replaces notebooks, paper slips, and phone calls with a single digital backbone that connects the floor to the front office.

## 🏗️ Architecture

- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, SQLite (Dev) / PostgreSQL (Prod)
- **Design Philosophy**: A transaction-safe backend for textile mill operations, with a documented REST API.

## 📦 Core Modules

| Module | Features & Capabilities |
|---|---|
| **Inventory** | Yarn & fabric catalogue with real-time moving-average cost calculation. |
| **Purchasing** | Purchase orders, yarn receipt, supplier bills, and payable tracking. |
| **Orders** | Buyer orders with automated yarn sufficiency checks and visual progress tracking. |
| **Machines** | Real-time machine status tracking (`running`, `idle`, `breakdown`) & change logs. |
| **Production** | Production runs, precise yarn issuance, and individual roll creation (atomic tracking). |
| **QC** | Individual roll inspection routing: `passed` / `rework` / `rejected`. |
| **Dispatch** | Atomic confirmation with automated stock-out deductions and invoice generation. |
| **Finance** | Buyer invoices, incoming payments, and comprehensive receivables/payables ledgers. |

---

## 🚀 Quick Start

### 1. Backend

The backend is built with FastAPI. We recommend using a virtual environment.

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt

# Load initial schema, roles, partners, stock, and workers
python -m mill.seed            

# Start the development server
python -m uvicorn app:app --reload --port 8000
```

> **Note:** Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive Swagger API documentation.

#### Demo credentials

| Role | Username | Password |
|---|---|---|
| **Admin** | `admin` | `khadira2026!` |
| **Owner** | `owner` | `khadira2026!` |
| **Store** | `store` | `khadira2026!` |
| **Floor Supervisor** | `floor_supervisor` | `khadira2026!` |
| **QC Officer** | `qc` | `khadira2026!` |
| **Office** | `office` | `khadira2026!` |

---

## 🧪 Testing

The backend suite covers health checks, authentication, purchasing, sales orders, inventory, production, QC, and dispatch.

```bash
cd backend
python -m pytest tests/ -v
```

---

## 🔒 Key Design Decisions

- **Money in Paise**: All financial amounts are stored as integers (paise) to prevent floating-point rounding errors.
- **Stock in Sub-units**: Yarn is tracked in **grams**, fabric in **centimetres**. A strict DB constraint ensures stock is `never-negative`.
- **Atomic Roll Lifecycle**: `produced` → `awaiting_qc` → `passed` → `in_store` → `dispatched` (plus `rework`/`rejected` paths).
- **Wage Run Immutability**: Finalised wage runs cannot be edited or tampered with; necessary corrections require formal adjustment entries.
- **Cost Traceability**: Every order cost securely traces back to the specific yarn-issue cost snapshots at the exact time of issuance.
- **Double-Dispatch Prevention**: Guarded by a strict `UNIQUE` constraint on `dispatch_rolls.roll_id`.

---

## 📖 Documentation

See [`docs/business-rules.md`](docs/business-rules.md) for the full set of established business rules, validation constraints, and workflow definitions approved for the MVP.
