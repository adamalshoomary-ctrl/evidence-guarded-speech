"""Build the checkpoint 23B deliverable ledger.

Checkpoint 23B lists thirteen required deliverables.  A large amount of honest
public research has now been done against some of them, and none of it moves the
checkpoint any closer to acceptance, because acceptance is defined as written
review by accountable human roles.

This ledger exists so that the volume of work cannot be mistaken for progress.
It records, for every one of the thirteen, whether public research finished it,
advanced it, or could not begin it, what evidence exists, what remains, and
which human role has to supply that remainder.

Rebuild with::

    python3 -m motor_speech_voice.build_checkpoint_ledger
"""

from __future__ import annotations

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parent
LEDGER_PATH = MODULE_ROOT / "checkpoint-23b-ledger-v1.0.0.json"

PREPARED_AT = "2026-08-19"

COMPLETE = "public_research_complete"
PARTIAL = "public_research_partial"
BLOCKED = "blocked_requires_named_human"


def _deliverable(number, title, status, evidence, what_remains, who_supplies_it, note):
    return {
        "number": number,
        "title": title,
        "status": status,
        "evidence": list(evidence),
        "what_remains": what_remains,
        "who_supplies_it": list(who_supplies_it),
        "note": note,
    }


DELIVERABLES = [
    _deliverable(
        "one",
        "Signed intended use, population, user, action and prohibited use "
        "statement",
        BLOCKED,
        [],
        "A signature, and before that a benefit concrete enough to be worth "
        "signing. The draft in the governance review package records that it does "
        "not yet identify a sufficiently concrete benefit or eventual human "
        "action.",
        ["owner", "independent_professional_governance_group", "paid_lived_experience_governance_group"],
        "The draft exists and is deliberately unsigned. A draft is not a "
        "deliverable here.",
    ),
    _deliverable(
        "two",
        "Recorded adults first research scope and a separate prohibition on child "
        "inclusion",
        COMPLETE,
        ["motor_speech_voice/governance-contract-v1.0.0.json"],
        "Nothing. Adam approved adults first on 2026-08-14 and the contract "
        "records it.",
        [],
        "This is the only deliverable an owner decision alone could complete, and "
        "it is complete. It sets a research eligibility floor of eighteen and "
        "creates no product age gate.",
    ),
    _deliverable(
        "three",
        "Named paid lived experience governance and independent professional roles",
        BLOCKED,
        [],
        "Real people, appointed and paid. Public identification routes exist in "
        "the governance review package; a name on a shortlist is not an "
        "appointment.",
        ["owner", "paid_lived_experience_governance_group", "independent_professional_governance_group"],
        "This one also needs a budget, which does not exist.",
    ),
    _deliverable(
        "four",
        "Conflict register and decision rights matrix separating vendor, truth and "
        "release authority",
        BLOCKED,
        [],
        "Named parties. A conflict register with nobody in it records nothing.",
        ["owner", "independent_professional_governance_group"],
        "The machine readable shape for this exists in final_decision.py and is "
        "waiting for content.",
    ),
    _deliverable(
        "five",
        "Professionally reviewed task, burden, access, stop and safety protocol",
        BLOCKED,
        [],
        "Professional review. The task itself is locked and no prompt, syllable "
        "sequence, effort instruction or trial count has been selected.",
        ["independent_professional_governance_group", "paid_lived_experience_governance_group"],
        "The measurement input package records what a protocol would have to fix, "
        "which is not the same as fixing it.",
    ),
    _deliverable(
        "six",
        "Construct specific annotation, listener and clinical reference manuals",
        BLOCKED,
        [],
        "The relevant professionals, writing them. Manuals decide what the "
        "reference means, so they cannot be drafted by the party being checked.",
        ["independent_professional_governance_group"],
        "The source survey established there is no public annotation to imitate "
        "for the motor lane, so these would be written from nothing.",
    ),
    _deliverable(
        "seven",
        "Prospective acquisition, sample size, representation, split and "
        "statistical plan",
        PARTIAL,
        [
            "motor_speech_voice/measurement_plan/",
            "motor_speech_voice/measurement_plan/measurement-plan-registry-v1.0.0.json",
        ],
        "An independent statistician, a selected construct and pilot variance. "
        "Every recognised sizing method needs an anticipated reliability or prior "
        "variance components, and none of them can produce that from nothing.",
        ["owner"],
        "Public research produced the inputs a statistician would need, once per "
        "provisional construct, and structurally cannot produce a sample size. "
        "That is the whole distinction this deliverable turns on.",
    ),
    _deliverable(
        "eight",
        "Institution pathway determined and required prospective ethics review "
        "completed",
        BLOCKED,
        [],
        "An institution, and an ethics review body willing to review an "
        "unaffiliated individual. No Australian body is obliged to provide one, "
        "and two Queensland universities checked directly will not.",
        ["responsible_institution", "human_research_ethics_committee_or_review_body", "owner"],
        "The regulatory reading records the routes that exist and the decisive "
        "unknown, which is whether any registered committee accepts an applicant "
        "with no organisation. Settling that needs contact, which the approved "
        "research only route prohibits.",
    ),
    _deliverable(
        "nine",
        "Privacy impact assessment, responsible entity and data role matrix, "
        "applicable law, notices, controls, consent, retention and incident design",
        PARTIAL,
        [
            "motor_speech_voice/regulatory_reading/",
            "motor_speech_voice/regulatory_reading/regulatory-reading-registry-v1.0.0.json",
        ],
        "A legal entity to be the responsible entity, and a privacy lawyer. An "
        "assessment names who is accountable, and there is nobody to name.",
        ["owner", "australian_privacy_lawyer"],
        "Public research mapped which law applies and found one exposure the "
        "repository had not recorded at all: a statutory tort that applies to an "
        "individual regardless of entity status, turnover or privacy principle "
        "coverage, with no research exemption.",
    ),
    _deliverable(
        "ten",
        "Source and commercial rights review, including every proposed vendor and "
        "transfer",
        COMPLETE,
        [
            "motor_speech_voice/source_survey/",
            "motor_speech_voice/source_survey/source-survey-registry-v1.0.0.json",
        ],
        "Nothing for this deliverable. Twenty seven sources were surveyed with "
        "their licence, access route and rights state, nothing was selected and no "
        "acquisition was authorised.",
        [],
        "Complete does not mean favourable. The review's finding is that the "
        "motor lane has no qualifying public source at any licence and at any "
        "price.",
    ),
    _deliverable(
        "eleven",
        "Versioned split allocation method and overlap register before pilot access",
        BLOCKED,
        [],
        "A pilot to allocate. There is no participant, no recording and no split "
        "to freeze.",
        ["owner", "responsible_institution"],
        "The rules that would govern the allocation are recorded in the "
        "measurement input package. The allocation itself has no subject.",
    ),
    _deliverable(
        "twelve",
        "Documented preliminary Australian classification and clinical trial "
        "pathway assessment",
        PARTIAL,
        [
            "motor_speech_voice/regulatory_reading/",
            "motor_speech_voice/regulatory_reading/regulatory-reading-registry-v1.0.0.json",
        ],
        "A qualified Australian regulatory specialist, documenting the "
        "assessment. A careful reading by a non lawyer is not a determination and "
        "the checkpoint asks for a determination.",
        ["australian_regulatory_specialist", "human_research_ethics_committee_or_review_body"],
        "Public research located the point at which the answer changes, which is "
        "the useful part. It also found that the clinical trial question is one "
        "the regulator expressly declines to answer and assigns to an ethics "
        "committee, so it is unanswerable here for a structural reason rather "
        "than for want of effort.",
    ),
    _deliverable(
        "thirteen",
        "Recorded selection or no selection decision with reasons",
        BLOCKED,
        [],
        "Every review above. A decision recorded before the reviews that inform "
        "it would be a decision about nothing.",
        ["owner", "independent_professional_governance_group"],
        "A documented no selection would be a valid completed result. It is not "
        "available yet, because the reasons that would justify it have not been "
        "reviewed by anybody accountable.",
    ),
]

