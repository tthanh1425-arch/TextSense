"""TextSense persistence: ALL application history is stored in Microsoft SQL Server.

No local file-database fallback is used. If SQL Server is not configured/available, inference can
continue but history is not persisted; callers receive None and a RuntimeWarning.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import warnings
from datetime import datetime, timezone
from typing import Any

SQL_CONNECTION_ENV = 'TEXTSENSE_SQLSERVER_CONNECTION_STRING'
FEEDBACK_STATUSES = ('Chờ xem xét', 'Đã xác minh', 'Không chấp nhận')
_CACHED_AUTO_CONN_STR: str | None = None


def _now():
    return datetime.now(timezone.utc)


def _iso(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def sql_server_connection_string() -> str | None:
    global _CACHED_AUTO_CONN_STR
    value = os.environ.get(SQL_CONNECTION_ENV, '').strip()
    if value:
        return value
    if _CACHED_AUTO_CONN_STR:
        return _CACHED_AUTO_CONN_STR
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
        for server in ('localhost', '.\\SQLEXPRESS', '(localdb)\\MSSQLLocalDB'):
            candidate_str = (
                f'DRIVER={{{driver}}};SERVER={server};DATABASE=TextSenseDB;'
                'Trusted_Connection=yes;TrustServerCertificate=yes;'
            )
            try:
                with pyodbc.connect(candidate_str, timeout=2):
                    _CACHED_AUTO_CONN_STR = candidate_str
                    return candidate_str
            except Exception:
                continue
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
                    CASE WHEN OBJECT_ID(N'dbo.Predictions', N'U') IS NOT NULL THEN 1 ELSE 0 END,
                    CASE WHEN OBJECT_ID(N'dbo.UserFeedback', N'U') IS NOT NULL THEN 1 ELSE 0 END
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


def _feedback_has_extended_columns(cursor) -> bool:
    row = cursor.execute("""
        SELECT
            CASE WHEN COL_LENGTH(N'dbo.UserFeedback', N'BatchID') IS NOT NULL THEN 1 ELSE 0 END,
            CASE WHEN COL_LENGTH(N'dbo.UserFeedback', N'ReasonCategory') IS NOT NULL THEN 1 ELSE 0 END,
            CASE WHEN COL_LENGTH(N'dbo.UserFeedback', N'ReviewStatus') IS NOT NULL THEN 1 ELSE 0 END
    """).fetchone()
    return bool(row and len(row) == 3 and all(bool(v) for v in row))


def _table_has_user_id(cursor, table_name: str) -> bool:
    row = cursor.execute(
        "SELECT CASE WHEN COL_LENGTH(?, N'UserID') IS NOT NULL THEN 1 ELSE 0 END",
        (table_name,),
    ).fetchone()
    return bool(row and len(row) == 1 and row[0] == 1)


def _hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 120_000)
    return dk.hex(), salt.hex()


def _is_valid_email(value: str) -> bool:
    import re
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', value))


def _ensure_auth_schema(conn) -> None:
    """Safely create dbo.Users and UserID columns if missing, without altering existing data."""
    cursor = conn.cursor()
    cursor.execute("""
        IF OBJECT_ID(N'dbo.Users', N'U') IS NULL
        BEGIN
            CREATE TABLE dbo.Users (
                UserID BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                Username NVARCHAR(120) NOT NULL UNIQUE,
                Email NVARCHAR(254) NULL,
                DisplayName NVARCHAR(120) NOT NULL,
                PasswordHash VARCHAR(128) NOT NULL,
                PasswordSalt VARCHAR(64) NOT NULL,
                AuthProvider NVARCHAR(32) NOT NULL CONSTRAINT DF_Users_AuthProvider DEFAULT N'local',
                CreatedUtc DATETIMEOFFSET NOT NULL CONSTRAINT DF_Users_CreatedUtc DEFAULT SYSDATETIMEOFFSET()
            );
        END;
    """)
    cursor.execute("""
        IF COL_LENGTH(N'dbo.Users', N'Email') IS NULL
            ALTER TABLE dbo.Users ADD Email NVARCHAR(254) NULL;
        IF COL_LENGTH(N'dbo.Users', N'AuthProvider') IS NULL
            ALTER TABLE dbo.Users ADD AuthProvider NVARCHAR(32) NOT NULL CONSTRAINT DF_Users_AuthProvider DEFAULT N'local';
        IF COL_LENGTH(N'dbo.PredictionBatches', N'UserID') IS NULL
            ALTER TABLE dbo.PredictionBatches ADD UserID BIGINT NULL;
        IF COL_LENGTH(N'dbo.UserFeedback', N'UserID') IS NULL
            ALTER TABLE dbo.UserFeedback ADD UserID BIGINT NULL;
    """)
    conn.commit()


def create_user(username: str, display_name: str, password: str) -> dict[str, Any]:
    """Create a new user in dbo.Users using email or username. Raises ValueError on duplicate or invalid input."""
    ident = username.strip().lower()
    is_email = _is_valid_email(ident)
    dname = display_name.strip() or (ident.split('@')[0] if is_email else ident)
    if not is_email and (len(ident) < 3 or len(ident) > 50 or not ident.replace('_', '').replace('.', '').isalnum()):
        raise ValueError('Hãy nhập Email hợp lệ (ví dụ: ten@gmail.com) hoặc tên đăng nhập 3–50 ký tự.')
    if len(ident) > 120:
        raise ValueError('Email hoặc tên đăng nhập quá dài.')
    if len(password) < 6:
        raise ValueError('Mật khẩu cần ít nhất 6 ký tự.')
    connection_string = sql_server_connection_string()
    if not connection_string:
        raise RuntimeError('Chưa kết nối được SQL Server để đăng ký tài khoản.')
    pyodbc = _get_pyodbc()
    pw_hash, pw_salt = _hash_password(password)
    with pyodbc.connect(connection_string, timeout=8) as conn:
        _ensure_auth_schema(conn)
        cursor = conn.cursor()
        has_email_col = cursor.execute("SELECT CASE WHEN COL_LENGTH(N'dbo.Users', N'Email') IS NOT NULL THEN 1 ELSE 0 END").fetchone()[0] == 1
        if has_email_col:
            existing = cursor.execute(
                "SELECT TOP (1) UserID FROM dbo.Users WHERE Username = ? OR (Email IS NOT NULL AND Email = ?)",
                (ident, ident),
            ).fetchone()
        else:
            existing = cursor.execute("SELECT TOP (1) UserID FROM dbo.Users WHERE Username = ?", (ident,)).fetchone()
        if existing:
            raise ValueError('Email hoặc tên đăng nhập đã tồn tại.')
        if has_email_col:
            cursor.execute("""
                SET NOCOUNT ON;
                INSERT INTO dbo.Users (Username, Email, DisplayName, PasswordHash, PasswordSalt, AuthProvider)
                OUTPUT INSERTED.UserID
                VALUES (?, ?, ?, ?, ?, N'local')
            """, (ident, ident if is_email else None, dname[:120], pw_hash, pw_salt))
        else:
            cursor.execute("""
                SET NOCOUNT ON;
                INSERT INTO dbo.Users (Username, DisplayName, PasswordHash, PasswordSalt)
                OUTPUT INSERTED.UserID
                VALUES (?, ?, ?, ?)
            """, (ident, dname[:120], pw_hash, pw_salt))
        uid = _read_inserted_id(cursor)
        conn.commit()
        return {'user_id': uid, 'username': ident, 'email': ident if is_email else None, 'display_name': dname[:120]}


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """Verify email/username and password against dbo.Users."""
    ident = username.strip().lower()
    if not ident or not password:
        return None
    connection_string = sql_server_connection_string()
    if not connection_string:
        raise RuntimeError('Chưa kết nối được SQL Server để đăng nhập.')
    pyodbc = _get_pyodbc()
    with pyodbc.connect(connection_string, timeout=8) as conn:
        _ensure_auth_schema(conn)
        cursor = conn.cursor()
        has_email_col = cursor.execute("SELECT CASE WHEN COL_LENGTH(N'dbo.Users', N'Email') IS NOT NULL THEN 1 ELSE 0 END").fetchone()[0] == 1
        if has_email_col:
            row = cursor.execute("""
                SELECT TOP (1) UserID, Username, DisplayName, PasswordHash, PasswordSalt, Email
                FROM dbo.Users WHERE Username = ? OR Email = ?
            """, (ident, ident)).fetchone()
        else:
            row = cursor.execute("""
                SELECT TOP (1) UserID, Username, DisplayName, PasswordHash, PasswordSalt, NULL AS Email
                FROM dbo.Users WHERE Username = ?
            """, (ident,)).fetchone()
        if not row or not row[4]:
            return None
        expected_hash, _ = _hash_password(password, row[4])
        if not hmac.compare_digest(expected_hash, row[3]):
            return None
        return {'user_id': int(row[0]), 'username': row[1], 'display_name': row[2], 'email': row[5]}


def upsert_oauth_user(email: str, display_name: str, provider: str = 'google') -> dict[str, Any]:
    """Find or create a user in dbo.Users via verified OAuth email."""
    clean_email = email.strip().lower()
    if not _is_valid_email(clean_email):
        raise ValueError('Email OAuth không hợp lệ.')
    dname = display_name.strip() or clean_email.split('@')[0]
    connection_string = sql_server_connection_string()
    if not connection_string:
        raise RuntimeError('Chưa kết nối được SQL Server.')
    pyodbc = _get_pyodbc()
    with pyodbc.connect(connection_string, timeout=8) as conn:
        _ensure_auth_schema(conn)
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT TOP (1) UserID, Username, DisplayName, Email FROM dbo.Users WHERE Email = ? OR Username = ?",
            (clean_email, clean_email),
        ).fetchone()
        if row:
            return {'user_id': int(row[0]), 'username': row[1], 'display_name': row[2], 'email': row[3] or clean_email}
        cursor.execute("""
            SET NOCOUNT ON;
            INSERT INTO dbo.Users (Username, Email, DisplayName, PasswordHash, PasswordSalt, AuthProvider)
            OUTPUT INSERTED.UserID
            VALUES (?, ?, ?, '', '', ?)
        """, (clean_email[:120], clean_email, dname[:120], provider[:32]))
        uid = _read_inserted_id(cursor)
        conn.commit()
        return {'user_id': uid, 'username': clean_email[:120], 'display_name': dname[:120], 'email': clean_email}


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    connection_string = sql_server_connection_string()
    if not connection_string:
        return None
    try:
        pyodbc = _get_pyodbc()
        with pyodbc.connect(connection_string, timeout=5) as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT TOP (1) UserID, Username, DisplayName FROM dbo.Users WHERE UserID = ?",
                (int(user_id),),
            ).fetchone()
            if not row:
                return None
            return {'user_id': int(row[0]), 'username': row[1], 'display_name': row[2]}
    except Exception:
        return None


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
            SELECT TOP ({safe_limit}) TrainingRunID AS id,
                   CONVERT(VARCHAR(33), StartedUtc, 127) AS started_utc,
                   Task AS task,
                   Status AS status, ModelPath AS model_path, Accuracy AS accuracy,
                   F1Positive AS f1_positive, TestRows AS test_rows, SelectedC AS selected_c,
                   DataSha256 AS data_sha256
            FROM dbo.TrainingRuns ORDER BY TrainingRunID DESC
        """)
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def record_user_feedback(source_name: str, model_prediction: str,
                         suggested_label: str, user_note: str = '',
                         input_text: str | None = None,
                         batch_id: int | None = None,
                         row_number: int | None = None,
                         prediction_id: int | None = None,
                         reason_category: str = 'Lý do khác',
                         user_id: int | None = None) -> int | None:
    """Store user correction/feedback in SQL Server dbo.UserFeedback with duplicate guard."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        _warn_persistence('phản hồi người dùng', f'chưa cấu hình {SQL_CONNECTION_ENV}')
        return None
    text_str = '' if input_text is None else str(input_text)
    input_hash = hashlib.sha256(text_str.encode('utf-8')).hexdigest() if input_text is not None else None
    try:
        pyodbc = _get_pyodbc()
        with pyodbc.connect(connection_string, timeout=10) as conn:
            cursor = conn.cursor()
            extended = _feedback_has_extended_columns(cursor)
            has_uid = extended and _table_has_user_id(cursor, 'dbo.UserFeedback')
            if extended:
                resolved_prediction_id = None if prediction_id is None else int(prediction_id)
                if resolved_prediction_id is None and batch_id is not None and row_number is not None:
                    pred_row = cursor.execute(
                        'SELECT TOP (1) PredictionID FROM dbo.Predictions WHERE BatchID = ? AND RowNumber = ?',
                        (int(batch_id), int(row_number))
                    ).fetchone()
                    if pred_row:
                        resolved_prediction_id = int(pred_row[0])
                # Prevent accidental duplicate feedback for the same batch row or identical recent submission.
                if batch_id is not None and row_number is not None:
                    existing = cursor.execute("""
                        SELECT TOP (1) FeedbackID FROM dbo.UserFeedback
                        WHERE BatchID = ? AND RowNumber = ? AND SuggestedLabel = ?
                        ORDER BY FeedbackID DESC
                    """, (int(batch_id), int(row_number), str(suggested_label)[:100])).fetchone()
                    if existing:
                        return int(existing[0])
                elif input_hash is not None:
                    existing = cursor.execute("""
                        SELECT TOP (1) FeedbackID FROM dbo.UserFeedback
                        WHERE InputSha256 = ? AND ModelPrediction = ? AND SuggestedLabel = ?
                          AND DATEDIFF(MINUTE, CreatedUtc, SYSDATETIMEOFFSET()) <= 10
                        ORDER BY FeedbackID DESC
                    """, (input_hash, str(model_prediction)[:100], str(suggested_label)[:100])).fetchone()
                    if existing:
                        return int(existing[0])
                if has_uid:
                    cursor.execute("""
                        SET NOCOUNT ON;
                        INSERT INTO dbo.UserFeedback
                            (SourceName, BatchID, RowNumber, PredictionID, InputText, InputSha256,
                             ModelPrediction, SuggestedLabel, ReasonCategory, UserNote, ReviewStatus, UserID)
                        OUTPUT INSERTED.FeedbackID
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(source_name)[:40],
                        None if batch_id is None else int(batch_id),
                        None if row_number is None else int(row_number),
                        resolved_prediction_id,
                        None if input_text is None else text_str,
                        input_hash,
                        str(model_prediction)[:100],
                        str(suggested_label)[:100],
                        str(reason_category or 'Lý do khác')[:150],
                        str(user_note)[:4000],
                        'Chờ xem xét',
                        None if user_id is None else int(user_id),
                    ))
                else:
                    cursor.execute("""
                        SET NOCOUNT ON;
                        INSERT INTO dbo.UserFeedback
                            (SourceName, BatchID, RowNumber, PredictionID, InputText, InputSha256,
                             ModelPrediction, SuggestedLabel, ReasonCategory, UserNote, ReviewStatus)
                        OUTPUT INSERTED.FeedbackID
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(source_name)[:40],
                        None if batch_id is None else int(batch_id),
                        None if row_number is None else int(row_number),
                        resolved_prediction_id,
                        None if input_text is None else text_str,
                        input_hash,
                        str(model_prediction)[:100],
                        str(suggested_label)[:100],
                        str(reason_category or 'Lý do khác')[:150],
                        str(user_note)[:4000],
                        'Chờ xem xét',
                    ))
            else:
                cursor.execute("""
                    SET NOCOUNT ON;
                    INSERT INTO dbo.UserFeedback
                        (SourceName, InputText, ModelPrediction, SuggestedLabel, UserNote)
                    OUTPUT INSERTED.FeedbackID
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    str(source_name)[:40],
                    None if input_text is None else text_str,
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


def list_user_feedback(status_filter: str = '', reason_filter: str = '',
                       search: str = '', page: int = 1, page_size: int = 20,
                       user_id: int | None = None) -> dict[str, Any]:
    """List user feedback records with pagination, filtering, and status summary."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        return {'available': False, 'items': [], 'total': 0, 'counts': {}}
    pyodbc = _get_pyodbc()
    safe_page = max(1, int(page))
    safe_size = max(1, min(int(page_size), 100))
    offset = (safe_page - 1) * safe_size
    try:
        with pyodbc.connect(connection_string, timeout=8) as conn:
            cursor = conn.cursor()
            extended = _feedback_has_extended_columns(cursor)
            has_uid = _table_has_user_id(cursor, 'dbo.UserFeedback')
            where_clauses = []
            params: list[Any] = []
            if has_uid:
                if user_id is not None:
                    where_clauses.append('UserID = ?')
                    params.append(int(user_id))
                else:
                    where_clauses.append('UserID IS NULL')
            if extended and status_filter in FEEDBACK_STATUSES:
                where_clauses.append('ReviewStatus = ?')
                params.append(status_filter)
            if extended and reason_filter:
                where_clauses.append('ReasonCategory = ?')
                params.append(reason_filter)
            if search:
                where_clauses.append('(InputText LIKE ? OR UserNote LIKE ?)')
                like = f'%{search}%'
                params.extend([like, like])
            where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

            total = int(cursor.execute(
                f'SELECT COUNT_BIG(*) FROM dbo.UserFeedback {where_sql}', params
            ).fetchone()[0])

            counts = {'Chờ xem xét': 0, 'Đã xác minh': 0, 'Không chấp nhận': 0}
            if extended:
                cnt_where = ''
                cnt_params: list[Any] = []
                if has_uid:
                    if user_id is not None:
                        cnt_where = 'WHERE UserID = ?'
                        cnt_params.append(int(user_id))
                    else:
                        cnt_where = 'WHERE UserID IS NULL'
                for st, cnt in cursor.execute(
                    f'SELECT ReviewStatus, COUNT_BIG(*) FROM dbo.UserFeedback {cnt_where} GROUP BY ReviewStatus',
                    cnt_params
                ).fetchall():
                    if st in counts:
                        counts[st] = int(cnt)
                select_sql = f"""
                    SELECT FeedbackID, CONVERT(VARCHAR(33), CreatedUtc, 127) AS CreatedUtc,
                           SourceName, BatchID, RowNumber, PredictionID,
                           InputText, ModelPrediction, SuggestedLabel, ReasonCategory, UserNote,
                           ReviewStatus, CONVERT(VARCHAR(33), ReviewedUtc, 127) AS ReviewedUtc
                    FROM dbo.UserFeedback
                    {where_sql}
                    ORDER BY FeedbackID DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """
            else:
                counts['Chờ xem xét'] = total
                select_sql = f"""
                    SELECT FeedbackID, CONVERT(VARCHAR(33), CreatedUtc, 127) AS CreatedUtc,
                           SourceName, NULL AS BatchID, NULL AS RowNumber,
                           NULL AS PredictionID, InputText, ModelPrediction, SuggestedLabel,
                           N'Lý do khác' AS ReasonCategory, UserNote,
                           N'Chờ xem xét' AS ReviewStatus, NULL AS ReviewedUtc
                    FROM dbo.UserFeedback
                    {where_sql}
                    ORDER BY FeedbackID DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """
            rows = cursor.execute(select_sql, [*params, offset, safe_size]).fetchall()
            items = []
            for r in rows:
                items.append({
                    'feedback_id': int(r[0]),
                    'created_utc': _iso(r[1]),
                    'source_name': r[2],
                    'batch_id': int(r[3]) if r[3] is not None else None,
                    'row_number': int(r[4]) if r[4] is not None else None,
                    'prediction_id': int(r[5]) if r[5] is not None else None,
                    'input_text': r[6],
                    'model_prediction': r[7],
                    'suggested_label': r[8],
                    'reason_category': r[9],
                    'user_note': r[10],
                    'review_status': r[11],
                    'reviewed_utc': _iso(r[12]),
                })
            return {
                'available': True,
                'items': items,
                'total': total,
                'page': safe_page,
                'page_size': safe_size,
                'counts': counts,
            }
    except Exception as exc:
        return {'available': False, 'error': str(exc), 'items': [], 'total': 0, 'counts': {}}


def update_feedback_status(feedback_id: int, new_status: str) -> bool:
    """Update review status of a feedback record. Never alters model predictions."""
    if new_status not in FEEDBACK_STATUSES:
        raise ValueError('Trạng thái báo cáo không hợp lệ.')
    connection_string = sql_server_connection_string()
    if not connection_string:
        return False
    pyodbc = _get_pyodbc()
    with pyodbc.connect(connection_string, timeout=8) as conn:
        _ensure_auth_schema(conn)
        cursor = conn.cursor()
        if not _feedback_has_extended_columns(cursor):
            return False
        cursor.execute("""
            UPDATE dbo.UserFeedback
            SET ReviewStatus = ?, ReviewedUtc = SYSDATETIMEOFFSET()
            WHERE FeedbackID = ?
        """, (new_status, int(feedback_id)))
        updated = cursor.rowcount > 0
        conn.commit()
        return updated


def record_prediction_batch(task: str, source_name: str, results: list[dict],
                             upload_bytes: int = 0, raw_bytes: bytes | None = None,
                             user_id: int | None = None) -> int | None:
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
            if user_id is not None and _table_has_user_id(cursor, 'dbo.PredictionBatches'):
                cursor.execute("""
                    SET NOCOUNT ON;
                    INSERT INTO dbo.PredictionBatches
                        (Task, SourceName, [RowCount], UploadBytes, UploadSha256, UserID)
                    OUTPUT INSERTED.BatchID
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (task, str(source_name)[:260], len(rows), int(upload_bytes), digest,
                      None if user_id is None else int(user_id)))
            else:
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


