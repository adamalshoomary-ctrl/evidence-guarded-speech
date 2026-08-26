"""Build the checkpoint 23B candidate reference source survey.

Item 23 needs three kinds of independent human reference evidence that it does
not have: motor task timing and accuracy marked by two trained annotators,
perceptual voice judgement from several qualified raters with the individual
ratings kept, and intelligibility transcribed by several unfamiliar listeners.

This module records what publicly identifiable sources could supply, what they
may lawfully be used for, and whether they can be obtained at all.  It selects
nothing.  A record can say that a source ``fails`` a truth requirement or that
the question is ``unresolved``; it can never say that a source meets one,
because that judgement belongs to the independent governance roles rather than
to a survey.

Every fact below carries the date it was checked and whether it was verified
directly against the repository, catalogue or host, or merely reported and left
unverified.  Item 22 learned this the expensive way: published figures and
availability claims in this field are wrong often enough that an unverified
claim must be labelled rather than absorbed.

Rebuild with::

    python3 -m motor_speech_voice.build_source_survey
"""

from __future__ import annotations

import json
from pathlib import Path


SURVEY_ROOT = Path(__file__).resolve().parent / "source_survey"
SCHEMA_FILENAME = "source-survey-schema-v1.0.0.json"
REGISTRY_FILENAME = "source-survey-registry-v1.0.0.json"

CHECKED_AT = "2026-08-19"

# Roles every record shares.  Nothing here acquires, transfers or selects.
PERMITTED_ROLES = [
    "governance_review_material",
    "evidence_that_a_route_exists_or_does_not_exist",
]
PROHIBITED_ROLES = [
    "acquisition_without_a_separate_owner_decision",
    "item_23_truth_source",
    "candidate_training_or_tuning_data",
    "motor_speech_or_voice_claim",
    "clinical_inference",
    "product_release_truth",
    "substitute_for_independent_professional_review",
]


def _record(**fields):
    """Fill the shared governance and provenance shape around one source."""
    fields.setdefault("schema_version", "1.0.0")
    fields["record_id"] = f"{fields['source_id']}_survey_v1"
    fields["governance"] = {
        "permitted_roles": list(PERMITTED_ROLES),
        "prohibited_roles": list(PROHIBITED_ROLES),
        "raw_data_committed": False,
        "acquisition_authorised": False,
        "transfer_to_any_provider": "blocked",
    }
    fields["eligibility"]["selected"] = False
    fields["access"].setdefault("checked_at", CHECKED_AT)
    fields["licence"].setdefault("verified_at", CHECKED_AT)
    return fields


# ---------------------------------------------------------------------------
# Lane A: motor task timing and accuracy
#
# The item 23 requirement is two blinded trained annotators marking cycles and
# errors, with adjudication.  No source below supplies that publicly.
# ---------------------------------------------------------------------------

MOTOR_SOURCES = [
    _record(
        source_id="younger_nt_adults",
        title="Younger NT Adults diadochokinetic set (DDKtor / DDK deep network papers)",
        citation=(
            "Segal-Feldman, Y. et al. Enhancing analysis of diadochokinetic speech "
            "using deep neural networks. Computer Speech & Language, 2024."
        ),
        canonical_source={
            "landing_page": "https://github.com/MLSpeech/DDKtor",
            "terms_or_licence_url": None,
        },
        language_and_variety={
            "language": "English",
            "variety": "United States English, not stated explicitly",
            "covers_australian_english": False,
        },
        population={
            "description": (
                "92 neurotypical adult participants recorded as pre-test data in "
                "speech motor learning experiments, median age 22 to 25 across splits."
            ),
            "age_band": "adults",
            "clinical_status": "healthy",
            "limitations": [
                "Collected as pre-test data for a different experiment, not for a "
                "measurement validation purpose.",
                "Young adults only, so it cannot describe an adult population "
                "across the age range item 23 would include.",
            ],
        },
        tasks_present=["alternating_motion_rate", "sequential_motion_rate"],
        reference_truth={
            "offered_truth_class": "motor_task_timing_two_annotator",
            "independent_rater_or_annotator_count": 2,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "unresolved",
            "failure_reasons": [
                "This is the closest published match to the item 23 motor timing "
                "requirement: two independent annotators marked voice onset times "
                "and vowel durations and boundaries on AMR and SMR from "
                "neurotypical adults.",
                "No public release was located. The paper carries no data "
                "availability statement and the MIT licensed DDKtor repository "
                "distributes code and one model file but no speech data or "
                "annotations.",
                "Whether individual annotator records and an adjudication rule were "
                "kept cannot be determined without the data.",
            ],
        },
        access={
            "route": "no_public_release_located",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "unobtainable",
        },
        licence={
            "stated": None,
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "Full text of the Computer Speech & Language paper, read on 2026-08-19.",
                "The MLSpeech/DDKtor repository landing page, read on 2026-08-19.",
            ],
            "findings": [
                "The paper describes the annotation protocol in detail: burst onset "
                "from waveform spike and broadband spectrogram energy, vowel onset "
                "from the positive zero crossing at the start of periodic energy, "
                "syllable offset at the last periodic cycle.",
                "The repository instructs users to supply their own wav files and "
                "TextGrid annotations, confirming no data ships with it.",
                "No data availability statement, repository link or licence for the "
                "speech data appears anywhere in the paper.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_no_public_release",
            "reasons": [
                "The single best conceptual match for the item 23 motor timing truth "
                "class is not published, so no licence question even arises.",
                "Obtaining it would require contacting the authors, which is not "
                "authorised and would still leave rights, ethics and privacy open.",
            ],
        },
    ),
    _record(
        source_id="ondri_speech",
        title="Ontario Neurodegenerative Disease Research Initiative motor speech recordings",
        citation=(
            "Sunderland, K. M. et al. Characteristics of the Ontario Neurodegenerative "
            "Disease Research Initiative cohort. Alzheimer's & Dementia 19(1), 2023."
        ),
        canonical_source={
            "landing_page": "https://ondri.ca/",
            "terms_or_licence_url": None,
        },
        language_and_variety={
            "language": "English",
            "variety": "Canadian English",
            "covers_australian_english": False,
        },
        population={
            "description": (
                "147 participants aged 55 to 85 at baseline, 122 at one year "
                "follow-up, across neurodegenerative disease groups."
            ),
            "age_band": "adults",
            "clinical_status": "clinical",
            "limitations": [
                "A disease cohort recruited for a different longitudinal purpose.",
                "Parkinson's disease participants were recorded in the optimal "
                "medication ON state, which is a controlled but non-representative "
                "condition.",
            ],
        },
        tasks_present=["alternating_motion_rate", "sequential_motion_rate"],
        reference_truth={
            "offered_truth_class": "motor_task_accuracy_two_annotator",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": False,
            "adjudication_defined": False,
            "requirement_status": "fails",
            "failure_reasons": [
                "Syllable segmentation came from a Praat script that trained raters "
                "then corrected, so the human labels are corrections of a machine "
                "proposal rather than independent marking.",
                "The paper states explicitly that inter-annotator agreement is not "
                "available, so annotator disagreement cannot be inspected.",
                "Files were trimmed before analysis and the longest syllable train "
                "was selected, which is a preparation decision that the reference "
                "and any candidate would share.",
            ],
        },
        access={
            "route": "application_and_review",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": True,
            "account_required": True,
            "agreement_signature_required": True,
            "fee": None,
            "state": "obtainable_only_after_contact_or_agreement",
        },
        licence={
            "stated": None,
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "Full text of the Computer Speech & Language paper describing the "
                "ONDRI and Sub-ONDRI annotation, read on 2026-08-19.",
            ],
            "findings": [
                "The Sub-ONDRI subgroup of five participants did receive two "
                "independent annotators, but five participants cannot support any "
                "measurement error or variation estimate.",
                "The full ONDRI set was segmented at syllable level only, so it "
                "carries no voice onset time or vowel duration reference.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_truth_class",
            "reasons": [
                "Explicitly unavailable inter-annotator agreement means the reference "
                "cannot report its own uncertainty, which item 23 requires of every "
                "human reference.",
                "Access needs an institutional application this project cannot make.",
            ],
        },
    ),
]

