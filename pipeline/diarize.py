"""
Step: speaker diarization (generic).
Works out WHO speaks WHEN. Auto-detects the number of speakers by default;
pass --speakers N when the count is known (improves accuracy).
  python3 pipeline/diarize.py                 # auto-detect
  python3 pipeline/diarize.py --speakers 2    # known count
Saves /output/diarization.json
Needs HF_TOKEN in .env
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from pipeline_config import PYANNOTE_MODEL_ID
from run_context import add_run_arguments, context_from_args

REPO_ROOT = Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser()
parser.add_argument("--speakers", type=int, default=None,
                    help="known number of speakers (omit to auto-detect)")
add_run_arguments(parser)
args = parser.parse_args()
context = context_from_args(args, REPO_ROOT, require_audio=True)

load_dotenv(REPO_ROOT / ".env")
hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    sys.exit("ERROR: HF_TOKEN not found in .env")

audio_file = context.audio_path
mode = f"known count: {args.speakers}" if args.speakers else "auto-detect count"
print(f"Diarizing: {audio_file.name}  ({mode})")

tmp_wav = Path(tempfile.mkstemp(suffix=".wav")[1])
subprocess.run(
    ["ffmpeg", "-y", "-i", str(audio_file), "-ac", "1", "-ar", "16000", str(tmp_wav)],
    check=True, capture_output=True,
)

from pyannote.audio import Pipeline  # slow import
import soundfile as sf
import torch

pipeline = Pipeline.from_pretrained(
    PYANNOTE_MODEL_ID, token=hf_token
)

wav_np, sample_rate = sf.read(tmp_wav, dtype="float32")
waveform = torch.from_numpy(wav_np).unsqueeze(0)

kwargs = {}
if args.speakers:
    kwargs["num_speakers"] = args.speakers

diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate}, **kwargs)
tmp_wav.unlink()

turns = []
stats = {}
annotation = getattr(diarization, "speaker_diarization", diarization)
for segment, _, speaker in annotation.itertracks(yield_label=True):
    turns.append({
        "speaker": speaker,
        "start_s": round(segment.start, 2),
        "end_s": round(segment.end, 2),
        "duration_s": round(segment.end - segment.start, 2),
    })
    s = stats.setdefault(speaker, {"talk_time_s": 0.0, "turns": 0})
    s["talk_time_s"] = round(s["talk_time_s"] + segment.end - segment.start, 2)
    s["turns"] += 1

result = {
    "num_speakers_mode": "forced" if args.speakers else "auto",
    "turns": turns,
    "speakers": stats,
}

out_path = context.output_path("diarization.json")
context.write_json("diarization.json", result)

print(f"\nDone. Saved to: {out_path}")
print(f"Speakers found: {len(stats)}")
for spk, s in stats.items():
    print(f"  {spk}: {s['talk_time_s']}s across {s['turns']} turns")
