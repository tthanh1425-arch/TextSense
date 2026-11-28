# SỔ ĐĂNG KÝ LỖI TỔNG HỢP (8B – 8C – 8D)

*(Không tự ý sửa lỗi hoặc chuyển trạng thái `RESOLVED` trong Giai đoạn 8D.)*

| ID | Giai đoạn | Thành phần | Mức độ | Trạng thái | Ảnh hưởng |
|---|---|---|---|---|---|
| **DEF-8B-01** | 8B | `serve_textsense.py` (`infer_comment`) vs `predict.py` | **Medium** | `OPEN` | Quy tắc OR khi tách mệnh đề làm `/api/analyze` (`UI-S-03`) trả `1` trong khi `/api/batch` (`predict()`) trả `0` trên cùng câu ghép |
| **DEF-8B-02** | 8B | `serve_textsense.py` vs `predict.py` | **Low** | `OPEN` | Không thống nhất kiểm tra giới hạn 2.000 ký tự (`raw` ở `/api/analyze` vs `normalized` ở `predict()`) |
| **DEF-8B-03** | 8B | `E0-Artifact` (`LinearSVC` + TF-IDF v3) | **Low** | `OPEN` | Hạn chế cố hữu với phủ định kép/phủ định từ tiêu cực (`not bad` cho `1`, xác nhận lại tại `UI-S-04`) |
| **DEF-8B-04** | 8B | `03_GIAO_DIEN/predict.py` (`v3`) | **Low** | `OPEN` | Chưa giải mã HTML entities (`&amp;`, `&lt;`, `&gt;`), tạo token `lt`, `gt`, `amp` |
| **DEF-8C-01** | 8C | `/api/model-info` & `app.js` dòng 194–211 | **Medium** *(nâng từ Low sau khi xác minh UI 8D)* | `OPEN` | Giao diện hiển thị metrics của `E0-Train` (`94,44%`, `133.314` mẫu) dưới danh nghĩa artifact `E0-Artifact` (`Train+Val` `156.840`, `T1 F1=88,26%`) |
| **DEF-8C-02** | 8C | `/api/analyze` (`_read_bytes`) | **Low** | `OPEN` | Body rỗng `b""` trả `HTTP 422` thay vì `HTTP 400` |
| **DEF-8D-01** | 8D | `serve_textsense.py` (dòng 848) & `app.js` (dòng 345) | **Medium** | `OPEN` | `confidence` là sigmoid heuristic từ `|decision_score - threshold|` (chưa hiệu chỉnh xác suất) nhưng giao diện hiển thị `'Điểm tin cậy: XX.X%'` |
