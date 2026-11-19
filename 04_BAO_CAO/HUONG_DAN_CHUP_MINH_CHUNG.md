# Hướng dẫn chụp 3 ảnh minh chứng ứng dụng TextSense V3.22

Các ảnh cần chụp trực tiếp trên máy Windows sau khi giải nén bản cập nhật và khởi động ứng dụng. Không dùng ảnh minh họa hoặc ảnh từ phiên bản có nhãn cũ.

## Hình 8 – Dự đoán một bình luận
1. Chạy `python serve_textsense.py` trong `03_GIAO_DIEN`.
2. Mở `http://127.0.0.1:8502`.
3. Nhập một bình luận tiếng Anh có sắc thái rõ ràng, bấm Phân tích.
4. Chụp phần kết quả gồm nhãn và nội dung bình luận.
5. Lưu tên `Hinh_08_Du_doan_binh_luan.png`.

## Hình 9 – Phân tích tệp CSV/Excel
1. Chuyển sang tab Tệp dữ liệu.
2. Tải một tệp CSV hoặc XLSX có cột `text`.
3. Để hệ thống tự nhận diện cột hoặc chọn lại nếu cần.
4. Bấm Phân tích toàn bộ tệp.
5. Chụp khu vực tên tệp, số dòng và kết quả phân loại.
6. Lưu tên `Hinh_09_Phan_tich_CSV_Excel.png`.

## Hình 10 – Dashboard và kết quả tổng hợp
1. Sau khi phân tích tệp, cuộn đến dashboard.
2. Chụp số dòng hợp lệ/không hợp lệ, tỷ lệ Tiêu cực/Không tiêu cực, độ dài văn bản, từ khóa và bảng kết quả.
3. Lưu tên `Hinh_10_Dashboard_TextSense.png`.

Đặt ba ảnh vào `04_BAO_CAO/HINH_MINH_CHUNG/` rồi chèn vào các vị trí Hình 8–10 trong báo cáo Word.
