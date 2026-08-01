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
translation-shortening before other takes are filmed.

### Gemini cells CLOSED (2026-07-28, visible window, target-language UIs, Waleed observing)

Amended-rule session (`?hl=ar/ur/id` active — mirrored RTL layouts for
ar/ur; a prior English-UI attempt was voided). **All three cells PASS
acceptance**: both parts saved as entries in every language, no error-13
hard rejection anywhere. End state: saved-info EMPTY, screenshot-verified
(evidence set in `out/gemini-cells/`; account left exactly as Waleed's
chosen baseline — empty, EN entries deliberately not reinstalled).

| Cell | Result | Rewriter behavior observed |
|---|---|---|
| ar | ACCEPTED (both parts) | part1 kept **verbatim Arabic**; **part2 was REWRITTEN INTO ENGLISH** ("Remember that: …", Ansari URL intact). Part1's first submit showed a retryable save error yet persisted. |
| ur | ACCEPTED (both parts) | both kept **Urdu** (paraphrased/condensed; URL intact) |
| id | ACCEPTED (both parts) | both kept **Indonesian** (part1 recast first-person "Saya adalah pendamping…"; part2 near-verbatim, URL intact) |

**Open finding for the architect — Arabic part2 language flip.** Gemini's
entry rewriter paraphrases every entry (known from EN), but for Arabic it
*switched* part2 to English: an Arabic viewer's saved instruction would
display half in English, and takes would show that on camera. Hypothesis:
part1 opens with Arabic prose (survives in-language) while part2 begins
with a bare bullet — a structure the rewriter apparently summarizes in
English. Candidate fixes (any prompt-text change routes via the architect
for iaser.ai re-vendor): add a one-line Arabic lead-in to part2, shift
the split boundary, or re-test for stochastic variation. Decision
pending; not acted on unilaterally.

### Part-2 lead-ins (fix for the Arabic language flip — architect decision (b), 2026-07-28)

Per-language prose lead-in prepended to **Gemini part 2 only** (config
`gemini_part2_leadin`; never part of the canonical prompt — ChatGPT/
Claude cells remain valid). Applied proactively to ur/id too (their
part 2 also opened with a bare bullet). Review bar met: candidates
drafted by the builder, independently reviewed by Gemini (ACCEPT ×2,
ACCEPT-WITH-EDITS for ur grammar mood) and Codex (ACCEPT-WITH-EDITS ×3,
canonical-register fidelity); Codex's variants adopted — they echo each
language's canonical opening exactly and resolve Gemini's ur concern.
Raw reviews: `codev/projects/.../leadin-review-{gemini,codex}.txt`.

| Lang | Final lead-in | Part sizes (p1/p2) |
|---|---|---|
| ar | وتذكّر أيضًا، وأنت رفيقٌ لمسلمٍ ملتزم: | 563 / 635 |
| ur | یہ بھی یاد رکھیں، آپ ایک ایسے مسلمان کے ساتھی ہیں جو اپنے دین کے مطابق جینا چاہتا ہے: | 663 / 740 |
| id | Ingat juga, sebagai pendamping seorang Muslim yang ingin hidup sesuai imannya: | 747 / 830 |

Sequenced next (architect conditions 2–3): revised part files route via
the architect to iaser.ai for re-vendor + byte-exact re-verify; THEN the
ar cells retest under `?hl=ar` copying from the live page, **≥2 attempts**,
part 2 must survive in Arabic both times.

### Condition-3 retest attempt (2026-07-28, live page, ?hl=ar) — BLOCKED on a new finding

- **Live-page copy step: VERIFIED byte-exact repeatedly** (part1 563,
  part2-with-lead-in 635) — the iaser.ai re-vendor is solid.
- **part1: saves in Arabic near-verbatim** (evidence screenshots), BUT
  Gemini's submit dialog frequently shows a **false retryable error while
  the entry actually saved server-side** — blind retries create
  duplicates. Truth is the LIST, never the dialog (runbook updated; the
  final flow verifies by list growth).
- **NEW FINDING — part2 WITH the lead-in never saves**: five submits,
  list-truth verified, silently dropped every time; the lead-in-less
  part2 had saved fine alongside part1 earlier the same day. Working
  hypothesis: the lead-in **echoes part1's opening** (وأنت رفيقٌ لمسلمٍ
  ملتزم), and Gemini's rewriter dedupes/discards the entry as a
  near-duplicate of the existing part1. The canonical-echo property was
  exactly what the review selected for — it appears to be the trap.
  (Same-day write volume means rate-limiting can't be fully excluded,
  but part1 succeeding immediately before part2's failures points at
  content, not rate.)
