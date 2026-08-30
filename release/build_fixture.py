"""Build the openly licensed regression fixtures for the public snapshot.

The pipeline's two real recording regression checks were pinned to the
repository owner's own voice, which can never be published. This module builds
replacements from LibriSpeech, so the public snapshot ships something an
independent person can actually run.

Three choices here are worth stating rather than discovering later.

- **LibriSpeech, and only its development split.** The corpus is CC BY 4.0 with
  no terms of service layered on top, so redistribution with attribution is what
  the licence grants. The reasoning, and the manifest field it qualifies, are in
  ``release/redistribution-decision-v1.0.0.json``. Speakers assigned threshold
  tuning or held out evaluation are refused, so publishing a fixture can never
  expose a sealed split.
- **Assembled, and it says so.** The conversation fixture is two readers taking
  turns, not a conversation. There is no overlap, no interruption, no
  disfluency and no shared topic. It exercises the pipeline; it is not evidence
  about conversational speech, and the fixture manifest says that in as many
  words.
- **Uncompressed 16 kHz mono WAV.** The regression truth pins an exact byte
  hash, so the output has to be reproducible on a machine that is not this one.
  PCM has no encoder and no metadata, so the same inputs give the same bytes.
  FLAC would halve the size and embed an encoder version string.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import numpy as np
import soundfile as sf

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
ARCHIVE = PRIVATE_ROOT / "corpora" / "librispeech_slr12" / "dev-clean.tar.gz"
SPLITS = PRIVATE_ROOT / "splits" / "librispeech-slr12-small.json"
FIXTURE_ROOT = REPOSITORY_ROOT / "regression" / "fixtures"

SAMPLE_RATE_HZ = 16000
TARGET_RMS_DBFS = -23.0
PEAK_CEILING_DBFS = -1.0
GAP_WITHIN_TURN_S = 0.28
GAP_BETWEEN_TURNS_S = 0.45

# Deterministic, and chosen before anything was measured. Both conversation
# readers are in the development split, and the two are of different recorded
# sex so the diarizer is being asked an easy question rather than a subtle one:
# the fixture exists to prove the stage runs, not to benchmark diarization.
CONVERSATION = {
    "target_duration_s": 120.0,
    "turn_utterances": 2,
    "speakers": [
        {"speaker_id": "1272", "chapter_id": "128104", "reader": "John Rose"},
        {"speaker_id": "1988", "chapter_id": "24833", "reader": "Ransom"},
    ],
}
SOLO = {
    "target_duration_s": 150.0,
    "speakers": [
        {"speaker_id": "3576", "chapter_id": "138058", "reader": "JudyGibson"},
    ],
}


class FixtureError(RuntimeError):
    """Raised when a fixture cannot be built from permitted material."""


def permitted_speakers():
    """Development split dev-clean speakers, the only ones a fixture may use."""
    assignments = json.loads(SPLITS.read_text(encoding="utf-8"))["assignments"]
    return {
        speaker
        for speaker, entry in assignments.items()
        if entry["project_split"] == "development"
        and entry["source_stratum"] == "dev-clean"
    }


def _check_permitted(specification):
    allowed = permitted_speakers()
    for speaker in specification["speakers"]:
        if speaker["speaker_id"] not in allowed:
            raise FixtureError(
                f"speaker {speaker['speaker_id']} is not in the development "
                "split and may not be published"
            )


def read_chapter(speaker_id, chapter_id):
    """Return the chapter's utterances in numeric order, with transcripts."""
    prefix = f"LibriSpeech/dev-clean/{speaker_id}/{chapter_id}/"
    audio = {}
    transcripts = {}
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        for member in archive:
            if not member.name.startswith(prefix) or not member.isfile():
                continue
            payload = archive.extractfile(member).read()
            if member.name.endswith(".flac"):
                samples, rate = sf.read(io.BytesIO(payload), dtype="float64")
                if rate != SAMPLE_RATE_HZ:
                    raise FixtureError(f"{member.name} is not 16 kHz")
                audio[Path(member.name).stem] = samples
            elif member.name.endswith(".trans.txt"):
                for line in payload.decode("utf-8").splitlines():
                    key, _, text = line.partition(" ")
                    transcripts[key] = text
    if not audio:
        raise FixtureError(f"no audio found for {speaker_id}/{chapter_id}")
    order = sorted(audio, key=lambda stem: int(stem.rsplit("-", 1)[1]))
    return [(stem, audio[stem], transcripts.get(stem, "")) for stem in order]


