"""Versioned, isolated reliability and fairness audit."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pipeline.reliability_policy import (
    AUDIT_PROTOCOL_VERSION,
    FAIRNESS_DIMENSIONS,
    VALIDATION_POLICY_VERSION,
)
from pipeline.run_context import atomic_write_json, atomic_write_text
from regression.harness import (
    REPO_ROOT,
    compare_synthetic_truth,
    generate_synthetic_actual,
    load_truth,
    structural_diff,
)


SCHEMA_VERSION = "1.0.0"
REQUIRED_ARTIFACTS = (
    "run_manifest.json",
    "master.json",
    "transcript.json",
    "words_attributed.json",
    "audio_quality.json",
)


def _utc_now():
    return (datetime.now(timezone.utc).isoformat(timespec="seconds")
            .replace("+00:00", "Z"))


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_identity():
    files = (
        REPO_ROOT / "reliability" / "audit.py",
        REPO_ROOT / "pipeline" / "reliability_policy.py",
    )
    digest = hashlib.sha256()
    included = []
    for path in files:
        relative = str(path.relative_to(REPO_ROOT))
        included.append(relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {"files": included, "sha256": digest.hexdigest()}


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_artifact(label, directory):
    directory = Path(directory).expanduser().resolve()
    missing = [name for name in REQUIRED_ARTIFACTS
               if not (directory / name).is_file()]
    if missing:
        raise ValueError(
            f"{label} is missing required artifacts: {', '.join(missing)}"
        )
    manifest = _load_json(directory / "run_manifest.json")
    if manifest.get("status") != "complete":
        raise ValueError(f"{label} did not complete successfully")
    return {
        "label": label,
        "directory": str(directory),
        "manifest": manifest,
        "master": _load_json(directory / "master.json"),
        "transcript": _load_json(directory / "transcript.json"),
        "words": _load_json(directory / "words_attributed.json"),
        "quality": _load_json(directory / "audio_quality.json"),
        "acoustics": (_load_json(directory / "acoustics.json")
                      if (directory / "acoustics.json").is_file() else {}),
    }


def _pipeline_identity(artifact):
    provenance = artifact["manifest"].get("provenance") or {}
    pipeline = provenance.get("pipeline") or {}
    source = pipeline.get("source") or {}
    audio = provenance.get("input_audio") or {}
    return {
        "pipeline_version": pipeline.get("version"),
        "source_tree_sha256": source.get("source_tree_sha256"),
        "input_byte_sha256": audio.get("byte_sha256"),
        "input_duration_s": audio.get("duration_s"),
        "codec": audio.get("codec"),
        "sample_rate_hz": audio.get("sample_rate_hz"),
        "channels": audio.get("channels"),
    }


def _normalise_word(value):
    return re.sub(r"[^a-z0-9']+", "", str(value).lower())


def _word_tokens(artifact):
    return [_normalise_word(item.get("text")) for item in artifact["words"]
            if _normalise_word(item.get("text"))]


def _levenshtein(left, right):
    previous = list(range(len(right) + 1))
    for i, left_token in enumerate(left, 1):
        current = [i]
        for j, right_token in enumerate(right, 1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (left_token != right_token),
            ))
        previous = current
    return previous[-1]


def _pairwise_word_disagreement(left, right):
    left_tokens = _word_tokens(left)
    right_tokens = _word_tokens(right)
    denominator = max(len(left_tokens), len(right_tokens))
    edits = _levenshtein(left_tokens, right_tokens)
    return {
        "edit_count": edits,
        "denominator_words": denominator,
        "percentage": round(100 * edits / denominator, 2)
        if denominator else None,
        "interpretation": (
            "Pairwise pipeline disagreement only. This is not word error rate "
            "because neither transcript is an independent reference."
        ),
    }


def _speaker_disagreement(left, right):
    matched = 0
    disagreements = 0
    for left_word, right_word in zip(left["words"], right["words"]):
        if _normalise_word(left_word.get("text")) != _normalise_word(
                right_word.get("text")):
            continue
        matched += 1
        if left_word.get("speaker") != right_word.get("speaker"):
            disagreements += 1
    return {
        "disagreements": disagreements,
        "denominator_index_matched_words": matched,
        "percentage": round(100 * disagreements / matched, 2)
        if matched else None,
        "interpretation": (
            "Pairwise label disagreement on index matched words only. This is "
            "not speaker error because no independent speaker labels are used."
        ),
    }


def _flatten_numeric(value, prefix=""):
    result = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten_numeric(child, path))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        result[prefix] = value
    return result


def _metric_differences(left, right):
    left_values = _flatten_numeric({
        "computed_metrics": left["master"].get("computed_metrics") or {},
        "voice_prosody": (left["master"].get("meta") or {}).get(
            "per_speaker_voice_prosody") or {},
    })
    right_values = _flatten_numeric({
        "computed_metrics": right["master"].get("computed_metrics") or {},
        "voice_prosody": (right["master"].get("meta") or {}).get(
            "per_speaker_voice_prosody") or {},
    })
    rows = []
    for path in sorted(set(left_values) & set(right_values)):
        left_value = left_values[path]
        right_value = right_values[path]
        rows.append({
            "path": path,
            "left": left_value,
            "right": right_value,
            "absolute_difference": round(abs(left_value - right_value), 8),
            "release_threshold": None,
            "interpretation": "descriptive_only_not_a_progress_threshold",
        })
    return rows


def compare_repeat_artifacts(left, right):
    left_id = _pipeline_identity(left)
    right_id = _pipeline_identity(right)
    same_input = left_id["input_byte_sha256"] == right_id["input_byte_sha256"]
    same_version = left_id["pipeline_version"] == right_id["pipeline_version"]
    same_source = left_id["source_tree_sha256"] == right_id["source_tree_sha256"]
    return {
        "left": left["label"],
        "right": right["label"],
        "protocol_conditions": {
            "same_input_bytes": same_input,
            "same_pipeline_version": same_version,
            "same_source_tree": same_source,
        },
        "status": "observed" if same_input and same_version and same_source
        else "invalid_comparison",
        "word_disagreement": _pairwise_word_disagreement(left, right),
        "speaker_label_disagreement": _speaker_disagreement(left, right),
        "metric_differences": _metric_differences(left, right),
        "limitation": (
            "This combines provider and pipeline variation. Deterministic stage "
            "repeatability is tested separately with frozen upstream evidence."
        ),
    }


def compare_encoding_artifacts(left, right):
    left_id = _pipeline_identity(left)
    right_id = _pipeline_identity(right)
    duration_left = left_id.get("input_duration_s")
    duration_right = right_id.get("input_duration_s")
    duration_difference = (abs(duration_left - duration_right)
                           if duration_left is not None
                           and duration_right is not None else None)
    return {
        "left": left["label"],
        "right": right["label"],
        "encodings": [left_id.get("codec"), right_id.get("codec")],
        "duration_difference_s": round(duration_difference, 6)
        if duration_difference is not None else None,
        "same_pipeline_version": (
            left_id["pipeline_version"] == right_id["pipeline_version"]
        ),
        "same_source_tree": (
            left_id["source_tree_sha256"] == right_id["source_tree_sha256"]
        ),
        "word_disagreement": _pairwise_word_disagreement(left, right),
        "speaker_label_disagreement": _speaker_disagreement(left, right),
        "metric_differences": _metric_differences(left, right),
        "status": "descriptive_only",
        "limitation": (
            "A different encoding is tested. A second recording device is not "
            "available, so device repeatability remains untested."
        ),
    }


def _exact_repeatability():
    with tempfile.TemporaryDirectory(prefix="speech_reliability_exact_") as root:
        root = Path(root)
        first = generate_synthetic_actual(root / "first")
        second = generate_synthetic_actual(root / "second")
    differences = structural_diff(first, second)
    truth = load_truth(
        REPO_ROOT / "regression" / "truth" / "synthetic_controls.json"
    )
    deliberate = compare_synthetic_truth(first, truth)
    return {
        "status": "pass" if not differences else "fail",
        "requirement": "exact",
        "runs": 2,
        "differences": differences,
        "stages_exercised": [
            "audio quality", "acoustics", "merge metrics",
            "speaker attribution", "renderer", "claim verification",
        ],
        "deliberate_change_controls": {
            "status": deliberate["status"],
            "metrics": deliberate["metrics"],
            "failures": deliberate["failures"],
        },
    }


def _artifact_coverage(artifact, study_metadata):
    identity = _pipeline_identity(artifact)
    metadata = study_metadata.get(artifact["label"], {})
    transcript = artifact["transcript"]
    master = artifact["master"]
    measurement_entries = []
    measurement_metadata = master.get("measurement_metadata") or {}
    for sections in (measurement_metadata.get("speakers") or {}).values():
        for entries in sections.values():
            if isinstance(entries, dict):
                measurement_entries.extend(entries.values())
    measurement_entries.extend(
        (measurement_metadata.get("overall_voice_quality") or {}).values()
    )
    unavailable = sum(
        item.get("availability", {}).get("status") != "available"
        for item in measurement_entries if isinstance(item, dict)
    )
    denominator = sum(isinstance(item, dict) for item in measurement_entries)
    unavailable_rate = {
        "numerator": unavailable,
        "denominator": denominator,
        "percentage": round(100 * unavailable / denominator, 2)
        if denominator else None,
    }
    return {
        "artifact": artifact["label"],
        "recording_type": (master.get("meta") or {}).get("recording_type"),
        "participant_id": metadata.get("participant_id"),
        "language": metadata.get("language"),
        "provider_detected_language": transcript.get("language_code"),
        "accent": metadata.get("accent"),
        "age_band": metadata.get("age_band"),
        "voice_range": metadata.get("voice_range"),
        "device": metadata.get("device"),
        "codec": identity.get("codec"),
        "audio_quality": artifact["quality"].get("overall_status"),
        "speech_difference": metadata.get("speech_difference"),
        "metadata_source": metadata.get("source"),
        "consent_for_fairness_audit": metadata.get(
            "consent_for_fairness_audit", False
        ),
        "unavailable_measurement_rate": unavailable_rate,
    }


def _subgroup_audit(artifacts, study_metadata):
    coverage = [_artifact_coverage(item, study_metadata) for item in artifacts]
    unique_participants = {
        item["participant_id"] for item in coverage if item["participant_id"]
    }
    dimensions = {}
    for dimension in FAIRNESS_DIMENSIONS:
        values = {}
        for item in coverage:
            value = item.get(dimension)
            participant = item.get("participant_id")
            if (value is None or participant is None
                    or not item.get("metadata_source")
                    or item.get("consent_for_fairness_audit") is not True):
                continue
            values.setdefault(str(value), set()).add(participant)
        groups = {name: len(participants)
                  for name, participants in sorted(values.items())}
        dimensions[dimension] = {
            "groups": groups,
            "eligible_independent_participants": len(
                set().union(*values.values()) if values else set()
            ),
            "performance_estimate": "unavailable",
            "uncertainty_interval": None,
            "reason": (
                "No representative independently labelled participant sample "
                "supports a subgroup error estimate."
            ),
        }
    return {
        "status": "not_evaluated",
        "recordings": len(coverage),
        "identified_independent_participants": len(unique_participants),
        "coverage": coverage,
        "dimensions": dimensions,
        "error_measures": {
            "word_error_rate": {
                "status": "unavailable",
                "reason": "No independently corrected transcript is available by subgroup.",
            },
            "speaker_error_rate": {
                "status": "unavailable",
                "reason": "No independent time aligned speaker labels are available by subgroup.",
            },
            "unavailable_measurement_rate": {
                "status": "descriptive_only",
                "by_recording": {
                    item["artifact"]: item["unavailable_measurement_rate"]
                    for item in coverage
                },
                "reason": (
                    "It is counted per recording but cannot be compared fairly "
                    "without independent participants."
                ),
            },
            "key_metric_error": {
                "status": "unavailable",
                "reason": "No independent real speech metric reference is available by subgroup.",
            },
        },
        "claim": (
            "No fairness conclusion is made. Missing or empty subgroup results "
            "must not be interpreted as equal performance."
        ),
    }


def _release_gates(exact_status):
    return {
        "phase_a_exact_repeatability": {
            "status": "pass" if exact_status == "pass" else "block",
            "reason": "Deterministic stages must match exactly on identical frozen input.",
        },
        "individual_progress": {
            "status": "block",
            "reason": "Human repeatability and smallest detectable change are not established.",
        },
        "ranking": {
            "status": "block",
            "reason": "No representative validity and fairness study supports ranking people.",
        },
        "screening": {
            "status": "block",
            "reason": (
                "No independent reference standard and held out evaluation "
                "support screening."
            ),
        },
        "high_stakes_decision": {
            "status": "block",
            "reason": (
                "The current pipeline produces measured observations and "
                "traceable interpretations only, and supports no decision "
                "about a person."
            ),
        },
    }


def render_report(report):
    exact = report["repeatability"]["deterministic_exact"]
    lines = [
        "# Reliability and fairness audit",
        "",
        f"Status: {report['status']}",
        "",
        "## What is proven",
        "",
        f"- Deterministic same input repeatability: {exact['status']}.",
        f"- Exact differences: {len(exact['differences'])}.",
        f"- Deliberate generated changes: {exact['deliberate_change_controls']['status']}.",
        "",
        "## What is not proven",
        "",
        "- Personal day to day stability is not established.",
        "- No metric is approved for personal progress yet.",
        "- Device repeatability is not tested.",
        "- Fairness across language, accent, age, voice range, device, audio "
        "quality, or speech difference is not established.",
        "- No diagnostic accuracy claim is made.",
        "",
        "## Same recording repeats",
        "",
    ]
    repeats = report["repeatability"]["same_recording_repeats"]
    if not repeats:
        lines.append("No complete same version repeat pair was supplied.")
    for item in repeats:
        word = item["word_disagreement"]
        lines.append(
            f"- {item['left']} versus {item['right']}: {item['status']}; "
            f"pairwise word disagreement {word['edit_count']} of "
            f"{word['denominator_words']} words ({word['percentage']} percent)."
        )
    lines.extend(["", "## Encoding checks", ""])
    encodings = report["repeatability"]["encoding_comparisons"]
    if not encodings:
        lines.append("No encoding comparison pair was supplied.")
    for item in encodings:
        word = item["word_disagreement"]
        lines.append(
            f"- {item['left']} versus {item['right']}: "
            f"{item['encodings']}; pairwise word disagreement "
            f"{word['edit_count']} of {word['denominator_words']} words "
            f"({word['percentage']} percent)."
        )
    lines.extend(["", "## Fairness coverage", ""])
    fairness = report["fairness"]
    lines.append(
        f"- Identified independent participants: "
        f"{fairness['identified_independent_participants']}."
    )
    lines.append(f"- Result: {fairness['claim']}")
    lines.extend(["", "## Release gates", ""])
    for name, gate in report["release_gates"].items():
        lines.append(f"- {name}: {gate['status']}. {gate['reason']}")
    return "\n".join(lines).rstrip() + "\n"


def run_audit(*, repeat_artifacts=None, encoding_artifacts=None,
              other_artifacts=None, study_metadata=None, report_dir=None):
    repeat_artifacts = repeat_artifacts or []
    encoding_artifacts = encoding_artifacts or []
    other_artifacts = other_artifacts or []
    study_metadata = study_metadata or {}
    exact = _exact_repeatability()
    repeats = []
    if len(repeat_artifacts) >= 2:
        anchor = repeat_artifacts[0]
        repeats = [compare_repeat_artifacts(anchor, item)
                   for item in repeat_artifacts[1:]]
    encodings = []
    if len(encoding_artifacts) >= 2:
        anchor = encoding_artifacts[0]
        encodings = [compare_encoding_artifacts(anchor, item)
                     for item in encoding_artifacts[1:]]
    unique = {}
    for artifact in repeat_artifacts + encoding_artifacts + other_artifacts:
        unique.setdefault(artifact["directory"], artifact)
    gates = _release_gates(exact["status"])
    report = {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": AUDIT_PROTOCOL_VERSION,
        "measurement_validation_policy_version": VALIDATION_POLICY_VERSION,
        "generated_at_utc": _utc_now(),
        "audit_source": _source_identity(),
        "status": "pass_with_limits" if exact["status"] == "pass" else "fail",
        "repeatability": {
            "deterministic_exact": exact,
            "same_recording_repeats": repeats,
            "encoding_comparisons": encodings,
            "stable_condition_human_repeats": {
                "status": "not_available",
                "independent_participants": 0,
                "natural_day_to_day_variation": "not_estimated",
                "pipeline_measurement_error": "not_separable_from_human_variation",
                "consequence": "all personal progress metrics remain experimental",
            },
        },
        "fairness": _subgroup_audit(list(unique.values()), study_metadata),
        "release_gates": gates,
        "diagnostic_claims": {
            "made": False,
            "reason": (
                "No independent reference standard and held out evaluation "
                "data are available."
            ),
        },
    }
    if report_dir is not None:
        report_dir = Path(report_dir).expanduser().resolve()
        if (report_dir == REPO_ROOT
                or report_dir == REPO_ROOT / "output"
                or REPO_ROOT / "output" in report_dir.parents):
            raise ValueError("audit reports require an isolated directory")
        report_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(report_dir / "reliability_fairness.json", report)
        atomic_write_text(
            report_dir / "reliability_fairness.md", render_report(report)
        )
    return report
