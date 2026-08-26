"""Build and synchronize auditable, nonsecret run provenance."""

import hashlib
import json
import platform
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

try:
    from pipeline_config import (
        ACTIVE_SOURCE_FILES,
        DEFAULT_TRANSCRIBER,
        DIRECT_DEPENDENCIES,
        PIPELINE_VERSION,
        PROVENANCE_SCHEMA_VERSION,
        model_registry,
        prompt_registry,
    )
    from run_context import atomic_write_json
except ModuleNotFoundError:  # package imports used by the unit tests
    from .pipeline_config import (
        ACTIVE_SOURCE_FILES,
        DEFAULT_TRANSCRIBER,
        DIRECT_DEPENDENCIES,
        PIPELINE_VERSION,
        PROVENANCE_SCHEMA_VERSION,
        model_registry,
        prompt_registry,
    )
    from .run_context import atomic_write_json


def utc_now():
    return (datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audio_metadata(audio_path):
    """Read stable input identity and technical audio fields using ffprobe."""
    audio_path = Path(audio_path).resolve()
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries",
            "format=duration,format_name:stream=codec_type,codec_name,"
            "sample_rate,channels,channel_layout,duration,bit_rate,"
            "bits_per_sample,bits_per_raw_sample",
            "-of", "json", str(audio_path),
        ],
        check=True, capture_output=True, text=True,
    )
    probe = json.loads(result.stdout)
    stream = next(
        (item for item in probe.get("streams", [])
         if item.get("codec_type") == "audio"),
        None,
    )
    if stream is None:
        raise RuntimeError(f"ffprobe found no audio stream in {audio_path}")
    duration = (probe.get("format", {}).get("duration")
                or stream.get("duration"))
    return {
        "filename": audio_path.name,
        "path": str(audio_path),
        "byte_sha256": sha256_file(audio_path),
        "byte_size": audio_path.stat().st_size,
        "duration_s": round(float(duration), 3) if duration is not None else None,
        "container_format": probe.get("format", {}).get("format_name"),
        "codec": stream.get("codec_name"),
        "sample_rate_hz": int(stream["sample_rate"])
        if stream.get("sample_rate") else None,
        "channels": stream.get("channels"),
        "channel_layout": stream.get("channel_layout"),
        "bit_rate": int(stream["bit_rate"]) if stream.get("bit_rate") else None,
        "bits_per_sample": int(stream["bits_per_sample"])
        if stream.get("bits_per_sample") else None,
        "bits_per_raw_sample": int(stream["bits_per_raw_sample"])
        if stream.get("bits_per_raw_sample") else None,
    }


def _run_text(command, cwd):
    try:
        result = subprocess.run(
            command, cwd=cwd, check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _source_tree(repo_root):
    digest = hashlib.sha256()
    included = []
    for relative in ACTIVE_SOURCE_FILES:
        path = repo_root / relative
        if not path.is_file():
            continue
        included.append(relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return included, digest.hexdigest()


def source_revision(repo_root):
    """Identify both the Git base and exact active source bytes."""
    repo_root = Path(repo_root).resolve()
    files, tree_hash = _source_tree(repo_root)
    revision = _run_text(["git", "rev-parse", "HEAD"], repo_root)
    status = _run_text(
        ["git", "status", "--porcelain", "--untracked-files=all"], repo_root
    )
    return {
        "git_commit": revision,
        "working_tree_dirty": bool(status) if status is not None else None,
        "source_tree_sha256": tree_hash,
        "source_files": files,
    }


def package_versions():
    versions = {}
    for distribution in DIRECT_DEPENDENCIES:
        try:
            versions[distribution] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            versions[distribution] = None
    return versions


def _ffmpeg_version():
    line = _run_text(["ffmpeg", "-version"], None)
    return line.splitlines()[0] if line else None


def build_initial_provenance(repo_root, audio_path, run_id, run_configuration,
                             started_at_utc, input_audio_metadata=None):
    """Capture immutable run identity before any analysis stage starts."""
    repo_root = Path(repo_root).resolve()
    models = model_registry(
        run_configuration.get("transcriber", DEFAULT_TRANSCRIBER)
    )
    speakers_expected = run_configuration.get("speakers_expected")
    models["transcription"]["configuration"][
        "speakers_expected"
    ] = run_configuration.get(
        "transcription_speakers_expected", speakers_expected
    )
    models["diarization"]["configuration"][
        "num_speakers"
    ] = run_configuration.get(
        "diarization_speakers_expected", speakers_expected
    )
    solo_mode = run_configuration.get("recording_mode") == "solo"
    for name, model in models.items():
        model["invoked"] = not (
            solo_mode and name in {"diarization", "referee"}
        )
    dependency_files = {}
    for relative in ("requirements.txt", "constraints.txt"):
        path = repo_root / relative
        if path.is_file():
            dependency_files[relative] = sha256_file(path)

    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "pipeline": {
            "version": PIPELINE_VERSION,
            "source": source_revision(repo_root),
        },
        "run": {
            "id": run_id,
            "status": "running",
            "started_at_utc": started_at_utc,
            "completed_at_utc": None,
            "duration_s": None,
            "configuration": deepcopy(run_configuration),
        },
        "input_audio": (deepcopy(input_audio_metadata)
                        if input_audio_metadata is not None
                        else audio_metadata(audio_path)),
        "models": models,
        "prompts": prompt_registry(),
        "runtime": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "python_executable": str(Path(sys.executable).resolve()),
            "packages": package_versions(),
            "dependency_file_sha256": dependency_files,
            "ffmpeg": _ffmpeg_version(),
        },
        "stages": {},
    }


def _refresh_actual_models(provenance, output_dir, completed_outputs):
    transcript_path = output_dir / "transcript.json"
    if "transcript.json" in completed_outputs and transcript_path.is_file():
        try:
            transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
            actual = transcript.get("speech_model_used")
            if actual:
                model = provenance["models"]["transcription"]
                model["actual_model_id"] = actual
                model["configuration"]["actual_language_code"] = (
                    transcript.get("language_code")
                )
                model["configuration"]["provider_fallback_model_ids"] = (
                    transcript.get("speech_models")
                )
        except (json.JSONDecodeError, OSError):
            pass

    alignment_path = output_dir / "alignment.json"
    if "alignment.json" in completed_outputs and alignment_path.is_file():
        try:
            alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
            details = alignment.get("model_provenance", {})
            actual = details.get("alignment_model_id")
            if actual:
                model = provenance["models"]["alignment_timing"]
                model["actual_model_id"] = actual
                model["version_policy"] = details.get(
                    "alignment_model_version_policy", model["version_policy"]
                )
                model["configuration"]["language_code"] = details.get("language")
                provenance["models"]["alignment_asr"]["configuration"][
                    "vad_method"
                ] = details.get("vad_method")
        except (json.JSONDecodeError, OSError):
            pass


def sync_provenance_to_master(manifest_path):
    """Refresh dynamic IDs and copy the manifest provenance into master.json."""
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict):
        return
    provenance["stages"] = deepcopy(manifest.get("stages", {}))
    output_dir = Path(manifest["output_dir"])
    _refresh_actual_models(
        provenance, output_dir, set(manifest.get("completed_outputs", []))
    )
    manifest["provenance"] = provenance
    atomic_write_json(manifest_path, manifest)

    if "master.json" not in manifest.get("completed_outputs", []):
        return
    master_path = output_dir / "master.json"
    if not master_path.is_file():
        return
    master = json.loads(master_path.read_text(encoding="utf-8"))
    master.setdefault("meta", {})["provenance"] = deepcopy(provenance)
    atomic_write_json(master_path, master)
