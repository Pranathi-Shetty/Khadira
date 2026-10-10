"""Run schema migrations to bring existing databases up to date with the current models."""
import sqlite3
import os

def migrate_db(dbfile):
    if not os.path.exists(dbfile):
        print(f'Skipping {dbfile} (not found)')
        return

    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    print(f'\n--- Migrating {dbfile} ---')

    # --- Get existing columns ---
    def get_cols(table):
        try:
            cur.execute(f"PRAGMA table_info({table})")
            return {row[1] for row in cur.fetchall()}
        except Exception:
            return set()

    def get_tables():
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {row[0] for row in cur.fetchall()}

    # ----- ALTER existing tables to add new columns -----
    sup_cols = get_cols("supplier")
    if "payment_terms_days" not in sup_cols and sup_cols:
        cur.execute("ALTER TABLE supplier ADD COLUMN payment_terms_days INTEGER DEFAULT 30")
        print("  [+] supplier.payment_terms_days")
    elif sup_cols:
        print("  [=] supplier.payment_terms_days already exists")

    buy_cols = get_cols("buyer")
    if "payment_terms_days" not in buy_cols and buy_cols:
        cur.execute("ALTER TABLE buyer ADD COLUMN payment_terms_days INTEGER DEFAULT 30")
        print("  [+] buyer.payment_terms_days")
    elif buy_cols:
        print("  [=] buyer.payment_terms_days already exists")

    tables = get_tables()

    # ----- CREATE new tables -----

    if "notification" not in tables:
        cur.execute("""
            CREATE TABLE notification (
                id INTEGER PRIMARY KEY,
                recipient_role VARCHAR(40),
                recipient_id INTEGER REFERENCES user_account(id),
                entity_type VARCHAR(40),
                entity_id INTEGER,
                event_type VARCHAR(40) NOT NULL,
                message VARCHAR(255) NOT NULL,
                is_read BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME
            )
        """)
        print("  [+] notification table")
    else:
        print("  [=] notification table already exists")

    if "stock_count_session" not in tables:
        cur.execute("""
            CREATE TABLE stock_count_session (
                id INTEGER PRIMARY KEY,
                location_id INTEGER NOT NULL REFERENCES location(id),
                status VARCHAR(20) DEFAULT 'draft',
                counter_id INTEGER REFERENCES user_account(id),
                approver_id INTEGER REFERENCES user_account(id),
                created_at DATETIME,
                approved_at DATETIME
            )
        """)
        print("  [+] stock_count_session table")
    else:
        print("  [=] stock_count_session already exists")

    if "stock_count_line" not in tables:
        cur.execute("""
            CREATE TABLE stock_count_line (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES stock_count_session(id),
                item_id INTEGER NOT NULL REFERENCES item(id),
                system_qty_g BIGINT NOT NULL,
                counted_qty_g BIGINT NOT NULL,
                variance_g BIGINT NOT NULL,
                reason VARCHAR(200)
            )
        """)
        print("  [+] stock_count_line table")
    else:
        print("  [=] stock_count_line already exists")

    if "worker" not in tables:
        cur.execute("""
            CREATE TABLE worker (
                id INTEGER PRIMARY KEY,
                code VARCHAR(40) NOT NULL UNIQUE,
                full_name VARCHAR(160) NOT NULL,
                department VARCHAR(80) DEFAULT 'Production',
                wage_basis VARCHAR(20) DEFAULT 'hourly',
                hourly_rate_paise INTEGER DEFAULT 0,
                piece_rate_paise INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME
            )
        """)
        print("  [+] worker table")
    else:
        print("  [=] worker already exists")

    if "attendance_entry" not in tables:
        cur.execute("""
            CREATE TABLE attendance_entry (
                id INTEGER PRIMARY KEY,
                worker_id INTEGER NOT NULL REFERENCES worker(id),
                work_date DATE NOT NULL,
                shift VARCHAR(30) NOT NULL,
                hours_worked INTEGER,
                pieces_produced INTEGER,
                order_id INTEGER REFERENCES sale_order(id),
                run_id INTEGER REFERENCES production_run(id),
                notes TEXT,
                status VARCHAR(20) DEFAULT 'draft',
                created_by_id INTEGER NOT NULL REFERENCES user_account(id),
                approved_by_id INTEGER REFERENCES user_account(id),
                approved_at DATETIME,
                created_at DATETIME
            )
        """)
        # SQLite doesn't support adding unique constraint after the fact easily, but the model has it
        # The UniqueConstraint is declared on the model but SQLite will enforce it at the ORM level
        print("  [+] attendance_entry table")
    else:
        print("  [=] attendance_entry already exists")

    if "wage_run" not in tables:
        cur.execute("""
            CREATE TABLE wage_run (
                id INTEGER PRIMARY KEY,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                status VARCHAR(20) DEFAULT 'draft',
                created_by_id INTEGER NOT NULL REFERENCES user_account(id),
                finalised_by_id INTEGER REFERENCES user_account(id),
                created_at DATETIME,
                finalised_at DATETIME,
                UNIQUE (period_start, period_end)
            )
        """)
        print("  [+] wage_run table")
    else:
        print("  [=] wage_run already exists")

    if "wage_run_line" not in tables:
        cur.execute("""
            CREATE TABLE wage_run_line (
                id INTEGER PRIMARY KEY,
                wage_run_id INTEGER NOT NULL REFERENCES wage_run(id) ON DELETE CASCADE,
                worker_id INTEGER NOT NULL REFERENCES worker(id),
                total_hours_minutes INTEGER DEFAULT 0,
                total_pieces INTEGER DEFAULT 0,
                applied_rate_paise INTEGER DEFAULT 0,
                net_wage_paise INTEGER DEFAULT 0,
                UNIQUE (wage_run_id, worker_id)
            )
        """)
        print("  [+] wage_run_line table")
    else:
        print("  [=] wage_run_line already exists")

    if "order_cost" not in tables:
        cur.execute("""
            CREATE TABLE order_cost (
                id INTEGER PRIMARY KEY,
                order_id INTEGER NOT NULL UNIQUE REFERENCES sale_order(id),
                yarn_used_g INTEGER DEFAULT 0,
                material_cost_paise INTEGER,
                allocated_wage_paise INTEGER DEFAULT 0,
                overhead_paise INTEGER DEFAULT 0,
                known_cost_paise INTEGER DEFAULT 0,
                passed_metres INTEGER DEFAULT 0,
                calculated_at DATETIME
            )
        """)
        print("  [+] order_cost table")
    else:
        print("  [=] order_cost already exists")

    conn.commit()
    conn.close()
    print(f"  [OK] {dbfile} migration complete")


if __name__ == "__main__":
    print("=" * 56)
    print("  Khadira ERP - Schema Migration")
    print("=" * 56)
    migrate_db("mill.db")
    migrate_db("mill_demo.db")
    print("\nAll migrations complete.")