ACCEPTANCE_RULE = (
    "Checkpoint 23B acceptance is written review from the accountable roles, not "
    "an agent's interpretation of public guidance and not a count of finished "
    "deliverables. Two of thirteen are complete and both were completable without "
    "any external party. Nothing in this ledger, and no amount of further public "
    "research, can move a blocked deliverable, because each is blocked on a "
    "person rather than on information."
)

WHAT_PUBLIC_RESEARCH_CHANGED = [
    "It established that the motor lane has no qualifying public reference source "
    "at any licence and at any price, so any rapid syllable claim depends on "
    "prospective collection rather than on data anyone can obtain.",
    "It established that the absent legal entity is a demonstrated blocker in "
    "three separate places: the data use agreement countersignature that gates "
    "the largest relevant intelligibility corpus, the Australian sponsor a "
    "clinical trial notification requires, and the Australian legal entity a "
    "medical device sponsor must be.",
    "It located the point on the intended purpose ladder where Australian medical "
    "device regulation engages, and found that checkpoint 23E's own described "
    "action sits close to the regulator's definition of screening.",
    "It found a personal legal exposure the repository had not recorded: a "
    "statutory tort of serious invasion of privacy, in force since 10 June 2025, "
    "which applies to an individual with no entity and has no research exemption.",
    "It found that Queensland law treats recording and later sharing as separate "
    "questions, and that sharing recordings or transcripts with annotators is the "
    "one that needs consent from every party.",
    "It recorded the inputs an independent statistician would need for each of "
    "the twelve provisional constructs, and made it structurally impossible for "
    "that package to contain a sample size.",
]


def build_ledger():
    counts = {}
    for deliverable in DELIVERABLES:
        counts[deliverable["status"]] = counts.get(deliverable["status"], 0) + 1
    return {
        "schema_version": "1.0.0",
        "ledger_id": "motor_speech_voice_checkpoint_23b_ledger_v1",
        "checkpoint": "23B",
        "checkpoint_status": "in_progress",
        "prepared_at": PREPARED_AT,
        "deliverable_count": len(DELIVERABLES),
        "deliverables": DELIVERABLES,
        "counts": counts,
        "acceptance_rule": ACCEPTANCE_RULE,
        "what_public_research_changed": WHAT_PUBLIC_RESEARCH_CHANGED,
        "selection_recorded": False,
        "external_party_contacted": False,
        "money_spent": False,
        "data_acquired": False,
    }


def main():
    ledger = build_ledger()
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")
    counts = ledger["counts"]
    print(f"Wrote the checkpoint 23B ledger with {ledger['deliverable_count']} deliverables.")
    print(
        f"{counts.get(COMPLETE, 0)} complete, {counts.get(PARTIAL, 0)} partial, "
        f"{counts.get(BLOCKED, 0)} blocked on a named human role."
    )
    print("Checkpoint 23B remains in progress.")


if __name__ == "__main__":
    main()
