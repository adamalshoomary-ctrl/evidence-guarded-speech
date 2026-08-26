"""
Calibration tool: tune the renderer against YOUR ears.
Walks through every rendered effect in master.json (drags, CAPS, uptalk,
long fillers), plays you the audio slice, shows what the renderer decided,
and asks: did it get it right? At the end it reports agreement rates per
effect type and suggests threshold changes.

This is an interactive developer tool. It is deliberately not a pipeline stage
and the runner never calls it.

Run from the repo root:  python3 pipeline/calibrate.py
Point it at an isolated run with --output-dir and --audio, exactly like a
pipeline stage. Uses macOS 'afplay' to play clips (ffmpeg cuts them).
Answers: y / n / s(kip) / r(eplay) / q(uit).
"""

import argparse
import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from run_context import add_run_arguments, context_from_args

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDERER_THRESHOLDS = ("DRAG_RATIO", "DRAG_MIN_S", "DRAG_PERCENTILE",
                       "LOUD_DB_ABOVE", "RISE_RATIO", "RISE_MIN_HZ")


def current_thresholds():
    """Read the live renderer constants without importing executable merge.py.

    merge.py does all its work at import time, so it cannot be imported for
    one value. Reading them keeps this tool's advice from drifting out of date.
    """
    tree = ast.parse((REPO_ROOT / "pipeline" / "merge.py").read_text(
        encoding="utf-8"))
    return {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in RENDERER_THRESHOLDS
    }

parser = argparse.ArgumentParser()
add_run_arguments(parser)
args = parser.parse_args()
context = context_from_args(args, REPO_ROOT, require_audio=True)

master_path = context.output_path("master.json")
if not master_path.exists():
    sys.exit(f"ERROR: {master_path} missing - run the pipeline first")
master = json.loads(master_path.read_text(encoding="utf-8"))

audio_file = context.audio_path

def play(t, dur=2.5, pad=0.6):
    """Cut a short clip around time t and play it."""
    start = max(0.0, t - pad)
    tmp = Path(tempfile.mkstemp(suffix=".wav")[1])
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{start:.2f}", "-t", f"{dur:.2f}",
         "-i", str(audio_file), str(tmp)],
        check=True, capture_output=True,
    )
    subprocess.run(["afplay", str(tmp)])
    tmp.unlink()

def effect_type(fx):
    if "rising_pitch_hz" in fx:
        return "uptalk (?)"
    if "held_s" in fx:
        return "drag (stretched letters)"
    if "loud_db_above_avg" in fx:
        return "CAPS (loud)"
    if "filler_s" in fx:
        return "filler"
    return "other"

# collect all effects
items = []
for turn in master["turns"]:
    for fx in turn["word_effects"]:
        items.append((turn["speaker"], fx))

if not items:
    sys.exit("No rendered effects found in master.json - nothing to calibrate.")

print(f"Calibration: {len(items)} rendered effects to review.")
print("For each: the clip plays, you answer y (renderer was right), "
      "n (wrong), s (skip), r (replay), q (quit early).\n")

tally = {}
for i, (speaker, fx) in enumerate(items, 1):
    kind = effect_type(fx)
    detail = {k: v for k, v in fx.items() if k not in ("word", "t")}
    print(f"[{i}/{len(items)}] {kind}  word: {fx['word']!r}  at {fx['t']}s  "
          f"({speaker})  {detail}")
    play(fx["t"])
    while True:
        ans = input("  right? y/n/s/r/q: ").strip().lower()
        if ans == "r":
            play(fx["t"])
            continue
        break
    if ans == "q":
        break
    if ans in ("y", "n"):
        t = tally.setdefault(kind, {"y": 0, "n": 0})
        t[ans] += 1

print("\n===== calibration report =====")
for kind, t in tally.items():
    total = t["y"] + t["n"]
    rate = 100 * t["y"] / total if total else 0
    print(f"{kind}: {t['y']}/{total} agreed ({rate:.0f}%)")

print("\nCurrent thresholds in pipeline/merge.py:")
for name, value in current_thresholds().items():
    print(f"  {name} = {value}")

print("""
How to act on this (thresholds live at the top of pipeline/merge.py, and the
current values are printed above so this advice cannot go stale):
- drag agreement low (too many drags)   -> raise DRAG_RATIO or DRAG_MIN_S
- drags you heard but weren't flagged   -> lower DRAG_RATIO
- CAPS agreement low (too shouty)       -> raise LOUD_DB_ABOVE
- uptalk false positives                -> raise RISE_RATIO or RISE_MIN_HZ
- uptalk you heard but missed           -> lower RISE_RATIO
Rerun merge.py + this tool after each change until agreement feels ~85%+.

These thresholds were tuned by ear against the owner's own recordings. They are
an operational starting point, not a validated detector.
""")
