# 🏭 Khadira Textile Mills — Integrated Web Platform & ERP

Unified textile artisan showcase landing page integrated directly with the high-performance **FastAPI backend** (`backend/`).

---

## 🏗️ Architecture

- **Frontend Landing Page & Console**: React, Vite, Lucide-React, Custom Design System (`src/`)
- **Backend API**: FastAPI, SQLAlchemy 2.0, Alembic, SQLite database (`backend/mill.db`)
- **API Proxy**: Vite dev server proxies `/api` directly to `http://127.0.0.1:8000`

---

## 🚀 Quick Start

### 1. Start the Backend API (FastAPI)

```bash
npm run backend
```
> The API will be live at `http://127.0.0.1:8000`. Interactive Swagger docs are accessible at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

To re-seed demo data at any time:
```bash
npm run backend:seed
```

### 2. Start the Frontend (Vite)

In another terminal:
```bash
npm run dev
```
> Open [http://localhost:5173](http://localhost:5173) in your browser. The navbar will show `ERP LIVE` with live latency when the backend is active.

---

## 🔐 Demo Credentials

All roles can authenticate using the 1-click demo buttons in the login modal, or with the credentials below:

| Role | Username | Password | Access & Responsibilities |
|---|---|---|---|
| **Store Manager** | `store` | `ETM-2026` / `khadira2026!` | Yarn & fabric stock catalogue, low-stock alerts |
| **Floor Supervisor** | `supervisor` / `floor_supervisor` | `ETM-2026` / `khadira2026!` | Looms & bay telemetry, order assignments |
| **QC Inspector** | `qc` | `ETM-2026` / `khadira2026!` | Digital roll inspection, pass/rework/reject routing |
| **Accounts & Owner** | `owner` / `office` | `ETM-2026` / `khadira2026!` | Buyer orders, pricing, ledger, delivery dates |
| **Plant Director** | `admin` | `ETM-2026` / `khadira2026!` | Master division overrides, full mill telemetry |

---

## ⚡ Live Features Integrated

- **Live Session Authentication**: `POST /api/auth/login` sets HTTP session cookies and syncs user roles and permissions.
- **Dynamic Catalogue & Stock**: Store console pulls real yarn lots & fabric SKUs from SQLite.
- **Machine Fleet Telemetry**: Supervisor console monitors configured spinning, weaving, and dyeing machines.
- **Interactive QC Actions**: Roll inspection triggers `POST /api/rolls/{id}/inspect` and `POST /api/rolls/{id}/store`.
- **Order Pipeline**: Owner console tracks buyer orders and triggers `POST /api/orders/{id}/confirm`.
- **Telemetry Sync**: Clicking "Sync Feeds" in the console dynamically polls the backend with live ping latency.

