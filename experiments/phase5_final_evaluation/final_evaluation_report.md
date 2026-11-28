# BÁO CÁO ĐÁNH GIÁ CUỐI CÙNG GIAI ĐOẠN 5 – TEXTSENSE V4

**Thời điểm đánh giá:** 2026-11-27  
**Giao thức & Manifest:** [evaluation_protocol.json](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/experiments/phase5_final_evaluation/evaluation_protocol.json), [evaluation_manifest.json](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/experiments/phase5_final_evaluation/evaluation_manifest.json)  
**Xác minh trước khi mở Test:** Toàn bộ 14/14 artifact trong `experiments/freeze_manifest.json`, `political_test_T1.csv` (`39.210` dòng, SHA-256 `5654ab35f4ce...`) và `s140_test_T2_60k.csv` (`60.000` dòng, SHA-256 `dcd4c1e5920d...`) khớp SHA-256 100%. Số dòng bị bỏ qua (`n_skipped`) = **`0`** ở mọi mô hình.

---

## 1. Kết quả tổng hợp trên T1 (Chính trị, `39.210` dòng) và T2 (Sentiment140, `60.000` dòng)

| Mô hình | T1 P(1) | T1 R(1) | T1 F1(1) | T1 PR-AUC | T1 Acc | T2 P(1) | T2 R(1) | T2 F1(1) | T2 PR-AUC | T2 Acc | Threshold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`E0-Artifact`** *(Train+Val)* | `0.8705` | `0.8951` | **`0.8826`** | **`0.9380`** | **`0.9476`** | `0.7461` | `0.3218` | `0.4497` | `0.6858` | `0.6062` | `-0.1922` |
| `E0-Train` *(Train)* | `0.8628` | `0.8887` | `0.8756` | `0.9336` | `0.9444` | `0.7429` | `0.3216` | `0.4488` | `0.6856` | `0.6051` | `-0.1922` |
| `E1a` *(v4, C=1.0)* | `0.8628` | `0.8887` | `0.8756` | `0.9336` | `0.9444` | `0.7430` | `0.3228` | `0.4501` | `0.6880` | `0.6056` | `-0.1922` |
| `E1b` *(v4, C=0.5)* | `0.8581` | `0.8925` | `0.8750` | `0.9300` | `0.9439` | `0.7437` | `0.3245` | `0.4518` | `0.6880` | `0.6063` | `-0.2202` |
| `E2` *(+400k S140)* | `0.6371` | `0.7331` | `0.6818` | `0.7469` | `0.8494` | `0.7545` | `0.8713` | **`0.8087`** | **`0.8763`** | **`0.7939`** | `-0.2379` |
| `E2w` *(r=0.15)* | `0.7799` | `0.8171` | `0.7981` | `0.8691` | `0.9090` | `0.7575` | `0.8115` | `0.7836` | `0.8413` | `0.7759` | `-0.1879` |
| `E3` *(+not_ trên E2w)* | `0.7820` | `0.8196` | `0.8004` | `0.8726` | `0.9100` | `0.7596` | `0.8141` | `0.7859` | `0.8444` | `0.7783` | `-0.1916` |
| `E4a` *(char_wb 2-5)* | `0.7455` | `0.7818` | `0.7632` | `0.8338` | `0.8932` | `0.7328` | `0.8068` | `0.7681` | `0.8200` | `0.7564` | `-0.2086` |
| `E4b` *(Word+Char)* | `0.7833` | `0.8123` | `0.7975` | `0.8704` | `0.9092` | `0.7641` | `0.8153` | `0.7889` | `0.8485` | `0.7818` | `-0.1714` |
| `E5a` *(cw=None)* | `0.7820` | `0.8196` | `0.8004` | `0.8726` | `0.9100` | `0.7596` | `0.8141` | `0.7859` | `0.8444` | `0.7783` | `-0.1916` |
| `E5b` *(ngưỡng F2)* | `0.6718` | **`0.9051`** | `0.7712` | `0.8726` | `0.8818` | `0.7073` | **`0.8840`** | `0.7858` | `0.8444` | `0.7591` | `-0.4124` |
| `E6-50k` *(khóa E2)* | `0.7685` | `0.8391` | `0.8023` | `0.8725` | `0.9090` | `0.7247` | `0.8032` | `0.7619` | `0.8180` | `0.7490` | `-0.2379` |
| `E6-120k` *(khóa E2)* | `0.7177` | `0.8015` | `0.7573` | `0.8289` | `0.8869` | `0.7381` | `0.8390` | `0.7853` | `0.8481` | `0.7707` | `-0.2379` |
| `E6-400k` *(khóa E2)* | `0.6371` | `0.7331` | `0.6818` | `0.7469` | `0.8494` | `0.7545` | `0.8713` | **`0.8087`** | **`0.8763`** | **`0.7939`** | `-0.2379` |

