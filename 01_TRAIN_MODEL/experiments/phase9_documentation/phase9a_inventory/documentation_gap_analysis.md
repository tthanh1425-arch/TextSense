# PHÂN TÍCH KHOẢNG TRỐNG TÀI LIỆU (`documentation_gap_analysis.md`) – GIAI ĐOẠN 9A

| Hạng mục còn thiếu / cần cập nhật | Mức độ ưu tiên | Nguyên nhân | Hướng xử lý đề xuất ở Giai đoạn 9B |
|---|---|---|---|
| **1. Báo cáo học thuật tổng hợp V4** (gồm Trang bìa, Kết luận, Tài liệu tham khảo) | **High** | Các tệp trong `04_BAO_CAO/` thuộc phiên bản V3 cũ (`Bao_cao_do_an_TextSense_V3_22.docx`, `BAO_CAO_TONG_HOP.md`) | Soạn báo cáo học thuật hoàn chỉnh V4 từ các số liệu `VERIFIED` của Giai đoạn 1–8 |
| **2. Sai lệch số liệu trong `README.md`** (`196.056` mẫu, `threshold=-0.2203`) | **Medium** | `README.md` chưa cập nhật theo `baseline_v3` (`196.050` mẫu, `-0.192201...`) và quy trình V4 | Cập nhật `README.md` và tài liệu hướng dẫn sử dụng ở Giai đoạn 9B |
| **3. Tài liệu hóa các lỗi `OPEN` từ Giai đoạn 8** (`DEF-8B-01`, `DEF-8C-01`, `DEF-8D-01`) | **Medium** | Các lỗi giữ trạng thái `OPEN` theo quy định chưa sửa code | Ghi rõ trong mục Hạn chế & Hướng phát triển của báo cáo cuối; không tự sửa code nếu chưa có phase sửa lỗi riêng |
| **4. Kiểm thử Chrome trực quan (`NOT EXECUTED`)** | **Low–Medium** | Thiếu `DevToolsActivePort` ở máy kiểm thử | Ghi nhận trung thực là `NOT EXECUTED` trong báo cáo học thuật; đề xuất chạy bổ sung khi bật Chrome remote debugging |
