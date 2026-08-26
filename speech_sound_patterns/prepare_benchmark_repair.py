"""Create label-blind expected-phone inputs for the checkpoint 22D repair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import (
    FROZEN_BENCHMARK_MANIFEST_SHA256,
    PRIVATE_BENCHMARK_ROOT,
    load_phone_map,
    scorable_reference_phone,
    strip_stress,
    validate_frozen_private_benchmark_manifest,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
DEFAULT_MANIFEST = PRIVATE_ROOT / "benchmark" / "benchmark-manifest-v1.0.0.json"
DEFAULT_OUTPUT = (
    PRIVATE_BENCHMARK_ROOT / "repair-v1" / "expected-only-manifest-v1.0.0.json"
)
FORBIDDEN_LABEL_KEYS = {
    "five_reviewer_phone_strings",
    "aggregate_mispronunciations",
    "reviewer_states",
    "reference_decision",
    "truth",
    "prediction",
    "pronounced-phone",
}


def _load(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"required private input is missing: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _speechocean_source(manifest):
    matches = [
        source
        for source in manifest["sources"]
        if source["source_id"] == "speechocean762"
    ]
    if len(matches) != 1:
        raise ValueError("frozen SpeechOcean source is unavailable")
    return matches[0]


def _assert_label_blind(value):
    if isinstance(value, dict):
        overlap = FORBIDDEN_LABEL_KEYS & set(value)
        if overlap:
            raise ValueError(
                "expected-only manifest contains expert result fields: "
                + ", ".join(sorted(overlap))
            )
        for item in value.values():
            _assert_label_blind(item)
    elif isinstance(value, list):
        for item in value:
            _assert_label_blind(item)


def build_expected_only_manifest(
    manifest,
    reference,
    manifest_sha256=None,
    expectation=None,
    expected_manifest_id="speech_sound_repair_expected_only_v1",
):
    """Return only intended phones and input identity, never expert outcomes.

    The defaults describe the frozen checkpoint 22D sample. Checkpoint 22E4B
    passes its powered manifest identity and sample expectation instead. The
    label-blind guarantee below does not depend on either.
    """
    if manifest_sha256 is None:
        manifest_sha256 = FROZEN_BENCHMARK_MANIFEST_SHA256
    errors = validate_frozen_private_benchmark_manifest(
        manifest, manifest_sha256, expectation=expectation
    )
    if errors:
        raise ValueError("; ".join(errors))
    source = _speechocean_source(manifest)
    clips = {clip["safe_id"]: clip for clip in source["clips"]}
    records = {record["safe_id"]: record for record in reference["records"]}
    expected_clip_count = 480
    if expectation is not None:
        expected_clip_count = expectation["clip_counts"]["speechocean762"]
    if set(clips) != set(records) or len(clips) != expected_clip_count:
        raise ValueError("SpeechOcean expected input and sample indexes differ")

    phone_map = load_phone_map()
    output_clips = []
    for safe_id in sorted(clips):
        clip = clips[safe_id]
        record = records[safe_id]
        if clip["project_split"] not in {"development", "threshold_tuning"}:
            raise ValueError("repair input cannot include a held-out participant")
        reference_phones = []
        word_starts = []
        targets = []
        for word in record["words"]:
            word_starts.append(len(reference_phones))
            phones = word["reference_phones"].split()
            for local_index, raw_phone in enumerate(phones):
                global_index = len(reference_phones)
                reference_phones.append(raw_phone)
                scorable, reason = scorable_reference_phone(
                    phones, local_index, phone_map
                )
                base = strip_stress(raw_phone)
                targets.append(
                    {
                        "global_index": global_index,
                        "word_index": word["word_index"],
                        "local_index": local_index,
                        "arpabet": base,
                        "ipa_parts": phone_map["reference_phones"][base]["ipa"],
                        "scorable": scorable,
                        "unscorable_reason": reason,
                    }
                )
        output_clips.append(
            {
                "safe_id": safe_id,
                "private_participant_id": clip["private_participant_id"],
                "project_split": clip["project_split"],
                "source_stratum": clip["source_stratum"],
                "canonical_audio_path": clip["canonical_audio_path"],
                "canonical_audio_sha256": clip["canonical_audio_sha256"],
                "duration_s": clip["duration_s"],
                "reference_phones": reference_phones,
                "word_starts": word_starts,
                "targets": targets,
            }
        )
    document = {
        "schema_version": "1.0.0",
        "expected_manifest_id": expected_manifest_id,
        "private_benchmark_manifest_sha256": manifest_sha256,
        "source_id": "speechocean762",
        "source_reference_sha256": source["private_reference_sha256"],
        "selection_used_expert_labels_or_model_outputs": False,
        "expert_outcomes_included": False,
        "held_out_participants": 0,
        "clips": output_clips,
    }
    _assert_label_blind(document)
    return document


def prepare(
    manifest_path=DEFAULT_MANIFEST,
    output_path=DEFAULT_OUTPUT,
    manifest_sha256=None,
    expectation=None,
    expected_manifest_id="speech_sound_repair_expected_only_v1",
):
    manifest = _load(manifest_path)
    source = _speechocean_source(manifest)
    reference_path = REPOSITORY_ROOT / source["private_reference_path"]
    if file_sha256(reference_path) != source["private_reference_sha256"]:
        raise ValueError("private SpeechOcean reference checksum changed")
    reference = _load(reference_path)
    document = build_expected_only_manifest(
        manifest,
        reference,
        manifest_sha256=manifest_sha256,
        expectation=expectation,
        expected_manifest_id=expected_manifest_id,
    )
    output_path = Path(output_path).resolve(strict=False)
    output_path.relative_to(PRIVATE_BENCHMARK_ROOT.resolve())
    if output_path.exists():
        raise ValueError("expected-only repair manifest already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json_bytes(document))
    return output_path, document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path, document = prepare(args.manifest, args.output)
    print(f"Expected-only repair input: {len(document['clips'])} clips")
    print(f"Held-out participants: {document['held_out_participants']}")
    print(f"Private manifest: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
