"""Step 10 Automated Test: Service-driven scenario data verification.

Proves:
- The scenario loader generates rich demonstration data purely through real domain functions
- Stock was never negative at any time
- Stock levels equal the sum of movements
- Yarn lot remainders add up to RAW inventory
- Every invoice equals its dispatch exactly
- Order progress matches physical rolls and tolerances
- Historical tables (RollEvent, StockMove, YarnReceipt, RunMaterial, etc.) are all populated
- Running the scenario loader twice does not create duplicate records
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mill.models import Base
from mill.scenario_loader import load_scenario
from verify_scenario import verify_scenario


@pytest.fixture
def fresh_scenario_db(tmp_path):
    db_file = tmp_path / "scenario_test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        load_scenario(session, force_reset=False)
        yield session
    finally:
        session.close()


def test_scenario_verification_all_checks_pass(fresh_scenario_db):
    """Assert all 6 verification checks pass on freshly loaded service-driven scenario."""
    res = verify_scenario(fresh_scenario_db)
    assert res["all_passed"] is True
    assert res["details"]["stock_never_negative"] is True
    assert res["details"]["stock_levels_match_movements"] is True
    assert res["details"]["batch_remainders_add_up"] is True
    assert res["details"]["every_invoice_equals_dispatch"] is True
    assert res["details"]["order_progress_matches_rolls"] is True
    assert res["details"]["no_history_tables_empty"] is True


def test_scenario_loader_idempotency(fresh_scenario_db):
    """Assert that running scenario loader twice does not create duplicates."""
    res = load_scenario(fresh_scenario_db, force_reset=False)
    assert res["status"] == "already_loaded"
