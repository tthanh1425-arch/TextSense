"""Phase 8B: Independent Inference Pipeline QA Test Suite (Groups A-E).

Tests E0-Artifact (01_TRAIN_MODEL/outputs/binary_linear_svm.joblib) through
03_GIAO_DIEN/predict.py and 03_GIAO_DIEN/serve_textsense.py (infer_comment /
analyze_sentence_breakdown) in strictly read-only mode (no DB writes, no T1/T2).
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "03_GIAO_DIEN"))

import predict as pred_mod  # noqa: E402
import serve_textsense as web_mod  # noqa: E402

MODEL_PATH = ROOT / "01_TRAIN_MODEL" / "outputs" / "binary_linear_svm.joblib"
BASELINE_PATH = ROOT / "baseline_v3" / "binary_linear_svm.joblib"
EXPECTED_SHA = "474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_test_cases() -> list[dict]:
    cases: list[dict] = []

    # Group A: Basic texts (30 cases: 10 negative, 10 non-negative, 10 mixed/ambiguous)
    a_neg = [
        ("The new policy is a complete disaster for working families.", 1),
        ("Corrupt politicians are ruining the country's economy.", 1),
        ("This leadership has failed miserably on every promise.", 1),
        ("Terrible decision that hurts poor citizens the most.", 1),
        ("The minister's speech was full of lies and propaganda.", 1),
        ("Unemployment is rising and nobody in power cares.", 1),
        ("Horrible handling of the crisis by the administration.", 1),
        ("Wasting taxpayer money on useless projects is shameful.", 1),
        ("The healthcare system is broken and getting worse.", 1),
        ("Disgusting behavior from elected officials during the debate.", 1),
    ]
    a_nonneg = [
        ("The infrastructure project created thousands of new jobs.", 0),
        ("Great progress in renewable energy over the past year.", 0),
        ("The committee released its annual budget report today.", 0),
        ("Voters turned out in large numbers for the local election.", 0),
        ("Public schools received additional funding for science labs.", 0),
        ("The parliament will convene on Monday morning to discuss the bill.", 0),
        ("Strong economic growth helped stabilize inflation this quarter.", 0),
        ("Citizens welcomed the transparent digital government portal.", 0),
        ("The diplomatic summit concluded with a trade agreement.", 0),
        ("Clean water access improved in several rural districts.", 0),
    ]
    a_mixed = [
        ("The bill has some good ideas, though implementation remains unclear.", -1),
        ("Taxes were reduced, yet public transit fares increased.", -1),
        ("Some critics raised concerns while supporters praised the reform.", -1),
        ("The speech was long and technical, covering many topics.", -1),
        ("Maybe this policy will help in the long run, who knows.", -1),
        ("Exports rose slightly despite global supply chain pressures.", -1),
        ("Half of the council voted yes and half voted no.", -1),
        ("The mayor promised changes, but results are still pending.", -1),
        ("Interesting proposal that needs much more data to evaluate.", -1),
        ("Prices stabilized, though wages have barely moved.", -1),
    ]
    for i, (txt, sem) in enumerate(a_neg + a_nonneg + a_mixed, 1):
        cases.append({
            "case_id": f"A-{i:02d}", "group": "A_basic", "input_text": txt,
            "expected_behavior": "valid_prediction", "expected_semantic_label": sem,
        })

    # Group B: Contrastive & compound sentences (30 cases)
    b_texts = [
        "The design is beautiful, but the performance is disappointing.",
        "The food wasn't bad, but I wouldn't call it delicious either.",
        "The service was excellent, although the price was disappointing.",
        "I like the product, but the customer support is terrible.",
        "The update fixed several bugs, but introduced new problems.",
        "The speech sounded inspiring, however the actual policy is awful.",
        "Education funding increased, yet teacher morale is terrible.",
        "The roads are smoother, but traffic congestion is worse than ever.",
        "Healthcare access expanded, although wait times remain unacceptable.",
        "The new law protects consumers, but hurts small businesses badly.",
        "Great presentation by the minister, but zero accountability for failures.",
        "Inflation cooled slightly, however grocery prices are still outrageous.",
        "The app looks modern, but crashes constantly during checkout.",
        "Good intentions behind the reform, but poor execution ruined it.",
        "The city built new parks, yet homelessness continues to worsen.",
        "Strong defense spending, but veterans are neglected.",
        "I appreciate the effort, although the outcome is a total failure.",
        "The train is fast, but the stations are filthy and unsafe.",
        "Economic indicators look solid, yet many families feel abandoned.",
        "Nice rhetoric during the campaign, but broken promises afterward.",
        "The policy helps exporters, while domestic workers suffer.",
        "Clean interface, but customer complaints are ignored.",
        "The bridge was completed on time, though the budget exploded.",
        "Police response was quick, but the investigation was sloppy.",
        "Solar adoption is growing, however coal pollution remains terrible.",
        "The mayor is popular, yet city services are failing.",
        "Good battery life, awful screen quality.",
        "Helpful staff, but the waiting room was dirty and chaotic.",
        "Transparent reporting, but disastrous financial management.",
        "Impressive growth numbers, although inequality is worsening rapidly.",
    ]
    for i, txt in enumerate(b_texts, 1):
        cases.append({
            "case_id": f"B-{i:02d}", "group": "B_contrastive", "input_text": txt,
            "expected_behavior": "valid_prediction_check_parity", "expected_semantic_label": -1,
        })

    # Group C: Negation & context (30 cases)
    c_texts = [
        ("not good", 1),
        ("not bad", 0),
        ("never worked", 1),
        ("no problem", 0),
        ("not only good but excellent", 0),
        ("not as bad as expected", 0),
        ("I don't dislike it", 0),
        ("I wouldn't recommend it", 1),
        ("The product is not perfect, but acceptable.", 0),
        ("I thought it was terrible, but it turned out fine.", 0),
        ("This policy is not helpful at all.", 1),
        ("They did not fail to deliver on time.", 0),
        ("Nobody believes the official report.", 1),
        ("Nothing in this budget helps poor families.", 1),
        ("Without transparency, democracy suffers.", 1),
        ("Neither the mayor nor the council took responsibility.", 1),
        ("I cannot say this is a bad decision.", 0),
        ("It is not the worst law ever passed.", 0),
        ("The minister never lies to the public.", 0),
        ("No one can deny the terrible damage done.", 1),
        ("This isn't going to end well for voters.", 1),
        ("He didn't do anything wrong in that debate.", 0),
        ("We shouldn't ignore the rising poverty rate.", 1),
        ("She wasn't happy about the unfair tax hike.", 1),
        ("Not a single promise was kept by the party.", 1),
        ("Don't worry, the economy is not collapsing.", 0),
        ("I don't hate the proposal, it's just incomplete.", 0),
        ("There is no reason to panic about the audit.", 0),
        ("This is anything but a successful reform.", 1),
        ("Hardly anyone supports this corrupt bill.", 1),
    ]
    for i, (txt, sem) in enumerate(c_texts, 1):
        cases.append({
            "case_id": f"C-{i:02d}", "group": "C_negation", "input_text": txt,
            "expected_behavior": "valid_prediction", "expected_semantic_label": sem,
        })

    # Group D: Boundary inputs (26 cases)
    long_ok = ("policy reform " * 140).strip()          # ~1960 chars (< 2000)
    long_over = ("terrible policy " * 140).strip()      # ~2240 chars (> 2000)
    near_2000_raw_over_norm_ok = ("bad " + ("!" * 2005)) # raw > 2000, norm == "bad" (3 chars)
    d_cases = [
        ("", "reject_empty"),
        ("     \t  ", "reject_empty"),
        ("!!! ??? --- ...", "reject_empty"),
        ("https://example.com/news/123", "reject_url"),
        ("www.example.com/politics", "reject_url"),
        ("https://x.com/user/status/12345", "reject_url"),
        ("Terrible policy! https://t.co/abc123", "valid_prediction"),
        ("RT @user123: Great speech today! http://news.org", "valid_prediction"),
        (long_ok, "valid_prediction"),
        (long_over, "reject_too_long"),
        (near_2000_raw_over_norm_ok, "check_raw_vs_norm_limit"),
        ("😡😡😡", "reject_empty_after_norm"),
        ("Bad policy 😡😡", "valid_prediction"),
        ("Ｔｈｉｓ　ｉｓ　ａｗｆｕｌ！", "valid_prediction"),
        ("It’s a terrible—broken—system…", "valid_prediction"),
        ("@#$%^&*()_+={}[]|\\", "reject_empty"),
        ("Line one is good.\nLine two is terrible.", "valid_prediction"),
        ("bad bad bad bad bad bad", "valid_prediction"),
        ("1234567890 2026", "valid_prediction"),
        ("Chính sách này thật tệ hại và gây bức xúc.", "reject_vietnamese"),
        ("Bình luận tiếng Việt có dấu rất rõ ràng.", "reject_vietnamese"),
        ("The policy is bad nhưng thực sự rất tệ hại.", "reject_vietnamese"),
        ("The policy is bad nhưng ok", "valid_prediction_low_vi_ratio"),
        ("a", "valid_prediction_single_char"),
        ("no", "valid_prediction_short_word"),
        ("News &amp; politics &lt;fail&gt;", "valid_prediction"),
    ]
    for i, (txt, exp) in enumerate(d_cases, 1):
        cases.append({
            "case_id": f"D-{i:02d}", "group": "D_boundary", "input_text": txt,
            "expected_behavior": exp, "expected_semantic_label": -1,
        })

    # Group E: Stability & consistency (20 representative cases)
    e_texts = [
        "The economic policy is terrible and hurts workers.",
        "Great progress on clean energy infrastructure.",
        "I don't think this law is fair.",
        "Good design, but awful battery life.",
        "https://example.com",
        "",
        "Văn bản tiếng Việt có dấu.",
        "Corrupt officials must be held accountable.",
        "Public schools received new funding.",
        "Not bad at all, actually quite good.",
        "They won't listen to citizens.",
        "The budget passed without debate.",
        "Prices are rising fast!",
        "Thank you for the transparent report.",
        "Nothing worked as promised.",
        "!!!???",
        "Terrible crisis management.",
        "Strong leadership and steady growth.",
        "Mixed results across the region.",
        "Another broken promise from the minister.",
    ]
    for i, txt in enumerate(e_texts, 1):
        cases.append({
            "case_id": f"E-{i:02d}", "group": "E_stability", "input_text": txt,
            "expected_behavior": "deterministic_consistent", "expected_semantic_label": -1,
        })

    return cases


def main() -> None:
    started_utc = datetime.now(timezone.utc).isoformat()
    sha_before = {
        "baseline_v3/binary_linear_svm.joblib": sha256_file(BASELINE_PATH),
        "01_TRAIN_MODEL/outputs/binary_linear_svm.joblib": sha256_file(MODEL_PATH),
        "03_GIAO_DIEN/predict.py": sha256_file(ROOT / "03_GIAO_DIEN" / "predict.py"),
        "03_GIAO_DIEN/serve_textsense.py": sha256_file(ROOT / "03_GIAO_DIEN" / "serve_textsense.py"),
    }
    assert sha_before["baseline_v3/binary_linear_svm.joblib"] == EXPECTED_SHA
    assert sha_before["01_TRAIN_MODEL/outputs/binary_linear_svm.joblib"] == EXPECTED_SHA

    cases = build_test_cases()
    pd.DataFrame(cases).to_csv(OUT_DIR / "test_cases.csv", index=False, encoding="utf-8-sig")

    # Run predict() on all cases
    t0 = time.perf_counter()
    texts = [c["input_text"] for c in cases]
    pred_results = pred_mod.predict(MODEL_PATH, texts, batch_size=512)
    total_batch_sec = time.perf_counter() - t0

    art = joblib.load(MODEL_PATH)
    thr = float(art["threshold"])

    result_rows = []
    parity_rows = []
    for c, r in zip(cases, pred_results):
        txt = c["input_text"]
        norm = pred_mod.normalize_text(txt)
        result_rows.append({
            "case_id": c["case_id"],
            "group": c["group"],
            "input_text": txt,
            "normalized_text": norm,
            "decision_score": r.get("decision_score"),
            "threshold": r.get("decision_threshold", thr) if r["status"] == "ok" else thr,
            "model_label": r["predicted_label"],
            "status": r["status"],
            "expected_behavior": c["expected_behavior"],
            "expected_semantic_label": c["expected_semantic_label"],
        })

        # Run infer_comment() parity for Groups A, B, C, D, E
        infer_label = None
        infer_status = "ok"
        sent_count = 0
        neg_parts = 0
        diff_reason = "same"
        try:
            inf = web_mod.infer_comment(txt)
            infer_label = inf["code"]
            sa = inf["sentence_analysis"]
            sent_count = int(sa.get("total_parts", 1))
            neg_parts = int(sa.get("negative_parts", 0))
            if r["predicted_label"] is None:
                diff_reason = f"predict_rejected({r['status']})_vs_infer_accepted"
            elif r["predicted_label"] != infer_label:
                diff_reason = "OR_rule_clause_negative" if (r["predicted_label"] == 0 and infer_label == 1 and neg_parts > 0) else "other_mismatch"
        except web_mod.RequestFailure as exc:
            infer_status = f"HTTP_{exc.status}:{exc.message}"
            if r["predicted_label"] is not None:
                diff_reason = f"predict_accepted_vs_infer_rejected({exc.status})"
            else:
                diff_reason = "both_rejected"

        parity_rows.append({
            "case_id": c["case_id"],
            "group": c["group"],
            "input_text": txt,
            "predict_label": r["predicted_label"],
            "predict_status": r["status"],
            "decision_score": r.get("decision_score"),
            "sentence_count": sent_count,
            "negative_parts": neg_parts,
            "infer_comment_label": infer_label,
            "infer_status": infer_status,
            "difference_reason": diff_reason,
        })

    pd.DataFrame(result_rows).to_csv(OUT_DIR / "pipeline_test_results.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(parity_rows).to_csv(OUT_DIR / "predict_infer_parity.csv", index=False, encoding="utf-8-sig")

    # Group E: Stability checks (repeatability, single vs batch, shuffled order, batch size <512, ==512, >512)
    e_texts = [c["input_text"] for c in cases if c["group"] == "E_stability"]
    r_run1 = pred_mod.predict(MODEL_PATH, e_texts)
    r_run2 = pred_mod.predict(MODEL_PATH, e_texts)
    repeat_ok = all(a == b for a, b in zip(r_run1, r_run2))

    single_ok = all(pred_mod.predict(MODEL_PATH, [t])[0] == r for t, r in zip(e_texts, r_run1))

    rev_texts = list(reversed(e_texts))
    r_rev = list(reversed(pred_mod.predict(MODEL_PATH, rev_texts)))
    order_ok = all(a == b for a, b in zip(r_run1, r_rev))

    # Batch sizes: 100 (<512), 512 (==512), 600 (>512)
    large_600 = (e_texts * 30)[:600]
    r_600 = pred_mod.predict(MODEL_PATH, large_600, batch_size=512)
    r_512 = pred_mod.predict(MODEL_PATH, large_600[:512], batch_size=512)
    r_100 = pred_mod.predict(MODEL_PATH, large_600[:100], batch_size=512)
    batch_size_ok = (
        len(r_600) == 600
        and all(a == b for a, b in zip(r_600[:512], r_512))
        and all(a == b for a, b in zip(r_600[:100], r_100))
    )

    sha_after = {k: sha256_file(ROOT / k) for k in sha_before}
    assert sha_before == sha_after, "File hash changed during test!"

    parity_df = pd.DataFrame(parity_rows)
    b_parity = parity_df[parity_df["group"] == "B_contrastive"]
    b_same = int((b_parity["difference_reason"] == "same").sum())
    b_or_flip = int((b_parity["difference_reason"] == "OR_rule_clause_negative").sum())

    d_df = pd.DataFrame([r for r in result_rows if r["group"] == "D_boundary"])
    d_par = parity_df[parity_df["group"] == "D_boundary"]

    print(f"Total cases: {len(cases)}, batch_sec={total_batch_sec:.4f}")
    print(f"Group B parity: same={b_same}/30, OR_rule_flip={b_or_flip}/30")
    print(f"Group D mismatches predict vs infer: {d_par[d_par['difference_reason'].str.contains('rejected')][['case_id','difference_reason']].to_dict(orient='records')}")
    print(f"Group E: repeat_ok={repeat_ok}, single_ok={single_ok}, order_ok={order_ok}, batch_size_ok={batch_size_ok}")

    summary = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(cases),
        "counts_by_group": pd.DataFrame(cases)["group"].value_counts().to_dict(),
        "group_b_same": b_same,
        "group_b_or_flip": b_or_flip,
        "group_e_checks": {
            "repeat_ok": repeat_ok,
            "single_vs_batch_ok": single_ok,
            "order_invariant_ok": order_ok,
            "batch_size_lt_eq_gt_512_ok": batch_size_ok,
        },
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
        },
    }
    (OUT_DIR / "_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
