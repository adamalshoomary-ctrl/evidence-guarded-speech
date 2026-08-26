"""Isolated software snapshot and independent truth regression harness."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

from pipeline.audio_quality import analyze_audio
from pipeline.acoustic_primitives import extract_voice_prosody
from pipeline.claim_ledger import (
    claim_ledger,
    scenario_record,
    verify_claim_ledger,
)
from pipeline.run_context import atomic_write_json, atomic_write_text


REPO_ROOT = Path(__file__).resolve().parent.parent
TRUTH_DIR = REPO_ROOT / "regression" / "truth"
SNAPSHOT_DIR = REPO_ROOT / "regression" / "snapshots"
SNAPSHOT_PATH = SNAPSHOT_DIR / "deterministic_contract.json"
SCHEMA_VERSION = "1.1.0"
PROTECTED_THRESHOLDS = (
    "DRAG_RATIO",
    "DRAG_MIN_S",
    "DRAG_PERCENTILE",
    "LOUD_DB_ABOVE",
    "RISE_RATIO",
    "RISE_MIN_HZ",
)
# "corpus_metadata_derived" was added at schema 1.1.0 for the openly licensed
# fixtures. Their speaker identity and count come from the source corpus's own
# metadata carried through a deterministic assembly, not from anybody reviewing
# the audio, and calling that a reviewed annotation would overstate it.
ELIGIBLE_TRUTH_STATUSES = {"adjudicated", "single_annotator_reviewed",
                           "synthetic_ground_truth", "corpus_metadata_derived"}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_thresholds(source_path=None):
    """Read protected renderer constants without importing executable merge.py."""
    source_path = Path(source_path or REPO_ROOT / "pipeline" / "merge.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in PROTECTED_THRESHOLDS:
            values[target.id] = ast.literal_eval(node.value)
    missing = sorted(set(PROTECTED_THRESHOLDS) - set(values))
    if missing:
        raise ValueError("protected renderer thresholds missing: "
                         + ", ".join(missing))
    return values


def _write_wav(path, samples, sample_rate=16000):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.asarray(samples, dtype=np.float64)
    pcm = np.round(np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def _bursts(*, seconds=10.0, amplitude=0.2, noise=0.0, seed=11):
    sample_rate = 16000
    count = int(seconds * sample_rate)
    time = np.arange(count) / sample_rate
    signal = amplitude * np.sin(2 * np.pi * 180 * time)
    envelope = np.zeros(count)
    for start_s in np.arange(0.4, seconds, 2.0):
        start = int(start_s * sample_rate)
        end = min(count, start + int(1.2 * sample_rate))
        envelope[start:end] = 1.0
    signal *= envelope
    if noise:
        signal += np.random.default_rng(seed).normal(0.0, noise, count)
    return signal


def _clean_audio_quality():
    return {
        "schema_version": "1.0.0",
        "decision": "continue",
        "overall_status": "pass",
        "checks": [],
        "limitations": [],
    }


def _word(text, start_s, end_s):
    return {
        "text": text,
        "start": round(start_s * 1000),
        "end": round(end_s * 1000),
        "confidence": 0.99,
    }


def _timeline(duration_s):
    result = []
    t = 0.0
    while t <= duration_s:
        result.append({
            "t": round(t, 2),
            "loudness_db": 0.0 if math.isclose(t, 5.0) else -20.0,
            "pitch_hz": 100.0,
        })
        t += 0.5
    return result


def _pitch_track(duration_s):
    result = []
    t = 0.0
    while t <= duration_s:
        pitch = 100.0
        if 6.24 <= t <= 6.4:
            pitch = 140.0
        result.append([round(t, 2), pitch])
        t += 0.05
    return result


def _merge_inputs(output_dir):
    """Create a designed conversation with known overlap and renderer events."""
    words = [
        _word("alpha", 0.0, 0.3),
        _word("speaks", 0.4, 0.7),
        _word("yeah", 0.8, 1.1),
        _word("continues", 1.2, 1.5),
        _word("slowword", 3.0, 4.5),
        _word("loud", 5.0, 5.3),
        _word("really.", 6.0, 6.4),
        _word("overlapword.", 7.0, 7.4),
    ]
    diarization = {
        "turns": [
            {"speaker": "SPEAKER_00", "start_s": 0.0, "end_s": 0.75,
             "duration_s": 0.75},
            {"speaker": "SPEAKER_01", "start_s": 0.75, "end_s": 1.15,
             "duration_s": 0.4},
            {"speaker": "SPEAKER_00", "start_s": 1.15, "end_s": 7.3,
             "duration_s": 6.15},
            {"speaker": "SPEAKER_01", "start_s": 7.0, "end_s": 7.5,
             "duration_s": 0.5},
        ],
        "account_holder_speaker": "SPEAKER_00",
        "contamination": None,
    }
    vad = {
        "audio_duration_s": 8.0,
        "speaking_time_s": 6.5,
        "silence_time_s": 1.5,
        "speech_chunks": [
            {"start": 0.0, "end": 1.5},
            {"start": 3.0, "end": 8.0},
        ],
        "pauses": [{"starts_at": 1.5, "ends_at": 3.0, "duration": 1.5}],
    }
    acoustics = {
        "overall": {"duration_s": 8.0},
        "per_speaker": {},
        "timeline": _timeline(8.0),
        "pitch_track": _pitch_track(8.0),
    }
    fixtures = {
        "diarization.json": diarization,
        "transcript.json": {"words": words},
        "alignment.json": {"segments": []},
        "vad.json": vad,
        "acoustics.json": acoustics,
        "audio_quality.json": _clean_audio_quality(),
    }
    for name, value in fixtures.items():
        atomic_write_json(output_dir / name, value)


def _run_merge(output_dir):
    _merge_inputs(output_dir)
    result = subprocess.run(
        [sys.executable, "pipeline/merge.py", "--output-dir", str(output_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return (
        json.loads((output_dir / "master.json").read_text(encoding="utf-8")),
        json.loads(
            (output_dir / "words_attributed.json").read_text(encoding="utf-8")
        ),
    )


def _rate_case(output_dir, *, spacing_s):
    words = [
        _word(f"word{index}", index * spacing_s,
              index * spacing_s + min(0.2, spacing_s * 0.8))
        for index in range(30)
    ]
    end_s = words[-1]["end"] / 1000.0
    fixtures = {
        "diarization.json": {
            "turns": [{"speaker": "SPEAKER_00", "start_s": 0.0,
                       "end_s": end_s, "duration_s": end_s}],
            "account_holder_speaker": "SPEAKER_00",
            "contamination": {"status": "clear", "warning": None},
        },
        "transcript.json": {"words": words},
        "alignment.json": {"segments": []},
        "vad.json": {
            "audio_duration_s": end_s,
            "speaking_time_s": end_s,
            "silence_time_s": 0.0,
            "speech_chunks": [{"start": 0.0, "end": end_s}],
            "pauses": [],
        },
        "acoustics.json": {
            "overall": {"duration_s": end_s},
            "per_speaker": {},
            "timeline": [],
            "pitch_track": [],
        },
        "audio_quality.json": _clean_audio_quality(),
    }
    for name, value in fixtures.items():
        atomic_write_json(output_dir / name, value)
    result = subprocess.run(
        [sys.executable, "pipeline/merge.py", "--output-dir", str(output_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    master = json.loads((output_dir / "master.json").read_text(encoding="utf-8"))
    return master["computed_metrics"]["SPEAKER_00"]["wpm"]


def _monotone_case(output_dir):
    sample_rate = 16000
    seconds = 8.0
    time = np.arange(int(sample_rate * seconds)) / sample_rate
    audio = output_dir / "monotone.wav"
    _write_wav(audio, 0.2 * np.sin(2 * np.pi * 180 * time), sample_rate)
    atomic_write_json(output_dir / "diarization.json", {
        "turns": [{"speaker": "SPEAKER_00", "start_s": 0.0,
                   "end_s": seconds, "duration_s": seconds}],
    })
    result = subprocess.run(
        [sys.executable, "pipeline/acoustics.py", "--audio", str(audio),
         "--output-dir", str(output_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    acoustics = json.loads(
        (output_dir / "acoustics.json").read_text(encoding="utf-8")
    )
    return acoustics["overall"]


def _primitive_context():
    return {
        "status": "context_missing",
        "task_id": None,
        "task_version": None,
        "prompt_id": None,
        "prompt_version": None,
        "language": None,
        "preparation": None,
        "accommodations": [],
        "task_profile": "unknown_ad_hoc",
        "task_comparability": "not_comparable",
        "supported_primitives": [
            "f0_median_hz", "f0_percentiles_hz",
            "f0_distribution_span_st", "recorder_level_percentiles_dbfs",
            "recorder_level_span_db",
        ],
        "requires_research_consent": False,
        "research_consent_granted": False,
        "device": {
            "device_class": "synthetic",
            "platform": "generated_fixture",
            "microphone": "not_applicable",
            "source": "synthetic_truth",
        },
        "quality_policy": "lenient",
        "capture_processing": {
            "automatic_gain_control": "off",
            "noise_suppression": "off",
            "echo_cancellation": "off",
        },
    }


def _voice_prosody_case():
    sample_rate = 48000
    seconds = 5.0
    time = np.arange(int(sample_rate * seconds)) / sample_rate
    steady = 0.2 * np.sin(2 * np.pi * 180.0 * time)
    gain = np.where(time < seconds / 2.0, 0.25, 1.0)
    samples = steady * gain
    diarization = {"turns": [{
        "speaker": "SPEAKER_00", "start_s": 0.0,
        "end_s": seconds, "duration_s": seconds,
    }]}
    artifact = extract_voice_prosody(
        samples, sample_rate, diarization,
        {"speech_chunks": [{"start": 0.0, "end": seconds}]},
        _primitive_context(), _clean_audio_quality(), "solo",
        {"codec": "synthetic_float", "sample_rate_hz": sample_rate,
         "channels": 1},
    )
    summary = artifact["speakers"]["SPEAKER_00"]
    return {
        "f0_median_hz": summary["values"]["f0_median_hz"],
        "f0_distribution_span_st": summary["values"][
            "f0_distribution_span_st"
        ],
        "recorder_level_span_db": summary["values"][
            "recorder_level_span_db"
        ],
        "frame_step_s": artifact["configuration"]["frame_step_s"],
        "combined_index_present": "combined_index" in summary["values"],
    }


def _effect_events(master):
    field_types = {
        "filler_s": "filler",
        "held_s": "drag",
        "loud_db_above_avg": "loud",
        "rising_pitch_hz": "uptalk",
    }
    result = []
    for turn in master.get("turns", []):
        for effect in turn.get("word_effects", []):
            for field, effect_type in field_types.items():
                if field in effect:
                    result.append({
                        "type": effect_type,
                        "word": effect.get("word"),
                        "speaker": effect.get("speaker"),
                        "timestamp_s": effect.get("t"),
                    })
    return result


def _verification_cases():
    master = {
        "meta": {"enrichment_status": {"listener": {"status": "complete"}}},
        "computed_metrics": {"SPEAKER_00": {"wpm": 120.0}},
        "measurement_metadata": {"speakers": {"SPEAKER_00": {
            "computed_metrics": {"wpm": {
                "value_path": "computed_metrics.SPEAKER_00.wpm",
                "availability": {"status": "available"},
                "quality": {"category": "high"},
            }},
            "voice_quality": {},
        }}, "overall_voice_quality": {}},
        "turns": [],
        "notable_moments": [],
        "listener_contradictions": [],
        "speaker_overall_impressions": {},
    }
    scenario = scenario_record("Synthetic test", declared=True)

    def run(speaker):
        text = "Speaking rate was 120 wpm."
        package = {
            "report_markdown": f"{text} [C001]",
            "claims": [{
                "claim_id": "C001",
                "claim_type": "measured_observation",
                "text": text,
                "speaker": speaker,
                "references": [{
                    "source": "metric",
                    "path": "computed_metrics.SPEAKER_00.wpm",
                    "speaker": speaker,
                    "turn_id": None,
                    "timestamp_s": None,
                    "claimed_value": 120.0,
                    "direction": "none",
                }],
            }],
        }
        ledger = claim_ledger(package, scenario)
        return verify_claim_ledger(master, ledger, package["report_markdown"])

    return {
        "valid_claim": run("SPEAKER_00")["status"],
        "wrong_speaker_claim": run("SPEAKER_01")["status"],
    }


def generate_synthetic_actual(work_dir):
    """Run independent designed controls in an isolated directory."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    merge_master, attributed = _run_merge(work_dir / "merge")
    fast_wpm = _rate_case(work_dir / "fast", spacing_s=0.25)
    slow_wpm = _rate_case(work_dir / "slow", spacing_s=1.0)
    monotone = _monotone_case(work_dir / "monotone")

    quality = {}
    quality_specs = {
        "clean": _bursts(),
        "noisy": _bursts(amplitude=0.03, noise=0.08),
        "loud": _bursts(amplitude=0.7),
        "quiet": _bursts(amplitude=0.005),
    }
    for name, samples in quality_specs.items():
        case_dir = work_dir / "quality"
        case_dir.mkdir(parents=True, exist_ok=True)
        audio = case_dir / f"{name}.wav"
        _write_wav(audio, samples)
        report = analyze_audio(audio, "lenient")
        quality[name] = {
            "decision": report["decision"],
            "overall_status": report["overall_status"],
            "checks": {item["id"]: item["status"] for item in report["checks"]},
        }

    return {
        "speaker_attribution": [
            {"index": item["i"], "word": item["text"],
             "speaker": item["speaker"], "start_s": item["start_s"],
             "end_s": item["end_s"], "confidence": item["confidence"]}
            for item in attributed
        ],
        "turns": [{
            "turn_id": turn["turn_id"],
            "speaker": turn["speaker"],
            "start_s": turn["start_s"],
            "end_s": turn["end_s"],
            "pause_before_s": turn.get("pause_before_s"),
            "expressive_text": turn["expressive_text"],
        } for turn in merge_master["turns"]],
        "renderer_events": _effect_events(merge_master),
        "metrics": {
            "fast_wpm": fast_wpm,
            "slow_wpm": slow_wpm,
            "conversation": merge_master["computed_metrics"],
        },
        "quality": quality,
        "monotone": {
            "pitch_median_hz": monotone.get("pitch_median_hz"),
            "pitch_variation_hz": monotone.get("pitch_variation_hz"),
        },
        "voice_prosody": _voice_prosody_case(),
        "verification": _verification_cases(),
    }


