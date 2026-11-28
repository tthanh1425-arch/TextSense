# SỔ ĐĂNG KÝ RỦI RO KỸ THUẬT (`risk_register.md`) – GIAI ĐOẠN 8A

| ID | Rủi ro | Mức độ | Bằng chứng mã nguồn | Hướng kiểm thử ở Giai đoạn 8B/8C |
|---|---|---|---|---|
| R1 | Khác biệt kết quả giữa `predict()` (notebook/batch) và `infer_comment()` (web đơn) trên câu ghép nhiều mệnh đề | **High** | `serve_textsense.py` dòng 834–839 (`code == 1 or has_negative_part`) vs `predict.py` dòng 132–134 | Kiểm thử đối chiếu 100 câu ở cả 2 cấp độ: `predict()` trực tiếp và `/api/analyze` |
| R2 | Trường `confidence` trong API dễ bị hiểu nhầm là xác suất đã hiệu chỉnh | **Medium** | `serve_textsense.py` dòng 848–849 (`1 / (1 + exp(-margin))`) | Kiểm tra UI không gắn nhãn `% xác suất` cho `confidence` |
| R3 | Kiểm thử API `/api/analyze` hoặc `/api/batch` có thể ghi dữ liệu thử nghiệm vào SQL Server nếu DB đang bật | **High** | `serve_textsense.py` dòng 1051, 1207 gọi `record_prediction_batch()` | Khi chạy test API, dùng mock `record_prediction_batch` hoặc xác nhận DB đang ngắt/chỉ đọc |
| R4 | SQL Server không khả dụng ở môi trường cục bộ | **Medium** | `database.py` dòng 80–106; Giai đoạn 0 ghi nhận `available: False` | Kiểm tra kết nối read-only & graceful fallback (`history_saved=False`) ở bước DB chuyên biệt |
| R5 | Thiếu `pytest` trong `.venv-1` | **Low** | `importlib.metadata` báo `pytest: NOT INSTALLED` | Chạy `tests/test_web_sentiment.py` qua `python` (`__main__` runner) |
| R6 | Tệp tĩnh `03_GIAO_DIEN/web/model_weights.json` chứa threshold cũ (`-0.2203`) | **Low** | `03_GIAO_DIEN/web/model_weights.json` vs `E0-Artifact` (`-0.192201`) | Xác nhận `app.js` và `serve_textsense.py` không đọc tệp này |
| R7 | Thông báo lỗi trong `predict.py` nhắc tên notebook cũ `v2` | **Low** | `03_GIAO_DIEN/predict.py` dòng 78, 85, 96, 177 | Ghi nhận lỗi văn bản (không ảnh hưởng suy luận) |
| R8 | Đầu vào biên (rỗng, chỉ dấu câu, >2000 ký tự, tiếng Việt, URL, Unicode) | **Medium** | `predict.py` dòng 113–125, `serve_textsense.py` dòng 822–832 | Kiểm thử đầy đủ các ca biên ở bước 8B |
| R9 | Lệch artifact giữa `baseline_v3/` và `01_TRAIN_MODEL/outputs/` | **Critical** *(Đã kiểm soát)* | Cả 2 khớp SHA-256 `474b0f5fdce1...` | Kiểm tra lại hash trước mỗi đợt test |
| R10 | Sai khác môi trường thư viện (`sklearn` 1.9.1) | **Medium** *(Đã kiểm soát)* | `.venv-1` khớp 100% phiên bản tạo artifact (`3.14.8` / `1.9.1`) | Dùng cố định `.venv-1` trong mọi bước kiểm thử |
