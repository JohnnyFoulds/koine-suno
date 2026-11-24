"""Greek orthography to 1st-century CE (Egyptian) Koine IPA.

This module is a Python port of the ``koi1`` period of Wiktionary's
``Module:grc-pronunciation`` and ``Module:grc-pronunciation/data``
(https://en.wiktionary.org/wiki/Module:grc-pronunciation), which are
licensed CC BY-SA 4.0. Only the first-century rules are ported; the other
periods (Classical Attic, later Koine, Byzantine) are out of scope.

The pipeline has three stages:

1. ``_units``: split a word into base letters, each carrying the set of
   combining diacritics (breathings, accents, diaeresis, iota subscript)
   that sit on it.
2. ``_phones``: walk the letters left to right and emit IPA phones,
   resolving diphthongs and the few context-sensitive consonant rules.
3. ``_syllabify``: group the phones into syllables using the same
   onset-maximisation rule as the Lua module, and mark the stressed one.

``tests/test_wiktionary_parity.py`` checks the output character for
character against IPA rendered by Wiktionary itself.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Combining diacritics, as they appear after Unicode NFD decomposition.
# ---------------------------------------------------------------------------
SMOOTH = "̓"  # smooth breathing  (ἀ)
ROUGH = "̔"  # rough breathing   (ἁ)
ACUTE = "́"  # acute accent, also the monotonic tonos (ά)
GRAVE = "̀"  # grave accent      (ὰ)
CIRCUM = "͂"  # circumflex        (ᾶ)
IOTA_SUB = "ͅ"  # iota subscript    (ᾳ)
DIAER = "̈"  # diaeresis         (ϊ): blocks a diphthong
MACRON = "̄"  # vowel-length marks; a marked vowel never
BREVE = "̆"  # starts a diphthong

ACCENTS = {ACUTE, GRAVE, CIRCUM}

# ---------------------------------------------------------------------------
# Letter classes used by the context rules (Module:grc-pronunciation/data).
# ---------------------------------------------------------------------------
VOWELS = set("αεηιουω")
DORSAL = set("γκχ")  # γ before these is the nasal [ŋ]
VOICED = set("βγδζλμνρ")  # σ before these is voiced to [z]
VOICED_STOP = set("βγδ")  # κ before these is voiced to [ɡ]
UNVOICED = set("θκπστφχ")  # αυ/ευ before these end in voiceless [ʍ]

# Single vowels. Vowel length had been lost by the first century, so long
# and short pairs merge (ο and ω are both [o]); η is a raised [e̝].
SIMPLE_VOWEL = {
    "α": "a",
    "ε": "e",
    "η": "e̝",
    "ι": "i",
    "ο": "o",
    "υ": "y",
    "ω": "o",
}

# Diphthongs ending in ι had become single vowels.
I_DIPHTHONG = {
    "α": "ɛ",  # αι
    "ε": "i",  # ει
    "η": "e̝",  # ηι (and ῃ)
    "ο": "y",  # οι
    "υ": "y",  # υι
    "ω": "o",  # ωι (and ῳ)
}

# Diphthongs ending in υ keep their first vowel plus a [w]/[ʍ] glide.
# ου is the exception: it had become the single vowel [u].
U_DIPHTHONG = {"α": "a", "ε": "e", "η": "e̝", "ω": "o"}

# Consonants with no context rule.
CONSONANT = {
    "β": "b",
    "δ": "d",
    "ζ": "z",
    "θ": "tʰ",
    "λ": "l",
    "μ": "m",
    "ν": "n",
    "π": "p",
    "ρ": "r",
    "τ": "t",
    "φ": "pʰ",
    "χ": "kʰ",
}

# ---------------------------------------------------------------------------
# IPA classes used by the syllabifier (the ``chars`` table of the module).
# ---------------------------------------------------------------------------
IPA_LIQUID = {"r", "l", "n"}
IPA_OBSTRUENT = {"b", "d", "ɡ", "k", "p", "t", "kʰ", "pʰ", "tʰ"}

# Punctuation kept in the output (Greek question mark and ano teleia are
# normalised to their English equivalents for lyric sheets).
PUNCTUATION = {
    ";": "?",
    ";": "?",
    "·": ",",
    "·": ",",
    ",": ",",
    ".": ".",
    "!": "!",
    ":": ":",
}

# Elision marks (κατ᾽, δ’) are dropped; the elided word joins the next.
ELISION = {"᾽", "’", "'", "ʼ", "᾿"}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class Unit:
    """One base Greek letter plus the combining marks attached to it."""

    base: str
    marks: set[str] = field(default_factory=set)


@dataclass
class Phone:
    """One IPA segment.

    ``stressed`` and ``rough`` are only meaningful on vowels: they record
    whether the vowel (or diphthong) carried an accent or a rough breathing.
    """

    ipa: str
    vowel: bool = False
    stressed: bool = False
    rough: bool = False


@dataclass
class Syllable:
    """A syllable: consonant onset, one vowel nucleus, consonant coda."""

    onset: list[Phone]
    nucleus: Phone
    coda: list[Phone]

    @property
    def stressed(self) -> bool:
        return self.nucleus.stressed

    def ipa(self, keep_h: bool = True) -> str:
        """Render as IPA, with a leading stress mark when stressed.

        A rough breathing is written ``(h)``: Wiktionary marks it as
        optional because /h/ was being lost in first-century Egypt.
        """
        h = "(h)" if (self.nucleus.rough and keep_h) else ""
        onset = "".join(p.ipa for p in self.onset)
        coda = "".join(p.ipa for p in self.coda)
        stress = "ˈ" if self.stressed else ""
        return stress + onset + h + self.nucleus.ipa + coda


@dataclass
class Word:
    """A transcribed word and any punctuation that followed it."""

    greek: str
    syllables: list[Syllable]
    trailing: str = ""

    def ipa(self, keep_h: bool = True) -> str:
        """Render as IPA with Wiktionary's conventions.

        Syllables are separated by ``.``, except that the stress mark
        itself serves as the separator before a stressed syllable.
        """
        out = ""
        for i, syllable in enumerate(self.syllables):
            part = syllable.ipa(keep_h)
            if i and not part.startswith("ˈ"):
                out += "."
            out += part
        return out


# ---------------------------------------------------------------------------
# Stage 1: letters
# ---------------------------------------------------------------------------
def _units(word: str) -> list[Unit]:
    """Split a word into base letters with their diacritics.

    Double letters are expanded the way the Lua module does it:
    ξ -> κσ and ψ -> πσ. Final sigma is folded into σ.
    """
    text = unicodedata.normalize("NFD", word.lower()).replace("ς", "σ")
    units: list[Unit] = []
    for ch in text:
        if unicodedata.combining(ch):
            if units:
                units[-1].marks.add(ch)
        elif ch == "ξ":
            units += [Unit("κ"), Unit("σ")]
        elif ch == "ψ":
            units += [Unit("π"), Unit("σ")]
        elif "α" <= ch <= "ω":
            units.append(Unit(ch))
        # Anything else (Latin letters, digits) is ignored.
    return units


def _base(units: list[Unit], i: int) -> str:
    """Base letter at index ``i``, or ``""`` when out of range."""
    return units[i].base if 0 <= i < len(units) else ""


# ---------------------------------------------------------------------------
# Stage 2: phones
# ---------------------------------------------------------------------------
def _can_start_diphthong(first: Unit, second: Unit | None) -> bool:
    """A vowel pair is a diphthong unless split by a diaeresis or a
    vowel-length mark on the first vowel."""
    return (
        second is not None
        and DIAER not in second.marks
        and MACRON not in first.marks
        and BREVE not in first.marks
    )


def _u_glide(units: list[Unit], i: int) -> str:
    """Glide for the υ-diphthong starting at ``i``.

    Voiceless [ʍ] before a voiceless consonant, otherwise [w]; σ followed
    by a voiced consonant counts as voiced (σ itself becomes [z] there).
    """
    after, after2 = _base(units, i + 2), _base(units, i + 3)
    if after == "σ" and after2 in VOICED:
        return "w"
    if after in UNVOICED:
        return "ʍ"
    return "w"


def _vowel_phone(ipa: str, marks: set[str]) -> Phone:
    return Phone(
        ipa,
        vowel=True,
        stressed=bool(marks & ACCENTS),
        rough=ROUGH in marks,
    )


def _consonant(units: list[Unit], i: int) -> tuple[str, int]:
    """IPA for the consonant at ``i`` and how many letters it consumes."""
    letter, nxt = units[i].base, _base(units, i + 1)
    if letter == "γ":
        return ("ŋ" if nxt in DORSAL else "ɡ"), 1
    if letter == "κ":
        return ("ɡ" if nxt in VOICED_STOP else "k"), 1
    if letter == "σ":
        return ("z" if nxt in VOICED else "s"), 1
    if letter == "τ" and nxt in ("σ", "ζ"):
        # τσ / τζ are read as one affricate.
        voiced = _base(units, i + 2) in VOICED
        return ("dz" if voiced else "ts"), 2
    return CONSONANT[letter], 1


def _phones(units: list[Unit]) -> list[Phone]:
    """Convert letters to IPA phones (first-century rules)."""
    phones: list[Phone] = []
    i = 0
    while i < len(units):
        unit = units[i]
        letter = unit.base

        if letter not in VOWELS:
            ipa, step = _consonant(units, i)
            phones.append(Phone(ipa))
            i += step
            continue

        second = units[i + 1] if i + 1 < len(units) else None
        if _can_start_diphthong(unit, second):
            # Accents and breathings sit on the second vowel of a
            # diphthong (εἰ, αὐ), so merge both units' marks.
            marks = unit.marks | second.marks
            if second.base == "ι" and letter in I_DIPHTHONG:
                phones.append(_vowel_phone(I_DIPHTHONG[letter], marks))
                i += 2
                continue
            if second.base == "υ" and letter == "ο":
                phones.append(_vowel_phone("u", marks))
                i += 2
                continue
            if second.base == "υ" and letter in U_DIPHTHONG:
                phones.append(_vowel_phone(U_DIPHTHONG[letter], marks))
                phones.append(Phone(_u_glide(units, i)))
                i += 2
                continue

        # A plain vowel. An iota subscript (ᾳ ῃ ῳ) is silent by now.
        phones.append(_vowel_phone(SIMPLE_VOWEL[letter], unit.marks))
        i += 1
    return phones


# ---------------------------------------------------------------------------
# Stage 3: syllables
# ---------------------------------------------------------------------------
def _syllable_end(phones: list[Phone], vowel: int, next_vowel: int) -> int:
    """Index of the last phone of the syllable whose nucleus is ``vowel``.

    Same rule as ``find_syllable_break`` in the Lua module: the next
    syllable takes one consonant as its onset, or two when they are an
    obstruent followed by a liquid (muta cum liquida: κλ, θρ, τν).
    """
    cluster = list(range(vowel + 1, next_vowel))
    if not cluster:  # vowels in hiatus
        return vowel
    if (
        len(cluster) >= 2
        and phones[cluster[-1]].ipa in IPA_LIQUID
        and phones[cluster[-2]].ipa in IPA_OBSTRUENT
    ):
        onset_size = 2
    else:
        onset_size = 1
    if len(cluster) <= onset_size:  # whole cluster is the onset
        return vowel
    return cluster[-onset_size - 1]


def _syllabify(phones: list[Phone]) -> list[Syllable]:
    """Group phones into syllables around each vowel nucleus."""
    vowels = [i for i, p in enumerate(phones) if p.vowel]
    if not vowels:
        return []
    syllables: list[Syllable] = []
    start = 0
    for k, vowel in enumerate(vowels):
        if k + 1 < len(vowels):
            end = _syllable_end(phones, vowel, vowels[k + 1])
        else:
            end = len(phones) - 1  # last syllable takes the rest
        syllables.append(
            Syllable(
                onset=phones[start:vowel],
                nucleus=phones[vowel],
                coda=phones[vowel + 1 : end + 1],
            )
        )
        start = end + 1
    return syllables


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def transcribe(text: str) -> list[Word]:
    """Transcribe Greek text into syllabified words.

    Accepts polytonic or monotonic Greek. Words are split on whitespace;
    punctuation is attached to the preceding word as ``Word.trailing``.
    """
    words: list[Word] = []
    token = ""

    def flush(trailing: str = "") -> None:
        nonlocal token
        if token:
            syllables = _syllabify(_phones(_units(token)))
            if syllables:
                words.append(Word(token, syllables, trailing))
            token = ""
        elif trailing and words:
            words[-1].trailing += trailing

    for ch in unicodedata.normalize("NFC", text):
        if ch in PUNCTUATION:
            flush(PUNCTUATION[ch])
        elif ch.isspace():
            flush()
        elif ch not in ELISION:
            token += ch
    flush()
    return words


def to_ipa(text: str, keep_h: bool = True) -> str:
    """Transcribe Greek text to first-century Koine IPA."""
    return " ".join(w.ipa(keep_h) + w.trailing for w in transcribe(text))
