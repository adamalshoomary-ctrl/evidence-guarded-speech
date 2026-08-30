"""Prepare the frozen private checkpoint 22D benchmark without held-out clips."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import tarfile
import wave
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from .benchmark import (
    BENCHMARK_SCHEMA_VERSION,
    PRIVATE_BENCHMARK_ROOT,
    canonical_json_sha256,
    load_benchmark_contract,
    load_phone_map,
    validate_private_benchmark_manifest,
)
from .corpus_manifest import load_registered_manifests, validate_private_evidence
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, deterministic_key, file_sha256


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
CORPUS_ROOT = PRIVATE_ROOT / "corpora"
AUDIT_ROOT = PRIVATE_ROOT / "audit"
SPLIT_ROOT = PRIVATE_ROOT / "splits"
BENCHMARK_ROOT = PRIVATE_BENCHMARK_ROOT / "v1"
MANIFEST_PATH = PRIVATE_BENCHMARK_ROOT / "benchmark-manifest-v1.0.0.json"
# Resolved from PATH so this runs on Linux and Windows too. It was
# hardcoded to a macOS Homebrew path, which no other machine has.
FFMPEG_DEFAULT = Path(shutil.which("ffmpeg") or "ffmpeg")


class BenchmarkPreparationError(ValueError):
    """Raised when source data cannot satisfy the frozen benchmark selection."""


def _stable_key(scope, identifier):
    return deterministic_key(f"speech_sound_patterns_benchmark_v1:{scope}", identifier)


def _selected_participants(assignments, split, count, stratum=None):
    eligible = [
        participant
        for participant, item in assignments.items()
        if item["project_split"] == split
        and (stratum is None or item["source_stratum"] == stratum)
    ]
    if len(eligible) < count:
        raise BenchmarkPreparationError(
            f"not enough {split} participants for stratum {stratum}"
        )
    return sorted(
        eligible,
        key=lambda item: (_stable_key(f"{split}:{stratum}", item), item),
    )[:count]


def _load_assignments(filename):
    return json.loads((SPLIT_ROOT / filename).read_text(encoding="utf-8"))[
        "assignments"
    ]


def _safe_write(path, payload):
    path = Path(path).resolve(strict=False)
    path.relative_to(PRIVATE_BENCHMARK_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _scan_object_end(text, start):
    if start >= len(text) or text[start] != "{":
        raise BenchmarkPreparationError("selected source record is not an object")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        character = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    raise BenchmarkPreparationError("source JSON object is truncated")


def _selected_top_level_objects(path, selected_prefixes):
    """Decode only selected participant records from a top-level JSON object."""
    text = Path(path).read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    position = 0
    while position < len(text) and text[position].isspace():
        position += 1
    if position >= len(text) or text[position] != "{":
        raise BenchmarkPreparationError(f"{path} is not a JSON object")
    position += 1
    selected = {}
    while True:
        while position < len(text) and (text[position].isspace() or text[position] == ","):
            position += 1
        if position < len(text) and text[position] == "}":
            break
        key, position = decoder.raw_decode(text, position)
        while position < len(text) and text[position].isspace():
            position += 1
        if position >= len(text) or text[position] != ":":
            raise BenchmarkPreparationError(f"{path} has malformed object syntax")
        position += 1
        while position < len(text) and text[position].isspace():
            position += 1
        end = _scan_object_end(text, position)
        if any(key.startswith(prefix) for prefix in selected_prefixes):
            selected[key] = json.loads(text[position:end])
        position = end
    return selected


def _stream_tar_members(archive_path, wanted, handler):
    """Pass each wanted archive member to ``handler`` in one streaming pass.

    The powered checkpoint 22E4B sample reads thousands of clips, so the caller
    consumes each payload as it arrives instead of holding every one in memory.
    """
    remaining = set(wanted)
    with tarfile.open(archive_path, "r|gz") as archive:
        for member in archive:
            if member.name not in remaining:
                continue
            if not member.isfile():
                raise BenchmarkPreparationError(
                    f"archive member is not a file: {member.name}"
                )
            handle = archive.extractfile(member)
            if handle is None:
                raise BenchmarkPreparationError(
                    f"archive member cannot be read: {member.name}"
                )
            handler(member.name, handle.read())
            remaining.remove(member.name)
            if not remaining:
                break
    if remaining:
        sample = sorted(remaining)[:5]
        raise BenchmarkPreparationError(
            f"archive is missing {len(remaining)} selected members: {sample}"
        )


def _extract_tar_members(archive_path, wanted):
    results = {}

    def collect(name, payload):
        results[name] = payload

    _stream_tar_members(archive_path, set(wanted), collect)
    return results


def _canonicalize_audio(payload, source_suffix, target_path, ffmpeg):
    target_path = Path(target_path)
    source_path = target_path.with_suffix(source_suffix)
    _safe_write(source_path, payload)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(target_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    source_path.unlink()
    with wave.open(str(target_path), "rb") as handle:
        channels = handle.getnchannels()
        sample_rate = handle.getframerate()
        frames = handle.getnframes()
    duration = frames / sample_rate
    if channels != 1 or sample_rate != 16000 or not 0 < duration <= 30:
        raise BenchmarkPreparationError(
            f"canonical audio is outside the benchmark contract: {target_path}"
        )
    return {
        "canonical_audio_path": target_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "canonical_audio_sha256": file_sha256(target_path),
        "duration_s": round(duration, 6),
    }


def _write_text(safe_id, text, root=None):
    root = BENCHMARK_ROOT if root is None else Path(root)
    path = root / "clips" / safe_id / f"{safe_id}.lab"
    normalized = " ".join(text.strip().split())
    if not normalized:
        raise BenchmarkPreparationError(f"selected clip {safe_id} has empty text")
    _safe_write(path, (normalized + "\n").encode("utf-8"))
    return path.relative_to(REPOSITORY_ROOT).as_posix(), file_sha256(path), normalized


def _textgrid_intervals(payload, tier_name=None):
    text = payload.decode("utf-8", errors="strict")
    item_starts = [
        match.start()
        for match in re.finditer(r"^\s*item \[\d+\]:", text, re.MULTILINE)
    ]
    if item_starts:
        blocks = [
            text[start : item_starts[index + 1] if index + 1 < len(item_starts) else len(text)]
            for index, start in enumerate(item_starts)
        ]
        if tier_name is not None:
            blocks = [
                block
                for block in blocks
                if re.search(
                    rf'^\s*name\s*=\s*"{re.escape(tier_name)}"',
                    block,
                    re.MULTILINE,
                )
            ]
            if len(blocks) != 1:
                raise BenchmarkPreparationError(
                    f"TextGrid does not contain exactly one {tier_name} tier"
                )
        elif len(blocks) != 1:
            raise BenchmarkPreparationError(
                "TextGrid tier must be selected when more than one exists"
            )
        text = blocks[0]
    blocks = re.findall(
        r"intervals \[\d+\]:\s*"
        r"xmin = ([0-9.eE+-]+)\s*"
        r"xmax = ([0-9.eE+-]+)\s*"
        r'text = "([^"]*)"',
        text,
        re.MULTILINE,
    )
    if not blocks:
        raise BenchmarkPreparationError("TextGrid contains no readable intervals")
    result = []
    previous_end = None
    for start, end, label in blocks:
        start_value = float(start)
        end_value = float(end)
        if start_value > end_value or (
            previous_end is not None and start_value < previous_end - 1e-9
        ):
            raise BenchmarkPreparationError("TextGrid intervals overlap or reverse")
        previous_end = end_value
        result.append([round(start_value, 6), round(end_value, 6), label])
    return result


def _base_clip(
    safe_id,
    record_id,
    participant_id,
    split,
    stratum,
    audio,
    text_path,
    text_sha256,
    reference_sha256,
    same_system_subset,
):
    return {
        "safe_id": safe_id,
        "private_record_id": record_id,
        "private_participant_id": participant_id,
        "project_split": split,
        "source_stratum": stratum,
        **audio,
        "intended_text_path": text_path,
        "intended_text_sha256": text_sha256,
        "reference_record_sha256": reference_sha256,
        "eligible_tools": ["mfa", "panphon", "phoneticxeus"],
        "same_clip_local_system_subset": same_system_subset,
    }


def _participant_count(policy, count_field, stratum):
    """Read a per stratum participant count from a sample policy.

    The frozen checkpoint 22D policy states one integer for every stratum. The
    powered checkpoint 22E4B policy states a count per stratum, because it takes
    every remaining adult while leaving the child sample where it was.
    """
    value = policy[count_field]
    if isinstance(value, dict):
        if stratum not in value:
            raise BenchmarkPreparationError(
                f"sample policy {count_field} is missing stratum {stratum}"
            )
        return value[stratum]
    return value


def _prepare_speechocean(ffmpeg, contract, policy=None, root=None):
    source_id = "speechocean762"
    if policy is None:
        policy = contract["sample_policy"][source_id]
    root = BENCHMARK_ROOT if root is None else Path(root)
    assignments = _load_assignments("speechocean762-v1.2.0.json")
    selected_participants = {}
    for split, count_field in (
        ("development", "development_participants_per_source_stratum"),
        ("threshold_tuning", "threshold_tuning_participants_per_source_stratum"),
    ):
        for stratum in policy["source_strata"]:
            for participant in _selected_participants(
                assignments,
                split,
                _participant_count(policy, count_field, stratum),
                stratum,
            ):
                selected_participants[participant] = assignments[participant]
    prefixes = {str(participant).zfill(5) for participant in selected_participants}
    metadata_root = AUDIT_ROOT / "speechocean762_v1_2_0" / "speechocean762"
    aggregate = {}
    for filename in ("train.json", "test.json"):
        aggregate.update(
            _selected_top_level_objects(metadata_root / filename, prefixes)
        )
    details = _selected_top_level_objects(
        metadata_root / "resource" / "scores-detail.json", prefixes
    )
    if set(aggregate) != set(details):
        raise BenchmarkPreparationError(
            "selected SpeechOcean aggregate and five-reviewer records differ"
        )
    by_participant = defaultdict(list)
    for utterance_id, row in aggregate.items():
        participant = str(row["speaker"])
        if participant not in selected_participants:
            raise BenchmarkPreparationError("unselected SpeechOcean record escaped filtering")
        by_participant[participant].append(utterance_id)
    if set(by_participant) != set(selected_participants) or any(
        len(items) != policy["clips_per_selected_participant"]
        for items in by_participant.values()
    ):
        raise BenchmarkPreparationError(
            "selected SpeechOcean participants do not each contain twenty clips"
        )
    ordered_records = sorted(
        aggregate,
        key=lambda item: (_stable_key(source_id, item), item),
    )
    safe_id_by_member = {
        f"speechocean762/WAVE/SPEAKER{aggregate[item]['speaker']}/{item}.WAV": (
            f"so_{index:06d}"
        )
        for index, item in enumerate(ordered_records, start=1)
    }
    audio_by_safe_id = {}

    def canonicalize(member, payload):
        safe_id = safe_id_by_member[member]
        target = root / "clips" / safe_id / f"{safe_id}.wav"
        audio_by_safe_id[safe_id] = _canonicalize_audio(
            payload, ".source.wav", target, ffmpeg
        )

    _stream_tar_members(
        CORPUS_ROOT / "speechocean762_v1_2_0" / "speechocean762.tar.gz",
        set(safe_id_by_member),
        canonicalize,
    )
    first_for_participant = {
        participant: min(
            items, key=lambda item: (_stable_key(f"{source_id}:system_subset", item), item)
        )
        for participant, items in by_participant.items()
    }
    clips = []
    reference_records = []
    for index, utterance_id in enumerate(ordered_records, start=1):
        safe_id = f"so_{index:06d}"
        row = aggregate[utterance_id]
        detail = details[utterance_id]
        participant = str(row["speaker"])
        assignment = selected_participants[participant]
        if row["text"] != detail["text"]:
            raise BenchmarkPreparationError("SpeechOcean transcript records disagree")
        if len(row["words"]) != len(detail["words"]):
            raise BenchmarkPreparationError("SpeechOcean word records disagree")
        words = []
        for word_index, (aggregate_word, detail_word) in enumerate(
            zip(row["words"], detail["words"])
        ):
            if aggregate_word["text"] != detail_word["text"]:
                raise BenchmarkPreparationError("SpeechOcean word text differs")
            reviewer_phones = detail_word["phones"]
            if len(reviewer_phones) != 5:
                raise BenchmarkPreparationError("SpeechOcean reviewer count changed")
            words.append(
                {
                    "word_index": word_index,
                    "text": detail_word["text"],
                    "reference_phones": detail_word["ref-phones"],
                    "five_reviewer_phone_strings": reviewer_phones,
                    "aggregate_mispronunciations": aggregate_word.get(
                        "mispronunciations", []
                    ),
                }
            )
        reference = {
            "safe_id": safe_id,
            "private_utterance_id": utterance_id,
            "private_participant_id": participant,
            "project_split": assignment["project_split"],
            "source_stratum": assignment["source_stratum"],
            "text": detail["text"],
            "words": words,
            "scalar_scores_imported_as_relations": False,
        }
        reference_sha = canonical_json_sha256(reference)
        reference_records.append(reference)
        audio = audio_by_safe_id[safe_id]
        text_path, text_sha, _ = _write_text(safe_id, detail["text"], root)
        clips.append(
            _base_clip(
                safe_id,
                utterance_id,
                participant,
                assignment["project_split"],
                assignment["source_stratum"],
                audio,
                text_path,
                text_sha,
                reference_sha,
                utterance_id == first_for_participant[participant],
            )
        )
    return _source_document(
        source_id, "expert_phone_relations", reference_records, clips, root
    )


def _acted_prompts():
    result = {}
    path = CORPUS_ROOT / "acted_clear_speech_2013" / "clear_speech_prompts.txt"
    for line in path.read_text(encoding="utf-8").splitlines():
        number, text = line.split(" ", 1)
        result[number.zfill(4)] = text
    return result


def _prepare_acted_clear(ffmpeg, contract):
    source_id = "acted_clear_speech"
    root = CORPUS_ROOT / "acted_clear_speech_2013"
    with zipfile.ZipFile(root / "clear_speech_wavs.zip") as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".wav")]
    by_condition = defaultdict(list)
    for name in names:
        parts = Path(name).stem.split("_")
        if len(parts) != 3:
            raise BenchmarkPreparationError("Acted Clear filename shape changed")
        by_condition[parts[1]].append(name)
    wanted = []
    count = contract["sample_policy"]["acted_clear_speech"][
        "clips_per_speaking_condition"
    ]
    for condition, condition_names in sorted(by_condition.items()):
        wanted.extend(
            sorted(
                condition_names,
                key=lambda item: (_stable_key(f"{source_id}:{condition}", item), item),
            )[:count]
        )
    if len(by_condition) != 5 or len(wanted) != 25:
        raise BenchmarkPreparationError("Acted Clear condition selection is incomplete")
    prompts = _acted_prompts()
    with zipfile.ZipFile(root / "clear_speech_wavs.zip") as audio_archive, zipfile.ZipFile(
        root / "clear_speech_TextGrid.zip"
    ) as grid_archive:
        grid_by_stem = {
            Path(name).stem: name
            for name in grid_archive.namelist()
            if name.lower().endswith(".textgrid")
            and "__MACOSX" not in Path(name).parts
            and not Path(name).name.startswith("._")
        }
        clips = []
        reference_records = []
        for index, name in enumerate(sorted(wanted), start=1):
            safe_id = f"ac_{index:06d}"
            stem = Path(name).stem
            condition = stem.split("_")[1]
            prompt_id = stem.split("_")[2]
            text = prompts[prompt_id]
            grid_payload = grid_archive.read(grid_by_stem[stem])
            intervals = _textgrid_intervals(grid_payload)
            reference = {
                "safe_id": safe_id,
                "private_record_id": stem,
                "condition": condition,
                "prompt_id": prompt_id,
                "text": text,
                "hand_corrected_phone_intervals": intervals,
                "textgrid_sha256": hashlib.sha256(grid_payload).hexdigest(),
                "truth_class": "human_corrected_phone_boundaries_only",
            }
            reference_sha = canonical_json_sha256(reference)
            reference_records.append(reference)
            target = BENCHMARK_ROOT / "clips" / safe_id / f"{safe_id}.wav"
            audio = _canonicalize_audio(audio_archive.read(name), ".source.wav", target, ffmpeg)
            text_path, text_sha, _ = _write_text(safe_id, text)
            clips.append(
                _base_clip(
                    safe_id,
                    stem,
                    "single_fixture_speaker",
                    "fixture",
                    condition,
                    audio,
                    text_path,
                    text_sha,
                    reference_sha,
                    True,
                )
            )
    return _source_document(
        source_id, "human_corrected_phone_boundaries", reference_records, clips
    )


def _read_selected_csv_rows(path, delimiter, selected_participants, participant_field):
    result = defaultdict(list)
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter=delimiter):
            participant = row[participant_field]
            if participant in selected_participants:
                result[participant].append(row)
    return result


def _prepare_common_phone(ffmpeg, contract):
    source_id = "common_phone_1_0"
    policy = contract["sample_policy"][source_id]
    assignments = _load_assignments("common-phone-v1.0.json")
    selected = {}
    for split, count in (
        ("development", policy["development_participants"]),
        ("threshold_tuning", policy["threshold_tuning_participants"]),
    ):
        for participant in _selected_participants(assignments, split, count):
            selected[participant] = assignments[participant]
    rows_by_participant = defaultdict(list)
    metadata = AUDIT_ROOT / "common_phone_1_0" / "CP" / "en"
    for filename in ("train.csv", "dev.csv", "test.csv"):
        rows = _read_selected_csv_rows(metadata / filename, ",", selected, "id")
        for participant, values in rows.items():
            rows_by_participant[participant].extend(values)
    chosen = {}
    for participant in selected:
        rows = rows_by_participant[participant]
        if not rows:
            raise BenchmarkPreparationError("selected Common Phone participant has no clips")
        chosen[participant] = min(
            rows,
            key=lambda item: (
                _stable_key(f"{source_id}:{participant}", item["audio file"]),
                item["audio file"],
            ),
        )
    members = {}
    for participant, row in chosen.items():
        stem = Path(row["audio file"]).stem
        members[f"CP/en/wav/{stem}.wav"] = (participant, row, "audio")
        members[f"CP/en/grids/{stem}.TextGrid"] = (participant, row, "grid")
    payloads = _extract_tar_members(
        CORPUS_ROOT / "common_phone_1_0" / "cp-1-0.tgz", set(members)
    )
    clips = []
    reference_records = []
    ordered = sorted(chosen, key=lambda item: (_stable_key(source_id, item), item))
    for index, participant in enumerate(ordered, start=1):
        safe_id = f"cp_{index:06d}"
        row = chosen[participant]
        stem = Path(row["audio file"]).stem
        grid_payload = payloads[f"CP/en/grids/{stem}.TextGrid"]
        reference = {
            "safe_id": safe_id,
            "private_record_id": row["audio file"],
            "private_participant_id": participant,
            "project_split": selected[participant]["project_split"],
            "text": row["text"],
            "automatic_phone_intervals": _textgrid_intervals(grid_payload, "MAU"),
            "textgrid_sha256": hashlib.sha256(grid_payload).hexdigest(),
            "truth_class": "automatic_forced_alignment_not_phone_truth",
        }
        reference_sha = canonical_json_sha256(reference)
        reference_records.append(reference)
        target = BENCHMARK_ROOT / "clips" / safe_id / f"{safe_id}.wav"
        audio = _canonicalize_audio(
            payloads[f"CP/en/wav/{stem}.wav"], ".source.wav", target, ffmpeg
        )
        text_path, text_sha, _ = _write_text(safe_id, row["text"])
        clips.append(
            _base_clip(
                safe_id,
                row["audio file"],
                participant,
                selected[participant]["project_split"],
                selected[participant]["source_stratum"],
                audio,
                text_path,
                text_sha,
                reference_sha,
                True,
            )
        )
    return _source_document(
        source_id, "automatic_forced_alignments", reference_records, clips
    )


def _prepare_common_voice(ffmpeg, contract):
    source_id = "common_voice_26_australian_english"
    policy = contract["sample_policy"][source_id]
    assignments = _load_assignments("common-voice-26-au.json")
    selected = {}
    for split, count in (
        ("development", policy["development_participants"]),
        ("threshold_tuning", policy["threshold_tuning_participants"]),
    ):
        for participant in _selected_participants(assignments, split, count):
            selected[participant] = assignments[participant]
    rows_by_participant = defaultdict(list)
    metadata = AUDIT_ROOT / "common_voice_26_au"
    for filename in ("train.tsv", "dev.tsv", "test.tsv"):
        rows = _read_selected_csv_rows(metadata / filename, "\t", selected, "client_id")
        for participant, values in rows.items():
            rows_by_participant[participant].extend(values)
    chosen = {}
    for participant in selected:
        rows = rows_by_participant[participant]
        if not rows:
            raise BenchmarkPreparationError("selected Common Voice participant has no clips")
        chosen[participant] = min(
            rows,
            key=lambda item: (
                _stable_key(f"{source_id}:{participant}", item["path"]),
                item["path"],
            ),
        )
    members = {f"clips/{row['path']}" for row in chosen.values()}
    payloads = _extract_tar_members(
        CORPUS_ROOT
        / "common_voice_26_au"
        / "common-voice-scripted-speech-26-0-austra-c6a1c1a1.tar.gz",
        members,
    )
    clips = []
    reference_records = []
    ordered = sorted(chosen, key=lambda item: (_stable_key(source_id, item), item))
    for index, participant in enumerate(ordered, start=1):
        safe_id = f"cv_{index:06d}"
        row = chosen[participant]
        reference = {
            "safe_id": safe_id,
            "private_record_id": row["path"],
            "private_participant_id": participant,
            "project_split": selected[participant]["project_split"],
            "sentence_id": row["sentence_id"],
            "text": row["sentence"],
            "validation_votes": {
                "up": int(row["up_votes"]),
                "down": int(row["down_votes"]),
            },
            "truth_class": "validated_sentence_audio_not_phone_truth",
        }
        reference_sha = canonical_json_sha256(reference)
        reference_records.append(reference)
        target = BENCHMARK_ROOT / "clips" / safe_id / f"{safe_id}.wav"
        audio = _canonicalize_audio(
            payloads[f"clips/{row['path']}"], ".source.mp3", target, ffmpeg
        )
        text_path, text_sha, _ = _write_text(safe_id, row["sentence"])
        clips.append(
            _base_clip(
                safe_id,
                row["path"],
                participant,
                selected[participant]["project_split"],
                selected[participant]["source_stratum"],
                audio,
                text_path,
                text_sha,
                reference_sha,
                True,
            )
        )
    return _source_document(
        source_id, "validated_sentence_audio", reference_records, clips
    )


def _source_document(source_id, truth_class, reference_records, clips, root=None):
    root = BENCHMARK_ROOT if root is None else Path(root)
    reference_path = root / "references" / f"{source_id}.json"
    reference_document = {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "source_id": source_id,
        "truth_class": truth_class,
        "records": reference_records,
    }
    _safe_write(reference_path, canonical_json_bytes(reference_document))
    return {
        "source_id": source_id,
        "truth_class": truth_class,
        "private_reference_path": reference_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "private_reference_sha256": file_sha256(reference_path),
        "clips": clips,
    }


def prepare_benchmark(ffmpeg=FFMPEG_DEFAULT):
    contract = load_benchmark_contract()
    phone_map = load_phone_map()
    if not Path(ffmpeg).is_file():
        raise BenchmarkPreparationError("ffmpeg executable is unavailable")
    _, manifests = load_registered_manifests()
    private_errors = validate_private_evidence(manifests)
    if private_errors:
        raise BenchmarkPreparationError("; ".join(private_errors))
    if BENCHMARK_ROOT.exists() or MANIFEST_PATH.exists():
        raise BenchmarkPreparationError(
            "private benchmark output already exists; do not overwrite frozen evidence"
        )
    sources = [
        _prepare_speechocean(Path(ffmpeg), contract),
        _prepare_acted_clear(Path(ffmpeg), contract),
        _prepare_common_phone(Path(ffmpeg), contract),
        _prepare_common_voice(Path(ffmpeg), contract),
    ]
    manifest = {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "protocol_id": "speech_sound_patterns_developer_benchmark_v1",
        "selection_seed": contract["split_policy"]["selection_seed"],
        "benchmark_contract_sha256": canonical_json_sha256(contract),
        "phone_map_sha256": canonical_json_sha256(phone_map),
        "held_out_evaluation_accessed": False,
        "selection_used_labels_or_outputs": False,
        "sources": sources,
    }
    errors = validate_private_benchmark_manifest(manifest)
    if errors:
        raise BenchmarkPreparationError("; ".join(errors))
    _safe_write(MANIFEST_PATH, canonical_json_bytes(manifest))
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", type=Path, default=FFMPEG_DEFAULT)
    args = parser.parse_args()
    manifest = prepare_benchmark(args.ffmpeg.resolve())
    print(
        "Prepared private checkpoint 22D benchmark: "
        f"{sum(len(source['clips']) for source in manifest['sources'])} clips"
    )
    print(f"Private manifest SHA256: {canonical_json_sha256(manifest)}")
    print("Held out evaluation participants were not selected or scored.")


if __name__ == "__main__":
    main()
