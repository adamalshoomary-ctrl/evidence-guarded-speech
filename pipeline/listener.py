"""
Step: the listener (v4 - enrichment pass, runs AFTER merge).
Gemini receives BOTH the raw audio AND the merged turn structure
(final speaker labels, timestamps, expressive transcript, metrics),
listens to the audio first, then compares against the data.

It returns findings keyed to OUR turn_ids and OUR speaker labels -
no more label guessing, no more invented timestamps - and this script
writes them directly INTO master.json:
  - per-turn directly audible listener_note
  - notable_moments (with contradiction flags where audio disagrees
    with the instrumented data)
  - speaker_overall_impressions
  - meta.audio_conditions, meta.listener_contradictions

Raw response also saved to /output/listener.json for debugging.
Run:  python3 pipeline/listener.py   (after merge.py)
Needs GEMINI_API_KEY in .env
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field

from pipeline_config import (
    ENRICHMENT_REQUEST_TIMEOUT_S,
    GEMINI_THINKING_LEVEL,
)
from llm_contract import (
    GEMINI_MODEL_ID,
    ProviderFailureError,
    SemanticValidationError,
    initial_enrichment_status,
    parse_structured_response,
    pending_status,
    run_with_retry,
    update_enrichment_status,
)
from run_context import add_run_arguments, context_from_args
from voice_safety import unsupported_voice_inferences

REPO_ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
add_run_arguments(parser)
args = parser.parse_args()
context = context_from_args(args, REPO_ROOT, require_audio=True)
OUT = context.output_dir

load_dotenv(REPO_ROOT / ".env")
api_key = os.getenv("GEMINI_API_KEY")

master_path = context.output_path("master.json", required=True)
master = json.loads(master_path.read_text(encoding="utf-8"))

# A listener rerun invalidates every prior listener and downstream evaluator
# artifact. Clear them before the request so failure cannot expose stale data.
for stale_path in (OUT / "listener.json", OUT / "audit.md",
                   OUT / "evaluation.md", OUT / "evaluation_claims.json",
                   OUT / "verification.md", OUT / "verification.json"):
    stale_path.unlink(missing_ok=True)
for stale_path in OUT.glob("evaluation_*.md"):
    stale_path.unlink()
for stale_path in OUT.glob("evaluation_claims_*.json"):
    stale_path.unlink()
for turn in master.get("turns", []):
    turn.pop("listener_note", None)
master["notable_moments"] = []
master.pop("listener_contradictions", None)
master["speaker_overall_impressions"] = {}
master["meta"]["audio_conditions"] = None
master["meta"]["renderer_audit"] = None
enrichment = master["meta"].setdefault(
    "enrichment_status", initial_enrichment_status()
)
enrichment["listener"] = pending_status(GEMINI_MODEL_ID)
enrichment["evaluator"] = pending_status(GEMINI_MODEL_ID)
context.write_json("master.json", master)

audio_file = context.audio_path

# compact turn digest for the prompt
digest = []
for t in master["turns"]:
    digest.append({
        "turn_id": t["turn_id"],
        "speaker": t["speaker"],
        "start_s": t["start_s"],
        "end_s": t["end_s"],
        "text": t["expressive_text"][:400],
        "low_confidence_words": t.get("low_confidence_words", []),
    })

measurement_limits = []
for speaker, sections in (master.get("measurement_metadata", {})
                          .get("speakers", {})).items():
    for section_name, entries in sections.items():
        for metric, evidence in entries.items():
            availability = evidence.get("availability", {}).get("status")
            quality = evidence.get("quality", {}).get("category")
            if availability != "available" or quality in {"low", "unavailable"}:
                measurement_limits.append({
                    "speaker": speaker,
                    "section": section_name,
                    "metric": metric,
                    "availability": availability,
                    "quality": quality,
                })

quality_context = {
    "audio_quality": {
        "status": (master.get("meta", {}).get("audio_quality") or {})
                  .get("overall_status"),
        "limitations": (master.get("meta", {}).get("audio_quality") or {})
                       .get("limitations", []),
    },
    "measurement_limits": measurement_limits,
}

# ---- sample rendered effects for the built-in renderer audit -------------
import random
random.seed(7)

def kind_of(fx):
    if "rising_pitch_hz" in fx:
        return "uptalk"
    if "held_s" in fx:
        return "drag"
    if "loud_db_above_avg" in fx:
        return "loud"
    if "filler_s" in fx and fx["filler_s"] >= 0.5:
        return "long_filler"
    return None

CLAIM = {
    "drag": "is noticeably stretched/held longer than the speaker's normal pace",
    "loud": "is spoken noticeably louder than the speaker's normal volume",
    "uptalk": "ends with a rising, question-like pitch although it is a statement",
    "long_filler": "is a noticeably long, drawn-out filler",
}

by_kind = {}
for t in master["turns"]:
    for fx in t.get("word_effects", []):
        k = kind_of(fx)
        if k:
            by_kind.setdefault(k, []).append(fx)
audit_samples = []
if by_kind:
    per_kind = max(2, 16 // len(by_kind))
    for k, pool in by_kind.items():
        audit_samples += [(k, fx) for fx in random.sample(pool, min(per_kind, len(pool)))]
    audit_samples = audit_samples[:16]

audit_claims = "\n".join(
    f'CHECK {i}: at {fx["t"]}s the word {fx["word"]!r} {CLAIM[k]} (category: {k})'
    for i, (k, fx) in enumerate(audit_samples, 1)
) or "(no rendered effects to audit)"

valid_ids = {t["turn_id"] for t in master["turns"]}
valid_speakers = {t["speaker"] for t in master["turns"]}


class TurnFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: int
    note: str = Field(description="One sentence about noteworthy delivery")


class NotableMoment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    t_s: float
    turn_id: int
    observation: str = Field(description="Open ended audible observation")


class ListenerContradiction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: int
    data_says: str
    audio_says: str
    evidence: str = Field(description="Open ended description of audible evidence")


class RendererAuditResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check: int
    supported: bool
    note: str = Field(description="Brief open ended reason for the judgment")


class ListenerResponse(BaseModel):
    """Exact listener enrichment shape consumed by the pipeline."""

    model_config = ConfigDict(extra="forbid")

    turn_findings: list[TurnFinding]
    moments: list[NotableMoment]
    contradictions: list[ListenerContradiction]
    overall: dict[str, str] = Field(
        description="Speaker labels mapped to open ended overall impressions"
    )
    audio_conditions: str
    renderer_audit: list[RendererAuditResult]

PROMPT = f"""You are an expert speech analyst with EARS. Below is the turn
structure of this recording, produced by instrumented analysis. Speaker
labels, timestamps, and expressive effects have explicit confidence limits;
do not treat flagged evidence as certain. The expressive spelling encodes
measured delivery - CAPS = louder than that speaker's average, stretched
letters = held longer, trailing ? = measured rising pitch, [SPK: "..."] =
backchannel).

