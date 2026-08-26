"""Build the checkpoint 23B documented Australian regulatory and privacy reading.

Checkpoint 23B requires a "documented preliminary Australian classification and
clinical-trial pathway assessment" and a privacy impact assessment.  A privacy
impact assessment needs a legal entity to be the entity, and a classification
determination needs a qualified specialist, so neither can be produced here.
What public research can produce is an accurate reading of the public rules
against a stated intended purpose, with the operative wording quoted and the
open questions named.

The reading is organised around a ladder of three intended purposes, because in
Australian medical device law the answer follows the intended purpose rather
than the technology.  The same speech measurement can sit outside regulation
entirely, inside an exclusion, or inside the medical device framework depending
only on what is claimed for it.  Recording where the answer changes is the
useful output; recording a single verdict would be less true and less useful.

Every record is a documented reading by a non lawyer.  It is never advice, a
determination, an approval or a defence, and the schema cannot express that it
is.  Every record names at least one accountable human role that must actually
settle it.

Rebuild with::

    python3 -m motor_speech_voice.build_regulatory_reading
"""

from __future__ import annotations

import json
from pathlib import Path


READING_ROOT = Path(__file__).resolve().parent / "regulatory_reading"
SCHEMA_FILENAME = "regulatory-reading-schema-v1.0.0.json"
REGISTRY_FILENAME = "regulatory-reading-registry-v1.0.0.json"

PREPARED_AT = "2026-08-19"
READ_ON = "2026-08-19"

P1 = "developer_research_only"
P2 = "consumer_communication_coaching"
P3 = "consumer_screening_referral"


def _source(citation, url, currency, extract, read_at_source=True):
    return {
        "citation": citation,
        "url": url,
        "currency": currency,
        "read_at_source": read_at_source,
        "read_on": READ_ON,
        "extract": extract,
    }


def _record(**fields):
    fields.setdefault("schema_version", "1.0.0")
    fields["record_id"] = f"{fields['question_id']}_reading_v1"
    fields.setdefault("conflicts", [])
    fields.setdefault("unresolved", [])
    fields["status"] = "documented_reading_not_a_determination"
    fields["is_legal_or_regulatory_advice"] = False
    fields["creates_any_authority"] = False
    return fields


# Sources quoted by more than one record.
TG_ACT = _source(
    "Therapeutic Goods Act 1989 (Cth), section 41BD, What is a medical device",
    "https://www.legislation.gov.au/C2004A03952/latest/text",
    "Compilation in force 5 September 2025",
    "A medical device is: (a) any instrument, apparatus, appliance, software, "
    "implant, reagent, material or other article (whether used alone or in "
    "combination, and including the software necessary for its proper "
    "application) intended, by the person under whose name it is or is to be "
    "supplied, to be used for human beings for the purpose of one or more of the "
    "following: (i) diagnosis, prevention, monitoring, prediction, prognosis, "
    "treatment or alleviation of disease; (ii) diagnosis, monitoring, treatment, "
    "alleviation of or compensation for an injury or disability; (iii) "
    "investigation, replacement or modification of the anatomy or of a "
    "physiological or pathological process or state ...",
)

TG_ACT_INTENDED_PURPOSE = _source(
    "Therapeutic Goods Act 1989 (Cth), section 41BD(2)",
    "https://www.legislation.gov.au/C2004A03952/latest/text",
    "Compilation in force 5 September 2025",
    "For the purposes of paragraph (1)(a), the purpose for which an instrument, "
    "apparatus, appliance, software, implant, reagent, material or other article "
    "(the main equipment) is to be used is to be ascertained from the information "
    "supplied, by the person under whose name the main equipment is or is to be "
    "supplied, on or in any one or more of the following: (a) the labelling on "
    "the main equipment; (b) the instructions for using the main equipment; (c) "
    "any advertising material relating to the main equipment; (d) technical "
    "documentation describing the mechanism of action of the main equipment.",
)

TGA_SOFTWARE_GUIDANCE = _source(
    "Therapeutic Goods Administration, Understanding how we regulate "
    "software-based medical devices",
    "https://www.tga.gov.au/resources/guidance/understanding-how-we-regulate-software-based-medical-devices",
    "Published and last updated 24 February 2026",
    "Some software products and mobile apps are sources of information or tools "
    "to manage a healthy lifestyle. We do not regulate health and lifestyle apps, "
    "unless they meet the definition of a medical device.",
)

EXCLUDED_GOODS = (
    "Therapeutic Goods (Excluded Goods) Determination 2018 (Cth), Schedule 1",
    "https://www.legislation.gov.au/F2018L01350/latest/text",
    "Compilation F2024C00750, 8 August 2024",
)


