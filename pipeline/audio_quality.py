"""Deterministic audio preflight used before expensive pipeline extraction."""

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np

try:
    from run_context import add_run_arguments, context_from_args
except ModuleNotFoundError:  # package imports used by unit tests
    from .run_context import add_run_arguments, context_from_args


REPO_ROOT = Path(__file__).resolve().parent.parent
QUALITY_SCHEMA_VERSION = "1.0.0"
THRESHOLD_VERSION = "generated-fixtures-1.0.0"
ANALYSIS_SAMPLE_RATE_HZ = 16000
MAX_ANALYSIS_DURATION_S = 300.0

THRESHOLDS = {
    "minimum_duration_s": 5.0,
    "long_duration_s": 1800.0,
    "minimum_sample_rate_hz": 16000,
    "clipping_ratio": 0.001,
    "hot_peak_dbfs": -0.5,
    "quiet_peak_dbfs": -45.0,
    "near_silent_rms_dbfs": -60.0,
    "low_rms_dbfs": -35.0,
    "near_silent_frame_ratio": 0.98,
    "minimum_speech_proportion": 0.10,
    "minimum_snr_proxy_db": 12.0,
    "unstable_level_spread_db": 12.0,
    "reverberation_tail_ratio": 0.60,
}


class AudioQualityError(Exception):
    """The input could not be inspected or decoded safely."""


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dbfs(value):
    return 20.0 * math.log10(max(float(value), 1e-12))


def _round(value, digits=3):
    if value is None:
        return None
    return round(float(value), digits)


def _check(check_id, status, value, unit, threshold, reason, affects=(),
           availability="available"):
    return {
        "id": check_id,
        "status": status,
        "value": value,
        "unit": unit,
        "threshold": threshold,
        "threshold_version": THRESHOLD_VERSION,
        "availability": availability,
        "reason": reason,
        "affects": list(affects),
    }


def _problem_status(problem, policy, *, hard=False, warning_only=False):
    if not problem:
        return "pass"
    if hard:
        return "fail"
    if warning_only:
        return "warn"
    return "warn" if policy == "lenient" else "fail"


def require_program(name):
    """Fail with the missing program named, rather than blaming the recording.

    ffmpeg and ffprobe are hard requirements of every run and they are separate
    installs that nothing in requirements.txt can supply. When one is absent the
    subprocess call raises the same OSError as an unreadable file, so the
    message a newcomer used to get was "ffprobe could not read the audio file"
    about a recording that was perfectly fine. They concluded the shipped
    example was corrupt. Found 2026-08-28.
    """
    if shutil.which(name) is None:
        raise AudioQualityError(
            f"{name} is not installed, so this recording cannot be read. It is "
            "part of ffmpeg, which this pipeline needs and pip cannot install. "
            "Install it with 'brew install ffmpeg' on macOS, "
            "'sudo apt install ffmpeg' on Debian or Ubuntu, or from "
            "https://ffmpeg.org/download.html on Windows. The recording itself "
            "is probably fine."
        )


def probe_audio(audio_path):
    """Return stable input metadata for quality and provenance."""
    audio_path = Path(audio_path).resolve()
    require_program("ffprobe")
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration,format_name:stream=codec_type,codec_name,"
                "sample_rate,channels,channel_layout,duration,bit_rate,"
                "bits_per_sample,bits_per_raw_sample",
                "-of", "json", str(audio_path),
            ],
            check=True, capture_output=True, text=True,
        )
        probe = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise AudioQualityError("ffprobe could not read the audio file") from exc

    stream = next(
        (item for item in probe.get("streams", [])
         if item.get("codec_type") == "audio"),
        None,
    )
    if stream is None:
        raise AudioQualityError("the file contains no readable audio stream")
    duration = probe.get("format", {}).get("duration") or stream.get("duration")
    if duration is None:
        raise AudioQualityError("the audio duration is unavailable")

    return {
        "filename": audio_path.name,
        "path": str(audio_path),
        "byte_sha256": _sha256_file(audio_path),
        "byte_size": audio_path.stat().st_size,
        "duration_s": round(float(duration), 3),
        "container_format": probe.get("format", {}).get("format_name"),
        "codec": stream.get("codec_name"),
        "sample_rate_hz": (int(stream["sample_rate"])
                           if stream.get("sample_rate") else None),
        "channels": stream.get("channels"),
        "channel_layout": stream.get("channel_layout"),
        "bit_rate": int(stream["bit_rate"]) if stream.get("bit_rate") else None,
        "bits_per_sample": int(stream["bits_per_sample"])
        if stream.get("bits_per_sample") else None,
        "bits_per_raw_sample": int(stream["bits_per_raw_sample"])
        if stream.get("bits_per_raw_sample") else None,
    }


