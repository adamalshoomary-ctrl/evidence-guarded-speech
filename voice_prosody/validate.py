"""Command line validator for the voice and prosody primitive contract."""

import argparse
from pathlib import Path

from voice_prosody.contract import CONTRACT_PATH, load_contract, validate_contract


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path, nargs="?", default=CONTRACT_PATH)
    args = parser.parse_args()
    try:
        contract = load_contract(args.contract)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Voice and prosody contract is unreadable: {exc}")
    errors = validate_contract(contract)
    if errors:
        print("Voice and prosody protocol: INVALID")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Voice and prosody protocol: VALID")
    print(f"Defined primitives: {len(contract['primitive_registry'])}")


if __name__ == "__main__":
    main()
