# Khadira Textile ERP — System Audit & Remediation Plan

This document benchmarks the current Khadira Textile ERP codebase against the core operating brief, the six operational criteria, and data integrity rules.

---

## 1. Audit Against the Six Criteria

| # | Criterion | Status | One-Line Reason |
|---|-----------|:------:|-----------------|
| **1** | **Receive & know raw material** | **Partly works** | Inward yarn ledger exists in backend, but yarn cannot be received through the frontend, and stock-on-hand is not displayed in the inventory table. |
| **2** | **See the production floor** | **Partly works** | Order-to-machine assignment and run stages work, but machine daily meter output and machine downtime reporting lack frontend controls. |
| **3** | **Check quality & trace problems** | **Partly works** | Roll state machine and defect tracking exist in backend, but rolls cannot be inspected (pass/hold/reject) from the frontend, and lineage is not surfaced. |
| **4** | **Answer buyers instantly** | **Partly works** | Coarse order status (`draft`, `in_production`, `completed`) is visible, but delivery target dates and meter progress (% woven / rolls passed) are omitted. |
| **5** | **Dispatch correctly** | **Missing** | Backend only marks rolls dispatched via direct ID list without creating an invoice, and no dispatch screen exists in the frontend. |
| **6** | **Close the books** | **Missing** | Order costing omits yarn material valuation, and no unified financial report brings raw material bills, wages, and buyer payments together to show mill profit. |
| *—* | *Workforce: Attendance & Wages* | **Partly works** | Complete backend APIs exist for workers, attendance, and wage runs, but neither attendance nor wages are exposed in the frontend. |
| *—* | *Role-based permissions* | **Works** | Backend strictly checks permission matrix via `can(...)` dependencies, and frontend toggles persona workspaces. |

---

## 2. Audit Against the Core Rules

