"""Validate the immutable post-report repository closure for checkpoint 22H."""

from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess

from .feasibility import REPOSITORY_ROOT, file_sha256
from .final_acceptance import (
    CONTRACT_PATH,
    CONTRACT_SHA256,
    FINAL_DECISION,
    REPORT_PATH,
    FinalAcceptanceError,
    _read_json,
    canonical_digest,
    load_final_contract,
    snapshot_public_repository,
    validate_final_report,
    write_exclusive_atomic,
)


MODULE_ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = MODULE_ROOT / "repository-closure-v1.0.0.json"
CLOSURE_RELATIVE_PATH = CLOSURE_PATH.relative_to(REPOSITORY_ROOT).as_posix()
ACTIVE_RESEARCH_CONTRACT_PATH = MODULE_ROOT / "research-contract-v1.7.0.json"

CLOSURE_FIELDS = {
    "schema_version", "closure_id", "closure_version", "checkpoint", "status",
    "final_acceptance_contract", "final_evidence", "active_research_contract",
    "public_repository", "verification", "release_boundaries", "decision",
}


def _git_environment():
    """Ignore caller-provided repository redirection and replacement objects."""
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return environment


def _git(repo_root, arguments, **kwargs):
    repo_root = Path(repo_root).resolve()
    command = ["git", "--no-replace-objects", "-C", str(repo_root), *arguments]
    return subprocess.run(command, env=_git_environment(), **kwargs)


