# 🏭 Khadira Textile Mills ERP

![Status](https://img.shields.io/badge/Status-MVP_Complete-green)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/Frontend-Next.js_15-000000)

A unified, high-performance ERP system designed specifically for Khadira Textile Mills. This platform replaces notebooks, paper slips, and phone calls with a single digital backbone that connects the floor to the front office.

## 🏗️ Architecture

- **Frontend**: Next.js 15, TypeScript, TailwindCSS, Lucide-React (Modern UI with Glassmorphism)
- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, SQLite (Dev) / PostgreSQL (Prod)
- **Design Philosophy**: Dynamic, responsive, and visually premium interface built over a strictly constrained, transaction-safe relational database.

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
| **Attendance** | Worker register with robust hourly/piece-rate basis tracking. |
| **Wages** | Monthly wage runs with a multi-step `draft` → `approve` → `finalise` flow. |
| **Costing** | Advanced order & roll costing: Yarn cost + Wages + Overhead / passed metres. |

---

## 🚀 Quick Start

### 1. Backend

The backend is built with FastAPI. We recommend using a virtual environment.

```bash
cd backend
pip install -r requirements.txt

# Load initial schema, roles, partners, stock, and workers
python -m mill.seed            

# Start the development server
python -m uvicorn app:app --reload --port 8000
```

> **Note:** Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive Swagger API documentation.

#### Demo credentials

| Role | Username | Password |
|---|---|---|
| **Admin** | `admin` | `admin123` |
| **Owner** | `owner` | `owner123` |
| **Store** | `store` | `store123` |
| **Floor Supervisor** | `supervisor` | `super123` |
| **QC Officer** | `qc_officer` | `qc1234` |
| **Office** | `office` | `office123` |

### 2. Frontend

The frontend is a Next.js application styled with TailwindCSS.

```bash
cd frontend
npm install
npm run dev
```

> **Note:** Open [http://localhost:3000](http://localhost:3000) to view the application dashboard.

---

## 🧪 Testing

The backend includes a comprehensive, 18-flow automated test suite covering edge cases, race conditions, and complete production cycles.

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
