# BÁO CÁO KIỂM TOÁN FREEZE GATE SAU BƯỚC 4A – TEXTSENSE V4

**Ngày kiểm toán:** 2026-11-27  
**Kết luận tổng thể:** **`PASS`** *(Không phát hiện lỗi trọng yếu, không sai hash, không có dấu hiệu truy cập `T1`/`T2` trước Freeze Gate. Đủ điều kiện trình duyệt mở `T1` và `T2` ở Bước 4B / Giai đoạn 5.)*

---

## 1. Phạm vi tệp đã kiểm tra

Chỉ đọc các tệp thuộc phạm vi Bước 4A (tuyệt đối **không** mở hoặc đọc `political_test_T1.csv` hay `s140_test_T2_60k.csv`, **không** chỉnh sửa bất kỳ tệp đã khóa nào):
- `baseline_v3/splits/binary/{train,validation}.csv`, `baseline_v3/binary_linear_svm.joblib`
- `data/splits/{political_train,political_val,s140_train_400k,s140_val_60k,s140_train_e6_50k,s140_train_e6_120k}.csv`
- `experiments/freeze_manifest.json`, `experiments/phase4A_validation_summary.md`, `manifest.json`
- `experiments/{E0-Train,E1a,E1b,E2,E2w,E3,E4a,E4b,E5a,E5b,E6-50k,E6-120k,E6-400k}/{config.json,val_metrics.json,model.joblib}`
- `scripts/phase4a_run.py`, `scripts/phase4a_resume.py`, `preprocessing_v4.py`, `scripts/negation_feature.py`

---

## 2. Kết quả và bằng chứng từng mục kiểm toán (A–E)

### Mục A. `E0-Train` và `E1a`
- **Bằng chứng dữ liệu:**
  - `baseline_v3/splits/binary/train.csv` vs `data/splits/political_train.csv`: cùng `133.314` dòng, khớp 100% `label`, số dòng khác `text` giữa `v3` và `v4` = **`0`**.
  - `baseline_v3/splits/binary/validation.csv` vs `data/splits/political_val.csv`: cùng `23.526` dòng, khớp 100% `label`, số dòng khác `text` giữa `v3` và `v4` = **`0`**.
  - Nguyên nhân: Dữ liệu gốc `Twitter_Data.csv` và `Reddit_Data.csv` đã được tiền làm sạch trước đó (không chứa HTML entities, không có dạng tách khoảng trắng `don t`, chỉ có `dont`/`cant`/`wont` vốn đã được `v3` xử lý).
- **Bằng chứng mô hình & dự đoán:**
  - Cả hai dùng `TfidfVectorizer(ngram_range=(1,2), min_df=2, max_features=40000, sublinear_tf=True)`, `LinearSVC(C=1.0, class_weight=None, random_state=42)`, `threshold = -0.19220128657328076` (chọn theo F1 trên `political_val`).
  - Sai khác lớn nhất trên `decision_function(political_val)` = **`0.0`**; dự đoán nhị phân trùng khớp **`100%`** (`F1 = 0.8792`).
- **Kết luận Mục A:** `E0-Train` và `E1a` nhận đầu vào chính trị giống hệt nhau; không có cải thiện từ `v4` trên `political_val` (chỉ có khác biệt nhẹ trên `s140_val_60k`: `0.4509` vs `0.4496` vì Sentiment140 chứa nhiều dạng `don t`, `i m`).

### Mục B. `E3` và `E5a`
- **Bằng chứng:**
  - `E5a` kế thừa trực tiếp từ `E3` và thử 4 cấu hình `class_weight ∈ {None, balanced, {0:1, 1:1.5}, {0:1, 1:2}}` (`val_metrics.json` ghi nhận đầy đủ 4 ứng viên: `0.8026`, `0.7954`, `0.7968`, `0.7937`).
  - Cấu hình `class_weight = None` đạt F1 cao nhất (`0.8026`), trùng với cấu hình mặc định của `E3`.
  - Đối chiếu trọng số mô hình: `max_abs_diff(coef_) = 0.0`, `E3 pol_val == E5a pol_val` (`True`), `E3 s140_val == E5a s140_val` (`True`).
  - `model.joblib` có SHA-256 khác nhau (`9ec29b3760b7...` vs `ea0030580091...`) chỉ vì dictionary artifact lưu metadata `experiment_id` và `created_utc` riêng cho từng lần chạy.
- **Kết luận Mục B:** `E5a` không phải lỗi lặp vô ý mà là kết quả tất yếu khi `class_weight=None` thắng 3 phương án còn lại trên `political_val`. *(Lưu ý nhỏ: `E5a/config.json` và `E5b/config.json` kế thừa `vectorizer` qua `base_experiment` thay vì lặp lại trường `vectorizer`.)*

