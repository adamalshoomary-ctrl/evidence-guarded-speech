"""Command line validator for the personal progress protocol and registry."""

import argparse
import json
from pathlib import Path

from pipeline.personal_progress import (
    CONTRACT_PATH,
    REGISTRY_PATH,
    validate_progress_contract,
    validate_reliability_registry,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path, nargs="?", default=CONTRACT_PATH)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    args = parser.parse_args()

    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Personal progress files are unreadable: {exc}")

    errors = validate_progress_contract(contract)
    errors.extend(validate_reliability_registry(registry, contract))
    if errors:
        print("Personal progress protocol: INVALID")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Personal progress protocol: VALID")
    print("Released speech metrics: "
          f"{len(registry['approved_metric_profiles'])}")


if __name__ == "__main__":
    main()
