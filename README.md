# 🏭 Khadira Textile Mills — Full-Stack ERP Platform

A unified, full-stack ERP system purpose-built for textile mill operations — from raw yarn purchasing through production, quality control, dispatch, and invoicing. Features a rich React dashboard with role-based access and a high-performance FastAPI backend.

---

## 🏗️ Architecture

```
khadira/
├── src/                    # React frontend (Vite)
│   ├── App.jsx             # Main application & ERP dashboard
│   ├── App.css             # Landing page styles
│   ├── everest-erp.css     # ERP dashboard design system
│   ├── services/api.js     # API client layer
│   └── assets/             # Static assets
├── public/                 # Public assets (images, icons, favicon)
├── backend/                # FastAPI backend
│   ├── app.py              # ASGI entry point
│   ├── mill/
│   │   ├── main.py         # Application factory
│   │   ├── config.py       # Settings & environment
│   │   ├── db.py           # Database session factory
│   │   ├── auth.py         # Authentication & session management
│   │   ├── permissions.py  # RBAC permission checks
│   │   ├── seed.py         # Demo data seeder
│   │   ├── models/         # SQLAlchemy 2.0 models
│   │   ├── services/       # Business logic layer (16 modules)
│   │   └── api/            # FastAPI route handlers
│   ├── migrations/         # Alembic schema migrations
│   ├── tests/              # Pytest test suite
│   └── requirements.txt    # Python dependencies
├── docs/                   # Documentation
├── vite.config.js          # Vite config with API proxy
└── package.json            # Node dependencies & scripts
```

### Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite 8, Lucide React icons |
| **Backend** | FastAPI, Uvicorn, Python 3.11+ |
| **ORM & Migrations** | SQLAlchemy 2.0, Alembic |
| **Database** | SQLite (development), configurable via `DATABASE_URL` |
| **Auth** | Session cookies with bcrypt password hashing |
| **API Proxy** | Vite dev server proxies `/api` → `http://127.0.0.1:8000` |

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** ≥ 18 and **npm**
- **Python** ≥ 3.11 with `venv`

### 1. Clone & Install Frontend Dependencies

```bash
git clone <repo-url> && cd khadira
npm install
```

### 2. Set Up the Backend

```bash
cd backend
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # Configure as needed
```

### 3. Seed Demo Data

You can choose between the comprehensive demonstration dataset (recommended) or the minimal baseline dataset:

#### Option A: Full Demonstration Dataset (`mill_demo.db`) — Recommended
```bash
cd backend
# Pre-seeded database is already included, or re-generate with:
python -m mill.seed_demo
```
Includes:
- **24 Buyer Orders** (`ORD-2026-00001` to `ORD-2026-00024`) spanning draft, confirmed, in-production, QC, ready, dispatched, and cancelled.
- **311 Fabric Rolls** (`ROLL-000001` to `ROLL-000311`) with ASTM 4-point grades (Grade A, B, C) and lifecycle statuses (passed, in_store, dispatched, awaiting_qc, rework, rejected).
- **8 Mill Workers** across weaving, spinning, dyeing, and QC departments.
- **112 Shift Attendance Entries** across morning, afternoon, and night shifts.
- **2 Wage-Run Payroll Cycles** (September 2026 finalised, October 2026 draft) with calculated allowances and net payouts.
- **Order-Level & Roll-Level Costing** (yarn consumption, allocated wages, mill overhead).

To run the backend with this dataset, set `DATABASE_URL` in `backend/.env`:
```ini
DATABASE_URL=sqlite:///./mill_demo.db
```

#### Option B: Minimal Baseline Dataset (`mill.db`)
```bash
cd backend
python -m mill.seed
```
Generates minimal starter seed (6 users, 7 catalog items, 3 machines, 3 orders, 3 rolls).

### 4. Start Both Servers

**Terminal 1 — Backend API:**
```bash
cd backend
uvicorn app:app --reload --port 8000
```
> API docs available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

**Terminal 2 — Frontend Dev Server:**
```bash
npm run dev
```
> Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🔐 Demo Credentials

All roles can authenticate using the 1-click demo buttons in the login modal, or with the credentials below:

| Role | Username | Password | Access & Responsibilities |
|---|---|---|---|
| **Plant Director** | `admin` | `ETM-2026` / `khadira2026!` | Full mill control, master overrides, all dashboards |
| **Accounts & Owner** | `owner` / `office` | `ETM-2026` / `khadira2026!` | Buyer orders, pricing, ledger, finance, delivery dates |
| **Store Manager** | `store` | `ETM-2026` / `khadira2026!` | Yarn & fabric stock catalogue, low-stock alerts, inventory |
| **Floor Supervisor** | `supervisor` / `floor_supervisor` | `ETM-2026` / `khadira2026!` | Looms & machine telemetry, production runs, order assignments |
| **QC Inspector** | `qc` | `ETM-2026` / `khadira2026!` | Digital roll inspection, pass/rework/reject routing |

---

## 📦 API Modules

The backend exposes a comprehensive REST API organized into the following domains:

