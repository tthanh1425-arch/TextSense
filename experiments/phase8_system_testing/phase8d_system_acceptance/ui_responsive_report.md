# BÁO CÁO KIỂM THỬ HIỂN THỊ & RESPONSIVE (GIAI ĐOẠN 8D-2)

- **Kiểm thử trình duyệt thực tế (`1366×768`, `1920×1080`, `390×844` & chụp ảnh `ui_screenshots/`):** **`NOT EXECUTED`** *(Chrome DevTools MCP không kết nối được tới Chrome do thiếu `DevToolsActivePort` — Chrome chưa bật remote debugging).*
- **Kiểm tra mã nguồn CSS (`03_GIAO_DIEN/web/style.css`):** Đã xác nhận có 3 breakpoint responsive tại dòng `1534` (`@media (max-width: 768px)`), dòng `2167` (`@media (max-width: 900px)`) và dòng `2208` (`@media (max-width: 640px)`). Cần chạy kiểm thử trực quan trên trình duyệt khi bật Chrome remote debugging để xác nhận không tràn ngang ở `390×844`.
