"""Build versioned evidence and uncertainty records for speech measurements."""

from copy import deepcopy

try:
    from reliability_policy import measurement_validation
except ModuleNotFoundError:
    from .reliability_policy import measurement_validation


MEASUREMENT_SCHEMA_VERSION = "1.3.0"
MEASUREMENT_ALGORITHM_VERSION = "merge-metrics-1.0.0"
MINIMUM_REQUIREMENTS_VERSION = "generated-fixtures-1.0.0"
ASR_CONFIDENCE_THRESHOLD = 0.50
ASR_CONFIDENCE_THRESHOLD_VERSION = (
    "provisional-provider-guidance-and-generated-fixtures-1.0.0"
)

MINIMUM_REQUIREMENTS = {
    "basic": {"word_count": 1, "talk_time_s": 0.5},
    "rate": {"word_count": 20, "talk_time_s": 10.0},
    "language": {"word_count": 20, "talk_time_s": 10.0},
    "vocabulary": {"word_count": 50, "talk_time_s": 20.0},
    "pitch": {"pitch_observation_count": 5},
    "loudness": {"timeline_point_count": 5},
    "turn": {"turn_count": 3},
    "response_pause": {"response_opportunity_count": 2},
    "voice_quality": {"analysed_s": 3.0},
    "pronoun_ratio": {"word_count": 20, "second_person_word_count": 1},
}

QUALITY_CATEGORIES = {
    "high": "Required evidence is present and no known warning applies.",
    "moderate": "Usable with a named uncertainty or confounder.",
    "low": "Available only with a material quality limitation.",
    "unavailable": "The value must not support a conclusion.",
}


def _definition(construct, unit, fields, minimum="basic", *,
                modes=("solo", "conversation"), task="any speech task",
                dependencies=("transcription", "word_timing"), confounders=()):
    return {
        "construct": construct,
        "unit": unit,
        "source_fields": list(fields),
        "minimum": minimum,
        "recording_modes": list(modes),
        "task": task,
        "quality_dependencies": list(dependencies),
        "confounders": list(confounders),
    }


