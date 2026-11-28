"""Phase 4A: Controlled Training, Tuning & Validation Evaluation (E0-Train through E6).

STRICT INVARIANTS:
- NEVER opens, loads, or evaluates political_test_T1.csv or s140_test_T2_60k.csv.
- NEVER modifies baseline_v3/, predict.py, UI, data/splits/, or SQL Server.
- All hyperparameter & threshold selections happen ONLY on political_val.csv.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from preprocessing_v4 import PREPROCESSING_VERSION, normalize_text as normalize_v4  # noqa: E402
from negation_feature import (  # noqa: E402
    NEGATION_STOPWORDS,
    NEGATION_TRIGGERS,
    add_negation_features,
)

# Read-only import of baseline_v3 normalize_text for E0-Train S140 validation monitoring
sys.path.insert(0, str(ROOT / "baseline_v3"))
from predict import PREPROCESSING_VERSION as V3_PREP_VERSION, normalize_text as normalize_v3  # noqa: E402

SPLITS = ROOT / "data" / "splits"
EXPERIMENTS = ROOT / "experiments"
MANIFEST_PATH = ROOT / "manifest.json"
SEED = 42


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def choose_threshold(scores: np.ndarray, labels: np.ndarray, beta: float = 1.0) -> tuple[float, float]:
    """Choose binary decision threshold using validation only (matches Cell 27 tie-break)."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    candidates = np.unique(np.r_[0.0, np.quantile(scores, np.linspace(0, 1, 501))])
    if beta == 1.0:
        score_fn = lambda yt, yp: float(f1_score(yt, yp, pos_label=1, zero_division=0))
    else:
        score_fn = lambda yt, yp: float(fbeta_score(yt, yp, beta=beta, pos_label=1, zero_division=0))
    best = (score_fn(labels, scores > 0.0), 0.0)
    for thr in candidates:
        val = score_fn(labels, scores > thr)
        if val > best[0] + 1e-12 or (abs(val - best[0]) <= 1e-12 and abs(thr) < abs(best[1])):
            best = (val, float(thr))
    return best[1], best[0]


def compute_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    y_true = np.asarray(y_true, dtype=int)
    scores = np.asarray(scores, dtype=float)
    y_pred = (scores > threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = (int(x) for x in cm.ravel())
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    return {
        "n_evaluated": int(len(y_true)),
        "n_skipped": 0,
        "pos_count": int(y_true.sum()),
        "neg_count": int((1 - y_true).sum()),
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_class1": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall_class1": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1_class1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f2_class1": float(fbeta_score(y_true, y_pred, beta=2.0, pos_label=1, zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "pr_auc_class1": float(average_precision_score(y_true, scores)),
        "specificity": specificity,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def make_word_pipeline(C: float = 1.0, class_weight=None) -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), min_df=2,
            max_features=40000, sublinear_tf=True, dtype=np.float32,
        )),
        ("classifier", LinearSVC(C=C, class_weight=class_weight, max_iter=3000, random_state=SEED)),
    ])


def make_char_pipeline(C: float = 1.0, class_weight=None) -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), min_df=3,
            max_features=80000, sublinear_tf=True, dtype=np.float32,
        )),
        ("classifier", LinearSVC(C=C, class_weight=class_weight, max_iter=3000, random_state=SEED)),
    ])


def make_union_pipeline(C: float = 1.0, class_weight=None) -> Pipeline:
    union = FeatureUnion([
        ("word", TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), min_df=2,
            max_features=40000, sublinear_tf=True, dtype=np.float32,
        )),
        ("char", TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), min_df=3,
            max_features=80000, sublinear_tf=True, dtype=np.float32,
        )),
    ])
    return Pipeline([
        ("features", union),
        ("classifier", LinearSVC(C=C, class_weight=class_weight, max_iter=3000, random_state=SEED)),
    ])


def load_existing_record(exp_id: str) -> dict | None:
    exp_dir = EXPERIMENTS / exp_id
    cfg_p = exp_dir / "config.json"
    vm_p = exp_dir / "val_metrics.json"
    mod_p = exp_dir / "model.joblib"
    if not (cfg_p.is_file() and vm_p.is_file() and mod_p.is_file()):
        return None
    cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
    vm = json.loads(vm_p.read_text(encoding="utf-8"))
    return {
        "experiment_id": exp_id,
        "model_path": str(mod_p.relative_to(ROOT)).replace("\\", "/"),
        "config_path": str(cfg_p.relative_to(ROOT)).replace("\\", "/"),
        "model_sha256": cfg["model_sha256"],
        "config_sha256": sha256_file(cfg_p),
        "threshold": float(cfg["threshold"]),
        "threshold_objective": cfg["threshold_objective"],
        "preprocessing_version": cfg["preprocessing_version"],
        "pol_val": vm["political_val"],
        "s140_val": vm["s140_val"],
        "train_time_sec": cfg["train_time_sec"],
        "infer_time_sec": cfg["infer_time_sec"],
        "_config": cfg,
        "_tuning": vm.get("tuning_details"),
    }


def load_existing_record(exp_id: str) -> dict | None:
    exp_dir = EXPERIMENTS / exp_id
    cfg_p = exp_dir / "config.json"
    val_p = exp_dir / "val_metrics.json"
    mod_p = exp_dir / "model.joblib"
    if cfg_p.is_file() and val_p.is_file() and mod_p.is_file():
        cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
        val = json.loads(val_p.read_text(encoding="utf-8"))
        return {
            "experiment_id": exp_id,
            "model_path": str(mod_p.relative_to(ROOT)).replace("\\", "/"),
            "config_path": str(cfg_p.relative_to(ROOT)).replace("\\", "/"),
            "model_sha256": cfg["model_sha256"],
            "config_sha256": sha256_file(cfg_p),
            "threshold": float(cfg["threshold"]),
            "threshold_objective": cfg["threshold_objective"],
            "preprocessing_version": cfg["preprocessing_version"],
            "pol_val": val["political_val"],
            "s140_val": val["s140_val"],
            "train_time_sec": cfg["train_time_sec"],
            "infer_time_sec": cfg["infer_time_sec"],
            "_cfg": cfg,
            "_val": val,
        }
    return None