Inspect meta.audio_quality before interpreting the sound. It contains the
deterministic preflight policy, checks, limitations, and signal quality
proxies. Treat warnings as limitations on affected observations. Do not call
an operational proxy a calibrated SNR or reverberation measurement.

QUALITY CONTEXT:
{json.dumps(quality_context, ensure_ascii=False)}

YOUR METHOD - in this order:
1. LISTEN to the full audio first, noting only directly audible events.
2. Then read the turn structure and compare.
3. Report what the audio tells you that the data cannot - and every place
   the audio CONTRADICTS the data, limited to words, timing, speaker, audible
   laughter, sighs, pauses, level changes, and renderer effects.
   Contradictions are your most valuable output.
4. AUDIT the renderer: below are claims about specific words at specific
   times. While listening, judge each one strictly - "supported": true only
   if a human listener would notice the described quality unprompted.

RENDERER CLAIMS TO AUDIT:
{audit_claims}

AUDIO ONLY rule: you cannot see anything. Never state visual actions as
fact; say "sounds like..." with the audible evidence.

VOICE SAFETY rule: describe acoustic events, not hidden causes or human
traits. Never infer emotion, cognitive load, fatigue, boredom, nervousness,
anxiety, confidence, personality, sincerity, gender, health, disorder, or
vocal damage from sound. Never call a voice monotone, lifeless, shaky, or
flat. A pause is a pause, a laugh is a laugh, and a sigh is a sigh; do not say
what caused it. These restrictions also apply to contradictions, notes,
moments, overall summaries, audio conditions, and renderer audit notes.

Use ONLY these turn_ids: {sorted(valid_ids)} and ONLY these speaker labels:
{sorted(valid_speakers)}. Reference times within each turn's start/end.

TURN STRUCTURE:
{json.dumps(digest, ensure_ascii=False)}

