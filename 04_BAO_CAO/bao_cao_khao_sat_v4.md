# BÁO CÁO KHẢO SÁT DỰ ÁN TEXTSENSE (GIAI ĐOẠN 0 – V4)

**Ngày khảo sát:** 2026-11-27  
**Phạm vi:** Rà soát toàn bộ cấu trúc dự án, baseline v3, dữ liệu nguồn (Twitter, Reddit, Sentiment140), quy trình tiền xử lý – huấn luyện – suy luận – giao diện – SQL Server, và đề xuất kế hoạch triển khai Giai đoạn 1–9 theo Master Prompt V4.  
**Tuân thủ quy định:** Không đọc nội dung, không phân tích và không sử dụng `real_world_eval_tweets.csv` trong bất kỳ bước nào. Không ghi dữ liệu vào SQL Server. Không sửa đổi `baseline_v3/`.

---

## 1. Cấu trúc dự án hiện tại

```text
TextSense/
├── 01_TRAIN_MODEL/
│   ├── TextSense_Notebook_SQLServer_Hoan_Thien_v3.ipynb   # Notebook huấn luyện chính (69 cells)
│   ├── requirements.txt                                   # Thư viện huấn luyện (scikit-learn==1.9.1)
│   ├── data/                                              # Dữ liệu gốc + archive (3)/ (Sentiment140)
│   └── outputs/                                           # Artifact v3 đang triển khai + splits/binary/
├── 02_SQL_SERVER/
│   ├── textsense.sql                                      # Schema TextSenseDB (257 dòng)
│   └── requirements.txt                                   # pyodbc>=5.2,<6
├── 03_GIAO_DIEN/
│   ├── serve_textsense.py                                 # Web server & HTTP API (cổng 8502)
│   ├── predict.py                                         # Module suy luận dùng chung cho CLI & Web
│   ├── database.py                                        # Kết nối & truy vấn SQL Server
│   ├── requirements.txt
│   └── web/                                               # Frontend tĩnh (index.html, app.js, style.css, ...)
├── 04_BAO_CAO/                                            # Tài liệu & biểu đồ minh chứng v3
├── baseline_v3/                                           # Bản đóng băng baseline v3
├── data/
│   ├── raw/                                               # Twitter_Data.csv, Reddit_Data.csv, sentiment140_*.csv
│   └── processed/                                         # Đang trống
├── experiments/
│   ├── eval_e0.py                                         # Script đánh giá E0 cũ (cần cập nhật loại real_world & T3)
│   └── e0_baseline_results.json                           # Kết quả E0 cũ
├── reports/
│   └── bao_cao_khao_sat_v4.md                             # Báo cáo này
├── tests/
│   └── test_web_sentiment.py                              # Smoke/regression test (11 test functions)
└── .venv-1/                                               # Môi trường ảo Python 3.14.8
```

---

## 2. Thành phần hiện có và mối liên hệ

- **Huấn luyện (`01_TRAIN_MODEL/`):** `TextSense_Notebook_SQLServer_Hoan_Thien_v3.ipynb` đọc `Twitter_Data.csv` và `Reddit_Data.csv`, làm sạch bằng `normalize_text` (`textsense_clean_v3_context`), chia Train/Validation/Test (68%/12%/20%), tối ưu `C` qua 5-fold StratifiedKFold (`scoring='average_precision'`), chọn ngưỡng quyết định tối ưu F1 lớp `1` trên Validation, đánh giá trên Test, sau đó fit lại `final_pipeline` trên `Train + Validation` và xuất ra `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib`.
- **Suy luận & Giao diện (`03_GIAO_DIEN/`):** `serve_textsense.py` import `predict`, `normalize_text`, `OUTPUT` từ `03_GIAO_DIEN/predict.py` và tải trực tiếp `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib`.
- **Cơ sở dữ liệu (`02_SQL_SERVER/textsense.sql`, `03_GIAO_DIEN/database.py`):** Định nghĩa các bảng `dbo.Tweets`, `dbo.TweetTokens`, `dbo.TrainingRuns`, `dbo.PredictionBatches`, `dbo.Predictions`, `dbo.UserFeedback`, `dbo.Users`. Khi SQL Server không khả dụng, hệ thống web vẫn trả kết quả dự đoán bình thường nhưng `history_saved=False`.
- **Kiểm thử (`tests/test_web_sentiment.py`):** Chạy qua `.\.venv-1\Scripts\python.exe tests/test_web_sentiment.py` cho kết quả **ALL TESTS PASSED!** (11 hàm test với `fake_model` và mock `pyodbc`).

