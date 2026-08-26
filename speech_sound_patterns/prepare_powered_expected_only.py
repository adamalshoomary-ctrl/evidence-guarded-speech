"""Build the label-blind candidate input for the powered checkpoint 22E4B sample.

Every candidate lane reads this file and never the expert relation truth. It
carries the intended phones, the scorable scope and the input identity, and the
checkpoint 22D label-blind assertion refuses to write it if any expert result
field is reachable from it.

The construction is the frozen checkpoint 22D one, called with the powered
manifest identity and sample expectation rather than reimplemented.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import PRIVATE_BENCHMARK_ROOT, canonical_json_sha256
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256
from .prepare_benchmark_repair import prepare
from .prepare_powered_benchmark import (
    POWERED_MANIFEST_PATH,
    assert_valid_sample_contract,
    sample_expectation,
)


POWERED_EXPECTED_ONLY_PATH = (
    PRIVATE_BENCHMARK_ROOT / "v2" / "expected-only-manifest-v1.1.0.json"
)
EXPECTED_MANIFEST_ID = "speech_sound_powered_expected_only_v1"


def build(manifest_path=POWERED_MANIFEST_PATH, output_path=POWERED_EXPECTED_ONLY_PATH):
    contract = assert_valid_sample_contract()
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    return prepare(
        manifest_path,
        output_path,
        manifest_sha256=canonical_json_sha256(manifest),
        expectation=sample_expectation(contract),
        expected_manifest_id=EXPECTED_MANIFEST_ID,
    )


def verify(manifest_path=POWERED_MANIFEST_PATH, output_path=POWERED_EXPECTED_ONLY_PATH):
    """Rebuild the document in memory and compare it with the file on disk."""
    contract = assert_valid_sample_contract()
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    from .prepare_benchmark_repair import _load, _speechocean_source
    from .prepare_benchmark_repair import build_expected_only_manifest

    source = _speechocean_source(manifest)
    reference = _load(REPOSITORY_ROOT / source["private_reference_path"])
    rebuilt = build_expected_only_manifest(
        manifest,
        reference,
        manifest_sha256=canonical_json_sha256(manifest),
        expectation=sample_expectation(contract),
        expected_manifest_id=EXPECTED_MANIFEST_ID,
    )
    on_disk = Path(output_path).read_bytes()
    if canonical_json_bytes(rebuilt) != on_disk:
        raise ValueError("the powered label-blind input does not match its rules")
    return len(rebuilt["clips"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=POWERED_MANIFEST_PATH)
    parser.add_argument("--output", type=Path, default=POWERED_EXPECTED_ONLY_PATH)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="recompute the document and compare it with the existing file",
    )
    args = parser.parse_args()
    if args.verify:
        clips = verify(args.manifest, args.output)
        print(f"Powered label-blind input reproduces exactly: {clips} clips")
        print(f"Private manifest SHA256: {file_sha256(args.output)}")
        return
    path, document = build(args.manifest, args.output)
    print(f"Powered label-blind input: {len(document['clips'])} clips")
    print(f"Held-out participants: {document['held_out_participants']}")
    print(f"Expert outcomes included: {document['expert_outcomes_included']}")
    print(f"Private manifest: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