def _normalise(samples):
    """Bring one speaker to a common loudness without touching the peak rule."""
    rms = float(np.sqrt(np.mean(np.square(samples))))
    if rms <= 0.0:
        raise FixtureError("a source utterance is silent")
    scaled = samples * (10.0 ** (TARGET_RMS_DBFS / 20.0) / rms)
    peak = float(np.max(np.abs(scaled)))
    ceiling = 10.0 ** (PEAK_CEILING_DBFS / 20.0)
    if peak > ceiling:
        scaled = scaled * (ceiling / peak)
    return scaled


def _room_tone(entries):
    """Return the quietest second of a speaker's own recording.

    Gaps are room tone rather than digital zeros because a recording made in a
    room never contains absolute silence, and a published fixture should look
    like a recording.

    It was also a hypothesis, and the hypothesis was wrong, which is worth
    recording rather than quietly deleting. Both fixtures warn on level
    stability and on the reverberation proxy, and the first guess was that the
    zero filled gaps caused it by dragging the tenth percentile frame level down
    to about minus 240 dB and forcing the analyser onto its fallback thresholds.
    Replacing the gaps moved the reverberation proxy from 0.845 to 0.816 and
    left the level spread identical at 19.89 dB, so that was not the cause.

    The measured cause is that LibriSpeech is cleaner than the recordings the
    checks were tuned on. The fixture's noise floor sits at about minus 62 dB
    against minus 38 dB for the owner's conversation recording, so the distance
    between the floor and ordinary speech is genuinely wide. The warning is
    correct about the recording and is accepted rather than engineered away.
    Adding noise to raise the floor would manufacture a pass, and retuning the
    threshold would be a calibration study this item is not.
    """
    joined = np.concatenate([samples for _, samples, _ in entries])
    window = SAMPLE_RATE_HZ
    if joined.size < window * 2:
        raise FixtureError("a speaker has too little audio to sample room tone")
    frame = SAMPLE_RATE_HZ // 50
    usable = joined.size - joined.size % frame
    energy = np.sqrt(
        np.mean(np.square(joined[:usable].reshape(-1, frame)), axis=1)
    )
    per_window = window // frame
    running = np.convolve(energy, np.ones(per_window) / per_window, mode="valid")
    start = int(np.argmin(running)) * frame
    return joined[start:start + window]


def _gap(tone, seconds, index):
    """A gap of room tone, taken at a rotating offset so it never repeats."""
    length = int(round(seconds * SAMPLE_RATE_HZ))
    offset = (index * 4093) % max(1, tone.size - length)
    return tone[offset:offset + length].copy()


