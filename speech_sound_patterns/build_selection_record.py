"""Write the committed checkpoint 22E5 selection and rejection record.

The written verdicts and reasons live in this module, so changing one is a code
change that a reviewer can see. Every number in the record is read from the
committed evidence instead of being retyped: gate outcomes come from the powered
comparison, lane roles and blockers come from the provider register, and both
are pinned by hash so a later edit to either makes the record invalid.

Each issued version is rebuilt from the register it was written against, so a
rebuild reproduces the committed file byte for byte or the evidence changed.

    python3 -m speech_sound_patterns.build_selection_record
    python3 -m speech_sound_patterns.build_selection_record --record-version 1.0.0
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .comparison import (
    CANDIDATE_PROFILES,
    FROZEN_SELECTION_GATES,
    comparison_profile,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes
from .provider_register import (
    REGISTER_PATH,
    assert_historical_register,
    assert_valid_register,
)
from .selection_record import (
    ACTIVE_SELECTION_VERSION,
    BASELINE_GATE_CHECKS_PASSED_OF_TEN,
    LANE_DECISION_PROFILES,
    RECORD_STATUS,
    SELECTION_SCHEMA_VERSION,
    SELECTION_VERSIONS,
    SelectionRecordError,
    assert_valid_selection_record,
    evidence_pins,
    gate_eligible_lane_ids,
    selection_profile,
)

PURPOSE = (
    "Record what was decided about every checkpoint 22E lane after two frozen "
    "comparisons, including why, what it would cost, what it is not allowed to "
    "do, and what would have to change before it could be reconsidered. This "
    "record closes the search for a pronunciation concern detector. It selects "
    "nothing, releases nothing and changes no pipeline behaviour."
)

# What each later version of the record adds to that purpose. The decision does
# not change, so the statement of it does not either; only the account of which
# evidence the record was written against.
PURPOSE_SUFFIXES = {
    "1.1.0": (
        " Restated at checkpoint 22E6 against the corrected provider register. "
        "No verdict moved. The Bookbot lane's reason changed from an "
        "undocumented Australian training source to a disproved one, because "
        "WikiPron defines no Australian English dialect and the named dataset "
        "does not exist."
    ),
}

DECISION_REASON = (
    "No lane passed every unchanged gate on both partitions, in two frozen "
    "comparisons, the second of which used every non held out adult in the "
    "corpus. An exploratory analysis scored each of the five original expert "
    "reviewers as though the reviewer were the candidate system, and three of "
    "the five pass every gate on both partitions, which suggests the gates sit "
    "at roughly competent human level rather than being unreachable. That "
    "analysis is context rather than committed evidence, and no gate was moved "
    "on the strength of it in either direction. The strongest "
    "candidate is this project's own segmentation free GOP, which held "
    "development precision at 0.751 against the 0.75 minimum and missed "
    "development recall at 0.189 against the 0.200 minimum, while its threshold "
    "tuning precision fell to 0.622. No paid external provider added anything "
    "the free local stack had not already provided. This completes checkpoint "
    "22E honestly. It does not authorise more threshold searching, a weaker "
    "gate, a larger slice of the same corpus or an early look at the held out "
    "participants."
)

CARRIED_FORWARD = [
    "the five selection gates, unchanged, for any future comparison",
    "the ARPAbet to IPA phone map and the expert consensus rule, both proven to "
    "reproduce the committed checkpoint 22D relation rows exactly",
    "the participant exclusive split assignments, including the 26 sealed held "
    "out adults",
    "both frozen comparison contracts and reports, and the powered sample "
    "contract, as unedited historical records",
    "the corpus manifests, licence evidence and the corpus to provider transfer "
    "review",
    "the provider register and its fail closed upload gate",
    "the segmentation free GOP implementation and the pinned POWSM and "
    "CommonPhone environments, as developer research code only",
]

NOT_CARRIED_FORWARD = [
    "any operating point, threshold or score cut off; none was selected and none "
    "may be reused",
    "any expected to produced phone mapping proposed by a candidate system",
    "any provider configuration, locale or request setting as a selected "
    "configuration",
    "any claim that a candidate is accurate enough for a user facing output",
    "the checkpoint 22E4 near miss, which the powered replication did not "
    "reproduce",
]

LIMITATIONS = [
    "Everything measured in checkpoints 22E4 and 22E4B rests on SpeechOcean762, "
    "which is Mandarin first language read speech assessed against American "
    "English. No result transfers to Australian speakers, and the sample cannot "
    "be enlarged again without unsealing the held out set reserved for "
    "checkpoint 22H.",
    "No external lane can supply Australian variety exact relation evidence. "
    "That is now demonstrated rather than inferred: across the powered adult set "
    "Azure en-AU named zero of 44,335 phone positions while en-US named 42,903 "
    "of 42,903.",
    "Australian adult and child phone labelled evidence does not exist in this "
    "project. ANDOSL or an equivalent expertly labelled Australian set, and "
    "AusKidTalk for children, are the identified acquisition routes and neither "
    "has been obtained.",
    "Child evidence remains far too thin for any estimate: two positive "
    "development opportunities and four positive tuning opportunities. No child "
    "row entered a gate or a threshold, so no verdict in this record is a child "
    "verdict.",
    "A portion of every error measured is reviewer disagreement rather than "
    "candidate error. Fleiss kappa across the five expert reviewers is 0.566 for "
    "development adults and 0.520 for tuning adults.",
    "This record decides roles in a benchmark. It releases no detector, score, "
    "coaching output or product behaviour, and the ordinary pipeline is "
    "unchanged by it.",
    "The powered comparison report originally described this checkpoint's Azure "
    "monetary cost as free F0, which understated it: the Australia East resource "
    "had been moved to standard S0 before that run, at a cost of about A$14. On "
    "2026-07-28 the owner directed that the report be corrected rather than "
    "annotated, so the summariser now carries a per comparison cost and the "
    "powered report was regenerated. That regeneration changed one field and "
    "nothing else, which is checkable: the report rebuilds byte for byte from "
    "the unchanged private evidence, and the checkpoint 22E4 report still "
    "rebuilds byte for byte with its original free F0 wording, which was "
    "accurate for its 240 clip volume.",
]

LANE_RECORDS = {
    "azure_speech": {
        "reason": (
            "Measured on every non held out adult and rejected for this role on "
            "its own numbers. The en-US per phone accuracy score is the nominally "
            "strongest candidate in the powered comparison at eight of ten "
            "checks, but its precision point estimate is flat and clearly short "
            "of the 0.75 minimum on both partitions, 0.703 on development and "
            "0.679 on threshold tuning, and every point of its apparent "
            "improvement over checkpoint 22E4 came from the Wilson lower bound "
            "rising with the sample rather than from better decisions. The en-US "
            "named relation path reached four of ten. The en-AU locale produced "
            "no scorable evidence at all, so an Australian score can never be "
            "attached to a known target. This rejects the lane for the "
            "pronunciation concern role only; the resource, credential and "
            "transfer review remain valid and unused."
        ),
        "incremental_value": (
            "None. The checkpoint 22D local baseline reached nine of ten checks "
            "at its closest point and still selected nothing, while the strongest "
            "Azure candidate reached eight of ten with a stable precision "
            "failure. A paid external provider added no evidence the free local "
            "stack had not already provided."
        ),
        "limitations": {
            "cost": (
                "The Australia East resource was moved from the free F0 tier to "
                "standard S0 before the powered run, because F0 allows five audio "
                "hours a month and the run needed 9.72. The run cost about A$14 "
                "at the A$1.4492 standard rate against A$289.83 of remaining "
                "account credit. The owner has chosen on 2026-07-28 to leave the "
                "resource on S0, so any future run carries a per audio hour "
                "charge and the resource stays billable in principle."
            ),
            "privacy": (
                "Australian region processing, with no documented retention for "
                "real time pronunciation assessment and no documented training "
                "use. That is an absence of a documented use rather than a "
                "contractual exclusion. Only public corpus clip audio and the "
                "intended reference text were transmitted; no child clip, held "
                "out clip, Australian Common Voice clip or owner recording ever "
                "left this machine."
            ),
            "legal": (
                "Public Microsoft Online Services terms permit comparative "
                "benchmarking and aggregate publication, so nothing legal blocks "
                "this lane. Every upload stayed gated by the corpus to provider "
                "transfer review, at version 1.2.0 for the powered volume."
            ),
            "operational": (
                "Eight thousand one hundred and sixty requests, all HTTP 200 with "
                "no retry. One en-US configuration of 4,080 returned different "
                "content for a byte identical repeated request, so that clip's "
                "sixteen targets abstain under the contract's zero numeric "
                "tolerance. A remote lane also makes the developer artifact "
                "depend on a network and on a vendor model with no version "
                "number."
            ),
            "australian_variety": (
                "This is the lane where the Australian limitation was "
                "demonstrated. en-AU returns real Australian calibrated accuracy "
                "scores but emits every phone name as an empty string, so it "
                "cannot say which sound was produced, and en-US names phones only "
                "against a General American target. No Azure configuration can "
                "supply Australian variety exact relation evidence."
            ),
            "child_and_adult": (
                "No child clip was transmitted, by rule. The gates are adult only "
                "and this lane carries no child evidence of any kind."
            ),
        },
        "reopen_requires": [
            "a Microsoft locale change that names phones in en-AU, verified on "
            "real responses",
            "a materially different task, such as the controlled prompt pack in "
            "checkpoint 22F, followed by a new frozen comparison under the same "
            "unchanged gates",
            "an explicit owner decision to spend again",
        ],
    },
    "elsa_scripted_v3": {
        "reason": (
            "Never ran and never received audio. Its documented substituted phone "
            "field remains the strongest produced phone field found in any "
            "external product, so the lane stays open rather than rejected, but a "
            "token requires a signed NDA, the master services agreement makes "
            "benchmark publication a negotiated written permission rather than a "
            "default right, and the access and permissions enquiry drafted at "
            "checkpoint 22E3 had still not been sent or answered as at "
            "2026-07-28. Nothing about this lane has been measured, so nothing "
            "about it may be concluded."
        ),
        "incremental_value": (
            "Unknown and unmeasured. Its potential value is that it is the only "
            "external lane documented to name the substituted phone, which is "
            "exactly what Azure en-AU cannot do. Its actual value is zero until "
            "written permission exists."
        ),
        "limitations": {
            "cost": (
                "Unknown. No pricing was obtained, because access begins with an "
                "NDA rather than a signup."
            ),
            "privacy": (
                "Processing in Singapore, Ireland or US East with no Australian "
                "region, open ended retention described only as as long as ELSA "
                "deems reasonably necessary, and aggregate anonymised usage data "
                "permitted for product and machine learning improvement. That "
                "combination would need its own decision before any transfer and "
                "would never be acceptable for owner recordings."
            ),
            "legal": (
                "Written benchmark and aggregate publication permission is "
                "required and does not exist. The corpus to provider transfer "
                "review permits this lane no audio, so the register's upload gate "
                "fails closed."
            ),
            "operational": (
                "Deletion and insertion semantics are undocumented and no public "
                "worked example of the error fields exists, so even with a token "
                "the response shape would need its own smoke test before any "
                "comparison."
            ),
            "australian_variety": (
                "No Australian English model is documented anywhere in the public "
                "material. The reference is General American, so this lane could "
                "not supply Australian variety evidence either."
            ),
            "child_and_adult": (
                "No child provision is documented, and no child audio would be "
                "sent in any case."
            ),
        },
        "reopen_requires": [
            "Adam to send the drafted access and permissions enquiry",
            "written benchmark and aggregate publication permission",
            "written region, retention, deletion and training use answers",
            "one real response demonstrating the substitution, deletion and "
            "insertion behaviour",
            "a new corpus to provider transfer review decision before any audio",
        ],
    },
    "iflytek_ise_global": {
        "reason": (
            "Rejected because Adam declined the lane on 2026-07-25, before any "
            "audio was sent anywhere. The recorded engineering concerns stand "
            "independently: the English response flags a replacement without ever "
            "naming the produced phone, the adult and pupil switch is documented "
            "for Chinese tasks only, and the privacy promises are not practically "
            "auditable. The account, free quota and verified credential still "
            "exist, so this is an owner decision that can be revisited rather "
            "than a technical impossibility."
        ),
        "incremental_value": (
            "None, and none was sought. The lane received no audio, so it "
            "contributed nothing to either comparison."
        ),
        "limitations": {
            "cost": (
                "One hundred thousand free calls were granted until 2026-10-22 "
                "and were never used, with roughly 0.003 US dollars per call "
                "afterwards. Cost was never the obstacle."
            ),
            "privacy": (
                "Singapore processing with lawful transfer out and affiliate "
                "sharing permitted, a one week retention claim that cannot be "
                "independently audited, and a policy permitting use for "
                "continuous product development with no explicit exclusion."
            ),
            "legal": (
                "The platform agreement does not prohibit benchmarking, but the "
                "vendor remains on the United States Entity List, which is "
                "recorded as reputational exposure rather than a legal bar on "
                "using the service."
            ),
            "operational": (
                "The English phoneme layer returns error flags rather than a "
                "produced phone, so it could only ever have supplied error type "
                "agreement, never exact relation evidence."
            ),
            "australian_variety": (
                "No Australian English model or locale is offered."
            ),
            "child_and_adult": (
                "The documented child and adult group switch applies to Chinese "
                "tasks only, so the child capability that made this lane "
                "interesting does not exist for English."
            ),
        },
        "reopen_requires": [
            "a new explicit owner decision to reopen the lane",
        ],
    },
    "segmentation_free_gop": {
        "reason": (
            "This project's own clean implementation of the published "
            "segmentation free equations, and the strongest candidate in both "
            "frozen comparisons. It is not selected: on the powered sample it "
            "holds development precision at 0.751 against the 0.75 minimum but "
            "misses development recall at 0.189 against the 0.200 minimum, and "
            "its threshold tuning precision falls to 0.622. It keeps a research "
            "only role rather than a rejection because it is free, local, "
            "deterministic, carries no licence or provenance risk, failed by the "
            "smallest margin of any lane, and is the obvious thing to retest "
            "under the narrower controlled task that checkpoint 22F creates. "
            "Research only means developer engineering evidence and nothing "
            "else: no threshold is selected, no operating point is frozen, and no "
            "output may reach a person."
        ),
        "incremental_value": (
            "Small, and negative against the local baseline. The checkpoint 22D "
            "repair reached nine of ten checks at its closest point; this reached "
            "eight of ten at checkpoint 22E4 and seven of ten on the powered "
            "sample. It did repair the weakness it was built for, since it no "
            "longer depends on forced phone boundaries, but that repair did not "
            "carry it past the gates."
        ),
        "limitations": {
            "cost": (
                "None. It runs on this machine with no network access and no "
                "charge."
            ),
            "privacy": (
                "None beyond ordinary local file handling. No audio leaves the "
                "machine."
            ),
            "legal": (
                "The published method is CC BY 4.0 and the underlying Meta phone "
                "model is Apache 2.0, so an independent implementation is "
                "permitted. The authors' own repository carries no code licence "
                "and was not copied, and the SpeechOcean trained regression head "
                "is excluded."
            ),
            "operational": (
                "About 1.8 times real time across all repeats with a peak of "
                "roughly 2.0 gigabytes, and repeats were exact. It needs an "
                "expected phone sequence, so it cannot run on a source without a "
                "pronunciation lexicon, which is why it produced no secondary "
                "source evidence."
            ),
            "australian_variety": (
                "It was measured only on Mandarin first language read speech "
                "scored against American English. It carries no Australian "
                "evidence, and the underlying model's targets are not Australian."
            ),
            "child_and_adult": (
                "Children contributed two positive development opportunities and "
                "four positive tuning opportunities, far too few for any child "
                "estimate. No child row entered a gate or a threshold."
            ),
        },
        "reopen_requires": [
            "a materially narrower task, such as the controlled prompt pack in "
            "checkpoint 22F, followed by a new frozen comparison under the same "
            "unchanged gates",
            "expertly labelled evidence in a second variety before any Australian "
            "claim",
        ],
    },
    "powsm": {
        "reason": (
            "Rejected on measured evidence. The free phone relation path reached "
            "four of ten checks on both the first and the powered comparison, "
            "with high recall and very poor precision: its false concern rate ran "
            "at roughly twenty times the permitted maximum. The failure is "
            "structural rather than a tuning miss, because an unconstrained phone "
            "sequence cannot be conditioned on the expected phone, so a "
            "legitimate variant reads as a concern. Its licence, pinned revision, "
            "audited environment and measured runtime remain valid work and are "
            "recorded, but this lane is not a detector for this task."
        ),
        "incremental_value": (
            "None. It falls far below the checkpoint 22D local baseline of nine "
            "of ten checks, and it fails in the same direction as the checkpoint "
            "22D relation path it was meant to replace."
        ),
        "limitations": {
            "cost": "None. It runs locally at no charge.",
            "privacy": "None. No audio leaves the machine.",
            "legal": (
                "The released weights carry an explicit CC BY 4.0 licence, which "
                "is why this lane was core rather than conditional. Agreement "
                "with ZIPA could never be independent confirmation, because both "
                "derive from the IPAPack++ family."
            ),
            "operational": (
                "The pinned checkpoint declares a twenty second input length and "
                "one clip in the powered sample is 20.408 seconds, so that clip "
                "is recorded as unprocessable for this lane and its nineteen "
                "targets abstain there alone. Truncating would have dropped real "
                "speech and invented deletion concerns. Roughly 1.4 times real "
                "time with a peak of about 3.0 gigabytes."
            ),
            "australian_variety": (
                "Its training labels are grapheme to phoneme derived and biased "
                "toward canonical pronunciations, so it carries no Australian "
                "variety evidence and would systematically flag legitimate "
                "variants."
            ),
            "child_and_adult": (
                "The child sample is far too small to support any estimate, and "
                "no child row entered a gate."
            ),
        },
        "reopen_requires": [
            "a different task in which an unconstrained phone sequence is "
            "compared against a properly licensed accepted variant set rather "
            "than a single expected phone",
            "a new frozen comparison under the same unchanged gates",
        ],
    },
    "zipa": {
        "reason": (
            "Never loaded and never run. The code is MIT and the four weight "
            "repositories now carry apache-2.0 tags, but no model card licence "
            "statement or training provenance bundle exists for the exact "
            "checkpoints, and a licence tag alone is not a provenance record. The "
            "author enquiry had not been answered as at 2026-07-28. Even "
            "unblocked, its close relation to POWSM means agreement between them "
            "could never count as independent confirmation, and POWSM has now "
            "failed this task decisively."
        ),
        "incremental_value": (
            "Unknown, and now unlikely. It shares the IPAPack++ training family "
            "with POWSM, which reached four of ten checks, so the expected value "
            "of unblocking it for this task is low."
        ),
        "limitations": {
            "cost": (
                "None expected. The models run locally and ONNX artifacts exist."
            ),
            "privacy": "None. No audio would leave the machine.",
            "legal": (
                "The exact weight licence and training provenance are "
                "unconfirmed, so loading any checkpoint is prohibited. A code "
                "repository licence does not license separately hosted weights."
            ),
            "operational": (
                "No revision has been pinned, so there is nothing reproducible to "
                "run yet, and a serialization audit would be required first."
            ),
            "australian_variety": (
                "Grapheme to phoneme derived training labels biased toward "
                "canonical pronunciations, so no Australian variety evidence."
            ),
            "child_and_adult": (
                "No child provision and no child evidence."
            ),
        },
        "reopen_requires": [
            "author confirmation or a model card statement of the exact "
            "checkpoint licence and training provenance",
            "a pinned confirmed revision and a serialization audit before any "
            "load",
        ],
    },
    "wav2vec2_commonphone": {
        "reason": (
            "Its role is fixed by its training lineage rather than by any result. "
            "It was trained on Common Phone, which derives from Common Voice, so "
            "this project's Common Phone and Australian Common Voice evidence are "
            "not independent of it and can never count toward a selection gate, a "
            "headline result or corroboration. It ran in the powered comparison "
            "as a supporting comparator only, was never gated, and showed the "
            "same high recall and very poor precision pattern as the other free "
            "phone paths. Supporting only is a permanent property of this model "
            "here, not a verdict that better numbers could overturn."
        ),
        "incremental_value": (
            "None, and none is admissible. This lane cannot contribute selection "
            "evidence at all, so its outputs are context for disagreement "
            "analysis only."
        ),
        "limitations": {
            "cost": "None. Local and free.",
            "privacy": "None. No audio leaves the machine.",
            "legal": (
                "CC0 weights in safetensors format, so nothing legal restricts "
                "local use. The restriction here is scientific, not legal."
            ),
            "operational": (
                "About 0.5 times real time with a peak of roughly 3.4 gigabytes, "
                "the least expensive lane to run."
            ),
            "australian_variety": (
                "It has seen Australian Common Voice speech in training, which is "
                "precisely why this project's Australian evidence cannot test it."
            ),
            "child_and_adult": "No child evidence and no child role.",
        },
        "reopen_requires": [],
    },
    "unsw_speech_attributes": {
        "reason": (
            "Never loaded. The published Space code is Apache 2.0, but the actual "
            "adult and Australian child checkpoints carry no licence tag, model "
            "card or training statement, and the published method trained on "
            "TIMIT and validated on L2-ARCTIC, both of which restrict commercial "
            "and derived use. The combined enquiry had not been answered as at "
            "2026-07-28. Its articulatory attributes would explain a difference "
            "rather than decide one, so it was never a candidate detector in any "
            "case."
        ),
        "incremental_value": (
            "Unknown, and explanatory rather than decisive. Attribute detections "
            "could describe the place, manner and voicing behind a concern, but "
            "they cannot supply the expected to produced phone relation the gates "
            "measure."
        ),
        "limitations": {
            "cost": "None expected. Local models.",
            "privacy": "None. No audio would leave the machine.",
            "legal": (
                "An unconfirmed checkpoint licence and restricted training "
                "corpora block commercial use of derived weights. Availability is "
                "not permission."
            ),
            "operational": (
                "A serialization security review is required before any load, and "
                "no pinned revision has been cleared."
            ),
            "australian_variety": (
                "It is the only lane offering an explicitly Australian child "
                "checkpoint, which is exactly why its provenance matters and why "
                "it may not be used until the rights are written down."
            ),
            "child_and_adult": (
                "Its Australian child checkpoint is the one asset that could "
                "support child work later, and it is unusable today."
            ),
        },
        "reopen_requires": [
            "a combined UNSW answer covering checkpoint licence, training corpora "
            "and derived weight rights",
            "a serialization security review before any load",
        ],
    },
    "child_phoneme_model": {
        "reason": (
            "Never downloaded. The model card reports an OpenRAIL licence and "
            "MyST and Providence fine tuning. OpenRAIL is not an unrestricted "
            "commercial grant and the derived data rights of both corpora are "
            "unresolved. The published use is child phoneme representation and "
            "vocalization classification rather than validated pronunciation "
            "assessment, so the model name promises more than the evidence "
            "supports."
        ),
        "incremental_value": (
            "Unknown, and out of scope. The frozen gates are adult only, so this "
            "lane could not have changed any outcome at this checkpoint even if "
            "it were unblocked."
        ),
        "limitations": {
            "cost": (
                "None expected locally. MyST commercial licensing through Boulder "
                "Learning would carry a cost if that route were ever needed."
            ),
            "privacy": "None. No audio would leave the machine.",
            "legal": (
                "OpenRAIL use restrictions and unresolved MyST and Providence "
                "derived weight rights block download and load."
            ),
            "operational": (
                "No revision has been cleared and no environment has been built."
            ),
            "australian_variety": (
                "It is American child speech and carries no Australian variety "
                "evidence."
            ),
            "child_and_adult": (
                "This is the only child specific model lane, and child evidence "
                "in this project remains far too thin to support any estimate "
                "regardless of the model."
            ),
        },
        "reopen_requires": [
            "a review of the exact OpenRAIL terms",
            "written confirmation of MyST and Providence derived weight rights if "
            "those terms are ambiguous",
            "a separate child evidence plan, because the current child sample "
            "cannot support any estimate",
        ],
    },
    "auskidtalk": {
        "reason": (
            "An acquisition and collaboration path rather than a system, and it "
            "remains blocked because access is governed by a data custodian under "
            "research ethics with no public commercial terms, and the enquiry had "
            "not been answered as at 2026-07-28. It is the only right accent, "
            "right age Australian child asset identified, covering roughly 620 "
            "children including disordered speech, but the published annotation "
            "workflow is orthographic rather than phone level, so it would need "
            "expert annotation work before it could support anything the gates "
            "measure."
        ),
        "incremental_value": (
            "None yet, and potentially the largest of any lane later. It is the "
            "most plausible route to Australian child phone evidence, which no "
            "lane in either comparison can supply."
        ),
        "limitations": {
            "cost": "Unknown. No commercial terms are published.",
            "privacy": (
                "Child speech under research ethics governance, so any future use "
                "would need its own consent, privacy and governance decision far "
                "beyond the current corpus rules."
            ),
            "legal": (
                "Research only custodian access, with commercial research and "
                "derived model rights unestablished."
            ),
            "operational": (
                "Orthographic time aligned annotation rather than phone level "
                "annotation, so expert phone labelling would be required first."
            ),
            "australian_variety": (
                "This is the Australian evidence the project lacks, for children "
                "specifically."
            ),
            "child_and_adult": (
                "Children only. It does not address the adult Australian gap, "
                "which ANDOSL or an equivalent expertly labelled Australian set "
                "would."
            ),
        },
        "reopen_requires": [
            "a combined UNSW answer covering corpus access, phone level "
            "annotation availability, aggregate benchmarking, commercial research "
            "and derived model rights",
            "a separate consent, privacy and governance decision before any child "
            "data is handled",
        ],
    },
    "bookbot_au_g2p": {
        "reason": (
            "Not a scorer, and never was. It converts spelling to Australian "
            "broad IPA and could propose expected phone targets for the "
            "checkpoint 22F prompt pack, but its model card does not document its "
            "training and evaluation data sufficiently, so its provenance must be "
            "verified and its output compared against independent Australian "
            "references before it may propose a single target. Generated targets "
            "can never be reference truth."
        ),
        "incremental_value": (
            "None at this checkpoint, by design. It produces targets rather than "
            "judgements, so it cannot pass or fail a detection gate."
        ),
        "limitations": {
            "cost": "None. Local and Apache 2.0.",
            "privacy": "None. It consumes text, not audio.",
            "legal": (
                "Apache 2.0 licence, but the WikiPron source and Australian "
                "variant provenance are unverified."
            ),
            "operational": (
                "It is a text to phone model with no acoustic capability "
                "whatsoever, so it can never confirm what a speaker actually "
                "produced."
            ),
            "australian_variety": (
                "It is the only Australian variety asset currently available to "
                "this project, which makes verifying its provenance a "
                "prerequisite rather than a nicety."
            ),
            "child_and_adult": (
                "It has no age specific behaviour; the same targets would be "
                "proposed for anyone."
            ),
        },
        "reopen_requires": [
            "verification of the WikiPron source and Australian variant "
            "provenance",
            "comparison of generated targets against licensed or independently "
            "documented Australian references",
            "checkpoint 22F, which is where a prompt pack is built",
        ],
    },
    "soapbox": {
        "reason": (
            "Rejected because there is no path to obtain it. Curriculum "
            "Associates acquired SoapBox and stated it does not plan to enter new "
            "contracts with outside organisations, the developer site now "
            "redirects to the acquirer's internal AI Labs page with no signup, and "
            "documented default product improvement logging contradicts the "
            "earlier assumption of immediate deletion. No account was created, no "
            "contact was made and no audio was sent."
        ),
        "incremental_value": (
            "None. The lane was never obtainable, so nothing was measured."
        ),
        "limitations": {
            "cost": (
                "Not applicable. No commercial offering exists for new customers."
            ),
            "privacy": (
                "Documented default product improvement logging with opt out by "
                "support request, which would have needed its own decision had "
                "the lane been available."
            ),
            "legal": (
                "No terms are obtainable, so no permission can be established."
            ),
            "operational": (
                "Custom ARPAbet targets and per phone quality scores were "
                "documented for legacy customers only."
            ),
            "australian_variety": "No Australian model is documented.",
            "child_and_adult": (
                "It was a child speech specialist, which is what makes it worth "
                "recording as a loss rather than an omission."
            ),
        },
        "reopen_requires": [
            "a written external API offer from Curriculum Associates with "
            "acceptable terms",
        ],
    },
    "speechace": {
        "reason": (
            "Blocked by its own terms rather than by its capability. It exposes "
            "custom phone sequences and a sound most like field, which match this "
            "task better than most, but its terms prohibit using the API or its "
            "data to test or evaluate another speech assessment system and "
            "prohibit publishing evaluation results without written approval. "
            "That is exactly this benchmark, so no account was created and no "
            "audio was sent."
        ),
        "incremental_value": (
            "Unknown. It is the strongest untested external candidate on paper, "
            "and the only one blocked purely by contract rather than by "
            "capability or provenance."
        ),
        "limitations": {
            "cost": (
                "Unknown. Pricing was not pursued, because the terms bar the use."
            ),
            "privacy": (
                "Not reviewed, because the lane could not proceed far enough for "
                "it to matter."
            ),
            "legal": (
                "Its terms prohibit comparative evaluation and prohibit "
                "publishing results without written prior approval. Only a "
                "written waiver removes this."
            ),
            "operational": (
                "The sound most like semantics are documented ambiguously and "
                "would need empirical verification before being treated as "
                "produced phone identity."
            ),
            "australian_variety": (
                "No Australian variety evidence is documented."
            ),
            "child_and_adult": (
                "No separate child provision is established."
            ),
        },
        "reopen_requires": [
            "a written waiver for comparative evaluation and aggregate "
            "publication",
            "empirical verification of the sound most like semantics before any "
            "reliance",
        ],
    },
    "speechsuper": {
        "reason": (
            "Rejected because its current terms prohibit using the API or any "
            "product data to train, test or evaluate another speech engine, "
            "machine learning model or speech assessment system, which is "
            "precisely the planned comparison. Phone level scoring exists but is "
            "unusable here. No account was created and no audio was sent."
        ),
        "incremental_value": (
            "None. The lane is unusable under its current terms, so nothing was "
            "measured."
        ),
        "limitations": {
            "cost": "Not pursued.",
            "privacy": "Not reviewed. The lane cannot be used.",
            "legal": (
                "Its terms prohibit exactly this evaluation, and no waiver has "
                "been sought."
            ),
            "operational": (
                "Not applicable. No request was ever built for this lane."
            ),
            "australian_variety": (
                "No Australian variety evidence is documented."
            ),
            "child_and_adult": (
                "No separate child provision is established."
            ),
        },
        "reopen_requires": [
            "a change to its terms of service, or a written waiver, before any "
            "account is created",
        ],
    },
}


# Written text that differs by record version. Checkpoint 22E6 corrected what
# the Bookbot verdict rests on without moving the verdict, so the change lives
# here rather than by editing the committed version 1.0.0 wording.
LANE_RECORD_OVERRIDES = {
    "1.1.0": {
        "bookbot_au_g2p": {
            "reason": (
                "Not a scorer, and never was. It converts spelling to "
                "Australian broad IPA and could have proposed expected phone "
                "targets for a prompt pack, but its claimed training source is "
                "disproved rather than merely undocumented: WikiPron defines "
                "English with two dialects only, UK and US, so the Australian "
                "dataset its name advertises does not exist and cannot be "
                "inspected by anyone. The lane fails closed on lineage rather "
                "than on licence, and Wiktionary's own Australian tagged "
                "entries take over the target role because they can be read one "
                "entry at a time. Generated targets can never be reference "
                "truth."
            ),
            "limitations": {
                "legal": (
                    "Apache 2.0, which was never the blocker. The lane is "
                    "closed on lineage: the training source the model names "
                    "does not exist."
                ),
                "australian_variety": (
                    "It was treated as the only Australian variety asset this "
                    "project had, and it is not one. The Australian tagged "
                    "Wiktionary entries replace that role and can be inspected "
                    "directly."
                ),
            },
            "reopen_requires": [
                "an inspectable Australian pronunciation reference to replace "
                "the disproved training source",
                "comparison of any generated target against that reference "
                "before a single target is proposed",
                "checkpoint 22F, which is where a prompt pack is built",
            ],
        },
    },
}


def lane_records(version):
    """Merge the written lane text for one record version."""
    merged = {}
    for lane_id, written in LANE_RECORDS.items():
        record = dict(written)
        override = LANE_RECORD_OVERRIDES.get(version, {}).get(lane_id)
        if override:
            limitations = dict(record["limitations"])
            limitations.update(override.get("limitations", {}))
            record.update(
                {key: value for key, value in override.items() if key != "limitations"}
            )
            record["limitations"] = limitations
        merged[lane_id] = record
    return merged


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def measured_candidate_outcomes(powered):
    """Copy each candidate's gate outcome out of the committed powered report."""
    outcomes = []
    for candidate in powered["candidates"]:
        candidate_id = candidate["candidate_id"]
        if candidate_id not in CANDIDATE_PROFILES:
            raise SelectionRecordError(
                f"the powered comparison reports an unknown candidate: {candidate_id}"
            )
        point = candidate.get("reported_operating_point") or {}
        outcomes.append(
            {
                "candidate_id": candidate_id,
                "lane_id": candidate["lane_id"],
                "selection_eligible": candidate["selection_eligible"],
                "evidence_available": candidate["evidence_available"],
                "passes_every_unchanged_gate": candidate.get(
                    "any_operating_point_passes_both_partitions"
                ),
                "gate_checks_passed_of_ten": point.get("gate_checks_passed_of_ten"),
            }
        )
    return sorted(outcomes, key=lambda outcome: outcome["candidate_id"])


