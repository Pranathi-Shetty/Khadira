# Backend Overview

Khadira is being developed as a unified textile-mill operations platform. This repository currently contains its API backend, not a browser interface. The API connects core records for purchasing, inventory, customer orders, production, quality inspection, dispatch, and finance. Attendance and payroll rules are documented separately but are not implemented as API workflows.

## Code organization

- `backend/mill/models/` defines database entities and relationships.
- `backend/mill/services/` contains business rules and workflow operations.
- `backend/mill/api/` exposes the workflows through FastAPI routes.
- `backend/migrations/` contains Alembic schema migrations.
- `backend/tests/` contains API and workflow tests.
- `backend/mill/seed.py` creates local demo data in SQLite.

## Main workflows

### Purchasing and inventory

Users create supplier purchase orders and record receipts against purchase-order lines. A receipt records a yarn lot and posts stock movements. Inventory is maintained by item and location; yarn quantities use grams, and stock updates reject changes that would make a quantity negative. The current `Roll` model does not reference a yarn lot, so the API does not provide end-to-end lot-to-roll traceability.

### Buyer orders

Orders contain fabric items. When an order is confirmed, the service estimates required yarn from the fabric's yarn-per-metre value and the order quantity, then compares it with available yarn stock. An order is rejected if the estimate exceeds stock.

### Production and quality

Production runs are assigned to a machine and move through the configured stages for that machine type. Advancing a run can record yarn consumption as stock movements. Rolls can be created at the final stage and start with `awaiting_qc` status. Inspection verdicts are `passed`, `failed`, or `held`; a passed roll can then be moved into finished-goods stock.

### Dispatch and finance

Dispatch accepts rolls that are already in store, deducts their lengths from finished-goods stock, and marks them `dispatched`. The dispatch endpoint does **not** create an invoice automatically. Invoices are created separately through the finance API, where sale or purchase invoices and invoice payments are recorded.

## Access and health

Business routes use the permission checks in `backend/mill/api/deps.py`. Login creates a session cookie; its `Secure` attribute is controlled by configuration, so local development defaults should not be treated as deployment security settings. The root and `/api/health` routes are public; the health route checks whether the configured database accepts a query.

The seeded roles are `admin`, `owner`, `store`, `floor_supervisor`, `qc`, and `office`. Seeded accounts use a shared development password and must only be used locally.

## Current scope and gaps

- The repository is API-only; a browser frontend is not included.
- Attendance and wage/payroll processing are not implemented.
- Roll QR labels are not implemented.
- Yarn lots are recorded at receipt, but rolls are not linked back to those lots.
- Dispatch and invoice creation are separate operations.

See [business rules](business-rules.md) for the broader workflow rules and planned behavior. That document includes rules that are not yet implemented in the API.
