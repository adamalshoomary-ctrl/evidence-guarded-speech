"""Pure recording mode validation and stage routing for the runner."""

try:
    from pipeline_config import DEFAULT_TRANSCRIBER, TRANSCRIBERS
except ModuleNotFoundError:  # package import used by unit tests
    from .pipeline_config import DEFAULT_TRANSCRIBER, TRANSCRIBERS

RECORDING_MODES = ("solo", "conversation", "auto")


def resolve_recording_mode(requested_mode, speakers):
    """Validate the request and return the execution mode."""
    if requested_mode not in RECORDING_MODES:
        raise ValueError(f"unknown recording mode: {requested_mode}")
    if requested_mode == "solo" and speakers not in (None, 1):
        raise ValueError("solo mode accepts only --speakers 1")
    if requested_mode == "conversation" and speakers == 1:
        raise ValueError("conversation mode cannot use --speakers 1")
    if requested_mode == "auto" and speakers == 1:
        return "solo"
    return requested_mode


def build_stage_plan(execution_mode, speakers, history_command,
                     transcriber=DEFAULT_TRANSCRIBER, interpret=False):
    """Return runner stage specifications for one validated execution mode.

    The transcriber is an explicit choice made by the caller. There is no
    fallback between the two paths: they do not transcribe the same way, so a
    record that could have come from either would be unreadable.

    `interpret` adds the optional language model interpretation layer. It is
    off by default: this pipeline's output is the measurement record, and a
    model describing that record is a separate thing a caller asks for. The
    referee is not part of that layer even though it uses the same provider,
    because it corrects speaker attribution inside master.json and so belongs
    to the measurement rather than to the commentary on it.
    """
    if transcriber not in TRANSCRIBERS:
        raise ValueError(f"unknown transcriber: {transcriber}")
    transcribe_command = [
        "transcribe.py" if transcriber == "assemblyai" else "transcribe_local.py"
    ]
    # The speaker count is a hint to the provider's own diarizer. The local
    # path has none, so passing it would put an argument in the run manifest
    # that changed nothing about the transcript.
    if transcriber == "assemblyai" and execution_mode != "solo" and speakers:
        transcribe_command += ["--speakers", str(speakers)]

    stage_1 = [
        ("Verbatim transcript", transcribe_command, ["transcript.json"], []),
        (
            "Letter-level timing",
            (["align.py", "--vad-method", "silero"]
             if execution_mode == "solo" else ["align.py"]),
            ["alignment.json"],
            [],
        ),
        ("Pause detection", ["pauses.py"], ["vad.json"], []),
    ]
    later = []

    if execution_mode == "solo":
        later.append(
            ("Solo timing and contamination check", ["solo_timing.py"],
             ["diarization.json"], [])
        )
    else:
        diarization_command = ["diarize.py"]
        if speakers:
            diarization_command += ["--speakers", str(speakers)]
        stage_1.insert(
            0,
            ("Speaker diarization", diarization_command,
             ["diarization.json"], []),
        )

    later.extend([
        ("Voice measurements (per speaker)", ["acoustics.py"],
         ["acoustics.json"], []),
        ("Merge (attribution) -> master.json", ["merge.py"],
         ["master.json", "master_preview.txt", "words_attributed.json"], []),
    ])

    if execution_mode != "solo":
        later.extend([
            ("Referee (label corrections)", ["referee.py"], ["master.json"],
             ["words_attributed.json"]),
            ("Merge (rebuild with corrections)", ["merge.py", "--rebuild"],
             ["master.json", "master_preview.txt"], []),
        ])

    later.append(
        ("Timestamped speech event candidates", ["fluency_events.py"],
         ["master.json", "fluency_events.json"], [])
    )

    if interpret:
        later.extend([
            ("Listener enrichment (audio + data)", ["listener.py"],
             ["master.json"], ["listener.json", "audit.md"]),
            ("Interpretation -> evaluation.md", ["evaluate.py"],
             ["master.json", "evaluation.md", "evaluation_claims.json"], []),
            ("Verify claims -> verification.md", ["verify.py"],
             ["verification.md", "verification.json"], []),
        ])
    later.append(("History + progress tracking", history_command, [], []))
    return stage_1, later


INTERPRETATION_OUTPUTS = (
    "listener.json", "audit.md", "evaluation.md", "evaluation_claims.json",
    "verification.md", "verification.json",
)
