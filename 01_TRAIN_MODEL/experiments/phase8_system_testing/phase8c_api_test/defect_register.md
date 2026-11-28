# SỔ ĐĂNG KÝ LỖI GIAI ĐOẠN 8C (`defect_register.md`)

*(Không tự ý sửa bất kỳ lỗi nào trong Giai đoạn 8C.)*

| ID | Mức độ | Endpoint / Thành phần | Mô tả & Bằng chứng | Đề xuất hướng xử lý (chưa thực hiện) |
|---|---|---|---|---|
| **DEF-8C-01** | **Low** | `/api/model-info` (`serve_textsense.py` dòng 1340–1360) | Endpoint đọc `binary_metrics.json` (chỉ số của `E0-Train`: `Accuracy=0.9444`, `test_rows=39210`) trong khi artifact `.joblib` đang chạy là `E0-Artifact` (`Train+Val`) | Bổ sung chú thích `trained_on` hoặc cập nhật nguồn hiển thị thông tin artifact |
| **DEF-8C-02** | **Low** | `/api/analyze` (`_read_bytes`, `API-B2-06`) | Body rỗng `b""` trả `HTTP 422` thay vì `HTTP 400` (khác với JSON lỗi cú pháp trả `400`) | Chuẩn hóa tài liệu API hoặc thống nhất `400` cho body rỗng |
| **DEF-8B-01** *(tái xác nhận)* | **Medium** | `/api/analyze` vs `/api/batch` | Quy tắc OR khi tách mệnh đề làm `/api/analyze` khác `/api/batch` trên một số câu ghép tương phản | Ghi rõ sự khác biệt luồng xử lý trong tài liệu hướng dẫn |
| **DEF-8B-02** *(tái xác nhận)* | **Low** | `/api/analyze` vs `/api/batch` | `API-B3-04`: `/api/analyze` kiểm tra `len(raw) > 2000` (`413`), còn `/api/batch` kiểm tra `len(normalized) > 2000` | Thống nhất kiểm tra giới hạn độ dài raw ở cả hai luồng nếu cần |
| **TEST-NOTE-01** | **Info** | `run_phase8c_tests.py` (`API-E-01`) | Test script kiểm tra `== ""` cho ô trống trong XLSX trong khi `openpyxl` trả `None` (API thực tế hoạt động đúng, không nhầm `None` thành `0`) | Cập nhật assertion trong test script thành `in (None, "")` nếu chạy lại |
