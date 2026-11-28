# BÁO CÁO KIỂM THỬ HỆ THỐNG CUỐI CÙNG – TEXTSENSE (`final_system_test_report.md`)

**Ngày lập:** 2026-11-28  
**Kết luận nghiệm thu tổng thể:** **`PASS WITH WARNINGS`**

---

## 1. Thông tin dự án
- **Tên đề tài:** Phân loại cảm xúc tiêu cực trong thảo luận chính trị trên mạng xã hội bằng phương pháp học máy (**TextSense**).
- **Mô hình chính thức:** `E0-Artifact` (`baseline_v3/binary_linear_svm.joblib` ≡ `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib`, SHA-256: `474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a`).

## 2. Mục tiêu kiểm thử
Xác minh tính toàn vẹn mô hình, độ ổn định của pipeline suy luận, hợp đồng HTTP API, khả năng kết nối & tương thích schema SQL Server ở chế độ chỉ đọc, và tính nhất quán với giao diện Web.

## 3. Phạm vi
Bao gồm toàn bộ Giai đoạn **8A** (kiểm kê môi trường), **8B** (pipeline suy luận), **8C** (HTTP API) và **8D** (SQL Server chỉ đọc, giao diện Web, tổng hợp nghiệm thu). Không huấn luyện lại mô hình và không sửa mã nguồn trong suốt Giai đoạn 8.

## 4. Kiến trúc hệ thống
`Web UI (03_GIAO_DIEN/web/) → ThreadingHTTPServer (serve_textsense.py, cổng 8502) → predict.py (textsense_clean_v3_context + TF-IDF + LinearSVC > -0.192201) & database.py (pyodbc → TextSenseDB)`

## 5. Môi trường kiểm thử (`.venv-1`)
- Windows 11, Python `3.14.8`, `scikit-learn 1.9.1`, `pandas 3.1.1`, `numpy 2.5.5`, `scipy 1.18.1`, `joblib 1.6.0`, `openpyxl 3.1.5`, `pyodbc 5.5.0`, `ODBC Driver 17 for SQL Server`.

## 6. Tóm tắt các giai đoạn 8A–8D

| Giai đoạn | Nội dung | Kết quả |
|---|---|---|
| **8A** | Kiểm kê môi trường, SHA-256 artifact, API & SQL config | `PASS WITH WARNINGS` |
| **8B** | Kiểm thử pipeline (`136` ca A–E + parity `predict` vs `infer_comment`) | `PASS WITH WARNINGS` |
| **8C** | Kiểm thử HTTP API (`51` ca, mock DB `61` lần, concurrency `5/10/20`) | `PASS WITH WARNINGS` (`49/51 PASS`) |
| **8D-1** | Kiểm tra SQL Server `TextSenseDB` chỉ đọc | `PASS` (`7/7` bảng, `4` FK) |
| **8D-2** | Kiểm thử tài nguyên & luồng UI–API (`12/12` PASS); Chrome DOM trực quan | `PASS WITH WARNINGS` (Chrome DOM `NOT EXECUTED`) |

## 7. Kết quả đánh giá mô hình (Đóng băng từ Giai đoạn 5 – không đo lại bằng bộ test 8B/8C)
- **T1 (`political_test_T1.csv`, `39.210` dòng):** Accuracy `0.9476`, Precision(1) `0.8705`, Recall(1) `0.8951`, **F1(1) `0.8826`** (95% CI `[0.8774, 0.8878]`), **PR-AUC `0.9380`** (95% CI `[0.9336, 0.9423]`).
- **T2 (`s140_test_T2_60k.csv`, `60.000` dòng):** F1(1) `0.4497`, PR-AUC `0.6858`.

## 8. Kết quả kiểm thử pipeline (8B)
- `136/136` ca xử lý không lỗi; ổn định 100% qua các lần lặp, đảo thứ tự và batch `<512`, `=512`, `>512` (`600` dòng).
- Phát hiện `6/136` ca bị quy tắc OR trong `infer_comment()` đảo `0 → 1` (`DEF-8B-01`) và `1` ca lệch giới hạn raw vs normalized (`DEF-8B-02`).

## 9. Kết quả kiểm thử API (8C)
- `49/51 PASS` trên server tạm `127.0.0.1:64184` (DB mock 100%); concurrency `5/5`, `10/10`, `20/20` thành công `100%`.

## 10. Kết quả kiểm thử SQL Server (8D-1)
- Kết nối chỉ đọc thành công tới `TextSenseDB`; `7/7` bảng (`Tweets`, `TweetTokens`, `TrainingRuns`, `PredictionBatches`, `Predictions`, `UserFeedback`, `Users`) và `4` khóa ngoại khớp schema `textsense.sql`.

## 11. Kết quả kiểm thử giao diện (8D-2)
- Tài nguyên tĩnh (`/`, `/style.css`, `/app.js`, `/csv_viewer.js`) trả `200`; `12/12` luồng UI–API đạt; kiểm thử trực quan trên Chrome (`1366×768`, `1920×1080`, `390×844`) `NOT EXECUTED` do thiếu `DevToolsActivePort`.

## 12. Kết quả kiểm thử batch và export
- `/api/batch` giữ nguyên số dòng, thứ tự và biểu diễn dòng bị loại bằng chuỗi rỗng; `/api/export-xlsx` xuất file XLSX 4 sheet hợp lệ, bảo vệ công thức `=CMD()`, giữ ô trống là `None`.

## 13. Danh sách lỗi còn tồn tại (`OPEN`)
- `DEF-8B-01` (Medium): Khác biệt nhãn giữa `/api/analyze` (OR rule) và `/api/batch` (`predict()`).
- `DEF-8C-01` (Medium): `/api/model-info` & UI hiển thị metrics của `E0-Train` thay vì `E0-Artifact`.
- `DEF-8D-01` (Medium): Giao diện hiển thị `confidence` (sigmoid heuristic) dưới dạng `Điểm tin cậy: XX.X%`.
- `DEF-8B-02` (Low), `DEF-8B-03` (Low), `DEF-8B-04` (Low), `DEF-8C-02` (Low).

## 14. Rủi ro còn tồn tại
- Rủi ro hiểu nhầm `%` độ tin cậy và metrics `E0-Train` trên giao diện; rủi ro lệch miền nếu dùng mô hình cho dữ liệu ngoài miền chính trị; chưa xác minh hiển thị responsive trực quan trên Chrome thực tế.

## 15. Đánh giá khả năng triển khai
- **Model:** Ready (trong miền chính trị) | **API:** Ready with Warnings | **Database:** Ready | **UI:** Partially Verified (With Warnings) | **System:** **`PASS WITH WARNINGS`**.

## 16. Kết luận nghiệm thu
Hệ thống TextSense đạt **`PASS WITH WARNINGS`** — hoạt động ổn định từ giao diện, API đến SQL Server và bảo toàn nguyên vẹn `E0-Artifact` (SHA-256 khớp 100%).

## 17. Đề xuất công việc tiếp theo
1. Cập nhật hiển thị `/api/model-info` (`DEF-8C-01`) và chú thích `confidence` (`DEF-8D-01`) nếu được phê duyệt.
2. Bổ sung kiểm thử trực quan Chrome ở `1366×768`, `1920×1080`, `390×844`.
3. Chuyển sang **Giai đoạn 9 – Hoàn thiện báo cáo và đóng gói hồ sơ cuối cùng**.
