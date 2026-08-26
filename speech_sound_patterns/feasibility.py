"""Fail-closed helpers for the item 22 local feasibility checkpoint."""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
FEASIBILITY_SCHEMA_VERSION = "1.0.0"
SELECTION_SEED = "speech_sound_patterns_22c_development_selection_v1"
FROZEN_SAMPLE_MANIFEST_SHA256 = (
    "655c8ba92d56b6804b453397f7919cb57ed4875d035f2884493a7c7e63e938fa"
)
ALLOWED_SOURCE_STATES = {
    "development",
    "fixture_not_population_evidence",
    "owner_controlled_integration_only",
}
ALLOWED_SOURCES = {
    "speechocean762",
    "acted_clear_speech_2013",
    "common_phone_1_0",
    "common_voice_26_australian_english",
    "owner_controlled_integration",
}
SPECIAL_PHONE_TOKENS = {
    "<blank>",
    "<sos>",
    "<eos>",
    "<unk>",
    "<eps>",
    "sil",
    "sp",
    "spn",
}
PANPHON_FEATURES = (
    "syl",
    "son",
    "cons",
    "cont",
    "delrel",
    "lat",
    "nas",
    "strid",
    "voi",
    "sg",
    "cg",
    "ant",
    "cor",
    "distr",
    "lab",
    "hi",
    "lo",
    "back",
    "round",
    "velaric",
    "tense",
    "long",
    "hitone",
    "hireg",
)


def canonical_json_bytes(document):
    """Return stable UTF-8 JSON bytes for evidence hashing."""
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_sha256(document):
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_key(source_id, private_identifier):
    value = f"{SELECTION_SEED}\0{source_id}\0{private_identifier}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_private_sample_manifest(document, repository_root):
    """Validate the ignored clip manifest without accepting held-out evidence."""
    errors = []
    if not isinstance(document, dict):
        return ["sample manifest must be an object"]
    required = {
        "schema_version",
        "protocol_id",
        "selection_seed",
        "development_only",
        "sources",
    }
    missing = sorted(required - set(document))
    if missing:
        return [f"sample manifest missing fields: {', '.join(missing)}"]
    if document["schema_version"] != FEASIBILITY_SCHEMA_VERSION:
        errors.append("sample manifest schema version is unsupported")
    if document["protocol_id"] != "speech_sound_local_feasibility_v1":
        errors.append("sample manifest protocol id is unsupported")
    if document["selection_seed"] != SELECTION_SEED:
        errors.append("sample selection seed is not frozen")
    if document["development_only"] is not True:
        errors.append("feasibility selection must be development only")
    sources = document["sources"]
    if not isinstance(sources, list) or not sources:
        return errors + ["sample manifest sources must be nonempty"]

    seen_sources = set()
    seen_safe_ids = set()
    private_root = (
        Path(repository_root) / ".research_data" / "speech_sound_patterns"
    ).resolve()
    for source_index, source in enumerate(sources):
        location = f"sources[{source_index}]"
        if not isinstance(source, dict):
            errors.append(f"{location} must be an object")
            continue
        source_id = source.get("source_id")
        if source_id not in ALLOWED_SOURCES:
            errors.append(f"{location} has an unapproved source")
        elif source_id in seen_sources:
            errors.append(f"{location} repeats source {source_id}")
        seen_sources.add(source_id)
        if source.get("independent_accuracy_evidence") is not False:
            errors.append(f"{location} cannot claim independent accuracy evidence")
        clips = source.get("clips")
        if not isinstance(clips, list) or not clips:
            errors.append(f"{location}.clips must be nonempty")
            continue
        for clip_index, clip in enumerate(clips):
            clip_location = f"{location}.clips[{clip_index}]"
            if not isinstance(clip, dict):
                errors.append(f"{clip_location} must be an object")
                continue
            required_clip = {
                "safe_id",
                "source_state",
                "canonical_audio_path",
                "canonical_audio_sha256",
                "sample_rate_hz",
                "channels",
                "duration_s",
                "intended_text_state",
                "eligible_tools",
            }
            missing_clip = sorted(required_clip - set(clip))
            if missing_clip:
                errors.append(
                    f"{clip_location} missing fields: {', '.join(missing_clip)}"
                )
                continue
            safe_id = clip["safe_id"]
            if not isinstance(safe_id, str) or not safe_id.startswith(source_id):
                errors.append(f"{clip_location}.safe_id is not source scoped")
            elif safe_id in seen_safe_ids:
                errors.append(f"{clip_location}.safe_id is duplicated")
            seen_safe_ids.add(safe_id)
            if clip["source_state"] not in ALLOWED_SOURCE_STATES:
                errors.append(f"{clip_location} is not development-only evidence")
            if clip["sample_rate_hz"] != 16000 or clip["channels"] != 1:
                errors.append(f"{clip_location} is not canonical 16 kHz mono audio")
            duration = clip["duration_s"]
            if (
                not isinstance(duration, (int, float))
                or isinstance(duration, bool)
                or not math.isfinite(duration)
                or duration <= 0
                or duration > 30
            ):
                errors.append(f"{clip_location} has an unsafe duration")
            audio_path = clip["canonical_audio_path"]
            try:
                resolved = (Path(repository_root) / audio_path).resolve()
                resolved.relative_to(private_root)
            except (TypeError, ValueError):
                errors.append(f"{clip_location} audio escapes private storage")
            if not isinstance(clip["canonical_audio_sha256"], str) or len(
                clip["canonical_audio_sha256"]
            ) != 64:
                errors.append(f"{clip_location} audio checksum is invalid")
            tools = clip["eligible_tools"]
            if not isinstance(tools, list) or not tools:
                errors.append(f"{clip_location} must declare eligible tools")
            elif not set(tools) <= {"phoneticxeus", "mfa", "panphon"}:
                errors.append(f"{clip_location} declares an unknown tool")
            if clip["intended_text_state"] == "unknown":
                if "mfa" in tools:
                    errors.append(
                        f"{clip_location} cannot run MFA without known intended text"
                    )
            elif clip["intended_text_state"] != "source_transcript":
                errors.append(f"{clip_location} has an invalid intended text state")
            elif "mfa" in tools:
                text_digest = clip.get("intended_text_sha256")
                if not isinstance(text_digest, str) or len(text_digest) != 64:
                    errors.append(
                        f"{clip_location} MFA transcript checksum is invalid"
                    )
    missing_sources = ALLOWED_SOURCES - seen_sources
    if missing_sources:
        errors.append(
            "sample manifest is missing required sources: "
            + ", ".join(sorted(missing_sources))
        )
    return errors


