"""Token ledger and gate-1 checks for sung Greek.

Every Greek token that a song sings must be traceable to a critical edition
and to published linguistic annotation. This module builds a ledger for a
span of the New Testament and checks it mechanically:

* **Text.** The sung text is Nestle 1904 (public domain), read from the
  MACULA Greek dataset. Each token must be letter-identical in SBLGNT, so
  that no sung word sits in a variant unit. Comparison ignores case,
  grave versus acute accent, punctuation and elision marks only.
* **Morphology.** The MACULA parse of each token must agree with the
  independent MorphGNT parse of the same SBLGNT token (lemma, case,
  number, gender, person, tense, voice, mood).
* **Sense.** Each token must carry a Louw-Nida sense from MACULA; a
  different sense for the aligned SBLGNT token is reported as a warning.

Disagreement is never adjudicated: a failing token means the passage is not
used. Data sources (not bundled; see the README for how to fetch them):

* MACULA Greek, Clear Bible, Inc., CC BY 4.0:
  ``Nestle1904/tsv/macula-greek-Nestle1904.tsv`` and
  ``SBLGNT/tsv/macula-greek-SBLGNT.tsv``.
* MorphGNT SBLGNT, J. K. Tauber (ed.), parsing CC BY-SA:
  ``<nn>-<Book>-morphgnt.txt``.
"""

from __future__ import annotations

import csv
import difflib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .ipa import to_ipa
from .suno import to_suno

# USFM book codes in NT order; MorphGNT numbers the books 01-27 likewise.
BOOKS = (
    "MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI "
    "TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV"
).split()

# MACULA feature words -> MorphGNT parse letters. MorphGNT's parse code has
# eight positions: person, tense, voice, mood, case, number, gender, degree.
FEATURES = {
    "person": (0, {"first": "1", "second": "2", "third": "3"}),
    "tense": (
        1,
        {
            "present": "P",
            "imperfect": "I",
            "future": "F",
            "aorist": "A",
            "perfect": "X",
            "pluperfect": "Y",
        },
    ),
    "voice": (2, {"active": "A", "middle": "M", "passive": "P"}),
    "mood": (
        3,
        {
            "indicative": "I",
            "imperative": "D",
            "subjunctive": "S",
            "optative": "O",
            "infinitive": "N",
            "participle": "P",
        },
    ),
    "case": (
        4,
        {
            "nominative": "N",
            "genitive": "G",
            "dative": "D",
            "accusative": "A",
            "vocative": "V",
        },
    ),
    "number": (5, {"singular": "S", "plural": "P"}),
    "gender": (6, {"masculine": "M", "feminine": "F", "neuter": "N"}),
}

SPEC = re.compile(
    r"^(?P<book>[1-3]?[A-Z]{2,3})\s+(?P<ch>\d+):(?P<v1>\d+)"
    r"(?:-(?P<v2>\d+))?(?:!(?P<w1>\d+)(?:-(?P<w2>\d+))?)?$"
)


def norm(word: str) -> str:
    """Comparison key: lower case, grave folded to acute, letters only."""
    text = unicodedata.normalize("NFD", word.lower()).replace("̀", "́")
    kept = "".join(
        ch for ch in text if ch.isalpha() or unicodedata.combining(ch)
    )
    return unicodedata.normalize("NFC", kept)


@dataclass
class Entry:
    """One sung token and the result of its checks."""

    ref: str
    surface: str
    sblgnt: str
    lemma: str
    morph: str
    ln: str
    gloss: str
    ipa: str
    suno: str
    status: str = "PASS"
    issues: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.status = "FAIL"
        self.issues.append(message)

    def warn(self, message: str) -> None:
        if self.status == "PASS":
            self.status = "WARN"
        self.issues.append(message)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _parse_spec(
    spec: str,
) -> tuple[str, int, int, int, int | None, int | None]:
    match = SPEC.match(spec.strip())
    if not match or match["book"] not in BOOKS:
        raise ValueError(
            f"bad reference {spec!r}; use e.g. 'JHN 1:1', 'JHN 1:1-5' "
            "or '1JN 4:8!8-11' (word range in one verse)"
        )
    v1 = int(match["v1"])
    v2 = int(match["v2"] or v1)
    w1 = int(match["w1"]) if match["w1"] else None
    w2 = int(match["w2"] or match["w1"]) if match["w1"] else None
    if w1 is not None and v1 != v2:
        raise ValueError("a word range is only allowed within one verse")
    return match["book"], int(match["ch"]), v1, v2, w1, w2


def _macula_verses(path: Path, book: str) -> dict[str, list[dict]]:
    """Rows of one book from a MACULA TSV, grouped by 'BOOK c:v'."""
    verses: dict[str, list[dict]] = {}
    prefix = book + " "
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["ref"].startswith(prefix):
                verse = row["ref"].split("!")[0]
                verses.setdefault(verse, []).append(row)
    return verses


