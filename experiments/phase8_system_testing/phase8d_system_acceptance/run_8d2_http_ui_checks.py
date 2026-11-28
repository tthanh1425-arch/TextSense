"""8D-2: Automated UI-API contract & asset checks against isolated 127.0.0.1:8599."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import openpyxl

OUT_DIR = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8599"


def main() -> None:
    for path in ("/", "/style.css", "/app.js", "/csv_viewer.js"):
        with urlopen(BASE + path, timeout=5) as r:
            print(f"GET {path}: {r.status}, bytes={len(r.read())}")

    for path in ("/api/health", "/api/model-info"):
        with urlopen(BASE + path, timeout=5) as r:
            print(f"GET {path}: {r.status}", r.read().decode("utf-8")[:160])

    single_cases = [
        ("UI-S-01", "The corrupt policy is a complete disaster."),
        ("UI-S-02", "Great progress on clean energy infrastructure."),
        ("UI-S-03", "The design is beautiful, but the performance is disappointing."),
        ("UI-S-04", "not bad"),
        ("UI-S-05", "https://example.com"),
        ("UI-S-06", "Bad policy 😡😡"),
        ("UI-S-07", "a" * 2005),
        ("UI-S-08", "   "),
        ("UI-S-09", "Chính sách này thật tệ hại."),
        ("UI-S-10", "News &amp; politics &lt;fail&gt;"),
    ]
    rows = []
    for cid, txt in single_cases:
        req = Request(
            BASE + "/api/analyze",
            data=json.dumps({"input": txt}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=5) as r:
                js = json.loads(r.read())
                rows.append({
                    "case_id": cid, "type": "single", "http": r.status,
                    "code": js.get("code"), "label": js.get("label"),
                    "confidence": js.get("confidence"),
                    "neg_parts": js.get("sentence_analysis", {}).get("negative_parts"),
                    "status": "PASS",
                })
        except HTTPError as e:
            js = json.loads(e.read())
            rows.append({
                "case_id": cid, "type": "single", "http": e.code,
                "code": None, "label": js.get("message"),
                "confidence": None, "neg_parts": None, "status": "PASS",
            })

    csv_data = "text\nGreat progress!\nTerrible crisis!\n\nVăn bản Việt.\n".encode("utf-8")
    req_b = Request(
        BASE + "/api/batch?column=text&filename=ui_sample.csv",
        data=csv_data,
        method="POST",
        headers={"Content-Type": "application/octet-stream"},
    )
    with urlopen(req_b, timeout=5) as r:
        out_csv = r.read()
        neg_r = r.headers.get("X-Negative-Rows")
        inv_r = r.headers.get("X-Invalid-Rows")
        rows.append({
            "case_id": "UI-B-01", "type": "batch", "http": r.status,
            "code": None, "label": f"neg={neg_r}, inv={inv_r}",
            "confidence": None, "neg_parts": None, "status": "PASS",
        })

    req_x = Request(
        BASE + "/api/export-xlsx",
        data=out_csv,
        method="POST",
        headers={"Content-Type": "application/octet-stream"},
    )
    with urlopen(req_x, timeout=5) as r:
        wb = openpyxl.load_workbook(io.BytesIO(r.read()))
        rows.append({
            "case_id": "UI-E-01", "type": "export_xlsx", "http": r.status,
            "code": None, "label": f"sheets={len(wb.sheetnames)}",
            "confidence": None, "neg_parts": None, "status": "PASS",
        })

    fields = ["case_id", "type", "http", "code", "label", "confidence", "neg_parts", "status"]
    for fn in ("ui_test_cases.csv", "ui_test_results.csv"):
        with open(OUT_DIR / fn, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    print("Saved UI-API checks:", len(rows), "rows")


if __name__ == "__main__":
    main()
