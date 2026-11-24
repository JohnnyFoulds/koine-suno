# How it works

koine-suno turns Greek text into a spelling that Suno sings in a
first-century pronunciation. There are two independent steps, and only the
first claims linguistic accuracy.

```
Greek text ──► first-century IPA ──► Suno respelling
  (ipa.py: Wiktionary port)  (suno.py: English spelling rules)
```

## 1. Which pronunciation

Greek pronunciation changed a great deal over the Koine period, roughly 300
BC to AD 400. It began close to Classical Attic and ended close to Modern
Greek [1], [2]. A choice of period has to be made, and koine-suno uses
Wiktionary's **"1st CE Egyptian"** reconstruction (`koi1`) because:

* it is the period in which the New Testament was written;
* Egyptian papyri are the main evidence for first-century spoken Koine,
  because their misspellings show which sounds had merged [1], [2];
* Wiktionary's module is an open, rule-based implementation of it, which
  makes the output reproducible and testable [3].

The main features of this stage of the language, as encoded in the rules:

| Feature | Example | koi1 |
|---|---|---|
| Vowel length lost; accent is now stress | λόγος | ˈlo.ɡos |
| η is a raised e | εἰρήνη | iˈre̝.ne̝ |
| αι, ει, οι became single vowels | καί, εἰ, οἱ | ɛ, i, y |
| υ is a front rounded vowel (German *ü*) | ψυχή | psyˈkʰe̝ |
| ου is *u* | νοῦς | ˈnus |
| αυ, ευ end in a glide | αὐτός, πνεῦμα | aʍˈtos, ˈpnew.ma |
| β γ δ are still stops | ἀγάπη | aˈɡa.pe̝ |
| φ θ χ are still aspirated stops | χάρις | ˈkʰa.ris |
| Rough breathing optional | ἁμαρτία | (h)a.marˈti.a |
| σ voiced before voiced consonants | κόσμος | ˈkoz.mos |
| γ before γ κ χ is a nasal | ἄγγελος | ˈaŋ.ɡe.los |

Later Koine, the `koi2` period, moves β γ δ and φ θ χ to fricatives and
merges η with ι. That is the basis of some modern "reconstructed Koine"
teaching systems but post-dates the New Testament, so it is not used here.

## 2. Greek → IPA (`ipa.py`)

`ipa.py` is a direct port of the `koi1` branch of
`Module:grc-pronunciation` and its `/data` table [3]. It runs in three
stages:

1. **Letters.** The word is decomposed (Unicode NFD) into base letters, each
   with its set of diacritics. ξ becomes κσ, ψ becomes πσ, and ς becomes σ,
   as in the Lua module.
2. **Phones.** Letters are read left to right:
   * a vowel followed by ι or υ forms a diphthong unless a diaeresis or a
     length mark splits them. The accent and breathing of the diphthong
     are taken from either letter;
   * a υ-diphthong gets the glide [ʍ] before a voiceless consonant and [w]
     elsewhere;
   * γ, κ, σ and τσ/τζ have context rules (see the table above). Every
     other consonant maps one to one.
3. **Syllables.** Each vowel is a syllable nucleus. Between two vowels, the
   following syllable takes one consonant as its onset, or two when they
   are an obstruent plus a liquid (κλ, θρ, θν). The rest goes to the coda
   of the preceding syllable. This is the Lua module's
   `find_syllable_break`.

The output uses Wiktionary's notation: `.` between syllables, `ˈ` before
the stressed one, and `(h)` for an optional rough breathing.

**Verification.** `tests/wiktionary_koi1_ref.json` holds 47 words, including
diphthongs, nasal assimilation, voicing, muta cum liquida and rough
breathing. They were transcribed by Wiktionary itself through its
`expandtemplates` API. The port reproduces every one exactly.

## 3. IPA → Suno spelling (`suno.py`)

Suno has no documented phonetic notation [4]. It predicts pronunciation from
spelling, with strong English priors, so the respelling uses the English
spelling of each sound least likely to be misread.

| IPA | Spelling | Reason |
|---|---|---|
| a | `ah` (`ar` before r) | bare *a* reads as the short vowel in *cat* |
| e, ɛ | `eh` open, `e` closed | *ek*, *en* read correctly; a bare *e* at the end of a syllable does not |
| e̝ | `ay` | nearest English vowel to a close *e* |
| i | `ee` | |
| o | `oh` open, `o` closed | bare *o* in an open syllable can read as *oo* (*to*) |
| u | `oo` | |
| y | `ü` (or `ee`, `ew`) | English has no front rounded vowel |
| aw, ew | `ow`, `ehw` | *ow* as in *cow* |
| pʰ tʰ kʰ | `p t k` | *ph th ch* would be sung as /f θ tʃ/ |
| ɡ | `g`, `gh` before e/i/y | stops *g* softening to /dʒ/ |
| ŋ | `n` | *ng*, *nk* already read as [ŋɡ], [ŋk] |
| final s | `ss` | stops voicing to /z/ (*-os* → *-oss*) |

The stressed syllable of a word with more than one syllable is written in
capitals. Monosyllables stay in lower case.

These rules are a phonetic approximation, and they have not been checked by
ear. See [suno-guide.md](suno-guide.md) for how to test them and fix the
words that fail.

## References

[1] G. Horrocks, *Greek: A History of the Language and Its Speakers*, 2nd
ed. Chichester, U.K.: Wiley-Blackwell, 2010.

[2] "Koine Greek phonology," *Wikipedia*. [Online]. Available:
https://en.wikipedia.org/wiki/Koine_Greek_phonology

[3] Wiktionary contributors, "Module:grc-pronunciation" and
"Module:grc-pronunciation/data," *Wiktionary*. [Online]. Available:
https://en.wiktionary.org/wiki/Module:grc-pronunciation

[4] G. Whittaker, "How to make Suno pronounce words correctly," *Jack
Righteous*, Aug. 2026. [Online]. Available:
https://jackrighteous.com/blogs/guides-using-suno-ai-music-creation/suno-v5-multilingual-english-pronunciation-guide