METRIC_DEFINITIONS = {
    "talk_time_s": _definition(
        "attributed speech span", "seconds",
        ("diarization.turns", "transcript.words", "vad.speech_chunks"),
    ),
    "talk_share_pct": _definition(
        "share of attributed speech", "percent",
        ("diarization.turns", "transcript.words"),
        dependencies=("transcription", "speaker_attribution", "turn_metrics"),
        confounders=("overlap and speaker attribution error",),
    ),
    "words": _definition(
        "attributed transcribed words", "words", ("transcript.words",),
        dependencies=("transcription", "speaker_attribution"),
    ),
    "wpm": _definition(
        "speaking rate", "words per minute",
        ("transcript.words", "diarization.turns"), "rate",
        dependencies=("transcription", "speaker_attribution", "word_timing", "rate"),
        confounders=("task type and natural pausing",),
    ),
    "filler_count": _definition(
        "verbatim filler count", "events", ("transcript.words",), "rate",
        dependencies=("transcription", "speaker_attribution", "language"),
        confounders=("ASR disfluency recognition",),
    ),
    "fillers_per_min": _definition(
        "verbatim filler rate", "events per minute",
        ("transcript.words", "diarization.turns"), "rate",
        dependencies=("transcription", "speaker_attribution", "word_timing", "rate"),
        confounders=("ASR disfluency recognition", "task type"),
    ),
    "drag_count": _definition(
        "unusually lengthened words", "events",
        ("transcript.words", "alignment.segments.chars", "vad.speech_chunks"),
        "rate", dependencies=("transcription", "word_timing", "speaker_attribution"),
        confounders=("word timing error", "natural emphasis"),
    ),
    "loud_spike_count": _definition(
        "words above personal loudness baseline", "events",
        ("acoustics.timeline", "speaker_baselines.median_loudness_db"),
        "loudness", dependencies=("loudness", "speaker_attribution"),
        confounders=("microphone distance and automatic gain control",),
    ),
    "uptalk_count": _definition(
        "phrase final measured pitch rises", "events",
        ("acoustics.pitch_track", "transcript.words"), "pitch",
        dependencies=("pitch", "word_timing", "speaker_attribution"),
        confounders=("question punctuation and expressive intonation",),
    ),
    "uptalk_per_min": _definition(
        "phrase final measured pitch rise rate", "events per minute",
        ("acoustics.pitch_track", "transcript.words", "diarization.turns"),
        "pitch", dependencies=("pitch", "word_timing", "speaker_attribution", "rate"),
        confounders=("question punctuation and expressive intonation",),
    ),
    "backchannels_given": _definition(
        "short interjections inside another speaker turn", "events",
        ("diarization.turns", "transcript.words"), "turn",
        modes=("conversation",), task="interactive conversation",
        dependencies=("transcription", "speaker_attribution", "turn_metrics"),
        confounders=("overlap and diarization error",),
    ),
    "avg_response_pause_s": _definition(
        "mean detected pause before a response", "seconds",
        ("vad.pauses", "turns.pause_before_s"), "response_pause",
        dependencies=("word_timing", "speaker_attribution", "turn_metrics"),
        confounders=("turn segmentation and response opportunity count",),
    ),
    "median_pitch_hz": _definition(
        "median speaker pitch from confidently attributed words", "hertz",
        ("acoustics.pitch_track", "transcript.words.speaker_confidence"),
        "pitch", dependencies=("pitch", "speaker_attribution"),
        confounders=("voicing detection and speaker attribution",),
    ),
    "hedge_count": _definition(
        "rule matched hedging expressions", "events", ("transcript.words",),
        "language", dependencies=("transcription", "speaker_attribution", "language"),
        confounders=("language, dialect, context, and literal phrase use",),
    ),
    "hedges_per_min": _definition(
        "rule matched hedge rate", "events per minute",
        ("transcript.words", "diarization.turns"), "language",
        dependencies=("transcription", "speaker_attribution", "language", "rate"),
        confounders=("language, dialect, context, and literal phrase use",),
    ),
    "hedge_breakdown": _definition(
        "matched hedge phrases by rule", "event counts", ("transcript.words",),
        "language", dependencies=("transcription", "speaker_attribution", "language"),
        confounders=("language, dialect, context, and literal phrase use",),
    ),
    "question_count": _definition(
        "ASR punctuated question endings", "events", ("transcript.words.text",),
        "language", dependencies=("transcription", "speaker_attribution", "language"),
        confounders=("ASR punctuation and rhetorical questions",),
    ),
    "question_ratio": _definition(
        "ASR punctuated questions per attributed turn", "questions per turn",
        ("transcript.words.text", "turns"), "turn",
        dependencies=("transcription", "speaker_attribution", "turn_metrics", "language"),
        confounders=("ASR punctuation and turn segmentation",),
    ),
    "pronoun_balance.i_me_my": _definition(
        "first person singular pronouns", "words", ("transcript.words",),
        "language", dependencies=("transcription", "speaker_attribution", "language"),
        confounders=("task, language, dialect, and quoted speech",),
    ),
    "pronoun_balance.you_your": _definition(
        "second person pronouns", "words", ("transcript.words",),
        "language", dependencies=("transcription", "speaker_attribution", "language"),
        confounders=("task, language, dialect, and quoted speech",),
    ),
    "pronoun_balance.ratio": _definition(
        "first to second person pronoun ratio", "ratio", ("transcript.words",),
        "pronoun_ratio", dependencies=("transcription", "speaker_attribution", "language"),
        confounders=("task, language, dialect, quoted speech, and small denominator",),
    ),
    "repetition_count": _definition(
        "adjacent token or two token repetition", "events", ("transcript.words",),
        "language", dependencies=("transcription", "speaker_attribution", "language"),
        confounders=("intentional rhetorical repetition",),
    ),
    "repetition_rate": _definition(
        "adjacent repetition rate", "events per minute",
        ("transcript.words", "diarization.turns"), "language",
        dependencies=("transcription", "speaker_attribution", "language", "rate"),
        confounders=("intentional rhetorical repetition",),
    ),
    "vocab_variety": _definition(
        "unique token proportion", "ratio", ("transcript.words",),
        "vocabulary", dependencies=("transcription", "speaker_attribution", "language"),
        confounders=("sample length, task, names, language, and inflection",),
    ),
}

