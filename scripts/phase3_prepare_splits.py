"""Phase 3: Organize v4-normalized splits in data/splits/, create nested E6 subsets,
verify integrity/nesting/leakage/SHA-256, and generate root manifest.json.
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

BASELINE_SPLITS = ROOT / "baseline_v3" / "splits" / "binary"
BASELINE_MANIFEST = ROOT / "baseline_v3" / "binary_manifest.json"
SAMPLED = ROOT / "data" / "sampled"
SPLITS = ROOT / "data" / "splits"
SEED = 42


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split_summary(df: pd.DataFrame, text_col: str = "text", label_col: str = "label") -> dict:
    vc = df[label_col].value_counts().sort_index().to_dict()
    return {
        "rows": int(len(df)),
        "label_counts": {str(int(k)): int(v) for k, v in vc.items()},
        "empty_after_v4": int((df[text_col].astype(str).str.len() == 0).sum()),
        "lt3_after_v4": int(((df[text_col].astype(str).str.len() > 0) & (df[text_col].astype(str).str.len() < 3)).sum()),
        "internal_duplicates": int(df[text_col].duplicated().sum()),
    }


def main() -> None:
    SPLITS.mkdir(parents=True, exist_ok=True)

    # 0. Verify baseline_v3 integrity before touching anything
    base_manifest = json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))
    t1_raw_path = BASELINE_SPLITS / "test.csv"
    t1_raw_sha = sha256_file(t1_raw_path)
    assert t1_raw_sha == base_manifest["split_file_sha256"]["test"], "baseline_v3 T1 SHA-256 mismatch!"

    # 1. Prepare political splits (preserving exact baseline_v3 split membership, applying v4 normalization)
    pol_train = pd.read_csv(BASELINE_SPLITS / "train.csv")
    pol_val = pd.read_csv(BASELINE_SPLITS / "validation.csv")
    pol_test = pd.read_csv(t1_raw_path)

    for name, df in [("political_train", pol_train), ("political_val", pol_val), ("political_test_T1", pol_test)]:
        df["text_v3"] = df["text"]
        df["text"] = df["text"].map(normalize_text)
        df["preprocessing_version"] = PREPROCESSING_VERSION

    pol_train_path = SPLITS / "political_train.csv"
    pol_val_path = SPLITS / "political_val.csv"
    pol_test_path = SPLITS / "political_test_T1.csv"

    pol_cols = ["source", "text", "text_v3", "category", "label", "preprocessing_version"]
    pol_train[pol_cols].to_csv(pol_train_path, index=False, encoding="utf-8")
    pol_val[pol_cols].to_csv(pol_val_path, index=False, encoding="utf-8")
    pol_test[pol_cols].to_csv(pol_test_path, index=False, encoding="utf-8")

    # 2. Prepare Sentiment140 splits (normalized with v4)
    s_train = pd.read_csv(SAMPLED / "sentiment140_train_400k.csv")
    s_val = pd.read_csv(SAMPLED / "sentiment140_val_60k.csv")
    s_test = pd.read_csv(SAMPLED / "sentiment140_test_60k.csv")

    for df in (s_train, s_val, s_test):
        df["text_raw"] = df["text"]
        df["text"] = df["text"].map(normalize_text)
        df["preprocessing_version"] = PREPROCESSING_VERSION

    s_cols = ["orig_idx", "source", "text", "text_raw", "orig_sentiment", "label", "preprocessing_version"]
    s_train_path = SPLITS / "s140_train_400k.csv"
    s_val_path = SPLITS / "s140_val_60k.csv"
    s_test_path = SPLITS / "s140_test_T2_60k.csv"

    s_train[s_cols].to_csv(s_train_path, index=False, encoding="utf-8")
    s_val[s_cols].to_csv(s_val_path, index=False, encoding="utf-8")
    s_test[s_cols].to_csv(s_test_path, index=False, encoding="utf-8")

    # 3. Create nested E6 subsets from s_train_400k (50k -> 120k -> 400k)
    # Deterministic slice: first N/2 per class from s_train (which was already shuffled with SEED=42)
    neg_400 = s_train[s_train["label"] == 1]
    pos_400 = s_train[s_train["label"] == 0]
    assert len(neg_400) == 200_000 and len(pos_400) == 200_000

    e6_120k = (
        pd.concat([neg_400.iloc[:60_000], pos_400.iloc[:60_000]], ignore_index=True)
        .sample(frac=1.0, random_state=SEED)
        .reset_index(drop=True)
    )
    e6_50k = (
        pd.concat([neg_400.iloc[:25_000], pos_400.iloc[:25_000]], ignore_index=True)
        .sample(frac=1.0, random_state=SEED)
        .reset_index(drop=True)
    )

    e6_50k_path = SPLITS / "s140_train_e6_50k.csv"
    e6_120k_path = SPLITS / "s140_train_e6_120k.csv"
    e6_50k[s_cols].to_csv(e6_50k_path, index=False, encoding="utf-8")
    e6_120k[s_cols].to_csv(e6_120k_path, index=False, encoding="utf-8")

    # 4. Verify strict nesting and zero leakage
    idx_50 = set(e6_50k["orig_idx"])
    idx_120 = set(e6_120k["orig_idx"])
    idx_400 = set(s_train["orig_idx"])
    assert len(idx_50) == 50_000 and len(idx_120) == 120_000 and len(idx_400) == 400_000
    assert idx_50.issubset(idx_120), "E6-50k is not a subset of E6-120k!"
    assert idx_120.issubset(idx_400), "E6-120k is not a subset of E6-400k!"

    t1_k = set(pol_test["text"])
    t2_k = set(s_test["text"])
    ptr_k = set(pol_train["text"])
    pva_k = set(pol_val["text"])
    str_k = set(s_train["text"])
    sva_k = set(s_val["text"])

    leakage = {
        "pol_train_vs_T1": len(ptr_k & t1_k),
        "pol_val_vs_T1": len(pva_k & t1_k),
        "pol_train_vs_pol_val": len(ptr_k & pva_k),
        "s140_train_vs_T1": len(str_k & t1_k),
        "s140_val_vs_T1": len(sva_k & t1_k),
        "T2_vs_T1": len(t2_k & t1_k),
        "s140_train_vs_s140_val": len(str_k & sva_k),
        "s140_train_vs_T2": len(str_k & t2_k),
        "s140_val_vs_T2": len(sva_k & t2_k),
        "s140_train_vs_pol_train": len(str_k & ptr_k),
        "s140_train_vs_pol_val": len(str_k & pva_k),
    }
    assert all(v == 0 for v in leakage.values()), f"Leakage detected: {leakage}"

    # 5. Build root manifest.json
    datasets = {
        "political_train": {
            "path": "data/splits/political_train.csv",
            "source": "Twitter_Data.csv + Reddit_Data.csv (baseline_v3 train split)",
            "purpose": "Train",
            "preprocessing_version": PREPROCESSING_VERSION,
            "random_seed": SEED,
            "sha256": sha256_file(pol_train_path),
            **split_summary(pol_train),
        },
        "political_val": {
            "path": "data/splits/political_val.csv",
            "source": "Twitter_Data.csv + Reddit_Data.csv (baseline_v3 validation split)",
            "purpose": "Validation",
            "preprocessing_version": PREPROCESSING_VERSION,
            "random_seed": SEED,
            "sha256": sha256_file(pol_val_path),
            **split_summary(pol_val),
        },
        "political_test_T1": {
            "path": "data/splits/political_test_T1.csv",
            "source": "Twitter_Data.csv + Reddit_Data.csv (baseline_v3 test split - PROTECTED)",
            "purpose": "Test",
            "preprocessing_version": PREPROCESSING_VERSION,
            "random_seed": SEED,
            "baseline_v3_raw_sha256": t1_raw_sha,
            "sha256": sha256_file(pol_test_path),
            **split_summary(pol_test),
        },
        "s140_train_400k": {
            "path": "data/splits/s140_train_400k.csv",
            "source": "sentiment140_train.csv",
            "purpose": "Train",
            "preprocessing_version": PREPROCESSING_VERSION,
            "random_seed": SEED,
            "sha256": sha256_file(s_train_path),
            **split_summary(s_train),
        },
        "s140_val_60k": {
            "path": "data/splits/s140_val_60k.csv",
            "source": "sentiment140_train.csv",
            "purpose": "Validation",
            "preprocessing_version": PREPROCESSING_VERSION,
            "random_seed": SEED,
            "sha256": sha256_file(s_val_path),
            **split_summary(s_val),
        },
        "s140_test_T2_60k": {
            "path": "data/splits/s140_test_T2_60k.csv",
            "source": "sentiment140_train.csv",
            "purpose": "Test",
            "preprocessing_version": PREPROCESSING_VERSION,
            "random_seed": SEED,
            "sha256": sha256_file(s_test_path),
            **split_summary(s_test),
        },
        "s140_train_e6_50k": {
            "path": "data/splits/s140_train_e6_50k.csv",
            "source": "sentiment140_train.csv (nested subset of s140_train_400k)",
            "purpose": "Train",
            "preprocessing_version": PREPROCESSING_VERSION,
            "random_seed": SEED,
            "sha256": sha256_file(e6_50k_path),
            **split_summary(e6_50k),
        },
        "s140_train_e6_120k": {
            "path": "data/splits/s140_train_e6_120k.csv",
            "source": "sentiment140_train.csv (nested subset of s140_train_400k)",
            "purpose": "Train",
            "preprocessing_version": PREPROCESSING_VERSION,
            "random_seed": SEED,
            "sha256": sha256_file(e6_120k_path),
            **split_summary(e6_120k),
        },
    }

    manifest = {
        "project": "TextSense V4",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "preprocessing_version": PREPROCESSING_VERSION,
        "random_seed": SEED,
        "label_convention": {"0": "Không tiêu cực (Non-negative)", "1": "Tiêu cực (Negative)"},
        "e6_nesting_relation": {
            "description": "E6-50k ⊂ E6-120k ⊂ E6-400k (all stratified 50/50 by orig_idx from s140_train_400k)",
            "e6_50k_in_e6_120k": True,
            "e6_120k_in_e6_400k": True,
        },
        "baseline_v3_integrity": {
            "test_csv_sha256_expected": base_manifest["split_file_sha256"]["test"],
            "test_csv_sha256_actual": t1_raw_sha,
            "untouched": True,
        },
        "leakage_checks": leakage,
        "datasets": datasets,
    }

    manifest_path = ROOT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Phase 3 splits & manifest.json created successfully.")
    for k, v in datasets.items():
        print(f"  {k}: rows={v['rows']}, labels={v['label_counts']}, sha256={v['sha256'][:12]}")


if __name__ == "__main__":
    main()
