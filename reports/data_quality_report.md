# BÁO CÁO CHẤT LƯỢNG DỮ LIỆU & KIỂM TRA RÒ RỈ (GIAI ĐOẠN 1 – V4)

**Ngày thực hiện:** 2026-11-27  
**Script thực thi:** [phase1_data_prep.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/scripts/phase1_data_prep.py)  
**Manifest dữ liệu:** [data_manifest.json](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/data/sampled/data_manifest.json)  
**Tệp mẫu đầu ra:**
- Tổng hợp `520.000` mẫu: [sentiment140_520k.csv](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/data/sampled/sentiment140_520k.csv)
- Train (`400.000` mẫu): [sentiment140_train_400k.csv](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/data/sampled/sentiment140_train_400k.csv)
- Validation (`60.000` mẫu): [sentiment140_val_60k.csv](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/data/sampled/sentiment140_val_60k.csv)
- Test `T2` (`60.000` mẫu): [sentiment140_test_60k.csv](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/data/sampled/sentiment140_test_60k.csv)

---

## 1. Kiểm tra dữ liệu Twitter và Reddit

Dữ liệu thô từ `data/raw/Twitter_Data.csv` và `data/raw/Reddit_Data.csv` được đối chiếu trực tiếp với tập sạch và tập chia của `baseline_v3/` (giữ nguyên tuyệt đối `T1` = `39.210` dòng):

| Nguồn | Số dòng thô | Null text | Null category | Rỗng / `< 3` ký tự (strip) | Trùng lặp text thô | Ký tự lỗi `\ufffd` | Giá trị nhãn gốc |
|---|---:|---:|---:|---:|---:|---:|---|
| `Twitter_Data.csv` | `162.980` | 4 | 7 | 1 / 2 | 0 | 7 | `-1.0`, `0.0`, `1.0`, `NaN` |
| `Reddit_Data.csv` | `37.249` | 100 | 0 | 121 / 136 | 350 | 0 | `-1`, `0`, `1` |
| **Tổng thô** | **`200.229`** | **104** | **7** | **122 / 138** | **350** | **7** | |

Sau quy trình làm sạch của baseline v3 (loại null, loại `< 3` ký tự sau chuẩn hóa, loại `2` nhóm/`14` dòng mâu thuẫn nhãn, loại `3.883` dòng trùng token):
- **Twitter sạch:** `159.582` dòng (`34.919` Tiêu cực, `124.663` Không tiêu cực).
- **Reddit sạch:** `36.468` dòng (`8.227` Tiêu cực, `28.241` Không tiêu cực).
- **Tổng chính trị sạch:** `196.050` dòng (`43.146` Tiêu cực [22,01%], `152.904` Không tiêu cực [77,99%]).
- Chia tập `baseline_v3/splits/binary/`: Train `133.314`, Validation `23.526`, Test `T1` `39.210`.

---

## 2. Kiểm tra và làm sạch dữ liệu Sentiment140

Nguồn chính: `data/raw/sentiment140_train.csv` (bản sao khớp SHA-256 với `01_TRAIN_MODEL/data/archive (3)/train_data.csv`).

### 2.1. Quy ước nhãn thực tế
- Cột `sentiment` trong tệp CSV thực tế sử dụng giá trị **`0`** (Negative, `767.059` dòng) và **`1`** (Positive, `756.916` dòng), không dùng `0/4`.
- Ánh xạ sang nhãn nhị phân TextSense:
  - `orig_sentiment = 0` → `label = 1` (**Tiêu cực**)
  - `orig_sentiment = 1` → `label = 0` (**Không tiêu cực**)
- Không suy diễn lớp trung tính vì Sentiment140 chỉ có 2 cực emoticon proxy.

### 2.2. Quy trình làm sạch từng bước

