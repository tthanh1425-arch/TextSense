# Kiểm thử TextSense trên máy Windows trước khi nộp đồ án

Mở PowerShell tại thư mục gốc `TextSense` (đã sao lưu thư mục trước khi cập nhật).

## 1. Xác nhận môi trường, model và notebook

```powershell
cd 'C:\Users\vothi\OneDrive\Desktop\TextSense'
Test-Path .\.venv-1\Scripts\python.exe
Test-Path .\01_TRAIN_MODEL\outputs\binary_linear_svm.joblib
Test-Path .\01_TRAIN_MODEL\TextSense_Notebook_SQLServer_Hoan_Thien_v2.ipynb
.\.venv-1\Scripts\python.exe --version
```

Ba lệnh `Test-Path` phải trả `True`. Không cần đào tạo lại model chỉ để chạy giao diện.

## 2. Chạy giao diện và kiểm tra nhãn tổng thể / từng phần

```powershell
$env:TEXTSENSE_SQLSERVER_CONNECTION_STRING = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=TextSenseDB;Trusted_Connection=yes;'
.\.venv-1\Scripts\python.exe .\03_GIAO_DIEN\serve_textsense.py
```

Mở `http://127.0.0.1:8502`. Kiểm tra:

1. Bình luận một câu: hiển thị kết quả ("Có nội dung tiêu cực" / "Không phát hiện nội dung tiêu cực"), không có thanh % nội bộ.
2. Bình luận nhiều vế: thử `The design is beautiful, but the performance is disappointing.`. Quy tắc phân loại: nếu có ít nhất 1 vế tiêu cực (hoặc cả bình luận bị dự đoán tiêu cực) thì kết quả là "Có nội dung tiêu cực"; chỉ khi không có vế nào tiêu cực và cả bình luận cũng không thì kết quả là "Không phát hiện nội dung tiêu cực". Những vế mang sắc thái tiêu cực được đánh dấu rõ ràng.
3. Dấu phẩy liệt kê: `I bought a phone, a charger, and a case.` không bị chia thành nhiều vế chỉ vì dấu phẩy.
4. Có câu phủ định: `The food wasn't bad, but I wouldn't call it delicious either.` có thể phân loại sai; đây là giới hạn của model, KHÔNG ép dự đoán bằng từ khóa.
5. Không hiển thị `Tỷ lệ phần tiêu cực` hoặc % bên trong một bình luận.
6. CSV/XLSX: tự tìm cột `text`, dự đoán hàng loạt, xem từng dòng, xuất CSV và Excel. Dashboard tập dữ liệu **vẫn có phần trăm số bình luận** theo hai nhóm.
7. Kiểm tra `http://127.0.0.1:8502/api/health`: `model_present=true`, `sql_server.available=true` nếu SQL kết nối đúng.

## 3. Kiểm tra lịch sử SQL Server

Sau khi phân loại một bình luận, chạy trong SSMS:

```sql
USE TextSenseDB;
SELECT TOP (10) BatchID, SourceName, [RowCount], CreatedUtc
FROM dbo.PredictionBatches ORDER BY BatchID DESC;
SELECT TOP (10) PredictionID, BatchID, InputText, PredictedLabel, LabelName
FROM dbo.Predictions ORDER BY PredictionID DESC;
```

Nếu không thấy bản ghi mới, kiểm tra cảnh báo dưới kết quả và cấu hình biến môi trường **ngay trong PowerShell đã chạy web**. Ứng dụng không tự lưu lịch sử vào SQLite.

## 4. Streamlit dashboard (PowerShell thứ hai)

```powershell
cd 'C:\Users\vothi\OneDrive\Desktop\TextSense'
$env:TEXTSENSE_SQLSERVER_CONNECTION_STRING = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=TextSenseDB;Trusted_Connection=yes;'
.\.venv-1\Scripts\python.exe -m streamlit run .\03_GIAO_DIEN\app.py
```

Mở `http://localhost:8501`; kiểm tra Huấn luyện, Dự đoán, Kết quả, SQL/Lịch sử, Hướng dẫn.

## 5. Notebook và dữ liệu SQL

Notebook: `01_TRAIN_MODEL/TextSense_Notebook_SQLServer_Hoan_Thien_v2.ipynb`. **Không Run All nếu chưa muốn huấn luyện/import lại**. Cell 1.4 của notebook sẽ thay dữ liệu trong `dbo.Tweets` và `dbo.TweetTokens`. Hãy sao lưu dữ liệu trước khi chạy lại. Các bảng lịch sử SQL được giữ nguyên, nhưng việc thay dữ liệu huấn luyện không cần thiết chỉ để kiểm thử web.
