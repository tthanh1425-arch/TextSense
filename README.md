# TextSense – cấu trúc gọn cho đồ án Khoa học dữ liệu

## Cấu trúc

- `01_TRAIN_MODEL/do_an_textsense_v3.ipynb`: **notebook duy nhất** để đọc cả hai CSV, làm sạch, thống kê, import SQL tùy chọn, huấn luyện/so sánh Naive Bayes và LinearSVC, xuất metrics/biểu đồ/model.
- `01_TRAIN_MODEL/data/`: `Twitter_Data.csv` và `Reddit_Data.csv` (đều bắt buộc).
- `01_TRAIN_MODEL/outputs/`: file được sinh khi chạy notebook; **không có model giả hay pretrained**.
- `02_SQL_SERVER/textsense.sql`: tạo TextSenseDB + Tweets/TweetTokens + truy vấn thống kê SQL Server. **SQL là tùy chọn khi train**.
- `03_GIAO_DIEN/`: giao diện HTML/API và dashboard Streamlit, SQLite chỉ dùng cho lịch sử giao diện.
- `04_BAO_CAO/`: tài liệu trình bày và nơi lưu hình minh chứng.

## Cách chạy huấn luyện (VS Code/Windows)

1. Mở thư mục `TextSense` bằng VS Code; mở notebook `01_TRAIN_MODEL/do_an_textsense_v3.ipynb`.
2. Trong Terminal:

```powershell
py -3 -m pip install -r 01_TRAIN_MODEL/requirements.txt
```

3. Chọn Python kernel, bấm **Run All**. Notebook mặc định `RUN_FULL_TRAIN=True` và dùng **đồng thời cả hai CSV**.
4. Sau khi hoàn tất, kiểm tra model `01_TRAIN_MODEL/outputs/binary_linear_svm.joblib`, bảng `binary_model_comparison.csv`, `binary_metrics.json`, `binary_cv_results.csv` cùng đồ thị và báo cáo.
5. Huấn luyện toàn bộ dữ liệu với 5-fold CV có thể tốn thời gian và bộ nhớ; không tắt giữa chừng.

## SQL Server (không bắt buộc)

1. Nếu giảng viên yêu cầu SQL Server, mở `02_SQL_SERVER/textsense.sql` trong SSMS và chạy phần tạo database/bảng.
2. Cài `pyodbc` và ODBC Driver 18 cho SQL Server ở máy Windows: `py -3 -m pip install pyodbc`.
3. Trong notebook đổi `IMPORT_SQL_SERVER=True`, cấu hình `SQL_CONNECTION_STRING` đúng máy chủ và chạy cell SQL.
4. Mở lại `textsense.sql`, chạy phần SELECT để thống kê và Top 30 từ.
5. Nếu không có SQL Server, **để False**. Huấn luyện không phụ thuộc kết nối SQL.

## Giao diện

```powershell
py -3 -m pip install -r 03_GIAO_DIEN/requirements.txt
cd 03_GIAO_DIEN
py -3 serve_textsense.py
```

Truy cập http://127.0.0.1:8502. Dashboard tùy chọn: `py -3 -m streamlit run app.py`.

Giao diện đọc **duy nhất** model `../01_TRAIN_MODEL/outputs/binary_linear_svm.joblib`, không copy model. Lịch sử giao diện lưu SQLite cục bộ, độc lập SQL Server (dùng để phân tích tập dữ liệu).

## Rubric & trung thực khoa học

- Câu 1: hai nguồn dữ liệu, thống kê mô tả và biểu đồ.
- Câu 2: làm sạch, TF-IDF, chia Train 68%/Validation 12%/Test 20% phân tầng; giữ phân bố lớp thật thay vì SMOTE.
- Câu 3: NB baseline vs LinearSVC trên cùng split; 5-fold CV chọn C; chọn ngưỡng bằng validation, test độc lập; chạy thử.
- Câu 4: giao diện web dự đoán văn bản, CSV, dashboard và minh chứng ảnh chụp thật.

Nhãn proxy: `-1 → 1 Phản cảm`; `0/1 → 0 Không phản cảm`. **Không được diễn giải đây là mô hình phát hiện phân biệt chủng tộc/giới tính hoặc xác minh phản cảm thực tế.** Tiếng Việt chưa được đánh giá độc lập.

**Lưu ý:** Bản ZIP không chứa model huấn luyện sẵn và chưa có kết quả full-training cho phiên bản cấu trúc mới. Không tự khẳng định F1 hoặc điểm số khi chưa chạy thật và bảo vệ.