MOTOR_SOURCES += [
    _record(
        source_id="ewa_db",
        title="EWA-DB, Early Warning of Alzheimer speech database",
        citation=(
            "Rusko, M. et al. Slovak database of speech affected by neurodegenerative "
            "diseases. Scientific Data 11, 2024. doi:10.1038/s41597-024-04171-6"
        ),
        canonical_source={
            "landing_page": "https://catalog.elda.org/en-us/repository/browse/ELRA-S0489/",
            "terms_or_licence_url": "https://zenodo.org/records/10952480",
        },
        language_and_variety={
            "language": "Slovak",
            "variety": None,
            "covers_australian_english": False,
        },
        population={
            "description": (
                "1,649 speakers: 1,323 healthy controls, 175 Parkinson's disease, "
                "87 Alzheimer's disease, 62 mild cognitive impairment, 2 mixed. "
                "Audio is published only for the 1,003 speakers who gave written "
                "consent to publication."
            ),
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": [
                "Slovak, so nothing about it transfers to an English task without "
                "separate evidence.",
                "Recorded through a smartphone application on mixed Apple and "
                "Android devices at 16 kHz, so device effects are uncontrolled.",
                "646 of the 1,649 speakers did not consent to audio publication.",
            ],
        },
        tasks_present=[
            "sustained_vowel",
            "diadochokinesis_pataka",
            "object_and_action_naming",
            "picture_description",
        ],
        reference_truth={
            "offered_truth_class": "population_description_only",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": False,
            "adjudication_defined": False,
            "requirement_status": "fails",
            "failure_reasons": [
                "The manual annotation is automatic speech recognition transcription "
                "corrected by trained annotators, plus tags for phenomena such as "
                "hesitation and intelligibility. It is not syllable boundary, "
                "syllable count, timing or task error marking for the "
                "diadochokinesis recordings.",
                "The remaining labels are diagnosis, demographic and clinical test "
                "scores. A diagnosis describes a study population and is not the "
                "numeric ground truth for a timing primitive.",
                "Annotators were predominantly speech and language pathology "
                "students working under supervision, and no agreement statistic "
                "for the diadochokinesis task is reported.",
            ],
        },
        access={
            "route": "free_account_and_signed_agreement",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": True,
            "agreement_signature_required": True,
            "fee": "0.00 EUR for academic and commercial users, member and non member",
            "state": "obtainable_only_after_contact_or_agreement",
        },
        licence={
            "stated": (
                "ELRA catalogue offers Non Commercial Use, ELRA END USER and "
                "Commercial Use, ELRA VAR; the Zenodo deposit states no licence"
            ),
            "spdx_id": None,
            "commercial_use_permitted": True,
            "source_of_licence_string": "catalogue_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "Zenodo API record 10952480, queried 2026-08-19.",
                "ELRA catalogue entry ELRA-S0489, read 2026-08-19.",
                "PubMed Central full text PMC11618578, read 2026-08-19.",
            ],
            "findings": [
                "The ELRA distribution includes audio for 1,003 consenting speakers, "
                "ASR transcription JSON for all 1,649, and manual annotation for a "
                "further subset, at 0.00 EUR under either licence type.",
                "The ELRA route needs an account and a signed licence, which is a "
                "click-through rather than a negotiation, but is still an agreement "
                "this project has not decided to sign.",
            ],
            "conflicting_claims": [
                "The Scientific Data paper states the database is publicly available "
                "at ELDA and at Zenodo. The Zenodo deposit is in fact access "
                "restricted with no licence recorded and no files listed, so the "
                "Zenodo half of that published claim is wrong as of 2026-08-19.",
                "The paper's own description of manual annotation coverage and the "
                "ELRA catalogue's speaker count for manual annotation do not match "
                "exactly; neither figure is relied on here.",
            ],
        },
        eligibility={
            "decision": "blocked_truth_class",
            "reasons": [
                "The largest openly obtainable collection of rapid syllable "
                "recordings carries no rapid syllable reference truth.",
                "It could support engineering feasibility questions only, and even "
                "that would need a separate owner decision to sign the ELRA licence "
                "and a separate rights and privacy review.",
            ],
        },
    ),
    _record(
        source_id="voc_als",
        title="VOC-ALS, voice signals in amyotrophic lateral sclerosis and healthy controls",
        citation=(
            "Sannino, G. et al. Voice signals database of ALS patients with different "
            "dysarthria severity and healthy controls. Scientific Data 11, 2024. "
            "doi:10.1038/s41597-024-03597-2"
        ),
        canonical_source={
            "landing_page": "https://www.synapse.org/Synapse:syn53009474",
            "terms_or_licence_url": "https://www.nature.com/articles/s41597-024-03597-2",
        },
        language_and_variety={
            "language": "Italian",
            "variety": None,
            "covers_australian_english": False,
        },
        population={
            "description": (
                "153 participants: 51 healthy controls and 102 people with ALS at "
                "differing dysarthria severity, recruited consecutively at one "
                "hospital ALS centre."
            ),
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": [
                "Italian, and a single-centre clinical cohort.",
                "Recorded on one smartphone model through one application, so the "
                "capture path is fixed and untested against any other device.",
            ],
        },
        tasks_present=["sustained_vowel", "syllable_repetition_pa_ta_ka"],
        reference_truth={
            "offered_truth_class": "population_description_only",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": False,
            "adjudication_defined": False,
            "requirement_status": "fails",
            "failure_reasons": [
                "Labels are the ALSFRS-R speech subscore and derived acoustic "
                "measures. No human marked syllable boundaries, counts, onsets or "
                "task errors.",
                "A clinical rating scale subscore is a different truth class from "
                "task timing and cannot be pooled with it.",
            ],
        },
        access={
            "route": "free_account_and_signed_agreement",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": True,
            "agreement_signature_required": True,
            "fee": None,
            "state": "obtainable_only_after_contact_or_agreement",
        },
        licence={
            "stated": "Creative Commons Attribution 4.0 International",
            "spdx_id": "CC-BY-4.0",
            "commercial_use_permitted": True,
            "source_of_licence_string": "publication_text",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "PubMed Central full text PMC11271596, read 2026-08-19.",
            ],
            "findings": [
                "All recordings were sampled at 8000 Hz with 16 bit resolution. "
                "That is telephone bandwidth and is not adequate for burst or voice "
                "onset time measurement, whatever the licence permits.",
                "Access requires a Synapse Registered User profile and acceptance of "
                "Synapse governance and terms of use.",
            ],
            "conflicting_claims": [
                "The licence string comes from the article rather than from the "
                "Synapse landing page, which did not render a licence. The two have "
                "not been reconciled.",
            ],
        },
        eligibility={
            "decision": "blocked_truth_class",
            "reasons": [
                "No rapid syllable reference truth, and an 8 kHz capture path that "
                "would not support timing measurement even if there were.",
            ],
        },
    ),
    _record(
        source_id="neurovoz",
        title="NeuroVoz, Castilian Spanish corpus of parkinsonian speech",
        citation=(
            "Mendes-Laureano, J. et al. NeuroVoz: a Castillian Spanish corpus of "
            "parkinsonian speech. Scientific Data, 2024."
        ),
        canonical_source={
            "landing_page": "https://zenodo.org/records/10777657",
            "terms_or_licence_url": "https://zenodo.org/records/10777657",
        },
        language_and_variety={
            "language": "Spanish",
            "variety": "Castilian Spanish",
            "covers_australian_english": False,
        },
        population={
            "description": (
                "112 native Castilian Spanish speakers, 58 healthy controls and 54 "
                "people with Parkinson's disease recorded in the medication ON state."
            ),
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": [
                "Spanish, and a single clinical condition.",
                "Recorded only in the medication ON state.",
            ],
        },
        tasks_present=[
            "sustained_vowel",
            "diadochokinesis_pa_ta_ka",
            "listen_and_repeat",
            "monologue",
        ],
        reference_truth={
            "offered_truth_class": "perceptual_voice_single_rater",
            "independent_rater_or_annotator_count": 1,
            "individual_records_retained": False,
            "adjudication_defined": False,
            "requirement_status": "fails",
            "failure_reasons": [
                "The perceptual material is a GRBAS assessment by one expert. Item 23 "
                "requires several blinded qualified raters with individual ratings "
                "and disagreement retained, and states that one clinician cannot "
                "substitute.",
                "The diadochokinetic recordings carry no human syllable marking.",
            ],
        },
        access={
            "route": "application_and_review",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": False,
            "account_required": True,
            "agreement_signature_required": False,
            "fee": None,
            "state": "restricted",
        },
        licence={
            "stated": (
                "Creative Commons Attribution Non Commercial No Derivatives 4.0 "
                "International"
            ),
            "spdx_id": "CC-BY-NC-ND-4.0",
            "commercial_use_permitted": False,
            "source_of_licence_string": "repository_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "Zenodo record 10777657 and the Zenodo search API, read 2026-08-19.",
            ],
            "findings": [
                "The record is publicly listed but the audio files are restricted "
                "and require login plus permission from the data custodians.",
                "The non commercial and no derivatives terms block this project "
                "independently of the access question.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_licence_non_commercial",
            "reasons": [
                "A non commercial licence cannot support a commercial product "
                "backend, which is what this repository is.",
                "No derivatives additionally blocks the transformations any analysis "
                "would need.",
            ],
        },
    ),
    _record(
        source_id="alois_db",
        title="ALOIS-DB, speech and language affected by mild cognitive impairment",
        citation="ALOIS-DB Zenodo deposit 17037153, 2025.",
        canonical_source={
            "landing_page": "https://zenodo.org/records/17037153",
            "terms_or_licence_url": "https://zenodo.org/records/17037153",
        },
        language_and_variety={
            "language": "Slovak",
            "variety": None,
            "covers_australian_english": False,
        },
        population={
            "description": "258 speakers with mild cognitive impairment and healthy controls.",
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": ["Slovak, and a single cognitive condition focus."],
        },
        tasks_present=["sustained_vowel", "diadochokinesis"],
        reference_truth={
            "offered_truth_class": "unresolved",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "unresolved",
            "failure_reasons": [
                "The deposit is access restricted, so what annotation it carries "
                "cannot be inspected and must fail closed.",
            ],
        },
        access={
            "route": "application_and_review",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": False,
            "account_required": True,
            "agreement_signature_required": True,
            "fee": None,
            "state": "restricted",
        },
        licence={
            "stated": None,
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": ["Zenodo API record 17037153, queried 2026-08-19."],
            "findings": [
                "Access is restricted, no licence is recorded and no files are "
                "listed, so both the rights and the content questions are open.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_access_restricted",
            "reasons": [
                "Restricted access with no stated licence fails closed on both "
                "rights and content.",
            ],
        },
    ),
]


