"""Command line validation for the checkpoint 22E8 reference variety probe."""

import argparse
import json
from pathlib import Path

from .variety_probe_validate import REPORT_PATH, validate_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", nargs="?", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    document = json.loads(args.report.read_text(encoding="utf-8"))
    errors = validate_report(document)
    if errors:
        print("Reference variety probe: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    print("Reference variety probe: VALID")
    print(
        "No system, threshold or reference is selected, no gate moved, and no "
        "detection accuracy is claimed."
    )


if __name__ == "__main__":
    main()
