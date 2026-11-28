"""Unified text preprocessing v4 (textsense_clean_v4) for TextSense.

Single source of truth for notebook, training scripts, and inference.
Handles NFKC normalization, HTML entities, RT prefixes, URLs, context-aware
English contractions (both apostrophe and space-separated forms), and
punctuation/whitespace normalization.
"""
from __future__ import annotations

import html
import re
import unicodedata

PREPROCESSING_VERSION = "textsense_clean_v4"

RETWEET_PREFIX_RE = re.compile(r"^\s*rt\s+@[\w_]+\s*:?[ \t]*", flags=re.I)
URL_RE = re.compile(r"(?:https?://|www\.)\S+", flags=re.I)

# Negative contractions: apostrophe ("don't"), space-separated ("don t"), and merged ("dont").
_NEG_STEMS = (
    ("aren", "are"),
    ("couldn", "could"),
    ("didn", "did"),
    ("doesn", "does"),
    ("don", "do"),
    ("hadn", "had"),
    ("hasn", "has"),
    ("haven", "have"),
    ("isn", "is"),
    ("mightn", "might"),
    ("mustn", "must"),
    ("needn", "need"),
    ("shouldn", "should"),
    ("wasn", "was"),
    ("weren", "were"),
    ("wouldn", "would"),
)

_CONTRACTIONS: dict[str, str] = {
    "aint": "is not",
    "ain't": "is not",
    "ain t": "is not",
    "cant": "can not",
    "can't": "can not",
    "can t": "can not",
    "cannot": "can not",
    "wont": "will not",
    "won't": "will not",
    "won t": "will not",
    "shant": "shall not",
    "shan't": "shall not",
    "shan t": "shall not",
}

for _stem, _base in _NEG_STEMS:
    _expanded = f"{_base} not"
    _CONTRACTIONS[f"{_stem}t"] = _expanded
    _CONTRACTIONS[f"{_stem}'t"] = _expanded
    _CONTRACTIONS[f"{_stem} t"] = _expanded

# Non-negative contractions (apostrophe and safe space-separated forms).
# Ambiguous bare words like "lets" (verb) or "im" (when not "i'm"/"i m") are NOT blindly expanded,
# except "i m" / "i'm" -> "i am" and "it s" / "it's" -> "it is" (handled with context below).
_OTHER_CONTRACTIONS: dict[str, str] = {
    "i'm": "i am",
    "i m": "i am",
    "you're": "you are",
    "you re": "you are",
    "we're": "we are",
    "we re": "we are",
    "they're": "they are",
    "they re": "they are",
    "i've": "i have",
    "i ve": "i have",
    "you've": "you have",
    "you ve": "you have",
    "we've": "we have",
    "we ve": "we have",
    "they've": "they have",
    "they ve": "they have",
    "i'll": "i will",
    "i ll": "i will",
    "you'll": "you will",
    "you ll": "you will",
    "he'll": "he will",
    "he ll": "he will",
    "she'll": "she will",
    "she ll": "she will",
    "it'll": "it will",
    "it ll": "it will",
    "we'll": "we will",
    "we ll": "we will",
    "they'll": "they will",
    "they ll": "they will",
    "let's": "let us",
    "let s": "let us",
    "who's": "who is",
    "what's": "what is",
    "where's": "where is",
    "here's": "here is",
    "there's": "there is",
    "that's": "that is",
    "he's": "he is",
    "she's": "she is",
}
_CONTRACTIONS.update(_OTHER_CONTRACTIONS)

# Context-aware "'s" / " s" for "it's" / "it s" / "that s" / "there s" / "he s" / "she s":
# Before "been" or "got", "'s" / " s" means "has"; otherwise "is".
_CONTEXT_HAS_RE = re.compile(
    r"\b(it|that|there|he|she)(?:'s|\s+s)\s+(been|got)\b",
    flags=re.IGNORECASE,
)
_CONTEXT_IS_RE = re.compile(
    r"\b(it|that|there|what|who|here|he|she)(?:'s|\s+s)\b",
    flags=re.IGNORECASE,
)

# Context-aware "'d" / " d": only expand "i'd", "you'd", "we'd", "they'd", "he'd", "she'd"
# with apostrophe, or space-separated "d" before common verbs/adverbs (avoiding "i d" = ID, "3 d", "vitamin d").
_APOSTROPHE_D_RE = re.compile(
    r"\b(i|you|we|they|he|she)'d\b",
    flags=re.IGNORECASE,
)
_SPACE_D_RE = re.compile(
    r"\b(i|you|we|they|he|she)\s+d\s+(like|love|hate|prefer|rather|better|be|have|go|say|think|never|not)\b",
    flags=re.IGNORECASE,
)

_CONTRACTIONS_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in sorted(_CONTRACTIONS, key=len, reverse=True)) + r")\b",
    flags=re.IGNORECASE,
)


def _is_na(value) -> bool:
    if value is None:
        return True
    try:
        # Handle float('nan') / numpy.nan / pandas.NA without requiring pandas import
        return value != value
    except Exception:
        return False


def normalize_text(value) -> str:
    """NFKC, HTML entities, RT/URL, context-aware contractions, lowercase, punctuation & spaces.

    Idempotent: normalize_text(normalize_text(x)) == normalize_text(x).
    """
    if _is_na(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = html.unescape(text)
    text = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    text = RETWEET_PREFIX_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = text.casefold()

    # Context-aware "'s" / " s" and "'d" / " d" before general contraction table
    text = _CONTEXT_HAS_RE.sub(lambda m: f"{m.group(1)} has {m.group(2)}", text)
    text = _CONTEXT_IS_RE.sub(lambda m: f"{m.group(1)} is", text)
    text = _APOSTROPHE_D_RE.sub(lambda m: f"{m.group(1)} would", text)
    text = _SPACE_D_RE.sub(lambda m: f"{m.group(1)} would {m.group(2)}", text)

    # Collapse multiple spaces before matching space-separated contractions
    text = " ".join(text.split())
    text = _CONTRACTIONS_RE.sub(lambda m: _CONTRACTIONS[m.group(0)], text)

    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = text.replace("_", " ")
    return " ".join(text.split())