Keep moments and contradictions high-quality over high-quantity; empty
contradictions list is fine if data and audio agree.
Provide 2-3 sentences per speaker in the overall impressions, one sentence
on audio conditions, and one judgment for every renderer check. The enforced
response schema defines the output structure."""

client = (
    genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=ENRICHMENT_REQUEST_TIMEOUT_S * 1000
        ),
    )
    if api_key
    else None
)
uploaded = None

def ask():
    global uploaded
    if client is None:
        raise ProviderFailureError("GEMINI_API_KEY is unavailable")
    if uploaded is None:
        uploaded = client.files.upload(file=str(audio_file))
    response = client.models.generate_content(
        model=GEMINI_MODEL_ID,
        contents=[uploaded, PROMPT],
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=GEMINI_THINKING_LEVEL
            ),
            response_mime_type="application/json",
            response_json_schema=ListenerResponse.model_json_schema(),
        ),
    )
    return parse_structured_response(response, ListenerResponse)

def valid(data):
    tf = data.get("turn_findings", [])
    if not tf:
        return False
    referenced_ids = [f.get("turn_id") for f in tf]
    referenced_ids += [m.get("turn_id") for m in data.get("moments", [])]
    referenced_ids += [c.get("turn_id")
                       for c in data.get("contradictions", [])]
    if any(turn_id not in valid_ids for turn_id in referenced_ids):
        return False
    if any(speaker not in valid_speakers for speaker in data.get("overall", {})):
        return False
    checks = [v.get("check") for v in data.get("renderer_audit", [])]
    if any(not isinstance(i, int) or not (1 <= i <= len(audit_samples))
           for i in checks):
        return False
    return True

print(f"Listener (enrichment): {audio_file.name} + {len(digest)} turns")
def request_listener():
    candidate = ask()
    if not valid(candidate):
        raise SemanticValidationError("listener references failed validation")
    violations = unsupported_voice_inferences(candidate)
    if violations:
        raise SemanticValidationError(
            "unsupported voice inference: " + ", ".join(violations)
        )
    return candidate

data, status = run_with_retry(
    "listener", GEMINI_MODEL_ID, request_listener
)
if data is None:
    update_enrichment_status(master_path, "listener", status)
    print("Listener unavailable - objective measurements remain usable; "
          "audio interpretation and renderer audit are unavailable.")
    sys.exit(0)

context.write_json("listener.json", data)

# ---- write findings INTO master.json -------------------------------------
by_id = {t["turn_id"]: t for t in master["turns"]}
applied = 0
for f in data.get("turn_findings", []):
    t = by_id.get(f.get("turn_id"))
    if not t:
        continue
    if f.get("note"):
        t["listener_note"] = f["note"]
    applied += 1

master["notable_moments"] = [
    {"t_s": m.get("t_s"), "turn_id": m.get("turn_id"),
     "observation": m.get("observation", "")}
    for m in data.get("moments", [])
]
master["listener_contradictions"] = data.get("contradictions", [])
master["speaker_overall_impressions"] = {
    k: v for k, v in data.get("overall", {}).items() if k in valid_speakers
}
master["meta"]["audio_conditions"] = data.get("audio_conditions")

# ---- score the built-in renderer audit -----------------------------------
KNOB = {"drag": "DRAG_RATIO / DRAG_MIN_S / DRAG_PERCENTILE",
        "loud": "LOUD_DB_ABOVE",
        "uptalk": "RISE_RATIO / RISE_MIN_HZ",
        "long_filler": "filler stretch thresholds"}
results = {}
for v in data.get("renderer_audit", []):
    i = v.get("check")
    if not isinstance(i, int) or not (1 <= i <= len(audit_samples)):
        continue
    k, fx = audit_samples[i - 1]
    r = results.setdefault(k, {"yes": 0, "no": 0, "misses": []})
    if v.get("supported"):
        r["yes"] += 1
    else:
        r["no"] += 1
        r["misses"].append(f"{fx['word']!r} at {fx['t']}s - {v.get('note', '')[:80]}")

audit_summary = {}
if results:
    lines = ["# Renderer audit (folded into listener)\n"]
    for k, r in results.items():
        total = r["yes"] + r["no"]
        pct = round(100 * r["yes"] / total) if total else 0
        audit_summary[k] = {"agreement_pct": pct, "checked": total}
        lines.append(f"## {k}: {r['yes']}/{total} supported ({pct}%)")
        if pct < 80:
            lines.append(f"LOW - consider raising: {KNOB[k]} (in merge.py)")
        for miss in r["misses"]:
            lines.append(f"- not supported: {miss}")
        lines.append("")
    context.write_text("audit.md", "\n".join(lines))
    master["meta"]["renderer_audit"] = audit_summary

master["meta"]["enrichment_status"]["listener"] = status
context.write_json("master.json", master)

print(f"\nDone. Enriched {applied}/{len(master['turns'])} turns in master.json")
print(f"Moments: {len(master['notable_moments'])} | "
      f"Contradictions: {len(master['listener_contradictions'])}")
for c in master["listener_contradictions"][:4]:
    print(f"  turn {c.get('turn_id')}: data says {c.get('data_says')!r} "
          f"but audio says {c.get('audio_says')!r}")
for m in master["notable_moments"][:4]:
    print(f"  at {m.get('t_s')}s: {m.get('observation', '')[:100]}")
if audit_summary:
    print("Renderer audit: " + ", ".join(
        f"{k} {v['agreement_pct']}%" for k, v in audit_summary.items()))
