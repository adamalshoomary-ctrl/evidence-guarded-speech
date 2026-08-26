"""Build the checkpoint 23B measurement and sampling input package.

Checkpoint 23B requires a "prospective acquisition, sample-size, representation,
split and statistical plan".  Public research cannot produce that plan, because
a plan needs an independent statistician, a selected construct and pilot
variance, and item 23 has none of them.  What public research can produce is the
set of INPUTS that statistician would have to be given, written down once per
provisional construct so that the question is ready the day a real one exists.

This module writes that package.  It selects nothing.  Each record names the
construct's narrowest defensible observation exactly as the checkpoint 23A
register states it, the truth class that would have to establish it, what the
checkpoint 23B source survey found about obtaining that truth in public, the
variation a design would have to separate, the inputs only a statistician can
supply, the reporting standards that would govern the result, and what blocks
the question today.

Two structural rules make the artifact hard to misread later.

A record may contain no JSON number at all.  Every legitimate quantity here
lives inside a citation or a formula written as text, so a bare number would be
a computed result, and this package holds no results.  The validator refuses
one.

``sample_size.computed_value`` is typed ``null`` in the schema, so no sample
size can be written into a record even by accident.  The plan already says that
"thirty" or "one hundred" is not a scientific plan; this makes that structural
rather than aspirational.

Rebuild with::

    python3 -m motor_speech_voice.build_measurement_plan
"""

from __future__ import annotations

import json
from pathlib import Path


PLAN_ROOT = Path(__file__).resolve().parent / "measurement_plan"
SCHEMA_FILENAME = "measurement-plan-schema-v1.0.0.json"
REGISTRY_FILENAME = "measurement-plan-registry-v1.0.0.json"

PREPARED_AT = "2026-08-19"

# Inputs every construct needs, whatever its lane.  They are repeated into each
# record rather than referenced once, because a record that travels alone must
# still be complete.
UNIVERSAL_STATISTICIAN_INPUTS = [
    {
        "input": "The one primary estimand for the question, stated before any data "
        "exists, together with the secondary quantities that may be reported "
        "beside it.",
        "why_public_research_cannot_supply_it": "An estimand follows from an "
        "intended benefit and an intended claim. Checkpoint 23B has neither: the "
        "draft intended use records that it does not yet identify a sufficiently "
        "concrete benefit or eventual human action.",
    },
    {
        "input": "Expected between-person and within-person variance for the "
        "quantity, from a pilot run under the same task and capture path.",
        "why_public_research_cannot_supply_it": "No task is selected and no pilot "
        "has been run, so there is no variance to expect. Published variance from "
        "another protocol, population or capture path describes that study rather "
        "than this one.",
    },
    {
        "input": "The precision the study must reach, expressed as an acceptable "
        "confidence interval width for each reported quantity rather than as a "
        "target point estimate.",
        "why_public_research_cannot_supply_it": "Acceptable precision is a "
        "consequence of the claim being made and the harm of being wrong. Both "
        "belong to the accountable governance roles.",
    },
    {
        "input": "The number of candidate questions being carried, and how "
        "multiplicity across them will be handled.",
        "why_public_research_cannot_supply_it": "The construct register may be "
        "narrowed or rejected entirely by the governance group, so the count of "
        "questions is not yet fixed.",
    },
    {
        "input": "Expected withdrawal, partial task completion, unusable recordings "
        "and missing reference, as rates rather than as a contingency.",
        "why_public_research_cannot_supply_it": "These depend on the recruited "
        "population, the burden of the final protocol and the capture path, none "
        "of which exist.",
    },
    {
        "input": "Recruitment feasibility, participant burden and the cost of each "
        "additional participant, rater or listener.",
        "why_public_research_cannot_supply_it": "There is no sponsor, no budget "
        "ceiling and no recruitment route, so feasibility cannot be estimated.",
    },
]

# Every record carries these, because they are properties of the whole package
# rather than of one construct.
UNIVERSAL_BLOCKERS = [
    {
        "blocker": "No construct, task or measure is selected. Every lane in the "
        "checkpoint 23B governance contract remains unselected, and the register "
        "may be rejected in full.",
        "blocker_class": "no_task_or_construct_selected",
    },
    {
        "blocker": "No independent statistician is engaged, and the checkpoint "
        "requires the statistical plan to be prospectively received and reviewed "
        "by one.",
        "blocker_class": "statistician_absent",
    },
    {
        "blocker": "No pilot has been run, so no variance estimate exists to size "
        "anything against.",
        "blocker_class": "no_pilot_variance",
    },
    {
        "blocker": "The accountable professional and paid lived-experience "
        "governance roles are unfilled, and no external authority has been "
        "approached.",
        "blocker_class": "professional_governance_absent",
    },
    {
        "blocker": "There is no legal entity to sponsor collection, hold the data "
        "or sign an agreement, which the source survey already demonstrated as a "
        "concrete rather than formal obstacle.",
        "blocker_class": "no_legal_entity",
    },
    {
        "blocker": "No institution pathway or ethics review exists, and "
        "participant recording is prohibited until one does.",
        "blocker_class": "ethics_review_absent",
    },
]

UNIVERSAL_LEAKAGE_RISKS = [
    "A participant's sessions, attempts and recordings must move together. "
    "Splitting them puts the same person on both sides of a comparison and makes "
    "a memorised speaker look like a general result.",
    "Anything inspected during checkpoint 23C feasibility work is permanently "
    "pilot and development evidence for that participant and their related "
    "household, session and repeated recordings.",
    "Item 22 material is not reusable by default. Even development use needs a "
    "new lawful purpose, consent, rights and ethics decision, and an overlap "
    "register covering every repository source and participant.",
]

UNIVERSAL_SUBGROUPS = [
    "Australian English varieties the claim includes, including Aboriginal "
    "Englishes",
    "multilingual adults and adults who speak English as an additional language",
    "adults who cannot read the prompt, where a spoken alternative applies",
    "disability, communication difference and assisted communication",
    "gender-diverse voices and professional voice users",
    "regional and remote participants and their capture conditions",
    "device and capture-path strata the claim includes",
]


def _record(**fields):
    """Fill the shared shape around one construct."""
    fields.setdefault("schema_version", "1.0.0")
    fields["record_id"] = f"{fields['candidate_id']}_measurement_inputs_v1"
    fields["required_statistician_inputs"] = (
        list(fields.get("required_statistician_inputs", []))
        + [dict(item) for item in UNIVERSAL_STATISTICIAN_INPUTS]
    )
    fields["blockers"] = list(fields.get("blockers", [])) + [
        dict(item) for item in UNIVERSAL_BLOCKERS
    ]
    split = fields["split_and_clustering"]
    split["minimum_split_unit"] = "participant"
    split["leakage_risks"] = list(split.get("leakage_risks", [])) + list(
        UNIVERSAL_LEAKAGE_RISKS
    )
    fields["subgroup_and_representation"] = list(
        fields.get("subgroup_and_representation", [])
    ) + list(UNIVERSAL_SUBGROUPS)
    fields["missingness_and_abstention"]["reported_separately"] = True
    fields["agreement_and_reliability"]["measurement_error_required"] = True
    fields["estimand_shape"]["status"] = "candidate_shape_not_selected"
    fields["observation"]["claim_level"] = "measured_observation_candidate_not_selected"
    fields["sample_size"]["state"] = "not_computable_without_the_inputs_above"
    fields["sample_size"]["computed_value"] = None
    fields["selected"] = False
    return fields


# Published methods a statistician could choose between.  Citing a method is not
# choosing one, and none of these can be applied until the inputs above exist.
RELIABILITY_SAMPLE_SIZE_METHODS = [
    "Walter, S. D., Eliasziw, M. and Donner, A. Sample size and optimal designs "
    "for reliability studies. Statistics in Medicine, 1998, "
    "doi:10.1002/(SICI)1097-0258(19980115)17:1<101::AID-SIM727>3.0.CO;2-E. A "
    "hypothesis testing approach. Its inputs are the minimum acceptable "
    "intraclass correlation, the expected intraclass correlation, the "
    "significance level, the power, and the number of raters or repetitions per "
    "participant. Primary text not opened here; its inputs are reported from an "
    "open access implementation and its notation for the number of subjects and "
    "the number of replicates is the reverse of most modern restatements.",
    "Bonett, D. G. Sample size requirements for estimating intraclass "
    "correlations with desired precision. Statistics in Medicine, 2002, "
    "doi:10.1002/sim.1108. A precision approach. Its inputs are the expected "
    "intraclass correlation, the desired confidence interval width, the "
    "confidence level, and the number of raters or repetitions. Primary text not "
    "opened here.",
    "Zou, G. Y. Sample size formulas for estimating intraclass correlation "
    "coefficients with precision and assurance. Statistics in Medicine, 2012, "
    "doi:10.1002/sim.5466. Adds an assurance probability, because the width of a "
    "confidence interval is itself random and a precision calculation without "
    "assurance can miss its target about half the time. Primary text not opened "
    "here.",
    "Bland, J. M. Deciding the sample size for a study of agreement between two "
    "methods of measurement, at https://www-users.york.ac.uk/~mb55/meas/sizemeth.htm, "
    "read 2026-08-19. Sizes a study by the precision required on the limits of "
    "agreement themselves, expressed as a multiple of the standard deviation of "
    "the differences, so it does not require that standard deviation to be known "
    "in advance.",
]

LISTENER_SAMPLE_SIZE_METHODS = [
    "A generalisability theory decision study, which projects the reliability of "
    "a planned design by reweighting variance components measured in an earlier "
    "generalisability study, and so sizes the number of listeners and the number "
    "of items separately because each carries its own component. Lakes, K. D. and "
    "Hoyt, W. T. Applications of generalizability theory to clinical child and "
    "adolescent psychology research. Journal of Clinical Child and Adolescent "
    "Psychology, 2009, doi:10.1080/15374410802575461, open access and read at "
    "source. Brennan, R. L. Generalizability Theory, Springer 2001, is the "
    "standard reference text and was not opened here.",
    "Bonett, D. G. Sample size requirements for estimating intraclass "
    "correlations with desired precision. Statistics in Medicine, 2002, "
    "doi:10.1002/sim.1108, applied to the listener facet where an averaged "
    "listener panel is the reported unit. Primary text not opened here.",
]

