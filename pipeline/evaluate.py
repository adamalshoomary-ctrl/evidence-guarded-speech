"""
Step: the interpretation layer.
Sends master.json (+ optional scenario.txt) to the model and asks it to
describe what was measured.

This stage is opt in. A run without --interpret produces master.json and
stops. Nothing here creates measurement truth: the model may only restate and
explain values that already exist in master.json, every statement it makes
must resolve to an entry in the evidence catalog, and the deterministic run
record above its report is written by this file rather than by the model.

It produces no score, rating, index or summary number, and it does not
characterise the speaker. Those were removed in item R5 on 2026-08-24. They
were language model output parsed by regular expression against hand written
anchors, they were never validated as measurement scales, and they addressed
an audience this project does not have.

Saves OUTPUT/evaluation.md and OUTPUT/evaluation_claims.json
Uses GEMINI_API_KEY from .env
"""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from claim_ledger import (
    EvaluationPackage,
    build_evidence_catalog,
    canonicalize_package_claim_order,
    canonicalize_package_claim_text,
    canonicalize_package_references,
    claim_ledger,
    evaluation_model_input,
    normalise_report_newlines,
    render_measurement_record,
    scenario_record,
    unavailable_claim_ledger,
    validate_package_semantics,
    verify_claim_ledger,
)
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
context = context_from_args(args, REPO_ROOT)
OUT = context.output_dir

load_dotenv(REPO_ROOT / ".env")
api_key = os.getenv("GEMINI_API_KEY")

master_path = context.output_path("master.json", required=True)
master_data = json.loads(master_path.read_text(encoding="utf-8"))
enrichment = master_data.setdefault("meta", {}).setdefault(
    "enrichment_status", initial_enrichment_status()
)
enrichment["evaluator"] = pending_status(
    GEMINI_MODEL_ID
)
context.write_json("master.json", master_data)
model_input = evaluation_model_input(master_data)
# Runtime packages and source hashes are audit data, not measurement evidence.
model_input["meta"].pop("provenance", None)
master = json.dumps(model_input, ensure_ascii=False)

# Remove prior evaluator products before requesting new content. A failed
# request will replace evaluation.md with an explicit unavailable report.
for stale_path in (
    OUT / "evaluation.md", OUT / "evaluation_claims.json",
    OUT / "verification.md", OUT / "verification.json",
):
    stale_path.unlink(missing_ok=True)
# Numbered products came from a removed test-retest mode that measured the
# variance of scores this stage no longer produces. Clear any that survive in
# a reused output directory rather than leaving them to be read as current.
for stale_path in OUT.glob("evaluation_*.md"):
    stale_path.unlink()
for stale_path in OUT.glob("evaluation_claims_*.json"):
    stale_path.unlink()

scenario_path = REPO_ROOT / "scenario.txt"
if scenario_path.exists():
    scenario = scenario_path.read_text(encoding="utf-8").strip()
    scenario_data = scenario_record(scenario, declared=True)
    scenario_block = f"SCENARIO (provided by the user):\n{scenario}"
else:
    scenario = "No scenario was declared. Any setting is a model inference."
    scenario_data = scenario_record(scenario, declared=False)
    scenario_block = ("SCENARIO: none provided. Infer the likely setting, "
                      "relationship, and stakes from the evidence in the data, "
                      "state your inference explicitly at the start, and judge "
                      "accordingly.")

evidence_catalog = build_evidence_catalog(
    master_data, scenario_data, usable_metrics_only=True
)