def snapshot_actual(synthetic_actual, source_path=None):
    """Select stable deterministic outputs, excluding runtime provenance."""
    return {
        "schema_version": SCHEMA_VERSION,
        "protected_renderer_thresholds": protected_thresholds(source_path),
        "synthetic_contract": synthetic_actual,
    }


def structural_diff(expected, actual, path=""):
    """Return precise stable JSON path differences."""
    here = path or "$"
    if isinstance(expected, dict) and isinstance(actual, dict):
        result = []
        for key in sorted(set(expected) | set(actual)):
            child = f"{here}.{key}"
            if key not in expected:
                result.append(f"{child}: unexpected {actual[key]!r}")
            elif key not in actual:
                result.append(f"{child}: missing, expected {expected[key]!r}")
            else:
                result.extend(structural_diff(expected[key], actual[key], child))
        return result
    if isinstance(expected, list) and isinstance(actual, list):
        result = []
        if len(expected) != len(actual):
            result.append(f"{here}: expected {len(expected)} items, actual {len(actual)}")
        for index, (left, right) in enumerate(zip(expected, actual)):
            result.extend(structural_diff(left, right, f"{here}[{index}]"))
        return result
    return [] if expected == actual else [
        f"{here}: expected {expected!r}, actual {actual!r}"
    ]


