"""Build the publishable per clip evidence bundle for the variety probe.

The probe's numbers were previously checkable only by someone holding the
private research data: a multi gigabyte Common Voice download and about three
and a half hours of inference. This module turns the stored evidence into a
5.8 MB bundle that regenerates the committed report exactly, needing no audio,
no model and no credentials.

**No Common Voice audio is redistributed, and none may be.** The decoded clips
and the canonicalised waveforms stay private. What travels is the derived
measurement record: frame counts, phone tokens, phone indices and goodness of
pronunciation scores. The permission, its scope and its reasoning are in
``release/redistribution-decision-v1.0.0.json``.

The pseudonymisation is not cosmetic. Stored evidence carries each contributor's
verbatim Common Voice ``client_id``, which joins straight back to the public
corpus and recovers that person's whole clip history, declared accent, age and
gender. Publishing that would breach the platform terms and the project's own
prohibition on speaker re identification. The bundle mints opaque keys instead,
and the mapping is never written to disk.

Two constraints make the substitution safe rather than merely plausible, and
both are asserted here rather than assumed:

- **Keys must be globally unique.** ``variety_probe_score._speaker_rates``
  groups by the participant value alone, while every other call site groups by
  source and participant together. Real Common Voice identifiers are unique
  across groups so the inconsistency never mattered. A scheme that numbered
  speakers within each source directory collapsed the American reporting group,
  which merges two directories, from 600 speakers to 300.
- **Sort order must be preserved**, both of the ``(source_id, participant)``
  pairs and of the evidence file paths. The speaker clustered bootstrap indexes
  speakers in sorted order, so reordering either would change the resamples and
  move every published interval.
"""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PRIVATE_EVIDENCE = (
    REPOSITORY_ROOT
    / ".research_data"
    / "speech_sound_patterns"
    / "variety-probe"
    / "evidence"
)
BUNDLE_ROOT = REPOSITORY_ROOT / "speech_sound_patterns" / "variety-probe-evidence"
REPORT = REPOSITORY_ROOT / "speech_sound_patterns" / "variety-probe-v1.2.0.json"

GROUP_CODES = {
    "common_voice_26_american_english_female": "amf",
    "common_voice_26_american_english_male": "amm",
    "common_voice_26_australian_english": "aus",
    "common_voice_26_british_english": "gbr",
}

# Fields that may leave the private research data. Anything else in a stored
# record is refused rather than silently dropped, so a future field cannot be
# published by accident.
PERMITTED_FIELDS = {"clip", "frames", "participant", "source_id", "references"}


class BundleError(RuntimeError):
    """Raised when evidence cannot be published as it stands."""


def _load_private():
    paths = sorted(PRIVATE_EVIDENCE.glob("*/*.json"))
    if not paths:
        raise BundleError(f"no stored evidence under {PRIVATE_EVIDENCE}")
    records = []
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        unexpected = sorted(set(record) - PERMITTED_FIELDS)
        if unexpected:
            raise BundleError(
                f"{path.name} carries unpublishable fields: {', '.join(unexpected)}"
            )
        if record["source_id"] not in GROUP_CODES:
            raise BundleError(f"{path.name} has an unknown source {record['source_id']}")
        records.append((path, record))
    return records


def _speaker_keys(records):
    """Opaque keys that are globally unique and preserve the original order."""
    pairs = sorted({(record["source_id"], record["participant"]) for _, record in records})
    keys = {}
    counter = collections.Counter()
    for source_id, participant in pairs:
        index = counter[source_id]
        counter[source_id] += 1
        keys[(source_id, participant)] = f"spk_{GROUP_CODES[source_id]}_{index:05d}"
    if len(set(keys.values())) != len(keys):
        raise BundleError("speaker keys are not globally unique")
    reordered = sorted({(source, keys[(source, person)]) for source, person in pairs})
    if reordered != [(source, keys[(source, person)]) for source, person in pairs]:
        raise BundleError("speaker keys do not preserve the original sort order")
    return keys


def build():
    records = _load_private()
    keys = _speaker_keys(records)

    if BUNDLE_ROOT.exists():
        for stale in sorted(BUNDLE_ROOT.glob("*/*.json")):
            stale.unlink()

    sequence = collections.Counter()
    written = []
    for _, record in records:
        source_id = record["source_id"]
        code = GROUP_CODES[source_id]
        index = sequence[source_id]
        sequence[source_id] += 1
        name = f"clip_{code}_{index:05d}"
        record["participant"] = keys[(source_id, record["participant"])]
        record["clip"] = f"{name}.mp3"
        directory = BUNDLE_ROOT / source_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.json"
        path.write_text(
            json.dumps(record, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        written.append(path)

    expected = [
        f"clip_{GROUP_CODES[source]}_{index:05d}.json"
        for source in sorted(sequence)
        for index in range(sequence[source])
    ]
    if [path.name for path in sorted(BUNDLE_ROOT.glob("*/*.json"))] != expected:
        raise BundleError("bundle file order does not match the private evidence")
    return written, keys, sequence


def _digest(paths):
    running = hashlib.sha256()
    for path in sorted(paths):
        running.update(path.relative_to(BUNDLE_ROOT).as_posix().encode("utf-8"))
        running.update(path.read_bytes())
    return running.hexdigest()


def main():
    written, keys, sequence = build()
    digest = _digest(written)
    total = sum(path.stat().st_size for path in written)
    manifest = {
        "schema_version": "1.0.0",
        "bundle_id": "variety_probe_evidence_v1",
        "built_by": "release/build_evidence_bundle.py",
        "permission_record": "release/redistribution-decision-v1.0.0.json",
        "records": len(written),
        "speakers": len(keys),
        "bytes": total,
        "composite_sha256": digest,
        "reproduces": {
            "report": "speech_sound_patterns/variety-probe-v1.2.0.json",
            "report_sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(),
            "command": "python3 -m speech_sound_patterns.variety_probe_score",
            "runtime": "about two minutes, needing only numpy",
        },
        "contains": [
            "per clip frame counts",
            "phone tokens and their index within the expected sequence",
            "goodness of pronunciation scores under both references",
            "the declared accent group, as the directory name",
        ],
        "does_not_contain": [
            "any audio",
            "any prompt text or transcript",
            "any Common Voice contributor identifier",
            "any mapping from a bundle key back to a contributor",
            "any Common Voice metadata row",
        ],
        "per_group": {source: sequence[source] for source in sorted(sequence)},
    }
    (BUNDLE_ROOT / "bundle-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"records {len(written)}, speakers {len(keys)}, {total} bytes")
    print(f"composite sha256 {digest}")
    for source in sorted(sequence):
        print(f"  {source}: {sequence[source]}")


if __name__ == "__main__":
    main()