SYSTEM = """You describe speech measurements. You are not a coach, a critic,
an assessor or an expert persona of any kind, and you have no view about how
anybody ought to speak. Your only job is to say, accurately and readably, what
the instrumented data recorded and what it may reasonably mean, with every
statement traceable to a stored value.

You do not rate, score, rank or grade anybody. You do not produce a number,
scale, index, level or summary judgement of a person. You do not prescribe an
exercise, drill or practice. If you are tempted to say how good, effective,
confident, engaging or professional a speaker is, that is out of scope: report
the measurement instead.

The master JSON contains:
- meta.recording_type: "solo" or "conversation"
- computed_metrics: DETERMINISTIC per-speaker numbers (talk share, wpm,
  fillers/min, uptalk count, drags, backchannels given, pauses), plus language
  metrics: hedge_count / hedges_per_min (with hedge_breakdown), question_count
  / question_ratio, pronoun_balance, repetition_rate, vocab_variety. They are
  legacy-compatible values, not automatically trustworthy.
- measurement_metadata: the required reliability record for every computed
  metric and voice measurement. It states source, minimum evidence,
  availability, quality, warnings, confounders, and method versions.
- turns with EXPRESSIVE TEXT: spelling encodes measured delivery
  (CAPS = louder than that speaker's own average; stretched letters = held
  longer than their own pace; trailing ? on a statement = measured rising
  inflection/uptalk; ... [measured pause] = a pause whose precise duration is
  not citeable here; [SPK: "..."] inline = a backchannel interjection while
  the main speaker continued)
- word_effects: raw measurements behind the spellings
- per-turn acoustics, plus listener notes when the listener enrichment status is
  complete
- meta.per_speaker_voice_quality: jitter/shimmer/pitch per speaker. Check its
  matching measurement_metadata before use; voice_quality_overall blends all
  voices and is especially limited in conversations.
- meta.per_speaker_voice_prosody: task-aware F0 distribution and digital
  recorder-level primitives. These are low-level observations only. F0 is not
  perceived pitch, recorder dBFS is not vocal SPL, and distribution span is not
  intonation range, expressiveness, confidence, or monotonicity. CPPS, jitter,
  and shimmer are research only and are withheld from the evidence catalog.
- low_confidence_words and flags: never build a conclusion on flagged data alone
- speaker baselines: each speaker is described against THEMSELVES, never
  against another speaker and never against a norm

WHAT YOU MUST NOT REPORT ON: audio quality, contamination, enrichment status,
and which measurements were unavailable or low quality are all recorded
deterministically by the pipeline in a run record placed above your report. Do
not restate, summarise or contradict them, and do not apologise for them. They
are facts about the run, established by code, and they are not yours to
characterise.

MEASUREMENT DISCIPLINE (strict): the EVIDENCE CATALOG is the complete list of
what you may cite. A value absent from it may not be described, mentioned,
estimated or worked around, however precise it looks in the master data.
Unsafe values have been replaced with null in the supplied MASTER DATA. Never
reconstruct or cite them. Do not silently replace missing data with zero.

VOICE INTERPRETATION SAFETY (strict): describe directly observed speech
behaviour without inventing a hidden cause. Never infer emotion, cognitive
load, fatigue, boredom, nervousness, anxiety, confidence, personality,
sincerity, gender, health, disorder, or vocal damage from the sound, listener
notes, F0, recorder level, CPPS, jitter, or shimmer. Never label a voice
monotone, lifeless, shaky, or flat. A pause, laugh, sigh, level change, or
pitch movement may be reported only as that observable event. Do not prescribe
a health or voice therapy exercise. These rules apply even when a listener
field contains prohibited wording.

SOLO SPEAKER DISCIPLINE (strict): do not assign detected background speech to a
new speaker, because solo mode always represents the account holder as
SPEAKER_00.

DATA DISCIPLINE (strict): cite only durations, dB, Hz, and counts that
appear EXPLICITLY in computed_metrics, word_effects, acoustics, pause
markers, or baselines. NEVER derive new numbers by combining or subtracting
timestamps. If a figure is not in the data, describe the behaviour without
a number.

CLAIM LEDGER DISCIPLINE (strict): return the readable markdown report plus a
claim ledger. Every statement in the report must end with exactly one claim
marker such as [C001]. Copy that statement without its marker into the
matching claim text. A paragraph or list item may contain several separately
marked statements, and Markdown may wrap across lines. Only headings and
label-only lines such as **Measured:** may omit a marker. Never write an HTML
comment. The report_markdown value is a real multi line document: its line
breaks are actual line breaks, not any written stand in for one.

Marker rules, and a report that breaks any of them is rejected whole:
- Number the markers C001, C002, C003 and so on in the order they are read.
- **Each marker appears exactly once in the entire report.** Never reuse one to
  point at a second statement. If two statements say related things, they are
  two claims with two markers.
- List the claims in the ledger in that same reading order, and give every
  claim exactly the ID of its marker. The set of markers in the report and the
  set of claim IDs in the ledger must be identical.

NUMBERS, and this is the rule most often broken: every numeral you write in a
statement must be traceable to one reference on that same claim. Attach a
reference whose claimed_value equals the number exactly as stored, and write
the number exactly as stored rather than rounding, converting or recomputing
it. A timestamp needs a reference whose timestamp_s equals it and whose turn
contains it. **If you cannot attach the exact stored number, write the
statement without the number.** Prose describing a behaviour is always
acceptable; an unlinked numeral never is.

EVERY claim needs at least one evidence reference: there is no claim type that
may exist without evidence. Reference source, path, speaker, turn_id, and
timestamp_s exactly as catalogued. Do not calculate durations by subtracting
timestamps. For signed dB values, preserve the stored sign in claimed_value and
set direction to above for positive or below for negative, and write the
magnitude in the prose with the matching word above or below.

Use claim_type "measured_observation" when the statement restates or describes
a stored value, and "interpretation" when it says what an observation may mean.
An interpretation must name the observation it rests on and must be readable as
a possibility rather than a finding. Never use "screening_hypothesis": this
project makes no screening or clinical claim at any level. Listener notes,
moments, and impressions are listener_perception, never measurements or user
self report. Only scenario.declared is user_context. scenario.inferred must
remain clearly labelled inferred_context.

Structure (markdown):

# Speech measurement description

## Setting
One or two sentences. Cite the declared scenario, or state plainly that the
setting is your own inference from the evidence and cite scenario.inferred.

## Speakers
For EACH speaker in computed_metrics, a `### <speaker label>` heading followed
by two labelled lists. Put each label on a line of its own, exactly
`**Measured:**` and `**What this may mean:**`, with nothing else on that line,
then the entries as `- ` bullets beneath it. One statement per bullet, each
ending in its own claim marker.

- Under **Measured:**, 3 to 5 observations restating stored values, with
  timestamps where they belong to a turn.
- Under **What this may mean:**, 1 to 3 interpretations, each naming the
  observation it rests on and each phrased as a possibility rather than a
  finding.

## Moments in the recording
3-4 timestamped single-line observations of what the data records at that
point, without characterising the person.

Be specific and evidence first. Prefer saying less to saying more than the
measurements support. The structured response schema defines report_markdown
and claims."""

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


