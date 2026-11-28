"""Resume Phase 4A from E5a through E6-400k and build Freeze Gate manifest + summary."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from preprocessing_v4 import PREPROCESSING_VERSION  # noqa: E402
from negation_feature import add_negation_features  # noqa: E402
from phase4a_run import (  # noqa: E402
    EXPERIMENTS,
    MANIFEST_PATH,
    SEED,
    choose_threshold,
    compute_metrics,
    env_info,
    fit_and_eval,
    load_existing_record,
    make_char_pipeline,
    make_union_pipeline,
    make_word_pipeline,
    pre_run_checks,
    save_experiment,
    sha256_file,
)


def main() -> None:
    data = pre_run_checks()
    pol_tr = data["political_train"]
    pol_va = data["political_val"]
    s_tr_400 = data["s140_train_400k"]
    s_va_60 = data["s140_val_60k"]
    s_tr_50 = data["s140_train_e6_50k"]
    s_tr_120 = data["s140_train_e6_120k"]

    completed_ids = ["E0-Train", "E1a", "E1b", "E2", "E2w", "E3", "E4a", "E4b"]
    records = []
    for eid in completed_ids:
        rec = load_existing_record(eid)
        assert rec is not None, f"Missing completed experiment: {eid}"
        records.append(rec)
        print(f"Loaded {eid}: pol_val F1={rec['pol_val']['f1_class1']:.4f}, s140_val F1={rec['s140_val']['f1_class1']:.4f}", flush=True)

    rec_map = {r["experiment_id"]: r for r in records}
    best_c_val = float(rec_map["E1b"]["_cfg"]["model"]["C"])
    e2_thr = float(rec_map["E2"]["threshold"])
    e2w_sw_cfg = rec_map["E2w"]["_cfg"]["sample_weight"]
    best_r = float(e2w_sw_cfg["selected_r"])

    n_pol, n_s140 = len(pol_tr), len(s_tr_400)
    comb_texts = pd.concat([pol_tr["text"], s_tr_400["text"]], ignore_index=True)
    comb_labels = pd.concat([pol_tr["label"], s_tr_400["label"]], ignore_index=True)

    base_id = "E2w" if (rec_map["E2w"]["pol_val"]["f1_class1"] >= rec_map["E2"]["pol_val"]["f1_class1"] and best_r != 1.0) else "E2"
    best_sw = np.concatenate([
        np.full(n_pol, e2w_sw_cfg["w_pol"], dtype=np.float64),
        np.full(n_s140, e2w_sw_cfg["w_s140"], dtype=np.float64),
    ])
    base_sw_desc = {"selected_r": best_r, "w_pol": e2w_sw_cfg["w_pol"], "w_s140": e2w_sw_cfg["w_s140"]} if base_id == "E2w" else {"r": 1.0, "w_pol": 1.0, "w_s140": 1.0}

    pool_e5 = {k: rec_map[k] for k in ("E2", "E2w", "E3", "E4a", "E4b")}
    e5_base_id = max(pool_e5, key=lambda k: pool_e5[k]["pol_val"]["f1_class1"])
    print(f"\nSelected base for E5a/E5b: {e5_base_id} (pol_val F1={pool_e5[e5_base_id]['pol_val']['f1_class1']:.4f})", flush=True)

    if e5_base_id == "E3":
        e5_tr_x = comb_texts.map(add_negation_features)
        e5_pva_x = pol_va["text"].map(add_negation_features)
        e5_sva_x = s_va_60["text"].map(add_negation_features)
        e5_pipe_fn = make_word_pipeline
    elif e5_base_id == "E4a":
        e5_tr_x, e5_pva_x, e5_sva_x, e5_pipe_fn = comb_texts, pol_va["text"], s_va_60["text"], make_char_pipeline
    elif e5_base_id == "E4b":
        e5_tr_x, e5_pva_x, e5_sva_x, e5_pipe_fn = comb_texts, pol_va["text"], s_va_60["text"], make_union_pipeline
    else:
        e5_tr_x, e5_pva_x, e5_sva_x, e5_pipe_fn = comb_texts, pol_va["text"], s_va_60["text"], make_word_pipeline

    e5_sw = best_sw if (e5_base_id == "E2w" or (e5_base_id in {"E3", "E4a", "E4b"} and base_id == "E2w")) else None
    e5_sw_desc = base_sw_desc if e5_sw is not None else {"r": 1.0, "w_pol": 1.0, "w_s140": 1.0}
    env = env_info()

    # E5a
    e5a_rec = load_existing_record("E5a")
    if e5a_rec is None:
        print("\n--- Running E5a ---", flush=True)
        cw_options = [("None", None), ("balanced", "balanced"), ("1_1.5", {0: 1.0, 1: 1.5}), ("1_2", {0: 1.0, 1: 2.0})]
        e5a_candidates = {}
        for cw_name, cw_val in cw_options:
            _, _, _, t_cw, pm_cw, sm_cw, tr_cw, _ = fit_and_eval(
                e5_pipe_fn(C=best_c_val, class_weight=cw_val),
                e5_tr_x, comb_labels, e5_pva_x, pol_va["label"], e5_sva_x, s_va_60["label"],
                sample_weight=e5_sw, beta=1.0,
            )
            e5a_candidates[cw_name] = {"class_weight": cw_val, "threshold": t_cw, "political_val": pm_cw, "s140_val": sm_cw, "train_time_sec": round(tr_cw, 3)}
            print(f"  class_weight={cw_name}: pol_val F1={pm_cw['f1_class1']:.4f}, P={pm_cw['precision_class1']:.4f}, R={pm_cw['recall_class1']:.4f}", flush=True)

        best_cw_key = max(e5a_candidates, key=lambda k: e5a_candidates[k]["political_val"]["f1_class1"])
        best_cw_val = dict(cw_options)[best_cw_key]
        e5a_pipe, e5a_sc, _, e5a_thr, e5a_pm, e5a_sm, tr_s, inf_s = fit_and_eval(
            e5_pipe_fn(C=best_c_val, class_weight=best_cw_val),
            e5_tr_x, comb_labels, e5_pva_x, pol_va["label"], e5_sva_x, s_va_60["label"],
            sample_weight=e5_sw, beta=1.0,
        )
        e5a_rec = save_experiment(
            "E5a", e5a_pipe,
            {
                "experiment_id": "E5a", "base_experiment": e5_base_id,
                "preprocessing_version": rec_map[e5_base_id]["preprocessing_version"],
                "train_datasets": ["data/splits/political_train.csv (133314)", "data/splits/s140_train_400k.csv (400000)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "model": {"type": "LinearSVC", "C": best_c_val, "selected_class_weight": best_cw_val, "max_iter": 3000, "random_state": SEED},
                "sample_weight": e5_sw_desc, "threshold": e5a_thr, "threshold_objective": "F1_class1 (political_val)",
                "seed": SEED, "train_time_sec": round(tr_s, 3), "infer_time_sec": round(inf_s, 3), "env": env,
            },
            pol_va, e5a_sc, e5a_pm, e5a_sm,
            [f"E5a (base={e5_base_id}, class_weight={best_cw_key}): thr={e5a_thr:.6f}, pol_val F1={e5a_pm['f1_class1']:.4f}"],
            extra_val_data=e5a_candidates,
        )
    else:
        art_5a = joblib.load(EXPERIMENTS / "E5a" / "model.joblib")
        e5a_pipe = art_5a["pipeline"]
        e5a_sc = e5a_pipe.decision_function(e5_pva_x)
        best_cw_val = e5a_rec["_cfg"]["model"]["selected_class_weight"]
        best_cw_key = str(best_cw_val)
        tr_s, inf_s = e5a_rec["train_time_sec"], e5a_rec["infer_time_sec"]
    records.append(e5a_rec)

    # E5b
    e5b_rec = load_existing_record("E5b")
    if e5b_rec is None:
        print("\n--- Running E5b ---", flush=True)
        e5b_thr, _ = choose_threshold(e5a_sc, pol_va["label"], beta=2.0)
        e5b_pm = compute_metrics(pol_va["label"], e5a_sc, e5b_thr)
        s140_sc_e5b = e5a_pipe.decision_function(e5_sva_x)
        e5b_sm = compute_metrics(s_va_60["label"], s140_sc_e5b, e5b_thr)
        e5b_rec = save_experiment(
            "E5b", e5a_pipe,
            {
                "experiment_id": "E5b", "base_experiment": "E5a",
                "preprocessing_version": rec_map[e5_base_id]["preprocessing_version"],
                "train_datasets": ["data/splits/political_train.csv (133314)", "data/splits/s140_train_400k.csv (400000)"],
                "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                "model": {"type": "LinearSVC", "C": best_c_val, "selected_class_weight": best_cw_val, "max_iter": 3000, "random_state": SEED},
                "sample_weight": e5_sw_desc, "threshold": e5b_thr, "threshold_objective": "F2_class1 (beta=2.0, political_val)",
                "seed": SEED, "train_time_sec": round(tr_s, 3), "infer_time_sec": round(inf_s, 3), "env": env,
            },
            pol_va, e5a_sc, e5b_pm, e5b_sm,
            [f"E5b (F2 thr on E5a): thr={e5b_thr:.6f}, pol_val F1={e5b_pm['f1_class1']:.4f}, F2={e5b_pm['f2_class1']:.4f}, R={e5b_pm['recall_class1']:.4f}, P={e5b_pm['precision_class1']:.4f}"],
        )
        print(f"E5b pol_val F1={e5b_pm['f1_class1']:.4f}, F2={e5b_pm['f2_class1']:.4f}, P={e5b_pm['precision_class1']:.4f}, R={e5b_pm['recall_class1']:.4f}", flush=True)
    records.append(e5b_rec)

    # E6-50k, E6-120k, E6-400k
    print("\n--- Running E6 (50k, 120k, 400k) with locked E2 C & threshold ---", flush=True)
    for scale_name, s_df in [("E6-50k", s_tr_50), ("E6-120k", s_tr_120), ("E6-400k", s_tr_400)]:
        rec6 = load_existing_record(scale_name)
        if rec6 is None:
            tr_x = pd.concat([pol_tr["text"], s_df["text"]], ignore_index=True)
            tr_y = pd.concat([pol_tr["label"], s_df["label"]], ignore_index=True)
            p_6, sc_6, _, t_6, pm_6, sm_6, tr_6, inf_6 = fit_and_eval(
                make_word_pipeline(C=best_c_val, class_weight=None),
                tr_x, tr_y, pol_va["text"], pol_va["label"], s_va_60["text"], s_va_60["label"],
                fixed_threshold=e2_thr,
            )
            rec6 = save_experiment(
                scale_name, p_6,
                {
                    "experiment_id": scale_name, "base_experiment": "E2 (locked C & threshold)",
                    "preprocessing_version": PREPROCESSING_VERSION,
                    "train_datasets": ["data/splits/political_train.csv (133314)", f"s140 ({len(s_df)})"],
                    "val_datasets": ["data/splits/political_val.csv (23526)", "data/splits/s140_val_60k.csv (60000)"],
                    "vectorizer": {"type": "TfidfVectorizer", "ngram_range": [1, 2], "min_df": 2, "max_features": 40000, "sublinear_tf": True},
                    "model": {"type": "LinearSVC", "C": best_c_val, "class_weight": None, "max_iter": 3000, "random_state": SEED},
                    "sample_weight": "uniform (1.0)", "threshold": e2_thr, "threshold_objective": "LOCKED_FROM_E2",
                    "seed": SEED, "train_time_sec": round(tr_6, 3), "infer_time_sec": round(inf_6, 3), "env": env,
                },
                pol_va, sc_6, pm_6, sm_6,
                [f"{scale_name} (locked thr={e2_thr:.6f}): pol_val F1={pm_6['f1_class1']:.4f}, s140_val F1={sm_6['f1_class1']:.4f}"],
            )
            print(f"  {scale_name}: pol_val F1={pm_6['f1_class1']:.4f}, s140_val F1={sm_6['f1_class1']:.4f}", flush=True)
        records.append(rec6)

    # Freeze Gate
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    base_art_path = ROOT / "baseline_v3" / "binary_linear_svm.joblib"
    base_art_meta = joblib.load(base_art_path)
    freeze_manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase 4A Freeze Gate (Before opening T1/T2)",
        "python_version": env["python"],
        "libraries": env,
        "code_sha256": {
            "phase4a_run.py": sha256_file(ROOT / "scripts" / "phase4a_run.py"),
            "phase4a_resume.py": sha256_file(Path(__file__)),
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
    print("\nPhase 4A completed and Freeze Gate manifest saved!", flush=True)


if __name__ == "__main__":
    main()
