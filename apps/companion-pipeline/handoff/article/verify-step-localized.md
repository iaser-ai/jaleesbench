# Verify-step package — ar / ur / id

Produced from the **literal published EN strings** (`tmp/verify-step-en-shipped.md`,
iaser.ai d631601/7370c20), verified byte-identical to the text relayed by the
architect before translating. Three strings per language, because ar/ur/id still
carry the **old** versions of strings 2 and 3.

Bold lead-ins mirror what `**The path**` / `**The paste**` actually became in each
published article — read off the live pages, not invented:

| EN | ar | ur | id |
|---|---|---|---|
| **The path**: | **المسار**: | **راستہ**: | **Jalurnya**: |
| **The paste**: | **اللصق**: | **چسپاں کرنا**: | **Menempelnya**: |
| **The check**: | **التحقّق**: | **تصدیق**: | **Pemeriksaannya**: |

Product nouns also taken from each live article, not re-coined:
"Your instructions for Gemini" → «تعليماتك لـ Gemini» / «Gemini کے لیے آپ کی ہدایات» /
"Petunjuk Anda untuk Gemini"; Personal Intelligence → الذكاء الشخصي / ذاتی ذہانت /
Kecerdasan Pribadi. The ar page title was independently confirmed against the live
Gemini UI during the saved-info probes — it matches.

---

## 1. NEW — **The check**, after the walkthrough GIF, before "Why two parts?"

### ar
**التحقّق**: يعيد Gemini أحيانًا كتابة المدخلات المحفوظة أو يرفضها. بعد كل لصق، انظر إلى القائمة في صفحة «تعليماتك لـ Gemini» نفسها، وتأكّد أن المدخل المحفوظ يطابق ما لصقته حرفًا بحرف. فإن تغيّر أو لم يظهر، فاحذفه والصقه من جديد. وإن ظهرت لك رسالة خطأ، فتحقّق من القائمة أولًا على كل حال — فقد يكون المدخل حُفظ فعلًا، وإعادة اللصق تُنشئ مدخلًا مكرّرًا.

### ur
**تصدیق**: Gemini کبھی محفوظ اندراجات کو دوبارہ لکھ دیتا ہے یا رد کر دیتا ہے۔ ہر بار چسپاں کرنے کے بعد اُسی «Gemini کے لیے آپ کی ہدایات» والے صفحے کی فہرست دیکھیں، اور تصدیق کریں کہ محفوظ اندراج لفظ بہ لفظ وہی ہے جو آپ نے چسپاں کیا تھا۔ اگر وہ بدل گیا ہو یا موجود نہ ہو تو اسے حذف کر کے دوبارہ چسپاں کریں۔ اور اگر خرابی کا پیغام نظر آیا ہو تب بھی پہلے فہرست دیکھ لیں — ممکن ہے اندراج بہرحال محفوظ ہو چکا ہو، اور دوبارہ چسپاں کرنے سے دہرا اندراج بن جائے گا۔

### id
**Pemeriksaannya**: Gemini kadang menulis ulang atau menolak entri yang disimpan. Setelah setiap kali menempel, lihat daftar di halaman "Petunjuk Anda untuk Gemini" yang sama dan pastikan entri yang tersimpan sama persis, kata per kata, dengan yang Anda tempel. Jika berubah atau hilang, hapus lalu tempel ulang. Dan jika Anda melihat pesan galat, tetap periksa daftarnya lebih dulu — entrinya mungkin sudah tersimpan, dan menempel ulang akan membuat duplikat.

---

## 2. REWORKED — "Why two parts?"

Replaces the current localized paragraph, whose tail claims Gemini stores a close
paraphrase and that "the substance stays intact". That claim is false and is the
reason this string is changing; it is removed in all three.

### ar
**لماذا جزآن؟** في اختباراتنا، يفشل حاليًا لصق الموجِّه كاملًا كمدخل واحد في Gemini، وتظهر رسالة الخطأ العامة «Something went wrong». وليس السبب في المحتوى: فكل جزء يُحفظ وحده بنجاح، وكذلك يُحفظ نصٌّ محايد بالطول الإجمالي نفسه. يعالج Gemini كل مدخل عند حفظه، ويبدو أن الموجِّه الكامل يُثقل هذه الخطوة، بينما يُحفظ المدخلان الأقصر بثبات أكبر بكثير. وهذه المعالجة نفسها هي سبب أهمية التحقّق أعلاه: فخلافًا لـ ChatGPT وClaude اللذين يخزّنان نصّك حرفيًا، يحفظ Gemini أحيانًا صيغة معادًا كتابتها بدلًا منه — وإعادة الكتابة قد تغيّر في صمت مَن تتحدث عنه التعليمات، وهذا يُبطل مقصود الموجِّه. والحفظ الحرفي يحدث فعلًا؛ وقد لا يحتاج الأمر إلا إلى إعادة المحاولة.

وملاحظة خاصة بالعربية: لاحظنا أن Gemini قد يعيد كتابة مدخل عربي بالإنجليزية إذا بدأ المدخل بقائمة نقاط مباشرة؛ ولهذا صُغْنا الجزء الثاني بحيث يفتتح بجملتين تمهيديتين بالعربية.