def _derived_measures_record(source_id, title, citation, url, description, findings):
    """Openly licensed rapid syllable numbers that ship without any audio.

    These are worth recording precisely because they look like a solution and
    are not one.  A published table of syllable rates can describe what values
    other researchers observed.  It cannot validate an implementation, because
    there is no recording to run the implementation on.
    """
    return _record(
        source_id=source_id,
        title=title,
        citation=citation,
        canonical_source={"landing_page": url, "terms_or_licence_url": url},
        language_and_variety={
            "language": "not stated on the record",
            "variety": None,
            "covers_australian_english": False,
        },
        population={
            "description": description,
            "age_band": "unknown",
            "clinical_status": "unknown",
            "limitations": [
                "The deposit contains derived measurements only. There is no audio.",
            ],
        },
        tasks_present=["diadochokinesis"],
        reference_truth={
            "offered_truth_class": "derived_measures_without_audio",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "fails",
            "failure_reasons": [
                "Without audio there is nothing for a candidate implementation to "
                "be run against, so this cannot serve as a reference for any "
                "computational or analytical validation.",
                "Published summary values from another protocol are not a "
                "reference range for a different task, population or capture path.",
            ],
        },
        access={
            "route": "open_direct_download",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "obtainable_without_contact",
        },
        licence={
            "stated": "Creative Commons Attribution 4.0 International",
            "spdx_id": "CC-BY-4.0",
            "commercial_use_permitted": True,
            "source_of_licence_string": "repository_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": ["Zenodo API record, queried 2026-08-19."],
            "findings": findings,
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_truth_class",
            "reasons": [
                "Openly licensed and freely obtainable, and still not a reference "
                "source, because it holds numbers rather than speech.",
            ],
        },
    )


MOTOR_SOURCES += [
    _derived_measures_record(
        "ddk_development_measures",
        "Supplementary material, diadochokinetic tasks from childhood to adulthood",
        (
            "Lancheros, M., Friedrichs, D. & Laganaro, M. What do differences between "
            "alternating and sequential diadochokinetic tasks tell us about the "
            "development of oromotor skills? 2023."
        ),
        "https://zenodo.org/records/10018228",
        "Participants across childhood, adolescence and adulthood; counts are not stated on the record.",
        [
            "One spreadsheet of syllabic rate and articulatory execution measures "
            "for alternating and sequential tasks.",
            "Open access under CC BY 4.0 with a single file and no recordings.",
        ],
    ),
    _derived_measures_record(
        "ddk_post_stroke_rate_measures",
        "Diadochokinetic rate measures in post-stroke spastic and unilateral upper motor neuron dysarthria",
        "De-identified diadochokinetic rate dataset, Zenodo deposit 18324421.",
        "https://zenodo.org/records/18324421",
        "Adults with post-stroke dysarthria; counts are not stated on the record.",
        [
            "Participant level diadochokinetic rate measures in syllables per second "
            "for alternating tasks, supplied as one de-identified spreadsheet.",
        ],
    ),
    _derived_measures_record(
        "plosive_vot_features_parkinson",
        "Articulatory features of plosive consonants for early detection of Parkinson's disease",
        "Extracted voice onset time feature deposit, Zenodo 10406860.",
        "https://zenodo.org/records/10406860",
        "27 individuals diagnosed with Parkinson's disease and 27 healthy controls.",
        [
            "Temporal and spectral features extracted from voice onset time segments "
            "of the plosives in rapid syllables, supplied as two feature files.",
            "The features are already the output of somebody else's unvalidated "
            "extraction choices, so they cannot check a different implementation.",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Lane B: perceptual voice judgement
#
# The item 23 requirement is several blinded qualified raters under a
# standardised protocol, with individual ratings and disagreement retained.
# ---------------------------------------------------------------------------

VOICE_SOURCES = [
    _record(
        source_id="pvqd",
        title="Perceptual Voice Qualities Database",
        citation=(
            "Walden, P. R. Perceptual Voice Qualities Database (PVQD): database "
            "characteristics. Journal of Voice, 2020. Mendeley Data 9dz247gnyb."
        ),
        canonical_source={
            "landing_page": "https://data.mendeley.com/datasets/9dz247gnyb/2",
            "terms_or_licence_url": "https://data.mendeley.com/datasets/9dz247gnyb/2",
        },
        language_and_variety={
            "language": "English",
            "variety": "United States English",
            "covers_australian_english": False,
        },
        population={
            "description": (
                "296 audio recordings across a range of voice quality severities, "
                "ages and sexes, recorded in a quiet environment with a head mounted "
                "condenser microphone at 44.1 kHz and 16 bit resolution."
            ),
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": [
                "United States English throughout, so it carries the same imported "
                "reference problem item 22 documented for phone level work.",
                "The distribution is weighted toward euphonic and mildly impaired "
                "voices, with comparatively few severe cases.",
                "Only 187 of the 296 samples carry a specified diagnosis.",
            ],
        },
        tasks_present=["sustained_vowel_a_and_i", "cape_v_sentences"],
        reference_truth={
            "offered_truth_class": "perceptual_voice_multi_rater",
            "independent_rater_or_annotator_count": 19,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "unresolved",
            "failure_reasons": [
                "This is the only openly licensed source located that plausibly "
                "reaches the multiple qualified rater requirement: 19 expert raters "
                "across six blocks, each block rated by three or four listeners, "
                "with samples presented twice.",
                "Whether the distributed ratings file retains individual rater rows "
                "or only combined values cannot be resolved without opening the "
                "file, and no acquisition is authorised, so this stays unresolved "
                "rather than being assumed either way.",
                "The database provides combined vowel and sentence ratings, so it "
                "cannot answer task specific questions, and it omits the CAPE-V "
                "consistency judgement entirely.",
                "Its own published reliability analysis pooled ratings across blocks "
                "without accounting for block specific variability, which risks "
                "inflating the reported reliability.",
                "Independent re-rating measured the real ceiling. Eight speech "
                "language pathologists rating a curated 30 sample subset produced "
                "inter-rater intraclass correlations of 0.79 on vowels and 0.87 on "
                "sentences for overall severity, 0.76 and 0.70 for breathiness, "
                "0.60 and 0.56 for roughness, 0.51 and 0.66 for strain, 0.34 and "
                "0.24 for pitch, and 0.47 and 0.47 for loudness. Pitch and loudness "
                "are therefore poor, and no candidate may be graded against them.",
                "On the most reliable feature the median absolute difference between "
                "raters was 14.8 points on vowels and 12.5 points on sentences on a "
                "100 point scale. No automatic measure can be shown to be more "
                "accurate than that, because there is nothing more accurate to "
                "compare it with.",
            ],
        },
        access={
            "route": "open_direct_download",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "obtainable_without_contact",
        },
        licence={
            "stated": "CC BY 4.0",
            "spdx_id": "CC-BY-4.0",
            "commercial_use_permitted": True,
            "source_of_licence_string": "repository_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "Mendeley Data record 9dz247gnyb version 2, read 2026-08-19, and a "
                "reachability check returning HTTP 200 on the same date.",
                "Open access full text of Pommee, Renaud and Verduyckt, Reliability "
                "and task effects in CAPE-V auditory-perceptual voice assessments: "
                "insights from the PVQD30 subset, Journal of Voice 2025, "
                "doi:10.1016/j.jvoice.2025.02.020, read 2026-08-19.",
            ],
            "findings": [
                "The independent re-rating study also records concrete quality "
                "problems in the source: some samples are incomplete, some contain "
                "reading errors or clinician instructions, and recording conditions "
                "and background noise are inconsistent across the set.",
                "The eight raters in that study were Quebecois clinicians rating "
                "United States English material, which is itself a variety mismatch "
                "of the kind item 22 measured.",
                "Deciding whether this source satisfies the item 23 perceptual truth "
                "requirement is a governance judgement, not a survey outcome. This "
                "record deliberately cannot express that it does.",
            ],
            "conflicting_claims": [
                "Secondary descriptions of the database report four raters with one "
                "rating only 16 percent of cases. The open access PVQD30 paper "
                "reports 19 expert raters across six blocks. Only the second was "
                "read at source, and the first is not relied on here.",
            ],
        },
        eligibility={
            "decision": "open_but_truth_class_unresolved",
            "reasons": [
                "Openly licensed for commercial use and obtainable with no contact, "
                "no account and no agreement.",
                "Whether it can serve as perceptual reference truth remains open on "
                "two counts: whether individual rater records are distributed, and "
                "whether independent voice governance accepts it at all.",
                "Its measured agreement ceiling constrains any future claim built on "
                "it, and rules out pitch and loudness specifically.",
            ],
        },
    ),
    _record(
        source_id="saarbruecken_voice_database",
        title="Saarbruecken Voice Database",
        citation="Puetzer, M. & Barry, W. J. Saarbruecken Voice Database. Zenodo 16874898.",
        canonical_source={
            "landing_page": "https://zenodo.org/records/16874898",
            "terms_or_licence_url": "https://zenodo.org/records/16874898",
        },
        language_and_variety={
            "language": "German",
            "variety": None,
            "covers_australian_english": False,
        },
        population={
            "description": (
                "More than 2,000 German speakers phonating vowels and producing a "
                "short sentence, recorded at 50 kHz and 16 bit, spanning normal "
                "voices and a wide range of laryngeal and voice pathologies."
            ),
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": [
                "German, so its material cannot be read into an English task.",
                "Organised by pathology label, which describes a population rather "
                "than measuring a voice property.",
            ],
        },
        tasks_present=["sustained_vowel", "short_sentence"],
        reference_truth={
            "offered_truth_class": "audio_without_qualifying_labels",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "fails",
            "failure_reasons": [
                "The deposit carries recordings and pathology grouping. It carries no "
                "perceptual rating of any kind, so it supplies no perceptual truth.",
            ],
        },
        access={
            "route": "open_direct_download",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "obtainable_without_contact",
        },
        licence={
            "stated": "Creative Commons Attribution 4.0 International",
            "spdx_id": "CC-BY-4.0",
            "commercial_use_permitted": True,
            "source_of_licence_string": "repository_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "Zenodo API record 16874898, queried 2026-08-19, showing open access, "
                "CC BY 4.0 and 73 archive files grouped by pathology.",
                "Reachability checks on 2026-08-19: stimmdb.coli.uni-saarland.de "
                "returned HTTP 200 and the older stimmdatenbank host returned 404.",
            ],
            "findings": [
                "The collection moved host and is now managed by Essen University "
                "Hospital with a Zenodo distribution, so earlier notes that it was "
                "offline for revision are out of date.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_truth_class",
            "reasons": [
                "Openly licensed audio with no perceptual reference attached.",
            ],
        },
    ),
    _record(
        source_id="saarbruecken_grb_labels",
        title="GRB assessment of the Saarbruecken Voice Database",
        citation=(
            "Arias-Londono, J. D., Gomez-Garcia, J. A., Godino-Llorente, J. I. & "
            "Mendes-Laureano, J. GRB assessment of the Saarbruecken Voice Database. "
            "Zenodo 3550736, annex to IEEE JSTSP 14(2), 2020."
        ),
        canonical_source={
            "landing_page": "https://zenodo.org/records/3550736",
            "terms_or_licence_url": "https://zenodo.org/records/3550736",
        },
        language_and_variety={
            "language": "German",
            "variety": None,
            "covers_australian_english": False,
        },
        population={
            "description": (
                "Grade, roughness and breathiness labels covering a subset of the "
                "Saarbruecken speakers; the associated paper uses 568 normophonic "
                "and 970 pathological subjects."
            ),
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": [
                "Labels only. The recordings live in the separate Saarbruecken "
                "deposit.",
            ],
        },
        tasks_present=["sustained_vowel_a_i_u"],
        reference_truth={
            "offered_truth_class": "perceptual_voice_single_rater",
            "independent_rater_or_annotator_count": 1,
            "individual_records_retained": False,
            "adjudication_defined": False,
            "requirement_status": "fails",
            "failure_reasons": [
                "The labels come from a single evaluator. The paper the deposit "
                "annexes describes its own predecessor work as emulating the "
                "perceptual capabilities of a single evaluator, and refers "
                "throughout to the perceptual evaluation provided by the speech "
                "therapist in the singular.",
                "Item 23 states directly that one clinician cannot substitute for "
                "several independent qualified raters, so an openly licensed single "
                "rater label set does not become perceptual truth by being free.",
            ],
        },
        access={
            "route": "open_direct_download",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "obtainable_without_contact",
        },
        licence={
            "stated": "Creative Commons Attribution 4.0 International",
            "spdx_id": "CC-BY-4.0",
            "commercial_use_permitted": True,
            "source_of_licence_string": "repository_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "Zenodo API record 3550736, queried 2026-08-19: open access, "
                "CC BY 4.0, one spreadsheet of 122,880 bytes.",
                "Open access preprint of the annexed IEEE JSTSP paper, Zenodo "
                "record 3601013, read 2026-08-19.",
            ],
            "findings": [
                "This is the nearest thing to a free perceptual label set attached to "
                "a free audio corpus, and it fails on rater multiplicity alone.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_truth_class",
            "reasons": [
                "Single rater perceptual labels are excluded by the item 23 truth "
                "architecture regardless of licence or availability.",
            ],
        },
    ),
]

