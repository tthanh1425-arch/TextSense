"""Local SQLite persistence for training runs, uploads and prediction history."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / 'app_data' / 'textsense_history.sqlite3'

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS training_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_utc TEXT NOT NULL,
    task TEXT NOT NULL,
    status TEXT NOT NULL,
    model_path TEXT,
    metrics_json TEXT,
    log_text TEXT
);
CREATE TABLE IF NOT EXISTS prediction_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_utc TEXT NOT NULL,
    task TEXT NOT NULL,
    source_name TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    upload_bytes INTEGER NOT NULL,
    upload_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES prediction_batches(id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    input_text TEXT,
    predicted_label INTEGER,
    label_name TEXT,
    status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_training_runs_created ON training_runs(started_utc);
CREATE INDEX IF NOT EXISTS idx_prediction_batches_created ON prediction_batches(created_utc);
CREATE INDEX IF NOT EXISTS idx_predictions_batch ON predictions(batch_id);
"""


def init_db(db_path: Path = DB_PATH) -> Path:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
    return db_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_training_run(task: str, status: str, model_path: str | None = None,
                        metrics: dict | None = None, log_text: str = '', db_path: Path = DB_PATH) -> int:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            '''INSERT INTO training_runs(started_utc, task, status, model_path, metrics_json, log_text)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (_now(), task, status, model_path,
             json.dumps(metrics, ensure_ascii=False, default=lambda value: value.item() if hasattr(value, 'item') else str(value)) if metrics is not None else None,
             log_text[-50000:])
        )
        return int(cur.lastrowid)


def record_prediction_batch(task: str, source_name: str, results: list[dict],
                             upload_bytes: int = 0, raw_bytes: bytes | None = None,
                             db_path: Path = DB_PATH) -> int:
    init_db(db_path)
    digest = hashlib.sha256(raw_bytes or b'').hexdigest()
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            '''INSERT INTO prediction_batches(created_utc, task, source_name, row_count, upload_bytes, upload_sha256)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (_now(), task, source_name, len(results), int(upload_bytes), digest)
        )
        batch_id = int(cur.lastrowid)
        conn.executemany(
            '''INSERT INTO predictions(batch_id, row_number, input_text, predicted_label, label_name, status)
               VALUES (?, ?, ?, ?, ?, ?)''',
            [(batch_id, i + 1, str(row.get('text', '')),
              row.get('predicted_label'), row.get('label_name'), str(row.get('status', 'unknown')))
             for i, row in enumerate(results)]
        )
    return batch_id


def list_training_runs(limit: int = 50, db_path: Path = DB_PATH) -> list[dict]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(
            'SELECT * FROM training_runs ORDER BY id DESC LIMIT ?', (int(limit),)).fetchall()]


def list_prediction_batches(limit: int = 50, db_path: Path = DB_PATH) -> list[dict]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(
            'SELECT * FROM prediction_batches ORDER BY id DESC LIMIT ?', (int(limit),)).fetchall()]


def get_predictions(batch_id: int, db_path: Path = DB_PATH) -> list[dict]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(
            'SELECT * FROM predictions WHERE batch_id=? ORDER BY row_number', (int(batch_id),)).fetchall()]
