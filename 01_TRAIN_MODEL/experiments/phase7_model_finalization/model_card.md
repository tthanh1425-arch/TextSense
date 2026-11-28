# MODEL CARD – TEXTSENSE (`E0-Artifact`)

## 1. Model Overview
- **Tên mô hình:** TextSense Binary Negative Sentiment Classifier (`E0-Artifact`)
- **Phiên bản:** `baseline_v3` (chính thức chốt tại Giai đoạn 7 – V4)
- **Mục đích:** Phân loại nhị phân bình luận mạng xã hội tiếng Anh để phát hiện nội dung mang sắc thái tiêu cực trong thảo luận chính trị.
- **Bài toán:** Phân loại nhị phân (`0 = Không tiêu cực`, `1 = Tiêu cực`).
- **Đơn vị sử dụng:** Hệ thống TextSense (CLI `03_GIAO_DIEN/predict.py` và Web API `03_GIAO_DIEN/serve_textsense.py`).

## 2. Intended Use
- Phân loại bình luận tiếng Anh theo hai nhóm (`0`: Không tiêu cực, `1`: Tiêu cực).
- Hỗ trợ nhận diện và tổng hợp nội dung tiêu cực trong thảo luận chính trị phù hợp với miền huấn luyện (Twitter/Reddit).
- Hỗ trợ phân tích hàng loạt tệp CSV/XLSX có sự giám sát của người dùng.

## 3. Out-of-scope Use
- Không dùng làm công cụ xác định sự thật hoặc tính đúng/sai của phát ngôn.
- Không dùng làm công cụ kiểm duyệt tự động không có con người giám sát.
- Không suy luận ý định, quan điểm hoặc lập trường chính trị của người viết.
- Không dùng kết quả như một kết luận pháp lý hoặc đánh giá đạo đức.
- Không mặc định hoạt động tốt trên tiếng Việt hoặc các ngôn ngữ chưa được đánh giá (`predict.py` chặn văn bản có dấu tiếng Việt > 3% ký tự chữ cái).

## 4. Training Data
- **Nguồn dữ liệu:** `Twitter_Data.csv` (`159.582` dòng sạch) và `Reddit_Data.csv` (`36.468` dòng sạch).
- **Số lượng mẫu huấn luyện artifact:** `156.840` dòng (`Political Train 133.314 + Political Validation 23.526`, sau khi giữ riêng `T1 = 39.210` dòng Test).
- **Quy tắc ánh xạ nhãn:** Nhãn gốc `-1 → 1` (Tiêu cực), `0` và `1 → 0` (Không tiêu cực).
- **Phân bố lớp (toàn bộ 196.050 dòng sạch):** Lớp `0`: `152.904` (`77,99%`), Lớp `1`: `43.146` (`22,01%`). Trong `Train+Val` (`156.840`): Lớp `0`: `122.323`, Lớp `1`: `34.517`.
- **Giới hạn dữ liệu:** Nhãn nguồn là nhãn proxy tự động (lexicon-based), tập trung nhiều vào thảo luận chính trị Ấn Độ (`modi`, `india`, `bjp`, `congress`), có thể chứa nhiễu gán nhãn.

## 5. Model Architecture
- **Tiền xử lý:** `textsense_clean_v3_context` (NFKC, loại `RT @user:` & URL, mở rộng phủ định `don't`/`dont` → `do not`, `casefold`, bỏ dấu câu & `_`).
- **Vectorizer:** `TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_features=40000, sublinear_tf=True, dtype=np.float32)` — kích thước từ vựng thực tế: `40.000` đặc trưng.
- **Classifier:** `LinearSVC(C=1.0, class_weight=None, max_iter=3000, random_state=42, loss='squared_hinge', penalty='l2')`, `classes_ = [0, 1]`, `intercept_ = -1.1482702`.
- **Ngưỡng quyết định (`threshold`):** `-0.19220128657328076` (chọn theo F1 lớp `1` trên Validation ở baseline v3).

## 6. Evaluation (Giai đoạn 5 – Đánh giá độc lập)
- **T1 (`political_test_T1.csv`, `39.210` dòng, `0` dòng bị bỏ qua):**
  - Accuracy: `0.9476` | Macro F1: `0.9245` | Specificity: `0.9624`
  - Lớp `1` Precision: `0.8705` (95% CI `[0.8629, 0.8772]`)
  - Lớp `1` Recall: `0.8951` (95% CI `[0.8885, 0.9014]`)
  - Lớp `1` F1: `0.8826` (95% CI `[0.8774, 0.8878]`)
  - Lớp `1` PR-AUC: `0.9380` (95% CI `[0.9336, 0.9423]`)
  - Confusion Matrix: `TN=29.432`, `FP=1.149`, `FN=905`, `TP=7.724`
- **T2 (`s140_test_T2_60k.csv`, `60.000` dòng, `0` dòng bị bỏ qua):**
  - Accuracy: `0.6062` | Macro F1: `0.5715` | Specificity: `0.8905`
  - Lớp `1` Precision: `0.7461` (`[0.7382, 0.7532]`), Recall: `0.3218` (`[0.3165, 0.3273]`), F1: `0.4497` (`[0.4437, 0.4557]`), PR-AUC: `0.6858` (`[0.6793, 0.6915]`).
- **So sánh thống kê:** Đạt F1 và PR-AUC cao nhất trên `T1` trong toàn bộ 14 mô hình `E0–E6`, vượt có ý nghĩa thống kê ($p_{\text{Holm}} < 10^{-6}$) so với `E1b`, `E2w`, `E3`, `E4b`, `E5b`.

## 7. Limitations
- Nhãn huấn luyện và kiểm thử (`T1`, `T2`) đều là nhãn proxy tự động, có thể chứa nhiễu.
- Ngôn ngữ và chủ đề chính trị thay đổi theo thời gian (khái niệm drift).
- Mỉa mai, châm biếm, câu hỗn hợp tích cực–tiêu cực và phủ định phức tạp có thể gây phân loại nhầm.
- Từ ngữ tiêu cực xuất hiện trong ngữ cảnh trích dẫn hoặc phủ nhận tiêu cực vẫn có thể kích hoạt False Positive.
- Không đánh giá đồng đều trên mọi ngôn ngữ và miền dữ liệu; kết quả trên `T2` (`F1=0.4497`) thấp hơn đáng kể so với `T1` (`F1=0.8826`), cho thấy mô hình chuyên biệt miền chính trị và không tổng quát hóa tốt sang tweet đời thường.

## 8. Ethical Considerations
- Không coi kết quả mô hình là phán quyết cuối cùng.
- Cần con người xem xét trong mọi trường hợp nhạy cảm hoặc có tác động đến người dùng.
- Tránh sử dụng mô hình để quy kết, gán nhãn cá nhân hoặc nhóm người.