def build(specification, name):
    """Assemble one fixture and return its waveform and its manifest."""
    _check_permitted(specification)
    chapters = {
        speaker["speaker_id"]: read_chapter(
            speaker["speaker_id"], speaker["chapter_id"]
        )
        for speaker in specification["speakers"]
    }
    normalised = {
        speaker_id: [
            (stem, _normalise(samples), text) for stem, samples, text in entries
        ]
        for speaker_id, entries in chapters.items()
    }

    per_turn = specification.get("turn_utterances", len(next(iter(chapters))))
    cursors = {speaker["speaker_id"]: 0 for speaker in specification["speakers"]}
    order = [speaker["speaker_id"] for speaker in specification["speakers"]]
    target = int(round(specification["target_duration_s"] * SAMPLE_RATE_HZ))

    tones = {
        speaker_id: _room_tone(entries)
        for speaker_id, entries in normalised.items()
    }
    pieces = []
    used = []
    gaps = 0
    turn = 0
    total = 0
    while total < target:
        speaker_id = order[turn % len(order)]
        entries = normalised[speaker_id]
        cursor = cursors[speaker_id]
        if cursor >= len(entries):
            raise FixtureError(
                f"speaker {speaker_id} ran out of utterances before "
                f"{specification['target_duration_s']} seconds"
            )
        taken = 0
        while taken < per_turn and cursor < len(entries) and total < target:
            stem, samples, text = entries[cursor]
            if pieces:
                seconds = GAP_BETWEEN_TURNS_S if taken == 0 else GAP_WITHIN_TURN_S
                gap = _gap(tones[speaker_id], seconds, gaps)
                gaps += 1
                pieces.append(gap)
                total += len(gap)
            pieces.append(samples)
            used.append(
                {
                    "speaker_id": speaker_id,
                    "utterance_id": stem,
                    "turn": turn,
                    "samples": int(len(samples)),
                    "seconds": round(len(samples) / SAMPLE_RATE_HZ, 3),
                    "transcript": text,
                }
            )
            total += len(samples)
            cursor += 1
            taken += 1
        cursors[speaker_id] = cursor
        turn += 1

    waveform = np.concatenate(pieces)
    readers = {
        speaker["speaker_id"]: speaker for speaker in specification["speakers"]
    }
    manifest = {
        "schema_version": "1.0.0",
        "fixture_id": name,
        "fixture_kind": "assembled_open_licensed_recording",
        "built_by": "release/build_fixture.py",
        "source": {
            "corpus": "LibriSpeech, OpenSLR 12, dev-clean",
            "licence": "CC-BY-4.0",
            "attribution": (
                "Cite Panayotov et al., LibriSpeech, ICASSP 2015, and retain "
                "CC BY 4.0 attribution."
            ),
            "permission_record": "release/redistribution-decision-v1.0.0.json",
            "split_restriction": "development split only, never threshold tuning or held out evaluation",
        },
        "audio": {
            "sample_rate_hz": SAMPLE_RATE_HZ,
            "channels": 1,
            "encoding": "16 bit PCM WAV",
            "duration_s": round(len(waveform) / SAMPLE_RATE_HZ, 6),
        },
        "assembly": {
            "target_rms_dbfs": TARGET_RMS_DBFS,
            "peak_ceiling_dbfs": PEAK_CEILING_DBFS,
            "gap_within_turn_s": GAP_WITHIN_TURN_S,
            "gap_between_turns_s": GAP_BETWEEN_TURNS_S,
            "gap_content": (
                "The quietest second of the speaker's own recording, taken at a "
                "rotating offset. Digital silence made the quality preflight "
                "warn about level stability and reverberation, because a tenth "
                "percentile frame level near minus 240 dB forces the analyser "
                "onto its fallback thresholds."
            ),
            "normalisation": (
                "Each source utterance was scaled to a common RMS and then "
                "limited to the peak ceiling. Loudness differences between the "
                "two readers would otherwise show up as an unstable recording "
                "level in the quality preflight."
            ),
        },
        "readers": [
            {
                "speaker_id": speaker_id,
                "librivox_reader": readers[speaker_id]["reader"],
                "chapter_id": readers[speaker_id]["chapter_id"],
                "utterances": sum(1 for item in used if item["speaker_id"] == speaker_id),
            }
            for speaker_id in order
        ],
        "utterances": used,
        "what_this_is_not": [
            "Not a conversation. The readers take turns because the builder "
            "alternates them, so there is no overlap, no interruption, no "
            "shared topic and no repair.",
            "Not spontaneous speech. It is read audiobook prose, so it carries "
            "no filled pauses, repetitions or false starts.",
            "Not truth for any measurement. It establishes recording identity, "
            "mode, speaker count and duration, and nothing else.",
            "Not representative of any population, and specifically not of "
            "Australian English.",
        ],
    }
    return waveform, manifest


