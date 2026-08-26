"""
Step: verbatim transcript, local path (no paid credentials).

The alternative to `transcribe.py`, which needs an AssemblyAI key. This stage
runs a Whisper model on this machine and writes the same `transcript.json`
shape, so every later stage is unchanged.

Three things about it are deliberate and are not cosmetic.

**It is chosen, never fallen back to.** `run_all.py --transcriber local` selects
it. A missing AssemblyAI key fails the run instead of quietly switching, because
the two paths do not transcribe the same way and a record that could have come
from either is not a record at all. The transcript names which produced it.

**It primes the decoder for disfluencies.** Whisper is trained to tidy speech
up, and this project measures the untidy parts. Without priming, the model
returned zero fillers on a recording that contains them. The initial prompt is
a documented, measured intervention, and its cost is that the model may also
report a filler that was not said. `docs/offline-transcription.md` carries the
measurement.

**It uses Silero for voice activity, not the WhisperX default.** The default is
pyannote, which is gated behind a Hugging Face token and a manual licence
acceptance. A stage whose purpose is to need no credentials cannot use it.

What it does not provide is speaker labels. Conversation runs do not need them,
because attribution comes from diarization. The solo contamination check does
read them, and records itself as unavailable rather than clear when they are
absent, which is the honest outcome and not a silent pass.

Run:  python3 pipeline/transcribe_local.py
"""

import argparse
import sys
from pathlib import Path

import whisperx

from pipeline_config import (
    WHISPERX_BATCH_SIZE,
    WHISPERX_COMPUTE_TYPE,
    WHISPERX_DEVICE,
    WHISPERX_TRANSCRIPTION_MODEL_ID,
    WHISPERX_TRANSCRIPTION_REPOSITORY,
    WHISPERX_TRANSCRIPTION_VAD_METHOD,
    whisperx_alignment_model_id,
)
from local_transcript import timed_words
from run_context import add_run_arguments, context_from_args

REPO_ROOT = Path(__file__).resolve().parent.parent

# Whisper suppresses disfluencies unless the decoding context contains them.
# This prompt is the whole intervention: it is short, it is only filled words
# and discourse markers, and it names nothing about the recording's content, so
# it cannot steer the transcript toward any subject matter.
DISFLUENCY_PRIMING_PROMPT = "Um, uh, so, like, you know, I mean, er, hmm."


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--speakers", type=int, default=None,
        help=("accepted for stage compatibility and deliberately unused: this "
              "path produces no speaker labels"),
    )
    add_run_arguments(parser)
    args = parser.parse_args()
    context = context_from_args(args, REPO_ROOT, require_audio=True)

    audio_file = context.audio_path
    print(f"Transcribing locally: {audio_file.name}  "
          f"(model {WHISPERX_TRANSCRIPTION_MODEL_ID}, disfluency priming on)")
    if args.speakers:
        print("  note: --speakers is ignored; the local path has no speaker "
              "labels and attribution comes from diarization")

    model = whisperx.load_model(
        WHISPERX_TRANSCRIPTION_MODEL_ID,
        WHISPERX_DEVICE,
        compute_type=WHISPERX_COMPUTE_TYPE,
        vad_method=WHISPERX_TRANSCRIPTION_VAD_METHOD,
        asr_options={"initial_prompt": DISFLUENCY_PRIMING_PROMPT},
    )
    audio = whisperx.load_audio(str(audio_file))
    result = model.transcribe(audio, batch_size=WHISPERX_BATCH_SIZE)
    language = result["language"]
    print(f"Transcribed. Language: {language}")

    alignment_model_id, _ = whisperx_alignment_model_id(language)
    align_model, metadata = whisperx.load_align_model(
        language_code=language, device=WHISPERX_DEVICE,
        model_name=alignment_model_id,
    )
    aligned = whisperx.align(
        result["segments"], align_model, metadata, audio, WHISPERX_DEVICE,
        return_char_alignments=False,
    )

    duration_s = len(audio) / 16000.0
    words, borrowed = timed_words(aligned, (0.0, duration_s))
    if not words:
        sys.exit("ERROR: local transcription produced no timed words")

    transcript = {
        "text": " ".join(word["text"] for word in words),
        "words": words,
        "language_code": language,
        "speech_model_used": WHISPERX_TRANSCRIPTION_REPOSITORY,
        "transcriber": "local",
        "speaker_labels": False,
        "why_no_speaker_labels": (
            "Whisper does not label speakers. Conversation attribution comes "
            "from diarization, and the solo contamination check records itself "
            "as unavailable rather than clear."
        ),
        "disfluency_priming_prompt": DISFLUENCY_PRIMING_PROMPT,
        "words_with_borrowed_timing": borrowed,
        "alignment_model_id": alignment_model_id,
    }
    out_path = context.output_path("transcript.json")
    context.write_json("transcript.json", transcript)

    print(f"\nDone. Saved to: {out_path}")
    print(f"Total words: {len(words)} | words needing borrowed timing: "
          f"{borrowed}")


if __name__ == "__main__":
    main()