VOICE_DEFINITIONS = {
    "pitch_median_hz": ("median detected fundamental frequency", "hertz"),
    "pitch_variation_hz": ("variation of detected fundamental frequency", "hertz"),
    "jitter": ("local cycle to cycle period variation proxy", "ratio"),
    "shimmer": ("local cycle to cycle amplitude variation proxy", "ratio"),
}

VOICE_PROSODY_DEFINITIONS = {
    "f0_median_hz": (
        "median estimated fundamental frequency across eligible voiced frames",
        "hertz", "f0_median_hz",
    ),
    "f0_p05_hz": (
        "fifth percentile estimated fundamental frequency", "hertz",
        "f0_percentiles_hz",
    ),
    "f0_p25_hz": (
        "twenty fifth percentile estimated fundamental frequency", "hertz",
        "f0_percentiles_hz",
    ),
    "f0_p75_hz": (
        "seventy fifth percentile estimated fundamental frequency", "hertz",
        "f0_percentiles_hz",
    ),
    "f0_p95_hz": (
        "ninety fifth percentile estimated fundamental frequency", "hertz",
        "f0_percentiles_hz",
    ),
    "f0_distribution_span_st": (
        "fifth to ninety fifth percentile fundamental frequency distribution span",
        "semitones", "f0_distribution_span_st",
    ),
    "recorder_level_p05_dbfs": (
        "fifth percentile digital recorder level", "dBFS",
        "recorder_level_percentiles_dbfs",
    ),
    "recorder_level_p25_dbfs": (
        "twenty fifth percentile digital recorder level", "dBFS",
        "recorder_level_percentiles_dbfs",
    ),
    "recorder_level_median_dbfs": (
        "median digital recorder level", "dBFS",
        "recorder_level_percentiles_dbfs",
    ),
    "recorder_level_p75_dbfs": (
        "seventy fifth percentile digital recorder level", "dBFS",
        "recorder_level_percentiles_dbfs",
    ),
    "recorder_level_p95_dbfs": (
        "ninety fifth percentile digital recorder level", "dBFS",
        "recorder_level_percentiles_dbfs",
    ),
    "recorder_level_span_db": (
        "fifth to ninety fifth percentile digital recorder level span within one capture",
        "decibels relative within capture", "recorder_level_span_db",
    ),
    "cpps_db": (
        "task specific smoothed cepstral peak prominence", "decibels",
        "cpps_db",
    ),
    "jitter_local_pct": (
        "sustained vowel local period perturbation", "percent",
        "jitter_local_pct",
    ),
    "shimmer_local_pct": (
        "sustained vowel local amplitude perturbation", "percent",
        "shimmer_local_pct",
    ),
}


def is_low_asr_confidence(word):
    """Return true only for a present numeric confidence below the cutoff."""
    value = word.get("confidence")
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and value < ASR_CONFIDENCE_THRESHOLD)


def is_measurement_usable_for_progress(evidence):
    """Use only quality evidence independently released for progress."""
    evidence = evidence or {}
    return (evidence.get("availability", {}).get("status") == "available"
            and evidence.get("quality", {}).get("category")
            in {"high", "moderate"}
            and evidence.get("validation", {}).get("reliability", {})
            .get("progress_use") == "approved")


def _value_at(metrics, path):
    value = metrics
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _computed_paths(metrics):
    paths = set(metrics)
    paths.discard("pronoun_balance")
    pronouns = metrics.get("pronoun_balance")
    if isinstance(pronouns, dict):
        paths.update(f"pronoun_balance.{key}" for key in pronouns)
    return paths


