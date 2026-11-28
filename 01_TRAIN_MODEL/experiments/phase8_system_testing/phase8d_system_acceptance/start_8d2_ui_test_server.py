"""Isolated 8D-2 UI Test Server on 127.0.0.1:8599 with ALL DB writes mocked."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "03_GIAO_DIEN"))

import pyodbc  # noqa: E402
import database as db_mod  # noqa: E402
import serve_textsense as web_mod  # noqa: E402


def _blocked(*args, **kwargs):
    raise AssertionError("REAL SQL SERVER CONNECTION BLOCKED DURING 8D-2 UI TEST!")


pyodbc.connect = _blocked

for mod in (db_mod, web_mod):
    mod.sql_server_status = lambda: {"configured": True, "available": False, "message": "Mocked read-only (8D-2 DB isolated)."}
    mod.record_prediction_batch = lambda *a, **kw: None
    mod.record_user_feedback = lambda *a, **kw: 9999
    mod.update_feedback_status = lambda *a, **kw: True
    mod.list_prediction_batches = lambda *a, **kw: []
    mod.get_predictions = lambda *a, **kw: []
    mod.list_user_feedback = lambda *a, **kw: {"items": [], "counts": {}}
    mod.query_predictions_paginated = lambda *a, **kw: {"items": [], "total": 0}
    mod.get_user_by_id = lambda *a, **kw: None


if __name__ == "__main__":
    server = web_mod.start_local_server(8599)
    print(f"8D-2 UI Test Server listening on http://127.0.0.1:8599 (pid={os.getpid()})", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()
