# CẤU HÌNH TRIỂN KHAI CHÍNH THỨC (`E0-Artifact`)

## 1. Định danh & Artifact
- **Model ID:** `E0-Artifact` (`baseline_v3`)
- **Artifact đóng băng:** `baseline_v3/binary_linear_svm.joblib`
- **Artifact đang triển khai:** `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib`
- **SHA-256 (khớp 100% ở cả hai đường dẫn):** `474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a`
- **Preprocessing Version:** `textsense_clean_v3_context`

## 2. Tham số Vectorizer & Classifier
- **Vectorizer:** `TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_features=40000, sublinear_tf=True, dtype=numpy.float32)` (40.000 features).
- **Classifier:** `LinearSVC(C=1.0, class_weight=None, max_iter=3000, random_state=42, loss='squared_hinge', penalty='l2')`.

## 3. Quy tắc ngưỡng, dự đoán và ánh xạ nhãn
- **Threshold lưu trong artifact:** `artifact['threshold'] = -0.19220128657328076`.
- **Chiều so sánh xác minh từ `03_GIAO_DIEN/predict.py` (dòng 132–134):**
  - `decision_score = pipeline.decision_function([cleaned_text])`
  - `decision_score > -0.19220128657328076` → `predicted_label = 1` (**Tiêu cực / `Có nội dung tiêu cực`**)
  - `decision_score <= -0.19220128657328076` → `predicted_label = 0` (**Không tiêu cực / `Không phát hiện nội dung tiêu cực`**)
- **Phân biệt Score và Probability:** `LinearSVC` chỉ xuất `decision_score` (khoảng cách có dấu tới siêu phẳng phân tách), **không** phải xác suất đã hiệu chỉnh. Không hiển thị `decision_score` dưới dạng `% xác suất` nếu chưa qua hiệu chỉnh xác suất riêng.

## 4. Yêu cầu đầu vào & Xử lý lỗi
- Ngôn ngữ: Tiếng Anh. Độ dài sau chuẩn hóa tối đa: `2.000` ký tự (`MAX_TEXT_CHARS = 2000`).
- Các trạng thái từ chối hợp lệ (không trả nhãn `predicted_label=None`):
  - Chuỗi chỉ là URL (`URL_PATTERN.fullmatch`): `'Đây là đường dẫn, không phải nội dung bình luận'`
  - Chuỗi rỗng sau `normalize_text`: `'Văn bản rỗng'`
  - Vượt quá `2.000` ký tự: `'Vượt quá 2,000 ký tự'`
  - Tỷ lệ ký tự có dấu tiếng Việt > 3%: `'Văn bản có dấu tiếng Việt; mô hình được huấn luyện trên dữ liệu tiếng Anh, không trả nhãn.'`
- Ngoại lệ hệ thống: Thiếu file `.joblib` → `FileNotFoundError`; cấu trúc dict thiếu `pipeline` hoặc `class_names` → `ValueError`; `batch_size < 1` → `ValueError`; lệch `sklearn_version` hoặc `preprocessing_version` → `RuntimeWarning`.

## 5. Schema đầu ra dự kiến (`predict.py`)
Mỗi bản ghi trả về `dict`:
- `text`: văn bản gốc
- `predicted_label`: `0 | 1 | None`
- `label_name`: `'Không phát hiện nội dung tiêu cực' | 'Có nội dung tiêu cực' | None`
- `task`: `'binary'`
- `decision_score`: `float | None` (khi `status == 'ok'`)
- `decision_threshold`: `float` (khi `status == 'ok'`)
- `status`: `'ok'` hoặc thông báo lý do từ chối

## 6. Phiên bản thư viện yêu cầu (theo Freeze Manifest)
- Python `3.14.8`
- `scikit-learn == 1.9.1`, `pandas == 3.1.1`, `numpy == 2.5.5`, `scipy == 1.18.1`, `joblib == 1.6.0`
