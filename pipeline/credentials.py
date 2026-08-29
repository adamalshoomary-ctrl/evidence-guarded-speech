"""What credentials a run needs, worked out before the run spends anything.

The runner used to read no credential at all. Each stage loaded its own key at
the moment it ran, and the stages that need one sit at the end of the queue, so
somebody holding a transcription key and no model key paid for a full
transcription, waited for a one to two gigabyte model download, and then
received a report saying the interpretation was unavailable. The missing key
was knowable before any of that and nothing looked. Found 2026-08-28.

Two classes of credential, and the difference decides whether a run stops.

**Load bearing.** Transcription and diarization cannot degrade. There is no
fallback between the two transcription paths, deliberately, because they do not
produce the same evidence. A run without these keys cannot produce a
measurement record, so the run stops before it costs anything.

**Requested.** The model stages degrade safely by design, and that design is
about a provider failing mid run, not about a key that was never there. So the
rule is narrower than "stop whenever a model key is absent": a run stops only
when the caller **asked** for the thing the key serves. Typing ``--interpret``
without a model key asks for an interpretation that cannot be produced, and
waiting several minutes to be told so is the defect. Conversation mode uses the
same provider for the speaker label referee without anybody asking, so a
missing key there warns and the run continues and degrades, exactly as before.

Nothing here reads, logs or stores a key's value. It asks whether one is set.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
EXAMPLE_NAME = ".env.example"

ASSEMBLYAI = {
    "variable": "ASSEMBLYAI_API_KEY",
    "purpose": "transcribes the recording",
    "issued_at": "https://www.assemblyai.com/dashboard/signup",
    "extra": None,
}
HUGGING_FACE = {
    "variable": "HF_TOKEN",
    "purpose": "downloads the speaker diarization model",
    "issued_at": "https://huggingface.co/settings/tokens",
    "extra": (
        "A valid token is not enough on its own. Accept the model user "
        "agreement at https://hf.co/pyannote/speaker-diarization-3.1 first, "
        "or the download returns a bare 401."
    ),
}
GEMINI = {
    "variable": "GEMINI_API_KEY",
    "purpose": "runs the optional language model stages",
    "issued_at": "https://aistudio.google.com/apikey",
    "extra": None,
}
# The same key, named for what it does when nobody asked for it. Conversation
# mode runs the speaker label referee without --interpret, so the warning has to
# say what is actually lost rather than repeat the blocking wording.
GEMINI_REFEREE = {
    "variable": "GEMINI_API_KEY",
    "purpose": "corrects speaker labels after diarization",
    "issued_at": "https://aistudio.google.com/apikey",
    "extra": None,
}


def required_credentials(execution_mode, transcriber, interpret):
    """Return (blocking, requested) credential records for one flag combination.

    Blocking credentials stop the run. Requested ones warn and let it degrade.
    """
    blocking, advisory = [], []
    if transcriber == "assemblyai":
        blocking.append(ASSEMBLYAI)
    if execution_mode != "solo":
        blocking.append(HUGGING_FACE)
    if interpret:
        blocking.append(GEMINI)
    elif execution_mode != "solo":
        advisory.append(GEMINI_REFEREE)
    return blocking, advisory


def _is_set(variable):
    return bool((os.getenv(variable) or "").strip())


def _describe(record):
    lines = [
        f"  {record['variable']} is not set. It {record['purpose']}.",
        f"    Get one at {record['issued_at']}",
    ]
    if record["extra"]:
        lines.append(f"    {record['extra']}")
    return lines


def check_credentials(execution_mode, transcriber, interpret, load=True):
    """Return (stop_message, warning_lines) for this run's flag combination.

    ``stop_message`` is None when the run may proceed.
    """
    if load:
        load_dotenv(ENV_PATH)
    blocking, advisory = required_credentials(
        execution_mode, transcriber, interpret
    )
    missing = [record for record in blocking if not _is_set(record["variable"])]
    warnings = []
    for record in advisory:
        if not _is_set(record["variable"]):
            warnings.append(
                f"{record['variable']} is not set, so the stage that "
                f"{record['purpose']} cannot run. The run continues, records the "
                "stage as unavailable, and everything else is unaffected. Add the "
                f"key from {record['issued_at']} if you want that stage."
            )
    if not missing:
        return None, warnings

    lines = [
        "ERROR: this run needs a credential that is not set, so it stopped "
        "before doing any work.",
        "",
    ]
    for record in missing:
        lines.extend(_describe(record))
    lines.extend([
        "",
        f"Put each one on its own line in {ENV_PATH}, as NAME=value.",
        f"There is a template at {REPO_ROOT / EXAMPLE_NAME}: copy it to .env "
        "and fill in the values you have.",
    ])
    if any(record is ASSEMBLYAI for record in missing):
        lines.append(
            "To run with no paid credentials at all, add --transcriber local, "
            "which transcribes on this machine."
        )
    return "\n".join(lines), warnings
