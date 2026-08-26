"""
Step: the referee (DiarizationLM-style label correction).
Runs between merge and merge --rebuild. Sends the word-level speaker labels
(with confidence flags) to Gemini and asks for CONSERVATIVE corrections
based on pragmatic/semantic logic: rebuttals inside first-person narratives,
question-answer adjacency, second-person address, etc.

Hard constraints (transcript-preserving, per the research):
- words are NEVER changed, added, or removed - only speaker labels move
- edits reference word index ranges and existing speaker labels only
- spans capped at 12 words; total edited words capped at 15%
- invalid edits are discarded

Reads/writes /output/words_attributed.json (created by merge.py).
Run:  python3 pipeline/referee.py    then:  python3 pipeline/merge.py --rebuild
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
    parse_structured_response,
    run_with_retry,
    skipped_status,
    update_enrichment_status,
)
from run_context import add_run_arguments, context_from_args

REPO_ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
add_run_arguments(parser)
args = parser.parse_args()
context = context_from_args(args, REPO_ROOT)
OUT = context.output_dir
MASTER_PATH = context.output_path("master.json", required=True)

load_dotenv(REPO_ROOT / ".env")
api_key = os.getenv("GEMINI_API_KEY")

words_path = context.output_path("words_attributed.json", required=True)
words = json.loads(words_path.read_text(encoding="utf-8"))

speakers = sorted({w["speaker"] for w in words})
if len(speakers) < 2:
    update_enrichment_status(
        MASTER_PATH, "referee", skipped_status(GEMINI_MODEL_ID)
    )
    print("Solo recording - nothing to referee. Done.")
    sys.exit(0)


class RefereeEdit(BaseModel):
    """One label-only correction proposed by the referee."""

    model_config = ConfigDict(extra="forbid")

    from_i: int = Field(description="First word index in the correction span")
    to_i: int = Field(description="Last word index in the correction span")
    speaker: str = Field(description="Existing speaker label for the span")
    reason: str = Field(description="Brief pragmatic reason for the correction")


class RefereeResponse(BaseModel):
    """Structured Gemini response for conservative label corrections."""

    model_config = ConfigDict(extra="forbid")

    edits: list[RefereeEdit] = Field(
        description="Label-only corrections; an empty list is valid"
    )

# compact DiarizationLM-style representation: speaker tag on change + indices
lines = []
prev = None
for w in words:
    if w["speaker"] != prev:
        lines.append(f"\n<{w['speaker']}>")
        prev = w["speaker"]
    flag = ""
    if w["confidence"] not in ("high", "smoothed"):
        flag = "*"          # * = attribution uncertain
    if w.get("interjection_candidate"):
        flag = "!"          # ! = acoustic evidence of an interjection here
    lines.append(f"{w['i']}{flag}:{w['text']}")
compact = " ".join(lines)

PROMPT = f"""You are a speaker-attribution referee for a conversation
transcript. Below, every word has an index and a current speaker label
(words after a <SPEAKER_XX> tag belong to that speaker until the next tag).
Markers: * = the attribution of this word is acoustically uncertain,
! = there is acoustic evidence of a quick interjection by the OTHER speaker
at this word.

Your ONLY job: find word spans whose speaker label is PRAGMATICALLY wrong
and reassign them. Strong evidence looks like:
- a rebuttal or reaction inside someone else's first-person narrative
  (e.g. "He's lying." / "No." / "That's crazy" mid-story)
- a question immediately answered by the same labelled speaker
  ("...has he shown you proof? No, because we only had a..." - the answer
  belongs to the other speaker)
- second-person address that only makes sense from the other person
- the continuation of a sentence the other speaker started

BE CONSERVATIVE. Rules:
- If unsure, do NOT edit. An empty list is a good answer.
- Only reassign to one of: {speakers}
- Spans of at most 12 consecutive words
- Prefer spans containing * or ! markers, but strong pragmatic evidence
  alone is acceptable
- NEVER change any word text - labels only

Return only the correction data requested by the enforced response schema.

TRANSCRIPT:
{compact}"""

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
n = len(words)
max_edited = int(0.15 * n)


def validate_semantics(data):
    """Reject a response before mutation if any edit breaks a hard rule."""
    projected = [w["speaker"] for w in words]
    edited_count = 0
    for edit in data["edits"]:
        a, b, spk = edit["from_i"], edit["to_i"], edit["speaker"]
        if not (0 <= a <= b < n):
            raise SemanticValidationError("edit index outside transcript")
        if b - a + 1 > 12:
            raise SemanticValidationError("edit span exceeds 12 words")
        if spk not in speakers:
            raise SemanticValidationError("edit uses an unknown speaker label")
        for i in range(a, b + 1):
            if projected[i] != spk:
                projected[i] = spk
                edited_count += 1
        if edited_count > max_edited:
            raise SemanticValidationError("total edit cap exceeded")


def ask():
    if client is None:
        raise ProviderFailureError("GEMINI_API_KEY is unavailable")
    response = client.models.generate_content(
        model=GEMINI_MODEL_ID,
        contents=PROMPT,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=GEMINI_THINKING_LEVEL
            ),
            response_mime_type="application/json",
            response_json_schema=RefereeResponse.model_json_schema(),
        ),
    )
    data = parse_structured_response(response, RefereeResponse)
    validate_semantics(data)
    return data

print(f"Referee: checking {len(words)} words across {len(speakers)} speakers...")
data, status = run_with_retry("referee", GEMINI_MODEL_ID, ask)
update_enrichment_status(MASTER_PATH, "referee", status)
if data is None:
    print("Referee unavailable - continuing with original labels (safe).")
    sys.exit(0)

# ---- apply the already validated label-only corrections -----------------
original_text = [w["text"] for w in words]
edited_count = 0
applied = []
for e in data.get("edits", []):
    a, b, spk = e["from_i"], e["to_i"], e["speaker"]
    changed = False
    for i in range(a, b + 1):
        if words[i]["speaker"] != spk:
            words[i]["speaker"] = spk
            words[i]["confidence"] = "referee"
            changed = True
            edited_count += 1
    if changed:
        applied.append(e)

if [w["text"] for w in words] != original_text:
    sys.exit("ERROR: referee attempted to alter transcript text")

context.write_json("words_attributed.json", words, indent=None)

print(f"\nDone. Applied {len(applied)} edits ({edited_count} words relabelled).")
for e in applied[:8]:
    span = " ".join(w["text"] for w in words[int(e["from_i"]):int(e["to_i"]) + 1])
    print(f'  [{e["from_i"]}-{e["to_i"]}] -> {e["speaker"]}: "{span[:60]}" '
          f'({e.get("reason", "")[:60]})')
print("\nNow run: python3 pipeline/merge.py --rebuild")
