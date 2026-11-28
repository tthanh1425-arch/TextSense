# BÁO CÁO KIỂM THỬ CHỨC NĂNG GIAO DIỆN (GIAI ĐOẠN 8D-2)

**Phương pháp:** Khởi động test server cô lập trên `127.0.0.1:8599` (mock DB, đã tắt sau kiểm thử) và chạy [run_8d2_http_ui_checks.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/experiments/phase8_system_testing/phase8d_system_acceptance/run_8d2_http_ui_checks.py).  
**Lưu ý phạm vi:** Kiểm thử tương tác DOM trực tiếp trên trình duyệt Chrome (`browser` subagent) gặp lỗi kết nối Chrome DevTools (`DevToolsActivePort` ENOENT) nên phần thao tác UI trực quan trên trình duyệt được ghi nhận là **`NOT EXECUTED`**; toàn bộ tải tài nguyên tĩnh (`/`, `/style.css`, `/app.js`, `/csv_viewer.js`) và `12/12` luồng UI–API (`/api/analyze`, `/api/batch`, `/api/export-xlsx`, `/api/health`, `/api/model-info`) đã thực thi và đạt **`12/12 PASS`**.

| Nhóm kiểm thử | Kết quả | Chi tiết quan sát |
|---|---|---|
| Tải tài nguyên tĩnh | **PASS** | `/` (`42.770 B`), `/style.css` (`38.746 B`), `/app.js` (`64.820 B`), `/csv_viewer.js` (`2.150 B`) đều trả `HTTP 200` |
| Phân loại đơn (`UI-S-01`..`UI-S-10`) | **PASS** (`10/10`) | Tiêu cực (`UI-S-01`, `1`), Không tiêu cực (`UI-S-02`, `0`), Câu ghép (`UI-S-03`, `1` với `neg_parts=1`), `not bad` (`UI-S-04`, `1`), URL/rỗng/tiếng Việt/`>2000` ký tự bị từ chối `422`/`413` |
| Hàng loạt & Xuất XLSX (`UI-B-01`, `UI-E-01`) | **PASS** (`2/2`) | `/api/batch` trả `200` (`neg=1, inv=1`), `/api/export-xlsx` trả `200` với 4 sheet hợp lệ |
| Thao tác DOM trên Chrome trực tiếp | **NOT EXECUTED** | Chrome DevTools MCP báo `Could not find DevToolsActivePort` |
