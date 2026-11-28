# BÁO CÁO HOÀN THÀNH GIAI ĐOẠN 9B – BIÊN SOẠN BÁO CÁO ĐỒ ÁN TEXTSENSE V4

**Ngày hoàn thành:** 2026-11-28  
**Kết luận nghiệm thu Giai đoạn 9B:** **`PASS WITH WARNINGS`** *(Báo cáo dự thảo V4 hoàn chỉnh, số liệu 100% có nguồn xác minh; đánh dấu `PASS WITH WARNINGS` do còn placeholder thông tin cá nhân/trường lớp, chưa chạy kiểm thử Chrome trực quan ở 8D-2 và `README.md` còn chờ phê duyệt cập nhật).*

---

## 1. Trả lời 10 câu hỏi nghiệm thu Giai đoạn 9B

1. **Đã đọc và xác minh những tài liệu nào?**
   `bao_cao_khao_sat_v4.md`, `data_quality_report.md`, `preprocessing_v4_report.md`, `phase3_integrity_verification.md`, `phase4_experiment_design.md`, `phase4A_validation_summary.md`, `freeze_gate_audit_report.md`, `final_evaluation_report.md`, `t1_metrics_all_models.csv`, `t2_metrics_all_models.csv`, `bootstrap_ci_t1.csv`, `paired_bootstrap_t1.csv`, `mcnemar_t1.csv`, `phase7_manifest.json`, `model_selection_decision.md`, `final_system_test_report.md`, `sql_readonly_report.md`, `defect_register_consolidated.md`, `phase9a_completion_report.md`, `data_manifest.json`, `manifest.json`, `README.md`.
2. **Những số liệu nào đã được xác nhận?**
   Toàn bộ quy mô dữ liệu chính trị (`196.050` sạch: `133.314 / 23.526 / 39.210`), Sentiment140 (`1.513.897` pool sạch → `520.000` mẫu: `400k / 60k / 60k`), kết quả `E0–E6` trên `T1`/`T2`, `E0-Artifact` (`T1 F1=0.8826`, `PR-AUC=0.9380`, `Acc=0.9476`), và toàn bộ số liệu kiểm thử 8A–8D.
3. **Mâu thuẫn Sentiment140 được giải quyết như thế nào?**
   Đối chiếu `data_manifest.json` và `manifest.json`: `1.515.430` / `400k` là số liệu sơ bộ trước lọc trùng `v4` và trước điều chỉnh quy mô; **`1.513.897`** (pool sạch) và **`520.000`** (`400k Train + 60k Val + 60k T2`) là số liệu thực tế đã được sử dụng trong Giai đoạn 3–5.
4. **Những nội dung nào chưa thể xác minh?**
   Kiểm thử giao diện trực quan trên trình duyệt Chrome (`1366×768`, `1920×1080`, `390×844`) vẫn là `NOT EXECUTED` (`DevToolsActivePort` ENOENT); thông tin cá nhân sinh viên/trường/GVHD chưa có trong repository.
5. **Báo cáo đã hoàn thành những chương nào?**
   Hoàn thành đầy đủ Phần đầu + **Chương 1 đến Chương 6** + **Tài liệu tham khảo (APA 7)** + **Phụ lục** trong `reports/bao_cao_do_an_TextSense_V4_draft.md`.
6. **Những nội dung nào còn placeholder?**
   Tên trường/khoa/bộ môn, họ tên & MSSV sinh viên, họ tên giảng viên hướng dẫn, lời cam đoan và lời cảm ơn.
7. **Có phát hiện sai lệch giữa báo cáo và hệ thống không?**
   Đã ghi nhận đầy đủ `README.md` cũ (`196.056` mẫu, `-0.2203`) và các lỗi `OPEN` (`DEF-8B-01..04`, `DEF-8C-01..02`, `DEF-8D-01`).
8. **Có thay đổi bất kỳ mã nguồn, dữ liệu, mô hình hoặc cơ sở dữ liệu nào không?**
   **Không.** Tuyệt đối chỉ đọc và tạo mới 5 tệp tài liệu Giai đoạn 9B.
9. **SHA-256 artifact chính thức trước và sau có còn khớp không?**
   **Có**, cả `baseline_v3/binary_linear_svm.joblib` và `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib` đều giữ nguyên `474b0f5fdce1f2e0ca6ddbda55d2efb9dc7fb70330aa4b68e72c4dbc2b2c6b8a`.
10. **Có đủ điều kiện chuyển sang Giai đoạn 9C hay chưa?**
    **Có**, đủ điều kiện trình người phụ trách xem xét bản dự thảo `bao_cao_do_an_TextSense_V4_draft.md` và phê duyệt chuyển sang Giai đoạn 9C (đóng gói cuối cùng / chỉnh sửa theo góp ý).

*(Đã dừng hoàn toàn sau Giai đoạn 9B, không sửa hệ thống, chờ phê duyệt của bạn.)*