def _morphgnt_verses(directory: Path, book: str) -> dict[str, list[dict]]:
    """MorphGNT tokens of one book, grouped by 'BOOK c:v'."""
    number = f"{BOOKS.index(book) + 1:02d}"
    files = sorted(directory.glob("*-morphgnt.txt"))
    verses: dict[str, list[dict]] = {}
    for path in files:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                cols = line.split()
                if len(cols) < 7 or not cols[0].startswith(number):
                    continue
                ref = f"{book} {int(cols[0][2:4])}:{int(cols[0][4:6])}"
                verses.setdefault(ref, []).append(
                    {"parse": cols[2], "word": cols[4], "lemma": cols[6]}
                )
    return verses


def _align(a: list[str], b: list[str]) -> dict[int, int]:
    """Map positions in ``a`` to letter-identical positions in ``b``."""
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    mapping: dict[int, int] = {}
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            mapping[block.a + k] = block.b + k
    return mapping


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def _check_parse(entry: Entry, row: dict, mg: dict) -> None:
    if norm(row["lemma"]) != norm(mg["lemma"]):
        entry.fail(f"lemma: MACULA {row['lemma']} vs MorphGNT {mg['lemma']}")
    for feature, (position, letters) in FEATURES.items():
        value = row.get(feature, "")
        if not value:
            continue
        expected = letters.get(value)
        found = mg["parse"][position]
        if expected is None:
            entry.warn(f"{feature}: unmapped MACULA value {value!r}")
        elif expected != found:
            entry.fail(
                f"{feature}: MACULA {value} vs MorphGNT {found} "
                f"({mg['parse']})"
            )


def _check_sense(entry: Entry, row: dict, srow: dict) -> None:
    """Louw-Nida sense: Nestle annotation first, SBLGNT as fallback.

    A sense present in only one edition is used and noted; two different
    senses are a warning, because the meaning the song implies must then
    be checked by hand against BDAG and Louw-Nida.
    """
    ln, sln = row.get("ln", ""), srow.get("ln", "")
    if ln and sln and ln != sln:
        entry.warn(f"sense: Nestle LN {ln} vs SBLGNT LN {sln}")
    elif not ln and sln:
        entry.ln = sln
        entry.issues.append(f"sense: LN {sln} taken from SBLGNT annotation")
    elif not ln:
        entry.warn("sense: no Louw-Nida sense in either edition")


def _check_punctuation(entry: Entry, row: dict, srow: dict) -> None:
    """Different punctuation after a word can change the sentence.

    John 1:3-4 is the classic case: the editions put the sentence break
    before or after ``ho gegonen``. Any difference is reported so the
    lyric sheet can gloss both readings.
    """
    after = row.get("after", "").strip()
    safter = srow.get("after", "").strip()
    if after != safter:
        entry.warn(
            f"punctuation: Nestle {after or 'none'!r} vs "
            f"SBLGNT {safter or 'none'!r}"
        )


def build(spec: str, macula: str | Path, morphgnt: str | Path) -> list[Entry]:
    """Build and check the ledger for a reference such as 'JHN 1:1-5'."""
    book, chapter, v1, v2, w1, w2 = _parse_spec(spec)
    macula = Path(macula)
    n1904 = _macula_verses(
        macula / "Nestle1904/tsv/macula-greek-Nestle1904.tsv", book
    )
    sbl = _macula_verses(macula / "SBLGNT/tsv/macula-greek-SBLGNT.tsv", book)
    mgnt = _morphgnt_verses(Path(morphgnt), book)

    entries: list[Entry] = []
    for verse_no in range(v1, v2 + 1):
        verse = f"{book} {chapter}:{verse_no}"
        rows = n1904.get(verse)
        if not rows:
            raise ValueError(f"{verse} not found in Nestle 1904")
        keys = [norm(r["text"]) for r in rows]
        to_sbl = _align(keys, [norm(r["text"]) for r in sbl.get(verse, [])])
        to_mg = _align(keys, [norm(m["word"]) for m in mgnt.get(verse, [])])

        lo = (w1 or 1) - 1
        hi = w2 or len(rows)
        for i in range(lo, hi):
            row = rows[i]
            entry = Entry(
                ref=row["ref"],
                surface=row["text"],
                sblgnt="",
                lemma=row["lemma"],
                morph=row["morph"],
                ln=row["ln"],
                gloss=row["gloss"],
                ipa=to_ipa(row["text"]),
                suno=to_suno(row["text"]),
            )
            if i in to_sbl:
                srow = sbl[verse][to_sbl[i]]
                entry.sblgnt = srow["text"]
                _check_sense(entry, row, srow)
                _check_punctuation(entry, row, srow)
            else:
                entry.fail("text: not letter-identical in SBLGNT")
            if i in to_mg:
                _check_parse(entry, row, mgnt[verse][to_mg[i]])
            else:
                entry.fail("morphology: no aligned MorphGNT token")
            entries.append(entry)
    return entries


def as_dicts(entries: list[Entry]) -> list[dict]:
    return [asdict(e) for e in entries]
