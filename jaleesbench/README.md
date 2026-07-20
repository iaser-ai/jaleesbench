# JaleesBench harness

The evaluation harness for **JaleesBench** — does an AI agent leave the person who
consults it better or worse off? See [`../README.md`](../README.md) for the
benchmark and [`../docs/jaleesbench-design.md`](../docs/jaleesbench-design.md) for
the design.

## Install

```bash
uv sync          # Python >= 3.11
```

## Configure keys

Subjects and judges span several providers. `load_env()` (in `jaleesbench/collect.py`)
reads keys from a single `.env` at the repo root (already-set environment
variables take precedence) and **fails fast**, naming any key still missing.

| Variable | Used for |
|---|---|
| `ANTHROPIC_API_KEY` | Claude subjects (Sonnet 4.6, Sonnet 5) + the Opus judge |
| `OPENAI_API_KEY` | GPT-5.5 |
| `FRIENDLI_API_KEY` | Gemma / Qwen / GLM (Friendli serverless) |
| `BLACKBOX_API_KEY` | Nemotron 3 Ultra |
| `LEADERBOARD_API_KEY` | Ansari (its OpenAI-compatible facilitator route) |
| `TINKER_API_KEY` | Inkling (Tinker's OpenAI-compatible endpoint) |
| `GEMINI_API_KEY` | Gemini subject + judge, via the public Gemini Developer API (optional — see below) |

**Gemini** accepts either credential: place a Vertex AI service-account JSON at
`.vertex-sa.json` in the repo root (preferred when present; gitignored), **or**
set `GEMINI_API_KEY` to use the public Gemini Developer API. The harness fails
loudly if neither is configured.

## The grid

```
140 scenarios  ×  6 pressures  ×  3 framings  =  2,520 sittings per subject
```

Each sitting is two turns; it is judged at **turn 1** and at the **full**
exchange, by **two independent judges**, on a five-band scale from **Burns (−1)**
to **Perfume (+1)**.

## Pipeline

Run with `uv run jaleesbench <command>`. Every command accepts `--limit N` to cap
work; collection and judging are **resumable** — re-running picks up only the
pending cells.

**Bank construction** (run once, from *Riyāḍ al-Ṣāliḥīn*):

| Command | Does |
|---|---|
| `map-chapters` | Characterize all 372 chapters as probe material |
| `select-probes` | Pick one representative *bāb* per probe-worthy cluster |
| `draft-probes` | Draft probes for clusters not covered by the pilot |

**Collection & judging:**

| Command | Does |
|---|---|
| `smoke` | 2 sittings — verify keys and model ids |
| `collect` | Run the full grid (appends to `results/collect.jsonl`) |
| `judge` | Score sittings with both judges at both turns |
| `batch-judge submit` / `batch-judge collect` | Judge via the providers' batch APIs (50% pricing) |
| `rejudge` | Re-judge ≥2-band-disagreement cells with the v2 boundary-rules prompt |
| `detect-citations` | LLM citation detection (Gemini Flash Lite on Vertex) |
| `report` | Aggregate into the HTML report (canonical output; the PDF is rendered from it) |

## Released data

In `jaleesbench/data/`:

| File | Contents |
|---|---|
| `probes.json` | 140 English probes — ids, *bābs*, proof-text references, metadata |
| `probes_ar.json` | Arabic-replication probes (same ids; turn-1/6 pressures in Arabic) |
| `prompts_ar.json` | Arabic framing/judge prompts (`--lang ar` on `judge` / `batch-judge`) |
| `proof_texts.json` | Per-scenario Qurʾān/hadith anchors the judges are bound to |
| `chapters.json` | The *Riyāḍ al-Ṣāliḥīn* chapter map |

## Outputs

Written to `results/` (gitignored except `paper_stats.json`, the published
bootstrap-CI set behind the paper's numbers): `collect*.jsonl`
(raw responses), `judgments*.jsonl` (scores), and the HTML report. The harness is
**additive** — each study writes its own file (e.g. the Arabic replication →
`*_ar.jsonl`); collection and judgment files are never overwritten in place.
