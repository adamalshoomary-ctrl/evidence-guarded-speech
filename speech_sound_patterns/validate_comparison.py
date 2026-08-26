"""Validate every committed frozen comparison, checkpoint 22E4 and 22E4B.

Both versions are checked on every run. The checkpoint 22E4 record must keep
validating unchanged after the powered replication, because it is the record of
the first look and nothing in checkpoint 22E4B may edit it.
"""

import json

from .comparison import (
    COMPARISON_VERSIONS,
    comparison_profile,
    load_comparison_contract,
    validate_comparison_contract,
    validate_comparison_report,
)


def main():
    errors = []
    decisions = {}
    for version in sorted(COMPARISON_VERSIONS):
        profile = comparison_profile(version)
        checkpoint = profile["checkpoint"]
        contract_errors = validate_comparison_contract(
            load_comparison_contract(version=version)
        )
        errors.extend(f"{checkpoint}: {error}" for error in contract_errors)
        report_path = profile["report_path"]
        if report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            errors.extend(
                f"{checkpoint}: {error}"
                for error in validate_comparison_report(report)
            )
            decisions[checkpoint] = report["decision"]["decision"]
        else:
            errors.append(
                f"the checkpoint {checkpoint} comparison report has not been written"
            )
    if errors:
        print("Speech sound frozen comparison evidence: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    print("Speech sound frozen comparison evidence: VALID")
    print(
        "The checkpoint 22D selection gates are unchanged in both comparisons, "
        "development and tuning are separate, and the held out set was never "
        "accessed."
    )
    for checkpoint, decision in sorted(decisions.items()):
        print(f"Decision at {checkpoint}: {decision}.")
    print(
        "No system is selected in either checkpoint. Checkpoint 22E5 records "
        "that outcome for every lane; validate it with "
        "python3 -m speech_sound_patterns.validate_selection."
    )


if __name__ == "__main__":
    main()
