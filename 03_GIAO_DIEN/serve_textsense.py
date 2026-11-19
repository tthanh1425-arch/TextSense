"""Standalone local TextSense web UI and HTTP API.

Start with: python serve_textsense.py
Open: http://127.0.0.1:8502
The server binds to loopback; CSV/XLSX uploads capped at 100 MB / 300,000 rows.
"""
from __future__ import annotations

import base64
import csv
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO, StringIO, TextIOWrapper
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from collections import Counter
from zipfile import ZipFile, BadZipFile
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font, PatternFill, Alignment

import pandas as pd

from database import record_prediction_batch, record_user_feedback, sql_server_status
from predict import predict
from predict import OUTPUT

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = (BASE_DIR / 'web').resolve()
MODEL_TASK = 'binary'
MODEL_PATH = OUTPUT / f'{MODEL_TASK}_linear_svm.joblib'
DEFAULT_PORT = int(os.environ.get('TEXTSENSE_PORT', '8502'))
MAX_CSV_BYTES = 100 * 1024 * 1024
MAX_CSV_ROWS = 300_000
MAX_RESULT_BYTES = 220 * 1024 * 1024
MAX_XLSX_UNCOMPRESSED = 900 * 1024 * 1024
MAX_TEXT_CHARS = 2_000
MAX_JSON_BYTES = 32 * 1024
RESULT_COLUMN = 'Nhãn dự đoán TextSense (0/1)'
RESULT_NAME_COLUMN = 'Kết quả TextSense'
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


def decode_csv_upload(raw: bytes) -> tuple[str, str]:
    """Decode ordinary CSVs from Excel/Windows without guessing away corrupt text."""
    if raw.startswith(b'PK\x03\x04'):
        raise ValueError('Tệp này là Excel. Hãy dùng đuôi .xlsx thay vì .csv.')
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        codecs = ['utf-16']
    elif raw.startswith(b'\xef\xbb\xbf'):
        codecs = ['utf-8-sig']
    else:
        probe = raw[:4096]
        if probe.count(b'\x00') >= 2:
            even = probe[::2].count(0)
            odd = probe[1::2].count(0)
            codecs = ['utf-16-le' if odd > even else 'utf-16-be']
        else:
            # Unicode CSV, then common Windows Vietnamese/Western code pages.
            codecs = ['utf-8-sig', 'cp1258', 'cp1252', 'iso-8859-1']
    for codec in codecs:
        try:
            decoded = raw.decode(codec, errors='strict')
        except (UnicodeError, LookupError):
            continue
        sample = decoded[:10000]
        if '\x00' in sample or any(ord(char) < 32 and char not in '\r\n\t' for char in sample):
            continue
        if not decoded.strip('\ufeff\r\n\t '):
            raise ValueError('Tệp CSV trống hoặc không có nội dung.')
        return decoded, codec
    raise ValueError('Không nhận diện được cách lưu chữ của tệp CSV. Hãy thử lưu lại dưới dạng CSV UTF-8.')


def detect_csv_delimiter(decoded: str) -> tuple[str, int]:
    """Use well-formed sample records, not occurrence counts inside comments."""
    first_line = decoded.partition('\n')[0].strip('\ufeff\r ')
    directive = re.fullmatch(r'sep\s*=\s*([,;\t|])', first_line, flags=re.IGNORECASE)
    if directive:
        return directive.group(1), 1
    options = [',', ';', '\t', '|']
    known_names = {'comment', 'comments', 'text', 'clean_text', 'clean_comment',
                   'tweet', 'content', 'message', 'review', 'category', 'label',
                   'sentiment', 'bình luận', 'noi_dung', 'nội dung', 'nội_dung'}
    choices = []
    for rank, sep in enumerate(options):
        try:
            reader = csv.reader(StringIO(decoded), delimiter=sep, strict=True)
            rows = []
            for row in reader:
                if not row or not any(cell.strip() for cell in row):
                    continue
                rows.append(row)
                if len(rows) >= 12:
                    break
        except (csv.Error, ValueError):
            continue
        if not rows:
            continue
        width = len(rows[0])
        matched = sum(len(row) == width for row in rows[1:])
        mismatched = len(rows) - 1 - matched
        name_hits = sum(col.strip().casefold().replace(' ', '_') in known_names for col in rows[0])
        score = (40 if width > 1 else 0) + 7 * matched - 30 * mismatched + min(width, 20) + 9 * name_hits
        choices.append((score, -rank, sep))
    if not choices:
        raise ValueError('Cấu trúc CSV bị lỗi. Hãy kiểm tra dấu ngoặc kép và dòng tiêu đề.')
    return max(choices)[2], 0


