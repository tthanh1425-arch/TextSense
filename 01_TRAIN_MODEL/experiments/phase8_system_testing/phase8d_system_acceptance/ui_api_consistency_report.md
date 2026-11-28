# BÁO CÁO ĐỐI CHIẾU FRONTEND VÀ BACKEND (GIAI ĐOẠN 8D-2)

| Chức năng | Frontend request (`app.js`) | API response (`serve_textsense.py`) | Hiển thị / Kết quả thực tế | Nhất quán? |
|---|---|---|---|---|
| Thông tin mô hình | `GET /api/model-info` (dòng 194) | Đọc `binary_metrics.json` (`E0-Train`: `acc=0.9444`, `f1=0.8756`, `train_rows=133314`) | Hiển thị `94,44%` / `87,56%` / `133.314` trong khi artifact suy luận là `E0-Artifact` (`Train+Val`, `T1 F1=88,26%`) | **Lệch phiên bản (`DEF-8C-01`)** |
| Phân loại đơn | `POST /api/analyze` (dòng 449) | JSON (`code`, `label`, `confidence`, `decision_score`, `sentence_analysis`) | `app.js` dòng 345 hiển thị `'Điểm tin cậy: ' + (confidence*100).toFixed(1) + '%'` dù `confidence` là sigmoid heuristic chưa hiệu chỉnh | **Lưu ý (`DEF-8D-01`)** |
| Phân loại hàng loạt | `POST /api/batch` (dòng 988) | CSV + headers (`X-Negative-Rows`, `X-Invalid-Rows`) | Khớp `100%` với `predict()` | **Nhất quán** |
| Xuất Excel | `POST /api/export-xlsx` (dòng 1224) | XLSX (`4` sheets, `openpyxl` hợp lệ) | Giữ nguyên nhãn & ô trống (`None`, không chuyển thành `0`) | **Nhất quán** |
| Trạng thái hệ thống | `GET /api/health` (dòng 64) | JSON `status=ok`, `sql_server` | Phân biệt rõ server sống với trạng thái SQL Server | **Nhất quán** |
