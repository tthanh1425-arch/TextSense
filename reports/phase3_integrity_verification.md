# BÁO CÁO XÁC MINH TOÀN VẸN DỮ LIỆU GIAI ĐOẠN 3 (V4)

**Ngày kiểm tra:** 2026-11-27  
**Phạm vi:** Xác minh tính lồng nhau của các tập `E6`, đối chiếu `SHA-256` của `T1` (`baseline_v3/splits/binary/test.csv` ↔ `data/splits/political_test_T1.csv`) và toàn bộ 8 tệp trong `data/splits/` so với [manifest.json](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/manifest.json).

---

## 1. Kết quả giao nhau giữa các tập E6

Kiểm tra dựa trên bộ ba `(orig_idx, text, label)` để xác minh đồng thời chỉ mục gốc, nội dung văn bản và nhãn:

| Cặp so sánh | Số dòng tập A | Số dòng tập B | Số bản ghi giao nhau | Sai khác (`A - B`) |
|---|---:|---:|---:|---:|
| `E6-50k` vs `E6-120k` | `50.000` | `120.000` | `50.000` | `0` |
| `E6-50k` vs `E6-400k` | `50.000` | `400.000` | `50.000` | `0` |
| `E6-120k` vs `E6-400k` | `120.000` | `400.000` | `120.000` | `0` |

---

## 2. Kết quả xác minh tính lồng nhau

- `E6-50k`: `50.000` bản ghi duy nhất (`25.000` Tiêu cực / `25.000` Không tiêu cực).
- `E6-120k`: `120.000` bản ghi duy nhất (`60.000` Tiêu cực / `60.000` Không tiêu cực).
- `E6-400k`: `400.000` bản ghi duy nhất (`200.000` Tiêu cực / `200.000` Không tiêu cực).
- Quan hệ bao hàm nghiêm ngặt: **`E6-50k ⊂ E6-120k ⊂ E6-400k`** được xác nhận đúng 100%, không có bản ghi ngoài dự kiến hay sai lệch `orig_idx` / nhãn.

---

## 3. Kết quả kiểm tra SHA-256 của T1

| Tệp | SHA-256 thực tế | Ghi chú |
|---|---|---|
| `baseline_v3/splits/binary/test.csv` | `d6fa7f3fa45ef5bac8eff90673ecb929144921cc84a6b71ffd26afaf3634cf1c` | Khớp 100% `baseline_v3/binary_manifest.json` (không bị sửa) |
| `data/splits/political_test_T1.csv` | `5654ab35f4ceb09eb67cc2b781be3909810d1e03a9e47aa9fa9a8c934cf849f0` | Khác SHA-256 tệp do bổ sung 2 cột metadata `text_v3` và `preprocessing_version` |

**Đối chiếu nội dung từng dòng giữa hai tệp `T1` (`39.210` dòng):**
- Số dòng bằng nhau: `True` (`39.210` dòng).
- Khớp 100% cột `source`: `True`.
- Khớp 100% cột `text_v3 == baseline.text`: `True`.
- Khớp 100% cột `category`: `True`.
- Khớp 100% cột `label`: `True`.
- Số dòng có `text` (chuẩn hóa v4) khác `text_v3`: **`0`** (nội dung văn bản của `T1` sau v4 trùng khớp 100% với bản gốc `baseline_v3`).

---

## 4. SHA-256 của 8 tệp split trong `data/splits/`

Tất cả 8 tệp đều khớp 100% với `manifest.json` (không thiếu, không sai lệch):

| Tệp trong `data/splits/` | Số dòng | Khớp `manifest.json` | SHA-256 |
|---|---:|:---:|---|
| `political_train.csv` | `133.314` | `True` | `af203576bd351cde73526b84eab3d7e7fca1dd4e30be32441154f29855d67902` |
| `political_val.csv` | `23.526` | `True` | `65b9fbb2c477475314d9db8016a9db3e7f15b23ff0b5de94b7999ffcd4e65d7f` |
| `political_test_T1.csv` | `39.210` | `True` | `5654ab35f4ceb09eb67cc2b781be3909810d1e03a9e47aa9fa9a8c934cf849f0` |
| `s140_train_400k.csv` | `400.000` | `True` | `5f74f2540333a083fa5c0f4c4f4e35a2b3ebc7664483e103e99f5525da700cdb` |
| `s140_val_60k.csv` | `60.000` | `True` | `b5eb7a5b76d918658f1fc40686f1d18384ae0da2e597d32e951e193699336f74` |
| `s140_test_T2_60k.csv` | `60.000` | `True` | `dcd4c1e5920d4ed92bb09459a4d72056e82928ad4952953701d0d3565be0970a` |
| `s140_train_e6_50k.csv` | `50.000` | `True` | `7c939de795e285754e14cf6b30de10ac6f008986dbb8313c1e67cc863f9a7ed1` |
| `s140_train_e6_120k.csv` | `120.000` | `True` | `8ece80d446408dd1311138366b0ba2d8b497ab7d94c90dc76cad5ab4409df177` |

---

## 5. Phân biệt trùng lặp có chủ đích và trùng lặp không được phép

- **Trùng lặp có chủ đích (Hợp lệ):** `50.000` bản ghi của `E6-50k` nằm trong `E6-120k`, và `120.000` bản ghi của `E6-120k` nằm trong `E6-400k` (`s140_train_400k.csv`). Đây là thiết kế lồng nhau bắt buộc để đánh giá ảnh hưởng kích thước dữ liệu Sentiment140 trên cùng phân phối, không được loại bỏ.
- **Trùng lặp không được phép (Rò rỉ):** Trùng lặp nội bộ trong từng tập, trùng lặp giữa `Train` ↔ `Validation` ↔ `Test` (`T1` và `T2`), hoặc trùng lặp giữa `Sentiment140` với `T1` / `Train+Val` chính trị. Kết quả kiểm tra thực tế ở tất cả các cặp này đều bằng **`0`**.

---

## 6. Kết luận về tính toàn vẹn dữ liệu

Toàn bộ dữ liệu chia tập ở Giai đoạn 3 đạt **toàn vẹn 100%**: `baseline_v3/` nguyên vẹn, `T1` (`39.210` dòng) được bảo vệ tuyệt đối, `T2` (`60.000` dòng) độc lập hoàn toàn, ba tập `E6` lồng nhau chính xác, và cả 8 tệp trong `data/splits/` khớp SHA-256 với [manifest.json](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/manifest.json). Hệ thống dữ liệu sẵn sàng cho **Giai đoạn 4 – Xây dựng và chạy thí nghiệm E0–E6** khi được phê duyệt.
