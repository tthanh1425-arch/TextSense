"""E3 heuristic negation feature generator for TextSense V4.

This is a lightweight lexical heuristic (not a syntactic/semantic negation scope parser).
It preserves all original tokens and appends `not_<token>` features for up to 3 tokens
following a negation trigger, skipping function/stop words.
"""
from __future__ import annotations

NEGATION_TRIGGERS = frozenset({
    "not", "no", "never", "nobody", "nothing", "neither", "nor", "without",
})

NEGATION_STOPWORDS = frozenset({
    "a", "an", "the", "to", "of", "in", "on", "at", "by", "for", "with", "from", "as",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "that", "this", "these", "those", "it", "its",
    "and", "or", "but", "if", "so", "than", "then",
})


def add_negation_features(normalized_text: str, window: int = 3) -> str:
    """Append `not_<token>` heuristic features to an already v4-normalized text."""
    if not normalized_text:
        return ""
    tokens = normalized_text.split()
    extra: list[str] = []
    remaining = 0
    for tok in tokens:
        if tok in NEGATION_TRIGGERS:
            remaining = window
            continue
        if remaining > 0:
            if tok not in NEGATION_STOPWORDS:
                extra.append(f"not_{tok}")
            remaining -= 1
    if not extra:
        return normalized_text
    return normalized_text + " " + " ".join(extra)
