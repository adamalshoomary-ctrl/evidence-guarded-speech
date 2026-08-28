"""
Pauses, by voice activity detection.
Runs Silero VAD on the first audio file in /audio and saves:
  - every stretch of actual speech (start/end)
  - every pause between speech: where it happened and how long it lasted
Saves to /output/vad.json
Run from the repo root:  python3 pipeline/pauses.py
Needs ffmpeg installed. See the requirements in README.md.
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from silero_vad import load_silero_vad, get_speech_timestamps

from run_context import add_run_arguments, context_from_args

# --- setup ---------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
add_run_arguments(parser)
args = parser.parse_args()
context = context_from_args(args, REPO_ROOT, require_audio=True)

audio_file = context.audio_path
print(f"Finding pauses in: {audio_file.name}")

# --- convert to 16kHz mono wav with ffmpeg (avoids codec headaches) ------
tmp_wav = Path(tempfile.mkstemp(suffix=".wav")[1])
subprocess.run(
    ["ffmpeg", "-y", "-i", str(audio_file), "-ac", "1", "-ar", "16000",
     str(tmp_wav)],
    check=True, capture_output=True,
)

# --- run silero vad ------------------------------------------------------
wav_np, sample_rate = sf.read(tmp_wav, dtype="float32")
wav = torch.from_numpy(wav_np)

model = load_silero_vad(onnx=False, opset_version=16)
speech = get_speech_timestamps(
    wav, model,
    sampling_rate=sample_rate,
    return_seconds=True,      # timestamps in seconds, not samples
    min_silence_duration_ms=250,   # anything quieter/shorter isn't a "pause"
)
tmp_wav.unlink()

# --- derive pauses (the gaps between speech chunks) ----------------------
total_duration = len(wav_np) / sample_rate
pauses = []
for a, b in zip(speech, speech[1:]):
    gap = round(b["start"] - a["end"], 3)
    if gap >= 0.25:
        pauses.append({
            "starts_at": a["end"],
            "ends_at": b["start"],
            "duration": gap,
        })

speaking_time = round(sum(s["end"] - s["start"] for s in speech), 2)

result = {
    "audio_duration_s": round(total_duration, 2),
    "speaking_time_s": speaking_time,
    "silence_time_s": round(total_duration - speaking_time, 2),
    "speech_chunks": speech,
    "pauses": pauses,
}

out_path = context.output_path("vad.json")
context.write_json("vad.json", result)

# --- summary -------------------------------------------------------------
print(f"\nDone. Saved to: {out_path}")
print(f"Total: {result['audio_duration_s']}s | speaking: {speaking_time}s | silence: {result['silence_time_s']}s")
print(f"Pauses found: {len(pauses)}")
longest = sorted(pauses, key=lambda p: -p["duration"])[:5]
for p in longest:
    print(f"  {p['duration']:.2f}s pause at {p['starts_at']:.1f}s")
