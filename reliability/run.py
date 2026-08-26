"""Command line entry point for the reliability and fairness audit."""

import argparse
import json
from pathlib import Path

from reliability.audit import load_artifact, render_report, run_audit


def _artifact(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected LABEL=OUTPUT_DIR")
    label, directory = value.split("=", 1)
    if not label:
        raise argparse.ArgumentTypeError("artifact label cannot be empty")
    return load_artifact(label, directory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat-output", action="append", default=[],
                        type=_artifact, metavar="LABEL=OUTPUT_DIR")
    parser.add_argument("--encoding-output", action="append", default=[],
                        type=_artifact, metavar="LABEL=OUTPUT_DIR")
    parser.add_argument("--artifact", action="append", default=[],
                        type=_artifact, metavar="LABEL=OUTPUT_DIR")
    parser.add_argument("--study-metadata", type=Path)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    metadata = {}
    if args.study_metadata:
        document = json.loads(args.study_metadata.read_text(encoding="utf-8"))
        if document.get("schema_version") != "1.0.0":
            parser.error("unsupported study metadata schema version")
        metadata = document.get("artifacts") or {}
    report = run_audit(
        repeat_artifacts=args.repeat_output,
        encoding_artifacts=args.encoding_output,
        other_artifacts=args.artifact,
        study_metadata=metadata,
        report_dir=args.report_dir,
    )
    print(render_report(report))
    raise SystemExit(0 if report["status"] != "fail" else 1)


if __name__ == "__main__":
    main()
