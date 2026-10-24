# air-54 — JaleesWeights paper: bring the tex up to date with the released code and data

## 2026-10-23 — implement

Scope (issue #54): cite the JaleesBench arXiv paper, add artefact pointers (code, data release, tutorial), reconcile statements the release contradicts, rebuild the PDF. No number re-run, nothing spent.

What I found before editing:
- The baseline tex (commit 5f9c933) builds clean with `latexmk -xelatex` at 9 pages. All five tables already float to the end of the document, after the appendix; that is pre-existing and I left it alone.
- `plainnat` does not print `eprint` fields, so adding the arXiv id to the bib entry alone leaves it invisible. I put the id in `howpublished` as a hyperlink.
- The release README says the two paired bootstrap intervals quoted in the paper came from unseeded code; the seeded released step gives `[+0.144, +0.306]` and `[+0.210, +0.389]`. I kept the paper's numbers and added one sentence in the new Data subsection saying this.
- No trained weights are released anywhere (README is explicit). The paper never claimed they were, but a reader of "JaleesWeights" would assume it, so the Availability section says so in its opening paragraph.
- The pool question: the JaleesBench main run now has 14 subjects; Inkling is still the best open base model bare, so the "past the best open base model" claim stands.

What changed in the tex: header comment; orienting paragraphs for Method and Results (the writing rules require one per section; those two sections had none); `\citep{jaleesbench2026}` at the point of measurement in §2.1; §2.4 Models now says Gemma trained on a B200 and was served from an H200 via Modal, and Tinker served Inkling-Small; new §5 Availability (Code / Data / Tutorial) before the Conclusion. Bib: `jaleesbench2026` gains eprint/primaryClass/howpublished; the old repo-URL note is dropped because the Availability section carries the URL.

Rebuilt PDF: 10 pages (one more than before, from the new section), zero LaTeX errors, zero bibtex warnings, zero overfull boxes.

Left for Waleed: the "under $100" cost claim (README puts the 4-bit chain at ~$110 and the bf16 run of record at a $60–80 budget, cost not recorded separately); the floats-at-end layout; whether the mini paper should be rebuilt since it shares the bib entry.

## 2026-10-24 — review fix from architect

§5.2 listed the two seeded paired intervals in the reverse order of §3.1 and without saying which was which. Now: `[+0.210, +0.389]` for Inkling-Small stage 1 over base, then `[+0.144, +0.306]` for Gemma stage 2 over stage 1, matching §3.1's order. The extra words pushed the references onto a new page, so two sentences in the same subsection were shortened (checksums/install, licence notice) to keep the paper at 10 pages. Rebuilt clean. Holding for the pr gate.