def compare_snapshot(actual, snapshot_path=SNAPSHOT_PATH):
    snapshot_path = Path(snapshot_path)
    if not snapshot_path.is_file():
        return {"status": "fail", "differences": [
            f"snapshot missing: {snapshot_path}"
        ]}
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    differences = structural_diff(expected, actual)
    return {"status": "pass" if not differences else "fail",
            "differences": differences}


def bless_snapshot(actual, snapshot_path=SNAPSHOT_PATH, allowed_root=SNAPSHOT_DIR):
    """Replace only a software snapshot, never any truth file."""
    snapshot_path = Path(snapshot_path).resolve()
    allowed_root = Path(allowed_root).resolve()
    if snapshot_path.parent != allowed_root:
        raise ValueError("--bless may write only inside the snapshot directory")
    if TRUTH_DIR.resolve() in snapshot_path.parents:
        raise ValueError("--bless cannot write truth labels")
    atomic_write_json(snapshot_path, actual)


def load_truth(path):
    path = Path(path)
    truth = json.loads(path.read_text(encoding="utf-8"))
    required = {"schema_version", "fixture_id", "fixture_kind", "reference",
                "coverage", "expectations"}
    missing = sorted(required - set(truth))
    if missing:
        raise ValueError(f"{path.name} missing: {', '.join(missing)}")
    if truth["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"{path.name} has an unsupported schema version")
    if truth["fixture_kind"] not in {"human_recording", "synthetic_control",
                                     "assembled_human_recording"}:
        raise ValueError(f"{path.name} has an unsupported fixture kind")
    reference = truth["reference"]
    for field in ("source", "annotator_role", "guide_version", "date",
                  "adjudication_status", "independent_from_pipeline"):
        if reference.get(field) in (None, ""):
            raise ValueError(f"{path.name} reference missing {field}")
    if not reference["independent_from_pipeline"]:
        raise ValueError(f"{path.name} is not independent from the pipeline")
    return truth


def _metric(numerator, denominator, reference_source):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "percentage": (round(100 * numerator / denominator, 1)
                       if denominator else None),
        "reference_source": reference_source,
    }


