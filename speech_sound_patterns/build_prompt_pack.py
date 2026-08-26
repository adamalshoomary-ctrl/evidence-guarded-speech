"""Build the checkpoint 22F research prompt pack from the acquired references.

The committed pack is generated, never typed. Running this against the acquired
private material must reproduce the committed file byte for byte, and a test
asserts exactly that whenever the material is present.

Two documents come out. The pack itself is committed: twenty words and the
consonant opportunities inside them. The private record holds the verbatim
British and Australian forms and the whole eligible pool, and stays in
gitignored storage because that material is the derived lexicon.
"""

import argparse
import json
from pathlib import Path

from .prompt_pack import PACK_PATH, PACK_ROOT, build_pack

RECORD_PATH = PACK_ROOT / "prompt-pack-private-record-v1.0.0.json"


def serialise(document):
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, default=PACK_PATH)
    parser.add_argument("--record", type=Path, default=RECORD_PATH)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild and compare with the committed pack instead of writing it",
    )
    args = parser.parse_args()

    pack, record = build_pack()
    rendered = serialise(pack)

    if args.check:
        existing = args.pack.read_text(encoding="utf-8")
        if existing != rendered:
            print("Research prompt pack: DOES NOT REPRODUCE")
            raise SystemExit(1)
        print("Research prompt pack: reproduces byte for byte")
        return

    args.pack.write_text(rendered, encoding="utf-8")
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(serialise(record), encoding="utf-8")
    print(f"Wrote {args.pack}")
    print(f"Wrote {args.record} (gitignored: it holds the derived lexicon)")
    print(
        f"{pack['totals']['words']} words, "
        f"{pack['totals']['scorable_opportunities']} scorable and "
        f"{pack['totals']['unscorable_opportunities']} unscorable opportunities, "
        f"chosen from an eligible pool of {pack['eligible_pool']['words']} words."
    )


if __name__ == "__main__":
    main()
