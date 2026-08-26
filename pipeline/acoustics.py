"""Extract legacy renderer tracks and Phase C voice/prosody primitives.

The top-level legacy fields remain compatible with the existing renderer.
`voice_prosody` is the new task-aware, timestamped measurement path.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import librosa
import numpy as np
import parselmouth
from parselmouth.praat import call

from acoustic_primitives import (
    ALGORITHM_VERSION,
    ANALYSIS_SAMPLE_RATE_HZ,
    analysis_context,
    extract_voice_prosody,
)
from run_context import add_run_arguments, context_from_args


REPO_ROOT = Path(__file__).resolve().parent.parent
ACOUSTICS_SCHEMA_VERSION = "2.0.0"
LEGACY_ALGORITHM_VERSION = "legacy-renderer-acoustics-v3"


def _load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _decode_audio(audio_file, destination):
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(audio_file),
            "-ac", "1", "-ar", str(ANALYSIS_SAMPLE_RATE_HZ),
            "-c:a", "pcm_f32le", str(destination),
        ],
        check=True, capture_output=True,
    )


def _legacy_voice_quality(sound):
    """Preserve the old field shape; evidence metadata governs its use."""
    try:
        pitch = sound.to_pitch(time_step=0.05)
        point = call(sound, "To PointProcess (periodic, cc)", 75, 500)
        jitter = call(point, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer = call(
            [sound, point], "Get shimmer (local)",
            0, 0, 0.0001, 0.02, 1.3, 1.6,
        )
        values = pitch.selected_array["frequency"]
        voiced = values[values > 0]
        return {
            "pitch_median_hz": round(float(np.median(voiced)), 1)
            if len(voiced) else None,
            "pitch_variation_hz": round(float(np.std(voiced)), 1)
            if len(voiced) else None,
            "jitter": round(float(jitter), 4) if jitter == jitter else None,
            "shimmer": round(float(shimmer), 4) if shimmer == shimmer else None,
        }
    except Exception:  # Praat can reject tiny, quiet or aperiodic clips
        return None


def _legacy_fields(sound, samples, sample_rate, diarization):
    """Reproduce the protected renderer inputs without changing thresholds."""
    duration = sound.get_total_duration()
    overall = _legacy_voice_quality(sound) or {}
    overall["duration_s"] = round(duration, 2)
    overall["note"] = (
        "Legacy compatibility values. Use voice_prosody and its measurement "
        "metadata for Phase C evidence. Whole-recording conversation values "
        "blend speakers and are unavailable for person-level claims."
    )

    per_speaker = {}
    by_speaker = {}
    for turn in diarization.get("turns", []):
        if turn.get("duration_s", 0) >= 0.5:
            by_speaker.setdefault(turn.get("speaker"), []).append(
                (float(turn["start_s"]), float(turn["end_s"]))
            )
    for speaker, segments in by_speaker.items():
        if speaker is None:
            continue
        pieces = [
            samples[int(start * sample_rate):int(end * sample_rate)]
            for start, end in segments
        ]
        pieces = [piece for piece in pieces if len(piece)]
        if not pieces:
            continue
        joined = np.concatenate(pieces)
        if len(joined) < sample_rate:
            continue
        speaker_sound = parselmouth.Sound(
            joined.astype(np.float64), sampling_frequency=sample_rate
        )
        values = _legacy_voice_quality(speaker_sound)
        if values:
            values["speech_analysed_s"] = round(len(joined) / sample_rate, 1)
            values["legacy_concatenated_regions"] = True
            per_speaker[speaker] = values

    pitch_object = sound.to_pitch(time_step=0.05)
    hop = 0.5
    rms = librosa.feature.rms(
        y=samples,
        frame_length=int(sample_rate * hop),
        hop_length=int(sample_rate * hop),
    )[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    timeline = []
    for index, recorder_level in enumerate(rms_db):
        time_s = round(index * hop, 2)
        pitch = pitch_object.get_value_at_time(time_s)
        timeline.append({
            "t": time_s,
            "loudness_db": round(float(recorder_level), 1),
            "pitch_hz": round(float(pitch), 1) if pitch == pitch else None,
        })
    pitch_track = []
    time_s = 0.0
    while time_s < duration:
        pitch = pitch_object.get_value_at_time(time_s)
        pitch_track.append([
            round(time_s, 2),
            round(float(pitch), 1) if pitch == pitch else 0,
        ])
        time_s += 0.05
    return overall, per_speaker, timeline, pitch_track


def extract_acoustics(audio_file, diarization, vad, audio_quality,
                      session_context_path=None, recording_mode=None):
    """Return one complete artifact from already resolved pipeline inputs."""
    with tempfile.TemporaryDirectory(prefix="speech_acoustics_") as temp_dir:
        wav_path = Path(temp_dir) / "analysis.wav"
        _decode_audio(audio_file, wav_path)
        sound = parselmouth.Sound(str(wav_path))
        samples, sample_rate = librosa.load(wav_path, sr=None, mono=True)
        speakers = {
            turn.get("speaker") for turn in diarization.get("turns", [])
            if turn.get("speaker") is not None
        }
        inferred_type = "solo" if len(speakers) <= 1 else "conversation"
        recording_type = recording_mode or inferred_type
        declared_context = analysis_context(
            session_context_path, recording_type, REPO_ROOT
        )
        input_audio = dict((audio_quality or {}).get("audio") or {})
        input_audio.setdefault("filename", Path(audio_file).name)
        input_audio.setdefault("path", str(Path(audio_file).resolve()))
        input_audio.setdefault("sample_rate_hz", sample_rate)
        input_audio.setdefault("channels", 1)
        primitives = extract_voice_prosody(
            samples, sample_rate, diarization, vad, declared_context,
            audio_quality, recording_type, input_audio,
        )
        overall, per_speaker, timeline, pitch_track = _legacy_fields(
            sound, samples, sample_rate, diarization
        )
    return {
        "schema_version": ACOUSTICS_SCHEMA_VERSION,
        "algorithm_version": ALGORITHM_VERSION,
        "legacy_algorithm_version": LEGACY_ALGORITHM_VERSION,
        "overall": overall,
        "per_speaker": per_speaker,
        "timeline": timeline,
        "pitch_track": pitch_track,
        "voice_prosody": primitives,
    }


def main():
    parser = argparse.ArgumentParser()
    add_run_arguments(parser)
    args = parser.parse_args()
    context = context_from_args(args, REPO_ROOT, require_audio=True)
    audio_file = context.audio_path
    print(f"Measuring voice and prosody in: {audio_file.name}")

    diarization_path = context.output_path(
        "diarization.json", required=context.run_id is not None
    )
    diarization = _load_json(diarization_path, {"turns": []})
    vad = _load_json(context.output_path("vad.json"), {"speech_chunks": []})
    audio_quality = _load_json(context.output_path("audio_quality.json"), {})
    result = extract_acoustics(
        audio_file, diarization, vad, audio_quality,
        session_context_path=context.session_context_path,
        recording_mode=context.recording_mode,
    )
    output_path = context.output_path("acoustics.json")
    context.write_json("acoustics.json", result, indent=None)
    speakers = list(result["voice_prosody"]["speakers"])
    print(f"Phase C per-speaker summaries: {speakers}")
    print(f"Done. Saved to: {output_path}")


if __name__ == "__main__":
    main()