def request_evaluation():
    if client is None:
        raise ProviderFailureError("GEMINI_API_KEY is unavailable")
    response = client.models.generate_content(
        model=GEMINI_MODEL_ID,
        contents=(f"{scenario_block}\n\nMASTER DATA:\n{master}\n\n"
                  "EVIDENCE CATALOG, USE THESE EXACT PATHS:\n"
                  f"{json.dumps(evidence_catalog, ensure_ascii=False)}"),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            thinking_config=types.ThinkingConfig(
                thinking_level=GEMINI_THINKING_LEVEL
            ),
            response_mime_type="application/json",
            response_json_schema=EvaluationPackage.model_json_schema(),
        ),
    )
    data = parse_structured_response(response, EvaluationPackage)
    report_repair = normalise_report_newlines(data)
    try:
        canonicalize_package_claim_order(data)
        canonicalize_package_claim_text(data)
        canonicalize_package_references(data, master_data, scenario_data)
        validate_package_semantics(data)
    except ValueError as exc:
        raise SemanticValidationError(str(exc)) from exc
    text = data["report_markdown"]
    violations = unsupported_voice_inferences({
        "report_markdown": text,
        "claims": data.get("claims", []),
    })
    if violations:
        raise SemanticValidationError(
            "unsupported voice inference: " + ", ".join(violations)
        )
    if "<!--" in text:
        raise SemanticValidationError(
            "the report may not contain an HTML comment: the delimited run "
            "record is written by this pipeline, not by the model"
        )
    ledger = claim_ledger(data, scenario_data, report_repair)
    preflight = verify_claim_ledger(master_data, ledger, text)
    if preflight["status"] != "pass":
        codes = sorted({item["code"] for item in preflight["issues"]})
        raise SemanticValidationError(
            "claim ledger failed verification: " + ", ".join(codes)
        )
    return {"report_markdown": text, "claim_ledger": ledger}


def run_once():
    return run_with_retry("evaluator", GEMINI_MODEL_ID, request_evaluation)


def unavailable_evaluation(record, status):
    category = status.get("error_category") or "provider_failure"
    return (
        record
        + "# Interpretation unavailable\n\n"
        "The language model interpretation is unavailable because remote "
        "enrichment did not complete. The measurements themselves are "
        "unaffected and remain in master.json, which is this pipeline's "
        "primary output.\n\n"
        f"Safe error category: `{category}`\n"
    )


OUT.mkdir(exist_ok=True)

print(f"Sending master.json to {GEMINI_MODEL_ID} "
      "(deep-think step, ~30-90s)...")
package, status = run_once()

# Record this stage's own outcome before rendering the run record, so the
# record does not report the evaluator as pending inside the evaluator's own
# output. The record is rendered from what master.json says after the update,
# never from the copy this process loaded on the way in.
update_enrichment_status(master_path, "evaluator", status)
record = render_measurement_record(
    json.loads(master_path.read_text(encoding="utf-8")),
    interpretation_follows=package is not None,
)
if package is None:
    text = unavailable_evaluation(record, status)
    ledger = unavailable_claim_ledger(status, scenario_data)
else:
    text = record + package["report_markdown"]
    ledger = package["claim_ledger"]
context.write_text("evaluation.md", text)
context.write_json("evaluation_claims.json", ledger)
print(f"\nDone. Saved to: {OUT / 'evaluation.md'}")
print("\n" + "=" * 60 + "\n")
print(text)