def _require_repository(repo_root):
    repo_root = Path(repo_root).resolve()
    try:
        top = _git(
            repo_root,
            ["rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FinalAcceptanceError("historical snapshot root is not a Git repository") from exc
    if Path(top).resolve() != repo_root:
        raise FinalAcceptanceError("historical snapshot Git root differs from repository")


def _require_regular_file(path, label):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise FinalAcceptanceError(f"{label} must be a regular repository file")


def _git_blob(repo_root, revision, relative):
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or ".." in Path(relative).parts
    ):
        raise FinalAcceptanceError("historical Git blob path is invalid")
    try:
        return _git(
            repo_root,
            ["show", f"{revision}:{relative}"],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FinalAcceptanceError(
            f"historical Git blob is unavailable: {relative}"
        ) from exc


def _historical_config_literal(repo_root, revision, name):
    """Read one literal module-level assignment from a historical config tree."""
    config_bytes = _git_blob(
        repo_root, revision, "pipeline/pipeline_config.py"
    )
    try:
        tree = ast.parse(config_bytes.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise FinalAcceptanceError(
            "historical pipeline configuration is unreadable"
        ) from exc
    for node in tree.body:
        if isinstance(node, ast.Assign):
            matched = any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            )
        elif isinstance(node, ast.AnnAssign):
            matched = isinstance(node.target, ast.Name) and node.target.id == name
        else:
            continue
        if not matched:
            continue
        if node.value is None:
            raise FinalAcceptanceError(
                f"historical {name} declaration has no value"
            )
        try:
            return ast.literal_eval(node.value)
        except (ValueError, TypeError) as exc:
            raise FinalAcceptanceError(
                f"historical {name} declaration is not literal"
            ) from exc
    raise FinalAcceptanceError(f"historical {name} declaration is missing")


def historical_pipeline_version(revision, repo_root=REPOSITORY_ROOT):
    """Read the pipeline version from one historical tree, never from live state."""
    repo_root = Path(repo_root).resolve()
    _require_repository(repo_root)
    version = _historical_config_literal(
        repo_root, revision, "PIPELINE_VERSION"
    )
    if not isinstance(version, str) or not version:
        raise FinalAcceptanceError("historical pipeline version is invalid")
    return version


def historical_active_source_digest(revision, repo_root=REPOSITORY_ROOT):
    """Recompute provenance source identity entirely from one historical tree."""
    repo_root = Path(repo_root).resolve()
    _require_repository(repo_root)
    active_files = _historical_config_literal(
        repo_root, revision, "ACTIVE_SOURCE_FILES"
    )
    if (
        not isinstance(active_files, (tuple, list))
        or not active_files
        or any(not isinstance(item, str) or not item for item in active_files)
        or len(set(active_files)) != len(active_files)
    ):
        raise FinalAcceptanceError(
            "historical active source declaration is invalid"
        )
    digest = hashlib.sha256()
    for relative in active_files:
        content = _git_blob(repo_root, revision, relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def snapshot_git_repository(revision, repo_root=REPOSITORY_ROOT, *, exclude_paths=()):
    """Rebuild the public-file snapshot from one immutable Git tree."""
    repo_root = Path(repo_root).resolve()
    _require_repository(repo_root)
    try:
        listing = _git(
            repo_root,
            ["ls-tree", "-rz", "--full-tree", str(revision)],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FinalAcceptanceError(
            "cannot enumerate historical repository snapshot"
        ) from exc

    # git always reports forward slashes, so the exclusion set has to be
    # spelled the same way. str(Path(...)) gives backslashes on Windows and
    # never matched, which silently left the closure file inside its own
    # snapshot and made the commit unfindable. Measured 2026-08-29.
    excluded = {Path(item).as_posix() for item in exclude_paths}
    records = []
    object_ids = []
    for raw in listing.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, encoded_path = raw.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split()
            relative = encoded_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise FinalAcceptanceError(
                "historical repository tree entry is malformed"
            ) from exc
        if relative in excluded:
            continue
        if object_type != "blob":
            raise FinalAcceptanceError(
                f"historical public repository entry is not a blob: {relative}"
            )
        records.append((relative, mode, object_id))
        object_ids.append(object_id)

    try:
        batch = _git(
            repo_root,
            ["cat-file", "--batch"],
            check=True,
            input=("\n".join(object_ids) + "\n").encode("ascii"),
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FinalAcceptanceError(
            "cannot read historical repository snapshot"
        ) from exc

    stream = io.BytesIO(batch)
    entries = []
    for relative, mode, expected_object_id in records:
        header = stream.readline().rstrip(b"\n")
        try:
            object_id, object_type, encoded_size = header.decode("ascii").split()
            size = int(encoded_size)
        except (UnicodeDecodeError, ValueError) as exc:
            raise FinalAcceptanceError(
                "historical repository blob header is malformed"
            ) from exc
        content = stream.read(size)
        terminator = stream.read(1)
        if (
            object_id != expected_object_id
            or object_type != "blob"
            or len(content) != size
            or terminator != b"\n"
        ):
            raise FinalAcceptanceError(
                "historical repository blob content is malformed"
            )
        if mode == "120000":
            try:
                target = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise FinalAcceptanceError(
                    f"historical symlink target is not UTF-8: {relative}"
                ) from exc
            entries.append({"path": relative, "type": "symlink", "target": target})
        else:
            entries.append({
                "path": relative,
                "type": "file",
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": size,
            })
    if stream.read(1):
        raise FinalAcceptanceError("historical repository blob batch has extra data")
    entries.sort(key=lambda item: item["path"])
    return {"entries": entries, "sha256": canonical_digest(entries)}


def find_historical_closure_commit(
    document,
    repo_root=REPOSITORY_ROOT,
    *,
    frozen_revision=None,
):
    """Find the direct child of acceptance whose tree matches the closure."""
    repo_root = Path(repo_root).resolve()
    _require_repository(repo_root)
    closure_path = repo_root / CLOSURE_RELATIVE_PATH
    _require_regular_file(closure_path, "repository closure")
    if frozen_revision is None:
        contract = load_final_contract()
        report = _read_json(REPORT_PATH)
        contract_revision = contract["repository_acceptance_policy"][
            "normal_pipeline"
        ]["frozen_pre_22h_git_commit"]
        report_revision = (report.get("repository_acceptance") or {}).get(
            "git_commit"
        )
        if contract_revision != report_revision:
            raise FinalAcceptanceError(
                "frozen acceptance revisions disagree"
            )
        frozen_revision = contract_revision
    try:
        revisions = _git(
            repo_root,
            ["log", "--format=%H", "--", CLOSURE_RELATIVE_PATH],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        current_closure = closure_path.read_bytes()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FinalAcceptanceError(
            "cannot locate historical repository closure"
        ) from exc

    expected = document.get("public_repository") or {}
    for revision in revisions:
        try:
            parents = _git(
                repo_root,
                ["rev-list", "--parents", "-n", "1", revision],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip().split()
            if parents != [revision, frozen_revision]:
                continue
            committed_closure = _git(
                repo_root,
                ["show", f"{revision}:{CLOSURE_RELATIVE_PATH}"],
                check=True,
                capture_output=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError):
            continue
        if committed_closure != current_closure:
            continue
        snapshot = snapshot_git_repository(
            revision,
            repo_root,
            exclude_paths={CLOSURE_RELATIVE_PATH},
        )
        if (
            snapshot["sha256"] == expected.get("snapshot_sha256")
            and len(snapshot["entries"]) == expected.get("file_count")
        ):
            return revision
    return None


def build_repository_closure(evidence):
    """Build the closure after all post-report public edits and checks finish."""
    _require_regular_file(CONTRACT_PATH, "final acceptance contract")
    _require_regular_file(REPORT_PATH, "final evidence")
    _require_regular_file(
        ACTIVE_RESEARCH_CONTRACT_PATH, "active research contract"
    )
    contract = load_final_contract()
    report = _read_json(REPORT_PATH)
    report_errors = validate_final_report(report, contract=contract)
    if report_errors:
        raise FinalAcceptanceError("\n".join(report_errors))
    if not ACTIVE_RESEARCH_CONTRACT_PATH.is_file():
        raise FinalAcceptanceError("active research contract v1.7 is missing")
    research = _read_json(ACTIVE_RESEARCH_CONTRACT_PATH)
    if research.get("protocol_version") != "1.7.0":
        raise FinalAcceptanceError("active research contract version changed")
    return {
        "schema_version": "1.0.0",
        "closure_id": "speech_sound_patterns_repository_closure_v1",
        "closure_version": "1.0.0",
        "checkpoint": "22H",
        "status": "item_22_engineering_repository_closed_release_locked",
        "final_acceptance_contract": {
            "path": CONTRACT_PATH.name,
            "sha256": CONTRACT_SHA256,
            "status": contract["status"],
        },
        "final_evidence": {
            "path": REPORT_PATH.name,
            "sha256": file_sha256(REPORT_PATH),
            "status": report["status"],
            "decision": report["engineering_decision"]["decision"],
        },
        "active_research_contract": {
            "path": ACTIVE_RESEARCH_CONTRACT_PATH.name,
            "sha256": file_sha256(ACTIVE_RESEARCH_CONTRACT_PATH),
            "protocol_version": research["protocol_version"],
            "status": research["status"],
        },
        "public_repository": copy.deepcopy(evidence["public_repository"]),
        "verification": copy.deepcopy(evidence["verification"]),
        "release_boundaries": copy.deepcopy(contract["release_boundaries"]),
        "decision": {
            "decision": FINAL_DECISION,
            "item_22_engineering_complete": True,
            "held_out_evaluation_performed": False,
            "held_out_performance_established": False,
            "candidate_system_or_rule_selected": False,
            "normal_pipeline_speech_sound_activation": False,
            "scientific_release": False,
            "product_release": False,
            "next_roadmap_item_approved": False,
        },
    }


def _validate_repository_closure(document, *, check_public_snapshot=True):
    errors = []
    required_regular_files = [
        (CONTRACT_PATH, "final acceptance contract"),
        (REPORT_PATH, "final evidence"),
        (ACTIVE_RESEARCH_CONTRACT_PATH, "active research contract"),
    ]
    if check_public_snapshot:
        required_regular_files.append((CLOSURE_PATH, "repository closure"))
    for path, label in required_regular_files:
        try:
            _require_regular_file(path, label)
        except FinalAcceptanceError as exc:
            errors.append(str(exc))
    if errors:
        return errors
    contract = load_final_contract()
    if not isinstance(document, dict) or set(document) != CLOSURE_FIELDS:
        return ["repository closure root fields changed"]
    exact = {
        "schema_version": "1.0.0",
        "closure_id": "speech_sound_patterns_repository_closure_v1",
        "closure_version": "1.0.0",
        "checkpoint": "22H",
        "status": "item_22_engineering_repository_closed_release_locked",
    }
    for field, expected in exact.items():
        if document.get(field) != expected:
            errors.append(f"repository closure {field} changed")
    if document.get("final_acceptance_contract") != {
        "path": CONTRACT_PATH.name,
        "sha256": CONTRACT_SHA256,
        "status": contract["status"],
    }:
        errors.append("repository closure final contract binding changed")
    report = _read_json(REPORT_PATH)
    if document.get("final_evidence") != {
        "path": REPORT_PATH.name,
        "sha256": file_sha256(REPORT_PATH),
        "status": report.get("status"),
        "decision": (report.get("engineering_decision") or {}).get("decision"),
    }:
        errors.append("repository closure final evidence binding changed")
    errors.extend(validate_final_report(report, contract=contract))
    research = _read_json(ACTIVE_RESEARCH_CONTRACT_PATH)
    if document.get("active_research_contract") != {
        "path": ACTIVE_RESEARCH_CONTRACT_PATH.name,
        "sha256": file_sha256(ACTIVE_RESEARCH_CONTRACT_PATH),
        "protocol_version": "1.7.0",
        "status": research.get("status"),
    }:
        errors.append("repository closure active research contract binding changed")

    public = document.get("public_repository") or {}
    if set(public) != {
        "closure_excluded_path", "only_exclusion", "snapshot_sha256", "file_count",
    }:
        errors.append("repository closure public snapshot fields changed")
    if public.get("closure_excluded_path") != CLOSURE_RELATIVE_PATH:
        errors.append("repository closure excluded path changed")
    if public.get("only_exclusion") is not True:
        errors.append("repository closure must exclude only itself")
    if not isinstance(public.get("snapshot_sha256"), str) or len(
        public.get("snapshot_sha256", "")
    ) != 64:
        errors.append("repository closure public snapshot checksum is invalid")
    if not isinstance(public.get("file_count"), int) or isinstance(
        public.get("file_count"), bool
    ) or public.get("file_count", 0) <= 0:
        errors.append("repository closure public file count is invalid")
    if check_public_snapshot:
        snapshot = snapshot_public_repository(exclude_paths={CLOSURE_RELATIVE_PATH})
        current_matches = (
            public.get("snapshot_sha256") == snapshot["sha256"]
            and public.get("file_count") == len(snapshot["entries"])
        )
        if not current_matches:
            historical_commit = find_historical_closure_commit(document)
            if historical_commit is None:
                if public.get("snapshot_sha256") != snapshot["sha256"]:
                    errors.append(
                        "public repository differs from the closed snapshot and "
                        "no matching historical closure commit exists"
                    )
                if public.get("file_count") != len(snapshot["entries"]):
                    errors.append(
                        "public repository file count differs from closure and "
                        "no matching historical closure commit exists"
                    )

    verification = document.get("verification") or {}
    if set(verification) != {
        "private_acceptance_evidence_revalidated", "validator_commands",
        "validator_commands_passed", "python_compilation", "test_commands",
        "protected_state_unchanged", "public_state_unchanged_during_closure",
        "acceptance_source_sha256", "acceptance_python",
    }:
        errors.append("repository closure verification fields changed")
    if verification.get("private_acceptance_evidence_revalidated") is not True:
        errors.append("private acceptance evidence was not revalidated")
    if verification.get("validator_commands") != verification.get(
        "validator_commands_passed"
    ) or not isinstance(verification.get("validator_commands"), int) or (
        verification.get("validator_commands", 0) <= 0
    ):
        errors.append("repository closure validators did not all pass")
    if verification.get("python_compilation") != "pass":
        errors.append("repository closure Python compilation did not pass")
    if verification.get("protected_state_unchanged") is not True:
        errors.append("protected state changed during repository closure")
    if verification.get("public_state_unchanged_during_closure") is not True:
        errors.append("public state changed during repository closure")
    report_source = (report.get("repository_acceptance") or {}).get(
        "acceptance_source_sha256"
    )
    if verification.get("acceptance_source_sha256") != report_source:
        errors.append("repository closure acceptance source binding changed")
    if verification.get("acceptance_python") != (
        report.get("repository_acceptance") or {}
    ).get("acceptance_python"):
        errors.append("repository closure acceptance Python identity changed")
    required_validator_count = len(
        contract["repository_acceptance_policy"]["required_validators"]
    ) + 1
    if verification.get("validator_commands") != required_validator_count:
        errors.append("repository closure validator count changed")
    tests = verification.get("test_commands")
    required_commands = contract["repository_acceptance_policy"][
        "required_test_commands"
    ]
    if not isinstance(tests, list) or [
        item.get("command") for item in tests if isinstance(item, dict)
    ] != required_commands:
        errors.append("repository closure test evidence is missing")
    else:
        for item in tests:
            if (
                not isinstance(item, dict)
                or set(item) != {
                    "command", "status", "tests_run", "failures", "errors",
                    "skipped",
                }
                or item.get("status") != "pass"
                or any(
                    item.get(field) != 0
                    for field in ("failures", "errors", "skipped")
                )
                or not isinstance(item.get("tests_run"), int)
                or isinstance(item.get("tests_run"), bool)
                or item.get("tests_run", 0) < contract[
                    "repository_acceptance_policy"
                ]["required_test_minimums"][item["command"]]
            ):
                errors.append("repository closure test evidence is invalid")
    if document.get("release_boundaries") != contract["release_boundaries"]:
        errors.append("repository closure release boundaries changed")
    if document.get("decision") != {
        "decision": FINAL_DECISION,
        "item_22_engineering_complete": True,
        "held_out_evaluation_performed": False,
        "held_out_performance_established": False,
        "candidate_system_or_rule_selected": False,
        "normal_pipeline_speech_sound_activation": False,
        "scientific_release": False,
        "product_release": False,
        "next_roadmap_item_approved": False,
    }:
        errors.append("repository closure decision changed")
    return errors


def validate_repository_closure(document, *, check_public_snapshot=True):
    try:
        return _validate_repository_closure(
            document, check_public_snapshot=check_public_snapshot
        )
    except Exception as exc:  # noqa: BLE001 - malformed closure must fail closed
        return [f"repository closure is malformed: {type(exc).__name__}"]


def write_repository_closure(document):
    errors = validate_repository_closure(document, check_public_snapshot=False)
    if errors:
        raise FinalAcceptanceError("\n".join(errors))
    from .feasibility import canonical_json_bytes

    write_exclusive_atomic(CLOSURE_PATH, canonical_json_bytes(document))
