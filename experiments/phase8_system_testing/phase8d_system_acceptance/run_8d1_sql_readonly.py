"""8D-1: Strictly read-only SQL Server connection, schema & row count verification."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pyodbc

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "03_GIAO_DIEN"))

import database as db  # noqa: E402

EXPECTED_TABLES = [
    "Tweets",
    "TweetTokens",
    "TrainingRuns",
    "PredictionBatches",
    "Predictions",
    "UserFeedback",
    "Users",
]


def main() -> None:
    conn_str = db.sql_server_connection_string()
    assert conn_str, "No SQL Server connection string resolved"

    out = {"db_name": None, "status": db.sql_server_status(), "tables": {}, "foreign_keys": []}
    compat_rows = []

    with pyodbc.connect(conn_str, timeout=4, readonly=True) as conn:
        cur = conn.cursor()
        out["db_name"] = cur.execute("SELECT DB_NAME()").fetchone()[0]
        for t in EXPECTED_TABLES:
            exists = cur.execute(
                "SELECT CASE WHEN OBJECT_ID(?, N'U') IS NOT NULL THEN 1 ELSE 0 END",
                (f"dbo.{t}",),
            ).fetchone()[0]
            if not exists:
                out["tables"][t] = {"exists": False}
                compat_rows.append({"table": f"dbo.{t}", "exists": False, "row_count": 0, "column_count": 0, "status": "MISSING"})
                continue
            cnt = int(cur.execute(f"SELECT COUNT(*) FROM dbo.[{t}]").fetchone()[0])
            cols = cur.execute(
                "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH "
                "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
                ("dbo", t),
            ).fetchall()
            col_list = [{"name": r[0], "type": r[1], "nullable": r[2], "max_len": r[3]} for r in cols]
            out["tables"][t] = {"exists": True, "row_count": cnt, "columns": col_list}
            compat_rows.append({
                "table": f"dbo.{t}", "exists": True, "row_count": cnt,
                "column_count": len(col_list),
                "columns": ", ".join(f"{c['name']}({c['type']})" for c in col_list),
                "status": "PASS",
            })

        fks = cur.execute(
            "SELECT fk.name, OBJECT_NAME(fk.parent_object_id), OBJECT_NAME(fk.referenced_object_id) FROM sys.foreign_keys fk"
        ).fetchall()
        out["foreign_keys"] = [{"name": r[0], "table": r[1], "ref_table": r[2]} for r in fks]

    (OUT_DIR / "_sql_readonly_raw.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(OUT_DIR / "sql_schema_compatibility.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["table", "exists", "row_count", "column_count", "columns", "status"])
        writer.writeheader()
        writer.writerows(compat_rows)

    print("DB:", out["db_name"], "| status:", out["status"]["available"])
    for r in compat_rows:
        print(f"  {r['table']}: exists={r['exists']}, rows={r['row_count']}, cols={r['column_count']}")
    print("FKs:", len(out["foreign_keys"]))


if __name__ == "__main__":
    main()
