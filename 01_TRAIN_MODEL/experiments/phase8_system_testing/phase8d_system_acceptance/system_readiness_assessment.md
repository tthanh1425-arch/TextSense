# ĐÁNH GIÁ MỨC ĐỘ SẴN SÀNG TRIỂN KHAI (`system_readiness_assessment.md`)

| Tầng kiến trúc | Mức độ sẵn sàng | Căn cứ bằng chứng |
|---|---|---|
| **Model readiness** | **READY (trong miền chính trị)** | `E0-Artifact` đạt `T1 F1 = 0.8826`, `PR-AUC = 0.9380`, `Acc = 0.9476`, SHA-256 nguyên vẹn. Giới hạn: chỉ phù hợp tiếng Anh miền chính trị (`T2 F1 = 0.4497`). |
| **API readiness** | **READY WITH WARNINGS** | `49/51` pass (`2` sai khác nhỏ ở assertion/422), concurrency `5/10/20` đạt `100%`, batch & XLSX toàn vẹn. Cần lưu ý `DEF-8C-01` và `DEF-8B-01`. |
| **Database readiness** | **READY (Schema & Read-only verified)** | Kết nối `TextSenseDB` thành công (`ODBC Driver 17`), đủ `7/7` bảng và `4` FK khớp `textsense.sql`. |
| **UI readiness** | **PARTIALLY VERIFIED (WITH WARNINGS)** | Tài nguyên tĩnh & `12/12` luồng UI–API đạt; kiểm thử trực quan trên trình duyệt thực tế (`1366×768`, `1920×1080`, `390×844`) `NOT EXECUTED` do thiếu Chrome remote debugging. Có `DEF-8C-01` và `DEF-8D-01`. |
| **System readiness** | **`PASS WITH WARNINGS`** | Hệ thống vận hành ổn định, bảo toàn dữ liệu và artifact, không có lỗi `Critical` hay `High`; cần xử lý/ghi chú `DEF-8C-01`, `DEF-8D-01`, `DEF-8B-01` và chạy bổ sung kiểm thử trực quan Chrome trước khi phát hành chính thức. |
