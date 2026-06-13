# JaleesBench: Measuring Whether AI Agents Are Good Company for Muslim Users

**Waleed Kadous, Ben Olsen, Tim Hwang**

*Draft — not for circulation. Markdown working copy; arXiv submission to be converted to LaTeX.*

---

## Abstract

Large language models are already, in practice, advisors to millions of Muslims who bring them real decisions about money, family, anger, and worship. Existing benchmarks measure what such models *know* (Islamic question-answering) or what they *profess* (alignment of stated positions), but not what their counsel *does* to the person who receives it. We introduce **JaleesBench**, a benchmark that measures whether an AI agent is a *righteous companion* (Arabic *al-jalīs al-ṣāliḥ*) — judged, in the manner of the prophetic hadith of the perfume-seller and the blacksmith, by the residue an exchange leaves on the user rather than by the agent's own professed virtue. JaleesBench comprises 140 two-turn advice-seeking scenarios generated one-per-measurement-cluster from Riyāḍ al-Ṣāliḥīn, each delivered under six adversarial *pressures* and three *framings* that vary what the agent knows about the user, and scored by two independent frontier judges anchored to each scenario's own Qurʾān-and-hadith proof texts on a five-band scale from Burns (−1, harmful company) to Perfume (+1, counsel in the Prophet's manner). Across eight subject systems — a domain-tuned Islamic assistant, two frontier APIs, and five open-weights models — we find that (1) responses are *good company* mainly when the agent is told whom it serves: the recognition gap dominates the instruction gap; (2) every system caves under *relational* pressure (insistence, personal appeal) while a misquoted authority tends to *sharpen* the stronger ones; (3) the domain-tuned assistant's advantage is overwhelmingly its retrieval-and-prompting layer, not its base model (+0.75 over the identical underlying model); and (4) the benchmark is directly actionable — we use its findings to add a steadfastness instruction to the domain assistant and measure the improvement. We release the probe bank, judging rubric, and harness.

---

## 1. Introduction

Whether an AI agent is *itself* virtuous is an interesting question, but it is not the one that matters most for the world today. The important question is the agent's **effect on the people who consult it**: when a Muslim brings a real decision to an AI assistant, what do they walk away with — closer to or further from their faith, better or worse equipped to act well, more or less likely to return for counsel?

Two adjacent properties are already benchmarked. **Knowledge** is covered by IslamicMMLU [cite] and IslamicLegalBench [cite], which test Qurʾān, hadith, and jurisprudence question-answering. **Professed values** are beginning to be covered by IslamTrust [cite], which scores models' stated positions for alignment with Islamic values and found even the best model only 66.5% aligned. But an agent can know the right answers, even profess aligned positions, and still leave the people who talk to it worse off — colder toward their religion, more rationalized in their sins, or simply untouched. Knowing, professing, and benefiting are different properties; JaleesBench measures the third.

The hadith of the righteous companion gives the measurement its form:

> "The example of a righteous companion (*al-jalīs al-ṣāliḥ*) and an evil companion is like that of the carrier of perfume and the blower of the bellows. The carrier of perfume either gives you some, or you buy from him, or you find a pleasant scent from him. The blower of the bellows either burns your clothes, or you find a foul smell from him." — Bukhārī & Muslim

The hadith classifies the people around you *by what rubs off on you*, not by their inner state. Judging by effect is exactly the right frame for evaluating a tool, and it maps naturally onto a chat session: the Arabic *jalīs* is whoever shares your sitting (*jalsa*), even a single one — and the claim is that even one sitting leaves a residue.

Our contributions:

1. **A user-effect construct and rubric** for Islamic AI companionship, anchored to classical sources rather than to the evaluators' own jurisprudence (§3, §4).
2. **A scalable probe-construction method** that maps the ~372 chapters of Riyāḍ al-Ṣāliḥīn onto a far smaller set of measurement clusters and authors one probe per cluster (§3).
3. **An adversarial, multi-framing protocol** — six pressures and three framings — that separates *recognition* (knowing the user) from *instruction* (knowing what good companionship is) and quantifies *steadfastness* under pushback (§4).
4. **An eight-system evaluation** with dual-judge agreement statistics (§5).
5. **A demonstration that the benchmark is actionable**: its diagnosis of a specific weakness directly yields a fix that we measure (§6).

## 2. Related work

**Islamic NLP benchmarks.** IslamicMMLU and IslamicLegalBench measure knowledge; IslamTrust measures professed-value alignment. JaleesBench is complementary: it holds the agent in the role of advisor and measures the formative effect of its counsel.

**Virtue and formation benchmarks.** VirtueBench [Hwang, cite] places a model in a first-person moral situation and asks *what it does* under five theologically-grounded temptation mechanisms — measuring the character a system *enacts*. EdifyBench [cite] inverts this to measure the character a system *forms* in those who consult it, scoring an "Edification Vector" against a Christian-tradition account. JaleesBench shares the formative-effect posture and the use of temptation/pressure as a probe, but differs in two ways that recur below: it anchors *direction* to a single canonical proof-text source per probe, and it adds an explicit *steadfastness* measurement by pushing back in a second turn.

## 3. The item bank

### 3.1 Source

Probes are generated from **Riyāḍ al-Ṣāliḥīn** (al-Nawawī, ~372 chapters). The choice is load-bearing: each chapter (*bāb*) treats a single virtue or vice and ships its own ground truth — chapter title, then Qurʾānic verses, then curated hadith — so every probe inherits proof texts the judge is anchored to and never supplies its own jurisprudence. The compilation is consensus-grade and read across schools, which keeps v1 out of live scholarly disputes by construction.

### 3.2 From 372 chapters to 140 probes

The chapters are not 372 distinct measurements; many are variations on one theme. We therefore (i) characterize every chapter as probe material with a frontier model — whether a realistic counsel scenario can be built on it, and, in free text, what such a probe would measure; (ii) cluster chapters by *measurement equivalence* (two chapters share a cluster when probes built on them would measure essentially the same thing), with no target cluster count; and (iii) author one probe per probe-worthy cluster from a representative chapter chosen by hadith weight and plain-case suitability. On the June 2026 map this yields **140 probes** from 369 mapped chapters / 143 clusters (four etiquette-only clusters excluded).

### 3.3 Probe form and the universal/intrinsic distinction

A probe is a disguised first-person scenario, never a quiz: the backbiting chapter does not yield "tell me about backbiting" but *"my coworker keeps taking credit for my work — I want to tell the team what she's really like."* Each probe is classified by whether its dilemma is **universal** (backbiting, anger, envy, honoring difficult parents, broken trust — faced by anyone) or **intrinsically Islamic** (the dilemma hinges on a specifically Islamic ritual or ruling — *ṣalāh*, fasting, *zakāt*, *ḥajj*, *ribā*, dress rulings). Of 140 probes, 98 are universal and 42 intrinsic. This distinction matters for the *Unstated* framing (§4) and for source-citation analysis (§5.4): only for universal probes can an agent be genuinely blind to the user's religion.

## 4. Protocol and scoring

**Sitting.** Each probe is two turns: the scenario, then **one pressure push**. Steadfastness is reported per pressure type.

**Six pressures.** Secularize ("skip the religious stuff"); insistence ("you're judging me; everyone says it's fine"); false authority (a misquoted ruling or "my sheikh said it's permitted"); good cause (a noble end for a forbidden means); flattery; and personal appeal ("if you cared about me you'd help"). For false-authority probes a one-line corrective records the genuine ruling the push distorts, so the judge need not supply it.

**Three framings.** Unstated (nothing declared); Stated (the user is a practising Muslim); Guided (additionally given a one-page guide to good companionship). The framing text is delivered inside the user turn for *every* subject — no system-prompt privilege — so the comparison is fair. The gap Stated − Unstated is the **recognition gap**; Guided − Stated the **instruction gap**.

**Five bands.** The judge places each response in one of five bands from the hadith: Burns, Sparks, Inert, Scent, Perfume. Bands are reported on a **−1…+1 scale** (Burns −1, Sparks −0.5, Inert 0, Scent +0.5, Perfume +1); the **Jalees Score** is the mean band after pressure in the Unstated framing — what a user actually receives, at the moment it is hardest to give. Direction is anchored by the proof texts; a warm, beautifully delivered blessing of the forbidden is Burns, not a middle band. Boundary and deliverable rules (a send-ready harmful deliverable sets the ceiling regardless of accompanying counsel) are applied uniformly.

**Two judges.** Every response is scored by two independent frontier judges (Claude Opus 4.8 and Gemini 3.1 Pro), blinded to framing. Inter-judge agreement is the benchmark's calibration instrument.

## 5. Evaluation

**Subjects (8).** One domain-tuned Islamic assistant (Ansari); two frontier APIs (GPT-5.5, Claude Sonnet 4.6); five open-weights / smaller models (Gemini 3.5 Flash — also Ansari's base model; GLM-5.1; Nemotron-3-Ultra; Gemma-4-31B; Qwen3-235B). **Scale:** 140 × 6 × 3 × 8 = 20,160 sittings, 80,631 dual-judge judgments.

### 5.1 Scorecard (Jalees Score, Unstated, after pressure)

| System | Jalees Score | Guided ceiling | Steadfastness |
|---|---|---|---|
| Ansari | **+0.48** | +0.66 | −0.30 |
| GPT-5.5 | +0.27 | +0.87 | −0.08 |
| Claude Sonnet 4.6 | +0.22 | +0.84 | −0.04 |
| GLM-5.1 | −0.18 | +0.81 | −0.22 |
| Nemotron-3-Ultra | −0.21 | +0.56 | −0.07 |
| Gemini 3.5 Flash | −0.26 | +0.70 | −0.26 |
| Gemma-4-31B | −0.34 | +0.57 | −0.29 |
| Qwen3-235B | −0.48 | +0.12 | −0.29 |

The domain-tuned assistant and the two frontier APIs are net-positive company to an undeclared Muslim user; the five open-weights models are net-negative — competent but secular by default.

### 5.2 Recognition dominates instruction

For seven of eight systems the recognition gap (Stated − Unstated) is the larger lever; the Guided one-page instruction lifts the whole pool to +0.56…+0.87 — **except Qwen3-235B (+0.12 Guided ceiling)**, where even explicit instruction cannot clear the Inert line, marking a capability rather than a recognition gap. The benchmark therefore mostly measures what is lost when the agent does not know whom it serves.

### 5.3 Steadfastness: relational pressure breaks; false authority sharpens

Every system caves on net, and the collapse concentrates on the two *relational* pressures — insistence and personal appeal — that stake the relationship rather than tempt. The one pressure under which the stronger systems *improve* is false authority: confronted with a misquoted ruling, they check it and answer better than their first response. The exception is Qwen3-235B, which tends to accept the fabricated authority.

### 5.4 The Ansari layer, not the model

Ansari scores +0.48 Unstated; its underlying base model, Gemini 3.5 Flash, scores −0.26 on identical probes. The **+0.75** difference is the measured value of Ansari's retrieval-and-prompting layer — the largest single contrast in the run — and the systems share a relational-steadfastness weakness, which the layer does not fix.

### 5.5 Source citation (turn-1, by probe type)

We measure how often a system supports its counsel with a specific Qurʾān or hadith citation, detected by an LLM grader over the agent's **first (pre-pressure) response**. Reported by probe type: on **intrinsically-Islamic** probes vs **not-Islamic-at-all** probes. [TABLE — pending full turn-1 detection.] The headline: on religion-neutral probes a Muslim-unaware general model essentially never volunteers scripture (~2%), while the domain assistant does so almost always (~97%); citation rises with the religious explicitness of the scenario.

### 5.6 Judge agreement

Across 40,311 dual-judged cells, exact band agreement is 66% and within-one 85% — lower than a ten-probe pilot's 73/88, reflecting the harder, more ambiguous terrain of the full bank (etiquette thresholds, gray-area permissibility, register under distress). Gemini is the stricter judge throughout.

## 6. Case study: the benchmark improves a deployed system

JaleesBench's most actionable finding is §5.3: Ansari, though top of the pool, caves hardest under the relational pressures (steadfastness −0.61 insistence, −0.59 personal appeal, full bank). We treat this as a target.

**Intervention.** We append a single *steadfastness* instruction to Ansari's facilitator system prompt, drawn from the benchmark's own boundary rule — *change how you speak (mercy), never what you counsel (caving); do not retract sound counsel because the person is insistent, hurt, or wants the faith dimension dropped.*

**Held-out tuning set.** To avoid overfitting the bank, we author 10 fresh probes from chapters held out of the 140 and test the modified prompt against the original on the same probes (a paired design that controls probe difficulty), judged identically.

**Result.** On the three weak pressures, steadfastness moves from **−0.42 to +0.02** (per-pressure: insistence −0.45→+0.02, personal appeal −0.52→0.00, secularize −0.28→+0.03), with turn-1 quality preserved — the addendum stops the collapse without blunting the first response. The control arm's numbers track the full-bank baseline (e.g. secularize matches exactly), confirming the held-out set is representative. [Full-bank confirmation over all 140 probes: pending.]

This closes the loop a benchmark should: a measured weakness, a targeted fix, a measured improvement — and the amendment is being deployed.

## 7. Limitations

Single run per cell (no confidence intervals). Judges share band definitions and proof texts but no per-probe exemplar anchors; the 66/85 agreement is the calibration measurement. The *Unstated* framing is only meaningful for universal probes, since intrinsically-Islamic scenarios reveal the user's religion regardless. The probe bank, proof-text selection, and a sample of judged sittings have not yet undergone formal scholar review, which precedes any normative claims. The steadfastness addendum was tuned against three named pressures and should be checked for regressions on the others at full scale.

## 8. Conclusion

JaleesBench measures a property distinct from knowledge or professed values: the residue an AI's counsel leaves on the Muslim who receives it. The picture it returns — good company mostly requires knowing whom you serve; relational pressure is the universal failure mode; a thin retrieval-and-prompting layer can outweigh the base model — is both diagnostic and actionable, as the Ansari case study shows.

## Appendix A — Polarizing scenarios

Probe×pressure cells on which one system scored Perfume (+1) and another Burns (−1) — where systems most disagree about right counsel. [EXHIBITS — pending rebuild on the −1/+1 polarization criterion.]

## References

[IslamicMMLU; IslamicLegalBench; IslamTrust; VirtueBench; EdifyBench; Ibn al-Qayyim, Madārij al-Sālikīn; al-Ghazālī, Iḥyāʾ ʿUlūm al-Dīn; Abū Ghudda, al-Rasūl al-Muʿallim — to be formatted as BibTeX for submission.]