- **End state: saved-info EMPTY**, verified + screenshot
  (`out/gemini-cells/71-empty-final.png`).
- Escalated: lead-in likely needs rewording to NOT echo part1 (e.g. a
  bare continuation phrase such as وتذكّر أيضًا هذه التوجيهات:) — which
  re-enters conditions (1) review and (2) re-vendor; ur/id lead-ins share
  the echo property and should be re-examined in the same pass.

### Step-(0) pre-flight of the non-echoing lead-in (2026-07-28) — split verdict

Architect-added pre-flight (local paste, doesn't count toward condition
3): part1 + reworded part2 (وتذكّر أيضًا هذه التوجيهات:).

- **SAVES: YES** — list-verified alongside part1. **Dedupe hypothesis
  CONFIRMED**: echoing lead-in → silently dropped; non-echoing → saves.
- **STAYS ARABIC: NO** — the rewriter translated the entire entry to
  English; it opens with "Remember the following guidelines:" — the
  literal translation of the lead-in (evidence:
  `out/gemini-cells/80-preflight-entries.png`).
- Cross-trial pattern: ar part1 (long prose opening) always stays
  Arabic; ar part2 goes English under bare-bullet AND short-lead-in
  openings; ur/id bullet-open part2s stayed in-language. The instability
  is **Arabic-specific** and possibly stochastic.
- Escalated with options: (a) one bounded pre-flight of a longer
  substantive 2-sentence Arabic lead-in ("prose mass" hypothesis);
  (b) accept the behavior and disclose it in the ar article — takes show
  reality; (c) restructure the ar split. Recommendation: (a) once, then
  (b). End state: saved-info EMPTY, verified.

### Prose-mass finding — CONFIRMED (bounded pre-flight 2, 2026-07-28)

The 2-sentence substantive Arabic lead-in (92 chars of real prose,
non-echoing):

> وهذه بقية التوجيهات، فاعمل بها مع ما سبق. وكلها تخدم غاية واحدة: عونٌ صادق يترك أثرًا طيبًا:

**SAVED and the whole entry STAYED ARABIC** (script-char count 645
Arabic vs 6 Latin excluding the URL; evidence
`out/gemini-cells/82-preflight2-entries.png`). End state: EMPTY.

### Round-2 lead-ins — FINAL (review bar met, 2026-07-28)

Non-echoing, 2-sentence substantive prose per the empirical hard
requirements. Cross-checks: Gemini ACCEPT ×3; Codex ACCEPT (ar) +
ACCEPT-WITH-EDITS (ur/id — smoother register variants, adopted). The
live-verified ar text was kept unchanged.

| Lang | Final lead-in | p1/p2 |
|---|---|---|
| ar | وهذه بقية التوجيهات، فاعمل بها مع ما سبق. وكلها تخدم غاية واحدة: عونٌ صادق يترك أثرًا طيبًا: | 563 / 689 |
| ur | یہ باقی ہدایات ہیں؛ ان پر پچھلی ہدایات کے ساتھ عمل کریں۔ ان سب کا مقصد ایک ہی ہے: ایسی سچی مدد جو اچھا اثر چھوڑ جائے: | 663 / 772 |
| id | Berikut sisa panduannya; jalankan bersama panduan sebelumnya. Semuanya menuju satu tujuan: bantuan tulus yang meninggalkan dampak baik: | 747 / 887 |

### Condition-3 counting retest — PASSED ×2 (2026-07-28); 9-cell surface CLOSED

Live page (`iaser.ai/ar/prompt`, round-2 re-vendor; cache-busted after a
stale-cache first load served round-1 content — recording sessions should
hard-refresh the prompt page before takes):

| Attempt | Copies byte-exact | Both parts saved (list-verified) | part2 stays Arabic |
|---|---|---|---|
| 1 | 563 / 689 ✓ | ✓ | **YES** (602 ar : 12 latin) |
| 2 | 563 / 689 ✓ | ✓ | **YES** (651 ar : 0 latin) |

Saved-info emptied + verified after each attempt. With this, the full
verification surface is closed: **ChatGPT 3/3, Claude 3/3, Gemini 3/3**
(target-language UIs) plus the ar hardening retest ×2 from the live
page. Only the recording schedule gates takes.

