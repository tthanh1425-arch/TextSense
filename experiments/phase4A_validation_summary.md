# TỔNG HỢP KẾT QUẢ BƯỚC 4A – VALIDATION (E0–E6)

**Ngày hoàn tất:** 2026-11-27T09:06:31.714498+00:00  
**Trạng thái:** Đã chốt `experiments/freeze_manifest.json`. **Chưa mở `T1` và `T2`.**  
*(Ghi chú: `E0-Artifact` được fit trên `Train + Validation` nên không đánh giá và không xếp hạng trên `political_val.csv`.)*

## 1. Bảng so sánh trên Political Validation (`23.526` dòng) & S140 Validation (`60.000` dòng)

| Mã | Prep | Pol Precision (1) | Pol Recall (1) | Pol F1 (1) | Pol PR-AUC | Pol Acc | S140 F1 (1) | Threshold | Train (s) | SHA-256 (12) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| E0-Train | `textsense_clean_v3_context` | 0.8676 | 0.8911 | 0.8792 | 0.9372 | 0.9461 | 0.4496 | -0.1922 | 8.75 | `04613c64ec74` |
| E1a | `textsense_clean_v4` | 0.8676 | 0.8911 | 0.8792 | 0.9372 | 0.9461 | 0.4509 | -0.1922 | 8.40 | `f623bbc355d9` |
| E1b | `textsense_clean_v4` | 0.8608 | 0.8997 | 0.8799 | 0.9336 | 0.9459 | 0.4507 | -0.2202 | 8.56 | `10706924ff67` |
| E2 | `textsense_clean_v4` | 0.6420 | 0.7294 | 0.6829 | 0.7403 | 0.8509 | 0.8068 | -0.2379 | 28.82 | `f9ada6dcb928` |
| E2w | `textsense_clean_v4` | 0.7873 | 0.8157 | 0.8013 | 0.8689 | 0.9109 | 0.7827 | -0.1879 | 33.09 | `c5d4127ade98` |
| E3 | `textsense_clean_v4+negation_window3` | 0.7886 | 0.8171 | 0.8026 | 0.8719 | 0.9115 | 0.7856 | -0.1916 | 43.88 | `9ec29b3760b7` |
| E4a | `textsense_clean_v4` | 0.7417 | 0.7819 | 0.7613 | 0.8249 | 0.8921 | 0.7689 | -0.2086 | 160.47 | `41a7c41391f2` |
| E4b | `textsense_clean_v4` | 0.7849 | 0.8132 | 0.7988 | 0.8677 | 0.9098 | 0.7894 | -0.1714 | 182.12 | `3f436ab22eb9` |
| E5a | `textsense_clean_v4+negation_window3` | 0.7886 | 0.8171 | 0.8026 | 0.8719 | 0.9115 | 0.7856 | -0.1916 | 43.85 | `ea0030580091` |
| E5b | `textsense_clean_v4+negation_window3` | 0.6762 | 0.9034 | 0.7734 | 0.8719 | 0.8835 | 0.7861 | -0.4124 | 43.85 | `32fcfe17016c` |
| E6-50k | `textsense_clean_v4` | 0.7666 | 0.8312 | 0.7976 | 0.8710 | 0.9072 | 0.7604 | -0.2379 | 16.64 | `e101a1433244` |
| E6-120k | `textsense_clean_v4` | 0.7228 | 0.7881 | 0.7540 | 0.8241 | 0.8868 | 0.7846 | -0.2379 | 20.76 | `948af73ed6e7` |
| E6-400k | `textsense_clean_v4` | 0.6420 | 0.7294 | 0.6829 | 0.7403 | 0.8509 | 0.8068 | -0.2379 | 43.17 | `5614085b83a3` |

## 2. Chi tiết tối ưu E1b (`C`), E2w (`sample_weight`) và E5a (`class_weight`)

- **E1b (`C` tốt nhất):** `0.5`
- **E2w (`r` tốt nhất):** `0.15` (chọn nền `E2w` cho E3/E4)
- **Nền cho E5a/E5b:** `E3` (chọn `class_weight = None`)

## 3. Freeze Gate
- Toàn bộ artifact, `config.json`, mã nguồn và tập Train/Val đã được khóa SHA-256 trong `experiments/freeze_manifest.json`.
- Sẵn sàng chờ phê duyệt để mở `T1` và `T2` ở Bước 4B / Giai đoạn 5.