### Mục C. `E2` và `E6-400k`
- **Bằng chứng:**
  - Cùng dữ liệu (`political_train` `133.314` + `s140_train_400k` `400.000`), cùng `C=0.5`, `sample_weight=1.0`, `textsense_clean_v4`, `seed=42`, `threshold=-0.23788077037364946`.
  - `max_abs_diff(coef_) = 0.0`, `E2 pol_val == E6-400k pol_val` (`True`), `E2 s140_val == E6-400k s140_val` (`True`).
  - SHA-256 khác nhau do `experiment_id` (`"E2"` vs `"E6-400k"`), `threshold_objective` (`"F1_class1"` vs `"LOCKED_FROM_E2"`) và `created_utc`; thời gian huấn luyện khác nhau (`28.824s` vs `43.173s`) là dao động CPU/OS bình thường giữa các lần chạy.
- **Kết luận Mục C:** Nhất quán 100%.

### Mục D. Nhánh `E3 / E4a / E4b`
- **Bằng chứng (`config.json`):**
  - `E3`: `base_experiment = "E2w"`, `sample_weight = {'selected_r': 0.15, 'w_pol': 2.7588, 'w_s140': 0.4138}`, `C = 0.5`.
  - `E4a`: `base_experiment = "E2w"`, cùng `sample_weight` (`r=0.15`), cùng `C = 0.5`, đổi vectorizer sang `char_wb (2,5)`.
  - `E4b`: `base_experiment = "E2w"`, cùng `sample_weight` (`r=0.15`), cùng `C = 0.5`, đổi vectorizer sang `FeatureUnion(Word(1,2) + Char_wb(2,5))`.
  - `phase4A_validation_summary.md` ghi đúng: `E2w (r=0.15)` là nền cho `E3/E4`.
- **Kết luận Mục D:** Nhất quán 100%.

### Mục E. Kiểm toán `experiments/freeze_manifest.json`
1. **Timestamp khóa (`created_utc`):** Có (`2026-11-27T09:06:31.708834+00:00`).
2. **Phiên bản Python & thư viện:** Có (`Python 3.14.8`, `sklearn 1.9.1`, `pandas 3.1.1`, `numpy 2.5.5`, `scipy 1.18.1`, `joblib 1.6.0`).
3. **SHA-256 thực tế vs manifest:** Khớp **100%** cho toàn bộ `code_sha256` (3 tệp), `train_val_splits_sha256` (6 tệp), và `allowed_artifacts_for_step4B` (`14` `model.joblib` + `13` `config.json`, `0` sai lệch).
4. **Preprocessing version, threshold, danh sách artifact:** Có đầy đủ cho cả 14 artifact.
5. **`E0-Artifact`:** Không có metric trên `political_val.csv`, chỉ nằm trong danh sách được phép đánh giá `T1`/`T2` ở Bước 4B.
6. **Kiểm tra tham chiếu `T1`/`T2` trong mã nguồn 4A:** Chuỗi `political_test_T1` / `s140_test_T2` chỉ xuất hiện trong docstring cảnh báo ở đầu `scripts/phase4a_run.py`, **không** xuất hiện trong bất kỳ lệnh đọc hay luồng thực thi nào.

---

## 3. Bảng trạng thái kiểm toán

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| A. `E0-Train` vs `E1a` | **PASS** | Đầu vào chính trị v3 và v4 giống nhau 100% (`0` dòng khác); không quy kết cải thiện từ v4 trên dữ liệu chính trị |
| B. `E3` vs `E5a` | **PASS** | `class_weight=None` thắng trên Validation nên trùng trọng số `E3`; lưu ý nhỏ là `E5a/E5b` `config.json` kế thừa `vectorizer` qua `base_experiment` |
| C. `E2` vs `E6-400k` | **PASS** | Cùng trọng số mô hình (`max_diff=0.0`) và metric; SHA-256 & runtime khác do metadata và lịch trình CPU |
| D. Nhánh `E3 / E4a / E4b` | **PASS** | Cả 3 đều kế thừa đúng nền `E2w` (`r=0.15`, `C=0.5`) |
| E. `freeze_manifest.json` & Bảo vệ `T1`/`T2` | **PASS** | Khớp SHA-256 100% (14 models, 13 configs, 3 scripts, 6 splits); không truy cập `T1`/`T2` |

---

## 4. Kết luận chung

**`PASS`** — Freeze Gate sau Bước 4A đạt tính nhất quán và khả năng tái lập hoàn chỉnh. **Đã dừng hoàn toàn tại đây, chưa mở `T1`/`T2`**, chờ người phụ trách phê duyệt để chuyển sang **Bước 4B / Giai đoạn 5**.