def read_csv_upload(raw: bytes) -> pd.DataFrame:
    if not raw:
        raise ValueError('Tệp CSV trống.')
    if len(raw) > MAX_CSV_BYTES:
        raise ValueError('CSV vượt giới hạn 100 MB.')
    decoded, codec = decode_csv_upload(raw)
    delimiter, skiprows = detect_csv_delimiter(decoded)
    try:
        frame = pd.read_csv(BytesIO(raw), encoding=codec, sep=delimiter,
                            skiprows=skiprows, dtype=str, keep_default_na=False,
                            nrows=MAX_CSV_ROWS + 1, on_bad_lines='error')
    except (UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError,
            csv.Error, ValueError) as exc:
        raise ValueError('Cấu trúc CSV chưa đúng. Hãy kiểm tra dòng tiêu đề, dấu phân cách và dấu ngoặc kép.') from exc
    if frame.empty:
        raise ValueError('CSV không có dòng dữ liệu.')
    if len(frame) > MAX_CSV_ROWS:
        raise ValueError(f'CSV chỉ được có tối đa {MAX_CSV_ROWS:,} dòng.')
    return clean_imported_frame(frame)



def read_excel_upload(raw: bytes, requested_sheet: str = '') -> tuple[pd.DataFrame, list[str], str]:
    """Read XLSX (not legacy XLS) and select a likely data sheet; allow manual override."""
    if not raw or len(raw) > MAX_CSV_BYTES:
        raise ValueError('Tệp Excel trống hoặc vượt giới hạn 100 MB.')
    if not raw.startswith(b'PK'):
        raise ValueError('Tệp .xlsx không hợp lệ. Hãy lưu lại dưới dạng Excel Workbook (.xlsx).')
    try:
        with ZipFile(BytesIO(raw)) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > MAX_XLSX_UNCOMPRESSED:
                raise ValueError('Tệp Excel có dữ liệu giải nén quá lớn.')
        with pd.ExcelFile(BytesIO(raw), engine='openpyxl') as workbook:
            sheets = workbook.sheet_names
            if not sheets or len(sheets) > 50:
                raise ValueError('Tệp Excel cần có từ 1 đến 50 trang tính.')
            if requested_sheet and requested_sheet not in sheets:
                raise ValueError('Không tìm thấy trang tính đã chọn.')
            if requested_sheet:
                selected = requested_sheet
            else:
                candidates = []
                for position, name in enumerate(sheets):
                    preview = workbook.parse(sheet_name=name, dtype=str,
                                             keep_default_na=False, nrows=20)
                    if preview.empty or not len(preview.columns):
                        continue
                    roles = csv_column_roles(preview)
                    suggested = roles['suggested_column']
                    if suggested:
                        label = str(suggested).strip().casefold().replace(' ', '_')
                        known = {'tweet', 'bình_luận', 'clean_text', 'clean_comment',
                                 'comment', 'text', 'full_text', 'content', 'review',
                                 'sentence', 'message'}
                        priority = 10 if label in known else 0
                        lengths = preview[suggested].astype(str).str.len()
                        priority += min(float(lengths.mean()), 1000) / 1000
                        candidates.append((priority, len(preview), -position, name))
                if not candidates:
                    raise ValueError('Không tìm thấy trang tính có bình luận để phân tích.')
                selected = max(candidates)[-1]
            frame = workbook.parse(sheet_name=selected, dtype=str,
                                   keep_default_na=False, nrows=MAX_CSV_ROWS + 1)
    except ValueError:
        raise
    except (BadZipFile, OSError, KeyError, TypeError, ImportError) as exc:
        raise ValueError('Không đọc được tệp Excel. Hãy kiểm tra định dạng .xlsx và thử lại.') from exc
    if frame.empty:
        raise ValueError('Trang tính đã chọn không có dòng dữ liệu.')
    if len(frame) > MAX_CSV_ROWS:
        raise ValueError(f'Mỗi lần phân tích tối đa {MAX_CSV_ROWS:,} dòng.')
    return clean_imported_frame(frame), sheets, selected


