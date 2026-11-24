# The ledger and its checks

`koine-ledger` exists because nobody checks the sung Greek by hand. The
person learning from the songs cannot yet judge Greek, and the songs are
written with an AI, so correctness has to come from sources, not from anyone's
knowledge. The rule is that nothing is composed: every sung Greek word is
copied from a critical edition, and every judgement about it comes from
published annotation made by scholars, checked by a second source.

## Data

| Source | What it supplies | Licence |
|---|---|---|
| MACULA Greek, Nestle 1904 [1] | The sung text; parse; Louw–Nida sense; gloss | Text public domain; annotation CC BY 4.0 |
| MACULA Greek, SBLGNT [1] | A second edition for variant and punctuation checks; second sense annotation | SBLGNT EULA; annotation CC BY 4.0 |
| MorphGNT SBLGNT [2] | An independent parse and lemma for every SBLGNT word | Parsing CC BY-SA |

Nestle 1904 is used for the sung text because it is in the public domain.
SBLGNT is used only for comparison.

## Algorithm

For each verse in the requested span:

1. Read the Nestle 1904 words from MACULA.
2. Normalise every word for comparison: lower case, grave folded to acute,
   letters and diacritics only (punctuation and elision marks removed).
3. Align the Nestle words with the SBLGNT words, and separately with the
   MorphGNT words, using a longest-matching-block alignment
   (`difflib.SequenceMatcher`). Only letter-identical words align.
4. For each Nestle word in the span:
   - **Text.** No letter-identical SBLGNT word: FAIL. The word sits in a
     variant unit and is not sung.
   - **Sense.** Louw–Nida sense from Nestle; if absent, from SBLGNT (noted);
     two different senses: WARN; none: WARN.
   - **Punctuation.** Different punctuation after the word: WARN. Editions
     sometimes divide sentences differently (John 1:3–4), which changes the
     meaning of the words around the break.
   - **Morphology.** Lemma and each grammatical feature must match the aligned
     MorphGNT word: FAIL on any difference.

A word that SBLGNT has and Nestle lacks does not fail anything, because it is
not sung. A FAIL is never adjudicated: the passage is replaced.

## What it does not check

- Whether the English around a Greek chunk implies the right meaning or the
  right grammatical function. That is gate 2, done against BDAG and
  Louw–Nida and recorded in the song's ledger notes.
- How Suno sings it. That needs listening.

## References

[1] Clear Bible, Inc., *MACULA Greek Linguistic Datasets*.
https://github.com/Clear-Bible/macula-greek

[2] J. K. Tauber, Ed., *MorphGNT: SBLGNT Edition*, doi:
10.5281/zenodo.376200. https://github.com/morphgnt/sblgnt