MEDICAL_DEVICE_RECORDS = [
    _record(
        question_id="medical_device_definition",
        domain="medical_device_regulation",
        question="Does software that measures a person's speech meet the "
        "definition of a medical device in Australia, and what decides it?",
        applies_to_purposes=[P1, P2, P3],
        primary_sources=[
            TG_ACT,
            TG_ACT_INTENDED_PURPOSE,
            TGA_SOFTWARE_GUIDANCE,
            _source(
                "Therapeutic Goods Administration, Understanding how we regulate "
                "software-based medical devices, The importance of intended purpose",
                "https://www.tga.gov.au/resources/guidance/understanding-how-we-regulate-software-based-medical-devices",
                "Published and last updated 24 February 2026",
                "We regulate software based on the manufacturer's intended purpose "
                "and how it is supplied. The manufacturer defines how they intend "
                "the device to be used, not all possible uses. For instance, 2 apps "
                "may present with similar functionalities but have different "
                "intended purposes based on the features or information that is "
                "made available to the user, for example: an app designed only to "
                "measure and display a person's heart rate for fitness purposes; an "
                "app intended to measure and display a person's heart rate that "
                "detects conditions such as bradycardia or tachycardia.",
            ),
        ],
        reading=[
            "Nothing about measuring speech makes software a medical device or "
            "keeps it out. The definition turns on the purpose the supplier "
            "states, and section 41BD(2) says that purpose is read off the "
            "labelling, the instructions, the advertising and the technical "
            "documentation. A claim made on a marketing page counts.",
            "The regulator's own worked example is almost exactly this project's "
            "ladder in another organ system. An app that measures and displays "
            "heart rate for fitness is not a device; the same app that detects "
            "bradycardia or tachycardia is. The measurement did not change, the "
            "claim did.",
            "Two limbs of the definition are the live ones here. Limb (a)(ii) "
            "covers diagnosis, monitoring, treatment or alleviation of an injury "
            "or disability, and a motor speech difficulty is plausibly a "
            "disability. Limb (a)(iii) covers investigation of a physiological "
            "process or state, and speech production is a physiological process. "
            "Limb (a)(iii) read at its widest would capture a great deal, and the "
            "regulator's guidance in practice reads it more narrowly than its "
            "words allow.",
        ],
        confidence="clear_on_the_face_of_the_source",
        unresolved=[
            {
                "question": "How far limb (a)(iii), investigation of a "
                "physiological process or state, reaches for software that "
                "measures speech timing and makes no health claim.",
                "why_it_cannot_be_settled_here": "The statutory words are broader "
                "than the regulator's published examples, and reconciling them is "
                "an exercise in regulatory interpretation rather than reading.",
                "who_must_settle_it": "An Australian regulatory specialist, "
                "documenting the assessment the plan already requires before "
                "participant recruitment or candidate software use.",
            }
        ],
        consequences=[
            "The wording used to describe this project is a regulatory act, not "
            "marketing. A sentence such as may indicate a speech problem placed on "
            "a public page would be evidence of intended purpose.",
            "The product vision's stated ambition to support people with speech "
            "differences and difficulties sits on the far side of this line and "
            "cannot be reached by improving the measurement alone.",
        ],
        decided_by=["australian_regulatory_specialist", "owner"],
    ),
    _record(
        question_id="wellness_and_coaching_exclusions",
        domain="medical_device_regulation",
        question="If a consumer communication coaching feature were a medical "
        "device, would the general health or wellness or the behavioural change "
        "and coaching exclusions take it back out?",
        applies_to_purposes=[P2, P3],
        primary_sources=[
            _source(
                f"{EXCLUDED_GOODS[0]}, item 14B",
                EXCLUDED_GOODS[1],
                EXCLUDED_GOODS[2],
                "software, or a combination of software and non-invasive hardware, "
                "that is: (a) intended by its manufacturer to be used by a consumer "
                "to promote or facilitate general health or wellness by measuring "
                "or monitoring (through non-invasive means) a physical parameter, "
                "such as movement, sleep, heart rate, heart rhythm, temperature, "
                "blood pressure or oxygen saturation; and (b) not intended by its "
                "manufacturer to be used: (i) in clinical practice; or (ii) for the "
                "purpose of diagnosis, screening, prevention, monitoring, "
                "prediction, prognosis, alleviation, treatment, or making a "
                "recommendation or decision about the treatment, of a serious "
                "disease or a serious condition, ailment or defect",
            ),
            _source(
                f"{EXCLUDED_GOODS[0]}, item 14C",
                EXCLUDED_GOODS[1],
                EXCLUDED_GOODS[2],
                "software that is: (a) intended by its manufacturer to be used by a "
                "consumer to improve general health or wellness by coaching, or "
                "encouraging behavioural change, in relation to personal or "
                "environmental factors, such as weight, exercise, sun exposure or "
                "dietary intake; and (b) not intended by its manufacturer to be "
                "used: (i) in clinical practice or to provide information to the "
                "consumer that would generally be accepted to require the "
                "interpretation of a health professional; or (ii) for the purpose "
                "of diagnosis, prognosis, or making a decision about the treatment, "
                "of a disease, condition, ailment or defect",
            ),
            _source(
                "Therapeutic Goods Administration, Software-based medical device "
                "exclusions",
                "https://www.tga.gov.au/resources/guidance/understanding-if-your-software-based-medical-device-excluded-our-regulation",
                "Last updated 16 March 2026",
                "There are currently 15 categories of software products listed in "
                "Schedule 1 of the Determination. If your product meets all the "
                "conditions of an excluded good described in the Determination, it "
                "is not subject to TGA regulation and must not be included in the "
                "ARTG. ... Some software products have multiple functions. To "
                "qualify for exclusion, every function must meet the exclusion "
                "criteria.",
            ),
        ],
        reading=[
            "Both exclusions are plausibly available to a coaching feature that "
            "makes no claim about any disease or condition, and both are lost the "
            "moment it makes one.",
            "The two have different thresholds and that difference matters. Item "
            "14B is lost only for a serious disease or condition. Item 14C is lost "
            "for diagnosis, prognosis or a treatment decision about any disease, "
            "condition, ailment or defect, serious or not, and is additionally "
            "lost if the software provides information that would generally be "
            "accepted to require the interpretation of a health professional.",
            "Whether speech is a physical parameter under item 14B is an open "
            "reading. The list is introduced by such as and is not exhaustive, and "
            "speech measured through a microphone is non-invasive, so the reading "
            "is available; it has not been tested.",
            "The multiple function rule is the sharpest practical constraint. "
            "Every function of the software must meet the exclusion criteria, so "
            "one screening feature inside an otherwise excluded coaching product "
            "takes the whole product out of the exclusion.",
        ],
        confidence="reading_with_material_uncertainty",
        unresolved=[
            {
                "question": "Whether speech timing or voice acoustics count as a "
                "physical parameter within item 14B.",
                "why_it_cannot_be_settled_here": "The instrument's list is "
                "illustrative and no published guidance addresses speech.",
                "who_must_settle_it": "An Australian regulatory specialist.",
            },
            {
                "question": "Whether communication skill is general health or "
                "wellness at all, which both exclusions assume as their subject "
                "matter.",
                "why_it_cannot_be_settled_here": "The guidance defines general "
                "health and wellness as broad or non specific health or wellness "
                "issues, for example a person's state of mind, general mobility, or "
                "fitness. Communication is not named either way.",
                "who_must_settle_it": "An Australian regulatory specialist.",
            },
        ],
        conflicts=[
            "The instrument's item 14C paragraph (b)(ii) lists diagnosis, "
            "prognosis and treatment decisions, and does not list screening. The "
            "regulator's guidance page for the same exclusion defines general "
            "consumer use to include not intending the software to be used for "
            "diagnosis, screening, prevention, monitoring, prediction, prognosis, "
            "alleviation, treatment, or making recommendations or decisions about "
            "the treatment, of a disease, condition, ailment, or defect. The "
            "guidance is therefore wider than the instrument it explains. Both are "
            "recorded; neither is preferred here.",
        ],
        consequences=[
            "An exclusion is not a safe harbour that survives a feature being "
            "added later. It is a property of the whole product at the time it is "
            "supplied.",
            "If a coaching mode and a screening mode ever coexist in one product, "
            "the exclusion analysis is decided by the screening mode.",
        ],
        decided_by=["australian_regulatory_specialist", "owner"],
    ),
    _record(
        question_id="self_management_exclusion_and_future_speech_support",
        domain="medical_device_regulation",
        question="Would the health self-management exclusion cover the product "
        "vision's stated future ambition to support people with speech "
        "difficulties?",
        applies_to_purposes=[P2, P3],
        primary_sources=[
            _source(
                f"{EXCLUDED_GOODS[0]}, item 14A",
                EXCLUDED_GOODS[1],
                EXCLUDED_GOODS[2],
                "software that is: (a) intended by its manufacturer to be used by a "
                "consumer for the self-management of an existing disease, "
                "condition, ailment or defect that is not a serious disease or "
                "serious condition, ailment or defect; and (b) not intended by its "
                "manufacturer to be used: (i) in clinical practice; or (ii) in "
                "relation to a serious disease or serious condition, ailment or "
                "defect; or (iii) for the purpose of diagnosis, treatment, or "
                "making a specific recommendation or decision about the treatment, "
                "of a disease, condition, ailment or defect that is not a serious "
                "disease or serious condition, ailment or defect",
            ),
            _source(
                "Therapeutic Goods Administration, Understanding the health "
                "self-management software exclusion",
                "https://www.tga.gov.au/resources/guidance/understanding-health-self-management-software-exclusion",
                "Last updated 16 March 2026",
                "An example of a serious condition is diabetes. Diabetes is "
                "considered serious as it requires the intervention of a health "
                "professional to be evaluated and treated effectively. An example "
                "of a condition that is not serious is mild fever. A general "
                "consumer could reasonably evaluate whether they have a mild fever "
                "and manage it safely without the intervention of a health "
                "professional.",
            ),
        ],
        reading=[
            "Item 14A is available only for self-management of a condition that is "
            "not serious. A named speech condition that a person has been "
            "diagnosed with is very unlikely to be not serious on the regulator's "
            "own test, because evaluating and treating it effectively requires a "
            "professional.",
            "So the exclusion most people would reach for when imagining a support "
            "mode for people with speech difficulties is the one least likely to "
            "apply to it.",
        ],
        confidence="reading_with_material_uncertainty",
        unresolved=[
            {
                "question": "Whether a particular speech condition is serious "
                "within the meaning of the Regulations.",
                "why_it_cannot_be_settled_here": "Seriousness is assessed against "
                "a statutory test about what an average person can evaluate and "
                "treat safely without a registered practitioner, and applying it to "
                "a named condition is a regulatory judgement.",
                "who_must_settle_it": "An Australian regulatory specialist, with "
                "input from the independent professional governance group.",
            }
        ],
        consequences=[
            "The product vision already places speech support later and behind "
            "stronger evidence and professional involvement. This reading adds a "
            "second, independent reason for that ordering: the regulatory position "
            "of a support mode is materially harder than that of general coaching, "
            "and is not improved by better measurement.",
        ],
        decided_by=[
            "australian_regulatory_specialist",
            "independent_professional_governance_group",
            "owner",
        ],
    ),
]

TGA_CLASSIFICATION_SOURCE = (
    "Therapeutic Goods Administration, Classifying active medical devices in "
    "Australia (including software-based medical devices), Rule 4.5",
    "https://www.tga.gov.au/resources/guidance/classifying-active-medical-devices-australia-including-software-based-medical-devices",
    "Retrieved 2026-08-19; page states no separate last updated date in the "
    "extracted text",
)

