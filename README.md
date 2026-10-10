# Khadira Textile Mills ERP

Khadira is a backend API for managing core textile-mill workflows. It is built with FastAPI and SQLAlchemy and currently includes inventory, purchasing, orders, production, quality control, dispatch, and finance features.

> **Scope:** This repository contains the backend API; it does not include a frontend. Attendance and wage rules are documented, but attendance and payroll API workflows are not implemented yet. Treat this as a development MVP, not a production-ready deployment.

## Features

- User login, sessions, and role-based access
- Yarn and fabric inventory, stock movements, and costing
- Supplier purchase orders and receipts
- Buyer orders and order progress
- Machine records and production runs
- Roll tracking and quality inspection
- Dispatch, invoicing, and payment recording
- Dashboard, configuration, and database-backed health check

The API is documented interactively at `/docs` when the server is running. A concise set of business rules is in [docs/business-rules.md](docs/business-rules.md); some documented rules describe planned behavior and are not implemented in the API yet.

## Run locally on Windows PowerShell

From the repository root:

```powershell
Set-Location backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env
python -m mill.seed
python -m uvicorn app:app --reload --port 8000
```

If `backend\.env` already exists, do not overwrite it with the copy command. The seed command creates the local SQLite database and sample data. It includes shared demo credentials, so use them only for local development and never expose this setup to the public internet.

For macOS or Linux, create and activate the environment with:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
python -m mill.seed
python -m uvicorn app:app --reload --port 8000
```

The API runs at `http://127.0.0.1:8000`.

## API and health checks

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

The health endpoint checks database connectivity and returns `503` if the database query fails.

## Demo accounts

The local seed creates the following accounts. They all use the same development-only password: `khadira2026!`.

| Role | Username |
|---|---|
| Administrator | `admin` |
| Owner | `owner` |
| Store keeper | `store` |
| Floor supervisor | `floor_supervisor` |
| QC inspector | `qc` |
| Office staff | `office` |

Change the shared password and set a strong, unique `SECRET_KEY` before any deployment. Configure database, cookie, and allowed-origin settings for the target environment; the checked-in `.env.example` is for local development only.

## Run tests

From the repository root:

```powershell
Set-Location backend
python -m pytest tests -v
```

The test suite exercises authentication and the main purchasing, inventory, order, production, QC, dispatch, and finance flows.

## Technical notes

- Financial amounts are stored as integer paise to avoid floating-point rounding.
- Yarn stock is tracked in grams; fabric length is tracked in centimetres.
- Stock updates and dispatch operations enforce transactional constraints, including protection against negative stock and duplicate roll dispatch.
- Local development uses SQLite. Review database, security, and deployment settings before using another database or deploying the service.
