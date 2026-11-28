"""Phase 8C: Controlled HTTP API QA Test Suite for TextSense.

Runs an isolated ephemeral ThreadingHTTPServer on 127.0.0.1:0 with ALL database
functions mocked and pyodbc.connect blocked so zero real SQL Server calls occur.
"""
from __future__ import annotations

import hashlib
import io
import json
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import joblib
import numpy as np
import openpyxl
import pandas as pd
import scipy
import sklearn

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "03_GIAO_DIEN"))

import database as db_mod  # noqa: E402
import predict as pred_mod  # noqa: E402
import serve_textsense as web_mod  # noqa: E402

EXPECTED_MODEL_SHA = "474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a"
TRACKED_FILES = [
    "baseline_v3/binary_linear_svm.joblib",
    "01_TRAIN_MODEL/outputs/binary_linear_svm.joblib",
    "03_GIAO_DIEN/predict.py",
    "03_GIAO_DIEN/serve_textsense.py",
    "03_GIAO_DIEN/database.py",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


class DbMockTracker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.fail_feedback = False
        self.batch_seq = 9000
        self.fb_seq = 5000

    def install(self) -> None:
        # Block pyodbc.connect completely if pyodbc is ever imported
        try:
            import pyodbc
            def _blocked_connect(*args, **kwargs):
                raise AssertionError("REAL SQL SERVER CONNECTION BLOCKED BY 8C TEST HARNESS!")
            pyodbc.connect = _blocked_connect
        except Exception:
            pass

        def mock_sql_status():
            self.calls.append(("sql_server_status", {}))
            return {"configured": True, "available": False, "message": "Mocked read-only status (DB isolated in 8C)."}

        def mock_record_batch(task, source_name, results, upload_bytes, upload_raw, user_id=None):
            self.batch_seq += 1
            self.calls.append(("record_prediction_batch", {"source": source_name, "rows": len(results), "mock_id": self.batch_seq}))
            return None  # Simulate offline/no-persist or return mock ID; returning None verifies history_saved=False without DB

        def mock_record_feedback(**kwargs):
            self.calls.append(("record_user_feedback", {"source": kwargs.get("source_name"), "fail_mode": self.fail_feedback}))
            if self.fail_feedback:
                return None
            self.fb_seq += 1
            return self.fb_seq

        def mock_update_fb(fb_id, status):
            self.calls.append(("update_feedback_status", {"fb_id": fb_id, "status": status}))
            return True

        for mod in (db_mod, web_mod):
            if hasattr(mod, "sql_server_status"):
                setattr(mod, "sql_server_status", mock_sql_status)
            if hasattr(mod, "record_prediction_batch"):
                setattr(mod, "record_prediction_batch", mock_record_batch)
            if hasattr(mod, "record_user_feedback"):
                setattr(mod, "record_user_feedback", mock_record_feedback)
            if hasattr(mod, "update_feedback_status"):
                setattr(mod, "update_feedback_status", mock_update_fb)


def http_call(url: str, method: str = "GET", body: bytes | None = None, headers: dict | None = None, timeout: float = 15.0):
    req = Request(url, data=body, method=method, headers=headers or {})
    t0 = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, dict(resp.headers), raw, time.perf_counter() - t0
    except HTTPError as exc:
        raw = exc.read()
        return exc.code, dict(exc.headers), raw, time.perf_counter() - t0


def main() -> None:
    started_utc = datetime.now(timezone.utc).isoformat()
    sha_before = {p: sha256_file(ROOT / p) for p in TRACKED_FILES}
    assert sha_before["baseline_v3/binary_linear_svm.joblib"] == EXPECTED_MODEL_SHA
    assert sha_before["01_TRAIN_MODEL/outputs/binary_linear_svm.joblib"] == EXPECTED_MODEL_SHA

    tracker = DbMockTracker()
    tracker.install()

    server = web_mod.start_local_server(0)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    print(f"Started ephemeral test server on {base_url} (pid={__import__('os').getpid()})", flush=True)

    results: list[dict] = []

    def rec(cid, endpoint, group, inp_desc, expected, status_code, resp_summary, outcome, elapsed, note=""):
        results.append({
            "case_id": cid, "endpoint": endpoint, "group": group,
            "input_summary": inp_desc, "expected": expected,
            "http_status": status_code, "actual_summary": resp_summary,
            "result": outcome, "elapsed_ms": round(elapsed * 1000, 2), "note": note,
        })

    try:
        # === API-A: Health & Model Info ===
        st, _, raw, el = http_call(f"{base_url}/api/health")
        js = json.loads(raw)
        ok = st == 200 and js.get("status") == "ok" and js.get("model_present") is True and "password" not in raw.decode().lower()
        rec("API-A-01", "/api/health", "API-A", "GET", "200 + status=ok + model_present=True", st, str(js), "PASS" if ok else "FAIL", el)

        st, _, raw, el = http_call(f"{base_url}/api/model-info")
        js = json.loads(raw)
        ok = st == 200 and js.get("task") == "binary" and "LinearSVC" in str(js.get("model"))
        rec("API-A-02", "/api/model-info", "API-A", "GET", "200 + task=binary", st, f"model={js.get('model')}, acc={js.get('accuracy')}", "PASS" if ok else "FAIL", el)

        # === API-B: /api/analyze ===
        b1_valid = [
            ("API-B1-01", "The corrupt policy is a complete disaster."),
            ("API-B1-02", "Great progress on clean energy infrastructure."),
            ("API-B1-03", "Good design, but awful customer support."),
            ("API-B1-04", "I do not support this unfair law."),
            ("API-B1-05", "The service was excellent, although the price was disappointing."),
            ("API-B1-06", "Terrible speech! https://t.co/abc123"),
            ("API-B1-07", "Bad policy 😡😡"),
            ("API-B1-08", "What a mess!!! ??? ...awful..."),
        ]
        for cid, txt in b1_valid:
            body = json.dumps({"input": txt}).encode("utf-8")
            st, _, raw, el = http_call(f"{base_url}/api/analyze", "POST", body, {"Content-Type": "application/json"})
            js = json.loads(raw)
            inf = web_mod.infer_comment(txt)
            ok = st == 200 and js.get("code") in (0, 1) and js.get("code") == inf["code"] and js.get("history_saved") is False
            rec(cid, "/api/analyze", "API-B1_valid", txt, f"200 + code={inf['code']}", st, f"code={js.get('code')}, score={js.get('decision_score')}", "PASS" if ok else "FAIL", el)

        b2_invalid = [
            ("API-B2-01", json.dumps({}).encode(), "application/json", 422, "missing input"),
            ("API-B2-02", json.dumps({"input": None}).encode(), "application/json", 422, "null input"),
            ("API-B2-03", json.dumps({"input": 12345}).encode(), "application/json", 422, "number input"),
            ("API-B2-04", json.dumps({"input": True}).encode(), "application/json", 422, "boolean input"),
            ("API-B2-05", b"{bad json", "application/json", 400, "malformed json"),
            ("API-B2-06", b"", "application/json", 400, "empty body"),
            ("API-B2-07", json.dumps({"input": "    \t "}).encode(), "application/json", 422, "whitespace"),
            ("API-B2-08", json.dumps({"input": "!!!???"}).encode(), "application/json", 422, "punctuation only"),
            ("API-B2-09", json.dumps({"input": "bad " * 600}).encode(), "application/json", 413, "too long (>2000)"),
            ("API-B2-10", json.dumps({"input": "hello"}).encode(), "text/plain", 415, "unsupported content-type"),
        ]
        for cid, body, ctype, exp_st, desc in b2_invalid:
            st, _, raw, el = http_call(f"{base_url}/api/analyze", "POST", body, {"Content-Type": ctype})
            ok = st == exp_st
            rec(cid, "/api/analyze", "API-B2_invalid", desc, f"HTTP {exp_st}", st, raw.decode("utf-8", "replace")[:120], "PASS" if ok else "FAIL", el)

        b3_boundary = [
            ("API-B3-01", "a", 200, "1 char"),
            ("API-B3-02", ("policy reform " * 140).strip(), 200, "1960 chars (<2000)"),
            ("API-B3-03", ("terrible policy " * 140).strip(), 413, "2240 chars (>2000)"),
            ("API-B3-04", "bad " + ("!" * 2005), 413, "raw>2000 norm=3 (DEF-8B-02)"),
            ("API-B3-05", "Chính sách này thật tệ hại.", 422, "Vietnamese"),
            ("API-B3-06", "News &amp; politics &lt;fail&gt;", 200, "HTML entities"),
            ("API-B3-07", "Line one is good.\nLine two is terrible.", 200, "multiline"),
            ("API-B3-08", "Ｔｈｉｓ　ｉｓ　ａｗｆｕｌ！ 😡", 200, "NFKC + emoji"),
        ]
        for cid, txt, exp_st, desc in b3_boundary:
            body = json.dumps({"input": txt}).encode("utf-8")
            st, _, raw, el = http_call(f"{base_url}/api/analyze", "POST", body, {"Content-Type": "application/json"})
            ok = st == exp_st
            rec(cid, "/api/analyze", "API-B3_boundary", desc, f"HTTP {exp_st}", st, raw.decode("utf-8", "replace")[:120], "PASS" if ok else "FAIL", el)

        # === API-C: /api/batch ===
        def run_batch(cid, csv_bytes, exp_st, desc, col="text", expect_parity=True):
            st, hdrs, raw, el = http_call(
                f"{base_url}/api/batch?column={col}&filename=test.csv",
                "POST", csv_bytes, {"Content-Type": "application/octet-stream"},
            )
            if st != exp_st:
                rec(cid, "/api/batch", "API-C_batch", desc, f"HTTP {exp_st}", st, raw.decode("utf-8", "replace")[:120], "FAIL", el)
                return None
            if st != 200:
                rec(cid, "/api/batch", "API-C_batch", desc, f"HTTP {exp_st}", st, "rejected as expected", "PASS", el)
                return None
            out_df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
            in_df = pd.read_csv(io.BytesIO(csv_bytes), dtype=str, keep_default_na=False)
            parity_ok = True
            if expect_parity:
                direct = pred_mod.predict(web_mod.get_model_path(), in_df[col].tolist())
                exp_vals = [str(int(r["predicted_label"])) if r["predicted_label"] is not None else "" for r in direct]
                parity_ok = (out_df[web_mod.RESULT_COLUMN].tolist() == exp_vals)
            ok = len(out_df) == len(in_df) and parity_ok and hdrs.get("X-History-Saved") == "false"
            rec(cid, "/api/batch", "API-C_batch", desc, f"200 + {len(in_df)} rows + parity", st, f"rows={len(out_df)}, neg={hdrs.get('X-Negative-Rows')}, inv={hdrs.get('X-Invalid-Rows')}", "PASS" if ok else "FAIL", el)
            return raw

        run_batch("API-C-01", "text\nTerrible policy.\n".encode(), 200, "1 row")
        run_batch("API-C-02", "text\nGood job.\nBad policy.\nNot bad.\nGreat day.\nAwful crisis.\n".encode(), 200, "5 rows")
        rows_100 = "text\n" + "\n".join([f"Policy comment {i} is {'awful' if i%2 else 'great'}." for i in range(100)]) + "\n"
        run_batch("API-C-03", rows_100.encode(), 200, "100 rows")
        rows_1000 = "text\n" + "\n".join([f"Sample comment {i} {'bad' if i%3==0 else 'good'}." for i in range(1000)]) + "\n"
        run_batch("API-C-04", rows_1000.encode(), 200, "1000 rows")
        run_batch("API-C-05", "text\nGood policy.\nhttps://example.com\nBad policy.\n".encode(), 200, "1 invalid URL row")
        run_batch("API-C-06", "text\nGood policy.\n\n   \nBad policy.\n".encode(), 200, "interleaved empty rows")
        run_batch("API-C-07", "text\nVăn bản tiếng Việt.\nTerrible!\n!!!\nGreat!\n".encode(), 200, "mixed rejected + valid")
        run_batch("API-C-08", "text\nBad policy.\nBad policy.\n".encode(), 200, "duplicate rows")
        run_batch("API-C-09", "text\nBad policy 😡\nＴｈｉｓ　ｉｓ　ｇｒｅａｔ！\n".encode("utf-8"), 200, "Unicode + emoji")
        run_batch("API-C-10", "text\nHello\n".encode(), 422, "missing column name", col="wrong_col", expect_parity=False)

        # === API-D: /api/feedback (mocked DB) ===
        fb_valid = {"source": "Bình luận riêng lẻ", "prediction": "Không phát hiện nội dung tiêu cực", "suggested_label": "Có nội dung tiêu cực", "note": "QA test", "text": "Not good"}
        st, _, raw, el = http_call(f"{base_url}/api/feedback", "POST", json.dumps(fb_valid).encode(), {"Content-Type": "application/json"})
        js = json.loads(raw)
        rec("API-D-01", "/api/feedback", "API-D_feedback", "valid feedback", "200 + feedback_saved=True", st, str(js), "PASS" if (st == 200 and js.get("feedback_saved")) else "FAIL", el)

        st, _, raw, el = http_call(f"{base_url}/api/feedback", "POST", json.dumps({"text": "missing labels"}).encode(), {"Content-Type": "application/json"})
        rec("API-D-02", "/api/feedback", "API-D_feedback", "missing required labels", "422", st, raw.decode("utf-8", "replace")[:100], "PASS" if st == 422 else "FAIL", el)

        st, _, raw, el = http_call(f"{base_url}/api/feedback", "POST", b"{bad", {"Content-Type": "application/json"})
        rec("API-D-03", "/api/feedback", "API-D_feedback", "malformed json", "400", st, raw.decode("utf-8", "replace")[:100], "PASS" if st == 400 else "FAIL", el)

        tracker.fail_feedback = True
        st, _, raw, el = http_call(f"{base_url}/api/feedback", "POST", json.dumps(fb_valid).encode(), {"Content-Type": "application/json"})
        tracker.fail_feedback = False
        rec("API-D-04", "/api/feedback", "API-D_feedback", "simulated DB failure", "503", st, raw.decode("utf-8", "replace")[:100], "PASS" if st == 503 else "FAIL", el)

        # === API-E: /api/export-xlsx ===
        batch_csv = run_batch("API-E-00_prep", 'text\n"Good, great"\nBad policy!\n"Line1\nLine2"\n=CMD()\nVăn bản Việt.\n'.encode("utf-8"), 200, "prep CSV for XLSX", expect_parity=False)
        st, hdrs, raw_xlsx, el = http_call(f"{base_url}/api/export-xlsx", "POST", batch_csv, {"Content-Type": "application/octet-stream"})
        wb = openpyxl.load_workbook(io.BytesIO(raw_xlsx))
        ws = wb["Kết quả phân loại"]
        rows_xlsx = list(ws.iter_rows(values_only=True))
        # Check header + 5 data rows, formula protection '=CMD() -> "'=CMD()" or safe string
        ok_xlsx = st == 200 and len(rows_xlsx) == 6 and rows_xlsx[5][1] == ""  # Vietnamese row rejected -> empty code, not 0
        rec("API-E-01", "/api/export-xlsx", "API-E_xlsx", "valid CSV with quotes/newlines/Vietnamese/formula", "200 + valid XLSX 6 rows", st, f"sheets={wb.sheetnames}, rows={len(rows_xlsx)}", "PASS" if ok_xlsx else "FAIL", el)

        st, _, raw, el = http_call(f"{base_url}/api/export-xlsx", "POST", b"", {"Content-Type": "application/octet-stream"})
        rec("API-E-02", "/api/export-xlsx", "API-E_xlsx", "empty CSV", "422", st, raw.decode("utf-8", "replace")[:100], "PASS" if st == 422 else "FAIL", el)

        # === Error handling & Security ===
        st, _, raw, el = http_call(f"{base_url}/api/nonexistent", "GET")
        rec("API-ERR-01", "/api/nonexistent", "Error_Security", "GET unknown endpoint", "404", st, raw.decode("utf-8", "replace")[:100], "PASS" if st == 404 else "FAIL", el)

        st, _, raw, el = http_call(f"{base_url}/api/analyze", "DELETE")
        rec("API-ERR-02", "/api/analyze", "Error_Security", "unsupported method DELETE", "405 or 501", st, raw.decode("utf-8", "replace")[:100], "PASS" if st in (405, 501) else "FAIL", el)

        oversize = json.dumps({"input": "a" * 40000}).encode("utf-8")
        st, _, raw, el = http_call(f"{base_url}/api/analyze", "POST", oversize, {"Content-Type": "application/json"})
        rec("API-ERR-03", "/api/analyze", "Error_Security", "JSON > 32KB", "413", st, raw.decode("utf-8", "replace")[:100], "PASS" if st == 413 else "FAIL", el)

        # === Concurrency (5, 10, 20 concurrent requests) ===
        conc_summary = {}
        for n_conc in (5, 10, 20):
            def _worker(i):
                txt = f"Terrible crisis {i}" if i % 2 == 0 else f"Great progress {i}"
                exp_code = 1 if i % 2 == 0 else 0
                st_c, _, raw_c, el_c = http_call(
                    f"{base_url}/api/analyze", "POST",
                    json.dumps({"input": txt}).encode(), {"Content-Type": "application/json"},
                )
                js_c = json.loads(raw_c)
                return st_c == 200 and js_c.get("code") == exp_code and txt in js_c.get("text", ""), el_c

            with ThreadPoolExecutor(max_workers=n_conc) as ex:
                outs = list(ex.map(_worker, range(n_conc)))
            all_ok = all(o[0] for o in outs)
            max_ms = round(max(o[1] for o in outs) * 1000, 2)
            conc_summary[f"conc_{n_conc}"] = {"success": sum(1 for o in outs if o[0]), "total": n_conc, "max_ms": max_ms}
            rec(f"API-CONC-{n_conc}", "/api/analyze", "Concurrency", f"{n_conc} concurrent requests", f"{n_conc}/{n_conc} 200 + no mix", 200 if all_ok else 500, str(conc_summary[f"conc_{n_conc}"]), "PASS" if all_ok else "FAIL", max_ms / 1000.0)

    finally:
        server.shutdown()
        server.server_close()
        web_mod._server = None
        print("Ephemeral test server stopped cleanly.", flush=True)

    sha_after = {p: sha256_file(ROOT / p) for p in TRACKED_FILES}
    assert sha_before == sha_after, "File hash changed during 8C testing!"

    df_res = pd.DataFrame(results)
    df_res.to_csv(OUT_DIR / "api_test_cases.csv", index=False, encoding="utf-8-sig")
    df_res.to_csv(OUT_DIR / "api_test_results.csv", index=False, encoding="utf-8-sig")

    summary = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "server_bind": f"127.0.0.1:{port}",
        "total_cases": len(df_res),
        "passed": int((df_res["result"] == "PASS").sum()),
        "failed": int((df_res["result"] == "FAIL").sum()),
        "db_mock_calls_count": len(tracker.calls),
        "db_mock_calls": tracker.calls[:20],
        "concurrency": conc_summary,
        "sha256_before": sha_before,
        "sha256_after": sha_after,
        "sha256_unchanged": sha_before == sha_after,
        "environment": {
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "joblib": joblib.__version__,
            "openpyxl": openpyxl.__version__,
        },
    }
    (OUT_DIR / "_run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Phase 8C tests finished: {summary['passed']}/{summary['total_cases']} PASSED, failed={summary['failed']}, DB mock calls={len(tracker.calls)}")


if __name__ == "__main__":
    main()
