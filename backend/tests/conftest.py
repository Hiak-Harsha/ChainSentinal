# conftest.py - shared test fixtures
import gc
import sys
from pathlib import Path
import pytest

# Ensure the backend directory is on the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session", autouse=True)
def teardown_duckdb():
    yield
    try:
        from app.core.db_singleton import close_db
        close_db()
    except Exception:
        pass
    gc.collect()
