# Using the output in Suno

The IPA is checked against Wiktionary. Whether Suno sings the respelling the
way it is meant to depends on the model, the voice and the melody, so every
new word needs a listening check.

## Workflow

1. **Generate the spellings.**

   ```console
   koine-suno --table < lyrics.txt     # check word by word
   koine-suno < lyrics.txt > suno.txt  # paste into Suno's lyrics box
   ```

2. **Render a short test section first.** Use one verse with every Greek
   word of the song in it. Change one thing at a time, otherwise you cannot
   tell which change fixed a word.

3. **Listen against a reference.** Compare against the IPA from
   `koine-suno --ipa`, or against recorded Koine lemma audio if you have
   it.

4. **Fix failures without changing the rules.** Put the word in an overrides
   file and regenerate only that section:

   ```json
   {
     "πνεῦμα": "PNEV-mah",
     "ἀποκάλυψις": "ah-poh-KAH-leep-seess"
   }
   ```

   ```console
   koine-suno --overrides fix.json < lyrics.txt
   ```

   Keep one overrides file per album so every track spells a word the same
   way.

## Known risks

| Spelling | Risk | Fallback |
|---|---|---|
| `ü` (υ, οι) | sung as *oo* or *ew*, or dropped | `--y ee` (later Koine/Byzantine value) |
| `ehw` (ευ: πνεῦμα) | sung as two syllables, or as *you* | override, e.g. `PNEV-mah` (the later [ev] value) |
| initial `pn`, `ps` | vowel inserted (*puh-NEV*) or *p* dropped | melody placement; otherwise accept |
| stress | caps alone may not move the stress | put the stressed syllable on a strong beat |

## Lyric-sheet tip

Keep three parallel lines while writing: the Greek, the `koine-suno` output
(what goes into Suno) and an English gloss. `koine-suno --table` gives you
the first two.