| Module | Endpoint Prefix | Description |
|---|---|---|
| **Auth** | `/api/auth` | Login, logout, session management, current user |
| **Dashboard** | `/api/dashboard` | Aggregated KPIs and overview metrics |
| **Items** | `/api/items` | Yarn & fabric item catalogue (CRUD) |
| **Partners** | `/api/partners` | Suppliers & buyers management |
| **Purchasing** | `/api/purchasing` | Purchase orders, receipts, yarn lot tracking |
| **Orders** | `/api/orders` | Buyer orders, confirmation, progress tracking |
| **Machines** | `/api/machines` | Machine fleet registry and configuration |
| **Production** | `/api/production` | Production runs, stage advancement, yarn consumption |
| **Rolls** | `/api/rolls` | Roll creation, metadata, status lifecycle |
| **QC** | `/api/rolls/{id}/inspect` | Quality inspection verdicts (pass/fail/hold) |
| **Dispatch** | `/api/dispatch` | Roll dispatch, stock deduction, delivery |
| **Finance** | `/api/finance` | Invoices, payments, buyer/supplier ledger |
| **Inventory** | `/api/inventory` | Stock levels, movements, location tracking |
| **Reports** | `/api/reports` | Production, financial, and operational reports |
| **Notifications** | `/api/notifications` | System alerts and low-stock notifications |
| **Settings** | `/api/settings` | Configurable mill parameters (overhead rates, etc.) |

---

## 📡 Client Layer & Pagination (`requestAllPages`)

The frontend communicates with the FastAPI backend through a typed API client in `src/services/api.js`.

### Automatic Page Traversal (`requestAllPages`)
For high-volume datasets (such as 311 fabric rolls or 24 buyer orders), the API client implements `requestAllPages`:
- **Iterative page-by-page traversal**: Automatically requests sequential pages (`page=1`, `page=2`, ...) until all records are retrieved.
- **Envelope normalization**: Handles paginated API envelopes (`{ items: [...], total, page, page_size }`) and flat arrays seamlessly.
- **Convenience helpers**:
  ```javascript
  import { requestAllPages, MillAPI } from './services/api';

  // Retrieve all 311 rolls automatically across all pages
  const allRolls = await MillAPI.getAllRolls();

  // Retrieve all 24 orders with optional filters
  const allOrders = await MillAPI.getAllOrders();

  // Generic full-collection retrieval
  const items = await requestAllPages('items', { page_size: 100 });
  ```

---

## 🔄 Core Business Workflows

### Purchasing → Inventory
Purchase orders → Supplier receipts → Yarn lot recording → Stock movements → Moving-average cost recalculation

### Order → Production → QC → Dispatch
Buyer order confirmation (yarn stock check) → Production run assignment → Stage-by-stage advancement → Roll creation → QC inspection (pass/fail/hold) → Finished-goods storage → Dispatch → Invoice generation

### Finance
Sale & purchase invoices → Partial payments → Outstanding tracking → Ledger management

### Key Business Rules
- **Stock units**: Yarn in grams, fabric in centimetres (API converts to kg/m)
- **Non-negative stock**: Enforced at database level via `CHECK` constraints
- **Moving-average costing**: Recalculated on every yarn receipt
- **Production costing**: Yarn cost snapshot at issue time prevents historical drift
- **Order progress**: Based on passed roll lengths vs. order quantity
- **Dispatch**: Atomic transaction — validates rolls, deducts stock, creates invoice

> See [`docs/business-rules.md`](docs/business-rules.md) for the full specification.

---

## 🧪 Testing

```bash
cd backend

# Run the main test suite
python -m pytest tests/

# Run all tests including extended ERP tests
python -m pytest tests/ --override-ini="addopts="

# Run a specific test file
python -m pytest tests/test_e2e_flow.py -v
```

### Test Structure

| File | Coverage |
|---|---|
| `tests/conftest.py` | Shared fixtures, test DB setup, auth helpers |
| `tests/test_e2e_flow.py` | End-to-end workflow: purchase → production → dispatch |
| `tests/test_step2.py` | Service-layer and API integration tests |
| `tests/test_erp.py` | Extended ERP module tests (excluded by default) |

---

## ⚙️ Configuration

Backend configuration is managed via environment variables (`.env` file in `backend/`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./mill.db` | Database connection string |
| `SECRET_KEY` | `change-me-in-production` | Session signing key |
| `SESSION_HOURS` | `8` | Session expiry duration |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `COOKIE_SECURE` | `false` | Set `true` in production (HTTPS) |
| `SERVERLESS` | `false` | Enable serverless-compatible DB mode |

---

## 📜 npm Scripts

| Script | Command | Description |
|---|---|---|
| `npm run dev` | `vite` | Start the Vite dev server with HMR |
| `npm run build` | `vite build` | Production build |
| `npm run preview` | `vite preview` | Preview the production build |
| `npm run lint` | `oxlint` | Run the OxLint linter |
| `npm run backend` | `uvicorn app:app --reload` | Start the FastAPI backend |
| `npm run backend:seed` | `python -m mill.seed` | Seed the database with demo data |
| `npm run backend:test` | `pytest tests/` | Run backend tests |

---

## 📂 Documentation

- [`docs/backend_overview.md`](docs/backend_overview.md) — Architecture, code organization, and workflow details
- [`docs/business-rules.md`](docs/business-rules.md) — Approved business rules for wages, stock, costing, dispatch, and payments

---

## 🛣️ Roadmap

- [ ] Attendance & wage/payroll processing
- [ ] Roll QR label generation
- [ ] Yarn lot → roll traceability
- [ ] Statutory payroll compliance (PF, ESI, TDS)
- [ ] Bank reconciliation
- [ ] Buyer portal & notifications
- [ ] Biometric attendance integration

---

## 📄 License

Private — All rights reserved.
