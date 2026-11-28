# KIỂM KÊ KIẾN TRÚC VÀ LUỒNG DỮ LIỆU HỆ THỐNG (GIAI ĐOẠN 8A)

## 1. Luồng suy luận thực tế (`03_GIAO_DIEN/predict.py`)

`Input → Normalize (textsense_clean_v3_context) → Filter (URL / Empty / >2000 chars / Vietnamese >3%) → TfidfVectorizer → LinearSVC.decision_function → Threshold (> -0.19220128657328076) → Label (1 / 0)`

- **Đường dẫn tải artifact (`predict.py` dòng 14, 75–87):** `OUTPUT / 'binary_linear_svm.joblib'` (`01_TRAIN_MODEL/outputs/binary_linear_svm.joblib`), cache theo `(path, mtime_ns, file_size)`.
- **Batching (`predict.py` dòng 128–137):** Xử lý theo lô `batch_size = 512`.
- **Ánh xạ nhãn (`predict.py` dòng 13, 134):**
  - `decision_score > threshold` → `1` (`'Có nội dung tiêu cực'`)
  - `decision_score <= threshold` → `0` (`'Không phát hiện nội dung tiêu cực'`)

## 2. Khác biệt giữa `predict()` và `infer_comment()` (`serve_textsense.py`)

| Thành phần | `predict()` (`predict.py` & `/api/batch`) | `infer_comment()` (`serve_textsense.py` dòng 818–860, `/api/analyze`) |
|---|---|---|
| Phạm vi áp dụng | Phân tích cả chuỗi văn bản đầu vào (1 lần) | Phân tích cả chuỗi **VÀ** tách mệnh đề (`analyze_sentence_breakdown`) |
| Quy tắc quyết định | `code = 1` nếu `decision_score > threshold` | `final_code = 1` nếu `code == 1 OR negative_parts > 0` (quy tắc **OR**) |
| Trường `confidence` | Không có (chỉ trả `decision_score` và `decision_threshold`) | Tính heuristic `1 / (1 + exp(-abs(decision_score - threshold)))` (dòng 848–849) |

## 3. API Endpoints (`serve_textsense.py`, cổng mặc định `8502`) & Giao diện (`web/app.js`)

- **Điểm khởi chạy:** `03_GIAO_DIEN/serve_textsense.py` (`ThreadingHTTPServer` trên `127.0.0.1:8502` / `TEXTSENSE_PORT`).
- **API GET:** `/api/config`, `/api/health`, `/api/model-info`, `/api/auth/me`, `/api/auth/google`, `/api/auth/google/callback`, `/api/history/batches`, `/api/history/predictions`, `/api/feedback`, `/api/stats`, `/api/stats/term-comments`, và tệp tĩnh `/`.
- **API POST:** `/api/analyze` (phân tích 1 câu), `/api/sentences` (tách mệnh đề), `/api/columns` (đọc cột CSV/XLSX), `/api/batch` (phân tích hàng loạt), `/api/export-xlsx`, `/api/feedback`, `/api/feedback/status`, `/api/auth/{register,login,logout}`.
- **Tệp tĩnh đáng chú ý:** `03_GIAO_DIEN/web/model_weights.json` (chứa `threshold=-0.2203` cũ) **không** được `web/app.js` hay `serve_textsense.py` gọi tới.
- **Tương tác SQL Server:** `/api/analyze` (dòng 1051), `/api/batch` (dòng 1207), `/api/feedback` (dòng 1072) đều gọi hàm ghi vào `database.py` nếu SQL Server khả dụng.
