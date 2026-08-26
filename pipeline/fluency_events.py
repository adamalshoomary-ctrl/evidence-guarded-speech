"""Create a guarded artifact of timestamped speech event candidates.

The stage runs after final speaker attribution. It does not diagnose, score,
interpret, or infer that candidate absence means fluent speech.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_context import add_run_arguments, context_from_args


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    add_run_arguments(parser)
    args = parser.parse_args()
    context = context_from_args(args, REPO_ROOT)

    # The repository root is not automatically on sys.path when this file is
    # invoked as `python pipeline/fluency_events.py`.
    import sys
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from fluency_events.extract import extract_candidates, validate_artifact

    words = _load(context.output_path("words_attributed.json", required=True))
    alignment = _load(context.output_path("alignment.json", required=True))
    master_path = context.output_path("master.json", required=True)
    master = _load(master_path)
    audio_quality = _load(
        context.output_path("audio_quality.json", required=True)
    )

    artifact = extract_candidates(words, alignment, master, audio_quality)
    errors = validate_artifact(artifact)
    if errors:
        raise SystemExit("Invalid fluency event artifact:\n" + "\n".join(errors))
    context.write_json("fluency_events.json", artifact)
    master.setdefault("meta", {})["fluency_event_evidence"] = {
        "status": artifact["status"],
        "artifact": "fluency_events.json",
        "candidate_events_excluded_from_evaluation": True,
        "candidate_absence_does_not_establish_fluency": True,
        "possible_block_automation": "unavailable",
        "scientific_release": "locked",
        "diagnosis": "blocked",
        "severity": "blocked",
        "released_interpretation": "blocked",
        "personal_progress": "blocked",
    }
    context.write_json("master.json", master)

    print(
        "Speech event evidence: "
        f"{artifact['candidate_count']} review candidates; "
        "possible block automation unavailable."
    )
    print("Candidates are not confirmed events, a score, or a diagnosis.")
    print(f"Done. Saved to: {context.output_path('fluency_events.json')}")


if __name__ == "__main__":
    main()
