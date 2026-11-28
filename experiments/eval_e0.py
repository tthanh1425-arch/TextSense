"""Evaluate baseline v3 (E0) on T1 (political test split), T3 (Sentiment140 test), and real_world_eval_tweets."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "baseline_v3"))
from predict import predict  # noqa: E402

MODEL_PATH = ROOT / "baseline_v3" / "binary_linear_svm.joblib"


def bootstrap_ci(y_true, y_pred, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed)
    n = len(y_true)
    f1s, recs, precs = [], [], []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        yp = y_pred[idx]
        f1s.append(f1_score(yt, yp, pos_label=1, zero_division=0))
        recs.append(recall_score(yt, yp, pos_label=1, zero_division=0))
        precs.append(precision_score(yt, yp, pos_label=1, zero_division=0))
    return {
        "f1_ci95": [float(np.percentile(f1s, 2.5)), float(np.percentile(f1s, 97.5))],
        "recall_ci95": [float(np.percentile(recs, 2.5)), float(np.percentile(recs, 97.5))],
        "precision_ci95": [float(np.percentile(precs, 2.5)), float(np.percentile(precs, 97.5))],
    }


def evaluate_set(name, texts, y_true):
    res = predict(MODEL_PATH, texts, batch_size=1024)
    y_pred = np.array([r["predicted_label"] if r["predicted_label"] is not None else 0 for r in res])
    skipped = sum(1 for r in res if r["predicted_label"] is None)
    y_true = np.asarray(y_true, dtype=int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    metrics = {
        "name": name,
        "n": int(len(y_true)),
        "pos_count": int(y_true.sum()),
        "neg_count": int((1 - y_true).sum()),
        "skipped_by_predict": int(skipped),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_class1": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall_class1": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1_class1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }
    metrics.update(bootstrap_ci(y_true, y_pred))
    return metrics


def main():
    results = {}

    # 1. T1: Political test split
    t1_df = pd.read_csv(ROOT / "baseline_v3" / "splits" / "binary" / "test.csv")
    print("T1 columns:", list(t1_df.columns), "rows:", len(t1_df))
    text_col = "text" if "text" in t1_df.columns else "clean_text"
    label_col = "label" if "label" in t1_df.columns else "target"
    results["T1_overall"] = evaluate_set("T1_overall", t1_df[text_col].fillna("").tolist(), t1_df[label_col].values)
    if "source" in t1_df.columns:
        for src, sub in t1_df.groupby("source"):
            results[f"T1_{src}"] = evaluate_set(f"T1_{src}", sub[text_col].fillna("").tolist(), sub[label_col].values)

    # 2. T3: Sentiment140 test_data.csv (sentiment: 0=negative -> 1, 1=positive -> 0)
    t3_df = pd.read_csv(ROOT / "data" / "raw" / "sentiment140_test.csv")
    print("\nT3 sample sentiment=0 (negative):")
    print(t3_df[t3_df["sentiment"] == 0]["sentence"].head(3).tolist())
    print("T3 sample sentiment=1 (positive):")
    print(t3_df[t3_df["sentiment"] == 1]["sentence"].head(3).tolist())
    t3_y = (t3_df["sentiment"] == 0).astype(int).values
    results["T3_s140_test"] = evaluate_set("T3_s140_test", t3_df["sentence"].fillna("").tolist(), t3_y)

    # 3. real_world_eval_tweets.csv (consensus where annotator_1 == annotator_2)
    rw_df = pd.read_csv(ROOT / "data" / "raw" / "real_world_eval_tweets.csv")
    agree_df = rw_df[rw_df["annotator_1"] == rw_df["annotator_2"]]
    results["real_world_agree"] = evaluate_set(
        "real_world_agree",
        agree_df["text"].fillna("").tolist(),
        agree_df["annotator_1"].values,
    )

    out_path = ROOT / "experiments" / "e0_baseline_results.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nSaved results to:", out_path)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
