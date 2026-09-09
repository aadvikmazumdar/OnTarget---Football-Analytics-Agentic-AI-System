from __future__ import annotations

import threading
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "ontarget.duckdb"

_local = threading.local()
_shared = None
_lock = threading.Lock()


def _base():
    global _shared
    if _shared is None:
        with _lock:
            if _shared is None:
                if not DB_PATH.exists():
                    raise RuntimeError(
                        f"{DB_PATH} missing - run `python scripts/build_db.py`"
                    )
                _shared = duckdb.connect(str(DB_PATH), read_only=True)
    return _shared


def db():
    """Thread-local cursor over one shared read-only connection."""
    cur = getattr(_local, "cur", None)
    if cur is None:
        cur = _base().cursor()
        _local.cur = cur
    return cur