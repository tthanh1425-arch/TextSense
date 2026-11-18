"""Standalone local TextSense web UI and HTTP API.

Start with: python serve_textsense.py
Open: http://127.0.0.1:8502
The server only binds to loopback; CSV uploads are capped at 100 MB / 300,000 rows.
"""
from __future__ import annotations

import base64
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from collections import Counter

import pandas as pd

from database import record_prediction_batch
from predict import predict
from predict import OUTPUT

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = (BASE_DIR / 'web').resolve()
MODEL_TASK = 'binary'
MODEL_PATH = OUTPUT / f'{MODEL_TASK}_linear_svm.joblib'
DEFAULT_PORT = int(os.environ.get('TEXTSENSE_PORT', '8502'))
MAX_CSV_BYTES = 100 * 1024 * 1024
MAX_CSV_ROWS = 300_000
MAX_TEXT_CHARS = 2_000
MAX_JSON_BYTES = 32 * 1024
RESULT_COLUMN = 'Nhãn dự đoán TextSense (0/1)'
RESULT_NAME_COLUMN = 'Tên nhãn proxy TextSense'
CODE_TO_RESULT = {0: 'nonnegative', 1: 'negative'}


STOPWORDS_EN = {
    'the','and','for','that','this','with','you','your','are','was','were','have','has','had',
    'but','not','all','they','them','their','there','then','than','from','about','would','could',
    'should','will','just','what','when','where','which','who','why','how','into','out','our',
    'his','her','she','him','its',"it's",'too','very','can','cant','cannot','don','does','did',
    'been','being','get','got','one','two','more','most','some','any','only','also','because',
    'people','someone','something','like','know','think','make','made','much','many','really',
    'https','http','www','com','amp','rt'
}


# Danh sach doi chieu minh hoa (tieng Anh), KHONG phai nhan duoc gan / kiem chung.
# Thong ke nay phu thuoc ngu canh, khong suy ra loi xuc pham tu moi lan xuat hien.
SUSPECT_TERMS_EN = frozenset({
    'abusive', 'asshole', 'assholes', 'bastard', 'bastards', 'bitch', 'bitches',
    'bullshit', 'crap', 'crappy', 'damn', 'dick', 'dicks', 'dumb',
    'dumbass', 'fool', 'fools', 'fuck', 'fucked', 'fucker', 'fuckers',
    'fucking', 'fucks', 'idiot', 'idiots', 'jerk', 'jerks', 'loser',
    'losers', 'moron', 'morons', 'pathetic', 'scum', 'shit', 'shitty',
    'stfu', 'stupid', 'suck', 'sucks', 'trash', 'ugly', 'worthless',
    'wtf',
})


