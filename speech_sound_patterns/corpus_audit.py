"""Deterministic private participant splits and source capability audits."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import tarfile
import zipfile
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from .corpus_manifest import REPOSITORY_ROOT, SPLITS, canonical_json_sha256


AUDIT_SCHEMA_VERSION = "1.0.0"
DEFAULT_SPLIT_SEED = "speech_sound_patterns_corpus_split_v1"


class CorpusAuditError(ValueError):
    """Raised when source metadata cannot support an exclusive split audit."""


def _stable_order(source_id, seed, participant_id):
    value = f"{source_id}\0{seed}\0{participant_id}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _split_sizes(total):
    if total < 3:
        raise CorpusAuditError("an evaluated stratum needs at least three participants")
    development = max(1, round(total * 0.6))
    tuning = max(1, round(total * 0.2))
    if development + tuning >= total:
        development = total - 2
        tuning = 1
    return development, tuning, total - development - tuning


def assign_stratified_participants(source_id, participant_strata, seed=DEFAULT_SPLIT_SEED):
    """Return exact deterministic 60/20/20 assignments within each stratum."""
    if not isinstance(participant_strata, dict) or not participant_strata:
        raise CorpusAuditError("participant strata must be a nonempty mapping")
    groups = defaultdict(list)
    for participant_id, stratum in participant_strata.items():
        if not isinstance(participant_id, str) or not participant_id:
            raise CorpusAuditError("participant ids must be nonempty strings")
        if not isinstance(stratum, str) or not stratum:
            raise CorpusAuditError("participant strata must be nonempty strings")
        groups[stratum].append(participant_id)
    assignments = {}
    for stratum, participants in sorted(groups.items()):
        ordered = sorted(
            participants,
            key=lambda item: (_stable_order(source_id, seed, item), item),
        )
        development, tuning, _ = _split_sizes(len(ordered))
        for index, participant_id in enumerate(ordered):
            if index < development:
                split = "development"
            elif index < development + tuning:
                split = "threshold_tuning"
            else:
                split = "held_out_evaluation"
            assignments[participant_id] = {
                "project_split": split,
                "source_stratum": stratum,
            }
    return assignments


def map_source_splits(source_participants, split_mapping):
    """Map verified source participant splits to the three project splits."""
    if set(split_mapping.values()) != set(SPLITS):
        raise CorpusAuditError("source mapping must cover every project split")
    seen = {}
    assignments = {}
    for source_split, participants in source_participants.items():
        if source_split not in split_mapping:
            raise CorpusAuditError(f"source split {source_split} is not mapped")
        for participant_id in participants:
            if participant_id in seen:
                raise CorpusAuditError(
                    f"participant {participant_id} crosses {seen[participant_id]} and {source_split}"
                )
            seen[participant_id] = source_split
            assignments[participant_id] = {
                "project_split": split_mapping[source_split],
                "source_stratum": source_split,
            }
    return assignments


def validate_private_assignment(document):
    errors = []
    if not isinstance(document, dict):
        return ["assignment must be an object"]
    required = {
        "schema_version",
        "source_id",
        "seed",
        "contains_exact_age",
        "assignments",
    }
    missing = sorted(required - set(document))
    if missing:
        return [f"assignment missing fields: {', '.join(missing)}"]
    if document["schema_version"] != AUDIT_SCHEMA_VERSION:
        errors.append("assignment schema version is unsupported")
    if document["contains_exact_age"] is not False:
        errors.append("private split assignment must not retain exact age")
    assignments = document["assignments"]
    if not isinstance(assignments, dict) or not assignments:
        errors.append("assignments must be a nonempty object")
        return errors
    for participant_id, item in assignments.items():
        if not isinstance(participant_id, str) or not participant_id:
            errors.append("participant ids must be nonempty strings")
        if not isinstance(item, dict):
            errors.append(f"participant {participant_id} assignment must be an object")
            continue
        if item.get("project_split") not in SPLITS:
            errors.append(f"participant {participant_id} has an invalid split")
        if not isinstance(item.get("source_stratum"), str) or not item[
            "source_stratum"
        ]:
            errors.append(f"participant {participant_id} has no aggregate stratum")
    return errors


def build_private_assignment(source_id, assignments, seed=DEFAULT_SPLIT_SEED):
    document = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "source_id": source_id,
        "seed": seed,
        "contains_exact_age": False,
        "assignments": dict(sorted(assignments.items())),
    }
    errors = validate_private_assignment(document)
    if errors:
        raise CorpusAuditError("\n".join(errors))
    return document


def assignment_summary(document):
    errors = validate_private_assignment(document)
    if errors:
        raise CorpusAuditError("\n".join(errors))
    counts = Counter(
        item["project_split"] for item in document["assignments"].values()
    )
    strata = defaultdict(Counter)
    for item in document["assignments"].values():
        strata[item["source_stratum"]][item["project_split"]] += 1
    return {
        "assignment_sha256": canonical_json_sha256(document),
        "participant_counts": {split: counts[split] for split in SPLITS},
        "cross_split_overlap_count": 0,
        "strata": {
            name: {split: values[split] for split in SPLITS}
            for name, values in sorted(strata.items())
        },
    }


def write_private_assignment(path, document):
    """Write an auditable identifier index only inside the ignored data root."""
    path = Path(path).resolve(strict=False)
    private_root = (REPOSITORY_ROOT / ".research_data").resolve()
    try:
        path.relative_to(private_root)
    except ValueError as exc:
        raise CorpusAuditError(
            "private assignments must stay inside the repository .research_data root"
        ) from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)
    return assignment_summary(document)


def audit_speechocean(metadata_root, assignment_path):
    metadata_root = Path(metadata_root)
    participant_meta = {}
    utterance_to_speaker = {}
    source_splits = {}
    for source_split in ("train", "test"):
        records = json.loads((metadata_root / f"{source_split}.json").read_text())
        speakers = set()
        for utterance_id, row in records.items():
            if utterance_id in utterance_to_speaker:
                raise CorpusAuditError(
                    "SpeechOcean utterance identifiers cross source splits"
                )
            participant_id = str(row["speaker"])
            age_band = "source_child" if int(row["age"]) < 18 else "source_adult"
            stratum = f"{age_band}_{row['gender']}"
            previous = participant_meta.setdefault(participant_id, stratum)
            if previous != stratum:
                raise CorpusAuditError("SpeechOcean participant metadata is inconsistent")
            utterance_to_speaker[utterance_id] = participant_id
            speakers.add(participant_id)
        source_splits[source_split] = speakers
    if source_splits["train"] & source_splits["test"]:
        raise CorpusAuditError("SpeechOcean source train and test speakers overlap")
    if len(participant_meta) != 250 or len(utterance_to_speaker) != 5000:
        raise CorpusAuditError(
            "SpeechOcean v1.2.0 must contain 250 speakers and 5000 utterances"
        )
    scores_detail = json.loads(
        (metadata_root / "resource" / "scores-detail.json").read_text()
    )
    if set(scores_detail) != set(utterance_to_speaker):
        raise CorpusAuditError("SpeechOcean detail records do not match utterances")
    notation_counts = Counter()
    for utterance_id, row in scores_detail.items():
        for field in ("accuracy", "completeness", "fluency", "prosodic", "total"):
            if len(row[field]) != 5:
                raise CorpusAuditError(
                    f"SpeechOcean {utterance_id} does not retain five {field} reviews"
                )
        for word in row["words"]:
            for field in ("accuracy", "stress", "total", "phones"):
                if len(word[field]) != 5:
                    raise CorpusAuditError(
                        f"SpeechOcean {utterance_id} word lacks five {field} reviews"
                    )
            for phone_record in word["phones"]:
                notation_counts["insertion"] += phone_record.count("[")
                notation_counts["score_zero_or_missed"] += phone_record.count("(")
                notation_counts["accent_marked_score_one"] += phone_record.count("{")
    assignments = assign_stratified_participants("speechocean762", participant_meta)
    document = build_private_assignment("speechocean762", assignments)
    summary = write_private_assignment(assignment_path, document)
    summary.update(
        {
            "source_original_split_overlap": 0,
            "participants": len(participant_meta),
            "utterances": len(scores_detail),
            "expert_records_per_utterance": 5,
            "relation_notation_counts": dict(notation_counts),
        }
    )
    return summary


def audit_common_voice(
    metadata_root,
    assignment_path,
    source_id="common_voice_26_australian_english",
):
    """Audit one Common Voice accent subset and freeze its participant split.

    Checkpoint 22E7 added the British and American comparison subsets. They go
    through this same function rather than a parallel one, because a comparison
    is only fair if every group was split, deduplicated and sealed by identical
    code.
    """
    metadata_root = Path(metadata_root)
    source_participants = {}
    row_counts = {}
    expected_fields = {
        "client_id",
        "path",
        "sentence_id",
        "sentence",
        "up_votes",
        "down_votes",
        "accents",
        "locale",
    }
    seen_clip_paths = {}
    for source_split in ("train", "dev", "test"):
        with (metadata_root / f"{source_split}.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if not expected_fields.issubset(reader.fieldnames or []):
                raise CorpusAuditError("Common Voice metadata fields are incomplete")
            rows = list(reader)
        for row in rows:
            participant_id = row["client_id"]
            clip_path = row["path"]
            if not participant_id or not clip_path:
                raise CorpusAuditError(
                    "Common Voice rows require participant and clip identifiers"
                )
            if clip_path in seen_clip_paths:
                raise CorpusAuditError(
                    f"Common Voice clip {clip_path} repeats in "
                    f"{seen_clip_paths[clip_path]} and {source_split}"
                )
            seen_clip_paths[clip_path] = source_split
        source_participants[source_split] = {row["client_id"] for row in rows}
        row_counts[source_split] = len(rows)
    assignments = map_source_splits(
        source_participants,
        {
            "train": "development",
            "dev": "threshold_tuning",
            "test": "held_out_evaluation",
        },
    )
    document = build_private_assignment(
        source_id,
        assignments,
        seed="source_speaker_disjoint_splits",
    )
    summary = write_private_assignment(assignment_path, document)
    summary.update({"clip_counts": row_counts, "participants": len(assignments)})
    return summary


def _read_common_phone_splits(metadata_root):
    metadata_root = Path(metadata_root)
    expected_fields = {"audio file", "id", "text"}
    source_rows = {}
    seen_clips = {}
    seen_participants = {}
    for source_split in ("train", "dev", "test"):
        with (metadata_root / f"{source_split}.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            reader = csv.DictReader(handle)
            if set(reader.fieldnames or []) != expected_fields:
                raise CorpusAuditError("Common Phone split fields are incomplete")
            rows = list(reader)
        for row in rows:
            clip = row["audio file"]
            participant = row["id"]
            if not clip or not participant or not row["text"]:
                raise CorpusAuditError("Common Phone split rows are incomplete")
            if clip in seen_clips:
                raise CorpusAuditError(
                    f"Common Phone clip {clip} repeats across source rows"
                )
            seen_clips[clip] = source_split
            prior_split = seen_participants.setdefault(participant, source_split)
            if prior_split != source_split:
                raise CorpusAuditError(
                    f"Common Phone participant crosses {prior_split} and {source_split}"
                )
        source_rows[source_split] = rows
    return source_rows


def _common_voice_identifiers(metadata_root):
    participants = set()
    clips = set()
    metadata_root = Path(metadata_root)
    for source_split in ("train", "dev", "test"):
        with (metadata_root / f"{source_split}.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                participants.add(row["client_id"])
                clips.add(row["path"])
    return participants, clips


def audit_common_phone(
    metadata_root, assignment_path, common_voice_metadata_root=None
):
    """Audit English source splits and remove detectable current-CV overlap."""
    metadata_root = Path(metadata_root)
    source_rows = _read_common_phone_splits(metadata_root)
    with (metadata_root / "meta.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != {
            "id",
            "gender",
            "age",
            "locale",
            "accent",
            "set",
        }:
            raise CorpusAuditError("Common Phone participant metadata is incomplete")
        meta_rows = list(reader)
    meta_by_id = {}
    for row in meta_rows:
        if row["id"] in meta_by_id:
            raise CorpusAuditError("Common Phone participant metadata is duplicated")
        if row["set"] not in {"train", "dev", "test"}:
            raise CorpusAuditError("Common Phone participant metadata has unknown split")
        meta_by_id[row["id"]] = row

    expected_counts = {"train": 4716, "dev": 771, "test": 774}
    participants_by_split = {
        name: {row["id"] for row in rows} for name, rows in source_rows.items()
    }
    if {name: len(values) for name, values in participants_by_split.items()} != (
        expected_counts
    ):
        raise CorpusAuditError("Common Phone English speaker counts differ from 1.0")
    all_participants = set().union(*participants_by_split.values())
    if set(meta_by_id) != all_participants:
        raise CorpusAuditError("Common Phone metadata does not match split speakers")
    for source_split, participants in participants_by_split.items():
        if any(meta_by_id[item]["set"] != source_split for item in participants):
            raise CorpusAuditError("Common Phone metadata split labels disagree")

    overlapping_clips = set()
    overlapping_participants = set()
    excluded_participants = set()
    if common_voice_metadata_root is not None:
        cv_participants, cv_clips = _common_voice_identifiers(
            common_voice_metadata_root
        )
        overlapping_participants = all_participants & cv_participants
        for rows in source_rows.values():
            for row in rows:
                if row["audio file"] in cv_clips:
                    overlapping_clips.add(row["audio file"])
                    excluded_participants.add(row["id"])
        excluded_participants.update(overlapping_participants)

    eligible_by_split = {
        name: values - excluded_participants
        for name, values in participants_by_split.items()
    }
    assignments = map_source_splits(
        eligible_by_split,
        {
            "train": "development",
            "dev": "threshold_tuning",
            "test": "held_out_evaluation",
        },
    )
    document = build_private_assignment(
        "common_phone_1_0",
        assignments,
        seed="source_speaker_disjoint_splits_after_current_cv_overlap_exclusion",
    )
    summary = write_private_assignment(assignment_path, document)
    summary.update(
        {
            "source_participant_counts": expected_counts,
            "eligible_participant_counts": {
                name: len(values) for name, values in eligible_by_split.items()
            },
            "clip_counts": {
                name: len(rows) for name, rows in source_rows.items()
            },
            "current_common_voice_participant_id_overlap": len(
                overlapping_participants
            ),
            "current_common_voice_clip_id_overlap": len(overlapping_clips),
            "participants_excluded_for_detectable_current_cv_overlap": len(
                excluded_participants
            ),
        }
    )
    return summary


def audit_common_phone_archive(archive_path, metadata_root, sample_grids=25):
    """Check English audio and TextGrid pairing inside the actual archive."""
    source_rows = _read_common_phone_splits(metadata_root)
    expected_stems = {
        Path(row["audio file"]).stem
        for rows in source_rows.values()
        for row in rows
    }
    stems = {"mp3": set(), "wav": set(), "grids": set()}
    inspected_grid_tiers = Counter()
    inspected_grids = 0
    with tarfile.open(archive_path, "r|gz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.startswith("CP/en/"):
                continue
            path = Path(member.name)
            if "__MACOSX" in path.parts or path.name.startswith("._"):
                continue
            folder = path.parts[2] if len(path.parts) > 3 else None
            suffix = path.suffix.lower()
            if folder == "mp3" and suffix == ".mp3":
                stems["mp3"].add(path.stem)
            elif folder == "wav" and suffix == ".wav":
                stems["wav"].add(path.stem)
            elif folder == "grids" and suffix == ".textgrid":
                stems["grids"].add(path.stem)
                if inspected_grids < sample_grids:
                    handle = archive.extractfile(member)
                    if handle is None:
                        raise CorpusAuditError("Common Phone TextGrid is unreadable")
                    payload = handle.read().decode("utf-8", errors="strict")
                    if 'Object class = "TextGrid"' not in payload:
                        raise CorpusAuditError("Common Phone TextGrid is malformed")
                    tier_names = set(
                        re.findall(r'^\s*name\s*=\s*"([^"]+)"', payload, re.MULTILINE)
                    )
                    if not tier_names:
                        raise CorpusAuditError("Common Phone TextGrid has no tiers")
                    inspected_grid_tiers.update(tier_names)
                    inspected_grids += 1
    for kind, actual in stems.items():
        if actual != expected_stems:
            missing = sorted(expected_stems - actual)[:3]
            unexpected = sorted(actual - expected_stems)[:3]
            raise CorpusAuditError(
                f"Common Phone English {kind} files do not pair with split rows: "
                f"expected {len(expected_stems)}, found {len(actual)}, "
                f"missing sample {missing}, unexpected sample {unexpected}"
            )
    if inspected_grids != sample_grids:
        raise CorpusAuditError("Common Phone TextGrid sample is incomplete")
    return {
        "english_clips": len(expected_stems),
        "paired_mp3_wav_and_textgrid": True,
        "textgrids_inspected": inspected_grids,
        "observed_tier_names": dict(sorted(inspected_grid_tiers.items())),
    }


def _librispeech_speakers(archive_path, subset):
    speakers = set()
    with tarfile.open(archive_path, "r:gz") as archive:
        prefix = f"LibriSpeech/{subset}/"
        for member in archive:
            if not member.name.startswith(prefix):
                continue
            parts = member.name.split("/")
            if len(parts) >= 3 and parts[2].isdigit():
                speakers.add(parts[2])
    if not speakers:
        raise CorpusAuditError(f"LibriSpeech {subset} has no speaker ids")
    return speakers


def audit_librispeech(corpus_root, assignment_path):
    corpus_root = Path(corpus_root)
    participants = {}
    for subset in ("dev-clean", "dev-other"):
        for participant_id in _librispeech_speakers(
            corpus_root / f"{subset}.tar.gz", subset
        ):
            if participant_id in participants:
                raise CorpusAuditError("LibriSpeech small subsets share a speaker")
            participants[participant_id] = subset
    assignments = assign_stratified_participants(
        "librispeech_slr12_small", participants
    )
    document = build_private_assignment("librispeech_slr12_small", assignments)
    summary = write_private_assignment(assignment_path, document)
    summary.update({"participants": len(participants)})
    return summary


def audit_acted_clear(corpus_root):
    corpus_root = Path(corpus_root)
    with zipfile.ZipFile(corpus_root / "clear_speech_wavs.zip") as archive:
        wave_names = [name for name in archive.namelist() if name.lower().endswith(".wav")]
    with zipfile.ZipFile(corpus_root / "clear_speech_TextGrid.zip") as archive:
        grid_names = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".textgrid")
            and "__MACOSX" not in Path(name).parts
            and not Path(name).name.startswith("._")
        ]
    if len(wave_names) != 125 or len(grid_names) != 125:
        raise CorpusAuditError(
            "Acted Clear expected 125 wave trials and 125 hand corrected TextGrids"
        )
    wave_stems = {Path(name).stem for name in wave_names}
    grid_stems = {Path(name).stem for name in grid_names}
    if len(wave_stems) != 125 or wave_stems != grid_stems:
        raise CorpusAuditError(
            "Acted Clear audio and hand corrected TextGrids must pair one to one"
        )
    with zipfile.ZipFile(corpus_root / "clear_speech_TextGrid.zip") as archive:
        for name in grid_names:
            payload = archive.read(name).decode("utf-8", errors="strict")
            interval_count = re.search(r"intervals:\s*size\s*=\s*(\d+)", payload)
            labels = re.findall(r'^\s*text\s*=\s*"([^"]*)"', payload, re.MULTILINE)
            if (
                'Object class = "TextGrid"' not in payload
                or interval_count is None
                or int(interval_count.group(1)) < 2
                or len(labels) != int(interval_count.group(1))
                or not any(label and label != "sil" for label in labels)
            ):
                raise CorpusAuditError(
                    f"Acted Clear TextGrid {name} lacks usable phone intervals"
                )
    conditions = Counter()
    for name in grid_names:
        parts = Path(name).stem.split("_")
        if len(parts) < 3:
            raise CorpusAuditError("Acted Clear filename cannot identify condition")
        conditions[parts[1]] += 1
    if sorted(conditions.values()) != [25, 25, 25, 25, 25]:
        raise CorpusAuditError("Acted Clear conditions are incomplete")
    return {
        "participants": 1,
        "wave_files": len(wave_names),
        "hand_corrected_textgrids": len(grid_names),
        "conditions": dict(sorted(conditions.items())),
    }


# Checkpoint 22E7. The openly licensed reference stack and the comparison accent
# subsets. Every count below is recomputed from the acquired bytes, because the
# figures this project inherited from an earlier search were already wrong once.

# Rhoticity is the sharpest single difference between the reference this project
# has been using and the variety its speakers actually speak. Australian and
# British English are non-rhotic; American English is rhotic. Counting every
# rhotic symbol would prove nothing, because non-rhotic varieties still have an
# onset /r/ in "red". What separates the varieties is the coda: an /r/ after a
# vowel and not before one, or a vowel carrying r colour outright.
RHOTIC_CONSONANTS = frozenset("ɹɻr")
R_COLOURED_VOWELS = frozenset("ɚɝ")
RHOTIC_HOOK = "˞"
VOWEL_BASES = frozenset("aeiouyæøœɑɒɔəɘɛɜɐɤɨɪɯɵɶʉʊʌʏ") | R_COLOURED_VOWELS
_COMBINING = frozenset(chr(code) for code in range(0x0300, 0x0370))


def _base_characters(phone):
    return frozenset(character for character in phone if character not in _COMBINING)


def _is_vowel(phone):
    return bool(_base_characters(phone) & VOWEL_BASES)


def _is_r_coloured(phone):
    return RHOTIC_HOOK in phone or bool(_base_characters(phone) & R_COLOURED_VOWELS)


def _has_postvocalic_rhotic(phones):
    for index, phone in enumerate(phones):
        if _is_r_coloured(phone):
            return True
        if not _base_characters(phone) & RHOTIC_CONSONANTS:
            continue
        follows_a_vowel = index > 0 and _is_vowel(phones[index - 1])
        precedes_a_vowel = index + 1 < len(phones) and _is_vowel(phones[index + 1])
        if follows_a_vowel and not precedes_a_vowel:
            return True
    return False


def _phone_report(sequences):
    inventory = Counter()
    for phones in sequences:
        inventory.update(phones)
    any_rhotic = sum(
        1
        for phones in sequences
        if any(
            _is_r_coloured(phone) or _base_characters(phone) & RHOTIC_CONSONANTS
            for phone in phones
        )
    )
    postvocalic = sum(1 for phones in sequences if _has_postvocalic_rhotic(phones))
    total = len(sequences)
    return {
        "phone_inventory_size": len(inventory),
        "phone_inventory": sorted(inventory),
        "entries_using_any_rhotic_symbol": any_rhotic,
        "entries_with_a_postvocalic_rhotic": postvocalic,
        "postvocalic_rhotic_share": round(postvocalic / total, 6) if total else 0.0,
    }


def audit_wikipron(tsv_path):
    """Count a WikiPron scrape and describe the variety its phones imply."""
    tsv_path = Path(tsv_path)
    words = Counter()
    sequences = []
    with tsv_path.open(encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.rstrip("\n")
            if not line:
                continue
            fields = line.split("\t")
            if len(fields) != 2 or not fields[0] or not fields[1]:
                raise CorpusAuditError(
                    f"{tsv_path.name} line {line_number} is not a word and pronunciation pair"
                )
            phones = fields[1].split()
            if not phones:
                raise CorpusAuditError(
                    f"{tsv_path.name} line {line_number} has an empty pronunciation"
                )
            words[fields[0]] += 1
            sequences.append(tuple(phones))
    if not sequences:
        raise CorpusAuditError(f"{tsv_path.name} contains no entries")
    report = {
        "entries": len(sequences),
        "distinct_words": len(words),
        "words_with_more_than_one_pronunciation": sum(
            1 for count in words.values() if count > 1
        ),
    }
    report.update(_phone_report(sequences))
    return report


def audit_mfa_dictionary(dictionary_path):
    """Count an MFA pronunciation dictionary and recompute its phone inventory."""
    dictionary_path = Path(dictionary_path)
    words = Counter()
    sequences = []
    with dictionary_path.open(encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.rstrip("\n")
            if not line:
                continue
            fields = line.split("\t")
            if len(fields) < 2:
                raise CorpusAuditError(
                    f"{dictionary_path.name} line {line_number} is not tab separated"
                )
            word = fields[0]
            phones = fields[-1].split()
            probabilities = fields[1:-1]
            for value in probabilities:
                try:
                    float(value)
                except ValueError:
                    raise CorpusAuditError(
                        f"{dictionary_path.name} line {line_number} has a "
                        "non numeric probability field"
                    ) from None
            if not word or not phones:
                raise CorpusAuditError(
                    f"{dictionary_path.name} line {line_number} is incomplete"
                )
            words[word] += 1
            sequences.append(tuple(phones))
    if not sequences:
        raise CorpusAuditError(f"{dictionary_path.name} contains no entries")
    report = {
        "entries": len(sequences),
        "distinct_words": len(words),
        "words_with_more_than_one_pronunciation": sum(
            1 for count in words.values() if count > 1
        ),
    }
    report.update(_phone_report(sequences))
    return report


def kaikki_accent_tag_census(archive_path, limit=None):
    """Count every pronunciation tag in the extraction, so no tag name is guessed.

    Wiktionary's accent templates reach Wiktextract as free tags, and their exact
    spelling is not documented anywhere this project controls. Selecting the
    Australian entries by a guessed tag name would silently build the wrong
    reference, so the tag vocabulary is measured before anything is selected.
    """
    tags = Counter()
    raw_tags = Counter()
    lines = 0
    with gzip.open(Path(archive_path), "rt", encoding="utf-8") as handle:
        for line in handle:
            lines += 1
            if limit is not None and lines > limit:
                break
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CorpusAuditError(
                    f"Kaikki line {lines} is not valid JSON: {exc}"
                ) from None
            if entry.get("lang_code") != "en":
                continue
            for sound in entry.get("sounds") or ():
                if not isinstance(sound, dict) or "ipa" not in sound:
                    continue
                tags.update(sound.get("tags") or ())
                # Kept in a separate counter rather than folded in under a
                # prefix. Selection reads `tags`, so mixing the two here would
                # make the census disagree with the extraction it exists to
                # inform, which it briefly did at 222 against 220.
                raw_tags.update(sound.get("raw_tags") or ())
    return {
        "lines_read": lines,
        "tags": dict(tags.most_common()),
        "raw_tags": dict(raw_tags.most_common()),
    }


def extract_kaikki_australian(archive_path, extract_path, australian_tags):
    """Write the Australian tagged English pronunciations to private storage."""
    australian_tags = frozenset(australian_tags)
    if not australian_tags:
        raise CorpusAuditError("an Australian tag set is required")
    entries = {}
    lines = 0
    english_entries = 0
    observed_tags = set()
    with gzip.open(Path(archive_path), "rt", encoding="utf-8") as handle:
        for line in handle:
            lines += 1
            entry = json.loads(line)
            if entry.get("lang_code") != "en":
                continue
            english_entries += 1
            word = entry.get("word")
            if not word:
                continue
            for sound in entry.get("sounds") or ():
                if not isinstance(sound, dict):
                    continue
                ipa = sound.get("ipa")
                if not ipa:
                    continue
                tags = tuple(sound.get("tags") or ())
                observed_tags.update(tags)
                if not australian_tags.intersection(tags):
                    continue
                record = {
                    "ipa": ipa,
                    "tags": sorted(tags),
                    "part_of_speech": entry.get("pos"),
                }
                bucket = entries.setdefault(word, [])
                if record not in bucket:
                    bucket.append(record)
    if not entries:
        raise CorpusAuditError("no Australian tagged pronunciation was found")
    document = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "source_id": "wiktionary_australian_kaikki",
        "australian_tags": sorted(australian_tags),
        "contains_exact_age": False,
        "lines_read": lines,
        "english_entries": english_entries,
        "distinct_pronunciation_tags": len(observed_tags),
        "entries": {word: sorted(items, key=lambda item: item["ipa"]) for word, items in sorted(entries.items())},
    }
    path = Path(extract_path).resolve(strict=False)
    private_root = (REPOSITORY_ROOT / ".research_data").resolve()
    try:
        path.relative_to(private_root)
    except ValueError as exc:
        raise CorpusAuditError(
            "the Australian extract must stay inside the ignored research root"
        ) from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)
    pronunciations = sum(len(items) for items in entries.values())
    return {
        "lines_read": lines,
        "english_entries": english_entries,
        "australian_words": len(entries),
        "australian_pronunciations": pronunciations,
        "extract_sha256": canonical_json_sha256(document),
    }


def extract_common_voice_metadata(archive_path, metadata_root):
    """Pull only the split TSVs out of a Common Voice archive, never the clips."""
    metadata_root = Path(metadata_root)
    metadata_root.mkdir(parents=True, exist_ok=True)
    wanted = {"train.tsv", "dev.tsv", "test.tsv"}
    written = {}
    with tarfile.open(archive_path, "r|gz") as archive:
        for member in archive:
            name = Path(member.name).name
            if not member.isfile() or name not in wanted or name in written:
                continue
            if Path(member.name).parent not in (Path("."), Path("")):
                raise CorpusAuditError(
                    f"Common Voice metadata {member.name} is not at the archive root"
                )
            handle = archive.extractfile(member)
            if handle is None:
                raise CorpusAuditError(f"Common Voice metadata {name} is unreadable")
            (metadata_root / name).write_bytes(handle.read())
            written[name] = member.size
            if len(written) == len(wanted):
                break
    missing = sorted(wanted - set(written))
    if missing:
        raise CorpusAuditError(
            f"Common Voice archive is missing {', '.join(missing)}"
        )
    return dict(sorted(written.items()))


def _metadata_rows(metadata_root):
    """Yield every supplied Common Voice row, tagged with its source split."""
    for source_split in ("train", "dev", "test"):
        with (Path(metadata_root) / f"{source_split}.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                yield {**row, "source_split": source_split}


def common_voice_identifiers(metadata_root):
    """Return participant and clip identifiers for one Common Voice subset."""
    participants = set()
    clips = set()
    for row in _metadata_rows(metadata_root):
        participants.add(row["client_id"])
        clips.add(row["path"])
    return participants, clips


SOURCE_SPLIT_TO_PROJECT = {
    "train": "development",
    "dev": "threshold_tuning",
    "test": "held_out_evaluation",
}


def _participant_rows(metadata_root):
    rows = defaultdict(list)
    for row in _metadata_rows(metadata_root):
        rows[row["client_id"]].append((row["source_split"], row.get("accents", "")))
    return rows


def build_common_voice_exclusions(metadata_roots, exclusion_path):
    """Record contributors whose declared accent puts them in two groups.

    Common Voice's accent field is multi-select and is answered per clip, so one
    contributor can declare an English accent on most of their recordings and an
    American one on another. Such a speaker cannot represent either variety, and
    leaving them in both a comparison group and its control would shrink the
    very difference the checkpoint 22E8 probe measures. They are excluded from
    both rather than assigned to whichever group they contributed more clips to,
    because the ambiguity is in the evidence and not in the arithmetic.
    """
    rows = {
        source_id: _participant_rows(root)
        for source_id, root in sorted(metadata_roots.items())
    }
    membership = defaultdict(list)
    for source_id, participants in rows.items():
        for participant_id in participants:
            membership[participant_id].append(source_id)
    excluded = {}
    for participant_id, sources in sorted(membership.items()):
        if len(sources) < 2:
            continue
        excluded[participant_id] = {
            "subsets": sorted(sources),
            "detail": {
                source_id: {
                    "clips": len(rows[source_id][participant_id]),
                    "declared_accents": sorted(
                        {accent for _, accent in rows[source_id][participant_id]}
                    ),
                    "project_splits": sorted(
                        {
                            SOURCE_SPLIT_TO_PROJECT[split]
                            for split, _ in rows[source_id][participant_id]
                        }
                    ),
                }
                for source_id in sorted(sources)
            },
        }
    document = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "record_id": "common_voice_accent_group_exclusions_v1",
        "contains_exact_age": False,
        "reason": "A contributor declaring more than one variety cannot represent either, so they are excluded from every comparison group.",
        "subsets_checked": sorted(rows),
        "excluded_participants": excluded,
    }
    path = Path(exclusion_path).resolve(strict=False)
    private_root = (REPOSITORY_ROOT / ".research_data").resolve()
    try:
        path.relative_to(private_root)
    except ValueError as exc:
        raise CorpusAuditError(
            "the exclusion record must stay inside the ignored research root"
        ) from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)
    return {
        "excluded_participants": len(excluded),
        "affected_subsets": sorted(
            {source_id for item in excluded.values() for source_id in item["subsets"]}
        ),
        "record_sha256": canonical_json_sha256(document),
    }


def audit_common_voice_group_overlap(metadata_roots):
    """Prove no speaker or clip is counted in two comparison groups.

    Each accent subset was filtered from one release, so a contributor tagged
    with two accents could in principle land in two groups. A speaker appearing
    in both the group under test and its control would not merely duplicate
    evidence, it would flatten the very difference the checkpoint 22E8 probe
    exists to measure, so this fails closed rather than reporting a warning.
    """
    identifiers = {
        source_id: common_voice_identifiers(root)
        for source_id, root in sorted(metadata_roots.items())
    }
    report = {}
    for left, right in combinations(sorted(identifiers), 2):
        shared_participants = identifiers[left][0] & identifiers[right][0]
        shared_clips = identifiers[left][1] & identifiers[right][1]
        report[f"{left}|{right}"] = {
            "shared_participants": len(shared_participants),
            "shared_clips": len(shared_clips),
        }
    return {
        "subset_sizes": {
            source_id: {"participants": len(people), "clips": len(clips)}
            for source_id, (people, clips) in identifiers.items()
        },
        "pairwise_overlap": report,
        "any_overlap": any(
            values["shared_participants"] or values["shared_clips"]
            for values in report.values()
        ),
    }