---

## 3. Baseline v3 (Đã kiểm tra & đóng băng hoàn chỉnh)

Đã đối chiếu SHA-256 giữa các tệp đang hoạt động (`01_TRAIN_MODEL/outputs/`, `03_GIAO_DIEN/predict.py`) và `baseline_v3/`: **khớp 100%**. Đã bổ sung bản sao `TextSense_Notebook_SQLServer_Hoan_Thien_v3.ipynb` và `requirements.txt` vào `baseline_v3/` để bảo đảm tái lập đầy đủ.

| Thông số | Giá trị thực tế trong Baseline v3 |
|---|---|
| Phiên bản tiền xử lý | `textsense_clean_v3_context` |
| Vectorizer | `TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_features=40000, sublinear_tf=True, dtype=np.float32)` |
| Classifier | `LinearSVC(C=1.0, class_weight=None, max_iter=3000, random_state=42)` |
| Ngưỡng quyết định (`threshold`) | `-0.19220128657328076` (tối ưu F1 lớp `1` trên Validation) |
| Ánh xạ nhãn | `-1 -> 1 (Tiêu cực)`, `0 -> 0`, `1 -> 0 (Không tiêu cực)` |
| Chia tập (`seed=42`, stratify `label__source`) | Train: `133.314` (68%), Validation: `23.526` (12%), Test: `39.210` (20%) — Tổng sạch: `196.050` |
| Huấn luyện artifact `.joblib` cuối | `trained_on = 'train+validation'` (`156.840` dòng) |
| Chỉ số Test (trong `binary_metrics.json`, fit trên Train) | Accuracy: `0.9444`, Macro F1: `0.9199`; Lớp `1`: Precision `0.8628`, Recall `0.8887`, F1 `0.8756` |
| Chỉ số Test (trong `e0_baseline_results.json`, dùng `.joblib` fit trên Train+Val) | `T1_overall` (n=39.210): Accuracy `0.9480`, Precision `0.8722`, Recall `0.8947`, F1 `0.8833` (45 dòng bị skip bởi `predict.py`) |
| Môi trường Python & thư viện (`.venv-1`) | Python `3.14.8`, `scikit-learn==1.9.1`, `pandas==3.1.1`, `numpy==2.5.5`, `scipy==1.18.1`, `joblib==1.6.0` |

---

## 4. Dữ liệu Twitter và Reddit

Kiểm tra trực tiếp `data/raw/Twitter_Data.csv` và `data/raw/Reddit_Data.csv` (SHA-256 trùng khớp 100% với bản trong `01_TRAIN_MODEL/data/`):

| Nguồn | Số dòng ban đầu | Cột | Null | Phân bố nhãn gốc |
|---|---:|---|---|---|
| `Twitter_Data.csv` | `162.980` | `['clean_text', 'category']` | `clean_text`: 4, `category`: 7 | `1.0`: 72.250; `0.0`: 55.213; `-1.0`: 35.510; `NaN`: 7 |
| `Reddit_Data.csv` | `37.249` | `['clean_comment', 'category']` | `clean_comment`: 100 | `1`: 15.830; `0`: 13.142; `-1`: 8.277 |
| **Tổng thô** | **`200.229`** | | | **`-1`: 43.787; `0`: 68.355; `1`: 88.080** |

