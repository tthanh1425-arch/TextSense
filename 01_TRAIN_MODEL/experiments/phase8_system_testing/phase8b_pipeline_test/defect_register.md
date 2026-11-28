# SỔ ĐĂNG KÝ LỖI & SAI KHÁC PHÁT HIỆN (GIAI ĐOẠN 8B)

*(Theo quy tắc Giai đoạn 8B, không tự ý sửa các vấn đề phát hiện được.)*

| ID | Mức độ | Thành phần | Bằng chứng & Tái hiện | Ảnh hưởng |
|---|---|---|---|---|
| **DEF-8B-01** | **Medium** *(Design behavior)* | `serve_textsense.py` (`infer_comment`, dòng 834–839) vs `predict.py` | Các câu ghép tương phản `B-01`, `B-03`, `B-20`, `C-09`, `D-17`, `E-04` có `predict()=0` nhưng `infer_comment()=1` do quy tắc OR (`code == 1 or has_negative_part`) | Kết quả phân loại đơn trên Web có thể khác kết quả chạy batch CSV hoặc notebook trên cùng câu ghép |
| **DEF-8B-02** | **Low** | `serve_textsense.py` (dòng 828) vs `predict.py` (dòng 118) | Ca `D-11` (`"bad " + "!"*2005`): `infer_comment()` kiểm tra `len(raw_stripped) > 2000` (trả HTTP 413), trong khi `predict()` kiểm tra `len(normalized) > 2000` (chấp nhận và dự đoán `1`) | Đầu vào có nhiều dấu câu vượt 2.000 ký tự bị từ chối ở API đơn nhưng vẫn qua ở batch |
| **DEF-8B-03** | **Low** *(Model limitation)* | `E0-Artifact` (`LinearSVC` + TF-IDF v3) | Nhóm C (`15/30` ca phủ định như `C-02` `"not bad"`, `C-06` `"not as bad as expected"`, `C-17` `"cannot say this is a bad decision"`) cho nhãn `1` dù ngữ nghĩa không tiêu cực | Hạn chế cố hữu của mô hình tuyến tính bag-of-words trên phủ định kép/phủ định từ tiêu cực |
| **DEF-8B-04** | **Low** | `03_GIAO_DIEN/predict.py` (`v3` `normalize_text`) | Ca `D-26` (`"News &amp; politics &lt;fail&gt;"`): `v3` không giải mã HTML entity nên `&lt;fail&gt;` bị tách thành `lt fail gt` | Tạo thêm token rác `lt`, `gt`, `amp` nếu văn bản web có HTML entity chưa giải mã |
