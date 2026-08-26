"""Structured interpretation claims, stable evidence references, and verification."""

import hashlib
import re
from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CLAIM_LEDGER_SCHEMA_VERSION = "1.1.0"
CLAIM_VERIFICATION_VERSION = "1.1.0"

# Schema version 1.0.0 is superseded. It carried two claim types this version
# does not. "coaching_interpretation" is renamed to "interpretation": the
# project has no coaching audience and the word described one. "prescription"
# is withdrawn rather than renamed, because it was the only claim type allowed
# to exist without evidence, and it existed so the report could tell a person
# what exercise to perform. Nothing in this version may do that, so every claim
# now requires evidence. Ledgers written under 1.0.0 remain readable records of
# what was produced then; they are not regenerated.
SUPERSEDED_CLAIM_TYPES = {
    "coaching_interpretation": "interpretation",
    "prescription": None,
}

# The pipeline writes a deterministic record above the model's report. It is
# not model output, carries no claim markers, and is excluded from claim
# checking rather than exempted from it: the text between these markers is
# rendered from master.json by code, so verifying it against master.json would
# verify the renderer against itself.
RECORD_BLOCK_START = "<!-- measurement-record -->"
RECORD_BLOCK_END = "<!-- /measurement-record -->"

ClaimType = Literal[
    "measured_observation",
    "interpretation",
    "screening_hypothesis",
]
EvidenceSource = Literal[
    "metric",
    "turn",
    "word_effect",
    "pause",
    "listener_perception",
    "user_context",
    "inferred_context",
]
Direction = Literal["none", "above", "below"]


class EvidenceReference(BaseModel):
    """One exact reference used to support an interpretation claim."""

    model_config = ConfigDict(extra="forbid")

    source: EvidenceSource
    path: str = Field(min_length=1)
    speaker: str | None = None
    turn_id: int | None = None
    timestamp_s: float | None = None
    claimed_value: float | None = None
    direction: Direction = "none"


