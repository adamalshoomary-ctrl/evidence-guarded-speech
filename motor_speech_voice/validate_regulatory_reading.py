"""Validate the checkpoint 23B documented Australian regulatory and privacy reading."""

from .regulatory_reading import load_json, validate_reading, REGISTRY_PATH


def main():
    errors = validate_reading()
    if errors:
        print("Motor speech and voice regulatory reading: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)

    registry = load_json(REGISTRY_PATH)
    counts = registry["counts"]
    print("Motor speech and voice regulatory reading: VALID")
    print(
        f"{registry['record_count']} questions read on {registry['prepared_at']} "
        f"across {len(counts['by_domain'])} domains."
    )
    print(
        f"{counts['open_questions_recorded']} open questions and "
        f"{counts['source_conflicts_recorded']} source conflicts are recorded "
        "rather than resolved."
    )
    print("No determination, approval or advice is recorded.")
    for name, body in registry["purpose_ladder"].items():
        occupied = "occupied" if body["occupied_today"] else "hypothetical"
        print(f"  rung {body['rung']} ({occupied}) {name}: {body['medical_device_position']}")


if __name__ == "__main__":
    main()
