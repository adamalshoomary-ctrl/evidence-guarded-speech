"""Strict PanPhon probe for observed PhoneticXEUS tokens."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import unicodedata
from pathlib import Path

from .feasibility import (
    PANPHON_FEATURES,
    REPOSITORY_ROOT,
    canonical_json_bytes,
    classify_panphon_token,
    file_sha256,
)


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
EXPECTED_DATA_HASHES = {
    "ipa_all.csv": "0ec0052edf4e58c8c23eda10c0195687eb167ce9bd206cf9a85b9cce8b181f0a",
    "ipa_bases.csv": "61991886e55adaf7df42799bb422af90ff403b2b6cc56dead4a5b4acddcc5568",
    "feature_weights.csv": "03e80a6489e4993de6f17e063eaa74eb59c1d9ba9bc0dec9bec6ffce0cb8080d",
    "diacritic_definitions.yml": "7e93c5bd9ee3dfeea820375d5c7e630dd3f358d2c6a32946091a97b843e73d56",
}


def _private_output(path):
    resolved = path.resolve(strict=False)
    resolved.relative_to(PRIVATE_ROOT.resolve())
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def run_probe(input_paths, output_path):
    import panphon
    from panphon import FeatureTable

    panphon_version = importlib.metadata.version("panphon")
    if panphon_version != "0.22.2":
        raise ValueError("PanPhon version is not pinned to 0.22.2")
    package_root = Path(panphon.__file__).resolve().parent
    data_root = package_root / "data"
    actual_hashes = {
        name: file_sha256(data_root / name) for name in EXPECTED_DATA_HASHES
    }
    if actual_hashes != EXPECTED_DATA_HASHES:
        raise ValueError("PanPhon packaged data checksums changed")

    observed = set()
    source_occurrences = {}
    input_documents = []
    for input_path in input_paths:
        document = json.loads(input_path.read_text(encoding="utf-8"))
        if document.get("probe_id") != "phoneticxeus_local_feasibility_v1":
            raise ValueError("PanPhon input is not a PhoneticXEUS probe")
        input_documents.append(
            {
                "sha256": file_sha256(input_path),
                "backend": document["backend"],
                "clip_count": len(document["clips"]),
                "model_revision": document["model_revision"],
            }
        )
        for clip in document["clips"]:
            for token in clip["collapsed_tokens"]:
                observed.add(token)
                key = f"{document['backend']}:{clip['source_id']}:{token}"
                source_occurrences[key] = source_occurrences.get(key, 0) + 1

    feature_table = FeatureTable()
    classifications = [
        classify_panphon_token(token, feature_table) for token in sorted(observed)
    ]
    # These checks guard specific unsafe parser behavior in the upstream release.
    for special in ("sil", "spn"):
        item = classify_panphon_token(special, feature_table)
        if item["decision"] != "special_nonphone":
            raise ValueError(f"PanPhon special token escaped fail-closed handling: {special}")
    if classify_panphon_token("g", feature_table)["decision"] != "unsupported":
        raise ValueError("ASCII g must not silently become IPA script g")
    if classify_panphon_token("ɡ", feature_table)["decision"] != "identity_nfd":
        raise ValueError("IPA script g must remain an atomic supported segment")

    document = {
        "schema_version": "1.0.0",
        "probe_id": "panphon_observed_inventory_probe_v1",
        "panphon_version": panphon_version,
        "python_version": platform.python_version(),
        "unicode_database_version": unicodedata.unidata_version,
        "normalization": "NFD",
        "feature_order": list(PANPHON_FEATURES),
        "packaged_data_sha256": actual_hashes,
        "input_documents": sorted(
            input_documents, key=lambda item: (item["backend"], item["sha256"])
        ),
        "observed_unique_token_count": len(classifications),
        "classifications": classifications,
        "source_occurrences": source_occurrences,
        "prohibited_apis": [
            "weighted_feature_edit_distance",
            "validate_word_as_atomic_phone_check",
            "unvalidated_word_or_distance_parsing",
        ],
        "claim_boundaries": {
            "listens_to_audio": False,
            "produced_phone_truth": False,
            "perceptual_distance": False,
            "pronunciation_correctness": False,
            "clinical_interpretation": False,
        },
    }
    output_path = _private_output(output_path)
    output_path.write_bytes(canonical_json_bytes(document))
    return document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    document = run_probe(
        [path.resolve() for path in args.input], args.output.resolve()
    )
    counts = {}
    for item in document["classifications"]:
        counts[item["decision"]] = counts.get(item["decision"], 0) + 1
    print(f"PanPhon observed-token probe: {counts}")
    print("Weighted distances and silent unknown-symbol dropping remain prohibited.")


if __name__ == "__main__":
    main()
