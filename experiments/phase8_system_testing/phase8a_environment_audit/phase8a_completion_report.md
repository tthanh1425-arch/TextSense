# BÁO CÁO HOÀN THÀNH GIAI ĐOẠN 8A – KIỂM KÊ & XÁC MINH MÔI TRƯỜNG

**Ngày hoàn thành:** 2026-11-28  
**Kết luận Giai đoạn 8A:** **`PASS WITH WARNINGS`**

## 1. Kết quả kiểm tra theo tiêu chí nghiệm thu
- [x] Kiểm kê đầy đủ các thành phần chính (`01_TRAIN_MODEL`, `02_SQL_SERVER`, `03_GIAO_DIEN`, `baseline_v3`, `experiments`, `data`, `tests`).
- [x] Xác định chính xác môi trường `.venv-1`: Python `3.14.8`, `scikit-learn 1.9.1`, `pandas 3.1.1`, `numpy 2.5.5`, `scipy 1.18.1`, `joblib 1.6.0`, `openpyxl 3.1.5`, `pyodbc 5.5.0`. *(Cảnh báo nhẹ: `pytest` chưa cài, dùng `python` chạy `__main__` của `test_web_sentiment.py`.)*
- [x] SHA-256 của cả `baseline_v3/binary_linear_svm.joblib` và `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib` đều khớp `474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a`.
- [x] Artifact load thành công, cấu hình khớp 100% hồ sơ Giai đoạn 7.
- [x] Xác định rõ luồng suy luận thực tế và sự khác biệt giữa `predict()` và `infer_comment()` (quy tắc OR khi tách mệnh đề).
- [x] Xác định đầy đủ API endpoints (`serve_textsense.py`, cổng `8502`) và các lời gọi `fetch` trong `web/app.js`.
- [x] Đọc cấu hình SQL Server (`database.py`, `textsense.sql`) mà không lộ thông tin bí mật, không chạy lệnh ghi. *(Trạng thái kết nối sống SQL Server: `NOT VERIFIED` trong 8A, chuyển sang bước kiểm thử DB chuyên biệt.)*
- [x] Không có file khóa nào bị chỉnh sửa; không có dữ liệu nào được ghi vào DB; đã tạo đủ 6 tệp hồ sơ 8A.

## 2. Điều kiện chuyển sang Giai đoạn 8B
- Đề xuất tiến hành **Giai đoạn 8B**: (1) kiểm thử parity 100 câu `T1`/`T2` giữa `predict()` và `serve_textsense.py` (có xét trường hợp tách mệnh đề), (2) kiểm thử đầu vào biên, (3) kiểm thử API với mock DB để không ghi dữ liệu thử nghiệm, và (4) kiểm tra SQL Server ở chế độ chỉ đọc.

*(Đã dừng hoàn toàn sau Giai đoạn 8A, chờ người phụ trách phê duyệt chuyển sang Giai đoạn 8B.)*
