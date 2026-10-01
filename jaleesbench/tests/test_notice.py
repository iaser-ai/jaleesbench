"""The English proof texts are third-party text: NOTICE and the root README must say so."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROOF_TEXTS = "jaleesbench/jaleesbench/data/proof_texts.json"


def _flat(name):
    return re.sub(r"\s+", " ", (ROOT / name).read_text())


def test_notice_names_an_existing_file():
    assert (ROOT / PROOF_TEXTS).is_file()
    assert PROOF_TEXTS in _flat("NOTICE")


def test_notice_attributes_and_excludes_the_english_text():
    notice = _flat("NOTICE")
    assert "sunnah.com" in notice
    assert "Riyad as-Salihin" in notice
    assert "Darussalam" in notice
    assert "NOT licensed under the Apache License, Version 2.0" in notice


def test_readme_points_to_the_notice():
    readme = _flat("README.md")
    assert PROOF_TEXTS in readme
    assert "sunnah.com" in readme
    assert "not** covered by the Apache-2.0 licence" in readme
    assert "(NOTICE)" in readme
