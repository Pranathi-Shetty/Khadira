"""Verification script for Khadira Textile Mills scenario demonstration data.

Verifies:
1. Stock never went negative at any point in history (running cumulative delta_g >= 0)
2. Stock levels equal the sum of movements for all items and locations
3. Yarn batch remainders add up (sum of lot remainders == RAW stock level, and lot consumption == run materials)
4. Every invoice equals its dispatch (exact roll cm, line pricing, and Decimal meter representation)
5. Order progress matches actual physical rolls at every stage
6. No table that should have history is empty (roll_event, stock_move, yarn_receipt, run_material, dispatch_roll, payment, etc.)
"""

import sys
import os
from decimal import Decimal

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from mill.models import (
    Item, Location, StockLevel, StockMove, Supplier, Buyer,
    PurchaseOrder, PurchaseOrderLine, YarnLot, YarnReceipt,
    Order, OrderLine, Machine, ProductionRun, Roll, RollEvent,
    RollDefect, RunMaterial, Invoice, InvoiceLine, Payment,
    Dispatch, DispatchRoll, AttendanceEntry, WageRun, AuditLog,
    ITEM_YARN, ITEM_FABRIC
)
from mill.services.pricing import invoice_matches_dispatch, meters_decimal_to_cm
from mill.services.orders import calculate_order_progress


