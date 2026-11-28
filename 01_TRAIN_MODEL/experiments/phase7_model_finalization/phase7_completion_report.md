# BÁO CÁO HOÀN THÀNH GIAI ĐOẠN 7 – CHỐT MÔ HÌNH CHÍNH THỨC (`E0-Artifact`)

**Ngày hoàn thành:** 2026-11-27  
**Trạng thái nghiệm thu:** **`PASS`**

## 1. Tóm tắt công việc đã hoàn thành
- Đối chiếu đầy đủ `experiments/freeze_manifest.json`, `experiments/phase5_final_evaluation/{t1_metrics_all_models.csv, t2_metrics_all_models.csv, bootstrap_ci_t1.csv, mcnemar_t1.csv, final_evaluation_report.md, evaluation_manifest.json}` và `baseline_v3/binary_linear_svm.joblib`.
- Xác minh `baseline_v3/binary_linear_svm.joblib` và `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib` có cùng SHA-256 (`474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a`), tải thành công trên Python `3.14.8` / `scikit-learn 1.9.1`.
- Xác minh quy tắc phân loại thực tế trong `03_GIAO_DIEN/predict.py`: `decision_score > -0.19220128657328076` → `1` (Tiêu cực), `<= threshold` → `0` (Không tiêu cực).
- Hoàn thiện đủ 7 tài liệu hồ sơ trong `experiments/phase7_model_finalization/`.

## 2. Danh sách tiêu chí nghiệm thu
- [x] `E0-Artifact` được xác minh đúng SHA-256 (`474b0f5fdce1...`).
- [x] Kết quả `T1`/`T2` đối chiếu chính xác với CSV và báo cáo Giai đoạn 5 (`T1 Precision=0.8705`, `Recall=0.8951`, `F1=0.8826`, `PR-AUC=0.9380`, `Accuracy=0.9476`; `T2 F1=0.4497`).
- [x] Cấu hình mô hình được xác minh trực tiếp từ artifact (`LinearSVC(C=1.0)`, `TfidfVectorizer(40000, (1,2), float32)`).
- [x] Threshold (`-0.19220128657328076`) và chiều so sánh (`>`) được xác minh từ `predict.py`.
- [x] Label mapping (`0=Không tiêu cực`, `1=Tiêu cực`) không bị đảo.
- [x] Không huấn luyện lại, không sửa artifact đã khóa, không tối ưu lại trên `T1`/`T2`.
- [x] Hoàn thành đầy đủ 7 tệp hồ sơ Giai đoạn 7.
- [x] Ghi nhận đầy đủ các điểm cần kiểm thử ở Giai đoạn 8 trong `integration_checklist.md`.

## 3. Điểm dừng
Đã dừng hoàn toàn sau Giai đoạn 7 (không sửa `predict.py`, giao diện, SQL Server, không chạy kiểm thử tích hợp), chờ người phụ trách phê duyệt chuyển sang **Giai đoạn 8 – Kiểm thử toàn bộ hệ thống**.
