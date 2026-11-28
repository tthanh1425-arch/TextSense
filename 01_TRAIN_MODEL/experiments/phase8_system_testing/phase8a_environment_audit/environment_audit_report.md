# BÁO CÁO KIỂM KÊ MÔI TRƯỜNG & CẤU TRÚC DỰ ÁN (GIAI ĐOẠN 8A)

**Thời điểm kiểm kê:** 2026-11-28T01:35:00+07:00  
**Chế độ:** Chỉ đọc (không sửa mã nguồn, không sửa artifact, không cài đặt thư viện, không ghi SQL Server).

---

## 1. Cấu trúc thư mục dự án

| Thư mục / Thành phần | Vai trò thực tế | Tệp trọng tâm đã kiểm kê |
|---|---|---|
| `01_TRAIN_MODEL/` | Huấn luyện & artifact triển khai | `TextSense_Notebook_SQLServer_Hoan_Thien_v3.ipynb`, `requirements.txt`, `outputs/binary_linear_svm.joblib` |
| `02_SQL_SERVER/` | Schema & driver SQL Server | `textsense.sql` (257 dòng), `requirements.txt` (`pyodbc>=5.2,<6`) |
| `03_GIAO_DIEN/` | Web server, CLI suy luận & DB client | `serve_textsense.py` (1.570 dòng), `predict.py` (195 dòng), `database.py` (848 dòng), `web/{index.html,app.js,style.css,csv_viewer.js,model_weights.json}` |
| `baseline_v3/` | Bản đóng băng baseline (`E0-Artifact`) | `binary_linear_svm.joblib`, `binary_manifest.json`, `binary_metrics.json`, `predict.py`, `splits/binary/{train,validation,test}.csv` |
| `data/` | Dữ liệu thô, mẫu & split V4 | `raw/`, `sampled/`, `splits/` (8 tệp split chuẩn hóa `textsense_clean_v4`) |
| `experiments/` | Kết quả thí nghiệm E0–E6 & Giai đoạn 5, 7 | `freeze_manifest.json`, `freeze_gate_audit_report.md`, `phase5_final_evaluation/`, `phase7_model_finalization/` |
| `tests/` | Kiểm thử tự động | `test_web_sentiment.py` (11 test cases web/DB mock), `test_negation_e3.py` (30 test cases E3) |

---

## 2. Môi trường Python & Thư viện (`.venv-1`)

**Python:** `3.14.8` (`C:\Users\vothi\OneDrive\Desktop\TextSense\.venv-1\Scripts\python.exe`)

| Thư viện | Phiên bản yêu cầu (Artifact / `requirements.txt`) | Phiên bản cài đặt thực tế | Trạng thái |
|---|---|---|---|
| `scikit-learn` | `1.9.1` | `1.9.1` | Khớp 100% |
| `pandas` | `3.1.1` (`>=2.0,<4`) | `3.1.1` | Khớp 100% |
| `numpy` | `2.5.5` (`>=1.24,<3`) | `2.5.5` | Khớp 100% |
| `scipy` | `1.18.1` | `1.18.1` | Khớp 100% |
| `joblib` | `1.6.0` (`>=1.3,<2`) | `1.6.0` | Khớp 100% |
| `openpyxl` | `>=3.1,<4` (API Excel) | `3.1.5` | Đạt |
| `pyodbc` | `>=5.2,<6` (SQL Server) | `5.5.0` | Đạt |
| `vaderSentiment` | `>=3.3.2` (Notebook) | `3.3.2` | Đạt |
| `matplotlib` | `>=3.8,<4` (Notebook) | `3.11.2` | Đạt |
| `pytest` | Tùy chọn cho `tests/` | **NOT INSTALLED** | Lưu ý (`test_web_sentiment.py` có `__main__` fallback) |
| `fastapi` / `flask` | Không sử dụng | **NOT INSTALLED** | Không ảnh hưởng (`serve_textsense.py` dùng `http.server.ThreadingHTTPServer` chuẩn Python) |

---

## 3. Cấu hình SQL Server (Chỉ đọc mã nguồn)

Kiểm tra từ `03_GIAO_DIEN/database.py` (dòng 17–68) và `02_SQL_SERVER/textsense.sql`:
- **Biến môi trường cấu hình:** `TEXTSENSE_SQLSERVER_CONNECTION_STRING` (nếu trống, tự dò driver `ODBC Driver 18 for SQL Server` → `ODBC Driver 17 for SQL Server` → `SQL Server` trên các server `localhost`, `.\SQLEXPRESS`, `(localdb)\MSSQLLocalDB`).
- **Database:** `TextSenseDB`.
- **Xác thực mặc định:** `Trusted_Connection=yes;TrustServerCertificate=yes;` (Windows Authentication).
- **Bảng schema (`textsense.sql`):** `dbo.Tweets`, `dbo.TweetTokens`, `dbo.TrainingRuns`, `dbo.PredictionBatches`, `dbo.Predictions`, `dbo.UserFeedback`, `dbo.Users`.
- **Trạng thái kết nối thực tế ở môi trường kiểm tra:** Chưa xác minh lại trong 8A (`NOT VERIFIED` trong 8A; lần kiểm tra trước đó ở Giai đoạn 0 báo `available: False` do chưa tìm thấy SQL Server instance hoạt động). Việc kiểm thử kết nối và đọc schema sẽ thực hiện ở bước chuyên biệt sau khi được phê duyệt.