def _find_word(actual, expected):
    candidates = [item for item in actual["speaker_attribution"]
                  if item["word"] == expected["word"]]
    if "index" in expected:
        candidates = [item for item in candidates
                      if item["index"] == expected["index"]]
    return candidates[0] if len(candidates) == 1 else None


def compare_synthetic_truth(actual, truth):
    """Compare designed controls with metric specific tolerances."""
    if truth["reference"]["adjudication_status"] != "synthetic_ground_truth":
        return {
            "fixture_id": truth["fixture_id"],
            "status": "incomplete",
            "metrics": {},
            "failures": ["synthetic truth is not independently established"],
        }
    source = truth["reference"]["source"]
    expected = truth["expectations"]
    failures = []
    results = {}

    words = expected.get("words", [])
    correct_speaker = 0
    correct_timing = 0
    for item in words:
        found = _find_word(actual, item)
        if found and found["speaker"] == item["speaker"]:
            correct_speaker += 1
        else:
            failures.append(f"speaker attribution failed for {item['word']}")
        tolerance = item.get("timing_tolerance_s", 0.02)
        if (found and abs(found["start_s"] - item["start_s"]) <= tolerance
                and abs(found["end_s"] - item["end_s"]) <= tolerance):
            correct_timing += 1
        else:
            failures.append(f"word timing or identity failed for {item['word']}")
    results["speaker_attribution_accuracy"] = _metric(
        correct_speaker, len(words), source
    )
    results["word_timing_within_tolerance"] = _metric(
        correct_timing, len(words), source
    )

    expected_events = {
        (item["type"], item["word"], item["speaker"])
        for item in expected.get("renderer_events", [])
    }
    actual_events = {
        (item["type"], item["word"], item["speaker"])
        for item in actual["renderer_events"]
    }
    tp = len(expected_events & actual_events)
    fp = len(actual_events - expected_events)
    fn = len(expected_events - actual_events)
    results["renderer_event_precision"] = _metric(tp, tp + fp, source)
    results["renderer_event_recall"] = _metric(tp, tp + fn, source)
    results["renderer_false_positives"] = {
        "count": fp,
        "denominator": len(actual_events),
        "reference_source": source,
    }
    results["renderer_false_negatives"] = {
        "count": fn,
        "denominator": len(expected_events),
        "reference_source": source,
    }
    if fp or fn:
        failures.append(
            f"renderer events differ, false positives {fp}, false negatives {fn}"
        )

    metric_passes = 0
    metric_checks = expected.get("metrics", [])
    for item in metric_checks:
        value = _resolve_json_path(actual, item["path"])
        if abs(float(value) - float(item["value"])) <= item["tolerance"]:
            metric_passes += 1
        else:
            failures.append(
                f"metric {item['path']} expected {item['value']} ± "
                f"{item['tolerance']}, actual {value}"
            )
    results["metric_values_within_tolerance"] = _metric(
        metric_passes, len(metric_checks), source
    )

    condition_passes = 0
    condition_checks = expected.get("conditions", [])
    for item in condition_checks:
        value = _resolve_json_path(actual, item["path"])
        operator = item["operator"]
        target = item["value"]
        passed = ((operator == "equals" and value == target)
                  or (operator == "less_than" and value < target)
                  or (operator == "greater_than" and value > target)
                  or (operator == "contains" and target in value))
        if passed:
            condition_passes += 1
        else:
            failures.append(
                f"condition {item['path']} {operator} {target}, actual {value}"
            )
    results["condition_checks_passed"] = _metric(
        condition_passes, len(condition_checks), source
    )
    return {
        "fixture_id": truth["fixture_id"],
        "status": "pass" if not failures else "fail",
        "metrics": results,
        "failures": failures,
    }