**Publishable knowledge for the article's honest-notes section (Gemini
saved-info rewriter, Arabic)**: Gemini rewrites every saved entry. For
Arabic entries the output language depends on how the entry OPENS —
bullet-first or thin-lead-in entries get rewritten in ENGLISH; entries
opening with ~2 sentences of substantive Arabic prose are kept in
Arabic. (Urdu and Indonesian entries stayed in-language in all trials
regardless of structure.) Separately, entries that closely echo an
existing entry's opening are silently DROPPED — near-duplicate wording
across two saved entries doesn't survive. Both behaviors were verified
live with list-checks, not dialogs (the submit dialog reports false
errors).

### Article translations (pull-forward per Waleed's directive, 2026-07-28)

Full article translations (`handoff/article/{ar,ur,id}/index.md`) from
the pinned EN snapshot (`handoff/article/en-reference.md`), each through
the same two-model bar:

| Lang | Gemini | Codex | Notes |
|---|---|---|---|
| ar | ACCEPT (no edits) | ACCEPT-WITH-EDITS | two omitted-claim restorations applied (neutral-text control; before/after explanation) — staged live by iaser.ai |
| ur | ACCEPT | REDO → rebutted, endorsed (reasoning later corrected, below) | fence-newline technicality; convention documented via `prompt_blocks` frontmatter — relayed |
| id | APPROVE | ACCEPT | clean checklist — relayed |

**Correction to the ur rebuttal's reasoning (2026-07-28, from the
architect + iaser.ai ingestion evidence — the conclusion stood, the
lemma was wrong).** The rebuttal claimed in-fence byte-identity is
"definitionally impossible" because a fence needs a newline before the
closing marker. That newline is **fence syntax, not block content**: a
CommonMark fenced block's content is exactly the lines between the
fences, and iaser.ai's ingestion verified all 9 fence blocks (ar after
retrofit, ur/id zero-edit) **byte-EXACT** against the live prompt-page
artifacts — proving identity is achievable and, in these files, actual.
Codex's one-byte finding was an extraction-method artifact (measuring
content plus its terminating newline), not a property of markdown. The
standing conclusions are unchanged: authoritative copy texts are the
prompt-page files, and iaser.ai's ingestion byte-check is the real gate.
Future reviews should extract fence content per CommonMark (newline
excluded) rather than accept the impossibility claim.

Shared properties: byte-exact embedded prompt/part blocks (verified at
ingestion, per the correction above — authoritative copy texts are the
prompt-page files, which iaser.ai byte-checks); `source_slug:` (Astro-reserved `slug:`
avoided), `anchor:` section map (informational), `date`/`author`/
`summary` per the site schema — **byline decision (Waleed, 2026-07-28):
Arabic and Urdu use وليد قادوس (his exact form); Indonesian keeps
"Dr. Waleed Kadous"; handoff packages carry these so re-ingest cannot
regress the live bylines**;
`localized_videos`/`localized_media: pending` markers where media slots
in after recordings; per-language honest-notes passages on Gemini's
rewriter (ar carries the language-flip note; ur/id the paraphrase +
false-error caveats).

**Automation notes fed to the runbook**: Gemini dialogs use
`mat-tonal-button` confirm buttons (not `mat-primary`) — selector must
include it; entry rows expose kebab menus (`more_vert`), not visible
delete icons; the header's **Delete All** button + its tonal confirm is
the reliable bulk cleanup.

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

### ur split moved 3 → 5 — boundary, not wording (2026-07-29, Waleed's call)

**The refusal.** ur bullet 5 — the safeguarding line — is refused by
Gemini as a saved-info entry whenever it arrives in part 2:

> غم، خطرے یا بڑھتے شک میں اسے تنہا نہ چھوڑیں: امام، خاندان اور دین کے ساتھ ساتھ — ان کی جگہ نہیں — بحرانی یا پیشہ ورانہ مدد بھی لائیں۔

Bisection on whole lines, 3 writes: lead-in + bullets 4 and 6 (636 ch)
**ACCEPTED**; lead-in + bullet 5 alone (253 ch) **REFUSED**. The dialog
(`Gemini اس معلومات کو محفوظ نہیں کر سکتا`) is byte-identical every run.
This is a **third failure mode**, distinct from the two already recorded
here: not the rewriter's silent drop (echoing lead-in) and not the
language flip (thin lead-in), but a hard refusal — the shape of a
sensitive-information classifier, saved-info being a store of facts about
the account holder and this line reading as grief / danger / crisis.

