"""
Verification layer: checks the interpretation against the stored measurements.

Every claim in evaluation.md resolves to an exact evidence path in an allow
list built from master.json, and is checked against the failure classes in
pipeline/claim_ledger.py, including wrong speaker, timestamp outside its turn,
value mismatch, wrong sign, and unavailable or low quality measurement. A
second, older numeric safety net scans the report for bare numbers and matches
each against a value in the data.

What this does NOT demonstrate is stated in the report itself and is worth
repeating here. Since item R5 removed the model's scores, its numeric claims
are largely restatements of values it was handed, so a clean report mostly
shows that a copy operation copied correctly. Verification is only as
interesting as the model's freedom to be wrong. The failure that actually
matters, an interpretation the evidence does not support, is not numeric and
this verifier cannot catch it.

Saves OUTPUT/verification.md, OUTPUT/verification.json, and prints the summary.
Run:  python3 pipeline/verify.py
"""

import argparse
import json
import re
import sys
from pathlib import Path

from claim_ledger import strip_measurement_record, verify_claim_ledger
from run_context import add_run_arguments, context_from_args

REPO_ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
add_run_arguments(parser)
args = parser.parse_args()
context = context_from_args(args, REPO_ROOT)
OUT = context.output_dir

eval_path = context.output_path("evaluation.md", required=True)
claims_path = context.output_path("evaluation_claims.json", required=True)
master_path = context.output_path("master.json", required=True)

# The run record above the report is rendered from master.json by the
# pipeline. Checking its numbers against master.json would check the renderer
# against itself and inflate the verified count with numbers no model wrote.
evaluation = strip_measurement_record(eval_path.read_text(encoding="utf-8"))
claim_ledger = json.loads(claims_path.read_text(encoding="utf-8"))
master = json.loads(master_path.read_text(encoding="utf-8"))

evaluator_status = (master.get("meta", {}).get("enrichment_status", {})
                    .get("evaluator", {}))
if evaluator_status.get("status") != "complete":
    category = evaluator_status.get("error_category") or "not_completed"
    report = "\n".join([
        "# Verification unavailable",
        "",
        "The language model interpretation did not complete, so there are "
        "no interpretation claims to verify.",
        f"Safe error category: `{category}`",
        "Objective measurement artifacts remain available in master.json.",
    ])
    context.write_text("verification.md", report)
    context.write_json("verification.json", {
        "schema_version": "1.0.0",
        "status": "unavailable",
        "error_category": category,
        "claim_verification": None,
        "legacy_numeric_verification": None,
    })
    print(report)
    sys.exit(0)

claim_verification = verify_claim_ledger(master, claim_ledger, evaluation)

# ---- collect every number that exists in the master data -----------------
truth = set()

