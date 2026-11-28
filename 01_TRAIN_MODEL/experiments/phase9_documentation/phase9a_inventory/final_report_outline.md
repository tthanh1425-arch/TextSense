# ĐỀ CƯƠNG BÁO CÁO CUỐI & MA TRẬN HỒ SƠ 17 MỤC (GIAI ĐOẠN 9A)

## 1. Ma trận hồ sơ báo cáo cuối cùng (17 mục bắt buộc)

| STT | Hồ sơ cần có | Tệp hiện có | Trạng thái | Nguồn xác minh | Công việc còn thiếu |
|---:|---|---|---|---|---|
| 1 | Trang bìa và thông tin học phần | `04_BAO_CAO/Bao_cao_do_an_TextSense_V3_22.docx` (bản V3 cũ) | `MISSING` *(bản V4)* | Chưa có tệp báo cáo học thuật V4 | Tạo bìa & thông tin học phần trong báo cáo cuối V4 (9B) |
| 2 | Giới thiệu đề tài | `reports/bao_cao_khao_sat_v4.md` | `VERIFIED` | `bao_cao_khao_sat_v4.md`, `README.md` | Biên tập thành chương mở đầu học thuật |
| 3 | Phát biểu bài toán | `reports/bao_cao_khao_sat_v4.md`, `model_card.md` | `VERIFIED` | Nhị phân `0/1`, lớp ưu tiên `1`, miền chính trị | Tổng hợp vào báo cáo cuối |
| 4 | Mô tả dữ liệu | `reports/data_quality_report.md`, `manifest.json` | `VERIFIED` | Twitter `159.582`, Reddit `36.468`, S140 `520k` | Tổng hợp bảng thống kê vào báo cáo cuối |
| 5 | Tiền xử lý và gán nhãn | `reports/preprocessing_v4_report.md`, `baseline_v3/predict.py` | `VERIFIED` | Phân biệt `v3_context` (`E0`) và `v4` (`E1–E6`), nhãn proxy | Tổng hợp vào báo cáo cuối |
| 6 | Phương pháp nghiên cứu | `reports/phase4_experiment_design.md` | `VERIFIED` | TF-IDF, LinearSVC, Bootstrap 1000, Paired Bootstrap, McNemar+Holm | Tổng hợp vào báo cáo cuối |
| 7 | Thiết kế thực nghiệm | `reports/phase4_experiment_design.md`, `freeze_gate_audit_report.md` | `VERIFIED` | Ma trận `E0–E6`, Freeze Gate `PASS` | Tổng hợp vào báo cáo cuối |
| 8 | Kết quả thực nghiệm | `experiments/phase5_final_evaluation/final_evaluation_report.md` | `VERIFIED` | `t1_metrics_all_models.csv`, `t2_metrics_all_models.csv` | Tổng hợp bảng & phân tích vào báo cáo cuối |
| 9 | Phân tích kết quả | `final_evaluation_report.md`, `error_analysis_t1.csv`, `error_analysis_t2.csv` | `VERIFIED` | Domain shift S140, nguồn Twitter/Reddit, phân nhóm lỗi | Viết phân tích học thuật chi tiết (9B) |
| 10 | Lựa chọn mô hình | `experiments/phase7_model_finalization/model_selection_decision.md` | `VERIFIED` | Chọn `E0-Artifact` (`T1 F1=0.8826`) | Tổng hợp vào báo cáo cuối |
| 11 | Kiến trúc hệ thống | `system_architecture_inventory.md`, `api_inventory.md` | `VERIFIED` | Web → `serve_textsense.py` → `predict.py` / `database.py` | Vẽ sơ đồ kiến trúc vào báo cáo cuối |
| 12 | Triển khai ứng dụng | `deployment_config.md`, `03_GIAO_DIEN/HUONG_DAN_CAI_DAT.txt`, `README.md` | `NEEDS_REVISION` | `README.md` còn ghi `196.056` và `-0.2203` | Cập nhật `README.md` / tài liệu triển khai V4 (9B) |
| 13 | Kiểm thử hệ thống | `reports/final_system_test_report.md`, hồ sơ `8A–8D` | `VERIFIED` | `PASS WITH WARNINGS` (ghi rõ Chrome DOM `NOT EXECUTED`) | Tổng hợp vào báo cáo cuối |
| 14 | Đánh giá hạn chế | `model_card.md`, `defect_register_consolidated.md` | `VERIFIED` | Nhãn proxy, domain shift, `DEF-8B/8C/8D` | Tổng hợp trung thực vào báo cáo cuối |
| 15 | Kết luận và hướng phát triển | Chưa có bản V4 hoàn chỉnh | `MISSING` *(bản tổng hợp V4)* | Dựa trên Giai đoạn 5, 7, 8 | Viết chương kết luận & hướng phát triển (9B) |
| 16 | Tài liệu tham khảo | Chưa có danh mục chuẩn hóa V4 | `MISSING` | Scikit-learn, Sentiment140, Twitter/Reddit datasets | Lập danh mục tài liệu tham khảo (9B) |
| 17 | Phụ lục | `phase7_manifest.json`, `phase8d_manifest.json`, `error_analysis_*.csv` | `VERIFIED` | Manifest, SHA-256, bảng phụ lục | Đóng gói phụ lục (9B) |

## 2. Bảng đối chiếu tính nhất quán số liệu trọng tâm (Bước 7)

| Nội dung | Nguồn gốc có thẩm quyền | Giá trị xác minh | Giá trị ở tài liệu khác | Trạng thái |
|---|---|---|---|---|
| Dữ liệu Twitter (sạch) | `baseline_v3/binary_metrics.json` | `159.582` | `README.md` không tách; V4 đúng `159.582` | Nhất quán |
| Dữ liệu Reddit (sạch) | `baseline_v3/binary_metrics.json` | `36.468` | V4 đúng `36.468` | Nhất quán |
| Tổng chính trị sạch | `baseline_v3/binary_metrics.json` | `196.050` | **`README.md` ghi `196.056`** | **Lệch (`README.md` cũ)** |
| Số mẫu Train (Pol / S140) | `manifest.json` | `133.314` / `400.000` | Mọi báo cáo V4 khớp | Nhất quán |
| Số mẫu Validation (Pol / S140) | `manifest.json` | `23.526` / `60.000` | Mọi báo cáo V4 khớp | Nhất quán |
| Số mẫu T1 / T2 | `manifest.json` | `39.210` / `60.000` | Mọi báo cáo V4 khớp | Nhất quán |
| Mô hình chính thức | `phase7_manifest.json` | `E0-Artifact` (`474b0f5fdce1...`) | Khớp 100% | Nhất quán |
| Threshold | `binary_linear_svm.joblib` | `-0.19220128657328076` | **`README.md` ghi `-0.2203`**, `model_weights.json` ghi `-0.2203` | **Lệch (`README.md` & tĩnh cũ)** |
| T1 F1 / T2 F1 (`E0-Artifact`) | `t1_metrics_all_models.csv`, `t2_metrics_all_models.csv` | `0.8826` / `0.4497` | `api/model-info` & UI hiển thị `0.8756` (`E0-Train`) | **Lệch hiển thị (`DEF-8C-01`)** |
| Kết luận kiểm thử | `final_system_test_report.md` | `PASS WITH WARNINGS` | Khớp 8A–8D | Nhất quán |
