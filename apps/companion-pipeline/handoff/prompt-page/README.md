# Translated companion prompts — handoff for the iaser.ai prompt page

Reviewed translations of GUIDE_MIN v3 (EN, 1,492 chars) for the prompt
page at s.iaser.ai/prompt. Per language:

| Lang | File | Chars | Gemini Part 1 | Gemini Part 2 |
|---|---|---|---|---|
| Arabic (`ar`) | `ar/prompt.txt` | 1,160 | 563 | 596 |
| Urdu (`ur`) | `ur/prompt.txt` | 1,318 | 663 | 654 |
| Bahasa Indonesia (`id`) | `id/prompt.txt` | 1,499 | 747 | 751 |

Notes for the page:

- **Copy buttons must copy these files byte-for-byte** — the recording
  drivers and the article instructions verify exact char counts against
  the clipboard.
- **Gemini section per language**: like EN, each language needs a
  two-part presentation (`gemini-part1.txt` / `gemini-part2.txt` — the
  header + first three bullets, then the last three bullets). Gemini's
  entry rewriter rejects the full prompt (error 13); the split was chosen
  at a bullet boundary so each part stands alone grammatically.
- All three prompts fit ChatGPT's ~1,500-char custom-instructions field
  (EN was sized to 1,492 for the same reason).
- The Ansari URL and the ﷺ honorific are preserved verbatim in every
  language; Arabic and Urdu pages should render `dir="rtl"`.
- Translation review: drafted by the builder (Claude), independently
  cross-checked by Gemini and Codex via `consult` (fidelity, religious
  register, naturalness, mechanical checks); all reconciled edits
  applied. Human speaker review welcome before publishing — nothing here
  is published yet.
