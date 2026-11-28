# DANH SÁCH KIỂM TRA TÍCH HỢP CHO GIAI ĐOẠN 8 (`integration_checklist.md`)

*(Chỉ đọc mã nguồn hiện tại — chưa chỉnh sửa `predict.py`, `serve_textsense.py`, giao diện hoặc SQL Server.)*

## 1. Thành phần tích hợp hiện tại đã kiểm tra
- **Đường dẫn tải model:** `03_GIAO_DIEN/predict.py` định nghĩa `OUTPUT = Path(__file__).resolve().parent.parent / '01_TRAIN_MODEL' / 'outputs'`; `serve_textsense.py` tải `OUTPUT / 'binary_linear_svm.joblib'`. SHA-256 tệp này khớp 100% với `baseline_v3/binary_linear_svm.joblib` (`474b0f5fdce1...`).
- **Tiền xử lý:** `03_GIAO_DIEN/predict.py` cài đặt `normalize_text` với `PREPROCESSING_VERSION = 'textsense_clean_v3_context'`, khớp 100% với `baseline_v3/predict.py` và `artifact['preprocessing_version']`.
- **Áp dụng threshold & ánh xạ nhãn:** `predict.py` (dòng 133–134) dùng `decision_scores > float(artifact.get('threshold', 0.0))` → `1` (`Có nội dung tiêu cực`), ngược lại `0` (`Không phát hiện nội dung tiêu cực`).
- **Xử lý đầu vào biên & nhiều văn bản:** `predict.py` xử lý theo lô (`batch_size=512`), lọc URL, rỗng, >2000 ký tự, tiếng Việt có dấu (>3%) trước khi gọi `decision_function`.

## 2. Các điểm rủi ro / cần kiểm thử kỹ ở Giai đoạn 8
1. **Khác biệt giữa `infer_comment()` (Web đơn) và `predict()` (Notebook/Batch CSV):**
   - Trong `03_GIAO_DIEN/serve_textsense.py` (dòng 834–839), khi phân tích 1 bình luận đơn, giao diện gọi thêm `analyze_sentence_breakdown(text)` (tách mệnh đề tương phản/câu) và áp dụng quy tắc **OR** (`code == 1 or has_negative_part`). Do đó, khi chạy kiểm thử đối chiếu 100 câu giữa notebook và giao diện ở Giai đoạn 8, cần kiểm tra cả **cấp độ `predict()` trực tiếp** lẫn **hành vi tách câu của `infer_comment()`** đối với các câu ghép nhiều mệnh đề.
2. **Hiển thị `confidence` trong `serve_textsense.py` (dòng 848–849):**
   - API hiện tính `confidence = 1 / (1 + exp(-|decision_score - threshold|))`. Cần kiểm tra giao diện không diễn giải nhầm giá trị này là xác suất đã hiệu chỉnh.
3. **Tham chiếu notebook cũ trong thông báo lỗi của `predict.py`:**
   - Dòng 78, 85, 96, 177 của `03_GIAO_DIEN/predict.py` vẫn nhắc tên `TextSense_Notebook_SQLServer_Hoan_Thien_v2.ipynb` (lỗi text thông báo, không ảnh hưởng logic suy luận).
4. **Tệp `03_GIAO_DIEN/web/model_weights.json` cũ:**
   - Tệp tĩnh không được `serve_textsense.py` sử dụng, chứa `threshold=-0.2203` cũ; cần xác nhận giao diện web chỉ gọi `/api/analyze` và `/api/batch`.
5. **Kiểm thử SQL Server chế độ chỉ đọc:**
   - Kiểm tra kết nối, đọc schema `dbo.TrainingRuns`, `dbo.PredictionBatches`, `dbo.Predictions`, `dbo.UserFeedback`, `dbo.Users`; không ghi dữ liệu thử nghiệm khi chưa được cho phép.
