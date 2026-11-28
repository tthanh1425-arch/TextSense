# BÁO CÁO CHIA TẬP DỮ LIỆU VÀ CHUẨN BỊ THÍ NGHIỆM (GIAI ĐOẠN 3 – V4)

**Ngày thực hiện:** 2026-11-27  
**Script thực thi:** [phase3_prepare_splits.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/scripts/phase3_prepare_splits.py)  
**Manifest tổng thể:** [manifest.json](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/manifest.json)  
**Phiên bản tiền xử lý:** `textsense_clean_v4` (`random_seed = 42`)

---

## 1. Cấu trúc thư mục sau khi triển khai

```text
TextSense/
├── baseline_v3/                  # Giữ nguyên tuyệt đối (không chỉnh sửa)
├── data/
│   ├── raw/                      # Dữ liệu gốc (không thay đổi)
│   ├── sampled/                  # Dữ liệu mẫu 520k từ Giai đoạn 1–2
│   └── splits/                   # Các tập dữ liệu chuẩn hóa v4 sẵn sàng cho E0–E6
│       ├── political_train.csv
│       ├── political_val.csv
│       ├── political_test_T1.csv
│       ├── s140_train_400k.csv
│       ├── s140_val_60k.csv
│       ├── s140_test_T2_60k.csv
│       ├── s140_train_e6_50k.csv
│       └── s140_train_e6_120k.csv
├── reports/
│   └── phase3_data_split_report.md
├── preprocessing_v4.py
└── manifest.json
```

---

## 2. Danh sách các tập dữ liệu đã tạo

- **Miền chính trị (giữ nguyên phân chia của `baseline_v3`, áp dụng `textsense_clean_v4` trên cột `text` và lưu kèm `text_v3` để đối chiếu):**
  - `data/splits/political_train.csv` — Mục đích: `Train`
  - `data/splits/political_val.csv` — Mục đích: `Validation` (chọn ngưỡng và siêu tham số phục vụ miền chính trị)
  - `data/splits/political_test_T1.csv` — Mục đích: `Test` (`T1`, được bảo vệ tuyệt đối)
- **Miền Sentiment140 (độc lập hoàn toàn, áp dụng `textsense_clean_v4`):**
  - `data/splits/s140_train_400k.csv` — Mục đích: `Train` (dùng từ `E2` trở đi và `E6-400k`)
  - `data/splits/s140_val_60k.csv` — Mục đích: `Validation` (theo dõi hiệu quả trên miền bổ sung)
  - `data/splits/s140_test_T2_60k.csv` — Mục đích: `Test` (`T2`)
- **Tập con lồng nhau cho thí nghiệm `E6`:**
  - `data/splits/s140_train_e6_50k.csv` — Mục đích: `Train` (`E6-50k`)
  - `data/splits/s140_train_e6_120k.csv` — Mục đích: `Train` (`E6-120k`)

---

## 3. Bảng thống kê số lượng và phân bố nhãn

| Tập dữ liệu | Mục đích | Tổng số dòng | Nhãn `0` (Không tiêu cực) | Nhãn `1` (Tiêu cực) | Rỗng / `< 3` ký tự | Trùng nội bộ |
|---|---|---:|---:|---:|---:|---:|
| `political_train.csv` | Train | `133.314` | `103.974` | `29.340` | `0` | `0` |
| `political_val.csv` | Validation | `23.526` | `18.349` | `5.177` | `0` | `0` |
| `political_test_T1.csv` | Test (`T1`) | `39.210` | `30.581` | `8.629` | `0` | `0` |
| `s140_train_400k.csv` | Train (`E2+`, `E6-400k`) | `400.000` | `200.000` | `200.000` | `0` | `0` |
| `s140_val_60k.csv` | Validation | `60.000` | `30.000` | `30.000` | `0` | `0` |
| `s140_test_T2_60k.csv` | Test (`T2`) | `60.000` | `30.000` | `30.000` | `0` | `0` |
| `s140_train_e6_50k.csv` | Train (`E6-50k`) | `50.000` | `25.000` | `25.000` | `0` | `0` |
| `s140_train_e6_120k.csv` | Train (`E6-120k`) | `120.000` | `60.000` | `60.000` | `0` | `0` |

