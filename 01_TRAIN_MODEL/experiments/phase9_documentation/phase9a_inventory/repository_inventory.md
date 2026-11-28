# KIỂM KÊ CẤU TRÚC REPOSITORY – TEXTSENSE (GIAI ĐOẠN 9A)

**Ngày kiểm kê:** 2026-11-28  
**Tổng số tệp dự án đã quét:** `307` tệp *(không tính `.git/`, `.venv-1/`, `__pycache__/`, `03_GIAO_DIEN/font/`)*. Danh sách đầy đủ từng tệp (đường dẫn, đuôi tệp, kích thước, `mtime`) lưu tại `_repo_scan.json`.

## 1. Phân loại 9 nhóm tệp trong Repository

| Nhóm | Số lượng / Đường dẫn tiêu biểu | Vai trò & Trạng thái |
|---|---|---|
| **1. Tài liệu chính thức (V4)** | `reports/bao_cao_khao_sat_v4.md`, `reports/data_quality_report.md`, `reports/preprocessing_v4_report.md`, `reports/phase3_data_split_report.md`, `reports/phase3_integrity_verification.md`, `reports/phase4_experiment_design.md`, `reports/phase4_design_revision_report.md`, `reports/final_system_test_report.md` | Đã xác minh (`VERIFIED`) |
| **2. Mã nguồn** | `03_GIAO_DIEN/{serve_textsense.py, predict.py, database.py}`, `03_GIAO_DIEN/web/{index.html, app.js, style.css, csv_viewer.js}`, `02_SQL_SERVER/textsense.sql`, `preprocessing_v4.py`, `scripts/{phase1_data_prep.py, phase2_verify_v4.py, phase3_prepare_splits.py, negation_feature.py, phase4a_run.py, phase4a_resume.py, phase5_final_eval.py}`, `tests/{test_web_sentiment.py, test_negation_e3.py}` | Đã xác minh (`VERIFIED`) |
| **3. Notebook** | `01_TRAIN_MODEL/TextSense_Notebook_SQLServer_Hoan_Thien_v3.ipynb`, `baseline_v3/TextSense_Notebook_SQLServer_Hoan_Thien_v3.ipynb`, `01_TRAIN_MODEL/data/archive (3)/Exploring Data.ipynb` | Đã xác minh (`v3` notebook), `EXISTS_UNVERIFIED` (`Exploring Data.ipynb`) |
| **4. Dữ liệu** | `data/raw/{Twitter_Data.csv, Reddit_Data.csv, sentiment140_train.csv, sentiment140_test.csv}`, `data/sampled/`, `data/splits/` (8 tệp V4), `baseline_v3/splits/binary/{train,validation,test}.csv`, `manifest.json` | Đã xác minh (`VERIFIED`) |
| **5. Mô hình & Artifact** | `baseline_v3/binary_linear_svm.joblib`, `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib` (`E0-Artifact`, SHA-256 `474b0f5fdce1...`), cùng 13 `model.joblib` trong `experiments/E0-Train..E6-400k/` | Đã xác minh (`VERIFIED`) |
| **6. Kết quả thực nghiệm** | `experiments/freeze_manifest.json`, `experiments/freeze_gate_audit_report.md`, `experiments/phase4A_validation_summary.md`, `experiments/phase5_final_evaluation/` (15 tệp/thư mục), `experiments/phase7_model_finalization/` (7 tệp) | Đã xác minh (`VERIFIED`) |
| **7. Báo cáo kiểm thử** | `experiments/phase8_system_testing/phase8a_environment_audit/` (6 tệp), `phase8b_pipeline_test/` (8 tệp), `phase8c_api_test/` (11 tệp), `phase8d_system_acceptance/` (14 tệp), `reports/final_system_test_report.md` | Đã xác minh (`VERIFIED`) |
| **8. Tài liệu triển khai** | `03_GIAO_DIEN/HUONG_DAN_CAI_DAT.txt`, `03_GIAO_DIEN/requirements.txt`, `01_TRAIN_MODEL/requirements.txt`, `02_SQL_SERVER/requirements.txt`, `README.md`, `experiments/phase7_model_finalization/deployment_config.md` | `README.md` có số cũ (`196.056`, `-0.2203`) → `NEEDS_REVISION` |
| **9. Tạm / Không còn sử dụng** | `data/raw/real_world_eval_tweets.csv`, `01_TRAIN_MODEL/data/real_world_eval_tweets.csv` (bị loại khỏi pipeline, không đọc), `experiments/eval_e0.py`, `experiments/e0_baseline_results.json` (từ kế hoạch cũ), `03_GIAO_DIEN/web/model_weights.json` (tĩnh cũ), `04_BAO_CAO/{Bao_cao_do_an_TextSense_V3_22.docx, BAO_CAO_TONG_HOP.md, NGUON_DU_LIEU.md, KIEM_THU_END_TO_END_WINDOWS.md}` (hồ sơ V3 cũ) | Giữ nguyên, không xóa |