MEDICAL_DEVICE_RECORDS.extend(
    [
        _record(
            question_id="classification_if_a_screening_result_is_shown",
            domain="medical_device_regulation",
            question="If a consumer facing feature told a person their speech may "
            "indicate a condition worth professional assessment, what device "
            "classification would that attract?",
            applies_to_purposes=[P3],
            primary_sources=[
                _source(
                    *TGA_CLASSIFICATION_SOURCE,
                    "Rule 4.5 applies to active medical devices intended to be "
                    "used to process data or information in order to: provide a "
                    "diagnosis of a disease or condition. or screen for the "
                    "potential presence of a disease or condition. Screening is "
                    "the detection of potential disease indicators in otherwise "
                    "healthy, asymptomatic but at-risk individuals, in order to "
                    "determine whether a confirmatory diagnostic test is "
                    "warranted.",
                ),
                _source(
                    *TGA_CLASSIFICATION_SOURCE,
                    "Provide diagnosis or screening result to a user: Disease or "
                    "condition may lead to death/severe deterioration without "
                    "urgent treatment/pose a high public health risk: Class III, "
                    "Rule 4.5 (1) (c); Disease or condition is serious/may pose a "
                    "moderate public health risk: Class IIb, Rule 4.5 (1) (d); Any "
                    "other case: Class IIa, Rule 4.5 (1) (e). Information to "
                    "relevant health professional to support diagnostic/screening "
                    "decision making: ... Disease or condition is serious/pose a "
                    "moderate public health risk: Class IIa, Rule 4.5 (2) (b); Any "
                    "other case: Class I, Rule 4.5 (2) (c).",
                ),
                _source(
                    *TGA_CLASSIFICATION_SOURCE,
                    "A higher classification applies if the device performs all "
                    "the decision-making itself and provides a diagnosis or a "
                    "screening result to the user, who may be either a layperson "
                    "or a health professional. A lower classification may apply if "
                    "the device only provides information to a relevant health "
                    "professional to assist them in diagnosing or screening for a "
                    "disease or condition, and the health professional is "
                    "responsible for the final diagnostic decision-making.",
                ),
            ],
            reading=[
                "The regulator's definition of screening is close to verbatim what "
                "checkpoint 23E contemplates. Its stated action is to indicate "
                "whether a professional assessment route should be studied, and "
                "the rule defines screening as detecting potential disease "
                "indicators in otherwise healthy, asymptomatic individuals in "
                "order to determine whether a confirmatory diagnostic test is "
                "warranted. That is not a distant analogy; it is the same "
                "sentence in different words.",
                "If the result goes to the person and the condition is serious, "
                "the reading is Rule 4.5(1)(d), Class IIb. That is the same class "
                "the regulator's own examples give to diagnosing emphysema from a "
                "CT scan.",
                "If instead the information goes to a relevant health professional "
                "who makes the decision, the reading drops one class to Rule "
                "4.5(2)(b), Class IIa. Whether that reduction is available here "
                "depends on whether a speech pathologist is a health professional "
                "under the Regulations, which is a separate question and is not "
                "obviously yes.",
                "Class IIb is not a paperwork tier. It requires conformity "
                "assessment evidence from a recognised independent body, ARTG "
                "inclusion, and an Australian sponsor.",
            ],
            confidence="reading_with_material_uncertainty",
            unresolved=[
                {
                    "question": "Whether a motor speech condition is a serious "
                    "condition, which decides between Class IIb and Class IIa on "
                    "the consumer facing path.",
                    "why_it_cannot_be_settled_here": "It requires applying the "
                    "statutory seriousness test to a named condition, and no "
                    "condition has been named because checkpoint 23A prohibits "
                    "naming one.",
                    "who_must_settle_it": "An Australian regulatory specialist.",
                },
                {
                    "question": "Whether the lower classification path is "
                    "available at all when the recipient is a speech pathologist.",
                    "why_it_cannot_be_settled_here": "It depends on the "
                    "Regulations' definition of health professional, which is "
                    "examined in its own record and does not name speech "
                    "pathology.",
                    "who_must_settle_it": "An Australian regulatory specialist.",
                },
            ],
            consequences=[
                "The cheapest looking product feature in this whole programme, a "
                "line of text suggesting the person see someone, is the single "
                "most expensive one in regulatory terms.",
                "A design that routes information to a professional rather than to "
                "the person is materially lower risk under this rule, but only if "
                "the professional qualifies, which is unresolved.",
            ],
            decided_by=["australian_regulatory_specialist", "owner"],
        ),
        _record(
            question_id="seriousness_test",
            domain="medical_device_regulation",
            question="What does serious mean in this context, and who decides it?",
            applies_to_purposes=[P2, P3],
            primary_sources=[
                _source(
                    *TGA_CLASSIFICATION_SOURCE,
                    "'Serious' has the meaning defined in the Regulations. Serious "
                    "means a condition, ailment or defect that is: generally "
                    "accepted as not being appropriate to be diagnosed or treated "
                    "without consulting a medical practitioner, dentist or other "
                    "kind of health care worker registered under a law of a state "
                    "or territory; or generally accepted to be beyond the ability "
                    "of the average person to evaluate accurately, or treat "
                    "safely, without supervision by a medical practitioner, "
                    "dentist or other kind of health care worker registered under "
                    "a law of a state or territory. Serious disease means a "
                    "disease that: may result in death or long-term disability; "
                    "and may be incurable or require major therapeutic "
                    "interventions; and must be diagnosed accurately, to mitigate "
                    "the public health impact of the disease.",
                ),
            ],
            reading=[
                "The test is not about how distressing a condition is. It is about "
                "whether an ordinary person can evaluate or treat it safely "
                "without a registered practitioner.",
                "On that test a motor speech condition reads as serious. It is not "
                "something an average person can accurately evaluate alone, and it "
                "is not appropriate to diagnose without a professional. Both limbs "
                "point the same way.",
                "There is a wrinkle worth flagging rather than smoothing over. "
                "Both limbs are written around a practitioner registered under a "
                "law of a state or territory, and speech pathology is not such a "
                "profession in Australia. A narrow reading might argue a condition "
                "chiefly assessed by speech pathologists escapes the definition. "
                "That reading looks weak, because motor speech difficulty is "
                "routinely evaluated by medical practitioners as well, but it has "
                "not been tested and is recorded rather than dismissed.",
                "Serious condition and serious disease are separate defined terms "
                "with different tests, and the classification rule uses both. The "
                "serious disease test is considerably harder to satisfy.",
            ],
            confidence="reading_with_material_uncertainty",
            unresolved=[
                {
                    "question": "Whether the registered under a law of a state or "
                    "territory wording changes the seriousness analysis for a "
                    "condition principally assessed by a self regulated profession.",
                    "why_it_cannot_be_settled_here": "It is a question of "
                    "statutory construction with no published guidance addressing "
                    "it.",
                    "who_must_settle_it": "An Australian regulatory specialist.",
                }
            ],
            consequences=[
                "Seriousness is the hinge for both the item 14B exclusion and the "
                "Rule 4.5 classification, so one contested reading drives two "
                "outcomes.",
            ],
            decided_by=["australian_regulatory_specialist"],
        ),
        _record(
            question_id="health_professional_and_speech_pathology",
            domain="professional_regulation",
            question="Is a speech pathologist a health professional for the "
            "purposes of Australian medical device regulation?",
            applies_to_purposes=[P2, P3],
            primary_sources=[
                _source(
                    "Therapeutic Goods Administration, Understanding clinical "
                    "decision support system software regulation, terminology used "
                    "in exemption criterion (a)",
                    "https://www.tga.gov.au/resources/guidance/understanding-clinical-decision-support-system-software-regulation",
                    "Retrieved 2026-08-19",
                    "A Health professional is defined by the Regulations and "
                    "includes a person who is: a medical practitioner, a dentist "
                    "or any other kind of health care worker registered under a "
                    "law of a State or Territory or a biomedical engineer, "
                    "chiropractor, optometrist, orthodontist, osteopath, "
                    "pharmacist, physiotherapist, podiatrist, prosthetist, or "
                    "rehabilitation engineer.",
                ),
                _source(
                    "Australian Health Practitioner Regulation Agency, Registers "
                    "of practitioners",
                    "https://www.ahpra.gov.au/Registration/Registers-of-Practitioners.aspx",
                    "Retrieved 2026-08-19",
                    "If you have a complaint about a service or fee, or a dispute "
                    "with a health service provider (such as a hospital, clinic or "
                    "a health practitioner) you should contact the relevant "
                    "healthcare complaints organisation in your state or "
                    "territory. They also manage complaints about other people "
                    "working in healthcare that are not registered health "
                    "practitioners (such as nutritionists, masseuses, naturopaths, "
                    "homeopaths, dieticians, social workers and speech "
                    "pathologists.).",
                ),
            ],
            reading=[
                "The regulator's list of health professionals names ten specific "
                "occupations and otherwise requires registration under a state or "
                "territory law. Speech pathology is not on the list.",
                "The national regulator states in its own words that speech "
                "pathologists are among the people working in healthcare who are "
                "not registered health practitioners. Australian speech pathology "
                "is self regulated through professional certification, which the "
                "engineering plan already records.",
                "Read together, the likely position is that a speech pathologist "
                "is not a health professional under the Medical Devices "
                "Regulations. That is a technical regulatory classification and "
                "says nothing whatever about their expertise or standing.",
                "Two consequences follow and both cut against the project. The "
                "clinical decision support exemption is built around supporting a "
                "health professional, so software built for speech pathologists "
                "may not reach it. And the Rule 4.5 reduction of one class for "
                "providing information to a relevant health professional may be "
                "unavailable for the same reason, leaving the higher consumer "
                "facing classification in place.",
            ],
            confidence="reading_with_material_uncertainty",
            unresolved=[
                {
                    "question": "Whether the Regulations' definition is exhaustive "
                    "or merely inclusive, given the guidance renders it with the "
                    "word includes.",
                    "why_it_cannot_be_settled_here": "The guidance paraphrases the "
                    "Regulations rather than quoting the definition in full, and "
                    "the definition itself was not read at source here.",
                    "who_must_settle_it": "An Australian regulatory specialist, "
                    "reading the Therapeutic Goods (Medical Devices) Regulations "
                    "2002 definition directly.",
                }
            ],
            consequences=[
                "This is a genuinely non obvious trap. A designer would reasonably "
                "assume that routing a result to a speech pathologist is the "
                "cautious, lower risk choice, and under this reading it may not "
                "reduce the regulatory burden at all.",
                "It also matters to the governance package, which correctly treats "
                "speech pathology certification and practitioner registration as "
                "different things.",
            ],
            decided_by=[
                "australian_regulatory_specialist",
                "independent_professional_governance_group",
            ],
        ),
        _record(
            question_id="clinical_decision_support_exemption",
            domain="medical_device_regulation",
            question="Could the clinical decision support exemption reduce the "
            "burden for any version of this project?",
            applies_to_purposes=[P3],
            primary_sources=[
                _source(
                    "Therapeutic Goods Administration, Understanding clinical "
                    "decision support system software regulation",
                    "https://www.tga.gov.au/resources/guidance/understanding-clinical-decision-support-system-software-regulation",
                    "Retrieved 2026-08-19",
                    "If your software provides decision support directly to "
                    "patients (or any non-health professional user) it also does "
                    "not qualify for the exemption. ... With the rapid uptake of "
                    "artificial intelligence and its growing incorporation into "
                    "medical devices, it is important to understand that an "
                    "AI-enabled CDSS will not meet the exemption criteria.",
                ),
                _source(
                    "Therapeutic Goods Administration, Understanding clinical "
                    "decision support system software regulation, exemption "
                    "criteria",
                    "https://www.tga.gov.au/resources/guidance/understanding-clinical-decision-support-system-software-regulation",
                    "Retrieved 2026-08-19",
                    "(a) is intended by its manufacturer to be for the sole "
                    "purpose of providing or supporting a recommendation to a "
                    "health professional about preventing, diagnosing, curing or "
                    "alleviating a disease, ailment, defect or injury in persons; "
                    "and (b) is not intended to directly process or analyse a "
                    "medical image or signal from another medical device "
                    "(including an in vitro diagnostic device); and (c) is not "
                    "intended to replace the clinical judgement of a health "
                    "professional in relation to making a clinical diagnosis or "
                    "decision about the treatment of patients",
                ),
            ],
            reading=[
                "No. Three independent reasons close it, and any one would be "
                "enough.",
                "The exemption is unavailable for software that provides decision "
                "support directly to patients or any non health professional user, "
                "which rules out every consumer facing design.",
                "The regulator states plainly that an AI-enabled clinical decision "
                "support system will not meet the exemption criteria. This project "
                "is built on machine learning components throughout.",
                "Criterion (a) requires the sole purpose of supporting a "
                "recommendation to a health professional, and the health "
                "professional definition may not include speech pathologists.",
            ],
            confidence="clear_on_the_face_of_the_source",
            consequences=[
                "There is no lighter regulatory route available by describing a "
                "future screening feature as decision support. That door is shut "
                "before the argument starts.",
            ],
            decided_by=["australian_regulatory_specialist"],
        ),
        _record(
            question_id="supply_sponsor_and_the_missing_entity",
            domain="medical_device_regulation",
            question="What does supplying software in Australia mean, and what "
            "does the absence of a legal entity do to it?",
            applies_to_purposes=[P2, P3],
            primary_sources=[
                _source(
                    "Therapeutic Goods Administration, Understanding how we "
                    "regulate software-based medical devices, Definition of supply",
                    "https://www.tga.gov.au/resources/guidance/understanding-how-we-regulate-software-based-medical-devices",
                    "Published and last updated 24 February 2026",
                    "Under the Therapeutic Goods Act 1989, supply means providing "
                    "therapeutic goods by any method, including sale, exchange, "
                    "gift, lease, loan, hire, offering as a sample or through "
                    "advertising. This definition applies whether the goods are "
                    "provided for payment or free of charge. ... If software is "
                    "made available to users in Australia, whether through an app "
                    "store, cloud platform, or website, it is considered to be "
                    "supplied in Australia.",
                ),
                _source(
                    "Therapeutic Goods Administration, Understanding how we "
                    "regulate software-based medical devices, sponsor obligations",
                    "https://www.tga.gov.au/resources/guidance/understanding-how-we-regulate-software-based-medical-devices",
                    "Published and last updated 24 February 2026",
                    "When a software product that meets the definition of a "
                    "medical device is supplied in this way, the sponsor must: be "
                    "an Australian legal entity responsible for the device; ensure "
                    "the device is included in the ARTG; comply with all relevant "
                    "regulatory obligations, including those relating to "
                    "advertising, safety, and post-market monitoring.",
                ),
                _source(
                    "Therapeutic Goods Administration, Understanding how we "
                    "regulate software-based medical devices, software updates",
                    "https://www.tga.gov.au/resources/guidance/understanding-how-we-regulate-software-based-medical-devices",
                    "Published and last updated 24 February 2026",
                    "Software updates can affect the intended purpose of a product "
                    "and change its status for the purpose of regulation. If an "
                    "update introduces new functionality, such as introducing "
                    "diagnostic support, treatment recommendations, or clinical "
                    "monitoring, the software may now meet the definition of a "
                    "medical device, even if it was not previously regulated.",
                ),
            ],
            reading=[
                "Free does not mean unsupplied. The definition expressly covers "
                "gift and provision free of charge, and making software available "
                "through a website or app store is supply in Australia.",
                "If the software is a medical device, the sponsor must be an "
                "Australian legal entity. There is no version of that obligation "
                "that an individual with no entity can satisfy by being careful.",
                "This is the third separate place the missing legal entity has "
                "blocked a route concretely rather than formally. The source "
                "survey found it blocking the largest relevant intelligibility "
                "corpus through a data use agreement countersignature. The "
                "clinical trial pathway requires an Australian sponsor. And here "
                "it is a precondition of lawful supply.",
                "A shipped product's regulatory status is not fixed at launch. An "
                "update that adds diagnostic or monitoring functionality can pull "
                "a previously unregulated product into the framework.",
            ],
            confidence="clear_on_the_face_of_the_source",
            consequences=[
                "Deciding whether to create a legal entity is not an administrative "
                "matter to be handled later. It gates the research reference data, "
                "the trial pathway and any regulated supply.",
                "A release process for this product would need a step that asks "
                "whether an update changed the intended purpose, and that step is "
                "a regulatory control rather than a nicety.",
            ],
            decided_by=["owner", "australian_regulatory_specialist"],
        ),
    ]
)

