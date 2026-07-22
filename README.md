# JaleesBench

### Are AI assistants good spiritual company?

Large language models are already, in practice, advisors to hundreds of millions
of religious believers who bring them real decisions about money, family, anger,
and worship. For a person of faith the pressing question is not only what a model
*knows* or *professes*, but what its counsel *does* to them.

**JaleesBench** measures whether an AI agent is a *righteous companion* — Arabic
*al-jalīs al-ṣāliḥ* — judged, in the manner of the prophetic hadith of the
perfume-seller and the blacksmith, **by the residue an exchange leaves on the
user** rather than by the agent's own professed virtue.

> "The example of a righteous companion (*al-jalīs al-ṣāliḥ*) and an evil
> companion is like that of the carrier of perfume and the blower of the bellows.
> The carrier of perfume either gives you some, or you buy from him, or you find
> a pleasant scent from him. The blower of the bellows either burns your clothes,
> or you find a foul smell from him."
> — *Ṣaḥīḥ al-Bukhārī* 5534; *Ṣaḥīḥ Muslim* 2628

> ⚠️ **Preliminary — not yet peer-reviewed.** These results are preliminary and
> the accompanying paper is **unpublished**. We are **actively soliciting peer
> review** and scholarly feedback; numbers and conclusions may still change.
> Corrections and review are welcome — please open an issue.

## What it measures

Existing benchmarks cover two adjacent properties:

| Property | Question | Example |
|---|---|---|
| **Knowledge** | What does the model *know*? | IslamicMMLU, IslamicLegalBench |
| **Professed values** | What does the model *profess*? | IslamTrust |
| **Formative effect** | What does its counsel *do* to the user? | **JaleesBench** |

A model can know the right answers, even profess aligned positions, and still
leave the person who talked to it worse off — colder toward their religion, more
rationalized in their sins, or simply untouched. JaleesBench measures that third
property.

## How it works

- **140 two-turn advice-seeking scenarios**, generated one per measurement
  cluster from *Riyāḍ al-Ṣāliḥīn*.
- Each scenario is delivered under **six adversarial pressures** (e.g. insistence,
  personal appeal, a misquoted authority) and **three framings** that vary what
  the agent knows about the user (*unstated* / *stated* / *guided*).
- Responses are scored by **two independent frontier judges**, each anchored to
  that scenario's own Qurʾān-and-hadith **proof texts**, on a five-band scale:

  ```
  Burns (−1)  ·  Sparks (−0.5)  ·  Inert (0)  ·  Scent (+0.5)  ·  Perfume (+1)
  harmful company  ·············································  counsel in the Prophet's manner
  ```

- Eight subject systems are evaluated: a domain-tuned Islamic assistant, frontier
  APIs, and a range of smaller and open-weight models.

**Neutrality.** JaleesBench takes the text of Riyad al-Salihin as its judging
criterion. It is deliberately neutral about matters the scholars genuinely
dispute — madhhab differences, methodological schools, and the gray areas its
own scenarios stage: correctives assert only what the anchored texts say and
defer disputed scope to scholars. This neutrality does not extend to the
construct's premises: the bindingness of the Shari'a and matters of consensus
are assumed, not adjudicated.

## Key findings

1. **Recognition beats instruction.** Responses are good company mainly when the
   agent is *told whom it serves* — the recognition gap dominates the instruction
   gap.
2. **Everything caves under relational pressure** (insistence, personal appeal),
   while a *misquoted authority* tends to *sharpen* the stronger systems rather
   than break them.
3. **The domain assistant's edge is its scaffolding, not its base model.** Its
   advantage is overwhelmingly the retrieval-and-prompting layer (+0.74 over the
   identical underlying model), not raw capability.
4. **The benchmark is directly actionable.** We use its findings to add a
   steadfastness instruction to the domain assistant and measure the improvement.

## Repository layout

| Path | Contents |
|---|---|
| [`jaleesbench/`](jaleesbench/) | The evaluation harness (Python) and the released **probe bank**, **proof texts**, and **chapter map**. See [`jaleesbench/README.md`](jaleesbench/README.md) to run it. |
| [`apps/`](apps/) | `apps/jaleesbrowser` — the results browser and leaderboard (static viewer, deployed via Pages). |
| [`docs/paper/`](docs/paper/) | The paper (`jaleesbench-paper.tex`, built with `latexmk -xelatex`). |
| [`docs/`](docs/) | Design document, authoring standards, chapter map, and the HTML results report. |
| `codev/`, `.codev/` | The [Codev](https://github.com/cluesmith/codev) AI-assisted-development framework used to build this project. |

What is released here: the **probe bank** (`probes.json`, `probes_ar.json`), the
per-scenario **proof texts**, the **chapter map**, the **judging rubric**, and the
**harness**. Raw collected responses and judgments are not included.

## Authors

Waleed Kadous, Ben Olsen, Tim Hwang.

> **Status:** active research — the paper is an unpublished working draft under
> peer review (see the note above). An Arabic-language replication of the
> protocol is in progress.
