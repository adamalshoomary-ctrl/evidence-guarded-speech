"""Validate checkpoint 22G contracts, aggregates and private artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .candidate_artifact import (
    CandidateArtifactError,
    assert_valid_trial_manifest,
    build_artifact,
    load_candidate_contract,
    validate_candidate_artifact,
)
from .candidate_evidence import (
    REPORT_PATH,
    validate_candidate_evidence_report,
)
from .extract_candidates import (
    CANDIDATE_ROOT,
    MANIFEST_ROOT,
    _inside,
    _validate_manifest_path,
    _validate_private_inputs,
)
from .feasibility import canonical_json_sha256


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateArtifactError(f"JSON is unreadable: {path}") from exc


def _validate_artifact_path(path):
    resolved = Path(path).resolve()
    if not _inside(resolved, CANDIDATE_ROOT) or _inside(
        resolved, MANIFEST_ROOT
    ):
        raise CandidateArtifactError(
            "candidate artifact must be inside the private candidate output root"
        )
    if not resolved.is_file():
        raise CandidateArtifactError("candidate artifact is missing")
    return resolved


def validate_artifact_against_manifest(artifact, manifest, *, contract=None):
    """Rebuild an artifact so its embedded raw evidence cannot be self-certified."""
    contract = contract or load_candidate_contract()
    errors = validate_candidate_artifact(artifact, contract=contract)
    manifest_digest = canonical_json_sha256(manifest)
    if (artifact.get("input_manifest") or {}).get("sha256") != manifest_digest:
        errors.append("candidate artifact does not match the supplied manifest checksum")
    try:
        expected = build_artifact(manifest, contract=contract)
    except (CandidateArtifactError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"candidate manifest cannot rebuild the artifact: {exc}")
    else:
        if artifact != expected:
            errors.append("candidate artifact does not rebuild from the supplied manifest")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-report", type=Path, default=REPORT_PATH)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)
    if bool(args.artifact) != bool(args.manifest):
        parser.error("--artifact and --manifest must be supplied together")

    try:
        contract = load_candidate_contract()
        report_errors = validate_candidate_evidence_report(
            _read(args.evidence_report),
            contract=contract,
        )
        if args.artifact:
            manifest_path = _validate_manifest_path(args.manifest)
            artifact_path = _validate_artifact_path(args.artifact)
            manifest = _read(manifest_path)
            assert_valid_trial_manifest(manifest, contract=contract)
            _validate_private_inputs(manifest)
            artifact_errors = validate_artifact_against_manifest(
                _read(artifact_path),
                manifest,
                contract=contract,
            )
        else:
            artifact_errors = []
    except CandidateArtifactError as exc:
        parser.error(str(exc))

    errors = report_errors + artifact_errors
    if errors:
        print("Developer candidate extractor: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    if args.artifact:
        print("Private manifest-backed candidate artifact: VALID")
    else:
        print("Candidate contract and aggregate evidence report: VALID")
        print("No private candidate artifact was supplied or checked.")
    print("Evidence adequacy failed before any threshold or repeated-rule search.")
    print("No candidate system, relation rule, or repeated relation rule is selected.")
    print("Normal pipeline and every product or clinical boundary remain closed.")


if __name__ == "__main__":
    main()
