"""
Step 4 of the pipeline: inside-the-word timing (forced alignment).
Runs WhisperX on the first audio file in /audio and saves, for every word,
its start/end time AND the timing of each individual character —
so we can later detect dragged sounds ("kindaaaa") and measure them.
Saves to /output/alignment.json
Run from the repo root:  python3 pipeline/align.py
First run downloads the model (~1-2 GB) — be patient.
"""

import argparse
from pathlib import Path

import whisperx

from pipeline_config import (
    WHISPERX_ASR_MODEL_ID,
    WHISPERX_BATCH_SIZE,
    WHISPERX_COMPUTE_TYPE,
    WHISPERX_DEVICE,
    whisperx_alignment_model_id,
)
from run_context import add_run_arguments, context_from_args

# --- setup ---------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument(
    "--vad-method", choices=("pyannote", "silero"), default="pyannote",
    help="voice activity detector used by WhisperX, default: pyannote",
)
add_run_arguments(parser)
args = parser.parse_args()
context = context_from_args(args, REPO_ROOT, require_audio=True)

audio_file = str(context.audio_path)
print(f"Aligning: {context.audio_path.name}")

device = WHISPERX_DEVICE
compute_type = WHISPERX_COMPUTE_TYPE

# --- 1. transcribe with whisper ------------------------------------------
print("Loading model (first time downloads it — can take a few minutes)...")
model = whisperx.load_model(
    WHISPERX_ASR_MODEL_ID,
    device,
    compute_type=compute_type,
    vad_method=args.vad_method,
)
audio = whisperx.load_audio(audio_file)
result = model.transcribe(audio, batch_size=WHISPERX_BATCH_SIZE)
print(f"Transcribed. Language: {result['language']}")

# --- 2. align: per-word and per-character timings ------------------------
print("Aligning words and characters...")
alignment_model_id, alignment_version_policy = whisperx_alignment_model_id(
    result["language"]
)
align_model, metadata = whisperx.load_align_model(
    language_code=result["language"], device=device,
    model_name=alignment_model_id,
)
aligned = whisperx.align(
    result["segments"],
    align_model,
    metadata,
    audio,
    device,
    return_char_alignments=True,   # the whole point: per-letter timing
)
aligned["model_provenance"] = {
    "language": result["language"],
    "asr_model_id": WHISPERX_ASR_MODEL_ID,
    "alignment_model_id": alignment_model_id,
    "alignment_model_version_policy": alignment_version_policy,
    "vad_method": args.vad_method,
}

# --- save ----------------------------------------------------------------
out_path = context.output_path("alignment.json")
context.write_json("alignment.json", aligned)

# --- quick summary: longest words vs their letter count -------------------
words = []
for seg in aligned.get("segments", []):
    for w in seg.get("words", []):
        if "start" in w and "end" in w:
            dur = w["end"] - w["start"]
            words.append((dur, w["word"].strip(), w["start"]))

words.sort(reverse=True)
print(f"\nDone. Saved to: {out_path}")
print("Longest-held words (candidates for drags):")
for dur, word, start in words[:8]:
    per_letter = dur / max(len(word), 1)
    print(f'  "{word}" at {start:.1f}s — held {dur:.2f}s ({per_letter:.3f}s per letter)')