def _resolve_json_path(value, path):
    for token in path.split("."):
        if isinstance(value, list):
            value = value[int(token)]
        else:
            value = value[token]
    return value


def compare_recording_truth(artifact_dir, truth):
    """Compare an isolated real run to independently supplied labels."""
    artifact_dir = Path(artifact_dir)
    reference = truth["reference"]
    if reference["adjudication_status"] not in ELIGIBLE_TRUTH_STATUSES:
        return {
            "fixture_id": truth["fixture_id"],
            "status": "incomplete",
            "metrics": {},
            "failures": ["truth labels are not reviewed or adjudicated"],
        }
    audio = truth.get("audio") or {}
    audio_path = REPO_ROOT / audio.get("path", "")
    if not audio_path.is_file() or sha256_file(audio_path) != audio.get("sha256"):
        return {
            "fixture_id": truth["fixture_id"],
            "status": "fail",
            "metrics": {},
            "failures": ["truth labels do not match the exact audio bytes"],
        }
    loaded = {}
    failures = []
    passed = 0
    checks = truth["expectations"].get("artifact_checks", [])
    for check in checks:
        name = check["artifact"]
        if name not in loaded:
            path = artifact_dir / name
            if not path.is_file():
                failures.append(f"missing artifact {name}")
                continue
            loaded[name] = json.loads(path.read_text(encoding="utf-8"))
        try:
            actual = _resolve_json_path(loaded[name], check["path"])
        except (KeyError, IndexError, ValueError, TypeError):
            failures.append(f"missing path {name}:{check['path']}")
            continue
        tolerance = check.get("tolerance")
        if tolerance is None:
            ok = actual == check["value"]
        else:
            ok = (isinstance(actual, (int, float))
                  and abs(actual - check["value"]) <= tolerance)
        if ok:
            passed += 1
        else:
            failures.append(
                f"{name}:{check['path']} expected {check['value']!r}, "
                f"actual {actual!r}"
            )
    source = reference["source"]
    return {
        "fixture_id": truth["fixture_id"],
        "status": "pass" if not failures else "fail",
        "metrics": {"artifact_checks_passed": _metric(passed, len(checks), source)},
        "failures": failures,
    }


