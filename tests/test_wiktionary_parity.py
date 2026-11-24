"""Tests for koine-suno.

``wiktionary_koi1_ref.json`` holds IPA rendered by Wiktionary itself: each
word was expanded as ``{{grc-IPA|<word>|period=koi1}}`` through the
en.wiktionary.org ``expandtemplates`` API on 2026-11-24. The port must
reproduce it exactly.
"""

import json
from pathlib import Path

import pytest

from koine_suno import SunoOptions, to_ipa, to_suno
from koine_suno.cli import main

REFERENCE_FILE = Path(__file__).parent / "wiktionary_koi1_ref.json"
REFERENCE = json.loads(REFERENCE_FILE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("word,expected", sorted(REFERENCE.items()))
def test_ipa_matches_wiktionary(word, expected):
    assert to_ipa(word) == expected


@pytest.mark.parametrize(
    "greek,expected",
    [
        ("πνεῦμα", "PNEHW-mah"),
        ("λόγος", "LOH-goss"),
        ("μετάνοια", "meh-TAH-nü-ah"),
        ("ἐκκλησία", "ek-klay-SEE-ah"),
        ("ἁμαρτία", "ah-mar-TEE-ah"),
        ("σάρξ", "sarks"),
        ("χάρις", "KAH-reess"),
        ("εἰρήνη", "ee-RAY-nay"),
        ("δόξα", "DOK-sah"),
        ("ἄγγελος", "AHN-gheh-loss"),
    ],
)
def test_suno_spelling(greek, expected):
    assert to_suno(greek) == expected


def test_line_breaks_and_punctuation_are_preserved():
    text = "τὸ πνεῦμα ὅπου θέλει πνεῖ,\nἐν ἀρχῇ ἦν ὁ λόγος."
    assert to_suno(text) == (
        "toh PNEHW-mah OH-poo TEH-lee pnee,\n" "en ar-KAY ayn oh LOH-goss."
    )


def test_y_fallback():
    assert to_suno("μετάνοια", SunoOptions(y="ee")) == "meh-TAH-nee-ah"


def test_override_wins():
    opts = SunoOptions(overrides={"πνεῦμα": "PNEV-mah"})
    assert to_suno("τὸ πνεῦμα", opts) == "toh PNEV-mah"


def test_cli_table(capsys):
    main(["--table", "δόξα"])
    assert capsys.readouterr().out.split() == ["δόξα", "ˈdok.sa", "DOK-sah"]
