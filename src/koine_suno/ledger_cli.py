"""Command-line interface: ``koine-ledger``."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .ledger import as_dicts, build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="koine-ledger",
        description=(
            "Build the token ledger for a New Testament span and run the "
            "gate-1 checks (text, morphology, sense). Exits 1 on any FAIL."
        ),
    )
    parser.add_argument(
        "spec", help="reference, e.g. 'JHN 1:1', 'JHN 1:1-5', '1JN 4:8!8-11'"
    )
    parser.add_argument(
        "--macula",
        default=os.environ.get("KOINE_MACULA"),
        help="path to a macula-greek checkout (or set KOINE_MACULA)",
    )
    parser.add_argument(
        "--morphgnt",
        default=os.environ.get("KOINE_MORPHGNT"),
        help="path to a morphgnt/sblgnt checkout (or set KOINE_MORPHGNT)",
    )
    parser.add_argument(
        "--json", metavar="FILE", help="also write the ledger as JSON"
    )
    args = parser.parse_args(argv)
    if not args.macula or not args.morphgnt:
        parser.error("--macula and --morphgnt (or the env vars) are required")

    entries = build(args.spec, args.macula, args.morphgnt)
    for e in entries:
        print(
            f"{e.status:<4}  {e.ref:<14} {e.surface:<12} {e.morph:<11} "
            f"LN {e.ln:<7} {e.suno:<14} {e.gloss}"
        )
        for issue in e.issues:
            print(f"      - {issue}")
    failed = sum(e.status == "FAIL" for e in entries)
    warned = sum(e.status == "WARN" for e in entries)
    print(f"\n{len(entries)} tokens: {failed} FAIL, {warned} WARN")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(as_dicts(entries), handle, ensure_ascii=False, indent=1)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