def count_suspect_terms(texts, mask, limit=15):
    """Count exact English tokens: occurrences and distinct comments containing a token."""
    occurrences, documents = Counter(), Counter()
    for message in texts[mask]:
        tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", message.casefold())
        matched = [token for token in tokens if token in SUSPECT_TERMS_EN]
        occurrences.update(matched)
        documents.update(set(matched))
    return [{'term': term, 'count': int(count), 'documents': int(documents[term])}
            for term, count in sorted(occurrences.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def build_batch_summary(frame: pd.DataFrame, text_column: str, results: list, filename: str = '') -> dict:
    """Tạo thống kê mô tả cho chính tệp CSV vừa phân tích; không gọi đây là độ chính xác."""
    texts = frame[text_column].fillna('').astype(str)
    codes = [row.get('predicted_label') if row.get('status') == 'ok' else None for row in results]
    valid_mask = pd.Series([code in (0, 1) for code in codes], index=frame.index)
    valid_text_mask = texts.str.strip().ne('')
    valid_mask &= valid_text_mask
    invalid_count = int((~valid_mask).sum())
    valid_count = int(valid_mask.sum())
    negative_count = sum(code == 1 and bool(valid_text_mask.iloc[i]) for i, code in enumerate(codes))
    nonnegative_count = sum(code == 0 and bool(valid_text_mask.iloc[i]) for i, code in enumerate(codes))

    normalized = texts.str.casefold().str.replace(r'\s+', ' ', regex=True).str.strip()
    duplicate_excess = int(normalized[normalized.ne('')].duplicated(keep='first').sum())

    word_counts = texts[valid_mask].map(lambda value: len(value.split()))
    length_buckets = [
        {'label': '≤ 8 từ', 'count': int((word_counts <= 8).sum())},
        {'label': '9–20 từ', 'count': int(((word_counts >= 9) & (word_counts <= 20)).sum())},
        {'label': '≥ 21 từ', 'count': int((word_counts >= 21).sum())},
    ]

    source_col = next((c for c in frame.columns if str(c).strip().casefold() in
                       {'source', 'platform', 'network', 'subreddit', 'community', 'nguon', 'nguồn'}), None)
    source_distribution = []
    if source_col is not None:
        source_values = frame.loc[valid_mask, source_col].fillna('').astype(str).str.strip().replace('', 'Không xác định')
        source_frame = pd.DataFrame({
            'source': source_values,
            'predicted': pd.Series(codes, index=frame.index)[valid_mask].astype(int)
        })
        grouped = source_frame.groupby('source', dropna=False).agg(
            count=('predicted', 'size'),
            negative=('predicted', lambda values: int((values == 1).sum())),
            nonnegative=('predicted', lambda values: int((values == 0).sum()))
        ).sort_values('count', ascending=False).head(8)
        source_distribution = [
            {'label': str(name)[:48], 'count': int(row['count']),
             'negative': int(row['negative']), 'nonnegative': int(row['nonnegative'])}
            for name, row in grouped.iterrows()
        ]
    else:
        low_name = filename.casefold()
        inferred = 'Twitter' if 'twitter' in low_name else 'Reddit' if 'reddit' in low_name else None
        if inferred:
            source_distribution = [{'label': inferred + ' (theo tên tệp)', 'count': valid_count,
                                    'negative': int(negative_count), 'nonnegative': int(nonnegative_count)}]

    original_label_col = next((c for c in frame.columns if str(c).strip().casefold() in
                               {'category', 'sentiment', 'label', 'class', 'target'}), None)
    original_labels = []
    proxy_agreement = None
    if original_label_col is not None:
        raw_labels = pd.to_numeric(frame[original_label_col], errors='coerce')
        counts = raw_labels.value_counts().to_dict()
        original_labels = [
            {'label': '-1 · Tiêu cực', 'count': int(counts.get(-1, 0))},
            {'label': '0 · Trung tính', 'count': int(counts.get(0, 0))},
            {'label': '1 · Tích cực', 'count': int(counts.get(1, 0))},
        ]
        comparable = valid_mask & raw_labels.isin([-1, 0, 1])
        if int(comparable.sum()):
            expected = raw_labels[comparable].map({-1: 1, 0: 0, 1: 0}).astype(int)
            predicted = pd.Series(codes, index=frame.index)[comparable].astype(int)
            proxy_agreement = {
                'count': int(comparable.sum()),
                'rate': round(float((expected == predicted).mean()), 6),
                'note': 'Mức độ trùng khớp với nhãn proxy gốc, không phải độ chính xác trên nhãn người gán.'
            }

    def top_terms(mask, limit=10):
        counter = Counter()
        for text in texts[mask].tolist():
            terms = re.findall(r"[a-z][a-z']{2,}", text.casefold())
            counter.update(term for term in terms if term not in STOPWORDS_EN)
        return [{'term': term, 'count': int(count)} for term, count in counter.most_common(limit)]

    top_all = top_terms(valid_mask)
    negative_mask = pd.Series([code == 1 for code in codes], index=frame.index) & valid_mask
    top_negative = top_terms(negative_mask)
    # Count all terms before taking the top 15 to avoid missing a group's count
    # when a term is outside that group's own top list.
    suspect_all_full = count_suspect_terms(texts, valid_mask, limit=None)
    suspect_negative_full = count_suspect_terms(texts, negative_mask, limit=None)
    suspect_all = suspect_all_full[:15]
    suspect_negative = suspect_negative_full[:15]
    negative_by_term = {item['term']: item for item in suspect_negative_full}
    suspect_combined = []
    for item in suspect_all_full[:15]:
        sub = negative_by_term.get(item['term'], {})
        suspect_combined.append({
            'term': item['term'],
            'total_count': item['count'],
            'negative_count': sub.get('count', 0),
            'total_documents': item['documents'],
            'negative_documents': sub.get('documents', 0),
        })

    date_col = next((c for c in frame.columns if str(c).strip().casefold() in
                     {'date', 'created_at', 'createdat', 'timestamp', 'datetime', 'published_at', 'created'}), None)
    monthly = []
    if date_col is not None:
        dates = pd.to_datetime(frame.loc[valid_mask, date_col], errors='coerce', utc=True)
        if dates.notna().sum() >= 2:
            grouped = dates.dropna().dt.strftime('%Y-%m').value_counts().sort_index().tail(12)
            monthly = [{'label': month, 'count': int(count)} for month, count in grouped.items()]

    return {
        'total': int(len(frame)), 'valid': valid_count, 'invalid': invalid_count,
        'negative': int(negative_count), 'nonnegative': int(nonnegative_count),
        'duplicate_excess': duplicate_excess,
        'avg_words': round(float(word_counts.mean()), 2) if len(word_counts) else 0,
        'median_words': round(float(word_counts.median()), 2) if len(word_counts) else 0,
        'length_buckets': length_buckets,
        'source_distribution': source_distribution,
        'original_labels': original_labels,
        'proxy_agreement': proxy_agreement,
        'top_terms': top_all, 'top_negative_terms': top_negative,
        'suspect_terms_all': suspect_all, 'suspect_terms_negative': suspect_negative,
        'suspect_terms_combined': suspect_combined,
        'suspect_terms_note': 'Tu/cum tu khop danh sach doi chieu tieng Anh, khong phai noi dung xuc pham da duoc xac minh.',
        'monthly_distribution': monthly,
    }


def encode_summary_header(summary: dict) -> str:
    raw = json.dumps(summary, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return base64.b64encode(raw).decode('ascii')


class RequestFailure(Exception):
    def __init__(self, status: int, message: str, detail: str = '', retryable: bool = False):
        super().__init__(message)
        self.status, self.message, self.detail, self.retryable = status, message, detail, retryable


def read_csv_upload(raw: bytes) -> pd.DataFrame:
    if not raw:
        raise ValueError('Tệp CSV trống.')
    if len(raw) > MAX_CSV_BYTES:
        raise ValueError('CSV vượt giới hạn 100 MB.')
    try:
        frame = pd.read_csv(BytesIO(raw), encoding='utf-8-sig', dtype=str,
                            keep_default_na=False, nrows=MAX_CSV_ROWS + 1,
                            on_bad_lines='error')
    except (UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError('CSV phải là UTF-8/UTF-8 BOM và có cấu trúc hợp lệ.') from exc
    if frame.empty:
        raise ValueError('CSV không có dòng dữ liệu.')
    if len(frame) > MAX_CSV_ROWS:
        raise ValueError(f'CSV chỉ được có tối đa {MAX_CSV_ROWS:,} dòng.')
    for column in list(frame.columns):
        if str(column).strip().casefold() == 'unnamed: 0':
            values = frame[column].astype(str).str.strip().reset_index(drop=True)
            zero = pd.Series(range(len(frame))).astype(str)
            one = pd.Series(range(1, len(frame) + 1)).astype(str)
            if values.equals(zero) or values.equals(one):
                frame = frame.drop(columns=[column])
            break
    if frame.shape[1] == 0:
        raise ValueError('CSV chỉ chứa cột chỉ mục, không có dữ liệu để phân tích.')
    return frame


LABEL_COLUMN_NAMES = {
    'category', 'label', 'sentiment', 'class', 'target', 'y', 'nhan', 'nhãn',
    'loai', 'loại', 'polarity', 'ground_truth', 'true_label', 'actual_label', 'label_id'
}
INDEX_COLUMN_NAMES = {'unnamed: 0', 'index', '__index_level_0__', 'id', 'row_id'}
LINK_COLUMN_NAMES = {'url', 'link', 'source', 'source_url', 'post_url', 'permalink', 'tweet_url'}


def csv_column_roles(frame: pd.DataFrame) -> dict:
    label_columns, index_columns = [], []
    for column in frame.columns:
        normalized = str(column).strip().casefold()
        compact = normalized.replace(' ', '_')
        if normalized in LABEL_COLUMN_NAMES or compact in LABEL_COLUMN_NAMES:
            label_columns.append(column)
        if normalized in INDEX_COLUMN_NAMES:
            values = frame[column].astype(str).str.strip().reset_index(drop=True)
            zero = pd.Series(range(len(frame))).astype(str)
            one = pd.Series(range(1, len(frame) + 1)).astype(str)
            if values.equals(zero) or values.equals(one):
                index_columns.append(column)
    link_columns = [c for c in frame.columns if str(c).strip().casefold() in LINK_COLUMN_NAMES]
    excluded = set(label_columns) | set(index_columns) | set(link_columns)
    text_candidates = [c for c in frame.columns if c not in excluded]
    preferred = ('tweet', 'bình luận', 'clean_text', 'clean_comment', 'comment', 'text',
                 'full_text', 'content', 'review', 'sentence', 'message')
    lookup = {str(c).strip().casefold(): c for c in text_candidates}
    suggested = next((lookup[name] for name in preferred if name in lookup), None)
    if suggested is None and text_candidates:
        suggested = max(text_candidates, key=lambda c: frame[c].astype(str).str.len().mean())
    return {'label_columns': label_columns, 'index_columns': index_columns,
            'link_columns': link_columns, 'text_candidates': text_candidates,
            'suggested_column': suggested}


def safe_csv_bytes(frame: pd.DataFrame) -> bytes:
    output = frame.copy()

    def protect(value):
        if not isinstance(value, str):
            return value
        stripped = value.lstrip()
        if stripped.startswith(('=', '+', '@')):
            return "'" + value
        if stripped.startswith('-') and not re.fullmatch(r'-?(?:\d+(?:\.\d*)?|\.\d+)', stripped):
            return "'" + value
        return value

    for column in output.select_dtypes(include=['object', 'string']).columns:
        output[column] = output[column].map(protect)
    return output.to_csv(index=False).encode('utf-8-sig')


def get_model_path() -> Path:
    if not MODEL_PATH.is_file():
        raise RequestFailure(503, 'Chưa có mô hình sẵn sàng',
                             'Hãy chạy notebook huấn luyện trong 01_TRAIN_MODEL rồi khởi động lại ứng dụng.')
    return MODEL_PATH


def infer_comment(input_value: str) -> dict:
    if MODEL_TASK != 'binary':
        raise RequestFailure(409, 'Giao diện web hiện dành cho mô hình nhị phân',
                             'Hãy train --task binary để sử dụng nhãn 0/1 trên giao diện này.')
    text = input_value.strip()
    if not text:
        raise RequestFailure(422, 'Chưa có nội dung', 'Hãy dán nội dung bình luận để phân tích.')
    if re.fullmatch(r'(?:https?://|www\.|(?:x|twitter)\.com/)\S+', text, flags=re.I):
        raise RequestFailure(422, 'TextSense chỉ phân tích nội dung bình luận',
                             'Hãy mở liên kết và dán riêng phần văn bản cần phân tích.')
    if len(text) > MAX_TEXT_CHARS:
        raise RequestFailure(413, 'Văn bản vượt giới hạn', f'Mỗi bình luận tối đa {MAX_TEXT_CHARS:,} ký tự.')
    result = predict(get_model_path(), [text])[0]
    if result['status'] != 'ok':
        raise RequestFailure(422, 'Không thể phân loại văn bản', result['status'])
    code = int(result['predicted_label'])
    return {'label': CODE_TO_RESULT[code], 'code': code, 'text': text,
            'tags': [], 'evidence': [], 'status': 'ok'}


class TextSenseHandler(BaseHTTPRequestHandler):
    server_version = 'TextSenseLocal/2.0'

    def log_message(self, format_str, *args):
        # Avoid writing user-provided comment text or CSV values into HTTP logs.
        pass

    def _send(self, status: int, body: bytes, content_type: str, extra=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        if extra:
            for key, value in extra.items():
                self.send_header(key, str(value))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _json(self, status: int, payload: dict):
        self._send(status, json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8'),
                   'application/json; charset=utf-8')

    def _fail(self, error: RequestFailure):
        self._json(error.status, {'message': error.message, 'detail': error.detail,
                                  'retryable': error.retryable})

    def _read_bytes(self, maximum: int) -> bytes:
        raw_length = self.headers.get('Content-Length', '')
        if not raw_length.isascii() or not raw_length.isdigit():
            raise RequestFailure(411, 'Thiếu kích thước dữ liệu', 'Trình duyệt không gửi Content-Length.')
        size = int(raw_length)
        if size > maximum:
            message = 'CSV tối đa 100 MB.' if maximum == MAX_CSV_BYTES else 'Nội dung yêu cầu vượt giới hạn.'
            raise RequestFailure(413, 'Dữ liệu quá lớn', message)
        if size == 0:
            raise RequestFailure(422, 'Dữ liệu trống', 'Không có nội dung để xử lý.')
        raw = self.rfile.read(size)
        if len(raw) != size:
            raise RequestFailure(400, 'Không nhận đủ dữ liệu')
        return raw

    def _csv_data(self):
        content_type = self.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
        if content_type not in ('text/csv', 'application/csv', 'application/octet-stream'):
            raise RequestFailure(415, 'Cần tệp CSV', 'Hãy chọn tệp .csv UTF-8.')
        raw = self._read_bytes(MAX_CSV_BYTES)
        try:
            return raw, read_csv_upload(raw)
        except ValueError as exc:
            raise RequestFailure(422, 'CSV không hợp lệ', str(exc)) from exc

    def do_POST(self):
        origin = self.headers.get('Origin')
        allowed = {f'http://127.0.0.1:{self.server.server_port}',
                   f'http://localhost:{self.server.server_port}'}
        if origin and origin not in allowed:
            self._json(403, {'message': 'Yêu cầu không cùng nguồn gốc.'})
            return
        parsed = urlsplit(self.path)
        try:
            if parsed.path == '/api/analyze':
                if self.headers.get('Content-Type', '').split(';', 1)[0].lower() != 'application/json':
                    raise RequestFailure(415, 'Cần dữ liệu JSON')
                raw = self._read_bytes(MAX_JSON_BYTES)
                try:
                    payload = json.loads(raw)
                except (ValueError, UnicodeError) as exc:
                    raise RequestFailure(400, 'JSON không hợp lệ') from exc
                if not isinstance(payload, dict) or not isinstance(payload.get('input'), str):
                    raise RequestFailure(422, 'Thiếu văn bản', 'Trường input phải là chuỗi ký tự.')
                result = infer_comment(payload['input'])
                record_prediction_batch('binary', 'manual_input', [{
                    'text': result['text'], 'predicted_label': result['code'],
                    'label_name': 'Phản cảm' if result['code'] == 1 else 'Không phản cảm', 'status': 'ok'
                }], len(raw), raw)
                self._json(200, result)
            elif parsed.path == '/api/columns':
                raw_csv, frame = self._csv_data()
                roles = csv_column_roles(frame)
                preview = [{name: str(row[name])[:180] for name in frame.columns}
                           for _, row in frame.head(3).iterrows()]
                self._json(200, {
                    'rows': len(frame), 'columns': list(frame.columns), 'size_bytes': len(raw_csv),
                    'suggested_column': roles['suggested_column'],
                    'text_candidates': roles['text_candidates'], 'label_columns': roles['label_columns'],
                    'index_columns': roles['index_columns'], 'link_columns': roles['link_columns'],
                    'preview_rows': preview
                })
            elif parsed.path == '/api/batch':
                raw_csv, frame = self._csv_data()
                params = parse_qs(parsed.query, keep_blank_values=True)
                column = params.get('column', [None])[0]
                filename = params.get('filename', ['uploaded.csv'])[0]
                if not isinstance(column, str) or column not in frame.columns:
                    raise RequestFailure(422, 'Không tìm thấy cột bình luận', 'Hãy chọn một cột văn bản trong CSV.')
                roles = csv_column_roles(frame)
                if column not in roles['text_candidates']:
                    raise RequestFailure(422, 'Bạn đang chọn cột nhãn hoặc chỉ mục',
                                         'Hãy chọn cột chứa nội dung, ví dụ clean_text, clean_comment hoặc text.')
                if MODEL_TASK != 'binary':
                    raise RequestFailure(409, 'Mô hình web chưa đúng chế độ', 'Hãy huấn luyện --task binary.')
                results = predict(get_model_path(), frame[column].fillna('').astype(str).tolist())
                codes = [row['predicted_label'] for row in results]
                result_values = [str(int(code)) if code is not None else '' for code in codes]
                if RESULT_COLUMN in frame.columns or RESULT_NAME_COLUMN in frame.columns:
                    raise RequestFailure(422, 'Tệp đã có cột kết quả TextSense',
                                         'Hãy dùng tệp gốc chưa có cột dự đoán để tránh ghi đè.')
                output = frame.copy()
                output[RESULT_NAME_COLUMN] = [
                    ('Phản cảm' if code == 1 else 'Không phản cảm') if code is not None else ''
                    for code in codes
                ]
                output[RESULT_COLUMN] = result_values
                nonnegative_count = sum(code == 0 for code in codes)
                negative_count = sum(code == 1 for code in codes)
                invalid_count = sum(code is None for code in codes)
                if nonnegative_count + negative_count + invalid_count != len(frame):
                    raise RuntimeError('Số lượng kết quả không khớp số dòng CSV.')
                record_prediction_batch('binary', filename, results, len(raw_csv), raw_csv)
                summary = build_batch_summary(frame, column, results, filename)
                data = safe_csv_bytes(output)
                self._send(200, data, 'text/csv; charset=utf-8', {
                    'Content-Disposition': 'attachment; filename="TextSense-ket-qua-nhi-phan.csv"',
                    'X-Total-Rows': len(output), 'X-Valid-Rows': len(output) - invalid_count,
                    'X-Nonnegative-Rows': nonnegative_count, 'X-Negative-Rows': negative_count,
                    'X-Invalid-Rows': invalid_count,
                    'X-TextSense-Summary': encode_summary_header(summary)
                })
            else:
                self._json(404, {'message': 'API không tồn tại.'})
        except RequestFailure as exc:
            self._fail(exc)
        except (ValueError, TypeError) as exc:
            self._json(422, {'message': 'Không xử lý được yêu cầu', 'detail': str(exc)})
        except Exception:
            self._json(500, {'message': 'Máy chủ gặp lỗi', 'detail': 'Không thể xử lý dữ liệu. Vui lòng thử lại.'})

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == '/api/config':
            self._json(200, {'max_csv_bytes': MAX_CSV_BYTES, 'max_csv_rows': MAX_CSV_ROWS,
                             'max_text_chars': MAX_TEXT_CHARS})
            return
        if parsed.path == '/api/health':
            self._json(200, {'status': 'ok', 'model_present': MODEL_PATH.is_file(),
                             'model_filename': MODEL_PATH.name, 'task': MODEL_TASK,
                             'label_names': {'0': 'Không phản cảm', '1': 'Phản cảm'}})
            return
        relative = 'index.html' if parsed.path == '/' else unquote(parsed.path).lstrip('/')
        allowed = {'index.html', 'style.css', 'app.js', 'csv_viewer.js', 'binh_luan_mau.csv'}
        if relative not in allowed and not re.fullmatch(r'media/[A-Za-z0-9_.-]+\.(?:webp|png)', relative):
            self._send(404, b'Not found', 'text/plain; charset=utf-8')
            return
        path = (WEB_DIR / relative).resolve()
        if not path.is_relative_to(WEB_DIR) or not path.is_file():
            self._send(404, b'Not found', 'text/plain; charset=utf-8')
            return
        mime = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
                '.png': 'image/png', '.webp': 'image/webp', '.csv': 'text/csv'}.get(path.suffix)
        content_type = mime + ('; charset=utf-8' if path.suffix in {'.html', '.css', '.js', '.csv'} else '')
        self._send(200, path.read_bytes(), content_type, {
            'Content-Security-Policy': ("default-src 'self'; script-src 'self'; style-src 'self'; "
                                        "img-src 'self' data:; connect-src 'self'; form-action 'self'; "
                                        "base-uri 'none'; frame-ancestors 'none'")
        })

    def do_HEAD(self):
        self.do_GET()

    def do_OPTIONS(self):
        self._send(405, b'Method not allowed', 'text/plain; charset=utf-8')


_server = None
_server_lock = threading.Lock()


def start_local_server(port: int = DEFAULT_PORT):
    global _server
    with _server_lock:
        if _server is not None:
            return _server
        server = ThreadingHTTPServer(('127.0.0.1', port), TextSenseHandler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, name='TextSenseHTTP', daemon=True).start()
        _server = server
        return server


if __name__ == '__main__':
    server = start_local_server(DEFAULT_PORT)
    print(f'TextSense web UI: http://127.0.0.1:{server.server_port}')
    print(f'Model: {MODEL_PATH} | upload CSV <= 100 MB | rows <= {MAX_CSV_ROWS:,}')
    print('Nhan Ctrl+C de dung.')
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        if _server is not None:
            _server.shutdown()
            _server.server_close()
