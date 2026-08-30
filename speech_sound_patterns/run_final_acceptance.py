"""Run checkpoint 22H repository acceptance exactly once.

The command runs validators, compilation, tests, the known owner conversation
through the unchanged normal pipeline, and the independent regression fixture.
All raw evidence stays below the gitignored private acceptance root. Only the
validated aggregate final report is written beside this module.

This command never opens speech-sound held-out assignments, identities, labels,
audio, or derived rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline.provenance import source_revision
from pipeline.pipeline_config import PIPELINE_VERSION, model_registry, prompt_registry

from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256
from .final_acceptance import (
    CONTRACT_PATH,
    CONTRACT_SHA256,
    PRIVATE_ACCEPTANCE_ROOT,
    REPORT_PATH,
    FinalAcceptanceError,
    analyze_pipeline_output,
    build_evidence_inventory,
    build_final_report,
    canonical_digest,
    load_final_contract,
    runtime_output_leakage,
    snapshot_protected_state,
    snapshot_public_repository,
    static_pipeline_leakage,
    validate_final_report,
    validate_private_manifest,
    write_exclusive_atomic,
    write_final_report,
)


TEST_COUNT = re.compile(r"Ran\s+(\d+)\s+tests?\s+in")
SKIPPED_COUNT = re.compile(r"skipped=(\d+)")
FAILURE_COUNT = re.compile(r"failures=(\d+)")
ERROR_COUNT = re.compile(r"errors=(\d+)")


def _utc_now():
    return (
        datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _safe_name(value):
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _run(command, *, label, log_root):
    start = time.monotonic()
    result = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )
    duration = time.monotonic() - start
    stdout = (result.stdout or "").encode("utf-8")
    stderr = (result.stderr or "").encode("utf-8")
    write_exclusive_atomic(log_root / f"{_safe_name(label)}.stdout.log", stdout)
    write_exclusive_atomic(log_root / f"{_safe_name(label)}.stderr.log", stderr)
    return result, duration, _sha256_bytes(stdout), _sha256_bytes(stderr)


def _acceptance_source_digest():
    paths = [
        CONTRACT_PATH,
        Path(__file__).resolve(),
        Path(__file__).with_name("final_acceptance.py"),
        Path(__file__).with_name("validate_final_acceptance.py"),
        Path(__file__).with_name("repository_closure.py"),
        Path(__file__).with_name("finalize_repository_closure.py"),
        REPOSITORY_ROOT / "tests" / "test_speech_sound_final_acceptance.py",
    ]
    digest = hashlib.sha256()
    for path in paths:
        if not path.is_file():
            raise FinalAcceptanceError(f"acceptance source is missing: {path}")
        relative = path.relative_to(REPOSITORY_ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _snapshot_subset_digest(snapshot, prefix):
    selected = [
        item for item in snapshot["entries"]
        if item["path"] == prefix or item["path"].startswith(prefix + "/")
    ]
    return _sha256_bytes(canonical_json_bytes(selected))


def _validation_commands(contract):
    commands = []
    for module in contract["repository_acceptance_policy"]["required_validators"]:
        command = [sys.executable, "-m", module]
        public = f"acceptance_python -m {module}"
        if module == "speech_sound_patterns.validate_final_acceptance":
            command.append("--contract-only")
            public += " --contract-only"
        commands.append((module, public, command))
    return commands


def _run_validators(contract, log_root):
    records = []
    for module, public, command in _validation_commands(contract):
        print(f"Validator: {module}", flush=True)
        result, duration, stdout_sha, stderr_sha = _run(
            command, label=f"validator_{module}", log_root=log_root
        )
        records.append({
            "module": module,
            "command": public,
            "status": "pass" if result.returncode == 0 else "fail",
            "exit_code": result.returncode,
            "duration_s": round(duration, 3),
            "stdout_sha256": stdout_sha,
            "stderr_sha256": stderr_sha,
        })
        if result.returncode != 0:
            break
    return records


def _run_compilation(contract, log_root):
    roots = contract["repository_acceptance_policy"]["python_compile_roots"]
    public = "acceptance_python -m compileall -q " + " ".join(roots)
    command = [sys.executable, "-m", "compileall", "-q", *roots]
    print("Compiling Python sources", flush=True)
    result, duration, stdout_sha, stderr_sha = _run(
        command, label="python_compilation", log_root=log_root
    )
    return {
        "command": public,
        "roots": roots,
        "status": "pass" if result.returncode == 0 else "fail",
        "exit_code": result.returncode,
        "duration_s": round(duration, 3),
        "stdout_sha256": stdout_sha,
        "stderr_sha256": stderr_sha,
    }


def _parse_test_count(text, pattern, default=0):
    match = pattern.search(text)
    return int(match.group(1)) if match else default


def _test_command_tokens(public):
    if public == (
        "acceptance_python -m unittest tests.test_speech_sound_final_acceptance"
    ):
        return [
            sys.executable, "-m", "unittest",
            "tests.test_speech_sound_final_acceptance",
        ]
    if public == "acceptance_python -m unittest discover -s tests":
        return [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    raise FinalAcceptanceError(f"unsupported frozen test command: {public}")


def _run_tests(contract, log_root):
    records = []
    for index, public in enumerate(
        contract["repository_acceptance_policy"]["required_test_commands"],
        start=1,
    ):
        print(f"Tests: {public}", flush=True)
        result, duration, stdout_sha, stderr_sha = _run(
            _test_command_tokens(public),
            label=f"tests_{index}",
            log_root=log_root,
        )
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        records.append({
            "command": public,
            "status": "pass" if result.returncode == 0 else "fail",
            "exit_code": result.returncode,
            "duration_s": round(duration, 3),
            "tests_run": _parse_test_count(combined, TEST_COUNT),
            "failures": _parse_test_count(combined, FAILURE_COUNT),
            "errors": _parse_test_count(combined, ERROR_COUNT),
            "skipped": _parse_test_count(combined, SKIPPED_COUNT),
            "stdout_sha256": stdout_sha,
            "stderr_sha256": stderr_sha,
        })
        if result.returncode != 0:
            break
    return records


def _all_pass(records):
    return records and all(item.get("status") == "pass" for item in records)


def _failure_record(run_root, errors, facts):
    return {
        "schema_version": "1.0.0",
        "status": "acceptance_failed_no_public_report_written",
        "checkpoint": "22H",
        "errors": list(errors),
        "safe_facts": facts,
    }


# The acceptance recording and the truth record it is checked against. They are
# constants rather than literals inside the command builders so that a copy of
# this repository carrying different audio changes two lines and not the code,
# and so that no recording filename is embedded in a function body. The public
# snapshot points both at the openly licensed fixture.
ACCEPTANCE_AUDIO = REPOSITORY_ROOT / "regression" / "fixtures" / "conversation.wav"
ACCEPTANCE_FIXTURE_ID = "fixture_conversation"


def _pipeline_command(run_id, pipeline_base):
    audio = ACCEPTANCE_AUDIO
    if not audio.is_file():
        raise FinalAcceptanceError("known conversation acceptance recording is missing")
    return [
        "caffeinate", "-dimsu", sys.executable,
        str(REPOSITORY_ROOT / "pipeline" / "run_all.py"),
        "--mode", "conversation",
        "--speakers", "2",
        "--audio", str(audio),
        "--output-dir", str(pipeline_base),
        "--isolated-run",
        "--run-id", run_id,
    ]


def _regression_command(output_dir, report_dir):
    return [
        sys.executable, "-m", "regression.run",
        "--synthetic-only",
        "--artifact", f"{ACCEPTANCE_FIXTURE_ID}={output_dir}",
        "--report-dir", str(report_dir),
    ]


def _quota_failure_exists():
    if not PRIVATE_ACCEPTANCE_ROOT.is_dir():
        return False
    for path in PRIVATE_ACCEPTANCE_ROOT.glob("*/acceptance-failure.json"):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (document.get("safe_facts") or {}).get("quota_exhaustion") is True:
            return True
    return False


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-id",
        default=datetime.now().strftime("22h_%Y%m%dT%H%M%S"),
    )
    parser.add_argument("--acknowledge-engineering-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.acknowledge_engineering_only:
        parser.error("--acknowledge-engineering-only is required")
    if not re.fullmatch(r"22h_[0-9]{8}T[0-9]{6}", args.run_id):
        parser.error("--run-id must use 22h_YYYYMMDDTHHMMSS")

    contract = load_final_contract()
    if REPORT_PATH.exists() or REPORT_PATH.is_symlink():
        raise SystemExit(
            f"Final report already exists and will not be overwritten: {REPORT_PATH}"
        )
    if _quota_failure_exists():
        raise SystemExit(
            "A prior acceptance run recorded quota exhaustion. The frozen "
            "contract prohibits rerunning to chase a different result."
        )
    PRIVATE_ACCEPTANCE_ROOT.mkdir(parents=True, exist_ok=True)
    run_root = PRIVATE_ACCEPTANCE_ROOT / args.run_id
    if run_root.exists() or run_root.is_symlink():
        raise SystemExit(f"Private acceptance run already exists: {run_root}")
    run_root.mkdir()
    log_root = run_root / "logs"
    log_root.mkdir()
    pipeline_base = run_root / "normal_pipeline"
    regression_dir = run_root / "regression"
    private_manifest_path = run_root / "acceptance-manifest.json"
    failure_path = run_root / "acceptance-failure.json"

    started_at = _utc_now()
    before = snapshot_protected_state()
    public_before = snapshot_public_repository()
    repo_before = source_revision(REPOSITORY_ROOT)
    acceptance_source_sha = _acceptance_source_digest()
    errors = []
    validators = []
    compilation = {}
    tests = []
    pipeline_record = {
        "status": "fail",
        "run_id": args.run_id,
        "process_exit_code": None,
    }
    static = static_pipeline_leakage(contract)
    runtime = {
        "status": "fail",
        "forbidden_filename_matches": [],
        "forbidden_key_matches": [],
        "forbidden_content_matches": [],
        "unreadable_artifacts": [],
    }
    quota_exhaustion_detected = False

    try:
        baseline = contract["repository_acceptance_policy"]["normal_pipeline"]
        if repo_before["git_commit"] != baseline["frozen_pre_22h_git_commit"]:
            errors.append("Git revision differs from the frozen pre-22H baseline")
        if repo_before["source_tree_sha256"] != baseline[
            "frozen_pre_22h_active_source_tree_sha256"
        ]:
            errors.append("active pipeline source differs from the frozen pre-22H baseline")
        if PIPELINE_VERSION != baseline["frozen_pre_22h_pipeline_version"]:
            errors.append("pipeline version differs from the frozen pre-22H baseline")
        if canonical_digest(model_registry()) != baseline[
            "frozen_pre_22h_model_registry_sha256"
        ]:
            errors.append("model registry differs from the frozen pre-22H baseline")
        if canonical_digest(prompt_registry()) != baseline[
            "frozen_pre_22h_prompt_registry_sha256"
        ]:
            errors.append("prompt registry differs from the frozen pre-22H baseline")

        if errors:
            raise FinalAcceptanceError("; ".join(errors))
        validators = _run_validators(contract, log_root)
        if len(validators) != len(
            contract["repository_acceptance_policy"]["required_validators"]
        ) or not _all_pass(validators):
            errors.append("one or more required validators failed")

        if not errors:
            compilation = _run_compilation(contract, log_root)
            if compilation["status"] != "pass":
                errors.append("Python compilation failed")

        if not errors:
            tests = _run_tests(contract, log_root)
            if len(tests) != len(
                contract["repository_acceptance_policy"]["required_test_commands"]
            ) or not _all_pass(tests):
                errors.append("one or more required test commands failed")

        if static["status"] != "pass":
            errors.append("normal pipeline static leakage check failed")

        if not errors:
            print("Running isolated normal conversation pipeline under caffeinate", flush=True)
            result, duration, pipeline_stdout_sha, pipeline_stderr_sha = _run(
                _pipeline_command(args.run_id, pipeline_base),
                label="normal_pipeline",
                log_root=log_root,
            )
            output_dir = pipeline_base / args.run_id
            regression_report = {}
            regression_result = None
            regression_stdout_sha = None
            regression_stderr_sha = None
            if result.returncode == 0 and output_dir.is_dir():
                print("Running independent real conversation regression", flush=True)
                (
                    regression_result, _, regression_stdout_sha,
                    regression_stderr_sha,
                ) = _run(
                    _regression_command(output_dir, regression_dir),
                    label="regression",
                    log_root=log_root,
                )
                if regression_result.returncode == 0:
                    try:
                        regression_report = json.loads(
                            (regression_dir / "regression_report.json")
                            .read_text(encoding="utf-8")
                        )
                    except (OSError, json.JSONDecodeError):
                        errors.append("independent regression report is unreadable")
                else:
                    errors.append("independent regression command failed")
            pipeline_record, pipeline_errors = analyze_pipeline_output(
                output_dir, args.run_id, regression_report, contract
            )
            pipeline_record["process_exit_code"] = result.returncode
            pipeline_record["process_duration_s"] = round(duration, 3)
            pipeline_record["process_stdout_sha256"] = pipeline_stdout_sha
            pipeline_record["process_stderr_sha256"] = pipeline_stderr_sha
            regression_record = pipeline_record.get("regression") or {}
            regression_path = regression_dir / "regression_report.json"
            regression_record.update({
                "process_exit_code": (
                    regression_result.returncode
                    if regression_result is not None else None
                ),
                "stdout_sha256": regression_stdout_sha,
                "stderr_sha256": regression_stderr_sha,
                "report_sha256": (
                    file_sha256(regression_path)
                    if regression_path.is_file() else None
                ),
            })
            pipeline_record["regression"] = regression_record
            combined_process_text = (
                (result.stdout or "") + "\n" + (result.stderr or "")
            ).casefold()
            quota_exhaustion_detected = any(
                token in combined_process_text
                for token in ("resource_exhausted", "quota_exhaustion", "http 429")
            )
            if result.returncode != 0:
                pipeline_errors.append("normal pipeline command failed")
                pipeline_record["status"] = "fail"
            errors.extend(pipeline_errors)
            if output_dir.is_dir():
                runtime = runtime_output_leakage(output_dir, contract)
            if runtime["status"] != "pass":
                errors.append("normal pipeline runtime leakage check failed")
    except (FinalAcceptanceError, OSError, subprocess.SubprocessError) as exc:
        errors.append(str(exc))
    finally:
        after = snapshot_protected_state()
        public_after = snapshot_public_repository()

    repo_after = source_revision(REPOSITORY_ROOT)
    if repo_after != repo_before:
        errors.append("active pipeline source or Git state changed during acceptance")
    if _acceptance_source_digest() != acceptance_source_sha:
        errors.append("acceptance source changed during acceptance")
    protected = {
        "before_sha256": before["sha256"],
        "after_sha256": after["sha256"],
        "unchanged": before == after,
        "history_unchanged": (
            _snapshot_subset_digest(before, "history.json")
            == _snapshot_subset_digest(after, "history.json")
        ),
        "progress_unchanged": (
            _snapshot_subset_digest(before, "progress.md")
            == _snapshot_subset_digest(after, "progress.md")
        ),
        "root_output_unchanged": (
            _snapshot_subset_digest(before, "output")
            == _snapshot_subset_digest(after, "output")
        ),
        "public_repository_unchanged": public_before == public_after,
    }
    if not all(
        protected[field]
        for field in (
            "unchanged", "history_unchanged", "progress_unchanged",
            "root_output_unchanged",
            "public_repository_unchanged",
        )
    ):
        errors.append("personal files or root output changed during acceptance")

    leakage = {
        "status": "pass" if static["status"] == runtime["status"] == "pass" else "fail",
        "pipeline_import_matches": static["pipeline_import_matches"],
        "dynamic_import_or_literal_matches": static[
            "dynamic_import_or_literal_matches"
        ],
        "stage_or_output_matches": static["stage_or_output_matches"],
        "forbidden_filename_matches": runtime["forbidden_filename_matches"],
        "forbidden_key_matches": runtime["forbidden_key_matches"],
        "forbidden_content_matches": runtime["forbidden_content_matches"],
        "unreadable_artifacts": runtime["unreadable_artifacts"],
    }

    owner = {
        "status": "not_performed_no_task_matched_owner_recording_available",
        "task_matched_recording_available": False,
        "used_for_selection": False,
        "used_for_accuracy": False,
        "used_for_fairness": False,
        "external_transfer": False,
        "private_artifact_committed": False,
    }

    completed_at = _utc_now()
    manifest = {
        "schema_version": "1.0.0",
        "manifest_id": "speech_sound_patterns_final_acceptance_evidence_v1",
        "manifest_version": "1.0.0",
        "checkpoint": "22H",
        "status": "acceptance_complete",
        "contract": {
            "path": CONTRACT_PATH.name,
            "sha256": CONTRACT_SHA256,
            "version": "1.0.0",
        },
        "repository": {
            "git_commit": repo_before["git_commit"],
            "working_tree_dirty": repo_before["working_tree_dirty"],
            "source_tree_sha256": repo_before["source_tree_sha256"],
            "acceptance_source_sha256": acceptance_source_sha,
            "started_at_utc": started_at,
            "completed_at_utc": completed_at,
            "acceptance_python": {
                "command_name": "acceptance_python",
                "implementation": platform.python_implementation(),
                "version": platform.python_version(),
                "executable_name": Path(sys.executable).resolve().name,
                "executable_sha256": file_sha256(Path(sys.executable).resolve()),
            },
            "public_repository_before_sha256": public_before["sha256"],
            "public_repository_after_sha256": public_after["sha256"],
        },
        "held_out_audit": {
            "status": "sealed_no_access",
            "resolution": "held_out_remains_sealed_no_evaluation",
            "access_audit_scope": (
                "procedure_and_code_path_without_operating_system_file_access_audit"
            ),
            "private_assignment_files_opened": 0,
            "participant_identities_read": 0,
            "labels_read": 0,
            "audio_files_read": 0,
            "derived_rows_read": 0,
            "local_model_runs": 0,
            "provider_transmissions": 0,
        },
        "validations": validators,
        "python_compilation": compilation,
        "tests": tests,
        "owner_functional_integration": owner,
        "normal_pipeline": pipeline_record,
        "protected_state": protected,
        "leakage_checks": leakage,
        "evidence_inventory": build_evidence_inventory(run_root),
    }

    manifest_errors = validate_private_manifest(
        manifest, contract=contract, evidence_root=run_root
    )
    errors.extend(error for error in manifest_errors if error not in errors)
    if errors:
        safe_facts = {
            "held_out_accessed": False,
            "protected_state_unchanged": protected["unchanged"],
            "validator_records": len(validators),
            "test_records": len(tests),
            "normal_pipeline_status": pipeline_record.get("status"),
            "quota_exhaustion": any(
                item.get("error_category") == "quota_exhaustion"
                for item in (pipeline_record.get("enrichment") or {}).values()
            ) or quota_exhaustion_detected,
        }
        write_exclusive_atomic(
            failure_path,
            canonical_json_bytes(_failure_record(run_root, errors, safe_facts)),
        )
        print("Final acceptance failed. No public report was written.")
        for error in errors:
            print(f"  {error}")
        print(f"Private failure record: {failure_path}")
        raise SystemExit(1)

    report = build_final_report(manifest, contract=contract)
    report_errors = validate_final_report(
        report, contract=contract, manifest=manifest
    )
    if report_errors:
        write_exclusive_atomic(
            failure_path,
            canonical_json_bytes(
                _failure_record(run_root, report_errors, {
                    "held_out_accessed": False,
                    "protected_state_unchanged": True,
                    "normal_pipeline_status": pipeline_record["status"],
                })
            ),
        )
        raise SystemExit("Final report failed exact private-evidence validation")

    report_bytes = canonical_json_bytes(report)
    rebuilt_before_publish = canonical_json_bytes(
        build_final_report(manifest, contract=contract)
    )
    if report_bytes != rebuilt_before_publish:
        raise SystemExit("Final report did not reproduce before publication")
    write_exclusive_atomic(private_manifest_path, canonical_json_bytes(manifest))
    final_manifest = json.loads(private_manifest_path.read_text(encoding="utf-8"))
    final_manifest_errors = validate_private_manifest(
        final_manifest, contract=contract, evidence_root=run_root
    )
    if final_manifest_errors:
        raise SystemExit(
            "Private acceptance evidence changed before report publication"
        )
    write_final_report(report)
    rebuilt = build_final_report(
        json.loads(private_manifest_path.read_text(encoding="utf-8")),
        contract=contract,
    )
    if canonical_json_bytes(rebuilt) != REPORT_PATH.read_bytes():
        raise SystemExit("Final report did not reproduce byte for byte")

    print("Final repository acceptance: PASS")
    print("Held-out participants remained sealed and were not evaluated.")
    print(f"Private acceptance evidence: {private_manifest_path}")
    print(f"Safe aggregate report: {REPORT_PATH}")
    print("Scientific and product release remain locked.")


if __name__ == "__main__":
    main()
