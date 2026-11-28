# BÁO CÁO KIỂM THỬ PIPELINE SUY LUẬN (GIAI ĐOẠN 8B)

**Ngày kiểm thử:** 2026-11-28  
**Artifact kiểm thử:** `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib` (SHA-256: `474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a`)  
**Tổng số ca kiểm thử:** `136` ca độc lập (không lấy từ `T1`/`T2`).

---

## 1. Tổng hợp kết quả Nhóm A–E

| Nhóm | Số ca | Trạng thái kỹ thuật | Phát hiện chính |
|---|---:|---|---|
| **A – Văn bản cơ bản** | `30` | **PASS** (`30/30` hợp lệ) | `10/10` câu không tiêu cực cho nhãn `0`; `7/10` câu tiêu cực cho nhãn `1` (`3` câu thiếu từ khóa mạnh nên điểm dưới ngưỡng) |
| **B – Tương phản & câu ghép** | `30` | **PASS WITH WARNINGS** | `27/30` đồng nhất; **`3/30`** (`B-01`, `B-03`, `B-20`) bị quy tắc **OR** trong `infer_comment()` đảo từ `0 → 1` |
| **C – Phủ định & ngữ cảnh** | `30` | **PASS** *(kỹ thuật)* / **WARNING** *(ngữ nghĩa)* | `15/30` khớp nhãn tham chiếu ngữ nghĩa, `15/30` lệch (ví dụ `not bad`, `not as bad as expected`, `not the worst law` bị dự đoán `1` do TF-IDF bag-of-words) |
| **D – Đầu vào biên** | `26` | **PASS WITH WARNINGS** | Từ chối đúng rỗng/URL/>2000/tiếng Việt, không crash; phát hiện `D-11` lệch kiểm tra độ dài raw (`infer_comment`) vs normalized (`predict`) |
| **E – Ổn định & nhất quán** | `20` (+600 batch) | **PASS** (`100%`) | `repeat_ok=True`, `single_vs_batch_ok=True`, `order_invariant_ok=True`, `batch_size_lt_eq_gt_512_ok=True` |

---

## 2. Kiểm tra chuyên sâu 8 tầng: `predict()` vs `infer_comment()`

Xác minh từ mã nguồn `03_GIAO_DIEN/serve_textsense.py` (dòng 830–843):
```python
result = predict(get_model_path(), [text])[0]
code = int(result['predicted_label'])
sentence_analysis = analyze_sentence_breakdown(text)
has_negative_part = bool(sentence_analysis.get('negative_parts', 0) > 0)
if code == 1 or has_negative_part:
    final_code = 1
```
- **`predict()`** chạy `Input → normalize_text(v3) → TfidfVectorizer → LinearSVC.decision_function → > -0.19220128657328076 → 1/0` trên **toàn bộ bình luận**.
- **`infer_comment()`** chạy thêm `split_comment_sentences()` / `analyze_sentence_breakdown()` và áp dụng **quy tắc OR** (`code == 1 or has_negative_part`).
- Tổng cộng **`6/136` ca** (`B-01`, `B-03`, `B-20`, `C-09`, `D-17`, `E-04`) có `predict() == 0` nhưng `infer_comment() == 1` vì một mệnh đề con bị dự đoán tiêu cực (chi tiết đầy đủ tại [predict_infer_parity.csv](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/experiments/phase8_system_testing/phase8b_pipeline_test/predict_infer_parity.csv)).