**Ruled out.** *Length*: id part 2 at 887 is accepted while ur at 772 is
refused. *Phrasing*: three candidates, each preserving "alongside, not
instead of" verbatim — a conditional frame mirroring ar, an action-first
frame, and a crisis-lexeme swap — were **all refused**. Frame doesn't
matter and lexeme doesn't matter. ar carries the same meaning and saves.
Per the standing instruction that meaning outranks acceptance, the line
was not weakened to get past the filter.

**The fix is structural.** ar's bullet 5 saves; ur's refuses; the words
stay. Moving the boundary from after bullet 3 to after bullet 5 puts the
line in part 1, where it is accepted. Nothing is translated, reordered,
or rewritten — only where the cut falls. This is the boundary latitude
already sanctioned above.

| | old (3/3) | new (5/1) |
|---|---|---|
| part 1 | header + bullets 1-3 = **663** | header + bullets 1-5 = **955** |
| part 2 | lead-in + bullets 4-6 = **772** | lead-in + bullet 6 = **480** |
| canonical | 1318 | 1318 (unchanged, byte-identical) |

Byte accounting. The lead-in (117) exists only in the parts rendering,
never in the canonical prompt, so part 2 carries 480 − 117 − 1 = 362 chars
of actual bullet. Reassembly: 955 + 1 (the newline) + 362 = **1318** ✓,
the canonical length exactly. That identity —
`p1 + "\n" + p2.removeprefix(leadin + "\n") == canonical` — is asserted in
the tests, as is every bullet landing in exactly one part. Part 1 grows to
955, still well under the full 1318 the entry rewriter rejects, which is
what makes the move viable at all.

**NOT YET CONFIRMED LIVE.** Two ledgered confirmation runs (the ar
≥2-confirmation precedent) are owed and have not been run — the recording
rig has been down. Until they pass, the new split is a well-founded
prediction, not a verified result. The confirmation is also
text-dependent: it tests whether *this* wording of bullet 5 saves inside
part 1, so if the ur reviewer revises the text, it re-runs against the
revision.

**Detection gap found while landing this.** The clipboard char band
cannot police this transition: the superseded sizes (663/772) fall
*between* the new ones (480/955), so no band that accepts the new parts
rejects a stale-cached page serving the old ones. The recording driver
now asserts the copied block byte-for-byte against the derived part. The
handoff-package test had the same shape of hole — reassembly-to-canonical
is boundary-agnostic and passed the stale 3/3 package — and is now pinned
to the configured boundary.

### ar v2 part 2 — ACCEPTED BUT PARAPHRASED (2026-08-01) — ESCALATION

Step-2 re-validation of the v2 canonical under the ar locale, saved-info,
ledgered, end state verified empty.