MOTOR_TASK_CONSTRUCTS = [
    _record(
        candidate_id="rapid_syllable_timing",
        title="Rapid syllable timing",
        register_lane="motor_task",
        governance_lane="motor_speech",
        related_governance_lanes=["general_speech"],
        register_row={
            "candidate": "Rapid syllable timing",
            "narrowest_defensible_observation": "Rate, valid repetition count, "
            "inter-onset timing, within-run change and temporal regularity during "
            "one frozen task",
            "required_reference": "Two blinded trained annotators marking cycles "
            "and errors, with adjudication",
            "disposition_23a": "Priority for professional review; task remains "
            "locked",
        },
        observation={
            "what_would_be_measured": "How regularly and how quickly a person "
            "repeats a fixed syllable sequence during one frozen task, expressed "
            "as timing between syllable onsets rather than as a judgement about "
            "the person.",
            "why_it_is_not_yet_a_measure": [
                "The task is locked. Checkpoint 23A left a rapid syllable question "
                "open for independent professionals and people with lived "
                "experience to accept or reject, and it selected no prompt, no "
                "syllable sequence, no effort instruction and no trial count.",
                "Checkpoint 23A recorded that rapid syllable tasks are "
                "heterogeneous across the published literature, so a result "
                "obtained under one protocol does not transfer to another.",
                "A maximum performance task is a proxy for ordinary speech rather "
                "than a sample of it, and the strength of that proxy is itself "
                "unestablished here.",
            ],
        },
        reference_requirement={
            "truth_class": "timing_and_boundary_truth",
            "substitutions_refused": [
                "The candidate system's own segmentation cannot check the candidate "
                "system's own segmentation.",
                "A diagnosis attached to a recording describes the population it "
                "was drawn from and is not the numeric ground truth for a timing "
                "primitive.",
                "A clinical rating scale score is a different truth class and "
                "cannot be regressed onto syllable onsets.",
                "A published table of rate measures from another protocol has no "
                "recording to check an implementation against.",
            ],
            "public_availability": "no_qualifying_public_source",
            "source_survey_basis": [
                "ewa_db",
                "alois_db",
                "neurovoz",
                "voc_als",
                "pc_gita",
                "younger_nt_adults",
                "ondri_speech",
                "ddk_development_measures",
                "ddk_post_stroke_rate_measures",
            ],
            "consequence": "The source survey established that no public source "
            "supplies two blinded annotators marking cycles and errors on rapid "
            "syllable material, at any licence and at any price. Every input below "
            "therefore depends on prospective collection with recruited "
            "participants and paid trained annotators. There is no cheaper path "
            "and no partial one.",
        },
        estimand_shape={
            "question": "How much of the variation in a timing quantity is "
            "between people rather than within the same person across attempts and "
            "sessions, and how far two trained annotators marking the same "
            "recording differ from each other and from the algorithm.",
            "unit_of_analysis": "participant_by_attempt",
            "comparison": "Algorithm against adjudicated human annotation on the "
            "same recording, and the same person against themselves across "
            "repeated attempts and separate sessions.",
        },
        variance_components_to_separate=[
            "between_participant",
            "within_participant_between_session",
            "within_session_between_attempt",
            "between_rater",
            "rater_by_participant_interaction",
            "between_device",
            "between_room_or_environment",
            "practice_or_order_effect",
            "current_state_fatigue_or_voice_use",
            "algorithm_or_model_version",
            "residual_unexplained",
        ],
        required_statistician_inputs=[
            {
                "input": "How many repeated performances of the task each "
                "participant provides, and how many separate sessions those "
                "performances are spread across.",
                "why_public_research_cannot_supply_it": "Repetition count is a "
                "protocol decision with a burden cost, and the protocol is "
                "unreviewed. A maximum effort task cannot be repeated freely.",
            },
            {
                "input": "How many trained annotators mark each recording, whether "
                "every recording is double marked or only a sample, and how "
                "disagreements are adjudicated.",
                "why_public_research_cannot_supply_it": "Annotation load is the "
                "dominant cost of this lane and there is no budget, no annotation "
                "manual and nobody trained to the manual.",
            },
            {
                "input": "Whether a within-run change quantity is treated as one "
                "number per attempt or as a trajectory, because the two need "
                "different models.",
                "why_public_research_cannot_supply_it": "This follows from the "
                "selected estimand, and none is selected.",
            },
            {
                "input": "The valid cycle rule and the minimum usable material "
                "threshold, since both decide which attempts enter the analysis at "
                "all.",
                "why_public_research_cannot_supply_it": "The plan lists the valid "
                "cycle rule and minimum usable material among task factors that "
                "the reviewed protocol must fix. Choosing them here would be "
                "choosing the task.",
            },
        ],
        agreement_and_reliability={
            "statistic_family": "continuous_agreement",
            "form_selection_inputs": [
                "Whether annotators are a fixed set used for every recording or a "
                "sample drawn from a larger pool, which decides between the "
                "available intraclass correlation models.",
                "Whether the reported unit is one annotator's marking or the mean "
                "of several, which decides between single and average measures.",
                "Whether systematic difference between annotators matters, which "
                "decides between absolute agreement and consistency.",
                "The confidence interval on the agreement estimate, which must be "
                "reported rather than the point estimate alone.",
            ],
            "reporting_standards": [
                "grras_reliability_and_agreement_reporting",
                "icc_form_selection_guidance",
                "limits_of_agreement",
                "generalisability_theory_multi_facet",
                "cosmin_measurement_property_guidance",
            ],
            "notes": [
                "Reliability and accuracy are different. A timing algorithm can "
                "repeat itself perfectly and still mark the wrong onsets.",
                "Measurement error in milliseconds and the smallest change "
                "distinguishable from it must both be reported, because without "
                "them no future change can be called real.",
                "A design with annotators crossed with participants has more than "
                "one facet, and a single intraclass correlation collapses them. "
                "Generalisability theory keeps them separate.",
            ],
        },
        missingness_and_abstention={
            "categories": [
                "participant_withdrew",
                "task_not_attempted",
                "task_attempted_but_invalid",
                "recording_quality_invalid",
                "unsupported_context_or_variety",
                "reference_missing_or_unresolved",
                "reference_raters_disagreed_beyond_adjudication",
                "algorithm_abstained",
                "consent_withdrawn_after_collection",
            ],
            "note": "Selective abstention is itself an access and fairness "
            "outcome. A system that declines to score the people it serves worst "
            "will look accurate while failing them, so abstention is reported by "
            "subgroup rather than pooled into a missing data total.",
        },
        split_and_clustering={
            "cluster_units": [
                "site",
                "device",
                "repeated_session",
                "rater",
                "prompt_or_stimulus",
            ],
            "leakage_risks": [
                "Annotators who mark development recordings learn the task and the "
                "population, so annotator assignment is part of the split rather "
                "than an administrative detail.",
            ],
        },
        subgroup_and_representation=[
            "adults with and without any self-identified speech concern, kept as "
            "separate frames rather than pooled",
        ],
        blockers=[
            {
                "blocker": "No public source supplies the two blinded annotator "
                "reference this question requires, so nothing can be checked "
                "against anything until participants and annotators are recruited.",
                "blocker_class": "no_reference_evidence_exists",
            },
        ],
        sample_size={
            "method_candidates": list(RELIABILITY_SAMPLE_SIZE_METHODS),
            "prerequisites": [
                "A selected task, prompt and valid cycle rule.",
                "A pilot estimate of between-person and within-person variance "
                "under that exact task and capture path.",
                "A decision on how many annotators mark how many recordings.",
                "An acceptable confidence interval width, set by the claim and by "
                "the harm of being wrong.",
            ],
        },
    ),
]

MOTOR_TASK_CONSTRUCTS.append(
    _record(
        candidate_id="rapid_syllable_task_accuracy",
        title="Rapid syllable task accuracy",
        register_lane="motor_task",
        governance_lane="motor_speech",
        related_governance_lanes=["controlled_intelligibility"],
        register_row={
            "candidate": "Rapid syllable task accuracy",
            "narrowest_defensible_observation": "Observable omissions, "
            "substitutions, additions, sequence breaks or incomplete performance "
            "under frozen scoring rules",
            "required_reference": "Two blinded trained annotators and intended "
            "prompt",
            "disposition_23a": "Priority supporting evidence; never a disorder "
            "label",
        },
        observation={
            "what_would_be_measured": "Whether the syllables a person produced "
            "match the syllables the prompt asked for, counted under frozen rules, "
            "without any statement about why they differed.",
            "why_it_is_not_yet_a_measure": [
                "An error count is only meaningful against an intended prompt, and "
                "no prompt is selected.",
                "The scoring rules that decide what counts as an omission, a "
                "substitution or a sequence break do not exist, and they change "
                "the number more than the speaker does.",
                "Checkpoint 23A recorded that this can never become a disorder "
                "label. A person may depart from a prompt for reasons that have "
                "nothing to do with motor speech, including mishearing it, "
                "misreading it or choosing a different strategy.",
            ],
        },
        reference_requirement={
            "truth_class": "task_fidelity",
            "substitutions_refused": [
                "An automatic transcript cannot establish what a person intended "
                "to say, which is the same limit that makes ordinary pipeline "
                "recordings ineligible for item 22.",
                "Elapsed file duration says nothing about whether the task was "
                "performed.",
                "A diagnosis attached to the recording is population description, "
                "not a per attempt error count.",
            ],
            "public_availability": "no_qualifying_public_source",
            "source_survey_basis": ["ewa_db", "younger_nt_adults", "ondri_speech"],
            "consequence": "The survey found rapid syllable recordings in "
            "quantity and no source that marks task errors with two independent "
            "annotators. EWA-DB's manual annotation is corrected automatic "
            "transcription plus phenomenon tags; it marks no syllable boundary, "
            "count, onset or task error.",
        },
        estimand_shape={
            "question": "How often two trained annotators agree on whether a "
            "given attempt contained an observable departure from the prompt, and "
            "how far an algorithm agrees with their adjudicated result.",
            "unit_of_analysis": "participant_by_attempt",
            "comparison": "Algorithm against adjudicated human marking, and "
            "annotator against annotator, on the same attempts.",
        },
        variance_components_to_separate=[
            "between_participant",
            "within_participant_between_session",
            "within_session_between_attempt",
            "between_rater",
            "rater_by_participant_interaction",
            "between_prompt_or_stimulus",
            "practice_or_order_effect",
            "algorithm_or_model_version",
            "residual_unexplained",
        ],
        required_statistician_inputs=[
            {
                "input": "Whether accuracy is a binary judgement per attempt, a "
                "count of departures, or a category per departure type, because "
                "each needs a different agreement statistic.",
                "why_public_research_cannot_supply_it": "This follows from the "
                "scoring manual, which does not exist and must be written by the "
                "relevant professionals.",
            },
            {
                "input": "The expected base rate of observable departures in the "
                "recruited population, since a rare category makes chance corrected "
                "agreement unstable.",
                "why_public_research_cannot_supply_it": "The population frame is "
                "undecided and no pilot exists. Item 22 met this exact problem "
                "when its pre-search audit found one positive coarse target in "
                "development and none in tuning.",
            },
        ],
        agreement_and_reliability={
            "statistic_family": "categorical_agreement",
            "form_selection_inputs": [
                "Whether categories are nominal or ordered, which decides whether "
                "disagreements are weighted.",
                "Whether the same annotators mark every attempt, which decides "
                "which chance corrected coefficient applies.",
                "The base rate of each category, because a high agreement figure "
                "on a rare category can be an artefact of the rate rather than of "
                "the annotators.",
                "Whether raw agreement is reported beside the chance corrected "
                "figure, since the two answer different questions.",
            ],
            "reporting_standards": [
                "grras_reliability_and_agreement_reporting",
                "cosmin_measurement_property_guidance",
            ],
            "notes": [
                "Raw disagreement is data. It is preserved rather than replaced by "
                "an adjudicated label, because the disagreement rate is itself the "
                "ceiling on any later claim.",
                "A category that no annotator ever assigns is reported as "
                "unobserved rather than as perfect agreement.",
            ],
        },
        missingness_and_abstention={
            "categories": [
                "participant_withdrew",
                "task_not_attempted",
                "task_attempted_but_invalid",
                "recording_quality_invalid",
                "unsupported_context_or_variety",
                "reference_missing_or_unresolved",
                "reference_raters_disagreed_beyond_adjudication",
                "algorithm_abstained",
                "consent_withdrawn_after_collection",
            ],
            "note": "An attempt that was not performed as instructed is a task "
            "fidelity outcome, not a poor score. The two must never be merged, "
            "because merging them turns a misunderstood instruction into evidence "
            "about a person's speech.",
        },
        split_and_clustering={
            "cluster_units": ["site", "repeated_session", "rater", "prompt_or_stimulus"],
            "leakage_risks": [
                "Prompts must be grouped. An annotator or model that has seen the "
                "intended sequence can reconstruct it rather than observe it.",
            ],
        },
        subgroup_and_representation=[
            "adults for whom the prompt language or syllable sequence is unfamiliar",
        ],
        blockers=[
            {
                "blocker": "No public source marks rapid syllable task errors with "
                "two independent annotators, so the reference must be created "
                "prospectively.",
                "blocker_class": "no_reference_evidence_exists",
            },
        ],
        sample_size={
            "method_candidates": [
                "Sample size methods for chance corrected agreement "
                "coefficients, which require the expected agreement, the expected "
                "category base rates and the desired confidence interval width. "
                "Sim, J. and Wright, C. C. The kappa statistic in reliability "
                "studies: use, interpretation, and sample size requirements. "
                "Physical Therapy, 2005, doi:10.1093/ptj/85.3.257. Citation "
                "confirmed against Crossref; primary text not opened here.",
                "Bonett, D. G. Sample size requirements for estimating intraclass "
                "correlations with desired precision. Statistics in Medicine, 2002, "
                "where the outcome is treated as continuous.",
            ],
            "prerequisites": [
                "A written scoring manual with fixed departure categories.",
                "A pilot estimate of each category's base rate.",
                "A decision on double marking coverage.",
            ],
        },
    )
)