def validate_frozen_private_sample_manifest(document, repository_root):
    """Validate both the manifest rules and the exact approved private sample."""
    errors = validate_private_sample_manifest(document, repository_root)
    if canonical_json_sha256(document) != FROZEN_SAMPLE_MANIFEST_SHA256:
        errors.append("private feasibility sample does not match the frozen identity")
    return errors


def classify_panphon_token(raw_token, feature_table):
    """Return an auditable, atomic PanPhon classification for one source token."""
    if not isinstance(raw_token, str) or not raw_token:
        raise ValueError("phone token must be a nonempty string")
    nfd = unicodedata.normalize("NFD", raw_token)
    result = {
        "raw": raw_token,
        "raw_codepoints": [f"U+{ord(char):04X}" for char in raw_token],
        "nfd": nfd,
        "nfd_codepoints": [f"U+{ord(char):04X}" for char in nfd],
        "normalization_changed": raw_token != nfd,
        "decision": "unsupported",
        "atomic_panphon_segment": False,
        "features": None,
    }
    if raw_token in SPECIAL_PHONE_TOKENS:
        result["decision"] = "special_nonphone"
        return result
    segments = feature_table.ipa_segs(nfd)
    atomic = bool(feature_table.seg_known(nfd) and segments == [nfd])
    result["atomic_panphon_segment"] = atomic
    result["parsed_segments"] = segments
    if not atomic:
        return result
    segment = feature_table.fts(nfd)
    result["decision"] = "identity_nfd"
    result["features"] = {
        name: segment[name] for name in PANPHON_FEATURES
    }
    return result


