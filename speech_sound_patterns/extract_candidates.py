"""Explicit offline command for the private checkpoint 22G candidate artifact.

This command assembles precomputed evidence. It does not load a speech model,
call a provider, search a threshold, read held-out data, or enter the normal
pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .candidate_artifact import (
    ARTIFACT_FILENAME,
    CandidateArtifactError,
    assert_valid_trial_manifest,
    build_artifact,
    load_candidate_contract,
    write_artifact,
)
from .feasibility import REPOSITORY_ROOT, file_sha256


PRIVATE_RESEARCH_ROOT = (
    REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
).resolve()
CANDIDATE_ROOT = (PRIVATE_RESEARCH_ROOT / "candidates").resolve()
MANIFEST_ROOT = (CANDIDATE_ROOT / "manifests").resolve()
PIPELINE_SENTINELS = {
    "run_manifest.json",
    "master.json",
    "listener.json",
    "evaluation.md",
    "evaluation_claims.json",
    "history.json",
    "progress.md",
}


def _inside(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return False
    return True


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateArtifactError(f"candidate manifest is unreadable: {path}") from exc


def _iter_evidence_refs(manifest):
    for trial in manifest.get("trials", []):
        audio = trial.get("audio") or {}
        if audio.get("path") is not None:
            yield "audio", audio["path"], audio.get("content_sha256")
        quality = trial.get("audio_quality") or {}
        yield "audio quality", quality.get("evidence_ref"), None
        raw = trial.get("raw_evidence") or {}
        for lane in ("asr", "alignment"):
            yield lane, (raw.get(lane) or {}).get("raw_output_ref"), None
        for system in raw.get("local_phone_systems") or []:
            yield "local system", system.get("raw_output_ref"), None
            for opportunity in system.get("opportunities") or []:
                yield "local proposal", opportunity.get("raw_output_ref"), None
        for provider in raw.get("cached_providers") or []:
            yield "cached provider", provider.get("raw_output_ref"), None
        for insertion in raw.get("insertions") or []:
            yield "insertion", insertion.get("raw_output_ref"), None


def _validate_ref(label, reference, expected_audio_sha=None):
    if reference is None:
        return
    if isinstance(reference, str):
        path_text = reference
        expected_sha = expected_audio_sha
    elif isinstance(reference, dict) and set(reference) == {"path", "sha256"}:
        path_text = reference["path"]
        expected_sha = reference["sha256"]
    else:
        raise CandidateArtifactError(
            f"{label} reference must be null, a private path, or path and sha256"
        )
    path = (REPOSITORY_ROOT / path_text).resolve()
    if not _inside(path, PRIVATE_RESEARCH_ROOT):
        raise CandidateArtifactError(f"{label} reference leaves the private research root")
    if not path.is_file():
        raise CandidateArtifactError(f"{label} referenced evidence is missing")
    if expected_sha is None:
        raise CandidateArtifactError(f"{label} referenced evidence needs a sha256")
    if file_sha256(path) != expected_sha:
        raise CandidateArtifactError(f"{label} referenced evidence checksum changed")


def _validate_private_inputs(manifest):
    for label, reference, expected_sha in _iter_evidence_refs(manifest):
        _validate_ref(label, reference, expected_sha)


def _validate_manifest_path(manifest_path):
    resolved = Path(manifest_path).resolve()
    if not _inside(resolved, MANIFEST_ROOT):
        raise CandidateArtifactError(
            "candidate manifest must be inside the private candidate manifests root"
        )
    if not resolved.is_file():
        raise CandidateArtifactError("candidate manifest is missing")
    return resolved


def _validate_output_root(output_dir):
    output_dir = Path(output_dir)
    resolved = output_dir.resolve()
    if not _inside(resolved, CANDIDATE_ROOT):
        raise CandidateArtifactError(
            "candidate output must be inside the private candidate output root"
        )
    if _inside(resolved, MANIFEST_ROOT):
        raise CandidateArtifactError("candidate output cannot be written over manifests")
    if output_dir.exists():
        raise CandidateArtifactError("candidate output directory must be new")
    parent = output_dir.parent
    while _inside(parent, CANDIDATE_ROOT):
        if parent.exists() and any((parent / name).exists() for name in PIPELINE_SENTINELS):
            raise CandidateArtifactError("candidate output path contains pipeline artifacts")
        if parent.resolve() == CANDIDATE_ROOT:
            break
        parent = parent.parent
    return output_dir


def extract(manifest_path, output_dir, *, acknowledged=False):
    """Build exactly one new private artifact after every boundary is checked."""
    if not acknowledged:
        raise CandidateArtifactError("developer-only acknowledgement is required")
    if os.environ.get("SPEECH_SOUND_OFFLINE") != "1":
        raise CandidateArtifactError("set SPEECH_SOUND_OFFLINE=1 before extraction")
    manifest_path = _validate_manifest_path(manifest_path)
    contract = load_candidate_contract()
    manifest = _load_json(manifest_path)
    assert_valid_trial_manifest(manifest, contract=contract)
    output_dir = _validate_output_root(output_dir)
    _validate_private_inputs(manifest)
    artifact = build_artifact(manifest, contract=contract)
    return artifact, write_artifact(artifact, output_dir / ARTIFACT_FILENAME)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Assemble one private developer-only speech sound artifact."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--acknowledge-developer-only",
        action="store_true",
        help="Acknowledge that this creates no product, clinical, or coaching result.",
    )
    args = parser.parse_args(argv)
    try:
        artifact, path = extract(
            args.manifest,
            args.output_dir,
            acknowledged=args.acknowledge_developer_only,
        )
    except CandidateArtifactError as exc:
        parser.error(str(exc))
    print("Speech sound candidate artifact: VALID")
    print(f"Trials: {len(artifact['trials'])}")
    print(
        "Expected opportunities: "
        f"{artifact['denominators']['expected_sound_opportunities']}"
    )
    print("Relation candidates: 0")
    print("Repeated relation candidates: 0")
    print(f"Written privately as {path.name}")


if __name__ == "__main__":
    main()