GENERAL_SPEECH_CONSTRUCTS = [
    _record(
        candidate_id="articulation_rate",
        title="Articulation rate",
        register_lane="general_speech",
        governance_lane="general_speech",
        related_governance_lanes=["motor_speech"],
        register_row={
            "candidate": "Articulation rate",
            "narrowest_defensible_observation": "Syllables per second after a "
            "predeclared pause rule on a fixed prompt",
            "required_reference": "Human-reviewed syllable and speech boundaries",
            "disposition_23a": "Candidate context only; not current WPM and not "
            "motor-specific",
        },
        observation={
            "what_would_be_measured": "How many syllables a person produces per "
            "second of actual speaking time on a fixed prompt, once pauses are "
            "removed by a rule declared in advance.",
            "why_it_is_not_yet_a_measure": [
                "The pause rule decides the number. A different pause threshold "
                "produces a different articulation rate from the same recording, "
                "so the rule is part of the measure rather than a preprocessing "
                "detail.",
                "Checkpoint 23A recorded explicitly that this is not the existing "
                "words per minute output and is not motor specific. The current "
                "pipeline's timing values may not be relabelled as motor evidence.",
                "Speaking faster or slower has many ordinary explanations, "
                "including familiarity with the prompt, register, mood and who the "
                "person is talking to.",
            ],
        },
        reference_requirement={
            "truth_class": "timing_and_boundary_truth",
            "substitutions_refused": [
                "Automatic speech recognition word timings are the candidate's own "
                "segmentation and cannot check it.",
                "A syllable count derived from the orthographic prompt assumes the "
                "person produced every syllable, which is the thing being measured.",
            ],
            "public_availability": "not_surveyed_public_availability_unknown",
            "source_survey_basis": [],
            "consequence": "The checkpoint 23B source survey covered motor task, "
            "perceptual voice and intelligibility truth. It did not survey sources "
            "carrying human reviewed syllable and speech boundaries on connected "
            "speech, so this record records the availability question as open "
            "rather than answered. Nobody should read that as encouraging.",
        },
        estimand_shape={
            "question": "How closely an automatic syllable and pause segmentation "
            "matches human reviewed boundaries on the same fixed prompt, and how "
            "stable the resulting rate is within one person across sessions.",
            "unit_of_analysis": "participant_by_session",
            "comparison": "Algorithm boundaries against human reviewed "
            "boundaries, and the same person against themselves on repeated "
            "readings of the same prompt.",
        },
        variance_components_to_separate=[
            "between_participant",
            "within_participant_between_session",
            "within_session_between_attempt",
            "between_rater",
            "between_prompt_or_stimulus",
            "between_device",
            "adaptation_or_familiarity_effect",
            "algorithm_or_model_version",
            "residual_unexplained",
        ],
        required_statistician_inputs=[
            {
                "input": "The exact pause rule, including the minimum silence "
                "duration that separates two runs of speech.",
                "why_public_research_cannot_supply_it": "The plan lists the pause "
                "definition among task factors the reviewed protocol must fix. "
                "Choosing a threshold here would silently define the measure.",
            },
            {
                "input": "Whether the prompt is held constant across participants "
                "or varied, since a varied prompt adds a stimulus facet.",
                "why_public_research_cannot_supply_it": "Prompt design is part of "
                "the unreviewed protocol.",
            },
        ],
        agreement_and_reliability={
            "statistic_family": "continuous_agreement",
            "form_selection_inputs": [
                "Whether the reported quantity is the rate itself or the boundary "
                "positions, because agreement on a derived rate can hide "
                "compensating boundary errors.",
                "Whether human reviewers are a fixed panel or a sample.",
                "Whether systematic offset between algorithm and human boundaries "
                "matters, which decides absolute agreement against consistency.",
            ],
            "reporting_standards": [
                "grras_reliability_and_agreement_reporting",
                "icc_form_selection_guidance",
                "limits_of_agreement",
                "cosmin_measurement_property_guidance",
            ],
            "notes": [
                "Two boundary errors in opposite directions cancel in the rate. "
                "Agreement must therefore be reported on the boundaries as well as "
                "on the derived quantity.",
            ],
        },
        missingness_and_abstention={
            "categories": [
                "participant_withdrew",
                "task_not_attempted",
                "task_attempted_but_invalid",
                "recording_quality_invalid",
                "unsupported_context_or_variety",
                "reference_missing_or_unresolved",
                "algorithm_abstained",
                "consent_withdrawn_after_collection",
            ],
            "note": "A recording rejected for quality is a capture outcome and "
            "must not be reported as a speech result.",
        },
        split_and_clustering={
            "cluster_units": ["site", "device", "repeated_session", "prompt_or_stimulus", "rater"],
            "leakage_risks": [
                "A fixed prompt read repeatedly makes later readings faster through "
                "familiarity, so reading order and repetition are part of the "
                "design rather than noise.",
            ],
        },
        subgroup_and_representation=[
            "adults reading aloud versus adults using the spoken alternative to "
            "reading",
        ],
        blockers=[
            {
                "blocker": "Whether human reviewed boundary reference material is "
                "publicly obtainable was not surveyed and remains unknown.",
                "blocker_class": "reference_availability_unresolved",
            },
        ],
        sample_size={
            "method_candidates": list(RELIABILITY_SAMPLE_SIZE_METHODS),
            "prerequisites": [
                "A fixed prompt and a fixed pause rule.",
                "A pilot estimate of within-person session to session variation.",
                "A decision on how much material each human reviewer marks.",
            ],
        },
    ),
    _record(
        candidate_id="speech_rate_and_pause_profile",
        title="Speech rate and pause profile",
        register_lane="general_speech",
        governance_lane="general_speech",
        related_governance_lanes=["motor_speech"],
        register_row={
            "candidate": "Speech rate and pause profile",
            "narrowest_defensible_observation": "Syllables per second including "
            "pauses, plus declared pause counts and durations",
            "required_reference": "Human-reviewed prompt, speech and pause "
            "boundaries",
            "disposition_23a": "Supporting context only; preserve non-motor "
            "explanations",
        },
        observation={
            "what_would_be_measured": "Overall speaking rate including pauses, "
            "with the pauses themselves counted and timed rather than discarded.",
            "why_it_is_not_yet_a_measure": [
                "Pausing carries meaning. A pause may be planning, breathing, "
                "emphasis, turn holding or hesitation, and the acoustic record "
                "cannot distinguish them.",
                "Checkpoint 23A requires that non-motor explanations be preserved "
                "rather than resolved, so this quantity is context and never "
                "evidence of a motor cause.",
                "Item 21 already stores separate timestamped event candidates and "
                "keeps them out of coaching, progress and screening. That boundary "
                "applies here too and is not relaxed by this record existing.",
            ],
        },
        reference_requirement={
            "truth_class": "timing_and_boundary_truth",
            "substitutions_refused": [
                "Silence is not a pause type. Checkpoint 21 established that "
                "silence cannot establish a block, and the same limit applies to "
                "labelling a pause's function.",
                "The candidate system's own voice activity detection cannot check "
                "the candidate system's own pause boundaries.",
            ],
            "public_availability": "not_surveyed_public_availability_unknown",
            "source_survey_basis": [],
            "consequence": "As with articulation rate, connected speech boundary "
            "reference was outside the source survey's three lanes, so the "
            "availability question is open.",
        },
        estimand_shape={
            "question": "How closely automatic pause detection matches human "
            "reviewed pause boundaries, and how much the pause profile of one "
            "person varies across sessions on the same prompt.",
            "unit_of_analysis": "participant_by_session",
            "comparison": "Algorithm against human reviewed boundaries, and the "
            "same person against themselves across sessions.",
        },
        variance_components_to_separate=[
            "between_participant",
            "within_participant_between_session",
            "within_session_between_attempt",
            "between_rater",
            "between_prompt_or_stimulus",
            "between_device",
            "between_room_or_environment",
            "current_state_fatigue_or_voice_use",
            "algorithm_or_model_version",
            "residual_unexplained",
        ],
        required_statistician_inputs=[
            {
                "input": "Whether pause count, total pause time and pause duration "
                "distribution are separate reported quantities or one composite.",
                "why_public_research_cannot_supply_it": "The plan prohibits a "
                "combined index without its own evidence, so the decision is a "
                "governance one.",
            },
            {
                "input": "How breath pauses are treated, given that they are "
                "physiologically necessary and not a speech outcome.",
                "why_public_research_cannot_supply_it": "This needs the reviewed "
                "protocol and professional input.",
            },
        ],
        agreement_and_reliability={
            "statistic_family": "continuous_agreement",
            "form_selection_inputs": [
                "Whether the quantity is a count, a total duration or a "
                "distribution, since a distribution needs more than a single "
                "agreement coefficient.",
                "Whether reviewers are a fixed panel or a sample.",
                "Whether the reported unit is a single reviewer or an average.",
            ],
            "reporting_standards": [
                "grras_reliability_and_agreement_reporting",
                "icc_form_selection_guidance",
                "limits_of_agreement",
                "cosmin_measurement_property_guidance",
            ],
            "notes": [
                "Pause counts are bounded below by zero and are often skewed, so "
                "an agreement statistic that assumes symmetry may mislead.",
            ],
        },
        missingness_and_abstention={
            "categories": [
                "participant_withdrew",
                "task_not_attempted",
                "task_attempted_but_invalid",
                "recording_quality_invalid",
                "unsupported_context_or_variety",
                "reference_missing_or_unresolved",
                "algorithm_abstained",
                "consent_withdrawn_after_collection",
            ],
            "note": "Background speech from another person invalidates the "
            "recording for this question rather than contributing a pause.",
        },
        split_and_clustering={
            "cluster_units": ["site", "device", "repeated_session", "prompt_or_stimulus", "rater"],
            "leakage_risks": [],
        },
        subgroup_and_representation=[
            "adults whose first language is not English, whose pause structure "
            "differs for reasons unrelated to motor speech",
        ],
        blockers=[
            {
                "blocker": "Public availability of human reviewed pause boundary "
                "reference was not surveyed.",
                "blocker_class": "reference_availability_unresolved",
            },
        ],
        sample_size={
            "method_candidates": list(RELIABILITY_SAMPLE_SIZE_METHODS),
            "prerequisites": [
                "A fixed prompt and a fixed pause definition.",
                "A pilot estimate of within-person variation.",
                "A decision on whether pause quantities are reported separately.",
            ],
        },
    ),
]

