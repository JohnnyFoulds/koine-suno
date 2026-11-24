"""Tests for the token ledger and its gate-1 checks.

The fixtures are excerpts (John 1:1-5, John 14:6, 1 John 1:5) of MACULA
Greek (Clear Bible, Inc., CC BY 4.0) and MorphGNT SBLGNT (J. K. Tauber,
parsing CC BY-SA), laid out with the same paths as full checkouts.
"""

from pathlib import Path

import pytest

from koine_suno.ledger import build, norm
from koine_suno.ledger_cli import main

FIXTURES = Path(__file__).parent / "fixtures"
MACULA = FIXTURES / "macula"
MORPHGNT = FIXTURES / "morphgnt"


def ledger(spec):
    return build(spec, MACULA, MORPHGNT)


def test_norm_ignores_case_grave_and_punctuation():
    assert norm("Λόγος,") == norm("λόγος")
    assert norm("καὶ") == norm("καί")
    assert norm("δι’") == norm("δι")


def test_john_1_1_passes_every_check():
    entries = ledger("JHN 1:1")
    assert len(entries) == 17
    assert all(e.status == "PASS" for e in entries)
    assert [e.surface for e in entries][:5] == [
        "Ἐν",
        "ἀρχῇ",
        "ἦν",
        "ὁ",
        "Λόγος",
    ]


def test_john_1_3_punctuation_difference_is_flagged():
    entries = {e.ref: e for e in ledger("JHN 1:3")}
    assert entries["JHN 1:3!10"].status == "WARN"
    assert "punctuation" in entries["JHN 1:3!10"].issues[0]


def test_variant_outside_sung_span_does_not_fail():
    # SBLGNT adds an article before Ἰησοῦς; the span from Ἐγώ is identical.
    assert all(e.status != "FAIL" for e in ledger("JHN 14:6!4-13"))


def test_word_only_in_sblgnt_leaves_nestle_tokens_matched():
    # SBLGNT's extra article has no Nestle token, so nothing sung fails.
    entries = ledger("JHN 14:6")
    assert all(e.status != "FAIL" for e in entries)


def test_variant_inside_span_fails(tmp_path):
    # Copy the fixtures and change one SBLGNT word in John 1:1.
    import shutil

    macula = tmp_path / "macula"
    shutil.copytree(MACULA, macula)
    path = macula / "SBLGNT/tsv/macula-greek-SBLGNT.tsv"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, line in enumerate(lines):
        if "\tJHN 1:1!2\t" in line:
            lines[i] = line.replace("ἀρχῇ", "ἀρχῆς")
    path.write_text("".join(lines), encoding="utf-8")

    entries = {e.ref: e for e in build("JHN 1:1", macula, MORPHGNT)}
    assert entries["JHN 1:1!2"].status == "FAIL"
    assert "SBLGNT" in entries["JHN 1:1!2"].issues[0]


def test_missing_nestle_sense_falls_back_to_sblgnt():
    entries = {e.ref: e for e in ledger("1JN 1:5!14-24")}
    assert entries["1JN 1:5!17"].ln == "13.1"


def test_word_range_and_bad_spec():
    assert len(ledger("1JN 1:5!14-16")) == 3
    with pytest.raises(ValueError):
        ledger("John 1:1")


def test_cli_exit_code_and_json(tmp_path, capsys):
    out = tmp_path / "ledger.json"
    code = main(
        [
            "JHN 1:1",
            "--macula",
            str(MACULA),
            "--morphgnt",
            str(MORPHGNT),
            "--json",
            str(out),
        ]
    )
    assert code == 0
    assert out.exists()
    assert "17 tokens: 0 FAIL" in capsys.readouterr().out