Sau quy trình làm sạch v3 trong `binary_metrics.json`: còn `196.050` dòng sạch duy nhất (`Twitter`: `159.582`, `Reddit`: `36.468`; lớp `0`: `152.904` [77,99%], lớp `1`: `43.146` [22,01%]).

---

## 5. Dữ liệu Sentiment140

Kiểm tra trực tiếp `data/raw/sentiment140_train.csv` và `data/raw/sentiment140_test.csv` (SHA-256 trùng khớp 100% với `01_TRAIN_MODEL/data/archive (3)/train_data.csv` và `test_data.csv`):

| Tệp | Số dòng | Cột | Null | Phân bố cột `sentiment` |
|---|---:|---|---|---|
| `sentiment140_train.csv` | `1.523.975` | `['sentence', 'sentiment']` | 0 | `0` (Negative): `767.059`; `1` (Positive): `756.916` |
| `sentiment140_test.csv` | `359` | `['sentence', 'sentiment']` | 0 | `0` (Negative): `177`; `1` (Positive): `182` |

**Xác nhận khả năng lấy mẫu 520.000 dòng (400.000 Train + 60.000 Validation + 60.000 Test T2):**
- Sau khi kiểm tra trùng lặp sơ bộ (`casefold + strip`) và loại `4.125` nhóm câu có nhãn mâu thuẫn trên `sentiment140_train.csv`, còn **`1.515.430` dòng duy nhất không mâu thuẫn** (`0` Negative: `762.858`; `1` Positive: `752.572`).
- **Kết luận:** Dữ liệu **hoàn toàn đủ điều kiện** để lấy mẫu phân tầng `520.000` dòng (`260.000` Negative + `260.000` Positive) gồm `400.000` Train, `60.000` Validation và `60.000` Test `T2` độc lập mà không cần tạo dữ liệu giả.

---

## 6. Các vấn đề kỹ thuật phát hiện

1. **Nhãn Sentiment140 trong CSV thực tế là `0` và `1`, không phải `0` và `4`:** Tệp `train_data.csv` và `test_data.csv` trong `archive (3)` đã mã hóa sẵn `0 = Negative` (`-> 1`), `1 = Positive` (`-> 0`). Cần dùng đúng ánh xạ này khi xử lý Giai đoạn 1.
2. **Dấu nháy bị tách khoảng trắng trong Sentiment140:** Kiểm tra mẫu thực tế cho thấy nhiều câu trong `sentiment140_train.csv` có dạng `can t`, `that s`, `didn t` (dấu nháy đã bị thay bằng khoảng trắng từ nguồn gốc). Logic `_CONTRACTIONS` ở v3 chưa xử lý dạng tách khoảng trắng và chưa xử lý `i'm`, `it's`, HTML entities (`&amp;`, `&lt;`, `&gt;`). Cần chuẩn hóa cẩn thận trong `textsense_clean_v4` (lưu ý tránh thay nhầm `it s` / `he s` nếu không an toàn, hoặc kiểm tra kỹ trên 30 câu thử nghiệm).
3. **Tham chiếu notebook cũ trong `predict.py`:** `03_GIAO_DIEN/predict.py` (dòng 78, 85, 96, 177) vẫn ghi tên `TextSense_Notebook_SQLServer_Hoan_Thien_v2.ipynb` thay vì `v3`.
4. **Tệp `03_GIAO_DIEN/web/model_weights.json` dư thừa/lệch ngưỡng:** Chứa `threshold: -0.220318...` (cũ), không khớp `binary_linear_svm.joblib` (`-0.192201...`), tuy nhiên `serve_textsense.py` không sử dụng tệp này.
5. **Script `experiments/eval_e0.py` và `e0_baseline_results.json` còn chứa bộ đánh giá cũ:** Vẫn đang gọi `real_world_eval_tweets.csv` và đặt tên `T3_s140_test`. Cần viết lại/cập nhật quy trình đánh giá v4 loại bỏ hoàn toàn `real_world_eval_tweets.csv`.
6. **SQL Server:** Trong môi trường kiểm tra hiện tại, `sql_server_status()` báo chưa kết nối được instance mặc định (`available: False`). Theo quy định v4, giữ chế độ chỉ đọc/không ghi vào `TrainingRuns` nếu chưa được cho phép.
7. **Baseline `.joblib` được fit trên `Train + Validation`:** Cần lưu ý khi đánh giá E0 trên `T1` (`test.csv`), kết quả của `binary_linear_svm.joblib` (`F1 = 0.8833`) cao hơn nhẹ so với con số `0.8756` trong `binary_metrics.json` (vốn đo trên mô hình fit bằng `Train`). Cần ghi rõ điều này khi lập bảng so sánh E0–E6 để đảm bảo công bằng.

