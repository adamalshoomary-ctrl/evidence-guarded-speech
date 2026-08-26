"""Extract the expert relation truth for the powered checkpoint 22E4B sample.

The checkpoint 22D scorer builds truth rows and PhoneticXEUS prediction rows in
one pass, so it cannot run without a candidate system. The powered replication
needs the truth alone: its candidates are the frozen checkpoint 22E4 lanes, and
the rejected greedy PhoneticXEUS path must not be run again on 2,280 clips just
to obtain a denominator.

Nothing about the truth is redefined here. The consensus rule, the scorable
phone scope, the reviewer parsing and the positive, negative and unscorable
states are the same functions the checkpoint 22D scorer calls, imported rather
than copied. ``tests/test_speech_sound_powered_sample.py`` runs this module over
the frozen checkpoint 22E4 manifest and requires every row to match the committed
private evidence exactly, so a silent redefinition fails before the powered
sample is used.

Only the coarse target relation class is extracted, because that is the only
class the frozen gates use and the only class checkpoint 22E4 scored. The
checkpoint 22D insertion and aggregate exact substitution classes are unchanged
historical evidence and are not part of this replication.

This module reads expert outcomes. No candidate runner may import it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import (
    PRIVATE_BENCHMARK_ROOT,
    canonical_json_sha256,
    load_phone_map,
    parse_review_phone_string,
    scorable_reference_phone,
    strip_stress,
    target_consensus,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256
from .score_benchmark import _age_stratum, _load_verified, _source, _truth_state


TRUTH_ROW_FIELDS = (
    "safe_id",
    "private_participant_id",
    "project_split",
    "age_stratum",
    "source_stratum",
    "word_index",
    "target_index",
    "reference_phone",
    "reviewer_states",
    "reference_decision",
    "truth",
)
POWERED_MANIFEST_PATH = PRIVATE_BENCHMARK_ROOT / "benchmark-manifest-v1.1.0.json"
POWERED_TRUTH_PATH = (
    PRIVATE_BENCHMARK_ROOT
    / "v2"
    / "evidence"
    / "scoring"
    / "speechocean-relation-evidence.json"
)
FROZEN_TRUTH_PATH = (
    PRIVATE_BENCHMARK_ROOT
    / "v1"
    / "evidence"
    / "scoring"
    / "speechocean-relation-evidence.json"
)


class RelationTruthError(ValueError):
    """Raised when the expert relation truth cannot be trusted."""


def relation_truth_rows(manifest, phone_map=None):
    """Return one row per scorable expected consonant target, truth only.

    This is the truth half of ``score_benchmark.score_speechocean``, with the
    candidate half removed. Every decision below is made by the same imported
    function the checkpoint 22D scorer used.
    """
    phone_map = load_phone_map() if phone_map is None else phone_map
    source = _source(manifest, "speechocean762")
    reference = _load_verified(
        REPOSITORY_ROOT / source["private_reference_path"],
        source["private_reference_sha256"],
    )
    references = {item["safe_id"]: item for item in reference["records"]}
    clips = {item["safe_id"]: item for item in source["clips"]}
    if set(references) != set(clips):
        raise RelationTruthError("SpeechOcean reference and clip indexes differ")

    rows = []
    for safe_id in sorted(clips):
        clip = clips[safe_id]
        record = references[safe_id]
        if canonical_json_sha256(record) != clip["reference_record_sha256"]:
            raise RelationTruthError(
                f"SpeechOcean reference row changed for {safe_id}"
            )
        split = clip["project_split"]
        age = _age_stratum(clip["source_stratum"])
        for word in record["words"]:
            phones = word["reference_phones"].split()
            parsed = [
                parse_review_phone_string(word["reference_phones"], reviewer)
                for reviewer in word["five_reviewer_phone_strings"]
            ]
            for local_index, phone in enumerate(phones):
                scorable, _ = scorable_reference_phone(phones, local_index, phone_map)
                if not scorable:
                    continue
                reviewer_states = [
                    item["targets"][local_index]["state"] for item in parsed
                ]
                consensus = target_consensus(reviewer_states)
                rows.append(
                    {
                        "safe_id": safe_id,
                        "private_participant_id": clip["private_participant_id"],
                        "project_split": split,
                        "age_stratum": age,
                        "source_stratum": clip["source_stratum"],
                        "word_index": word["word_index"],
                        "target_index": local_index,
                        "reference_phone": strip_stress(phone),
                        "reviewer_states": reviewer_states,
                        "reference_decision": consensus["decision"],
                        "truth": _truth_state(
                            consensus["decision"],
                            "coarse_relation_present",
                            "no_relation_concern",
                        ),
                    }
                )
    return rows


def reproduce_frozen_truth(
    frozen_manifest_path=None, frozen_truth_path=FROZEN_TRUTH_PATH
):
    """Compare this module's rows against the committed checkpoint 22D evidence.

    Returns the number of rows compared. Raises when any row differs, so the
    powered truth cannot rest on a redefined consensus, scope or state.
    """
    if frozen_manifest_path is None:
        frozen_manifest_path = (
            PRIVATE_BENCHMARK_ROOT / "benchmark-manifest-v1.0.0.json"
        )
    manifest = json.loads(Path(frozen_manifest_path).read_text(encoding="utf-8"))
    committed = json.loads(Path(frozen_truth_path).read_text(encoding="utf-8"))
    expected = committed["target_rows"]
    produced = relation_truth_rows(manifest)
    if len(produced) != len(expected):
        raise RelationTruthError(
            f"row count differs: {len(produced)} against {len(expected)}"
        )
    key = lambda row: (row["safe_id"], row["word_index"], row["target_index"])
    for produced_row, expected_row in zip(
        sorted(produced, key=key), sorted(expected, key=key)
    ):
        for field in TRUTH_ROW_FIELDS:
            if produced_row[field] != expected_row[field]:
                raise RelationTruthError(
                    f"{field} differs at {key(produced_row)}"
                )
    return len(produced)


def scorable_denominators(rows):
    """Count scorable opportunities per partition. Denominators, never outcomes."""
    counts = {}
    for row in rows:
        if row["truth"] == "unscorable":
            continue
        key = f"{row['project_split']}:{row['age_stratum']}"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def write_powered_relation_truth(
    manifest_path=POWERED_MANIFEST_PATH, output_path=POWERED_TRUTH_PATH
):
    output_path = Path(output_path)
    if output_path.exists():
        raise RelationTruthError(
            "powered relation evidence already exists; do not overwrite it"
        )
    reproduced = reproduce_frozen_truth()
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = relation_truth_rows(manifest)
    document = {
        "schema_version": "1.0.0",
        "evidence_id": "speech_sound_powered_relation_truth_private_v1",
        "checkpoint": "22E4B",
        "private_benchmark_manifest_sha256": canonical_json_sha256(manifest),
        "held_out_evaluation": False,
        "source_id": "speechocean762",
        "truth_class": "expert_phone_relations",
        "relation_class": "coarse_target_relation",
        "frozen_rows_reproduced": reproduced,
        "target_rows": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json_bytes(document))
    return output_path, document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=POWERED_MANIFEST_PATH)
    parser.add_argument("--output", type=Path, default=POWERED_TRUTH_PATH)
    args = parser.parse_args()
    path, document = write_powered_relation_truth(args.manifest, args.output)
    print(f"Powered relation truth: {path.relative_to(REPOSITORY_ROOT)}")
    print(f"Private evidence SHA256: {file_sha256(path)}")
    print(
        "Reproduced the committed checkpoint 22D rows exactly: "
        f"{document['frozen_rows_reproduced']}"
    )
    print(f"Target rows: {len(document['target_rows'])}")
    for partition, count in scorable_denominators(document["target_rows"]).items():
        print(f"  {partition}: {count} scorable opportunities")


if __name__ == "__main__":
    main()
