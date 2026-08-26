"""Shared retry, failure classification, and status helpers for LLM stages."""

import json
import threading
import time
from pathlib import Path

import httpx
import requests
from pydantic import ValidationError

from pipeline_config import ENRICHMENT_ATTEMPT_DEADLINE_S, GEMINI_MODEL_ID
from run_context import atomic_write_json

MAX_ATTEMPTS = 2


class EmptyResponseError(Exception):
    """The provider returned no usable content."""


class SchemaFailureError(Exception):
    """The response did not conform to its declared schema."""


class SemanticValidationError(Exception):
    """The response was shaped correctly but referred to invalid data."""


class ProviderFailureError(Exception):
    """Local configuration prevented a provider request."""


class EnrichmentTimeoutError(TimeoutError):
    """One enrichment attempt outlived its wall clock deadline."""


def status_record(status, attempts, model_id, error_category=None):
    """Build the stable, safe status shape stored in master.json."""
    return {
        "status": status,
        "attempts": attempts,
        "model_id": model_id,
        "error_category": error_category,
    }


def pending_status(model_id=GEMINI_MODEL_ID):
    return status_record("pending", 0, model_id)


def skipped_status(model_id=GEMINI_MODEL_ID):
    return status_record("skipped", 0, model_id)


def not_requested_status(model_id=GEMINI_MODEL_ID):
    """The stage was never asked for, which is not the same as waiting."""
    return status_record("not_requested", 0, model_id)


def initial_enrichment_status():
    """Return fresh status records so earlier run state cannot leak in.

    The interpretation layer is opt in, so the listener and the evaluator
    start as not requested rather than pending. A default run never calls
    them, and a record left saying "pending" would describe a stage that is
    about to happen when in fact none was ever asked for. Each stage sets
    itself pending when it actually starts.
    """
    return {
        "referee": pending_status(),
        "listener": not_requested_status(),
        "evaluator": not_requested_status(),
    }


def classify_failure(exc):
    """Map an exception to one non-sensitive operational category."""
    if isinstance(exc, EmptyResponseError):
        return "empty_response"
    if isinstance(exc, SchemaFailureError) or isinstance(exc, ValidationError):
        return "schema_failure"
    if isinstance(exc, SemanticValidationError):
        return "semantic_validation_failure"
    if isinstance(exc, ProviderFailureError):
        return "provider_failure"

    code = getattr(exc, "code", None)
    message = str(exc).upper()
    if code == 429 or "RESOURCE_EXHAUSTED" in message:
        return "quota_exhaustion"
    if isinstance(exc, (TimeoutError, httpx.TimeoutException,
                        requests.exceptions.Timeout)):
        return "timeout"
    return "provider_failure"


def call_with_deadline(request, deadline_s=ENRICHMENT_ATTEMPT_DEADLINE_S):
    """Run one request and give up on it after a deadline.

    A hung request is the failure this exists for. Without a deadline it never
    raises, so it never reaches ``classify_failure``, the documented degrade
    never fires, and the stage blocks the run instead of failing it.

    The worker runs as a daemon thread because a stuck provider call cannot be
    interrupted from outside. Waiting stops at the deadline and the interpreter
    can still exit even if the call never returns. The provider client carries
    its own shorter timeout, so in practice it aborts first and this stays a
    backstop for whatever the client cannot see.

    The deadline counts elapsed awake time, not time on the wall: it is a
    monotonic wait, and a system sleep suspends the whole process anyway. On a
    laptop that takes maintenance sleeps, a stage's reported wall clock duration
    can therefore be much larger than the deadline that governed it, which is a
    property of the machine rather than a failure of this bound. Run real
    recordings under ``caffeinate`` and the two agree.
    """
    if not deadline_s:
        return request()

    outcome = {}

    def worker():
        try:
            outcome["value"] = request()
        except BaseException as exc:  # noqa: BLE001 - re-raised on the caller
            outcome["error"] = exc

    thread = threading.Thread(target=worker, daemon=True, name="enrichment")
    thread.start()
    thread.join(deadline_s)
    if thread.is_alive():
        raise EnrichmentTimeoutError(
            f"no response within {deadline_s:.0f}s"
        )
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


def run_with_retry(stage, model_id, request,
                   deadline_s=ENRICHMENT_ATTEMPT_DEADLINE_S):
    """Run an LLM request once, retry once, then return explicit status."""
    last_category = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        began = time.monotonic()
        try:
            value = call_with_deadline(request, deadline_s)
        except Exception as exc:  # noqa: BLE001 - classification is the boundary
            last_category = classify_failure(exc)
            action = "retrying" if attempt < MAX_ATTEMPTS else "degrading"
            safe_detail = (
                f": {exc}" if isinstance(exc, SemanticValidationError) else ""
            )
            # The elapsed time is reported because a deadline nobody can see
            # working is a deadline nobody can tell has stopped working.
            print(f"  {stage} attempt {attempt}: {last_category} ({action}) "
                  f"after {time.monotonic() - began:.1f}s{safe_detail}")
            continue
        return value, status_record("complete", attempt, model_id)
    return None, status_record("unavailable", MAX_ATTEMPTS, model_id,
                               last_category)


def parse_structured_response(response, model_type):
    """Distinguish empty provider output from schema parsing failure."""
    raw = response.text
    if raw is None or not raw.strip():
        raise EmptyResponseError("provider returned no text")
    if response.parsed is None:
        raise SchemaFailureError("provider output did not parse")
    try:
        return model_type.model_validate(response.parsed).model_dump()
    except ValidationError as exc:
        raise SchemaFailureError("provider output failed schema validation") from exc


def require_text_response(response):
    """Return nonempty evaluator text or raise the typed empty failure."""
    text = response.text
    if text is None or not text.strip():
        raise EmptyResponseError("provider returned no text")
    return text


def update_enrichment_status(master_path, stage, status):
    """Update one stage status without disturbing measurements or peers."""
    master_path = Path(master_path)
    master = json.loads(master_path.read_text(encoding="utf-8"))
    enrichment = master.setdefault("meta", {}).setdefault(
        "enrichment_status", initial_enrichment_status()
    )
    enrichment[stage] = status
    atomic_write_json(master_path, master)
