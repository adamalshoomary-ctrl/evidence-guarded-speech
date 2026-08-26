"""Command line validator for the timestamped speech event contract."""

from .contract import load_contract, validate_contract


def main():
    errors = validate_contract(load_contract())
    if errors:
        raise SystemExit("Invalid fluency event contract:\n" + "\n".join(errors))
    print("Fluency event contract valid. Scientific release remains locked.")


if __name__ == "__main__":
    main()
