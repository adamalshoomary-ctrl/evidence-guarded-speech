"""Validate the committed aggregate checkpoint 22D benchmark evidence."""

import json

from .benchmark import (
    BENCHMARK_REPORT_PATH,
    FROZEN_BENCHMARK_REPORT_SHA256,
    assert_valid_benchmark_rules,
    validate_safe_benchmark_report,
)
from .feasibility import file_sha256
from .benchmark_meta_ctc import load_meta_contract
from .benchmark_repair import (
    REPAIR_REPORT_PATH,
    load_repair_contract,
    validate_repair_report,
)
from .score_benchmark_repair_meta_threshold import load_exact_threshold_contract


def main():
    assert_valid_benchmark_rules()
    if file_sha256(BENCHMARK_REPORT_PATH) != FROZEN_BENCHMARK_REPORT_SHA256:
        raise SystemExit("Checkpoint 22D benchmark report identity changed")
    report = json.loads(BENCHMARK_REPORT_PATH.read_text(encoding="utf-8"))
    errors = validate_safe_benchmark_report(report)
    repair_report = json.loads(REPAIR_REPORT_PATH.read_text(encoding="utf-8"))
    errors.extend(validate_repair_report(repair_report))
    if errors:
        print("Speech sound benchmark evidence: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    load_repair_contract()
    load_meta_contract()
    load_exact_threshold_contract()
    print("Speech sound benchmark evidence: VALID")
    print(
        "Baseline and repair evidence use development and tuning only; "
        "held out evaluation remains untouched."
    )
    print(
        "All 2,957 exact Meta thresholds were checked. No system, threshold, "
        "candidate artifact or product output is selected."
    )


if __name__ == "__main__":
    main()