def list_prediction_batches(limit: int = 50, user_id: int | None = None) -> list[dict]:
    """Read prediction batch history from SQL Server with label counts, scoped per user."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        return []
    pyodbc = _get_pyodbc()
    safe_limit = max(1, min(int(limit), 500))
    with pyodbc.connect(connection_string, timeout=8) as conn:
        _ensure_auth_schema(conn)
        cursor = conn.cursor()
        has_uid = _table_has_user_id(cursor, 'dbo.PredictionBatches')
        where_sql = ''
        params: list[Any] = []
        if has_uid:
            if user_id is not None:
                where_sql = 'WHERE b.UserID = ?'
                params.append(int(user_id))
            else:
                where_sql = 'WHERE b.UserID IS NULL'
        cursor.execute(f"""
            SELECT TOP ({safe_limit})
                   b.BatchID AS id,
                   CONVERT(VARCHAR(33), b.CreatedUtc, 127) AS created_utc,
                   b.Task AS task,
                   b.SourceName AS source_name,
                   b.[RowCount] AS row_count,
                   b.UploadBytes AS upload_bytes,
                   b.UploadSha256 AS upload_sha256,
                   SUM(CASE WHEN p.PredictedLabel = 1 THEN 1 ELSE 0 END) AS negative_count,
                   SUM(CASE WHEN p.PredictedLabel = 0 THEN 1 ELSE 0 END) AS nonnegative_count,
                   SUM(CASE WHEN p.PredictedLabel IS NULL THEN 1 ELSE 0 END) AS invalid_count
            FROM dbo.PredictionBatches AS b
            LEFT JOIN dbo.Predictions AS p ON p.BatchID = b.BatchID
            {where_sql}
            GROUP BY b.BatchID, b.CreatedUtc, b.Task, b.SourceName, b.[RowCount], b.UploadBytes, b.UploadSha256
            ORDER BY b.BatchID DESC
        """, params)
        columns = [item[0] for item in cursor.description]
        items = []
        for row in cursor.fetchall():
            rec = dict(zip(columns, row))
            rec['created_utc'] = _iso(rec.get('created_utc'))
            rec['analysis_type'] = 'Đơn lẻ' if rec.get('source_name') == 'manual_input' else 'Hàng loạt'
            items.append(rec)
        return items


def query_predictions_paginated(batch_id: int | None = None, label_filter: str = '',
                                search: str = '', date_from: str = '', date_to: str = '',
                                page: int = 1, page_size: int = 20,
                                user_id: int | None = None) -> dict[str, Any]:
    """Paginated prediction history from SQL Server, scoped per user."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        return {'available': False, 'items': [], 'total': 0}
    pyodbc = _get_pyodbc()
    safe_page = max(1, int(page))
    safe_size = max(1, min(int(page_size), 100))
    offset = (safe_page - 1) * safe_size
    where_clauses = []
    params: list[Any] = []
    if batch_id is not None:
        where_clauses.append('p.BatchID = ?')
        params.append(int(batch_id))
    if label_filter in ('0', '1'):
        where_clauses.append('p.PredictedLabel = ?')
        params.append(int(label_filter))
    elif label_filter == 'invalid':
        where_clauses.append('p.PredictedLabel IS NULL')
    if search:
        where_clauses.append('p.InputText LIKE ?')
        params.append(f'%{search}%')
    if date_from:
        where_clauses.append('b.CreatedUtc >= ?')
        params.append(date_from)
    if date_to:
        where_clauses.append('b.CreatedUtc <= ?')
        params.append(date_to)

    try:
        with pyodbc.connect(connection_string, timeout=10) as conn:
            cursor = conn.cursor()
            if user_id is not None and _table_has_user_id(cursor, 'dbo.PredictionBatches'):
                if user_id is not None:
                    where_clauses.append('b.UserID = ?')
                    params.append(int(user_id))
                else:
                    where_clauses.append('b.UserID IS NULL')
            where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''
            total = int(cursor.execute(f"""
                SELECT COUNT_BIG(*)
                FROM dbo.Predictions AS p
                JOIN dbo.PredictionBatches AS b ON b.BatchID = p.BatchID
                {where_sql}
            """, params).fetchone()[0])
            cursor.execute(f"""
                SELECT p.PredictionID, p.BatchID, p.RowNumber, p.InputText,
                       p.PredictedLabel, p.LabelName, p.Status,
                       CONVERT(VARCHAR(33), b.CreatedUtc, 127) AS CreatedUtc, b.SourceName
                FROM dbo.Predictions AS p
                JOIN dbo.PredictionBatches AS b ON b.BatchID = p.BatchID
                {where_sql}
                ORDER BY p.PredictionID DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """, [*params, offset, safe_size])
            items = []
            for r in cursor.fetchall():
                items.append({
                    'prediction_id': int(r[0]),
                    'batch_id': int(r[1]),
                    'row_number': int(r[2]),
                    'input_text': r[3],
                    'predicted_label': int(r[4]) if r[4] is not None else None,
                    'label_name': r[5],
                    'status': r[6],
                    'created_utc': _iso(r[7]),
                    'source_name': r[8],
                    'analysis_type': 'Đơn lẻ' if r[8] == 'manual_input' else 'Hàng loạt',
                })
            return {
                'available': True,
                'items': items,
                'total': total,
                'page': safe_page,
                'page_size': safe_size,
            }
    except Exception as exc:
        return {'available': False, 'error': str(exc), 'items': [], 'total': 0}


