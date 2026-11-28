"""Phase 5: Final One-Shot Evaluation on T1 (39,210) and T2 (60,000) from Freeze Manifest.

Reads only frozen artifacts from experiments/freeze_manifest.json, verifies all hashes,
evaluates T1 and T2, computes 1000-iteration Bootstrap CIs, Paired Bootstrap, McNemar + Holm,
and extracts FP/FN error analysis samples without modifying any frozen artifact or model.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.stats import binomtest, chi2
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "baseline_v3"))

from negation_feature import NEGATION_TRIGGERS, add_negation_features  # noqa: E402
from predict import normalize_text as normalize_v3  # noqa: E402

EXPERIMENTS = ROOT / "experiments"
OUT_DIR = EXPERIMENTS / "phase5_final_evaluation"
SEED = 42
N_BOOT = 1000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fast_pr_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Exact average precision matching sklearn on continuous scores."""
    return float(average_precision_score(y_true, scores))


def compute_full_metrics(y_true: np.ndarray, scores: np.ndarray, thr: float) -> tuple[dict, np.ndarray]:
    y_pred = (scores > thr).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = (int(x) for x in cm.ravel())
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    rep = classification_report(y_true, y_pred, labels=[0, 1], output_dict=True, zero_division=0)
    m = {
        "n_evaluated": int(len(y_true)),
        "n_skipped": 0,
        "pos_count": int(y_true.sum()),
        "neg_count": int((1 - y_true).sum()),
        "threshold": float(thr),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_class1": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall_class1": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1_class1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f2_class1": float(fbeta_score(y_true, y_pred, beta=2.0, pos_label=1, zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "pr_auc_class1": fast_pr_auc(y_true, scores),
        "specificity": spec,
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        "classification_report": rep,
    }
    return m, y_pred


