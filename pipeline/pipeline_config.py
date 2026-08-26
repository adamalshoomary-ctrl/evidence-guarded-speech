"""Versioned runtime configuration shared by every active pipeline stage."""

from copy import deepcopy

PIPELINE_VERSION = "0.11.0"
PROVENANCE_SCHEMA_VERSION = "1.0.0"

GEMINI_MODEL_ID = "gemini-3.5-flash"
GEMINI_THINKING_LEVEL = "high"

# Remote enrichment must be able to fail. Without a deadline a request that
# never returns never becomes an exception, so the documented retry and safe
# degrade never fire and one stuck call halts the whole run. That happened once
# for 3 hours 54 minutes in the listener stage.
#
# Two layers, and the order matters. The provider client aborts its own request
# first, which produces a clean classifiable timeout and frees the connection.
# The outer deadline is the backstop for anything the client cannot see, and it
# must be the longer of the two or it would pre-empt the clean failure. Both
# count elapsed awake time; a system sleep suspends the process rather than
# consuming the budget. Transcription is load bearing and is deliberately not
# covered here: it must fail the run rather than degrade.
#
# The longest legitimate enrichment attempt observed on this machine is well
# under two minutes, so these are generous headroom rather than tuning.
ENRICHMENT_REQUEST_TIMEOUT_S = 240
ENRICHMENT_ATTEMPT_DEADLINE_S = 300
ASSEMBLYAI_SPEECH_MODEL_IDS = (
    "universal-3-5-pro",
    "universal-2",
)
PYANNOTE_MODEL_ID = "pyannote/speaker-diarization-3.1"
WHISPERX_ASR_MODEL_ID = "small"
WHISPERX_ASR_REPOSITORY = "Systran/faster-whisper-small"
WHISPERX_DEVICE = "cpu"
WHISPERX_COMPUTE_TYPE = "int8"
WHISPERX_BATCH_SIZE = 8
SILERO_VAD_MODEL_ID = "silero_vad"

# Which transcriber a run uses. This is always an explicit choice and never a
# fallback. A missing credential fails the run rather than quietly producing a
# different kind of record: the two paths do not transcribe the same way, and a
# record that could have come from either is not a record at all.
TRANSCRIBERS = ("assemblyai", "local")
DEFAULT_TRANSCRIBER = "assemblyai"

# The local path exists so the pipeline runs with no paid credentials. It uses
# Silero for voice activity rather than the WhisperX default, because the
# default is pyannote and pyannote is gated behind a Hugging Face token and a
# manual licence acceptance. A stage that needs a credential cannot be the
# credential free path.
WHISPERX_TRANSCRIPTION_MODEL_ID = "small"
WHISPERX_TRANSCRIPTION_REPOSITORY = "Systran/faster-whisper-small"
WHISPERX_TRANSCRIPTION_VAD_METHOD = "silero"

PROMPT_VERSIONS = {
    "referee": "1.0.0",
    "listener": "1.2.0",
    "evaluator": "2.3.0",
}

RESPONSE_SCHEMA_VERSIONS = {
    "referee": "1.0.0",
    "listener": "1.1.0",
    "evaluator": "claim-ledger-1.0.0",
}

# Distribution names used both for installation and runtime provenance.
DIRECT_DEPENDENCIES = (
    "assemblyai",
    "python-dotenv",
    "whisperx",
    "silero-vad",
    "soundfile",
    "numpy",
    "librosa",
    "praat-parselmouth",
    "requests",
    "google-genai",
    "pyannote-audio",
    "torch",
    "pydantic",
    "httpx",
)

ACTIVE_SOURCE_FILES = (
    "data_model/contract-v1.1.0.json",
    "progress_model/contract-v1.1.0.json",
    "progress_model/reliability-registry-v1.1.0.json",
    "voice_prosody/contract-v1.1.0.json",
    "voice_prosody/contract.py",
    "fluency_events/contract-v1.1.0.json",
    "fluency_events/contract.py",
    "fluency_events/extract.py",
    "fluency_events/review.py",
    "pipeline/acoustic_primitives.py",
    "pipeline/acoustics.py",
    "pipeline/align.py",
    "pipeline/audio_quality.py",
    "pipeline/claim_ledger.py",
    "pipeline/diarize.py",
    "pipeline/evaluate.py",
    "pipeline/fluency_events.py",
    "pipeline/history.py",
    "pipeline/history_identity.py",
    "pipeline/listener.py",
    "pipeline/llm_contract.py",
    "pipeline/measurement_evidence.py",
    "pipeline/merge.py",
    "pipeline/pauses.py",
    "pipeline/personal_progress.py",
    "pipeline/pipeline_config.py",
    "pipeline/provenance.py",
    "pipeline/reliability_policy.py",
    "pipeline/recording_modes.py",
    "pipeline/referee.py",
    "pipeline/run_all.py",
    "pipeline/run_context.py",
    "pipeline/session_context.py",
    "pipeline/solo_timing.py",
    "pipeline/local_transcript.py",
    "pipeline/transcribe.py",
    "pipeline/transcribe_local.py",
    "pipeline/voice_safety.py",
    "pipeline/verify.py",
    "constraints.txt",
    "requirements.txt",
)

