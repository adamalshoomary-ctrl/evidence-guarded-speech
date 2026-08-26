"""Validate the active checkpoint 23B governance contract."""

from .governance import (
    active_pipeline_leakage,
    load_governance_contract,
    validate_governance_contract,
)


def main():
    document = load_governance_contract()
    errors = validate_governance_contract(document)
    leakage = active_pipeline_leakage()
    if leakage:
        errors.append(
            "item 23 governance leaked into the active pipeline: "
            + ", ".join(leakage)
        )
    if errors:
        print("Motor speech and voice governance contract: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)

    print("Motor speech and voice governance contract: VALID")
    print("Adults first scope is recorded.")
    print("Every research lane remains unselected.")
    print("External governance and the legal sponsor remain unresolved.")
    print("No contact, spending, participant work, data use or implementation is authorised.")


if __name__ == "__main__":
    main()