CLINICAL_TRIAL_RECORDS = [
    _record(
        question_id="clinical_trial_pathway",
        domain="clinical_trial_regulation",
        question="Would the future checkpoint 23C or 23D research be a clinical "
        "trial requiring a notification or an approval?",
        applies_to_purposes=[P1],
        primary_sources=[
            _source(
                "Therapeutic Goods Administration, How we regulate Australian "
                "clinical trials that use unapproved therapeutic goods",
                "https://www.tga.gov.au/products/unapproved-therapeutic-goods/access-pathways/clinical-trials/how-we-regulate-australian-clinical-trials-use-unapproved-therapeutic-goods",
                "Last updated 26 May 2025",
                "Before you conduct a clinical trial in Australia, you must "
                "consult your HREC to determine if: your study is a clinical "
                "trial; your study involves an unapproved therapeutic good; an "
                "exemption under the CTN or CTA scheme is appropriate. We don't "
                "give advice on these matters.",
            ),
            _source(
                "Therapeutic Goods Administration, How we regulate Australian "
                "clinical trials that use unapproved therapeutic goods",
                "https://www.tga.gov.au/products/unapproved-therapeutic-goods/access-pathways/clinical-trials/how-we-regulate-australian-clinical-trials-use-unapproved-therapeutic-goods",
                "Last updated 26 May 2025",
                "The CTN and CTA schemes are required to lawfully import or supply "
                "an unapproved therapeutic good for experimental purposes in "
                "humans in accordance with the Therapeutic Goods Act 1989. ... "
                "Will you be supplying unapproved therapeutic goods for use in "
                "humans in your research? If yes - you need a CTA or CTN.",
            ),
            _source(
                "Therapeutic Goods Administration, Clinical Trial Notification "
                "(CTN) scheme",
                "https://www.tga.gov.au/products/unapproved-therapeutic-goods/access-pathways/clinical-trials/clinical-trial-notification-ctn-scheme",
                "Last updated 9 April 2025",
                "A CTN is submitted by the Australian clinical trial sponsor. ... "
                "Alongside the CTN submission, you need approval from: The Human "
                "Research Ethics Committee (HREC); The institution or organisation "
                "where the trial will be carried out (Approving Authority). It is "
                "the responsibility of the Australian clinical trial sponsor to "
                "have all relevant approvals in place.",
            ),
        ],
        reading=[
            "The trigger is supplying an unapproved therapeutic good for use in "
            "humans. If the research software is not a medical device at all, "
            "which is the reading for the developer research only purpose, the "
            "schemes do not engage.",
            "There is a genuine argument either way about whether software that "
            "analyses recordings afterwards is supplied for use in humans when "
            "participants only perform a speech task and never touch the software. "
            "That argument is available and untested, and this record does not "
            "resolve it.",
            "The regulator will not resolve it either. It says in its own words "
            "that the researcher must consult their ethics committee to determine "
            "whether the study is a clinical trial, and that it does not give "
            "advice on the question.",
            "That makes the question structurally unanswerable for this project "
            "today. Deciding it requires an ethics committee, and obtaining one is "
            "itself unresolved.",
            "If the answer were ever yes, all three of the missing pieces appear "
            "at once: an Australian sponsor, an ethics committee approval and an "
            "institution acting as approving authority.",
        ],
        confidence="unresolved_needs_specialist",
        unresolved=[
            {
                "question": "Whether checkpoint 23C or 23D would be a clinical "
                "trial, and whether the research software would be an unapproved "
                "therapeutic good supplied for use in humans.",
                "why_it_cannot_be_settled_here": "The regulator expressly declines "
                "to advise on it and assigns the determination to a human research "
                "ethics committee, which this project does not have.",
                "who_must_settle_it": "A human research ethics committee, with an "
                "Australian regulatory specialist.",
            }
        ],
        consequences=[
            "This is a clean example of a question public research cannot close by "
            "being more thorough. The answer is defined as somebody else's "
            "determination.",
            "It also means the ethics route and the regulatory route are not "
            "independent. The regulatory question waits on the ethics committee, "
            "and the ethics committee is the thing hardest to obtain.",
        ],
        decided_by=[
            "human_research_ethics_committee_or_review_body",
            "australian_regulatory_specialist",
        ],
    ),
]

