# Khadira Textile Mills — Implementation & Execution Status

> **Document Version**: 1.0  
> **Last Updated**: October 11, 2026  
> **Codebase Size**: ~20,970 lines across Python, JSX, JS, CSS, HTML  
> **Status**: ✅ MVP Live (Full-Stack)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Database Schema & Models](#3-database-schema--models)
4. [Backend Services (Business Logic)](#4-backend-services-business-logic)
5. [API Endpoints](#5-api-endpoints)
6. [Authentication & Authorization (RBAC)](#6-authentication--authorization-rbac)
7. [Frontend Application](#7-frontend-application)
8. [Data Seeding & Demo Environment](#8-data-seeding--demo-environment)
9. [Testing](#9-testing)
10. [Database Migrations](#10-database-migrations)
11. [Configuration & Environment](#11-configuration--environment)
12. [File Inventory](#12-file-inventory)
13. [Implementation Status Matrix](#13-implementation-status-matrix)
14. [Known Gaps & Roadmap](#14-known-gaps--roadmap)

---

## 1. Executive Summary

Khadira is a full-stack, textile-mill ERP platform covering the complete yarn-to-dispatch lifecycle. The system is composed of:

- **React 19 + Vite 8 frontend** — A rich, role-based ERP dashboard with an artisan craft landing page, 3,934-line monolithic `App.jsx`, custom design system, and 11 sidebar navigation modules.
- **FastAPI backend** — 18 API route modules, 16 service modules, SQLAlchemy 2.0 models spanning 7 domain model files, session-cookie auth with bcrypt, Alembic migrations, and a comprehensive pytest suite.
- **SQLite database** — Development-ready with configurable `DATABASE_URL` for production databases.

### Core Workflows Implemented

| Workflow | Status | Path |
|---|---|---|
| User authentication (JWT cookie) | ✅ Complete | `POST /api/auth/login` → cookie → `GET /api/auth/me` |
| Item catalogue (yarn + fabric) | ✅ Complete | CRUD via `/api/items` |
| Supplier & buyer management | ✅ Complete | CRUD via `/api/partners/{suppliers,buyers}` |
| Purchase orders + yarn receipts | ✅ Complete | PO → confirm → receive → stock + lot |
| Buyer sales orders | ✅ Complete | Create → confirm (yarn check) → cancel |
| Machine fleet management | ✅ Complete | CRUD + active/inactive toggle |
| Production runs + stage advancement | ✅ Complete | Start → advance through stages → complete |
| Roll creation + QC inspection | ✅ Complete | Create → inspect (pass/fail/hold) → store |
| Dispatch + stock deduction | ✅ Complete | Atomic: validate rolls → deduct stock → mark dispatched |
| Finance (invoices + payments) | ✅ Complete | Sale/purchase invoices → partial payments → ledger |
| Inventory stock levels + movements | ✅ Complete | Real-time stock by item×location |
| Dashboard KPIs | ✅ Complete | Aggregated metrics endpoint |
| Notifications | ✅ Complete | Role-based alerts + mark-read |
| Reports | ✅ Complete | Production, financial, operational reports |
| Configurable settings | ✅ Complete | Key-value store for overhead rates, etc. |

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        BROWSER (localhost:5173)                              │
│  ┌────────────────────┐    ┌─────────────────────────────────────────────┐   │
│  │   Landing Page     │    │        ERP Dashboard (Role-Based)           │   │
│  │   (Artisan Craft)  │    │   ┌──────────┐ ┌────────────────────────┐  │   │
│  │   - Hero orbit     │    │   │ Sidebar  │ │ Main Workspace         │  │   │
│  │   - Product shelf  │    │   │ 11 tabs  │ │ - KPI cards            │  │   │
│  │   - Team cards     │    │   │ + nested │ │ - Data tables          │  │   │
│  │   - FAQ            │    │   │ submenu  │ │ - Live feed            │  │   │
│  │   - Login modal    │    │   └──────────┘ │ - Action buttons       │  │   │
│  └────────────────────┘    │                └────────────────────────┘  │   │
│                            └─────────────────────────────────────────────┘   │
└──────────────┬──────────────────────────────────────────────────────────────┘
               │ Vite proxy: /api → http://127.0.0.1:8000
               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (port 8000)                              │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐                │
│  │   API Layer  │  │ Service Layer   │  │   Model Layer    │                │
│  │  18 routers  │  │ 16 modules      │  │  7 model files   │                │
│  │  (FastAPI)   │→ │ (Business Logic)│→ │  (SQLAlchemy 2.0)│                │
│  └──────────────┘  └─────────────────┘  └────────┬─────────┘                │
│                                                   │                          │
│  ┌──────────────────┐  ┌───────────────┐          ▼                          │
│  │  Auth (bcrypt +  │  │  Permissions  │  ┌──────────────┐                   │
│  │  HMAC-SHA256 JWT)│  │  (RBAC Matrix)│  │  SQLite DB   │                   │
│  └──────────────────┘  └───────────────┘  │  (mill.db)   │                   │
│                                            └──────────────┘                   │
│  ┌──────────────────┐                                                        │
│  │ Alembic Migrations│ 2 versions: initial_schema + production_and_qc       │
│  └──────────────────┘                                                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Tech Stack Summary

| Component | Technology | Version |
|---|---|---|
| Frontend framework | React | 19.2.8 |
| Build tool | Vite | 8.3.0 |
| Icons | Lucide React | 1.55.0 |
| Linter | OxLint | 1.81.0 |
| Backend framework | FastAPI | ≥0.111 |
| ASGI server | Uvicorn | ≥0.29 |
| ORM | SQLAlchemy | ≥2.0 |
| Migrations | Alembic | ≥1.13 |
| Password hashing | bcrypt | ≥4.1 |
| Validation | Pydantic | ≥2.7 |
| Settings | Pydantic-Settings | ≥2.2 |
| Database | SQLite | (bundled) |
| Testing | Pytest | (dev) |

---

## 3. Database Schema & Models

### 3.1 Model Files

| File | Models Defined | Lines |
|---|---|---|
| `models/core.py` | `User`, `Session`, `Item`, `Location`, `StockLevel`, `StockMove`, `AuditLog`, `StockCountSession`, `StockCountLine`, `Notification` | 166 |
| `models/partners.py` | `Supplier`, `Buyer` | 44 |
| `models/purchasing.py` | `PurchaseOrder`, `PurchaseOrderLine`, `YarnReceipt`, `YarnLot` | 79 |
| `models/orders.py` | `Order`, `OrderLine` | 44 |
| `models/production.py` | `Machine`, `ProductionRun`, `Roll`, `RollEvent`, `RunMaterial`, `RunReconciliation`, `MachineDowntime`, `RollDefect` | 165 |
| `models/finance.py` | `Invoice`, `InvoiceLine`, `Payment` | 62 |
| `models/settings.py` | `Setting` | ~20 |

### 3.2 Entity Relationship Summary

```
User (user_account)
 ├── Session (user_session)        1:N
 └── AuditLog                      1:N

Item (yarn | fabric)
 ├── StockLevel (per location)     1:N (unique item×location)
 ├── StockMove (delta ledger)      1:N
 ├── OrderLine                     1:N
 ├── PurchaseOrderLine             1:N
 └── YarnLot                       1:N

Supplier
 └── PurchaseOrder                 1:N
      └── PurchaseOrderLine        1:N
           └── YarnReceipt         1:N
                └── YarnLot        1:1

Buyer
 ├── Order (sale_order)            1:N
 │    └── OrderLine                1:N
 └── Invoice                      1:N

Machine
 ├── ProductionRun                 1:N
 │    ├── Roll                     1:N
 │    │    ├── RollEvent           1:N
 │    │    └── RollDefect          1:N
 │    ├── RunMaterial              1:N
 │    └── RunReconciliation        1:1
 └── MachineDowntime               1:N

Location
 ├── StockLevel                    1:N
 ├── StockMove                     1:N
 └── StockCountSession             1:N
      └── StockCountLine           1:N

Invoice
 ├── InvoiceLine                   1:N
 └── Payment                      1:N

Notification (role/user-targeted)
Setting (key-value config store)
```

### 3.3 Key Model Details

#### User (`user_account`)
| Column | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `username` | String(120) | Unique, NOT NULL |
| `email` | String(200) | Nullable |
| `full_name` | String(200) | Nullable |
| `hashed_password` | String(200) | NOT NULL |
| `role` | String(40) | NOT NULL, default `office` |
| `is_active` | Boolean | default `True` |
| `created_at` | DateTime(tz) | auto UTC now |

**Roles (UserRole enum)**: `admin`, `owner`, `store`, `floor_supervisor`, `qc`, `office`

#### Item
| Column | Type | Purpose |
|---|---|---|
| `sku` | String(60) | Unique SKU identifier |
| `item_type` | String(20) | `yarn` or `fabric` |
| `count_denier` | String(40) | Yarn count (e.g., "20s", "40s") |
| `gsm` | Integer | Fabric weight (grams/sq.m) |
| `width_cm` | Integer | Fabric width |
| `yarn_kg_per_meter` | Numeric(10,4) | Fabric yarn consumption rate |
| `reorder_point_kg` | Integer | Low-stock threshold (grams) |

#### StockLevel
- Unique constraint on `(item_id, location_id)` — one record per item per location
- `qty_g` stored in **grams** (yarn) or **centimetres** (fabric)

#### Roll Status Lifecycle
| Status | Meaning |
|---|---|
| `awaiting_qc` | Created, pending inspection |
| `passed` | QC cleared |
| `failed` | QC rejected |
| `held` | QC deferred |
| `in_store` | Moved to finished goods |
| `dispatched` | Shipped to buyer |

#### Machine Stages (MACHINE_STAGES)
| Machine Type | Stage Pipeline |
|---|---|
| `spinning` | loading → spinning → doffing |
| `weaving` | warping → weaving → inspection |
| `dyeing` | prep → dyeing → finishing |

#### Invoice
- `invoice_type`: `sale` or `purchase`
- Linked to `Buyer` (sale) or `Supplier` (purchase)
- Status lifecycle: `draft` → `sent` → `paid` → `cancelled`
- `InvoiceLine`: qty × unit_price_paise + tax_pct
- `Payment`: amount_paise, method (cash/upi/neft/cheque), partial allowed

---

## 4. Backend Services (Business Logic)

All services are in `backend/mill/services/`.

| Service Module | Lines | Key Operations |
|---|---|---|
| **`auth.py`** | 78 | `hash_password`, `verify_password`, `create_session`, `user_for_token`, `logout` |
| **`inventory.py`** | 169 | `post_stock_move` (with non-negative check), `get_stock_levels`, `low_stock_alerts`, stock count sessions |
| **`production.py`** | 202 | `start_run`, `advance_run` (stage-by-stage), `complete_run`, `create_roll`, yarn consumption tracking, run reconciliation |
| **`purchasing.py`** | 114 | `create_po`, `confirm_po`, `receive_yarn` (creates lot + stock move + avg cost recalc) |
| **`orders.py`** | 95 | `create_order`, `confirm_order` (yarn stock validation), `cancel_order`, progress tracking |
| **`rolls.py`** | 114 | `create_roll`, `inspect_roll` (pass/fail/hold), `move_to_store` (finished goods stock move) |
| **`qc.py`** | 76 | `inspect_roll`, `report_defect`, `get_defects` |
| **`dispatch.py`** | 47 | `dispatch_rolls` — atomic: validate all rolls are `in_store` → deduct fabric stock → mark `dispatched` |
| **`costing.py`** | 94 | Yarn cost snapshots, overhead allocation (per-passed-metre), roll cost allocation |
| **`machines.py`** | 52 | Machine CRUD, downtime recording |
| **`stock.py`** | 62 | Stock queries, movement history, location summaries |
| **`attendance.py`** | 85 | Clock-in/out, draft → approved → voided lifecycle |
| **`wages.py`** | 105 | Monthly wage runs, hourly/piece-rate calculation, finalization |
| **`notifications.py`** | 82 | Create notifications, role-based delivery, mark-read |
| **`common.py`** | 38 | `DomainError` exception class, `set_setting` / `get_setting` helpers |

### Key Business Rules Enforced in Services

1. **Non-negative stock**: `post_stock_move()` raises `DomainError` if a deduction would make `qty_g < 0`
2. **Moving-average cost**: Recalculated on every yarn receipt in `purchasing.receive_yarn()`
3. **Yarn cost snapshot**: At production issue time, `items.average_cost_paise` is snapshotted onto the run — prevents historical cost drift
4. **Order confirmation**: `confirm_order()` estimates required yarn from `yarn_kg_per_meter × qty_meters` and rejects if stock is insufficient
5. **Dispatch atomicity**: Single transaction validates all rolls → posts stock-out moves → marks rolls dispatched
6. **Stock units**: Yarn in grams, fabric in centimetres internally; API converts to kg/m for display
7. **Overhead allocation**: Configurable paise/metre via `overhead_per_metre_paise` setting
8. **Passed metres**: Only rolls with status `passed`, `in_store`, or `dispatched` count toward production metrics
9. **Order progress**: `(sum_passed_roll_lengths_cm / 100) ÷ order_qty_metres × 100`

---

## 5. API Endpoints

All API routes are in `backend/mill/api/`.

### 5.1 Route Module Summary

| Router File | Lines | Prefix | Endpoints |
|---|---|---|---|
| `auth.py` | 60 | `/api/auth` | `POST /login`, `POST /logout`, `GET /me` |
| `dashboard.py` | 20 | `/api/dashboard` | `GET /` (aggregated KPIs) |
| `items.py` | 97 | `/api/items` | `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}` |
| `partners.py` | 74 | `/api/partners` | `GET /suppliers`, `POST /suppliers`, `GET /buyers`, `POST /buyers` |
| `purchasing.py` | 103 | `/api/purchasing` | `GET /`, `GET /{id}`, `POST /`, `POST /{id}/confirm`, `POST /{id}/cancel`, `POST /{id}/receive` |
| `orders.py` | 83 | `/api/orders` | `GET /`, `GET /{id}`, `POST /`, `POST /{id}/confirm`, `POST /{id}/cancel` |
| `machines.py` | 67 | `/api/machines` | `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}` |
| `production.py` | 116 | `/api/production` | `GET /`, `POST /`, `POST /{id}/advance`, `POST /{id}/finalize`, `POST /downtime` |
| `rolls.py` | 101 | `/api/rolls` | `GET /`, `GET /{id}`, `POST /`, `POST /{id}/inspect`, `POST /{id}/store` |
| `qc.py` | 17 | `/api/qc` | `GET /pending`, `POST /defects`, `GET /defects/{rollId}` |
| `dispatch.py` | 36 | `/api/dispatch` | `POST /`, `GET /` |
| `finance.py` | 106 | `/api/finance` | `GET /invoices`, `POST /invoices`, `GET /invoices/{id}`, `POST /invoices/{id}/pay`, `GET /payments` |
| `inventory.py` | 55 | `/api/inventory` | `GET /stock-levels`, `GET /movements`, `POST /count-session` |
| `reports.py` | 52 | `/api/reports` | `GET /production`, `GET /financial`, `GET /operational` |
| `notifications.py` | 43 | `/api/notifications` | `GET /`, `POST /{id}/read` |
| `settings.py` | 36 | `/api/settings` | `GET /`, `PATCH /` |
| `deps.py` | 105 | — | `get_db`, `current_user`, `require(perm)`, `can[perm]`, `ListParams`, `paginate()` |

### 5.2 Shared API Infrastructure (`deps.py`)

- **`get_db`**: Yields a SQLAlchemy session from `app.state.session_factory`
- **`current_user`**: Reads `mill_session` cookie → validates token → returns `User`
- **`can['permission']`**: Declarative permission dependency (e.g., `user: can['items.read']`)
- **`ListParams`**: Standard pagination (`page`, `page_size`, `q` search, `sort`)
- **`paginate()`**: Generic pagination helper returning `{items, total, page, page_size}`
- **`like()`**: SQL LIKE helper with safe escaping

### 5.3 Meta Endpoints

| Endpoint | Auth | Response |
|---|---|---|
| `GET /` | Public | `{"status":"ok", "app":"Khadira ERP", "version":"1.0.0", "docs":"/docs"}` |
| `GET /api/health` | Public | `{"status":"ok", "app":"Khadira"}` |

---

## 6. Authentication & Authorization (RBAC)

### 6.1 Authentication Flow

```
1. POST /api/auth/login  { username, password }
   ├── Verify password against bcrypt hash in DB
   ├── Create HMAC-SHA256 JWT token (custom _SimpleJWT, no PyJWT dependency)
   ├── Set HTTP cookie: "mill_session" (Secure=COOKIE_SECURE, HttpOnly)
   └── Return { id, username, full_name, role }

2. All subsequent requests
   ├── Browser sends "mill_session" cookie automatically
   ├── deps.current_user() extracts and validates JWT
   └── deps.require(permission) checks RBAC matrix

3. POST /api/auth/logout
   └── Clears the "mill_session" cookie
```

### 6.2 JWT Implementation

- **Custom HMAC-SHA256 JWT** — no external `PyJWT` dependency
- Base64url encoding with proper padding
- Expiry claim (`exp`) checked on every decode
- Default expiry: **12 hours** (`ACCESS_TOKEN_EXPIRE_MINUTES = 720`)
- Secret key: `SECRET_KEY` env var (default: dev value)

### 6.3 RBAC Permission Matrix

#### Primary: `permissions.py` (used by `api/deps.py`)

| Role | Permissions |
|---|---|
| **admin** | `*` (all permissions from all roles + admin-only: `users.read/write`, `settings.read/write`, `inventory.approve`) |
| **owner** | `*` (same as admin) |
| **store** | `items.read/write`, `purchasing.read/write`, `inventory.read/write`, `rolls.read`, `dispatch.read`, `reports.read` |
| **floor_supervisor** | `items.read/write`, `machines.read/write`, `production.read/write`, `rolls.read/write`, `orders.read/write`, `purchasing.read/write`, `partners.read/write`, `inventory.read/write`, `qc.read/write`, `finance.read/write`, `dispatch.read/write`, `reports.read`, `settings.read` |
| **qc** | `items.read`, `rolls.read`, `qc.read/write`, `reports.read` |
| **office** | `items.read`, `partners.read/write`, `orders.read/write`, `dispatch.read/write`, `finance.read/write`, `reports.read` |

#### Secondary: `auth.py` ROLE_PERMISSIONS (used by `auth.can()`)

Extends with additional granular permissions including:
- `attendance.read/write/approve`
- `wages.read/write/finalise`
- `costing.read/write`

### 6.4 Permission Domains

| Domain | Read | Write | Special |
|---|---|---|---|
| `items` | View catalogue | Create/edit items | — |
| `partners` | View suppliers/buyers | Create/edit partners | — |
| `purchasing` | View POs | Create POs, receive | — |
| `orders` | View orders | Create/confirm/cancel | — |
| `machines` | View fleet | Create/edit machines | — |
| `production` | View runs | Start/advance/finalize | — |
| `rolls` | View rolls | Create/inspect/store | — |
| `qc` | View QC data | Inspect/report defects | — |
| `dispatch` | View dispatches | Dispatch rolls | — |
| `finance` | View invoices | Create/pay invoices | — |
| `inventory` | View stock | Post moves | `approve` (admin) |
| `reports` | View reports | — | — |
| `settings` | View settings | Update settings | — |
| `users` | View users | Manage users | admin-only |
| `attendance` | View attendance | Clock in/out | `approve` |
| `wages` | View wages | Create runs | `finalise` |
| `costing` | View costs | Update costs | — |

---

## 7. Frontend Application

### 7.1 Structure

| File | Lines | Size | Purpose |
|---|---|---|---|
| `src/App.jsx` | 3,934 | 184 KB | Monolithic app: landing page + ERP dashboard |
| `src/App.css` | ~2,600 | 69 KB | Landing page styles |
| `src/everest-erp.css` | 1,765 | 35 KB | ERP dashboard design system |
| `src/index.css` | ~160 | 4 KB | Global base styles |
| `src/main.jsx` | 10 | 239 B | React entry point |
| `src/services/api.js` | 343 | 9 KB | API client layer (`MillAPI`) |

### 7.2 Landing Page Features

The landing page is a premium artisan showcase with:

- **Hero section** — 9-image elliptical orbit animation with parallax scrolling
- **Craft asset gallery** — 9 authentic textile/artisan images (spinning wheel, embroidery, block printing, natural dyes, etc.)
- **Product shelf** — Horizontal scrolling product showcase
- **Team cards** — Role-specific team member cards (Store Manager, Production Supervisor, QC Inspector, Accounts Owner)
- **FAQ accordion** — Expandable Q&A section
- **Footer** — Company branding with "From Thread to Tomorrow" tagline
- **Login modal** — Terminal-style login with role selection + 1-click demo buttons

### 7.3 ERP Dashboard Sidebar Navigation

The sidebar features a Persian carpet texture background with dark overlay, gold active indicators, and 11 navigation items:

| # | Sidebar Item | Tab Key | Icon | Description |
|---|---|---|---|---|
| 1 | Dashboard | `dashboard` | LayoutDashboard | Role-specific KPI overview |
| 2 | Yarn & Materials | `inventory` | Package | Item catalogue (yarn + fabric) |
| 3 | Production ▸ | — | Factory | Expandable submenu |
| 3a | → Weaving Looms | `machines` | — | Machine fleet |
| 3b | → Rolls & Batches | `rolls-qc` | — | Fabric roll tracking |
| 4 | Machines | `machines` | Activity | Machine registry |
| 5 | Quality Control | `rolls-qc` | ShieldCheck | QC inspection interface |
| 6 | Inventory | `stock-levels` | Boxes | Stock levels by location |
| 7 | Orders | `sales-orders` | FileText | Buyer order management |
| 8 | Dispatch | `transfers` | Truck | Roll dispatch operations |
| 9 | Workforce | `customers` | Users | Worker management |
| 10 | Finance | `purchases` | Coins | Invoices & payments |
| 11 | Reports | `reports` | BarChart3 | Operational reports |

### 7.4 Role-Specific Dashboard Views

Each login role gets a customized dashboard with unique KPIs, tables, feeds, and actions:

#### Store Manager
- **KPIs**: Active Inventory SKUs, Low Stock Alerts, Orders in Production, Backend Database status
- **Table**: Warehouse Inventory (`/api/items`) — SKU, Item Name, Type, Count/Denier, Reorder Min, Unit, Status
- **Actions**: Log Inward Yarn Bales, Dispatch to Warping Bay, Export Inventory Sheet

#### Production Supervisor
- **KPIs**: Production Fleet, Active Production Runs, Tracked Fabric Rolls, Telemetry Stream
- **Table**: Live Machine Fleet (`/api/machines`) — Machine Code, Name, Process Type, Assigned Run, Stage, Bay, Status
- **Actions**: Assign Order to Machine, Advance Production Stage, Export Floor Output CSV

#### Quality Inspector
- **KPIs**: Total Fabric Rolls, Awaiting QC Review, Passed Fabric Rolls, Total Meters Inspected
- **Table**: Digital Fabric Roll Inspection (`/api/rolls`) — Roll #, Run, Length, Grade, Date, Bay, Status
- **Actions**: Log ASTM 4-Point Map, Certify Export Batch, Print QR Passport

#### Accounts & Owner
- **KPIs**: Active Buyer Orders, Order Portfolio Value (₹), Confirmed Orders, Drafts Awaiting Approval
- **Table**: Buyer Orders & Ledger (`/api/orders`) — Ref, Buyer, Date, Qty, Value, Delivery, Status
- **Actions**: Create Sales Order, Generate GST Invoice, Export Profitability Summary

#### Plant Director (Admin)
- **KPIs**: Overall Fleet Status, Total Fabric Output, Buyer Order Demand, FastAPI Backend Core
- **Table**: Executive Mill Divisions & Telemetry — all machines with runs
- **Actions**: Master Priority Override, Factory-Wide Telemetry Sync, Export Executive Audit

### 7.5 API Client (`MillAPI`)

The frontend API client in `src/services/api.js` provides:

| Category | Methods |
|---|---|
| **Generic & Pagination** | `getList`, `requestAllPages`, `getById`, `create`, `update`, `remove` |
| **High-Volume Traversal** | `getAllOrders()`, `getAllRolls()`, `getAllItems()` |
| **Health** | `checkHealth()` |
| **Auth** | `login()`, `logout()`, `getMe()` |
| **Dashboard** | `getDashboard()` |
| **Items** | `getItems()`, `createItem()`, `updateItem()` |
| **Machines** | `getMachines()`, `createMachine()` |
| **Orders** | `getOrders()`, `createOrder()`, `confirmOrder()`, `cancelOrder()` |
| **Production** | `getProductionRuns()`, `startProductionRun()`, `advanceProduction()`, `finalizeRun()` |
| **Rolls** | `getRolls()`, `inspectRoll()`, `moveRollToStore()` |
| **QC** | `getPendingQC()`, `reportDefect()`, `getDefects()` |
| **Finance** | `getInvoices()`, `payInvoice()` |
| **Purchasing** | `getPurchasing()`, `createPO()`, `confirmPO()`, `cancelPO()`, `receivePOYarn()` |
| **Partners** | `getSuppliers()`, `createSupplier()`, `getBuyers()`, `createBuyer()` |
| **HR & Payroll** | `getWorkers()`, `getAttendance()`, `getWageRuns()` |
| **Costing** | `getCostingSummary()` |
| **Notifications** | `getNotifications()`, `markNotificationRead()` |
| **Downtime** | `reportDowntime()` |
| **Settings** | `getSettings()` |

### 7.6 Design System

The ERP dashboard uses a custom editorial design system (`everest-erp.css`):

- **Color palette**: Warm cream (`#F7F3EC`) background, dark text (`#1E293B`), gold accents
- **Sidebar**: Persian carpet texture background with dark gradient overlay, gold active pills
- **Typography**: Inter font family (Google Fonts)
- **Cards**: KPI cards with status indicators (good=green, warn=amber, neutral=blue)
- **Tables**: Full-width data grids with hover effects
- **Dashboard background**: Floral kalamkari pattern at 45% opacity (configurable)
- **Responsive**: Mobile navigation with hamburger menu

---

## 8. Data Seeding & Demo Environment

Khadira provides two database seeding environments: the **Full Demonstration Dataset (`mill_demo.db`)** for comprehensive evaluator verification and load demonstrations, and the **Minimal Baseline Dataset (`mill.db`)** for testing and lightweight development.

### 8.1 Full Demonstration Dataset (`mill_demo.db` — `backend/mill/seed_demo.py`)

A rich, realistic mill operating environment committed in the repository and directly switchable via `DATABASE_URL=sqlite:///./mill_demo.db`:

| Entity | Count | Lifecycle & Operational Details |
|---|---|---|
| **Buyer Orders** | **24** | `ORD-2026-00001` through `ORD-2026-00024` spanning all lifecycle statuses: `draft` (3), `confirmed` (4), `in_production` (5), `qc` (4), `ready` (4), `dispatched` (3), `cancelled` (1) |
| **Fabric Rolls** | **311** | `ROLL-000001` through `ROLL-000311` across ASTM 4-point grades: Grade A (215), Grade B (55), Grade C (16), Pending QC (25). Statuses: passed (190), in_store (45), dispatched (35), awaiting_qc (25), rework (11), rejected (5) |
| **Mill Workers** | **8** | `WRK-001` through `WRK-008` (weavers, loom operators, QC inspectors, dyeing masters, spinning operators, warping technicians) |
| **Shift Attendance** | **112** | Daily shift entries (morning, afternoon, night) with logged minutes worked and pieces produced |
| **Wage-Run Payroll** | **2** | September 2026 (`finalised`) and October 2026 (`draft`) cycles with line items for base wages, overtime, adjustments, and net payout |
| **Costing Breakdown** | Seeded | Order-level (`order_costs`) and roll-level (`roll_costs`) breakdown of direct yarn consumption, allocated labor wages, and mill overhead |
| **Catalog Items** | **11** | 6 yarn SKUs (20s, 30s, 40s, PC 65/35, Slub 24s, Organic 30s) + 5 fabric SKUs (Poplin, Twill, Slub, Organic Voile, Satin) |
| **Production Fleet** | **7** | Ring spinning frames (SP-01, SP-02), Air-jet looms (WL-01), Rapier looms (WL-02, WL-03), Jet dyeing (DJ-01), Stenter finishing (FN-01) |
| **Commercial Invoices** | **3** | GST sales invoices with NEFT settlement and ledger payments |

### 8.2 Minimal Baseline Dataset (`mill.db` — `backend/mill/seed.py`)

A minimal starter database for rapid unit test verification and initial onboarding:

| Entity | Count | Details |
|---|---|---|
| **Settings** | 3 | `company_name=Khadira`, `currency=INR`, `low_stock_threshold_kg=500` |
| **Locations** | 2 | RAW (Raw Material Store), FIN (Finished Goods Store) |
| **Users** | 6 | admin, owner, store, floor_supervisor, qc, office — all password: `khadira2026!` |
| **Suppliers** | 2 | Himalayan Yarn Co., Deccan Fibres Ltd. (with GSTIN) |
| **Buyers** | 3 | Sunrise Garments, Metro Fashion House, Textile Exports Corp. |
| **Yarn Items** | 4 | YRN-20-W (20s), YRN-30-W (30s), YRN-40-C (40s), YRN-PC-65 (65/35 blend) |
| **Fabric Items** | 3 | FAB-POP-WH (Poplin), FAB-TWL-BL (Twill), FAB-SLB-MIX (Slub) |
| **Machines** | 3 | SP-01 (Spinning), WL-01 (Weaving Loom), DJ-01 (Dyeing Jet) |
| **Stock** | 4 | 2,000 kg per yarn item in RAW location |
| **Orders** | 3 | ORD-2026-00001 (confirmed), ORD-2026-00002 (in_production), ORD-2026-00003 (draft) |
| **Production Run** | 1 | On WL-01, stage=inspection, linked to ORD-2026-00002 |
| **Rolls** | 3 | ROLL-000001 (in_store), ROLL-000002 (passed), ROLL-000003 (awaiting_qc) |

---

## 9. Testing

### 9.1 Test Infrastructure

| File | Lines | Coverage |
|---|---|---|
| `tests/conftest.py` | ~100 | Shared fixtures: in-memory SQLite, test app factory, auth helpers, `client` fixture |
| `tests/test_e2e_flow.py` | ~190 | Full end-to-end: login → PO → receive → order → confirm → production → roll → QC → dispatch |
| `tests/test_step2.py` | ~390 | Service-layer integration: items CRUD, partners, purchasing, orders, machines, production, rolls, QC, dispatch, finance, inventory, reports, notifications, settings |
| `tests/test_erp.py` | ~560 | Extended ERP module tests (excluded by default via `pytest.ini`) |

### 9.2 Test Configuration

```ini
# backend/pytest.ini
[pytest]
testpaths = tests
addopts = --ignore=tests/test_erp.py
```

### 9.3 Running Tests

```bash
cd backend

# Standard test suite (excludes test_erp.py)
python -m pytest tests/

# All tests including extended ERP
python -m pytest tests/ --override-ini="addopts="

# Verbose single file
python -m pytest tests/test_e2e_flow.py -v
```

---

## 10. Database Migrations

### Alembic Configuration

- Config file: `backend/alembic.ini`
- Migration environment: `backend/migrations/env.py`

### Migration History

| Version | File | Description |
|---|---|---|
| `0001` | `0001_initial_schema.py` | Initial schema: users, sessions, items, locations, stock, suppliers, buyers, POs, yarn receipts/lots, orders, invoices, payments, audit log |
| `0002` | `0002_production_and_qc.py` | Production models: machines, production runs, rolls, roll events, run materials, run reconciliation, machine downtime, roll defects, stock count sessions, notifications, settings |

---

## 11. Configuration & Environment

### Backend Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./mill.db` | Database connection string |
| `SECRET_KEY` | `change-me-in-production` | JWT/session signing key |
| `SESSION_HOURS` | `8` | Session cookie expiry |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated allowed origins |
| `COOKIE_SECURE` | `false` | Set `true` for HTTPS (production) |
| `SERVERLESS` | `false` | Serverless DB connection mode |

### Vite Configuration

```javascript
// vite.config.js
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### Configurable Mill Settings (via `/api/settings`)

| Key | Default Value | Purpose |
|---|---|---|
| `company_name` | `Khadira` | Display name |
| `currency` | `INR` | Currency code |
| `low_stock_threshold_kg` | `500` | Low-stock alert threshold |
| `overhead_per_metre_paise` | (configurable) | Per-metre overhead allocation |

---

## 12. File Inventory

### Backend (`backend/mill/`)

```
backend/
├── app.py                          # ASGI entry point
├── mill/
│   ├── __init__.py                 # Package marker
│   ├── main.py                     # Application factory (61 lines)
│   ├── config.py                   # Pydantic settings (36 lines)
│   ├── db.py                       # Session factory (38 lines)
│   ├── database.py                 # Legacy DB helpers
│   ├── auth.py                     # JWT + bcrypt + RBAC (184 lines)
│   ├── permissions.py              # RBAC permission matrix (84 lines)
│   ├── seed.py                     # Demo data seeder (228 lines)
│   ├── models.py                   # Legacy monolithic models (backward compat)
│   │
│   ├── models/                     # Modular SQLAlchemy 2.0 models
│   │   ├── __init__.py             # Re-exports all models (41 lines)
│   │   ├── base.py                 # DeclarativeBase
│   │   ├── core.py                 # User, Session, Item, Location, Stock, Audit (166 lines)
│   │   ├── partners.py             # Supplier, Buyer (44 lines)
│   │   ├── purchasing.py           # PO, POLine, YarnReceipt, YarnLot (79 lines)
│   │   ├── orders.py               # Order, OrderLine (44 lines)
│   │   ├── production.py           # Machine, Run, Roll, Events, Materials (165 lines)
│   │   ├── finance.py              # Invoice, InvoiceLine, Payment (62 lines)
│   │   └── settings.py             # Setting key-value model
│   │
│   ├── services/                   # Business logic (16 modules, ~1,412 lines)
│   │   ├── auth.py, inventory.py, production.py, purchasing.py
│   │   ├── orders.py, rolls.py, qc.py, dispatch.py
│   │   ├── costing.py, machines.py, stock.py
│   │   ├── attendance.py, wages.py, notifications.py, common.py
│   │
│   ├── api/                        # FastAPI route handlers (18 files, ~1,170 lines)
│   │   ├── deps.py                 # Shared dependencies (105 lines)
│   │   ├── auth.py, dashboard.py, items.py, partners.py
│   │   ├── purchasing.py, orders.py, machines.py, production.py
│   │   ├── rolls.py, qc.py, dispatch.py, finance.py
│   │   ├── inventory.py, reports.py, notifications.py, settings.py
│   │
│   └── routers/                    # Legacy route handlers (backward compat)
│
├── migrations/versions/            # 2 Alembic migrations
├── tests/                          # 4 test files + conftest
├── requirements.txt                # 8 Python dependencies
└── .env.example                    # Environment template
```

### Frontend (`src/`)

```
src/
├── main.jsx                        # React entry point (10 lines)
├── App.jsx                         # Monolithic app (3,934 lines)
├── App.css                         # Landing page styles (69 KB)
├── everest-erp.css                 # ERP dashboard design system (35 KB)
├── index.css                       # Global base styles (4 KB)
└── services/api.js                 # MillAPI client (343 lines)
```

---

## 13. Implementation Status Matrix

### ✅ Fully Implemented

| Feature | Backend | Frontend | Tests |
|---|---|---|---|
| User authentication (JWT cookies) | ✅ | ✅ | ✅ |
| Role-based access control | ✅ | ✅ | ✅ |
| Item catalogue (yarn + fabric) | ✅ | ✅ | ✅ |
| Supplier management | ✅ | ✅ | ✅ |
| Buyer management | ✅ | ✅ | ✅ |
| Purchase orders | ✅ | ✅ | ✅ |
| Yarn receipts + lot tracking | ✅ | ✅ | ✅ |
| Stock management (movements, levels) | ✅ | ✅ | ✅ |
| Buyer sales orders | ✅ | ✅ | ✅ |
| Order confirmation (stock validation) | ✅ | ✅ | ✅ |
| Machine fleet management | ✅ | ✅ | ✅ |
| Production runs (stage advancement) | ✅ | ✅ | ✅ |
| Roll creation + tracking | ✅ | ✅ | ✅ |
| QC inspection (pass/fail/hold) | ✅ | ✅ | ✅ |
| Roll defect reporting | ✅ | ✅ | ✅ |
| Dispatch (atomic stock deduction) | ✅ | ✅ | ✅ |
| Invoices (sale + purchase) | ✅ | ✅ | ✅ |
| Payments (partial, multi-method) | ✅ | ✅ | ✅ |
| Dashboard KPIs (5 role views) | ✅ | ✅ | — |
| Notifications | ✅ | ✅ | ✅ |
| Reports | ✅ | ✅ | ✅ |
| Settings | ✅ | ✅ | ✅ |
| Stock count sessions | ✅ | — | — |
| Machine downtime tracking | ✅ | ✅ | — |
| Run material tracking | ✅ | — | — |
| Run reconciliation | ✅ | ✅ | — |
| Audit logging | ✅ | — | — |
| Moving-average costing | ✅ | — | — |
| Overhead cost allocation | ✅ | — | — |

### ⚠️ Backend Implemented, UI Pending

| Feature | Backend | Frontend | Notes |
|---|---|---|---|
| Stock count approval workflow | ✅ | ❌ | `StockCountSession` model + service exists |
| Attendance clock-in/out | ✅ | ❌ | `attendance.py` service (85 lines) |
| Wage run calculation | ✅ | ❌ | `wages.py` service (105 lines) |
| Costing drill-down | ✅ | ❌ | `costing.py` service (94 lines) |

### ❌ Not Yet Implemented

| Feature | Notes |
|---|---|
| Yarn lot → roll traceability | Roll model doesn't reference yarn lot |
| Roll QR label generation | Planned feature |
| Statutory payroll (PF, ESI, TDS) | Out of MVP scope |
| Bank reconciliation | Out of MVP scope |
| Tax filing | Out of MVP scope |
| Biometric attendance integration | Out of MVP scope |
| Buyer portal & notifications | Out of MVP scope |
| Multi-plant operations | Documented in FAQ but not implemented |

---

## 14. Known Gaps & Roadmap

### Immediate Priorities

1. **Frontend views for remaining sidebar tabs** — Inventory (stock-levels), Orders (sales-orders), Dispatch (transfers), Workforce (customers), Finance (purchases) tabs currently render the generic role dashboard instead of dedicated views.
2. **Stock count approval UI** — Backend models and service exist; needs frontend form + approval workflow.
3. **Attendance & wage UI** — Backend services fully implement hourly/piece-rate calculation; needs frontend attendance entry and wage run dashboard.

### Medium-Term Roadmap

4. **Costing dashboard** — Roll cost allocation and overhead visualization
5. **Roll QR labels** — Generate printable QR labels for roll tracking
6. **Yarn lot → roll traceability** — Link `Roll` model to `YarnLot` via `RunMaterial`
7. **Print/export** — PDF/CSV export for invoices, reports, and inventory sheets

### Long-Term Goals

8. **Multi-tenant/multi-plant** — Support for multiple mill locations
9. **Statutory compliance** — PF, ESI, TDS integration
10. **External integrations** — GST e-filing, bank APIs, biometric devices
11. **Buyer portal** — Customer-facing order tracking

---

> **See also**: `docs/backend_overview.md` | `docs/business-rules.md` | `README.md`