*(Chi tiết đầy đủ Precision, Recall, F1, F2, Macro F1, PR-AUC, Specificity, TN/FP/FN/TP lưu tại `t1_metrics_all_models.csv`, `t2_metrics_all_models.csv`, và `t1_confusion_matrices/`, `t2_confusion_matrices/`.)*

---

## 2. Bootstrap 95% CI (1.000 lần, `seed=42`) & Kiểm định thống kê trên T1

### 2.1. Khoảng tin cậy 95% trên `T1` (các mô hình tiêu biểu)
- `E0-Artifact`: F1 = `0.8826` (`[0.8774, 0.8878]`), PR-AUC = `0.9380` (`[0.9336, 0.9423]`), P = `0.8705` (`[0.8629, 0.8772]`), R = `0.8951` (`[0.8885, 0.9014]`).
- `E0-Train` / `E1a`: F1 = `0.8756` (`[0.8699, 0.8808]`), PR-AUC = `0.9336` (`[0.9292, 0.9379]`).
- `E1b`: F1 = `0.8750` (`[0.8697, 0.8801]`), PR-AUC = `0.9300` (`[0.9253, 0.9345]`).
- `E2`: F1 = `0.6818` (`[0.6739, 0.6904]`), PR-AUC = `0.7469` (`[0.7373, 0.7554]`).
- `E2w`: F1 = `0.7981` (`[0.7914, 0.8042]`), PR-AUC = `0.8691` (`[0.8623, 0.8754]`).
- `E3`: F1 = `0.8004` (`[0.7941, 0.8070]`), PR-AUC = `0.8726` (`[0.8659, 0.8789]`).
- `E5b`: F1 = `0.7712` (`[0.7644, 0.7782]`), R = `0.9051` (`[0.8989, 0.9109]`), P = `0.6718` (`[0.6633, 0.6812]`).
- `E6-50k`: F1 = `0.8023` (`[0.7958, 0.8086]`), PR-AUC = `0.8725` (`[0.8663, 0.8786]`).

### 2.2. Paired Bootstrap & McNemar (Hiệu chỉnh Holm-Bonferroni, `m = 16` cặp trên `T1`)

| Cặp so sánh (`A vs B`) | $\Delta F1$ (95% CI) | $\Delta$ PR-AUC (95% CI) | $b$ / $c$ | $p_{\text{Holm}}$ | Kết luận thống kê |
|---|---|---|---:|---:|---|
| `E1a vs E0-Train` | `0.0000` (`[0.0000, 0.0000]`) | `0.0000` (`[0.0000, 0.0000]`) | `0 / 0` | `1.0000` | Không khác biệt (cùng đầu vào) |
| `E1b vs E0-Train` | `-0.0007` (`[-0.0030, +0.0015]`) | `-0.0036` (`[-0.0043, -0.0030]`) | `213 / 235` | `1.0000` | F1 không khác biệt có ý nghĩa |
| `E2 vs E1b` | `-0.1933` (`[-0.2011, -0.1862]`) | `-0.1833` (`[-0.1910, -0.1758]`) | `686 / 4391` | `< 1e-100` | Giảm mạnh do lệch miền S140 |
| `E2w vs E2` | `+0.1164` (`[+0.1105, +0.1223]`) | `+0.1223` (`[+0.1176, +0.1273]`) | `2749 / 411` | `< 1e-100` | Trọng số nguồn khôi phục mạnh |
| `E3 vs E2w` | `+0.0023` (`[-0.0007, +0.0052]`) | `+0.0035` (`[+0.0020, +0.0050]`) | `388 / 348` | `0.7528` | F1 chưa có ý nghĩa; PR-AUC tăng nhẹ |
| `E4a vs E2w` | `-0.0350` (`[-0.0417, -0.0288]`) | `-0.0353` (`[-0.0412, -0.0297]`) | `1477 / 2095` | `3.86e-24` | Char-only kém hơn rõ rệt |
| `E4b vs E2w` | `-0.0005` (`[-0.0047, +0.0036]`) | `+0.0013` (`[-0.0010, +0.0038]`) | `736 / 727` | `1.0000` | Không cải thiện có ý nghĩa |
| `E5b vs E5a` | `-0.0292` (`[-0.0340, -0.0244]`) | `0.0000` (`[0.0000, 0.0000]`) | `738 / 1844` | `< 1e-100` | Đổi Precision lấy Recall (+8.56%) |
| `E6-120k vs E6-50k` | `-0.0451` (`[-0.0495, -0.0409]`) | `-0.0436` (`[-0.0465, -0.0408]`) | `483 / 1347` | `1.33e-89` | Giảm đơn điệu khi tăng S140 |
| `E6-400k vs E6-120k` | `-0.0756` (`[-0.0813, -0.0702]`) | `-0.0821` (`[-0.0862, -0.0779]`) | `727 / 2200` | `< 1e-100` | Giảm đơn điệu khi tăng S140 |
| `E3 vs E0-Artifact` | `-0.0822` (`[-0.0883, -0.0766]`) | `-0.0655` (`[-0.0704, -0.0608]`) | `606 / 2080` | `< 1e-100` | Thấp hơn baseline trên T1 |

