# BÁO CÁO HIỆU CHỈNH CUỐI CÙNG THIẾT KẾ THÍ NGHIỆM GIAI ĐOẠN 4

**Ngày thực hiện:** 2026-11-27  
**Tài liệu thiết kế cập nhật:** [phase4_experiment_design.md](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/reports/phase4_experiment_design.md)  
**Mã nguồn & kiểm thử E3:** [negation_feature.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/scripts/negation_feature.py), [test_negation_e3.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/tests/test_negation_e3.py)

---

## 1. Tóm tắt 6 hiệu chỉnh đã áp dụng

1. **`E1a` và `E1b`:** Phân tách rõ `E0-Train → E1a` (đo tác động riêng của `textsense_clean_v4` khi giữ `C=1.0`) và `E1a → E1b` (đo tác động của việc tune `C` trên nền `v4`), kèm quy ước không diễn giải cải thiện của `E1b` so với `E0` là do riêng tiền xử lý.
2. **`E2w`:** Giữ quy tắc chuẩn hóa `mean(sample_weight) = 1.0`, bổ sung mức đối chứng `r = 1.0` (= `E2`), giữ `C` cố định giữa mọi mức `r`, báo cáo riêng cả trọng số từng mẫu lẫn tỷ trọng tổng trọng số mỗi nguồn, và nêu rõ ảnh hưởng của `sample_weight` đến hàm mục tiêu `LinearSVC`.
3. **`E3` (Negation Heuristic Feature):**
   - Giữ nguyên `NEGATION_TRIGGERS` (`not`, `no`, `never`, `nobody`, `nothing`, `neither`, `nor`, `without`).
   - Bổ sung `NEGATION_STOPWORDS` để **không** gắn `not_` vào các từ chức năng (`a`, `an`, `the`, `to`, `of`, `is`, `are`, `was`, `were`, `be`, `been`, ...).
   - Giữ nguyên toàn bộ token gốc, ghi rõ đây là **heuristic feature** (không phải bộ phân tích phạm vi phủ định ngữ nghĩa).
   - Đã kiểm thử đạt **30/30 câu** trong [test_negation_e3.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/tests/test_negation_e3.py) (gồm phủ định đơn, phủ định kép, phủ định liên tiếp và ngữ cảnh chính trị).
4. **`E6`:** Khóa cùng một cấu hình nền cho cả ba quy mô `50k`, `120k`, `400k` (`C`, Vectorizer, Preprocessing, `class_weight`, **`threshold`**, Political Train, `seed=42`); không tối ưu riêng `C` hay `threshold` theo từng quy mô.
5. **`Freeze Manifest` (`experiments/freeze_manifest.json`):** Bổ sung yêu cầu lưu `SHA-256` của `model.joblib`, `config.json`, mã nguồn huấn luyện, `preprocessing_v4.py`, các tập Train/Validation, phiên bản Python & thư viện, `threshold` + phương pháp chọn, và danh sách artifact được phép mở `T1`/`T2`.
6. **`E0-Train`:** Tham chiếu chính xác Cell 27 (`choose_threshold`) và Cell 47/59 trong `TextSense_Notebook_SQLServer_Hoan_Thien_v3.ipynb`; không ép kết quả tái hiện phải bằng số lịch sử nếu có khác biệt mà sẽ báo cáo rõ nguyên nhân và giao thức đánh giá.

---

## 2. Kết quả kiểm thử E3 trước khi chạy huấn luyện

Chạy `.\.venv-1\Scripts\python.exe tests/test_negation_e3.py`: **ALL 30 E3 NEGATION TESTS PASSED!** (xác nhận giữ nguyên token gốc và không gắn `not_` vào bất kỳ từ chức năng nào).

---

## 3. Giới hạn tuân thủ

- Chưa huấn luyện mô hình E0–E6.
- Chưa mở `T1` hoặc `T2`.
- Không sửa `baseline_v3/`, `predict.py`, giao diện hoặc SQL Server.
