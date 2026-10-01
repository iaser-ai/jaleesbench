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

## 2026-09-30 (evening) — scope change at the gate: Gemma gets a second way to run

Owner's decision, relayed by the architect: spec approved as it stood, conditional on one
change. The recipe of record now has three paths: Gemma on Modal (unchanged), Gemma on the
team's own GPU machine (new, same Hugging Face stack the Modal functions already run
inside), Inkling-Small on Tinker (unchanged). The eight owner questions stand at their
defaults. An earlier version of the brief said "own machine instead of Modal"; it was
superseded within minutes — Modal stays.

Spec changes: recipe-of-record text; run-order table shows both ways per GPU step; a new
hardware section (measured: 66.0 GB peak for bf16 stage-1 training on a B200, ~15 min, 420
conversations in ~6 min on an H200; derived: 62 GB of bf16 weights, one GPU of at least
80 GB for training with thin headroom, serving on 80 GB needs a smaller context window);
new approach section 6 recommending one shared computation with two thin launchers so the
two ways cannot drift; success criteria and tests for what can be checked on this Mac
(compile, usage, diff, CPU-only loss-mask check) and the named first smoke test for a team
with a GPU (stage-1 training limited to four examples); new owner question 9 (one GPU or
several; default one). Classification unchanged — the Modal drivers stay final; the
own-machine code is new, ported from their function bodies.

## 2026-09-30 (later) — owner's correction: the local path is a demonstration

Third revision of the brief within the hour: the local Gemma path does NOT have to match the
Modal path. It is a worked example of training locally — same two-stage recipe, same
builders, pairing rule, judge protocol and split — but it may use a smaller Gemma-family
model, and precision and batch settings may differ. Its numbers are not the paper's.

Consequence I worked out: a smaller Gemma model is not a subject of the benchmark main run,
so the demonstration cannot take its stage-1 teacher answers from the main run the way the
31B path does. It must collect its own base answers first (training half with guide;
held-out half bare and with guide), exactly as the Inkling-Small path does. Its run order
therefore mirrors Inkling-Small's, run on local hardware instead of Tinker.

Spec now: "no drift" requirement removed; approach section 6 rewritten around model choice;
Gemma-4 family sizes checked on Hugging Face (E2B, E4B, 12B, 26B-A4B, 31B — all ungated);
new owner question 9 with default **Gemma-4-12B, bf16, one 80 GB GPU (48 GB works with a
smaller serving window)**, alternatives E4B on 24 GB and 31B on 80 GB, trade-offs stated.
Modal-path run order restored to Modal-only; separate demonstration run order added.
Gate re-requested.

## 2026-09-30 (night) — plan drafted, reviewed, at the plan-approval gate

Spec approved (relayed by the architect; `porch approve` run). Plan written: eight phases,
one commit each — (1) as-run scripts at their final paths with the three comments reworded
first; (2) installable `uv` project, clone-relative paths, key loading scoped per step;
(3) data archives + checksums + fetch step (staged locally, nothing uploaded);
(4) free steps ported and proven byte-identical; (5) judging + Tinker steps;
(6) Modal drivers with configurable account names; (7) local demonstration;
(8) README, archive index, fresh-clone walk-through, owner report, PR.

Plan review: Gemini approve; Codex and Claude request-changes. All points accepted:
a common "preflight + --dry-run" shape for every paid step; counts corrected (43 kept
scripts; 88-member data archive); exhaustive checksum comparison of the archives;
Inkling-Small scoring declared as new code ported from the sweep script; GPU dependency
group with Linux markers and torch; three Modal images kept distinct; `uv.lock` as the 1 MB
exception; `config.json` original-machine paths kept and disclosed to the owner; release
tag fixed as `jaleesweights-data-v1`. Waiting at the gate.

Useful facts for implementation: `modal run <driver> --help` works with no Modal account
(tested with a fake HOME). `judge_all` builds both Anthropic and Gemini clients whenever
work remains — that is the second small change needed in the benchmark, beside
`load_env` narrowing.

## 2026-10-01 — plan approved; implement phase 1 done

Owner's one change at the plan gate: run records keep `metrics.jsonl` and `config.json`
(path fields rewritten to release-relative names), drop `checkpoints.jsonl`. Plan and spec
updated (78-member data archive), `porch approve` run.

