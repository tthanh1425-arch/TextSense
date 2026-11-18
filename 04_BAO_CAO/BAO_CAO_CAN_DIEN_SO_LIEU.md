# Báo cáo đồ án TextSense – khung điền kết quả thực tế

1. **Nguồn và dữ liệu:** Hai CSV Twitter và Reddit. Đọc `01_TRAIN_MODEL/outputs/binary_data_summary.csv` sau khi train.
2. **Thống kê:** biểu đồ nhãn gốc, nhãn nhị phân, nguồn dữ liệu, độ dài, 20 từ phổ biến.
3. **Tiền xử lý:** NFKC, URL, lowercase, dấu câu, trùng token, chia dữ liệu phân tầng.
4. **Mô hình:** TF-IDF + MultinomialNB đối chứng, TF-IDF + LinearSVC chính. Cùng split.
5. **Tối ưu và so sánh:** đọc `binary_cv_results.csv` và `binary_model_comparison.csv` (không tự điền kết quả).
6. **Đánh giá:** Accuracy, Precision, Recall, F1 lớp 1, Confusion Matrix, PR Curve.
7. **Ứng dụng:** chụp màn hình dự đoán đơn và CSV sau khi chạy thật.
8. **Giới hạn:** nhãn proxy cảm xúc, không xác minh phản cảm thật; tiếng Việt chưa kiểm chứng.
9. **Trình bày:** giải thích ý nghĩa F1 lớp 1, vì sao chọn LinearSVC, không oversampling, vì sao không dùng tập test để chọn ngưỡng.

Kết quả huấn luyện thực tế sẽ xuất tại `01_TRAIN_MODEL/outputs/BAO_CAO_THUC_NGHIEM.md`.
