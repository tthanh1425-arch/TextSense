# TextSense — Hệ thống phân tích cảm xúc và nhận diện nội dung tiêu cực

## 1. Giới thiệu dự án
**TextSense** là hệ thống phân tích cảm xúc bình luận mạng xã hội (nguồn Twitter và Reddit) sử dụng mô hình học máy **TF-IDF + LinearSVC** để phân loại bình luận tiếng Anh thành 2 nhóm nhãn:
- **Nhãn 1 (`Có nội dung tiêu cực`)**: Bình luận có sắc thái tiêu cực, bức xúc, thất vọng, chỉ trích hoặc phản đối (ánh xạ từ nhãn gốc `-1`).
- **Nhãn 0 (`Không phát hiện nội dung tiêu cực`)**: Bao gồm cả bình luận tích cực (`+1`) và trung tính (`0`).

## 2. Chức năng chính (5 khu vực)
1. **01. Trang chủ**: Giới thiệu hệ thống, quy ước 2 nhãn phân loại và quy trình sử dụng 3 bước.
2. **02. Phân tích cảm xúc**:
   - Phân tích một bình luận (tối đa 2.000 ký tự), phân tích chi tiết từng câu/vế, báo cáo kết quả sai.
   - Tích hợp **Lịch sử phân tích** và **Quản lý báo cáo sai** truy xuất trực tiếp từ SQL Server.
3. **03. Phân tích hàng loạt**: Tải tệp CSV/XLSX (tối đa 100 MB / 300.000 dòng), chọn sheet & cột văn bản, xem trước, bước xác nhận trước khi chạy, tìm kiếm/lọc/sắp xếp kết quả từng dòng, báo sai từng dòng và xuất CSV/Excel.
4. **04. Thống kê và trực quan hóa**: Tổng quan dữ liệu, phân bố 2 nhãn (Donut & Bar), độ dài & trùng lặp, từ ngữ cần xem xét thêm, thống kê từ/cụm từ (Unigram & Bigram, phân biệt tần suất xuất hiện và số bình luận chứa từ, xem bình luận chứa từ), phân tích theo nguồn/thời gian và đối chiếu nhãn tham chiếu (nếu tệp có).
5. **05. Thông tin mô hình**: Tham số TF-IDF + LinearSVC, quy trình tiền xử lý, dữ liệu huấn luyện (196.056 mẫu), chỉ số thực nghiệm trên tập Test và các giới hạn trung thực.

## 3. Công nghệ sử dụng
- **Backend**: Python (`http.server`, `pandas`, `scikit-learn`, `joblib`, `openpyxl`, `pyodbc`)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Machine Learning**: `TfidfVectorizer(max_features=40000, ngram_range=(1, 2), min_df=2, sublinear_tf=True)` + `LinearSVC(C=1.0, threshold=-0.2203)`
- **Cơ sở dữ liệu**: Microsoft SQL Server (`TextSenseDB`)

## 4. Cấu trúc thư mục
- `01_TRAIN_MODEL/`: Notebook huấn luyện (`TextSense_Notebook_SQLServer_Hoan_Thien_v3.ipynb`), dữ liệu (`data/`) và mô hình/chỉ số (`outputs/`).
- `02_SQL_SERVER/`: Script khởi tạo & cập nhật lược đồ (`textsense.sql`) và `requirements.txt`.
- `03_GIAO_DIEN/`: Máy chủ web (`serve_textsense.py`), suy luận (`predict.py`), kết nối SQL Server (`database.py`) và giao diện (`web/`).
- `04_BAO_CAO/`: Tài liệu báo cáo và hình minh chứng.
- `tests/`: Bộ kiểm thử tự động (`test_web_sentiment.py`).

## 5. Yêu cầu môi trường
- Windows 10/11, Python 3.10+ (dự án dùng `.venv-1` với Python 3.14.8 và `scikit-learn==1.9.1`).
- Microsoft SQL Server + ODBC Driver 17/18 for SQL Server.

## 6. Cách cài đặt
```powershell
cd 'C:\Users\vothi\OneDrive\Desktop\TextSense'
.\.venv-1\Scripts\python.exe -m pip install -r .\03_GIAO_DIEN\requirements.txt
```

## 7. Cách cấu hình SQL Server
1. Mở **SQL Server Management Studio (SSMS)**.
2. Mở và chạy toàn bộ tệp `02_SQL_SERVER/textsense.sql` để tạo `TextSenseDB` và các bảng (`Tweets`, `TweetTokens`, `TrainingRuns`, `PredictionBatches`, `Predictions`, `UserFeedback`) cùng các cột mở rộng mới.

## 8. Cách cấu hình biến môi trường
Đặt chuỗi kết nối trong PowerShell trước khi chạy backend (không lưu thông tin nhạy cảm vào mã nguồn):
```powershell
$env:TEXTSENSE_SQLSERVER_CONNECTION_STRING = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=TextSenseDB;Trusted_Connection=yes;'
```

## 9. Cách khởi động backend & frontend
`serve_textsense.py` phục vụ cả API và giao diện web tĩnh tại `web/`:
```powershell
.\.venv-1\Scripts\python.exe .\03_GIAO_DIEN\serve_textsense.py
```
Mở trình duyệt tại: `http://127.0.0.1:8502`

## 10. Kiểm thử tự động
```powershell
.\.venv-1\Scripts\python.exe .\tests\test_web_sentiment.py
```

## 11. Những giới hạn hiện tại
- Mô hình chỉ hỗ trợ **tiếng Anh**; văn bản tiếng Việt có dấu sẽ bị từ chối để tránh dự đoán sai lệch.
- Nhãn `0` gộp chung bình luận tích cực và trung tính.
- Mô hình có thể phân loại nhầm với câu mỉa mai, châm biếm hoặc thiếu ngữ cảnh.
- Phản hồi của người dùng được lưu ở trạng thái `Chờ xem xét` và **không** tự động huấn luyện lại mô hình.