def render_report(report):
    lines = ["# Regression report", "", f"Status: {report['status']}"]
    snapshot = report["software_snapshot"]
    lines.extend(["", "## Software snapshot", "",
                  f"Status: {snapshot['status']}"])
    for difference in snapshot.get("differences", []):
        lines.append(f"- {difference}")
    lines.extend(["", "## Independent truth", ""])
    for fixture in report["truth_results"]:
        lines.append(f"### {fixture['fixture_id']}")
        lines.append("")
        lines.append(f"Status: {fixture['status']}")
        for name, metric in fixture.get("metrics", {}).items():
            if "percentage" in metric:
                lines.append(
                    f"- {name}: {metric['numerator']} of {metric['denominator']} "
                    f"({metric['percentage']} percent), reference: "
                    f"{metric['reference_source']}"
                )
            else:
                lines.append(
                    f"- {name}: {metric['count']} of {metric['denominator']}, "
                    f"reference: {metric['reference_source']}"
                )
        for failure in fixture.get("failures", []):
            lines.append(f"- FAIL: {failure}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_harness(*, bless=False, artifacts=None, snapshot_path=SNAPSHOT_PATH,
                truth_dir=TRUTH_DIR, report_dir=None, synthetic_only=False):
    """Run all available layers without touching production outputs."""
    artifacts = artifacts or {}
    with tempfile.TemporaryDirectory(prefix="speech_regression_") as temp_dir:
        synthetic = generate_synthetic_actual(Path(temp_dir))
    actual_snapshot = snapshot_actual(synthetic)
    if bless:
        bless_snapshot(actual_snapshot, snapshot_path, Path(snapshot_path).parent)
    snapshot_result = compare_snapshot(actual_snapshot, snapshot_path)

    truth_results = []
    for path in sorted(Path(truth_dir).glob("*.json")):
        truth = load_truth(path)
        if truth["fixture_kind"] == "synthetic_control":
            truth_results.append(compare_synthetic_truth(synthetic, truth))
        elif truth["fixture_id"] in artifacts:
            truth_results.append(
                compare_recording_truth(artifacts[truth["fixture_id"]], truth)
            )
        elif not synthetic_only:
            truth_results.append({
                "fixture_id": truth["fixture_id"],
                "status": "incomplete",
                "metrics": {},
                "failures": ["no isolated pipeline artifacts were supplied"],
            })

    statuses = [snapshot_result["status"]]
    statuses.extend(item["status"] for item in truth_results)
    status = ("pass" if statuses and all(item == "pass" for item in statuses)
              else "incomplete" if "incomplete" in statuses
              and "fail" not in statuses else "fail")
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "software_snapshot": snapshot_result,
        "truth_results": truth_results,
    }
    if report_dir is not None:
        report_dir = Path(report_dir).resolve()
        forbidden = {REPO_ROOT / "output", REPO_ROOT}
        if report_dir in forbidden:
            raise ValueError("regression reports require an isolated directory")
        report_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(report_dir / "regression_report.json", report)
        atomic_write_text(report_dir / "regression_report.md", render_report(report))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bless", action="store_true",
                        help="replace only the software snapshot")
    parser.add_argument("--artifact", action="append", default=[],
                        metavar="FIXTURE_ID=OUTPUT_DIR")
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--synthetic-only", action="store_true")
    args = parser.parse_args()
    artifacts = {}
    for value in args.artifact:
        if "=" not in value:
            parser.error("--artifact must be FIXTURE_ID=OUTPUT_DIR")
        fixture_id, directory = value.split("=", 1)
        artifacts[fixture_id] = Path(directory).expanduser().resolve()
    report = run_harness(
        bless=args.bless,
        artifacts=artifacts,
        report_dir=args.report_dir,
        synthetic_only=args.synthetic_only,
    )
    print(render_report(report))
    raise SystemExit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
