"""Measure one private feasibility process with macOS ``time -l``.

The command keeps stdout and stderr private and binds resource metrics to the
resulting evidence file checksum.  It is a reproduction helper, not a normal
pipeline stage.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
from pathlib import Path

from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256
from .mfa_probe import _parse_time_metrics


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
ALLOWED_KEYS = {
    "phoneticxeus_mps_full_warm",
    "phoneticxeus_mps_cold_2",
    "phoneticxeus_mps_cold_3",
    "phoneticxeus_cpu_source_subset",
    "panphon_observed_mapping",
}


def _private(path):
    resolved = Path(path).resolve(strict=False)
    resolved.relative_to(PRIVATE_ROOT.resolve())
    return resolved


def parse_elapsed_seconds(stderr):
    match = re.search(r"^\s*([0-9]+(?:\.[0-9]+)?)\s+real\s", stderr, re.MULTILINE)
    if not match:
        raise ValueError("macOS time output has no elapsed real time")
    return float(match.group(1))


def _sysctl(name):
    result = subprocess.run(
        ["/usr/sbin/sysctl", "-n", name],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def measure(key, evidence_path, output_path, log_root, command):
    if key not in ALLOWED_KEYS:
        raise ValueError("resource metric key is not part of checkpoint 22C")
    evidence_path = _private(evidence_path)
    output_path = _private(output_path)
    log_root = _private(log_root)
    if not command:
        raise ValueError("a measured command is required")
    if Path(command[0]).name != "env" or command[1:2] != ["-i"]:
        raise ValueError("measured commands must begin with env -i")
    log_root.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(
        ["/usr/bin/time", "-l", *command],
        capture_output=True,
        text=True,
    )
    (log_root / f"{key}.stdout.log").write_text(process.stdout, encoding="utf-8")
    (log_root / f"{key}.stderr-and-time.log").write_text(
        process.stderr, encoding="utf-8"
    )
    if process.returncode != 0 or not evidence_path.is_file():
        raise RuntimeError(f"measured process {key} failed; inspect the private log")
    parsed = _parse_time_metrics(process.stderr)
    if any(parsed[item] is None for item in ("maximum_resident_set_bytes", "peak_memory_footprint_bytes", "swaps")):
        raise ValueError("macOS time output is incomplete")

    if output_path.exists():
        document = json.loads(output_path.read_text(encoding="utf-8"))
    else:
        operating_system = platform.mac_ver()[0]
        document = {
            "schema_version": "1.0.0",
            "measurement_tool": "/usr/bin/time -l",
            "units": "bytes_and_seconds",
            "machine": {
                "hardware": _sysctl("machdep.cpu.brand_string"),
                "architecture": platform.machine(),
                "physical_memory_bytes": int(_sysctl("hw.memsize")),
                "operating_system": f"macOS {operating_system}",
                "mps_available": True,
            },
        }
    document[key] = {
        "exit_status": process.returncode,
        "evidence_sha256": file_sha256(evidence_path),
        "real_s": parse_elapsed_seconds(process.stderr),
        "maximum_resident_set_bytes": parsed["maximum_resident_set_bytes"],
        "peak_memory_footprint_bytes": parsed["peak_memory_footprint_bytes"],
        "swaps": parsed["swaps"],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json_bytes(document))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, choices=sorted(ALLOWED_KEYS))
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--log-root", required=True, type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    measure(args.key, args.evidence, args.output, args.log_root, command)
    print(f"Measured {args.key}; evidence and logs remain private.")


if __name__ == "__main__":
    main()