def _warning(category, code, reason):
    return {"category": category, "code": code, "reason": reason}


def _deduplicate(items):
    result = []
    seen = set()
    for item in items:
        key = (item["category"], item["code"], item["reason"])
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def _audio_warnings(audio_quality, dependencies):
    if not isinstance(audio_quality, dict):
        return [_warning(
            "audio_quality_failure", "audio_quality_unavailable",
            "Audio quality evidence is unavailable for this measurement.",
        )]
    warnings = []
    for check in audio_quality.get("checks") or []:
        if check.get("status") not in {"warn", "fail"}:
            continue
        affects = set(check.get("affects") or [])
        if "all_measurements" not in affects and not affects.intersection(dependencies):
            continue
        category = ("audio_quality_failure" if check.get("status") == "fail"
                    else "audio_quality_warning")
        warnings.append(_warning(category, str(check.get("id")),
                                 str(check.get("reason"))))
    return warnings


def _minimum_failures(requirement_name, sample):
    required = MINIMUM_REQUIREMENTS[requirement_name]
    return [
        {"field": field, "required": minimum, "observed": sample.get(field)}
        for field, minimum in required.items()
        if sample.get(field) is None or sample.get(field) < minimum
    ]


def _metric_entry(speaker, path, value, definition, sample, recording_type,
                  shared_warnings):
    warnings = list(shared_warnings)
    failures = _minimum_failures(definition["minimum"], sample)
    available = True
    unavailable_reason = None
    if recording_type not in definition["recording_modes"]:
        available = False
        unavailable_reason = "recording_mode_not_applicable"
        warnings.append(_warning(
            "insufficient_sample", unavailable_reason,
            f"This measurement requires: {', '.join(definition['recording_modes'])}.",
        ))
    elif value is None:
        available = False
        unavailable_reason = "measurement_missing"
        warnings.append(_warning(
            "acoustic_uncertainty" if "pitch" in definition["quality_dependencies"]
            else "insufficient_sample",
            unavailable_reason,
            "The source stage did not produce a value.",
        ))
    elif failures:
        available = False
        unavailable_reason = "insufficient_sample"
        details = ", ".join(
            f"{item['field']} {item['observed']} of {item['required']} required"
            for item in failures
        )
        warnings.append(_warning(
            "insufficient_sample", unavailable_reason,
            f"Minimum evidence was not met: {details}.",
        ))
    if any(item["category"] == "audio_quality_failure" for item in warnings):
        available = False
        unavailable_reason = "audio_quality_failure"

    warnings = _deduplicate(warnings)
    if not available:
        quality = "unavailable"
    elif any(item["category"] == "audio_quality_warning" for item in warnings):
        quality = "low"
    elif warnings:
        quality = "moderate"
    else:
        quality = "high"
    return {
        "value_path": f"computed_metrics.{speaker}.{path}",
        "construct": definition["construct"],
        "unit": definition["unit"],
        "source": {"stage": "merge", "fields": definition["source_fields"]},
        "requirements": {
            "recording_modes": definition["recording_modes"],
            "task": definition["task"],
            "minimum": deepcopy(MINIMUM_REQUIREMENTS[definition["minimum"]]),
        },
        "availability": {
            "status": "available" if available else "unavailable",
            "reason": unavailable_reason,
        },
        "quality": {"category": quality, "meaning": QUALITY_CATEGORIES[quality]},
        "sample": deepcopy(sample),
        "warnings": warnings,
        "known_confounders": definition["confounders"],
        "algorithm_version": MEASUREMENT_ALGORITHM_VERSION,
        "threshold_version": MINIMUM_REQUIREMENTS_VERSION,
        "validation": measurement_validation(path),
    }