PRIVACY_ACT = (
    "Privacy Act 1988 (Cth)",
    "https://www.legislation.gov.au/C2004A03712/latest/text",
    "Compilation in force 4 June 2026",
)

PRIVACY_RECORDS = [
    _record(
        question_id="privacy_act_application_to_an_individual",
        domain="privacy",
        question="Does the Privacy Act apply to a solo researcher with no company, "
        "and does the absence of a legal entity help or hurt?",
        applies_to_purposes=[P1],
        primary_sources=[
            _source(
                f"{PRIVACY_ACT[0]}, section 7B(1), Individuals in non-business "
                "capacity",
                PRIVACY_ACT[1],
                PRIVACY_ACT[2],
                "An act done, or practice engaged in, by an organisation that is "
                "an individual is exempt for the purposes of paragraph 7(1)(ee) if "
                "the act is done, or the practice is engaged in, other than in the "
                "course of a business carried on by the individual.",
            ),
            _source(
                f"{PRIVACY_ACT[0]}, section 16",
                PRIVACY_ACT[1],
                PRIVACY_ACT[2],
                "Nothing in the Australian Privacy Principles applies to: (a) the "
                "collection, holding, use or disclosure of personal information by "
                "an individual; or (b) personal information held by an individual; "
                "only for the purposes of, or in connection with, his or her "
                "personal, family or household affairs.",
            ),
            _source(
                f"{PRIVACY_ACT[0]}, section 6D(4)",
                PRIVACY_ACT[1],
                PRIVACY_ACT[2],
                "However, an individual, body corporate, partnership, "
                "unincorporated association or trust is not a small business "
                "operator if he, she or it: ... (b) provides a health service to "
                "another individual and holds any health information except in an "
                "employee record; or (c) discloses personal information about "
                "another individual to anyone else for a benefit, service or "
                "advantage ...",
            ),
        ],
        reading=[
            "The protection an unincorporated individual actually has is section "
            "7B(1), which exempts acts done other than in the course of a business "
            "carried on by the individual. It is not the small business exemption "
            "and not the personal affairs carve out.",
            "Section 16 is narrower and probably does not help. It applies only "
            "where the purpose is solely personal, family or household, and "
            "building a research corpus is not that.",
            "The absence of a legal entity is therefore not a safe harbour. It "
            "changes which provision does the work. Section 7B(1) holds only for "
            "as long as no business is carried on, and it would stop covering the "
            "research the moment the work became commercial in any way.",
            "The health service limb in section 6D(4)(b) removes small business "
            "operator status at any turnover including zero, so it matters as soon "
            "as any business exists. Whether a speech research study is a health "
            "service is itself unresolved.",
        ],
        confidence="reading_with_material_uncertainty",
        unresolved=[
            {
                "question": "Whether a speech research study is a health service "
                "within section 6FB, whose test turns on what either the "
                "participant or the researcher intends or claims.",
                "why_it_cannot_be_settled_here": "The definition contains no "
                "research carve out and no published guidance addresses research. "
                "A participant who believes the session tells them something about "
                "their speech health could bring it inside on the participant's "
                "intention alone.",
                "who_must_settle_it": "An Australian privacy lawyer.",
            },
            {
                "question": "Whether the privacy policy obligations in Australian "
                "Privacy Principle 1 survive the section 7B(1) exemption, given "
                "that the exemption operates on acts and practices while a policy "
                "obligation is closer to a standing state of affairs.",
                "why_it_cannot_be_settled_here": "No guidance or case law "
                "addressing the point was located.",
                "who_must_settle_it": "An Australian privacy lawyer.",
            },
        ],
        consequences=[
            "Any move toward commercial activity changes the privacy analysis "
            "before it changes anything else, and it does so silently.",
            "The engineering plan's requirement that qualified review name every "
            "entity and determine Australian Privacy Principle coverage is "
            "therefore not boilerplate. The coverage question genuinely turns on "
            "facts only the owner knows.",
        ],
        decided_by=["australian_privacy_lawyer", "owner"],
    ),
    _record(
        question_id="speech_recordings_as_sensitive_information",
        domain="privacy",
        question="Are speech recordings personal information, and can they be "
        "sensitive information?",
        applies_to_purposes=[P1, P2, P3],
        primary_sources=[
            _source(
                f"{PRIVACY_ACT[0]}, section 6FA, Meaning of health information",
                PRIVACY_ACT[1],
                PRIVACY_ACT[2],
                "The following information is health information: (a) information "
                "or an opinion about: (i) the health, including an illness, "
                "disability or injury, (at any time) of an individual ... that is "
                "also personal information; (b) other personal information "
                "collected to provide, or in providing, a health service to an "
                "individual ...",
            ),
            _source(
                f"{PRIVACY_ACT[0]}, section 6(1), definition of sensitive "
                "information",
                PRIVACY_ACT[1],
                PRIVACY_ACT[2],
                "sensitive information means: ... (b) health information about an "
                "individual; or (c) genetic information about an individual that "
                "is not otherwise health information; or (d) biometric information "
                "that is to be used for the purpose of automated biometric "
                "verification or biometric identification; or (e) biometric "
                "templates.",
            ),
            _source(
                f"{PRIVACY_ACT[0]}, Schedule 1, Australian Privacy Principle 3.3",
                PRIVACY_ACT[1],
                PRIVACY_ACT[2],
                "An APP entity must not collect sensitive information about an "
                "individual unless: (a) the individual consents to the collection "
                "of the information and: ... (ii) if the entity is an "
                "organisation, the information is reasonably necessary for one or "
                "more of the entity's functions or activities; or (b) subclause "
                "3.4 applies in relation to the information.",
            ),
        ],
        reading=[
            "The shortest route from a speech recording to sensitive information "
            "is the health information one, and it does not require a health "
            "service. Section 6FA(a)(i) covers information or an opinion about the "
            "health, including an illness, disability or injury, of an individual. "
            "A recording that evidences a speech or neurological condition is on "
            "its face that.",
            "The biometric route is narrower than it first looks. Limb (d) is "
            "conditional on the information being used for automated biometric "
            "verification or identification, which research on speech production "
            "would not be. Limb (e), biometric templates, carries no such "
            "condition, and whether a learned speaker embedding is a biometric "
            "template is undefined in the Act.",
            "If recordings are sensitive information and the researcher is an "
            "Australian Privacy Principle entity, collection needs consent and "
            "must be reasonably necessary. Consent here means express consent in "
            "practice, not inferred consent.",
            "The engineering plan already says an identifiable voice recording is "
            "personal information and is not automatically biometric sensitive "
            "information. That remains right. This record sharpens it: the health "
            "content route is the one to worry about, and it can engage on content "
            "alone.",
        ],
        confidence="reading_with_material_uncertainty",
        unresolved=[
            {
                "question": "Whether a learned speaker embedding or voice model "
                "derived from a recording is a biometric template.",
                "why_it_cannot_be_settled_here": "Neither biometric information "
                "nor biometric template is defined in the Act, and no guidance "
                "defining them was located.",
                "who_must_settle_it": "An Australian privacy lawyer.",
            }
        ],
        conflicts=[
            "The regulator's consumer facing guidance on biometric scanning "
            "states without qualification that voice is biometric information and "
            "that biometric information is sensitive information. The statutory "
            "definition and the regulator's own Australian Privacy Principle "
            "guidelines both carry the qualifier that it must be information to be "
            "used for automated biometric verification or identification. The two "
            "are recorded and not reconciled here. This conflict was reported by a "
            "research pass that read both pages; the statutory wording was read "
            "directly at the compilation and is the extract quoted above.",
        ],
        consequences=[
            "Consent design cannot treat audio as ordinary personal information. "
            "The plan's separate consent decisions already assume this.",
            "A future feature that identifies or verifies a speaker would change "
            "the classification by itself, independently of what is recorded.",
        ],
        decided_by=["australian_privacy_lawyer", "owner"],
    ),
]

