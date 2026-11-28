# BÁO CÁO AN TOÀN CƠ SỞ DỮ LIỆU (GIAI ĐOẠN 8C)

## 1. Cơ chế cô lập thao tác ghi
Trước khi khởi động test server tạm trên `127.0.0.1:64184`, `run_phase8c_tests.py` đã:
1. Gắn mock thay thế toàn bộ hàm DB trên cả hai module `database` và `serve_textsense`: `sql_server_status`, `record_prediction_batch`, `record_user_feedback`, `update_feedback_status`.
2. Chặn trực tiếp `pyodbc.connect` (ném `AssertionError` nếu có bất kỳ kết nối ODBC thật nào được gọi).

## 2. Bằng chứng không ghi SQL Server thật
- Tổng số lần gọi vào `DbMockTracker`: **`61` lần** (gồm `/api/health`, `/api/analyze`, `/api/batch`, `/api/feedback`).
- `0` kết nối thật tới SQL Server; `pyodbc.connect` không hề được kích hoạt.
- Toàn bộ response `/api/analyze` trả `history_saved: false`, `/api/batch` trả `X-History-Saved: false`.
- **Cảnh báo vận hành (Rủi ro đã xác nhận):** Nếu chạy test API trên môi trường có SQL Server đang bật mà **không** mock `record_prediction_batch` và `record_user_feedback`, thì `/api/analyze`, `/api/batch` và `/api/feedback` **sẽ ghi dữ liệu thử nghiệm trực tiếp vào `dbo.PredictionBatches`, `dbo.Predictions`, `dbo.UserFeedback`**.