Phase 1 (commit 3cac2db): 19 archive scripts + 24 final scripts copied to their final
paths (15 modules; `pairs.py`, `score.py`, `judge.py` hold several as-run scripts
concatenated under `# ===== as-run: <name> =====` separators), plus `split_70_70.json` and
`guided_prefix.txt`. Verified: every copy identical to its scratch original except the
three reworded comment blocks (`train_dpo_run.py` 9 lines, `train_dpo_run2.py` 7 lines,
`modal/gemma_sft_bf16.py` 3 lines, all comments); `git show` of the commit has no hit for
the private names; benchmark tests 107 passed, 1 skipped.

## 2026-10-01 — phase 2 done; owner decided the data terms

Phase 2 (commit a1a013b + review fixes): `jaleesweights/` is a uv project (benchmark
editable from `../jaleesbench`, Tinker pinned to the versions the runs used, `modal`,
Linux-only `gpu` group), `paths.py` / `env.py` / `common.py`, benchmark `load_env` and
`judge_all` narrowing with tests. Dependency honesty, found in review: torch and
transformers are already in the default install on every platform because
tinker-cookbook depends on them (true of the benchmark too); the `gpu` group genuinely
adds peft, accelerate and vLLM. A custom CUDA torch index was tried and dropped — on Linux
the PyPI torch wheel is a CUDA build anyway and the index leaked into the default graph.

Owner's decision on open question 7 (terms), relayed by the architect: Apache-2.0 LICENSE
at the repo root for the code; data release CC BY 4.0 with a NOTICE (in the archives and
the README) that provider model outputs remain subject to their providers' terms. The
hadith-translation copyright of the proof texts stays open and goes in the owner report.
Recorded in the spec and in plan phase 8.

## 2026-10-01 — phase 3: data archives, checksums, download step