FUNCTIONAL_CONSTRUCTS = [
    _record(
        candidate_id="controlled_intelligibility",
        title="Controlled intelligibility",
        register_lane="functional",
        governance_lane="controlled_intelligibility",
        related_governance_lanes=["motor_speech", "general_speech"],
        register_row={
            "candidate": "Controlled intelligibility",
            "narrowest_defensible_observation": "The relationship between an "
            "independently adjudicated production and words transcribed by "
            "multiple unfamiliar listeners under a fixed listening protocol",
            "required_reference": "Intended prompt, independently adjudicated "
            "actual production and blinded listener-level transcriptions retained "
            "separately",
            "disposition_23a": "Candidate independent outcome, not motor truth or "
            "cause",
        },
        observation={
            "what_would_be_measured": "How much of what a person actually said "
            "gets through to listeners who do not know them, under a listening "
            "condition fixed in advance.",
            "why_it_is_not_yet_a_measure": [
                "Intelligibility is a property of a speaker, a listener, a message "
                "and a channel together. Attributing it to the speaker alone is "
                "the exact error the Clarity Prediction Challenge record was kept "
                "as a warning against, where a hearing aid algorithm and a "
                "listener's hearing loss would have been charged to the talker.",
                "It answers a functional listener question and never a motor cause.",
                "Three separate things must be distinguished and cannot be "
                "collapsed: what the prompt asked for, what the person actually "
                "produced, and what the listener heard. Only the third is the "
                "measurement.",
            ],
        },
        reference_requirement={
            "truth_class": "intelligibility_truth",
            "substitutions_refused": [
                "Automatic speech recognition confidence is not a listener.",
                "One familiar listener is not several unfamiliar listeners, "
                "because familiarity is itself a large effect.",
                "A clinician's estimate of intelligibility is a clinical judgement "
                "and a different truth class.",
                "A consensus transcription destroys the between listener variation "
                "that is the measurement's own uncertainty.",
            ],
            "public_availability": "sources_exist_none_lawfully_usable",
            "source_survey_basis": [
                "speech_accessibility_project",
                "torgo",
                "talkbank_phonbank_clinical",
                "ua_speech",
                "osf_slp_intelligibility_estimations",
                "clarity_prediction_challenge",
            ],
            "consequence": "The survey found sources of the right shape and none "
            "this project may lawfully use. The largest permits commercial "
            "development and is blocked by a data use agreement needing an "
            "organisational countersignature, which is the missing legal entity "
            "blocking a route concretely. One openly visible collection carrying "
            "transcriptions from seventy unfamiliar listeners has no licence "
            "assigned at all, and public visibility is not a grant.",
        },
        estimand_shape={
            "question": "How much of the variation in listener transcription "
            "accuracy belongs to the speaker rather than to the listener, the "
            "stimulus or the listening condition.",
            "unit_of_analysis": "participant_by_listener",
            "comparison": "Speaker against speaker under a fixed listening "
            "condition, with listener and stimulus treated as separate facets "
            "rather than as noise.",
        },
        variance_components_to_separate=[
            "between_participant",
            "within_participant_between_session",
            "between_listener",
            "listener_by_speaker_interaction",
            "between_prompt_or_stimulus",
            "adaptation_or_familiarity_effect",
            "between_room_or_environment",
            "between_device",
            "residual_unexplained",
        ],
        required_statistician_inputs=[
            {
                "input": "How many listeners hear each speaker, how many speakers "
                "each listener hears, and whether the design is fully crossed or "
                "nested.",
                "why_public_research_cannot_supply_it": "This is the central "
                "design decision of a listener study and it drives cost, burden "
                "and every variance component. It needs a statistician and a "
                "budget.",
            },
            {
                "input": "The listener adaptation control: how quickly listeners "
                "improve at understanding a given speaker, and how presentation "
                "order guards against it.",
                "why_public_research_cannot_supply_it": "Adaptation size depends "
                "on the population and the material, and no pilot exists.",
            },
            {
                "input": "The scoring rule for a partially correct transcription, "
                "and how a listener's spelling, homophone choice or morphological "
                "guess is treated.",
                "why_public_research_cannot_supply_it": "This belongs in a "
                "listener manual written by the relevant professionals.",
            },
            {
                "input": "How the independently adjudicated actual production is "
                "established, since intelligibility is scored against what was "
                "produced rather than against what was prompted.",
                "why_public_research_cannot_supply_it": "Adjudicating actual "
                "production is itself a two annotator task with its own manual and "
                "its own cost.",
            },
        ],
        agreement_and_reliability={
            "statistic_family": "transcription_based_accuracy",
            "form_selection_inputs": [
                "Whether the reported unit is one listener or a panel mean, since "
                "a panel mean is far more reliable than any member of it and the "
                "two must not be reported interchangeably.",
                "Whether listeners are treated as a fixed panel or as a sample "
                "from a listener population the claim generalises to.",
                "Whether the analysis models speaker and listener as crossed "
                "random effects rather than averaging listeners away first.",
            ],
            "reporting_standards": [
                "grras_reliability_and_agreement_reporting",
                "generalisability_theory_multi_facet",
                "cosmin_measurement_property_guidance",
            ],
            "notes": [
                "Averaging listeners before analysis discards the listener "
                "variance component and makes the result look more precise than it "
                "is.",
                "A speaker who is easy for one listener and hard for another is "
                "reporting a real interaction, not measurement error.",
            ],
        },
        missingness_and_abstention={
            "categories": [
                "participant_withdrew",
                "task_not_attempted",
                "task_attempted_but_invalid",
                "recording_quality_invalid",
                "unsupported_context_or_variety",
                "reference_missing_or_unresolved",
                "reference_raters_disagreed_beyond_adjudication",
                "consent_withdrawn_after_collection",
            ],
            "note": "A listener who withdraws mid session leaves an incomplete "
            "block, which is a design problem rather than a missing value to "
            "impute.",
        },
        split_and_clustering={
            "cluster_units": [
                "listener",
                "prompt_or_stimulus",
                "site",
                "repeated_session",
                "device",
            ],
            "leakage_risks": [
                "A listener who has already heard a speaker is no longer an "
                "unfamiliar listener for that speaker, so listeners are consumed "
                "by exposure and must be tracked across splits.",
                "Reusing the same prompt sentences across development and "
                "evaluation lets a listener learn the material rather than the "
                "speaker.",
            ],
        },
        subgroup_and_representation=[
            "listeners with normal hearing under a verified hearing screen",
            "listener language background and familiarity with the speaker's "
            "variety",
        ],
        blockers=[
            {
                "blocker": "Every located source of the right shape is either non "
                "commercial, unlicensed, restricted to credentialed clinicians, "
                "about children, or blocked by an agreement requiring an "
                "organisational countersignature.",
                "blocker_class": "reference_evidence_not_lawfully_usable",
            },
        ],
        sample_size={
            "method_candidates": list(LISTENER_SAMPLE_SIZE_METHODS),
            "prerequisites": [
                "A fixed listening condition and stimulus set.",
                "A pilot estimate of listener, speaker and interaction variance.",
                "A decision on the crossed or nested listener design.",
            ],
        },
    ),
    _record(
        candidate_id="comprehensibility_or_effort",
        title="Comprehensibility or listener effort",
        register_lane="functional",
        governance_lane="controlled_intelligibility",
        related_governance_lanes=["participant_report"],
        register_row={
            "candidate": "Comprehensibility or effort",
            "narrowest_defensible_observation": "Listener experience under one "
            "predeclared instrument and condition",
            "required_reference": "Multiple listeners with individual results "
            "retained",
            "disposition_23a": "Deferred until intended benefit is defined",
        },
        observation={
            "what_would_be_measured": "How much work listeners report it took to "
            "understand, which is a different question from how much they "
            "understood.",
            "why_it_is_not_yet_a_measure": [
                "Checkpoint 23A deferred this outright until the intended benefit "
                "is defined, and the benefit is still undefined.",
                "Effort ratings measure the listener's experience. Reporting them "
                "as a speaker property would attribute a listener's attention, "
                "hearing, fatigue and attitude to the person speaking.",
                "No instrument is selected, and instrument choice changes the "
                "construct rather than just the scale.",
            ],
        },
        reference_requirement={
            "truth_class": "functional_truth",
            "substitutions_refused": [
                "Transcription accuracy is not effort. A listener may understand "
                "everything and still find it exhausting.",
                "An acoustic primitive cannot stand in for a listener's reported "
                "experience.",
            ],
            "public_availability": "sources_exist_none_lawfully_usable",
            "source_survey_basis": ["osf_slp_intelligibility_estimations", "torgo"],
            "consequence": "This question inherits the intelligibility lane's "
            "availability problem and adds an instrument selection problem on top "
            "of it.",
        },
        estimand_shape={
            "question": "How consistently listeners rate the effort of "
            "understanding the same speaker, and how much of that rating is the "
            "speaker rather than the listener.",
            "unit_of_analysis": "participant_by_listener",
            "comparison": "Speaker against speaker with listener retained as a "
            "separate facet.",
        },
        variance_components_to_separate=[
            "between_participant",
            "between_listener",
            "listener_by_speaker_interaction",
            "between_prompt_or_stimulus",
            "adaptation_or_familiarity_effect",
            "residual_unexplained",
        ],
        required_statistician_inputs=[
            {
                "input": "The selected instrument, its scale properties and "
                "whether its published measurement properties transfer to this "
                "population and condition.",
                "why_public_research_cannot_supply_it": "Instrument selection is "
                "deferred and would need review against measurement property "
                "guidance by someone accountable for it.",
            },
            {
                "input": "Whether the rating is ordinal or continuous, since that "
                "decides the agreement statistic and the model.",
                "why_public_research_cannot_supply_it": "It follows from the "
                "unselected instrument.",
            },
        ],
        agreement_and_reliability={
            "statistic_family": "ordinal_or_rating_scale_agreement",
            "form_selection_inputs": [
                "Whether the scale is treated as ordinal or as continuous.",
                "Whether the reported unit is one listener or a panel mean.",
                "Whether listener specific response style is modelled or ignored.",
            ],
            "reporting_standards": [
                "cosmin_measurement_property_guidance",
                "grras_reliability_and_agreement_reporting",
                "generalisability_theory_multi_facet",
            ],
            "notes": [
                "Rating scale agreement is where the perceptual voice lane's "
                "measured ceiling is most instructive: on the most reliable "
                "feature in the one open voice source, two trained clinicians "
                "typically differed by twelve to fifteen points on a hundred point "
                "scale. A new effort scale should not be assumed to do better.",
            ],
        },
        missingness_and_abstention={
            "categories": [
                "participant_withdrew",
                "task_not_attempted",
                "recording_quality_invalid",
                "unsupported_context_or_variety",
                "reference_missing_or_unresolved",
                "consent_withdrawn_after_collection",
            ],
            "note": "A listener declining to rate is recorded rather than treated "
            "as a mid scale response.",
        },
        split_and_clustering={
            "cluster_units": ["listener", "prompt_or_stimulus", "repeated_session"],
            "leakage_risks": [],
        },
        subgroup_and_representation=[
            "listeners of different ages and hearing status, where the claim "
            "includes them",
        ],
        blockers=[
            {
                "blocker": "The question is deferred at checkpoint 23A until an "
                "intended benefit exists, and no instrument is selected.",
                "blocker_class": "no_task_or_construct_selected",
            },
        ],
        sample_size={
            "method_candidates": list(LISTENER_SAMPLE_SIZE_METHODS),
            "prerequisites": [
                "A selected instrument and listening condition.",
                "A pilot estimate of listener and speaker variance on that "
                "instrument.",
            ],
        },
    ),
]

