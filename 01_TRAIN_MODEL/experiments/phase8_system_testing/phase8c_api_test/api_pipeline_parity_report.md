# BÁO CÁO ĐỐI CHIẾU TÍNH NHẤT QUÁN API VỚI PIPELINE (GIAI ĐOẠN 8C)

1. **`/api/analyze` vs `infer_comment()`:** Khớp **`100%`** (`8/8` ca `API-B1` và `8/8` ca `API-B3`).
2. **`/api/batch` vs `predict()`:** Khớp **`100%`** trên tất cả `9/9` lô kiểm thử (từ 1 dòng đến 1.000 dòng, bao gồm dòng rỗng/URL/tiếng Việt xen kẽ).
3. **Ảnh hưởng của `DEF-8B-01` và `DEF-8B-02` trên HTTP API:**
   - **`DEF-8B-01` (Quy tắc OR):** `/api/analyze` (`API-B1-03`: `"Good design, but awful customer support."`, `API-B1-05`: `"The service was excellent, although the price was disappointing."`) dùng `infer_comment()` nên tách mệnh đề và trả `1` khi có mệnh đề tiêu cực, trong khi `/api/batch` dùng `predict()` trực tiếp trên cả chuỗi.
   - **`DEF-8B-02` (Giới hạn 2.000 ký tự):** Tái hiện tại `API-B3-04` (`"bad " + "!"*2005`): `/api/analyze` trả `HTTP 413` (kiểm tra độ dài raw), trong khi `predict()`/`/api/batch` chấp nhận vì độ dài sau chuẩn hóa chỉ còn `3` ký tự.
4. **`/api/model-info` vs `E0-Artifact`:** `/api/model-info` đọc `binary_metrics.json` (chỉ số đo trên `E0-Train`, `Accuracy=0.9444`), trong khi `.joblib` phục vụ suy luận là `E0-Artifact` (`Train+Val`, `T1 Accuracy=0.9476`).
