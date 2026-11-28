"""Phase 2: Verify preprocessing_v4 on 30 representative sentences and run post-v4 duplicate/leakage audit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from preprocessing_v4 import PREPROCESSING_VERSION, normalize_text  # noqa: E402

SAMPLES = [
    ("1. Contraction standard", "I don't think this policy works.", "Chuẩn hóa don't -> do not"),
    ("2. Contraction space-sep", "i don t think this policy works", "Xử lý dấu nháy bị tách khoảng trắng don t -> do not"),
    ("3. Doesn't / doesn t", "He doesn't care and she doesn t either.", "Xử lý cả doesn't và doesn t -> does not"),
    ("4. Didn't / didn t", "They didn't vote; we didn t know.", "Xử lý cả didn't và didn t -> did not"),
    ("5. Can't / can t / cannot", "I can't believe he can t and cannot fix it.", "Chuẩn hóa can't, can t, cannot -> can not"),
    ("6. Isn't / isn t", "This isn't fair, it isn t right.", "Xử lý isn't và isn t -> is not"),
    ("7. Won't / wouldn t", "They won't listen and wouldn t help.", "Chuẩn hóa won't -> will not, wouldn t -> would not"),
    ("8. Wasn't / weren t", "He wasn't there; they weren t ready.", "Chuẩn hóa wasn't -> was not, weren t -> were not"),
    ("9. Haven't / hasn t / hadn t", "We haven't seen it, she hasn t called, he hadn t left.", "Chuẩn hóa các dạng phủ định hoàn thành"),
    ("10. Shouldn't / couldn t", "You shouldn't lie; we couldn t stop it.", "Chuẩn hóa shouldn't -> should not, couldn t -> could not"),
    ("11. Ain't / ain t", "That ain't true and it ain t fair.", "Chuẩn hóa ain't / ain t -> is not"),
    ("12. I'm / i m", "I'm tired and i m angry about this.", "Chuẩn hóa i'm và i m -> i am"),
    ("13. It's / it s (is)", "It's a disaster and it s getting worse.", "Chuẩn hóa it's và it s -> it is"),
    ("14. It's been / it s got (context)", "It's been a terrible week; it s got worse.", "Ngữ cảnh trước been/got: 's / s -> has"),
    ("15. That's / there s", "That's wrong, there s no hope.", "Chuẩn hóa that's -> that is, there s -> there is"),
    ("16. You're / they re / we re", "You're wrong, they re lying, we re tired.", "Chuẩn hóa you're/they re/we re -> are"),
    ("17. I've / we ll", "I've tried, we ll see what happens.", "Chuẩn hóa i've -> i have, we ll -> we will"),
    ("18. Let's vs lets (context)", "Let's go now; he lets them win.", "Phân biệt let's -> let us; giữ nguyên động từ lets"),
    ("19. Possessive s (no false expand)", "Modi s government and India's economy.", "Không thay nhầm sở hữu cách Modi s / India's thành is"),
    ("20. I'd / i d vs i d card (context)", "I'd love to help; i d rather stay; check my i d card.", "Phân biệt i'd/i d + động từ -> i would; giữ nguyên i d card"),
    ("21. HTML entities", "News &amp; politics &lt;bad&gt; &quot;quote&quot; don&#39;t lie.", "Giải mã HTML entity (&amp;, &lt;, &gt;, &quot;, &#39;) trước khi tách dấu"),
    ("22. RT prefix & URL", "RT @user123: Terrible speech! https://t.co/abc123", "Loại tiền tố RT @user và URL"),
    ("23. Curly apostrophe & NFKC", "It’s awful — don’t trust Ｔｈｉｓ!", "Chuẩn hóa NFKC và dấu nháy cong ’ -> ' trước khi tách viết tắt"),
    ("24. Punctuation & underscore", "bad_policy!!! really?? ...awful...", "Loại dấu câu và dấu gạch dưới _"),
    ("25. Empty / whitespace", "   \t\n  ", "Chuỗi chỉ khoảng trắng -> chuỗi rỗng"),
    ("26. Only punctuation", "!!! ??? --- ...", "Chuỗi chỉ dấu câu -> chuỗi rỗng"),
    ("27. Emoji & Hinglish", "Modi ji kya kar rahe ho 😡 #fail", "Loại emoji/hashtag, giữ nguyên token chữ cái"),
    ("28. Negation preserved", "Not good at all, never support this.", "Giữ nguyên từ phủ định not, never"),
    ("29. Wont (no apostrophe)", "wont complain", "Chuẩn hóa wont -> will not (nhất quán v3)"),
    ("30. Idempotency", "I'm sure it's been bad, don t lie &amp; wait.", "Kiểm tra tính lũy đẳng normalize(normalize(x)) == normalize(x)"),
]


def main() -> None:
    print(f"PREPROCESSING_VERSION = {PREPROCESSING_VERSION}")
    print("\n=== 30 REPRESENTATIVE SENTENCES ===")
    all_idem = True
    for name, raw, rule in SAMPLES:
        out = normalize_text(raw)
        idem = normalize_text(out) == out
        all_idem = all_idem and idem
        print(f"{name} | idem={idem} | {raw!r} => {out!r}")
    assert all_idem, "Idempotency check failed!"

    # Load all datasets and normalize with v4
    pol_train = pd.read_csv(ROOT / "baseline_v3" / "splits" / "binary" / "train.csv")
    pol_val = pd.read_csv(ROOT / "baseline_v3" / "splits" / "binary" / "validation.csv")
    pol_test = pd.read_csv(ROOT / "baseline_v3" / "splits" / "binary" / "test.csv")  # T1

    s_train = pd.read_csv(ROOT / "data" / "sampled" / "sentiment140_train_400k.csv")
    s_val = pd.read_csv(ROOT / "data" / "sampled" / "sentiment140_val_60k.csv")
    s_test = pd.read_csv(ROOT / "data" / "sampled" / "sentiment140_test_60k.csv")  # T2
    s_t2a = pd.read_csv(ROOT / "data" / "raw" / "sentiment140_test.csv")

    sets = {
        "pol_train": (pol_train, "text", "label"),
        "pol_val": (pol_val, "text", "label"),
        "T1": (pol_test, "text", "label"),
        "s140_train_400k": (s_train, "text", "label"),
        "s140_val_60k": (s_val, "text", "label"),
        "T2_60k": (s_test, "text", "label"),
        "T2a_359": (s_t2a, "sentence", "sentiment"),
    }

    norm_sets = {}
    stats = {}
    for name, (df, tcol, lcol) in sets.items():
        v4 = df[tcol].map(normalize_text)
        empty_cnt = int((v4.str.len() == 0).sum())
        lt3_cnt = int(((v4.str.len() > 0) & (v4.str.len() < 3)).sum())
        dup_cnt = int(v4.duplicated().sum())
        # Check label conflicts after v4
        tmp = pd.DataFrame({"k": v4, "y": df[lcol]})
        grp = tmp.groupby("k")["y"].nunique()
        conflict_groups = int((grp > 1).sum())
        stats[name] = {
            "rows": len(df),
            "empty_after_v4": empty_cnt,
            "lt3_after_v4": lt3_cnt,
            "internal_dups_after_v4": dup_cnt,
            "conflict_label_groups_after_v4": conflict_groups,
        }
        norm_sets[name] = set(v4) - {""}

    # Cross-set overlaps after v4
    overlaps = {
        "pol_train_vs_T1": len(norm_sets["pol_train"] & norm_sets["T1"]),
        "pol_val_vs_T1": len(norm_sets["pol_val"] & norm_sets["T1"]),
        "pol_train_vs_pol_val": len(norm_sets["pol_train"] & norm_sets["pol_val"]),
        "s140_train_vs_T1": len(norm_sets["s140_train_400k"] & norm_sets["T1"]),
        "s140_val_vs_T1": len(norm_sets["s140_val_60k"] & norm_sets["T1"]),
        "T2_vs_T1": len(norm_sets["T2_60k"] & norm_sets["T1"]),
        "s140_train_vs_pol_train": len(norm_sets["s140_train_400k"] & norm_sets["pol_train"]),
        "s140_train_vs_pol_val": len(norm_sets["s140_train_400k"] & norm_sets["pol_val"]),
        "s140_train_vs_s140_val": len(norm_sets["s140_train_400k"] & norm_sets["s140_val_60k"]),
        "s140_train_vs_T2": len(norm_sets["s140_train_400k"] & norm_sets["T2_60k"]),
        "s140_val_vs_T2": len(norm_sets["s140_val_60k"] & norm_sets["T2_60k"]),
        "s140_train_vs_T2a": len(norm_sets["s140_train_400k"] & norm_sets["T2a_359"]),
    }

    print("\n=== POST-V4 DATASET STATS ===")
    print(json.dumps(stats, indent=2))
    print("\n=== POST-V4 CROSS-SET OVERLAPS ===")
    print(json.dumps(overlaps, indent=2))


if __name__ == "__main__":
    main()