PRIVACY_RECORDS.extend(
    [
        _record(
            question_id="statutory_tort_serious_invasion_of_privacy",
            domain="privacy",
            question="Is there a privacy exposure that applies to an individual "
            "regardless of whether the Privacy Act does?",
            applies_to_purposes=[P1, P2, P3],
            primary_sources=[
                _source(
                    f"{PRIVACY_ACT[0]}, Schedule 2, Part 2, clause 7, Cause of "
                    "action",
                    PRIVACY_ACT[1],
                    PRIVACY_ACT[2],
                    "(1) An individual (the plaintiff) has a cause of action in "
                    "tort against another person (the defendant) if: (a) the "
                    "defendant invaded the plaintiff's privacy by doing one or "
                    "both of the following: (i) intruding upon the plaintiff's "
                    "seclusion; (ii) misusing information that relates to the "
                    "plaintiff; and (b) a person in the position of the plaintiff "
                    "would have had a reasonable expectation of privacy in all of "
                    "the circumstances; and (c) the invasion of privacy was "
                    "intentional or reckless; and (d) the invasion of privacy was "
                    "serious; and (e) the public interest in the plaintiff's "
                    "privacy outweighed any countervailing public interest. (2) "
                    "The invasion of privacy is actionable without proof of "
                    "damage.",
                ),
                _source(
                    f"{PRIVACY_ACT[0]}, Schedule 2, Part 2, clause 7(5)",
                    PRIVACY_ACT[1],
                    PRIVACY_ACT[2],
                    "Without limiting the matters that the court may consider in "
                    "determining whether a person in the position of the plaintiff "
                    "would have had a reasonable expectation of privacy in all of "
                    "the circumstances, the court may consider the following: (a) "
                    "the means, including the use of any device or technology, "
                    "used to invade the plaintiff's privacy; (b) the purpose of "
                    "the invasion of privacy; (c) attributes of the plaintiff "
                    "including the plaintiff's age, occupation or cultural "
                    "background ...",
                ),
                _source(
                    f"{PRIVACY_ACT[0]}, endnotes, commencement of Schedule 2",
                    PRIVACY_ACT[1],
                    PRIVACY_ACT[2],
                    "sch 2: 10 June 2025 (s 2(1) item 8)",
                ),
            ],
            reading=[
                "Yes, and it is the single most important thing in this reading "
                "that the repository did not previously record. A statutory tort "
                "of serious invasion of privacy has been in force since 10 June "
                "2025.",
                "It runs against another person. There is no entity requirement, "
                "no turnover threshold and no Australian Privacy Principle entity "
                "analysis. Every shield discussed in the other privacy records is "
                "irrelevant to it.",
                "It is actionable without proof of damage, and the court is "
                "expressly directed to consider the means and technology used and "
                "the purpose of the invasion.",
                "A research pass that read the exemptions in Part 3 of Schedule 2 "
                "reported that they cover journalism, agencies, their staff, law "
                "enforcement and intelligence, and that there is no research or "
                "academic exemption. The cause of action and its commencement were "
                "read directly at the compilation; the absence of a research "
                "exemption is reported from that pass and was not separately "
                "verified here.",
            ],
            confidence="clear_on_the_face_of_the_source",
            unresolved=[
                {
                    "question": "Whether consent obtained for a research recording "
                    "would engage the consent defence for every later use of that "
                    "recording.",
                    "why_it_cannot_be_settled_here": "The defence turns on the "
                    "scope of what was consented to, which depends on consent "
                    "documents that do not exist.",
                    "who_must_settle_it": "An Australian privacy lawyer.",
                }
            ],
            consequences=[
                "Adam is personally exposed to this whether or not he ever forms a "
                "company, and forming one would not by itself remove it.",
                "It raises the practical importance of the incidental speaker "
                "controls the plan already requires, because an incidental speaker "
                "is exactly a person with a reasonable expectation of privacy who "
                "never consented to anything.",
                "It should be added to the future privacy impact assessment as its "
                "own item rather than folded into Australian Privacy Principle "
                "compliance, because compliance with the principles is not a "
                "defence to it.",
            ],
            decided_by=["australian_privacy_lawyer", "owner"],
        ),
        _record(
            question_id="automated_decision_transparency_from_december_2026",
            domain="privacy",
            question="What changes on 10 December 2026 for software that makes "
            "decisions about people?",
            applies_to_purposes=[P2, P3],
            primary_sources=[
                _source(
                    "Privacy and Other Legislation Amendment Act 2024 (Cth), "
                    "Schedule 1 Part 15, inserting Australian Privacy Principle "
                    "1.7 into Schedule 1 of the Privacy Act 1988",
                    "https://www.legislation.gov.au/C2024A00128/latest/text",
                    "Act No. 128 of 2024, as made 10 December 2024",
                    "1.7 Without limiting subclause 1.3, the APP privacy policy of "
                    "an APP entity must contain the information covered by "
                    "subclause 1.8 if: (a) the entity has arranged for a computer "
                    "program to make, or do a thing that is substantially and "
                    "directly related to making, a decision; and (b) the decision "
                    "could reasonably be expected to significantly affect the "
                    "rights or interests of an individual; and (c) personal "
                    "information about the individual is used in the operation of "
                    "the computer program to make the decision or do the thing "
                    "that is substantially and directly related to making the "
                    "decision.",
                ),
                _source(
                    "Privacy and Other Legislation Amendment Act 2024 (Cth), "
                    "Schedule 1 Part 15, inserted Australian Privacy Principle 1.9",
                    "https://www.legislation.gov.au/C2024A00128/latest/text",
                    "Act No. 128 of 2024, as made 10 December 2024",
                    "For the purposes of subclauses 1.7 and 1.8: (a) making a "
                    "decision includes refusing or failing to make a decision; and "
                    "(b) doing a thing includes refusing or failing to do a thing; "
                    "and (c) a decision may affect the rights or interests of an "
                    "individual, whether the rights or interests of the individual "
                    "are adversely or beneficially affected ...",
                ),
            ],
            reading=[
                "From 10 December 2026 an Australian Privacy Principle entity "
                "whose software makes, or materially contributes to, decisions "
                "that could significantly affect a person's rights or interests "
                "must say so in its privacy policy and describe the kinds of "
                "information and decisions involved.",
                "The obligation is a transparency one about the privacy policy. It "
                "does not prohibit automated decisions and does not create a right "
                "to human review.",
                "Note that clause 1.9(c) covers beneficial as well as adverse "
                "effects, so a feature that helps someone is not outside it.",
                "The current research makes no such decision, and the obligation "
                "binds Australian Privacy Principle entities, so it does not apply "
                "to a solo researcher covered by the non business exemption. It "
                "becomes live at exactly the point the project becomes a product "
                "operated by an entity.",
            ],
            confidence="clear_on_the_face_of_the_source",
            unresolved=[
                {
                    "question": "Whether a coaching output that changes what a "
                    "person practises would be a decision that could reasonably be "
                    "expected to significantly affect their rights or interests.",
                    "why_it_cannot_be_settled_here": "The threshold is untested "
                    "and the regulator's detailed guidance on the new obligation "
                    "had not been published when this was read.",
                    "who_must_settle_it": "An Australian privacy lawyer.",
                }
            ],
            consequences=[
                "The existing plan already requires the future privacy impact "
                "assessment to record whether any future feature crosses this "
                "boundary rather than waiting for release. This record supplies "
                "the exact test it must be recorded against.",
            ],
            decided_by=["australian_privacy_lawyer"],
        ),
    ]
)

