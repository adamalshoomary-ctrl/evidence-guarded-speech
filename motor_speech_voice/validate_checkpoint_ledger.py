"""Validate the checkpoint 23B deliverable ledger."""

from .checkpoint_ledger import load_json, validate_ledger, LEDGER_PATH


def main():
    errors = validate_ledger()
    if errors:
        print("Checkpoint 23B deliverable ledger: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)

    ledger = load_json(LEDGER_PATH)
    counts = ledger["counts"]
    print("Checkpoint 23B deliverable ledger: VALID")
    print(f"{ledger['deliverable_count']} required deliverables recorded.")
    print(
        f"  {counts.get('public_research_complete', 0)} complete by public research"
    )
    print(f"  {counts.get('public_research_partial', 0)} advanced but unfinished")
    print(
        f"  {counts.get('blocked_requires_named_human', 0)} blocked on a named "
        "human role"
    )
    print("Checkpoint 23B remains in progress. Acceptance is written review.")


if __name__ == "__main__":
    main()