def clean_imported_frame(frame: pd.DataFrame) -> pd.DataFrame:
    for column in list(frame.columns):
        if str(column).strip().casefold() == 'unnamed: 0':
            values = frame[column].astype(str).str.strip().reset_index(drop=True)
            zero = pd.Series(range(len(frame))).astype(str)
            one = pd.Series(range(1, len(frame) + 1)).astype(str)
            if values.equals(zero) or values.equals(one):
                frame = frame.drop(columns=[column])
            break
    if frame.shape[1] == 0:
        raise ValueError('Tệp chỉ chứa cột chỉ mục, không có dữ liệu để phân tích.')
    return frame


def read_tabular_upload(raw: bytes, filename: str, sheet: str = '') -> tuple[pd.DataFrame, list[str], str]:
    suffix = Path(filename).suffix.lower()
    if suffix == '.csv':
        return read_csv_upload(raw), [], ''
    if suffix == '.xlsx':
        return read_excel_upload(raw, sheet)
    raise ValueError('Chỉ hỗ trợ tệp CSV hoặc Excel (.xlsx).')


def result_csv_to_xlsx(raw: bytes) -> bytes:
    """Stream the analyzed CSV into a genuine XLSX without rerunning inference."""
    if not raw or len(raw) > MAX_RESULT_BYTES:
        raise ValueError('Tệp kết quả trống hoặc quá lớn để tạo Excel.')
    reader = csv.reader(TextIOWrapper(BytesIO(raw), encoding='utf-8-sig', newline=''), strict=True)
    try:
        columns = next(reader)
    except (StopIteration, csv.Error) as exc:
        raise ValueError('Không có tiêu đề cột trong dữ liệu kết quả.') from exc
    if RESULT_COLUMN not in columns or RESULT_NAME_COLUMN not in columns:
        raise ValueError('Đây không phải tệp kết quả TextSense V3.16.')
    label_index = columns.index(RESULT_COLUMN)
    text_column = next((i for i, c in enumerate(columns)
                        if str(c).strip().casefold() in ('tweet','clean_text','comment','text','bình luận',
                                                        'clean_comment','content','review','message')), None)
    book = Workbook(write_only=True)
    output_sheet = book.create_sheet('Kết quả phân loại')
    output_sheet.freeze_panes = 'A2'
    output_sheet.sheet_view.showGridLines = False
    navy = PatternFill('solid', fgColor='213452')
    header = []
    for name in columns:
        cell = WriteOnlyCell(output_sheet, value=name)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = navy
        header.append(cell)
    output_sheet.append(header)
    counts = Counter()
    term_counts = Counter()
    number_rows = 0
    for record in reader:
        number_rows += 1
        if number_rows > MAX_CSV_ROWS:
            raise ValueError(f'Tệp kết quả vượt {MAX_CSV_ROWS:,} dòng.')
        if len(record) != len(columns):
            raise ValueError(f'Dữ liệu không hợp lệ tại dòng {number_rows + 1}.')
        code = record[label_index].strip()
        counts[code] += 1
        # Protect cells from formula execution, including if the source CSV was modified.
        safe = []
        for value in record:
            check = value.lstrip()
            if check.startswith(('=', '+', '@')) or (check.startswith('-') and not re.fullmatch(r'-?(?:\d+(?:\.\d*)?|\.\d+)', check)):
                value = "'" + value
            safe.append(value)
        output_sheet.append(safe)
        if text_column is not None and code in ('0', '1'):
            words = re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?", record[text_column].casefold(), re.UNICODE)
            term_counts.update(term for term in words if len(term) > 2 and term not in STOPWORDS_EN)
    sheet = book.create_sheet('Thống kê tổng hợp')
    sheet.sheet_view.showGridLines = False
    total = number_rows
    valid = counts['0'] + counts['1']
    rows = [
        ('TEXTSENSE · TỔNG HỢP PHÂN LOẠI', ''),
        ('Chỉ số', 'Giá trị'),
        ('Tổng số bình luận', total),
        ('Đã phân loại', valid),
        ('Chưa phân loại', total - valid),
        ('Có nội dung tiêu cực', counts['1']),
        ('Không phát hiện nội dung tiêu cực', counts['0']),
        ('Tỷ lệ có nội dung tiêu cực', counts['1']/valid if valid else 0),
        ('Tỷ lệ không phát hiện nội dung tiêu cực', counts['0']/valid if valid else 0),
        ('', ''),
        ('Từ ngữ xuất hiện nhiều', 'Số lần'),
    ]
    rows.extend(term_counts.most_common(15))
    rows.append(('', ''))
    rows.append(('Lưu ý', 'Hai nhóm phản ánh sắc thái cảm xúc, không xác minh lời lẽ xúc phạm.'))
    for i, values in enumerate(rows, start=1):
        excel_row = []
        for j, value in enumerate(values):
            cell = WriteOnlyCell(sheet, value=value)
            if i in (1, 2, 11):
                cell.font = Font(color='FFFFFF', bold=True)
                cell.fill = navy
            if i in (8, 9) and j == 1:
                cell.number_format = '0.0%'
            excel_row.append(cell)
        sheet.append(excel_row)
    sheet.column_dimensions['A'].width = 32
    sheet.column_dimensions['B'].width = 67
    data = BytesIO()
    book.save(data)
    return data.getvalue()


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