def bootstrap_metrics(
    y_true: np.ndarray,
    scores_dict: dict[str, np.ndarray],
    preds_dict: dict[str, np.ndarray],
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> tuple[dict[str, dict[str, np.ndarray]], list[dict]]:
    """Compute 1000-iteration bootstrap arrays and 95% CIs using shared indices across models."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    model_ids = list(scores_dict.keys())
    boot_arrays: dict[str, dict[str, np.ndarray]] = {
        mid: {k: np.empty(n_boot, dtype=np.float64) for k in ("precision", "recall", "f1", "pr_auc")}
        for mid in model_ids
    }

    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        for mid in model_ids:
            yp = preds_dict[mid][idx]
            sc = scores_dict[mid][idx]
            tp = float(np.sum((yt == 1) & (yp == 1)))
            fp = float(np.sum((yt == 0) & (yp == 1)))
            fn = float(np.sum((yt == 1) & (yp == 0)))
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
            boot_arrays[mid]["precision"][b] = p
            boot_arrays[mid]["recall"][b] = r
            boot_arrays[mid]["f1"][b] = f1
            boot_arrays[mid]["pr_auc"][b] = float(average_precision_score(yt, sc))

    ci_rows = []
    for mid in model_ids:
        row = {"model": mid}
        for metric in ("precision", "recall", "f1", "pr_auc"):
            arr = boot_arrays[mid][metric]
            lo, hi = np.percentile(arr, [2.5, 97.5])
            row[f"{metric}_mean"] = float(np.mean(arr))
            row[f"{metric}_ci95_low"] = float(lo)
            row[f"{metric}_ci95_high"] = float(hi)
        ci_rows.append(row)
    return boot_arrays, ci_rows


def mcnemar_test(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray) -> dict:
    a_ok = pred_a == y_true
    b_ok = pred_b == y_true
    b = int(np.sum(a_ok & (~b_ok)))  # A right, B wrong
    c = int(np.sum((~a_ok) & b_ok))  # A wrong, B right
    n_disc = b + c
    if n_disc == 0:
        method, stat, p_val = "none (b+c=0)", 0.0, 1.0
    elif n_disc < 25:
        method = "exact_binomial"
        stat = float(min(b, c))
        p_val = float(binomtest(min(b, c), n_disc, 0.5).pvalue)
    else:
        method = "continuity_corrected_chi2"
        stat = float(((abs(b - c) - 1.0) ** 2) / n_disc)
        p_val = float(chi2.sf(stat, df=1))
    return {"b_A_right_B_wrong": b, "c_A_wrong_B_right": c, "discordant": n_disc, "method": method, "stat": stat, "p_raw": p_val}


def holm_bonferroni(p_vals: list[float]) -> list[float]:
    m = len(p_vals)
    order = np.argsort(p_vals)
    adjusted = np.empty(m, dtype=float)
    running_max = 0.0
    for rank, idx in enumerate(order):
        val = min(1.0, (m - rank) * p_vals[idx])
        running_max = max(running_max, val)
        adjusted[idx] = running_max
    return adjusted.tolist()


def categorize_error(text: str, pred: int, truth: int) -> str:
    tokens = str(text).lower().split()
    tok_set = set(tokens)
    has_neg = bool(tok_set & NEGATION_TRIGGERS)
    has_contrast = bool(tok_set & {"but", "however", "though", "although", "yet"})
    has_pos = bool(tok_set & {"good", "great", "best", "love", "happy", "awesome", "nice", "proud", "excellent"})
    has_sarcasm_cue = any(p in str(text).lower() for p in ("yeah right", "haha", "lol", "sure ", "great job"))
    if has_sarcasm_cue:
        return "possible_sarcasm_or_irony"
    if has_neg and has_pos:
        return "negated_positive_or_mixed"
    if has_contrast:
        return "contrastive_clause"
    if has_neg:
        return "negation_scope"
    if len(tokens) <= 5:
        return "short_ambiguous_text"
    return "domain_or_context_nuance"


def main() -> None:
    started_utc = datetime.now(timezone.utc).isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "t1_confusion_matrices").mkdir(exist_ok=True)
    (OUT_DIR / "t2_confusion_matrices").mkdir(exist_ok=True)

    # 1. Pre-evaluation verification
    freeze = json.loads((EXPERIMENTS / "freeze_manifest.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

    for art in freeze["allowed_artifacts_for_step4B"]:
        mp = ROOT / art["model_path"]
        assert mp.is_file(), f"Missing frozen model: {mp}"
        assert sha256_file(mp) == art["model_sha256"], f"Model SHA-256 mismatch: {art['experiment_id']}"
        if "config_path" in art:
            cp = ROOT / art["config_path"]
            assert sha256_file(cp) == art["config_sha256"], f"Config SHA-256 mismatch: {art['experiment_id']}"

    t1_info = manifest["datasets"]["political_test_T1"]
    t2_info = manifest["datasets"]["s140_test_T2_60k"]
    t1_path = ROOT / t1_info["path"]
    t2_path = ROOT / t2_info["path"]
    t1_sha = sha256_file(t1_path)
    t2_sha = sha256_file(t2_path)
    assert t1_sha == t1_info["sha256"], "T1 SHA-256 mismatch!"
    assert t2_sha == t2_info["sha256"], "T2 SHA-256 mismatch!"

    t1_df = pd.read_csv(t1_path)
    t2_df = pd.read_csv(t2_path)
    assert len(t1_df) == 39210 and len(t2_df) == 60000

    # Prepare text variants once
    t1_v3 = t1_df["text_v3"].fillna("")
    t1_v4 = t1_df["text"].fillna("")
    t1_neg = t1_v4.map(add_negation_features)

    t2_v3 = t2_df["text_raw"].fillna("").map(normalize_v3)
    t2_v4 = t2_df["text"].fillna("")
    t2_neg = t2_v4.map(add_negation_features)

    y_t1 = t1_df["label"].to_numpy(dtype=int)
    y_t2 = t2_df["label"].to_numpy(dtype=int)

    # 2. Evaluate all 14 frozen models on T1 and T2
    t1_rows, t2_rows = [], []
    t1_scores_map, t1_preds_map = {}, {}
    t2_scores_map, t2_preds_map = {}, {}
    t1_by_source_rows = []

    for art in freeze["allowed_artifacts_for_step4B"]:
        eid = art["experiment_id"]
        prep = art["preprocessing_version"]
        thr = float(art["threshold"])
        loaded = joblib.load(ROOT / art["model_path"])
        pipe = loaded["pipeline"]

        if "v3" in prep:
            x1, x2 = t1_v3, t2_v3
        elif "negation" in prep:
            x1, x2 = t1_neg, t2_neg
        else:
            x1, x2 = t1_v4, t2_v4

        t_a = time.perf_counter()
        sc1 = pipe.decision_function(x1)
        t1_sec = time.perf_counter() - t_a

        t_b = time.perf_counter()
        sc2 = pipe.decision_function(x2)
        t2_sec = time.perf_counter() - t_b

        m1, p1 = compute_full_metrics(y_t1, sc1, thr)
        m2, p2 = compute_full_metrics(y_t2, sc2, thr)

        t1_scores_map[eid], t1_preds_map[eid] = sc1, p1
        t2_scores_map[eid], t2_preds_map[eid] = sc2, p2

        # Save confusion matrices
        (OUT_DIR / "t1_confusion_matrices" / f"{eid}.json").write_text(
            json.dumps({"model": eid, "tn": m1["tn"], "fp": m1["fp"], "fn": m1["fn"], "tp": m1["tp"], "classification_report": m1["classification_report"]}, indent=2),
            encoding="utf-8",
        )
        (OUT_DIR / "t2_confusion_matrices" / f"{eid}.json").write_text(
            json.dumps({"model": eid, "tn": m2["tn"], "fp": m2["fp"], "fn": m2["fn"], "tp": m2["tp"], "classification_report": m2["classification_report"]}, indent=2),
            encoding="utf-8",
        )

        base_row = {"model": eid, "preprocessing_version": prep, "model_sha256": art["model_sha256"]}
        t1_rows.append({**base_row, **{k: v for k, v in m1.items() if k != "classification_report"}, "infer_time_sec": round(t1_sec, 4)})
        t2_rows.append({**base_row, **{k: v for k, v in m2.items() if k != "classification_report"}, "infer_time_sec": round(t2_sec, 4)})

        # T1 breakdown by Twitter vs Reddit
        for src_name, mask in t1_df.groupby("source").groups.items():
            idx_s = np.array(list(mask))
            ms, _ = compute_full_metrics(y_t1[idx_s], sc1[idx_s], thr)
            t1_by_source_rows.append({
                "model": eid, "source": src_name, "n": ms["n_evaluated"],
                "precision_class1": ms["precision_class1"], "recall_class1": ms["recall_class1"],
                "f1_class1": ms["f1_class1"], "pr_auc_class1": ms["pr_auc_class1"], "accuracy": ms["accuracy"],
            })
        print(f"Evaluated {eid}: T1 F1={m1['f1_class1']:.4f} (PR-AUC={m1['pr_auc_class1']:.4f}) | T2 F1={m2['f1_class1']:.4f}", flush=True)

    pd.DataFrame(t1_rows).to_csv(OUT_DIR / "t1_metrics_all_models.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(t2_rows).to_csv(OUT_DIR / "t2_metrics_all_models.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(t1_by_source_rows).to_csv(OUT_DIR / "t1_metrics_by_source.csv", index=False, encoding="utf-8-sig")

    # 3. Bootstrap CIs (1000 iterations, seed=42)
    print("\nRunning 1000-iteration Bootstrap on T1 and T2...", flush=True)
    b_t1, ci_t1 = bootstrap_metrics(y_t1, t1_scores_map, t1_preds_map)
    b_t2, ci_t2 = bootstrap_metrics(y_t2, t2_scores_map, t2_preds_map)
    pd.DataFrame(ci_t1).to_csv(OUT_DIR / "bootstrap_ci_t1.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ci_t2).to_csv(OUT_DIR / "bootstrap_ci_t2.csv", index=False, encoding="utf-8-sig")

    # 4. Paired Bootstrap & McNemar + Holm on key pairs
    pairs = [
        ("E1a", "E0-Train"),
        ("E1b", "E0-Train"),
        ("E1b", "E1a"),
        ("E2", "E1b"),
        ("E2w", "E2"),
        ("E3", "E2w"),
        ("E4a", "E2w"),
        ("E4b", "E2w"),
        ("E5b", "E5a"),
        ("E6-120k", "E6-50k"),
        ("E6-400k", "E6-120k"),
        ("E1b", "E0-Artifact"),
        ("E2w", "E0-Artifact"),
        ("E3", "E0-Artifact"),
        ("E4b", "E0-Artifact"),
        ("E5b", "E0-Artifact"),
    ]

    for ds_name, y_ds, b_arrs, p_map, pb_file, mc_file in [
        ("T1", y_t1, b_t1, t1_preds_map, "paired_bootstrap_t1.csv", "mcnemar_t1.csv"),
        ("T2", y_t2, b_t2, t2_preds_map, "paired_bootstrap_t2.csv", "mcnemar_t2.csv"),
    ]:
        pb_rows, mc_rows = [], []
        for a, b in pairs:
            pb = {"model_A": a, "model_B": b}
            for met in ("precision", "recall", "f1", "pr_auc"):
                diff = b_arrs[a][met] - b_arrs[b][met]
                lo, hi = np.percentile(diff, [2.5, 97.5])
                pb[f"delta_{met}_mean"] = float(np.mean(diff))
                pb[f"delta_{met}_ci95_low"] = float(lo)
                pb[f"delta_{met}_ci95_high"] = float(hi)
            pb_rows.append(pb)

            mc = mcnemar_test(y_ds, p_map[a], p_map[b])
            mc_rows.append({"model_A": a, "model_B": b, **mc})

        p_holm = holm_bonferroni([r["p_raw"] for r in mc_rows])
        for r, ph in zip(mc_rows, p_holm):
            r["n_comparisons"] = len(mc_rows)
            r["p_holm"] = float(ph)
            r["significant_holm_0_05"] = bool(ph < 0.05)

        pd.DataFrame(pb_rows).to_csv(OUT_DIR / pb_file, index=False, encoding="utf-8-sig")
        pd.DataFrame(mc_rows).to_csv(OUT_DIR / mc_file, index=False, encoding="utf-8-sig")

    # 5. Error Analysis on T1 and T2 (focus on E0-Artifact, E1b, E3, E5b)
    def build_errors(df: pd.DataFrame, y_true: np.ndarray, scores_map: dict, preds_map: dict, has_source: bool) -> pd.DataFrame:
        rows = []
        for mid in ("E0-Artifact", "E1b", "E3", "E5b"):
            yp = preds_map[mid]
            sc = scores_map[mid]
            err_idx = np.where(yp != y_true)[0]
            # Sample up to 150 FP and 150 FN deterministically
            fp_idx = [i for i in err_idx if yp[i] == 1][:150]
            fn_idx = [i for i in err_idx if yp[i] == 0][:150]
            for i in fp_idx + fn_idx:
                txt = str(df.iloc[i]["text"])
                rows.append({
                    "model": mid,
                    "row_index": int(i),
                    "source": str(df.iloc[i]["source"]) if has_source else "sentiment140",
                    "truth": int(y_true[i]),
                    "predicted": int(yp[i]),
                    "decision_score": float(sc[i]),
                    "error_type": "FP" if yp[i] == 1 else "FN",
                    "error_category": categorize_error(txt, int(yp[i]), int(y_true[i])),
                    "text": txt,
                })
        return pd.DataFrame(rows)

    err_t1 = build_errors(t1_df, y_t1, t1_scores_map, t1_preds_map, has_source=True)
    err_t2 = build_errors(t2_df, y_t2, t2_scores_map, t2_preds_map, has_source=False)
    err_t1.to_csv(OUT_DIR / "error_analysis_t1.csv", index=False, encoding="utf-8-sig")
    err_t2.to_csv(OUT_DIR / "error_analysis_t2.csv", index=False, encoding="utf-8-sig")

    # 6. Save evaluation_protocol.json and evaluation_manifest.json
    finished_utc = datetime.now(timezone.utc).isoformat()
    protocol = {
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "seed": SEED,
        "bootstrap_iterations": N_BOOT,
        "ci_method": "percentile [2.5, 97.5] with shared resample indices per dataset",
        "mcnemar_method": "exact_binomial if b+c < 25 else continuity_corrected_chi2; Holm-Bonferroni across m=16 pairs",
        "environment": {
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "joblib": joblib.__version__,
        },
        "test_sets": {
            "T1": {"path": t1_info["path"], "rows": len(t1_df), "sha256": t1_sha},
            "T2": {"path": t2_info["path"], "rows": len(t2_df), "sha256": t2_sha},
        },
    }
    (OUT_DIR / "evaluation_protocol.json").write_text(json.dumps(protocol, indent=2, ensure_ascii=False), encoding="utf-8")

    eval_manifest = {
        "created_utc": finished_utc,
        "freeze_manifest_sha256": sha256_file(EXPERIMENTS / "freeze_manifest.json"),
        "t1_sha256": t1_sha,
        "t2_sha256": t2_sha,
        "models_evaluated": [a["experiment_id"] for a in freeze["allowed_artifacts_for_step4B"]],
        "output_files_sha256": {
            p.name: sha256_file(p)
            for p in sorted(OUT_DIR.iterdir())
            if p.is_file()
        },
    }
    (OUT_DIR / "evaluation_manifest.json").write_text(json.dumps(eval_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nPhase 5 evaluation artifacts saved successfully!", flush=True)


if __name__ == "__main__":
    main()