| Rule | Status | One-Line Reason |
|------|:------:|-----------------|
| **Stock can never go negative** | **Partly works** | Enforced in Python logic ([inventory.py:L54](file:///Users/aditi/Desktop/Khadira/backend/mill/services/inventory.py#L54)), but missing a `CheckConstraint("qty_g >= 0")` in the database storage layer. |
| **A roll can never be dispatched twice** | **Partly works** | Enforced in Python logic ([dispatch.py:L31](file:///Users/aditi/Desktop/Khadira/backend/mill/services/dispatch.py#L31)), but missing a database-level unique constraint on dispatched rolls in the active schema. |
| **Multi-step actions either fully succeed or leave no trace** | **Works** | Operations execute in atomic SQLAlchemy sessions that roll back on any domain error prior to commit. |
| **Rejected fabric can never be sold** | **Works** | Only `passed` rolls enter `in_store` ([qc.py:L38](file:///Users/aditi/Desktop/Khadira/backend/mill/services/qc.py#L38)), and only `in_store` rolls can be dispatched. |
| **An invoice always matches exactly what was dispatched** | **Missing** | Invoices have no foreign key to orders or dispatches; invoices are created manually and unlinked from what left the mill. |
| **Each person can only do what their role allows** | **Works** | Enforced by FastAPI route dependencies across all write endpoints via [permissions.py](file:///Users/aditi/Desktop/Khadira/backend/mill/permissions.py). |
| **History is never deleted or rewritten** | **Works** | Append-only ledger pattern used for `stock_move`, `roll_event`, and `audit_log`. |
| **Numbers shown always agree with underlying records** | **Partly works** | Live tables query SQLite records, but the Everest hero overview cards contain hardcoded fallback display strings (`12.8 Tons`, `8,240 Meters`, `92.4%`). |

---

## 3. Verification of the 11 Suspicions (Section 6)

### 1. Dispatch records & storage-layer double-dispatch prevention
* **Result**: **Partly True / Mostly False**.
* **Evidence**: The active domain package (`mill/models/`) has no `Dispatch` or `DispatchRoll` table. [dispatch.py:L13-L14](file:///Users/aditi/Desktop/Khadira/backend/mill/services/dispatch.py#L13-L14) notes: *"For now we handle dispatch as a service-level operation on rolls directly."* Double-dispatch is prevented only in application code (`roll.status != "in_store"`), with no unique constraint in the storage layer.

### 2. Storage layer prevents stock going below zero
* **Result**: **True** (suspicion confirmed).
* **Evidence**: [core.py:L87-L94](file:///Users/aditi/Desktop/Khadira/backend/mill/models/core.py#L87-L94) defines `StockLevel.qty_g` without a `CheckConstraint("qty_g >= 0")`. Only [inventory.py:L54](file:///Users/aditi/Desktop/Khadira/backend/mill/services/inventory.py#L54) blocks negative stock in Python.

### 3. Stock movement records kind of movement and user
* **Result**: **False** (suspicion confirmed).
* **Evidence**: [core.py:L100-L109](file:///Users/aditi/Desktop/Khadira/backend/mill/models/core.py#L100-L109) shows `StockMove` only has `item_id`, `location_id`, `delta_g`, `ref`, `note`, `created_at`. It has **no** `user_id` / `created_by` column, and **no** structured movement type enum.

### 4. Roll traced all the way back to yarn lot and supplier
* **Result**: **Partly True**.
* **Evidence**: The relational foreign keys exist (`Roll -> ProductionRun -> RunMaterial -> YarnLot -> YarnReceipt -> PO -> Supplier`), but [production.py:L71-L74](file:///Users/aditi/Desktop/Khadira/backend/mill/services/production.py#L71-L74) deducts yarn from `RAW` stock anonymously without writing to `RunMaterial`. In `mill_demo.db`, `SELECT COUNT(*) FROM run_material` is `0` and `yarn_lot` is `0`.

### 5. Definition of "complete" with tolerance & roll-based progress
* **Result**: **False** (suspicion confirmed).
* **Evidence**: [orders.py:L17-L44](file:///Users/aditi/Desktop/Khadira/backend/mill/models/orders.py#L17-L44) has no `tolerance_pct` column. [production.py:L83](file:///Users/aditi/Desktop/Khadira/backend/mill/services/production.py#L83) sets `order.status = "completed"` unconditionally when any linked run reaches its final stage, regardless of whether 100 meters or 1,200 meters were woven.

### 6. Invoices linked to order/dispatch & matching quantity
* **Result**: **False** (suspicion confirmed).
* **Evidence**: [finance.py:L16-L34](file:///Users/aditi/Desktop/Khadira/backend/mill/models/finance.py#L16-L34) shows `Invoice` has only `buyer_id` and `supplier_id`. It has **no** `order_id` or `dispatch_id`, and invoice lines are typed manually with no verification against dispatched roll meters.

### 7. Direct answer to "where is my order?" with current stage
* **Result**: **Partly True**.
* **Evidence**: Orders only expose coarse status strings (`draft`, `in_production`, `completed`). There is no endpoint or query summarizing physical floor stage (meters woven, rolls inspected, rolls ready in store, rolls dispatched).

### 8. Demonstration data created through real system paths
* **Result**: **True** (suspicion confirmed).
* **Evidence**: [seed_demo.py:L313-L350](file:///Users/aditi/Desktop/Khadira/backend/mill/seed_demo.py#L313-L350) writes directly using `db.add(Roll(...))` rather than calling domain services. This bypassed inventory ledger movements and left `yarn_receipt`, `yarn_lot`, and `run_material` empty.

### 9. Quantities stored in clearly named units
* **Result**: **Partly True**.
* **Evidence**: Most columns use clear suffixes (`_cm`, `_meters`, `_kg`, `_paise`). However, [core.py:L94](file:///Users/aditi/Desktop/Khadira/backend/mill/models/core.py#L94) explicitly comments that `StockLevel.qty_g` stores **grams** for yarn but **centimeters** for fabric. `StockMove.delta_g` similarly stores fabric centimeters under a `_g` column name.

### 10. Newly merged work follows exact units, role checks, history
* **Result**: **Partly True**.
* **Evidence**: Money is strictly in paise (`*_paise`), and role checks (`can(...)`) are enforced. However, [attendance.py:L29](file:///Users/aditi/Desktop/Khadira/backend/mill/api/attendance.py#L29) names a column `hours_worked` but restricts it to `le=1440` (minutes). In [costing.py:L46](file:///Users/aditi/Desktop/Khadira/backend/mill/api/costing.py#L46), `material_cost_paise = None` leaves yarn unvalued.

### 11. Single Alembic migration chain builds an empty DB
* **Result**: **Partly True / Incomplete**.
* **Evidence**: Revisions `0001 -> 0002 -> 0003` run cleanly, but omit `roll_defect`, `machine_downtime`, `run_material`, and `run_reconciliation`. Building from migrations alone creates an incomplete schema where those features fail. Additionally, `tests/test_erp.py` (which targets legacy table names) was suppressed via `addopts = --ignore=tests/test_erp.py` in `pytest.ini`.

---

## 4. Short Ordered Plan of Fixes

| # | Step | Why It Serves the Brief | Risk |
|---|------|-------------------------|------|
| **1** | **Database Foundations & Storage Integrity**<br>• Add `CheckConstraint("qty_g >= 0")` on `StockLevel`.<br>• Add `user_id` to `StockMove`.<br>• Add `Dispatch` & `DispatchRoll` models with `UniqueConstraint("roll_id")`.<br>• Add migration `0004` covering missing tables (`roll_defect`, `machine_downtime`, `run_material`, `run_reconciliation`, `dispatch`). | Enforces core rules in storage layer (never negative stock, no double-dispatch) and creates complete migration chain for clean database setup. | Low. Storage constraints reject illegal mutations without affecting valid transactions. |
| **2** | **Dispatch & Invoice Linkage**<br>• Add `order_id` and `dispatch_id` to `Invoice`.<br>• Have `dispatch_rolls` record the `Dispatch`, attach rolls, and generate the matching `sale` invoice for the dispatched yardage. | Enforces rule: *"An invoice always matches exactly what was dispatched."* Closes the gap between warehouse and finance. | Low. Keeps dispatch and invoice generation in one atomic database transaction. |
| **3** | **Traceability & Order Completion**<br>• Wire `advance_stage` / `issue_material` so yarn consumption links to `RunMaterial` and `YarnLot`.<br>• Add `tolerance_pct` (default 5%) and compute order completion from actual passed roll meters rather than setting status manually. | Fulfills Area 3 (trace roll to yarn lot & supplier) and Area 4 (direct calculation of order progress). | Medium. Must handle legacy runs where no lot was assigned without crashing. |
| **4** | **Yarn Valuation & Financial Summary**<br>• Value yarn in `OrderCost` using weighted average receipt cost.<br>• Add `/api/reports/financial-summary` returning `revenue - yarn_bills - wages - overhead = profit`. | Fulfills Area 6: *"Bring raw material bills, wages and buyer payments together in one place, so the owner can see whether the mill made money."* | Low. Read-only calculations derived from existing ledgers. |
| **5** | **Test Alignment & Demonstrable End-to-End Test**<br>• Re-enable `tests/test_erp.py` or harmonize it with active schema.<br>• Add an automated end-to-end test proving the complete chain: Yarn PO → Receipt → Order → Production Run → Roll QC → Dispatch → Invoice → Payment → Costing. | Proves that all 6 criteria and core rules work end-to-end with automated evidence. | Low. Pure test verification. |

---

## 5. Known Architectural Issues & Deferred Refactorings

1. **Dual Units in `StockLevel.qty_g` and `StockMove.delta_g`:**
   - **Context:** The database schema column `qty_g` was named after grams for raw materials (`unit='kg'`). For fabric items (`unit='meters'`), however, this column stores integer **centimetres** to preserve whole-number precision without floating-point errors.
   - **Decision:** As instructed in Step 7, renaming the database column now across all tables, triggers, constraints, and historical migrations is high risk. The underlying column remains `qty_g` in SQLite, while API endpoints transparently expose `unit="meters"`, `qty_cm`, and `quantity_m` for fabric, and `unit="kg"`, `qty_g`, and `qty_kg` for yarn.
   - **Recommendation for v2:** Rename to a polymorphic/unit-agnostic column name such as `qty_canonical_int` or separate `stock_level_yarn` and `stock_level_fabric` tables.

