"""
The runner (v5).

Every example names its recording with --audio. Leave --audio out and the
runner reads whichever single recording sits in audio/, which is convenient on
a machine that has one and an error on a fresh copy of this repository, because
no audio is published here.

  python3 pipeline/run_all.py --mode solo --audio regression/fixtures/solo.wav
  python3 pipeline/run_all.py --mode solo --audio recording.m4a --transcriber local
  python3 pipeline/run_all.py --mode conversation --speakers 2 --audio recording.m4a
  python3 pipeline/run_all.py --audio recording.m4a --output-dir results
  python3 pipeline/run_all.py --audio recording.m4a --speakers 2 --isolated-run
  python3 pipeline/run_all.py --audio recording.m4a --speakers 2 --interpret

Every run receives an ID and manifest. Stage 1 runs in parallel, later stages
run in order, and every active stage receives the same explicit input and
output context.
"""

import argparse
import json
import re
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from audio_quality import analyze_audio
from pipeline_config import DEFAULT_TRANSCRIBER, TRANSCRIBERS
from provenance import (
    build_initial_provenance,
    sync_provenance_to_master,
    utc_now,
)
from recording_modes import (
    INTERPRETATION_OUTPUTS,
    RECORDING_MODES,
    build_stage_plan,
    resolve_recording_mode,
)
from run_context import (
    MANIFEST_NAME,
    atomic_write_json,
    create_manifest,
    resolve_audio,
    update_manifest,
)
from session_context import (
    load_session_context,
    session_context_reference,
    validate_context_for_run,
)

PIPELINE = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE.parent

parser = argparse.ArgumentParser()
parser.add_argument("--speakers", type=int, default=None)
parser.add_argument("--mode", choices=RECORDING_MODES, default="auto",
                    help="declared recording mode, default: auto")
parser.add_argument("--me", type=str, default=None,
                    help="your speaker label (e.g. SPEAKER_00): appends this "
                         "run to history.json and updates progress.md")
parser.add_argument("--audio", type=Path, default=None,
                    help="explicit audio file instead of the first in /audio")
parser.add_argument("--output-dir", type=Path, default=None,
                    help="artifact directory, default: repository /output")
parser.add_argument("--isolated-run", action="store_true",
                    help="write under OUTPUT_DIR/RUN_ID")
parser.add_argument("--run-id", type=str, default=None,
                    help="optional stable run ID, otherwise one is generated")
parser.add_argument(
    "--session-context", type=Path, default=None,
    help="validated account, session, task, and consent context",
)
parser.add_argument(
    "--transcriber", choices=TRANSCRIBERS, default=DEFAULT_TRANSCRIBER,
    help=("which transcriber produces transcript.json. 'assemblyai' needs a "
          "paid key; 'local' runs on this machine and needs none. There is no "
          "fallback between them: a missing credential fails the run."),
)
parser.add_argument(
    "--quality-policy", choices=("lenient", "baseline"), default="lenient",
    help="audio gate strictness, default: lenient",
)
parser.add_argument(
    "--interpret", action="store_true",
    help=("also run the optional language model interpretation layer: "
          "listener, interpretation and claim verification. Off by default, "
          "because this pipeline's output is the measurement record in "
          "master.json. It needs a provider key and produces no score."),
)
parser.add_argument("--long-ok", action="store_true",
                    help="explicitly allow audio longer than 30 minutes")
args = parser.parse_args()
try:
    execution_mode = resolve_recording_mode(args.mode, args.speakers)
except ValueError as exc:
    parser.error(str(exc))
if execution_mode == "solo" and args.me not in (None, "SPEAKER_00"):
    parser.error("solo mode account holder is always SPEAKER_00")

run_id = args.run_id or time.strftime("%Y%m%dT%H%M%S") + uuid.uuid4().hex[:8]
if (run_id in {".", ".."}
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._]*", run_id)):
    parser.error("--run-id may contain only letters, numbers, dots, and underscores")

audio_path = resolve_audio(args.audio, REPO_ROOT / "audio")
base_output = (args.output_dir.expanduser().resolve()
               if args.output_dir else REPO_ROOT / "output")
output_dir = base_output / run_id if args.isolated_run else base_output
session_context_data = None
session_context_output_path = None
if args.session_context is not None:
    context_source_path = args.session_context.expanduser().resolve()
    if not context_source_path.is_file():
        parser.error(f"session context not found: {context_source_path}")
    try:
        session_context_data = load_session_context(context_source_path)
    except (json.JSONDecodeError, OSError) as exc:
        parser.error(f"session context is unreadable: {exc}")
    context_errors = validate_context_for_run(
        session_context_data, execution_mode, args.me, args.quality_policy
    )
    if context_errors:
        parser.error("invalid session context:\n" + "\n".join(context_errors))
    session_context_output_path = output_dir / "session_context.json"
    atomic_write_json(session_context_output_path, session_context_data)
