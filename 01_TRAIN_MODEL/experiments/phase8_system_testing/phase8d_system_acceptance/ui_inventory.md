# KIỂM KÊ GIAO DIỆN WEB TEXTSENSE (GIAI ĐOẠN 8D-2)

**Nguồn kiểm kê:** [index.html](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/03_GIAO_DIEN/web/index.html), [app.js](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/03_GIAO_DIEN/web/app.js), [style.css](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/03_GIAO_DIEN/web/style.css).

## 1. Cấu trúc màn hình, tab và chức năng thực tế
- **Trang chủ (`#trang-chu`):** Giới thiệu, nút điều hướng `#phan-tich` và `#hang-loat`, thẻ chỉ số mô hình (`mi-acc`, `mi-prec`, `mi-rec`, `mi-f1`, `mi-train-rows`, `mi-val-rows`, `mi-test-rows`) nạp từ `GET /api/model-info`.
- **Khu vực Phân tích (`#phan-tich`):**
  - Tab `subtab-single` (`#panel-single`): Form `#comment-form` (`#comment` giới hạn 2.000 ký tự, `#submit`, `#clear`, `#retry`), vùng kết quả (`#result-title`, `#result-confidence`, `#result-detail`, `#sentence-breakdown`, `#history-warning`, nút `#report` mở `#report-dialog`).
  - Tab `subtab-history`: Lịch sử phân tích từ `GET /api/history/batches` và `GET /api/history/predictions` (phụ thuộc SQL Server).
  - Tab `subtab-feedback`: Danh sách và cập nhật trạng thái báo cáo sai (`GET /api/feedback`, `POST /api/feedback/status`).
- **Khu vực Phân tích hàng loạt (`#hang-loat`):** Upload CSV/XLSX (`POST /api/columns`, `POST /api/batch`), xem bảng, xuất Excel (`POST /api/export-xlsx`), thống kê (`GET /api/stats`).
- **Xác thực người dùng:** Nút `#auth-open-btn` / `#auth-logout-btn`, gọi `/api/auth/{me,login,register,logout,google}`.