def _best_gate_checks(outcomes, lane_id):
    counts = [
        outcome["gate_checks_passed_of_ten"]
        for outcome in outcomes
        if outcome["lane_id"] == lane_id
        and outcome["selection_eligible"]
        and outcome["gate_checks_passed_of_ten"] is not None
    ]
    return max(counts) if counts else None


def build_record(version=ACTIVE_SELECTION_VERSION):
    record_profile = selection_profile(version)
    register = _load(record_profile["register_path"])
    if record_profile["register_path"] == REGISTER_PATH:
        assert_valid_register(register)
    else:
        assert_historical_register(register)
    powered = _load(comparison_profile("1.1.0")["report_path"])
    if powered["decision"]["decision"] != "no_selection":
        raise SelectionRecordError(
            "the powered comparison no longer reports no_selection; the written "
            "verdicts in this module were reasoned from that outcome and must be "
            "revisited by hand"
        )

    outcomes = measured_candidate_outcomes(powered)
    measured_lane_ids = gate_eligible_lane_ids()
    register_lanes = {lane["lane_id"]: lane for lane in register["lanes"]}

    written_records = lane_records(version)
    lanes = []
    for lane_id in sorted(LANE_DECISION_PROFILES):
        written = written_records[lane_id]
        register_lane = register_lanes[lane_id]
        profile = LANE_DECISION_PROFILES[lane_id]
        measured = lane_id in measured_lane_ids
        lanes.append(
            {
                "lane_id": lane_id,
                "display_name": register_lane["display_name"],
                "kind": register_lane["kind"],
                "register_role": register_lane["role"],
                "register_status": register_lane["status"],
                "audio_policy": register_lane["audio_policy"],
                "decision": profile["decision"],
                "decision_basis": profile["basis"],
                "reason": written["reason"],
                "incremental_value_beyond_22d_baseline": {
                    "measured": measured,
                    "summary": written["incremental_value"],
                    "gate_checks_passed_of_ten": (
                        _best_gate_checks(outcomes, lane_id) if measured else None
                    ),
                },
                "limitations": dict(written["limitations"]),
                "blocked_pending": list(register_lane["blocked_pending"]),
                "reopen_requires": list(written["reopen_requires"]),
            }
        )

    unmeasured = sum(1 for lane in lanes if lane["lane_id"] not in measured_lane_ids)
    limitations = list(LIMITATIONS)
    limitations.append(
        f"{unmeasured} of the {len(lanes)} lanes were never measured, because "
        "access, licence, provenance, an owner decision, provider terms or the "
        "lane's own role blocked them. Their verdicts record why nothing is "
        "known about them, not that they were tried and found wanting."
    )

    selected = sorted(
        lane["lane_id"] for lane in lanes if lane["decision"] == "selected_candidate"
    )
    record = {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "record_id": "speech_sound_selection_record",
        "record_version": version,
        "checkpoint": record_profile["checkpoint"],
        "status": RECORD_STATUS,
        "purpose": PURPOSE + PURPOSE_SUFFIXES.get(version, ""),
        "evidence_sources": evidence_pins(version),
        "selection_gates": {
            **FROZEN_SELECTION_GATES,
            "development_and_tuning_both_required": True,
            "inherited_unchanged_from_checkpoint_22d": True,
            "changed_in_this_checkpoint": False,
        },
        "measured_candidate_outcomes": outcomes,
        "lanes": lanes,
        "decision": {
            "decision": "selection_recorded" if selected else "no_selection",
            "selected_lane_ids": selected,
            "reason": DECISION_REASON,
            "no_selection_is_a_valid_completed_outcome": True,
            "gates_changed_in_this_checkpoint": False,
            "further_threshold_search_authorised": False,
            "remote_provider_required": False,
            "local_only_decision_permitted": True,
            "australian_variety_exact_relation_evidence_available": False,
            "children_supported": False,
            "held_out_set_accessed": False,
            "baseline_gate_checks_passed_of_ten": (
                BASELINE_GATE_CHECKS_PASSED_OF_TEN
            ),
        },
        "frozen_for_later_checkpoints": {
            "selected_mapping": None,
            "selected_feature": None,
            "selected_threshold": None,
            "selected_provider_configuration": None,
            "carried_forward": CARRIED_FORWARD,
            "not_carried_forward": NOT_CARRIED_FORWARD,
        },
        "limitations": limitations,
        "release_boundaries": powered["release_boundaries"],
        "next_checkpoint": record_profile["next_checkpoint"],
    }
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--record-version",
        choices=sorted(SELECTION_VERSIONS),
        default=ACTIVE_SELECTION_VERSION,
    )
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()
    version = arguments.record_version
    output = arguments.output or selection_profile(version)["record_path"]
    record = build_record(version)
    Path(output).write_bytes(canonical_json_bytes(record))
    assert_valid_selection_record(record)
    print(
        "Committed selection record: "
        f"{Path(output).resolve().relative_to(REPOSITORY_ROOT)}"
    )
    print(f"Decision: {record['decision']['decision']}")
    for lane in record["lanes"]:
        print(
            f"  {lane['lane_id']}: {lane['decision']} "
            f"({lane['decision_basis']})"
        )


if __name__ == "__main__":
    main()