def get_predictions(batch_id: int, user_id: int | None = None) -> list[dict]:
    """Read row-level prediction details from SQL Server only, scoped by user if UserID exists."""
    connection_string = sql_server_connection_string()
    if not connection_string:
        return []
    pyodbc = _get_pyodbc()
    with pyodbc.connect(connection_string, timeout=10) as conn:
        cursor = conn.cursor()
        if _table_has_user_id(cursor, 'dbo.PredictionBatches'):
            if user_id is not None:
                cursor.execute("""
                    SELECT p.PredictionID AS prediction_id, p.RowNumber AS row_number, p.InputText AS input_text,
                           p.PredictedLabel AS predicted_label, p.LabelName AS label_name, p.Status AS status
                    FROM dbo.Predictions AS p
                    JOIN dbo.PredictionBatches AS b ON b.BatchID = p.BatchID
                    WHERE p.BatchID = ? AND b.UserID = ?
                    ORDER BY p.RowNumber
                """, (int(batch_id), int(user_id)))
            else:
                cursor.execute("""
                    SELECT p.PredictionID AS prediction_id, p.RowNumber AS row_number, p.InputText AS input_text,
                           p.PredictedLabel AS predicted_label, p.LabelName AS label_name, p.Status AS status
                    FROM dbo.Predictions AS p
                    JOIN dbo.PredictionBatches AS b ON b.BatchID = p.BatchID
                    WHERE p.BatchID = ? AND b.UserID IS NULL
                    ORDER BY p.RowNumber
                """, (int(batch_id),))
        else:
            cursor.execute("""
                SELECT PredictionID AS prediction_id, RowNumber AS row_number, InputText AS input_text,
                       PredictedLabel AS predicted_label, LabelName AS label_name, Status AS status
                FROM dbo.Predictions WHERE BatchID = ? ORDER BY RowNumber
            """, (int(batch_id),))
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
