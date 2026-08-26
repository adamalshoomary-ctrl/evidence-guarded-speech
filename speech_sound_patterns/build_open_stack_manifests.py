"""Build the checkpoint 22E7 corpus manifests from the acquired bytes.

The manifests are committed, but their numbers are not typed by hand. Every
count, inventory size and checksum in them is produced here by reading the
private acquired files, so a committed figure cannot drift away from the data it
describes. A test rebuilds each manifest and compares it byte for byte with the
committed copy whenever the private material is present on the machine.

That discipline is the direct lesson of checkpoint 22E7's own findings. Three
published figures this project had recorded as fact were wrong, and they were
wrong because somebody had read a number off a web page and copied it forward.
"""

from __future__ import annotations

import argparse
import csv
import json
from functools import partial
from pathlib import Path

from .corpus_audit import assignment_summary, audit_mfa_dictionary, audit_wikipron
from .corpus_manifest import MANIFEST_ROOT, REPOSITORY_ROOT, canonical_json_sha256

PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
LEXICON_ROOT = PRIVATE_ROOT / "lexicons"
RECORD_ROOT = PRIVATE_ROOT / "acquisition"

AUSTRALIAN_EXTRACT = LEXICON_ROOT / "wiktionary-australian-tagged.json"
ACQUIRED_ON = "2026-07-29"

UNIVERSAL_PROHIBITED = [
    "scientific_release_truth",
    "product_release_truth",
    "clinical_inference",
    "accent_quality_judgment",
]

SHAREALIKE_DUTY = (
    "Share alike attaches when adapted material is distributed, not when it is "
    "used internally. A derived lexicon stays on the server. Shipping one inside "
    "a mobile application is distribution and would trigger the licence."
)

LEXICON_SPLIT = {
    "status": "not_applicable",
    "unit": None,
    "source_split_provenance": "A pronunciation lexicon has no speakers, so there is no participant split to make.",
    "project_strategy": "lexicon_has_no_participants",
    "frozen_held_out": False,
    "assignment_artifact": None,
    "assignment_sha256": None,
    "participant_counts": {},
    "cross_split_overlap_count": 0,
    "strata": {},
}


class ManifestBuildError(RuntimeError):
    """Raised when a manifest cannot be rebuilt from the acquired evidence."""


