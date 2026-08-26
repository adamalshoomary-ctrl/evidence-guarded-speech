"""Validate the checkpoint 23B measurement and sampling input package."""

from .measurement_plan import load_json, validate_plan, REGISTRY_PATH


def main():
    errors = validate_plan()
    if errors:
        print("Motor speech and voice measurement inputs: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)

    registry = load_json(REGISTRY_PATH)
    counts = registry["counts"]
    print("Motor speech and voice measurement inputs: VALID")
    print(
        f"{registry['record_count']} provisional constructs recorded on "
        f"{registry['prepared_at']}."
    )
    print("No construct, task, estimand, statistic or threshold is selected.")
    print("No sample size is computed, and no record may contain one.")
    for lane, body in registry["lane_summaries"].items():
        count = counts["by_governance_lane"].get(lane, 0)
        print(f"  {lane} ({count}): {body['reference_position']}")


if __name__ == "__main__":
    main()
