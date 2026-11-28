"""Inference with a locally trained artifact; prediction never trains or auto-labels data."""
import argparse
from functools import lru_cache
from pathlib import Path
import re
import sys
import warnings
import unicodedata

import joblib
import pandas as pd
import sklearn

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from preprocessing_v4 import normalize_text as normalize_text_v4  # noqa: E402
from scripts.negation_feature import add_negation_features  # noqa: E402

BINARY_NAMES = {0: 'Không phát hiện nội dung tiêu cực', 1: 'Có nội dung tiêu cực'}
OUTPUT = Path(__file__).resolve().parent.parent / '01_TRAIN_MODEL' / 'outputs'
RETWEET_PREFIX_RE = re.compile(r'^\s*rt\s+@[\w_]+\s*:?[ \t]*', flags=re.I)
URL_RE = re.compile(r'(?:https?://|www\.)\S+', flags=re.I)


# Chuẩn hóa phủ định trước khi xóa dấu câu; nguồn CSV có cả "wasnt" và "was not".
# Không tự gán nhãn bằng từ khóa: các đặc trưng này được HỌC từ dữ liệu gắn nhãn.
PREPROCESSING_VERSION = 'textsense_clean_v3_context'
_CONTRACTIONS = {
    'aint': 'is not', 'cant': 'can not', 'cannot': 'can not',
    'wont': 'will not', 'shant': 'shall not',
}
for _stem, _base in (
    ('aren', 'are'), ('couldn', 'could'), ('didn', 'did'),
    ('doesn', 'does'), ('don', 'do'), ('hadn', 'had'),
    ('hasn', 'has'), ('haven', 'have'), ('isn', 'is'),
    ('mightn', 'might'), ('mustn', 'must'), ('needn', 'need'),
    ('shouldn', 'should'), ('wasn', 'was'), ('weren', 'were'),
    ('wouldn', 'would'),
):
    _CONTRACTIONS[_stem + 't'] = _base + ' not'
# Chấp nhận cả kiểu có dấu nháy ("wasn't") và đã mất nháy ("wasnt").
_CONTRACTIONS.update({
    (word[:-1] + "'t"): expanded for word, expanded in list(_CONTRACTIONS.items())
    if word.endswith('nt') and word not in {'cannot'}
})
_CONTRACTIONS_RE = re.compile(
    r'\b(?:' + '|'.join(re.escape(t) for t in sorted(_CONTRACTIONS, key=len, reverse=True)) + r')\b',
    flags=re.IGNORECASE,
)


def normalize_text(value) -> str:
    """NFKC, RT/URL, contractions, lowercase, tách dấu câu và khoảng trắng.

    Idempotent: normalize_text(normalize_text(x)) == normalize_text(x).
    PHẢI đồng bộ chính xác giữa notebook và 03_GIAO_DIEN/predict.py.
    """
    if value is None or pd.isna(value):
        return ''
    value = unicodedata.normalize('NFKC', str(value)).replace('’', "'")
    value = RETWEET_PREFIX_RE.sub(' ', value)
    value = URL_RE.sub(' ', value)
    value = value.casefold()
    value = _CONTRACTIONS_RE.sub(lambda m: _CONTRACTIONS[m.group(0)], value)
    value = re.sub(r'[^\w\s]', ' ', value, flags=re.UNICODE)
    value = value.replace('_', ' ')
    return ' '.join(value.split())


VIETNAMESE_MARKS = set('àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ')
MAX_TEXT_CHARS = 2000
URL_PATTERN = re.compile(r'(?:https?://|www\.|(?:x|twitter)\.com/)\S+', flags=re.I)


def vietnamese_warning(value):
    letters = [c for c in str(value).lower() if c.isalpha()]
    return len(letters) > 0 and sum(c in VIETNAMESE_MARKS for c in letters) / len(letters) > 0.03


@lru_cache(maxsize=4)
def _load_artifact_cached(path_text, mtime_ns, file_size):
    artifact = joblib.load(path_text)
    if not isinstance(artifact, dict) or 'pipeline' not in artifact or 'class_names' not in artifact:
        raise ValueError('Artifact không đúng cấu trúc TextSense. Hãy train lại bằng TextSense_Notebook_SQLServer_Hoan_Thien_v2.ipynb.')
    return artifact


def load_artifact(model_path):
    path = Path(model_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f'Không tìm thấy model: {path}. Hãy chạy TextSense_Notebook_SQLServer_Hoan_Thien_v2.ipynb trước.')
    stat = path.stat()
    return _load_artifact_cached(str(path), stat.st_mtime_ns, stat.st_size)


