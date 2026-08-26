"""Command line validation for the checkpoint 22F research prompt pack."""

import argparse
import json
from pathlib import Path

from .prompt_pack_validate import PACK_PATH, validate_pack


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", nargs="?", type=Path, default=PACK_PATH)
    args = parser.parse_args()
    document = json.loads(args.pack.read_text(encoding="utf-8"))
    errors = validate_pack(document)
    if errors:
        print("Research prompt pack: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    print("Research prompt pack: VALID")
    print(
        f"{document['totals']['words']} words, "
        f"{document['totals']['scorable_opportunities']} scorable and "
        f"{document['totals']['unscorable_opportunities']} unscorable "
        "consonant opportunities."
    )
    print(
        "This historical checkpoint 22F pack remains unreviewed and inactive. "
        "Checkpoint 22G may assemble a separate private developer artifact, but "
        "no system or threshold is selected and the onboarding word pack is empty."
    )


if __name__ == "__main__":
    main()
