"""TextSense persistence: ALL application history is stored in Microsoft SQL Server.

No local file-database fallback is used. If SQL Server is not configured/available, inference can
continue but history is not persisted; callers receive None and a RuntimeWarning.
"""
from __future__ import annotations

import hashlib
import json
import os
import warnings
from datetime import datetime, timezone
from typing import Any

SQL_CONNECTION_ENV = 'TEXTSENSE_SQLSERVER_CONNECTION_STRING'


def _now():
    return datetime.now(timezone.utc)


def sql_server_connection_string() -> str | None:
    value = os.environ.get(SQL_CONNECTION_ENV, '').strip()
    if value:
        return value
    try:
        pyodbc = _get_pyodbc()
        drivers = pyodbc.drivers()
        driver = None
        for candidate in ('ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server', 'SQL Server'):
            if candidate in drivers:
                driver = candidate
                break
        if not driver:
            return None
        return (
            f'DRIVER={{{driver}}};SERVER=localhost;DATABASE=TextSenseDB;'
            'Trusted_Connection=yes;TrustServerCertificate=yes;'
        )
    except Exception:
        return None


def _get_pyodbc():
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError(
            'Thiếu pyodbc. Cài bằng: python -m pip install -r ../02_SQL_SERVER/requirements.txt'
        ) from exc
    return pyodbc


def sql_server_status() -> dict[str, Any]:
    connection_string = sql_server_connection_string()
    if not connection_string:
        return {
            'configured': False,
            'available': False,
            'message': f'Chưa cấu hình biến môi trường {SQL_CONNECTION_ENV}.'
        }
    try:
        pyodbc = _get_pyodbc()
        with pyodbc.connect(connection_string, timeout=4) as conn:
            row = conn.cursor().execute("""
                SELECT
                    CASE WHEN OBJECT_ID(N'dbo.TrainingRuns', N'U') IS NOT NULL THEN 1 ELSE 0 END,
                    CASE WHEN OBJECT_ID(N'dbo.PredictionBatches', N'U') IS NOT NULL THEN 1 ELSE 0 END,
                    CASE WHEN OBJECT_ID(N'dbo.Predictions', N'U') IS NOT NULL THEN 1 ELSE 0 END
            """).fetchone()
        if not all(bool(value) for value in row):
            return {
                'configured': True, 'available': False,
                'message': 'Đã kết nối SQL Server nhưng thiếu bảng lịch sử. Hãy chạy lại 02_SQL_SERVER/textsense.sql trong SSMS.'
            }
        return {'configured': True, 'available': True, 'message': 'Đã kết nối SQL Server; toàn bộ lịch sử dùng SQL Server.'}
    except Exception as exc:
        return {'configured': True, 'available': False, 'message': f'Không kết nối được SQL Server: {exc}'}


def _warn_persistence(action: str, exc: Exception | str) -> None:
    warnings.warn(
        f'Không lưu được {action} vào SQL Server: {exc}. Kết quả phân tích vẫn được trả về nhưng lịch sử không được lưu.',
        RuntimeWarning,
        stacklevel=2,
    )


def _read_inserted_id(cursor) -> int:
    """Skip ODBC informational result sets before reading INSERT ... OUTPUT."""
    while cursor.description is None:
        if not cursor.nextset():
            raise RuntimeError('SQL Server không trả về ID của bản ghi mới.')
    row = cursor.fetchone()
    if not row:
        raise RuntimeError('Không nhận được ID sau khi lưu vào SQL Server.')
    return int(row[0])


def record_training_run(task: str, status: str, model_path: str | None = None,
                        metrics: dict | None = None, log_text: str = '',
                        manifest_sha256: str | None = None) -> int | None:
    """Write training history to SQL Server dbo.TrainingRuns only."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        _warn_persistence('lịch sử huấn luyện', f'chưa cấu hình {SQL_CONNECTION_ENV}')
        return None

    report = metrics or {}
    class_report = report.get('classification_report', {})
    positive = class_report.get('Tiêu cực', class_report.get('Phản cảm', {}))
    data_hash = report.get('data_hashes', {}).get('canonical_dataset_sha256')
    selected_c = report.get('tuning', {}).get('selected_C')
    threshold = report.get('decision', {}).get('validation_selected_threshold')
    metrics_json = json.dumps(report, ensure_ascii=False, default=str)
    try:
        pyodbc = _get_pyodbc()
        with pyodbc.connect(connection_string, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SET NOCOUNT ON;
                INSERT INTO dbo.TrainingRuns
                (StartedUtc, Task, Status, ModelPath, Accuracy, MacroF1, PrecisionPositive,
                 RecallPositive, F1Positive, TestRows, SelectedC, DecisionThreshold,
                 PythonVersion, SklearnVersion, DataSha256, ManifestSha256, MetricsJson, LogText)
                OUTPUT INSERTED.TrainingRunID
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.get('created_utc') or _now(), task, status, model_path,
                report.get('accuracy'), report.get('f1_macro'), positive.get('precision'),
                positive.get('recall'), positive.get('f1-score'), report.get('test_rows'),
                selected_c, threshold, report.get('python_version'), report.get('sklearn_version'),
                data_hash, manifest_sha256, metrics_json, str(log_text)[-50000:]
            ))
            training_id = _read_inserted_id(cursor)
            conn.commit()
            return training_id
    except Exception as exc:
        _warn_persistence('lịch sử huấn luyện', exc)
        return None


def list_training_runs(limit: int = 50) -> list[dict]:
    """Read training history from SQL Server only."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        return []
    pyodbc = _get_pyodbc()
    safe_limit = max(1, min(int(limit), 500))
    with pyodbc.connect(connection_string, timeout=5) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT TOP ({safe_limit}) TrainingRunID AS id, StartedUtc AS started_utc, Task AS task,
                   Status AS status, ModelPath AS model_path, Accuracy AS accuracy,
                   F1Positive AS f1_positive, TestRows AS test_rows, SelectedC AS selected_c,
                   DataSha256 AS data_sha256
            FROM dbo.TrainingRuns ORDER BY TrainingRunID DESC
        """)
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def record_user_feedback(source_name: str, model_prediction: str,
                         suggested_label: str, user_note: str = '',
                         input_text: str | None = None) -> int | None:
    """Store user correction/feedback in SQL Server dbo.UserFeedback."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        _warn_persistence('phản hồi người dùng', f'chưa cấu hình {SQL_CONNECTION_ENV}')
        return None
    try:
        pyodbc = _get_pyodbc()
        with pyodbc.connect(connection_string, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SET NOCOUNT ON;
                INSERT INTO dbo.UserFeedback
                    (SourceName, InputText, ModelPrediction, SuggestedLabel, UserNote)
                OUTPUT INSERTED.FeedbackID
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(source_name)[:40],
                None if input_text is None else str(input_text),
                str(model_prediction)[:100],
                str(suggested_label)[:100],
                str(user_note)[:4000],
            ))
            feedback_id = _read_inserted_id(cursor)
            conn.commit()
            return feedback_id
    except Exception as exc:
        _warn_persistence('phản hồi người dùng', exc)
        return None