def save_experiment(
    exp_id: str,
    pipeline: Pipeline,
    config: dict,
    pol_val_df: pd.DataFrame,
    pol_val_scores: np.ndarray,
    pol_val_metrics: dict,
    s140_val_metrics: dict,
    log_lines: list[str],
    extra_val_data: dict | None = None,
) -> dict:
    exp_dir = EXPERIMENTS / exp_id
    if exp_dir.exists():
        raise FileExistsError(f"Experiment directory already exists (no-overwrite rule): {exp_dir}")
    exp_dir.mkdir(parents=True, exist_ok=False)

    model_path = exp_dir / "model.joblib"
    artifact = {
        "experiment_id": exp_id,
        "pipeline": pipeline,
        "task": "binary",
        "class_names": {0: "Không tiêu cực", 1: "Tiêu cực"},
        "threshold": float(config["threshold"]),
        "threshold_objective": config["threshold_objective"],
        "preprocessing_version": config["preprocessing_version"],
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "seed": SEED,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    joblib.dump(artifact, model_path, compress=3)
    model_sha = sha256_file(model_path)
    config["model_sha256"] = model_sha

    config_path = exp_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    config_sha = sha256_file(config_path)

    val_payload = {
        "experiment_id": exp_id,
        "political_val": pol_val_metrics,
        "s140_val": s140_val_metrics,
    }
    if extra_val_data:
        val_payload["tuning_details"] = extra_val_data
    val_path = exp_dir / "val_metrics.json"
    val_path.write_text(json.dumps(val_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Save Validation error samples (political_val ONLY, max 200 rows)
    thr = float(config["threshold"])
    y_pred = (pol_val_scores > thr).astype(int)
    err_mask = y_pred != pol_val_df["label"].to_numpy()
    err_df = pol_val_df.loc[err_mask, ["source", "text", "label"]].copy()
    err_df["predicted_label"] = y_pred[err_mask]
    err_df["decision_score"] = pol_val_scores[err_mask]
    err_df["error_type"] = np.where(err_df["predicted_label"] == 1, "FP", "FN")
    err_df.head(200).to_csv(exp_dir / "error_samples.csv", index=False, encoding="utf-8-sig")

    (exp_dir / "artifact_sha256.txt").write_text(f"{model_sha}  model.joblib\n{config_sha}  config.json\n", encoding="utf-8")
    (exp_dir / "training_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    return {
        "experiment_id": exp_id,
        "model_path": str(model_path.relative_to(ROOT)).replace("\\", "/"),
        "config_path": str(config_path.relative_to(ROOT)).replace("\\", "/"),
        "model_sha256": model_sha,
        "config_sha256": config_sha,
        "threshold": float(config["threshold"]),
        "threshold_objective": config["threshold_objective"],
        "preprocessing_version": config["preprocessing_version"],
        "pol_val": pol_val_metrics,
        "s140_val": s140_val_metrics,
        "train_time_sec": config["train_time_sec"],
        "infer_time_sec": config["infer_time_sec"],
    }


def pre_run_checks() -> dict:
    """Section 2.3: Verify manifest hashes, row counts, labels, preprocessing, and E3 tests."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    allowed_keys = [
        "political_train", "political_val",
        "s140_train_400k", "s140_val_60k",
        "s140_train_e6_50k", "s140_train_e6_120k",
    ]
    loaded = {}
    for k in allowed_keys:
        info = manifest["datasets"][k]
        p = ROOT / info["path"]
        assert p.is_file(), f"Missing split: {p}"
        actual_sha = sha256_file(p)
        assert actual_sha == info["sha256"], f"SHA-256 mismatch for {k}: {actual_sha} != {info['sha256']}"
        df = pd.read_csv(p)
        assert len(df) == info["rows"], f"Row count mismatch for {k}: {len(df)} != {info['rows']}"
        assert set(df["label"].unique()).issubset({0, 1}), f"Invalid labels in {k}"
        assert (df["preprocessing_version"] == PREPROCESSING_VERSION).all(), f"Prep version mismatch in {k}"
        loaded[k] = df

    # Run E3 negation 30-sentence test suite
    res = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "test_negation_e3.py")],
        capture_output=True, text=True, check=True,
    )
    assert "ALL 30 E3 NEGATION TESTS PASSED!" in res.stdout, "E3 negation tests failed!"
    print("Pre-run checks PASSED (all Train/Val SHA-256, row counts, labels, v4 prep, and 30 E3 tests).")
    return loaded


def fit_and_eval(
    pipe: Pipeline,
    train_texts,
    train_labels,
    pol_val_texts,
    pol_val_labels,
    s140_val_texts,
    s140_val_labels,
    sample_weight=None,
    beta: float = 1.0,
    fixed_threshold: float | None = None,
) -> tuple[Pipeline, np.ndarray, np.ndarray, float, dict, dict, float, float]:
    t0 = time.perf_counter()
    if sample_weight is not None:
        pipe.fit(train_texts, train_labels, classifier__sample_weight=sample_weight)
    else:
        pipe.fit(train_texts, train_labels)
    train_sec = time.perf_counter() - t0

    t1 = time.perf_counter()
    pol_scores = pipe.decision_function(pol_val_texts)
    s140_scores = pipe.decision_function(s140_val_texts)
    infer_sec = time.perf_counter() - t1

    if fixed_threshold is None:
        thr, _ = choose_threshold(pol_scores, pol_val_labels, beta=beta)
    else:
        thr = float(fixed_threshold)

    pol_m = compute_metrics(pol_val_labels, pol_scores, thr)
    s140_m = compute_metrics(s140_val_labels, s140_scores, thr)
    return pipe, pol_scores, s140_scores, thr, pol_m, s140_m, train_sec, infer_sec


def env_info() -> dict:
    return {
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "joblib": joblib.__version__,
    }


def main() -> None:
    data = pre_run_checks()
    pol_tr = data["political_train"]
    pol_va = data["political_val"]
    s_tr_400 = data["s140_train_400k"]
    s_va_60 = data["s140_val_60k"]
    s_tr_50 = data["s140_train_e6_50k"]
    s_tr_120 = data["s140_train_e6_120k"]

    # Prepare S140 Validation with v3 normalization for E0-Train only
    s_va_v3_texts = s_va_60["text_raw"].map(normalize_v3)
    pol_tr_v3 = pd.read_csv(ROOT / "baseline_v3" / "splits" / "binary" / "train.csv")
    pol_va_v3 = pd.read_csv(ROOT / "baseline_v3" / "splits" / "binary" / "validation.csv")

    records: list[dict] = []
    env = env_info()

    # 1. E0-Train (historical reproduction on political_train with v3)
    print("\n--- Running E0-Train ---")
    existing = load_existing_record("E0-Train")
    if existing:
        print("  Loaded existing E0-Train.")
        records.append(existing)
    else:
        pipe = make_word_pipeline(C=1.0, class_weight=None)
        pipe, pol_sc, _, thr, pol_m, s140_m, tr_s, inf_s = fit_and_eval(
            pipe, pol_tr_v3["text"], pol_tr_v3["label"],
            pol_va_v3["text"], pol_va_v3["label"],
            s_va_v3_texts, s_va_60["label"], beta=1.0,
        )
        records.append(save_experiment(
            "E0-Train", pipe,
            {
                "experiment_id": "E0-Train", "preprocessing_version": V3_PREP_VERSION,
                "train_datasets": ["baseline_v3/splits/binary/train.csv (133314)"],
                "val_datasets": ["baseline_v3/splits/binary/validation.csv (23526)", "s140_val_60k (v3-norm)"],
                "vectorizer": {"type": "TfidfVectorizer", "ngram_range": [1, 2], "min_df": 2, "max_features": 40000, "sublinear_tf": True},
                "model": {"type": "LinearSVC", "C": 1.0, "class_weight": None, "max_iter": 3000, "random_state": SEED},
                "sample_weight": "uniform (1.0)", "threshold": thr, "threshold_objective": "F1_class1 (political_val)",
                "seed": SEED, "train_time_sec": round(tr_s, 3), "infer_time_sec": round(inf_s, 3), "env": env,
            },
            pol_va_v3, pol_sc, pol_m, s140_m,
            [f"E0-Train reproduced on baseline_v3/train.csv ({len(pol_tr_v3)} rows), thr={thr:.6f}, pol_val F1={pol_m['f1_class1']:.4f}"],
        ))
    print(f"E0-Train pol_val F1={records[-1]['pol_val']['f1_class1']:.4f}")

    # 2. E1a (preprocessing v4, C=1.0 fixed)
    print("\n--- Running E1a ---")
    existing = load_existing_record("E1a")
    if existing:
        print("  Loaded existing E1a.")
        records.append(existing)
    else:
        pipe = make_word_pipeline(C=1.0, class_weight=None)
        pipe, pol_sc, _, thr, pol_m, s140_m, tr_s, inf_s = fit_and_eval(
            pipe, pol_tr["text"], pol_tr["label"],
            pol_va["text"], pol_va["label"],
            s_va_60["text"], s_va_60["label"], beta=1.0,
        )
        records.append(save_experiment(
            "E1a", pipe,
            {
                "experiment_id": "E1a", "base_experiment": "E0-Train", "preprocessing_version": PREPROCESSING_VERSION,
                "train_datasets": ["data/splits/political_train.csv (133314)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "vectorizer": {"type": "TfidfVectorizer", "ngram_range": [1, 2], "min_df": 2, "max_features": 40000, "sublinear_tf": True},
                "model": {"type": "LinearSVC", "C": 1.0, "class_weight": None, "max_iter": 3000, "random_state": SEED},
                "sample_weight": "uniform (1.0)", "threshold": thr, "threshold_objective": "F1_class1 (political_val)",
                "seed": SEED, "train_time_sec": round(tr_s, 3), "infer_time_sec": round(inf_s, 3), "env": env,
            },
            pol_va, pol_sc, pol_m, s140_m,
            [f"E1a (v4, C=1.0): thr={thr:.6f}, pol_val F1={pol_m['f1_class1']:.4f}"],
        ))
    print(f"E1a pol_val F1={records[-1]['pol_val']['f1_class1']:.4f}")

    # 3. E1b (tune C in {0.25, 0.5, 1.0, 2.0} on political_val)
    print("\n--- Running E1b ---")
    existing = load_existing_record("E1b")
    if existing:
        print("  Loaded existing E1b.")
        records.append(existing)
        best_c_val = float(existing["_config"]["model"]["C"])
    else:
        e1b_candidates = {}
        for c_val in (0.25, 0.5, 1.0, 2.0):
            p_c = make_word_pipeline(C=c_val, class_weight=None)
            p_c, p_sc, _, t_c, pm_c, sm_c, tr_c, inf_c = fit_and_eval(
                p_c, pol_tr["text"], pol_tr["label"],
                pol_va["text"], pol_va["label"],
                s_va_60["text"], s_va_60["label"], beta=1.0,
            )
            e1b_candidates[str(c_val)] = {"threshold": t_c, "political_val": pm_c, "s140_val": sm_c, "train_time_sec": round(tr_c, 3)}
            print(f"  C={c_val}: pol_val F1={pm_c['f1_class1']:.4f}, PR-AUC={pm_c['pr_auc_class1']:.4f}")
        best_c = max(e1b_candidates, key=lambda k: e1b_candidates[k]["political_val"]["f1_class1"])
        best_c_val = float(best_c)
        p_c, p_sc, _, t_c, pm_c, sm_c, tr_c, inf_c = fit_and_eval(
            make_word_pipeline(C=best_c_val, class_weight=None),
            pol_tr["text"], pol_tr["label"], pol_va["text"], pol_va["label"], s_va_60["text"], s_va_60["label"], beta=1.0,
        )
        records.append(save_experiment(
            "E1b", p_c,
            {
                "experiment_id": "E1b", "base_experiment": "E1a", "preprocessing_version": PREPROCESSING_VERSION,
                "train_datasets": ["data/splits/political_train.csv (133314)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "vectorizer": {"type": "TfidfVectorizer", "ngram_range": [1, 2], "min_df": 2, "max_features": 40000, "sublinear_tf": True},
                "model": {"type": "LinearSVC", "C": best_c_val, "C_candidates": [0.25, 0.5, 1.0, 2.0], "class_weight": None, "max_iter": 3000, "random_state": SEED},
                "sample_weight": "uniform (1.0)", "threshold": t_c, "threshold_objective": "F1_class1 (political_val)",
                "seed": SEED, "train_time_sec": round(tr_c, 3), "infer_time_sec": round(inf_c, 3), "env": env,
            },
            pol_va, p_sc, pm_c, sm_c,
            [f"E1b selected C={best_c_val}, thr={t_c:.6f}, pol_val F1={pm_c['f1_class1']:.4f}"],
            extra_val_data=e1b_candidates,
        ))
    print(f"E1b best C={best_c_val}: pol_val F1={records[-1]['pol_val']['f1_class1']:.4f}")

    # Combined 533,314 train set for E2, E2w, E3, E4
    comb_texts = pd.concat([pol_tr["text"], s_tr_400["text"]], ignore_index=True)
    comb_labels = pd.concat([pol_tr["label"], s_tr_400["label"]], ignore_index=True)
    n_pol, n_s140 = len(pol_tr), len(s_tr_400)

    # 4. E2 (Political + 400k S140, uniform weight, C from E1b)
    print("\n--- Running E2 ---")
    existing = load_existing_record("E2")
    if existing:
        print("  Loaded existing E2.")
        records.append(existing)
        e2_pm = existing["pol_val"]
        e2_thr = existing["threshold"]
    else:
        e2_pipe, e2_sc, _, e2_thr, e2_pm, e2_sm, tr_s, inf_s = fit_and_eval(
            make_word_pipeline(C=best_c_val, class_weight=None),
            comb_texts, comb_labels, pol_va["text"], pol_va["label"], s_va_60["text"], s_va_60["label"], beta=1.0,
        )
        records.append(save_experiment(
            "E2", e2_pipe,
            {
                "experiment_id": "E2", "base_experiment": "E1b", "preprocessing_version": PREPROCESSING_VERSION,
                "train_datasets": ["data/splits/political_train.csv (133314)", "data/splits/s140_train_400k.csv (400000)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "vectorizer": {"type": "TfidfVectorizer", "ngram_range": [1, 2], "min_df": 2, "max_features": 40000, "sublinear_tf": True},
                "model": {"type": "LinearSVC", "C": best_c_val, "class_weight": None, "max_iter": 3000, "random_state": SEED},
                "sample_weight": {"r": 1.0, "w_pol": 1.0, "w_s140": 1.0, "total_w_pol": n_pol, "total_w_s140": n_s140},
                "threshold": e2_thr, "threshold_objective": "F1_class1 (political_val)",
                "seed": SEED, "train_time_sec": round(tr_s, 3), "infer_time_sec": round(inf_s, 3), "env": env,
            },
            pol_va, e2_sc, e2_pm, e2_sm,
            [f"E2 (C={best_c_val}, +400k S140): thr={e2_thr:.6f}, pol_val F1={e2_pm['f1_class1']:.4f}, s140_val F1={e2_sm['f1_class1']:.4f}"],
        ))
    print(f"E2 pol_val F1={e2_pm['f1_class1']:.4f}, thr={e2_thr:.4f}")

    # 5. E2w (Source weighting r in {0.15, 0.25, 0.33, 0.50, 1.0}, mean(w)=1.0, C fixed as E2)
    print("\n--- Running E2w ---")
    existing = load_existing_record("E2w")
    if existing:
        print("  Loaded existing E2w.")
        records.append(existing)
        pm_w = existing["pol_val"]
        best_r_info = existing["_config"]["sample_weight"]
        best_r = float(best_r_info["selected_r"])
        best_sw = np.concatenate([
            np.full(n_pol, best_r_info["w_pol"], dtype=np.float64),
            np.full(n_s140, best_r_info["w_s140"], dtype=np.float64),
        ])
    else:
        e2w_candidates = {}
        for r in (0.15, 0.25, 0.33, 0.50, 1.0):
            k = (n_pol + n_s140) / (n_pol + r * n_s140)
            w_pol = k
            w_s140 = r * k
            sw = np.concatenate([np.full(n_pol, w_pol, dtype=np.float64), np.full(n_s140, w_s140, dtype=np.float64)])
            assert abs(sw.mean() - 1.0) < 1e-9
            tot_pol = float(n_pol * w_pol)
            tot_s140 = float(n_s140 * w_s140)
            tot_all = tot_pol + tot_s140

            p_w, sc_w, _, t_w, pm_w_i, sm_w_i, tr_w, inf_w = fit_and_eval(
                make_word_pipeline(C=best_c_val, class_weight=None),
                comb_texts, comb_labels, pol_va["text"], pol_va["label"], s_va_60["text"], s_va_60["label"],
                sample_weight=sw, beta=1.0,
            )
            e2w_candidates[str(r)] = {
                "r": r, "w_pol": w_pol, "w_s140": w_s140,
                "total_weight_pol": tot_pol, "total_weight_s140": tot_s140,
                "share_pol_pct": round(100.0 * tot_pol / tot_all, 2),
                "share_s140_pct": round(100.0 * tot_s140 / tot_all, 2),
                "threshold": t_w, "political_val": pm_w_i, "s140_val": sm_w_i, "train_time_sec": round(tr_w, 3),
            }
            print(f"  r={r}: w_pol={w_pol:.4f}, w_s140={w_s140:.4f} (share Pol={100*tot_pol/tot_all:.1f}%), pol_val F1={pm_w_i['f1_class1']:.4f}, s140_val F1={sm_w_i['f1_class1']:.4f}")

        best_r_key = max(e2w_candidates, key=lambda k: e2w_candidates[k]["political_val"]["f1_class1"])
        best_r_info = e2w_candidates[best_r_key]
        best_r = float(best_r_key)
        best_sw = np.concatenate([
            np.full(n_pol, best_r_info["w_pol"], dtype=np.float64),
            np.full(n_s140, best_r_info["w_s140"], dtype=np.float64),
        ])
        p_w, sc_w, _, t_w, pm_w, sm_w, tr_w, inf_w = fit_and_eval(
            make_word_pipeline(C=best_c_val, class_weight=None),
            comb_texts, comb_labels, pol_va["text"], pol_va["label"], s_va_60["text"], s_va_60["label"],
            sample_weight=best_sw, beta=1.0,
        )
        records.append(save_experiment(
            "E2w", p_w,
            {
                "experiment_id": "E2w", "base_experiment": "E2", "preprocessing_version": PREPROCESSING_VERSION,
                "train_datasets": ["data/splits/political_train.csv (133314)", "data/splits/s140_train_400k.csv (400000)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "vectorizer": {"type": "TfidfVectorizer", "ngram_range": [1, 2], "min_df": 2, "max_features": 40000, "sublinear_tf": True},
                "model": {"type": "LinearSVC", "C": best_c_val, "class_weight": None, "max_iter": 3000, "random_state": SEED},
                "sample_weight": {
                    "selected_r": best_r, "w_pol": best_r_info["w_pol"], "w_s140": best_r_info["w_s140"],
                    "total_weight_pol": best_r_info["total_weight_pol"], "total_weight_s140": best_r_info["total_weight_s140"],
                    "share_pol_pct": best_r_info["share_pol_pct"], "share_s140_pct": best_r_info["share_s140_pct"],
                },
                "threshold": t_w, "threshold_objective": "F1_class1 (political_val)",
                "seed": SEED, "train_time_sec": round(tr_w, 3), "infer_time_sec": round(inf_w, 3), "env": env,
            },
            pol_va, sc_w, pm_w, sm_w,
            [f"E2w best r={best_r}: pol_val F1={pm_w['f1_class1']:.4f}, s140_val F1={sm_w['f1_class1']:.4f}"],
            extra_val_data=e2w_candidates,
        ))

    # Determine selected base between E2 and E2w
    if pm_w["f1_class1"] >= e2_pm["f1_class1"] and best_r != 1.0:
        base_id = "E2w"
        base_sw = best_sw
        base_sw_desc = records[-1]["pol_val"] and {
            "selected_r": best_r, "w_pol": best_r_info["w_pol"], "w_s140": best_r_info["w_s140"],
        }
    else:
        base_id = "E2"
        base_sw = None
        base_sw_desc = {"r": 1.0, "w_pol": 1.0, "w_s140": 1.0}
    print(f"Selected base for E3/E4: {base_id} (sw={base_sw_desc})")

    # 6. E3 (Negation heuristic on selected base E2/E2w)
    print("\n--- Running E3 ---")
    comb_neg = comb_texts.map(add_negation_features)
    pol_va_neg = pol_va["text"].map(add_negation_features)
    s_va_neg = s_va_60["text"].map(add_negation_features)
    existing = load_existing_record("E3")
    if existing:
        print("  Loaded existing E3.")
        records.append(existing)
    else:
        e3_pipe, e3_sc, _, e3_thr, e3_pm, e3_sm, tr_s, inf_s = fit_and_eval(
            make_word_pipeline(C=best_c_val, class_weight=None),
            comb_neg, comb_labels, pol_va_neg, pol_va["label"], s_va_neg, s_va_60["label"],
            sample_weight=base_sw, beta=1.0,
        )
        records.append(save_experiment(
            "E3", e3_pipe,
            {
                "experiment_id": "E3", "base_experiment": base_id, "preprocessing_version": f"{PREPROCESSING_VERSION}+negation_window3",
                "negation_config": {"triggers": sorted(NEGATION_TRIGGERS), "stopwords_count": len(NEGATION_STOPWORDS), "window": 3},
                "train_datasets": ["data/splits/political_train.csv (133314)", "data/splits/s140_train_400k.csv (400000)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "vectorizer": {"type": "TfidfVectorizer", "ngram_range": [1, 2], "min_df": 2, "max_features": 40000, "sublinear_tf": True},
                "model": {"type": "LinearSVC", "C": best_c_val, "class_weight": None, "max_iter": 3000, "random_state": SEED},
                "sample_weight": base_sw_desc, "threshold": e3_thr, "threshold_objective": "F1_class1 (political_val)",
                "seed": SEED, "train_time_sec": round(tr_s, 3), "infer_time_sec": round(inf_s, 3), "env": env,
            },
            pol_va, e3_sc, e3_pm, e3_sm,
            [f"E3 (base={base_id}): thr={e3_thr:.6f}, pol_val F1={e3_pm['f1_class1']:.4f}, s140_val F1={e3_sm['f1_class1']:.4f}"],
        ))
    print(f"E3 pol_val F1={records[-1]['pol_val']['f1_class1']:.4f}, s140_val F1={records[-1]['s140_val']['f1_class1']:.4f}")

    # 7. E4a (Char_wb 2-5 only on selected base E2/E2w)
    print("\n--- Running E4a ---")
    existing = load_existing_record("E4a")
    if existing:
        print("  Loaded existing E4a.")
        records.append(existing)
    else:
        e4a_pipe, e4a_sc, _, e4a_thr, e4a_pm, e4a_sm, tr_s, inf_s = fit_and_eval(
            make_char_pipeline(C=best_c_val, class_weight=None),
            comb_texts, comb_labels, pol_va["text"], pol_va["label"], s_va_60["text"], s_va_60["label"],
            sample_weight=base_sw, beta=1.0,
        )
        records.append(save_experiment(
            "E4a", e4a_pipe,
            {
                "experiment_id": "E4a", "base_experiment": base_id, "preprocessing_version": PREPROCESSING_VERSION,
                "train_datasets": ["data/splits/political_train.csv (133314)", "data/splits/s140_train_400k.csv (400000)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "vectorizer": {"type": "TfidfVectorizer", "analyzer": "char_wb", "ngram_range": [2, 5], "min_df": 3, "max_features": 80000, "sublinear_tf": True},
                "model": {"type": "LinearSVC", "C": best_c_val, "class_weight": None, "max_iter": 3000, "random_state": SEED},
                "sample_weight": base_sw_desc, "threshold": e4a_thr, "threshold_objective": "F1_class1 (political_val)",
                "seed": SEED, "train_time_sec": round(tr_s, 3), "infer_time_sec": round(inf_s, 3), "env": env,
            },
            pol_va, e4a_sc, e4a_pm, e4a_sm,
            [f"E4a (char_wb 2-5, base={base_id}): thr={e4a_thr:.6f}, pol_val F1={e4a_pm['f1_class1']:.4f}"],
        ))
    print(f"E4a pol_val F1={records[-1]['pol_val']['f1_class1']:.4f}, s140_val F1={records[-1]['s140_val']['f1_class1']:.4f}")

    # 8. E4b (FeatureUnion Word 1-2 + Char_wb 2-5 on selected base E2/E2w)
    print("\n--- Running E4b ---")
    existing = load_existing_record("E4b")
    if existing:
        print("  Loaded existing E4b.")
        records.append(existing)
    else:
        e4b_pipe, e4b_sc, _, e4b_thr, e4b_pm, e4b_sm, tr_s, inf_s = fit_and_eval(
            make_union_pipeline(C=best_c_val, class_weight=None),
            comb_texts, comb_labels, pol_va["text"], pol_va["label"], s_va_60["text"], s_va_60["label"],
            sample_weight=base_sw, beta=1.0,
        )
        records.append(save_experiment(
            "E4b", e4b_pipe,
            {
                "experiment_id": "E4b", "base_experiment": base_id, "preprocessing_version": PREPROCESSING_VERSION,
                "train_datasets": ["data/splits/political_train.csv (133314)", "data/splits/s140_train_400k.csv (400000)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "vectorizer": {
                    "type": "FeatureUnion",
                    "word": {"ngram_range": [1, 2], "min_df": 2, "max_features": 40000, "sublinear_tf": True},
                    "char": {"analyzer": "char_wb", "ngram_range": [2, 5], "min_df": 3, "max_features": 80000, "sublinear_tf": True},
                },
                "model": {"type": "LinearSVC", "C": best_c_val, "class_weight": None, "max_iter": 3000, "random_state": SEED},
                "sample_weight": base_sw_desc, "threshold": e4b_thr, "threshold_objective": "F1_class1 (political_val)",
                "seed": SEED, "train_time_sec": round(tr_s, 3), "infer_time_sec": round(inf_s, 3), "env": env,
            },
            pol_va, e4b_sc, e4b_pm, e4b_sm,
            [f"E4b (Word+Char_wb, base={base_id}): thr={e4b_thr:.6f}, pol_val F1={e4b_pm['f1_class1']:.4f}"],
        ))
    print(f"E4b pol_val F1={records[-1]['pol_val']['f1_class1']:.4f}, s140_val F1={records[-1]['s140_val']['f1_class1']:.4f}")

    # Select best base among E2, E2w, E3, E4a, E4b for E5a/E5b
    pool_e5 = {r["experiment_id"]: r for r in records if r["experiment_id"] in {"E2", "E2w", "E3", "E4a", "E4b"}}
    e5_base_id = max(pool_e5, key=lambda k: pool_e5[k]["pol_val"]["f1_class1"])
    print(f"\nSelected base for E5a/E5b: {e5_base_id} (pol_val F1={pool_e5[e5_base_id]['pol_val']['f1_class1']:.4f})")

    def build_e5_inputs():
        if e5_base_id == "E3":
            return comb_neg, pol_va_neg["text"] if isinstance(pol_va_neg, pd.DataFrame) else pol_va_neg, s_va_neg, make_word_pipeline
        if e5_base_id == "E4a":
            return comb_texts, pol_va["text"], s_va_60["text"], make_char_pipeline
        if e5_base_id == "E4b":
            return comb_texts, pol_va["text"], s_va_60["text"], make_union_pipeline
        return comb_texts, pol_va["text"], s_va_60["text"], make_word_pipeline

    e5_tr_x, e5_pva_x, e5_sva_x, e5_pipe_fn = build_e5_inputs()
    e5_sw = best_sw if (e5_base_id == "E2w" or (e5_base_id in {"E3", "E4a", "E4b"} and base_id == "E2w")) else None
    e5_sw_desc = base_sw_desc if e5_sw is not None else {"r": 1.0, "w_pol": 1.0, "w_s140": 1.0}

    # 9. E5a (class_weight comparison, F1 objective)
    print("\n--- Running E5a ---")
    existing = load_existing_record("E5a")
    if existing:
        print("  Loaded existing E5a.")
        records.append(existing)
        best_cw_key = str(existing["_config"]["model"]["selected_class_weight"])
        best_cw_val = existing["_config"]["model"]["selected_class_weight"]
        e5a_pipe = joblib.load(ROOT / existing["model_path"])["pipeline"]
        e5a_sc = e5a_pipe.decision_function(e5_pva_x)
        tr_s = existing["train_time_sec"]
        inf_s = existing["infer_time_sec"]
    else:
        cw_options = [("None", None), ("balanced", "balanced"), ("1_1.5", {0: 1.0, 1: 1.5}), ("1_2", {0: 1.0, 1: 2.0})]
        e5a_candidates = {}
        for cw_name, cw_val in cw_options:
            p_cw, sc_cw, _, t_cw, pm_cw, sm_cw, tr_cw, inf_cw = fit_and_eval(
                e5_pipe_fn(C=best_c_val, class_weight=cw_val),
                e5_tr_x, comb_labels, e5_pva_x, pol_va["label"], e5_sva_x, s_va_60["label"],
                sample_weight=e5_sw, beta=1.0,
            )
            e5a_candidates[cw_name] = {"class_weight": cw_val, "threshold": t_cw, "political_val": pm_cw, "s140_val": sm_cw, "train_time_sec": round(tr_cw, 3)}
            print(f"  class_weight={cw_name}: pol_val F1={pm_cw['f1_class1']:.4f}, P={pm_cw['precision_class1']:.4f}, R={pm_cw['recall_class1']:.4f}")

        best_cw_key = max(e5a_candidates, key=lambda k: e5a_candidates[k]["political_val"]["f1_class1"])
        best_cw_val = dict(cw_options)[best_cw_key]
        e5a_pipe, e5a_sc, _, e5a_thr, e5a_pm, e5a_sm, tr_s, inf_s = fit_and_eval(
            e5_pipe_fn(C=best_c_val, class_weight=best_cw_val),
            e5_tr_x, comb_labels, e5_pva_x, pol_va["label"], e5_sva_x, s_va_60["label"],
            sample_weight=e5_sw, beta=1.0,
        )
        records.append(save_experiment(
            "E5a", e5a_pipe,
            {
                "experiment_id": "E5a", "base_experiment": e5_base_id,
                "preprocessing_version": records[[r["experiment_id"] for r in records].index(e5_base_id)]["preprocessing_version"],
                "train_datasets": ["data/splits/political_train.csv (133314)", "data/splits/s140_train_400k.csv (400000)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "model": {"type": "LinearSVC", "C": best_c_val, "selected_class_weight": best_cw_val, "max_iter": 3000, "random_state": SEED},
                "sample_weight": e5_sw_desc, "threshold": e5a_thr, "threshold_objective": "F1_class1 (political_val)",
                "seed": SEED, "train_time_sec": round(tr_s, 3), "infer_time_sec": round(inf_s, 3), "env": env,
            },
            pol_va, e5a_sc, e5a_pm, e5a_sm,
            [f"E5a (base={e5_base_id}, class_weight={best_cw_key}): thr={e5a_thr:.6f}, pol_val F1={e5a_pm['f1_class1']:.4f}"],
            extra_val_data=e5a_candidates,
        ))

    # 10. E5b (keep best class_weight from E5a, switch threshold objective to F2 beta=2)
    print("\n--- Running E5b ---")
    existing = load_existing_record("E5b")
    if existing:
        print("  Loaded existing E5b.")
        records.append(existing)
    else:
        e5b_thr, _ = choose_threshold(e5a_sc, pol_va["label"], beta=2.0)
        e5b_pm = compute_metrics(pol_va["label"], e5a_sc, e5b_thr)
        s140_sc_e5b = e5a_pipe.decision_function(e5_sva_x)
        e5b_sm = compute_metrics(s_va_60["label"], s140_sc_e5b, e5b_thr)
        records.append(save_experiment(
            "E5b", e5a_pipe,
            {
                "experiment_id": "E5b", "base_experiment": "E5a",
                "preprocessing_version": records[[r["experiment_id"] for r in records].index(e5_base_id)]["preprocessing_version"],
                "train_datasets": ["data/splits/political_train.csv (133314)", "data/splits/s140_train_400k.csv (400000)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "model": {"type": "LinearSVC", "C": best_c_val, "selected_class_weight": best_cw_val, "max_iter": 3000, "random_state": SEED},
                "sample_weight": e5_sw_desc, "threshold": e5b_thr, "threshold_objective": "F2_class1 (beta=2.0, political_val)",
                "seed": SEED, "train_time_sec": round(tr_s, 3), "infer_time_sec": round(inf_s, 3), "env": env,
            },
            pol_va, e5a_sc, e5b_pm, e5b_sm,
            [f"E5b (F2 thr on E5a): thr={e5b_thr:.6f}, pol_val F1={e5b_pm['f1_class1']:.4f}, F2={e5b_pm['f2_class1']:.4f}, R={e5b_pm['recall_class1']:.4f}, P={e5b_pm['precision_class1']:.4f}"],
        ))
        print(f"E5b pol_val F1={e5b_pm['f1_class1']:.4f}, F2={e5b_pm['f2_class1']:.4f}, P={e5b_pm['precision_class1']:.4f}, R={e5b_pm['recall_class1']:.4f}")

    # 11. E6-50k, E6-120k, E6-400k (all locked to E2 config: same C, vectorizer, v4, class_weight=None, threshold=e2_thr)
    print("\n--- Running E6 (50k, 120k, 400k) with locked E2 C & threshold ---")
    for scale_name, s_df in [("E6-50k", s_tr_50), ("E6-120k", s_tr_120), ("E6-400k", s_tr_400)]:
        existing = load_existing_record(scale_name)
        if existing:
            print(f"  Loaded existing {scale_name}.")
            records.append(existing)
            continue
        tr_x = pd.concat([pol_tr["text"], s_df["text"]], ignore_index=True)
        tr_y = pd.concat([pol_tr["label"], s_df["label"]], ignore_index=True)
        p_6, sc_6, _, t_6, pm_6, sm_6, tr_6, inf_6 = fit_and_eval(
            make_word_pipeline(C=best_c_val, class_weight=None),
            tr_x, tr_y, pol_va["text"], pol_va["label"], s_va_60["text"], s_va_60["label"],
            fixed_threshold=e2_thr,
        )
        records.append(save_experiment(
            scale_name, p_6,
            {
                "experiment_id": scale_name, "base_experiment": "E2 (locked C & threshold)",
                "preprocessing_version": PREPROCESSING_VERSION,
                "train_datasets": [f"data/splits/political_train.csv (133314)", f"s140 ({len(s_df)})"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "vectorizer": {"type": "TfidfVectorizer", "ngram_range": [1, 2], "min_df": 2, "max_features": 40000, "sublinear_tf": True},
                "model": {"type": "LinearSVC", "C": best_c_val, "class_weight": None, "max_iter": 3000, "random_state": SEED},
                "sample_weight": "uniform (1.0)", "threshold": e2_thr, "threshold_objective": "LOCKED_FROM_E2",
                "seed": SEED, "train_time_sec": round(tr_6, 3), "infer_time_sec": round(inf_6, 3), "env": env,
            },
            pol_va, sc_6, pm_6, sm_6,
            [f"{scale_name} (locked thr={e2_thr:.6f}): pol_val F1={pm_6['f1_class1']:.4f}, s140_val F1={sm_6['f1_class1']:.4f}"],
        ))
        print(f"  {scale_name}: pol_val F1={pm_6['f1_class1']:.4f}, s140_val F1={sm_6['f1_class1']:.4f}")

    # 12. Freeze Gate: create freeze_manifest.json and phase4A_validation_summary.md
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    base_art_path = ROOT / "baseline_v3" / "binary_linear_svm.joblib"
    base_art_meta = joblib.load(base_art_path)
    freeze_manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase 4A Freeze Gate (Before opening T1/T2)",
        "python_version": platform.python_version(),
        "libraries": env,
        "code_sha256": {
            "phase4a_run.py": sha256_file(Path(__file__)),
            "preprocessing_v4.py": sha256_file(ROOT / "preprocessing_v4.py"),
            "negation_feature.py": sha256_file(ROOT / "scripts" / "negation_feature.py"),
        },
        "train_val_splits_sha256": {
            k: manifest["datasets"][k]["sha256"]
            for k in ("political_train", "political_val", "s140_train_400k", "s140_val_60k", "s140_train_e6_50k", "s140_train_e6_120k")
        },
        "allowed_artifacts_for_step4B": [
            {
                "experiment_id": "E0-Artifact",
                "model_path": "baseline_v3/binary_linear_svm.joblib",
                "model_sha256": sha256_file(base_art_path),
                "preprocessing_version": base_art_meta.get("preprocessing_version"),
                "threshold": float(base_art_meta.get("threshold")),
                "threshold_objective": "Frozen baseline_v3 (trained on Train+Val; evaluate ONLY on T1/T2, NEVER on political_val)",
            },
            *[
                {
                    "experiment_id": r["experiment_id"],
                    "model_path": r["model_path"],
                    "config_path": r["config_path"],
                    "model_sha256": r["model_sha256"],
                    "config_sha256": r["config_sha256"],
                    "preprocessing_version": r["preprocessing_version"],
                    "threshold": r["threshold"],
                    "threshold_objective": r["threshold_objective"],
                }
                for r in records
            ],
        ],
    }
    (EXPERIMENTS / "freeze_manifest.json").write_text(
        json.dumps(freeze_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write phase4A_validation_summary.md
    lines = [
        "# TỔNG HỢP KẾT QUẢ BƯỚC 4A – VALIDATION (E0–E6)",
        "",
        f"**Ngày hoàn tất:** {datetime.now(timezone.utc).isoformat()}  ",
        "**Trạng thái:** Đã chốt `experiments/freeze_manifest.json`. **Chưa mở `T1` và `T2`.**  ",
        "*(Ghi chú: `E0-Artifact` được fit trên `Train + Validation` nên không đánh giá và không xếp hạng trên `political_val.csv`.)*",
        "",
        "## 1. Bảng so sánh trên Political Validation (`23.526` dòng) & S140 Validation (`60.000` dòng)",
        "",
        "| Mã | Prep | Pol Precision (1) | Pol Recall (1) | Pol F1 (1) | Pol PR-AUC | Pol Acc | S140 F1 (1) | Threshold | Train (s) | SHA-256 (12) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in records:
        pv, sv = r["pol_val"], r["s140_val"]
        lines.append(
            f"| {r['experiment_id']} | `{r['preprocessing_version']}` | {pv['precision_class1']:.4f} | {pv['recall_class1']:.4f} | "
            f"{pv['f1_class1']:.4f} | {pv['pr_auc_class1']:.4f} | {pv['accuracy']:.4f} | {sv['f1_class1']:.4f} | "
            f"{r['threshold']:.4f} | {r['train_time_sec']:.2f} | `{r['model_sha256'][:12]}` |"
        )
    lines.extend([
        "",
        "## 2. Chi tiết tối ưu E1b (`C`), E2w (`sample_weight`) và E5a (`class_weight`)",
        "",
        f"- **E1b (`C` tốt nhất):** `{best_c_val}`",
        f"- **E2w (`r` tốt nhất):** `{best_r}` (chọn nền `{base_id}` cho E3/E4)",
        f"- **Nền cho E5a/E5b:** `{e5_base_id}` (chọn `class_weight = {best_cw_key}`)",
        "",
        "## 3. Freeze Gate",
        "- Toàn bộ artifact, `config.json`, mã nguồn và tập Train/Val đã được khóa SHA-256 trong `experiments/freeze_manifest.json`.",
        "- Sẵn sàng chờ phê duyệt để mở `T1` và `T2` ở Bước 4B / Giai đoạn 5.",
    ])
    (EXPERIMENTS / "phase4A_validation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nPhase 4A completed and Freeze Gate manifest saved!")


if __name__ == "__main__":
    main()