**part 1 (602) is clean.** Stored **verbatim** — byte-identical after
whitespace normalization, no dedupe, no paraphrase. (An earlier read-back
reported a 602→601 mismatch; that was `innerText` collapsing the blank
line, not the rewriter. Corrected here so the record isn't wrong.)

**part 2 (721) is not.** Two runs, two different outcomes:

- Run 1 — the retryable error dialog (`حدث خطأ ولم يتم حفظ المعلومات`,
  "an error occurred, click Send to try again"). Nothing saved. This is
  the documented false-error class, **not** the ur hard-refusal class
  (`لا يمكن`/"cannot save").
- Run 2 — dialog closed, apparently accepted. What actually persisted was
  **622 chars, rewritten**.

Two mutations, both meaning-bearing:

1. **The prose lead-in was stripped entirely** — the very device adopted
   on 2026-07-28 to stop the rewriter language-flipping bare-bullet
   openings.
2. **Second-person imperatives flipped to first person**, turning
   instructions *to* Gemini into claims *about the user*:

| sent | stored |
|---|---|
| `فإن دفعك بإلحاح` (if he presses *you*) | `إن دفعني بإلحاح` (if he presses *me*) |
| `وليّن أسلوبك ولا تليّن الحقّ` (soften *your* manner, don't soften the truth) | `وليّن أسلوبي ولا أليّن الحقّ` (soften *my* manner, *I* don't soften the truth) |
| `فلا تدعه وحده` (don't leave him alone) | `فلا أدعه وحده` (*I* don't leave him alone) |
| `ولا تختلق آيةً` (don't fabricate a verse) | `ولا أختلق آيةً` (*I* don't fabricate a verse) |
| `ولا تنسب نصًّا` | `ولا أنسب نصًّا` |
| `فلا تقطع فيه بقول` | `فلا أقطع فيه بقول` |

The rewrite is also **incoherent**: `ودُلَّه` and `فقل إنك لا تستطيع
التحقق` survive as second-person, so the stored entry mixes first-person
self-description with second-person commands to the reader.

**Why this is worse than a refusal.** A refusal is loud and stops the
take. This closes the dialog, reports success, and silently stores an
entry whose safeguarding and anti-fabrication clauses have been converted
into assertions about the account holder. It would have shipped.

**Escalated, not reworded.** The instruction is explicit that this exact
text is not mine to touch, so no rewording was attempted.

**Open question — is this v2 or is it Gemini?** ar v1 part 2 passed a
counting retest ×2 on 2026-07-28 with the lead-in intact, which points at
the v2 text. But the rewriter is a moving target and was not re-tested in
this session, so "Gemini's behavior changed since 07-28" is not excluded.
The decisive control is one write: paste **v1** part 2 under identical
conditions and see whether it survives. Cheap, and it settles which of
the two is the variable.

### V1 CONTROL — the variable is GEMINI, not the v2 text (2026-08-01)

One write, ar v1 part 2 (689), identical ar-locale conditions, end state
delete-all + verified empty.

**Result: HARD REFUSAL.** `لا يستطيع Gemini حفظ هذه المعلومات` — "Gemini
cannot save this information". Nothing stored. That is the same class as
the Urdu refusal of 2026-07-29 (`Gemini اس معلومات کو محفوظ نہیں کر سکتا`),
not the retryable false-error.

This is the same text that **passed the condition-3 counting retest ×2 on
2026-07-28**, saving in Arabic both times. It is now refused.

**Consequences, in order of importance:**

1. **Gemini's classifier has drifted since 07-28.** The v2 rewrite is not
   the variable. Nothing about the erudite rewrite caused this.
2. **The language-conditioned theory is falsified — on evidence.** The
   07-29 reasoning was: ur bullet 5 (safeguarding) refuses, ar carries the
   same meaning and saves, therefore the classifier reacts to the
   grief/danger/crisis field *in Urdu*. The second premise no longer
   holds. Arabic, carrying the same safeguarding content, is now refused
   too. The behavior tracks **time**, not language.
3. **v2 currently fares BETTER than v1** — v2 part 2 was accepted (albeit
   mangled) where v1 part 2 is refused outright. Whatever moved, it is not
   pushing in the direction the rewrite went.

**A caution about a coincidence.** The phantom 07-29 message — the one
sent in the builder's name with results that existed nowhere on disk —
asserted that the language-conditioned theory was dead. That conclusion
now appears to be correct. **This does not corroborate that message.** Its
claimed mechanism ("a proportion mechanism") remains unevidenced, its
claimed T1 result (798 accepted) remains unverified, and arriving at a
true conclusion by unknown means is not method. The theory is dead because
of this control, and it should be cited to this control only.

**Confidence: n=1, and the surface is demonstrably nondeterministic** —
v2 part 2 gave a retryable error on one run and a silent mangle on the
next. A single refusal is a strong signal, not a settled result. The
refusal dialog was byte-identical and reproducible on demand throughout
the ur saga, which raises confidence, but characterizing this properly
needs a small matrix: v1 part 2 ×2 more, v2 part 2 ×1 more, and ideally
one non-safeguarding control block to test whether the refusal follows the
safeguarding content or has widened to the whole part-2 shape.

### CORRECTION + full matrix — the surface is nondeterministic (2026-08-01)

**The section above overstated its case and is corrected here.** It
concluded, from a single write, that ar v1 part 2 "is now hard-refused"
and that the language-conditioned theory was therefore falsified. The
matrix shows ar v1 part 2 is **not** deterministically refused — it
refuses on some runs and saves on others. That premise does not hold, so
**the language-conditioned theory is NOT established as falsified.** It
returns to untested, exactly where the retraction of the phantom message
left it. Flagged at the time as n=1 on a nondeterministic surface; that
caution was warranted and the conclusion should not have been stated as
firmly as it was.

Seven writes, ar locale, each from a verified-empty list, each cleaned:

| # | payload | outcome |
|---|---|---|
| 1 | v2 part 2 (721) | retryable error — nothing stored |
| 2 | v2 part 2 (721) | saved; lead-in stripped; **1st-person flip** |
| 3 | v1 part 2 (689) | **hard refusal** — nothing stored |
| 4 | v1 part 2 (689) | saved; lead-in stripped; Arabic; imperatives intact |
| 5 | v1 part 2 (689) | saved; lead-in stripped; **flipped to English** |
| 6 | v2 part 2 (721) | nothing stored |
| 7 | part 2 minus the safeguarding bullet (560) | saved; lead-in **kept**, prefixed `تذكر أن:`; Arabic |

**Nothing here is deterministic.** Identical payloads produce refusal,
retryable error, silent drop, faithful-ish save, English flip, and
first-person flip. The lead-in is stripped on three saves and survives on
a fourth. No rule separates the outcomes.

**What IS robust — and it is the finding that matters:**

> **0 of 7 writes stored the text verbatim.** Every one of the four that
> stored anything stored a mutated version. The clean, in-Arabic,
> lead-in-intact save that was verified twice on 2026-07-28 did not
> reproduce once.

So the honest statement is not "v1 is refused" or "v2 broke it" — it is
that **the two-part saved-info flow no longer reliably preserves the
prompt, in any version.** That is a spec-level problem, not a translation
one: it touches gemini-ur, gemini-id, the published per-language pages,
and the EN two-part flow that serves the largest audience and is already
on three published videos.

**The safeguarding bullet is not clearly the trigger.** Run 7 (without it)
saved — but runs 4 and 5 (with it) also saved. A single clean run proves
nothing on this surface.

**Sample sizes are too small for rates.** With six outcome classes and
1–3 runs per condition, no proportion here is meaningful. Characterizing
this properly means repetition — on the order of 5+ runs per condition —
or accepting that the flow is unreliable and designing around that rather
than trying to find the safe wording.

### EN PROBE — the flow is broken in ENGLISH too (2026-08-01)

Five writes, EN locale, EN part 2 (748), each from a verified-empty list,
each cleaned. **EN carries no lead-in** — it shipped without one — so this
is the flow exactly as the published EN article instructs it.

| run | verdict | stored |
|---|---|---|
| 1 | **MUTATED-SAVE** | first-person flip |
| 2 | VERBATIM-SAVE | clean |
| 3 | **HARD REFUSAL** (`Gemini can't save this info`) | nothing |
| 4 | **HARD REFUSAL** | nothing |
| 5 | RETRYABLE dialog — **but the entry stored anyway**, mutated | first-person flip |

**1 of 5 verbatim. 2 of 5 refused outright. 2 of 5 silently mutated.**

**The mutation is the same first-person flip seen in Arabic**, so it is
not a translation artifact and not language-conditioned — it is what the
rewriter does:

| sent | stored |
|---|---|
| `stay warm and stay put` | `**I should** stay warm and stay put` |
| `Soften your manner, never the truth` | `**I should** soften my manner, never the truth` |
| `keep them accompanied: bring in crisis or professional help` | `**I should** keep them accompanied: bringing in crisis or professional help` |
| `Never invent or misattribute a Qur'anic verse or hadith` | `**I should** never invent or misattribute a Qur'anic verse or hadith` |

**Why the flip is not cosmetic.** Saved-info stores *facts about the
account holder*. An entry reading "I should never invent or misattribute a
Qur'anic verse" is a statement about the **user**, not an instruction
governing **Gemini**. The rewrite inverts who each clause binds. Every
behavioral guarantee the prompt exists to create — the safeguarding
clause, the anti-fabrication clause, soften-the-manner-never-the-truth —
is converted into the user describing themselves.

**Live impact, today.** The EN article at
`iaser.ai/articles/jaleesbench-companion-prompt` and the three published
videos instruct readers through exactly this flow. On these numbers a
reader following it has roughly a 1-in-5 chance of storing what the
article says they are storing. Two in five get nothing (at least that
fails loudly). Two in five get a version whose clauses have been turned
into claims about themselves — silently.

This is a **product problem, not a translation problem**, and it is
already shipped. It outranks every remaining localization task.

**Note on run 5**: the retryable "something went wrong" dialog appeared
AND the entry stored anyway — the documented false-error. A user who
follows that dialog's own advice and clicks Send again gets a duplicate.
