"""App-lifetime DatabaseManager connection singleton for ChainSentinel.

Resolves per-request connection contention and DuckDB file locking concurrency bugs.
"""

from __future__ import annotations

from functools import lru_cache
import logging
from pathlib import Path

from app.core.config import settings
from chainsentinel.storage.db import DatabaseManager

logger = logging.getLogger("chainsentinel.db_singleton")


@lru_cache(maxsize=1)
def get_db(db_path: str | Path | None = None) -> DatabaseManager:
    """Get the application-lifetime DatabaseManager instance.
    
    FastAPI routes must use this singleton rather than instantiating
    separate DatabaseManager instances per request to avoid DuckDB lock contention.
    """
    path = db_path or settings.DB_PATH
    logger.info("Initializing app-lifetime DatabaseManager on %s", path)
    return DatabaseManager(db_path=path)


def reset_db_singleton() -> None:
    """Clear cached singleton (primarily used for test suite isolation)."""
    close_db()


def close_db() -> None:
    """Close the cached database connection if open and clear cache."""
    try:
        info = get_db.cache_info()
        if info.currsize > 0:
            db_inst = get_db()
            db_inst.close()
    except Exception as exc:
        logger.warning("Error closing db singleton: %s", exc)
    finally:
        get_db.cache_clear()
