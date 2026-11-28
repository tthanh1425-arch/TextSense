# BÁO CÁO XÁC MINH ARTIFACT (`E0-Artifact`) – GIAI ĐOẠN 8A

**Ngày kiểm tra:** 2026-11-28  
**Trạng thái:** **`PASS`**

## 1. Đối chiếu SHA-256

| Tệp | SHA-256 thực tế | Khớp giá trị phê duyệt (`474b0f5fdce1...`) |
|---|---|---:|
| `baseline_v3/binary_linear_svm.joblib` | `474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a` | **True** |
| `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib` | `474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a` | **True** |

## 2. Xác minh cấu trúc bên trong (`joblib.load`)
- **Khả năng load:** Thành công trên Python `3.14.8` + `scikit-learn 1.9.1` + `joblib 1.6.0`.
- **`preprocessing_version`:** `'textsense_clean_v3_context'`
- **`threshold`:** `-0.19220128657328076`
- **`class_names`:** `{0: 'Không tiêu cực', 1: 'Tiêu cực'}`
- **`trained_on`:** `'train+validation'` (`selected_C = 1.0`, `data_sha256 = cb38aecc6397db54434596376434be6bec61a2896d48c969c18907b61f5be517`)
- **Pipeline (`tfidf` → `classifier`):**
  - `tfidf`: `TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_features=40000, sublinear_tf=True, dtype=float32)`, `len(vocabulary_) = 40.000`.
  - `classifier`: `LinearSVC(C=1.0, class_weight=None, max_iter=3000, random_state=42)`, `classes_ = [0, 1]`, `coef_.shape = (1, 40000)` (`float64`), `intercept_ = [-1.1482702]`.