def _speaker_shared_warnings(words, audio_quality, dependencies, contamination):
    warnings = _audio_warnings(audio_quality, dependencies)
    low_asr = sum(is_low_asr_confidence(word) for word in words)
    missing_asr = sum(word.get("confidence") is None for word in words)
    low_speaker = sum(
        word.get("speaker_confidence") not in {"high", "smoothed", "referee"}
        for word in words
    )
    if low_asr:
        warnings.append(_warning(
            "transcription_uncertainty", "low_asr_confidence_words",
            f"{low_asr} attributed words are below the provisional ASR confidence cutoff.",
        ))
    if missing_asr:
        warnings.append(_warning(
            "transcription_uncertainty", "missing_asr_confidence",
            f"{missing_asr} attributed words have no ASR confidence value.",
        ))
    if low_speaker:
        warnings.append(_warning(
            "speaker_uncertainty", "low_speaker_confidence_words",
            f"{low_speaker} words have uncertain speaker attribution.",
        ))
    if isinstance(contamination, dict) and contamination.get("status") in {"warn", "unavailable"}:
        warnings.append(_warning(
            "speaker_uncertainty", "solo_contamination",
            contamination.get("warning") or "Solo speaker contamination evidence is unavailable.",
        ))
    return warnings


def _voice_entry(path, value, sample, recording_type, audio_quality,
                 contamination, *, speaker=None, overall=False):
    construct, unit = VOICE_DEFINITIONS[path]
    warnings = _audio_warnings(audio_quality, ("voice_quality", "pitch"))
    if overall and recording_type == "conversation":
        warnings.append(_warning(
            "speaker_uncertainty", "multiple_voices_blended",
            "Whole recording voice quality blends multiple speakers.",
        ))
    if isinstance(contamination, dict) and contamination.get("status") == "warn":
        warnings.append(_warning(
            "speaker_uncertainty", "solo_contamination",
            str(contamination.get("warning")),
        ))
    failures = _minimum_failures("voice_quality", sample)
    available = value is not None and not failures
    reason = None
    if path in {"pitch_variation_hz", "jitter", "shimmer"}:
        available = False
        reason = "legacy_measurement_superseded"
        warnings.append(_warning(
            "validation_limit", reason,
            "This task-blind legacy value cannot support a Phase C conclusion.",
        ))
    if overall and recording_type == "conversation":
        available = False
        reason = "multiple_voices_blended"
    if value is None:
        reason = "measurement_missing"
        warnings.append(_warning(
            "acoustic_uncertainty", reason,
            "The acoustic stage did not produce this voice measurement.",
        ))
    elif failures:
        reason = "insufficient_sample"
        warnings.append(_warning(
            "insufficient_sample", reason,
            f"At least {MINIMUM_REQUIREMENTS['voice_quality']['analysed_s']} seconds of analysed speech are required.",
        ))
    if any(item["category"] == "audio_quality_failure" for item in warnings):
        available = False
        reason = "audio_quality_failure"
    warnings = _deduplicate(warnings)
    if not available:
        quality = "unavailable"
    elif any(item["category"] == "audio_quality_warning" for item in warnings):
        quality = "low"
    elif warnings:
        quality = "moderate"
    else:
        quality = "high"
    root = ("meta.voice_quality_overall" if overall
            else f"meta.per_speaker_voice_quality.{speaker}")
    source_root = ("acoustics.overall" if overall
                   else f"acoustics.per_speaker.{speaker}")
    return {
        "value_path": f"{root}.{path}",
        "construct": construct,
        "unit": unit,
        "source": {"stage": "acoustics", "fields": [f"{source_root}.{path}"]},
        "requirements": {
            "recording_modes": ["solo", "conversation"],
            "task": "sufficient connected voiced speech",
            "minimum": deepcopy(MINIMUM_REQUIREMENTS["voice_quality"]),
        },
        "availability": {"status": "available" if available else "unavailable",
                         "reason": reason},
        "quality": {"category": quality, "meaning": QUALITY_CATEGORIES[quality]},
        "sample": deepcopy(sample),
        "warnings": warnings,
        "known_confounders": [
            "microphone and room conditions", "vocal task", "voice periodicity",
            "health and temporary vocal state",
        ],
        "algorithm_version": "praat-connected-speech-legacy-v3",
        "threshold_version": MINIMUM_REQUIREMENTS_VERSION,
        "validation": measurement_validation(path),
    }


