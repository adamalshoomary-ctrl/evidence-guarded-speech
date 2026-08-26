"""Checkpoint 22E8 sampling for the reference variety probe.

Chooses which speakers and clips the probe measures, before anything is scored
and without reading a single result. Selection is deterministic from a declared
seed, so the sample cannot be quietly reshaped after seeing an outcome.

Three rules do the real work here:

- **Development partitions only.** Threshold tuning and the sealed held-out
  speakers are untouched, in every group.
- **Equal groups.** The four subsets differ in size by a factor of seven. The
  same number of speakers and clips is drawn from each, so a per consonant rate
  is not dominated by whichever group happens to be largest.
- **Paired.** A clip is kept only if its prompt is fully covered by both
  dictionaries. Comparing two references on two different samples would confound
  the reference with the sample, which is the mistake this design exists to
  avoid.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .corpus_audit import SOURCE_SPLIT_TO_PROJECT, _metadata_rows
from .corpus_manifest import REPOSITORY_ROOT
from .variety_reference import (
    VarietyReferenceError,
    expected_sequence,
    load_australian_overlay,
    load_dictionary,
    load_model_vocabulary,
    vocabulary_index,
)

PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
METADATA_ROOT = PRIVATE_ROOT / "metadata"
EXCLUSION_RECORD = PRIVATE_ROOT / "splits" / "common-voice-26-accent-group-exclusions.json"
CONTRACT_PATH = Path(__file__).with_name("variety-probe-contract-v1.0.0.json")

GROUP_METADATA = {
    "common_voice_26_australian_english": "common_voice_26_au",
    "common_voice_26_british_english": "common_voice_26_gb",
    "common_voice_26_american_english_male": "common_voice_26_us_male",
    "common_voice_26_american_english_female": "common_voice_26_us_female",
}

# The two American subsets are one control group. Neither may stand alone,
# because accent and speaker gender would otherwise vary together.
REPORTING_GROUPS = {
    "australian": ["common_voice_26_australian_english"],
    "british": ["common_voice_26_british_english"],
    "american": [
        "common_voice_26_american_english_male",
        "common_voice_26_american_english_female",
    ],
}


class VarietyProbeError(RuntimeError):
    """Raised when a sample cannot be drawn honestly."""


def load_contract(path=CONTRACT_PATH):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    boundaries = contract["release_boundaries"]
    if any(boundaries[flag] for flag in boundaries):
        raise VarietyProbeError(
            "the probe contract must keep every release boundary closed"
        )
    return contract


def excluded_participants(path=EXCLUSION_RECORD):
    if not Path(path).is_file():
        raise VarietyProbeError(
            "the accent group exclusion record is missing; a contributor who "
            "declared two varieties would otherwise sit in both groups"
        )
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return set(document["excluded_participants"])


def _order(seed, group, identifier):
    value = f"{group}\0{seed}\0{identifier}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _references():
    index = vocabulary_index(load_model_vocabulary())
    overlay = load_australian_overlay()
    return {
        "american": (load_dictionary("english_us_mfa"), index, None),
        "british": (load_dictionary("english_uk_mfa"), index, overlay),
    }


def prompt_is_paired(sentence, references):
    """Keep a prompt only if both references can express it whole."""
    sequences = {}
    for name, (dictionary, index, overlay) in references.items():
        sequence, reason = expected_sequence(sentence, dictionary, index, overlay)
        if sequence is None:
            return None, f"{name}:{reason}"
        sequences[name] = sequence
    return sequences, None


def sample_group(
    source_id,
    references,
    excluded,
    speakers,
    clips_per_speaker,
    seed,
    metadata_root=METADATA_ROOT,
):
    """Draw a deterministic development-partition sample from one subset."""
    root = Path(metadata_root) / GROUP_METADATA[source_id]
    if not root.is_dir():
        raise VarietyProbeError(f"{source_id} metadata is not extracted")
    by_speaker = {}
    refusals = {}
    for row in _metadata_rows(root):
        if SOURCE_SPLIT_TO_PROJECT[row["source_split"]] != "development":
            continue
        if row["client_id"] in excluded:
            continue
        sequences, reason = prompt_is_paired(row["sentence"], references)
        if sequences is None:
            refusals[reason] = refusals.get(reason, 0) + 1
            continue
        by_speaker.setdefault(row["client_id"], []).append(
            {
                "clip": row["path"],
                "sentence": row["sentence"],
                "expected": {
                    name: sequence["tokens"] for name, sequence in sequences.items()
                },
            }
        )
    eligible = sorted(
        (person for person, items in by_speaker.items() if len(items) >= clips_per_speaker),
        key=lambda person: _order(seed, source_id, person),
    )
    if len(eligible) < speakers:
        raise VarietyProbeError(
            f"{source_id} has {len(eligible)} eligible development speakers, "
            f"fewer than the {speakers} the contract requires"
        )
    chosen = []
    for person in eligible[:speakers]:
        items = sorted(
            by_speaker[person], key=lambda item: _order(seed, source_id, item["clip"])
        )
        for item in items[:clips_per_speaker]:
            chosen.append({"source_id": source_id, "participant": person, **item})
    return {
        "clips": chosen,
        "eligible_speakers": len(eligible),
        "refusals": dict(sorted(refusals.items(), key=lambda item: -item[1])[:8]),
    }


ARCHIVE_ROOT = PRIVATE_ROOT / "corpora"
CLIP_ROOT = PRIVATE_ROOT / "variety-probe" / "clips"

GROUP_ARCHIVES = {
    "common_voice_26_australian_english": (
        "common_voice_26_au",
        "common-voice-scripted-speech-26-0-austra-c6a1c1a1.tar.gz",
    ),
    "common_voice_26_british_english": (
        "common_voice_26_gb",
        "common-voice-scripted-speech-26-0-britis-0fe481c3.tar.gz",
    ),
    "common_voice_26_american_english_male": (
        "common_voice_26_us_male",
        "common-voice-scripted-speech-26-0-americ-34c3c133.tar.gz",
    ),
    "common_voice_26_american_english_female": (
        "common_voice_26_us_female",
        "common-voice-scripted-speech-26-0-americ-079c33be.tar.gz",
    ),
}


def extract_sample_clips(sample, archive_root=ARCHIVE_ROOT, clip_root=CLIP_ROOT):
    """Pull only the sampled clips out of each archive, in one pass each.

    A tar stream is sequential, so the archive is read once and every wanted
    member is taken as it goes past. Nothing else is unpacked, which is why
    holding the corpora costs one archive per subset rather than twice that.
    """
    import tarfile

    extracted = {}
    for source_id, group in sample["groups"].items():
        wanted = {item["clip"] for item in group["clips"]}
        directory = Path(clip_root) / source_id
        directory.mkdir(parents=True, exist_ok=True)
        present = {path.name for path in directory.glob("*.mp3")}
        outstanding = wanted - present
        if outstanding:
            folder, filename = GROUP_ARCHIVES[source_id]
            archive_path = Path(archive_root) / folder / filename
            if not archive_path.is_file():
                raise VarietyProbeError(f"{source_id} archive is not acquired")
            with tarfile.open(archive_path, "r|gz") as archive:
                for member in archive:
                    name = Path(member.name).name
                    if not member.isfile() or name not in outstanding:
                        continue
                    handle = archive.extractfile(member)
                    if handle is None:
                        raise VarietyProbeError(f"{name} is unreadable in {filename}")
                    (directory / name).write_bytes(handle.read())
                    outstanding.discard(name)
                    if not outstanding:
                        break
        if outstanding:
            raise VarietyProbeError(
                f"{source_id} is missing {len(outstanding)} sampled clips"
            )
        extracted[source_id] = len(wanted)
    return extracted


CANONICAL_ROOT = PRIVATE_ROOT / "variety-probe" / "canonical"
CANONICAL_RATE = 16000


def canonicalise_clips(sample, clip_root=CLIP_ROOT, canonical_root=CANONICAL_ROOT):
    """Resample the sampled clips to the one format the frozen model accepts.

    Common Voice ships 48 kHz mono MP3 and the model requires 16 kHz mono. The
    conversion is identical for every group, so it cannot favour one of them,
    and it is done once rather than inside the scoring loop.
    """
    import numpy as np
    import soundfile
    from scipy.signal import resample_poly

    converted = {}
    for source_id, group in sample["groups"].items():
        source = Path(clip_root) / source_id
        target = Path(canonical_root) / source_id
        target.mkdir(parents=True, exist_ok=True)
        count = 0
        for item in group["clips"]:
            destination = target / (Path(item["clip"]).stem + ".wav")
            if destination.is_file():
                count += 1
                continue
            waveform, rate = soundfile.read(
                source / item["clip"], dtype="float64", always_2d=False
            )
            if waveform.ndim != 1:
                waveform = waveform.mean(axis=1)
            if rate != CANONICAL_RATE:
                divisor = np.gcd(int(rate), CANONICAL_RATE)
                waveform = resample_poly(
                    waveform, CANONICAL_RATE // divisor, int(rate) // divisor
                )
            if waveform.size == 0 or not np.isfinite(waveform).all():
                raise VarietyProbeError(f"{item['clip']} is empty or not finite")
            soundfile.write(
                destination, waveform.astype(np.float32), CANONICAL_RATE, subtype="FLOAT"
            )
            count += 1
        converted[source_id] = count
    return converted


def build_sample(contract=None, metadata_root=METADATA_ROOT):
    """Draw the whole probe sample, one group at a time, and record why."""
    contract = contract or load_contract()
    sampling = contract["sampling"]
    if sampling["held_out_access_allowed"] or sampling["threshold_tuning_access_allowed"]:
        raise VarietyProbeError("the contract may not open a sealed partition")
    references = _references()
    excluded = excluded_participants()
    groups = {}
    for source_id in GROUP_METADATA:
        groups[source_id] = sample_group(
            source_id,
            references,
            excluded,
            sampling["speakers_per_group"],
            sampling["clips_per_speaker"],
            sampling["seed"],
            metadata_root,
        )
    return {
        "seed": sampling["seed"],
        "speakers_per_group": sampling["speakers_per_group"],
        "clips_per_speaker": sampling["clips_per_speaker"],
        "excluded_participants": sorted(excluded),
        "groups": groups,
    }
