"""Shared input, output, manifest, and atomic write helpers."""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

AUDIO_TYPES = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac",
               ".mp4", ".webm"}
MANIFEST_NAME = "run_manifest.json"


def add_run_arguments(parser):
    """Add consistent runner supplied arguments to a standalone stage."""
    parser.add_argument("--audio", type=Path, default=None,
                        help="explicit audio file instead of the first in /audio")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="directory for this run's artifacts")
    parser.add_argument("--run-id", type=str, default=None,
                        help="runner generated ID used for manifest checks")
    parser.add_argument("--session-context", type=Path, default=None,
                        help="validated account, session, task, and consent context")
    parser.add_argument(
        "--recording-mode", choices=("solo", "conversation"), default=None,
        help="runner resolved recording mode for task aware stages",
    )


def resolve_audio(explicit_audio, audio_dir):
    """Resolve one audio input, honoring an explicit path exactly."""
    if explicit_audio is not None:
        audio_path = Path(explicit_audio).expanduser().resolve()
        if not audio_path.is_file():
            raise SystemExit(f"ERROR: audio file not found: {audio_path}")
        if audio_path.suffix.lower() not in AUDIO_TYPES:
            raise SystemExit(f"ERROR: unsupported audio type: {audio_path.suffix}")
        return audio_path

    audio_dir = Path(audio_dir)
    if not audio_dir.is_dir():
        raise SystemExit(
            f"ERROR: there is no {audio_dir.name}/ directory here, so there is "
            "nothing to run.\n"
            "This command reads whichever recording sits in that directory. A "
            "fresh copy of this repository ships without one, because it "
            "publishes no audio.\n"
            "Either name a file directly:\n"
            "  --audio regression/fixtures/solo.wav\n"
            f"or create {audio_dir.name}/ and put one recording in it."
        )
    audio_files = sorted(
        f for f in audio_dir.iterdir()
        if f.suffix.lower() in AUDIO_TYPES and not f.name.startswith(".")
    )
    if not audio_files:
        raise SystemExit(
            f"ERROR: {audio_dir.name}/ has no audio file in it, so there is "
            "nothing to run.\n"
            "Put one recording there, or name a file directly:\n"
            "  --audio regression/fixtures/solo.wav\n"
            "Readable types: " + ", ".join(sorted(AUDIO_TYPES))
        )
    if len(audio_files) > 1:
        names = ", ".join(path.name for path in audio_files)
        raise SystemExit(
            "ERROR: more than one audio file was found. Select one with "
            f"--audio. Found: {names}"
        )
    return audio_files[0].resolve()


@dataclass(frozen=True)
class RunContext:
    repo_root: Path
    output_dir: Path
    run_id: str | None
    audio_path: Path | None
    session_context_path: Path | None = None
    recording_mode: str | None = None

    @property
    def manifest_path(self):
        return self.output_dir / MANIFEST_NAME

    def output_path(self, name, required=False):
        path = self.output_dir / name
        if required:
            self._assert_declared_and_current(name)
            if not path.is_file():
                raise SystemExit(f"ERROR: missing {path} - run earlier steps first")
        return path

    def _assert_declared_and_current(self, name):
        if self.run_id is None:
            return
        if not self.manifest_path.is_file():
            raise SystemExit("ERROR: run manifest is missing")
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if manifest.get("run_id") != self.run_id:
            raise SystemExit("ERROR: run manifest ID does not match this stage")
        if name not in manifest.get("expected_outputs", []):
            raise SystemExit(f"ERROR: {name} is not declared for this run")
        if name not in manifest.get("completed_outputs", []):
            raise SystemExit(
                f"ERROR: {name} was not produced by the current run"
            )

    def write_json(self, name, value, *, indent=2):
        atomic_write_json(self.output_path(name), value, indent=indent)

    def write_text(self, name, value):
        atomic_write_text(self.output_path(name), value)


def context_from_args(args, repo_root, *, require_audio=False):
    repo_root = Path(repo_root).resolve()
    output_dir = (Path(args.output_dir).expanduser().resolve()
                  if args.output_dir else repo_root / "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = None
    if require_audio or args.audio is not None:
        audio_path = resolve_audio(args.audio, repo_root / "audio")
    session_context = getattr(args, "session_context", None)
    session_context_path = None
    if session_context is not None:
        session_context_path = Path(session_context).expanduser().resolve()
        if not session_context_path.is_file():
            raise SystemExit(
                f"ERROR: session context not found: {session_context_path}"
            )
    return RunContext(
        repo_root, output_dir, args.run_id, audio_path, session_context_path,
        getattr(args, "recording_mode", None),
    )


def atomic_write_text(path, value):
    """Replace a text file atomically using a temporary sibling."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_write_json(path, value, *, indent=2):
    atomic_write_text(
        path, json.dumps(value, indent=indent, ensure_ascii=False)
    )


def create_manifest(output_dir, run_id, audio_path, expected_outputs,
                    provenance=None):
    """Start a new run declaration without trusting existing artifacts."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "status": "running",
        "audio_path": str(Path(audio_path).resolve()),
        "output_dir": str(output_dir.resolve()),
        "expected_outputs": sorted(set(expected_outputs) | {MANIFEST_NAME}),
        "completed_outputs": [MANIFEST_NAME],
        "stages": {},
    }
    if provenance is not None:
        manifest["provenance"] = provenance
    atomic_write_json(output_dir / MANIFEST_NAME, manifest)
    return output_dir / MANIFEST_NAME


def update_manifest(manifest_path, *, stage=None, stage_status=None,
                    duration_s=None, completed_outputs=(), run_status=None,
                    stage_script=None, stage_arguments=(),
                    stage_started_at_utc=None, stage_completed_at_utc=None,
                    run_completed_at_utc=None, run_duration_s=None):
    """Update the manifest from the single runner process."""
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if stage is not None:
        manifest["stages"][stage] = {
            "status": stage_status,
            "duration_s": round(duration_s, 3),
            "script": stage_script,
            "arguments": list(stage_arguments),
            "started_at_utc": stage_started_at_utc,
            "completed_at_utc": stage_completed_at_utc,
        }
    completed = manifest.setdefault("completed_outputs", [])
    for name in completed_outputs:
        if name not in completed:
            completed.append(name)
    completed.sort()
    if run_status is not None:
        manifest["status"] = run_status
        provenance_run = manifest.get("provenance", {}).get("run")
        if isinstance(provenance_run, dict):
            provenance_run["status"] = run_status
            provenance_run["completed_at_utc"] = run_completed_at_utc
            provenance_run["duration_s"] = (
                round(run_duration_s, 3) if run_duration_s is not None else None
            )
    atomic_write_json(manifest_path, manifest)
