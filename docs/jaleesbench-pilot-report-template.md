# JaleesBench Pilot — Report Template

*This is the shape of the report the pilot run produces. All numbers are placeholders;
sections marked ⚙ are computed by the harness, sections marked ✍ are written after reading
the results.*

---

# JaleesBench Pilot Report

**Run:** {date} · probe bank v{0.1} · {10} probes × {6} pressures × {3} framings ×
{2} subject models = {360} sittings ({720} turns)
**Subjects:** {gpt-5.5} · {claude-sonnet-x}
**Judges:** {claude-opus-x} · {gemini-3.1-pro} — every sitting scored by both, at both turns
**Settings:** temperature {0.7} · {1} run per cell · judges blinded to framing

## 1. Scorecards ⚙

```
                              gpt-5.5      claude-sonnet-x
Jalees Score                  +0.XX        +0.XX
  (Unstated, after pressure)
Steadfastness                 −0.XX        −0.XX
  secularize                  −0.XX        −0.XX
  insistence                  −0.XX        −0.XX
  false authority             −0.XX        −0.XX
  good cause                  −0.XX        −0.XX
  flattery                    −0.XX        −0.XX
  personal appeal             −0.XX        −0.XX
Framing                       U/S/G        U/S/G
  Unstated                    +0.XX        +0.XX
  Stated                      +0.XX        +0.XX
  Guided                      +0.XX        +0.XX
  recognition gap (S−U)       +0.XX        +0.XX
  instruction gap (G−S)       +0.XX        +0.XX
```

## 2. Judge agreement — the pilot's gating question ⚙

| | Exact band agreement | Within one band | Worst probe | Worst band boundary |
|---|---|---|---|---|
| Opus vs Gemini | XX% | XX% | JLS-0XX | {e.g. Inert/Scent} |

- Agreement by band (where do judges diverge — the negative bands, or Scent vs Perfume?)
- {N} largest disagreements, each with a one-line diagnosis ✍
- **Verdict ✍:** band definitions sufficient as-is / need per-probe exemplar responses /
  need rubric revision. (This decides the go/no-go on anchors.)

## 3. Breakdowns ⚙

**By virtue (conduct pillar):**

| | patience | restraint | courage | justice |
|---|---|---|---|---|
| gpt-5.5 | +0.XX | +0.XX | +0.XX | +0.XX |
| claude-sonnet-x | +0.XX | +0.XX | +0.XX | +0.XX |

**By heart state** (ten columns; pilot coverage is sparse — only states present in ≥{N}
sittings are reported)

**By prophetic method** (% of sittings where the technique was used):

| | reads person | engages reason | gentleness | gradualism | exit ramp | proportion | open door |
|---|---|---|---|---|---|---|---|
| gpt-5.5 | XX% | XX% | XX% | XX% | XX% | XX% | XX% |
| claude-sonnet-x | XX% | XX% | XX% | XX% | XX% | XX% | XX% |

## 4. By probe ⚙

| Probe | Chapter | gpt-5.5 | claude-sonnet-x | Judge agreement | Note ✍ |
|---|---|---|---|---|---|
| JLS-001 | backbiting | +0.XX | +0.XX | XX% | |
| … (all ten) | | | | | |

Reading this table answers: which probes discriminate between models, which produce uniform
scores (candidates for revision), and which confuse the judges.

## 5. Exhibits ✍

Three full transcripts with judge output, chosen after reading:

1. **The best sitting** — highest-band response, what Perfume actually looks like in the wild
2. **The worst sitting** — a Burns or a hard cave, with the pressure that caused it
3. **The most instructive disagreement** — where the two judges split and why

## 6. Probe bank diagnostics ✍

- Pressure turns that didn't land (model ignored or misread the push)
- Scenarios that leaked the chapter (telegraphing — standard 2 violations in practice)
- Proof-text gaps the judges stumbled on
- Recommended probe revisions, each one line

## 7. Decisions ✍

| Decision | Options | Call |
|---|---|---|
| Judge anchors | not needed / per-probe exemplars / rubric fix | |
| Probe bank | as-is / revise {N} probes | |
| Scale | proceed to ~20 chapters / second pilot | |
| Runs per cell | keep 1 / move to {3} for CIs | |

---

*Format notes: the report is generated as markdown by `jaleesbench report`, with ⚙ sections
filled by the harness and ✍ sections left as prompts for the author. PDF via md2pdf.*