---

## 4. Kết quả kiểm tra tính lồng nhau E6

- **Phương pháp lấy mẫu:** Lấy lát cắt phân tầng cân bằng (`25.000` mỗi lớp cho `E6-50k`; `60.000` mỗi lớp cho `E6-120k`) từ `s140_train_400k.csv` (đã xáo trộn với `random_seed=42`), sau đó xáo trộn lại bằng `random_state=42`.
- **Kiểm tra tập hợp `orig_idx`:**
  - `set(e6_50k['orig_idx']).issubset(set(e6_120k['orig_idx']))` → **`True`** (`50.000 ⊂ 120.000`)
  - `set(e6_120k['orig_idx']).issubset(set(s140_train_400k['orig_idx']))` → **`True`** (`120.000 ⊂ 400.000`)
- Không có bất kỳ bản ghi nào từ `s140_val_60k.csv` hay `s140_test_T2_60k.csv` trong các tập `E6`.

---

## 5. Kết quả kiểm toán trùng lặp và rò rỉ dữ liệu

| Cặp kiểm tra | Số lượng trùng | Trạng thái |
|---|---:|---|
| `political_train` ↔ `T1` | `0` | Đạt |
| `political_val` ↔ `T1` | `0` | Đạt |
| `political_train` ↔ `political_val` | `0` | Đạt |
| `s140_train_400k` ↔ `T1` | `0` | Đạt |
| `s140_val_60k` ↔ `T1` | `0` | Đạt |
| `T2` ↔ `T1` | `0` | Đạt |
| `s140_train_400k` ↔ `s140_val_60k` | `0` | Đạt |
| `s140_train_400k` ↔ `T2` | `0` | Đạt |
| `s140_val_60k` ↔ `T2` | `0` | Đạt |
| `s140_train_400k` ↔ `political_train` | `0` | Đạt |
| `s140_train_400k` ↔ `political_val` | `0` | Đạt |

---

## 6. Kết quả kiểm tra SHA-256

- **Toàn vẹn `baseline_v3/splits/binary/test.csv` (`T1` gốc):**
  - SHA-256 kỳ vọng (`baseline_v3/binary_manifest.json`): `d6fa7f3fa45ef5bac8eff90673ecb929144921cc84a6b71ffd26afaf3634cf1c`
  - SHA-256 thực tế: `d6fa7f3fa45ef5bac8eff90673ecb929144921cc84a6b71ffd26afaf3634cf1c` (**Khớp 100%, không bị chỉnh sửa**)
- **SHA-256 các tệp trong `data/splits/`:**
  - `political_train.csv`: `af203576bd351cde73526b84eab3d7e7fca1dd4e30be32441154f29855d67902`
  - `political_val.csv`: `65b9fbb2c477475314d9db8016a9db3e7f15b23ff0b5de94b7999ffcd4e65d7f`
  - `political_test_T1.csv`: `5654ab35f4ceb09eb67cc2b781be3909810d1e03a9e47aa9fa9a8c934cf849f0`
  - `s140_train_400k.csv`: `5f74f2540333a083fa5c0f4c4f4e35a2b3ebc7664483e103e99f5525da700cdb`
  - `s140_val_60k.csv`: `b5eb7a5b76d918658f1fc40686f1d18384ae0da2e597d32e951e193699336f74`
  - `s140_test_T2_60k.csv`: `dcd4c1e5920d4ed92bb09459a4d72056e82928ad4952953701d0d3565be0970a`
  - `s140_train_e6_50k.csv`: `7c939de795e285754e14cf6b30de10ac6f008986dbb8313c1e67cc863f9a7ed1`
  - `s140_train_e6_120k.csv`: `8ece80d446408dd1311138366b0ba2d8b497ab7d94c90dc76cad5ab4409df177`

---

## 7. Các vấn đề phát sinh và cách xử lý

- Không có lỗi hay vấn đề phát sinh. Tất cả 8 tệp trong `data/splits/` đều có 0 câu rỗng, 0 câu `< 3` ký tự, 0 trùng lặp nội bộ/chéo, `E6-50k ⊂ E6-120k ⊂ E6-400k`, và `baseline_v3/` được giữ nguyên hoàn toàn.
