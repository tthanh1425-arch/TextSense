# BÁO CÁO XÁC MINH NGUỒN VÀ THỐNG NHẤT SỐ LIỆU (GIAI ĐOẠN 9B)

**Ngày xác minh:** 2026-11-28  
**Trạng thái:** **`PASS WITH WARNINGS`** *(Toàn bộ số liệu cốt lõi đã được xác minh từ nguồn gốc; còn 1 số thông tin cá nhân/trường lớp để placeholder và kiểm thử Chrome DOM ở 8D-2 là `NOT EXECUTED`.)*

---

## 1. Bảng kiểm tra nguồn nội bộ

| Nội dung | Tệp nguồn đã kiểm tra trực tiếp | Số liệu / Thông tin xác minh | Trạng thái |
|---|---|---|---|
| Nguồn dữ liệu chính trị | `baseline_v3/binary_metrics.json`, `reports/data_quality_report.md` | Twitter thô `162.980` (sạch `159.582`); Reddit thô `37.249` (sạch `36.468`); tổng sạch `196.050` | `VERIFIED` |
| Dữ liệu Sentiment140 | `data/sampled/data_manifest.json`, `manifest.json` | Thô `1.523.975`; sạch theo `v4` & loại rò rỉ `1.513.897`; lấy mẫu `520.000` (`Train 400.000`, `Val 60.000`, `T2 60.000`) | `VERIFIED` |
| Tiền xử lý | `baseline_v3/predict.py`, `preprocessing_v4.py`, `reports/preprocessing_v4_report.md` | `E0`: `textsense_clean_v3_context`; `E1–E6`: `textsense_clean_v4` | `VERIFIED` |
| Chia tập dữ liệu | `manifest.json`, `reports/phase3_integrity_verification.md` | Pol (`133.314 / 23.526 / 39.210`); S140 (`400.000 / 60.000 / 60.000`); `E6-50k ⊂ E6-120k ⊂ E6-400k` | `VERIFIED` |
| Cấu hình mô hình chính thức | `baseline_v3/binary_linear_svm.joblib`, `experiments/phase7_model_finalization/phase7_manifest.json` | `E0-Artifact`, `SHA-256: 474b0f5fdce1...`, `C=1.0`, `threshold=-0.19220128657328076`, fit trên `Train+Val` (`156.840`) | `VERIFIED` |
| Kết quả T1 (`39.210`) | `experiments/phase5_final_evaluation/t1_metrics_all_models.csv`, `bootstrap_ci_t1.csv` | `E0-Artifact`: Acc `0.9476`, P(1) `0.8705`, R(1) `0.8951`, F1(1) `0.8826` (`[0.8774, 0.8878]`), PR-AUC `0.9380` (`[0.9336, 0.9423]`) | `VERIFIED` |
| Kết quả T2 (`60.000`) | `experiments/phase5_final_evaluation/t2_metrics_all_models.csv` | `E0-Artifact`: F1(1) `0.4497`, PR-AUC `0.6858` (`E2/E6-400k`: F1 `0.8087`, PR-AUC `0.8763`) | `VERIFIED` |
| Kiến trúc & SQL Server | `system_architecture_inventory.md`, `api_inventory.md`, `sql_readonly_report.md` | `ThreadingHTTPServer` (`8502`), `predict.py`, `database.py`, `TextSenseDB` (`7/7` bảng) | `VERIFIED` |
| Kiểm thử hệ thống | `reports/final_system_test_report.md`, hồ sơ `8A–8D` | 8B (`136/136`, `6` ca OR), 8C (`49/51`, `0` ghi DB), 8D-1 (`PASS`), 8D-2 UI-API (`12/12`), Chrome DOM `NOT EXECUTED` | `VERIFIED` |

---

## 2. Giải quyết mâu thuẫn số liệu Sentiment140

- **Nguyên nhân có hai bộ số liệu trước đây:**
  - Số `1.515.430` / `400.000` (`280k Train + 60k Val + 60k T2`) thuộc **bản khảo sát sơ bộ ban đầu** trước khi áp dụng chuẩn `textsense_clean_v4` và trước chỉ thị giữ đủ `400.000` mẫu `Train`.
  - Số **`1.513.897`** (pool sạch) và **`520.000`** (`400.000` Train + `60.000` Validation + `60.000` Test `T2`) là số liệu **thực tế được xác minh** trong [data_manifest.json](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/data/sampled/data_manifest.json), [manifest.json](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/manifest.json) và [phase3_integrity_verification.md](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/reports/phase3_integrity_verification.md) (sau khi loại `114` rỗng, `122` `< 3` ký tự, `8.493` dòng thuộc `4.135` nhóm mâu thuẫn nhãn, `1.082` trùng nội bộ theo `v4`, `52` trùng `T1`, `208` trùng `Train+Val` chính trị và `7` trùng `sentiment140_test.csv`).
- **Kết luận:** Sử dụng thống nhất bộ số liệu **`1.513.897` / `520.000` (`400k + 60k + 60k`)** trong toàn bộ báo cáo V4.

---

## 3. Phân biệt `E0-Train` vs `E0-Artifact` và Đề xuất cập nhật `README.md`

- `E0-Train` (`Train 133.314`, `T1 Acc=0.9444`, `F1=0.8756`, `PR-AUC=0.9336`) và `E0-Artifact` (`Train+Val 156.840`, `T1 Acc=0.9476`, `P=0.8705`, `R=0.8951`, `F1=0.8826`, `PR-AUC=0.9380`) được tách bạch xuyên suốt.
- **Đề xuất cập nhật `README.md` (chờ phê duyệt, chưa tự sửa):**
  1. Dòng 15: sửa `196.056 mẫu` → `196.050 mẫu`.
  2. Dòng 20: sửa `threshold=-0.2203` → `threshold=-0.19220128657328076`.
  3. Mục 05 (Thông tin mô hình): phân biệt rõ chỉ số `E0-Train` trên `binary_metrics.json` với `E0-Artifact` đang triển khai.
