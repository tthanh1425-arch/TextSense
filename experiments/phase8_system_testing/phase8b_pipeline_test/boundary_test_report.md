# BÁO CÁO KIỂM THỬ ĐẦU VÀO BIÊN (NHÓM D – GIAI ĐOẠN 8B)

**Tổng số trường hợp Nhóm D:** `26` (`D-01` đến `D-26`), chi tiết từng dòng lưu tại [pipeline_test_results.csv](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/experiments/phase8_system_testing/phase8b_pipeline_test/pipeline_test_results.csv).

## 1. Tổng hợp xử lý đầu vào biên của `predict()`

| Nhóm đầu vào biên | Mã test | Trạng thái thực tế (`status`) | `predicted_label` | Đánh giá |
|---|---|---|---|---|
| Chuỗi rỗng / chỉ khoảng trắng / chỉ dấu câu / chỉ emoji / ký tự đặc biệt | `D-01, D-02, D-03, D-12, D-16` | `'Văn bản rỗng'` | `None` (không nhầm với `0`) | **PASS** |
| URL đơn lẻ (`https://`, `www.`, `x.com/`) | `D-04, D-05, D-06` | `'Đây là đường dẫn, không phải nội dung bình luận'` | `None` | **PASS** |
| Văn bản kèm URL / tiền tố `RT @user:` | `D-07, D-08` | `'ok'` | `1` (`D-07`), `0` (`D-08`) | **PASS** |
| Độ dài gần 2.000 (`1.960` ký tự) vs vượt 2.000 (`2.240` ký tự) | `D-09, D-10` | `'ok'` (`D-09`), `'Vượt quá 2,000 ký tự'` (`D-10`) | `0` (`D-09`), `None` (`D-10`) | **PASS** |
| Raw `2.009` ký tự nhưng sau chuẩn hóa chỉ còn `3` ký tự (`"bad " + "!"*2005`) | `D-11` | `predict()`: `'ok'` (`1`); `infer_comment()`: `HTTP 413` | `1` vs `Rejected` | **WARNING** (khác cách đo độ dài raw vs normalized) |
| Chứa emoji kèm nội dung, NFKC fullwidth, nháy cong, nhiều dòng, lặp từ, chỉ số | `D-13, D-14, D-15, D-17, D-18, D-19` | `'ok'` | `1` hoặc `0` | **PASS** |
| Tiếng Việt có dấu (>3% chữ cái có dấu) | `D-20, D-21, D-22, D-23` | `'Văn bản có dấu tiếng Việt; ... không trả nhãn.'` | `None` | **PASS** *(Lưu ý `D-23`: 1 từ tiếng Việt `"nhưng"` trên câu ngắn đã vượt 3% nên bị chặn)* |
| 1 ký tự (`"a"`), 1 từ (`"no"`), HTML entities (`&amp;`, `&lt;`) | `D-24, D-25, D-26` | `'ok'` | `0`, `0`, `1` | **PASS** *(Lưu ý `D-26`: `v3` không giải mã HTML entity nên `&lt;fail&gt;` thành `lt fail gt`)* |

## 2. Kết luận Nhóm D
- Không có bất kỳ exception nào chưa được xử lý.
- Các đầu vào bị loại đều trả `predicted_label = None` (không nhầm với `0`) và không làm hỏng các dòng hợp lệ cùng batch.