RECORDING_LAW_RECORDS = [
    _record(
        question_id="queensland_recording_and_publication",
        domain="recording_and_surveillance_law",
        question="What does Queensland law permit when recording a person's "
        "speech, and what does it permit afterwards?",
        applies_to_purposes=[P1],
        primary_sources=[
            _source(
                "Invasion of Privacy Act 1971 (Qld), section 43",
                "https://www.legislation.qld.gov.au/view/pdf/inforce/current/act-1971-050",
                "Current as at 1 July 2024",
                "(1) A person is guilty of an offence against this Act if the "
                "person uses a listening device to overhear, record, monitor or "
                "listen to a private conversation and is liable on conviction on "
                "indictment to a maximum penalty of 40 penalty units or "
                "imprisonment for 2 years. (2) Subsection (1) does not apply, (a) "
                "where the person using the listening device is a party to the "
                "private conversation ...",
            ),
            _source(
                "Invasion of Privacy Act 1971 (Qld), section 45",
                "https://www.legislation.qld.gov.au/view/pdf/inforce/current/act-1971-050",
                "Current as at 1 July 2024",
                "(1) A person who, having been a party to a private conversation "
                "and having used a listening device to overhear, record, monitor "
                "or listen to that conversation, subsequently communicates or "
                "publishes to any other person any record of the conversation "
                "made, directly or indirectly, by the use of the listening device "
                "or any statement prepared from such a record is guilty of an "
                "offence against this Act and is liable on conviction on "
                "indictment to a maximum penalty of 40 penalty units or "
                "imprisonment for 2 years. (2) Subsection (1) does not apply where "
                "the communication or publication, (a) is made to another party to "
                "the private conversation or with the consent, express or implied, "
                "of all other parties to the private conversation ...",
            ),
            _source(
                "Penalties and Sentences Regulation 2025 (Qld), section 4",
                "https://www.legislation.qld.gov.au/view/pdf/inforce/current/sl-2025-0106",
                "Current as at 1 July 2026",
                "For section 5A(1) of the Act, the value prescribed is $172.70.",
            ),
        ],
        reading=[
            "Recording and sharing are two separate questions with two separate "
            "answers, and the second is the one that bites on a research pipeline.",
            "Section 43(2)(a) permits a party to a private conversation to record "
            "it. That is the well known position and it is about recording only.",
            "Section 45(1) then makes it an offence for that same party to "
            "communicate or publish the record to any other person, unless all "
            "other parties consented. Handing recordings to trained annotators or "
            "listeners is on its face communicating a record to another person.",
            "Section 45(1) expressly extends to any statement prepared from such a "
            "record, so transcripts and derived documents are caught too, not only "
            "the audio.",
            "There is a prior question. Whether a recorded research session is a "
            "private conversation at all depends on the section 4 definition, "
            "which excludes circumstances in which a person ought reasonably to "
            "expect the words may be recorded. A properly consented research "
            "recording may fall outside the definition entirely, which would make "
            "both sections moot.",
            "At the current prescribed value of $172.70 per penalty unit, the "
            "40 penalty unit maximum is $6,908, or two years imprisonment. This "
            "arithmetic is the reader's own; the value and the unit count are "
            "quoted above.",
        ],
        confidence="reading_with_material_uncertainty",
        unresolved=[
            {
                "question": "Whether a consented research recording session is a "
                "private conversation within the section 4 definition.",
                "why_it_cannot_be_settled_here": "It turns on the circumstances "
                "and on the actual consent documents, which do not exist.",
                "who_must_settle_it": "A Queensland lawyer, reading the final "
                "consent materials.",
            },
            {
                "question": "Whether Queensland has enacted surveillance devices "
                "legislation replacing this Act.",
                "why_it_cannot_be_settled_here": "The 1971 Act was confirmed still "
                "in force in its 1 July 2024 form, and a research pass reported "
                "secondary commentary about a reform proposal that could not be "
                "confirmed at the Queensland legislation register. The question is "
                "recorded as open rather than answered either way.",
                "who_must_settle_it": "A Queensland lawyer.",
            },
        ],
        consequences=[
            "Consent must cover onward communication to annotators and listeners, "
            "not only the act of recording. A consent form that only permits "
            "recording could leave the annotation step exposed.",
            "This is a criminal provision applying to a natural person. It has no "
            "entity requirement and no turnover threshold, so it applies to Adam "
            "personally today.",
        ],
        decided_by=["queensland_lawyer", "owner"],
    ),
    _record(
        question_id="commonwealth_interception_scope",
        domain="recording_and_surveillance_law",
        question="Does Commonwealth interception law apply to recording speech on "
        "a local device?",
        applies_to_purposes=[P1],
        primary_sources=[
            _source(
                "Telecommunications (Interception and Access) Act 1979 (Cth), "
                "section 6(1)",
                "https://www.legislation.gov.au/C2004A02124/latest/text",
                "Compilation in force 4 June 2026",
                "For the purposes of this Act (other than Schedule 1), but subject "
                "to this section, interception of a communication passing over a "
                "telecommunications system consists of listening to or recording, "
                "by any means, such a communication in its passage over that "
                "telecommunications system without the knowledge of the person "
                "making the communication.",
            ),
            _source(
                "Telecommunications (Interception and Access) Act 1979 (Cth), "
                "section 7(1)",
                "https://www.legislation.gov.au/C2004A02124/latest/text",
                "Compilation in force 4 June 2026",
                "A person shall not: (a) intercept; (b) authorize, suffer or "
                "permit another person to intercept; or (c) do any act or thing "
                "that will enable him or her or another person to intercept; a "
                "communication passing over a telecommunications system.",
            ),
        ],
        reading=[
            "No. The prohibition is confined to a communication passing over a "
            "telecommunications system, and the definition of interception "
            "requires the recording to happen in its passage over that system.",
            "Recording a person speaking into a microphone in the same room does "
            "not meet the definition, so Queensland law rather than Commonwealth "
            "interception law is the operative rule.",
            "This changes if a session is ever conducted over a phone or voice "
            "call and recorded in transit, which would need its own reading.",
        ],
        confidence="clear_on_the_face_of_the_source",
        consequences=[
            "This closes an open item the engineering plan lists, which required "
            "legal review to map Commonwealth interception questions. The reading "
            "narrows that to the case where capture happens over a call.",
        ],
        decided_by=["queensland_lawyer"],
    ),
]

NS_2025 = (
    "NHMRC National Statement on Ethical Conduct in Human Research (2025)",
    "https://www.nhmrc.gov.au/sites/default/files/documents/attachments/publications/National-Statement-on-Ethical-Conduct-Human-Research-25.pdf",
    "Published 2025; NHMRC states it came into effect on 23 June 2026",
)

ETHICS_RECORDS = [
    _record(
        question_id="ethics_review_for_an_unaffiliated_individual",
        domain="research_ethics",
        question="Can a researcher with no institution obtain the ethics review "
        "this research would need in Australia?",
        applies_to_purposes=[P1],
        primary_sources=[
            _source(
                "NHMRC, National Statement on Ethical Conduct in Human Research",
                "https://www.nhmrc.gov.au/research-policy/ethics/national-statement-ethical-conduct-human-research",
                "Retrieved 2026-08-19",
                "The 2025 National Statement came into effect on 23 June 2026. "
                "... Compliance with the National Statement is a prerequisite for "
                "receipt of NHMRC funding.",
            ),
            _source(
                f"{NS_2025[0]}, paragraph 5.1.11",
                NS_2025[1],
                NS_2025[2],
                "If a research project is assessed as having more than low risk, "
                "it must be reviewed by an HREC.",
            ),
            _source(
                f"{NS_2025[0]}, paragraph 5.1.15",
                NS_2025[1],
                NS_2025[2],
                "Some research may be eligible for exemption from ethics review. "
                "The institution responsible for the research may choose to exempt "
                "from ethics review research that meets the criteria set out in "
                "paragraph 5.1.17. Where there is no institution providing "
                "oversight of the research, researchers should request a grant of "
                "exemption from an ethics review body.",
            ),
            _source(
                f"{NS_2025[0]}, paragraph 5.1.16",
                NS_2025[1],
                NS_2025[2],
                "Research that involves the use of personal information without "
                "consent cannot be granted an exemption from ethics review "
                "because, to conduct such research, a waiver of the requirement "
                "for consent would need to be granted by an appropriate ethics "
                "review body.",
            ),
            _source(
                "NHMRC, Human Research Ethics Committees",
                "https://www.nhmrc.gov.au/research-policy/ethics/human-research-ethics-committees",
                "Retrieved 2026-08-19",
                "Researchers who are not affiliated with an Australian "
                "organisation that has an HREC can contact any HREC from our "
                "registration list (provided above) and discuss matters with them "
                "directly.",
            ),
            _source(
                "Queensland University of Technology, Manual of Policies and "
                "Procedures D/6.5, University Human Research Ethics Committee",
                "https://www.mopp.qut.edu.au/D/D_06_05.jsp",
                "Retrieved 2026-08-19",
                "The University Human Research Ethics Committee normally considers "
                "applications only from QUT staff and students. ... The Committee "
                "does not review projects where there is no QUT involvement. ... A "
                "QUT staff member must be nominated as the project Chief "
                "Investigator and accept ultimate responsibility for the conduct "
                "of the project.",
            ),
            _source(
                "University of Southern Queensland, Human Research Ethics "
                "Procedure",
                "https://policy.unisq.edu.au/documents/181191PL",
                "Retrieved 2026-08-19",
                "The UniSQ HREC does not currently accept applications from "
                "Researchers with no formal affiliation with the University.",
            ),
        ],
        reading=[
            "There is no guaranteed route. No Australian body is obliged to review "
            "an unaffiliated individual's research, and the national guidance goes "
            "no further than saying such researchers may contact committees and "
            "discuss matters with them.",
            "Two Queensland universities checked directly show the realistic "
            "spread. One will not review a project with no involvement of its own "
            "and requires one of its own staff to be the chief investigator; the "
            "other states flatly that it does not accept applications from "
            "unaffiliated researchers.",
            "The National Statement's compliance duties are addressed to "
            "institutions throughout. Its one sentence written for a researcher "
            "with no institution, at paragraph 5.1.15, points to requesting an "
            "exemption from an ethics review body, which still needs a body "
            "willing to entertain the request.",
            "The exemption route is also narrower than it looks for this project. "
            "Paragraph 5.1.16 blocks exemption for research using personal "
            "information without consent, and research recordings of identifiable "
            "voices sit awkwardly with the exemption criteria in any case.",
            "Whether this research would be more than low risk, and therefore "
            "require a full committee under paragraph 5.1.11, is not obvious "
            "either way. A study in which trained listeners rate individuals' "
            "speech has to be assessed against harm categories that include "
            "psychological harm and devaluation of personal worth, and if either "
            "is foreseeable the paragraph applies.",
            "A research pass reported that a private not for profit provider "
            "operating twelve registered committees publishes a self funded "
            "investigator pathway with review fees in the range of roughly three "
            "to seven thousand dollars, and separately requires portal "
            "registration to be authorised through an organisation. Whether it "
            "accepts an applicant with no organisation at all could not be "
            "established from public pages. That is reported rather than verified "
            "here, and it is the decisive practical unknown.",
            "The vocabulary has changed and older notes will be wrong. The 2025 "
            "National Statement does not use the term negligible risk anywhere; "
            "the lower risk band is now low risk or minimal risk.",
        ],
        confidence="reading_with_material_uncertainty",
        unresolved=[
            {
                "question": "Whether any registered committee will accept an "
                "application from an individual with no organisation and no legal "
                "entity.",
                "why_it_cannot_be_settled_here": "No public page states an "
                "eligibility rule either way, and settling it requires contacting "
                "a committee, which the approved research only route prohibits.",
                "who_must_settle_it": "The owner, by deciding whether to make "
                "contact, and then the committee itself.",
            },
            {
                "question": "Whether this research would be assessed as more than "
                "low risk.",
                "why_it_cannot_be_settled_here": "The National Statement assigns "
                "the risk assessment to the institution responsible for the "
                "research, and there is none.",
                "who_must_settle_it": "An ethics review body or responsible "
                "institution.",
            },
        ],
        conflicts=[
            "NHMRC's main National Statement page states that the 2025 version "
            "came into effect on 23 June 2026. A research pass reported that "
            "NHMRC's own update FAQ page still says it will take effect in early "
            "2026, date to be advised. The main page was read directly and is "
            "quoted above; the FAQ divergence is reported and not resolved.",
        ],
        consequences=[
            "Ethics review is not a step that can be scheduled. It is a "
            "dependency on somebody else's willingness, and it currently has no "
            "confirmed supplier.",
            "This compounds with the clinical trial question, which the regulator "
            "assigns to an ethics committee. Both blocked routes are blocked by "
            "the same missing thing.",
            "A research pass also reported that NHMRC is revising the provisions "
            "defining human research and exemption from review, with public "
            "consultation expected. Any reading of those provisions may date.",
        ],
        decided_by=[
            "human_research_ethics_committee_or_review_body",
            "responsible_institution",
            "owner",
        ],
    ),
]

