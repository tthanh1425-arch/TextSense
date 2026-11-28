# KIỂM KÊ HTTP API VÀ DATABASE CALL GRAPH (GIAI ĐOẠN 8C)

**Nguồn kiểm kê:** [serve_textsense.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/03_GIAO_DIEN/serve_textsense.py), [predict.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/03_GIAO_DIEN/predict.py), [database.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/03_GIAO_DIEN/database.py), [app.js](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/03_GIAO_DIEN/web/app.js).  
**Server:** `ThreadingHTTPServer` trên `127.0.0.1:8502` (`TEXTSENSE_PORT`). Giới hạn: JSON `<= 32 KB`, CSV/XLSX `<= 100 MB` / `300.000` dòng, chuỗi đơn `<= 2.000` ký tự.

## 1. Bảng danh mục Endpoint thực tế

| Endpoint | HTTP Method | Có thực tế? | Request | Response | Truy cập DB? | Thao tác ghi? |
|---|---|---|---|---|---|---|
| `/api/health` | `GET` | Có (dòng 1332) | — | JSON (`status`, `model_present`, `sql_server`, `label_names`) | Có (`sql_server_status`) | Không |
| `/api/model-info` | `GET` | Có (dòng 1340) | — | JSON (metrics từ `binary_metrics.json`) | Không | Không |
| `/api/analyze` | `POST` | Có (dòng 1040) | `application/json` `{"input": str}` | JSON (`label`, `code`, `decision_score`, `sentence_analysis`, `history_saved`, `batch_id`) | Có | **Có** (`record_prediction_batch`) |
| `/api/batch` | `POST` | Có (dòng 1177) | `application/octet-stream` + `?column=&filename=` | `text/csv` + headers `X-Total-Rows`, `X-Negative-Rows`, `X-History-Saved`, `X-TextSense-Summary` | Có | **Có** (`record_prediction_batch`) |
| `/api/feedback` | `POST` | Có (dòng 1072) | `application/json` (`prediction`, `suggested_label`, ...) | JSON (`feedback_saved`, `feedback_id`, `review_status`) | Có | **Có** (`record_user_feedback`) |
| `/api/feedback` | `GET` | Có (dòng 1424) | Query params | JSON (`items`, `counts`) | Có (`list_user_feedback`) | Không |
| `/api/feedback/status` | `POST` | Có (dòng 1120) | `application/json` (`feedback_id`, `review_status`) | JSON | Có | **Có** (`update_feedback_status`) |
| `/api/export-xlsx` | `POST` | Có (dòng 1223) | `application/octet-stream` (CSV bytes) | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Không | Không |
| `/api/sentences` | `POST` | Có (dòng 1058) | `application/json` `{"input": str}` | JSON breakdown | Không | Không |
| `/api/columns` | `POST` | Có (dòng 1140) | `application/octet-stream` + `?filename=` | JSON (`columns`, `suggested_column`) | Không | Không |
| `/api/config`, `/api/stats`, `/api/history/*`, `/api/auth/*` | `GET`/`POST` | Có | Tùy endpoint | JSON | `/api/stats`, `/api/history/*`, `/api/auth/*` | `/api/auth/{register,login,google}` |

## 2. Database Call Graph (Bắt buộc cô lập trước khi chạy test)
- `POST /api/analyze` → `serve_textsense.record_prediction_batch()` → `database.record_prediction_batch()` → `INSERT dbo.PredictionBatches`, `dbo.Predictions`.
- `POST /api/batch` → `serve_textsense.record_prediction_batch()` → `database.record_prediction_batch()` → `INSERT dbo.PredictionBatches`, `dbo.Predictions`.
- `POST /api/feedback` → `serve_textsense.record_user_feedback()` → `database.record_user_feedback()` → `INSERT dbo.UserFeedback`.
- `GET /api/health` → `serve_textsense.sql_server_status()` → `database.sql_server_status()` → `SELECT OBJECT_ID(...)` (chỉ đọc).
