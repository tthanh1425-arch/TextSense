# BÁO CÁO KIỂM TOÁN TOÀN VẸN ARTIFACT (`E0-Artifact`)

**Ngày kiểm toán:** 2026-11-27  
**Trạng thái:** **`PASS`**

## 1. Xác minh tệp và SHA-256
- **Artifact đóng băng (`baseline_v3/binary_linear_svm.joblib`):** `474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a`
- **Artifact triển khai (`01_TRAIN_MODEL/outputs/binary_linear_svm.joblib`):** `474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a`
- **Khớp `experiments/freeze_manifest.json`:** `True` (`100%`)

## 2. Cấu trúc nội tại của artifact (`joblib.load`)
- **Kiểu artifact:** `dict` gồm 11 khóa: `['pipeline', 'task', 'class_names', 'threshold', 'sklearn_version', 'created_utc', 'python_version', 'data_sha256', 'selected_C', 'preprocessing_version', 'trained_on']`.
- **`task`:** `'binary'`
- **`trained_on`:** `'train+validation'`
- **`preprocessing_version`:** `'textsense_clean_v3_context'`
- **`threshold`:** `-0.19220128657328076` (được lưu trực tiếp trong artifact)
- **`selected_C`:** `1.0`
- **`class_names`:** `{0: 'Không tiêu cực', 1: 'Tiêu cực'}`
- **`sklearn_version` / `python_version`:** `'1.9.1'` / `'3.14.8'` (khớp hoàn toàn môi trường hiện tại `.venv-1`)
- **`data_sha256`:** `cb38aecc6397db54434596376434be6bec61a2896d48c969c18907b61f5be517`
- **`pipeline` steps:**
  1. `tfidf`: `TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_features=40000, sublinear_tf=True, dtype=float32)` — `len(vocabulary_) = 40.000`
  2. `classifier`: `LinearSVC(C=1.0, class_weight=None, max_iter=3000, random_state=42)` — `classes_ = [0, 1]`, `coef_.shape = (1, 40000)` (`float64`), `intercept_ = [-1.1482702]`.
