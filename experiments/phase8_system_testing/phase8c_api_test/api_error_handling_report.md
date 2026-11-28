# BÁO CÁO KIỂM THỬ XỬ LÝ LỖI, VALIDATION VÀ BẢO MẬT CƠ BẢN (GIAI ĐOẠN 8C)

**Tổng số ca kiểm thử lỗi & biên:** `25` ca (`API-B2` 10 ca, `API-B3` 8 ca, `API-D` 4 ca, `Error_Security` 3 ca) + `API-E-02` (empty XLSX).

## 1. Kết quả kiểm thử Validation & Ngoại lệ

| Nhóm | Ca đạt | Ghi nhận thực tế |
|---|---:|---|
| `API-B2` (đầu vào không hợp lệ `/api/analyze`) | `9/10` | Thiếu `input`, `null`, số, boolean, khoảng trắng, chỉ dấu câu → `422`; JSON sai cú pháp → `400`; `>2.000` ký tự → `413`; `Content-Type: text/plain` → `415`. Riêng `API-B2-06` (body rỗng `b""`) trả **`422`** (`"Dữ liệu trống"`) thay vì `400` (hành vi có chủ đích của `_read_bytes`). |
| `API-B3` (đầu vào biên `/api/analyze`) | `8/8` | `1` ký tự & `1.960` ký tự → `200`; `2.240` ký tự & `D-11` (`raw=2009, norm=3`) → `413`; tiếng Việt → `422`; HTML entity, nhiều dòng, NFKC+emoji → `200`. |
| `API-D` (`/api/feedback` với DB mock) | `4/4` | Hợp lệ → `200` (`feedback_saved=True`); thiếu nhãn → `422`; JSON lỗi → `400`; DB mock trả lỗi (`None`) → `503` (không lộ traceback). |
| `Error_Security` | `3/3` | Endpoint không tồn tại → `404`; `DELETE /api/analyze` → `501` (`Unsupported method`); JSON > 32KB → `413`. |
| `API-E-02` (`/api/export-xlsx` rỗng) | `1/1` | Body rỗng → `422`. |

## 2. Kiểm tra bảo mật cơ bản
- Không có endpoint nào trả về Python traceback, connection string, mật khẩu hay token.
- `safe_csv_bytes()` / `result_csv_to_xlsx()` bảo vệ công thức `=CMD()` khi xuất CSV/XLSX.