---

## 3. Phân tích theo nguồn (Twitter vs Reddit trên T1) và Phân tích lỗi

- **Theo nguồn trên `T1` (`Twitter`: `31.917`, `Reddit`: `7.293`):**
  - `E0-Artifact`: Twitter F1 = `0.8874`, Reddit F1 = `0.8633`.
  - `E2` (chưa trọng số): Reddit tụt mạnh xuống F1 = `0.6383` (Precision `0.5387`), Twitter F1 = `0.6938`.
  - `E3` (nền `E2w` + `not_`): Reddit F1 = `0.7693`, Twitter F1 = `0.8083`.
- **Phân tích lỗi (`error_analysis_t1.csv`, `error_analysis_t2.csv`, mỗi mô hình lấy tối đa 150 FP + 150 FN):**
  - Trên `T1`, nhóm lỗi lớn nhất là `domain_or_context_nuance` (`73–83` FN, `53–64` FP) và `negation_scope` (`44–52` FN, `34–47` FP), tiếp theo là `contrastive_clause` (`15–39`).
  - `E3` giảm được `negation_scope` FN (từ `52` ở `E0-Artifact` / `51` ở `E1b` xuống `44` trên mẫu `T1`, và từ `33` xuống `17` trên mẫu `T2`), nhưng không bù đắp được khoảng cách lệch miền khi gộp Sentiment140.

---

## 4. Kết luận theo quy tắc đánh giá

1. **Mô hình có F1 cao nhất trên `T1`:** **`E0-Artifact`** (`0.8826`, fit trên `Train+Val`), và trong nhóm chỉ fit trên `Train` là **`E0-Train` / `E1a`** (`0.8756`).
2. **Mô hình có PR-AUC cao nhất trên `T1`:** **`E0-Artifact`** (`0.9380`), kế tiếp là `E0-Train` / `E1a` (`0.9336`).
3. **Mô hình có Recall cao nhất trên `T1`:** **`E5b`** (`0.9051`), nhưng Precision giảm mạnh còn `0.6718` (`F1 = 0.7712`).
4. **Mô hình tổng quát hóa tốt nhất trên `T2`:** **`E2` / `E6-400k`** (`F1 = 0.8087`, `PR-AUC = 0.8763`), vượt xa `E0-Artifact` trên `T2` (`F1 = 0.4497`).
5. **Ý nghĩa nghiên cứu:** Việc bổ sung `400.000` mẫu Sentiment140 giúp mô hình phân loại tweet đời thường (`T2`) tốt hơn rõ rệt, **nhưng không giúp mô hình nhận diện bình luận tiêu cực tốt hơn trong miền chính trị (`T1`)** — trái lại gây suy giảm có ý nghĩa thống kê (`p_holm < 1e-100`) do lệch miền (tweet đời thường vs thảo luận chính trị Ấn Độ) và khác biệt nhãn proxy (`emoticon` 2 cực vs `lexicon` 3 cực gộp 2 cực).
6. **Hạn chế:** Nhãn của cả `T1` (proxy lexicon) và `T2` (proxy emoticon) đều là nhãn proxy tự động, không phải nhãn gán tay bởi con người.

*(Đã dừng hoàn toàn sau khi xuất báo cáo Giai đoạn 5; không huấn luyện lại, không thay đổi mô hình hay threshold, chờ người phụ trách quyết định bước tiếp theo ở Giai đoạn 6/7.)*
