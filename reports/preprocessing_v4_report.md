# BÁO CÁO CHUẨN HÓA TIỀN XỬ LÝ V4 (`textsense_clean_v4`)

**Ngày thực hiện:** 2026-11-27  
**Module thống nhất:** [preprocessing_v4.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/preprocessing_v4.py)  
**Script kiểm thử & kiểm toán trùng lặp:** [phase2_verify_v4.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/scripts/phase2_verify_v4.py)  
**Manifest dữ liệu:** [data_manifest.json](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/data/sampled/data_manifest.json)

*(Ghi chú: `03_GIAO_DIEN/predict.py` và `baseline_v3/` chưa bị thay đổi trong Giai đoạn 2 theo đúng quy định; chỉ tích hợp `predict.py` sau khi mô hình được chọn ở Giai đoạn 7.)*

---

## 1. Thiết kế `PREPROCESSING_VERSION = 'textsense_clean_v4'`

Hàm `normalize_text(value)` trong [preprocessing_v4.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/preprocessing_v4.py) thực hiện tuần tự:
1. Chuẩn hóa Unicode `NFKC` và giải mã HTML entities (`html.unescape`: `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#39;`, ...).
2. Chuẩn hóa dấu nháy cong (`’`, `‘`, `` ` `` → `'`), loại bỏ tiền tố `RT @user:` và URL (`http://`, `https://`, `www.`), chuyển về chữ thường (`casefold()`).
3. **Mở rộng từ viết tắt có kiểm tra ngữ cảnh:**
   - Hỗ trợ cả 3 biến thể: có dấu nháy (`don't`, `can't`, `didn't`, `isn't`, `i'm`, `it's`), dấu nháy bị tách khoảng trắng (`don t`, `doesn t`, `didn t`, `can t`, `isn t`, `i m`, `it s`, `you re`, `we ll`, `let s`, ...) và dạng mất dấu nháy đã có ở v3 (`dont`, `cant`, `wont`).
   - **Kiểm tra ngữ cảnh `'s` / ` s`:** Trước `been` hoặc `got` (`it's been`, `it s got`, `that s been`, `he s got`, ...) mở rộng thành `has`; các trường hợp đại từ + `'s` / ` s` còn lại (`it's`, `it s`, `that's`, `there's`, `what's`, `who's`, `here's`, `he's`, `she's`) mở rộng thành `is`. **Không** mở rộng sở hữu cách danh từ (`Modi s government`, `India's economy` giữ nguyên `s`).
   - **Kiểm tra ngữ cảnh `let's` / `let s` vs `lets`:** `let's` và `let s` → `let us`; động từ `lets` (`he lets them win`) được giữ nguyên.
   - **Kiểm tra ngữ cảnh `'d` / ` d`:** `i'd`, `you'd`, ... (có dấu nháy) → `<pronoun> would`; dạng tách khoảng trắng `i d` chỉ mở rộng khi đứng trước động từ/trạng từ chỉ ý định (`like`, `love`, `hate`, `prefer`, `rather`, `better`, `be`, `have`, `go`, `say`, `think`, `never`, `not`), tránh thay nhầm `i d card` (ID).
4. Loại dấu câu (`[^\w\s]`), thay `_` bằng khoảng trắng, gộp khoảng trắng thừa. Hàm bảo đảm tính lũy đẳng `normalize_text(normalize_text(x)) == normalize_text(x)`.

---

## 2. Kết quả kiểm thử 30 câu đại diện

Toàn bộ **30/30 câu** đạt kiểm tra ngữ nghĩa và tính lũy đẳng (`idem = True`):

| # | Nhóm kiểm thử | Văn bản gốc | Văn bản sau chuẩn hóa v4 | Quy tắc / Giải thích |
|---:|---|---|---|---|
| 1 | Viết tắt chuẩn | `I don't think this policy works.` | `i do not think this policy works` | Mở rộng `don't` → `do not` |
| 2 | Dấu nháy tách khoảng trắng | `i don t think this policy works` | `i do not think this policy works` | Mở rộng `don t` → `do not` |
| 3 | `doesn't` / `doesn t` | `He doesn't care and she doesn t either.` | `he does not care and she does not either` | Đồng nhất `doesn't` & `doesn t` → `does not` |
| 4 | `didn't` / `didn t` | `They didn't vote; we didn t know.` | `they did not vote we did not know` | Đồng nhất `didn't` & `didn t` → `did not` |
| 5 | `can't` / `can t` / `cannot` | `I can't believe he can t and cannot fix it.` | `i can not believe he can not and can not fix it` | Đồng nhất 3 dạng → `can not` |
| 6 | `isn't` / `isn t` | `This isn't fair, it isn t right.` | `this is not fair it is not right` | Đồng nhất `isn't` & `isn t` → `is not` |
| 7 | `won't` / `wouldn t` | `They won't listen and wouldn t help.` | `they will not listen and would not help` | `won't` → `will not`, `wouldn t` → `would not` |
| 8 | `wasn't` / `weren t` | `He wasn't there; they weren t ready.` | `he was not there they were not ready` | `wasn't` → `was not`, `weren t` → `were not` |
| 9 | Phủ định hoàn thành | `We haven't seen it, she hasn t called, he hadn t left.` | `we have not seen it she has not called he had not left` | Mở rộng `haven't`, `hasn t`, `hadn t` |
| 10 | `shouldn't` / `couldn t` | `You shouldn't lie; we couldn t stop it.` | `you should not lie we could not stop it` | Mở rộng `shouldn't`, `couldn t` |
| 11 | `ain't` / `ain t` | `That ain't true and it ain t fair.` | `that is not true and it is not fair` | Mở rộng `ain't`, `ain t` → `is not` |
| 12 | `I'm` / `i m` | `I'm tired and i m angry about this.` | `i am tired and i am angry about this` | Mở rộng `i'm` & `i m` → `i am` |
| 13 | `It's` / `it s` (`is`) | `It's a disaster and it s getting worse.` | `it is a disaster and it is getting worse` | Mở rộng `it's` & `it s` → `it is` |
| 14 | `It's been` / `it s got` | `It's been a terrible week; it s got worse.` | `it has been a terrible week it has got worse` | Ngữ cảnh trước `been`/`got` → `has` |
| 15 | `That's` / `there s` | `That's wrong, there s no hope.` | `that is wrong there is no hope` | Mở rộng `that's`, `there s` → `is` |
| 16 | `You're` / `they re` / `we re` | `You're wrong, they re lying, we re tired.` | `you are wrong they are lying we are tired` | Mở rộng `...re` → `... are` |
| 17 | `I've` / `we ll` | `I've tried, we ll see what happens.` | `i have tried we will see what happens` | Mở rộng `i've` → `i have`, `we ll` → `we will` |
| 18 | `Let's` vs `lets` | `Let's go now; he lets them win.` | `let us go now he lets them win` | `let's` → `let us`; giữ nguyên động từ `lets` |
| 19 | Sở hữu cách `s` | `Modi s government and India's economy.` | `modi s government and india s economy` | Không thay nhầm sở hữu cách thành `is` |
| 20 | `I'd` / `i d` vs `i d card` | `I'd love to help; i d rather stay; check my i d card.` | `i would love to help i would rather stay check my i d card` | Ngữ cảnh `i d` + động từ → `i would`; giữ `i d card` |
| 21 | HTML entities | `News &amp; politics &lt;bad&gt; &quot;quote&quot; don&#39;t lie.` | `news politics bad quote do not lie` | Giải mã `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#39;` trước khi xử lý viết tắt |
| 22 | Tiền tố RT & URL | `RT @user123: Terrible speech! https://t.co/abc123` | `terrible speech` | Loại bỏ `RT @user:` và URL |
| 23 | Nháy cong & NFKC | `It’s awful — don’t trust Ｔｈｉｓ!` | `it is awful do not trust this` | Chuẩn hóa NFKC và `’` → `'` |
| 24 | Dấu câu & `_` | `bad_policy!!! really?? ...awful...` | `bad policy really awful` | Tách `_` và bỏ dấu câu |
| 25 | Rỗng / khoảng trắng | `   \t\n  ` | `` | Trả về chuỗi rỗng |
| 26 | Chỉ dấu câu | `!!! ??? --- ...` | `` | Trả về chuỗi rỗng |
| 27 | Emoji & Hinglish | `Modi ji kya kar rahe ho 😡 #fail` | `modi ji kya kar rahe ho fail` | Giữ nguyên token chữ cái, bỏ emoji/dấu `#` |
| 28 | Giữ từ phủ định | `Not good at all, never support this.` | `not good at all never support this` | Bảo toàn `not`, `never` |
| 29 | `wont` (không nháy) | `wont complain` | `will not complain` | Nhất quán với v3 |
| 30 | Lũy đẳng (`idem`) | `I'm sure it's been bad, don t lie &amp; wait.` | `i am sure it has been bad do not lie wait` | `normalize(normalize(x)) == normalize(x)` |

---

## 3. Kiểm tra trùng lặp và rò rỉ sau chuẩn hóa v4

Khi chạy thử v4 trên bản lấy mẫu sơ bộ trước đó, phát hiện một số cặp trùng mới phát sinh do hợp nhất biến thể (ví dụ `i m` và `i am` cùng chuẩn hóa về `i am`). Vì pool sạch Sentiment140 có tới `1.513.897` dòng, toàn bộ quy trình lọc trùng, loại mâu thuẫn nhãn và lấy mẫu `520.000` dòng trong [phase1_data_prep.py](file:///c:/Users/vothi/OneDrive/Desktop/TextSense/scripts/phase1_data_prep.py) đã được cập nhật để **dùng trực tiếp khóa chuẩn hóa `textsense_clean_v4` trước khi lấy mẫu**.

### 3.1. Số liệu làm sạch Sentiment140 theo chuẩn `textsense_clean_v4`
- Dữ liệu thô `sentiment140_train.csv`: `1.523.975`
- Loại khóa rỗng (`len == 0`): `114`; loại `< 3` ký tự: `122` → còn `1.523.739`
- Loại nhóm mâu thuẫn nhãn (`4.135` nhóm): `8.493` dòng (tăng `211` dòng so với khóa cơ bản do hợp nhất biến thể viết tắt)
- Loại trùng nội bộ (`keep='first'`): `1.082` dòng (tăng `957` dòng so với khóa cơ bản)
- Loại trùng `T1` (`test.csv`): `52` dòng; loại trùng `Train+Val` chính trị: `208` dòng; loại trùng `sentiment140_test.csv`: `7` dòng
- **Pool sạch còn lại:** **`1.513.897` dòng** (`761.963` Tiêu cực `1`, `751.934` Không tiêu cực `0`) — **vẫn lấy đủ `400.000` Train + `60.000` Val + `60.000` Test `T2`**.

### 3.2. Kết quả kiểm toán sau chuẩn hóa v4 trên từng tập

| Tập dữ liệu | Số dòng | Rỗng sau v4 | `< 3` ký tự | Trùng nội bộ | Nhóm mâu thuẫn nhãn |
|---|---:|---:|---:|---:|---:|
| Political `Train` (`baseline_v3`) | `133.314` | `0` | `0` | `0` | `0` |
| Political `Validation` (`baseline_v3`) | `23.526` | `0` | `0` | `0` | `0` |
| Political `Test T1` (`baseline_v3`) | `39.210` | `0` | `0` | `0` | `0` |
| Sentiment140 `Train` (`400k`) | `400.000` | `0` | `0` | `0` | `0` |
| Sentiment140 `Validation` (`60k`) | `60.000` | `0` | `0` | `0` | `0` |
| Sentiment140 `Test T2` (`60k`) | `60.000` | `0` | `0` | `0` | `0` |
| Sentiment140 `test_data.csv` (`T2a`) | `359` | `0` | `0` | `0` | `0` |

### 3.3. Kiểm tra trùng lặp chéo giữa các tập sau chuẩn hóa v4
- `pol_train` ↔ `T1`: **`0`** | `pol_val` ↔ `T1`: **`0`** | `pol_train` ↔ `pol_val`: **`0`**
- `s140_train_400k` ↔ `T1`: **`0`** | `s140_val_60k` ↔ `T1`: **`0`** | `T2_60k` ↔ `T1`: **`0`**
- `s140_train_400k` ↔ `pol_train`: **`0`** | `s140_train_400k` ↔ `pol_val`: **`0`**
- `s140_train_400k` ↔ `s140_val_60k`: **`0`** | `s140_train_400k` ↔ `T2_60k`: **`0`** | `s140_val_60k` ↔ `T2_60k`: **`0`**
- `s140_train_400k` ↔ `T2a_359`: **`0`**
