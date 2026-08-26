"""Apply a structured manual review packet to a candidate artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.run_context import atomic_write_json

from .extract import apply_review_packet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("review_packet", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    packet = json.loads(args.review_packet.read_text(encoding="utf-8"))
    reviewed = apply_review_packet(artifact, packet)
    atomic_write_json(args.output, reviewed)
    print(f"Reviewed artifact saved to: {args.output}")
    print("One review packet remains not reference truth and cannot diagnose.")


if __name__ == "__main__":
    main()

