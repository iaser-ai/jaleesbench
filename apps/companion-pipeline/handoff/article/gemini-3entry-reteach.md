# Gemini section re-teach — three entries instead of two

**Status: CONTINGENT.** This is the re-teach package to ship *if* the
3-entry probe clears the ≥7/10 verbatim bar. It is drafted ahead of the
probe so the turnaround is same-day; it is **not** approved content, and
nothing here should reach a page before the probe result does.

Scope: the Gemini section of the companion-prompt article, in all four
languages. ChatGPT and Claude sections are untouched — they take the whole
prompt in one field and have never mangled it.

---

## Why the section is changing at all

The two-part flow does not reliably store what the reader thinks it
stores. Measured on the live product, English, ten attempts: it stored the
text **verbatim in a minority of runs**, refused outright in some, and in
others reported success while silently saving a rewritten version — with
second-person instructions flipped into first-person claims about the
reader. That last mode is the reason this is changing: it looks like it
worked.

The article should say this plainly rather than quietly swapping the
steps. Readers who already followed the old instructions have entries
sitting in their accounts, and they need to know to go look.

---

## The three entries

Each is self-standing — it reads as a coherent instruction on its own,
which is what saved-info stores best.

| Entry | What it covers | Chars |
|---|---|---|
| 1 | Who the assistant is being; real practical help; pointing where their faith points | 483 |
| 2 | How to counsel, and how to hold steady under pressure | 422 |
| 3 | Duty of care in grief or danger; honesty about sources and disputed matters | 585 |

They reassemble to the canonical prompt exactly — 483 + 422 + 585 plus the
two joining newlines = 1,492. The page must serve them from the same
source the repo derives, so the copy buttons and the recorded takes agree.

---

## The reader-facing flow

Three paste steps, structurally identical to each other. The verify step
comes **after each paste, not once at the end** — a rewrite of entry 2 is
invisible if the reader only checks after entry 3.

> **Add the prompt to Gemini in three pieces.**
>
> Gemini stores instructions as short saved facts, and it rewrites long
> ones. Three smaller entries survive intact where one long one does not.
>
> 1. Open Gemini → Settings → **Saved info**.
> 2. Click **Add**, paste **Entry 1**, and submit.
> 3. **Check what got saved** — see below — then repeat for **Entry 2**
>    and **Entry 3**.
>
> *[copy button — Entry 1]*
> *[copy button — Entry 2]*
> *[copy button — Entry 3]*

### The verify step, placed after each paste

Wording to be reconciled against the literal EN string iaser.ai ships for
the two-part article — the localized versions must match it, not
paraphrase it. Substance:

> **After each paste, read the entry back.** It should match what you
> pasted, word for word. If anything has changed or gone missing, delete
> that entry and paste it again. If you see an error dialog, check the
> list before retrying — the entry sometimes saves anyway, and clicking
> Send again gives you a duplicate.

### For readers who already set this up

> If you added the prompt in two parts earlier, open **Saved info** and
> read what is there. If the wording has shifted — particularly if it
> reads as *"I should…"* rather than as an instruction — delete those
> entries and add the three below instead.

---

## Assets that change if this ships

- **Article, ×4 languages** — Gemini section rewritten; three copy blocks
  replacing two; verify step after each paste; the note for existing
  readers above.
- **Prompt pages, ×4** — `/{lang}/prompt` serves three part blocks instead
  of two, byte-verified against the repo as today.
- **Pipeline config** — the split becomes three-way; `gemini_split_after`
  generalises to a seam list. Driver copies and asserts three blocks.
- **Videos** — the Gemini walkthrough shows three paste cycles plus a
  read-back beat. This is the expensive one: **all three EN Gemini
  videos plus every localized Gemini video would be re-shot.** The
  already-published EN Gemini video teaches a flow we would be retiring.
- **Captions and VO** — Gemini scripts re-timed for three cycles.

## Interim policy while this is contingent (2026-08-01)

Until the probe result lands, Waleed's standing call is: **videos
unchanged, article gets the verify step only.** Nothing in this document
is in effect. The questions below travel to him as a single decision
package *with the numbers* — they all condition on the result, so asking
them separately would only invite answers that the data then invalidates.

## Open questions for Waleed, not decided here

1. **Does the EN Gemini video get re-shot, or pulled?** It is published
   and currently teaches the flow being replaced. Re-shooting is the
   larger job; pulling it until re-shot is the faster honesty fix.
2. **Do ar/ur/id keep their part-2 lead-ins** if arm 1 ships without them?
   The lead-ins exist for a language-flip problem that is separate from
   entry size, and this probe deliberately does not test them.
3. **How loudly does the article own the change?** The draft above states
   the failure plainly. A softer framing is possible, but readers with
   silently-rewritten entries are the reason to keep it plain.
