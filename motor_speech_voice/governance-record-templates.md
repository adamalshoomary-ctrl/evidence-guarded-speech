# Checkpoint 23B governance record templates

Version: 1.0.0 draft

Status: blank templates only; no appointment, review, approval or selection

Updated: 2026-08-14

These templates turn future human decisions into evidence that can be checked.
They do not replace an institution's forms, an HREC application, legal advice,
professional assessment, a privacy impact assessment or a regulatory opinion.
No template may be filled until Adam approves the exact outreach and the
responsible organisation approves how private records will be stored.

The public repository keeps blank templates, aggregate decisions and permitted
evidence identifiers or hashes. It must not keep signatures, private contact
details, credentials supplied in confidence, contracts, invoices, private
advice or participant information.

## Record control used by every completed form

```text
Record type:
Record version:
Checkpoint: 23B
Lane or domain:
Candidate question, or none:
Private record identifier:
Created date and timezone:
Decision effective date:
Supersedes record identifier, or none:
Public contract version reviewed:
Public contract SHA 256:
Review package version reviewed:
Attachments and their private identifiers:
Public evidence metadata ID:
Evidence type:
Issuer role ID:
Responsible opaque assignment ID:
Institution issued opaque ID, or none:
Storage class:
Candidate question ID, or none for reusable competence or identity evidence:
Artifact SHA 256 of the exact signed or institution-issued bytes:
Public evidence-node SHA 256:
Dependency evidence-node SHA 256 values:
Issued final status:
Public summary permitted: yes, no, or specified text
Retention and deletion authority:
```

Every correction creates a new version. The original record remains auditable.
An unsigned draft, meeting note or email acknowledgement is not a decision.
Every dependency node hash must resolve to the approved parent contract or one
other cited evidence node. A dependent record cannot predate its dependency,
and a dependency loop is invalid. The public node hash is calculated over the
artifact digest, evidence type, issuer, responsible assignment, version, date,
institution ID, storage class, exact scope, candidate ID, dependency hashes and
final status. Changing any claim therefore changes the node identity and every
dependent node. The authorised reviewer must separately verify that the exact
signed or institution-issued artifact expressly attests that same claim block;
the public validator cannot inspect a private signature.

Project decisions bind the exact candidate specifications. Reusable competence
material stays candidate neutral and is cited by the project-specific decision.
Candidate-neutral evidence may not import evidence from another lane. If stable
identity source material is reused, the public evidence metadata represents its
dated project-specific verification and authority, not an unsupported copy of
an old identity record. An artifact SHA match proves only that the referenced
bytes did not change. It does not prove that their content is true, sufficient
or professionally sound.

## Owner and legal sponsor identity record

This record must exist before external messages describe a real study sponsor.

```text
Product owner legal name:
Trading or project name, if different:
Owning legal entity name:
Entity type:
Country and state or territory of registration:
Australian Business Number or other identifier, if applicable:
Registered address held privately: yes or no
Who can legally enter research and service contracts:
Proposed research sponsor legal entity:
Proposed responsible APP entities and data-role matrix:
Insurance status:
Institutional affiliation, if any:
Conflicts or related entities:
Qualified legal or governance reviewer:

Decision:
[ ] identity and authority verified for limited outreach
[ ] identity verified but sponsorship ability unresolved
[ ] no capable sponsor identified
[ ] rejected, with reasons

Conditions and reasons:
Owner signature or approved electronic decision:
Qualified reviewer signature, when required:
```

Identity verification does not establish ethics approval, APP coverage,
insurance, institutional responsibility or authority to recruit.

## Role appointment and competence record

Complete one record for every person and every distinct role. One person holding
two roles needs two assessments and cannot hold incompatible roles.

```text
Role ID from the governance contract:
Appointee private identifier:
Organisation and current position:
Appointment start and end:
Payment basis and amount held privately:
Payment independent of outcome: yes or no

Required registration, certification or qualification:
Verification source and date:
Current status verified by:
Beyond entry competence required:
Evidence of recent relevant adult work:
Task, population, language and variety competence:
Accessibility, identity and cultural competence:
Research, measurement or agreement competence, if applicable:
Scope limitations:

Decision rights accepted exactly as written: yes or no
Evidence obligations accepted exactly as written: yes or no
Independence requirements satisfied: yes or no
Conflict record identifier:
Recusals required:

Appointment decision:
[ ] eligible and appointed for this exact role
[ ] conditionally eligible, conditions listed below
[ ] ineligible
[ ] assessment incomplete

Conditions and reasons:
Appointee acknowledgement:
Appointing authority decision:
```