---

## 7. Các vấn đề phương pháp nghiên cứu

1. **Khác biệt miền (Domain Shift):** `Twitter_Data.csv` và `Reddit_Data.csv` tập trung vào thảo luận chính trị Ấn Độ (từ khóa top: `modi`, `india`, `bjp`, `congress`), trong khi `Sentiment140` là tweet đời thường tiếng Anh. Nếu bổ sung 280.000 mẫu Sentiment140 vào Train (gấp >2 lần tập Train chính trị `133.314`), mô hình có nguy cơ bị Sentiment140 lấn át -> Cần thực nghiệm E2w (trọng số theo nguồn) và E6 (50k / 120k / 400k).
2. **Khác biệt quy ước nhãn proxy:** Twitter/Reddit gốc có 3 lớp (`-1, 0, 1`, trong đó `0` và `1` gộp thành `0`), còn Sentiment140 chỉ có 2 cực (`0` Negative, `1` Positive) dựa trên emoticon proxy. Không được coi nhãn proxy là nhãn do con người xác nhận, và không được kết luận mô hình hiểu ngữ cảnh chính trị tốt hơn chỉ vì điểm trên T2 tăng.
3. **Rò rỉ dữ liệu:** Cần kiểm tra trùng lặp giữa `Twitter/Reddit` (đặc biệt tập Test `T1` đã đóng băng) và `400.000` mẫu `Sentiment140` (sau chuẩn hóa `textsense_clean_v4`) để bảo đảm không có câu nào trong `T1` hoặc `T2` lọt vào tập `Train`.

---

## 8. Những thành phần cần giữ nguyên

- Thư mục `baseline_v3/` (đóng băng hoàn toàn, không chỉnh sửa).
- Tập `Test` chính trị của baseline (`baseline_v3/splits/binary/test.csv`, `39.210` dòng) làm bộ kiểm thử ưu tiên `T1`.
- Giao diện web `03_GIAO_DIEN/web/` và cấu trúc API hiện tại (chỉ cập nhật mô hình/tiền xử lý nếu mô hình mới thắng ở Giai đoạn 7).
- Schema SQL Server `02_SQL_SERVER/textsense.sql` (không tự ý migration hoặc ghi dữ liệu).

---

## 9. Kế hoạch thay đổi chi tiết (Giai đoạn 1–9)

