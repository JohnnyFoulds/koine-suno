"""Command-line interface: ``koine-suno``."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .ipa import to_ipa
from .suno import SunoOptions, breakdown, load_overrides, to_suno


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koine-suno",
        description=(
            "Respell Koine Greek in its first-century pronunciation so "
            "that Suno sings it correctly."
        ),
    )
    parser.add_argument(
        "text", nargs="*", help="Greek text (read from stdin if omitted)"
    )
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "--ipa", action="store_true", help="print first-century IPA only"
    )
    output.add_argument(
        "--table",
        action="store_true",
        help="print Greek, IPA and Suno spelling per word",
    )
    parser.add_argument(
        "--y",
        default="ü",
        choices=["ü", "ee", "ew"],
        help="spelling for /y/ (υ, οι); default: ü",
    )
    parser.add_argument(
        "--keep-h", action="store_true", help="sing rough breathing as h"
    )
    parser.add_argument(
        "--no-caps",
        action="store_true",
        help="do not capitalise stressed syllables",
    )
    parser.add_argument(
        "--overrides",
        metavar="FILE",
        help='JSON file of fixed spellings, e.g. {"πνεῦμα": "PNEV-mah"}',
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def _print_table(rows: list[dict]) -> None:
    greek_width = max((len(r["greek"]) for r in rows), default=0)
    ipa_width = max((len(r["ipa"]) for r in rows), default=0)
    for row in rows:
        print(
            f'{row["greek"]:<{greek_width}}  '
            f'{row["ipa"]:<{ipa_width}}  {row["suno"]}'
        )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = " ".join(args.text) if args.text else sys.stdin.read()
    opts = SunoOptions(
        y=args.y,
        keep_h=args.keep_h,
        caps=not args.no_caps,
        overrides=load_overrides(args.overrides),
    )

    if args.ipa:
        print("\n".join(to_ipa(line) for line in text.splitlines()))
    elif args.table:
        _print_table(breakdown(text, opts))
    else:
        print(to_suno(text, opts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