def record_prediction_batch(task: str, source_name: str, results: list[dict],
                             upload_bytes: int = 0, raw_bytes: bytes | None = None) -> int | None:
    """Store a prediction batch and every row in SQL Server; never writes to a local file database."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        _warn_persistence('lịch sử dự đoán', f'chưa cấu hình {SQL_CONNECTION_ENV}')
        return None

    digest = hashlib.sha256(raw_bytes or b'').hexdigest()
    rows = []
    for index, result in enumerate(results, start=1):
        code = result.get('predicted_label')
        rows.append((
            index,
            None if result.get('text') is None else str(result.get('text')),
            int(code) if code in (0, 1) else None,
            None if result.get('label_name') is None else str(result.get('label_name'))[:40],
            str(result.get('status', 'unknown'))[:100],
        ))

    try:
        pyodbc = _get_pyodbc()
        with pyodbc.connect(connection_string, timeout=15) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SET NOCOUNT ON;
                INSERT INTO dbo.PredictionBatches
                    (Task, SourceName, [RowCount], UploadBytes, UploadSha256)
                OUTPUT INSERTED.BatchID
                VALUES (?, ?, ?, ?, ?)
            """, (task, str(source_name)[:260], len(rows), int(upload_bytes), digest))
            batch_id = _read_inserted_id(cursor)
            insert_sql = """
                INSERT INTO dbo.Predictions
                    (BatchID, RowNumber, InputText, PredictedLabel, LabelName, Status)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            values = [(batch_id, *row) for row in rows]
            # Insert in chunks to keep memory and ODBC parameter batches bounded.
            for start in range(0, len(values), 1000):
                cursor.executemany(insert_sql, values[start:start + 1000])
            conn.commit()
            return batch_id
    except Exception as exc:
        _warn_persistence('lịch sử dự đoán', exc)
        return None


def list_prediction_batches(limit: int = 50) -> list[dict]:
    """Read prediction batch history from SQL Server only."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        return []
    pyodbc = _get_pyodbc()
    safe_limit = max(1, min(int(limit), 500))
    with pyodbc.connect(connection_string, timeout=5) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT TOP ({safe_limit}) BatchID AS id, CreatedUtc AS created_utc, Task AS task,
                   SourceName AS source_name, RowCount AS row_count, UploadBytes AS upload_bytes,
                   UploadSha256 AS upload_sha256
            FROM dbo.PredictionBatches ORDER BY BatchID DESC
        """)
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_predictions(batch_id: int) -> list[dict]:
    """Read row-level prediction details from SQL Server only."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        return []
    pyodbc = _get_pyodbc()
    with pyodbc.connect(connection_string, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT RowNumber AS row_number, InputText AS input_text,
                   PredictedLabel AS predicted_label, LabelName AS label_name, Status AS status
            FROM dbo.Predictions WHERE BatchID = ? ORDER BY RowNumber
        """, (int(batch_id),))
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def record_user_feedback(source_name: str, model_prediction: str,
                         suggested_label: str, user_note: str = '',
                         input_text: str | None = None) -> int | None:
    """Store user correction/feedback in SQL Server dbo.UserFeedback."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        _warn_persistence('phản hồi người dùng', f'chưa cấu hình {SQL_CONNECTION_ENV}')
        return None
    try:
        pyodbc = _get_pyodbc()
        with pyodbc.connect(connection_string, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SET NOCOUNT ON;
                INSERT INTO dbo.UserFeedback
                    (SourceName, InputText, ModelPrediction, SuggestedLabel, UserNote)
                OUTPUT INSERTED.FeedbackID
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(source_name)[:40],
                None if input_text is None else str(input_text),
                str(model_prediction)[:100],
                str(suggested_label)[:100],
                str(user_note)[:4000],
            ))
            feedback_id = _read_inserted_id(cursor)
            conn.commit()
            return feedback_id
    except Exception as exc:
        _warn_persistence('phản hồi người dùng', exc)
        return None
