"""Command line validation for the backend data model and session context."""

import argparse
from pathlib import Path

from pipeline.session_context import (
    CONTRACT_PATH,
    load_data_model_contract,
    load_session_context,
    validate_data_model_contract,
    validate_session_context,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("context", nargs="?", type=Path)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()

    contract_errors = validate_data_model_contract(
        load_data_model_contract(args.contract)
    )
    if contract_errors:
        print("Backend data model: INVALID")
        for error in contract_errors:
            print(f"  {error}")
        raise SystemExit(1)
    print("Backend data model: VALID")

    if args.context is not None:
        context_errors = validate_session_context(
            load_session_context(args.context)
        )
        if context_errors:
            print("Session context: INVALID")
            for error in context_errors:
                print(f"  {error}")
            raise SystemExit(1)
        print("Session context: VALID")


if __name__ == "__main__":
    main()
