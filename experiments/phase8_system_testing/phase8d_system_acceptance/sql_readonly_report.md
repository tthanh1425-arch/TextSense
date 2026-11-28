# BÁO CÁO KIỂM TRA SQL SERVER CHỈ ĐỌC (GIAI ĐOẠN 8D-1)

**Ngày kiểm tra:** 2026-11-28  
**Trạng thái:** **`PASS`** *(Kết nối đọc thành công, tương thích schema 100%, 0 thao tác ghi).*

## 1. Cấu hình kết nối (Không lộ thông tin bí mật)
- **Biến môi trường `TEXTSENSE_SQLSERVER_CONNECTION_STRING`:** Không đặt; hệ thống tự dò qua `database.py` (`sql_server_connection_string()`).
- **ODBC Driver khả dụng:** `ODBC Driver 17 for SQL Server` (cùng `SQL Server`, `pyodbc 5.5.0`).
- **Database:** `TextSenseDB`.
- **Cơ chế xác thực:** Windows Authentication (`Trusted_Connection=yes;TrustServerCertificate=yes`), `timeout=4`, chế độ kết nối `readonly=True`.

## 2. Kết quả kiểm tra schema và số lượng bản ghi (`SELECT` chỉ đọc)

| Bảng | Tồn tại | Số cột | Số dòng hiện có | Trạng thái tương thích |
|---|:---:|---:|---:|---|
| `dbo.Tweets` | Có | `6` | `196.050` | **PASS** |
| `dbo.TweetTokens` | Có | `3` | `3.780.313` | **PASS** |
| `dbo.TrainingRuns` | Có | `20` | `7` | **PASS** |
| `dbo.PredictionBatches` | Có | `8` | `44` | **PASS** |
| `dbo.Predictions` | Có | `7` | `624.403` | **PASS** |
| `dbo.UserFeedback` | Có | `15` | `3` | **PASS** |
| `dbo.Users` | Có | `8` | `1` | **PASS** |

- **Foreign Keys:** `4` khóa ngoại đang hoạt động, khớp `02_SQL_SERVER/textsense.sql` và `03_GIAO_DIEN/database.py`.
- **Trạng thái từ ứng dụng (`sql_server_status()`):** `{'configured': True, 'available': True, 'message': 'Đã kết nối SQL Server; toàn bộ lịch sử dùng SQL Server.'}`.
- **Lưu ý vận hành:** Vì SQL Server thật đang bật và có sẵn dữ liệu (`44` batch, `624.403` predictions), mọi kiểm thử giao diện ở 8D-2 bắt buộc phải chạy qua test server cô lập có mock các hàm ghi DB.