def validate_safe_feasibility_report(document):
    """Validate the exact aggregate schema and reject private or unsafe claims."""
    errors = []
    if not isinstance(document, dict):
        return ["feasibility report must be an object"]
    root_keys = {
        "schema_version",
        "checkpoint",
        "status",
        "machine",
        "tools",
        "source_summary",
        "repeatability",
        "resource_use",
        "mapping",
        "release_boundaries",
        "limitations",
    }
    if set(document) != root_keys:
        errors.append("feasibility report root fields must match the aggregate schema")
        if not root_keys.issubset(document):
            return errors

    def exact_keys(value, expected, label):
        if not isinstance(value, dict):
            errors.append(f"{label} must be an object")
            return False
        if set(value) != set(expected):
            errors.append(f"{label} fields must match the aggregate schema")
            return False
        return True

    def finite_nonnegative(value, label, *, positive=False):
        valid = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
            and (not positive or value > 0)
        )
        if not valid:
            errors.append(f"{label} must be a finite {'positive' if positive else 'nonnegative'} number")

    if document["schema_version"] != FEASIBILITY_SCHEMA_VERSION:
        errors.append("feasibility report schema version is unsupported")
    if document["checkpoint"] != "22C":
        errors.append("feasibility report checkpoint must be 22C")
    if document["status"] != "local_feasibility_complete_release_locked":
        errors.append("feasibility report must remain release locked")

    def walk(value, path="report"):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
        elif isinstance(value, str) and (
            ".research_data" in value or value.startswith(("/", "~", "file://"))
        ):
            errors.append(f"{path} exposes a private or absolute storage path")
        elif isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{path} contains a non-finite number")

    walk(document)

    machine = document["machine"]
    if exact_keys(
        machine,
        {
            "hardware",
            "architecture",
            "physical_memory_bytes",
            "operating_system",
            "mps_available",
        },
        "machine",
    ):
        expected_machine = {
            "hardware": "Apple M4",
            "architecture": "arm64",
            "physical_memory_bytes": 17_179_869_184,
            "operating_system": "macOS 26.5.2",
            "mps_available": True,
        }
        if machine != expected_machine:
            errors.append("machine must remain the measured arm64 MPS host")
        finite_nonnegative(machine["physical_memory_bytes"], "machine physical memory", positive=True)

    tools = document["tools"]
    tool_ids = {"montreal_forced_aligner", "phoneticxeus", "panphon"}
    if exact_keys(tools, tool_ids, "tools"):
        mfa = tools["montreal_forced_aligner"]
        if exact_keys(
            mfa,
            {
                "version",
                "environment_python",
                "environment_lock",
                "environment_lock_sha256",
                "acoustic_model",
                "acoustic_model_sha256",
                "acoustic_model_bytes",
                "dictionary",
                "dictionary_sha256",
                "dictionary_bytes",
                "model_and_dictionary_license_metadata",
                "selected_role",
            },
            "tools.montreal_forced_aligner",
        ):
            expected_mfa = {
                "version": "3.4.1",
                "environment_python": "3.11.15",
                "environment_lock": (
                    "speech_sound_patterns/environments/"
                    "mfa-3.4.1-osx-arm64-explicit.txt"
                ),
                "environment_lock_sha256": (
                    "f355141edc0a7f08eb215932220c8139b24aeec72efe4f0f2d1c02cd7a3400c8"
                ),
                "acoustic_model": "english_us_arpa_v3.0.0",
                "acoustic_model_sha256": "d35ce271ded357d833d2f4b8d1041dc3748b9538567ba13f2c697f4e4126711b",
                "acoustic_model_bytes": 91_928_208,
                "dictionary": "english_us_arpa_v3.0.0",
                "dictionary_sha256": "e8c6c7b036ae2b7c78d2768b8dc6b1f9359175b842956d00b48c53c9c332e6b0",
                "dictionary_bytes": 7_186_498,
                "model_and_dictionary_license_metadata": "CC_BY_4.0",
                "selected_role": "expected_text_conditioned_timing_feasibility_only",
            }
            if any(mfa[key] != value for key, value in expected_mfa.items()):
                errors.append("MFA version or evidence role changed")
        xeus = tools["phoneticxeus"]
        if exact_keys(
            xeus,
            {
                "revision",
                "environment_python",
                "environment_lock",
                "environment_lock_sha256",
                "pip_lock",
                "pip_lock_sha256",
                "model_tree_sha256",
                "weights_sha256",
                "weights_bytes",
                "model_card_license_metadata",
                "commercial_release_status",
                "selected_role",
            },
            "tools.phoneticxeus",
        ):
            expected_xeus = {
                "revision": "8d83dee94817a07dc150f87d08f7e0ee01bdb66d",
                "environment_python": "3.10.20",
                "environment_lock": (
                    "speech_sound_patterns/environments/"
                    "phoneticxeus-8d83dee-osx-arm64-explicit.txt"
                ),
                "environment_lock_sha256": (
                    "fc378b1d4f429bcc019fdb0ab554c1dd0dad213d3271f6467f351306dc30b34a"
                ),
                "pip_lock": (
                    "speech_sound_patterns/environments/"
                    "phoneticxeus-8d83dee-pip.txt"
                ),
                "pip_lock_sha256": (
                    "e772cafbc5ac3df1fe02f574a0e5436ea6f14afa4c5541173ff13c7088abb1ad"
                ),
                "model_tree_sha256": "a3d1ee69e9dd4e2926c48f44d1765e0c11489e78ce9d3e06d49f5a3bd0a2ed3e",
                "weights_sha256": "ad58bf20a60e9d0380327bd8b2d0e8e90a9b8de2adccbfb479f9b21ea85eda18",
                "weights_bytes": 2_300_089_432,
                "model_card_license_metadata": "Apache_2.0",
                "commercial_release_status": "blocked_pending_complete_training_provenance_and_license_review",
                "selected_role": "reference_text_independent_phone_candidate_feasibility_only",
            }
            if any(xeus[key] != value for key, value in expected_xeus.items()):
                errors.append("PhoneticXEUS commercial release must remain blocked")
        panphon = tools["panphon"]
        if exact_keys(
            panphon,
            {
                "version",
                "locked_wheel_sha256",
                "license_metadata",
                "packaged_data_sha256",
                "selected_role",
            },
            "tools.panphon",
        ):
            if (
                panphon["version"] != "0.22.2"
                or panphon["locked_wheel_sha256"]
                != "a4c65113430d0699054cb00df978c02712d3c80913a1ef67697f888d96f3a00a"
                or panphon["license_metadata"] != "MIT"
                or panphon["selected_role"]
                != "strict_atomic_ipa_identity_to_24_feature_mapping_only"
            ):
                errors.append("PanPhon version or role changed")
            if exact_keys(
                panphon["packaged_data_sha256"],
                {"ipa_all.csv", "ipa_bases.csv", "feature_weights.csv", "diacritic_definitions.yml"},
                "tools.panphon.packaged_data_sha256",
            ) and panphon["packaged_data_sha256"] != {
                "ipa_all.csv": "0ec0052edf4e58c8c23eda10c0195687eb167ce9bd206cf9a85b9cce8b181f0a",
                "ipa_bases.csv": "61991886e55adaf7df42799bb422af90ff403b2b6cc56dead4a5b4acddcc5568",
                "feature_weights.csv": "03e80a6489e4993de6f17e063eaa74eb59c1d9ba9bc0dec9bec6ffce0cb8080d",
                "diacritic_definitions.yml": "7e93c5bd9ee3dfeea820375d5c7e630dd3f358d2c6a32946091a97b843e73d56",
            }:
                errors.append("PanPhon packaged data checksums changed")

    source = document["source_summary"]
    source_keys = {
        "private_sample_manifest_sha256",
        "selection",
        "development_only",
        "independent_accuracy_evidence",
        "source_count",
        "clip_count",
        "total_audio_s",
        "sources",
        "held_out_participants_or_labels_inspected",
        "owner_clip_used_for_accuracy",
    }
    if exact_keys(source, source_keys, "source_summary"):
        expected_safety = {
            "private_sample_manifest_sha256": FROZEN_SAMPLE_MANIFEST_SHA256,
            "development_only": True,
            "independent_accuracy_evidence": False,
            "source_count": 5,
            "clip_count": 13,
            "total_audio_s": 57.948813,
            "held_out_participants_or_labels_inspected": False,
            "owner_clip_used_for_accuracy": False,
        }
        for key, expected in expected_safety.items():
            if source[key] != expected:
                errors.append(f"source_summary.{key} changed")
        if source["selection"] != (
            "fixed_hash_selection_from_frozen_development_participants_without_using_labels_scores_or_outputs"
        ):
            errors.append("source_summary selection rule changed")
        if not isinstance(source["sources"], list) or len(source["sources"]) != 5:
            errors.append("source_summary.sources must contain five aggregate rows")
        else:
            expected_rows = {
                "acted_clear_speech_2013": (3, "hand_corrected_timing_fixture_only"),
                "common_phone_1_0": (3, "broad_phone_engineering_development_only"),
                "common_voice_26_australian_english": (3, "australian_robustness_development_only"),
                "owner_controlled_integration": (1, "functional_integration_only_unknown_intended_text"),
                "speechocean762": (3, "expert_corpus_development_audio_only_in_this_checkpoint"),
            }
            actual_rows = {}
            for item in source["sources"]:
                if exact_keys(item, {"source", "clip_count", "role"}, "source_summary source row"):
                    actual_rows[item["source"]] = (item["clip_count"], item["role"])
            if actual_rows != expected_rows:
                errors.append("source_summary source roles or counts changed")

    repeatability = document["repeatability"]
    if exact_keys(repeatability, tool_ids, "repeatability"):
        expected_repeat = {
            "montreal_forced_aligner": {
                "clip_count": 12,
                "fresh_alignment_count": 36,
                "canonical_alignment_exact_across_repeats": True,
            },
            "phoneticxeus": {
                "mps_fresh_process_count": 3,
                "mps_warm_inference_count": 130,
                "mps_raw_logits_exact_within_and_across_processes": True,
                "cpu_clip_count": 5,
                "cpu_warm_inference_count": 15,
                "cpu_raw_logits_exact_within_process": True,
                "cpu_mps_comparison_clip_count": 5,
                "cpu_mps_frame_argmax_exact": True,
                "cpu_mps_collapsed_tokens_exact": True,
                "cpu_mps_max_absolute_raw_logit_difference": 0.0001792908,
            },
            "panphon": {
                "observed_unique_phone_tokens": 55,
                "strict_atomic_identity_mappings": 55,
                "unsupported_observed_tokens": 0,
            },
        }
        for key, expected in expected_repeat.items():
            if repeatability[key] != expected:
                errors.append(f"repeatability.{key} changed or is incomplete")

    resources = document["resource_use"]
    resource_keys = {"measurement_note", *tool_ids}
    if exact_keys(resources, resource_keys, "resource_use"):
        expected_resource_keys = {
            "montreal_forced_aligner": {
                "alignment_s_min", "alignment_s_median", "alignment_s_max",
                "alignment_real_time_factor", "maximum_resident_set_bytes",
                "peak_memory_footprint_bytes", "swaps",
            },
            "phoneticxeus": {
                "mps_model_load_s_range", "mps_inference_s_min",
                "mps_inference_s_median", "mps_inference_s_max",
                "mps_inference_real_time_factor", "cpu_inference_s_min",
                "cpu_inference_s_median", "cpu_inference_s_max",
                "cpu_inference_real_time_factor", "mps_maximum_resident_set_bytes",
                "mps_peak_memory_footprint_bytes", "cpu_maximum_resident_set_bytes",
                "cpu_peak_memory_footprint_bytes", "swaps",
            },
            "panphon": {
                "observed_mapping_process_s", "maximum_resident_set_bytes",
                "peak_memory_footprint_bytes", "swaps",
            },
        }
        for tool, keys in expected_resource_keys.items():
            item = resources[tool]
            if exact_keys(item, keys, f"resource_use.{tool}"):
                for key, value in item.items():
                    if key == "mps_model_load_s_range":
                        if not isinstance(value, list) or len(value) != 2:
                            errors.append("PhoneticXEUS model load range is invalid")
                        else:
                            for index, number in enumerate(value):
                                finite_nonnegative(number, f"model load range {index}", positive=True)
                    else:
                        finite_nonnegative(value, f"resource_use.{tool}.{key}", positive=key != "swaps")
                if item["swaps"] != 0:
                    errors.append(f"resource_use.{tool}.swaps must remain zero")

    mapping = document["mapping"]
    if exact_keys(
        mapping,
        {"montreal_forced_aligner", "phoneticxeus", "panphon", "cross_system_agreement_is_truth", "accuracy_or_relation_scoring_performed"},
        "mapping",
    ):
        if mapping["cross_system_agreement_is_truth"] is not False or mapping["accuracy_or_relation_scoring_performed"] is not False:
            errors.append("mapping cannot become truth or accuracy scoring")
        mfa_mapping = mapping["montreal_forced_aligner"]
        if exact_keys(mfa_mapping, {"input", "output", "nonphones", "observed_interval_aggregates", "may_establish_produced_phone"}, "mapping.montreal_forced_aligner"):
            if (
                mfa_mapping["may_establish_produced_phone"] is not False
                or mfa_mapping["input"] != "known_source_transcript_plus_audio"
                or mfa_mapping["output"]
                != "ARPA_word_and_phone_intervals_conditioned_on_expected_sequence"
                or mfa_mapping["nonphones"]
                != ["empty_unlabeled_interval", "eps", "sil", "sp", "spn"]
            ):
                errors.append("MFA cannot establish a produced phone")
            if exact_keys(
                mfa_mapping["observed_interval_aggregates"],
                {
                    "word_count", "phone_count", "lexical_phone_count",
                    "silence_count", "unknown_count", "unlabeled_count",
                    "clips_with_unknown", "clips_with_unlabeled",
                },
                "MFA interval aggregates",
            ) and mfa_mapping["observed_interval_aggregates"] != {
                "word_count": 131,
                "phone_count": 396,
                "lexical_phone_count": 355,
                "silence_count": 36,
                "unknown_count": 4,
                "unlabeled_count": 1,
                "clips_with_unknown": 3,
                "clips_with_unlabeled": 1,
            }:
                errors.append("MFA interval aggregates changed")
        xeus_mapping = mapping["phoneticxeus"]
        if exact_keys(xeus_mapping, {"input", "vocabulary_total", "special_tokens", "phone_tokens", "output", "official_phone_timestamps", "calibrated_confidence", "sequence_alternatives", "top_frame_logits_are_sequence_alternatives"}, "mapping.phoneticxeus"):
            if (
                xeus_mapping["input"] != "mono_16_kHz_audio_without_reference_text"
                or xeus_mapping["output"]
                != "greedy_phone_sequence_plus_contextual_frame_CTC_logits"
                or (xeus_mapping["vocabulary_total"], xeus_mapping["special_tokens"], xeus_mapping["phone_tokens"])
                != (428, 4, 424)
            ):
                errors.append("PhoneticXEUS output semantics changed")
            for key in ("official_phone_timestamps", "calibrated_confidence", "sequence_alternatives", "top_frame_logits_are_sequence_alternatives"):
                if xeus_mapping[key] is not False:
                    errors.append(f"mapping.phoneticxeus.{key} must remain false")
        pan_mapping = mapping["panphon"]
        if exact_keys(pan_mapping, {"input", "normalization", "atomic_identity_required", "feature_count", "unknown_or_composite_behavior", "weighted_distance_enabled"}, "mapping.panphon"):
            if (
                pan_mapping["atomic_identity_required"] is not True
                or pan_mapping["weighted_distance_enabled"] is not False
                or pan_mapping["normalization"] != "NFD_only"
                or pan_mapping["feature_count"] != 24
                or pan_mapping["unknown_or_composite_behavior"]
                != "unsupported_without_partial_mapping"
            ):
                errors.append("PanPhon must remain strict and unweighted")

    boundaries = document.get("release_boundaries", {})
    required_false = {
        "scientific_release",
        "product_release",
        "normal_pipeline_activation",
        "coaching",
        "personal_progress",
        "screening",
        "diagnosis",
    }
    if exact_keys(boundaries, required_false, "release_boundaries"):
        for key in sorted(required_false):
            if boundaries.get(key) is not False:
                errors.append(f"release boundary {key} must remain false")
    limitations = document["limitations"]
    if not isinstance(limitations, list) or len(limitations) < 11 or not all(
        isinstance(item, str) and item for item in limitations
    ):
        errors.append("limitations must retain the complete nonempty limitation set")
    else:
        joined = " ".join(limitations).lower()
        for phrase in (
            "not accuracy",
            "no held out",
            "commercial or product use remains blocked",
            "weighted distance is prohibited",
            "no task detector candidate artifact",
        ):
            if phrase not in joined:
                errors.append(f"limitations are missing required boundary: {phrase}")
    return errors