def _voice_prosody_entry(path, value, primitive_state, summary, speaker):
    """Translate the Phase C artifact's own gate into report evidence."""
    construct, unit, availability_key = VOICE_PROSODY_DEFINITIONS[path]
    primitive_state = deepcopy(primitive_state or {})
    status = primitive_state.get("status", "unavailable")
    reason = primitive_state.get("reason")
    quality = primitive_state.get("quality", "unavailable")
    warnings = []
    for warning in primitive_state.get("warnings") or []:
        if "check_id" in warning:
            warnings.append(_warning(
                "audio_quality_warning",
                str(warning.get("check_id")),
                str(warning.get("reason") or "Audio quality limits this primitive."),
            ))
        else:
            warnings.append(_warning(
                "validation_limit",
                str(warning.get("code") or "research_limit"),
                str(warning.get("reason") or "This primitive remains experimental."),
            ))
    task_profile = summary.get("task_profile")
    if task_profile == "unknown_ad_hoc":
        warnings.append(_warning(
            "task_uncertainty", "task_context_unknown",
            "No declared versioned task is available; this attempt is not comparable.",
        ))
        if status == "available" and quality == "high":
            quality = "moderate"
    research_only = availability_key in {
        "cpps_db", "jitter_local_pct", "shimmer_local_pct"
    }
    if research_only and status == "available":
        status = "unavailable"
        reason = "research_only_not_released_evidence"
        quality = "unavailable"
        warnings.append(_warning(
            "validation_limit", reason,
            "The value is retained for governed research and cannot support any "
            "released interpretation.",
        ))
    if value is None:
        status = "unavailable"
        reason = reason or "measurement_missing"
        quality = "unavailable"
    if quality not in QUALITY_CATEGORIES:
        quality = "unavailable" if status != "available" else "moderate"
    validation = measurement_validation(path)
    validation["release_limits"]["single_recording_interpretation"] = (
        "measured_observation_only" if not research_only else "blocked"
    )
    validation["release_limits"]["released_interpretation"] = "blocked"
    validation["release_limits"]["combined_index"] = "blocked"
    return {
        "value_path": f"meta.per_speaker_voice_prosody.{speaker}.{path}",
        "construct": construct,
        "unit": unit,
        "source": {
            "stage": "acoustics",
            "fields": [
                f"acoustics.voice_prosody.speakers.{speaker}.values.{path}"
            ],
        },
        "requirements": {
            "recording_modes": ["solo", "conversation"],
            "task": summary.get("task_id") or "unknown_ad_hoc",
            "task_version": summary.get("task_version"),
            "task_profile": task_profile,
            "task_comparability": summary.get("task_comparability"),
            "minimum": deepcopy(summary.get("sample") or {}),
        },
        "availability": {"status": status, "reason": reason},
        "quality": {"category": quality, "meaning": QUALITY_CATEGORIES[quality]},
        "sample": deepcopy(summary.get("sample") or {}),
        "warnings": _deduplicate(warnings),
        "known_confounders": [
            "declared speech task and prompt",
            "microphone distance angle gain and processing",
            "room noise and reverberation",
            "speaker attribution and overlap",
            "pitch tracking errors and voice periodicity",
        ],
        "algorithm_version": "voice-prosody-primitives-1.0.0",
        "threshold_version": "voice-prosody-contract-1.0.0",
        "validation": validation,
    }