PERSONAL_CONSTRUCTS = [
    _record(
        candidate_id="communication_impact_and_desired_change",
        title="Communication impact and desired change",
        register_lane="personal",
        governance_lane="participant_report",
        related_governance_lanes=["controlled_intelligibility", "voice"],
        register_row={
            "candidate": "Communication impact and desired change",
            "narrowest_defensible_observation": "What the participant reports "
            "matters in their life and identity",
            "required_reference": "Participant report using an appropriate "
            "instrument or accessible qualitative method",
            "disposition_23a": "Required separate outcome; never inferred",
        },
        observation={
            "what_would_be_measured": "What the person themselves says matters "
            "about their communication, in their own terms.",
            "why_it_is_not_yet_a_measure": [
                "Checkpoint 23A records this as required and as never inferable. "
                "No acoustic, listener or clinical evidence may be used to "
                "estimate it.",
                "No instrument or accessible qualitative method is selected, and "
                "selecting one without lived experience governance would decide "
                "what counts as mattering on the participant's behalf.",
                "The product vision requires that progress mean becoming more "
                "capable in situations the person values, which cannot be defined "
                "without asking them.",
            ],
        },
        reference_requirement={
            "truth_class": "personal_truth",
            "substitutions_refused": [
                "Acoustic evidence cannot establish personal impact.",
                "A listener's judgement is not the speaker's experience.",
                "A clinical assessment answers a clinical question and not this "
                "one.",
                "A support person or representative may assist without becoming "
                "the source; the record must keep whose experience is reported "
                "distinct from who helped report it.",
            ],
            "public_availability": "not_applicable_participant_is_the_source",
            "source_survey_basis": [],
            "consequence": "No external dataset can supply this. It exists only "
            "when a consenting participant is asked, which makes it structurally "
            "dependent on the same ethics and governance route as every other "
            "lane.",
        },
        estimand_shape={
            "question": "What the person reports matters, and whether a reported "
            "change is meaningful to them rather than merely detectable.",
            "unit_of_analysis": "participant",
            "comparison": "The same person against their own earlier report, "
            "under an instrument or method whose interpretation they accept.",
        },
        variance_components_to_separate=[
            "between_participant",
            "within_participant_between_session",
            "current_state_fatigue_or_voice_use",
            "residual_unexplained",
        ],
        required_statistician_inputs=[
            {
                "input": "The instrument or accessible qualitative method, and "
                "whether its published measurement properties were established in "
                "a population this study's participants belong to.",
                "why_public_research_cannot_supply_it": "Instrument choice is a "
                "lived experience and professional governance decision, not a "
                "statistical one.",
            },
            {
                "input": "What the participant themselves considers a meaningful "
                "change, which anchors any later smallest detectable change.",
                "why_public_research_cannot_supply_it": "Only participants can "
                "supply it, and none has been recruited.",
            },
            {
                "input": "How qualitative material is analysed and by whom, if an "
                "accessible qualitative method is used instead of a scale.",
                "why_public_research_cannot_supply_it": "It needs the method, the "
                "analysts and the ethics approval that permits the material to be "
                "collected.",
            },
        ],
        agreement_and_reliability={
            "statistic_family": "not_applicable_no_second_observer",
            "form_selection_inputs": [
                "There is no second observer, because the participant is the only "
                "valid source. Reliability here means stability of the person's "
                "own report over a period short enough that nothing real changed, "
                "which is a test retest question rather than an inter rater one.",
                "Whether the instrument's recall window makes a retest interval "
                "meaningful at all.",
            ],
            "reporting_standards": [
                "cosmin_measurement_property_guidance",
            ],
            "notes": [
                "A stable report is not necessarily an accurate one and an "
                "unstable report is not necessarily an error; the person's "
                "situation may genuinely have changed.",
                "Measurement error here bounds what may later be called personal "
                "progress, which the repository already blocks for every existing "
                "metric.",
            ],
        },
        missingness_and_abstention={
            "categories": [
                "participant_withdrew",
                "task_not_attempted",
                "unsupported_context_or_variety",
                "consent_withdrawn_after_collection",
            ],
            "note": "A participant may decline any item without penalty, and a "
            "declined item is never imputed from their speech.",
        },
        split_and_clustering={
            "cluster_units": ["site", "repeated_session"],
            "leakage_risks": [],
        },
        subgroup_and_representation=[
            "adults who use assisted or augmentative communication",
            "adults for whom reading the instrument is not accessible",
        ],
        blockers=[
            {
                "blocker": "No instrument or accessible qualitative method is "
                "selected, and paid lived experience governance has not been "
                "engaged to review one.",
                "blocker_class": "no_task_or_construct_selected",
            },
        ],
        sample_size={
            "method_candidates": [
                "Test retest reliability sizing, which needs the expected "
                "reliability, the retest interval and the desired confidence "
                "interval width. Bonett, D. G. Sample size requirements for "
                "estimating intraclass correlations with desired precision. "
                "Statistics in Medicine, 2002.",
                "For qualitative methods, sizing is by information power and "
                "analytic saturation rather than by a variance calculation, which "
                "is a different discipline and needs its own methodologist.",
            ],
            "prerequisites": [
                "A selected instrument or method reviewed with people who have "
                "lived experience.",
                "An ethics approved route to ask participants anything at all.",
            ],
        },
    ),
]

VOICE_CONSTRUCTS = [
    _record(
        candidate_id="item_20_voice_acoustic_primitives",
        title="Existing item 20 CPPS and related voice acoustic primitives",
        register_lane="voice_acoustic",
        governance_lane="voice",
        related_governance_lanes=[],
        register_row={
            "candidate": "Existing item 20 CPPS and related primitives",
            "narrowest_defensible_observation": "Declared acoustic calculation for "
            "a standardised task",
            "required_reference": "Frozen algorithm, fixtures and task-valid audio",
            "disposition_23a": "Supporting research evidence only; no relabelling "
            "or composite",
        },
        observation={
            "what_would_be_measured": "The value a declared acoustic formula "
            "produces from a recording made under a standardised task, and nothing "
            "about what that value means.",
            "why_it_is_not_yet_a_measure": [
                "Item 20 is engineering complete and scientifically locked. Its "
                "values are low level primitives with no released score or "
                "interpretation, and finishing item 23 does not unlock them.",
                "Checkpoint 23A prohibits relabelling these values as motor "
                "evidence and prohibits combining them into an index.",
                "An acoustic value computed correctly can still be the wrong "
                "quantity for the question, which is why computational truth and "
                "perceptual truth are separate classes.",
            ],
        },
        reference_requirement={
            "truth_class": "computational_truth",
            "substitutions_refused": [
                "Agreement with a second library that implements the same formula "
                "is not independent evidence. Two implementations of the same idea "
                "can be wrong together.",
                "A perceptual rating is a different truth class and cannot verify "
                "an arithmetic result.",
            ],
            "public_availability": "not_applicable_computational_truth",
            "source_survey_basis": [],
            "consequence": "Verification here needs a written mathematical "
            "definition, a versioned implementation, synthetic fixtures and "
            "independently recomputed examples. No external corpus is required for "
            "that, and no external corpus can substitute for it.",
        },
        estimand_shape={
            "question": "How stable a declared acoustic value is for the same "
            "person across attempts, sessions, devices and rooms when nothing "
            "about their voice has changed.",
            "unit_of_analysis": "participant_by_session",
            "comparison": "The same person against themselves across repeated "
            "recordings, and the same recording across capture paths.",
        },
        variance_components_to_separate=[
            "between_participant",
            "within_participant_between_session",
            "within_session_between_attempt",
            "between_device",
            "between_room_or_environment",
            "current_state_fatigue_or_voice_use",
            "algorithm_or_model_version",
            "residual_unexplained",
        ],
        required_statistician_inputs=[
            {
                "input": "Which acoustic quantities are reported and whether any "
                "of them is primary, since item 20 exposes several.",
                "why_public_research_cannot_supply_it": "Selecting a primary "
                "quantity is a construct decision reserved for the voice "
                "governance lane.",
            },
            {
                "input": "The device and room equivalence design, since a value "
                "that moves with the microphone is a property of the capture path "
                "rather than of the person.",
                "why_public_research_cannot_supply_it": "It needs the capture "
                "paths the claim will actually include, which are undecided.",
            },
        ],
        agreement_and_reliability={
            "statistic_family": "continuous_agreement",
            "form_selection_inputs": [
                "Whether the comparison is the same recording processed twice, "
                "which tests determinism, or the same person recorded twice, which "
                "tests stability. These are different questions and must be "
                "reported separately.",
                "Whether device is a fixed set or a sample of devices the claim "
                "generalises to.",
                "Whether systematic offset between devices matters, which decides "
                "absolute agreement against consistency.",
            ],
            "reporting_standards": [
                "grras_reliability_and_agreement_reporting",
                "icc_form_selection_guidance",
                "limits_of_agreement",
                "cosmin_measurement_property_guidance",
            ],
            "notes": [
                "Determinism is cheap and proves almost nothing about a person. "
                "It must never be reported as reliability.",
                "The item 22 record already shows the failure mode: a repeatable "
                "system reporting the same unfounded concern every time makes the "
                "error look like evidence.",
            ],
        },
        missingness_and_abstention={
            "categories": [
                "participant_withdrew",
                "task_not_attempted",
                "task_attempted_but_invalid",
                "recording_quality_invalid",
                "unsupported_context_or_variety",
                "algorithm_abstained",
                "consent_withdrawn_after_collection",
            ],
            "note": "Item 20 already carries octave error checks and task and "
            "consent gates. Their outcomes are abstentions with reasons, not "
            "missing values.",
        },
        split_and_clustering={
            "cluster_units": ["device", "repeated_session", "site", "prompt_or_stimulus"],
            "leakage_risks": [
                "Device and participant are often confounded, because people bring "
                "their own phones. A device effect can masquerade as a person "
                "effect unless the design breaks the pairing.",
            ],
        },
        subgroup_and_representation=[
            "capture devices and operating systems the claim includes",
            "recording environments from quiet room to ordinary home",
        ],
        blockers=[
            {
                "blocker": "The voice lane is unselected and item 20's scientific "
                "release remains locked independently of item 23.",
                "blocker_class": "no_task_or_construct_selected",
            },
        ],
        sample_size={
            "method_candidates": list(RELIABILITY_SAMPLE_SIZE_METHODS),
            "prerequisites": [
                "A standardised task and a defined capture path set.",
                "A pilot estimate of within-person and between-device variation.",
            ],
        },
    ),
]

