# TextSense — đồ án phân tích cảm xúc bình luận mạng xã hội

TextSense sử dụng **TF-IDF + LinearSVC** để phân loại **toàn bộ bình luận tiếng Anh** thành **Tiêu cực (1)** hoặc **Không tiêu cực (0)**. Khi bình luận có nhiều câu/vế, ứng dụng có thể **chỉ ra phần nào được dự đoán tiêu cực**, kèm các phần còn lại để đối chiếu. Phân tích theo vế là chức năng hỗ trợ, **không thay thế nhãn của toàn bình luận**.

Dữ liệu gốc Twitter/Reddit có ba nhãn: `-1` (tiêu cực), `0` (trung tính), `1` (tích cực). Trong đồ án, `-1 -> 1`, còn `0` và `1 -> 0`. **Không phải** mô hình phát hiện phân biệt chủng tộc, giới tính hoặc mức độ xúc phạm. Model cũng chưa được đánh giá độc lập cho tiếng Việt hoặc phân loại các vế câu ngắn.

## Cấu trúc chính (giữ nguyên thư mục hiện có)

- `01_TRAIN_MODEL/TextSense_Notebook_SQLServer_Hoan_Thien_v2.ipynb`: notebook huấn luyện và kết quả thực nghiệm, dữ liệu trong `data/`, model trong `outputs/`.
- `02_SQL_SERVER/textsense.sql`: lược đồ `TextSenseDB` và các bảng Tweets, TweetTokens, TrainingRuns, PredictionBatches, Predictions.
- `03_GIAO_DIEN/serve_textsense.py`, `predict.py`, `database.py`: web API, suy luận bằng model đã lưu và SQL Server.
- `03_GIAO_DIEN/web/`: giao diện duy nhất được web server phục vụ (file `03_GIAO_DIEN/index.html` là bản sao được giữ lại để không mất file cũ).
- `03_GIAO_DIEN/app.py`: dashboard và quản lý lịch sử bằng Streamlit.
- `04_BAO_CAO/`: báo cáo và minh chứng; **không xóa hoặc sửa nội dung nghiên cứu cũ khi nâng cấp giao diện**.

**Giữ nguyên `.venv-1` và `.git` đang có trên máy.** Gói dự án phát hành không đóng gói lại hai thư mục này (môi trường Python được tạo theo đường dẫn máy Windows và lịch sử Git riêng của bạn). Khi **giải nén đè vào thư mục TextSense cũ**, chúng không bị xóa hay thay đổi. Dữ liệu, model, kết quả, báo cáo, SQLite lịch sử cũ và cache được giữ trong gói. Chương trình hiện tại không ghi lịch sử vào SQLite.

## Mở web UI trên Windows / PowerShell

Mở **PowerShell** tại thư mục TextSense, ví dụ:

```powershell
cd 'C:\Users\vothi\OneDrive\Desktop\TextSense'
$env:TEXTSENSE_SQLSERVER_CONNECTION_STRING = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=TextSenseDB;Trusted_Connection=yes;'
.\.venv-1\Scripts\python.exe .\03_GIAO_DIEN\serve_textsense.py
```

Mở **http://127.0.0.1:8502**. Nhấn `Ctrl+C` trong terminal để dừng. Biến kết nối SQL phải được đặt **trong cùng cửa sổ** chạy web (không tự chuyển sang terminal khác). Nếu SQL Server không kết nối, vẫn có kết quả dự đoán nhưng giao diện sẽ cảnh báo rằng **lịch sử chưa được lưu**.

**Lần đầu hoặc thiếu thư viện** (không xóa `.venv-1`):

```powershell
.\.venv-1\Scripts\python.exe -m pip install -r .\03_GIAO_DIEN\requirements.txt
```

Môi trường trong ZIP được tạo trên Windows bằng Python 3.14.8. Nếu giải nén sang máy khác, môi trường này có thể không còn hợp lệ; tạo mới môi trường chỉ khi thật sự cần. Model đã lưu dùng scikit-learn **1.9.1** (đã ghim trong `requirements.txt`), nên tránh tự đổi phiên bản thư viện.

## Dashboard Streamlit (PowerShell thứ hai)

```powershell
cd 'C:\Users\vothi\OneDrive\Desktop\TextSense'
$env:TEXTSENSE_SQLSERVER_CONNECTION_STRING = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=TextSenseDB;Trusted_Connection=yes;'
.\.venv-1\Scripts\python.exe -m streamlit run .\03_GIAO_DIEN\app.py
```

Mở **http://localhost:8501**. Tỷ lệ % của số **bình luận** Tiêu cực / Không tiêu cực trong một tệp CSV hoặc XLSX vẫn hiển thị trên dashboard vì có mẫu số và ý nghĩa thống kê. **Không** hiển thị % tiêu cực bên trong một bình luận riêng lẻ.

## Notebook / huấn luyện lại (chỉ khi cần)

Mở dự án bằng VS Code, sau đó mở:

`01_TRAIN_MODEL/TextSense_Notebook_SQLServer_Hoan_Thien_v2.ipynb`

Chọn kernel **`.venv-1 (Python 3.14.8)`**. Không cần huấn luyện lại để chạy web với model `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib` đã có.

**Cẩn trọng khi Run All:** cell **1.4** của notebook **xóa và nạp lại** dữ liệu ở `dbo.TweetTokens` và `dbo.Tweets` trong một transaction. Những bảng này hiện có thể đã chứa dữ liệu quan trọng. Chỉ chạy lại toàn bộ notebook khi đã sao lưu và có chủ đích tái nạp. Lịch sử trong `dbo.TrainingRuns`, `dbo.PredictionBatches`, `dbo.Predictions` không bị câu lệnh xóa dữ liệu huấn luyện này tác động.

Để tạo bảng SQL trên máy **chưa từng cài đặt**, mở `02_SQL_SERVER/textsense.sql` trong SSMS, chạy toàn bộ một lần. Không cần tạo lại database/bảng trên máy đã cài và nạp đủ dữ liệu.

### Lệnh kiểm tra lưu lịch sử trong SSMS

```sql
USE TextSenseDB;
SELECT TOP (10) * FROM dbo.PredictionBatches ORDER BY BatchID DESC;
SELECT TOP (20) * FROM dbo.Predictions ORDER BY PredictionID DESC;
SELECT TOP (10) * FROM dbo.TrainingRuns ORDER BY TrainingRunID DESC;
```

## Kết quả đánh giá và giới hạn

Model hiện có (file kết quả đi kèm): Test 39.212 mẫu; Accuracy khoảng **94,55%**, F1 lớp Tiêu cực khoảng **87,89%** trên tập Test của đồ án. Không lấy chỉ số này để khẳng định độ chính xác ở cấp độ **từng câu/vế**, vì không có tập kiểm thử riêng ở cấp độ đó. Với phủ định phức tạp như `wasn't bad`, mô hình có thể nhầm; không dùng từ khóa tự sửa nhãn để che lỗi.

Khi dùng ZIP cập nhật, **sao lưu thư mục TextSense đang sử dụng trước khi giải nén**. Không xóa dữ liệu SQL Server, `.venv-1`, `.git`, notebook, model hoặc bất kỳ file cá nhân nào. Các cập nhật chủ yếu nằm trong backend, UI và hướng dẫn.
