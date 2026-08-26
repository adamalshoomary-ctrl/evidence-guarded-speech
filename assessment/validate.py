"""Command line validation for the assessment manifest."""

import argparse
from pathlib import Path

from assessment.manifest import MANIFEST_PATH, load_manifest, validate_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()
    errors = validate_manifest(load_manifest(args.manifest))
    if errors:
        print("Assessment manifest: INVALID")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    print("Assessment manifest: VALID")


if __name__ == "__main__":
    main()
