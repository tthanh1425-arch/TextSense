"""Test E3 negation heuristic on 30 representative sentences (single, double, consecutive, political)."""
from __future__ import annotations

import sys
from pathlib import Path

TRAIN_DIR = Path(__file__).resolve().parents[2] / "01_TRAIN_MODEL"
sys.path.insert(0, str(TRAIN_DIR))
sys.path.insert(0, str(TRAIN_DIR / "scripts"))

from preprocessing_v4 import normalize_text  # noqa: E402
from negation_feature import add_negation_features  # noqa: E402

TEST_CASES = [
    ("1. Basic not + stopword skip", "this is not a good decision"),
    ("2. Contraction don't -> do not", "I don't like this policy"),
    ("3. Contraction can't -> can not", "They can't fix the economy"),
    ("4. Space-sep didn t -> did not", "government didn t help farmers"),
    ("5. Trigger 'no'", "There is no hope for reform"),
    ("6. Trigger 'never'", "Modi will never support corruption"),
    ("7. Trigger 'nobody'", "nobody trusts that minister anymore"),
    ("8. Trigger 'nothing'", "nothing good came from this law"),
    ("9. Trigger 'neither / nor'", "neither party nor leader cares"),
    ("10. Trigger 'without'", "passed the bill without any debate"),
    ("11. Double negation (not + never)", "not that he never tried"),
    ("12. Double negation (not + no)", "it is not true that there is no crisis"),
    ("13. Consecutive negation (not + without)", "not without serious problems"),
    ("14. Consecutive negation (never + nothing)", "never say nothing about failure"),
    ("15. Window limit = 3", "not very good economic policy today"),
    ("16. Stopwords inside window (the, of, to)", "not the end of democracy"),
    ("17. Stopwords (is, are, be, been)", "will not be a great success"),
    ("18. Stopwords (a, an, to)", "not an easy solution to implement"),
    ("19. Trigger at end of sentence", "they promised jobs but did not"),
    ("20. No negation trigger", "excellent leadership and strong growth"),
    ("21. Political: election", "voters did not support the ruling party"),
    ("22. Political: parliament", "opposition has no clear alternative"),
    ("23. Political: tax/budget", "budget is not fair to poor citizens"),
    ("24. Political: media/bias", "media is not reporting the truth"),
    ("25. Political: foreign policy", "without strong defense country suffers"),
    ("26. Political: unemployment", "youth have no jobs and no future"),
    ("27. Political: healthcare", "hospitals are not ready for crisis"),
    ("28. Political: corruption", "nobody is punished for the scam"),
    ("29. Political: positive with negation", "not bad at all actually impressive"),
    ("30. Empty string", ""),
]


def main() -> None:
    assert len(TEST_CASES) >= 30
    for label, raw in TEST_CASES:
        norm = normalize_text(raw)
        feat = add_negation_features(norm)
        # Ensure original normalized tokens are preserved as prefix
        if norm:
            assert feat.startswith(norm), f"Original tokens altered for {label}"
        # Ensure stopwords are never prefixed with not_
        for sw in ("not_a", "not_an", "not_the", "not_to", "not_of", "not_is", "not_are", "not_be", "not_been"):
            assert sw not in feat.split(), f"Stopword {sw} should not be prefixed in {label}: {feat}"
        added = feat[len(norm):].strip()
        print(f"{label} | NORM: {norm!r} | ADDED: {added!r}")
    print(f"\nALL {len(TEST_CASES)} E3 NEGATION TESTS PASSED!")


if __name__ == "__main__":
    main()
