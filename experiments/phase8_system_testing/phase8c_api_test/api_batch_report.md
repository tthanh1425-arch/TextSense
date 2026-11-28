# BÁO CÁO KIỂM THỬ BATCH VÀ XUẤT XLSX (GIAI ĐOẠN 8C)

## 1. Kiểm thử `/api/batch` (`API-C`: 11/11 PASS)
- Kiểm thử đầy đủ các kích thước: `1` dòng, `5` dòng, `100` dòng, `1.000` dòng, `1` dòng URL không hợp lệ, các dòng rỗng xen kẽ, trộn dòng bị từ chối (tiếng Việt, chỉ dấu câu) với dòng hợp lệ, dữ liệu trùng lặp, Unicode + emoji, và chọn sai tên cột (`422`).
- **Tính toàn vẹn & thứ tự:** Số dòng CSV trả về khớp `100%` số dòng đầu vào; thứ tự nhãn khớp `100%` với `predict()` trực tiếp; các dòng bị từ chối giữ nguyên chuỗi rỗng `""` ở cột nhãn (không nhầm với `0`); header `X-History-Saved: false`.

## 2. Kiểm thử `/api/export-xlsx` (`API-E`: 1/2 PASS, 1 lưu ý assertion)
- `API-E-02` (CSV rỗng): Trả `422` đúng quy định (**PASS**).
- `API-E-01` (CSV có dấu phẩy, dấu nháy, xuống dòng, tiếng Việt, công thức `=CMD()`):
  - API trả `HTTP 200`, tệp XLSX mở hợp lệ bằng `openpyxl`, gồm 4 sheet (`['Kết quả phân loại', 'Thống kê tổng hợp', 'Phân tích từ khóa', 'Từ ngữ cần xem xét thêm']`), `6` dòng (1 header + 5 dữ liệu).
  - Trong `api_test_results.csv`, ca `API-E-01` bị đánh `FAIL` do test script kiểm tra `rows_xlsx[5][1] == ""` trong khi `openpyxl` đọc ô trống là `None` (tức hệ thống thực tế **không** ghi nhầm `None` thành `0`).