VOICE_CONSTRUCTS.extend(
    [
        _record(
            candidate_id="voice_perceptual_judgement",
            title="Perceptual voice judgement",
            register_lane="voice_perceptual",
            governance_lane="voice",
            related_governance_lanes=["clinical_or_laryngeal_reference"],
            register_row={
                "candidate": "Overall severity, roughness, breathiness, strain or "
                "pitch/loudness deviation",
                "narrowest_defensible_observation": "Independent trained listener "
                "judgement under a standardised protocol",
                "required_reference": "Several blinded qualified raters, preserved "
                "ratings and adjudication",
                "disposition_23a": "Deferred to independent voice governance; no "
                "automatic label",
            },
            observation={
                "what_would_be_measured": "How trained listeners judge a voice on "
                "named perceptual features, with each listener's own rating kept "
                "rather than averaged away.",
                "why_it_is_not_yet_a_measure": [
                    "Checkpoint 23A defers this to independent voice governance "
                    "and prohibits any automatic label.",
                    "The one open source's measured agreement ceiling bounds "
                    "anything built on it before a single line of code is written.",
                    "Two of the features have poor human agreement and are "
                    "excluded outright, so the feature list is already shorter than "
                    "the register row suggests.",
                ],
            },
            reference_requirement={
                "truth_class": "perceptual_voice_truth",
                "substitutions_refused": [
                    "One clinician cannot substitute for several. The survey found "
                    "an openly licensed single evaluator label set and it does not "
                    "become perceptual truth by being free.",
                    "A consensus value destroys the retained disagreement this "
                    "plan requires.",
                    "A vendor score is not a trained listener.",
                    "An acoustic primitive cannot be relabelled as a perceptual "
                    "judgement.",
                ],
                "public_availability": "one_candidate_unresolved",
                "source_survey_basis": [
                    "pvqd",
                    "saarbruecken_grb_labels",
                    "neurovoz",
                    "aprocsa",
                    "voiced_physionet",
                    "bridge2ai_voice",
                    "avfad",
                ],
                "consequence": "Exactly one candidate exists, it is openly "
                "licensed and obtainable without contact, and whether it "
                "distributes individual rater rows rather than combined values is "
                "unresolved. That question decides whether the lane has a usable "
                "reference at all, and settling it is an owner decision rather "
                "than an agent one.",
            },
            estimand_shape={
                "question": "How far trained raters agree with each other on a "
                "named perceptual feature, and whether any automatic quantity "
                "tracks their adjudicated judgement more closely than they track "
                "each other.",
                "unit_of_analysis": "participant_by_rater",
                "comparison": "Rater against rater on the same recordings, and any "
                "candidate quantity against the rater panel.",
            },
            variance_components_to_separate=[
                "between_participant",
                "between_rater",
                "rater_by_participant_interaction",
                "between_prompt_or_stimulus",
                "within_participant_between_session",
                "between_device",
                "current_state_fatigue_or_voice_use",
                "residual_unexplained",
            ],
            required_statistician_inputs=[
                {
                    "input": "Which perceptual features are carried, given that "
                    "pitch and loudness are excluded by the measured agreement "
                    "evidence and may not be used as reference at all.",
                    "why_public_research_cannot_supply_it": "Feature selection is "
                    "reserved for independent voice governance, and the exclusion "
                    "of pitch and loudness narrows but does not decide the list.",
                },
                {
                    "input": "Whether vowel and sentence tasks are analysed "
                    "separately, since the measured agreement differs between them "
                    "and the one open source distributes combined values.",
                    "why_public_research_cannot_supply_it": "It depends on the "
                    "selected task and on what the source actually contains, which "
                    "is unresolved.",
                },
                {
                    "input": "How many raters hear each recording, whether every "
                    "recording is rated by the full panel, and how blocks of raters "
                    "are balanced.",
                    "why_public_research_cannot_supply_it": "This is a paid "
                    "clinician design decision. The one open source's own "
                    "reliability analysis pooled across blocks without accounting "
                    "for block specific variability, which is the error this input "
                    "exists to avoid.",
                },
            ],
            agreement_and_reliability={
                "statistic_family": "ordinal_or_rating_scale_agreement",
                "form_selection_inputs": [
                    "Whether raters are a fixed panel or a sample drawn from a "
                    "population of qualified raters the claim generalises to.",
                    "Whether the reported unit is one rater or the panel mean, "
                    "which changes the reliability substantially and must be stated.",
                    "Whether the scale is treated as continuous or ordinal.",
                    "Whether the confidence interval on the agreement estimate is "
                    "reported and used for the judgement, rather than the point "
                    "estimate alone.",
                ],
                "reporting_standards": [
                    "grras_reliability_and_agreement_reporting",
                    "icc_form_selection_guidance",
                    "generalisability_theory_multi_facet",
                    "cosmin_measurement_property_guidance",
                ],
                "notes": [
                    "The ceiling here is measured rather than assumed. An "
                    "independent re-rating of a curated subset of the one open "
                    "source by eight speech language pathologists found overall "
                    "severity the most reliable feature, with two raters typically "
                    "differing by roughly twelve to fifteen points on a hundred "
                    "point scale. No automatic measure can be shown to be more "
                    "accurate than the reference it is graded against.",
                    "Pitch and loudness had poor inter-rater reliability in that "
                    "study, so no candidate may be graded against them and the "
                    "existing item 20 pitch primitive gains nothing by this route.",
                    "The common interpretation bands for intraclass correlations "
                    "are a rule of thumb published under a stated design condition "
                    "of roughly thirty heterogeneous samples and at least three "
                    "raters, and their author states that the confidence interval "
                    "rather than the point estimate should decide the level. "
                    "Quoting a band without its interval overstates what is known.",
                ],
            },
            missingness_and_abstention={
                "categories": [
                    "participant_withdrew",
                    "task_not_attempted",
                    "task_attempted_but_invalid",
                    "recording_quality_invalid",
                    "unsupported_context_or_variety",
                    "reference_missing_or_unresolved",
                    "reference_raters_disagreed_beyond_adjudication",
                    "consent_withdrawn_after_collection",
                ],
                "note": "A rater declining to rate a sample is recorded with its "
                "reason. The one open source contains incomplete samples, reading "
                "errors and audible clinician instructions, so unratable material "
                "is an expected category rather than an anomaly.",
            },
            split_and_clustering={
                "cluster_units": ["rater", "prompt_or_stimulus", "site", "repeated_session"],
                "leakage_risks": [
                    "Raters who rate development material learn the sample "
                    "distribution, so rater allocation is part of the split.",
                ],
            },
            subgroup_and_representation=[
                "rater language background and variety familiarity, since the one "
                "open source's re-rating used clinicians rating a variety other "
                "than their own",
                "severity distribution, since the one open source is weighted "
                "toward euphonic and mildly impaired voices",
            ],
            blockers=[
                {
                    "blocker": "Whether the single open candidate distributes "
                    "individual rater rows rather than combined values is "
                    "unresolved, and it decides whether the lane has any usable "
                    "public reference.",
                    "blocker_class": "reference_availability_unresolved",
                },
                {
                    "blocker": "Every other located perceptual source fails for a "
                    "stated reason: a single evaluator, a non commercial licence, "
                    "released consensus values, credentialed access, or no "
                    "perceptual rating at all.",
                    "blocker_class": "reference_evidence_not_lawfully_usable",
                },
            ],
            sample_size={
                "method_candidates": list(RELIABILITY_SAMPLE_SIZE_METHODS),
                "prerequisites": [
                    "A selected feature list, with pitch and loudness excluded.",
                    "A selected task, analysed separately for vowel and sentence "
                    "material.",
                    "A resolved answer on whether individual rater rows exist in "
                    "the one open candidate.",
                    "A paid qualified rater panel and its blocking design.",
                ],
            },
        ),
        _record(
            candidate_id="voice_related_personal_impact",
            title="Voice related personal impact",
            register_lane="voice_functional",
            governance_lane="participant_report",
            related_governance_lanes=["voice"],
            register_row={
                "candidate": "Voice-related personal impact",
                "narrowest_defensible_observation": "Participant's experienced "
                "concern and effect",
                "required_reference": "Participant report and accessible interview",
                "disposition_23a": "Required if voice benefit is pursued; separate "
                "from acoustics",
            },
            observation={
                "what_would_be_measured": "What the person says their voice does "
                "to their life, which is a separate question from how their voice "
                "sounds to a listener or measures on an instrument.",
                "why_it_is_not_yet_a_measure": [
                    "It becomes required only if a voice benefit is pursued, and "
                    "the voice lane is unselected.",
                    "Checkpoint 23A keeps it explicitly separate from acoustics, "
                    "so no acoustic quantity may stand in for it or predict it.",
                    "It is recorded in the participant report lane rather than the "
                    "voice lane precisely so that an acoustic result cannot be "
                    "reported as a personal one.",
                ],
            },
            reference_requirement={
                "truth_class": "personal_truth",
                "substitutions_refused": [
                    "A perceptual severity rating is a listener's judgement and "
                    "not the speaker's experience.",
                    "An acoustic primitive cannot establish concern or effect.",
                ],
                "public_availability": "not_applicable_participant_is_the_source",
                "source_survey_basis": ["voiced_physionet"],
                "consequence": "The survey noted that participant reported "
                "instruments appear in at least one public voice source, and "
                "recorded them as a separate truth class rather than as voice "
                "reference. That separation is preserved here.",
            },
            estimand_shape={
                "question": "What the person reports their voice costs them, and "
                "whether a change in that report is meaningful to them.",
                "unit_of_analysis": "participant",
                "comparison": "The same person against their own earlier report.",
            },
            variance_components_to_separate=[
                "between_participant",
                "within_participant_between_session",
                "current_state_fatigue_or_voice_use",
                "residual_unexplained",
            ],
            required_statistician_inputs=[
                {
                    "input": "The instrument, and evidence that its measurement "
                    "properties were established in a population these "
                    "participants belong to.",
                    "why_public_research_cannot_supply_it": "Instrument selection "
                    "is a governance decision and its transferability is an "
                    "empirical question with no data here.",
                },
                {
                    "input": "The recall window, which determines whether a retest "
                    "interval measures stability or real change.",
                    "why_public_research_cannot_supply_it": "It follows from the "
                    "unselected instrument.",
                },
            ],
            agreement_and_reliability={
                "statistic_family": "not_applicable_no_second_observer",
                "form_selection_inputs": [
                    "There is no second observer. Stability is a test retest "
                    "question over an interval short enough that nothing real "
                    "changed.",
                    "Absolute agreement rather than consistency applies to a "
                    "retest, because a systematic shift between occasions is "
                    "exactly what matters.",
                ],
                "reporting_standards": ["cosmin_measurement_property_guidance"],
                "notes": [
                    "A person's voice concern may change for reasons that have "
                    "nothing to do with their voice, including their situation, "
                    "their audience and their day.",
                ],
            },
            missingness_and_abstention={
                "categories": [
                    "participant_withdrew",
                    "task_not_attempted",
                    "unsupported_context_or_variety",
                    "consent_withdrawn_after_collection",
                ],
                "note": "A declined item is never estimated from the person's "
                "voice.",
            },
            split_and_clustering={
                "cluster_units": ["site", "repeated_session"],
                "leakage_risks": [],
            },
            subgroup_and_representation=[
                "professional voice users, whose reported impact differs for "
                "occupational rather than physiological reasons",
            ],
            blockers=[
                {
                    "blocker": "The voice lane is unselected, and this question "
                    "becomes required only if a voice benefit is pursued.",
                    "blocker_class": "no_task_or_construct_selected",
                },
            ],
            sample_size={
                "method_candidates": [
                    "Test retest reliability sizing, which needs the expected "
                    "reliability, the retest interval and the desired confidence "
                    "interval width. Bonett, D. G. Sample size requirements for "
                    "estimating intraclass correlations with desired precision. "
                    "Statistics in Medicine, 2002, doi:10.1002/sim.1108. Primary "
                    "text not opened here.",
                ],
                "prerequisites": [
                    "A selected instrument reviewed with people who have lived "
                    "experience.",
                    "An ethics approved route to ask participants anything.",
                ],
            },
        ),
        _record(
            candidate_id="maximum_phonation_time",
            title="Maximum phonation time",
            register_lane="endurance",
            governance_lane="voice",
            related_governance_lanes=["motor_speech"],
            register_row={
                "candidate": "Maximum phonation time",
                "narrowest_defensible_observation": "Duration sustained in a "
                "frozen repeated protocol",
                "required_reference": "Repeated timed attempts and explicit "
                "validity and stop rules",
                "disposition_23a": "Low priority and not a standalone screen",
            },
            observation={
                "what_would_be_measured": "How long a person sustains a sound "
                "under a fixed protocol, with explicit rules for when an attempt "
                "counts and when it stops.",
                "why_it_is_not_yet_a_measure": [
                    "Checkpoint 23A marks it low priority and explicitly not a "
                    "standalone screen.",
                    "It is a maximum effort task, so it measures effort, technique "
                    "and willingness as much as capacity, and repeating it fatigues "
                    "the thing being measured.",
                    "The existing product decisions already record comfortable "
                    "sound probes as optional research only, and this task is more "
                    "demanding than those.",
                ],
            },
            reference_requirement={
                "truth_class": "task_fidelity",
                "substitutions_refused": [
                    "Elapsed file duration is not a sustained phonation duration.",
                    "A single best attempt is not a repeated protocol result.",
                ],
                "public_availability": "not_applicable_computational_truth",
                "source_survey_basis": [],
                "consequence": "The measurement is a duration under stated stop "
                "rules, so its truth is task fidelity and computational rather "
                "than an external human reference. That makes it cheap to verify "
                "and does not make it worth doing.",
            },
            estimand_shape={
                "question": "How much a person's sustained duration varies across "
                "attempts and sessions under a fixed protocol, and how much of that "
                "variation is effort and technique rather than capacity.",
                "unit_of_analysis": "participant_by_attempt",
                "comparison": "The same person against themselves across repeated "
                "attempts and sessions.",
            },
            variance_components_to_separate=[
                "between_participant",
                "within_participant_between_session",
                "within_session_between_attempt",
                "practice_or_order_effect",
                "current_state_fatigue_or_voice_use",
                "between_device",
                "residual_unexplained",
            ],
            required_statistician_inputs=[
                {
                    "input": "The number of attempts, the rest interval between "
                    "them and whether the reported value is the best, the mean or "
                    "the last attempt.",
                    "why_public_research_cannot_supply_it": "Each choice measures "
                    "a different thing, and the protocol is unreviewed.",
                },
                {
                    "input": "The stop rule and the validity rule, which decide "
                    "when an attempt is counted at all.",
                    "why_public_research_cannot_supply_it": "These are safety and "
                    "burden decisions needing professional review.",
                },
            ],
            agreement_and_reliability={
                "statistic_family": "continuous_agreement",
                "form_selection_inputs": [
                    "Whether the reported unit is a single attempt or a summary "
                    "across attempts.",
                    "Whether practice and fatigue are modelled as an order effect "
                    "rather than pooled into error.",
                ],
                "reporting_standards": [
                    "grras_reliability_and_agreement_reporting",
                    "icc_form_selection_guidance",
                    "limits_of_agreement",
                ],
                "notes": [
                    "A maximum performance task cannot be repeated freely, so the "
                    "usual advice to add repetitions to improve reliability works "
                    "against the measurement itself.",
                ],
            },
            missingness_and_abstention={
                "categories": [
                    "participant_withdrew",
                    "task_not_attempted",
                    "task_attempted_but_invalid",
                    "recording_quality_invalid",
                    "algorithm_abstained",
                    "consent_withdrawn_after_collection",
                ],
                "note": "A participant stopping early is a valid and expected "
                "outcome, never a poor result.",
            },
            split_and_clustering={
                "cluster_units": ["repeated_session", "device", "site"],
                "leakage_risks": [],
            },
            subgroup_and_representation=[
                "adults with respiratory conditions, for whom the task carries a "
                "different burden and a different meaning",
            ],
            blockers=[
                {
                    "blocker": "Checkpoint 23A ranks this low priority and rules "
                    "out its use as a standalone screen, so it would need a reason "
                    "to exist beyond being easy to measure.",
                    "blocker_class": "no_task_or_construct_selected",
                },
            ],
            sample_size={
                "method_candidates": list(RELIABILITY_SAMPLE_SIZE_METHODS),
                "prerequisites": [
                    "A reviewed protocol with stop and validity rules.",
                    "A pilot estimate of attempt to attempt variation.",
                ],
            },
        ),
    ]
)

