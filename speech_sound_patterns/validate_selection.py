"""Validate the committed checkpoint 22E5 selection and rejection record.

The record is checked against the evidence it cites rather than on its own, so
an edit to the provider register or to either frozen comparison invalidates it
instead of leaving a stale verdict standing. Pass ``--record-version`` to check
a superseded version; every issued version stays on disk and stays valid.
"""

import argparse

from .selection_record import (
    ACTIVE_SELECTION_VERSION,
    LANE_DECISION_PROFILES,
    SELECTION_VERSIONS,
    load_selection_record,
    validate_selection_record,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--record-version",
        choices=sorted(SELECTION_VERSIONS),
        default=ACTIVE_SELECTION_VERSION,
        help="which issued record to validate; earlier versions stay on disk",
    )
    arguments = parser.parse_args()
    record = load_selection_record(version=arguments.record_version)
    errors = validate_selection_record(record)
    if errors:
        print("Speech sound selection record: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)

    print("Speech sound selection record: VALID")
    print(f"Decision: {record['decision']['decision']}.")
    counts = {}
    for lane in record["lanes"]:
        counts[lane["decision"]] = counts.get(lane["decision"], 0) + 1
    for decision, count in sorted(counts.items()):
        print(f"  {decision}: {count}")
    measured = sum(
        1
        for lane in record["lanes"]
        if lane["incremental_value_beyond_22d_baseline"]["measured"]
    )
    print(
        f"{measured} of {len(LANE_DECISION_PROFILES)} lanes were measured against "
        "the unchanged gates; none passed them."
    )
    print(
        "No mapping, feature, threshold or provider configuration is frozen for "
        "later checkpoints, because nothing was selected."
    )


if __name__ == "__main__":
    main()