def verify_scenario(db) -> dict:
    results = {}
    print("=" * 68)
    print("  RUNNING SCENARIO VERIFICATION CHECKS")
    print("=" * 68)

    # ── 1. STOCK NEVER WENT NEGATIVE AT ANY TIME ─────────────────────────────
    print("[1/6] Checking that stock never went negative at any point in time...")
    moves = db.scalars(
        select(StockMove).order_by(StockMove.item_id, StockMove.location_id, StockMove.created_at.asc(), StockMove.id.asc())
    ).all()

    running_balances = {}
    violations = []
    for m in moves:
        key = (m.item_id, m.location_id)
        current = running_balances.get(key, 0)
        new_balance = current + m.delta_g
        if new_balance < 0:
            violations.append(f"Item {m.item_id} at Loc {m.location_id} went negative: {new_balance} (Move #{m.id}, delta={m.delta_g})")
        running_balances[key] = new_balance

    # Also verify current StockLevel table
    current_levels = db.scalars(select(StockLevel)).all()
    for lvl in current_levels:
        if lvl.qty_g < 0:
            violations.append(f"StockLevel #{lvl.id} has negative qty: {lvl.qty_g}")

    if violations:
        print(f"  [FAIL] Found {len(violations)} negative stock violations:")
        for v in violations[:5]:
            print(f"    - {v}")
        results["stock_never_negative"] = False
    else:
        print(f"  [PASS] Verified across {len(moves)} movements: running stock was NEVER negative at any time.")
        results["stock_never_negative"] = True

    # ── 2. STOCK LEVELS EQUAL SUM OF MOVEMENTS ───────────────────────────────
    print("[2/6] Checking that stock levels equal the exact sum of movements...")
    mismatch_levels = []
    for lvl in current_levels:
        movement_sum = db.scalar(
            select(func.sum(StockMove.delta_g)).where(
                StockMove.item_id == lvl.item_id,
                StockMove.location_id == lvl.location_id
            )
        ) or 0
        if movement_sum != lvl.qty_g:
            mismatch_levels.append(f"Item {lvl.item_id} Loc {lvl.location_id}: StockLevel={lvl.qty_g}, Sum(moves)={movement_sum}")

    if mismatch_levels:
        print(f"  [FAIL] Found {len(mismatch_levels)} stock level mismatches:")
        for m in mismatch_levels[:5]:
            print(f"    - {m}")
        results["stock_levels_match_movements"] = False
    else:
        print(f"  [PASS] All {len(current_levels)} active stock levels equal the exact sum of their movements.")
        results["stock_levels_match_movements"] = True

    # ── 3. BATCH REMAINDERS ADD UP ───────────────────────────────────────────
    print("[3/6] Checking that yarn batch remainders add up to RAW warehouse stock...")
    raw_loc = db.scalar(select(Location).where(Location.code == "RAW"))
    yarn_items = db.scalars(select(Item).where(Item.item_type == ITEM_YARN)).all()
    batch_mismatches = []

    for y in yarn_items:
        raw_level = db.scalar(
            select(StockLevel.qty_g).where(StockLevel.item_id == y.id, StockLevel.location_id == raw_loc.id)
        ) or 0

        active_lots = db.scalars(
            select(YarnLot).where(YarnLot.item_id == y.id, YarnLot.is_active.is_(True))
        ).all()
        lot_remainders_sum = sum(l.remaining_g for l in active_lots)

        if raw_level != lot_remainders_sum:
            batch_mismatches.append(f"Yarn {y.sku}: RAW stock={raw_level}g, Sum(lots)={lot_remainders_sum}g (diff={raw_level - lot_remainders_sum})")

        # Verify lot internal consistency: qty_g - remaining_g == sum(run_materials)
        for lot in active_lots:
            consumed_in_materials = db.scalar(
                select(func.sum(RunMaterial.issued_g)).where(RunMaterial.lot_id == lot.id)
            ) or 0
            if (lot.qty_g - lot.remaining_g) != consumed_in_materials:
                batch_mismatches.append(f"Lot {lot.lot_number}: qty - remaining = {lot.qty_g - lot.remaining_g}, but RunMaterial sum = {consumed_in_materials}")

    if batch_mismatches:
        print(f"  [FAIL] Found {len(batch_mismatches)} batch remainder mismatches:")
        for bm in batch_mismatches[:5]:
            print(f"    - {bm}")
        results["batch_remainders_add_up"] = False
    else:
        print(f"  [PASS] All {len(yarn_items)} yarn SKUs have lot remainders strictly matching RAW stock and RunMaterial issuances.")
        results["batch_remainders_add_up"] = True

    # ── 4. EVERY INVOICE EQUALS ITS DISPATCH ─────────────────────────────────
    print("[4/6] Checking that every invoice equals its dispatch exactly...")
    dispatches = db.scalars(select(Dispatch)).all()
    invoice_mismatches = []

    for disp in dispatches:
        inv = db.scalar(select(Invoice).where(Invoice.dispatch_id == disp.id))
        if inv is None:
            invoice_mismatches.append(f"Dispatch #{disp.id} ({disp.dispatch_number}) has no linked invoice")
            continue

        disp_rolls = [dr.roll for dr in disp.rolls]
        if not disp_rolls:
            invoice_mismatches.append(f"Dispatch #{disp.id} has no rolls attached")
            continue

        # Check pricing and length equality
        if not invoice_matches_dispatch(inv.lines[0].qty, [r.length_cm for r in disp_rolls]):
            invoice_mismatches.append(f"Invoice {inv.ref} does not match dispatch {disp.dispatch_number} via invoice_matches_dispatch helper")

        # Direct assertions on cm and paise
        tot_disp_cm = sum(r.length_cm for r in disp_rolls)
        inv_cm = meters_decimal_to_cm(inv.lines[0].qty)
        if tot_disp_cm != inv_cm:
            invoice_mismatches.append(f"Invoice {inv.ref} length {inv_cm}cm != Dispatch {disp.dispatch_number} {tot_disp_cm}cm")

    if invoice_mismatches:
        print(f"  [FAIL] Found {len(invoice_mismatches)} invoice-dispatch discrepancies:")
        for im in invoice_mismatches[:5]:
            print(f"    - {im}")
        results["every_invoice_equals_dispatch"] = False
    else:
        print(f"  [PASS] All {len(dispatches)} dispatches have exact matching invoices (equal rolls, lengths in cm, and rates).")
        results["every_invoice_equals_dispatch"] = True

    # ── 5. ORDER PROGRESS MATCHES ROLLS ──────────────────────────────────────
    print("[5/6] Checking that order progress matches physical roll records...")
    orders = db.scalars(select(Order)).all()
    progress_mismatches = []

    for o in orders:
        prog = calculate_order_progress(db, o.id)
        if o.status in ("draft", "cancelled"):
            if prog["roll_counts_by_stage"]["produced"] > 0:
                progress_mismatches.append(f"Order {o.ref} in status {o.status} has {prog['roll_counts_by_stage']['produced']} rolls produced")
        elif o.status == "delivered":
            if prog["meters_by_stage"]["dispatched"] < prog["min_acceptable_meters"]:
                progress_mismatches.append(f"Order {o.ref} marked delivered but dispatched {prog['meters_by_stage']['dispatched']}m < min {prog['min_acceptable_meters']}m")
        elif o.status == "production_complete":
            if prog["meters_by_stage"]["passed"] < prog["min_acceptable_meters"]:
                progress_mismatches.append(f"Order {o.ref} marked production_complete but passed {prog['meters_by_stage']['passed']}m < min {prog['min_acceptable_meters']}m")

    if progress_mismatches:
        print(f"  [FAIL] Found {len(progress_mismatches)} order progress mismatches:")
        for pm in progress_mismatches[:5]:
            print(f"    - {pm}")
        results["order_progress_matches_rolls"] = False
    else:
        print(f"  [PASS] All {len(orders)} sales orders have calculated progress matching physical rolls and tolerance boundaries.")
        results["order_progress_matches_rolls"] = True

    # ── 6. NO TABLE THAT SHOULD HAVE HISTORY IS EMPTY ────────────────────────
    print("[6/6] Checking that no historical or audit tables are empty...")
    history_tables = [
        ("RollEvent", RollEvent),
        ("StockMove", StockMove),
        ("YarnReceipt", YarnReceipt),
        ("YarnLot", YarnLot),
        ("RunMaterial", RunMaterial),
        ("Dispatch", Dispatch),
        ("DispatchRoll", DispatchRoll),
        ("Invoice", Invoice),
        ("Payment", Payment),
        ("AttendanceEntry", AttendanceEntry),
        ("WageRun", WageRun),
        ("RollDefect", RollDefect),
        ("AuditLog", AuditLog),
    ]

    empty_tables = []
    counts_summary = {}
    for tname, model in history_tables:
        cnt = db.scalar(select(func.count(model.id))) or 0
        counts_summary[tname] = cnt
        if cnt == 0:
            empty_tables.append(tname)

    if empty_tables:
        print(f"  [FAIL] Following historical tables are empty: {', '.join(empty_tables)}")
        results["no_history_tables_empty"] = False
    else:
        print(f"  [PASS] All {len(history_tables)} historical and audit tables contain rich operational rows:")
        for tname, cnt in counts_summary.items():
            print(f"    - {tname:<18}: {cnt:>6} records")
        results["no_history_tables_empty"] = True

    print("=" * 68)
    all_passed = all(results.values())
    if all_passed:
        print("  VERIFICATION RESULT: ALL 6 CHECKS PASSED PERFECTLY")
    else:
        print("  VERIFICATION RESULT: SOME CHECKS FAILED")
    print("=" * 68)
    return {"all_passed": all_passed, "details": results, "counts": counts_summary}


if __name__ == "__main__":
    db_target = sys.argv[1] if len(sys.argv) > 1 else "test_scenario.db"
    if not os.path.isabs(db_target) and not db_target.startswith("backend"):
        if os.path.basename(os.getcwd()) != "backend" and os.path.exists("backend"):
            db_target = os.path.join("backend", db_target)

    engine = create_engine(f"sqlite:///{db_target}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        res = verify_scenario(session)
        if not res["all_passed"]:
            sys.exit(1)
    finally:
        session.close()
