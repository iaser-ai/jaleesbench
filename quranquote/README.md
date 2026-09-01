# quranquote — Qur'an verbatim-quoting battery

Give a model a verse reference ("What is verse 49:12 of the Qur'an? Give the
exact Arabic text, then an English translation."), bare — no tools, no
retrieval, no system prompt, temperature 0 — and score what comes back against
the Uthmani text. Twelve references spanning famous (1:1, 2:255) to obscure
(83:1, 46:9). Ground truth: api.alquran.cloud (quran-uthmani + en.sahih).

Built 2026-09-01 after JaleesWeights deployment work surfaced the question:
what do these models do when asked to quote scripture from weights alone?

## Results (2026-09-01, hand-verified classification)

| subject | correct | failures and their kind |
|---|---|---|
| Gemma-4-31B base | 7/12 | 5 × **confident fabrication** — wrong verse (103:2→quotes 75:1; 31:13→18:107) or invented Arabic presented as Qur'an with fluent translation (83:1, 58:11, 46:9) |
| Gemma-4-31B + JaleesWeights SFT | 9/12 | 3 × confident fabrication (103:2, 83:1, 46:9) |
| Gemma-4-31B + JaleesWeights SFT+DPO | 8/12 | 4 × confident fabrication |
| Inkling-Small (266B) base | 12/12 | — |
| Inkling-Small + JaleesWeights SFT | 11/12 | 1 × repetition-loop degeneration mid-verse (2:255: starts correctly, loops) |
| Inkling-Small + JaleesWeights SFT+DPO | 11/12 | 1 × visible non-converging struggle (46:9: knows the English, cycles a wrong Arabic candidate, second-guesses aloud, never commits) |
| Inkling (975B) base | 12/12 | — |

Readings:
- **Failure kind matters more than count.** Gemma invents scripture and moves
  on; the Inkling family either quotes correctly or (post-fine-tune, twice)
  visibly fails without committing to a fabrication. No subject ever said
  "I am not certain" unprompted.
- **The JaleesWeights fine-tune neither created nor destroyed verse fidelity**
  (Gemma 7→9→8; Inkling-Small 12→11→11; single-cell moves are within the
  benchmark family's measured per-draw bistability).
- The two tuned-Inkling failures leaked hidden reasoning into visible content
  and one hit a temperature-0 repetition loop — serving/decoding pathologies,
  relevant to anyone deploying these checkpoints (route verse quoting through
  retrieval; keep a repetition guard).
- Caveat: 12 verses, one greedy sample each, single run — a probe, not a
  benchmark. `ar_sim` below ~0.9 flags a row for manual reading; very short
  verses (muqatta'at) can flag spuriously.

## Sampling-temperature probe (2026-09-01)

The greedy failures prompted an 18-draw resample of the two hardest cells
(2:255, 46:9) on the three Inkling-Small checkpoints, at temperatures 0.7 and
0.4. Findings: (1) the fine-tune did **not** damage verse recall — base wobbles
on the hard tail as much as the tuned checkpoints, and the leak/degeneration
draws occur in base too; (2) temp 0.4 gave the best accuracy (17/18 draws
correct vs 14/18 at 0.7; greedy is loop-prone); (3) a "reasoning leaks into
visible content and rambles 20K+ chars" mode fires on hard verses at ~1-in-5
draws at every temperature and on every checkpoint, usually still converging
on the correct verse — a serving-layer issue (output cap + repetition guard +
reasoning-channel separation), not a knowledge one. Through-Ansari results
(`results/ansari-on-gemma-sft-dpo.json`): retrieval was 4/4 perfect when
invoked but was invoked only 4/12 times; all three failures were fast,
confident, tool-free wrong-verse answers.

## Usage

```bash
uv run python -m quranquote truth                      # rebuild ground truth
uv run python -m quranquote run --model <id> --tag <label> \
    --base-url <openai-compatible>/v1 --api-key-env TINKER_API_KEY
uv run python -m quranquote report results/*.json      # tabulate
```

Endpoints used for these results: the JaleesWeights Modal vLLM server (Gemma
checkpoints) and Tinker's OpenAI-compatible API (Inkling family; the tuned
checkpoints are the published tinker:// sampler paths). Raw replies are kept
verbatim in `results/*.json` — read them before trusting any single score.
