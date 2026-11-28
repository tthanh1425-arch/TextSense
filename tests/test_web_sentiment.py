"""Smoke/regression tests; no SQL Server instance or model retraining needed."""
import io
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

try:
    import pytest
except ImportError:
    class _MockPytest:
        @staticmethod
        def fixture(func):
            return func
    pytest = _MockPytest()
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '03_GIAO_DIEN'))
import serve_textsense as web


@pytest.fixture
def fake_model(monkeypatch):
    # Deterministic model stub: tests endpoint/data flow, NOT model accuracy.
    def predict_stub(model_path, texts, batch_size=512):
        result = []
        for text in texts:
            code = 1 if any(term in str(text).casefold() for term in ('bad', 'awful', 'disappoint', 'terrible')) else 0
            status = 'ok' if str(text).strip() else 'Văn bản rỗng'
            result.append({'text': text, 'predicted_label': code if status == 'ok' else None,
                           'label_name': ('Có nội dung tiêu cực' if code else 'Không phát hiện nội dung tiêu cực') if status == 'ok' else None,
                           'status': status})
        return result
    monkeypatch.setattr(web, 'predict', predict_stub)
    monkeypatch.setattr(web, 'record_prediction_batch', lambda *args, **kwargs: None)
    return predict_stub


def test_contrastive_clause_splitting_without_overfragmentation():
    assert web.split_comment_sentences("Good design, but the battery is awful.") == [
        'Good design', 'but the battery is awful']
    assert web.split_comment_sentences('I bought a phone, charger, and a case.') == [
        'I bought a phone, charger, and a case']
    assert web.split_comment_sentences('Good design but poor battery.') == [
        'Good design', 'but poor battery']
    assert web.split_comment_sentences('Version 3.14 is okay. The update is awful.') == [
        'Version 3.14 is okay', 'The update is awful']


def test_classification_rule_any_negative_part_yields_negative(fake_model):
    # Có ít nhất 1 phần tiêu cực (hoặc cả bình luận bị dự đoán tiêu cực) -> Có nội dung tiêu cực
    payload = web.infer_comment('Good design, but the battery is awful.')
    assert payload['code'] == 1
    assert payload['label'] == 'negative'
    assert payload['label_name'] == 'Có nội dung tiêu cực'
    detail = payload['sentence_analysis']
    assert detail['mixed'] and detail['negative_parts'] == 1
    assert detail['total_parts'] == 2
    assert 'negative_rate' not in detail


def test_classification_rule_no_negative_parts_and_whole_nonnegative(fake_model):
    # Không có phần nào tiêu cực và cả bình luận cũng không -> Không phát hiện nội dung tiêu cực
    payload = web.infer_comment('Good design. Excellent battery.')
    assert payload['code'] == 0
    assert payload['label'] == 'nonnegative'
    assert payload['label_name'] == 'Không phát hiện nội dung tiêu cực'
    assert payload['sentence_analysis']['negative_parts'] == 0


def test_no_negative_parts_hides_optional_explanation(fake_model):
    detail = web.analyze_sentence_breakdown('Good design. Excellent battery.')
    assert detail['available'] is False
    assert detail['negative_parts'] == 0
    assert 'negative_rate' not in detail


def test_all_negative_parts_remain_available(fake_model):
    detail = web.analyze_sentence_breakdown('Awful design. Bad battery.')
    assert detail['available'] is True
    assert detail['mixed'] is False
    assert detail['negative_parts'] == 2


def test_single_sentence_no_breakdown(fake_model):
    assert web.analyze_sentence_breakdown('The performance is awful.')['available'] is False


def test_batch_percentages_still_describe_number_of_comments(fake_model):
    import pandas as pd
    frame = pd.DataFrame({'text':['Nice design', 'Bad battery', 'Great case'],
                          'source':['A','A','B']})
    result = fake_model(None, frame['text'].tolist())
    summary = web.build_batch_summary(frame, 'text', result)
    assert summary['valid'] == 3
    assert summary['negative'] == 1
    assert summary['nonnegative'] == 2


@pytest.fixture
def http_server(fake_model):
    # start_local_server uses local loopback even on port 0.
    server = web.start_local_server(0)
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        web._server = None


def send(url, body, kind):
    request = Request(url, data=body, method='POST', headers={'Content-Type': kind})
    with urlopen(request, timeout=10) as response:
        return response, response.read()


