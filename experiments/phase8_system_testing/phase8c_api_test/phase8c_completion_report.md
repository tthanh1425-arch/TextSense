# BÁO CÁO HOÀN THÀNH GIAI ĐOẠN 8C – KIỂM THỬ HTTP API TEXTSENSE

**Ngày hoàn thành:** 2026-11-28  
**Kết luận nghiệm thu Giai đoạn 8C:** **`PASS WITH WARNINGS`**

## 1. Tóm tắt kiểm thử
- **Phạm vi:** Kiểm kê endpoint thực tế, lập call graph DB, chạy `51` test case HTTP API trên server tạm `127.0.0.1:64184` (ephemeral, đã tắt sạch sau khi chạy) với toàn bộ hàm DB được mock (`61` lần gọi mock, `0` ghi DB thật).
- **Kết quả tổng quan:** **`49/51 PASS`** trong script (`2` ca đánh `FAIL`: `API-B2-06` trả `422` cho body rỗng thay vì `400`; `API-E-01` tạo XLSX hợp lệ 4 sheet/6 dòng nhưng `openpyxl` đọc ô trống là `None` thay vì `""` như assertion của script).
- **Toàn vẹn trước/sau:** SHA-256 của 2 artifact và 3 file mã nguồn Python giữ nguyên `100%`.

## 2. Trả lời 9 câu hỏi trọng tâm
1. **Endpoint thực tế:** `/api/health`, `/api/model-info`, `/api/analyze`, `/api/batch`, `/api/feedback`, `/api/feedback/status`, `/api/export-xlsx`, `/api/sentences`, `/api/columns`, `/api/config`, `/api/stats`, `/api/history/*`, `/api/auth/*`.
2. **Endpoint hoạt động đúng:** Tất cả các endpoint kiểm thử (`health`, `model-info`, `analyze`, `batch`, `feedback`, `export-xlsx`) đều hoạt động ổn định.
3. **Lỗi / sai khác:** `DEF-8C-01` (`/api/model-info` đọc `binary_metrics.json` của `E0-Train` thay vì `E0-Artifact`), `DEF-8C-02` (body rỗng trả `422`), cùng `DEF-8B-01` và `DEF-8B-02`.
4. **Nhất quán pipeline:** `/api/analyze` khớp `infer_comment()` `100%`; `/api/batch` khớp `predict()` `100%`.
5. **Batch:** Xử lý đúng 1–1.000 dòng, giữ nguyên thứ tự và phân biệt rõ dòng bị loại.
6. **Ghi DB ngoài ý muốn:** Có rủi ro nếu không mock khi chạy test trên máy có SQL Server bật; trong 8C đã cô lập 100% (`0` ghi DB thật).
7. **Concurrency:** `5/5`, `10/10`, `20/20` request đồng thời thành công `100%`, không trộn dữ liệu.
8. **Ảnh hưởng triển khai:** Không có lỗi `Critical` hay `High`.
9. **Có cần sửa trước khi sang 8D?** Không bắt buộc sửa ngay; có thể chuyển sang Giai đoạn 8D (kiểm thử SQL Server chỉ đọc / giao diện / lập `final_system_test_report.md`) sau khi được phê duyệt.

*(Đã dừng hoàn toàn sau Giai đoạn 8C, chờ chỉ thị tiếp theo.)*