VOICE_SOURCES += [
    _record(
        source_id="hupa",
        title="HUPA, Castilian Spanish corpus of voice disorders",
        citation="HUPA corpus, Zenodo deposit 17704572, with an associated Data in Brief article.",
        canonical_source={
            "landing_page": "https://zenodo.org/records/17704572",
            "terms_or_licence_url": "https://zenodo.org/records/17704572",
        },
        language_and_variety={
            "language": "Spanish",
            "variety": "Castilian Spanish",
            "covers_australian_english": False,
        },
        population={
            "description": "440 speakers, 239 healthy controls and 201 with diagnosed voice disorders.",
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": ["Spanish, sustained vowel only."],
        },
        tasks_present=["sustained_vowel_a"],
        reference_truth={
            "offered_truth_class": "unresolved",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "unresolved",
            "failure_reasons": [
                "The deposit is access restricted with no licence recorded, so its "
                "annotation cannot be inspected and fails closed.",
                "Published descriptions of how many raters assessed the recordings "
                "disagree with each other, so rater multiplicity is unresolved.",
            ],
        },
        access={
            "route": "application_and_review",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": False,
            "account_required": True,
            "agreement_signature_required": True,
            "fee": None,
            "state": "restricted",
        },
        licence={
            "stated": None,
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": ["Zenodo API record 17704572, queried 2026-08-19."],
            "findings": [
                "Access restricted, no licence recorded, no files listed.",
            ],
            "conflicting_claims": [
                "The associated article text has been reported to state a CC BY "
                "licence while the Zenodo deposit records none and restricts access. "
                "The repository page is treated as authoritative and the conflict is "
                "recorded rather than resolved.",
                "One published description reports three expert raters and another "
                "reports rating in situ by a single otolaryngologist. Neither was "
                "confirmed at source.",
            ],
        },
        eligibility={
            "decision": "blocked_licence_unresolved",
            "reasons": [
                "No licence and restricted access is a fail closed state on rights.",
            ],
        },
    ),
    _record(
        source_id="voiced_physionet",
        title="VOICED database",
        citation="VOICED database, PhysioNet, version 1.0.0.",
        canonical_source={
            "landing_page": "https://physionet.org/content/voiced/1.0.0/",
            "terms_or_licence_url": "https://physionet.org/content/voiced/1.0.0/",
        },
        language_and_variety={
            "language": "Italian",
            "variety": None,
            "covers_australian_english": False,
        },
        population={
            "description": "208 voice samples, 150 pathological and 58 healthy.",
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": ["Sustained vowel only, so no connected speech material."],
        },
        tasks_present=["sustained_vowel_a"],
        reference_truth={
            "offered_truth_class": "population_description_only",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": False,
            "adjudication_defined": False,
            "requirement_status": "fails",
            "failure_reasons": [
                "Labels are diagnosis, demographics, lifestyle factors and the "
                "participant reported Voice Handicap Index and Reflux Symptom Index.",
                "Participant reported instruments answer the person's own experience "
                "and are a separate truth class. They are not perceptual voice "
                "judgement and the two may not be pooled.",
            ],
        },
        access={
            "route": "open_direct_download",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "obtainable_without_contact",
        },
        licence={
            "stated": "Open Data Commons Attribution License v1.0",
            "spdx_id": "ODC-By-1.0",
            "commercial_use_permitted": True,
            "source_of_licence_string": "repository_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": ["PhysioNet content page for VOICED 1.0.0, read 2026-08-19."],
            "findings": [
                "A second openly licensed voice corpus with no perceptual rating "
                "attached, reinforcing that open audio is not the scarce thing.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_truth_class",
            "reasons": ["No perceptual reference, and participant report is a separate lane."],
        },
    ),
    _record(
        source_id="bridge2ai_voice",
        title="Bridge2AI-Voice",
        citation="Bridge2AI-Voice, PhysioNet, version 3.1.0.",
        canonical_source={
            "landing_page": "https://physionet.org/content/b2ai-voice/3.1.0/",
            "terms_or_licence_url": "https://physionet.org/content/b2ai-voice/3.1.0/",
        },
        language_and_variety={
            "language": "English",
            "variety": "North American English",
            "covers_australian_english": False,
        },
        population={
            "description": (
                "833 adults across five North American sites, spanning voice, "
                "neurological, mood and respiratory conditions."
            ),
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": [
                "The PhysioNet distribution carries derived acoustic features and "
                "phenotypic data; raw audio is held separately.",
            ],
        },
        tasks_present=[
            "sustained_vowel_e",
            "harvard_sentences",
            "random_item_generation",
            "stroop",
            "winograd",
        ],
        reference_truth={
            "offered_truth_class": "population_description_only",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": False,
            "adjudication_defined": False,
            "requirement_status": "fails",
            "failure_reasons": [
                "No rapid syllable task is present at all.",
                "No CAPE-V, GRBAS or other multi-rater perceptual judgement is "
                "included, and no listener transcription.",
                "Labels are clinical diagnoses and validated participant "
                "questionnaires, which are population description and participant "
                "report respectively.",
            ],
        },
        access={
            "route": "free_account_and_signed_agreement",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": True,
            "agreement_signature_required": True,
            "fee": None,
            "state": "restricted",
        },
        licence={
            "stated": "Bridge2AI Voice Registered Access License",
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "repository_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": ["PhysioNet content page for b2ai-voice 3.1.0, read 2026-08-19."],
            "findings": [
                "Credentialed access plus a signed data use agreement, and the "
                "licence does not state whether commercial use is permitted.",
                "The largest and newest adult voice collection found still supplies "
                "neither of the two truth classes item 23 needs.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_truth_class",
            "reasons": [
                "No rapid syllable task and no multi-rater perceptual judgement.",
                "Commercial permission is unstated, so rights would also fail closed.",
            ],
        },
    ),
    _record(
        source_id="avfad",
        title="Advanced Voice Function Assessment Databases",
        citation="AVFAD, Universidade de Aveiro.",
        canonical_source={
            "landing_page": "https://acsa.web.ua.pt/AVFAD.htm",
            "terms_or_licence_url": None,
        },
        language_and_variety={
            "language": "Portuguese",
            "variety": "European Portuguese",
            "covers_australian_english": False,
        },
        population={
            "description": "709 participants, 346 with vocal pathology and 363 without, 8,648 audio files.",
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": ["European Portuguese."],
        },
        tasks_present=["sustained_vowel", "cape_v_style_sentences", "reading", "spontaneous_speech"],
        reference_truth={
            "offered_truth_class": "unresolved",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "unresolved",
            "failure_reasons": [
                "Whether per rater perceptual scores are distributed with the "
                "database was not established from the project page.",
            ],
        },
        access={
            "route": "email_request_to_authors",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "obtainable_only_after_contact_or_agreement",
        },
        licence={
            "stated": None,
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "reported_not_verified",
            "inspected_materials": [
                "Reported from a discovery sweep on 2026-08-19 and not confirmed "
                "at source by this survey.",
            ],
            "findings": [
                "Recorded so that it is not rediscovered as a fresh lead. Its "
                "licence, rater structure and access terms all remain unchecked.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_licence_unresolved",
            "reasons": [
                "No stated licence and an email route that this project is not "
                "authorised to use.",
            ],
        },
    ),
    _record(
        source_id="aprocsa",
        title="APROCSA, auditory-perceptual rating of connected speech in aphasia",
        citation="APROCSA dataset, Language Neuroscience Laboratory, doi:10.21415/KT40-EA41.",
        canonical_source={
            "landing_page": "https://langneurosci.org/aprocsa-dataset",
            "terms_or_licence_url": "https://langneurosci.org/aprocsa-dataset",
        },
        language_and_variety={
            "language": "English",
            "variety": "United States English",
            "covers_australian_english": False,
        },
        population={
            "description": "Six speakers with chronic post-stroke aphasia, aged 46 to 72, rated on 27 features.",
            "age_band": "adults",
            "clinical_status": "clinical",
            "limitations": [
                "Six speakers cannot support any population claim.",
                "Aphasia is a language construct, and item 23 must not let a language "
                "measure stand in for a motor speech or voice one.",
            ],
        },
        tasks_present=["connected_speech"],
        reference_truth={
            "offered_truth_class": "perceptual_voice_consensus_only",
            "independent_rater_or_annotator_count": 5,
            "individual_records_retained": False,
            "adjudication_defined": None,
            "requirement_status": "fails",
            "failure_reasons": [
                "Five raters rated independently but the released ratings are "
                "consensus values, so the individual ratings and the disagreement "
                "between them are not available.",
                "Item 23 states that raw disagreement is data and must never be "
                "silently replaced by a consensus label.",
            ],
        },
        access={
            "route": "open_direct_download",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "obtainable_without_contact",
        },
        licence={
            "stated": (
                "Access to these materials is unrestricted, however permission is "
                "granted only for research, education, and clinical uses"
            ),
            "spdx_id": None,
            "commercial_use_permitted": False,
            "source_of_licence_string": "publication_text",
        },
        capability_audit={
            "verification_level": "reported_not_verified",
            "inspected_materials": [
                "Reported from a discovery sweep on 2026-08-19 and not confirmed "
                "at source by this survey.",
            ],
            "findings": [
                "The quoted permission covers research, education and clinical use "
                "and does not extend to a commercial product backend.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_licence_non_commercial",
            "reasons": [
                "Permission is limited to research, education and clinical use.",
                "Consensus ratings destroy the disagreement item 23 requires.",
            ],
        },
    ),
]


# ---------------------------------------------------------------------------
# Lane C: intelligibility judged by several unfamiliar listeners
#
# The item 23 requirement is the intended prompt, an independently adjudicated
# actual production, and several blinded unfamiliar listeners making
# orthographic transcriptions under fixed conditions, retained per listener.
# ---------------------------------------------------------------------------

INTELLIGIBILITY_SOURCES = [
    _record(
        source_id="speech_accessibility_project",
        title="Speech Accessibility Project",
        citation="Speech Accessibility Project, Beckman Institute, University of Illinois.",
        canonical_source={
            "landing_page": "https://speechaccessibilityproject.beckman.illinois.edu/",
            "terms_or_licence_url": (
                "https://speechaccessibilityproject.beckman.illinois.edu/"
                "conduct-research-through-the-project"
            ),
        },
        language_and_variety={
            "language": "English",
            "variety": "North American English",
            "covers_australian_english": False,
        },
        population={
            "description": (
                "About 999 participants and 1,500 hours of recorded speech across "
                "amyotrophic lateral sclerosis, cerebral palsy, Down syndrome, "
                "Parkinson's disease and stroke."
            ),
            "age_band": "adults",
            "clinical_status": "clinical",
            "limitations": [
                "North American English only.",
                "A clinical population, so it cannot describe the general adult "
                "population an undefined intended use would reach.",
            ],
        },
        tasks_present=["prompted_speech", "spontaneous_speech"],
        reference_truth={
            "offered_truth_class": "unresolved",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "unresolved",
            "failure_reasons": [
                "All samples are manually transcribed, and a subset carries "
                "certified clinician ratings on seven point scales for "
                "intelligibility and several speech dimensions.",
                "Clinician scale ratings are not unfamiliar listener orthographic "
                "transcription, which is what item 23 names as intelligibility "
                "truth. Whether any listener level transcription exists cannot be "
                "checked without access.",
            ],
        },
        access={
            "route": "signed_agreement_with_organisation_signatory",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": True,
            "account_required": False,
            "agreement_signature_required": True,
            "fee": None,
            "state": "obtainable_only_after_contact_or_agreement",
        },
        licence={
            "stated": "University of Illinois data use agreement, terms not published on the page",
            "spdx_id": None,
            "commercial_use_permitted": True,
            "source_of_licence_string": "project_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "The project's research access page, read 2026-08-19, returning "
                "HTTP 200.",
            ],
            "findings": [
                "The data use agreement requires two signatures: the data user and "
                "an authorised representative of the user's organisation. A "
                "one page proposal must also be submitted and approved.",
                "This is the clearest concrete instance of the missing legal entity "
                "blocking a route. The commercial permission is not the obstacle; "
                "the organisational signature is.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_access_requires_organisation",
            "reasons": [
                "The agreement cannot be executed without an organisation to "
                "countersign it, and no legal owner or sponsor exists.",
                "Even with one, the proposal review is a discretionary decision by "
                "a third party and cannot be assumed.",
            ],
        },
    ),
    _record(
        source_id="ua_speech",
        title="UA-Speech, Universal Access dysarthric speech corpus",
        citation="Kim, H. et al. Dysarthric speech database for universal access research. Interspeech 2008.",
        canonical_source={
            "landing_page": "http://www.isle.illinois.edu/sst/data/UASpeech/",
            "terms_or_licence_url": None,
        },
        language_and_variety={
            "language": "English",
            "variety": "United States English",
            "covers_australian_english": False,
        },
        population={
            "description": "About 29 speakers: 15 to 16 with cerebral palsy and 13 controls, aged 19 to 58.",
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": [
                "Isolated word material, so it cannot answer connected speech "
                "questions.",
            ],
        },
        tasks_present=["isolated_word_reading"],
        reference_truth={
            "offered_truth_class": "intelligibility_multi_listener_transcription",
            "independent_rater_or_annotator_count": 5,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "unresolved",
            "failure_reasons": [
                "Five naive listeners produced orthographic transcriptions per word, "
                "which is the right shape of evidence.",
                "The published per speaker figure is an average across those five "
                "listeners, and whether per listener transcriptions are distributed "
                "could not be established.",
                "The host did not accept a connection, so nothing about the "
                "distribution could be checked at source.",
            ],
        },
        access={
            "route": "host_unreachable",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": True,
            "fee": None,
            "state": "unobtainable",
        },
        licence={
            "stated": (
                "reported as available to government and academic research "
                "laboratories with no commercial use and no redistribution"
            ),
            "spdx_id": None,
            "commercial_use_permitted": False,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "DNS and HTTP checks on 2026-08-19.",
            ],
            "findings": [
                "isle.illinois.edu and www.isle.illinois.edu both resolve to "
                "130.126.122.239, but connections to the host failed and curl "
                "returned no HTTP status on 2026-08-19.",
                "This is a different failure from AusTalk, which does not resolve at "
                "all. The name still exists; the service did not answer.",
                "Because the terms could not be read at source, the licence string "
                "here is recorded as reported and drives no decision.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_host_unreachable",
            "reasons": [
                "The distribution host did not answer, so there is no route to check "
                "or accept terms.",
                "Every reported description of the terms excludes commercial use, so "
                "a working host would not resolve the rights question either.",
            ],
        },
    ),
    _record(
        source_id="torgo",
        title="TORGO database of dysarthric articulation",
        citation=(
            "Rudzicz, F., Namasivayam, A. K. & Wolff, T. The TORGO database of "
            "acoustic and articulatory speech from speakers with dysarthria. "
            "Language Resources and Evaluation 46(4), 2012."
        ),
        canonical_source={
            "landing_page": "http://www.cs.toronto.edu/~complingweb/data/TORGO/torgo.html",
            "terms_or_licence_url": "http://www.cs.toronto.edu/~complingweb/data/TORGO/torgo.html",
        },
        language_and_variety={
            "language": "English",
            "variety": "Canadian English",
            "covers_australian_english": False,
        },
        population={
            "description": "15 speakers: 8 with cerebral palsy or amyotrophic lateral sclerosis and 7 controls, about 23 hours.",
            "age_band": "mixed",
            "clinical_status": "mixed",
            "limitations": [
                "15 speakers in total.",
                "Collected primarily to improve speech recognition, not to measure "
                "speech.",
            ],
        },
        tasks_present=["isolated_words", "sentences", "articulatory_measurement"],
        reference_truth={
            "offered_truth_class": "audio_without_qualifying_labels",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": False,
            "adjudication_defined": False,
            "requirement_status": "fails",
            "failure_reasons": [
                "Annotation is phonemic and orthographic transcription plus a "
                "clinician administered dysarthria assessment. There is no multi "
                "listener intelligibility transcription.",
                "A single clinician's assessment instrument is not listener "
                "intelligibility truth.",
            ],
        },
        access={
            "route": "open_direct_download",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "obtainable_without_contact",
        },
        licence={
            "stated": "Use of this database is free for academic (non-profit) purposes.",
            "spdx_id": None,
            "commercial_use_permitted": False,
            "source_of_licence_string": "project_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "The University of Toronto TORGO page, fetched and read 2026-08-19, "
                "returning HTTP 200.",
            ],
            "findings": [
                "The licence sentence is unambiguous and quoted verbatim above. It "
                "restricts use to academic non-profit purposes.",
                "The data is a free 18 GB download, which makes it a standing "
                "temptation. The licence, not the availability, is what excludes it.",
            ],
            "conflicting_claims": [
                "The Linguistic Data Consortium lists the same corpus under a "
                "separate paid member agreement. The two routes carry different "
                "terms and the Toronto page is treated as authoritative for the free "
                "download it offers.",
            ],
        },
        eligibility={
            "decision": "blocked_licence_non_commercial",
            "reasons": [
                "Academic non-profit use only excludes this repository, which is the "
                "measurement backend of a future commercial product.",
            ],
        },
    ),
]

INTELLIGIBILITY_SOURCES += [
    _record(
        source_id="talkbank_phonbank_clinical",
        title="TalkBank and PhonBank clinical corpora, including PERCEPT-R",
        citation="TalkBank and PhonBank, Carnegie Mellon University; PERCEPT-R doi:10.21415/0JPJ-X403.",
        canonical_source={
            "landing_page": "https://talkbank.org/phon/access/Clinical/PERCEPT-R.html",
            "terms_or_licence_url": "https://talkbank.org/0share/rules.html",
        },
        language_and_variety={
            "language": "English",
            "variety": "United States English",
            "covers_australian_english": False,
        },
        population={
            "description": (
                "PERCEPT-R holds 280 participants aged 6 to 17 plus a few adults, "
                "with typical speech and with residual speech sound disorder."
            ),
            "age_band": "children",
            "clinical_status": "mixed",
            "limitations": [
                "Predominantly children, which is outside the approved adults first "
                "research scope.",
                "Segment level accuracy judgement of one sound, not whole utterance "
                "intelligibility.",
            ],
        },
        tasks_present=["single_word", "sentence"],
        reference_truth={
            "offered_truth_class": "intelligibility_multi_listener_transcription",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "fails",
            "failure_reasons": [
                "It carries per listener judgements from both untrained crowd "
                "listeners and trained lab listeners, which is a genuinely rare "
                "shape, but the judgement is segment accuracy rather than "
                "orthographic transcription of what was understood.",
                "The population is children, so it cannot enter the adults first "
                "scope at all.",
            ],
        },
        access={
            "route": "application_and_review",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": False,
            "account_required": True,
            "agreement_signature_required": False,
            "fee": None,
            "state": "restricted",
        },
        licence={
            "stated": "Creative Commons CC BY-NC-SA 3.0",
            "spdx_id": "CC-BY-NC-SA-3.0",
            "commercial_use_permitted": False,
            "source_of_licence_string": "project_page",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "TalkBank data usage rules, read 2026-08-19.",
                "The existing item 22 manifest talkbank-blocked.json, which recorded "
                "this family as restricted on 2026-07-21.",
            ],
            "findings": [
                "The stated licence precludes incorporating the data into commercial "
                "products, and explicitly names large language models as an example "
                "of what may not include it.",
                "Password access to clinical corpora is granted only to full time "
                "faculty or clinicians holding ASHA speech language pathology "
                "certification. Neither applies here.",
                "This confirms and sharpens item 22's earlier blocked decision with "
                "the exact reason.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_licence_non_commercial",
            "reasons": [
                "Non commercial share alike terms exclude a commercial product "
                "backend.",
                "Clinical corpus access additionally requires professional "
                "certification or faculty status that this project does not have.",
                "The population is children and therefore outside scope regardless.",
            ],
        },
    ),
    _record(
        source_id="osf_slp_intelligibility_estimations",
        title="Reliability and validity of speech language pathologists' estimations of intelligibility in dysarthria",
        citation="Open Science Framework project sr9aw.",
        canonical_source={
            "landing_page": "https://osf.io/sr9aw/",
            "terms_or_licence_url": "https://osf.io/sr9aw/",
        },
        language_and_variety={
            "language": "English",
            "variety": "United States English",
            "covers_australian_english": False,
        },
        population={
            "description": (
                "20 speakers with dysarthria, 70 naive listeners producing "
                "orthographic transcriptions, and 21 speech language pathologists "
                "producing visual analogue and percent estimates."
            ),
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": [
                "Assembled to study clinician estimation rather than to be reused as "
                "a reference corpus.",
            ],
        },
        tasks_present=["read_sentences"],
        reference_truth={
            "offered_truth_class": "intelligibility_multi_listener_transcription",
            "independent_rater_or_annotator_count": 70,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "unresolved",
            "failure_reasons": [
                "Seventy unfamiliar listeners producing orthographic transcriptions "
                "is exactly the evidence shape item 23 names for intelligibility.",
                "The project carries no licence at all, so no reuse permission "
                "exists to rely on and the rights question fails closed.",
                "Whether the speaker audio itself is included could not be "
                "established without opening the project files.",
            ],
        },
        access={
            "route": "open_direct_download",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "obtainable_without_contact",
        },
        licence={
            "stated": None,
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "The Open Science Framework API node record for sr9aw, queried "
                "2026-08-19.",
            ],
            "findings": [
                "The project is public but the API returns no licence relationship "
                "and a null node licence, so nothing has been granted.",
                "Public visibility is not a licence. Absent a grant, default "
                "copyright applies and this fails closed on rights.",
                "This is the closest openly visible match for the intelligibility "
                "truth class, which makes its missing licence worth recording "
                "precisely rather than glossing.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_licence_unresolved",
            "reasons": [
                "No licence is assigned, so there is no permission to rely on.",
            ],
        },
    ),
    _record(
        source_id="clarity_prediction_challenge",
        title="Clarity Prediction Challenge data, CPC1 and CPC2",
        citation="Clarity Prediction Challenge, University of Sheffield and partners.",
        canonical_source={
            "landing_page": "https://claritychallenge.org/docs/cpc2/cpc2_data",
            "terms_or_licence_url": "https://claritychallenge.org/docs/cpc2/cpc2_data",
        },
        language_and_variety={
            "language": "English",
            "variety": "British English",
            "covers_australian_english": False,
        },
        population={
            "description": (
                "25 listeners with documented hearing loss per challenge, with "
                "audiograms, listening to processed speech from a small number of "
                "talkers."
            ),
            "age_band": "adults",
            "clinical_status": "listeners",
            "limitations": [
                "The listeners are hearing impaired and the speech is processed by "
                "hearing aid algorithms.",
            ],
        },
        tasks_present=["sentence_listening_in_noise"],
        reference_truth={
            "offered_truth_class": "intelligibility_multi_listener_transcription",
            "independent_rater_or_annotator_count": 25,
            "individual_records_retained": True,
            "adjudication_defined": None,
            "requirement_status": "fails",
            "failure_reasons": [
                "Per listener response transcriptions and word level correctness are "
                "retained, which is the shape item 23 wants.",
                "The construct is wrong. It measures how well a hearing aid "
                "algorithm renders speech to a hearing impaired listener, not how "
                "intelligible a speaker is to unfamiliar listeners.",
                "Using it as speaker intelligibility evidence would attribute the "
                "listener's hearing loss and the processing chain to the talker.",
                "No licence is stated on the data pages, so rights also fail closed.",
            ],
        },
        access={
            "route": "open_direct_download",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "obtainable_without_contact",
        },
        licence={
            "stated": None,
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": ["The CPC2 data documentation page, read 2026-08-19."],
            "findings": [
                "No explicit licence appears on the data page.",
                "Recorded mainly as a worked example of why matching the evidence "
                "shape is not enough: the same file structure can answer a "
                "completely different question.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_truth_class",
            "reasons": [
                "It measures a listening and processing condition rather than a "
                "talker property.",
                "No licence is stated.",
            ],
        },
    ),
    _record(
        source_id="nki_ccrt",
        title="NKI-CCRT corpus",
        citation="Clapham, R. et al. NKI-CCRT corpus, speech intelligibility before and after advanced head and neck cancer treatment. LREC 2012.",
        canonical_source={
            "landing_page": "https://aclanthology.org/L12-1084/",
            "terms_or_licence_url": None,
        },
        language_and_variety={
            "language": "Dutch",
            "variety": None,
            "covers_australian_english": False,
        },
        population={
            "description": "55 speakers treated for head and neck cancer, recorded at three evaluation moments.",
            "age_band": "adults",
            "clinical_status": "clinical",
            "limitations": ["Dutch, and a specific treatment population."],
        },
        tasks_present=["read_speech"],
        reference_truth={
            "offered_truth_class": "intelligibility_multi_listener_transcription",
            "independent_rater_or_annotator_count": 13,
            "individual_records_retained": True,
            "adjudication_defined": None,
            "requirement_status": "unresolved",
            "failure_reasons": [
                "Thirteen recently graduated speech pathologists judged the material "
                "with individual judgements retained, which is a strong shape.",
                "The listeners are clinically trained rather than unfamiliar "
                "everyday listeners, which is a different question.",
                "Access terms and licence were not confirmed at source.",
            ],
        },
        access={
            "route": "application_and_review",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": False,
            "account_required": True,
            "agreement_signature_required": True,
            "fee": None,
            "state": "restricted",
        },
        licence={
            "stated": "reported as restricted scientific use",
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "reported_not_verified",
            "inspected_materials": [
                "Reported from a discovery sweep on 2026-08-19 and not confirmed "
                "at source by this survey.",
            ],
            "findings": [
                "Recorded so the lead is not rediscovered. Rights and access remain "
                "unchecked and drive no decision.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_licence_unresolved",
            "reasons": [
                "Reported restricted scientific use, unconfirmed, and Dutch.",
            ],
        },
    ),
]


# ---------------------------------------------------------------------------
# Australian English
#
# The intended research population is Australian adults.  These records exist
# so that nobody spends a second week rediscovering that the Australian option
# is not available.
# ---------------------------------------------------------------------------

AUSTRALIAN_SOURCES = [
    _record(
        source_id="austalk_alveo",
        title="AusTalk, the Big Australian Speech Corpus, and the Alveo Virtual Laboratory",
        citation="Burnham, D. et al. AusTalk: an audio-visual corpus of Australian English. LREC 2014.",
        canonical_source={
            "landing_page": "https://bigasc.edu.au/",
            "terms_or_licence_url": None,
        },
        language_and_variety={
            "language": "English",
            "variety": "Australian English",
            "covers_australian_english": True,
        },
        population={
            "description": "About one thousand speakers of Australian English across scripted, spontaneous and dialogue tasks.",
            "age_band": "adults",
            "clinical_status": "healthy",
            "limitations": [
                "No access route exists, so what it contains cannot be inspected.",
                "Audio visual recordings of identifiable participants would need "
                "their own privacy review if a route ever reopened.",
            ],
        },
        tasks_present=["scripted_speech", "spontaneous_speech", "dialogue"],
        reference_truth={
            "offered_truth_class": "unresolved",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "unresolved",
            "failure_reasons": [
                "Unreachable, so its annotation content fails closed.",
                "No published description suggests rapid syllable, perceptual voice "
                "or multi listener intelligibility material in any case.",
            ],
        },
        access={
            "route": "host_unreachable",
            "contact_with_a_person_required": False,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": False,
            "fee": None,
            "state": "unobtainable",
        },
        licence={
            "stated": None,
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "verified_directly",
            "inspected_materials": [
                "DNS and HTTP checks on alveo.edu.au, app.alveo.edu.au, "
                "austalk.edu.au and bigasc.edu.au, run 2026-08-19.",
            ],
            "findings": [
                "All four names still fail to resolve and all HTTP attempts returned "
                "no status, which reproduces exactly what item 22 recorded on "
                "2026-07-29.",
                "A discovery sweep during this checkpoint reported these hosts as "
                "live with working corpus and licence pages. That report was wrong "
                "and was rejected after direct checking. It is recorded here because "
                "an unverified availability claim about the one Australian corpus "
                "this project would most want is exactly the kind of error that "
                "wastes weeks.",
            ],
            "conflicting_claims": [
                "A discovery sweep on 2026-08-19 reported bigasc.edu.au and "
                "alveo.edu.au as accessible. Direct DNS and HTTP checks on the same "
                "date contradict that, and the direct checks are authoritative.",
            ],
        },
        eligibility={
            "decision": "blocked_host_unreachable",
            "reasons": [
                "Unobtainable, confirming the item 22 finding rather than reopening it.",
            ],
        },
    ),
    _record(
        source_id="auskidtalk",
        title="AusKidTalk, Australian children's speech corpus",
        citation="AusKidTalk, Macquarie University and partners.",
        canonical_source={
            "landing_page": "https://researchers.mq.edu.au/en/projects/auskidtalk-an-australian-childrens-speech-corpus/",
            "terms_or_licence_url": None,
        },
        language_and_variety={
            "language": "English",
            "variety": "Australian English",
            "covers_australian_english": True,
        },
        population={
            "description": "Australian children aged roughly 3 to 12, with orthographic transcription.",
            "age_band": "children",
            "clinical_status": "mixed",
            "limitations": [
                "Children only.",
                "Adam approved an adults first scope on 2026-08-14, and adult and "
                "child evidence must never be pooled.",
            ],
        },
        tasks_present=["elicited_speech"],
        reference_truth={
            "offered_truth_class": "audio_without_qualifying_labels",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "fails",
            "failure_reasons": [
                "Transcription only. No rapid syllable, perceptual voice or multi "
                "listener intelligibility reference is described.",
                "Children are outside the approved research scope, so it cannot be "
                "used whatever it contains.",
            ],
        },
        access={
            "route": "application_and_review",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": False,
            "account_required": True,
            "agreement_signature_required": True,
            "fee": None,
            "state": "restricted",
        },
        licence={
            "stated": None,
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "reported_not_verified",
            "inspected_materials": [
                "Reported from a discovery sweep on 2026-08-19 and not confirmed "
                "at source by this survey.",
            ],
            "findings": [
                "Recorded to close the Australian question rather than to open a "
                "lead. It is out of scope on population alone, so its access terms "
                "were not pursued.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "out_of_scope_population",
            "reasons": [
                "Children only, against an approved adults first research scope.",
            ],
        },
    ),
]


MOTOR_SOURCES += [
    _record(
        source_id="pc_gita",
        title="PC-GITA, Spanish speech corpus for Parkinson's disease analysis",
        citation=(
            "Orozco-Arroyave, J. R. et al. New Spanish speech corpus database for "
            "the analysis of people suffering from Parkinson's disease. LREC 2014."
        ),
        canonical_source={
            "landing_page": "https://www.researchgate.net/publication/265592171",
            "terms_or_licence_url": None,
        },
        language_and_variety={
            "language": "Spanish",
            "variety": "Colombian Spanish",
            "covers_australian_english": False,
        },
        population={
            "description": (
                "Reported as 100 native Colombian Spanish speakers, 50 with "
                "Parkinson's disease and 50 healthy controls."
            ),
            "age_band": "adults",
            "clinical_status": "mixed",
            "limitations": [
                "Spanish, and a single clinical condition.",
                "No canonical repository landing page was located, so every figure "
                "here rests on published description rather than on a data record.",
            ],
        },
        tasks_present=[
            "sustained_vowel",
            "isolated_words",
            "diadochokinesis_pa_ta_ka",
            "read_sentences",
            "read_text",
            "monologue",
        ],
        reference_truth={
            "offered_truth_class": "population_description_only",
            "independent_rater_or_annotator_count": None,
            "individual_records_retained": None,
            "adjudication_defined": None,
            "requirement_status": "fails",
            "failure_reasons": [
                "Reported labels are neurologist diagnosis and MDS-UPDRS-III "
                "assessment, which is population description rather than rapid "
                "syllable reference truth.",
                "No manual syllable boundary, count or task error marking is "
                "described in any material located.",
            ],
        },
        access={
            "route": "email_request_to_authors",
            "contact_with_a_person_required": True,
            "organisation_signatory_required": False,
            "account_required": False,
            "agreement_signature_required": True,
            "fee": None,
            "state": "obtainable_only_after_contact_or_agreement",
        },
        licence={
            "stated": None,
            "spdx_id": None,
            "commercial_use_permitted": None,
            "source_of_licence_string": "not_stated",
        },
        capability_audit={
            "verification_level": "reported_not_verified",
            "inspected_materials": [
                "Reported from a discovery sweep and secondary literature on "
                "2026-08-19 and not confirmed at source by this survey.",
            ],
            "findings": [
                "It is widely used in the automatic rapid syllable literature, which "
                "is why it is recorded rather than omitted.",
                "No repository page, licence or access page was located, so both "
                "rights and content remain unchecked and drive no conclusion.",
            ],
            "conflicting_claims": [],
        },
        eligibility={
            "decision": "blocked_licence_unresolved",
            "reasons": [
                "No stated licence and an author request route this project is not "
                "authorised to use.",
            ],
        },
    ),
]


ALL_SOURCES = (
    MOTOR_SOURCES + VOICE_SOURCES + INTELLIGIBILITY_SOURCES + AUSTRALIAN_SOURCES
)


LANE_CONCLUSIONS = {
    "motor_task_timing_and_accuracy": {
        "question": (
            "Is there a public source in which trained humans marked rapid syllable "
            "cycles, boundaries or task errors, so that a computed timing value has "
            "something independent to be graded against?"
        ),
        "answer": "no_qualifying_source_located",
        "conclusion": (
            "Public rapid syllable recordings exist in quantity, and none of them "
            "carries rapid syllable reference truth. The large collections carry "
            "diagnosis and clinical rating scale labels, which describe a study "
            "population and are a different truth class. The one located set that "
            "does carry two independent annotators marking voice onset times and "
            "vowel boundaries on neurotypical adults has no public release. This is "
            "a property of what has been published, not a licence problem and not a "
            "gap in searching: the same conclusion holds at every licence and at "
            "every price, including sources that require an application this project "
            "cannot make."
        ),
        "consequences": [
            "No licence decision, account, agreement or payment would obtain this "
            "truth class.",
            "Collecting it would mean recruiting participants and paying trained "
            "annotators, which is precisely the participant work that checkpoint 23B "
            "cannot authorise without professional governance and ethics review.",
            "Any future motor timing claim therefore depends on prospective data "
            "collection, and no shortcut through public data exists.",
        ],
    },
    "perceptual_voice": {
        "question": (
            "Is there a public source in which several qualified raters judged voice "
            "under a standardised protocol, with the individual ratings kept?"
        ),
        "answer": "one_candidate_source_with_unresolved_and_measured_limits",
        "conclusion": (
            "Exactly one located source plausibly reaches the multiple qualified "
            "rater requirement under a licence that permits commercial use and needs "
            "no contact, account or agreement: the Perceptual Voice Qualities "
            "Database, under CC BY 4.0. Two things stop that being good news. "
            "Whether it distributes individual rater rows or only combined values is "
            "unresolved and cannot be settled without opening the file. And an "
            "independent re-rating measured how far trained clinicians actually "
            "agree, which fixes a ceiling on anything built against it: good "
            "agreement for overall severity, moderate for roughness, breathiness and "
            "strain, and poor for pitch and loudness. Every other perceptual source "
            "located fails on rater multiplicity, on consensus collapsing the "
            "disagreement, on a non commercial licence, or on restricted access."
        ),
        "consequences": [
            "Pitch and loudness have no reliable human reference in the one available "
            "source, so no candidate measure may be graded against them, and the "
            "existing item 20 pitch primitive gains no reference by this route.",
            "On the most reliable feature two trained raters typically differ by "
            "12 to 15 points on a 100 point scale, so no future claim of finer "
            "resolution than that can be supported.",
            "The material is United States English, which repeats the imported "
            "reference problem item 22 measured, and there is no Australian "
            "equivalent.",
            "Whether this source is acceptable at all is a decision for independent "
            "voice governance, not for this survey.",
        ],
    },
    "intelligibility": {
        "question": (
            "Is there a public source in which several unfamiliar listeners wrote "
            "down what they understood, retained per listener, under a declared "
            "listening condition?"
        ),
        "answer": "no_lawfully_usable_source_located",
        "conclusion": (
            "Sources of the right shape exist and none of them is usable here. The "
            "largest carries commercial permission but requires a data use agreement "
            "countersigned by an authorised representative of an organisation, which "
            "this project does not have. Others are limited to academic non-profit "
            "use, or to research, education and clinical use, or require professional "
            "certification, or are restricted, or carry no licence at all. One "
            "openly visible set of seventy unfamiliar listener transcriptions has no "
            "licence assigned, so nothing has been granted. One set with per listener "
            "transcriptions measures hearing aid processing for hearing impaired "
            "listeners, which is a different construct wearing the same file shape."
        ),
        "consequences": [
            "The missing legal entity is not an abstract governance concern. It is "
            "the concrete reason the single most relevant modern corpus cannot be "
            "requested.",
            "An openly visible dataset without a licence grants nothing, and public "
            "visibility must never be read as permission.",
        ],
    },
    "australian_english": {
        "question": "Is there any Australian English source carrying any of the three truth classes?",
        "answer": "none_located",
        "conclusion": (
            "No Australian English source carrying motor task, perceptual voice or "
            "multi listener intelligibility reference evidence was located. The "
            "adult Australian corpus this project would most want remains "
            "unreachable, which direct checks on 2026-08-19 confirmed rather than "
            "changed. The one large Australian corpus that is active covers children "
            "and is outside the approved adults first scope."
        ),
        "consequences": [
            "Any Australian variety question in item 23 depends on prospective "
            "collection, exactly as the motor timing question does.",
            "An international source cannot answer an Australian variety question, "
            "and item 22 already demonstrated the cost of assuming otherwise.",
        ],
    },
}


CROSS_SOURCE_RULES = {
    "truth_classes_may_be_pooled": False,
    "diagnosis_is_numeric_ground_truth": False,
    "consensus_may_replace_retained_disagreement": False,
    "public_visibility_implies_a_licence": False,
    "single_rater_may_substitute_for_multiple_raters": False,
    "agreement_between_two_systems_is_evidence": False,
    "a_source_may_be_recorded_as_meeting_a_truth_requirement": False,
    "acquisition_authorised_by_this_survey": False,
}


def build_registry(records):
    """Summarise the survey without letting the summary become a decision."""
    obtainable_without_contact = sorted(
        record["source_id"]
        for record in records
        if record["access"]["state"] == "obtainable_without_contact"
    )
    commercially_permitted = sorted(
        record["source_id"]
        for record in records
        if record["licence"]["commercial_use_permitted"] is True
    )
    return {
        "schema_version": "1.0.0",
        "registry_id": "motor_speech_voice_source_survey_v1",
        "checkpoint": "23B",
        "status": "evidence_survey_complete_no_source_selected",
        "record_schema": SCHEMA_FILENAME,
        "surveyed_at": CHECKED_AT,
        "raw_data_root": ".research_data/motor_speech_voice/23b/",
        "raw_data_committed": False,
        "acquisition_authorised": False,
        "purpose": (
            "Record which publicly identifiable sources could supply the independent "
            "human reference evidence item 23 requires, what they may lawfully be "
            "used for, and whether they can be obtained at all. This survey selects "
            "no source, authorises no acquisition, and decides no truth requirement."
        ),
        "record_count": len(records),
        "records": [
            {"source_id": record["source_id"], "path": f"{record['source_id']}.json"}
            for record in records
        ],
        "counts": {
            "obtainable_without_any_contact_account_or_agreement": len(
                obtainable_without_contact
            ),
            "licence_permits_commercial_use": len(commercially_permitted),
            "recorded_as_meeting_an_item_23_truth_requirement": 0,
            "selected": 0,
        },
        "obtainable_without_contact": obtainable_without_contact,
        "commercial_use_permitted": commercially_permitted,
        "lane_conclusions": LANE_CONCLUSIONS,
        "cross_source_rules": CROSS_SOURCE_RULES,
        "limitations": [
            "A survey of what has been published is not a survey of what exists. A "
            "source that is unlisted, unindexed or described only in a language not "
            "searched here would be missed.",
            "Records marked reported_not_verified were not confirmed at source and "
            "drive no conclusion. They exist so the lead is not rediscovered.",
            "Availability and licence statements change. Every record carries the "
            "date it was checked, and a stale record must be rechecked rather than "
            "trusted.",
            "Nothing here establishes that a source is scientifically suitable, "
            "ethically reusable or acceptable to independent governance. It "
            "establishes only what could be obtained and under what terms.",
        ],
    }


def write_survey():
    SURVEY_ROOT.mkdir(parents=True, exist_ok=True)
    for record in ALL_SOURCES:
        path = SURVEY_ROOT / f"{record['source_id']}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    registry_path = SURVEY_ROOT / REGISTRY_FILENAME
    registry_path.write_text(
        json.dumps(build_registry(ALL_SOURCES), indent=2, ensure_ascii=False) + "\n"
    )
    return len(ALL_SOURCES)


def main():
    written = write_survey()
    print(f"Wrote {written} source survey records and the registry.")
    print("No source is selected and no acquisition is authorised.")


if __name__ == "__main__":
    main()
