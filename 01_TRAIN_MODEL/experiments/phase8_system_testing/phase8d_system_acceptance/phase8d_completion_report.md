# BÁO CÁO HOÀN THÀNH GIAI ĐOẠN 8D – NGHIỆM THU HỆ THỐNG TEXTSENSE

**Ngày hoàn thành:** 2026-11-28  
**Kết luận nghiệm thu tổng thể:** **`PASS WITH WARNINGS`**

## 1. Tóm tắt kết quả 8D-1, 8D-2, 8D-3
- **8D-1 (SQL Server chỉ đọc):** **`PASS`** — Kết nối thành công `TextSenseDB` (`ODBC Driver 17`), xác nhận đủ `7/7` bảng (`dbo.Tweets` `196.050`, `dbo.TweetTokens` `3.780.313`, `dbo.TrainingRuns` `7`, `dbo.PredictionBatches` `44`, `dbo.Predictions` `624.403`, `dbo.UserFeedback` `3`, `dbo.Users` `1`) và `4` khóa ngoại, `0` thao tác ghi.
- **8D-2 (Giao diện Web):** **`PASS` cho kiểm tra tài nguyên & `12/12` luồng UI–API** trên test server cô lập `127.0.0.1:8599` (đã tắt sạch); **kiểm thử trực quan trên trình duyệt Chrome (`1366×768`, `1920×1080`, `390×844`) là `NOT EXECUTED`** do Chrome chưa bật remote debugging (`DevToolsActivePort` ENOENT).
- **8D-3 (Tổng hợp & SHA-256):** Toàn bộ SHA-256 của artifact, backend và frontend khớp `100%` trước và sau kiểm thử; không có lỗi `Critical` hay `High`.

## 2. Trả lời nhanh 11 câu hỏi nghiệm thu
1. **`E0-Artifact` giữ nguyên?** Có (`474b0f5fdce1...`).
2. **Pipeline ổn định?** Có (`136/136` ca kỹ thuật không crash, batch 600 dòng tất định).
3. **API đúng hợp đồng?** `49/51` pass; `2` sai khác nhỏ (`422` body rỗng và `None` trong openpyxl).
4. **SQL Server đọc được?** Có (`TextSenseDB`, `7/7` bảng khớp schema).
5. **Giao diện hoạt động?** Tải đủ tài nguyên & `12/12` luồng UI–API pass; cần chạy thêm kiểm thử DOM Chrome trực quan.
6. **Frontend khớp Backend?** Khớp ở suy luận/batch/export; có `DEF-8C-01` (hiển thị metrics `E0-Train`) và `DEF-8D-01` (`confidence` hiển thị `%`).
7. **Batch & Export bảo toàn dữ liệu?** Có (giữ thứ tự, ô trống không bị biến thành `0`).
8. **Ảnh hưởng lỗi 8B/8C?** Chủ yếu là khác biệt giữa câu đơn (`OR` rule) và batch (`DEF-8B-01`), hiển thị metrics `E0-Train` (`DEF-8C-01`) và `%` tin cậy heuristic (`DEF-8D-01`).
9. **Rủi ro ghi DB ngoài ý muốn?** Có nếu chạy test không mock trên máy đang bật SQL Server; trong 8C/8D đã cô lập `0` ghi.
10. **Mức sẵn sàng:** **`PASS WITH WARNINGS`**.
11. **Cần giải quyết trước phát hành:** Xử lý/ghi chú `DEF-8C-01`, `DEF-8D-01`, `DEF-8B-01` và chạy kiểm thử Chrome responsive `390×844`.

*(Đã dừng hoàn toàn sau Giai đoạn 8D, không sửa mã nguồn, không sửa artifact.)*