class ClaimRecord(BaseModel):
    """One report statement and all evidence used to support it."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(pattern=r"^C\d{3}$")
    claim_type: ClaimType
    text: str = Field(min_length=1)
    speaker: str | None = None
    references: list[EvidenceReference] = Field(default_factory=list)


class EvaluationPackage(BaseModel):
    """Structured evaluator output split into human and machine products."""

    model_config = ConfigDict(extra="forbid")

    report_markdown: str = Field(min_length=1)
    claims: list[ClaimRecord] = Field(min_length=1)


def scenario_record(text, declared):
    """Return nonambiguous scenario provenance for claim verification."""
    text = text.strip()
    return {
        "source": "declared_user_context" if declared else "model_inference",
        "text": text,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def claim_ledger(package, scenario, report_repair=None):
    """Create the versioned artifact written beside evaluation.md."""
    return {
        "schema_version": CLAIM_LEDGER_SCHEMA_VERSION,
        "status": "complete",
        "scenario": scenario,
        "report_repair": report_repair,
        "claims": package["claims"],
    }


def unavailable_claim_ledger(status, scenario):
    """Keep an explicit artifact when remote evaluation is unavailable."""
    return {
        "schema_version": CLAIM_LEDGER_SCHEMA_VERSION,
        "status": "unavailable",
        "error_category": status.get("error_category") or "provider_failure",
        "scenario": scenario,
        "report_repair": None,
        "claims": [],
    }


def strip_measurement_record(report):
    """Return the model authored part of a report without the pipeline record.

    The record block is deterministic text rendered from master.json. It is
    removed before claim checking so that uncited prose written by code is
    never mistaken for uncited prose written by the model.
    """
    if RECORD_BLOCK_START not in report:
        return report
    start = report.index(RECORD_BLOCK_START)
    end = report.find(RECORD_BLOCK_END)
    if end == -1:
        return report[:start]
    return report[:start] + report[end + len(RECORD_BLOCK_END):]


# Line break placeholders seen in real provider responses, in the order they
# are tried. A structured response should carry real breaks; when it does not,
# it has carried one of these instead.
_ESCAPED_LINE_BREAKS = ("\\n", "/n")


def normalise_report_newlines(package):
    """Repair a report whose line breaks arrived as a literal placeholder.

    Seen twice on real runs on 2026-08-24, with a different placeholder each
    time: once as backslash n, once as slash n. Either way the whole markdown
    document arrives as a single line, renders as a wall of text, and still
    passes claim checking, because every marker is present and in order.

    The trigger is deliberately narrow. It fires only when the report contains
    no real line break at all, which no multi section markdown document ever
    legitimately does, and only for a placeholder that appears at least twice.
    Nothing else is rewritten, no claim text is touched, and the caller records
    that it happened rather than repairing it silently.
    """
    report = package.get("report_markdown") or ""
    if "\n" in report:
        return None
    for placeholder in _ESCAPED_LINE_BREAKS:
        if report.count(placeholder) >= 2:
            package["report_markdown"] = report.replace(placeholder, "\n")
            return (
                "The provider returned the report as a single line, with line "
                f"breaks written as the literal characters {placeholder!r}. "
                "They were restored before claim checking. No other text was "
                "changed."
            )
    return None


def report_claim_lines(report):
    """Map cited Markdown blocks to IDs and expose uncited prose."""
    report = strip_measurement_record(report)
    mapped = {}
    issues = []
    current = []
    block_start = None

    def finish_block():
        nonlocal current, block_start
        if not current:
            return
        stripped = " ".join(current)
        matches = list(re.finditer(r"\[(C\d{3})\]", stripped))
        trailing = stripped[matches[-1].end():].strip() if matches else stripped
        if (not matches
                or (trailing and not re.fullmatch(r"[*_.,;:!?)]*", trailing))):
            issues.append({
                "code": "uncited_report_line",
                "message": (f"Report block starting at line {block_start} needs "
                            "an ending claim marker for every statement."),
            })
        else:
            cursor = 0
            for match in matches:
                statement = stripped[cursor:match.start()].strip()
                if not statement:
                    issues.append({
                        "code": "uncited_report_line",
                        "message": (f"Report block starting at line {block_start} "
                                    "contains a marker without a statement."),
                    })
                else:
                    mapped[match.group(1)] = _normalise_statement(statement)
                cursor = match.end()
                punctuation = re.match(
                    r"\s*[*_.,;:!?)]*\s*", stripped[cursor:]
                )
                cursor += punctuation.end()
        current = []
        block_start = None

    for line_number, line in enumerate(report.splitlines(), 1):
        stripped = line.strip()
        has_marker = bool(re.search(r"\[C\d{3}\]", stripped))
        exempt = (not has_marker and (stripped.startswith("#")
                or re.fullmatch(r"[-*_]{3,}", stripped)
                or re.fullmatch(
                    r"[-*]?\s*(?:\*\*[^*]*:\*\*|\*\*[^*]+\*\*:)",
                    stripped,
                )))
        if not stripped or exempt:
            finish_block()
            continue
        starts_list_item = bool(re.match(r"^(?:[-*]|\d+\.)\s+", stripped))
        if starts_list_item and current:
            finish_block()
        if not current:
            block_start = line_number
        current.append(stripped)
        if re.search(r"\[C\d{3}\]$", stripped):
            finish_block()
    finish_block()
    return mapped, issues


def _normalise_statement(text):
    """Compare displayed wording without list or bold presentation syntax."""
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"^(?:[-*]|\d+\.)\s+", "", text)
    return text.replace("**", "").replace("__", "")


def canonicalize_package_claim_text(package):
    """Derive ledger wording from report markers instead of duplicated model text."""
    report_lines, issues = report_claim_lines(package["report_markdown"])
    if issues:
        raise ValueError(issues[0]["message"])
    for claim in package["claims"]:
        claim_id = claim["claim_id"]
        if claim_id in report_lines:
            claim["text"] = report_lines[claim_id]
    return package


def canonicalize_package_claim_order(package):
    """Renumber unique report claims by display order for a stable artifact."""
    report = package["report_markdown"]
    markers = re.findall(r"\[(C\d{3})\]", report)
    claim_ids = [claim["claim_id"] for claim in package["claims"]]
    if (len(markers) != len(set(markers))
            or len(claim_ids) != len(set(claim_ids))
            or set(markers) != set(claim_ids)):
        return package
    by_id = {claim["claim_id"]: claim for claim in package["claims"]}
    replacement = {
        old_id: f"C{index:03d}" for index, old_id in enumerate(markers, 1)
    }
    package["report_markdown"] = re.sub(
        r"\[(C\d{3})\]",
        lambda match: f"[{replacement[match.group(1)]}]",
        report,
    )
    ordered = []
    for old_id in markers:
        claim = by_id[old_id]
        claim["claim_id"] = replacement[old_id]
        ordered.append(claim)
    package["claims"] = ordered
    return package


def canonicalize_package_references(package, master, scenario):
    """Fill evidence ownership and timing from local data, never model copying."""
    catalog = {
        item["path"]: item for item in build_evidence_catalog(master, scenario)
    }
    for claim in package["claims"]:
        mentions = numeric_mentions(claim.get("text", ""))["timestamps"]
        for reference in claim.get("references") or []:
            item = catalog.get(reference.get("path"))
            if item is None:
                continue
            reference["source"] = item["source"]
            if "speaker" in item:
                reference["speaker"] = item.get("speaker")
            if "turn_id" in item:
                reference["turn_id"] = item.get("turn_id")
            if item.get("timestamp_s") is not None:
                reference["timestamp_s"] = item["timestamp_s"]
        for timestamp in mentions:
            if any(
                reference.get("timestamp_s") is not None
                and _close(timestamp, reference["timestamp_s"])
                for reference in claim.get("references") or []
            ):
                continue
            for reference in claim.get("references") or []:
                turn_id = reference.get("turn_id")
                turn = _turn_by_id(master, turn_id) if turn_id is not None else None
                if (turn and turn.get("start_s", float("inf")) <= timestamp
                        <= turn.get("end_s", float("-inf"))):
                    reference["timestamp_s"] = timestamp
                    break
    return package


def validate_package_semantics(package):
    """Require report markers, unique IDs, and evidence for factual claims."""
    report = package["report_markdown"]
    claims = package["claims"]
    ids = [claim["claim_id"] for claim in claims]
    if len(ids) != len(set(ids)):
        raise ValueError("claim IDs must be unique")
    expected_ids = [f"C{index:03d}" for index in range(1, len(ids) + 1)]
    if ids != expected_ids:
        raise ValueError("claim IDs must be sequential from C001")
    ledger_ids = set(ids)
    report_ids = set(re.findall(r"\[(C\d{3})\]", report))
    if report_ids != ledger_ids:
        raise ValueError("report claim markers do not match the claim ledger")
    if re.findall(r"\[(C\d{3})\]", report) != ids:
        raise ValueError("report claim markers must follow ledger order")
    report_lines, line_issues = report_claim_lines(report)
    if line_issues:
        raise ValueError(line_issues[0]["message"])
    for claim in claims:
        if (report_lines.get(claim["claim_id"])
                != _normalise_statement(claim["text"])):
            raise ValueError(
                f"claim {claim['claim_id']} text does not match its report line"
            )
        if not claim.get("references"):
            raise ValueError(
                f"claim {claim['claim_id']} requires evidence references"
            )


def _get_nested(value, tokens):
    for token in tokens:
        if isinstance(value, dict):
            if token not in value:
                raise KeyError(token)
            value = value[token]
        elif isinstance(value, list):
            try:
                value = value[int(token)]
            except (ValueError, IndexError) as exc:
                raise KeyError(token) from exc
        else:
            raise KeyError(token)
    return value


def _turn_by_id(master, turn_id):
    return next(
        (turn for turn in master.get("turns", [])
         if turn.get("turn_id") == turn_id),
        None,
    )


def resolve_reference(master, scenario, reference):
    """Resolve one supported stable path and return its value and ownership."""
    path = reference["path"]
    tokens = path.split(".")
    if not tokens:
        raise KeyError(path)
    turn = None
    owner = None
    if tokens[0] == "turns_by_id":
        if len(tokens) < 2:
            raise KeyError(path)
        try:
            turn_id = int(tokens[1])
        except ValueError as exc:
            raise KeyError(path) from exc
        turn = _turn_by_id(master, turn_id)
        if turn is None:
            raise KeyError(path)
        owner = turn.get("speaker")
        value = _get_nested(turn, tokens[2:])
        if len(tokens) >= 4 and tokens[2] == "word_effects":
            effect = _get_nested(turn, tokens[2:4])
            if isinstance(effect, dict) and effect.get("speaker"):
                owner = effect["speaker"]
    elif tokens[0] == "scenario":
        expected = ("declared" if scenario.get("source") == "declared_user_context"
                    else "inferred")
        if len(tokens) != 2 or tokens[1] != expected:
            raise KeyError(path)
        value = scenario.get("text")
    else:
        value = _get_nested(master, tokens)
        if tokens[0] == "computed_metrics" and len(tokens) >= 2:
            owner = tokens[1]
        elif (tokens[0:2] == ["meta", "per_speaker_voice_quality"]
              and len(tokens) >= 3):
            owner = tokens[2]
        elif (tokens[0:2] == ["meta", "per_speaker_voice_prosody"]
              and len(tokens) >= 3):
            owner = tokens[2]
        elif tokens[0] == "speaker_overall_impressions" and len(tokens) >= 2:
            owner = tokens[1]
        elif tokens[0] in {"notable_moments", "listener_contradictions"}:
            item = _get_nested(master, tokens[:2])
            if isinstance(item, dict) and item.get("turn_id") is not None:
                turn = _turn_by_id(master, item["turn_id"])
                owner = turn.get("speaker") if turn else None
    return {"value": value, "owner": owner, "turn": turn}


def measurement_metadata_index(master):
    """Index measurement reliability records by their exact value path."""
    metadata = master.get("measurement_metadata") or {}
    result = {}
    for sections in (metadata.get("speakers") or {}).values():
        for entries in sections.values():
            for evidence in entries.values():
                if isinstance(evidence, dict) and evidence.get("value_path"):
                    result[evidence["value_path"]] = evidence
    for evidence in (metadata.get("overall_voice_quality") or {}).values():
        if isinstance(evidence, dict) and evidence.get("value_path"):
            result[evidence["value_path"]] = evidence
    return result


def build_evidence_catalog(master, scenario, *, usable_metrics_only=False):
    """Give the evaluator exact citeable paths instead of asking it to guess."""
    catalog = []
    metadata = measurement_metadata_index(master)
    for path, evidence in metadata.items():
        availability = evidence.get("availability", {}).get("status")
        quality = evidence.get("quality", {}).get("category")
        release_limit = (evidence.get("validation", {})
                          .get("release_limits", {})
                          .get("released_interpretation"))
        if (usable_metrics_only
                and (availability != "available"
                     or quality in {"low", "unavailable"}
                     or release_limit == "blocked")):
            continue
        try:
            value = _get_nested(master, path.split("."))
        except KeyError:
            value = None
        owner = path.split(".")[1] if path.startswith("computed_metrics.") else None
        if path.startswith("meta.per_speaker_voice_quality."):
            owner = path.split(".")[2]
        if path.startswith("meta.per_speaker_voice_prosody."):
            owner = path.split(".")[2]
        catalog.append({
            "source": "metric",
            "path": path,
            "speaker": owner,
            "value": value,
            "availability": availability,
            "quality": quality,
        })
    for turn in master.get("turns", []):
        turn_id = turn.get("turn_id")
        speaker = turn.get("speaker")
        base = f"turns_by_id.{turn_id}"
        catalog.append({
            "source": "turn", "path": f"{base}.expressive_text",
            "speaker": speaker, "turn_id": turn_id,
            "start_s": turn.get("start_s"), "end_s": turn.get("end_s"),
        })
        for field in ("start_s", "end_s"):
            catalog.append({
                "source": "turn", "path": f"{base}.{field}",
                "speaker": speaker, "turn_id": turn_id,
                "timestamp_s": turn.get(field), "value": turn.get(field),
            })
        if turn.get("pause_before_s") is not None:
            catalog.append({
                "source": "pause", "path": f"{base}.pause_before_s",
                "speaker": speaker, "turn_id": turn_id,
                "value": turn["pause_before_s"],
            })
        for field, value in (turn.get("acoustics") or {}).items():
            catalog.append({
                "source": "metric", "path": f"{base}.acoustics.{field}",
                "speaker": speaker, "turn_id": turn_id, "value": value,
            })
        for index, effect in enumerate(turn.get("word_effects") or []):
            effect_speaker = effect.get("speaker") or speaker
            for field, value in effect.items():
                if field in {"word", "speaker"}:
                    continue
                catalog.append({
                    "source": "word_effect",
                    "path": f"{base}.word_effects.{index}.{field}",
                    "speaker": effect_speaker, "turn_id": turn_id,
                    "timestamp_s": effect.get("t"), "value": value,
                })
        if turn.get("listener_note"):
            catalog.append({
                "source": "listener_perception",
                "path": f"{base}.listener_note", "speaker": speaker,
                "turn_id": turn_id,
            })
    for index, moment in enumerate(master.get("notable_moments") or []):
        turn = _turn_by_id(master, moment.get("turn_id"))
        catalog.append({
            "source": "listener_perception",
            "path": f"notable_moments.{index}.observation",
            "speaker": turn.get("speaker") if turn else None,
            "turn_id": moment.get("turn_id"),
            "timestamp_s": moment.get("t_s"),
        })
    for index, contradiction in enumerate(
        master.get("listener_contradictions") or []
    ):
        turn = _turn_by_id(master, contradiction.get("turn_id"))
        for field in ("data_says", "audio_says", "evidence"):
            if contradiction.get(field):
                catalog.append({
                    "source": "listener_perception",
                    "path": f"listener_contradictions.{index}.{field}",
                    "speaker": turn.get("speaker") if turn else None,
                    "turn_id": contradiction.get("turn_id"),
                })
    for speaker in (master.get("speaker_overall_impressions") or {}):
        catalog.append({
            "source": "listener_perception",
            "path": f"speaker_overall_impressions.{speaker}",
            "speaker": speaker,
        })
    scenario_kind = ("user_context" if scenario.get("source") == "declared_user_context"
                     else "inferred_context")
    scenario_path = ("scenario.declared" if scenario_kind == "user_context"
                     else "scenario.inferred")
    catalog.append({"source": scenario_kind, "path": scenario_path})
    return catalog


def withheld_measurements(master):
    """List every measurement the evaluator was not allowed to use, and why."""
    withheld = []
    for path, evidence in sorted(measurement_metadata_index(master).items()):
        availability = evidence.get("availability", {}).get("status")
        quality = evidence.get("quality", {}).get("category")
        release_limit = (evidence.get("validation", {})
                         .get("release_limits", {})
                         .get("released_interpretation"))
        if (availability == "available"
                and quality not in {"low", "unavailable"}
                and release_limit != "blocked"):
            continue
        if availability != "available":
            reason = f"availability {availability or 'unknown'}"
        elif quality in {"low", "unavailable"}:
            reason = f"{quality} measurement quality"
        else:
            reason = "released interpretation blocked for this measurement"
        withheld.append({"path": path, "reason": reason})
    return withheld


def render_measurement_record(master, interpretation_follows=True):
    """Render the deterministic conditions block that opens evaluation.md.

    Written by code from master.json rather than by the model, because
    availability, audio quality and enrichment outcome are facts about the run
    and not something an interpretation layer should be asked to report on
    itself. It is delimited so claim checking can exclude it.
    """
    meta = master.get("meta") or {}
    lines = [RECORD_BLOCK_START, "", "## Run record", ""]
    lines.append(
        "*Written by the pipeline from `master.json`, not by the model. "
        "It carries no claim markers and is not part of what the verifier "
        "checks.*"
    )
    lines.append("")
    duration = meta.get("audio_duration_s")
    lines.append(
        f"- Recording: {meta.get('recording_type') or 'unknown'}, "
        + (f"{duration:.1f} s, " if isinstance(duration, (int, float)) else "")
        + f"{meta.get('num_speakers')} speaker(s)"
    )
    quality = meta.get("audio_quality") or {}
    lines.append(
        f"- Audio quality: {quality.get('overall_status') or 'unknown'} "
        f"(decision: {quality.get('decision') or 'unknown'}, "
        f"policy: {quality.get('policy') or 'unknown'})"
    )
    for check in quality.get("checks") or []:
        if check.get("status") == "pass":
            continue
        affects = ", ".join(check.get("affects") or []) or "nothing recorded"
        lines.append(
            f"  - {str(check.get('status')).upper()} {check.get('id')}: "
            f"{check.get('reason')} Affects: {affects}."
        )
    contamination = meta.get("contamination")
    if isinstance(contamination, dict):
        lines.append(
            f"- Second voice check: {contamination.get('status')}"
            + (f". {contamination['reason']}"
               if contamination.get("reason") else "")
        )
    statuses = meta.get("enrichment_status") or {}
    rendered = ", ".join(
        f"{name} {(value or {}).get('status')}"
        + (f" ({value['error_category']})"
           if (value or {}).get("error_category") else "")
        for name, value in sorted(statuses.items())
    )
    lines.append(f"- Enrichment: {rendered or 'none recorded'}")
    withheld = withheld_measurements(master)
    lines.append(
        f"- Measurements withheld from the interpretation: {len(withheld)}"
    )
    for item in withheld:
        lines.append(f"  - `{item['path']}`: {item['reason']}")
    if interpretation_follows:
        lines.extend([
            "",
            "The interpretation below describes measurements. It is not a "
            "measurement, it is not a screening or clinical statement, and it "
            "does not rate the speaker.",
        ])
    lines.extend(["", RECORD_BLOCK_END, ""])
    return "\n".join(lines)


def evaluation_model_input(master):
    """Hide unusable legacy values from the evaluator without altering evidence."""
    result = deepcopy(master)
    excluded = []
    for path, evidence in measurement_metadata_index(master).items():
        availability = evidence.get("availability", {}).get("status")
        quality = evidence.get("quality", {}).get("category")
        release_limit = (evidence.get("validation", {})
                          .get("release_limits", {})
                          .get("released_interpretation"))
        if (availability == "available"
                and quality not in {"low", "unavailable"}
                and release_limit != "blocked"):
            continue
        tokens = path.split(".")
        parent = result
        try:
            for token in tokens[:-1]:
                parent = (parent[int(token)] if isinstance(parent, list)
                          else parent[token])
            final = tokens[-1]
            if isinstance(parent, list):
                parent[int(final)] = None
            elif final in parent:
                parent[final] = None
            excluded.append({
                "path": path,
                "availability": availability,
                "quality": quality,
                "released_interpretation": release_limit,
            })
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    result.setdefault("meta", {})[
        "measurements_excluded_from_evaluation"
    ] = excluded
    for turn in result.get("turns", []):
        text = turn.get("expressive_text")
        if isinstance(text, str):
            turn["expressive_text"] = re.sub(
                r"\.\.\. \[\d+(?:\.\d+)?s\]", "... [measured pause]", text
            )
    return result


_TIMESTAMP_PATTERNS = [
    re.compile(
        r"(?:at|around)\s+(\d+(?:\.\d+)?)\s*(?:s|seconds?)\b", re.I
    ),
    re.compile(r"(\d+(?:\.\d+)?)\s*s\s+mark\b", re.I),
    re.compile(r"t\s*=\s*(\d+(?:\.\d+)?)", re.I),
]
_DATA_PATTERNS = [
    (re.compile(r"([+-]?\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b", re.I),
     "seconds"),
    (re.compile(r"([+-]?\d+(?:\.\d+)?)\s*dB\b", re.I), "dB"),
    (re.compile(r"([+-]?\d+(?:\.\d+)?)\s*Hz\b", re.I), "Hz"),
    (re.compile(r"([+-]?\d+(?:\.\d+)?)\s*(?:words?\s*(?:/|per)\s*min|wpm)\b", re.I),
     "per_minute"),
    (re.compile(r"([+-]?\d+(?:\.\d+)?)\s*(?:fillers?|uptalks?|hedges?)\s*(?:/|per)\s*min", re.I),
     "per_minute"),
    (re.compile(r"([+-]?\d+(?:\.\d+)?)\s*%"), "percent"),
]


def numeric_mentions(text):
    """Extract direct data values separately from timestamp references."""
    timestamps = []
    timestamp_spans = []
    for pattern in _TIMESTAMP_PATTERNS:
        for match in pattern.finditer(text):
            timestamps.append(float(match.group(1)))
            timestamp_spans.append(match.span(1))
    values = []
    for pattern, kind in _DATA_PATTERNS:
        for match in pattern.finditer(text):
            if any(start <= match.start(1) < end for start, end in timestamp_spans):
                continue
            raw_value = match.group(1)
            values.append({
                "value": float(raw_value),
                "kind": kind,
                "explicit_sign": raw_value.startswith(("+", "-")),
            })
    return {"timestamps": timestamps, "values": values}


def _close(left, right, tolerance=0.06):
    return abs(float(left) - float(right)) <= tolerance


def verify_claim_ledger(master, ledger, report_markdown):
    """Verify every claim and reference without trusting the evaluator."""
    scenario = ledger.get("scenario") or {}
    metadata = measurement_metadata_index(master)
    catalog_index = {
        item["path"]: item
        for item in build_evidence_catalog(master, scenario)
    }
    measurement_quality = {category: 0 for category in
                           ("high", "moderate", "low", "unavailable", "unrated")}
    issues = []
    claim_results = []
    report_lines, report_line_issues = report_claim_lines(report_markdown)
    issues.extend(report_line_issues)
    report_markers = re.findall(r"\[(C\d{3})\]", report_markdown)
    ledger_ids = [claim.get("claim_id") for claim in ledger.get("claims") or []]
    if len(report_markers) != len(set(report_markers)):
        issues.append({"code": "duplicate_report_marker",
                       "message": "A claim marker appears more than once."})
    if set(report_markers) != set(ledger_ids):
        issues.append({"code": "claim_marker_mismatch",
                       "message": "Report markers and ledger claim IDs differ."})
    if len(ledger_ids) != len(set(ledger_ids)):
        issues.append({"code": "duplicate_claim_id",
                       "message": "A claim ID appears more than once."})

    for claim in ledger.get("claims") or []:
        claim_id = claim.get("claim_id")
        claim_issues = []
        if (report_lines.get(claim_id)
                != _normalise_statement(claim.get("text", ""))):
            claim_issues.append({"code": "claim_text_missing",
                                 "message": "Claim text does not match its report line."})
        if claim.get("claim_type") == "screening_hypothesis":
            claim_issues.append({
                "code": "claim_level_not_authorized",
                "message": "This project makes no screening claim at any level.",
            })
        references = claim.get("references") or []
        if not references:
            claim_issues.append({"code": "missing_evidence",
                                 "message": "A claim has no evidence."})
        resolved_refs = []
        for index, reference in enumerate(references):
            prefix = f"reference {index + 1}"
            try:
                resolved = resolve_reference(master, scenario, reference)
            except (KeyError, TypeError):
                claim_issues.append({
                    "code": "reference_not_found",
                    "message": f"{prefix} path does not exist: {reference.get('path')}",
                })
                continue
            resolved_refs.append((reference, resolved))
            catalogued = catalog_index.get(reference.get("path"))
            if (catalogued is None
                    or catalogued.get("source") != reference.get("source")):
                claim_issues.append({
                    "code": "evidence_source_mismatch",
                    "message": (f"{prefix} source does not match the approved "
                                "catalog for this path."),
                })
            elif (catalogued.get("speaker") is not None
                  and reference.get("speaker") != catalogued.get("speaker")):
                claim_issues.append({
                    "code": "wrong_speaker",
                    "message": f"{prefix} speaker does not match the catalog.",
                })
            if (catalogued is not None and catalogued.get("turn_id") is not None
                    and reference.get("turn_id") != catalogued.get("turn_id")):
                claim_issues.append({
                    "code": "turn_mismatch",
                    "message": f"{prefix} turn does not match the catalog.",
                })
            if (catalogued is not None
                    and catalogued.get("timestamp_s") is not None
                    and (reference.get("timestamp_s") is None
                         or not _close(reference["timestamp_s"],
                                       catalogued["timestamp_s"]))):
                claim_issues.append({
                    "code": "timestamp_mismatch",
                    "message": f"{prefix} timestamp does not match the catalog.",
                })
            owner = resolved.get("owner")
            declared_speaker = reference.get("speaker")
            claim_speaker = claim.get("speaker")
            if declared_speaker and owner and declared_speaker != owner:
                claim_issues.append({
                    "code": "wrong_speaker",
                    "message": f"{prefix} belongs to {owner}, not {declared_speaker}.",
                })
            if claim_speaker and owner and claim_speaker != owner:
                claim_issues.append({
                    "code": "wrong_speaker",
                    "message": f"Claim speaker {claim_speaker} does not own {prefix}.",
                })
            turn = resolved.get("turn")
            if reference.get("turn_id") is not None:
                if turn is None or turn.get("turn_id") != reference["turn_id"]:
                    claim_issues.append({
                        "code": "turn_mismatch",
                        "message": f"{prefix} does not belong to turn {reference['turn_id']}.",
                    })
            timestamp = reference.get("timestamp_s")
            if timestamp is not None and turn is not None:
                if not (turn.get("start_s", float("inf")) <= timestamp
                        <= turn.get("end_s", float("-inf"))):
                    claim_issues.append({
                        "code": "timestamp_outside_turn",
                        "message": f"{prefix} timestamp is outside its turn.",
                    })
            path = reference.get("path")
            if reference.get("source") == "metric" and path in metadata:
                measurement = metadata[path]
                availability = measurement.get("availability", {}).get("status")
                quality = measurement.get("quality", {}).get("category")
                measurement_quality[quality if quality in measurement_quality
                                    else "unrated"] += 1
                if availability != "available":
                    claim_issues.append({
                        "code": "measurement_unavailable",
                        "message": f"{prefix} cites an unavailable measurement.",
                    })
                elif quality in {"low", "unavailable"}:
                    claim_issues.append({
                        "code": "measurement_low_quality",
                        "message": f"{prefix} cites a {quality} quality measurement.",
                    })
            elif reference.get("source") == "metric":
                measurement_quality["unrated"] += 1
            source = reference.get("source")
            if source == "listener_perception":
                listener_status = (master.get("meta", {})
                                   .get("enrichment_status", {})
                                   .get("listener", {}).get("status"))
                if listener_status != "complete":
                    claim_issues.append({
                        "code": "listener_evidence_unavailable",
                        "message": f"{prefix} cites unavailable listener perception.",
                    })
            if source == "user_context" and not path.startswith("scenario.declared"):
                claim_issues.append({
                    "code": "evidence_source_mismatch",
                    "message": "User context must cite declared scenario evidence.",
                })
            if source == "inferred_context" and not path.startswith("scenario.inferred"):
                claim_issues.append({
                    "code": "evidence_source_mismatch",
                    "message": "Inferred context must remain labelled as inference.",
                })
            claimed_value = reference.get("claimed_value")
            if claimed_value is not None:
                actual = resolved.get("value")
                if (not isinstance(actual, (int, float))
                        or isinstance(actual, bool)
                        or not _close(claimed_value, actual)):
                    claim_issues.append({
                        "code": "numeric_value_mismatch",
                        "message": f"{prefix} claimed value does not equal its source.",
                    })
            direction = reference.get("direction", "none")
            relative_db_path = any(
                token in (path or "").lower()
                for token in ("vs_own_avg_db", "above_avg_db", "below_avg_db")
            )
            if (relative_db_path and isinstance(resolved.get("value"), (int, float))
                    and resolved.get("value") != 0 and direction == "none"):
                claim_issues.append({
                    "code": "missing_direction",
                    "message": f"{prefix} must state the direction of relative dB.",
                })
            if direction != "none":
                actual = resolved.get("value")
                correct_sign = (isinstance(actual, (int, float))
                                and not isinstance(actual, bool)
                                and (actual > 0 if direction == "above" else actual < 0))
                if not correct_sign:
                    claim_issues.append({
                        "code": "wrong_direction",
                        "message": f"{prefix} has the wrong sign for {direction}.",
                    })

        mentions = numeric_mentions(claim.get("text", ""))
        for timestamp in mentions["timestamps"]:
            if not any(
                reference.get("timestamp_s") is not None
                and _close(timestamp, reference["timestamp_s"])
                for reference, _ in resolved_refs
            ):
                claim_issues.append({
                    "code": "timestamp_without_reference",
                    "message": f"Timestamp {timestamp} has no matching reference.",
                })
        for mention in mentions["values"]:
            if not any(
                reference.get("claimed_value") is not None
                and (
                    _close(mention["value"], reference["claimed_value"])
                    or (
                        not mention["explicit_sign"]
                        and reference.get("direction") in {"above", "below"}
                        and _close(
                            mention["value"],
                            abs(reference["claimed_value"]),
                        )
                    )
                )
                for reference, _ in resolved_refs
            ):
                claim_issues.append({
                    "code": "numeric_claim_without_direct_value",
                    "message": (f"{mention['value']} {mention['kind']} is not "
                                "linked to one directly stored value."),
                })
        text_direction = None
        if re.search(r"\bdB\s+above\b", claim.get("text", ""), re.I):
            text_direction = "above"
        elif re.search(r"\bdB\s+below\b", claim.get("text", ""), re.I):
            text_direction = "below"
        if text_direction and not any(
            reference.get("direction") == text_direction
            for reference, _ in resolved_refs
        ):
            claim_issues.append({
                "code": "direction_text_mismatch",
                "message": "The report direction is not represented by its evidence.",
            })
        claim_results.append({
            "claim_id": claim_id,
            "status": "pass" if not claim_issues else "fail",
            "issues": claim_issues,
        })

    issues.extend(
        {**issue, "claim_id": result["claim_id"]}
        for result in claim_results for issue in result["issues"]
    )
    reference_count = sum(
        len(claim.get("references") or []) for claim in ledger.get("claims") or []
    )
    return {
        "schema_version": CLAIM_VERIFICATION_VERSION,
        "status": "pass" if not issues else "fail",
        "summary": {
            "claims": len(ledger.get("claims") or []),
            "claims_passed": sum(result["status"] == "pass"
                                 for result in claim_results),
            "references": reference_count,
            "issues": len(issues),
            "measurement_references_by_quality": measurement_quality,
        },
        "claims": claim_results,
        "issues": issues,
    }
