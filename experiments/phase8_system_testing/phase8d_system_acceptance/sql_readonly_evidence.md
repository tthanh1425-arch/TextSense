# BẰNG CHỨNG KIỂM TRA SQL SERVER CHỈ ĐỌC (8D-1)

- **Script thực thi:** [run_8d1_sql_readonly.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/experiments/phase8_system_testing/phase8d_system_acceptance/run_8d1_sql_readonly.py)
- **Kết nối:** `pyodbc.connect(conn_str, timeout=4, readonly=True)`
- **Các truy vấn đã chạy (100% chỉ đọc `SELECT`):**
  1. `SELECT DB_NAME()` → `TextSenseDB`
  2. `SELECT CASE WHEN OBJECT_ID(?, N'U') IS NOT NULL THEN 1 ELSE 0 END`
  3. `SELECT COUNT(*) FROM dbo.[<Table>]`
  4. `SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS ...`
  5. `SELECT fk.name, OBJECT_NAME(fk.parent_object_id), OBJECT_NAME(fk.referenced_object_id) FROM sys.foreign_keys fk`
- **Kết quả chi tiết schema:** Lưu tại [sql_schema_compatibility.csv](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/experiments/phase8_system_testing/phase8d_system_acceptance/sql_schema_compatibility.csv).
