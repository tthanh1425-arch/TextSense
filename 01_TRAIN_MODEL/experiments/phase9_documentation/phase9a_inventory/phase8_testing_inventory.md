# KIỂM KÊ HỒ SƠ KIỂM THỬ HỆ THỐNG GIAI ĐOẠN 8 (GIAI ĐOẠN 9A)

| Phân đoạn | Thư mục / Báo cáo | Kết quả | Điểm chính & Giới hạn |
|---|---|---|---|
| **8A** | `phase8a_environment_audit/` (6 tệp) | `PASS WITH WARNINGS` | Môi trường `.venv-1` khớp (`Python 3.14.8`, `sklearn 1.9.1`); `pytest` chưa cài |
| **8B** | `phase8b_pipeline_test/` (8 tệp + runner) | `PASS WITH WARNINGS` | `136` ca độc lập A–E; phát hiện `DEF-8B-01..04` |
| **8C** | `phase8c_api_test/` (11 tệp + runner) | `PASS WITH WARNINGS` | `49/51` pass (`61` mock DB, `0` ghi DB thật); concurrency `5/10/20` đạt `100%`; `DEF-8C-01..02` |
| **8D** | `phase8d_system_acceptance/` (14 tệp) + `reports/final_system_test_report.md` | `PASS WITH WARNINGS` | 8D-1 SQL Server chỉ đọc `PASS` (`7/7` bảng `TextSenseDB`); 8D-2 UI–API `12/12` pass; **Chrome DOM & responsive (`1366×768`, `1920×1080`, `390×844`) là `NOT EXECUTED`** (`DevToolsActivePort` ENOENT); phát hiện `DEF-8D-01` |

- **7 lỗi đang `OPEN` (chưa sửa trong 9A):** `DEF-8B-01` (Medium), `DEF-8B-02` (Low), `DEF-8B-03` (Low), `DEF-8B-04` (Low), `DEF-8C-01` (Medium), `DEF-8C-02` (Low), `DEF-8D-01` (Medium).
- Không có mâu thuẫn số liệu giữa các báo cáo 8A–8D và `final_system_test_report.md`.
