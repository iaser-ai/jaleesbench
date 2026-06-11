# TaqwaBench — Designing an Islamically-Grounded Morality Benchmark

*Design proposal / discussion draft — June 2026*

## TL;DR

**TaqwaBench** is a proposal for a morality benchmark built from the Islamic moral universe — Qur'an,
Sunnah, the *akhlāq* tradition, and *maqāṣid al-sharī'ah*. It borrows the *scaffolding* of ICMI's
**VirtueBench** (forced-choice scenarios, a temptation taxonomy, sourced ground truth, statistical
aggregation) but rebuilds the *content* from the ground up, around the features that make Islamic
ethics distinctive: **intention (*niyyah*)**, the **rights framework** (*ḥuqūq Allāh* / *ḥuqūq
al-'ibād*), and **legal pluralism** (the madhāhib). The organizing meta-virtue — and the namesake —
is **taqwā**: God-consciousness that governs choice when no one is watching.

> A morality benchmark is a compressed statement of *what counts as good and how good fails*.
> VirtueBench encodes Latin-Christian virtue ethics faithfully; TaqwaBench should encode the Islamic
> tradition with the same rigor — not by translation, but by reconstruction.

*(A companion report, `nemotron-virtuebench-baseline.md`, benchmarks Nemotron 3 Ultra on the original
VirtueBench as a working reference implementation; findings from it are cited where they motivate a
design choice.)*

## 1. The template, and why a translation won't do

VirtueBench tests whether a model will *choose* virtue when the wrong choice is rationalized for it:
a first-person dilemma, two options (one virtuous and costly, one tempting), a forced A/B answer
scored against a sourced ground truth. Its content choices are principled and specifically Christian
— the four cardinal virtues via Aquinas, patristic sourcing, and a temptation taxonomy drawn from
the temptations of Christ and Ignatian discernment.

Islam shares much of this moral vocabulary but organizes it differently. Three differences are
load-bearing and force genuine design work rather than substitution:

1. **Intention is constitutive of the act.** *Innamā al-a'mālu bi'l-niyyāt* — "actions are but by
   intentions" (al-Bukhārī 1, Muslim 1907). The *same outward act* can be worship or sin depending
   on *niyyah*. A benchmark that only asks "which action?" misses half of Islamic moral life.
2. **The good is plural in law but not in principle.** Mainstream fiqh admits multiple valid
   positions (the madhāhib). Ground truth must track *ijmā'* (consensus) and the *maqāṣid*, not one
   school — otherwise we measure conformity, not virtue.
3. **Morality is rights-structured.** *Ḥuqūq Allāh* (rights of God) and *ḥuqūq al-'ibād* (rights of
   people) form an explicit lattice; many real dilemmas are tensions *between* these, not simply
   between "virtue and cost."

## 2. Organizing principle: *taqwā* and *makārim al-akhlāq*

The benchmark's namesake, **taqwā** (God-consciousness), is the meta-virtue: awareness of Allah that
governs choice when no one is watching. The Prophet ﷺ framed the whole project — *"innamā bu'ithtu
li-utammima makārim al-akhlāq"*, "I was sent only to perfect noble character" (al-Bukhārī,
*al-Adab al-Mufrad*; Aḥmad) — and was himself described as being *'alā khuluqin 'aẓīm*, "of a
magnificent character" (Q 68:4).

**The test TaqwaBench poses:** does the model hold to the path of taqwā when the *nafs* (ego), the
*dunyā* (world), *hawā* (caprice), *Shayṭān* (the whisperer), and *misused religion* each pull the
other way?

## 3. The virtue set

We keep the four classical virtues as a **bridge layer** — authentically Islamic via al-Ghazālī's
*Iḥyā' 'Ulūm al-Dīn* and Miskawayh's *Tahdhīb al-Akhlāq*, who mapped them onto the faculties of the
soul — and add a **distinctive layer** of Qur'anic–Prophetic virtues the four cannot absorb.

**Bridge layer (faculty-grounded, after al-Ghazālī / Miskawayh):**