def _decode_audio(audio_path, channels, duration_s):
    require_program("ffmpeg")
    decode_channels = channels if channels in (1, 2) else 1
    analysis_duration = min(duration_s, MAX_ANALYSIS_DURATION_S)
    command = [
        "ffmpeg", "-v", "error", "-i", str(audio_path),
        "-map", "0:a:0", "-t", f"{analysis_duration:.3f}",
        "-ar", str(ANALYSIS_SAMPLE_RATE_HZ),
        "-ac", str(decode_channels), "-f", "f32le", "pipe:1",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AudioQualityError("ffmpeg could not decode the audio stream") from exc
    samples = np.frombuffer(result.stdout, dtype="<f4")
    if samples.size == 0 or samples.size % decode_channels:
        raise AudioQualityError("decoding produced no complete audio samples")
    return samples.reshape(-1, decode_channels), analysis_duration


def _frame_metrics(mono):
    frame_length = max(1, int(ANALYSIS_SAMPLE_RATE_HZ * 0.02))
    usable = len(mono) - len(mono) % frame_length
    if usable < frame_length:
        raise AudioQualityError("decoded audio is too short for frame analysis")
    frames = mono[:usable].reshape(-1, frame_length)
    rms = np.sqrt(np.mean(np.square(frames.astype(np.float64)), axis=1))
    frame_db = 20.0 * np.log10(np.maximum(rms, 1e-12))
    noise_floor_db = float(np.percentile(frame_db, 10))
    signal_level_db = float(np.percentile(frame_db, 90))
    snr_proxy_db = signal_level_db - noise_floor_db
    active_threshold_db = max(noise_floor_db + 10.0, -45.0)
    active = frame_db >= active_threshold_db
    active_values = frame_db[active]
    level_spread_db = (float(np.percentile(active_values, 90)
                             - np.percentile(active_values, 10))
                       if active_values.size >= 10 else None)
    return {
        "frame_db": frame_db,
        "active": active,
        "noise_floor_dbfs": noise_floor_db,
        "signal_level_dbfs": signal_level_db,
        "snr_proxy_db": snr_proxy_db,
        "active_threshold_dbfs": active_threshold_db,
        "speech_proportion": float(np.mean(active)),
        "near_silent_frame_ratio": float(np.mean(frame_db <= -60.0)),
        "active_level_spread_db": level_spread_db,
    }


def _reverberation_tail_ratio(frame_db, active, noise_floor_db):
    """Return a conservative energy-tail proxy after clear speech offsets."""
    transitions = np.flatnonzero(active[:-1] & ~active[1:])
    ratios = []
    for index in transitions:
        tail = frame_db[index + 1:index + 11]
        if tail.size < 5:
            continue
        ratios.append(float(np.mean(tail >= noise_floor_db + 6.0)))
    return float(np.mean(ratios)) if len(ratios) >= 3 else None


def _empty_report(audio_path, policy, long_ok):
    audio_path = Path(audio_path).resolve()
    audio = {
        "filename": audio_path.name,
        "path": str(audio_path),
        "byte_sha256": (_sha256_file(audio_path)
                        if audio_path.is_file() else None),
        "byte_size": audio_path.stat().st_size if audio_path.is_file() else None,
        "duration_s": None,
        "container_format": None,
        "codec": None,
        "sample_rate_hz": None,
        "channels": None,
        "channel_layout": None,
    }
    return {
        "schema_version": QUALITY_SCHEMA_VERSION,
        "threshold_version": THRESHOLD_VERSION,
        "policy": policy,
        "long_audio_approved": bool(long_ok),
        "decision": "reject",
        "overall_status": "fail",
        "audio": audio,
        "analysis": None,
        "checks": [],
        "limitations": [],
    }


def _finalize(report):
    statuses = [item["status"] for item in report["checks"]]
    if "fail" in statuses:
        report["overall_status"] = "fail"
        report["decision"] = "reject"
    elif "warn" in statuses:
        report["overall_status"] = "warn"
        report["decision"] = "continue"
    else:
        report["overall_status"] = "pass"
        report["decision"] = "continue"
    report["limitations"] = [
        item["reason"] for item in report["checks"]
        if (item["status"] in {"warn", "fail"}
            or item["availability"] != "available")
    ]
    return report


def analyze_audio(audio_path, policy="lenient", long_ok=False):
    """Inspect one input and return a complete nonsecret quality report."""
    if policy not in {"lenient", "baseline"}:
        raise ValueError(f"unknown quality policy: {policy}")
    report = _empty_report(audio_path, policy, long_ok)
    try:
        audio = probe_audio(audio_path)
    except AudioQualityError as exc:
        report["checks"].append(_check(
            "file_readability", "fail", False, None, "readable audio stream",
            str(exc), ("all_measurements",),
        ))
        return _finalize(report)

    report["audio"] = audio
    report["checks"].append(_check(
        "file_readability", "pass", True, None, "readable audio stream",
        "The file and its first audio stream are readable.",
    ))

    duration_s = audio["duration_s"]
    too_short = duration_s < THRESHOLDS["minimum_duration_s"]
    too_long = duration_s > THRESHOLDS["long_duration_s"]
    duration_problem = too_short or (too_long and not long_ok)
    if too_short:
        duration_reason = "Audio under five seconds is too short for analysis."
    elif too_long and not long_ok:
        duration_reason = ("Audio over thirty minutes requires explicit "
                           "--long-ok approval.")
    elif too_long:
        duration_reason = ("Long audio was explicitly approved; quality is "
                           "sampled from the first five minutes.")
    else:
        duration_reason = "Audio duration is within the supported range."
    duration_status = ("warn" if too_long and long_ok else
                       _problem_status(duration_problem, policy, hard=True))
    report["checks"].append(_check(
        "duration", duration_status,
        duration_s, "seconds",
        {"minimum_s": THRESHOLDS["minimum_duration_s"],
         "long_s": THRESHOLDS["long_duration_s"],
         "long_ok": bool(long_ok)},
        duration_reason,
        ("all_measurements",) if duration_problem or too_long else (),
    ))
    if duration_problem:
        return _finalize(report)

    sample_rate = audio.get("sample_rate_hz")
    low_sample_rate = (sample_rate is None
                       or sample_rate < THRESHOLDS["minimum_sample_rate_hz"])
    report["checks"].append(_check(
        "sample_rate",
        _problem_status(low_sample_rate, policy),
        sample_rate, "Hz", {"minimum_hz": 16000},
        ("The source sample rate may limit timing and acoustic measurements."
         if low_sample_rate else
         "The source sample rate supports the current measurements."),
        ("pitch", "voice_quality", "word_timing") if low_sample_rate else (),
    ))

    channels = audio.get("channels") or 0
    unusual_channels = channels not in (1, 2)
    channel_reason = (
        "Audio with more than two channels is downmixed to mono for quality "
        "analysis and may not preserve every channel condition."
        if channels > 2 else
        "The audio channel count is unavailable or unsupported."
        if unusual_channels else
        ("Stereo channels are inspected separately, then averaged for "
         "frame analysis." if channels == 2 else
         "Mono audio requires no channel conversion for frame analysis.")
    )
    report["checks"].append(_check(
        "channel_handling", _problem_status(unusual_channels, policy),
        channels, "channels", {"supported": [1, 2]}, channel_reason,
        ("loudness", "voice_quality") if unusual_channels else (),
    ))

    try:
        decoded, analysed_duration = _decode_audio(
            audio_path, channels, duration_s
        )
    except AudioQualityError as exc:
        report["checks"].append(_check(
            "decoded_audio", "fail", False, None, "nonempty decoded samples",
            str(exc), ("all_measurements",),
        ))
        return _finalize(report)

    peak = float(np.max(np.abs(decoded)))
    rms = float(np.sqrt(np.mean(np.square(decoded.astype(np.float64)))))
    peak_dbfs = _dbfs(peak)
    rms_dbfs = _dbfs(rms)
    clipping_ratio = float(np.mean(np.abs(decoded) >= 0.999))
    mono = np.mean(decoded, axis=1)
    try:
        frames = _frame_metrics(mono)
    except AudioQualityError as exc:
        report["checks"].append(_check(
            "decoded_audio", "fail", False, None, "usable frame sequence",
            str(exc), ("all_measurements",),
        ))
        return _finalize(report)

    report["checks"].append(_check(
        "decoded_audio", "pass", True, None, "nonempty decoded samples",
        "The selected audio stream decoded into usable samples.",
    ))
    report["checks"].append(_check(
        "codec_support", "pass", audio.get("codec"), None,
        "decodable by the installed ffmpeg version",
        "The reported codec decoded successfully with the local runtime.",
    ))
    report["analysis"] = {
        "method": "ffmpeg_float_decode_and_frame_energy_v1",
        "decoded_sample_rate_hz": ANALYSIS_SAMPLE_RATE_HZ,
        "decoded_channels": decoded.shape[1],
        "analysed_duration_s": _round(analysed_duration, 3),
        "full_file_analysed": duration_s <= MAX_ANALYSIS_DURATION_S,
        "peak_dbfs": _round(peak_dbfs, 2),
        "rms_dbfs": _round(rms_dbfs, 2),
        "clipping_ratio": _round(clipping_ratio, 6),
        "near_silent_frame_ratio": _round(
            frames["near_silent_frame_ratio"], 4
        ),
        "speech_proportion": _round(frames["speech_proportion"], 4),
        "speech_proportion_method": "adaptive_frame_energy_proxy_v1",
        "snr_proxy_db": _round(frames["snr_proxy_db"], 2),
        "snr_proxy_method": "p90_minus_p10_frame_rms_v1",
        "active_level_spread_db": _round(
            frames["active_level_spread_db"], 2
        ),
        "active_level_spread_method":
            "p90_minus_p10_active_frame_rms_v1",
    }

    clipped = clipping_ratio >= THRESHOLDS["clipping_ratio"]
    report["checks"].append(_check(
        "clipping", _problem_status(clipped, policy),
        _round(clipping_ratio, 6), "ratio",
        {"maximum": THRESHOLDS["clipping_ratio"]},
        ("Clipped samples can distort loudness, pitch, and voice quality."
         if clipped else "No material digital clipping was detected."),
        ("loudness", "pitch", "voice_quality") if clipped else (),
    ))

    hot_peak = peak_dbfs >= THRESHOLDS["hot_peak_dbfs"]
    quiet_peak = peak_dbfs <= THRESHOLDS["quiet_peak_dbfs"]
    peak_problem = hot_peak or quiet_peak
    report["checks"].append(_check(
        "peak_level", _problem_status(peak_problem, policy),
        _round(peak_dbfs, 2), "dBFS",
        {"quiet_below": THRESHOLDS["quiet_peak_dbfs"],
         "hot_above": THRESHOLDS["hot_peak_dbfs"]},
        ("The recording peak is too quiet to support speech analysis."
         if quiet_peak else
         "The recording peak is very close to the digital maximum."
         if hot_peak else "Peak level is within the operational range."),
        ("all_measurements",) if quiet_peak else
        ("loudness", "voice_quality") if hot_peak else (),
    ))

    near_silent = (
        rms_dbfs <= THRESHOLDS["near_silent_rms_dbfs"]
        or frames["near_silent_frame_ratio"]
        >= THRESHOLDS["near_silent_frame_ratio"]
    )
    low_rms = rms_dbfs <= THRESHOLDS["low_rms_dbfs"]
    report["checks"].append(_check(
        "rms_and_near_silence",
        _problem_status(near_silent or low_rms, policy, hard=near_silent),
        {"rms_dbfs": _round(rms_dbfs, 2),
         "near_silent_frame_ratio": _round(
             frames["near_silent_frame_ratio"], 4)},
        None,
        {"near_silent_rms_below": THRESHOLDS["near_silent_rms_dbfs"],
         "low_rms_below": THRESHOLDS["low_rms_dbfs"],
         "near_silent_ratio_above":
             THRESHOLDS["near_silent_frame_ratio"]},
        ("The recording is effectively silent and cannot support analysis."
         if near_silent else
         "The recording level is low and may reduce measurement reliability."
         if low_rms else "Overall signal level is usable."),
        ("all_measurements",) if near_silent else
        ("transcription", "pitch", "voice_quality") if low_rms else (),
    ))

    low_speech = (frames["speech_proportion"]
                  < THRESHOLDS["minimum_speech_proportion"])
    report["checks"].append(_check(
        "speech_proportion", _problem_status(low_speech, policy),
        _round(frames["speech_proportion"], 4), "ratio",
        {"minimum": THRESHOLDS["minimum_speech_proportion"],
         "method": "adaptive_frame_energy_proxy_v1"},
        ("Very little speech-like energy was detected."
         if low_speech else
         "The recording contains enough speech-like energy for analysis."),
        ("rate", "language", "turn_metrics") if low_speech else (),
    ))

    low_snr = frames["snr_proxy_db"] < THRESHOLDS["minimum_snr_proxy_db"]
    report["checks"].append(_check(
        "signal_to_noise_proxy", _problem_status(low_snr, policy),
        _round(frames["snr_proxy_db"], 2), "dB proxy",
        {"minimum": THRESHOLDS["minimum_snr_proxy_db"],
         "method": "p90_minus_p10_frame_rms_v1"},
        ("Speech and background energy are poorly separated; this is an "
         "operational proxy, not a calibrated SNR measurement."
         if low_snr else
         "Speech and background energy are sufficiently separated by the "
         "documented proxy."),
        ("transcription", "pitch", "voice_quality") if low_snr else (),
    ))

    level_spread = frames["active_level_spread_db"]
    unstable = (level_spread is not None
                and level_spread > THRESHOLDS["unstable_level_spread_db"])
    report["checks"].append(_check(
        "recording_level_stability", _problem_status(unstable, policy),
        _round(level_spread, 2), "dB spread",
        {"maximum": THRESHOLDS["unstable_level_spread_db"],
         "method": "p90_minus_p10_active_frame_rms_v1"},
        ("Speech-like sections vary substantially in level."
         if unstable else
         "Speech-like sections have a stable operational level."
         if level_spread is not None else
         "Too few speech-like frames were available to assess level stability."),
        ("loudness", "voice_quality") if unstable else (),
        availability=("available" if level_spread is not None
                      else "unavailable"),
    ))

    tail_ratio = _reverberation_tail_ratio(
        frames["frame_db"], frames["active"], frames["noise_floor_dbfs"]
    )
    reverberant = (tail_ratio is not None
                   and tail_ratio > THRESHOLDS["reverberation_tail_ratio"])
    report["analysis"]["reverberation_tail_ratio"] = _round(tail_ratio, 3)
    report["checks"].append(_check(
        "reverberation_risk_proxy", _problem_status(reverberant, policy),
        _round(tail_ratio, 3), "ratio",
        {"maximum": THRESHOLDS["reverberation_tail_ratio"],
         "method": "post_offset_energy_tail_proxy_v1"},
        ("Energy persists after speech-like offsets, which may indicate "
         "reverberation or steady background sound."
         if reverberant else
         "No severe energy-tail risk was detected by the operational proxy."
         if tail_ratio is not None else
         "Too few clear speech offsets were available for a reverberation "
         "risk estimate."),
        ("pitch", "voice_quality", "word_timing") if reverberant else (),
        availability="available" if tail_ratio is not None else "unavailable",
    ))

    report["checks"].append(_check(
        "background_speech_preflight", "pass", "deferred", None,
        "solo contamination check after transcription",
        "A deterministic waveform preflight cannot identify another speaker "
        "reliably. Solo mode performs its existing provider cluster check "
        "before the report is treated as a personal baseline.",
        availability="deferred",
    ))
    return _finalize(report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quality-policy", choices=("lenient", "baseline"),
        default="lenient",
    )
    parser.add_argument("--long-ok", action="store_true")
    add_run_arguments(parser)
    args = parser.parse_args()
    context = context_from_args(args, REPO_ROOT, require_audio=True)
    report = analyze_audio(
        context.audio_path, policy=args.quality_policy, long_ok=args.long_ok
    )
    context.write_json("audio_quality.json", report)
    print(f"Audio quality: {report['overall_status']} "
          f"({report['policy']}) -> {report['decision']}")
    for item in report["checks"]:
        if item["status"] != "pass":
            print(f"  {item['status'].upper()}: {item['id']}: "
                  f"{item['reason']}")
    if report["decision"] == "reject":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
