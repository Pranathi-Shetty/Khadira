# Everest Textile Mills ERP

A unified ERP system for Everest Textile Mills — replacing notebooks, paper slips and phone calls with a single digital platform.

## Architecture

```
frontend/     Next.js 15 + TypeScript + TailwindCSS
backend/      FastAPI + SQLAlchemy + Alembic + SQLite (dev) / PostgreSQL (prod)
```

## Modules

| Module | Description |
|---|---|
| Inventory | Yarn & fabric catalogue with moving-average cost |
| Purchasing | Purchase orders, yarn receipt, supplier bills |
| Orders | Buyer orders with yarn sufficiency check & progress |
| Machines | Machine status tracking & status change log |
| Production | Runs, yarn issue, roll creation |
| QC | Roll inspection: pass / rework / reject |
| Dispatch | Atomic confirmation with stock-out and invoice generation |
| Finance | Buyer invoices & payments, receivables/payables |
| Attendance | Worker register with hourly/piece-rate basis |
| Wages | Monthly wage runs with approve/finalise flow |
| Costing | Order & roll cost: yarn + wages + overhead / passed metres |
| Reports | Owner dashboard, monthly profit report |

## Quick Start (Backend)

```bash
cd backend
pip install -r requirements.txt
python -m mill.seed            # loads demo data
uvicorn app:app --reload --port 8000
```

Open **http://127.0.0.1:8000/docs** for the interactive API documentation.

### Demo credentials

| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| Owner | owner | owner123 |
| Store | store | store123 |
| Floor Supervisor | supervisor | super123 |
| QC Officer | qc_officer | qc1234 |
| Office | office | office123 |

## Quick Start (Frontend)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

## Running Tests

```bash
cd backend
pytest tests/ -v
```

## Key Design Decisions

- **Money in paise**: all amounts stored as integers (no floating-point currency)
- **Stock in sub-units**: yarn in grams, fabric in centimetres → never-negative DB constraint
- **Roll lifecycle**: `produced → awaiting_qc → passed → in_store → dispatched` (+ rework/rejected paths)
- **Wage run immutability**: finalised runs cannot be edited; corrections via adjustment entries
- **Cost traceability**: every order cost traces to yarn-issue cost snapshots at issue time
- **Double-dispatch prevention**: `UNIQUE` constraint on `dispatch_rolls.roll_id`

## Business Rules Summary

See [`docs/business-rules.md`](docs/business-rules.md) for the full set of business rules approved for MVP.
