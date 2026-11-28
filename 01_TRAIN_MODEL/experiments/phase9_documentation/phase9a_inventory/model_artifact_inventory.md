# KIỂM KÊ HỒ SƠ MÔ HÌNH CHÍNH THỨC (GIAI ĐOẠN 9A)

- **Mô hình chính thức:** `E0-Artifact` (`baseline_v3/binary_linear_svm.joblib` ≡ `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib`).
- **SHA-256 xác minh:** `474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a` (khớp 100%).
- **Cấu hình:** `textsense_clean_v3_context` + `TfidfVectorizer(ngram_range=(1,2), min_df=2, max_features=40000, sublinear_tf=True, dtype=float32)` + `LinearSVC(C=1.0, class_weight=None, max_iter=3000, random_state=42)`, `threshold = -0.19220128657328076`, quy tắc `decision_score > threshold → 1` (Tiêu cực), ngược lại `0` (Không tiêu cực).
- **Bộ tài liệu Giai đoạn 7 (`experiments/phase7_model_finalization/`):**
  - `model_card.md` (`VERIFIED`)
  - `deployment_config.md` (`VERIFIED`)
  - `model_selection_decision.md` (`VERIFIED`)
  - `integration_checklist.md` (`VERIFIED`)
  - `artifact_integrity_report.md` (`VERIFIED`)
  - `phase7_manifest.json` (`VERIFIED`)
  - `phase7_completion_report.md` (`VERIFIED`)
- Tất cả 7 tài liệu trên đủ điều kiện trích dẫn trực tiếp vào báo cáo học thuật cuối cùng.
