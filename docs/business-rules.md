# Business Rules — Khadira Textile Mills ERP (MVP)

Approved defaults for the first implementation phase.

## Wages

- **Wage basis**: Each worker has one wage basis: `hourly` or `piece_rate`.
- **Hourly**: rate in paise/hour; attendance stores time in minutes.
- **Piece-rate**: rate in paise/piece; attendance stores count in pieces.
- **Overtime**: not calculated unless an explicit overtime-rate setting is added.
- **Attendance correction**: draft entries are editable; approved entries must be voided (with reason) and re-entered.
- **Monthly wage run**: period = calendar month; includes only `approved` attendance entries; one draft/finalised run per period; finalised runs are immutable; corrections use adjustments.

## Stock

- **Units**: yarn stored in **grams**; fabric stored in **centimetres**. API layer converts to kg/m.
- **Non-negative constraint**: a `CHECK` constraint prevents stock from going negative.
- **Moving average cost**: recalculated on every yarn receipt; cost stored in paise/gram.

## Yarn Cost in Production

- When yarn is issued to a production run, the cost-per-gram snapshot from `items.average_cost_paise` at issue time is stored on the run (`yarn_cost_paise_per_gram`).
- The costing service uses this snapshot, not the current average cost — preventing historical cost drift.

## Overhead

- Default method: **per passed metre** — a configurable paise/metre value (`overhead_per_metre_paise` setting).
- Alternative (pool method) is not implemented in MVP.

## Passed Metres

- Only rolls with status `passed`, `in_store`, or `dispatched` count as passed metres.
- Rejected and rework rolls are excluded from the cost denominator.

## Order Progress

- Progress % = (sum of passed roll lengths in cm / 100) ÷ order quantity in metres × 100.
- Complete when progress ≥ 100% − tolerance_pct.

## Dispatch & Invoice

- Dispatch confirmation is a single atomic transaction: checks all rolls are `in_store`, posts fabric-out stock moves, marks rolls `dispatched`, creates invoice.
- Invoice amount = total metres dispatched × price_per_metre.
- A roll can only be dispatched once (`UNIQUE` constraint on `dispatch_rolls.roll_id`).

## Payments

- Buyer payment: linked to an invoice; partial payments allowed; overpayment rejected unless an explicit credit flow is added.
- Supplier payment: linked to a supplier bill; same partial/overpayment rules.
- `outstanding = amount - sum(payments)`.

## Cost Per Roll

- All roll costs are **allocated** (not directly measured), proportional to roll length in metres.
- The UI must label roll costs as "allocated" (not directly measured) unless direct roll-level consumption/labour is recorded.

## Out of Scope (MVP)

- Statutory payroll compliance (PF, ESI, TDS, leave encashment)
- Bank reconciliation
- Tax filing
- Biometric attendance integration
- Buyer portal / notifications
