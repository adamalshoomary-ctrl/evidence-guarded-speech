"""
Step: history + progress (longitudinal tracking, runs last).
If --me SPEAKER_XX is given with a validated session context, appends one
record for that stable account, session, task attempt, and local speaker to
/history.json (repo root). The local speaker label is never durable identity.

No language model output is recorded. The five scores this file used to parse
out of evaluation.md were removed in item R5 on 2026-08-24, along with the
duplicated regular expression parser that read them.

Every durable write also rebuilds /progress.md through the evidence-gated
personal baseline evaluator. It does not use a generic percentage trend.
Fully deterministic - no LLM calls.

Run:  python3 pipeline/history.py --me SPEAKER_00 --session-context CONTEXT
Without --me it prints a skip notice and exits 0 (so the pipeline can
always run it as its final step).
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from history_identity import records_for_scope
from personal_progress import (
    HISTORY_RECORD_VERSION,
    comparison_from_session_context,
    evaluate_personal_progress,
    render_progress_markdown,
)
from run_context import (
    add_run_arguments,
    atomic_write_json,
    atomic_write_text,
    context_from_args,
)
from session_context import load_session_context, validate_context_for_run

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = REPO_ROOT / "history.json"
PROGRESS_PATH = REPO_ROOT / "progress.md"

parser = argparse.ArgumentParser()
parser.add_argument("--me", type=str, default=None,
                    help="your speaker label in this recording "
                         "(e.g. SPEAKER_00); enables history tracking")
parser.add_argument(
    "--history-path", type=Path, default=HISTORY_PATH,
    help=argparse.SUPPRESS,
)
parser.add_argument(
    "--progress-path", type=Path, default=PROGRESS_PATH,
    help=argparse.SUPPRESS,
)
add_run_arguments(parser)
args = parser.parse_args()
context = context_from_args(args, REPO_ROOT, require_audio=bool(args.me))
OUT = context.output_dir
history_path = args.history_path.expanduser().resolve()
progress_path = args.progress_path.expanduser().resolve()

if not args.me:
    print("History: no --me speaker given - skipping (nothing recorded).")
    sys.exit(0)

if context.session_context_path is None:
    sys.exit(
        "ERROR: --me requires --session-context so durable history is linked "
        "to stable account, session, and context identities"
    )

master_path = context.output_path("master.json", required=True)
master = json.loads(master_path.read_text(encoding="utf-8"))

try:
    session_context = load_session_context(context.session_context_path)
except (json.JSONDecodeError, OSError) as exc:
    sys.exit(f"ERROR: session context is unreadable: {exc}")
context_errors = validate_context_for_run(
    session_context,
    master.get("meta", {}).get("recording_type"),
    args.me,
)
if context_errors:
    sys.exit("ERROR: invalid session context: " + "; ".join(context_errors))

metrics = master.get("computed_metrics", {})
if args.me not in metrics:
    sys.exit(f"ERROR: --me {args.me} not found in this recording. "
             f"Speakers present: {sorted(metrics)}")

audio_name = context.audio_path.name


# The interpretation layer is opt in, so a run may legitimately have no
# verification report. Its absence is recorded as null and never as zero.
verification_pct = None
verif_path = OUT / "verification.md"
if verif_path.is_file():
    m = re.search(r"Verified against master\.json:\s*\d+\s*\((\d+)%\)",
                  verif_path.read_text(encoding="utf-8"))
    if m:
        verification_pct = int(m.group(1))

record = {
    "history_record_version": HISTORY_RECORD_VERSION,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "date": datetime.now().isoformat(timespec="seconds"),
    "account_id": session_context["account"]["account_id"],
    "session_id": session_context["session"]["session_id"],
    "context_id": session_context["context"]["context_id"],
    "context_category": session_context["context"]["category"],
    "task_attempt_id": session_context["attempt"]["attempt_id"],
    "attempt_role": session_context["attempt"]["attempt_role"],
    "progress_intent": session_context["attempt"]["progress_intent"],
    "parent_attempt_id": session_context["attempt"]["parent_attempt_id"],
    "exercise_id": session_context["attempt"]["exercise_id"],
    "task_id": session_context["task"]["task_id"],
    "task_version": session_context["task"]["task_version"],
    "prompt_id": session_context["task"]["prompt_id"],
    "prompt_version": session_context["task"]["prompt_version"],
    "comparison": comparison_from_session_context(session_context),
    "user_report": session_context["self_report"],
    "real_world_outcome": session_context.get("outcome_report"),
    "audio_filename": audio_name,
    "speaker_label": args.me,
    "computed_metrics": metrics[args.me],
    "measurement_metadata": (master.get("measurement_metadata", {})
                             .get("speakers", {}).get(args.me)),
    "renderer_audit": master.get("meta", {}).get("renderer_audit"),
    "verification_pct": verification_pct,
    "run_quality": {
        "audio_quality": master.get("meta", {}).get("audio_quality"),
        "renderer_audit": master.get("meta", {}).get("renderer_audit"),
        "verification_pct": verification_pct,
    },
}

history = []
if history_path.exists():
    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
        if not isinstance(history, list):
            print("WARNING: history.json is not a list - starting fresh")
            history = []
    except json.JSONDecodeError:
        print("WARNING: history.json unreadable - starting fresh")
        history = []
history.append(record)
atomic_write_json(history_path, history)
print(f"History: recorded run #{len(history)} for {args.me} "
      f"({audio_name}) -> {history_path.name}")

# -------------------------------- evidence-gated personal progress report
scoped_history = records_for_scope(history, record)
progress_result = evaluate_personal_progress(scoped_history)
atomic_write_text(progress_path, render_progress_markdown(progress_result))
print(f"Progress: wrote {progress_path.name} with "
      f"{progress_result['baseline_status']['status']} "
      f"({len(scoped_history)} same-context records considered)")
