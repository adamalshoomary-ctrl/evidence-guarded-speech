"""Prepare a deterministic private development sample for checkpoint 22C."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import tarfile
import wave
import zipfile
from collections import defaultdict
from pathlib import Path

from .feasibility import (
    FEASIBILITY_SCHEMA_VERSION,
    FROZEN_SAMPLE_MANIFEST_SHA256,
    REPOSITORY_ROOT,
    SELECTION_SEED,
    canonical_json_bytes,
    deterministic_key,
    file_sha256,
    validate_private_sample_manifest,
)


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
SAMPLE_ROOT = PRIVATE_ROOT / "feasibility" / "samples-v1"
MANIFEST_PATH = PRIVATE_ROOT / "feasibility" / "sample-manifest-v1.0.0.json"


def _load_assignment(filename):
    path = PRIVATE_ROOT / "splits" / filename
    return json.loads(path.read_text(encoding="utf-8"))["assignments"]


def _stable_participants(source_id, assignments, count=3):
    eligible = [
        identifier
        for identifier, item in assignments.items()
        if item["project_split"] == "development"
    ]
    return sorted(
        eligible, key=lambda item: deterministic_key(source_id, item)
    )[:count]


def _stable_record(source_id, participant_id, records):
    return sorted(
        records,
        key=lambda item: deterministic_key(
            source_id, f"{participant_id}\0{item['record_id']}"
        ),
    )[0]


def _safe_write(path, payload):
    path = path.resolve(strict=False)
    path.relative_to(PRIVATE_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _extract_tar_members(archive_path, wanted):
    remaining = set(wanted)
    results = {}
    with tarfile.open(archive_path, "r|gz") as archive:
        for member in archive:
            if member.name not in remaining:
                continue
            if not member.isfile():
                raise ValueError(f"archive member is not a file: {member.name}")
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"archive member cannot be read: {member.name}")
            results[member.name] = handle.read()
            remaining.remove(member.name)
            if not remaining:
                break
    if remaining:
        raise ValueError(f"archive members are missing: {sorted(remaining)}")
    return results


def _canonicalize_audio(source_path, target_path, ffmpeg):
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
    with wave.open(str(target_path), "rb") as handle:
        channels = handle.getnchannels()
        sample_rate = handle.getframerate()
        frames = handle.getnframes()
    duration = frames / sample_rate
    if channels != 1 or sample_rate != 16000 or not 0 < duration <= 30:
        raise ValueError(f"canonical audio is outside the spike contract: {target_path}")
    return {
        "canonical_audio_path": target_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "canonical_audio_sha256": file_sha256(target_path),
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "duration_s": round(duration, 6),
    }


def _build_clip(source_id, index, record, raw_payload, raw_suffix, ffmpeg, state):
    safe_id = f"{source_id}_{index:03d}"
    source_dir = SAMPLE_ROOT / source_id
    raw_path = source_dir / "source" / f"{safe_id}{raw_suffix}"
    wav_path = source_dir / "canonical" / f"{safe_id}.wav"
    _safe_write(raw_path, raw_payload)
    audio = _canonicalize_audio(raw_path, wav_path, ffmpeg)
    intended_text = record.get("text")
    clip = {
        "safe_id": safe_id,
        "private_source_id": record["record_id"],
        "private_participant_id": record.get("participant_id"),
        "source_state": state,
        "original_audio_sha256": file_sha256(raw_path),
        **audio,
        "intended_text_state": (
            "source_transcript" if intended_text is not None else "unknown"
        ),
        "eligible_tools": (
            ["phoneticxeus", "mfa", "panphon"]
            if intended_text is not None
            else ["phoneticxeus", "panphon"]
        ),
    }
    if intended_text is not None:
        text = " ".join(intended_text.strip().split())
        if not text:
            raise ValueError(f"empty source transcript for {safe_id}")
        clip["intended_text"] = text
        lab_path = wav_path.with_suffix(".lab")
        _safe_write(lab_path, (text + "\n").encode("utf-8"))
        clip["intended_text_sha256"] = file_sha256(lab_path)
    return clip


def _speechocean_records():
    source_id = "speechocean762"
    assignments = _load_assignment("speechocean762-v1.2.0.json")
    selected = _stable_participants(source_id, assignments)
    by_speaker = defaultdict(list)
    metadata_root = PRIVATE_ROOT / "audit" / "speechocean762_v1_2_0" / "speechocean762"
    for split in ("train", "test"):
        records = json.loads((metadata_root / f"{split}.json").read_text())
        for utterance_id, item in records.items():
            speaker = str(item["speaker"])
            if speaker in selected:
                by_speaker[speaker].append(
                    {
                        "record_id": utterance_id,
                        "participant_id": speaker,
                        "text": item["text"],
                        "member": (
                            f"speechocean762/WAVE/SPEAKER{speaker}/"
                            f"{utterance_id}.WAV"
                        ),
                    }
                )
    return [_stable_record(source_id, item, by_speaker[item]) for item in selected]


def _common_phone_records():
    source_id = "common_phone_1_0"
    assignments = _load_assignment("common-phone-v1.0.json")
    selected = _stable_participants(source_id, assignments)
    by_speaker = defaultdict(list)
    metadata_root = PRIVATE_ROOT / "audit" / "common_phone_1_0" / "CP" / "en"
    for split in ("train", "dev", "test"):
        with (metadata_root / f"{split}.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                participant = row["id"]
                if participant in selected:
                    filename = row["audio file"]
                    by_speaker[participant].append(
                        {
                            "record_id": filename,
                            "participant_id": participant,
                            "text": row["text"],
                            "member": f"CP/en/wav/{Path(filename).stem}.wav",
                        }
                    )
    return [_stable_record(source_id, item, by_speaker[item]) for item in selected]


def _common_voice_records():
    source_id = "common_voice_26_australian_english"
    assignments = _load_assignment("common-voice-26-au.json")
    selected = _stable_participants(source_id, assignments)
    by_speaker = defaultdict(list)
    metadata_root = PRIVATE_ROOT / "audit" / "common_voice_26_au"
    for split in ("train", "dev", "test"):
        with (metadata_root / f"{split}.tsv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                participant = row["client_id"]
                if participant in selected:
                    filename = row["path"]
                    by_speaker[participant].append(
                        {
                            "record_id": filename,
                            "participant_id": participant,
                            "text": row["sentence"],
                            "member": f"clips/{filename}",
                        }
                    )
    return [_stable_record(source_id, item, by_speaker[item]) for item in selected]


def _acted_clear_records():
    source_id = "acted_clear_speech_2013"
    prompt_path = (
        PRIVATE_ROOT
        / "corpora"
        / "acted_clear_speech_2013"
        / "clear_speech_prompts.txt"
    )
    candidates = []
    for line in prompt_path.read_text(encoding="utf-8").splitlines():
        number, text = line.split(" ", 1)
        filename = f"MKH800_19_{number}.wav"
        candidates.append(
            {
                "record_id": filename,
                "participant_id": "single_fixture_speaker",
                "text": text,
                "member": filename,
            }
        )
    return sorted(
        candidates,
        key=lambda item: deterministic_key(source_id, item["record_id"]),
    )[:3]


def _owner_record(owner_audio, ffmpeg):
    source_id = "owner_controlled_integration"
    safe_id = f"{source_id}_001"
    wav_path = SAMPLE_ROOT / source_id / "canonical" / f"{safe_id}.wav"
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        "20",
        "-t",
        "5",
        "-i",
        str(owner_audio),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(wav_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    with wave.open(str(wav_path), "rb") as handle:
        duration = handle.getnframes() / handle.getframerate()
    return {
        "safe_id": safe_id,
        "private_source_id": owner_audio.name,
        "private_participant_id": "owner",
        "source_state": "owner_controlled_integration_only",
        "original_audio_sha256": file_sha256(owner_audio),
        "canonical_audio_path": wav_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "canonical_audio_sha256": file_sha256(wav_path),
        "sample_rate_hz": 16000,
        "channels": 1,
        "duration_s": round(duration, 6),
        "intended_text_state": "unknown",
        "eligible_tools": ["phoneticxeus", "panphon"],
    }


def prepare(ffmpeg, owner_audio):
    archives = {
        "speechocean762": (
            PRIVATE_ROOT / "corpora" / "speechocean762_v1_2_0" / "speechocean762.tar.gz"
        ),
        "common_phone_1_0": (
            PRIVATE_ROOT / "corpora" / "common_phone_1_0" / "cp-1-0.tgz"
        ),
        "common_voice_26_australian_english": (
            PRIVATE_ROOT
            / "corpora"
            / "common_voice_26_au"
            / "common-voice-scripted-speech-26-0-austra-c6a1c1a1.tar.gz"
        ),
    }
    sources = []
    source_records = {
        "speechocean762": _speechocean_records(),
        "common_phone_1_0": _common_phone_records(),
        "common_voice_26_australian_english": _common_voice_records(),
    }
    for source_id, records in source_records.items():
        extracted = _extract_tar_members(
            archives[source_id], {record["member"] for record in records}
        )
        suffix = ".mp3" if source_id == "common_voice_26_australian_english" else ".wav"
        clips = [
            _build_clip(
                source_id,
                index,
                record,
                extracted[record["member"]],
                suffix,
                ffmpeg,
                "development",
            )
            for index, record in enumerate(records, start=1)
        ]
        sources.append(
            {
                "source_id": source_id,
                "independent_accuracy_evidence": False,
                "clips": clips,
            }
        )

    acted_records = _acted_clear_records()
    acted_archive = (
        PRIVATE_ROOT
        / "corpora"
        / "acted_clear_speech_2013"
        / "clear_speech_wavs.zip"
    )
    with zipfile.ZipFile(acted_archive) as archive:
        acted_clips = [
            _build_clip(
                "acted_clear_speech_2013",
                index,
                record,
                archive.read(record["member"]),
                ".wav",
                ffmpeg,
                "fixture_not_population_evidence",
            )
            for index, record in enumerate(acted_records, start=1)
        ]
    sources.append(
        {
            "source_id": "acted_clear_speech_2013",
            "independent_accuracy_evidence": False,
            "clips": acted_clips,
        }
    )
    sources.append(
        {
            "source_id": "owner_controlled_integration",
            "independent_accuracy_evidence": False,
            "clips": [_owner_record(owner_audio, ffmpeg)],
        }
    )
    sources.sort(key=lambda item: item["source_id"])
    document = {
        "schema_version": FEASIBILITY_SCHEMA_VERSION,
        "protocol_id": "speech_sound_local_feasibility_v1",
        "selection_seed": SELECTION_SEED,
        "development_only": True,
        "sources": sources,
    }
    errors = validate_private_sample_manifest(document, REPOSITORY_ROOT)
    if errors:
        raise ValueError("; ".join(errors))
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(document)
    if hashlib.sha256(payload).hexdigest() != FROZEN_SAMPLE_MANIFEST_SHA256:
        raise ValueError("prepared private sample does not match the frozen identity")
    MANIFEST_PATH.write_bytes(payload)
    return document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", required=True, type=Path)
    parser.add_argument("--owner-audio", required=True, type=Path)
    args = parser.parse_args()
    document = prepare(args.ffmpeg.resolve(), args.owner_audio.resolve())
    clip_count = sum(len(item["clips"]) for item in document["sources"])
    print(f"Prepared {clip_count} private development and integration clips.")
    print(f"Private manifest: {MANIFEST_PATH.relative_to(REPOSITORY_ROOT)}")
    print("No tuning or held-out participant was inspected.")


if __name__ == "__main__":
    main()