def predict(model_path, texts, batch_size=512):
    artifact = load_artifact(model_path)  # Cached by file path, modification time and size.
    trained_version = artifact.get('sklearn_version')
    if trained_version and trained_version != sklearn.__version__:
        warnings.warn(
            f'Model trained with scikit-learn {trained_version}; current version is {sklearn.__version__}. '
            'If loading or inference fails, recreate the environment from requirements.txt and rerun TextSense_Notebook_SQLServer_Hoan_Thien_v2.ipynb.',
            RuntimeWarning
        )
    if batch_size < 1:
        raise ValueError('batch_size must be a positive integer.')
    prep_ver = artifact.get('preprocessing_version')
    exp_id = artifact.get('experiment_id')
    use_v4 = bool(prep_ver and prep_ver.startswith('textsense_clean_v4'))
    use_negation = exp_id in {'E3', 'E5a', 'E5b'} or bool(prep_ver and 'negation' in prep_ver)
    if prep_ver and prep_ver not in {PREPROCESSING_VERSION, 'textsense_clean_v4', 'textsense_clean_v4+negation_window3'}:
        warnings.warn(
            f'Model preprocessing version ({prep_ver}) does not match current ({PREPROCESSING_VERSION}).',
            RuntimeWarning
        )
    model = artifact['pipeline']
    raw_texts = [str(text) if text is not None else '' for text in texts]
    clean_fn = normalize_text_v4 if use_v4 else normalize_text
    cleaned = [clean_fn(text) for text in raw_texts]
    model_inputs = [add_negation_features(c) for c in cleaned] if use_negation else cleaned
    statuses = []
    eligible = []
    for index, value in enumerate(cleaned):
        raw_value = raw_texts[index].strip()
        if URL_PATTERN.fullmatch(raw_value):
            statuses.append('Đây là đường dẫn, không phải nội dung bình luận')
        elif not value:
            statuses.append('Văn bản rỗng')
        elif len(value) > MAX_TEXT_CHARS:
            statuses.append(f'Vượt quá {MAX_TEXT_CHARS:,} ký tự')
        elif vietnamese_warning(value):
            statuses.append('Văn bản có dấu tiếng Việt; mô hình được huấn luyện trên dữ liệu tiếng Anh, không trả nhãn.')
        else:
            statuses.append('ok')
            eligible.append(index)

    predictions = {}
    scores = {}
    for start in range(0, len(eligible), batch_size):
        indices = eligible[start:start + batch_size]
        texts_batch = [model_inputs[i] for i in indices]
        if artifact.get('task') == 'binary':
            decision_scores = model.decision_function(texts_batch)
            threshold = float(artifact.get('threshold', 0.0))
            codes = (decision_scores > threshold).astype(int)
            for index, code, score in zip(indices, codes, decision_scores):
                predictions[index] = int(code)
                scores[index] = float(score)
        else:
            codes = model.predict(texts_batch)
            for index, code in zip(indices, codes):
                predictions[index] = int(code)

    results = []
    for index, original in enumerate(texts):
        if statuses[index] != 'ok':
            results.append({
                'text': original, 'predicted_label': None, 'label_name': None,
                'task': artifact['task'], 'decision_score': None, 'status': statuses[index]
            })
            continue
        code = predictions[index]
        row = {
            'text': original, 'predicted_label': code,
            'label_name': (BINARY_NAMES[code] if artifact['task'] == 'binary'
                           else artifact['class_names'][code]),
            'task': artifact['task'], 'status': 'ok'
        }
        if index in scores:
            row['decision_score'] = scores[index]
            row['decision_threshold'] = float(artifact.get('threshold', 0.0))
        results.append(row)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=['binary'], default='binary')
    parser.add_argument('--text')
    parser.add_argument('--csv', type=Path)
    parser.add_argument('--column', default='text')
    parser.add_argument('--out', type=Path, default=OUTPUT / 'inference.csv')
    args = parser.parse_args()
    if (args.text is None) == (args.csv is None):
        parser.error('Specify exactly one of --text or --csv')
    model_path = OUTPUT / f'{args.task}_linear_svm.joblib'
    if not model_path.exists():
        parser.error(f'No model: {model_path}. Run TextSense_Notebook_SQLServer_Hoan_Thien_v2.ipynb first.')
    if args.csv:
        frame = pd.read_csv(args.csv)
        if args.column not in frame:
            parser.error(f'Missing column {args.column}')
        texts = frame[args.column].fillna('').astype(str).tolist()
    else:
        texts = [args.text]
    result = predict(model_path, texts)
    if args.csv:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(result).to_csv(args.out, index=False, encoding='utf-8-sig')
        print(f'Saved to {args.out}')
    else:
        print(result[0])


if __name__ == '__main__':
    main()