# Phân tích câu/vế chỉ bổ sung thông tin cho dự đoán toàn bình luận.
# Dùng chính model đã huấn luyện: không có luật từ khóa tự ghi đè nhãn.
SENTENCE_LIMIT = 24
SENTENCE_BOUNDARY_RE = re.compile(
    r"(?<!\d)[.!?。！？…]+|[.!?。！？…]+(?!\d)|[;；\r\n]+|"
    r"[,，]\s*(?=(?:but|however|yet|though|although|nevertheless|whereas|while)\b)|"
    r"\s+(?=(?:but|however|yet|nevertheless)\b)|\s+[—–]\s+",
    flags=re.I,
)


def split_comment_sentences(text: str) -> list[str]:
    """Split sentence endings and contrastive clauses, not ordinary list commas.

    Keep the conjunction in the following clause for readable context.
    Do not split decimal points such as 3.14.
    """
    parts = [part.strip(' \t,，;；:：—–') for part in SENTENCE_BOUNDARY_RE.split(str(text))]
    return [part for part in parts if re.search(r'\w', part)]


def analyze_sentence_breakdown(text: str) -> dict:
    """Predict clause labels with the same model, not sentiment percentages.

    Only show supplementary details when at least one part is predicted negative;
    nonnegative parts remain visible as context. This is not an independently
    validated sentence-level classifier.
    """
    parts = split_comment_sentences(text)
    if len(parts) < 2:
        return {'available': False, 'mixed': False, 'sentences': []}
    if len(parts) > SENTENCE_LIMIT:
        return {'available': False, 'mixed': False, 'sentences': [],
                'detail': 'Bình luận có quá nhiều phần để hiển thị chi tiết.'}
    rows = predict(get_model_path(), parts)
    details = []
    negative_count = nonnegative_count = 0
    for part, row in zip(parts, rows):
        code = row.get('predicted_label') if row.get('status') == 'ok' else None
        if code == 1:
            negative_count += 1
        elif code == 0:
            nonnegative_count += 1
        details.append({'text': part, 'code': code,
                        'label': CODE_TO_RESULT.get(code, 'unavailable')})
    valid_count = negative_count + nonnegative_count
    return {
        'available': valid_count >= 2 and negative_count > 0,
        'mixed': negative_count > 0 and nonnegative_count > 0,
        'total_parts': valid_count,
        'negative_parts': negative_count,
        'nonnegative_parts': nonnegative_count,
        'sentences': details,
    }


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
    sentence_analysis = analyze_sentence_breakdown(text)
    has_negative_part = bool(sentence_analysis.get('negative_parts', 0) > 0)
    if code == 1 or has_negative_part:
        final_code = 1
        final_label = 'negative'
        final_label_name = 'Có nội dung tiêu cực'
    else:
        final_code = 0
        final_label = 'nonnegative'
        final_label_name = 'Không phát hiện nội dung tiêu cực'
    return {
        'label': final_label,
        'code': final_code,
        'label_name': final_label_name,
        'text': text,
        'status': 'ok',
        'sentence_analysis': sentence_analysis,
    }


