"""Command line validation for the pronunciation research contract."""

import argparse
from pathlib import Path

from assessment.pronunciation import PROTOCOL_PATH, load_protocol, validate_protocol


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("protocol", nargs="?", type=Path, default=PROTOCOL_PATH)
    args = parser.parse_args()
    errors = validate_protocol(load_protocol(args.protocol))
    if errors:
        print("Pronunciation research protocol: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    print("Pronunciation research protocol: VALID")


if __name__ == "__main__":
    main()