def test_http_single_and_clause_api_and_missing_sql_warning(http_server):
    response, data = send(http_server + '/api/analyze',
                          json.dumps({'input':'Nice design, but the battery is awful.'}).encode(),
                          'application/json')
    payload = json.loads(data)
    assert response.status == 200 and payload['code'] == 1
    assert payload['history_saved'] is False
    assert payload['sentence_analysis']['negative_parts'] == 1
    assert 'negative_rate' not in payload['sentence_analysis']
    response, data = send(http_server + '/api/sentences',
                          json.dumps({'input':'Nice design, but the battery is awful.'}).encode(),
                          'application/json')
    assert response.status == 200
    assert 'negative_rate' not in json.loads(data)
    with urlopen(http_server + '/api/health', timeout=10) as response:
        assert json.loads(response.read())['task'] == 'binary'
    with urlopen(http_server + '/', timeout=10) as response:
        html = response.read().decode('utf-8')
        assert 'sentence-breakdown-count' in html
        assert 'sentence-negative-rate' not in html


def test_http_csv_xlsx_and_export(http_server):
    raw = b'text,source\nNice design,A\nBad battery,B\n'
    response, data = send(http_server + '/api/columns?filename=sample.csv', raw, 'text/csv')
    assert response.status == 200
    assert json.loads(data)['suggested_column'] == 'text'
    response, exported = send(http_server + '/api/batch?column=text&filename=sample.csv', raw, 'text/csv')
    assert response.headers['X-Negative-Rows'] == '1'
    assert response.headers['X-Nonnegative-Rows'] == '1'
    assert response.headers['X-History-Saved'] == 'false'
    assert 'Nhãn dự đoán TextSense (0/1)' in exported.decode('utf-8-sig')
    response, xlsx = send(http_server + '/api/export-xlsx', exported, 'application/octet-stream')
    assert response.status == 200 and xlsx.startswith(b'PK')
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['text', 'source'])
    sheet.append(['Nice design', 'A'])
    sheet.append(['Bad battery', 'B'])
    buffer = io.BytesIO()
    workbook.save(buffer)
    response, data = send(http_server + '/api/columns?filename=sample.xlsx', buffer.getvalue(),
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    assert response.status == 200
    assert json.loads(data)['suggested_column'] == 'text'
    response, exported = send(http_server + '/api/batch?column=text&filename=sample.xlsx', buffer.getvalue(),
                              'application/octet-stream')
    assert response.headers['X-Total-Rows'] == '2'
    assert 'Bad battery' in exported.decode('utf-8-sig')


def test_frontend_contract_and_preserved_dual_pages():
    webdir = ROOT / '03_GIAO_DIEN/web'
    index = (webdir / 'index.html').read_text(encoding='utf-8')
    js = (webdir / 'app.js').read_text(encoding='utf-8')
    assert 'sentence-negative-rate' not in index + js
    assert 'negative_rate' not in index + js
    assert 'dash-negative-pct' in index + js
    assert 'sentence-breakdown-count' in index + js
    assert 'history-warning' in index + js
    assert 'result-confidence' in index + js
    assert 'result-disclaimer' in index + js
    assert (webdir / 'index.html').is_file()


def test_notebook_and_app_normalize_and_threshold_parity():
    import joblib
    import predict as app_predict

    nb_path = ROOT / '01_TRAIN_MODEL/TextSense_Notebook_SQLServer_Hoan_Thien_v3.ipynb'
    nb = json.loads(nb_path.read_text(encoding='utf-8'))
    nb_norm_src = ''.join(nb['cells'][6]['source'])
    ns = {'pd': __import__('pandas'), 're': __import__('re'), 'unicodedata': __import__('unicodedata'),
          'RETWEET_PREFIX_RE': app_predict.RETWEET_PREFIX_RE, 'URL_RE': app_predict.URL_RE}
    exec(nb_norm_src, ns)
    nb_normalize = ns['normalize_text']

    sample_sentences = [
        "RT @user: I wasn't happy with this terrible update! https://example.com",
        "Honestly, this phone isn't bad at all — works great!",
        "Worst service ever... complete waste of money.",
    ]
    for s in sample_sentences:
        assert nb_normalize(s) == app_predict.normalize_text(s)

    model_path = ROOT / '01_TRAIN_MODEL/outputs/binary_linear_svm.joblib'
    if model_path.is_file():
        artifact = joblib.load(model_path)
        app_results = app_predict.predict(model_path, sample_sentences)
        for s, app_res in zip(sample_sentences, app_results):
            cleaned = nb_normalize(s)
            nb_score = float(artifact['pipeline'].decision_function([cleaned])[0])
            nb_label = int(nb_score > float(artifact['threshold']))
            assert app_res['predicted_label'] == nb_label
            assert abs(app_res['decision_score'] - nb_score) < 1e-9


def test_database_prediction_write_with_mock_pyodbc(monkeypatch):
    import database

    class FakeCursor:
        def __init__(self):
            self.description = None
            self.statements = []
            self.inserted = []
        def execute(self, statement, args=()):
            self.statements.append((statement, args))
            return self
        def nextset(self):
            self.description = [('BatchID',)]
            return True
        def fetchone(self):
            return (42,)
        def executemany(self, statement, rows):
            self.inserted.extend(rows)
            return self

    class FakeConnection:
        def __init__(self):
            self.cursor_value = FakeCursor()
            self.committed = False
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def cursor(self):
            return self.cursor_value
        def commit(self):
            self.committed = True

    connection = FakeConnection()
    class FakePyodbc:
        @staticmethod
        def connect(string, timeout=None):
            assert 'TextSenseDB' in string
            return connection
    monkeypatch.setattr(database, 'sql_server_connection_string', lambda: 'DATABASE=TextSenseDB;')
    monkeypatch.setattr(database, '_get_pyodbc', lambda: FakePyodbc)
    result = [{'text':'Good design', 'predicted_label':0, 'label_name':'Không phát hiện nội dung tiêu cực', 'status':'ok'},
              {'text':'Bad battery', 'predicted_label':1, 'label_name':'Có nội dung tiêu cực', 'status':'ok'}]
    assert database.record_prediction_batch('binary', 'sample.csv', result, 50, b'fake') == 42
    assert connection.committed is True
    assert len(connection.cursor_value.inserted) == 2
    assert connection.cursor_value.inserted[0][0] == 42
    assert '[RowCount]' in connection.cursor_value.statements[0][0]


def test_user_feedback_write_with_mock_pyodbc(monkeypatch):
    import database

    class FakeCursor:
        def __init__(self):
            self.description = [('FeedbackID',)]
            self.statements = []
        def execute(self, statement, args=()):
            self.statements.append((statement, args))
            return self
        def nextset(self):
            return True
        def fetchone(self):
            return (101,)

    class FakeConnection:
        def __init__(self):
            self.cursor_value = FakeCursor()
            self.committed = False
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def cursor(self):
            return self.cursor_value
        def commit(self):
            self.committed = True

    connection = FakeConnection()
    class FakePyodbc:
        @staticmethod
        def connect(string, timeout=None):
            return connection
    monkeypatch.setattr(database, 'sql_server_connection_string', lambda: 'DATABASE=TextSenseDB;')
    monkeypatch.setattr(database, '_get_pyodbc', lambda: FakePyodbc)

    fid = database.record_user_feedback('Bình luận riêng lẻ', 'Không phát hiện nội dung tiêu cực', 'Có nội dung tiêu cực', 'Note', 'Sample text')
    assert fid == 101
    assert connection.committed is True
    assert 'dbo.UserFeedback' in connection.cursor_value.statements[0][0]


if __name__ == '__main__':
    class _MonkeyPatch:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    mp = _MonkeyPatch()
    stub = fake_model(mp)
    test_contrastive_clause_splitting_without_overfragmentation()
    test_classification_rule_any_negative_part_yields_negative(stub)
    test_classification_rule_no_negative_parts_and_whole_nonnegative(stub)
    test_no_negative_parts_hides_optional_explanation(stub)
    test_all_negative_parts_remain_available(stub)
    test_single_sentence_no_breakdown(stub)
    test_batch_percentages_still_describe_number_of_comments(stub)
    test_frontend_contract_and_preserved_dual_pages()
    test_notebook_and_app_normalize_and_threshold_parity()
    test_database_prediction_write_with_mock_pyodbc(mp)
    test_user_feedback_write_with_mock_pyodbc(mp)
    print("ALL TESTS PASSED!")
