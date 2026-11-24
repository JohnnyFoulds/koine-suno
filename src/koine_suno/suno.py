"""Koine syllables to English-orthography respellings for Suno.

Suno has no phonetic notation. It predicts pronunciation from spelling, and
its strongest priors are English. Each Koine phone is therefore written with
the English spelling least likely to be misread:

* open syllables use long-vowel digraphs (``ah``, ``eh``, ``ee``, ``oh``,
  ``oo``, ``ay``) so a vowel is never read as a short English vowel;
* the stressed syllable is capitalised and syllables are hyphenated;
* word-final /s/ after a vowel is written ``ss`` so it is not voiced to /z/;
* /ɡ/ before a front vowel is written ``gh`` so it is not softened (gem);
* the aspirates /pʰ tʰ kʰ/ are written plain ``p t k``. Writing ``ph``,
  ``th`` or ``ch`` would make Suno sing /f/, /θ/ or /tʃ/, and English
  initial voiceless stops are aspirated anyway.

Per-word overrides take precedence over the rules, so a spelling that fails
by ear can be fixed without changing the rules for every other word.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from .ipa import Phone, Syllable, Word, transcribe

# Vowels before which /ɡ/ must be written "gh".
FRONT_VOWELS = {"e", "e̝", "ɛ", "i", "y"}

# Consonant spellings. Aspiration is dropped (see the module docstring) and
# the velar nasal [ŋ] is written "n": before g/k English already reads
# "ng"/"nk" as [ŋɡ]/[ŋk].
CONSONANT = {
    "p": "p",
    "pʰ": "p",
    "t": "t",
    "tʰ": "t",
    "k": "k",
    "kʰ": "k",
    "b": "b",
    "d": "d",
    "ɡ": "g",
    "z": "z",
    "s": "s",
    "l": "l",
    "m": "m",
    "n": "n",
    "ŋ": "n",
    "r": "r",
    "w": "w",
    "ʍ": "w",
    "ts": "ts",
    "dz": "dz",
}

# Vowel plus [w]/[ʍ] glide (αυ, ευ, ηυ, ωυ). "ow" as in "cow" is a close
# match for [aw]; the others have no English word to lean on.
GLIDE_VOWEL = {"a": "ow", "e": "ehw", "e̝": "ayw", "o": "ohw"}


@dataclass
class SunoOptions:
    """Respelling options.

    y:
        Spelling for /y/ (υ, οι). ``"ü"`` is the accurate default;
        ``"ee"`` is the fallback if Suno cannot sing it (it matches the
        later Byzantine merger of /y/ with /i/); ``"ew"`` is a compromise.
    keep_h:
        Sing a rough breathing as ``h``. Off by default because /h/ was
        being lost in first-century Koine.
    caps:
        Capitalise the stressed syllable of polysyllabic words.
    sep:
        Syllable separator.
    overrides:
        Fixed spellings keyed by lower-case NFC Greek word.
    """

    y: str = "ü"
    keep_h: bool = False
    caps: bool = True
    sep: str = "-"
    overrides: dict[str, str] = field(default_factory=dict)


def _spell_vowel(
    nucleus: Phone, coda: list[Phone], opts: SunoOptions
) -> tuple[str, list[Phone]]:
    """Spell the nucleus; return the spelling and the remaining coda.

    A leading [w]/[ʍ] in the coda belongs to a diphthong and is consumed
    here. Closed syllables (with a coda) use the short spelling for e and
    o, because "ek", "en", "loss" already read correctly in English.
    """
    vowel = nucleus.ipa
    if coda and coda[0].ipa in ("w", "ʍ"):
        return GLIDE_VOWEL[vowel], coda[1:]

    closed = bool(coda)
    if vowel == "a":
        # "ar" reads as [ɑr]; "ahr" would look like a typo to the model.
        return ("a" if coda and coda[0].ipa == "r" else "ah"), coda
    if vowel in ("e", "ɛ"):
        return ("e" if closed else "eh"), coda
    if vowel == "o":
        return ("o" if closed else "oh"), coda
    spelling = {"e̝": "ay", "i": "ee", "u": "oo", "y": opts.y}
    return spelling.get(vowel, vowel), coda


def _spell_consonants(phones: list[Phone], next_vowel: str | None) -> str:
    """Spell a consonant sequence, hardening /ɡ/ before front vowels."""
    out = []
    for i, phone in enumerate(phones):
        if i + 1 < len(phones):
            following = phones[i + 1].ipa
        else:
            following = next_vowel
        if phone.ipa == "ɡ" and following in FRONT_VOWELS:
            out.append("gh")
        else:
            out.append(CONSONANT.get(phone.ipa, phone.ipa))
    return "".join(out)


def _spell_syllable(
    syllable: Syllable, opts: SunoOptions, word_final: bool
) -> str:
    onset = _spell_consonants(syllable.onset, syllable.nucleus.ipa)
    rough = syllable.nucleus.rough and opts.keep_h and not syllable.onset
    vowel, coda = _spell_vowel(syllable.nucleus, syllable.coda, opts)
    coda_spelling = _spell_consonants(coda, None)

    # Word-final /s/ after a vowel or sonorant becomes "ss" (λόγος ->
    # LOH-goss, not LOH-goz). After k/p/t the cluster (ξ, ψ, -ts) is
    # already read as voiceless, so it is left alone.
    if (
        word_final
        and coda
        and coda[-1].ipa == "s"
        and (len(coda) == 1 or coda[-2].ipa not in ("k", "p", "t"))
    ):
        coda_spelling += "s"

    return onset + ("h" if rough else "") + vowel + coda_spelling


def word_to_suno(word: Word, opts: SunoOptions) -> str:
    """Respell one transcribed word."""
    key = word.greek.lower()
    if key in opts.overrides:
        return opts.overrides[key]

    count = len(word.syllables)
    parts = []
    for i, syllable in enumerate(word.syllables):
        part = _spell_syllable(syllable, opts, word_final=(i == count - 1))
        # Monosyllables are left in lower case: with one syllable there is
        # nothing to contrast, and all-caps words read as shouting.
        if opts.caps and syllable.stressed and count > 1:
            part = part.upper()
        parts.append(part)
    return opts.sep.join(parts)


def to_suno(text: str, opts: SunoOptions | None = None) -> str:
    """Convert Greek text to a Suno respelling, preserving line breaks."""
    opts = opts or SunoOptions()
    lines = []
    for line in text.splitlines() or [text]:
        words = transcribe(line)
        lines.append(
            " ".join(word_to_suno(w, opts) + w.trailing for w in words)
        )
    return "\n".join(lines)


def breakdown(text: str, opts: SunoOptions | None = None) -> list[dict]:
    """Per-word rows of Greek, first-century IPA and Suno spelling."""
    opts = opts or SunoOptions()
    return [
        {"greek": w.greek, "ipa": w.ipa(), "suno": word_to_suno(w, opts)}
        for w in transcribe(text)
    ]


def load_overrides(path: str | Path | None) -> dict[str, str]:
    """Load a JSON object of ``{"greek word": "spelling"}`` overrides."""
    if not path:
        return {}
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        unicodedata.normalize("NFC", greek).lower(): spelling
        for greek, spelling in raw.items()
    }
