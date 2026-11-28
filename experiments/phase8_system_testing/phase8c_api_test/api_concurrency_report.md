# BÁO CÁO KIỂM THỬ ĐỒNG THỜI VÀ ỔN ĐỊNH (GIAI ĐOẠN 8C)

**Endpoint kiểm thử:** `POST /api/analyze` (qua `ThreadingHTTPServer` trên `127.0.0.1:64184`, DB đã được mock).

| Mức đồng thời | Thành công | Tổng request | Thời gian tối đa (`max_ms`) | Lỗi / Trộn kết quả | Trạng thái |
|---:|---:|---:|---:|---:|---|
| `5` luồng | `5` | `5` | `11.54 ms` | `0` | **PASS** |
| `10` luồng | `10` | `10` | `13.58 ms` | `0` | **PASS** |
| `20` luồng | `20` | `20` | `524.19 ms` | `0` | **PASS** |

- Không xảy ra timeout, exception hay trộn dữ liệu giữa các request đồng thời.
- Mô hình `E0-Artifact` (đã cache qua `lru_cache` trong `predict.py`) phục vụ an toàn dưới các luồng đọc đồng thời.