The final package has exactly one opaque product-owner assignment. Every
owner-issued record and every product-owner role decision uses that assignment.
A candidate vendor or developer organisation cannot supply a professional
approval or signed blocker.

## Separation of duties and reference-truth control record

Complete this only if one candidate is selected. Distinct assignments and
distinct organisations must control the six duties below. A required
participant or clinical reference owner joins the same separation matrix;
reusing one organisation under a different assignment is not independent.

```text
Construct-control assignment and organisation:
Task-control assignment and organisation:
Reference-truth assignment and organisation:
Threshold assignment and organisation:
Data-custody assignment and organisation:
Release assignment and organisation:

Reference-truth appointment evidence node:
Reference-truth project-decision evidence node:
Exact selected candidate and lane:
Exact construct, task and measure node dependencies:
Appointment is reusable, candidate neutral and globally scoped: yes or no
Project decision is candidate bound and exactly lane scoped: yes or no
Signed decision held privately or institutionally: yes or no

Participant-reference accountable assignments and organisations, if required:
Clinical-reference accountable assignments and organisations, if required:
No organisation aliases another applicable control duty: yes or no
Independent truth and release group acknowledgement:
```

CPSP alone does not prove adult motor speech or adult voice competence. Ahpra
registration alone does not prove competence for a proposed laryngeal reference.
Academic seniority, a publication or vendor experience is never an appointment.

## Conflict disclosure and recusal record

```text
Person or organisation private identifier:
Roles considered:
Candidate questions affected:

Employment or office holding:
Ownership, shares, options or beneficial interests:
Patents, licences, royalties or inventor interests:
Consulting, referral or service fees:
Research grants, gifts or in kind support:
Publications, methods or instruments whose reputation may be affected:
Supervision, close collaboration or family relationships:
Treating clinician or dependent relationship:
Vendor, developer, reference or dataset involvement:
Other financial, professional, personal or reputational interests:
Nothing to disclose: yes or no

Assessment:
[ ] no material conflict identified
[ ] participation allowed with declared limits
[ ] factual evidence only, no deliberation or vote
[ ] full recusal for the affected question
[ ] role incompatible

Required controls:
Meeting or evidence stages excluded from:
Decision maker for this assessment:
Person acknowledgement:
```

The disclosure is refreshed when circumstances change and before any held out
evidence is opened. Silence is not a declaration of no conflict.

## Lived experience terms and decision record

The group must contain more than one paid adult and must not ask one person to
represent all relevant experiences. Final number and composition follow the
governed population and access plan.

```text
Group private identifier:
Membership selection process:
Experiences represented and important gaps:
Accessible formats and communication support:
Interpreter, AAC, support person or non reading routes:
Payment, expenses and cancellation terms:
Independent support and complaint route:
Right to leave without penalty:
How minority and dissenting views are retained:
Conflicts and recusals:

Draft intended benefit understood: yes, no, or changes required
Population and excluded groups acceptable: yes, no, or changes required
Burden and stopping rules acceptable: yes, no, or changes required
Consent choices acceptable: yes, no, or changes required
Language and identity boundaries acceptable: yes, no, or changes required
Complaint and harm routes acceptable: yes, no, or changes required
Proposed question worth further research: yes, no, or unresolved

Decision:
[ ] accept within this domain
[ ] require changes before another review
[ ] reject the candidate question
[ ] no selection because a meaningful safe benefit is absent

Conditions, reasons, dissent and unsupported groups:
Voting or consensus method:
Member approvals held privately:
```

## Intended use and prohibited use sign off

Each accountable role signs only its own domain. The owner cannot turn a domain
rejection into approval.

