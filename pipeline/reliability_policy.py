"""Release policy for longitudinal reliability and subgroup evaluation."""

VALIDATION_POLICY_VERSION = "1.1.0"
AUDIT_PROTOCOL_VERSION = "1.0.0"

FAIRNESS_DIMENSIONS = (
    "language",
    "accent",
    "age_band",
    "voice_range",
    "device",
    "audio_quality",
    "speech_difference",
)

COUNT_METRICS = {
    "words", "filler_count", "drag_count", "loud_spike_count",
    "uptalk_count", "backchannels_given", "hedge_count", "question_count",
    "repetition_count", "pronoun_balance.i_me_my",
    "pronoun_balance.you_your",
}
RATE_METRICS = {
    "wpm", "fillers_per_min", "uptalk_per_min", "hedges_per_min",
    "repetition_rate",
}
PROPORTION_METRICS = {
    "talk_share_pct", "question_ratio", "pronoun_balance.ratio",
    "vocab_variety",
}
TIME_METRICS = {"talk_time_s", "avg_response_pause_s"}
PITCH_METRICS = {
    "median_pitch_hz", "pitch_median_hz", "pitch_variation_hz",
    "f0_median_hz", "f0_p05_hz", "f0_p25_hz", "f0_p75_hz",
    "f0_p95_hz", "f0_distribution_span_st",
}
LEGACY_VOICE_QUALITY_METRICS = {"jitter", "shimmer"}
PERTURBATION_PERCENT_METRICS = {"jitter_local_pct", "shimmer_local_pct"}
RECORDER_LEVEL_METRICS = {
    "recorder_level_p05_dbfs", "recorder_level_p25_dbfs",
    "recorder_level_median_dbfs", "recorder_level_p75_dbfs",
    "recorder_level_p95_dbfs", "recorder_level_span_db",
}


def _analysis_plan(metric):
    """Return a metric appropriate prespecified repeatability analysis."""
    if metric in COUNT_METRICS:
        return {
            "error_unit": "events",
            "agreement": "exact and absolute event count agreement",
            "human_repeatability": (
                "event count agreement plus rate SDC95 when exposure differs"
            ),
            "change_rule": (
                "A change is interpretable only above its estimated SDC95 and "
                "a separately justified meaningful change."
            ),
        }
    if metric in RATE_METRICS:
        return {
            "error_unit": "native rate unit",
            "agreement": "absolute difference in the native rate unit",
            "human_repeatability": (
                "ICC(2,1) absolute agreement, SEM agreement, and individual SDC95"
            ),
            "change_rule": (
                "A change is interpretable only above its estimated SDC95 and "
                "a separately justified meaningful change."
            ),
        }
    if metric in PROPORTION_METRICS:
        return {
            "error_unit": "percentage points or ratio units",
            "agreement": "absolute difference in the stored unit",
            "human_repeatability": (
                "ICC(2,1) absolute agreement, SEM agreement, and individual SDC95"
            ),
            "change_rule": (
                "A change is interpretable only above its estimated SDC95 and "
                "a separately justified meaningful change."
            ),
        }
    if metric in TIME_METRICS:
        return {
            "error_unit": "seconds",
            "agreement": "absolute time difference",
            "human_repeatability": (
                "ICC(2,1) absolute agreement, SEM agreement, SDC95, and limits "
                "of agreement"
            ),
            "change_rule": (
                "A change is interpretable only above its estimated SDC95 and "
                "a task specific meaningful change."
            ),
        }
    if metric in PITCH_METRICS:
        pitch_unit = ("semitones" if metric == "f0_distribution_span_st"
                      else "hertz")
        return {
            "error_unit": pitch_unit,
            "agreement": f"absolute difference in {pitch_unit}",
            "human_repeatability": (
                "ICC(2,1) absolute agreement, SEM agreement, SDC95, and limits "
                "of agreement"
            ),
            "change_rule": (
                "A change is interpretable only above its estimated SDC95 and "
                "a task specific meaningful change."
            ),
        }
    if metric in LEGACY_VOICE_QUALITY_METRICS:
        return {
            "error_unit": "stored ratio unit",
            "agreement": "absolute difference in the stored ratio",
            "human_repeatability": (
                "ICC(2,1) absolute agreement, SEM agreement, SDC95, and limits "
                "of agreement"
            ),
            "change_rule": (
                "A change is interpretable only above its estimated SDC95 and "
                "a clinically governed meaningful change."
            ),
        }
    if metric in PERTURBATION_PERCENT_METRICS:
        return {
            "error_unit": "percent",
            "agreement": "absolute difference in percentage points",
            "human_repeatability": (
                "device and task specific bias, limits of agreement, ICC "
                "absolute agreement, SEM agreement, and SDC95"
            ),
            "change_rule": (
                "Research only; no interpretation is released, clinical or "
                "longitudinal."
            ),
        }
    if metric == "cpps_db":
        return {
            "error_unit": "decibels",
            "agreement": "absolute difference in decibels",
            "human_repeatability": (
                "task and device specific bias, limits of agreement, ICC "
                "absolute agreement, SEM agreement, and SDC95"
            ),
            "change_rule": (
                "Research only; no interpretation is released, clinical or "
                "longitudinal."
            ),
        }
    if metric in RECORDER_LEVEL_METRICS:
        return {
            "error_unit": "digital recorder decibels",
            "agreement": "absolute difference in dBFS or within capture dB",
            "human_repeatability": (
                "device and capture processing specific bias, limits of agreement, "
                "ICC absolute agreement, SEM agreement, and SDC95"
            ),
            "change_rule": (
                "No vocal loudness or longitudinal interpretation is permitted "
                "without a calibrated or directly validated capture path."
            ),
        }
    return {
        "error_unit": "native measurement unit",
        "agreement": "metric specific exact or absolute agreement",
        "human_repeatability": "a method must be fixed before labelled evaluation",
        "change_rule": (
            "No longitudinal interpretation is permitted until a metric "
            "specific rule is approved."
        ),
    }


def measurement_validation(metric):
    """Attach the current evidence limit to one measurement."""
    return {
        "policy_version": VALIDATION_POLICY_VERSION,
        "reliability": {
            "status": "experimental",
            "exact_same_input_requirement": "exact for deterministic stages",
            "human_repeatability_status": "not_established",
            "progress_use": "blocked",
            "personal_progress_contract_version": "1.0.0",
            "minimum_baseline_observations": None,
            "natural_variation_status": "not_established",
            "meaningful_change_status": "not_established",
            "reason": (
                "No stable condition repeated productions from enough independent "
                "participants have established measurement error or smallest "
                "detectable change for this metric."
            ),
            "prespecified_analysis": _analysis_plan(metric),
            "acceptable_error": {
                "identical_frozen_input": 0,
                "repeated_human_production": None,
                "status": "not_established",
                "reason": (
                    "A numeric human tolerance cannot be selected from the "
                    "owner recordings or reused across unlike metrics. It must "
                    "be fixed using development participants before held out "
                    "evaluation. Until then the release decision is blocked."
                ),
            },
        },
        "fairness": {
            "status": "not_evaluated",
            "dimensions_not_evaluated": list(FAIRNESS_DIMENSIONS),
            "known_performance_gaps": [],
            "limitation": (
                "No representative independently labelled subgroup evaluation "
                "is available. An empty gap list does not mean equal performance."
            ),
        },
        "release_limits": {
            "single_recording_interpretation": "allowed_with_measurement_quality_limits",
            "individual_progress": "blocked",
            "ranking": "blocked",
            "screening": "blocked",
            "high_stakes_decision": "blocked",
        },
    }