total_start = time.time()
run_started_at_utc = utc_now()

quality_started_at_utc = utc_now()
quality_start = time.time()
quality_report = analyze_audio(
    audio_path, policy=args.quality_policy, long_ok=args.long_ok
)
quality_duration_s = time.time() - quality_start
quality_completed_at_utc = utc_now()
atomic_write_json(output_dir / "audio_quality.json", quality_report)

common_args = [
    "--audio", str(audio_path),
    "--output-dir", str(output_dir),
    "--run-id", run_id,
    "--recording-mode", (
        "solo" if execution_mode == "solo" else "conversation"
    ),
]
if session_context_output_path is not None:
    common_args += ["--session-context", str(session_context_output_path)]

history_cmd = ["history.py"]
if args.me:
    history_cmd += ["--me", args.me]

# label, command, outputs that must be atomically replaced, optional outputs
STAGE_1, LATER = build_stage_plan(
    execution_mode, args.speakers, history_cmd, transcriber=args.transcriber,
    interpret=args.interpret,
)

EXPECTED_OUTPUTS = [
    "audio_quality.json", "diarization.json", "transcript.json",
    "alignment.json", "vad.json", "acoustics.json", "words_attributed.json",
    "master.json", "fluency_events.json", "master_preview.txt",
]
if args.interpret:
    EXPECTED_OUTPUTS.extend(INTERPRETATION_OUTPUTS)
if session_context_output_path is not None:
    EXPECTED_OUTPUTS.append("session_context.json")
initial_provenance = build_initial_provenance(
    REPO_ROOT,
    audio_path,
    run_id,
    {
        "recording_mode_requested": args.mode,
        "recording_mode": execution_mode,
        "speakers_expected": 1 if execution_mode == "solo" else args.speakers,
        "transcription_speakers_expected": (
            None if execution_mode == "solo" else args.speakers
        ),
        "diarization_speakers_expected": (
            None if execution_mode == "solo" else args.speakers
        ),
        "transcriber": args.transcriber,
        "history_speaker_label": args.me,
        "isolated_output": args.isolated_run,
        "quality_policy": args.quality_policy,
        "interpretation_requested": args.interpret,
        "long_audio_approved": args.long_ok,
        "session_context_reference": (
            session_context_reference(session_context_data)
            if session_context_data is not None else None
        ),
    },
    run_started_at_utc,
    input_audio_metadata=quality_report["audio"],
)
manifest_path = create_manifest(
    output_dir, run_id, audio_path, EXPECTED_OUTPUTS,
    provenance=initial_provenance,
)
quality_stage_status = (
    "complete" if quality_report["decision"] == "continue" else "failed"
)
quality_stage_arguments = ["--quality-policy", args.quality_policy]
if args.long_ok:
    quality_stage_arguments.append("--long-ok")
update_manifest(
    manifest_path,
    stage="Audio quality preflight",
    stage_status=quality_stage_status,
    duration_s=quality_duration_s,
    completed_outputs=(
        ["audio_quality.json", "session_context.json"]
        if session_context_output_path is not None
        else ["audio_quality.json"]
    ),
    stage_script="audio_quality.py",
    stage_arguments=quality_stage_arguments,
    stage_started_at_utc=quality_started_at_utc,
    stage_completed_at_utc=quality_completed_at_utc,
)
sync_provenance_to_master(manifest_path)


def file_signature(name):
    path = output_dir / name
    if not path.is_file():
        return None
    stat = path.stat()
    return stat.st_ino, stat.st_mtime_ns, stat.st_size


def run_step(spec):
    label, cmd, required_outputs, optional_outputs = spec
    watched = required_outputs + optional_outputs
    before = {name: file_signature(name) for name in watched}
    start = time.time()
    started_at_utc = utc_now()
    full = [sys.executable, str(PIPELINE / cmd[0])] + cmd[1:] + common_args
    result = subprocess.run(full, capture_output=True, text=True)
    completed_at_utc = utc_now()
    after = {name: file_signature(name) for name in watched}
    return (spec, result, time.time() - start, before, after,
            started_at_utc, completed_at_utc)


def print_step(label, script, result, took, output_error=None):
    ok = result.returncode == 0 and output_error is None
    status = "OK" if ok else "FAILED"
    print(f"\n{'=' * 62}")
    print(f"{status}: {label}  ({script})  {took:.0f}s")
    print("=" * 62)
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    if out:
        print(out)
    if output_error:
        print(f"\n--- output contract ---\n{output_error}")
    if result.returncode != 0 and err:
        print("\n--- error ---")
        print(err[-3000:])


