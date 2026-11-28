# THIẾT KẾ THÍ NGHIỆM GIAI ĐOẠN 4 – E0 ĐẾN E6 (PHIÊN BẢN HIỆU CHỈNH)

**Ngày hiệu chỉnh:** 2026-11-27  
**Trạng thái:** Chờ phê duyệt trước khi chạy huấn luyện hàng loạt.  
**Nguyên tắc bất biến:** Không sửa `baseline_v3/`, không ghi SQL Server, không sửa `predict.py` hay giao diện.

---

## 1. Quy trình hai pha và bảo vệ tuyệt đối tập kiểm thử (T1, T2)

Để loại bỏ hoàn toàn rủi ro rò rỉ thông tin từ tập kiểm thử (`Test leakage`), Giai đoạn 4 được tách nghiêm ngặt thành hai bước:

1. **Bước 4A – Phát triển & Tối ưu trên Validation (KHÔNG mở T1/T2):**
   - Chỉ sử dụng `political_train.csv`, `s140_train_*.csv`, `political_val.csv` và `s140_val_60k.csv`.
   - Các mô hình chỉ fit trên tập `Train` (`E0-Train`, `E1–E6`) được phép đánh giá và lựa chọn siêu tham số (`C`, `sample_weight`, `class_weight`), đặc trưng (`not_`, `char_wb`), và `threshold` trên **`political_val.csv`**. `s140_val_60k.csv` chỉ dùng để theo dõi khả năng duy trì hiệu quả trên miền tổng quát.
   - **Lưu ý phương pháp:** `Validation` là tập phát triển và lựa chọn mô hình, **không phải** tập kiểm định độc lập cuối cùng.
   - **Tuyệt đối không xuất, không xem và không đánh giá `T1` hoặc `T2`** trong suốt Bước 4A.
2. **Cổng chốt mô hình (Freeze Gate) trước khi mở Test:**
   - Sau khi hoàn tất Bước 4A cho toàn bộ `E0–E6`, lập biên bản/manifest chốt cấu hình (`experiments/freeze_manifest.json`) ghi nhận: thời điểm chốt, danh sách artifact `.joblib` được phép đánh giá, `SHA-256` của từng artifact, siêu tham số và `threshold` đã khóa.
3. **Bước 4B / Giai đoạn 5 – Đánh giá một lần trên T1 và T2:**
   - Chỉ mở `political_test_T1.csv` (`T1`) và `s140_test_T2_60k.csv` (`T2`) để đánh giá đúng **một lần** trên các artifact đã chốt trong `freeze_manifest.json`.
   - Sau khi đã mở `T1`/`T2`, **không được phép** sửa đổi mô hình, siêu tham số hay ngưỡng dựa trên kết quả kiểm thử.

---

## 2. Phân biệt rõ E0-Artifact và E0-Train

| Phiên bản E0 | Nguồn gốc | Dữ liệu fit | Tiền xử lý | Ngưỡng (`threshold`) | Cách xử lý khi đối chiếu |
|---|---|---|---|---|---|
| **E0-Artifact** | `baseline_v3/binary_linear_svm.joblib` (đã đóng băng) | `Train + Validation` (`156.840` dòng) | `textsense_clean_v3_context` | `-0.19220128657328076` (giữ nguyên) | **`political_val.csv` không còn độc lập với `E0-Artifact`**. Không tính hoặc dùng chỉ số `E0-Artifact` trên `political_val.csv` để xếp hạng, lựa chọn hay so sánh với `E0-Train` và `E1–E6`. Chỉ đánh giá độc lập trên `T1` sau Freeze Gate như mốc triển khai hiện tại |
| **E0-Train** | Tái hiện mô hình lịch sử theo `TextSense_Notebook_SQLServer_Hoan_Thien_v3.ipynb` | Chỉ `political_train` (`133.314` dòng) | `textsense_clean_v3_context` | Tối ưu F1 trên `political_val` theo đúng hàm `choose_threshold` (Cell 27) và quy trình tạo `binary_metrics.json` (Cell 47/59) | **Không** gán ngưỡng của `E0-Artifact` cho `E0-Train`; không cố ép kết quả tái hiện phải bằng tuyệt đối số lịch sử (`Accuracy=0.9444`, lớp `1` `F1=0.8756`) — nếu có sai khác sẽ báo cáo rõ nguyên nhân và giao thức đánh giá |