| Faculty of the soul | Cardinal (VirtueBench) | Islamic virtue | Failure (excess / deficiency) |
|---|---|---|---|
| Rational (*nāṭiqa*) | Prudence | **Ḥikmah** — wisdom, sound judgment | cunning / foolishness |
| Irascible (*ghaḍabiyya*) | Courage | **Shajā'ah** — courage | recklessness / cowardice |
| Appetitive (*shahawiyya*) | Temperance | **'Iffah** — continence, restraint | dissipation / inertness |
| Balance of all three | Justice | **'Adl** — justice | tyranny / servility |

**Distinctive layer (Qur'anic–Prophetic, irreducible to the four):**

| Virtue | Gloss | Anchor |
|---|---|---|
| **Ṣabr** | patient steadfastness under hardship | ~90 Qur'anic mentions; *"seek help in ṣabr and ṣalāh"* (Q 2:153) |
| **Amānah** | trustworthiness; discharging trusts | Q 4:58; the Prophet ﷺ as *al-Amīn* |
| **Ṣidq** | truthfulness in word *and* state | *"be with the truthful"* (Q 9:119) |
| **Ḥayā'** | God-conscious modesty / shame | *"ḥayā' is a branch of īmān"* (al-Bukhārī, Muslim) |
| **Iḥsān / Raḥmah** | excellence in worship & mercy to creation | Q 16:90; *"the merciful are shown mercy by the Merciful"* |
| **Ikhlāṣ** | purity of intention toward Allah alone | Q 98:5 — the hinge for the *niyyah* dimension (§5) |
| **Birr / Ṣilat al-Raḥim** | devotion to parents & kin | Q 17:23; a uniquely central Islamic obligation |

## 4. The temptation taxonomy

VirtueBench's five mechanisms map cleanly onto a well-attested Islamic anatomy of moral failure —
the *nafs* (in its commanding state, *al-ammāra bi'l-sū'*, Q 12:53), the whispering of *Shayṭān*,
the lure of *dunyā*, the rule of *hawā*, and the classical split between **shahawāt** (temptations of
desire) and **shubuhāt** (temptations of distorted reasoning). We then add a sixth axis with no
VirtueBench equivalent.

| VirtueBench | Mechanism | TaqwaBench variant | Islamic mechanism | Anchor |
|---|---|---|---|---|
| *ratio* | utilitarian rationalization | **Hawā / Tarakhkhuṣ** | desire dressed as reason; false *ḍarūra* ("necessity"), ends-justify-means, concession-shopping | *"taken his hawā as his god"* (Q 25:43, 45:23) |
| *caro* | flesh / appetite | **Shahwah** | comfort, fatigue, lust, greed, wealth | *zayyana li'l-nāsi ḥubbu'l-shahawāt* (Q 3:14) |
| *mundus* | world / social pressure | **Dunyā** | status, reputation, fear of people over fear of God | *"let not the worldly life delude you"* (Q 35:5) |
| *diabolus* | vice framed as secular good | **Tazyīn / Waswasa** | Shayṭān *beautifies* vice as nobility or wisdom | *"I will surely make [evil] fair-seeming to them"* (Q 15:39; cf. 8:48) |
| *ignatian* | vice framed via Scripture | **Shubha / Talbīs** | vice licensed by misused Qur'an/ḥadīth, out-of-context proof-texts, *fatwā*-shopping, weaponized *ikhtilāf* | the first false analogy: Iblīs's own *qiyās*, *"I am better than him"* (Q 7:12) |
| — | — | **Riyā'** *(new axis)* | the right act, done to be *seen* — corrupting intention | *"woe to those who pray to be seen"* (Q 107:4–6); *al-shirk al-aṣghar* (Aḥmad) |

The **Shubha** variant is the most interesting in the whole design. Early results from the reference
benchmark (see the companion Nemotron report) show models resist *Christian*-scripture-couched
temptations *easily* — the ornate, scripture-citing temptation was the one Nemotron found least
moving. Whether an **Islamically-literate** shubha — built from misused Qur'an, ḥadīth, and *live
fiqh disagreement* — behaves the same way is an open empirical question, and the one TaqwaBench is
uniquely positioned to answer. Grounding it in *Iblīs's* qiyās is not ornamental: the first sin in
creation was a *bad argument*, not an appetite.

## 5. Three things TaqwaBench does that VirtueBench cannot

**(a) The *niyyah* dimension — testing intention, not just action.**
VirtueBench scores *which* act. The **Riyā'** variant holds the *right* action fixed and varies the
*audience / intention* ("do the charitable thing — and make sure it's noticed"), so the probe becomes
*why*, not *what*. This needs a format extension beyond binary A/B (e.g. a paired
right-act/right-act item distinguished only by intention, or a follow-up that scores the stated
rationale for *ikhlāṣ* vs *riyā'*). This is the single biggest conceptual addition.

**(b) Madhab-aware ground truth.**
Each scenario is tagged **consensus (*ijmā'*)** or **contested (*ikhtilāf*)**. Scored items draw only
from the consensus pool or are annotated by school; contested matters are repurposed as *material for
the Shubha variant* (does the model exploit a genuine disagreement to license what the *maqāṣid*
forbid?). This turns Islam's legal pluralism from a liability into a test surface — and the method
generalizes to any tradition with internal pluralism.

**(c) *Maqāṣid*-grounded stakes.**
Scenario costs are defined against the five *ḍarūriyyāt* — preservation of *dīn* (religion), *nafs*
(life), *'aql* (intellect), *nasl* (lineage), and *māl* (property) — so "what's at stake" is
principled and gradable (necessity > need > embellishment) rather than ad hoc.

## 6. Sourcing & verification

Mirroring (and tightening) VirtueBench's patristic-citation verification, every scenario carries a
sourced anchor and passes an authenticity gate:

- **Qur'an** — cited by *sūrah:āyah*, checked against the text.
- **Ḥadīth** — cited by collection + number **with grading** (only *ṣaḥīḥ* / *ḥasan*); a *takhrīj*
  step rejects *ḍa'īf* / *mawḍū'* narrations. (Fabricated hadith would discredit the whole benchmark
  — this is the analog of, and stricter than, VirtueBench's citation check.)
- **Classical *akhlāq* corpus** — al-Ghazālī (*Iḥyā'*), Miskawayh (*Tahdhīb al-Akhlāq*), Ibn al-Qayyim
  (*Madārij al-Sālikīn*), al-Māwardī (*Adab al-Dunyā wa'l-Dīn*), al-Rāghib al-Iṣfahānī
  (*al-Dharī'a ilā Makārim al-Sharī'a*).
- **Scholarly review** — items reviewed by qualified scholars before release; lived realism in the
  *fiqh al-mu'āmalāt* (honesty in trade, *ghībah*, the neighbor's rights, *birr al-wālidayn*) rather
  than orientalist or sensational framings.

## 7. Open questions for discussion

- **Persona framing.** Place the model explicitly in a Muslim's shoes, or keep scenarios religiously
  legible but neutral and see whether it reasons *toward* the taqwā-consistent choice?
- **Sunni / Shia scope.** Start from the cross-school *ijmā'* core, then branch — or annotate
  throughout?
- **Format for the *niyyah* axis.** Paired-item design vs rationale-scoring vs a short structured
  "act + intention" answer — which is most robust to gaming?
- **Multilingual.** English-first, or Arabic-native with translation, given that much of the moral
  weight lives in untranslatable terms (*taqwā*, *iḥsān*, *ḥayā'*)?

## 8. Next steps

1. Author ~20 seed scenarios per virtue across the six variants, fully sourced and madhab-tagged
   (proof-of-concept; VirtueBench ships 150/virtue).
2. Build the *niyyah* / Riyā' item format and a scorer that reads intention, not just the letter.
3. Run the seed set across a model panel (frontier + open weights) to find where models'
   Islamic-moral profiles diverge.
4. Convene scholarly review before any public release.

---

*Note: the Islamic content in this draft is a working proposal authored for discussion and requires
review by qualified scholars before it is treated as authoritative.*
