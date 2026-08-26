"""Validate the checkpoint 23B candidate reference source survey."""

from .source_survey import load_json, validate_survey, REGISTRY_PATH


def main():
    errors = validate_survey()
    if errors:
        print("Motor speech and voice source survey: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)

    registry = load_json(REGISTRY_PATH)
    counts = registry["counts"]
    print("Motor speech and voice source survey: VALID")
    print(f"{registry['record_count']} sources surveyed on {registry['surveyed_at']}.")
    print(
        f"{counts['obtainable_without_any_contact_account_or_agreement']} are "
        "obtainable with no contact, account or agreement."
    )
    print(
        f"{counts['licence_permits_commercial_use']} carry a licence that permits "
        "commercial use."
    )
    print("No source is recorded as meeting an item 23 truth requirement.")
    print("No source is selected and no acquisition is authorised.")
    for lane, body in registry["lane_conclusions"].items():
        print(f"  {lane}: {body['answer']}")


if __name__ == "__main__":
    main()
