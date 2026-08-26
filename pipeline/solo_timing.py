"""Build compatible single speaker timing and a lightweight voice warning."""

import argparse
import json
from pathlib import Path

try:
    from run_context import add_run_arguments, context_from_args
except ModuleNotFoundError:  # package import used by unit tests
    from .run_context import add_run_arguments, context_from_args

REPO_ROOT = Path(__file__).resolve().parent.parent
SOLO_TIMING_VERSION = "1.0.0"
ACCOUNT_HOLDER = "SPEAKER_00"


def _speaker_evidence(transcript):
    """Summarize provider speaker clusters without inventing a threshold."""
    grouped = {}
    utterances = transcript.get("utterances") or []
    if utterances:
        for utterance in utterances:
            label = utterance.get("speaker")
            if label is None:
                continue
            item = grouped.setdefault(
                str(label), {"utterance_count": 0, "word_count": 0,
                             "speech_s": 0.0}
            )
            item["utterance_count"] += 1
            item["word_count"] += len(utterance.get("words") or [])
            start = utterance.get("start")
            end = utterance.get("end")
            if start is not None and end is not None:
                item["speech_s"] += max(0, end - start) / 1000.0
    else:
        previous = None
        for word in transcript.get("words") or []:
            label = word.get("speaker")
            if label is None:
                continue
            label = str(label)
            item = grouped.setdefault(
                label, {"utterance_count": 0, "word_count": 0,
                        "speech_s": 0.0}
            )
            if label != previous:
                item["utterance_count"] += 1
            item["word_count"] += 1
            start = word.get("start")
            end = word.get("end")
            if start is not None and end is not None:
                item["speech_s"] += max(0, end - start) / 1000.0
            previous = label

    evidence = [
        {
            "provider_speaker": label,
            "utterance_count": item["utterance_count"],
            "word_count": item["word_count"],
            "speech_s": round(item["speech_s"], 2),
        }
        for label, item in grouped.items()
    ]
    return sorted(
        evidence,
        key=lambda item: (-item["speech_s"], -item["word_count"],
                          item["provider_speaker"]),
    )


def _contamination_method(transcript):
    """Name the evidence this check actually had, never the one it wanted.

    The local transcription path produces no speaker labels, so the check has
    nothing to run on. Recording it under the provider's method name would
    describe evidence that was never collected.
    """
    if transcript.get("transcriber") == "local":
        return "no_speaker_clusters_available_v1"
    return "assemblyai_speaker_clusters_v1"


def build_solo_diarization(transcript, vad):
    """Assign all detected speech to SPEAKER_00 and preserve contamination evidence."""
    chunks = vad.get("speech_chunks") or []
    turns = [
        {
            "speaker": ACCOUNT_HOLDER,
            "start_s": round(float(chunk["start"]), 2),
            "end_s": round(float(chunk["end"]), 2),
            "duration_s": round(float(chunk["end"] - chunk["start"]), 2),
        }
        for chunk in chunks
        if chunk.get("start") is not None and chunk.get("end") is not None
        and chunk["end"] > chunk["start"]
    ]
    if not turns:
        words = transcript.get("words") or []
        timed = [word for word in words
                 if word.get("start") is not None and word.get("end") is not None]
        if timed:
            start = min(word["start"] for word in timed) / 1000.0
            end = max(word["end"] for word in timed) / 1000.0
            turns = [{
                "speaker": ACCOUNT_HOLDER,
                "start_s": round(start, 2),
                "end_s": round(end, 2),
                "duration_s": round(end - start, 2),
            }]
    if not turns:
        raise ValueError("solo timing found no speech regions or timed words")

    evidence = _speaker_evidence(transcript)
    method = _contamination_method(transcript)
    if not evidence:
        local = transcript.get("transcriber") == "local"
        contamination = {
            "status": "unavailable",
            "method": method,
            "provider_speaker_count": None,
            "speaker_evidence": [],
            "warning": (
                ("Second voice detection is unavailable on the local "
                 "transcription path, which produces no speaker labels. This "
                 "recording has not been checked for a second voice at all, "
                 "and unavailable is not a clean result.")
                if local else
                ("Second voice detection was unavailable because the "
                 "transcript contained no provider speaker clusters.")
            ),
        }
    elif len(evidence) > 1:
        contamination = {
            "status": "warn",
            "method": method,
            "provider_speaker_count": len(evidence),
            "speaker_evidence": evidence,
            "warning": ("Multiple speaker clusters were detected in a solo "
                        "recording. All speech remains assigned to SPEAKER_00, "
                        "but this recording should not be treated as a clean "
                        "personal baseline."),
        }
    else:
        contamination = {
            "status": "clear",
            "method": method,
            "provider_speaker_count": 1,
            "speaker_evidence": evidence,
            "warning": None,
        }

    talk_time = round(sum(turn["duration_s"] for turn in turns), 2)
    return {
        "num_speakers_mode": "solo_forced",
        "recording_mode": "solo",
        "account_holder_speaker": ACCOUNT_HOLDER,
        "algorithm_version": SOLO_TIMING_VERSION,
        "turns": turns,
        "speakers": {
            ACCOUNT_HOLDER: {
                "talk_time_s": talk_time,
                "turns": len(turns),
            }
        },
        "contamination": contamination,
    }


def main():
    parser = argparse.ArgumentParser()
    add_run_arguments(parser)
    args = parser.parse_args()
    context = context_from_args(args, REPO_ROOT)
    transcript_path = context.output_path("transcript.json", required=True)
    vad_path = context.output_path("vad.json", required=True)
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    vad = json.loads(vad_path.read_text(encoding="utf-8"))
    try:
        result = build_solo_diarization(transcript, vad)
    except ValueError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    context.write_json("diarization.json", result)

    contamination = result["contamination"]
    print(f"Solo timing: {len(result['turns'])} speech regions assigned to "
          f"{ACCOUNT_HOLDER} ({result['speakers'][ACCOUNT_HOLDER]['talk_time_s']}s)")
    if contamination["status"] == "warn":
        print(f"WARNING: {contamination['warning']}")
        for item in contamination["speaker_evidence"]:
            print(f"  provider speaker {item['provider_speaker']}: "
                  f"{item['speech_s']}s across "
                  f"{item['utterance_count']} utterances")
    elif contamination["status"] == "clear":
        print("Contamination check: one provider speaker cluster detected.")
    else:
        print(f"WARNING: {contamination['warning']}")


if __name__ == "__main__":
    main()