```text
Exact user:
Exact adult population:
Exact setting:
Exact task specific input:
Exact research question:
Exact action taken from the result:
Expected participant or public benefit:
Claim level:
Unsupported populations, tasks, devices and settings:

Prohibited diagnosis, disorder, cause and severity claims:
Prohibited health, normality, risk, prognosis and triage claims:
Prohibited identity, accent, gender presentation or ideal voice claims:
Prohibited employment, education, insurance and eligibility decisions:
Prohibited coaching, product, history and progress use:
Other prohibited interpretations:

Owner scope decision:
Lived experience decision:
Motor speech professional decision, if applicable:
Voice professional decision, if applicable:
Measurement scientist decision:
Institutional decision:
Privacy and legal decision:
Regulatory assessment identifier:

Overall state:
[ ] unsigned draft
[ ] changes required
[ ] signed for the exact stated research use
[ ] rejected
```

## Candidate question domain review

Complete separately for motor speech, voice, participant report, controlled
intelligibility and clinical or laryngeal reference. Do not calculate a total
score or rank unlike constructs.

```text
Lane:
Question ID:
Exact construct:
Exact non construct:
Why the question matters to adults:
Truth class:
Independent truth owner:
Evidence that cannot substitute for truth:

Task variants still unresolved:
Access barriers and accommodations:
Known confounders:
Foreseeable harms:
Capture dependence:
Manual and adjudication requirements:
Prospective endpoint and statistical requirements:
Representation requirements:
Institution, ethics, privacy, rights and regulatory dependencies:
Conditions that force no selection:

Domain decision:
[ ] candidate may proceed to final 23B deliberation subject to every condition
[ ] changes and another domain review required
[ ] no selection in this lane

Reasons, limits and required evidence:
Reviewer role IDs and private record identifiers:
Signed decisions held privately:
```

A decision to continue is not task selection, participant permission or 23C
approval. A lane no selection must leave its tasks, measures, scores and
thresholds unavailable.

## Task, access, burden and stop review

```text
Candidate question and lane:
Prompt and version:
Instruction wording and delivery:
Demonstration and comprehension check:
Effort requested:
Practice, feedback, repetitions, order and rest:
Duration and retry limits:
Reading, hearing, memory, language, motor and respiratory demands:
AAC, interpreter, support person and non reading routes:
Which accommodations create a different task:
Device, application, codec, distance, room and operator controls:

Recorded attempt states:
Participant reported effort and discomfort:
Immediate stop signals and symptoms:
Researcher stop authority:
Equipment stop rules:
Emergency wording and escalation route:
Complaint and adverse event route:

Professional decision:
Lived experience decision:
Institution and ethics decision:
[ ] accepted for the exact governed protocol
[ ] changes required
[ ] rejected
```

An incomplete, declined, misunderstood, inaccessible or invalid attempt is
`could_not_assess`. It is not zero, normal, poor performance or an after the
fact exclusion.

## Institution, ethics and site authority record

```text
Legal sponsor:
Responsible research institution:
Lead investigator:
Institutional responsibility accepted in writing: yes or no
Insurance and indemnity decision identifier:
Every entity or person that collects, holds, uses, discloses, accesses or
exercises effective control, plus contractual service roles:
Research contracts:

Risk and review pathway determination:
Determining authority and date:
HREC or institution-approved lower-risk or exemption review body:
Application identifier:
Decision, conditions and expiry:
Protocol and document versions approved:
No project self-exemption confirmed: yes or no
Site governance authority:
Site authorisation identifier and date:
Monitoring, reporting and amendment duties:
Complaints and adverse event route:

Recruitment authorised: yes or no
Recording authorised: yes or no
Candidate software use authorised: yes or no
Reasons and conditions:
```

Ethics approval is not institutional or site authorisation. Site authorisation
is not measurement validation. No box is inferred from another one.

## Privacy, recording law and security decision record

