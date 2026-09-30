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

## 2026-09-30 — spec reviewed, at the spec-approval gate

Three-way review: Gemini approve; Codex request-changes (5 points); Claude comment (7 points).
All accepted (one in part). The changes that matter to later phases:

- **Reword before the first commit.** My draft said "commit the as-run originals, then
  port". Codex pointed out that would put the private wording into public git history.
  The spec now requires the comment rewording first, and the private-material search covers
  every commit on the branch, not just the final tree. Run it before pushing.
- **Benchmark package finds its data from its installed position.** If it is installed as a
  non-editable dependency, its results folder and key-file paths point into the
  environment, not the clone. The plan must handle this.
- **Eight rebuilt files, not six.** Six builder scripts; eight files to compare.
- **Paired-interval bootstrap is not repeatable** and two intervals printed in the paper
  cannot be recovered exactly. Making it repeatable is the one authorised change to
  behaviour. Whether the paper is corrected is an owner question.
- **Reference data is read-only; a new run writes elsewhere** and chains step to step.
- An owner-facing report outside git will list all 204 scratch files with class and
  destination, plus the search result.

Eight questions for the owner are in the spec (weights, capability results, two existing
comment lines, linking issue 21, sibling-project files, console logs, redistribution terms,
the paper's two paired intervals). Waiting at the gate.
