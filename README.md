# koine-suno

Respell Koine Greek in its first-century pronunciation so that
[Suno](https://suno.com) sings it correctly. It ships as a command-line tool
and as an MCP server.

```console
$ koine-suno "τὸ πνεῦμα ὅπου θέλει πνεῖ"
toh PNEHW-mah OH-poo TEH-lee pnee

$ koine-suno --table "ἐκκλησία δόξα χάρις"
ἐκκλησία  ek.kle̝ˈsi.a  ek-klay-SEE-ah
δόξα      ˈdok.sa      DOK-sah
χάρις     ˈkʰa.ris     KAH-reess
```

## Why

Suno has no phonetic input. It reads lyrics as spelling, mostly with English
habits. What it does with Greek script is undocumented and out of your
control, and the usual academic transliteration (*pneuma*, *charis*,
*eirēnē*) gets read with English spelling rules. Neither gives you the
language as it sounded when the New Testament was written.

koine-suno works in two steps:

1. **Greek → IPA.** A Python port of the first-century (`koi1`, "1st CE
   Egyptian") rules of Wiktionary's
   [`Module:grc-pronunciation`](https://en.wiktionary.org/wiki/Module:grc-pronunciation).
   The test suite checks the output character for character against IPA
   produced by Wiktionary itself.
2. **IPA → Suno spelling.** Each sound gets the English spelling least
   likely to be misread. The stressed syllable is in capitals and
   syllables are hyphenated.

The details are in [docs/how-it-works.md](docs/how-it-works.md).

## Install

Requires Python 3.10 or later.

```console
git clone https://github.com/JohnnyFoulds/koine-suno.git
cd koine-suno
pip install -e .
```

This installs two commands: `koine-suno` (the CLI) and `koine-suno-mcp` (the
MCP server).

## Command line

```console
koine-suno "<greek>"               # Suno spelling (line breaks preserved)
koine-suno --ipa "<greek>"         # first-century IPA only
koine-suno --table "<greek>"       # Greek | IPA | Suno, one word per line
koine-suno --y ee "<greek>"        # write /y/ (υ, οι) as "ee" instead of "ü"
koine-suno --keep-h "<greek>"      # sing rough breathing as "h"
koine-suno --no-caps "<greek>"     # do not capitalise stressed syllables
koine-suno --overrides fix.json    # fixed spellings for specific words
cat lyrics.txt | koine-suno        # read from stdin
```

An overrides file maps Greek words to the spelling you want, for words that
did not sound right when you listened:

```json
{ "πνεῦμα": "PNEV-mah" }
```

## MCP server

Add the server to your MCP client configuration, for example
`claude_desktop_config.json` or `.mcp.json`:

```json
{
  "mcpServers": {
    "koine-suno": { "command": "koine-suno-mcp" }
  }
}
```

| Tool | Arguments | Returns |
|---|---|---|
| `koine_to_suno` | `text`, `y` = `"ü"`, `keep_h` = `false` | Suno respelling |
| `koine_ipa` | `text` | First-century IPA |
| `koine_breakdown` | `text`, `y` = `"ü"` | List of `{greek, ipa, suno}` |

The server supports both the 1.x and 2.x MCP Python SDKs.

## Python

```python
from koine_suno import SunoOptions, breakdown, to_ipa, to_suno

to_ipa("εἰρήνη")                          # 'iˈre̝.ne̝'
to_suno("εἰρήνη")                         # 'ee-RAY-nay'
to_suno("μετάνοια", SunoOptions(y="ee"))  # 'meh-TAH-nee-ah'
breakdown("σάρξ")  # [{'greek': 'σάρξ', 'ipa': 'ˈsarks', 'suno': 'sarks'}]
```

## Getting it right in Suno

The Greek-to-IPA step has been checked against Wiktionary. The IPA-to-spelling
step has not been checked by ear in Suno; that is your job, and
[docs/suno-guide.md](docs/suno-guide.md) gives the workflow. In short: render
a test line, listen, and fix any word that fails with `--y ee` or an
override.

## Development

```console
pip install -e '.[dev]'
pytest           # Wiktionary parity and spelling tests
flake8           # PEP 8
black --check .  # formatting (79 columns)
```

## Licence and attribution

The pronunciation rules in `src/koine_suno/ipa.py` are adapted from
Wiktionary's
[Module:grc-pronunciation](https://en.wiktionary.org/wiki/Module:grc-pronunciation)
and
[Module:grc-pronunciation/data](https://en.wiktionary.org/wiki/Module:grc-pronunciation/data),
© Wiktionary contributors, licensed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The
reference data in `tests/wiktionary_koi1_ref.json` was produced by the same
module. As an adaptation, this project is distributed under the same licence;
see [LICENSE](LICENSE).