ACOUSTIC_ARTICULATION_CONSTRUCTS = [
    _record(
        candidate_id="acoustic_articulation_properties",
        title="Acoustic articulation properties",
        register_lane="acoustic_articulation",
        governance_lane="unassigned_requires_governance",
        related_governance_lanes=["motor_speech", "general_speech"],
        register_row={
            "candidate": "Formant trajectories, vowel dispersion, VOT, segment "
            "duration or F2 transitions",
            "narrowest_defensible_observation": "Named acoustic property in a "
            "named phonetic context",
            "required_reference": "Human phonetic boundaries; direct movement "
            "evidence if movement is claimed",
            "disposition_23a": "Deferred; high variety, anatomy, task and item 22 "
            "overlap",
        },
        observation={
            "what_would_be_measured": "A named acoustic property measured in a "
            "named phonetic context, such as the time between a stop release and "
            "voicing onset.",
            "why_it_is_not_yet_a_measure": [
                "Checkpoint 23A defers it, and this record does not assign it to a "
                "governance lane because the register row does not map onto exactly "
                "one. An agent may not make that assignment.",
                "These properties vary strongly with language variety and with "
                "anatomy, which is the same confound item 22 measured directly "
                "when an American reference flagged Australian rhotic and t "
                "productions more often.",
                "If movement is claimed, acoustics alone cannot establish it. "
                "Direct movement evidence would be required, and that is a "
                "different kind of study entirely.",
                "It overlaps item 22 substantially, and item 22 material is not "
                "reusable by default.",
            ],
        },
        reference_requirement={
            "truth_class": "timing_and_boundary_truth",
            "substitutions_refused": [
                "An automatic aligner's boundaries cannot check an automatic "
                "aligner's boundaries.",
                "A pronunciation lexicon proposes how a word may be said and never "
                "observes how anybody said it, which item 22 recorded explicitly.",
                "An acoustic measurement cannot substitute for movement evidence "
                "when a movement claim is made.",
            ],
            "public_availability": "not_surveyed_public_availability_unknown",
            "source_survey_basis": [],
            "consequence": "Human phonetic boundary reference was outside the "
            "source survey's three lanes. Item 22 separately established that the "
            "whole field of English corpora with expert phone level annotation is "
            "nine datasets, of which one is commercially usable here, so the "
            "supply of this kind of reference is known to be thin even though it "
            "was not surveyed for item 23.",
        },
        estimand_shape={
            "question": "How closely automatic phonetic boundary placement matches "
            "human placement in a named context, and how stable the derived "
            "acoustic property is within a person.",
            "unit_of_analysis": "recording",
            "comparison": "Algorithm boundaries against human phonetic boundaries "
            "in the same named context.",
        },
        variance_components_to_separate=[
            "between_participant",
            "within_participant_between_session",
            "between_rater",
            "between_prompt_or_stimulus",
            "between_device",
            "algorithm_or_model_version",
            "residual_unexplained",
        ],
        required_statistician_inputs=[
            {
                "input": "The named property and the named phonetic context, since "
                "the property is meaningless without the context.",
                "why_public_research_cannot_supply_it": "Both are deferred, and "
                "choosing them would be selecting the construct.",
            },
            {
                "input": "How variety is handled, given that a variety mismatch may "
                "be excluded but never subtracted.",
                "why_public_research_cannot_supply_it": "It needs expertly "
                "labelled Australian speech that this repository has established "
                "does not exist in public.",
            },
        ],
        agreement_and_reliability={
            "statistic_family": "continuous_agreement",
            "form_selection_inputs": [
                "Whether agreement is reported on the boundary positions or on the "
                "derived property, since the two can disagree.",
                "Whether human labellers are a fixed panel or a sample.",
            ],
            "reporting_standards": [
                "grras_reliability_and_agreement_reporting",
                "icc_form_selection_guidance",
                "limits_of_agreement",
            ],
            "notes": [
                "Where varieties legitimately differ, the opportunity is "
                "unscorable rather than wrong. Where they agree, a model may raise "
                "a candidate for human review and never a finding.",
            ],
        },
        missingness_and_abstention={
            "categories": [
                "participant_withdrew",
                "task_not_attempted",
                "task_attempted_but_invalid",
                "recording_quality_invalid",
                "unsupported_context_or_variety",
                "reference_missing_or_unresolved",
                "algorithm_abstained",
                "consent_withdrawn_after_collection",
            ],
            "note": "An unsupported variety produces an unscorable opportunity "
            "with a reason, never a default or corrected value.",
        },
        split_and_clustering={
            "cluster_units": ["site", "device", "prompt_or_stimulus", "rater", "repeated_session"],
            "leakage_risks": [
                "Item 22 participants and material overlap this question directly, "
                "so the overlap register applies before any use.",
            ],
        },
        subgroup_and_representation=[
            "Australian English varieties, which no public source carries with any "
            "of the three item 23 truth classes",
        ],
        blockers=[
            {
                "blocker": "The register defers this question and it is not "
                "assigned to a governance lane, so nobody currently owns the "
                "decision.",
                "blocker_class": "no_task_or_construct_selected",
            },
            {
                "blocker": "Australian variety reference for this kind of property "
                "does not exist in public, which item 22 established rather than "
                "assumed.",
                "blocker_class": "no_reference_evidence_exists",
            },
        ],
        sample_size={
            "method_candidates": list(RELIABILITY_SAMPLE_SIZE_METHODS),
            "prerequisites": [
                "A named acoustic property and a named phonetic context.",
                "A variety handling rule that excludes rather than subtracts.",
                "A resolved item 22 overlap decision.",
            ],
        },
    ),
]