def build_measurement_metadata(computed_metrics, words, turns, acoustics,
                               audio_quality, recording_type,
                               pitch_observation_counts=None,
                               contamination=None):
    """Return metadata parallel to computed metrics without changing values."""
    pitch_observation_counts = pitch_observation_counts or {}
    acoustics = acoustics or {}
    timeline = acoustics.get("timeline") or []
    per_speaker_voice = acoustics.get("per_speaker") or {}
    voice_prosody = acoustics.get("voice_prosody") or {}
    per_speaker_prosody = voice_prosody.get("speakers") or {}
    by_speaker = {}

    for speaker, metrics in computed_metrics.items():
        unknown = _computed_paths(metrics) - set(METRIC_DEFINITIONS)
        if unknown:
            raise ValueError(
                "computed metrics lack evidence definitions: "
                + ", ".join(sorted(unknown))
            )
        speaker_words = [word for word in words
                         if word.get("final_speaker") == speaker]
        speaker_turns = [turn for turn in turns if turn.get("speaker") == speaker]
        pronouns = metrics.get("pronoun_balance") or {}
        sample = {
            "word_count": len(speaker_words),
            "talk_time_s": metrics.get("talk_time_s"),
            "turn_count": len(speaker_turns),
            "response_opportunity_count": max(len(speaker_turns) - 1, 0),
            "pitch_observation_count": pitch_observation_counts.get(speaker, 0),
            "timeline_point_count": len(timeline),
            "second_person_word_count": pronouns.get("you_your", 0),
            "low_asr_confidence_word_count": sum(
                is_low_asr_confidence(word) for word in speaker_words
            ),
            "missing_asr_confidence_word_count": sum(
                word.get("confidence") is None for word in speaker_words
            ),
            "low_speaker_confidence_word_count": sum(
                word.get("speaker_confidence")
                not in {"high", "smoothed", "referee"}
                for word in speaker_words
            ),
        }
        entries = {}
        for path, definition in METRIC_DEFINITIONS.items():
            warnings = _speaker_shared_warnings(
                speaker_words, audio_quality,
                definition["quality_dependencies"], contamination,
            )
            entries[path] = _metric_entry(
                speaker, path, _value_at(metrics, path), definition, sample,
                recording_type, warnings,
            )
        voice = per_speaker_voice.get(speaker) or {}
        voice_sample = {"analysed_s": voice.get("speech_analysed_s")}
        voice_entries = {
            path: _voice_entry(
                path, voice.get(path), voice_sample, recording_type,
                audio_quality, contamination, speaker=speaker,
            )
            for path in VOICE_DEFINITIONS
        }
        prosody_summary = per_speaker_prosody.get(speaker) or {}
        prosody_values = prosody_summary.get("values") or {}
        prosody_states = prosody_summary.get("availability") or {}
        prosody_entries = {
            path: _voice_prosody_entry(
                path,
                prosody_values.get(path),
                prosody_states.get(availability_key),
                prosody_summary,
                speaker,
            )
            for path, (_, _, availability_key) in
            VOICE_PROSODY_DEFINITIONS.items()
        }
        by_speaker[speaker] = {
            "computed_metrics": entries,
            "voice_quality": voice_entries,
            "voice_prosody": prosody_entries,
        }

    overall = acoustics.get("overall") or {}
    overall_sample = {"analysed_s": overall.get("duration_s")}
    overall_voice = {
        path: _voice_entry(
            path, overall.get(path), overall_sample, recording_type,
            audio_quality, contamination, overall=True,
        )
        for path in VOICE_DEFINITIONS
    }
    return {
        "schema_version": MEASUREMENT_SCHEMA_VERSION,
        "algorithm_version": MEASUREMENT_ALGORITHM_VERSION,
        "minimum_requirements_version": MINIMUM_REQUIREMENTS_VERSION,
        "asr_confidence": {
            "low_below": ASR_CONFIDENCE_THRESHOLD,
            "threshold_version": ASR_CONFIDENCE_THRESHOLD_VERSION,
            "calibration_status": "provisional_not_accuracy_calibrated",
        },
        "quality_categories": deepcopy(QUALITY_CATEGORIES),
        "minimum_requirements": deepcopy(MINIMUM_REQUIREMENTS),
        "speakers": by_speaker,
        "overall_voice_quality": overall_voice,
    }