Built both archives deterministically (sorted members, zeroed metadata, gzip mtime 0 — a
rebuild gives the same checksum, confirmed). `jaleesweights-data.tar.gz`: 58 data files +
10 × {config.json with path fields rewritten, metrics.jsonl} + NOTICE = 79 members, 73.5 MB.
`jaleesbench-main-run.tar.gz`: collect, judgments, judgments_v2, citations_llm + NOTICE =
5 members, 110.9 MB. Installed with `fetch_data --from-dir`; all 84 installed files match
the member checksums; all data files byte-identical to the scratch originals; no config.json
contains an absolute path (`load_checkpoint_path` tinker:// addresses are left as they are —
identifiers, per the spec's security note; flagged for the owner report).

**Finding:** the benchmark's own scoring overlays `judgments_v2.jsonl` (282 re-judged cells)
on `judgments.jsonl`. With only the three files the builders read, the benchmark's
paper-stats test fails on the installed main run (3 subjects off by ~0.002). Added the
overlay to the main-run archive (158 KB); JaleesWeights keeps reading the base file as the
runs did — the overlay touches none of the stage-1 selection cells. Benchmark tests now 110
passed (the real-data test runs and passes against the installed copy).

The one-off build script (not committed; sources exist only on this machine):

```python
"""One-off: build the two JaleesWeights data archives from the read-only sources on the
original machine. Deterministic (sorted members, fixed metadata, gzip mtime 0) so a rebuild
gives the same checksums. Not committed: the sources exist only on this machine."""
import gzip, hashlib, io, json, os, pathlib, sys, tarfile

SCRATCH = pathlib.Path("<main checkout>/tmp/dpo-experiment")
MAIN = pathlib.Path("<main checkout>/jaleesbench/results")
WT = pathlib.Path("<worktree>/jaleesweights")
OUT = WT / "data" / "staging"; OUT.mkdir(parents=True, exist_ok=True)
NOTICE = (WT / "release" / "NOTICE").read_bytes()
RUNS = ["run1", "run2", "sft_small_run", "dpo_small_sft2_run",
        "dpo_small_sft2_sweep_lr0.0001", "dpo_small_sft2_sweep_lr0.0001_ep3",
        "dpo_small_sft2_sweep_lr0.0003", "dpo_small_sft2_sweep_lr1e-05_ep3",
        "dpo_small_sft2_sweep_lr3e-05", "dpo_small_sft2_sweep_lr3e-05_ep3"]
PATH_FIELDS = ("log_path", "train_path", "file_path")

def rewrite_config(run: str, raw: bytes) -> bytes:
    cfg = json.loads(raw)
    def fix(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in PATH_FIELDS and isinstance(v, str) and v.startswith(str(SCRATCH)):
                    rel = pathlib.Path(v).relative_to(SCRATCH)
                    node[k] = ("tinker-runs/" + rel.name) if k == "log_path" else rel.name
                else:
                    fix(v)
        elif isinstance(node, list):
            for v in node: fix(v)
    fix(cfg)
    text = json.dumps(cfg, indent=2) + "\n"
    assert str(SCRATCH) not in text and "/Users/" not in text, run
    return text.encode()

def build(name: str, members: list[tuple[str, bytes]]):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for arcname, data in sorted(members):
            info = tarfile.TarInfo(arcname); info.size = len(data)
            info.mtime = 0; info.uid = info.gid = 0; info.uname = info.gname = ""; info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    out = OUT / name
    with open(out, "wb") as fh:
        with gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0, compresslevel=6) as gz:
            gz.write(buf.getvalue())
    return out, [(a, len(d), hashlib.sha256(d).hexdigest()) for a, d in sorted(members)]

# --- experiment archive: 58 top-level jsonl + 10 x {config.json (rewritten), metrics.jsonl} + NOTICE
members = [(p.name, p.read_bytes()) for p in sorted(SCRATCH.glob("*.jsonl"))]
assert len(members) == 58, len(members)
for run in RUNS:
    members.append((f"tinker-runs/{run}/config.json", rewrite_config(run, (SCRATCH / run / "config.json").read_bytes())))
    members.append((f"tinker-runs/{run}/metrics.jsonl", (SCRATCH / run / "metrics.jsonl").read_bytes()))
members.append(("NOTICE", NOTICE))
exp_out, exp_list = build("jaleesweights-data.tar.gz", members)
# --- main run archive
# judgments_v2.jsonl: the benchmark's re-judged disagreement cells, overlaid by its own
# scoring (score.load_judgments) — included so the benchmark's tools and tests work on the
# installed main run. JaleesWeights itself reads the base judgments.jsonl, as the runs did.
mr = [(n, (MAIN / n).read_bytes()) for n in ("collect.jsonl", "judgments.jsonl", "judgments_v2.jsonl", "citations_llm.jsonl")]
mr.append(("NOTICE", NOTICE))
mr_out, mr_list = build("jaleesbench-main-run.tar.gz", mr)

rel = WT / "release"
with open(rel / "checksums.sha256", "w") as fh:
    for p in (exp_out, mr_out):
        fh.write(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n")
with open(rel / "CONTENTS.md", "w") as fh:
    fh.write("# Data release contents (tag `jaleesweights-data-v1`)\n\n")
    fh.write("Two archives. Every member is listed with its size in bytes and its SHA-256. "
             "Members are the files as the original runs produced them (the main run also carries the benchmark's "
             "`judgments_v2.jsonl` overlay of re-judged cells, which the benchmark's own scoring applies and "
             "JaleesWeights does not), with one exception: in each "
             "`tinker-runs/*/config.json` the `log_path`, `train_path` and `file_path` fields were rewritten "
             "from the original machine's absolute paths to release-relative names (nothing else in those "
             "files changed). `NOTICE` states the licence (CC BY 4.0) and that provider model outputs remain "
             "subject to their providers' terms.\n\n")
    for title, p, lst in (("jaleesweights-data.tar.gz — reference data of the recipe of record and the archived arms (extracted to `jaleesweights/data/reference/`)", exp_out, exp_list),
                          ("jaleesbench-main-run.tar.gz — the benchmark main run the builders read (extracted to `jaleesbench/results/`)", mr_out, mr_list)):
        fh.write(f"## {title}\n\n{len(lst)} members, {p.stat().st_size:,} bytes compressed.\n\n| member | bytes | sha256 |\n|---|---:|---|\n")
        for a, n, h in lst: fh.write(f"| `{a}` | {n:,} | `{h}` |\n")
        fh.write("\n")
# member checksum list for the exhaustive comparison (not committed)
with open(OUT / "members.sha256", "w") as fh:
    for a, n, h in exp_list: fh.write(f"{h}  reference/{a}\n")
    for a, n, h in mr_list: fh.write(f"{h}  main-run/{a}\n")
print(exp_out, exp_out.stat().st_size, len(exp_list)); print(mr_out, mr_out.stat().st_size, len(mr_list))
```