ALL_READINGS = (
    MEDICAL_DEVICE_RECORDS
    + CLINICAL_TRIAL_RECORDS
    + PRIVACY_RECORDS
    + RECORDING_LAW_RECORDS
    + ETHICS_RECORDS
)


# The ladder exists because the answer follows the claim, not the technology.
# Only the first rung is occupied today; the other two are hypothetical and are
# read so that the flip point is known before anything is built.
PURPOSE_LADDER = {
    P1: {
        "rung": "one",
        "description": "A firewalled developer research question, with no result "
        "shown to a participant, a clinician or anybody else, and no software "
        "supplied to anyone. This is the checkpoint 23B draft intended use and the "
        "only rung this repository occupies.",
        "occupied_today": True,
        "medical_device_position": "likely_outside_the_definition",
        "what_still_applies": [
            "Queensland recording and publication law applies to Adam personally "
            "today, and the sharing of recordings with annotators is a separate "
            "question from the recording itself.",
            "The statutory tort of serious invasion of privacy applies regardless "
            "of entity status and has no research exemption.",
            "Research ethics review is required by the National Statement for more "
            "than low risk research, and no route to obtain it is confirmed.",
            "Whether the work would be a clinical trial is a determination the "
            "regulator assigns to an ethics committee and declines to make itself.",
        ],
    },
    P2: {
        "rung": "two",
        "description": "A hypothetical consumer feature that coaches communication "
        "and shows the person measured observations about their own speech, making "
        "no claim about any disease, condition, ailment or defect. Not built, not "
        "approved and not proposed here.",
        "occupied_today": False,
        "medical_device_position": "may_be_a_device_and_may_be_excluded",
        "what_still_applies": [
            "If it is a device, the wellness and coaching exclusions are plausibly "
            "available, and every function of the product must qualify for the "
            "exclusion to hold.",
            "Supply includes free supply through a website or app store, and a "
            "device needs an Australian legal entity as sponsor.",
            "An update that adds diagnostic or monitoring functionality can change "
            "the regulatory status of an already released product.",
            "Privacy obligations engage in full once an entity operates it, "
            "including express consent for sensitive information and, from 10 "
            "December 2026, automated decision transparency in the privacy policy.",
        ],
    },
    P3: {
        "rung": "three",
        "description": "A hypothetical consumer feature that tells a person their "
        "speech may indicate a condition and that they may wish to seek "
        "professional assessment. Not built, not approved and not proposed here. "
        "Checkpoint 23E's described action sits closest to this rung and remains "
        "optional and unapproved.",
        "occupied_today": False,
        "medical_device_position": "device_and_no_exclusion_available",
        "what_still_applies": [
            "The regulator's definition of screening closely matches checkpoint "
            "23E's own description of its action.",
            "The reading is Class IIb where the result goes to the person and the "
            "condition is serious, dropping one class only if it instead informs a "
            "qualifying health professional, which may be unavailable because "
            "speech pathologists are probably not health professionals under the "
            "Regulations.",
            "The clinical decision support exemption is closed for three "
            "independent reasons.",
            "Conformity assessment evidence, ARTG inclusion and an Australian "
            "sponsor all become mandatory.",
        ],
    },
}

STANDING_DISCLAIMER = (
    "This is a documented reading of public sources by a non lawyer who is not an "
    "Australian regulatory specialist. It is not legal advice, regulatory advice, "
    "a classification determination, an approval, an exemption, a defence or a "
    "substitute for the written specialist assessments checkpoint 23B requires. "
    "Every record names the human roles that must actually settle it. Reading the "
    "rules carefully is worth doing and is not the same as being told the answer."
)

WHAT_THIS_IS_NOT = [
    "It is not the privacy impact assessment checkpoint 23B requires. That needs "
    "a legal entity to be the responsible entity, and there is none.",
    "It is not the documented Australian classification and clinical trial pathway "
    "assessment checkpoint 23B requires, because that must be documented by a "
    "qualified Australian specialist.",
    "It is not advice that any purpose on the ladder is safe to build. Rungs two "
    "and three are hypothetical and neither is proposed.",
    "It is not a naming of any condition. Checkpoint 23A prohibits selecting a "
    "named motor speech condition or voice disorder, and no record names one.",
    "It is not progress toward checkpoint 23B acceptance, which is defined as "
    "written review by accountable human roles.",
]

LIMITATIONS = [
    "Sources change. Every source carries the currency the source itself states "
    "and the date it was read, and a stale reading must be redone rather than "
    "trusted.",
    "Where a record's reading rests on a fact reported by a research pass rather "
    "than read at the primary source in this session, the record says so in the "
    "sentence that uses it. Those facts drive no conclusion on their own.",
    "The ladder has three rungs because three were enough to locate the flip "
    "point. Real products occupy positions between them, and a real intended use "
    "statement would be more specific than any rung here.",
    "A reading that a rule does not apply is the weakest kind of reading, because "
    "it depends on nothing else in the statute book applying either, and no search "
    "can prove that.",
    "NHMRC has announced a revision of the provisions defining human research and "
    "exemption from ethics review. The ethics reading may date sooner than the "
    "others.",
]


def build_registry(records):
    domains = {}
    purposes = {P1: 0, P2: 0, P3: 0}
    confidence = {}
    for record in records:
        domains[record["domain"]] = domains.get(record["domain"], 0) + 1
        confidence[record["confidence"]] = confidence.get(record["confidence"], 0) + 1
        for purpose in record["applies_to_purposes"]:
            purposes[purpose] += 1
    unresolved_total = sum(len(record["unresolved"]) for record in records)
    conflicts_total = sum(len(record["conflicts"]) for record in records)
    return {
        "schema_version": "1.0.0",
        "registry_id": "motor_speech_voice_regulatory_reading_v1",
        "checkpoint": "23B",
        "prepared_at": PREPARED_AT,
        "status": "documented_reading_recorded_no_determination_made",
        "record_schema": SCHEMA_FILENAME,
        "standing_disclaimer": STANDING_DISCLAIMER,
        "purpose_ladder": PURPOSE_LADDER,
        "record_count": len(records),
        "records": [
            {
                "question_id": record["question_id"],
                "record_id": record["record_id"],
                "domain": record["domain"],
                "confidence": record["confidence"],
                "applies_to_purposes": list(record["applies_to_purposes"]),
            }
            for record in records
        ],
        "counts": {
            "questions_read": len(records),
            "by_domain": domains,
            "by_purpose": purposes,
            "by_confidence": confidence,
            "open_questions_recorded": unresolved_total,
            "source_conflicts_recorded": conflicts_total,
            "determinations_made": 0,
            "approvals_obtained": 0,
            "advice_received": 0,
        },
        "what_this_is_not": WHAT_THIS_IS_NOT,
        "limitations": LIMITATIONS,
    }


def write_reading():
    READING_ROOT.mkdir(parents=True, exist_ok=True)
    for record in ALL_READINGS:
        path = READING_ROOT / f"{record['question_id']}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    registry_path = READING_ROOT / REGISTRY_FILENAME
    registry_path.write_text(
        json.dumps(build_registry(ALL_READINGS), indent=2, ensure_ascii=False) + "\n"
    )
    return len(ALL_READINGS)


def main():
    written = write_reading()
    print(f"Wrote {written} regulatory reading records and the registry.")
    print("No determination, approval or advice is recorded.")


if __name__ == "__main__":
    main()
