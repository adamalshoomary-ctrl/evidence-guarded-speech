"""Close the final public Item 22 repository snapshot after report-era edits."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime
from pathlib import Path

from .final_acceptance import (
    PRIVATE_ACCEPTANCE_ROOT,
    REPORT_PATH,
    FinalAcceptanceError,
    _read_json,
    load_final_contract,
    snapshot_protected_state,
    snapshot_public_repository,
    validate_final_report,
    validate_private_manifest,
)
from .feasibility import file_sha256
from .repository_closure import (
    CLOSURE_PATH,
    CLOSURE_RELATIVE_PATH,
    build_repository_closure,
    validate_repository_closure,
    write_repository_closure,
)
from .run_final_acceptance import (
    _acceptance_source_digest,
    _all_pass,
    _run,
    _run_compilation,
    _run_tests,
    _run_validators,
)


def _safe_manifest_path(path):
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(PRIVATE_ACCEPTANCE_ROOT.resolve())
    except ValueError as exc:
        raise FinalAcceptanceError(
            "acceptance manifest must stay below the private acceptance root"
        ) from exc
    if resolved.name != "acceptance-manifest.json" or not resolved.is_file() or (
        resolved.is_symlink()
    ):
        raise FinalAcceptanceError("private acceptance manifest is missing or unsafe")
    return resolved


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--acceptance-manifest", type=Path, required=True)
    parser.add_argument("--acknowledge-engineering-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.acknowledge_engineering_only:
        parser.error("--acknowledge-engineering-only is required")
    if CLOSURE_PATH.exists() or CLOSURE_PATH.is_symlink():
        parser.error(f"repository closure already exists: {CLOSURE_PATH}")

    try:
        manifest_path = _safe_manifest_path(args.acceptance_manifest)
        contract = load_final_contract()
        manifest = _read_json(manifest_path)
        report = _read_json(REPORT_PATH)
        errors = validate_private_manifest(
            manifest, contract=contract, evidence_root=manifest_path.parent
        )
        errors.extend(validate_final_report(report, contract=contract, manifest=manifest))
        if errors:
            raise FinalAcceptanceError("\n".join(errors))
        expected_python = report["repository_acceptance"]["acceptance_python"]
        actual_python = {
            "command_name": "acceptance_python",
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "executable_name": Path(sys.executable).resolve().name,
            "executable_sha256": file_sha256(Path(sys.executable).resolve()),
        }
        if actual_python != expected_python:
            raise FinalAcceptanceError(
                "repository closure must use the same acceptance Python identity"
            )

        closure_run = PRIVATE_ACCEPTANCE_ROOT / (
            "repository_closure_" + datetime.now().strftime("%Y%m%dT%H%M%S")
        )
        closure_run.mkdir(parents=True, exist_ok=False)
        logs = closure_run / "logs"
        logs.mkdir()
        protected_before = snapshot_protected_state()
        public_before = snapshot_public_repository(
            exclude_paths={CLOSURE_RELATIVE_PATH}
        )

        validators = _run_validators(contract, logs)
        private_command = [
            sys.executable,
            "-m", "speech_sound_patterns.validate_final_acceptance",
            "--manifest", str(manifest_path), "--pre-closure",
        ]
        private_result, _, _, _ = _run(
            private_command,
            label="validator_final_acceptance_private_rebuild",
            log_root=logs,
        )
        compilation = _run_compilation(contract, logs)
        tests = _run_tests(contract, logs)

        if not _all_pass(validators):
            raise FinalAcceptanceError("repository closure validator failed")
        if private_result.returncode != 0:
            raise FinalAcceptanceError("private final evidence rebuild failed")
        if compilation.get("status") != "pass":
            raise FinalAcceptanceError("repository closure compilation failed")
        if not _all_pass(tests):
            raise FinalAcceptanceError("repository closure tests failed")
        required_commands = contract["repository_acceptance_policy"][
            "required_test_commands"
        ]
        if [item.get("command") for item in tests] != required_commands:
            raise FinalAcceptanceError("repository closure test commands changed")
        for item in tests:
            minimum = contract["repository_acceptance_policy"][
                "required_test_minimums"
            ][item["command"]]
            if item.get("tests_run", 0) < minimum or item.get("skipped") != 0:
                raise FinalAcceptanceError(
                    "repository closure test count or skip policy failed"
                )
        final_private_errors = validate_private_manifest(
            _read_json(manifest_path),
            contract=contract,
            evidence_root=manifest_path.parent,
        )
        if final_private_errors:
            raise FinalAcceptanceError(
                "private acceptance evidence changed during closure: "
                + "; ".join(final_private_errors)
            )
        protected_after = snapshot_protected_state()
        public_after = snapshot_public_repository(
            exclude_paths={CLOSURE_RELATIVE_PATH}
        )
        if protected_before != protected_after:
            raise FinalAcceptanceError("protected state changed during closure")
        if public_before != public_after:
            raise FinalAcceptanceError("public state changed during closure")
        acceptance_source = _acceptance_source_digest()
        if acceptance_source != report["repository_acceptance"][
            "acceptance_source_sha256"
        ]:
            raise FinalAcceptanceError(
                "acceptance source differs from the source bound by the final report"
            )

        evidence = {
            "public_repository": {
                "closure_excluded_path": CLOSURE_RELATIVE_PATH,
                "only_exclusion": True,
                "snapshot_sha256": public_after["sha256"],
                "file_count": len(public_after["entries"]),
            },
            "verification": {
                "private_acceptance_evidence_revalidated": True,
                "validator_commands": len(validators) + 1,
                "validator_commands_passed": sum(
                    item["status"] == "pass" for item in validators
                ) + (private_result.returncode == 0),
                "python_compilation": compilation["status"],
                "test_commands": [
                    {
                        "command": item["command"],
                        "status": item["status"],
                        "tests_run": item["tests_run"],
                        "failures": item["failures"],
                        "errors": item["errors"],
                        "skipped": item["skipped"],
                    }
                    for item in tests
                ],
                "protected_state_unchanged": True,
                "public_state_unchanged_during_closure": True,
                "acceptance_source_sha256": acceptance_source,
                "acceptance_python": actual_python,
            },
        }
        closure = build_repository_closure(evidence)
        closure_errors = validate_repository_closure(
            closure, check_public_snapshot=False
        )
        if closure_errors:
            raise FinalAcceptanceError("\n".join(closure_errors))
        write_repository_closure(closure)
        closure_errors = validate_repository_closure(
            json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        )
        if closure_errors:
            raise FinalAcceptanceError("\n".join(closure_errors))
    except FinalAcceptanceError as exc:
        parser.error(str(exc))

    print("Item 22 repository closure: VALID")
    print("Private final evidence was revalidated and the public snapshot is closed.")
    print("Held-out evaluation was not performed and every release remains locked.")


if __name__ == "__main__":
    main()