_MODEL_REGISTRY = {
    "transcription": {
        "kind": "provider",
        "provider": "AssemblyAI",
        "requested_model_id": ASSEMBLYAI_SPEECH_MODEL_IDS[0],
        "fallback_model_ids": list(ASSEMBLYAI_SPEECH_MODEL_IDS[1:]),
        "actual_model_id": None,
        "version_policy": "provider_named_model_family",
        "configuration": {
            "disfluencies": True,
            "speaker_labels": True,
            "punctuate": True,
            "format_text": True,
        },
    },
    "diarization": {
        "kind": "local",
        "provider": "Hugging Face via pyannote.audio",
        "requested_model_id": PYANNOTE_MODEL_ID,
        "actual_model_id": PYANNOTE_MODEL_ID,
        "version_policy": "moving_repository_revision",
        "configuration": {
            "input_channels": 1,
            "sample_rate_hz": 16000,
        },
    },
    "alignment_asr": {
        "kind": "local",
        "provider": "WhisperX via faster-whisper",
        "requested_model_id": WHISPERX_ASR_MODEL_ID,
        "actual_model_id": WHISPERX_ASR_REPOSITORY,
        "version_policy": "moving_repository_revision",
        "configuration": {
            "device": WHISPERX_DEVICE,
            "compute_type": WHISPERX_COMPUTE_TYPE,
            "batch_size": WHISPERX_BATCH_SIZE,
        },
    },
    "alignment_timing": {
        "kind": "local",
        "provider": "WhisperX",
        "requested_model_id": "language_default",
        "actual_model_id": None,
        "version_policy": "resolved_from_pinned_whisperx_package",
        "configuration": {
            "device": WHISPERX_DEVICE,
            "character_alignments": True,
        },
    },
    "voice_activity_detection": {
        "kind": "local",
        "provider": "silero-vad package",
        "requested_model_id": SILERO_VAD_MODEL_ID,
        "actual_model_id": SILERO_VAD_MODEL_ID,
        "version_policy": "package_pinned",
        "configuration": {
            "onnx": False,
            "opset_version": 16,
            "sample_rate_hz": 16000,
            "min_silence_duration_ms": 250,
        },
    },
}

for _stage in ("referee", "listener", "evaluator"):
    _MODEL_REGISTRY[_stage] = {
        "kind": "provider",
        "provider": "Google Gemini",
        "requested_model_id": GEMINI_MODEL_ID,
        "actual_model_id": GEMINI_MODEL_ID,
        "version_policy": "moving_alias",
        "configuration": {
            "thinking_level": GEMINI_THINKING_LEVEL,
            "temperature": "provider_default",
            "response_mode": "structured_json",
        },
    }


_LOCAL_TRANSCRIPTION_MODEL = {
    "kind": "local",
    "provider": "WhisperX via faster-whisper",
    "requested_model_id": WHISPERX_TRANSCRIPTION_MODEL_ID,
    "actual_model_id": WHISPERX_TRANSCRIPTION_REPOSITORY,
    "version_policy": "moving_repository_revision",
    "configuration": {
        "device": WHISPERX_DEVICE,
        "compute_type": WHISPERX_COMPUTE_TYPE,
        "batch_size": WHISPERX_BATCH_SIZE,
        "vad_method": WHISPERX_TRANSCRIPTION_VAD_METHOD,
        "disfluencies": "not_configurable",
        "speaker_labels": False,
        "punctuate": "model_default",
    },
}


def model_registry(transcriber=DEFAULT_TRANSCRIBER):
    """Return a fresh serializable copy for one run's provenance.

    The transcription entry follows the transcriber the run actually chose, so
    a record can never describe a provider that did not produce it.
    """
    if transcriber not in TRANSCRIBERS:
        raise ValueError(f"unknown transcriber: {transcriber}")
    registry = deepcopy(_MODEL_REGISTRY)
    if transcriber == "local":
        registry["transcription"] = deepcopy(_LOCAL_TRANSCRIPTION_MODEL)
    registry["transcription"]["transcriber"] = transcriber
    return registry


def prompt_registry():
    """Return maintained prompt and response shape versions by LLM stage."""
    return {
        stage: {
            "prompt_version": PROMPT_VERSIONS[stage],
            "response_schema_version": RESPONSE_SCHEMA_VERSIONS[stage],
        }
        for stage in PROMPT_VERSIONS
    }


def whisperx_alignment_model_id(language_code):
    """Resolve and return the exact WhisperX default selected for a language."""
    from whisperx.alignment import (  # imported only inside the alignment stage
        DEFAULT_ALIGN_MODELS_HF,
        DEFAULT_ALIGN_MODELS_TORCH,
    )

    if language_code in DEFAULT_ALIGN_MODELS_TORCH:
        return DEFAULT_ALIGN_MODELS_TORCH[language_code], "package_pinned"
    if language_code in DEFAULT_ALIGN_MODELS_HF:
        return DEFAULT_ALIGN_MODELS_HF[language_code], "moving_repository_revision"
    raise ValueError(f"No default alignment model for language: {language_code}")