- **Giai đoạn 1 (Kiểm tra & chuẩn hóa dữ liệu):** Làm sạch & kiểm tra chất lượng Twitter, Reddit, Sentiment140; kiểm tra rò rỉ dữ liệu chéo giữa các nguồn và bảo vệ tuyệt đối `T1` (`39.210` dòng Test chính trị của baseline v3 — loại mọi bản ghi Sentiment140 trùng với `T1` khỏi tập dữ liệu); lấy mẫu phân tầng **`520.000` dòng Sentiment140** (`260.000` Negative, `260.000` Positive, `seed=42`) gồm **`400.000` Train** (`200.000` Neg / `200.000` Pos), **`60.000` Validation** (`30.000` Neg / `30.000` Pos) và **`60.000` Test `T2`** (`30.000` Neg / `30.000` Pos) độc lập hoàn toàn; xuất `reports/data_quality_report.md` và manifest dữ liệu.
- **Giai đoạn 2 (Tiền xử lý v4):** Xây dựng hàm `normalize_text` duy nhất (`PREPROCESSING_VERSION = 'textsense_clean_v4'`) xử lý từ viết tắt (kể cả dạng tách khoảng trắng an toàn) và HTML entities; kiểm tra trùng lặp dữ liệu sau chuẩn hóa v4 giữa Twitter, Reddit, Sentiment140 (`520.000` mẫu) và `T1`; kiểm thử trên 30 câu đại diện; xuất `reports/preprocessing_v4_report.md`.
- **Giai đoạn 3 (Chia tập dữ liệu):** Xác nhận và đóng băng phân chia độc lập `400.000` Train / `60.000` Validation / `60.000` Test `T2` cho Sentiment140, lưu chỉ mục/splits/manifest vào `data/splits/` và `manifest.json`. Giữ nguyên tuyệt đối `T1` (`39.210` dòng) của baseline v3; không dùng `T1` trong bất kỳ bước huấn luyện, chọn đặc trưng, chọn tham số hay chọn ngưỡng nào.
- **Giai đoạn 4 (Thí nghiệm E0–E6):** Chạy tuần tự E0, E1, E2 (`Train` chính trị + đủ **`400.000` mẫu Sentiment140 Train**), E2w, E3 (phủ định `not_`), E4 (char n-gram 2–5), E5 (class weight + ngưỡng F2 trên Validation chính trị), E6 với các mức dữ liệu Sentiment140 Train là **`50.000`, `120.000` và `400.000` dòng** (lấy lồng nhau từ cùng tập `400.000` Train, giữ nguyên `60.000` Validation và `60.000` Test `T2` độc lập). Sử dụng Validation chính trị để chọn ngưỡng/điều chỉnh mô hình phục vụ miền chính trị; Validation Sentiment140 để theo dõi miền bổ sung. Lưu từng thư mục `experiments/E0/` ... `experiments/E6/`.
- **Giai đoạn 5 (Đánh giá & Phân tích lỗi):** Chuẩn hóa quy trình đánh giá E0–E6 trên cùng `T1` (tiêu chí chính) và `T2` (tiêu chí bổ sung) với cùng nguyên tắc tính chỉ số, ghi nhận chính xác số dòng được đánh giá và số dòng bị bỏ qua; phân biệt rõ baseline fit trên `Train` với artifact fit trên `Train + Validation`. Tính Precision/Recall/F1 lớp `1`, PR-AUC, Accuracy, Specificity, Bootstrap 1.000 lần (CI 95%), McNemar, phân tích lỗi chi tiết vào `reports/error_analysis.md`.
- **Giai đoạn 6 (RoBERTa tham chiếu - tùy chọn):** Chuẩn bị script/notebook chạy `cardiffnlp/twitter-roberta-base-sentiment-latest` (chỉ suy luận, không train lại) nếu có GPU/Colab.
- **Giai đoạn 7 (Lựa chọn & Tích hợp):** Áp dụng bộ tiêu chí lựa chọn (ưu tiên F1 & Recall lớp `1` trên `T1`, không suy giảm `T2`). Cập nhật `predict.py` và model triển khai nếu vượt baseline; nếu không, giữ baseline.
- **Giai đoạn 8 (Kiểm thử toàn hệ thống):** Kiểm thử parity notebook vs web trên 100 câu T1/T2, kiểm thử tiền xử lý, đầu vào biên, SQL Server (chỉ đọc), mô hình, tái lập. Xuất `reports/final_system_test_report.md`.
- **Giai đoạn 9 (Hoàn thiện hồ sơ):** Tổng hợp đầy đủ bộ báo cáo học thuật, hướng dẫn sử dụng, tài liệu triển khai và manifest cuối cùng.

---

## 10. Danh sách công việc tiếp theo

Chờ người dùng xem xét và phê duyệt **Giai đoạn 0** trước khi tiến hành **Giai đoạn 1: Kiểm tra và chuẩn hóa dữ liệu** (`Twitter_Data.csv`, `Reddit_Data.csv`, `sentiment140_train.csv`).