class TextSenseHandler(BaseHTTPRequestHandler):
    server_version = 'TextSenseLocal/3.24'

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
            message = 'Tệp tải lên tối đa 100 MB.' if maximum == MAX_CSV_BYTES else 'Nội dung yêu cầu vượt giới hạn.'
            raise RequestFailure(413, 'Dữ liệu quá lớn', message)
        if size == 0:
            raise RequestFailure(422, 'Dữ liệu trống', 'Không có nội dung để xử lý.')
        raw = self.rfile.read(size)
        if len(raw) != size:
            raise RequestFailure(400, 'Không nhận đủ dữ liệu')
        return raw

    def _tabular_data(self, params):
        content_type = self.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
        if content_type not in ('text/csv', 'application/csv', 'application/octet-stream',
                                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'):
            raise RequestFailure(415, 'Định dạng tệp không hợp lệ', 'Hãy tải tệp CSV hoặc Excel (.xlsx).')
        filename = params.get('filename', [''])[0]
        sheet = params.get('sheet', [''])[0]
        if not isinstance(filename, str) or Path(filename).suffix.lower() not in ('.csv', '.xlsx'):
            raise RequestFailure(415, 'Định dạng tệp không hợp lệ', 'Hãy tải tệp CSV hoặc Excel (.xlsx).')
        raw = self._read_bytes(MAX_CSV_BYTES)
        try:
            frame, sheet_names, selected_sheet = read_tabular_upload(raw, filename, sheet)
            return raw, frame, sheet_names, selected_sheet
        except ValueError as exc:
            raise RequestFailure(422, 'Không đọc được tệp', str(exc)) from exc

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
                history_id = record_prediction_batch('binary', 'manual_input', [{
                    'text': result['text'], 'predicted_label': result['code'],
                    'label_name': result['label_name'], 'status': 'ok'
                }], len(raw), raw)
                result['history_saved'] = history_id is not None
                self._json(200, result)
            elif parsed.path == '/api/sentences':
                if self.headers.get('Content-Type', '').split(';', 1)[0].lower() != 'application/json':
                    raise RequestFailure(415, 'Cần dữ liệu JSON')
                raw = self._read_bytes(MAX_JSON_BYTES)
                try:
                    payload = json.loads(raw)
                except (ValueError, UnicodeError) as exc:
                    raise RequestFailure(400, 'JSON không hợp lệ') from exc
                if not isinstance(payload, dict) or not isinstance(payload.get('input'), str):
                    raise RequestFailure(422, 'Thiếu văn bản', 'Trường input phải là chuỗi ký tự.')
                text = payload['input'].strip()
                if not text or len(text) > MAX_TEXT_CHARS:
                    raise RequestFailure(422, 'Nội dung không phù hợp', 'Bình luận cần có từ 1 đến 2.000 ký tự.')
                self._json(200, analyze_sentence_breakdown(text))
            elif parsed.path == '/api/feedback':
                if self.headers.get('Content-Type', '').split(';', 1)[0].lower() != 'application/json':
                    raise RequestFailure(415, 'Cần dữ liệu JSON')
                raw = self._read_bytes(MAX_JSON_BYTES)
                try:
                    payload = json.loads(raw)
                except (ValueError, UnicodeError) as exc:
                    raise RequestFailure(400, 'JSON không hợp lệ') from exc
                if not isinstance(payload, dict):
                    raise RequestFailure(422, 'Dữ liệu không hợp lệ')
                source = str(payload.get('source', 'Bình luận riêng lẻ'))
                prediction = str(payload.get('prediction', ''))
                suggested_label = str(payload.get('suggested_label', ''))
                note = str(payload.get('note', ''))
                text = payload.get('text')
                feedback_id = record_user_feedback(
                    source_name=source,
                    model_prediction=prediction,
                    suggested_label=suggested_label,
                    user_note=note,
                    input_text=text
                )
                self._json(200, {
                    'status': 'ok',
                    'feedback_saved': feedback_id is not None,
                    'feedback_id': feedback_id,
                    'message': 'Phản hồi đã được ghi nhận vào SQL Server.' if feedback_id is not None
                               else 'Chưa lưu được vào SQL Server. Vui lòng kiểm tra kết nối.'
                })
            elif parsed.path == '/api/columns':
                params = parse_qs(parsed.query, keep_blank_values=True)
                raw_csv, frame, sheet_names, selected_sheet = self._tabular_data(params)
                roles = csv_column_roles(frame)
                preview = [{name: str(row[name])[:180] for name in frame.columns}
                           for _, row in frame.head(3).iterrows()]
                self._json(200, {
                    'rows': len(frame), 'columns': list(frame.columns), 'size_bytes': len(raw_csv),
                    'sheets': sheet_names, 'selected_sheet': selected_sheet,
                    'suggested_column': roles['suggested_column'],
                    'text_candidates': roles['text_candidates'], 'label_columns': roles['label_columns'],
                    'index_columns': roles['index_columns'], 'link_columns': roles['link_columns'],
                    'preview_rows': preview
                })
            elif parsed.path == '/api/batch':
                params = parse_qs(parsed.query, keep_blank_values=True)
                raw_csv, frame, sheet_names, selected_sheet = self._tabular_data(params)
                column = params.get('column', [None])[0]
                filename = params.get('filename', [''])[0]
                if not isinstance(column, str) or column not in frame.columns:
                    raise RequestFailure(422, 'Không tìm thấy cột bình luận', 'Hãy chọn cột chứa bình luận trong tệp.')
                roles = csv_column_roles(frame)
                if column not in roles['text_candidates']:
                    raise RequestFailure(422, 'Bạn đang chọn cột nhãn hoặc chỉ mục',
                                         'Hãy chọn cột chứa nội dung, ví dụ clean_text, clean_comment hoặc text.')
                if MODEL_TASK != 'binary':
                    raise RequestFailure(409, 'Mô hình web chưa đúng chế độ', 'Hãy huấn luyện --task binary.')
                results = predict(get_model_path(), frame[column].fillna('').astype(str).tolist())
                codes = [row['predicted_label'] for row in results]
                result_values = [str(int(code)) if code is not None else '' for code in codes]
                if RESULT_COLUMN in frame.columns or RESULT_NAME_COLUMN in frame.columns or 'Tên nhãn proxy TextSense' in frame.columns:
                    raise RequestFailure(422, 'Tệp đã có cột kết quả TextSense',
                                         'Hãy dùng tệp gốc chưa có cột dự đoán để tránh ghi đè.')
                output = frame.copy()
                output[RESULT_NAME_COLUMN] = [
                    ('Có nội dung tiêu cực' if code == 1 else 'Không phát hiện nội dung tiêu cực') if code is not None else ''
                    for code in codes
                ]
                output[RESULT_COLUMN] = result_values
                nonnegative_count = sum(code == 0 for code in codes)
                negative_count = sum(code == 1 for code in codes)
                invalid_count = sum(code is None for code in codes)
                if nonnegative_count + negative_count + invalid_count != len(frame):
                    raise RuntimeError('Số lượng kết quả không khớp số dòng dữ liệu.')
                history_id = record_prediction_batch('binary', filename, results, len(raw_csv), raw_csv)
                summary = build_batch_summary(frame, column, results, filename)
                data = safe_csv_bytes(output)
                self._send(200, data, 'text/csv; charset=utf-8', {
                    'Content-Disposition': 'attachment; filename="TextSense-ket-qua.csv"',
                    'X-Total-Rows': len(output), 'X-Valid-Rows': len(output) - invalid_count,
                    'X-Nonnegative-Rows': nonnegative_count, 'X-Negative-Rows': negative_count,
                    'X-Invalid-Rows': invalid_count,
                    'X-History-Saved': 'true' if history_id is not None else 'false',
                    'X-TextSense-Summary': encode_summary_header(summary)
                })
            elif parsed.path == '/api/export-xlsx':
                if self.headers.get('Content-Type', '').split(';', 1)[0].strip().lower() != 'application/octet-stream':
                    raise RequestFailure(415, 'Định dạng dữ liệu không phù hợp')
                raw = self._read_bytes(MAX_RESULT_BYTES)
                try:
                    excel = result_csv_to_xlsx(raw)
                except (ValueError, csv.Error) as exc:
                    raise RequestFailure(422, 'Không tạo được tệp Excel', str(exc)) from exc
                self._send(200, excel, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', {
                    'Content-Disposition': 'attachment; filename="TextSense-ket-qua.xlsx"'
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
            sql_status = sql_server_status()
            self._json(200, {'status': 'ok', 'model_present': MODEL_PATH.is_file(),
                             'model_filename': MODEL_PATH.name, 'task': MODEL_TASK,
                             'sql_server': sql_status,
                             'history_storage': 'SQL Server',
                             'label_names': {'0': 'Không phát hiện nội dung tiêu cực', '1': 'Có nội dung tiêu cực'}})
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
    print(f'Model: {MODEL_PATH} | CSV/XLSX <= 100 MB | rows <= {MAX_CSV_ROWS:,}')
    sql_status = sql_server_status()
    print(f"SQL Server history: {sql_status['message']}")
    print('Lich su huan luyen, du doan va CSV/Excel deu dung SQL Server.')
    print('Nhan Ctrl+C de dung.')
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        if _server is not None:
            _server.shutdown()
            _server.server_close()