---

## 3. Bảng thiết kế cấu hình thí nghiệm E0–E6 (Cô lập từng yếu tố)

Mỗi thí nghiệm chỉ thay đổi **một yếu tố kiểm soát** duy nhất:

| Mã | Yếu tố cô lập | Dữ liệu Train | Tiền xử lý | Vectorizer | Mô hình & Trọng số | Mục tiêu ngưỡng trên `political_val` |
|---|---|---|---|---|---|---|
| **E0-Artifact** | Mốc triển khai đóng băng | Political `Train+Val` (`156.840`) | `v3_context` | Word `(1,2)`, `max_feat=40k`, `min_df=2`, `sublinear_tf=True` | `LinearSVC(C=1.0)`, `class_weight=None` | Giữ nguyên `-0.192201` |
| **E0-Train** | Mốc Train đóng băng | Political `Train` (`133.314`) | `v3_context` | Giữ nguyên E0 | `LinearSVC(C=1.0)`, `class_weight=None` | F1 lớp `1` (tái hiện lịch sử) |
| **E1a** | Đo tác động **riêng** của `v4` khi giữ `C=1.0` (`E0-Train → E1a`) | Political `Train` (`133.314`) | **`textsense_clean_v4`** | Giữ nguyên E0 | **Giữ `C=1.0`**, `class_weight=None` | F1 lớp `1` |
| **E1b** | Đo tác động **riêng** của việc tune `C` trên nền `v4` (`E1a → E1b`); *không quy kết E1b vs E0 là do riêng v4* | Political `Train` (`133.314`) | `textsense_clean_v4` | Giữ nguyên E0 | **Tune `C` ∈ `{0.25, 0.5, 1.0, 2.0}`**, `class_weight=None` | F1 lớp `1` |
| **E2** | Chỉ bổ sung `400k` S140 | Political `133.314` + **S140 `400.000`** (`533.314`) | `textsense_clean_v4` | Giữ nguyên E1 | `C` tốt nhất từ E1b (hoặc `1.0`), `sample_weight=1.0` đều (`r=1.0`) | F1 lớp `1` |
| **E2w** | Chỉ thêm trọng số nguồn (gồm đối chứng `r=1.0`) | Political `133.314` + S140 `400.000` (`533.314`) | `textsense_clean_v4` | Giữ nguyên E2 | Giữ `C` cố định như E2; thử `r ∈ {0.15, 0.25, 0.33, 0.50, 1.0}` (chuẩn hóa `mean(w)=1.0`) | F1 lớp `1` |
| **E3** | Chỉ thêm đặc trưng phủ định | Nền tốt nhất giữa E2 / E2w | `textsense_clean_v4` + **phủ định `not_`** | Word `(1,2)` trên văn bản + token `not_` | Giữ nguyên mô hình & trọng số của nền | F1 lớp `1` |
| **E4a** | Chỉ dùng Char n-gram `(2,5)` | Giống nền E2/E2w | `textsense_clean_v4` | **`char_wb (2,5)`**, `min_df=3`, `max_feat=80k`, `sublinear_tf=True` | Giữ nguyên mô hình & trọng số của nền | F1 lớp `1` |
| **E4b** | Kết hợp Word `(1,2)` + Char `(2,5)` | Giống nền E2/E2w | `textsense_clean_v4` | **`FeatureUnion(Word(1,2) 40k + Char_wb(2,5) 80k)`** | Giữ nguyên mô hình & trọng số của nền | F1 lớp `1` |
| **E5a** | Chỉ thử `class_weight` (giữ F1) | Nền tốt nhất trước E5 | `textsense_clean_v4` | Giữ nguyên đặc trưng nền | **`class_weight`** ∈ `{None, 'balanced', {0:1, 1:1.5}, {0:1, 1:2}}` | **F1** lớp `1` |
| **E5b** | Chỉ đổi mục tiêu ngưỡng sang F2 | Giống E5a | `textsense_clean_v4` | Giữ nguyên E5a | **Giữ `class_weight` tốt nhất của E5a** | **F2** lớp `1` ($\beta=2$) |
| **E6-50k** | Quy mô S140 lồng nhau `50k` | Political `133.314` + **S140 `50.000`** | `textsense_clean_v4` | Khóa giống E2 | Khóa `C`, `class_weight`, `seed=42` giống E2 | **Khóa `threshold` giống E2** (không tối ưu riêng) |
| **E6-120k** | Quy mô S140 lồng nhau `120k` | Political `133.314` + **S140 `120.000`** | `textsense_clean_v4` | Khóa giống E2 | Khóa `C`, `class_weight`, `seed=42` giống E2 | **Khóa `threshold` giống E2** (không tối ưu riêng) |
| **E6-400k** | Quy mô S140 lồng nhau `400k` | Political `133.314` + **S140 `400.000`** | `textsense_clean_v4` | Khóa giống E2 | Khóa `C`, `class_weight`, `seed=42` giống E2 | **Khóa `threshold` giống E2** (không tối ưu riêng) |

