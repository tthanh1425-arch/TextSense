"""Phase 1: Data quality audit, cleaning, leakage removal, and stratified 520k sampling of Sentiment140
(400,000 Train + 60,000 Validation + 60,000 Test T2, balanced 50/50 per split).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from preprocessing_v4 import PREPROCESSING_VERSION, normalize_text  # noqa: E402

RAW = ROOT / "data" / "raw"
SAMPLED = ROOT / "data" / "sampled"
BASELINE_SPLITS = ROOT / "baseline_v3" / "splits" / "binary"
SEED = 42

TRAIN_PER_CLASS = 200_000   # 400,000 total
VAL_PER_CLASS = 30_000      # 60,000 total
TEST_PER_CLASS = 30_000     # 60,000 total
TOTAL_PER_CLASS = TRAIN_PER_CLASS + VAL_PER_CLASS + TEST_PER_CLASS  # 260,000 -> 520,000 total


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_key(value) -> str:
    return normalize_text(value)


def main() -> None:
    SAMPLED.mkdir(parents=True, exist_ok=True)
    old_400k = SAMPLED / "sentiment140_400k.csv"
    if old_400k.exists():
        old_400k.unlink()

    # 1. Load baseline political splits (read-only)
    pol_train = pd.read_csv(BASELINE_SPLITS / "train.csv")
    pol_val = pd.read_csv(BASELINE_SPLITS / "validation.csv")
    pol_test = pd.read_csv(BASELINE_SPLITS / "test.csv")

    t1_keys = set(pol_test["text"].map(norm_key))
    pol_tv_keys = set(pol_train["text"].map(norm_key)) | set(pol_val["text"].map(norm_key))

    # 2. Load Sentiment140 test_data.csv (359 rows) for leakage protection
    s140_test_path = RAW / "sentiment140_test.csv"
    s140_test = pd.read_csv(s140_test_path)
    s140_test_keys = set(s140_test["sentence"].map(norm_key))

    # 3. Load and clean Sentiment140 train_data.csv
    s140_train_path = RAW / "sentiment140_train.csv"
    df = pd.read_csv(s140_train_path)
    df["orig_idx"] = df.index
    raw_rows = len(df)
    raw_counts = df["sentiment"].value_counts().to_dict()

    df = df.dropna(subset=["sentence", "sentiment"]).copy()
    after_na = len(df)

    df["key"] = df["sentence"].map(norm_key)
    empty_rows = int((df["key"].str.len() == 0).sum())
    too_short_rows = int(((df["key"].str.len() > 0) & (df["key"].str.len() < 3)).sum())
    df = df[df["key"].str.len() >= 3].copy()
    after_len = len(df)

    grp_n = df.groupby("key")["sentiment"].nunique()
    conflict_keys = set(grp_n[grp_n > 1].index)
    conflict_rows_removed = int(df["key"].isin(conflict_keys).sum())
    df = df[~df["key"].isin(conflict_keys)].copy()

    before_dedup = len(df)
    df = df.drop_duplicates("key", keep="first").copy()
    dup_rows_removed = int(before_dedup - len(df))

    # Leakage removal against T1, political train+val, and s140_test
    mask_t1 = df["key"].isin(t1_keys)
    mask_pol_tv = df["key"].isin(pol_tv_keys)
    mask_s140_test = df["key"].isin(s140_test_keys)
    removed_t1 = int(mask_t1.sum())
    removed_pol_tv = int((~mask_t1 & mask_pol_tv).sum())
    removed_s140_test = int((~mask_t1 & ~mask_pol_tv & mask_s140_test).sum())

    df = df[~(mask_t1 | mask_pol_tv | mask_s140_test)].copy()
    clean_pool_rows = len(df)

    # Map Sentiment140 labels: 0 -> 1 (Negative), 1 -> 0 (Non-negative / Positive)
    df["label"] = df["sentiment"].map({0: 1, 1: 0}).astype(int)
    pool_counts = df["label"].value_counts().to_dict()

    # 4. Stratified sampling: 260,000 Negative (1) + 260,000 Positive (0) = 520,000
    neg_pool = df[df["label"] == 1]
    pos_pool = df[df["label"] == 0]
    assert len(neg_pool) >= TOTAL_PER_CLASS and len(pos_pool) >= TOTAL_PER_CLASS, (
        f"Insufficient clean rows: neg={len(neg_pool)}, pos={len(pos_pool)}, need {TOTAL_PER_CLASS} each"
    )

    neg_520 = neg_pool.sample(n=TOTAL_PER_CLASS, random_state=SEED)
    pos_520 = pos_pool.sample(n=TOTAL_PER_CLASS, random_state=SEED)

    # Disjoint slice into Train (200k/class), Validation (30k/class), Test T2 (30k/class)
    train_df = pd.concat(
        [neg_520.iloc[:TRAIN_PER_CLASS], pos_520.iloc[:TRAIN_PER_CLASS]], ignore_index=True
    ).sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    val_df = pd.concat(
        [
            neg_520.iloc[TRAIN_PER_CLASS : TRAIN_PER_CLASS + VAL_PER_CLASS],
            pos_520.iloc[TRAIN_PER_CLASS : TRAIN_PER_CLASS + VAL_PER_CLASS],
        ],
        ignore_index=True,
    ).sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    test_df = pd.concat(
        [
            neg_520.iloc[TRAIN_PER_CLASS + VAL_PER_CLASS :],
            pos_520.iloc[TRAIN_PER_CLASS + VAL_PER_CLASS :],
        ],
        ignore_index=True,
    ).sample(frac=1.0, random_state=SEED).reset_index(drop=True)

    for split_name, part in [("train", train_df), ("validation", val_df), ("test", test_df)]:
        part["split"] = split_name
        part["source"] = "sentiment140_train.csv"

    all_520 = pd.concat([train_df, val_df, test_df], ignore_index=True)
    all_520 = all_520.rename(columns={"sentence": "text", "sentiment": "orig_sentiment"})

    # Verify zero overlap across splits and against external sets
    tr_k = set(train_df["key"])
    va_k = set(val_df["key"])
    te_k = set(test_df["key"])
    all_k = tr_k | va_k | te_k
    assert len(tr_k & va_k) == 0 and len(tr_k & te_k) == 0 and len(va_k & te_k) == 0
    assert len(all_k) == 520_000
    assert len(all_k & t1_keys) == 0
    assert len(all_k & pol_tv_keys) == 0
    assert len(all_k & s140_test_keys) == 0

    out_cols = ["orig_idx", "text", "label", "orig_sentiment", "source", "split"]
    out_520_path = SAMPLED / "sentiment140_520k.csv"
    all_520[out_cols].to_csv(out_520_path, index=False, encoding="utf-8")

    # Save individual sampled subsets for Phase 2/3 inspection
    split_cols = ["orig_idx", "text", "label", "orig_sentiment", "source"]
    train_path = SAMPLED / "sentiment140_train_400k.csv"
    val_path = SAMPLED / "sentiment140_val_60k.csv"
    test_path = SAMPLED / "sentiment140_test_60k.csv"
    all_520[all_520["split"] == "train"][split_cols].to_csv(train_path, index=False, encoding="utf-8")
    all_520[all_520["split"] == "validation"][split_cols].to_csv(val_path, index=False, encoding="utf-8")
    all_520[all_520["split"] == "test"][split_cols].to_csv(test_path, index=False, encoding="utf-8")

    manifest = {
        "phase": "Phase 1+2 - Data Quality, Cleaning (textsense_clean_v4), Leakage Removal & 520k Stratified Sampling",
        "preprocessing_version": PREPROCESSING_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": SEED,
        "source_files": {
            "Twitter_Data.csv": {"sha256": sha256_file(RAW / "Twitter_Data.csv"), "raw_rows": 162980},
            "Reddit_Data.csv": {"sha256": sha256_file(RAW / "Reddit_Data.csv"), "raw_rows": 37249},
            "sentiment140_train.csv": {"sha256": sha256_file(s140_train_path), "raw_rows": raw_rows},
            "sentiment140_test.csv": {"sha256": sha256_file(s140_test_path), "raw_rows": len(s140_test)},
        },
        "sentiment140_cleaning": {
            "raw_rows": raw_rows,
            "raw_counts_orig_sentiment": {str(k): int(v) for k, v in raw_counts.items()},
            "after_na_rows": after_na,
            "empty_key_rows_removed": empty_rows,
            "too_short_lt3_rows_removed": too_short_rows,
            "after_len_ge3_rows": after_len,
            "conflicting_label_groups_removed": len(conflict_keys),
            "conflicting_label_rows_removed": conflict_rows_removed,
            "duplicate_key_rows_removed": dup_rows_removed,
            "leakage_removed_overlap_T1": removed_t1,
            "leakage_removed_overlap_political_train_val": removed_pol_tv,
            "leakage_removed_overlap_s140_test": removed_s140_test,
            "clean_pool_rows": clean_pool_rows,
            "clean_pool_label_counts": {str(k): int(v) for k, v in pool_counts.items()},
        },
        "sampled_datasets": {
            "total_520k_file": "data/sampled/sentiment140_520k.csv",
            "total_520k_sha256": sha256_file(out_520_path),
            "total_rows": len(all_520),
            "label_mapping": {"orig_sentiment_0": "1 (Tiêu cực)", "orig_sentiment_1": "0 (Không tiêu cực)"},
            "splits": {
                "train_400k": {
                    "file": "data/sampled/sentiment140_train_400k.csv",
                    "sha256": sha256_file(train_path),
                    "rows": len(train_df),
                    "label_counts": {"0": int((train_df["label"] == 0).sum()), "1": int((train_df["label"] == 1).sum())},
                },
                "validation_60k": {
                    "file": "data/sampled/sentiment140_val_60k.csv",
                    "sha256": sha256_file(val_path),
                    "rows": len(val_df),
                    "label_counts": {"0": int((val_df["label"] == 0).sum()), "1": int((val_df["label"] == 1).sum())},
                },
                "test_T2_60k": {
                    "file": "data/sampled/sentiment140_test_60k.csv",
                    "sha256": sha256_file(test_path),
                    "rows": len(test_df),
                    "label_counts": {"0": int((test_df["label"] == 0).sum()), "1": int((test_df["label"] == 1).sum())},
                },
            },
            "leakage_checks": {
                "train_vs_val_overlap": 0,
                "train_vs_test_T2_overlap": 0,
                "val_vs_test_T2_overlap": 0,
                "all_520k_vs_T1_overlap": 0,
                "all_520k_vs_political_train_val_overlap": 0,
                "all_520k_vs_s140_test_overlap": 0,
                "internal_duplicates": 0,
            },
        },
    }
    manifest_path = SAMPLED / "data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Saved 520k dataset and manifest successfully.")
    print("Clean pool:", clean_pool_rows, pool_counts)
    print("Train 400k:", len(train_df), "Val 60k:", len(val_df), "Test T2 60k:", len(test_df))


if __name__ == "__main__":
    main()
