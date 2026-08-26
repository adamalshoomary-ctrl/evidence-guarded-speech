"""Command line validation for the speech sound pattern research contract."""

import argparse
from pathlib import Path

from .contract import CONTRACT_PATH, load_contract, validate_contract


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", nargs="?", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()
    errors = validate_contract(load_contract(args.contract))
    if errors:
        print("Speech sound pattern research contract: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    print("Speech sound pattern research contract: VALID")
    print(
        "Corpus manifests, local feasibility, the development benchmark, its "
        "conservative repair, the external schema smoke test, the frozen role "
        "based comparison and the selection and rejection record are complete."
    )
    print(
        "Item 22 engineering acceptance passed on the no-selection path. No "
        "candidate system, candidate output mapping, relation rule, repeated rule "
        "or threshold was selected."
    )
    print(
        "Held-out evaluation was not performed and every result is unavailable, "
        "not zero, pass or failure."
    )
    print("Normal pipeline, scientific release and every product use remain blocked.")


if __name__ == "__main__":
    main()