def harvest(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            harvest(v)
    elif isinstance(obj, list):
        for v in obj:
            harvest(v)
    elif isinstance(obj, (int, float)):
        for nd in (0, 1, 2):
            truth.add(round(float(obj), nd))

harvest(master)

# pause markers inside expressive text: "... [1.4s]"
for t in master.get("turns", []):
    for m in re.finditer(r"\[(\d+(?:\.\d+)?)s\]", t.get("expressive_text", "")):
        truth.add(round(float(m.group(1)), 1))

def verified(x, tol=0.06):
    x = float(x)
    if round(x, 2) in truth or round(x, 1) in truth or round(x, 0) in truth:
        return True
    return any(abs(x - v) <= tol for v in truth)

# ---- signed loudness values (for directional above/below checks) ---------
signed_db = set()

def harvest_signed(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if (k in ("loud_db_above_avg", "loudness_vs_own_avg_db")
                    and isinstance(v, (int, float))):
                signed_db.add(round(float(v), 1))
            harvest_signed(v)
    elif isinstance(obj, list):
        for v in obj:
            harvest_signed(v)

harvest_signed(master)

def signed_ok(magnitude, direction, tol=0.06):
    pool = [v for v in signed_db
            if (v > 0 if direction == "above" else v < 0)]
    return any(abs(abs(v) - magnitude) <= tol for v in pool)

# ---- extract claims from the evaluation ----------------------------------
CLAIM_PATTERNS = [
    (r"(\d+(?:\.\d+)?)\s*(?:s\b|sec|second)", "seconds"),
    (r"(\d+(?:\.\d+)?)\s*dB", "dB"),
    (r"(\d+(?:\.\d+)?)\s*Hz", "Hz"),
    (r"(\d+(?:\.\d+)?)\s*(?:fillers?|uptalks?)\s*(?:/|per)\s*min", "per-min rate"),
    (r"t\s*=\s*(\d+(?:\.\d+)?)", "timestamp"),
]
DIRECTIONAL_DB = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*dB\s+(above|below)", re.I)

claims = []
for line in evaluation.splitlines():
    stripped = line.strip()
    directional_vals = set()
    for m in DIRECTIONAL_DB.finditer(line):
        raw = float(m.group(1))
        directional_vals.add(abs(raw))
        claims.append({
            "value": abs(raw),
            "kind": f"dB {m.group(2).lower()}",
            "direction": m.group(2).lower(),
            "line": stripped[:110],
        })
    for pattern, kind in CLAIM_PATTERNS:
        for m in re.finditer(pattern, line):
            value = float(m.group(1))
            if kind == "dB" and value in directional_vals:
                continue  # already checked directionally above
            claims.append({
                "value": value,
                "kind": kind,
                "line": stripped[:110],
            })

ok, bad, wrong_dir = [], [], []
for c in claims:
    direction = c.get("direction")
    if direction:
        opposite = "below" if direction == "above" else "above"
        if signed_ok(c["value"], direction):
            ok.append(c)
        elif signed_ok(c["value"], opposite) or verified(c["value"]):
            wrong_dir.append(c)  # magnitude exists, but not with this sign
        else:
            bad.append(c)
    else:
        (ok if verified(c["value"]) else bad).append(c)

# ---- report --------------------------------------------------------------
total = len(claims)
rate = 100 * len(ok) / total if total else 100.0

lines = [
    "# Verification report",
    "\n## Evidence linked claims",
    f"Claims verified: {claim_verification['summary']['claims_passed']} of "
    f"{claim_verification['summary']['claims']}",
    f"Evidence references checked: {claim_verification['summary']['references']}",
    f"Claim issues: {claim_verification['summary']['issues']}",
    "Measurement references by quality: "
    + ", ".join(
        f"{key} {value}" for key, value in
        claim_verification["summary"]["measurement_references_by_quality"].items()
    ),
    "\n## Legacy numeric safety net",
    f"\nNumeric claims found: {total}",
    f"Verified against master.json: {len(ok)} ({rate:.0f}%)",
    f"UNVERIFIED: {len(bad)}",
    f"WRONG DIRECTION: {len(wrong_dir)}",
]
if claim_verification["issues"]:
    lines.append("\n## Claim issues\n")
    for issue in claim_verification["issues"]:
        claim_id = issue.get("claim_id") or "report"
        lines.append(f"- {claim_id}, {issue['code']}: {issue['message']}")
if wrong_dir:
    lines.append("\n## Wrong-direction claims (magnitude exists, sign does not)\n")
    for c in wrong_dir:
        lines.append(f"- {c['value']} ({c['kind']}) in: \"{c['line']}\"")
if bad:
    lines.append("\n## Unverified claims (fix or distrust these)\n")
    for c in bad:
        lines.append(f"- {c['value']} ({c['kind']}) in: \"{c['line']}\"")
if not bad and not wrong_dir:
    lines.append("\nEvery legacy numeric check traces to the data.")

lines.extend([
    "\n## What this report does not demonstrate\n",
    "A clean result here is weaker evidence than it looks, and saying so is "
    "part of the result.",
    "",
    "The interpretation layer is not allowed to produce a score, a rating or "
    "any number of its own. Its numeric claims are therefore largely "
    "restatements of values it was handed, and checking them mostly confirms "
    "that a copy operation copied correctly. Verification is only as "
    "interesting as the model's freedom to be wrong.",
    "",
    "In production this verifier has never rejected a claim. The only "
    "demonstrated catch is a synthetic case in the regression harness. And "
    "the failure that matters most, an interpretation the evidence does not "
    "support, carries no arithmetic at all, so nothing in this file can "
    "detect it.",
    "",
    "The run record at the top of `evaluation.md` is written by the pipeline "
    "from `master.json` and is excluded from every check above, because "
    "verifying it would verify the renderer against itself.",
])

report = "\n".join(lines)
context.write_text("verification.md", report)
overall_status = (
    "pass" if claim_verification["status"] == "pass"
    and not bad and not wrong_dir else "fail"
)
context.write_json("verification.json", {
    "schema_version": "1.0.0",
    "status": overall_status,
    "claim_verification": claim_verification,
    "legacy_numeric_verification": {
        "claims": total,
        "verified": len(ok),
        "unverified": len(bad),
        "wrong_direction": len(wrong_dir),
    },
})
print(report)

if overall_status == "fail":
    sys.exit(0)  # report, don't fail the pipeline - the report is the product
