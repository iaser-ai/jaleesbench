# air-11 — Probe bank v4: register + wasatiyya tags, RS-policy realignment (issue #11)

## Implement

All wording in issue #11 is Waleed-approved; applied verbatim. Changes:

- `probes.json` → v4: `register` + `wasatiyya` tags on all 140 probes
  (126/9/3/2 and 107/28/5, generated from the appendix table and asserted at
  apply time); 5 C1a citation relabels; JLS-100 corrective rewritten (C3); six
  C4 correctives rewritten (103, 133, 106, 137, 109, 079); JLS-103 anchor text
  (Nawawī bab-261 prose) added — that probe previously had an empty
  proof-texts body, only a corrective. Exactly 12 `proof_texts` changed
  (verified via diff); no turn1/pressure text touched.
- `probes_ar.json`: tags mirrored id-for-id, texts untouched, version stays 2
  (per scope — note: the Arabic bank's English correctives now lag the v4
  realignment; flagged in the PR body for the architect).
- `docs/jaleesbench-design.md`: bab-211 ḍaʿīf disclosure appended to the
  gradings-filter sentence (design doc is where that sentence lives; there is
  no docs/jaleesbench-source.md).
- Root `README.md`: Neutrality contract paragraph at the end of "How it works".
- `prompts.py`: `GUIDE_V4_ADDENDUM` + `REGISTER_OVERLAY` constants, dormant —
  not referenced by GUIDE/FRAMINGS/judge_blocks; a test pins the dormancy.
- Tests: `test_probe_bank_v4_tags` (validity + tallies + AR mirror),
  `test_v4_prompt_additions_dormant`; version pin removed from the v3 retag
  test (superseded by the v4 pin).

Serialization preserved byte-for-byte conventions: probes.json indent=1,
probes_ar.json indent=2, ensure_ascii=False, no trailing newline.

73/73 tests pass. docs/paper/ untouched (architect re-judges C4 post-merge).
