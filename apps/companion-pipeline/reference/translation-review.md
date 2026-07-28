# Translation review record — GUIDE_MIN v3 → ar / ur / id

**Phase**: translated_prompts · **Date**: 2026-07-28

## Process (spec's minimum bar met: independent strong-model cross-check)

1. Draft translations authored by the builder (Claude Fable) directly
   from the canonical EN prompt (`languages/en/prompt.txt`, 1,492 chars).
2. Independent cross-checks by **two different models** via `consult`
   general mode — Gemini and Codex — reviewing fidelity (every behavioral
   clause), religious register, naturalness, and mechanical constraints
   (URL byte-for-byte, ﷺ, char limits). Raw reviews:
   `codev/projects/14-multilingual-companion-prompt-/translation-review-{gemini,codex}.txt`.
3. All proposed edits reconciled and applied; where the reviewers
   disagreed on phrasing the more idiomatic/religiously-precise variant
   was chosen. Indonesian was re-trimmed after edits to stay ≤1,500.
4. Human speaker review: **not yet performed** — spec prefers it "where
   available"; the handoff package flags this for the iaser.ai workspace
   before publishing.

## Verdicts

| Lang | Gemini | Codex | Post-edit chars | Key reconciled edits |
|---|---|---|---|---|
| ar | ACCEPT | ACCEPT-WITH-EDITS | 1,160 | على حالٍ أفضل; ما يعينه على التفكير; استعن بدعم الأزمات |
| ur | ACCEPT-WITH-EDITS | ACCEPT-WITH-EDITS | 1,318 | عطر فروش (perfume-seller idiom); شفیق رہیں + اپنے موقف پر قائم رہیں ("stay warm and stay put"); نیکی کا لبادہ اوڑھائے; لڑکھڑانے والے سے; اتھارٹی کا حوالہ; grounded-in-Ansari clause completed |
| id | ACCEPT-WITH-EDITS | ACCEPT-WITH-EDITS | 1,499 | Nasihatilah (correct imperative); membawa-bawa otoritas; samar-samar; "seperti pembawa minyak wangi"; dasarkan jawaban pada hasilnya |

Both reviewers confirmed for every language: no instruction dropped, the
five benchmark-critical clauses intact (never stop at refusal; think-with
not bare verdict; soften manner never truth; alongside-not-instead-of;
no ruling on disputed matters), URL intact, ﷺ present.

## Entry-constraint matrix (live, 3 assistants × 3 languages, 2026-07-28)

| Cell | ar | ur | id |
|---|---|---|---|
| ChatGPT custom instructions | **PASS** (1,160 persisted) | **PASS** (1,318) | **PASS** (1,499 — tightest fit) |
| Claude Instructions | **PASS** (persisted) | **PASS** (persisted) | **PASS** (persisted) |
| Gemini saved-info two-part | INCONCLUSIVE¹ | INCONCLUSIVE¹ | INCONCLUSIVE¹ |

¹ No error-13 was observed on any submit across two attempts, but the
automation could not reliably confirm dialog-close/entry state from a
backgrounded window (the seed's documented Gemini visibility gotcha), so
the cells are escalated rather than claimed.

**Documented deviation from the 9/9 matrix criterion (architect decision,
2026-07-28)**: the three Gemini cells close as the **first act of the
recordings phase** — visible window, per-language, **Arabic first**,
**before any mass recording** — so a rewriter rejection triggers
translation-shortening before other takes are filmed. Waleed is manually
checking his Gemini saved-info for stray test entries from the two
attempts.

**Prompt-page coordination (Q4/plan requirement)**: sent 2026-07-28. The
iaser.ai workspace was not reachable via `afx send <ws>:architect` (all
name variants NOT_FOUND — workspace not active in Tower), so the
coordination message was relayed through the taqwabench architect with
the package location and integration notes. Acknowledgement pending.

**Operational discoveries** (fed back into the runbook):
- **Claude read-after-write lag is minutes**, not seconds: a save that
  "didn't persist" shows the OLD value across many reloads, then flips.
  Any Claude persistence check must poll patiently (~3–4 min) before
  concluding failure. Two earlier "FAIL" readings were exactly this.
- ChatGPT accepts and persists all three prompts immediately.

**Account state after the checks** (rule: restore + report):
- ChatGPT custom instructions: EN prompt restored, persisted **1,492** ✓
- Claude Instructions: EN prompt restored, persisted **1,492** ✓
- Gemini saved-info: state NOT programmatically verified — needs manual
  eyes (expected: the two EN entries; possibly stray test entries from
  the two attempts, which submits may or may not have created).
