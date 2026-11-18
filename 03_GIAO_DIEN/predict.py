"""Inference with a locally trained artifact; prediction never trains or auto-labels data."""
import argparse
from functools import lru_cache
from pathlib import Path
import re
import warnings
import unicodedata

import joblib
import pandas as pd
import sklearn

BINARY_NAMES = {0: 'Không phản cảm', 1: 'Phản cảm'}
OUTPUT = Path(__file__).resolve().parent.parent / '01_TRAIN_MODEL' / 'outputs'
RETWEET_PREFIX_RE = re.compile(r'^\s*rt\s+@[\w_]+\s*:?[ \t]*', flags=re.I)
URL_RE = re.compile(r'(?:https?://|www\.)\S+', flags=re.I)


def normalize_text(value) -> str:
    """Apply the same normalization to pre-cleaned training text and raw web input.

    Kaggle files contain pre-cleaned text (lowercase with punctuation removed). Mirror
    that representation at inference: NFKC, remove leading RT @handle, remove URLs,
    casefold, remove punctuation and collapse whitespace. Accented letters are kept.
    """
    if pd.isna(value):
        return ''
    value = unicodedata.normalize('NFKC', str(value))
    value = RETWEET_PREFIX_RE.sub(' ', value)
    value = URL_RE.sub(' ', value)
    value = value.casefold()
    value = re.sub(r'[^\w\s]', '', value, flags=re.UNICODE)
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
        raise ValueError('Artifact không đúng cấu trúc TextSense. Hãy train lại bằng do_an_textsense_v3.ipynb.')
    return artifact


def load_artifact(model_path):
    path = Path(model_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f'Không tìm thấy model: {path}. Hãy chạy do_an_textsense_v3.ipynb trước.')
    stat = path.stat()
    return _load_artifact_cached(str(path), stat.st_mtime_ns, stat.st_size)


def predict(model_path, texts, batch_size=512):
    artifact = load_artifact(model_path)  # Cached by file path, modification time and size.
    trained_version = artifact.get('sklearn_version')
    if trained_version and trained_version != sklearn.__version__:
        warnings.warn(
            f'Model trained with scikit-learn {trained_version}; current version is {sklearn.__version__}. '
            'If loading or inference fails, recreate the environment from requirements.txt and rerun do_an_textsense_v3.ipynb.',
            RuntimeWarning
        )
    if batch_size < 1:
        raise ValueError('batch_size must be a positive integer.')
    model = artifact['pipeline']
    raw_texts = [str(text) if text is not None else '' for text in texts]
    cleaned = [normalize_text(text) for text in raw_texts]
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
        texts_batch = [cleaned[i] for i in indices]
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
        parser.error(f'No model: {model_path}. Run do_an_textsense_v3.ipynb first.')
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