ALL_CONSTRUCTS = (
    MOTOR_TASK_CONSTRUCTS
    + GENERAL_SPEECH_CONSTRUCTS
    + FUNCTIONAL_CONSTRUCTS
    + PERSONAL_CONSTRUCTS
    + VOICE_CONSTRUCTS
    + ACOUSTIC_ARTICULATION_CONSTRUCTS
)


# Facts about method that belong to the package rather than to one construct.
METHOD_NOTES = [
    "There are two different standard error of measurement formulas in the "
    "literature and they are not interchangeable. One is reliability based, "
    "computed as the sample standard deviation multiplied by the square root of "
    "one minus the reliability, and it moves with how heterogeneous the sample "
    "is. The other is agreement based and is the within-subject standard "
    "deviation, estimated as the square root of the residual mean square from a "
    "one-way analysis of variance, and it is in the units of the measurement. "
    "Which one a study uses must be stated as an input, because the same data "
    "yields different numbers. de Vet, H. C. W. et al. Minimal changes in health "
    "status questionnaires. Health and Quality of Life Outcomes, 2006, "
    "doi:10.1186/1477-7525-4-54, and Bland, J. M. and Altman, D. G. Statistics "
    "notes: measurement error. BMJ, 1996, doi:10.1136/bmj.312.7047.1654. Both "
    "read at source.",
    "The smallest detectable change is one point nine six multiplied by the "
    "square root of two multiplied by the standard error of measurement, where "
    "the square root of two appears because a change involves two measurements. "
    "Expressed through the within-subject standard deviation the same quantity is "
    "two point seven seven times that standard deviation. Reporting a change "
    "smaller than this as real is a measurement error, not a finding.",
    "The familiar intraclass correlation interpretation bands, poor below zero "
    "point five, moderate to zero point seven five, good to zero point nine and "
    "excellent above it, are a rule of thumb published under a stated design "
    "condition of roughly thirty heterogeneous samples and at least three raters. "
    "Their authors state that there are no standard values for acceptable "
    "reliability, that a low value can reflect a homogeneous sample rather than "
    "poor agreement, and that the confidence interval rather than the point "
    "estimate should decide the level. Koo, T. K. and Li, M. Y. Journal of "
    "Chiropractic Medicine, 2016, doi:10.1016/j.jcm.2016.02.012, read at source. "
    "This matters here because the repository already quotes those bands when "
    "reporting the one open perceptual voice source's agreement ceiling.",
    "The reliability and agreement reporting checklist requires a study to "
    "explain how its sample size was chosen and to state the number of raters, "
    "participants and replicate observations. That requirement is the reason this "
    "package exists: the explanation has to be constructible, and today it is "
    "not. Kottner, J. et al. Guidelines for Reporting Reliability and Agreement "
    "Studies. Journal of Clinical Epidemiology, 2011, "
    "doi:10.1016/j.jclinepi.2010.03.002; checklist read at source through the "
    "EQUATOR network reproduction of its table, the article itself not opened.",
    "Diagnostic accuracy reporting applies only if a study frames a measure as a "
    "classification test against a reference standard. No item 23 question is "
    "framed that way, and none may be without a separate approved checkpoint. "
    "Bossuyt, P. M. et al. STARD 2015. BMJ, 2015, doi:10.1136/bmj.h5527.",
    "A single intraclass correlation computed across raters treats variation that "
    "replicates across raters, such as occasion to occasion variation, as true "
    "signal. Where a design has more than one facet, generalisability theory "
    "estimates the components separately and its decision study is the principled "
    "way to ask how many raters or listeners a planned design needs. It requires "
    "variance components measured in an earlier study as input, so it does not "
    "escape the pilot requirement. Lakes, K. D. and Hoyt, W. T. Journal of "
    "Clinical Child and Adolescent Psychology, 2009, "
    "doi:10.1080/15374410802575461, read at source.",
]

LANE_SUMMARIES = {
    "motor_speech": {
        "questions": ["rapid_syllable_timing", "rapid_syllable_task_accuracy"],
        "reference_position": "No qualifying public source exists at any licence "
        "and at any price.",
        "consequence": "Both questions depend entirely on prospective collection "
        "with recruited participants and paid trained annotators. No public "
        "shortcut exists and no partial one does either.",
    },
    "general_speech": {
        "questions": ["articulation_rate", "speech_rate_and_pause_profile"],
        "reference_position": "Not surveyed. Whether human reviewed boundary "
        "reference is publicly obtainable is unknown.",
        "consequence": "The availability question is open rather than answered, "
        "and an open question is not an encouraging one.",
    },
    "voice": {
        "questions": [
            "item_20_voice_acoustic_primitives",
            "voice_perceptual_judgement",
            "maximum_phonation_time",
        ],
        "reference_position": "Exactly one open perceptual candidate, with a "
        "measured agreement ceiling and one unresolved question about whether it "
        "distributes individual rater rows.",
        "consequence": "Perceptual work is bounded by ordinary clinician "
        "disagreement before any code is written, and pitch and loudness are "
        "excluded outright. The acoustic and endurance questions need no external "
        "human reference and are limited by the absence of a selected construct "
        "rather than by data.",
    },
    "controlled_intelligibility": {
        "questions": ["controlled_intelligibility", "comprehensibility_or_effort"],
        "reference_position": "Sources of the right shape exist and none is "
        "lawfully usable here.",
        "consequence": "The largest is blocked by a data use agreement needing an "
        "organisational countersignature rather than by its commercial terms, "
        "which is the missing legal entity blocking a route concretely.",
    },
    "participant_report": {
        "questions": [
            "communication_impact_and_desired_change",
            "voice_related_personal_impact",
        ],
        "reference_position": "Not applicable. The participant is the only valid "
        "source.",
        "consequence": "No dataset can supply this, so it depends on the same "
        "ethics and consent route as every other lane and can never be inferred "
        "from speech.",
    },
    "clinical_or_laryngeal_reference": {
        "questions": [],
        "reference_position": "Not required, because no clinical or pathology "
        "claim is proposed.",
        "consequence": "It becomes mandatory only if governance ever permits a "
        "claim requiring medical or laryngeal evidence, and no question in this "
        "package proposes one.",
    },
    "unassigned_requires_governance": {
        "questions": ["acoustic_articulation_properties"],
        "reference_position": "Not surveyed, and item 22 separately established "
        "that English corpora with expert phone level annotation are scarce.",
        "consequence": "The register row does not map onto exactly one governance "
        "lane, so nobody currently owns the decision. An agent may not assign it.",
    },
}

WHAT_THIS_IS_NOT = [
    "It is not a statistical plan. A plan is prospectively reviewed by an "
    "independent statistician against a selected construct and pilot variance, "
    "and none of those exists.",
    "It is not a selection. No construct, task, estimand, statistic, threshold or "
    "design is chosen, and the schema cannot express a choice.",
    "It is not a sample size calculation, and no record can contain one.",
    "It is not evidence that any of these questions is worth asking. The "
    "governance group may reject the entire construct register.",
    "It is not progress toward checkpoint 23B acceptance, which is defined as "
    "written review by accountable human roles.",
]

LIMITATIONS = [
    "The construct register this package expands may be narrowed or rejected in "
    "full, in which case some of these records describe questions that will never "
    "be asked.",
    "Reporting standards cited here were read at source where the source is open "
    "access. Several sample size methods sit behind paywalls; their required "
    "inputs are recorded from open implementations and restatements, and each "
    "citation says so. A paywalled formula transcribed by a third party is a "
    "lead, not a verified equation.",
    "Naming a variance component does not mean a design can separate it. Some "
    "components are confounded in any practical study, and saying which ones is "
    "part of what the statistician is for.",
    "Every input list here is a minimum. A statistician reviewing a real protocol "
    "will ask for things nobody thought of yet.",
]


def build_registry(records):
    lanes = {}
    availability = {}
    for record in records:
        lanes[record["governance_lane"]] = lanes.get(record["governance_lane"], 0) + 1
        key = record["reference_requirement"]["public_availability"]
        availability[key] = availability.get(key, 0) + 1
    return {
        "schema_version": "1.0.0",
        "registry_id": "motor_speech_voice_measurement_plan_v1",
        "checkpoint": "23B",
        "prepared_at": PREPARED_AT,
        "status": "measurement_inputs_recorded_nothing_selected",
        "record_schema": SCHEMA_FILENAME,
        "purpose": "To record, once per provisional construct, the inputs an "
        "independent statistician would need before a study could be designed. It "
        "selects nothing and computes nothing.",
        "record_count": len(records),
        "records": [
            {
                "candidate_id": record["candidate_id"],
                "record_id": record["record_id"],
                "register_lane": record["register_lane"],
                "governance_lane": record["governance_lane"],
                "public_availability": record["reference_requirement"][
                    "public_availability"
                ],
            }
            for record in records
        ],
        "counts": {
            "constructs_recorded": len(records),
            "by_governance_lane": lanes,
            "by_reference_availability": availability,
            "selected": 0,
            "sample_sizes_computed": 0,
            "thresholds_recorded": 0,
        },
        "lane_summaries": LANE_SUMMARIES,
        "method_notes": METHOD_NOTES,
        "what_this_is_not": WHAT_THIS_IS_NOT,
        "limitations": LIMITATIONS,
    }


def write_plan():
    PLAN_ROOT.mkdir(parents=True, exist_ok=True)
    for record in ALL_CONSTRUCTS:
        path = PLAN_ROOT / f"{record['candidate_id']}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    registry_path = PLAN_ROOT / REGISTRY_FILENAME
    registry_path.write_text(
        json.dumps(build_registry(ALL_CONSTRUCTS), indent=2, ensure_ascii=False) + "\n"
    )
    return len(ALL_CONSTRUCTS)


def main():
    written = write_plan()
    print(f"Wrote {written} measurement input records and the registry.")
    print("No construct, statistic, threshold or sample size is selected.")


if __name__ == "__main__":
    main()