def finalize_step(spec, result, took, before, after,
                  started_at_utc, completed_at_utc):
    label, cmd, required_outputs, optional_outputs = spec
    output_error = None
    completed = []
    if result.returncode == 0:
        unchanged = [name for name in required_outputs
                     if after[name] is None or after[name] == before[name]]
        if unchanged:
            output_error = ("required outputs were not replaced by this stage: "
                            + ", ".join(unchanged))
        else:
            completed.extend(required_outputs)
            completed.extend(name for name in optional_outputs
                             if after[name] is not None
                             and after[name] != before[name])
    stage_status = ("complete" if result.returncode == 0
                    and output_error is None else "failed")
    update_manifest(
        manifest_path,
        stage=label,
        stage_status=stage_status,
        duration_s=took,
        completed_outputs=completed,
        stage_script=cmd[0],
        stage_arguments=cmd[1:],
        stage_started_at_utc=started_at_utc,
        stage_completed_at_utc=completed_at_utc,
    )
    sync_provenance_to_master(manifest_path)
    print_step(label, cmd[0], result, took, output_error)
    return stage_status == "complete"


def finish_run(status):
    update_manifest(
        manifest_path,
        run_status=status,
        run_completed_at_utc=utc_now(),
        run_duration_s=time.time() - total_start,
    )
    sync_provenance_to_master(manifest_path)


print(f"Run ID: {run_id}")
print(f"Recording mode: {args.mode} (execution: {execution_mode})")
print(f"Quality policy: {args.quality_policy}")
print("Interpretation layer: "
      + ("on (--interpret): listener, interpretation, verification"
         if args.interpret
         else "off. master.json is the output. Add --interpret for the "
              "optional model layer"))
print(f"Transcriber: {args.transcriber}"
      + ("  (local, no paid credentials)" if args.transcriber == "local"
         else "  (AssemblyAI, needs a key)"))
print(f"Audio: {audio_path}")
print(f"Output: {output_dir}")
print(f"Manifest: {output_dir / MANIFEST_NAME}")
print(f"Audio quality: {quality_report['overall_status']} "
      f"-> {quality_report['decision']}")
for item in quality_report["checks"]:
    if item["status"] != "pass":
        print(f"  {item['status'].upper()}: {item['id']}: {item['reason']}")
if quality_report["decision"] == "reject":
    finish_run("failed")
    sys.exit("\nPipeline stopped: audio quality preflight rejected the input.")
print(f"Stage 1: launching {len(STAGE_1)} extractors in parallel...")
if execution_mode == "solo":
    print("  solo path: Silero VAD replaces pyannote; Gemini referee is skipped")
for label, _, _, _ in STAGE_1:
    print(f"  started: {label}")

failed = []
with ThreadPoolExecutor(max_workers=len(STAGE_1)) as pool:
    futures = {pool.submit(run_step, spec): spec[0] for spec in STAGE_1}
    pending = set(futures)
    while pending:
        done = {future for future in pending if future.done()}
        for future in done:
            (spec, result, took, before, after,
             started_at_utc, completed_at_utc) = future.result()
            if not finalize_step(
                spec, result, took, before, after,
                started_at_utc, completed_at_utc,
            ):
                failed.append(spec[1][0])
            pending.discard(future)
        if pending:
            remaining = sorted(futures[future] for future in pending)
            elapsed = time.time() - total_start
            print(f"  ... {elapsed:.0f}s elapsed - still running: "
                  f"{', '.join(remaining)}")
            time.sleep(10)

if failed:
    finish_run("failed")
    sys.exit(f"\nPipeline stopped: stage 1 failures in {failed}. Fix and rerun.")

for spec in LATER:
    label = spec[0]
    print(f"\n  started: {label} ...")
    (spec, result, took, before, after,
     started_at_utc, completed_at_utc) = run_step(spec)
    if not finalize_step(
        spec, result, took, before, after,
        started_at_utc, completed_at_utc,
    ):
        finish_run("failed")
        sys.exit(f"\nPipeline stopped: {spec[1][0]} failed. Fix and rerun.")

finish_run("complete")
print(f"\n{'=' * 62}")
print(f"PIPELINE COMPLETE in {time.time() - total_start:.0f}s")
results = f"Results: {output_dir / 'master.json'}"
if args.interpret:
    results += (f", {output_dir / 'evaluation.md'}, "
                f"{output_dir / 'verification.md'}")
print(results)
