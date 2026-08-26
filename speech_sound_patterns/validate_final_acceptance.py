"""Validate the checkpoint 22H contract, aggregate report, and private proof."""

from __future__ import annotations

import argparse
from pathlib import Path

from .final_acceptance import (
    PRIVATE_ACCEPTANCE_ROOT,
    REPORT_PATH,
    FinalAcceptanceError,
    _read_json,
    load_final_contract,
    validate_final_report,
    validate_private_manifest,
)


def _private_manifest_path(path):
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(PRIVATE_ACCEPTANCE_ROOT.resolve())
    except ValueError as exc:
        raise FinalAcceptanceError(
            "private acceptance manifest must stay below the private acceptance root"
        ) from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise FinalAcceptanceError("private acceptance manifest is missing or unsafe")
    return resolved


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--pre-closure", action="store_true")
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)
    if args.contract_only and args.manifest:
        parser.error("--contract-only cannot be combined with --manifest")
    if args.contract_only and args.pre_closure:
        parser.error("--contract-only cannot be combined with --pre-closure")
    if args.pre_closure and args.manifest is None:
        parser.error("--pre-closure requires the private acceptance manifest")

    try:
        contract = load_final_contract()
        if args.contract_only:
            errors = []
        else:
            report = _read_json(args.report)
            manifest = None
            if args.manifest is not None:
                manifest = _read_json(_private_manifest_path(args.manifest))
                manifest_errors = validate_private_manifest(
                    manifest,
                    contract=contract,
                    evidence_root=_private_manifest_path(args.manifest).parent,
                )
            else:
                manifest_errors = []
            errors = manifest_errors + validate_final_report(
                report, contract=contract, manifest=manifest
            )
            from .repository_closure import (
                CLOSURE_PATH,
                validate_repository_closure,
            )
            if CLOSURE_PATH.is_symlink():
                errors.append("repository closure path may not be a symlink")
            elif CLOSURE_PATH.exists():
                errors.extend(validate_repository_closure(_read_json(CLOSURE_PATH)))
            elif not args.pre_closure:
                errors.append(
                    "post-report repository closure is missing; Item 22 is not closed"
                )
    except FinalAcceptanceError as exc:
        parser.error(str(exc))

    if errors:
        print("Speech sound final acceptance: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    if args.contract_only:
        print("Speech sound final acceptance contract: VALID")
        print("Held-out evidence remains sealed and was not read.")
        print("No candidate system, rule, threshold, or release is selected.")
    else:
        if args.pre_closure:
            print("Speech sound final acceptance evidence: VALID, CLOSURE PENDING")
        else:
            print("Speech sound final acceptance and repository closure: VALID")
        if args.manifest is not None:
            print("Private acceptance evidence rebuilds the report exactly.")
        else:
            print("No private acceptance manifest was supplied or checked.")
        from .repository_closure import CLOSURE_PATH
        if CLOSURE_PATH.is_file():
            print("The post-report public repository closure is valid.")
        if args.pre_closure:
            print("Item 22 is not complete until repository closure succeeds.")
        else:
            print("Item 22 engineering acceptance is complete on the no-selection path.")
        print("Scientific release and product release remain locked.")


if __name__ == "__main__":
    main()
