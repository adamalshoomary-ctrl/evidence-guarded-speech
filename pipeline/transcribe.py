"""
Step: verbatim transcript (v5).
Sends the audio to AssemblyAI with:
  - disfluencies ON (keeps every um, uh, false start)
  - speaker labels ON, with speakers_expected when --speakers is given
    (improves attribution of short interjections at the source)
  - word-level timestamps
Saves the complete raw JSON to /output/transcript.json
Run:  python3 pipeline/transcribe.py [--speakers N]
"""

import argparse
import sys
import os
from pathlib import Path

import assemblyai as aai
from dotenv import load_dotenv

from pipeline_config import ASSEMBLYAI_SPEECH_MODEL_IDS
from run_context import add_run_arguments, context_from_args

REPO_ROOT = Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser()
parser.add_argument("--speakers", type=int, default=None,
                    help="known number of speakers (passed to AssemblyAI)")
add_run_arguments(parser)
args = parser.parse_args()
context = context_from_args(args, REPO_ROOT, require_audio=True)

load_dotenv(REPO_ROOT / ".env")
api_key = os.getenv("ASSEMBLYAI_API_KEY")
if not api_key:
    sys.exit("ERROR: ASSEMBLYAI_API_KEY not found in .env")
aai.settings.api_key = api_key

audio_file = context.audio_path
hint = f", speakers_expected={args.speakers}" if args.speakers else ""
print(f"Transcribing: {audio_file.name}  (disfluencies on{hint})")

config_kwargs = dict(
    speech_models=list(ASSEMBLYAI_SPEECH_MODEL_IDS),
    disfluencies=True,
    speaker_labels=True,
    punctuate=True,
    format_text=True,
)
if args.speakers:
    config_kwargs["speakers_expected"] = args.speakers

transcript = aai.Transcriber(
    config=aai.TranscriptionConfig(**config_kwargs)
).transcribe(str(audio_file))

if transcript.status == aai.TranscriptStatus.error:
    sys.exit(f"ERROR from AssemblyAI: {transcript.error}")

out_path = context.output_path("transcript.json")
context.write_json("transcript.json", transcript.json_response)

words = transcript.json_response.get("words", [])
fillers = [w for w in words if w["text"].strip(".,?!").lower()
           in {"um", "uh", "erm", "hmm", "mm"}]
print(f"\nDone. Saved to: {out_path}")
print(f"Total words: {len(words)} | fillers caught: {len(fillers)}")
