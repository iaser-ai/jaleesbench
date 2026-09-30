# spir-36 thread — JaleesWeights handoff folder (issue #36)

## 2026-09-30 — specify phase

Read the architect's local notes, the paper, all 44 scratch scripts, and the experiment
issue (#21). Wrote the spec draft.

**What I checked, at no cost** (scratch copies only; main checkout untouched):

- Re-ran the six deterministic training-set builders against today's data. All six
  reproduce the frozen files byte for byte (316 / 310 stage-1 examples, 502 / 672 stage-2
  pairs, the conversation inputs, the trainer-format export).
- Recomputed the paper's main table from the existing judgment files. Every point estimate
  matches to three decimals. Interval ends wobble by up to 0.005 between runs because the
  paired-comparison code iterates a Python set; the ported scoring step must be repeatable.

**Surprises**

- Every per-run `code.diff` contains diffs of `codev/state/main.md`, not just lockfile
  diffs. All ten are classed "left out".
- A Tinker cleanup record in the scratch folder lists other parties' runs. Left out.
- The benchmark's key loader demands seven provider keys before judging; a new team needs
  two or three. Written into the spec as an explicit scope item, as the architect asked.
- No analysis script exists for the Inkling-Small rows of the paper's main table; those
  numbers were computed ad hoc. The final pipeline needs a scoring step that covers them.
- Capability-panel raw results are not in the scratch folder; they are only on the owner's
  Modal volume.

**Decisions from the architect (2026-09-30)**

- Draft with the two sibling-project files left out and the provenance line in our bf16
  stage-1 docstring reworded; owner confirms at the gate.
- Do not touch the two existing comment lines in the benchmark's collection module, do not
  download from Modal, keep "recipe only, no weights" — all three are the owner's calls and
  are listed as open questions in the spec.

**Standing limits**: no release (draft or public) and no paid Modal / Tinker / judging step
without the owner's approval relayed by the architect.