---

## 4. Đặc tả chi tiết E3 (Phủ định) và E2w (Trọng số nguồn)

### 4.1. Đặc tả E3 – Đặc trưng phủ định (`not_`, Heuristic Feature)
- **Bản chất:** Đây là **heuristic feature** dựa trên từ vựng, không phải hệ thống phân tích phạm vi phủ định ngữ nghĩa chính xác.
- **Module triển khai & kiểm thử:** [negation_feature.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/scripts/negation_feature.py) và [test_negation_e3.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/tests/test_negation_e3.py) (đã kiểm thử đạt **30/30 câu** gồm phủ định đơn, phủ định kép, phủ định liên tiếp và ngữ cảnh chính trị).
- **Danh sách từ phủ định kích hoạt (`NEGATION_TRIGGERS`):** `{"not", "no", "never", "nobody", "nothing", "neither", "nor", "without"}`.
- **Danh sách stopwords không gắn tiền tố `not_` (`NEGATION_STOPWORDS`):** `{"a", "an", "the", "to", "of", "in", "on", "at", "by", "for", "with", "from", "as", "is", "are", "was", "were", "be", "been", "being", "am", "that", "this", "these", "those", "it", "its", "and", "or", "but", "if", "so", "than", "then"}` — tuyệt đối không gắn `not_` vào các từ chức năng này.
- **Phạm vi phủ định (`window = 3`):** Sau mỗi từ kích hoạt, xét tối đa **3 token tiếp theo**; nếu token không nằm trong `NEGATION_STOPWORDS` và không phải từ kích hoạt khác thì sinh token `not_<token>`. Toàn bộ token gốc và nội dung câu được giữ nguyên ở phần đầu. Ví dụ: `"this is not a good decision"` → `"this is not a good decision not_good not_decision"`.

### 4.2. Kiểm soát E2w – Trọng số theo nguồn và tương tác với `C`
- Trong `LinearSVC`, hàm mục tiêu là $\frac{1}{2}\|w\|^2 + C \sum_i s_i \cdot \ell(y_i, x_i)$. Do `sample_weight` $s_i$ nhân trực tiếp vào hàm mất mát của từng mẫu, nếu thay đổi tổng $\sum_i s_i$ thì độ lớn hiệu dụng của $C$ cũng thay đổi theo.
- **Quy tắc chuẩn hóa bắt buộc:** Chuẩn hóa `sample_weight` sao cho **trung bình trọng số trên toàn tập Train bằng đúng `1.0`** ($\sum_i s_i = N_{\text{train}} = 533.314$) và **giữ `C` cố định** giữa mọi mức $r$.
- **Các mức thử nghiệm (gồm đối chứng `r=1.0`):** $r = w_{\text{s140}} / w_{\text{pol}} \in \{0.15, 0.25, 0.33, 0.50, 1.0\}$. Với $k = \frac{N_{\text{pol}} + N_{\text{s140}}}{N_{\text{pol}} + r \cdot N_{\text{s140}}}$, ta có $w_{\text{pol}} = k$, $w_{\text{s140}} = r \cdot k$.
- Báo cáo riêng cả **tỷ lệ trọng số từng mẫu** ($w_{\text{pol}}, w_{\text{s140}}$) và **tỷ trọng tổng trọng số đóng góp của mỗi nguồn** ($W_{\text{pol}} = N_{\text{pol}} w_{\text{pol}}$, $W_{\text{s140}} = N_{\text{s140}} w_{\text{s140}}$, % mỗi nguồn).

