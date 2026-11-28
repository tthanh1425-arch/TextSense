# HỒ SƠ QUYẾT ĐỊNH CHỐT MÔ HÌNH CHÍNH THỨC (`E0-Artifact`)

## 1. Vì sao chọn `E0-Artifact`?
- **Mục tiêu cốt lõi của TextSense** là nhận diện bình luận tiêu cực trong **thảo luận chính trị tiếng Anh** (`T1`, `39.210` dòng).
- Trên `T1`, `E0-Artifact` đạt **hiệu suất cao nhất toàn diện** ở cả hai chỉ số ưu tiên: **F1 lớp `1` = `0.8826`** (95% CI `[0.8774, 0.8878]`) và **PR-AUC = `0.9380`** (95% CI `[0.9336, 0.9423]`), đồng thời `Recall = 0.8951`, `Precision = 0.8705`, `Accuracy = 0.9476`.
- `E0-Artifact` chính là artifact đã triển khai sẵn trong `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib` (SHA-256 trùng khớp 100% với `baseline_v3/`), giúp giữ ổn định hoàn toàn cho hệ thống.

## 2. Vì sao không chọn `E3`?
- Dù `E3` (`E2w` + `not_`) là mô hình tốt nhất trong nhánh có bổ sung `400.000` Sentiment140 (`T1 F1 = 0.8004`, `PR-AUC = 0.8726`), nhưng vẫn **thấp hơn `E0-Artifact` `-0.0822` F1** (`p_holm < 1e-100`). Đặc trưng phủ định `not_` không đủ để bù đắp sự suy giảm do lệch miền từ Sentiment140.

## 3. Vì sao không chọn `E2` / `E2w`?
- `E2` (gộp `400k` Sentiment140 không trọng số) đạt `T2 F1 = 0.8087` trên tweet đời thường nhưng làm **`T1 F1` tụt mạnh xuống `0.6818`** (`-0.2008` so với `E0-Artifact`).
- `E2w` (`r=0.15`) khôi phục được lên `T1 F1 = 0.7981` nhưng vẫn thấp hơn `E0-Artifact` `-0.0845` F1 (`p_holm < 1e-100`).

## 4. Vì sao không chọn `E5b`?
- `E5b` (ngưỡng tối ưu F2) đạt Recall cao nhất trên `T1` (`0.9051`), nhưng phải trả giá bằng **Precision giảm mạnh xuống `0.6718`** (`FP` tăng từ `1.149` lên `3.815`, `F1 = 0.7712`). Mức cảnh báo giả quá cao không phù hợp làm mô hình mặc định.

## 5. Vì sao không dùng `E0-Train` thay `E0-Artifact`?
- `E0-Train` (`T1 F1 = 0.8756`, `PR-AUC = 0.9336`) chỉ fit trên `133.314` mẫu `Train`, còn `E0-Artifact` được fit lại với cùng siêu tham số (`C=1.0`, `threshold=-0.192201`) trên toàn bộ `Train + Validation` (`156.840` mẫu) sau khi chốt siêu tham số, nhờ đó đạt `T1 F1 = 0.8826` (`+0.0070`) mà không vi phạm tính độc lập của `T1`.

## 6. Vì sao chưa cần bổ sung RoBERTa?
- Theo Master Prompt V4, Giai đoạn 6 (RoBERTa tham chiếu) là tùy chọn và không dùng để thay thế mô hình chính nếu chưa có hạ tầng GPU/yêu cầu triển khai mới. `LinearSVC` hiện tại cho tốc độ suy luận `~1.11s` cho `39.210` câu trên CPU và đạt `F1 = 0.8826` trên miền mục tiêu, đáp ứng tốt yêu cầu vận hành cục bộ.

## 7. Đánh đổi khi lựa chọn `E0-Artifact`
- **Ưu điểm:** Hiệu suất cao nhất trên miền chính trị (`T1`), suy luận rất nhanh trên CPU, không phải sửa đổi hệ thống đã kiểm chứng.
- **Đánh đổi:** Hiệu suất trên tweet đời thường ngoài miền chính trị (`T2 F1 = 0.4497`, `Recall = 0.3218`) thấp. Mô hình không phù hợp nếu sử dụng làm bộ phân loại cảm xúc tổng quát ngoài miền thảo luận chính trị.
