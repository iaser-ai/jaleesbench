# air-39 thread — attribute the English proof texts (issue #39)

## 2026-10-01 — implement

Done: `NOTICE` at the repo root, a `## Licence` section in the root README, a small
test (`jaleesbench/tests/test_notice.py`) that the two documents name the data file, the
source and the exclusion. `codev/state/main.md` removed from the index only
(`git rm --cached`); the file is still on disk and the existing ignore rule covers it.
No change to `proof_texts.json` or the benchmark code.

What checking sunnah.com's attribution found (live site returns 403 to scripted
requests; read through the Internet Archive snapshot of 2026-07-20):

- sunnah.com does **not** name the translator or publisher of its Riyad as-Salihin
  English. Its About page says: "For the English we use various translators, a full list
  of which will appear here shortly". So the NOTICE says exactly that, and gives the
  Darussalam identification as a correspondence, not as something sunnah.com states.
  I did not compare the text against a printed Darussalam copy.
- The same About page (section 8) says: "We do not permit the scraping of our data, nor
  mass reproduction of entire books or collections on other websites … Reproducing
  individual hadith or selections of hadith for a teaching/didactic/presentation purpose
  is permitted." `proof_texts.json` holds all 1,896 hadith of the collection — the whole
  book. The owner's decision (attribute and exclude, do not remove) stands and is what
  this PR does; flagged to the architect because it bears on that decision.

Hazard for whoever merges: because the PR deletes `codev/state/main.md` from the index,
a `git pull` in any other checkout removes that checkout's working copy of the file
(or refuses to pull if it has local edits). Copy it aside before pulling and put it
back after.