---

## 5. Phương pháp thống kê và kiểm định (Áp dụng ở Bước 4B / Giai đoạn 5)

- **Bootstrap CI 95%:** `n_boot = 1.000`, `random_state = 42`, lấy mẫu có hoàn lại kích thước $N$, tính khoảng tin cậy bằng phương pháp phân vị (`np.percentile([2.5, 97.5])`) cho **Precision, Recall, F1 và PR-AUC** của lớp `1`.
- **Paired Bootstrap:** Khi so sánh chênh lệch $\Delta = \text{metric}(M_A) - \text{metric}(M_B)$ trên cùng tập `T1` (hoặc `T2`), dùng **cùng mảng chỉ số bootstrap `idx`** ở mỗi lần lặp `b = 1..1000` cho cả hai mô hình để tính CI 95% của $\Delta$.
- **McNemar Test:** Áp dụng trên dự đoán nhị phân ghép cặp của hai mô hình trên cùng `T1` (`39.210` dòng):
  - Đếm số cặp bất đồng $b$ (`M_A` đúng, `M_B` sai) và $c$ (`M_A` sai, `M_B` đúng). Các trường hợp hòa (cả hai cùng đúng hoặc cùng sai) không tham gia vào $b + c$.
  - Nếu $b + c = 0$: trả về $p = 1.0$. Nếu $b + c < 25$: dùng kiểm định nhị thức chính xác (`binomtest(min(b, c), b + c, 0.5)`). Nếu $b + c \ge 25$: dùng thống kê $\chi^2$ với hiệu chỉnh liên tục $\frac{(|b - c| - 1)^2}{b + c}$.

---

## 6. Lưu trữ artifact, điều kiện chốt mô hình và trình tự thực hiện

### 6.1. Dữ liệu lưu cho mỗi thí nghiệm (`experiments/<Mã>/`)
Mỗi cấu hình lưu `config.json`, `val_metrics.json`, `model.joblib` kèm: tên thí nghiệm & phiên bản, tập Train/Val sử dụng, `preprocessing_version`, tham số Vectorizer, tham số Model, `sample_weight` & `class_weight`, `threshold` & mục tiêu tối ưu, `random_seed = 42`, thời gian chạy (train & infer), `SHA-256` của `model.joblib`, và kết quả trên `political_val.csv` & `s140_val_60k.csv`.

### 6.2. Điều kiện chốt mô hình (`experiments/freeze_manifest.json`) trước khi mở T1/T2
Trước khi mở `T1`/`T2`, `experiments/freeze_manifest.json` phải ghi nhận đầy đủ:
1. Thời điểm chốt (`created_utc`), `python_version`, phiên bản thư viện (`sklearn`, `pandas`, `numpy`, `scipy`, `joblib`).
2. `SHA-256` của: `model.joblib`, `config.json`, mã nguồn huấn luyện, [preprocessing_v4.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/preprocessing_v4.py) (và `negation_feature.py`), cùng các tập `Train`/`Validation` được sử dụng.
3. `threshold` và phương pháp lựa chọn ngưỡng của từng thí nghiệm (chỉ từ Validation).
4. Danh sách chính xác các artifact được phép đánh giá trên `T1`/`T2`.

### 6.3. Trình tự thực hiện sau khi phê duyệt
1. **Bước 4A:** Chạy lần lượt `E0-Train` (tái hiện), `E1a`, `E1b`, `E2`, `E2w`, `E3`, `E4a`, `E4b`, `E5a`, `E5b`, `E6-50k/120k/400k` — chỉ ghi nhận và báo cáo kết quả trên **Validation**.
2. **Freeze Gate:** Dừng lại / chốt `experiments/freeze_manifest.json` trước khi đánh giá `T1` và `T2`.
3. **Bước 4B (Giai đoạn 5):** Đánh giá các artifact đã chốt trên `T1` và `T2` (kèm Bootstrap 1.000 lần, Paired Bootstrap, McNemar, phân tích lỗi).