def _acquisition_record(source_id):
    path = RECORD_ROOT / f"{source_id}.json"
    if not path.is_file():
        raise ManifestBuildError(
            f"{source_id} has no acquisition record; run acquire_open_stack first"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _archives(record):
    return [
        {
            "filename": archive["filename"],
            "size_bytes": archive["size_bytes"],
            "canonical_download_url": archive["canonical_download_url"],
            "upstream_checksum": archive["upstream_checksum"],
            "local_sha256": archive["local_sha256"],
            "local_verification_status": archive["local_verification_status"],
        }
        for archive in sorted(record["archives"], key=lambda item: item["filename"])
    ]


def _licence_evidence(record):
    return [
        f"{item['name']} captured {item['captured_at']} from {item['url']}, SHA256 {item['sha256']}."
        for item in sorted(record["licence_snapshots"], key=lambda item: item["name"])
    ]


def _wikipron_manifest(source_id, variety, filename, role, prohibited, description, findings_extra):
    record = _acquisition_record(source_id)
    audit = audit_wikipron(REPOSITORY_ROOT / record["local_storage"] / filename)
    commit = record["archives"][0]["canonical_download_url"].split("/")[5]
    return {
        "schema_version": "1.0.0",
        "manifest_id": f"{source_id}_manifest_v1",
        "source_id": source_id,
        "title": f"WikiPron {variety} English broad pronunciations",
        "version": {
            "label": f"repository commit {commit}, file {filename}",
            "release_date": "2026-07-23",
            "immutable_id": f"wikipron_{commit}_{filename}",
        },
        "citation": "Lee, Jackson L. et al. Massively Multilingual Pronunciation Mining with WikiPron. LREC 2020.",
        "canonical_source": {
            "landing_page": "https://github.com/CUNY-CL/wikipron",
            "licence_url": "https://en.wiktionary.org/wiki/Wiktionary:Copyrights",
        },
        "access": {
            "state": "available",
            "retrieved_at": record["archives"][0]["retrieved_at"],
            "account_required": False,
            "terms_state": "not_required",
            "terms_url": "https://en.wiktionary.org/wiki/Wiktionary:Copyrights",
            "terms_version": None,
            "terms_snapshot_sha256": None,
        },
        "licence": {
            "state": "verified_for_declared_role",
            "spdx_id": "CC-BY-SA-4.0",
            "commercial_use_permitted": True,
            "verified_at": ACQUIRED_ON,
            "attribution_required": True,
            "attribution_text": "Pronunciations mined from English Wiktionary by WikiPron and reused under Wiktionary's CC BY SA terms.",
        },
        "governance": {
            "permitted_roles": [role],
            "prohibited_roles": sorted(set(UNIVERSAL_PROHIBITED) | set(prohibited)),
            "raw_data_committed": False,
            "local_storage": record["local_storage"],
            "rehosting_permitted": False,
            "reidentification_prohibited": True,
            "provider_transfer": "blocked",
            "retention_or_deletion_duties": SHAREALIKE_DUTY,
        },
        "population": {
            "description": description,
            "known_strata": [],
            "limitations": [
                "Wiktionary entries are contributed by volunteers rather than by a documented expert panel, so this is a reference lexicon and never a description of what a speaker produced.",
                f"The scrape carries {audit['phone_inventory_size']} distinct symbols, which is far more than any single English variety uses. Loanwords, narrow transcriptions and non English sounds are present and must be filtered before use.",
                "The branch tip is not a version. This manifest pins the exact commit, because the commit pinned here is itself the one that changed the English dialect selectors.",
                "Share alike attaches when adapted material is distributed, so a derived lexicon stays server side.",
            ],
        },
        "annotation": {
            "truth_class": "unavailable",
            "provenance": "Word and broad IPA pairs mined from English Wiktionary. There is no recording, no speaker and no observation of a production.",
            "fields_retained": ["word", "broad_ipa"],
            "original_records_retained": True,
            "scalar_scores_are_relation_truth": False,
            "limitations": [
                "A lexicon proposes how a word may be said and can never establish how anybody said it, so no truth class applies to it.",
                "A volunteer variety tag is an editorial label, not a measured property of the transcription it carries.",
            ],
        },
        "capability_audit": {
            "status": "complete",
            "inspected_materials": [
                f"The acquired file {filename}, read in full and recounted on {ACQUIRED_ON}.",
            ]
            + _licence_evidence(record),
            "findings": [
                f"The file holds {audit['entries']} entries over {audit['distinct_words']} distinct words, of which {audit['words_with_more_than_one_pronunciation']} carry more than one pronunciation.",
                f"Its recomputed phone inventory is {audit['phone_inventory_size']} distinct symbols.",
                f"{audit['entries_with_a_postvocalic_rhotic']} entries, {audit['postvocalic_rhotic_share'] * 100:.2f} percent, place a rhotic after a vowel and not before one. Post-vocalic rhotics were counted rather than all rhotics, because a non-rhotic variety still has an onset r in red.",
            ]
            + findings_extra,
        },
        "participant_split": dict(LEXICON_SPLIT),
        "lineage": {
            "lineage_group": "wiktionary",
            "derived_from": ["english_wiktionary"],
            "independence_claim": "no_evidence_claim_permitted",
            "duplicate_detection": "Overlap with the Australian tagged Wiktionary entries is expected and recorded, because both derive from the same dictionary and neither is independent evidence of the other.",
            "candidate_model_overlap_status": "unknown_requires_model_specific_audit",
        },
        "archives": _archives(record),
    }


def build_wikipron_uk():
    return _wikipron_manifest(
        "wikipron_eng_latn_uk_broad",
        "British",
        "eng_latn_uk_broad.tsv",
        "british_reference_variant_supplement",
        [
            "australian_variety_truth",
            "accepted_variant_truth",
            "distribution_of_a_derived_lexicon_without_meeting_sharealike",
            "primary_british_reference_without_an_inventory_repair",
        ],
        "British English pronunciation entries mined from Wiktionary in broad IPA.",
        [
            "Measured against the matched American scrape from the same commit, this file is markedly less rhotic, so its British tag carries real signal.",
            "It is still far more rhotic than the Montreal Forced Aligner British dictionary and its inventory is three times larger, so checkpoint 22E7 records it as a supplement to the British reference rather than as the British reference itself.",
        ],
    )


def build_wikipron_us():
    return _wikipron_manifest(
        "wikipron_eng_latn_us_broad",
        "American",
        "eng_latn_us_broad.tsv",
        "american_reference_contrast_measurement",
        [
            "australian_variety_truth",
            "accepted_variant_truth",
            "distribution_of_a_derived_lexicon_without_meeting_sharealike",
            "reference_for_australian_or_british_speakers",
        ],
        "American English pronunciation entries mined from Wiktionary in broad IPA, held only as the matched contrast for the British scrape.",
        [
            "This file exists in the project for one reason: without it, any statement about how British the British scrape is would be an assertion rather than a measurement.",
            "It comes from the same repository, the same commit and the same contributor population as the British scrape, so the two differ in declared variety and in little else.",
        ],
    )


def build_mfa_english_dictionary():
    source_id = "mfa_english_dictionary"
    record = _acquisition_record(source_id)
    storage = REPOSITORY_ROOT / record["local_storage"]
    audits = {
        name: audit_mfa_dictionary(storage / f"{name}.dict")
        for name in ("english_uk_mfa", "english_us_mfa", "english_mfa")
    }
    uk = audits["english_uk_mfa"]
    us = audits["english_us_mfa"]
    generic = audits["english_mfa"]
    return {
        "schema_version": "1.0.0",
        "manifest_id": f"{source_id}_manifest_v1",
        "source_id": source_id,
        "title": "Montreal Forced Aligner English pronunciation dictionaries v3.1.0",
        "version": {
            "label": "v3.1.0, files english_uk_mfa.dict, english_us_mfa.dict and english_mfa.dict",
            "release_date": "2024-06-16",
            "immutable_id": "mfa_models_english_dictionary_v3_1_0",
        },
        "citation": "McAuliffe, Michael and Sonderegger, Morgan. English MFA dictionaries v3.1.0. Montreal Forced Aligner published models, 2024.",
        "canonical_source": {
            "landing_page": "https://mfa-models.readthedocs.io/en/latest/dictionary/English/index.html",
            "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        },
        "access": {
            "state": "available",
            "retrieved_at": record["archives"][0]["retrieved_at"],
            "account_required": False,
            "terms_state": "not_required",
            "terms_url": "https://mfa-models.readthedocs.io/en/latest/dictionary/English/index.html",
            "terms_version": "v3.1.0",
            "terms_snapshot_sha256": None,
        },
        "licence": {
            "state": "verified_for_declared_role",
            "spdx_id": "CC-BY-4.0",
            "commercial_use_permitted": True,
            "verified_at": ACQUIRED_ON,
            "attribution_required": True,
            "attribution_text": "Montreal Forced Aligner English pronunciation dictionaries v3.1.0 by McAuliffe and Sonderegger, reused under CC BY 4.0.",
        },
        "governance": {
            "permitted_roles": [
                "british_referenced_expected_phone_path",
                "american_referenced_expected_phone_path",
            ],
            "prohibited_roles": sorted(
                set(UNIVERSAL_PROHIBITED)
                | {"australian_variety_truth", "accepted_variant_truth"}
            ),
            "raw_data_committed": False,
            "local_storage": record["local_storage"],
            "rehosting_permitted": False,
            "reidentification_prohibited": True,
            "provider_transfer": "blocked",
            "retention_or_deletion_duties": "Attribution is required wherever a derived pronunciation is published or shipped. Nothing is rehosted.",
        },
        "population": {
            "description": "Aligner ready English pronunciation dictionaries published beside the Montreal Forced Aligner acoustic models, in one shared phone alphabet across varieties.",
            "known_strata": ["english_uk_mfa", "english_us_mfa", "english_mfa"],
            "limitations": [
                "There is no Australian English dictionary in the published set, so this cannot supply an Australian reference on its own.",
                "A dictionary describes a documented variety, not any individual speaker, and it can never accept or reject what a speaker produced.",
                "The generic English dictionary mixes varieties and is retained only as the recorded alternative that was not chosen.",
            ],
        },
        "annotation": {
            "truth_class": "unavailable",
            "provenance": "Published word and phone dictionaries with pronunciation and silence probabilities. There is no recording, no speaker and no observation of a production.",
            "fields_retained": ["word", "pronunciation_probabilities", "phones"],
            "original_records_retained": True,
            "scalar_scores_are_relation_truth": False,
            "limitations": [
                "A lexicon proposes how a word may be said and can never establish how anybody said it, so no truth class applies to it.",
                "The probability columns describe pronunciation frequency inside the aligner and are not confidence in a speaker's production.",
            ],
        },
        "capability_audit": {
            "status": "complete",
            "inspected_materials": [
                f"All three acquired dictionary files, read in full and recounted on {ACQUIRED_ON}.",
            ]
            + _licence_evidence(record),
            "findings": [
                f"English (UK) holds {uk['entries']} entries over {uk['distinct_words']} head words with {uk['phone_inventory_size']} distinct phones. English (US) holds {us['entries']} entries over {us['distinct_words']} head words with {us['phone_inventory_size']} distinct phones. Generic English holds {generic['entries']} entries over {generic['distinct_words']} head words with {generic['phone_inventory_size']} distinct phones.",
                "Those counts each exceed the published figures by exactly the aligner's own special tokens. English (UK) adds <unk>, <cutoff>, [bracketed] and [laughter] to the documented 46,163 words, generic English adds <unk> to the documented 42,352, and both add the spoken noise phone spn to the documented phone list. The earlier recorded inventories of 99 and 103 phones for generic English were both wrong; the page lists 91 and the file carries 92 including spn.",
                f"Post-vocalic rhotics separate the two varieties exactly as a real British and American pair should: {uk['postvocalic_rhotic_share'] * 100:.2f} percent of English (UK) entries against {us['postvocalic_rhotic_share'] * 100:.2f} percent of English (US) entries.",
                f"Generic English sits between them at {generic['postvocalic_rhotic_share'] * 100:.2f} percent, which is the measurable sense in which it is not one variety.",
                "Checkpoint 22E7 therefore chooses English (UK) as the British referenced expected-phone path and English (US) as its American counterpart, because the pair shares one phone alphabet. Two reference paths that differed in alphabet as well as in variety could not produce an interpretable difference at checkpoint 22E8.",
            ],
        },
        "participant_split": dict(LEXICON_SPLIT),
        "lineage": {
            "lineage_group": "montreal_forced_aligner",
            "derived_from": [],
            "independence_claim": "no_evidence_claim_permitted",
            "duplicate_detection": "The aligner pinned at checkpoint 22C carries its own American ARPA dictionary in a different phone alphabet, and the two must never be mixed in one comparison.",
            "candidate_model_overlap_status": "not_applicable",
        },
        "archives": _archives(record),
    }


def build_wiktionary_australian():
    source_id = "wiktionary_australian_kaikki"
    record = _acquisition_record(source_id)
    if not AUSTRALIAN_EXTRACT.is_file():
        raise ManifestBuildError(
            "the Australian tagged extract is missing; run extract_kaikki_australian first"
        )
    extract = json.loads(AUSTRALIAN_EXTRACT.read_text(encoding="utf-8"))
    entries = extract["entries"]
    pronunciations = sum(len(items) for items in entries.values())
    plain = {word for word in entries if word.isalpha() and word.islower()}
    phonemic = {
        word
        for word, items in entries.items()
        if any(item["ipa"].startswith("/") for item in items)
    }
    pool = plain & phonemic
    return {
        "schema_version": "1.0.0",
        "manifest_id": f"{source_id}_manifest_v1",
        "source_id": source_id,
        "title": "Wiktionary Australian tagged English pronunciations, through Kaikki",
        "version": {
            "label": "Kaikki English extraction of 2026-07-25 from the enwiktionary dump dated 2026-07-06",
            "release_date": "2026-07-25",
            "immutable_id": "kaikki_english_20260725_enwiktionary_20260706",
        },
        "citation": "Ylonen, Tatu. Wiktextract: Wiktionary as Machine-Readable Structured Data. LREC 2022.",
        "canonical_source": {
            "landing_page": "https://kaikki.org/dictionary/English/",
            "licence_url": "https://en.wiktionary.org/wiki/Wiktionary:Copyrights",
        },
        "access": {
            "state": "available",
            "retrieved_at": record["archives"][0]["retrieved_at"],
            "account_required": False,
            "terms_state": "not_required",
            "terms_url": "https://en.wiktionary.org/wiki/Wiktionary:Copyrights",
            "terms_version": None,
            "terms_snapshot_sha256": None,
        },
        "licence": {
            "state": "verified_for_declared_role",
            "spdx_id": "CC-BY-SA-4.0",
            "commercial_use_permitted": True,
            "verified_at": ACQUIRED_ON,
            "attribution_required": True,
            "attribution_text": "Entries extracted from English Wiktionary by Wiktextract and reused under Wiktionary's CC BY SA terms.",
        },
        "governance": {
            "permitted_roles": ["australian_reference_variant_overlay"],
            "prohibited_roles": sorted(
                set(UNIVERSAL_PROHIBITED)
                | {
                    "accepted_variant_truth",
                    "acoustic_judgement",
                    "distribution_of_a_derived_lexicon_without_meeting_sharealike",
                }
            ),
            "raw_data_committed": False,
            "local_storage": record["local_storage"],
            "rehosting_permitted": False,
            "reidentification_prohibited": True,
            "provider_transfer": "blocked",
            "retention_or_deletion_duties": SHAREALIKE_DUTY,
        },
        "population": {
            "description": "English Wiktionary entries whose pronunciation carries an Australian accent tag, extracted locally from the full English Wiktextract release.",
            "known_strata": ["Australian", "Australia", "General-Australian"],
            "limitations": [
                "A Wiktionary accent tag is a volunteer annotation, so it may propose a target and can never accept or reject what a speaker produced.",
                "Entries mix phonemic transcriptions in slashes with narrower phonetic transcriptions in brackets, and the two are different claims that must not be pooled.",
                "Many Australian tagged pronunciations carry other variety tags beside the Australian one, so they are shared pronunciations rather than distinctively Australian ones.",
                "Kaikki regenerates weekly and publishes no checksum, so the acquired archive itself is the only fixed record of these exact bytes.",
                "Share alike attaches when adapted material is distributed, so a derived lexicon stays server side.",
            ],
        },
        "annotation": {
            "truth_class": "unavailable",
            "provenance": "Word, part of speech, IPA and accent tags extracted from English Wiktionary. There is no recording, no speaker and no observation of a production.",
            "fields_retained": ["word", "ipa", "accent_tags", "part_of_speech"],
            "original_records_retained": True,
            "scalar_scores_are_relation_truth": False,
            "limitations": [
                "A lexicon proposes how a word may be said and can never establish how anybody said it, so no truth class applies to it.",
                "An Australian tag identifies a documented Australian pronunciation, not the pronunciation a particular Australian speaker uses.",
            ],
        },
        "capability_audit": {
            "status": "complete",
            "inspected_materials": [
                f"The full acquired extraction, {extract['english_entries']} English entries read line by line on {ACQUIRED_ON}.",
                "A census of every pronunciation tag in the extraction, taken before any tag was selected.",
            ]
            + _licence_evidence(record),
            "findings": [
                f"The accent tag vocabulary was measured rather than guessed. The extraction carries {extract['distinct_pronunciation_tags']} distinct pronunciation tags, and exactly three are Australian: {', '.join(extract['australian_tags'])}. Selecting on a guessed tag name would have built the wrong reference silently.",
                f"Those tags yield {len(entries)} distinct words carrying {pronunciations} Australian tagged pronunciations. The figure of roughly 2,700 entries recorded from the 2026-07-28 search is wrong and is corrected here.",
                f"{len(plain)} of those words are plain lower case alphabetic forms rather than affixes, contractions or multiword entries, and {len(pool)} of those also carry a phonemic transcription.",
                "Against a prompt pack of about twenty chosen words, that pool is ample many times over, which is what checkpoint 22F needs to know.",
                "Inspected entries show the exact phenomena this repair exists for: car as /kaː/ without a final rhotic, bath as /bɐːθ/, dance as /dæːns/ and data as a flapped [ˈdäːɾə].",
            ],
        },
        "participant_split": dict(LEXICON_SPLIT),
        "lineage": {
            "lineage_group": "wiktionary",
            "derived_from": ["english_wiktionary"],
            "independence_claim": "no_evidence_claim_permitted",
            "duplicate_detection": "Overlap with the WikiPron scrapes is expected and recorded, because all three derive from the same dictionary and none is independent evidence of another.",
            "candidate_model_overlap_status": "unknown_requires_model_specific_audit",
        },
        "archives": _archives(record),
    }


COMMON_VOICE_SUBSETS = {
    "common_voice_26_british_english": {
        "filename": "common-voice-26-british-english.json",
        "title": "Common Voice Scripted Speech 26.0 British English",
        "dataset_id": "cmrt6zrob000zmm07yqwjlpwi",
        "storage": "common_voice_26_gb",
        "locale": "en-GB",
        "role": "british_variety_comparison_group",
        "extra_prohibited": [],
        "selection": (
            "Validated rows whose self declared accent field indicates an England, "
            "Scottish, Welsh or Irish accent, matched case insensitively. No gender "
            "or age filter is applied."
        ),
        "extra_limitations": [
            "This is British Isles English pooled across England, Scotland, Wales and Ireland, not England alone, so it is broader than the variety the repaired reference describes.",
            "No gender filter was applied here, while both American subsets were filtered to a declared gender. The groups are therefore not selected identically, and that asymmetry is reported rather than absorbed.",
        ],
        "role_note": "The variety the repaired reference actually describes, so it should improve most cleanly under it. That makes it the informative middle case rather than a spare comparison.",
    },
    "common_voice_26_american_english_male": {
        "filename": "common-voice-26-american-english-male.json",
        "title": "Common Voice Scripted Speech 26.0 American English, male speakers",
        "dataset_id": "cmrt6zbgx000vmm07hfuefigk",
        "storage": "common_voice_26_us_male",
        "locale": "en-US",
        "role": "american_variety_control_group",
        "extra_prohibited": ["american_comparison_from_one_gender_alone"],
        "selection": (
            "Validated rows whose self declared accent field is exactly United States "
            "English with no other co-occurring tag, and whose gender field is exactly "
            "male_masculine."
        ),
        "extra_limitations": [
            "This subset is male only. Used on its own it would make accent and speaker gender vary together, so the female subset must be present for any American comparison to mean anything.",
            "Filtering on a declared gender also excludes American contributors who declared none, while the Australian and British subsets include theirs.",
        ],
        "role_note": "Half of the American control group. The control is the group that should stay roughly unchanged when the reference variety is repaired.",
    },
    "common_voice_26_american_english_female": {
        "filename": "common-voice-26-american-english-female.json",
        "title": "Common Voice Scripted Speech 26.0 American English, female speakers",
        "dataset_id": "cmrt70j4z001qmm07nvfsmgmr",
        "storage": "common_voice_26_us_female",
        "locale": "en-US",
        "role": "american_variety_control_group",
        "extra_prohibited": ["american_comparison_from_one_gender_alone"],
        "selection": (
            "Validated rows whose self declared accent field is exactly United States "
            "English with no other co-occurring tag, and whose gender field is exactly "
            "female_feminine."
        ),
        "extra_limitations": [
            "This subset is female only and exists to remove the gender confound in the male subset. Neither American subset may stand as the American group by itself.",
            "Filtering on a declared gender also excludes American contributors who declared none, while the Australian and British subsets include theirs.",
        ],
        "role_note": "The other half of the American control group, acquired so that accent and speaker gender do not vary together.",
    },
}


EXCLUSION_RECORD = (
    PRIVATE_ROOT / "splits" / "common-voice-26-accent-group-exclusions.json"
)


def _group_membership_finding(source_id):
    """State plainly whether this subset shares a contributor with another group."""
    if not EXCLUSION_RECORD.is_file():
        raise ManifestBuildError(
            "the accent group exclusion record is missing; "
            "run build_common_voice_exclusions first"
        )
    document = json.loads(EXCLUSION_RECORD.read_text(encoding="utf-8"))
    excluded = document["excluded_participants"]
    mine = {
        participant_id: item
        for participant_id, item in excluded.items()
        if source_id in item["subsets"]
    }
    relative = EXCLUSION_RECORD.relative_to(REPOSITORY_ROOT)
    digest = canonical_json_sha256(document)
    if not mine:
        return (
            "No clip path and no client identifier is shared with any other Common "
            "Voice accent subset this project holds, so no speaker of this group is "
            f"also a speaker of another. Checked against {len(document['subsets_checked'])} "
            f"subsets and recorded in {relative}, SHA256 {digest}."
        )
    others = sorted(
        {
            other
            for item in mine.values()
            for other in item["subsets"]
            if other != source_id
        }
    )
    return (
        f"{len(mine)} contributor of this subset also appears in "
        f"{', '.join(others)}, having declared a different variety on different "
        "clips. Common Voice asks for accent per clip and accepts more than one "
        "answer, so this is a property of the source rather than a packaging "
        "error. No clip is shared. Such a contributor cannot represent either "
        "variety and is excluded from every comparison group rather than "
        "assigned to whichever they recorded more clips for. The exclusion is "
        f"frozen in {relative}, SHA256 {digest}, and checkpoint 22E8 must honour it."
    )


def _common_voice_manifest(source_id):
    profile = COMMON_VOICE_SUBSETS[source_id]
    record = _acquisition_record(source_id)
    metadata_root = PRIVATE_ROOT / "metadata" / profile["storage"]
    assignment_path = (
        PRIVATE_ROOT / "splits" / f"{profile['storage'].replace('_', '-')}.json"
    )
    if not assignment_path.is_file():
        raise ManifestBuildError(
            f"{source_id} has no frozen participant split; run audit_common_voice first"
        )
    assignment = json.loads(assignment_path.read_text(encoding="utf-8"))
    summary = assignment_summary(assignment)
    clip_counts = {}
    for split in ("train", "dev", "test"):
        path = metadata_root / f"{split}.tsv"
        if not path.is_file():
            raise ManifestBuildError(f"{source_id} is missing {split}.tsv metadata")
        with path.open(newline="", encoding="utf-8") as handle:
            clip_counts[split] = sum(1 for _ in csv.DictReader(handle, delimiter="\t"))
    participants = sum(summary["participant_counts"].values())
    relative_assignment = str(assignment_path.relative_to(REPOSITORY_ROOT))
    return {
        "schema_version": "1.0.0",
        "manifest_id": f"{source_id}_manifest_v1",
        "source_id": source_id,
        "title": profile["title"],
        "version": {
            "label": f"26.0 accent subset, locale {profile['locale']}",
            "release_date": "2026-07-20",
            "immutable_id": f"mdc_{profile['dataset_id']}",
        },
        "citation": (
            f"Mozilla Data Collective Curators. {profile['title']}, "
            f"dataset {profile['dataset_id']}."
        ),
        "canonical_source": {
            "landing_page": f"https://mozilladatacollective.com/datasets/{profile['dataset_id']}",
            "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        },
        "access": {
            "state": "available",
            "retrieved_at": record["archives"][0]["retrieved_at"],
            "account_required": True,
            "terms_state": "accepted",
            "terms_url": "https://mozilladatacollective.com/terms/consumers",
            "terms_version": "2026-05-06",
            "terms_snapshot_sha256": next(
                item["sha256"]
                for item in record["licence_snapshots"]
                if item["name"] == "mdc_consumer_terms.html"
            ),
        },
        "licence": {
            "state": "verified_for_declared_role",
            "spdx_id": "CC0-1.0",
            "commercial_use_permitted": True,
            "verified_at": ACQUIRED_ON,
            "attribution_required": False,
            "attribution_text": None,
        },
        "governance": {
            "permitted_roles": [profile["role"]],
            "prohibited_roles": sorted(
                set(UNIVERSAL_PROHIBITED)
                | {
                    "phone_truth",
                    "australian_lexical_variant_truth",
                    "speaker_reidentification",
                    "dataset_rehosting",
                    "selection_evidence_for_a_common_voice_trained_model",
                }
                | set(profile["extra_prohibited"])
            ),
            "raw_data_committed": False,
            "local_storage": record["local_storage"],
            "rehosting_permitted": False,
            "reidentification_prohibited": True,
            "provider_transfer": "blocked",
            "retention_or_deletion_duties": "Do not rehost or re-share, do not attempt reidentification, maintain reasonable safeguards, and cease use or delete copies if required by account termination and the applicable dataset licence.",
        },
        "population": {
            "description": (
                f"Validated scripted speech, {sum(clip_counts.values())} clips from "
                f"{participants} self identified speakers in the supplied speaker "
                f"disjoint splits. {profile['selection']}"
            ),
            "known_strata": ["source_train", "source_dev", "source_test"],
            "limitations": [
                "Accent information is self reported context rather than phonetic truth.",
                "Sentence validation does not prove every phone matched one pronunciation.",
                "The subset provides no phone timestamps and no lexical pronunciation variants.",
                "Recording quality varies across contributors. Comparing accent subsets of one release on one platform controls most of that, and a difference between two reference paths on the same audio remains far better evidence than a difference between two corpora.",
            ]
            + profile["extra_limitations"],
        },
        "annotation": {
            "truth_class": "validated_sentence_audio",
            "provenance": "Common Voice sentence prompts, listener validation votes and optional self reported metadata; no phone annotation.",
            "fields_retained": [
                "client_id_private",
                "path_private",
                "sentence_id",
                "sentence",
                "validation_votes",
                "self_reported_accent_context",
                "source_split",
            ],
            "original_records_retained": True,
            "scalar_scores_are_relation_truth": False,
            "limitations": [
                "A validated sentence supports a false concern and differential rate measurement only.",
                "These are native speakers reading known text, so a flag is presumed a false concern rather than a detected error, and no detection accuracy claim can rest on this source.",
                "Self reported demographic fields are optional and cannot create pronunciation truth.",
            ],
        },
        "capability_audit": {
            "status": "complete",
            "inspected_materials": [
                f"Authenticated dataset metadata, and the archive digest recomputed locally on {ACQUIRED_ON}.",
                "The supplied train, dev and test files, read row by row for participant and clip identifiers.",
            ]
            + _licence_evidence(record),
            "findings": [
                f"The package contains {clip_counts['train']} train, {clip_counts['dev']} dev and {clip_counts['test']} test clips.",
                f"The splits contain {summary['participant_counts']['development']}, {summary['participant_counts']['threshold_tuning']} and {summary['participant_counts']['held_out_evaluation']} speakers respectively.",
                "No client identifier appears in more than one supplied split.",
                _group_membership_finding(source_id),
                profile["role_note"],
            ],
        },
        "participant_split": {
            "status": "audited",
            "unit": "participant",
            "source_split_provenance": "The package supplies train, dev and test TSV files with zero client identifier overlap.",
            "project_strategy": "Map source train to development, source dev to threshold tuning and source test to frozen held out evaluation, exactly as the Australian subset already is.",
            "frozen_held_out": True,
            "assignment_artifact": relative_assignment,
            "assignment_sha256": summary["assignment_sha256"],
            "participant_counts": summary["participant_counts"],
            "cross_split_overlap_count": 0,
            "strata": summary["strata"],
        },
        "lineage": {
            "lineage_group": "common_voice",
            "derived_from": ["common_voice_26_english"],
            "independence_claim": "not_independent_of_common_voice_family",
            "duplicate_detection": "Private client and clip identifiers are checked against every Common Voice derived source before assembly.",
            "candidate_model_overlap_status": "known_overlap_not_independent",
        },
        "archives": _archives(record),
    }


BUILDERS = {
    "wikipron_eng_latn_uk_broad": (build_wikipron_uk, "wikipron-uk-broad.json"),
    "wikipron_eng_latn_us_broad": (build_wikipron_us, "wikipron-us-broad.json"),
    "wiktionary_australian_kaikki": (
        build_wiktionary_australian,
        "wiktionary-australian-kaikki.json",
    ),
    "mfa_english_dictionary": (
        build_mfa_english_dictionary,
        "mfa-english-dictionary.json",
    ),
    **{
        source_id: (
            partial(_common_voice_manifest, source_id),
            profile["filename"],
        )
        for source_id, profile in COMMON_VOICE_SUBSETS.items()
    },
}


def manifest_bytes(document):
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def build_all():
    return {
        source_id: (builder(), filename)
        for source_id, (builder, filename) in BUILDERS.items()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="write the manifests instead of checking"
    )
    args = parser.parse_args()
    differences = []
    for source_id, (document, filename) in build_all().items():
        path = MANIFEST_ROOT / filename
        payload = manifest_bytes(document)
        if args.write:
            path.write_bytes(payload)
            print(f"{source_id}: wrote {filename}")
            continue
        if not path.is_file() or path.read_bytes() != payload:
            differences.append(source_id)
    if not args.write:
        if differences:
            print("Open stack manifests differ from the acquired evidence:")
            for source_id in differences:
                print(f"  {source_id}")
            raise SystemExit(1)
        print("Open stack manifests rebuild exactly from the acquired evidence.")


if __name__ == "__main__":
    main()