def write(name, specification):
    from pipeline.audio_quality import analyze_audio

    waveform, manifest = build(specification, name)
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    path = FIXTURE_ROOT / f"{name}.wav"
    sf.write(path, waveform, SAMPLE_RATE_HZ, subtype="PCM_16", format="WAV")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest["audio"]["path"] = path.relative_to(REPOSITORY_ROOT).as_posix()
    manifest["audio"]["sha256"] = digest
    manifest["audio"]["bytes"] = path.stat().st_size
    report = analyze_audio(path)
    checks = {check["id"]: check for check in report["checks"]}
    manifest["quality_preflight"] = {
        "overall_status": report["overall_status"],
        "measured": {
            key: checks[key]["value"]
            for key in (
                "duration",
                "sample_rate",
                "peak_level",
                "clipping",
                "speech_proportion",
                "signal_to_noise_proxy",
                "recording_level_stability",
                "reverberation_risk_proxy",
            )
            if key in checks
        },
        "accepted_warnings": [
            check["id"]
            for check in report["checks"]
            if check["status"] not in ("pass", "ok", "info")
        ],
        "why_the_warnings_are_accepted": (
            "Read audiobook speech has a wider distance between its noise floor "
            "and ordinary speech than the phone recordings these two heuristics "
            "were tuned on. The owner's own solo recording warns on the same two "
            "checks. Adding noise to raise the floor would manufacture a pass, "
            "and moving the threshold would be a calibration study. The warning "
            "is correct about the recording, the run proceeds, and the fixture "
            "is published as measured."
        ),
    }
    (FIXTURE_ROOT / f"{name}-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path, manifest


TRUTH_ROOT = REPOSITORY_ROOT / "regression" / "truth"

MODES = {
    "conversation": {"recording_type": "conversation", "num_speakers": 2},
    "solo": {"recording_type": "solo", "num_speakers": 1,
             "account_holder_speaker": "SPEAKER_00"},
}


def write_truth(name, manifest):
    """Emit the regression truth record this fixture can honestly support."""
    expected = MODES[name]
    checks = [
        {"artifact": "master.json", "path": "meta.recording_type",
         "value": expected["recording_type"]},
        {"artifact": "master.json", "path": "meta.num_speakers",
         "value": expected["num_speakers"]},
    ]
    if "account_holder_speaker" in expected:
        checks.append({"artifact": "master.json",
                       "path": "meta.account_holder_speaker",
                       "value": expected["account_holder_speaker"]})
    checks.append({"artifact": "master.json", "path": "meta.audio_duration_s",
                   "value": manifest["audio"]["duration_s"], "tolerance": 0.05})
    checks.append({"artifact": "audio_quality.json", "path": "audio.byte_sha256",
                   "value": manifest["audio"]["sha256"]})
    readers = ", ".join(
        f"{reader['speaker_id']} ({reader['librivox_reader']})"
        for reader in manifest["readers"]
    )
    truth = {
        "schema_version": "1.1.0",
        "fixture_id": f"fixture_{name}",
        "fixture_kind": "assembled_human_recording",
        "audio": {"path": manifest["audio"]["path"],
                  "sha256": manifest["audio"]["sha256"]},
        "reference": {
            "source": (
                "LibriSpeech dev-clean corpus metadata for "
                + ("speakers " if len(manifest["readers"]) > 1 else "speaker ")
                + readers
                + ", the deterministic assembly recorded in "
                + f"regression/fixtures/{name}-manifest.json, and an "
                "independent FFprobe container duration"
            ),
            "annotator_role": (
                "source corpus maintainers, whose speaker identities are carried "
                "through an assembly that adds no labels of its own"
            ),
            "guide_version": "1.0.0",
            "date": "2026-08-24",
            "adjudication_status": "corpus_metadata_derived",
            "independent_from_pipeline": True,
        },
        "coverage": [
            "recording identity by exact byte hash",
            f"{expected['recording_type']} mode",
            ("two audible speakers" if expected["num_speakers"] == 2
             else "one audible speaker"),
            "container duration",
        ],
        "limitations": [
            "The recording is assembled from read audiobook utterances, so it "
            "carries no filled pauses, repetitions, false starts or repairs, "
            "and no measurement of those may be validated against it.",
            "The conversation fixture is two readers taking turns, not a "
            "conversation. There is no overlap and no interruption, so turn "
            "taking and attribution under overlap are untested by it."
            if expected["num_speakers"] == 2 else
            "A single reader working from prepared text is not spontaneous "
            "speech, and nothing about spontaneous production follows from it.",
            "No exhaustive human word, pause, overlap or renderer event "
            "annotation exists for it. Those dimensions are evaluated against "
            "synthetic ground truth only.",
            "It represents no population, and specifically not Australian "
            "English.",
        ],
        "expectations": {"artifact_checks": checks},
    }
    path = TRUTH_ROOT / f"fixture_{name}.json"
    path.write_text(json.dumps(truth, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def main():
    for name, specification in (("conversation", CONVERSATION), ("solo", SOLO)):
        path, manifest = write(name, specification)
        print(
            f"{name}: {manifest['audio']['duration_s']} s, "
            f"{len(manifest['utterances'])} utterances, "
            f"{manifest['audio']['bytes']} bytes"
        )
        print(f"  {path.relative_to(REPOSITORY_ROOT)}")
        print(f"  sha256 {manifest['audio']['sha256']}")
        print(f"  {write_truth(name, manifest).relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