| Bước xử lý | Số dòng bị loại | Số dòng còn lại | Ghi chú |
|---|---:|---:|---|
| Dữ liệu thô `sentiment140_train.csv` | — | `1.523.975` | 0 null, 0 HTML entity `&...;`, 0 URL, 0 `\ufffd` |
| Loại khóa chuẩn hóa rỗng (`len == 0`) | `114` | `1.523.861` | Câu chỉ gồm khoảng trắng / ký tự không mang token |
| Loại câu quá ngắn (`0 < len < 3`) | `122` | `1.523.739` | Câu 1–2 ký tự không đủ ngữ cảnh |
| Loại nhóm mâu thuẫn nhãn (`4.135` nhóm) | `8.493` | `1.515.246` | Quy tắc: cùng văn bản chuẩn hóa v4 xuất hiện cả `0` và `1` → loại toàn bộ nhóm để tránh nhiễu nhãn proxy |
| Loại trùng lặp nội bộ (`keep='first'`) | `1.082` | `1.514.164` | Giữ lại 1 bản ghi đại diện cho mỗi văn bản chuẩn hóa v4 |
| Loại bản ghi trùng `T1` (Test chính trị) | `52` | `1.514.112` | **Bảo vệ tuyệt đối `T1`** |
| Loại bản ghi trùng Train/Val chính trị | `208` | `1.513.904` | Tránh trùng lặp chéo giữa miền chính trị và Sentiment140 |
| Loại bản ghi trùng `sentiment140_test.csv` (`359`) | `7` | **`1.513.897`** | Giữ độc lập cho tập `T2a` |

**Nguồn sạch sẵn sàng lấy mẫu (`clean_pool`):** `1.513.897` dòng (`761.963` Tiêu cực `1`, `751.934` Không tiêu cực `0`).

### 2.3. Lấy mẫu phân tầng 520.000 dòng (400k Train + 60k Val + 60k T2)
- `random_state = 42`, lấy mẫu phân tầng `260.000` câu Tiêu cực (`1`) và `260.000` câu Không tiêu cực (`0`) từ `clean_pool`, sau đó tách rời hoàn toàn thành 3 tập cân bằng 50/50:
  - **Train:** `400.000` dòng (`200.000` Tiêu cực `1`, `200.000` Không tiêu cực `0`)
  - **Validation:** `60.000` dòng (`30.000` Tiêu cực `1`, `30.000` Không tiêu cực `0`)
  - **Test `T2`:** `60.000` dòng (`30.000` Tiêu cực `1`, `30.000` Không tiêu cực `0`)
- Mỗi bản ghi lưu kèm `orig_idx` (chỉ mục dòng gốc trong `sentiment140_train.csv`).

---

## 3. Phân bố dữ liệu tổng hợp sau xử lý

| Nguồn / Tập | Tiêu cực (`1`) | Không tiêu cực (`0`) | Tổng |
|---|---:|---:|---:|
| Twitter (sạch, trong `baseline_v3` splits) | `34.919` | `124.663` | `159.582` |
| Reddit (sạch, trong `baseline_v3` splits) | `8.227` | `28.241` | `36.468` |
| Sentiment140 — Train | `200.000` | `200.000` | `400.000` |
| Sentiment140 — Validation | `30.000` | `30.000` | `60.000` |
| Sentiment140 — Test `T2` | `30.000` | `30.000` | `60.000` |
| **Tổng cộng** | **`303.146`** | **`412.904`** | **`716.050`** |

*(Ghi chú: Không sử dụng `real_world_eval_tweets.csv`.)*

---

## 4. Kiểm tra rò rỉ dữ liệu (Leakage Audit)

Kiểm tra trùng lặp dựa trên khóa chuẩn hóa (`NFKC`, `casefold`, bỏ dấu câu/underscore, chuẩn hóa khoảng trắng):

| Cặp kiểm tra | Số lượng trùng lặp | Trạng thái |
|---|---:|---|
| Political `Train` ↔ `T1` (`test.csv`) | `0` | Đạt |
| Political `Validation` ↔ `T1` (`test.csv`) | `0` | Đạt |
| Political `Train` ↔ `Validation` | `0` | Đạt |
| Sentiment140 `Train (400k)` ↔ `Validation (60k)` ↔ `Test T2 (60k)` | `0` | Đạt |
| Sentiment140 `520k` ↔ `T1` (`39.210` dòng) | `0` (đã loại `53` dòng từ pool) | Đạt |
| Sentiment140 `520k` ↔ Political `Train + Validation` | `0` (đã loại `208` dòng từ pool) | Đạt |
| Sentiment140 `520k` ↔ `sentiment140_test.csv` (`359` dòng) | `0` (đã loại `7` dòng từ pool) | Đạt |
| Trùng lặp nội bộ trong `sentiment140_520k.csv` | `0` | Đạt |

*(Lưu ý: Ở Giai đoạn 2, sau khi áp dụng hàm `normalize_text` phiên bản `textsense_clean_v4`, sẽ chạy lại một lượt kiểm tra trùng lặp sau chuẩn hóa v4 giữa Twitter, Reddit, Sentiment140 `520k` và `T1`.)*
