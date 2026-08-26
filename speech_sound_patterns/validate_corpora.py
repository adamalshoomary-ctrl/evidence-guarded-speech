"""Command line validation for speech sound corpus and licence manifests."""

import argparse
from pathlib import Path

from .corpus_manifest import (
    REGISTRY_PATH,
    load_registered_manifests,
    validate_private_evidence,
    validate_registered_manifests,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("registry", nargs="?", type=Path, default=REGISTRY_PATH)
    parser.add_argument(
        "--verify-private",
        action="store_true",
        help="check ignored assignment files and local archive sizes",
    )
    parser.add_argument(
        "--rehash-archives",
        action="store_true",
        help="also recalculate every local archive SHA256",
    )
    args = parser.parse_args()
    errors = validate_registered_manifests(args.registry)
    if not errors and (args.verify_private or args.rehash_archives):
        _, manifests = load_registered_manifests(args.registry)
        errors.extend(
            validate_private_evidence(
                manifests, rehash_archives=args.rehash_archives
            )
        )
    if errors:
        print("Speech sound corpus manifests: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    print("Speech sound corpus manifests: VALID")
    print("Raw data remains private and scientific and product release remain locked.")


if __name__ == "__main__":
    main()