### ur
**دو حصے کیوں؟** ہمارے تجربات میں پورا پرامپٹ ایک اندراج کے طور پر چسپاں کرنا Gemini میں فی الحال ناکام ہو جاتا ہے، اور عمومی خرابی کا پیغام "Something went wrong" ظاہر ہوتا ہے۔ سبب مواد نہیں: ہر حصہ اکیلے کامیابی سے محفوظ ہوتا ہے، اور اتنی ہی مجموعی لمبائی کا غیر جانب دار متن بھی محفوظ ہو جاتا ہے۔ Gemini ہر اندراج کو محفوظ کرتے وقت پروسیس کرتا ہے، اور لگتا ہے کہ پورا پرامپٹ اس مرحلے پر بوجھ بن جاتا ہے، جب کہ دو مختصر اندراجات کہیں زیادہ قابلِ اعتماد طریقے سے محفوظ ہوتے ہیں۔ یہی مرحلہ اوپر دی گئی تصدیق کی اہمیت کا سبب بھی ہے: ChatGPT اور Claude آپ کا لفظ بہ لفظ متن رکھتے ہیں، جب کہ Gemini کبھی اس کے بجائے دوبارہ لکھی گئی صورت محفوظ کر دیتا ہے — اور یہ دوبارہ لکھائی خاموشی سے یہ بدل سکتی ہے کہ ہدایات کس کے بارے میں ہیں، جو پرامپٹ کا مقصد ہی ختم کر دیتا ہے۔ اندراج کبھی لفظ بہ لفظ محفوظ بھی ہو جاتا ہے؛ شاید صرف دوبارہ کوشش کی ضرورت ہو۔

### id
**Mengapa dua bagian?** Dalam pengujian kami, menempel prompt utuh sebagai satu entri Gemini saat ini gagal dengan galat umum "Something went wrong". Penyebabnya bukan isinya: tiap bagian tersimpan baik-baik saja sendiri-sendiri, begitu pula teks netral dengan total panjang yang sama. Gemini memproses setiap entri petunjuk saat menyimpannya, dan prompt utuh tampaknya membebani tahap itu. Dua entri yang lebih pendek tersimpan jauh lebih andal. Tahap pemrosesan itu pula yang membuat pemeriksaan di atas penting: tidak seperti ChatGPT dan Claude yang menyimpan teks persis Anda, Gemini kadang justru menyimpan versi yang ditulis ulang — dan penulisan ulang bisa diam-diam mengubah tentang siapa petunjuk itu berbicara, sehingga prompt-nya kehilangan gunanya. Penyimpanan persis memang terjadi; kadang hanya perlu mencoba ulang.

---

## 3. TROUBLESHOOTING clause — in the "causes" list

### ar
old: `أو أن المدخل في Gemini لم يُحفظ في التعليمات المحفوظة.`
new: `أو أن المدخل في Gemini لم يُحفظ ضمن الذكاء الشخصي أو أُعيدت كتابته عند الحفظ (انظر **«التحقّق»** أعلاه).`

### ur
old: `یا Gemini میں اندراج محفوظ شدہ معلومات میں محفوظ نہیں ہوا۔`
new: `یا Gemini میں اندراج ذاتی ذہانت کے تحت محفوظ نہیں ہوا یا محفوظ ہوتے وقت دوبارہ لکھ دیا گیا (اوپر **«تصدیق»** دیکھیں)۔`

### id
old: `di Gemini, entrinya tidak tersimpan di Info tersimpan.`
new: `di Gemini, entrinya tidak tersimpan di bawah Kecerdasan Pribadi atau ditulis ulang saat disimpan (lihat **Pemeriksaannya** di atas).`

---

## Two decisions to confirm, not silently taken

**1. Arabic keeps its language-flip note.** The ar article's current paragraph
carries an Arabic-specific observation the EN has never had: that Gemini may rewrite
an Arabic entry *into English* when it opens with a bare bullet list, which is why ar
part 2 opens with two lead-in sentences. That note is still true and still explains a
visible feature of the ar page, so I kept it as a short second paragraph — while
deleting the false "substance stays intact" clause it used to sit beside. Dropping it
wholesale would have removed a true, ar-specific explanation the reader needs; keeping
the whole old paragraph would have kept the false claim. Flagging because it makes ar
one paragraph longer than EN by design.

**2. The duplicate-entry advice now lives in `The check`, not in `Why two parts?`.**
All three old localized paragraphs ended with the "an error can appear even though it
saved — check the list before retrying" note. EN's new string 1 carries that, so
leaving it in string 2 would say it twice on the same page. Removed from string 2 in
all three, matching the EN structure.

---

## Review record

Two independent reviewers, per the standing fidelity bar.

| Reviewer | ar | ur | id |
|---|---|---|---|
| Gemini | ACCEPT | ACCEPT | ACCEPT |
| Codex | ACCEPT-WITH-EDITS | ACCEPT-WITH-EDITS | ACCEPT |

Codex's edits were adopted in full — all were genuine fidelity misses, not
preference:

1. **The quoted error string `"Something went wrong"` had been dropped from ar
   and ur string 2.** The EN quotes it literally, and a reader matching what is
   on their screen to what the article says needs the exact words. Restored in
   both. (id already carried it.)
2. **The bold cross-reference in string 3** was bolded only in id. Now bold in
   all three, matching the EN.
3. **ar softened "sometimes" to "may"** in two places — restored to أحيانًا, so
   the frequency claim matches the English rather than sounding more remote.
4. **ur register**: "saved with greater confidence" was an unnatural calque;
   replaced with قابلِ اعتماد طریقے سے. Final sentence made idiomatic without
   weakening it.

Codex also independently endorsed keeping the Arabic language-flip note, on the
grounds that it explains the actual construction of part 2 and does not
reintroduce the false claim — the same reasoning given above, reached separately.

Raw reviews: `codev/projects/14-multilingual-companion-prompt-/verify-step-review-{gemini,codex}.txt`.