```text
Legal sponsor and responsible entity and data-role matrix:
Privacy Act coverage determination:
Private health service provider determination:
Applicable state and territory health records laws:
Applicable surveillance, listening device and recording laws:
Participant and speaker locations:
Recorder and operator locations:
Device and server locations:
Local, phone and VoIP capture route:
Commonwealth interception-in-transit assessment:
Human listening and transcription rules:
Use, disclosure, communication and publication rules:
Incidental speaker prevention, quarantine, prohibited use, minimisation,
destruction and content-free event logging controls:

Approved data flow diagram identifier:
Data dictionary identifier:
Collection and notice basis:
Separate consent versions:
Mandatory core elements and consequences of declining:
Optional choices that default to decline:
Countries, regions, subprocessors and overseas controls:
Secondary use and model training state:
Raw audio and derived data retention:
Withdrawal and verified deletion rules:
Backup expiry and immutable evidence limits:
Encryption, key ownership and access roles:
Logging, monitoring and administrator access:
Breach and incident plan:
Security review and unresolved findings:
Vendor and contract dependencies:

Privacy decision:
Recording law decision:
Security decision:
[ ] collection and named uses accepted with conditions
[ ] changes required
[ ] prohibited
```

Consent never cures an unlawful or insecure design. A party's ability to record
a Queensland conversation is not research permission and does not settle other
locations or later communication.

## Prospective statistical and split plan decision

```text
Candidate question:
One primary estimand:
Agreement, validity or repeatability target:
Acceptable precision and failure boundaries:
Expected between and within person variation:
Repeated performances, raters or listeners:
Missing, invalid, partial and withdrawn records:
Cluster structure:
Subgroups and minimum supported evidence:
Multiplicity:
Pilot inputs and their provenance:

Participant sample size and derivation:
Listener sample size and derivation:
Rater sample size and derivation:
Recruitment loss allowance:

Participant exclusive allocation method:
Other cluster exclusive rules:
Pilot, development, tuning and held out partitions:
Independent custodian:
Overlap register:
Held out access rule and single opening condition:

Statistician decision:
Custodian decision:
[ ] prospective plan accepted before collection
[ ] pilot evidence required under a separately approved protocol
[ ] changes required
[ ] infeasible, no selection
```

No number is copied from convention. Anything seen while developing a method
can never become held out evidence.

## Australian regulatory assessment record

```text
Exact intended purpose and presentation reviewed:
Candidate software, if any:
Developer, manufacturer and Australian sponsor:
Medical device definition assessment:
Exclusion or exemption assessment:
Classification, if applicable:
Whether proposed work is a clinical trial or investigation:
CTN, CTA or other pathway assessment:
Safety, monitoring and reporting duties:
Future ARTG and advertising boundary:
Change triggers requiring reassessment:
Unresolved facts:

Qualified assessor and conflict record:
Written assessment identifier:
[ ] no candidate software use authorised by this record
[ ] pathway documented, separate authorities still required
[ ] proposed use prohibited until listed conditions are met
```

The specialist documents a route. They do not grant TGA, ethics, institution or
site approval.

## Lane decision and checkpoint decision record

Complete one lane record before the overall checkpoint record.

```text
Lane:
Decision: selection or no selection for a candidate lane; required reference,
not required or unavailable for a conditional reference lane
Parent selected candidate question, or none:
Selected construct, or null:
Selected task, or null:
Selected measure, or null:
Selected score, or null:
Selected threshold, or null:
Exact reasons:
Evidence identifiers reviewed:
Evidence SHA 256 values bound by this decision:
Required role decisions:
Role scope covers this lane: yes or no
Exact reference protocol or manual hash bound by each accountable role:
Conflicts, recusals and dissent:
Unresolved limitations and unsupported groups:
Participant evidence accessed: yes or no
Private evidence accessed: yes or no
Held out evidence accessed: yes or no
Downstream consequences:
Signed release group recommendation:
Owner acknowledgement:
```

The overall record lists all lane decisions and cannot replace them with one
global result. Its owner-issued evidence record lists the parent hash and every
other cited evidence-node digest as dependencies. A selected or
required-reference lane decision is issued by the independent truth and release
group and binds the candidate specifications plus all applicable reviews and
deliverables. Reference construct, task and measure nodes use exact
reference-lane scope. The reference lane decision and its accountable role,
conflict and protocol or manual decisions use exact selected-plus-reference
scope. A closed lane decision is owner issued and binds the parent plus any
explicitly cited blocking role evidence; each blocker evidence node itself
depends on exactly the parent and cannot import another lane. If a required
authority or review is unresolved, an affected lane cannot record selection. A
final checkpoint no selection sets dependent checkpoints to not applicable and
proves that participant and held-out evidence remained unopened.
