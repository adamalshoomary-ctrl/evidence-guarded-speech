# Motor speech and voice research engineering plan

Status: **SHELVED on 2026-08-22.** Checkpoint 23A complete; checkpoint 23B
blocked on named human roles; checkpoint 23C is not approved and will not be

> **Read this first, 2026-08-22.** Item 23 is shelved and should not be
> continued. It is blocked for structural reasons that no amount of further
> planning resolves: the motor lane has no qualifying reference source in public
> at any licence and at any price, acceptance is defined as written review by
> accountable human roles that do not exist, and Queensland recording law and
> Australian ethics review apply to Adam personally regardless of what licence
> the project adopts.
>
> Only 5 of the 27 surveyed sources were blocked on commercial grounds, so the
> project's move to open research barely helps this item, unlike item 22.
>
> This plan is retained as completed evidence for **why this project makes no
> clinical or screening claim**. That is its value. Do not read it as a live
> roadmap, and do not propose checkpoint 23C.

Updated: 2026-08-19

This is the full engineering brief for improvement plan item 23. It carries the
scientific, safety, governance and delivery boundaries for checkpoints 23A
through 23F. `improvement-plan.md` remains the authority for programme order.

## The decision from checkpoint 23A

For this repository's currently undefined population, task, consumer capture
path, reference standard and action, the reviewed evidence does not justify a
general-purpose motor speech detector, automatic voice health score or disorder
screen.

It supports investigating a smaller question: whether a deliberately designed
task can produce a reliable, task-specific observation such as syllable
repetition timing. Human-measured intelligibility, participant-reported impact
and existing low-level voice measurements may provide separate context. They
must not be blended into a single score or treated as interchangeable truth.

No measurement system, vendor algorithm, named condition, disorder, score,
clinical cutoff, threshold, task, prompt, exercise or product output is selected
by 23A. A fully documented `no_selection` remains a successful outcome at every
later checkpoint.

The roadmap leaves the following unordered questions for professional and
lived-experience governance. This list is not an evidence-based safety or
measurement selection:

- controlled rapid syllable timing, regularity and observable task accuracy;
- controlled connected-speech timing as a general task observation, not a
   motor-specific finding and not a relabelling of the current WPM output;
- unfamiliar-listener intelligibility as a separate functional outcome;
- the existing item 20 voice primitives as supporting acoustic observations,
   never as voice health or laryngeal truth.

No new automatic voice screening construct is justified now. More voice
acoustics or a composite voice index would not repair the absence of direct
laryngeal examination, independent perceptual evidence, personal impact and
task and device validation.

## What item 23 is for

Item 23 asks whether this project can measure any narrow motor speech or voice
construct safely enough to justify later research. It does not begin with a
condition and search for a convenient signal. It begins with an intended use,
the user benefit, foreseeable harms, a precise task, independent truth and a
statement of what the observation cannot mean.

Motor speech and voice are separate lanes because they describe different
constructs, need different tasks and require different reference evidence.
Sharing one recording or one acoustic library does not make their truth the
same.

Item 23 must preserve five distinct evidence questions:

1. Did the person understand and validly perform the declared task?
2. Did the software calculate the declared number correctly from that audio?
3. Is the number repeatable under the conditions in which it may be used?
4. Does it relate to a separately measured functional or professional outcome
   for the exact intended population and use?
5. Does showing or acting on it help people more than it harms them?

Passing an earlier question never proves a later one.

## What item 23 is not allowed to do

Until a later checkpoint explicitly satisfies every relevant gate, item 23 does
not allow:

- a diagnosis, possible diagnosis, named disorder, disease probability, cause,
  severity or prognosis;
- a general motor speech, voice health, communication quality, normality or
  impairment score;
- a normal, abnormal, pass, fail, healthy, impaired or at-risk label;
- a claim about tongue or jaw strength, exact articulator movement, airflow,
  respiratory capacity, glottal efficiency, vocal-fold structure or laryngeal
  pathology from ordinary audio;
- an inference about age, race, ethnicity, nationality, sex, gender, emotion,
  personality, mental health, honesty or professionalism;
- an ideal accent, dialect, gender presentation, pitch, pace, loudness or voice;
- automatic emergency triage or reassurance that urgent assessment is not
  needed;
- use in employment, insurance, education access, benefits, policing or any
  other high-impact decision;
- coaching, exercise prescription, history, progress or personal-change claims;
- reuse of item 22 phone evidence as motor speech or voice truth;
- use of item 21's unreviewed repetition, prolongation or phrase-context
  candidates, reviewed derivatives or candidate absence as motor task accuracy,
  motor signs, screening truth, diagnosis or absence of concern;
- reuse of the current ASR WPM, pause output or item 20 voice values under a new
  clinical-sounding label;
- a rapid syllable task in ordinary onboarding or a normal pipeline run;
- transfer of Adam's recordings, participant recordings or corpus audio to
  Redenlab or any new provider without a separate explicit decision and the
  required consent, ethics, privacy, rights and contract review.

Missing, unsupported or unreliable evidence must produce an explicit
`unavailable` or `could_not_assess` state. It can never become zero, normal,
acceptable or a pass.

## Evidence status and four-level claim ladder

The intended use is not yet a screening product. The currently approved use is
offline developer research to decide whether a safe construct is worth studying.

Availability is metadata attached to an attempted level 1 observation. It is
not a fifth claim level.

| Claim level | Meaning in item 23 | Current permission |
|---|---|---|
| Level 1, measured observation | A named unit calculated for this task, recording and method version, with availability metadata | Candidate for later validation; not released |
| Level 2, coaching interpretation | An explanation or exercise derived from the observation | Locked |
| Level 3, screening hypothesis | Evidence intended to identify who may need a professional assessment | Locked until 23E and separate Australian classification, ethics and governance approval |
| Level 4, clinical conclusion | Disorder, cause, severity, diagnosis, prognosis or treatment | Outside current implementation authority |

The exact future context of use must name the user, population, setting, task,
decision, person acting on the result, possible action and expected benefit. A
metric cannot be selected before those fields are complete. Calling the same
function “coaching” or “wellness” does not change its intended purpose.

## Why audio cannot identify cause by itself

One recording is the combined output of respiration, phonation, resonance,
articulation, prosody, language, cognition, hearing, anatomy, current health,
effort, task demands, room, microphone and software. Different causes can
produce similar audio. The same cause can produce different audio across people
or days.

For example, a slower task can reflect deliberate pacing, unfamiliar text,
fatigue, literacy, language planning, pain, medication, recording delay or motor
execution. An acoustic result cannot decide among those explanations without
independent evidence. Repeatability only shows that a result repeats; it does
not show that its interpretation is correct.

## Evidence review

### Motor speech assessment is multidimensional

The ASHA adult dysarthria practice portal describes screening as identifying a
need for further assessment rather than diagnosing a condition or establishing
detailed severity. Comprehensive assessment combines speech subsystems,
intelligibility, naturalness, efficiency, participation, language, cognition,
hearing, swallowing, context and culturally responsive professional judgement.
This makes a one-number audio screen an unsupported reduction of a much broader
question.

Rapid alternating and sequential syllable tasks are used professionally, but
the research does not make “DDK” one universal construct. A review of 360
articles found substantial variation in stimuli, instructions, duration,
analysis and interpretation. Performance changes with language, syllable,
hearing, cognition, structure, age, practice, fatigue and whether the task is
speech-like. Rapid maximum performance also does not reliably substitute for
ordinary connected speech.

Automatic DDK timing has shown analytical promise in narrowly defined research
datasets, including participant-disjoint evaluation. Other studies show errors
increase for more severely affected speech and for particular syllables. These
are reasons to investigate a carefully governed task, not evidence for a
general-population detector or portable cutoff.

### Voice assessment is also multidimensional

Professional voice evaluation combines auditory-perceptual judgement,
laryngeal visualisation, acoustics, aerodynamics, personal report and functional
impact. The ASHA instrumental protocol standardises tasks and capture but does
not make acoustic measurements a diagnosis. The clinical guideline for
persistent dysphonia supports visualising the larynx before voice therapy and
when serious causes must be considered.

Item 20 already implements guarded F0, recorder-level dBFS and CPPS primitives,
plus research-only sustained-vowel jitter and shimmer. CPPS is the most
defensible of the current acoustic voice-quality primitives, but systematic
reviews still find heterogeneous tasks, devices, software and reference
methods. It is an adjunct observation. It is not direct vocal-fold evidence and
does not establish dysphonia, pathology, normality, cause or severity.

Adding HNR, spectral tilt, AVQI, ABI, CSID or an automatically inferred
roughness, breathiness or strain label would not solve that problem. Composite
indices hide separate constructs and failure modes. Maximum phonation time is a
controlled respiratory-phonatory task observation rather than an acoustic
voice measure; it combines respiratory, phonatory, instruction and effort
effects. Perceptual labels require independent trained human raters under a
standardised protocol, with disagreement retained.

### Intelligibility and lived experience answer different questions

Research-grade intelligibility commonly uses orthographic transcription by
multiple unfamiliar listeners under a declared listening condition. It remains
affected by listener language, hearing, familiarity, adaptation, context,
vocabulary and noise. A clinician's single estimated percentage, an ASR score
or algorithm agreement is not equivalent truth.

Intelligibility, comprehensibility, communication effort, naturalness,
participation and living well are related but distinct. An Australian and UK
core-outcomes study involving people with lived experience placed
intelligibility, conversational participation, living well and communication
partner skill above a narrow set of impairment measurements. Participant report
therefore remains its own evidence source. It must not be inferred from
acoustics.

### Device and task differences are material

Some gross temporal measures have been robust in particular tasks and capture
comparisons, but that does not generalise to pause, boundary, regularity or DDK
measures. Compression, dropped samples, clock drift, automatic trimming,
segmentation and voice activity detection can change them. Spectral and
amplitude features are additionally affected by microphone frequency response,
placement, angle, gain, automatic gain control, noise suppression, codec and
room acoustics.

Research that included Redenlab investigators found that many speech and voice
measures were not numerically interchangeable across ordinary plug-and-play
microphones. Cross-device studies also warn that high correlation is not the
same as agreement. Every future result therefore needs task, capture, device,
software, algorithm, settings, quality and failure provenance. Device classes
that have not passed agreement testing remain unsupported.

### Language, variety, identity and access are part of validity

Rates, segment timing and formants vary across languages, varieties, phonetic
contexts, ages and anatomies. Australian English, Aboriginal Englishes and
multilingual English cannot be treated as noisy versions of one imported norm.
The item 22 reference-variety work already demonstrates why a repeatable system
can consistently measure the wrong reference.

Demographic and identity information may be volunteered only where it is
necessary, specifically consented and governed. It must never be inferred from
voice. Reading, hearing, imitation, maximum-effort and sustained-voice tasks
create different access barriers. A spoken prompt, AAC contribution or
non-reading alternative enables participation but is a different task; its
results cannot be pooled into reading-task norms without separate evidence.

## Provisional construct register

This register prioritises questions for checkpoint 23B governance. It does not
select a metric or task.

| Lane | Candidate | Narrowest defensible observation | Required reference | 23A disposition |
|---|---|---|---|---|
| Motor task | Rapid syllable timing | Rate, valid repetition count, inter-onset timing, within-run change and temporal regularity during one frozen task | Two blinded trained annotators marking cycles and errors, with adjudication | Priority for professional review; task remains locked |
| Motor task | Rapid syllable task accuracy | Observable omissions, substitutions, additions, sequence breaks or incomplete performance under frozen scoring rules | Two blinded trained annotators and intended prompt | Priority supporting evidence; never a disorder label |
| General speech | Articulation rate | Syllables per second after a predeclared pause rule on a fixed prompt | Human-reviewed syllable and speech boundaries | Candidate context only; not current WPM and not motor-specific |
| General speech | Speech rate and pause profile | Syllables per second including pauses, plus declared pause counts and durations | Human-reviewed prompt, speech and pause boundaries | Supporting context only; preserve non-motor explanations |
| Functional | Controlled intelligibility | The relationship between an independently adjudicated production and words transcribed by multiple unfamiliar listeners under a fixed listening protocol | Intended prompt, independently adjudicated actual production and blinded listener-level transcriptions retained separately | Candidate independent outcome, not motor truth or cause |
| Functional | Comprehensibility or effort | Listener experience under one predeclared instrument and condition | Multiple listeners with individual results retained | Deferred until intended benefit is defined |
| Personal | Communication impact and desired change | What the participant reports matters in their life and identity | Participant report using an appropriate instrument or accessible qualitative method | Required separate outcome; never inferred |
| Voice acoustic | Existing item 20 CPPS and related primitives | Declared acoustic calculation for a standardised task | Frozen algorithm, fixtures and task-valid audio | Supporting research evidence only; no relabelling or composite |
| Voice perceptual | Overall severity, roughness, breathiness, strain or pitch/loudness deviation | Independent trained listener judgement under a standardised protocol | Several blinded qualified raters, preserved ratings and adjudication | Deferred to independent voice governance; no automatic label |
| Voice functional | Voice-related personal impact | Participant's experienced concern and effect | Participant report and accessible interview | Required if voice benefit is pursued; separate from acoustics |
| Endurance | Maximum phonation time | Duration sustained in a frozen repeated protocol | Repeated timed attempts and explicit validity and stop rules | Low priority and not a standalone screen |
| Acoustic articulation | Formant trajectories, vowel dispersion, VOT, segment duration or F2 transitions | Named acoustic property in a named phonetic context | Human phonetic boundaries; direct movement evidence if movement is claimed | Deferred; high variety, anatomy, task and item 22 overlap |

The register cannot be narrowed to a selected candidate until the 23B
governance group defines the intended benefit and can explain why the task is
worth its burden. It may reject every row.

## Required truth architecture

Truth is construct-specific. Each source answers only its own question.

| Truth class | What can establish it | What cannot substitute |
|---|---|---|
| Task fidelity | Frozen prompt, recording, participant confirmation where appropriate, and trained review of completion and errors | ASR transcript alone or elapsed file duration |
| Computational truth | A written mathematical definition, versioned implementation, synthetic fixtures and independently recomputed examples | Agreement with the same library or a second opaque API |
| Timing and boundary truth | Two independent trained annotators blinded to software output, a written manual, preserved raw labels and predeclared adjudication | The candidate system's own segmentation |
| Perceptual voice truth | Multiple independent qualified raters under a standardised protocol, with individual ratings and disagreement retained | One clinician, a vendor score or an inferred acoustic label |
| Intelligibility truth | Intended prompt, independently adjudicated actual production and several blinded unfamiliar listeners making orthographic transcriptions under fixed conditions; omissions, substitutions and partial productions follow predeclared separate task-fidelity and intelligibility rules | ASR confidence, one familiar listener or a clinician estimate |
| Personal truth | The participant's own report, goals, acceptability and experienced impact | Acoustic, listener or clinical inference |
| Functional truth | Task-specific communication success and appropriately selected participant or partner outcomes | A signal primitive alone |
| Clinical reference | Independent comprehensive professional assessment and, where the claim requires it, medical, laryngological, physiological, hearing, cognitive or language evidence | Diagnosis code alone, audio alone or vendor judgement |

A diagnosis may describe a study population but is not the numeric ground truth
for a primitive. Every human or clinical reference is itself a fallible
measurement whose uncertainty must be reported. Clinical assessors, annotators and listeners must be independent
of candidate development and blinded where practicable. Conflicts, training,
language background, hearing requirements, familiarisation, workload and
adjudication must be recorded. Raw disagreement is data and must never be
silently replaced by a consensus label.

## Population and age decision

The approved checkpoint 23B scope is an adult research lane first. A child lane would
need its own child-specific tasks, reference ranges, assent and guardian consent,
safeguarding, recruitment, burden limits, professional expertise, ethics review
and held-out evaluation. Adult and child evidence must never be pooled to make
one look representative.

Adam approved the adults-first path on 2026-08-14 by saying to continue after
being asked whether 23B should begin with that scope. Adults means age 18 and
over for research eligibility. This is planning authority only. It does not
authorise recruitment, recording, data access, external contact, spending, task
selection or implementation. Children remain outside item 23's active scope and
would need a separately approved future study.

This research decision does not create a product age gate or an exact-age
account field. Research age information, if scientifically necessary, must be
minimal, purpose-specific, consented, access-controlled and kept out of normal
product identity records.

Item 23 requires its own ethics-governed research data dictionary and artifact
schema. Research age, clinical, fairness and detailed device metadata must not be
written into existing session-context, account, history, progress or assessment
records. The assessment rapid-syllable task remains `future_locked` throughout
item 23. Any 23C task uses an item 23-only offline manifest. Changing the
assessment or a product schema requires a later, separately approved release
decision.

The first research language remains English, but “English” is not one
homogeneous reference. The sampling and analysis plan must explicitly cover the
Australian varieties and multilingual use that the intended population
includes. A group without enough independent evidence is unsupported, not
silently passed.

## Confounder register

The future protocol must record, control, stratify or explicitly limit each
relevant confounder. It must never pretend they can all be mathematically
corrected away.

### Participant and current-state factors

- age and anatomy where scientifically necessary and consented;
- language, language variety, accent, literacy and task familiarity;
- hearing, vision and access needs;
- dentition, oral structure, respiratory and laryngeal state;
- current illness, pain, fatigue, sleep, hydration and recent voice use;
- medication and substances where necessary, proportionate and consented;
- cognition, language planning, prompt comprehension and memory demands;
- vocal training, acting, singing, speech therapy and practice effects;
- effort, motivation, discomfort, identity goals and gender presentation.

### Task factors

- exact prompt and phonetic content;
- alternating versus sequential syllables;
- comfortable versus maximum effort;
- written, repeated, pictured, spontaneous or conversational production;
- instruction wording, demonstration and feedback;
- practice, trial count, task order, rest and duration;
- pause definition, valid-cycle rule and minimum usable material;
- passage predictability, semantic context and listener adaptation.

### Capture factors

- microphone and device model where available without invasive fingerprinting;
- operating system, app, codec, sample rate and bit depth;
- distance, angle, room, reverberation and background speech;
- gain, clipping, compression, automatic gain and noise cancellation;
- packet loss, drift, trimming, channel mixing and resampling;
- home, clinic, lab or remote setting and capture-site effects.

### Analysis and reference factors

- algorithm, dependency, model and configuration version;
- segmentation, pause and outlier rules;
- ASR language modelling and speaker-attribution errors;
- annotator qualifications, listener hearing and language background;
- listener familiarity, adaptation, fatigue and repeated exposure;
- reference disagreement, missingness and adjudication;
- participant, speaker, site or device overlap across data splits.

## Foreseeable harms and required controls

| Harm | Required control before exposure |
|---|---|
| False reassurance or delayed assessment | No “normal” output; clear limits; static professional and emergency safety route; measure false negatives only for a predeclared use |
| False alarm, anxiety, stigma or unnecessary cost | No user-facing flag in item 23; paid lived-experience review; measure false positives and downstream actions |
| Accent, dialect, multilingual speech, disability or identity treated as pathology | Representative co-design and data; task-specific subgroup evidence; unsupported-group abstention; no demographic inference or ideal voice |
| A device, room or site artefact mistaken for a person difference | Capture provenance, quality gates, simultaneous-device agreement and site-separated evaluation |
| Pain, fatigue, breathlessness or distress from rapid or maximum tasks | Optional participation, stop rules, rest, task burden testing, accessible alternatives and no penalty for non-completion |
| Reading, hearing, imitation or natural-speech access barriers | Accessible instructions and participation; separate task versions rather than pooled pseudo-equivalence |
| Metric gaming that reduces meaningful communication | No coaching or progress use; personal and functional outcomes remain separate |
| High-impact third-party use | Contractual purpose limits, access control, audit logs and an explicit prohibition on employment, insurance and eligibility decisions |
| Reidentification, incidental content or sensitive health inference | Data minimisation, purpose-specific consent, encryption, restricted access, retention and verified deletion, no unrelated model training |
| Vendor lock-in or opaque change | Exportable raw evidence and provenance, version pinning, independent validation, change control and exit rights |

Sudden new slurred speech can be a sign of stroke. A future participant or
product safety route must use clinician-reviewed static wording consistent with
the Australian Stroke Foundation FAST advice to call 000 immediately. The
software must not listen for emergencies or reassure someone that an emergency
is absent. Persistent or concerning voice change also needs an appropriate
professional route rather than an acoustic explanation.

## Governance before data or code

Checkpoint 23B must establish named, accountable roles. One person or vendor
must not control construct selection, data, truth, thresholds and release.

| Role | Required authority |
|---|---|
| Product owner | Freeze the intended benefit and prohibited uses; approve spending, outreach and release scope |
| Paid lived-experience governance group | Decide whether the benefit is meaningful, identify harms, review wording, burden, access, consent, complaints and release acceptability |
| Independent adult motor speech CPSP | Review motor construct, task, exclusions, truth manual, clinical boundaries and safety route |
| Independent voice CPSP | Review voice construct, task, perceptual reference and identity-sensitive boundaries |
| Child and safeguarding specialists, if that lane is chosen | Add paediatric motor-speech and voice expertise, safeguarding, age-appropriate lived-experience and parent or guardian governance |
| ENT or laryngologist | Required before any claim that could be read as laryngeal pathology or before a voice clinical reference is designed |
| Speech measurement scientist | Define acoustic and temporal construct, capture, verification and analytical validation |
| Biostatistician or measurement specialist | Set the prospective sample, split, reliability, agreement, missingness and analysis plan |
| Responsible research institution | Determine the applicable ethics pathway and provide separate institutional and site research-governance authorisation |
| HREC | Provide prospective ethical review and approval when the institution's pathway requires it |
| Privacy, security and Australian legal reviewers | Complete the privacy impact assessment, data flow, retention, access, vendor and cross-border controls |
| Australian medical-device regulatory specialist | Classify the exact intended purpose before any screening evidence, clinical-facing workflow or public release |
| Independent truth and release group | Protect held-out evidence, include paid lived-experience members with real decision rights, review adverse subgroup results and make a release recommendation without vendor control |
| Redenlab, if engaged | Ring-fenced measurement-science adviser, protocol collaborator or candidate vendor; never a professional-governance, clinical, truth, ethics, regulatory or release authority |

Consumer involvement must begin during design, not after a system exists. It
must be accessible to people who use AAC or text and those who need support
people, extra time, breaks or asynchronous participation. Preparation,
participation and access costs should be paid. Possible identification and
support routes include People with Disability Australia, Queenslanders with
Disability Network and Health Consumers Queensland; listing them does not
preselect a partner. If Aboriginal or Torres Strait Islander people or data are
included or affected, community-led governance consistent with the NHMRC
Indigenous ethical guidelines must precede recruitment; a generic consumer seat
is insufficient.

## Australian ethics, privacy, regulatory and claims boundary

The 2025 NHMRC National Statement is effective from 23 June 2026. It treats
psychological harm, stigma, discrimination, privacy harm and economic or legal
consequences as research risks. The National Statement does not support
retrospective ethical review or approval. The responsible institution must
determine the applicable ethical review pathway. An HREC provides prospective
ethical review when that pathway requires it, while institutional and site
research-governance authorisation remains separate. A responsible institution
may instead issue a lower-risk or exemption determination through its accepted
process; the project cannot self-exempt.

An identifiable voice recording is personal information. It is not
automatically biometric sensitive information merely because it contains a
voice, but automated identity or verification templates can be biometric
information, and inferred health or disability information can be sensitive
health information. The planned data flow must cover collection, consent,
access, overseas processing, subprocessors, model training, retention,
withdrawal, export, deletion, backups and breach response. The review must name
every entity and person that collects, holds, uses, discloses, accesses or
controls the information and map its data role, jurisdiction, vendors, countries
and subprocessors. It must determine APP and health-service-provider coverage,
satisfy APP 5 collection-notice and APP 6 use-or-disclosure duties, and map
state, territory and Commonwealth recording or interception law across
participant, speaker, recorder, operator, device and server locations and local,
phone or VoIP capture. Incidental speakers need prevention, quarantine, no-use,
minimisation and destruction rules. Withdrawal and deletion must be stated per
data layer and reconciled with any lawful or ethical retention. Publicly
available or previously collected audio is not automatically lawful for a new
health inference purpose.

TGA status follows intended purpose, claims, presentation and function. Software
used to screen for possible disease or to support clinical decisions can be
software as a medical device even if it is called coaching or wellness. At 23B,
before participant recruitment or use of candidate software, an Australian
regulatory specialist must document whether the planned 23C or 23D activity is
research software outside the medical-device definition, excluded software, an
exempt device, or use of an unapproved medical device in a clinical trial. The
assessment must identify manufacturer and Australian sponsor responsibilities
where applicable and resolve any CTN, CTA, exemption, notification or other
obligations before the relevant activity. A CTN or CTA route requires the HREC
decision and the approving institution or site's authorisation; it cannot be
recorded with lower-risk review or site governance marked not applicable. ARTG
obligations must be resolved separately before Australian supply. This plan is
not legal or regulatory advice.

Speech Pathology Australia's AI position states that, when AI is used in speech
pathology practice, speech pathologists should ensure evidence-based,
person-centred, safe use, ongoing informed consent, privacy, professional
judgement and critical review. Its Code of Ethics and Professional Standards
form part of Australia's self-regulated speech pathology profession. None makes
the association a statutory regulator or replaces ethics, privacy, TGA or
medical governance. Any public accuracy, objectivity, clinical validation or
improvement claim must also be specific and supportable under Australian
consumer law.

## Redenlab investigation

Redenlab is an Australian-founded commercial clinical-outcome measurement
company whose public materials and associated research indicate relevant
protocol, remote-recording and acoustic-analysis experience. Its public work
includes sustained voice, rapid syllable, reading, monologue and conversational
tasks. It is the first potential Australian measurement-science or vendor
contact identified for future investigation because of that practical link.

It is not preselected and is not a professional-governance, clinical, ethics,
regulatory, truth or release authority. Public vendor claims do not validate a
system for this product, population, device mix or intended use. Some public examples use
proprietary algorithms and reference data. Redenlab-associated research also
documents device comparability problems. Its public privacy policy is dated
2018 and appears oriented to website use; it cannot substitute for a project
data-processing agreement or current Australian privacy review.

No contact, purchase, account action, contract, audio transfer or data sharing
occurred in 23A.

Before any engagement, Adam must approve the purpose and budget. A written
question set must cover:

- whether Redenlab would act as adviser, protocol designer, platform, algorithm
  vendor or analyst, and every commercial or intellectual-property conflict;
- the exact construct, intended use, excluded use, task and supported ages,
  languages, varieties, disabilities, devices and environments;
- mathematical feature definitions, proprietary components, model versions,
  training sources, overlap risks, exportable evidence and reproducibility;
- independent reference truth, rater process, disagreement, development and
  held-out separation and publication of negative results;
- test-retest agreement, measurement error, smallest detectable change,
  simultaneous-device agreement, external validation and subgroup failures;
- recording-quality gates, task-validity checks, abstention, incidents, drift,
  updates and rollback;
- contracting entity, Australian sponsor and manufacturer roles, TGA or ARTG
  position and independently reviewable quality evidence;
- hosting, countries, subprocessors, secondary research, model training,
  retention, withdrawal, export, deletion verification, backups and breach
  obligations;
- ability to prohibit secondary use and allow independent audit and publication.

If Redenlab supplies a candidate method, it cannot supply the sole reference
truth or control the held-out evaluation or release decision.

## Validation framework

The work follows the V3 separation of verification, analytical validation and
clinical validation, with usability and accessibility treated as a fourth
required evidence stream.

### Verification

Prove that capture metadata and the declared calculation are implemented
correctly. Use synthetic signals and structural fixtures with known timing,
versioned mathematical definitions, independent recomputation, boundary cases,
determinism and explicit invalid states. Passing verification says nothing about
human meaning.

### Analytical validation

Compare the calculation with independent construct-specific reference evidence.
Report bias, absolute error, agreement limits, coverage, task-invalid rate and
abstention. Reliability correlations or ICC alone are insufficient because high
correlation can coexist with material disagreement.

For repeated sessions, predeclare within-person standard deviation, standard
error of measurement, agreement limits and minimum detectable change. Same-file
reruns test determinism, not biological or task repeatability. Repeatability
requires independent performances across appropriate trials, days, devices and
settings.

### Clinical and functional validation

This stage is permitted only after the intended use and action are fixed. It
must compare with independent comprehensive assessment and separately measured
functional and participant outcomes. A diagnostic label alone is not reference
truth for timing or acoustics. Sensitivity, specificity, predictive values,
cutoffs or prevalence-dependent claims are prohibited until the intended
population, recruitment route, reference standard and action are prospectively
frozen.

### Usability, accessibility and benefit

Measure whether people understand the task and limits, can opt out, can use
accessible alternatives, experience discomfort or harm, and find the result
useful for the declared goal. Record exclusions and non-completion rather than
analysing only people who can perform the task easily.

## Data and evaluation rules

- Acquisition must be prospective or explicitly approved for the exact
  secondary use. Rights, commercial use, consent and ethics are separate gates.
- Participants, not clips or sessions, are the split unit. Development, tuning
  and held-out evaluation are participant-exclusive.
- Sites, households, devices and repeated sessions must be grouped where needed
  to prevent leakage.
- The held-out set is sealed before feature, threshold and exclusion search. It
  is opened once only after the method and analysis plan are frozen.
- The split-allocation method is frozen in 23B. Every participant, recording,
  device, prompt and reference accessed during 23C is permanently marked
  `pilot_development_only`; that participant and related household, session and
  repeated recordings can enter neither tuning nor held-out evidence. Actual
  development, tuning and held-out assignments are frozen before any 23D
  benchmark outcome or label is inspected.
- An overlap register covers item 22 and every other repository source and
  participant. Item 22 material is not reusable by default; even development
  use needs a new lawful-purpose, consent, rights and ethics decision.
- Sample sizes and subgroup minimums come from a prospective statistical plan,
  pilot variance and intended claim. No arbitrary number is frozen in 23A.
- Study recruitment must represent the intended Australian population and
  deliberately include relevant speech, voice, language, access and device
  variation. Convenience data cannot support a general-population claim.
- Training or tuning on corrected evaluation phrases, held-out participants,
  reference annotations or repeated recordings from the same participant is
  prohibited.
- Report every subgroup and capture stratum predeclared by the plan, with
  uncertainty and missingness. An underpowered group is `not_evaluated`.
- Report task-invalid, recording-invalid and unsupported-population abstention
  separately. Selective abstention is itself a fairness and access outcome.
- Algorithm, prompt, task, manual, consent, reference and environment versions
  are immutable in final evaluation.
- Preserve evidence lineage and raw independent ratings subject to consent and
  retention limits. Agreed withdrawal and deletion commitments, subject to
  disclosed lawful and ethics-approved retention requirements, override
  engineering convenience.

## Required result shape before any product consideration

Any future research artifact must keep these fields separate:

- participant-safe research identifier and consent version;
- task ID, task version, prompt, instructions and completion state;
- attempt, session and recording provenance;
- construct name, definition, unit and claim level;
- algorithm, dependency, model and settings versions;
- timestamped or sample-indexed evidence;
- raw value, uncertainty and quality status;
- availability status and exact abstention or failure reason;
- capture and device metadata allowed by consent;
- relevant declared confounders and unsupported contexts;
- reference source, rater-level labels, disagreement and adjudication;
- data split and overlap checks;
- limitations and explicitly prohibited interpretations.

There is no combined score field. Motor task, voice acoustic, perceptual,
functional, participant-report and clinical-reference records remain separate.

## Ordered delivery plan

Only one checkpoint may be active at a time. Each later checkpoint requires
Adam's explicit approval after the earlier checkpoint is committed.

### Fail-closed checkpoint states

Every checkpoint writes a versioned decision artifact containing dependency
hashes, eligibility, decision, reason, downstream states and
`held_out_accessed`. A validator must reject missing fields, an ineligible
selection, an unexplained transition or held-out access on a no-selection path.

| Decision | Required downstream state |
|---|---|
| 23B `no_selection` | 23C through 23E are `not_applicable`; held-out remains sealed |
| 23C `no_selection` | 23D and 23E are `not_applicable`; held-out remains sealed |
| 23D `no_selection` | 23E is `not_applicable`; held-out remains sealed |
| 23E `no_selection` | No screen exists; held-out remains sealed |
| Eligible method reaches 23F | One unchanged method is evaluated once |
| No method reaches 23F | Documentation-only closure proves the dependency chain and that held-out evidence was not accessed |

Only a final validated closure artifact may call item 23 engineering complete.

### 23A: evidence review and engineering plan

Purpose: define the question and its boundaries before selecting a measurement.

Deliverables:

- this evidence review;
- intended-use and prohibited-claim ladder;
- candidate construct and deferral register;
- separate truth architecture;
- confounder, harm and failure registers;
- Australian ethics, privacy, regulatory and emergency boundaries;
- governance roles and Redenlab due-diligence route;
- ordered checkpoints, gates and valid no-selection path.

Acceptance:

- no detector, vendor, task, named condition, cutoff or score is selected;
- motor speech, voice, function, personal report and clinical truth remain
  separate;
- item 20, item 21 and item 22 outputs are not promoted into clinical evidence;
- no audio is collected, repurposed or transferred and no external party is
  contacted;
- the live plan and short project handoff point to this authority;
- repository validators and a normal isolated pipeline regression remain
  unchanged;
- a checkpoint acceptance record stores exact commands, exit results, real-run
  provenance, item 23 leakage checks and protected-state before and after hashes.

### 23B: professional governance and lawful truth design

Purpose: decide whether a specific candidate is useful and governable before
data collection or implementation.

Required deliverables:

- signed intended-use, population, user, action and prohibited-use statement;
- the recorded adults-first research scope and a separate prohibition on child
  inclusion;
- named paid lived-experience governance and independent professional roles;
- conflict register and decision-rights matrix separating vendor, truth and
  release authority;
- professionally reviewed task, burden, access, stop and safety protocol;
- construct-specific annotation, listener and clinical-reference manuals;
- prospective acquisition, sample-size, representation, split and statistical
  plan;
- institution pathway determined and required prospective HREC review completed
  before recruitment or use of participant recordings;
- privacy impact assessment, responsible entity and data-role matrix, applicable
  APP, health-records, recording and interception law, APP 5 notice, APP 6 use
  and disclosure map, incidental-speaker controls, consent, retention,
  withdrawal, deletion, security, complaint and incident design;
- source and commercial-rights review, including every proposed vendor and
  transfer;
- versioned split-allocation method and overlap register before pilot access;
- documented preliminary Australian classification and clinical-trial pathway
  assessment for any proposed candidate software or screening intent;
- recorded `selection` or `no_selection` decision with reasons.

Acceptance requires written review from the accountable roles, not an agent's
interpretation of public guidance. The owner approves product scope, the
consumer and professional groups exercise their recorded governance rights, the
institution establishes the research pathway, the HREC gives ethical approval
when required, and privacy and regulatory specialists document their respective
assessments rather than acting as approval authorities. If the benefit, truth,
ethics, access, privacy, rights or regulatory route is unresolved, the only
valid result is `no_selection`. No code or participant recording is authorised
by planning alone.

### 23C: isolated local feasibility and repeatability

Purpose: determine whether the selected primitive can be measured at all under
the frozen research task.

Boundaries:

- a separate offline research command and output directory;
- synthetic fixtures first. Participant recordings remain prohibited until the
  responsible institution has completed the applicable HREC determination or
  approval and each recording is covered by final consent, privacy, rights and
  research-governance authority for the exact use;
- participant use additionally needs a recorded institutional determination or
  approval identifier, final participant information and consent materials,
  approved protocol and data-management plan, approved source and transfer
  register, and Adam's explicit authorisation to start recruitment or secondary
  use; otherwise 23C is synthetic-only and cannot claim human repeatability;
- no normal pipeline import, report, listener, evaluator, coaching, history or
  progress integration;
- no import of item 21 candidates, reviewed derivatives or absence states;
- no new external provider unless separately approved;
- no threshold search, screening label or combined score;
- task validity, recording quality, abstention and provenance are mandatory.

Acceptance must include numeric verification, deterministic reruns, independent
manual-reference agreement, independent repeated performances, device and room
probes, explicit failure cases and evidence that output wording stays at measured
observation level. A poor, inaccessible or device-bound result closes with
`no_selection`.

### 23D: participant-exclusive development and tuning benchmark

Purpose: test the frozen candidate on representative consented research data
without touching held-out participants.

Before any tuning, freeze:

- participant and capture splits;
- primary and safety endpoints;
- reference manual and adjudication;
- task and device validity rules;
- subgroup and missingness analyses;
- measurement agreement and repeatability gates;
- task-invalid, recording-invalid, unsupported-context, subgroup-failure and
  abstention gates for the exact measured observation;
- access, burden, privacy, security and runtime gates;
- stop and no-selection rules.

Development may inform implementation. Tuning may make the one predeclared final
analytical measurement choice, but may not create a screening rule, model or
threshold. Results must be reported by participant, subgroup, task, site and device
as planned. Failure cannot be repaired by moving a gate, changing the population
or examining held-out evidence.

### 23E: developer-only screening evidence, if justified

Purpose: decide whether the frozen observation has enough independent evidence
to test one narrowly stated screening hypothesis.

This checkpoint is optional. It begins only after the owner approves its scope,
the independent professional and paid lived-experience groups exercise their
recorded decision rights, the institution establishes the pathway, any required
HREC approval is in force, the privacy assessment is complete and the Australian
regulatory pathway has been resolved for the proposed use. The artifact remains
private, offline and developer-only.
It may indicate only the predeclared research action, such as whether a
professional assessment route should be studied. It never infers cause,
disorder, diagnosis, severity or prognosis.

Before development, 23E must freeze any false-positive, false-negative,
false-reassurance, predictive-value, screening-threshold, prevalence and
downstream-action gates for the exact intended population and reference
standard. None of these may be imported from the analytical 23D benchmark.

The one screening hypothesis, independent clinical reference, action, rule or
model, threshold if any, development and tuning split and analysis are frozen
prospectively. Screening development and tuning occur within 23E; held-out
evaluation remains prohibited until 23F.

No-screen `no_selection` is a complete result. The absence of a detector is not
permission to rename the same output a risk, concern, wellness or coaching
score.

### 23F: frozen held-out evaluation and repository acceptance

Purpose: evaluate the unchanged eligible method once, or prove honestly that no
method qualified and held-out evidence remained sealed.

Before opening held-out evidence, freeze code, models, dependencies, tasks,
prompts, reference manuals, raters, thresholds, exclusions, abstention, analysis,
wording and hashes. Evaluation is performed by an independent or firewalled
analyst. No refitting, threshold adjustment, participant removal or new subgroup
story is permitted after opening.

The final aggregate report includes every predeclared endpoint, uncertainty,
failure, subgroup, device, site, missingness, harm and abstention result. It
cannot expose participant identity or unsupported small cells. A failed method
is recorded as failed; it is not quietly narrowed after the fact.

Final repository acceptance must prove:

- ordinary pipeline output, coaching, history and progress contain no item 23
  result;
- item 20, item 21 and item 22 contracts and validators still pass;
- personal `history.json`, `progress.md` and root output were not changed by
  acceptance runs;
- every research artifact and decision is versioned and reproducible within
  consent and retention limits;
- held-out access is auditable, or no eligible method existed and the material
  remained sealed;
- release remains locked pending a separate owner, professional, participant,
  ethics, privacy, regulatory and product decision.

## Reopening and change control

A later method, vendor, population, language, task, device class, clinical
action or claim is a new context of use. It cannot inherit validation silently.
Material changes require a new version, impact assessment and the earlier
validation stages affected by the change. Held-out evidence from an earlier
version becomes development evidence only under an approved new plan; it cannot
remain held out for the changed system.

No checkpoint may be reopened merely to search more thresholds, weaken a gate
or recast a failed endpoint. Reopening requires genuinely new independent
evidence or a different approved construct and begins before held-out access.

## Evidence gaps at the end of 23A

The following are deliberately unresolved:

- the exact user benefit and action worth testing;
- implementation of the approved adults-first scope without creating a product
  age gate;
- whether any rapid syllable task is acceptable, accessible and useful;
- an Australian task protocol reviewed by independent motor speech and voice
  professionals and people with lived experience;
- representative, consented and commercially lawful Australian recordings;
- independent task, timing, perceptual, functional and clinical truth;
- device and room agreement for the future capture path;
- repeatability, measurement error and minimum detectable change;
- sample size and subgroup power;
- an ethics institution, HREC determination and privacy impact assessment;
- the legal and TGA classification of any future screening intent;
- evidence that a result improves an outcome rather than creating anxiety,
  exclusion or false reassurance.

Those gaps are the work of later checkpoints. They are not small print and may
not be converted into optimistic assumptions.

## Sources reviewed for 23A

All web sources were accessed on 2026-08-13. Vendor pages establish public
claims and questions only; they are not independent validation.

### Clinical and measurement evidence

- [ASHA, Dysarthria in Adults](https://www.asha.org/practice-portal/clinical-topics/dysarthria-in-adults/): screening, comprehensive assessment,
  cultural and functional boundaries.
- [ASHA, Voice Disorders](https://www.asha.org/practice-portal/clinical-topics/voice-disorders/): multidimensional voice assessment and professional
  scope.
- [Patel et al., Recommended Protocols for Instrumental Assessment of Voice](https://pubs.asha.org/doi/10.1044/2018_AJSLP-17-0009): task and capture
  standardisation and the role of CPP.
- [CPP and CPPS normative systematic review](https://doi.org/10.1016/j.jvoice.2025.11.013) and
  [CPP diagnostic-accuracy meta-analysis](https://doi.org/10.1016/j.jvoice.2026.06.017): heterogeneity and the limits of carrying voice acoustic norms or
  discrimination into a different task and context of use.
- [Revised CAPE-V consensus](https://doi.org/10.1016/j.jvoice.2025.01.022):
  standardised human perceptual voice reference.
- [AAO-HNSF, Clinical Practice Guideline for Hoarseness](https://aao-hnsfjournals.onlinelibrary.wiley.com/doi/10.1177/0194599817751030): laryngeal examination and safety boundaries.
- [Kent, Kim and Chen, DDK scoping review](https://doi.org/10.1044/2021_JSLHR-21-00396): heterogeneity of rapid syllable tasks, methods and causes.
- [Wav2DDK analytical validation](https://pmc.ncbi.nlm.nih.gov/articles/PMC10555468/): a narrow example of automated timing against manual reference.
- [Automatic DDK methods and severity-related errors](https://pmc.ncbi.nlm.nih.gov/articles/PMC9150739/): failure variation by speech and stimulus.
- [Task-specific oral motor study](https://doi.org/10.1016/j.neuropsychologia.2016.12.010): limits of using maximum-performance tasks as ordinary
  speech proxies.
- [Speech and articulation-rate definition study](https://doi.org/10.1044/2021_JSLHR-21-00206): task and pause-rule dependence. A future protocol must also
  freeze sample boundaries, syllable counting, disfluencies, revisions,
  incomplete words, filled pauses, overlap and leading or trailing silence;
  item 21 candidates cannot supply these human reference labels.
- [Vogel et al., quantitative speech consensus recommendations](https://pmc.ncbi.nlm.nih.gov/articles/PMC11102369/): intended-use-driven protocol,
  task and capture metadata and multiple evidence sources. A Redenlab leader is
  a coauthor, so it is not independent evidence about the vendor.
- [Goldsack et al., V3 framework](https://www.nature.com/articles/s41746-020-0260-4): verification, analytical validation and clinical validation.
- [Speech biomarker recommendations](https://pmc.ncbi.nlm.nih.gov/articles/PMC7670321/): context of use, validation, privacy and reproducibility.
- [Core outcomes for dysarthria after stroke](https://pmc.ncbi.nlm.nih.gov/articles/PMC11059832/): lived-experience and professional priorities for
  function and participation.
- [Intelligibility reference methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC9406197/): unfamiliar-listener transcription and listener dependence.
- [Australian English vowel-formant evidence](https://doi.org/10.1016/j.jvoice.2020.09.026): local variety and speaker dependence of acoustic
  articulation evidence.
- [F2 transition review](https://pmc.ncbi.nlm.nih.gov/articles/PMC4056257/) and
  [Central Australian Aboriginal English timing evidence](https://doi.org/10.1080/07268602.2024.2365167): acoustic-proxy and
  language-variety limits.
- [Consumer-device task and repeatability study](https://pubmed.ncbi.nlm.nih.gov/39738817/): feature-specific device and repeatability limits.
- [Plug-and-play microphone comparison](https://pubmed.ncbi.nlm.nih.gov/37972580/): non-equivalence of many measures across practical capture
  paths.
- [GRRAS](https://doi.org/10.1016/j.jclinepi.2010.03.004): the current published
  agreement and reliability reporting guideline. Its
  [GRRAS-COSMIN replacement](https://www.grras-cosmin.org/) remains in development.
- [STARD-AI](https://doi.org/10.1038/s41591-025-03953-8),
  [TRIPOD+AI](https://doi.org/10.1136/bmj-2023-078378) and
  [FUTURE-AI](https://doi.org/10.1136/bmj-2024-081554): later reporting and
  lifecycle standards if screening or prediction is ever approved.

### Australian professional, ethics, privacy and safety sources

- [Speech Pathology Australia AI position statement](https://www.speechpathologyaustralia.org.au/Common/Uploaded%20files/Smart%20Suite/Smart%20Library/dd3436ff-627d-4394-9c28-8e08f113048c/20240508_AI_in_Speech%20Pathology_Position_Statement.pdf): consent, professional judgement, evidence, privacy and safety.
- [Speech Pathology Australia Code of Ethics](https://www.speechpathologyaustralia.org.au/Public/About-Us/Ethics-and-standards/Ethics/Code-of-Ethics.aspx),
  [Professional Standards](https://www.speechpathologyaustralia.org.au/Common/Uploaded%20files/Smart%20Suite/Smart%20Library/386be7e2-9872-4d51-a0fa-4649c740ff1e/SPA_Professional%20Standards%202020_V3_24062020%20FINAL%20.pdf) and
  [self-regulation explanation](https://www.speechpathologyaustralia.org.au/Public/About-Us/Advocacy/Regulation-education-campaign/Regulation-key-definitions.aspx): professional rather than statutory governance.
- [Speech Pathology Australia Voice Best Practice Principles](https://www.speechpathologyaustralia.org.au/Common/Uploaded%20files/Smart%20Suite/Smart%20Library/dd1ad82c-29b5-49fb-9e8c-4474ed763f65/20191216%20-%20Laryngology-%20Voice%20Best%20Practice%20Principles%20Resource.pdf): voice screening and multidisciplinary assessment boundaries.
- [NHMRC National Statement on Ethical Conduct in Human Research 2025](https://www.nhmrc.gov.au/about-us/publications/national-statement-ethical-conduct-human-research-2025): current prospective ethics and research-risk framework.
- [NHMRC Statement on Consumer and Community Involvement](https://www.nhmrc.gov.au/about-us/publications/statement-consumer-and-community-involvement-health-medical-research): equitable, reciprocal and supported involvement.
- [NHMRC Indigenous ethical guidelines](https://www.nhmrc.gov.au/sites/default/files/documents/Indigenous%20guidelines/Indigenous-ethical-guidelines.pdf): community-led values and governance where Aboriginal or Torres Strait Islander people or data are included.
- [People with Disability Australia research services](https://pwd.org.au/services/research-services/),
  [Queenslanders with Disability Network](https://qdn.org.au/about-qdn/) and
  [Health Consumers Queensland payment guidance](https://www.hcq.org.au/paying-consumers/): possible accessible and paid involvement routes, not selected partners.
- [OAIC APP key concepts](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-b-key-concepts),
  [health information](https://www.oaic.gov.au/privacy/your-privacy-rights/health-information/what-is-health-information) and
  [commercial AI privacy guidance](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products): voice, health inference, consent, minimisation and vendor review.
- [OAIC APP 3 collection](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-3-app-3-collection-of-solicited-personal-information),
  [APP 8 cross-border disclosure](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-8-app-8-cross-border-disclosure-of-personal-information),
  [APP 11 security](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information),
  [PIA guide](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/privacy-impact-assessments/guide-to-undertaking-privacy-impact-assessments) and
  [AI training guidance](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models/_nocache): collection, overseas disclosure, security, impact assessment and secondary training controls.
- [TGA software-based medical device guidance](https://www.tga.gov.au/resources/guidance/understanding-how-we-regulate-software-based-medical-devices),
  [clinical decision support guidance](https://www.tga.gov.au/resources/guidance/understanding-clinical-decision-support-system-software-regulation) and
  [active-device classification guidance](https://www.tga.gov.au/resources/guidance/classifying-active-medical-devices-australia-including-software-based-medical-devices): intended purpose and Australian screening boundary.
- [TGA software clinical-trial FAQs](https://www.tga.gov.au/products/medical-devices/software-and-artificial-intelligence-ai/manufacturing/artificial-intelligence-ai-and-medical-device-software-regulation/software-based-medical-devices-faqs),
  [Clinical Trial Notification scheme](https://www.tga.gov.au/products/unapproved-therapeutic-goods/access-pathways/clinical-trials/clinical-trial-notification-ctn-scheme),
  [Australian Clinical Trial Handbook](https://www.tga.gov.au/resources/guidance/australian-clinical-trial-handbook),
  [software exclusions](https://www.tga.gov.au/products/medical-devices/software-and-artificial-intelligence-ai/overview/software-based-medical-device-exclusions),
  [coaching exclusion](https://www.tga.gov.au/resources/guidance/understanding-behavioural-change-or-coaching-software-exclusion) and
  [general wellness exclusion](https://www.tga.gov.au/resources/guidance/understanding-general-health-or-wellness-software-exclusion): research, trial, exclusion and supply questions that must be assessed separately.
- [Current Australian Guidance for AI Adoption](https://www.industry.gov.au/publications/guidance-for-ai-adoption) and
  [legal landscape](https://www.industry.gov.au/publications/guidance-for-ai-adoption/legal-landscape): accountability, impact planning, risk management,
  essential information, testing and monitoring and human control.
- [ACCC guidance on false or misleading claims](https://www.accc.gov.au/consumers/advertising-and-promotions/false-or-misleading-claims): support for accuracy and validation claims.
- [Australian Stroke Foundation FAST signs](https://strokefoundation.org.au/about-stroke/learn/signs-of-stroke): emergency route for sudden slurred speech.

### Redenlab public investigation

- [Redenlab overview](https://redenlab.com/), [protocol design](https://redenlab.com/solution/protocol-design-and-development/),
  [analysis and interpretation](https://redenlab.com/solution/data-analysis-interpretation/) and
  [quality assurance](https://redenlab.com/solution/quality-control-assurance/): public capability and quality claims.
- [Redenlab publications](https://redenlab.com/publications/): relevant research and disclosed affiliations.
- [Redenlab privacy policy](https://redenlab.com/privacy/): public website policy and due-diligence gaps.

## Checkpoint 23A conclusion

There is enough evidence to justify asking professionals and people with lived
experience whether one narrow, controlled research construct is useful. There
is not enough evidence to choose a detector, voice index, cutoff, condition or
screening claim.

Repository acceptance passed after Adam approved the narrow repair to item 22's
historical-snapshot validator. No item 22 closure, final evidence or frozen
contract artifact changed. The exact item 23 acceptance evidence is recorded
below. Adam committed checkpoint 23A as `1d774fc`, then approved checkpoint 23B
planning with adults first on 2026-08-14. The active 23B contract and review
package record every external role and authority as unresolved and keep all
contact, spending, participant work, data use and implementation locked.

## Checkpoint 23A acceptance evidence

Acceptance ran on 2026-08-13. Item 23A changed research planning and the
historical snapshot validator only; it added no item 23 runtime module.

- `caffeinate -dimsu python3
  pipeline/run_all.py --mode conversation --speakers 2 --audio "audio/Westfield
  Mt Gravatt.m4a" --output-dir
  an isolated output directory` exited 0. Run ID
  `a run identifier` completed all 14 stages in 536 seconds. The first
  evaluator attempt reached its established 240 second deadline; the retry
  completed. All 34 evidence-linked claims verified. No `--me` or session
  context was supplied.
- An explicit artifact scan found no item 23, motor speech, rapid-syllable,
  disorder or screening-result field in the isolated output. The run manifest's
  output-directory name was excluded from the content scan because it records
  the developer-chosen path rather than a pipeline feature.
- SHA-256 inventories of `history.json`, `progress.md` and every file under the
  root `output` matched before and after the run.
- `python3 -m voice_prosody.validate`, `python3 -m fluency_events.validate`,
  `python3 -m assessment.validate`, `python3 -m
  assessment.validate_pronunciation`, `python3 -m data_model.validate` and
  `python3 -m progress_model.validate` all passed under the repository's pinned
  Miniforge interpreter. The progress registry still releases zero metrics.
- `python3 -m speech_sound_patterns.validate_final_acceptance` passed using the
  unchanged item 22 closure as a historical snapshot.
- `python3 -m unittest tests.test_speech_sound_final_acceptance -v` passed 40
  tests.
- The final full discovery run reached the optional private variety-probe rebuild
  and blocked in a macOS file read for more than three minutes. It was interrupted
  rather than reported as a pass. A discovery run excluding exactly that one
  private rebuild test then passed all 736 public and locally available tests in
  47.961 seconds. The same private test had skipped cleanly with `Errno 60,
  Operation timed out` in an earlier full run. No private evidence result is
  claimed.
- A second isolated solo pipeline run, ID `20260813T1604317384ce63`, completed
  all expected solo stages in 157 seconds under `caffeinate`, without `--me`.
  Its 17 evidence-linked claims verified, despite correctly recorded low-level
  and reverberation warnings. The complete regression report using both isolated
  real runs and synthetic controls passed: 4 of 4 conversation checks, 5 of 5
  solo checks and every synthetic check.
- `git diff --check` passed. The item 22 repository closure, final evidence,
  final contract and active research contract remain byte-identical to commit
  `5545ced`.

## Checkpoint 23B in-progress record

Adam approved 23B planning with adults first on 2026-08-14. This records a
minimum research-participant age of 18 and leaves children for a separately
approved future study. It does not create a product age gate.

The public preparation layer now contains:

- `governance-review-package.md`, the unsigned intended-use draft, independent
  lane model, Australian governance routes, role and conflict requirements,
  candidate dossiers, access and safety requirements, reference-manual
  requirements, prospective sampling inputs, privacy and consent worksheet,
  regulatory worksheet, no-selection gates and unsent outreach drafts;
- `governance-contract-v1.0.0.json`, a machine-readable record that every lane,
  role, external authority, task, sample size, data permission and release
  boundary remains unresolved or closed;
- `governance.py` and `validate_governance.py`, which reject weakened or hidden
  selections and prove the active pipeline has no item 23 binding;
- `final_decision.py`, which defines the future closure shape for either
  `selection` or `no_selection` without creating a decision and keeps
  participant data, scores, thresholds, releases, implementation and 23C
  approval closed; every public evidence-node hash binds its exact issued
  artifact digest, claims, accountable assignment, scope, candidate and
  dependencies, while its closed graph rejects unknown or cyclic hashes,
  pre-parent records, cross-lane dependencies, responsibility substitution and
  an overall decision that does not bind the complete cited package; the future
  artifact has one product owner, exact truth-owner evidence and organisation
  separation across construct, task, truth, thresholds, custody, release and
  applicable conditional reference owners;
- `governance-record-templates.md`, blank records for owner and sponsor
  identity, role competence, conflicts, lived experience, intended use,
  candidate domains, task access and stopping, institution and HREC authority,
  privacy and security, statistics and splits, regulation and lane decisions;
- `governance-runbook.md`, which separates public repository material from
  future private evidence and defines version and change control;
- `source_survey/`, `build_source_survey.py`, `source_survey.py` and
  `validate_source_survey.py`, the candidate reference source survey: 27
  records covering every publicly identifiable source that could supply motor
  task, perceptual voice or intelligibility reference evidence, with its
  licence, access route and rights state. Its schema cannot express that a
  source meets an item 23 truth requirement, and its validator refuses a
  selection, an authorised acquisition, a non commercial or unobtainable source
  described as open, a registry that disagrees with its own records, any
  acquired data in the repository and any pipeline import; and
- `tests/test_motor_speech_voice_governance.py` and
  `tests/test_motor_speech_voice_final_decision.py`, focused mutation and
  synthetic-structure tests for the current state and future closure rules. Test
  fixtures are not research evidence or selections.

No external person or organisation has been contacted or appointed. No money
has been spent, no account opened, no task or measure selected, no participant
or private evidence accessed, no recording collected or repurposed, and no
pipeline or downstream implementation added.

The next required owner fact is the legal organisation, if any, that owns and
could sponsor the research. Named outreach, exact message text, budget and any
institutional collaboration terms require separate owner decisions. Until real
written reviews fill the applicable roles, checkpoint 23B remains in progress;
this preparation layer cannot satisfy checkpoint acceptance on its own.

## Checkpoint 23B preparation-layer engineering verification

Verification ran on 2026-08-14. This verifies only the public preparation layer
and its fail-closed behavior. It is not checkpoint 23B acceptance, professional
review, sponsor authority, ethics approval, participant permission or a
candidate selection.

- `python3 -m unittest tests.test_motor_speech_voice_governance
  tests.test_motor_speech_voice_final_decision -q` passed 60 tests. The tests
  cover the immutable parent fingerprint, malformed nested records, one
  accountable owner, developer and vendor independence, exact lane and
  candidate binding, signed-artifact and evidence-node integrity, dependency
  closure and chronology, exact blocker dependencies, reference-truth control,
  organisation separation, participant and clinical reference routes, HREC,
  lower-risk, CTN and CTA paths, and every release lock.
- Three read-only adversarial review streams reproduced and drove repairs for
  owner substitution, vendor-controlled blockers, metadata relabelling,
  cross-lane and transitive dependencies, placeholder truth ownership,
  organisation aliasing, conditional scope broadening and missing CTN site
  prerequisites. Their final targeted passes found no reproducible public-schema
  bypass. The remaining human boundary is explicit: code cannot inspect private
  bytes or signatures or decide whether professional advice is substantively
  correct.
- The final full public discovery run passed 796 tests in 73.228 seconds. It
  excluded exactly
  `test_speech_sound_variety_probe.VarietyProbeReportTests.test_the_report_rebuilds_from_the_private_evidence`.
  An earlier discovery command used the wrong exclusion class name, reached
  that optional private rebuild and was interrupted without a result. No
  private content was printed or changed and no private evidence result is
  claimed.
- `python3 -m voice_prosody.validate`, `python3 -m fluency_events.validate`,
  `python3 -m assessment.validate`, `python3 -m
  assessment.validate_pronunciation`, `python3 -m data_model.validate`,
  `python3 -m progress_model.validate`, `python3 -m
  speech_sound_patterns.validate_final_acceptance` and `python3 -m
  motor_speech_voice.validate_governance` all passed under the pinned Miniforge
  interpreter. The progress registry still releases zero metrics, item 22
  remains closed on its valid no-selection path and every item 23 lane remains
  unselected. The explicit item 22 final-acceptance suite passed 40 tests.
- A `caffeinate -dimsu` conversation run used Adam's explicit 108 second test
  recording, an isolated temporary output, no `--me` and no session context.
  Run `20260814T1950091c22d3cf` completed all pipeline stages in 444 seconds.
  Objective extraction and measurement artifacts completed. Both evaluator
  attempts failed the existing semantic claim checks, so the pipeline correctly
  withheld coaching prose and exposed only the safe unavailable report; no
  unverifiable coaching claim was released.
- A `caffeinate -dimsu` solo run used Adam's explicit 141 second solo recording,
  an isolated temporary output, no `--me` and no session context. Run
  `20260814T1958052e87aadd` completed all pipeline stages in 252 seconds. It
  correctly retained the low-level and reverberation warnings. Both evaluator
  attempts again failed semantic claim verification, so coaching prose was
  safely withheld while objective artifacts remained available.
- The combined regression report passed its software snapshot, 4 of 4 real
  conversation artifact checks, 5 of 5 real solo artifact checks and every
  synthetic attribution, timing, renderer, metric and condition control. An
  explicit artifact scan found no item 23 governance, candidate, motor-speech
  or checkpoint field in either run; the only match was the developer-chosen
  temporary directory name recorded by each manifest.
- Before and after both real runs, `history.json` remained
  `156b418a9c83de0c860eaba06bd10e714cd00da8c200e99a268546c7651d0ed5`,
  `progress.md` remained
  `1b05ca629d342825db45534d1d7ddeeb184f105ad56e1f74c6c6bd6757b91347`,
  and the composite SHA 256 for all 32 normal `output` files remained
  `756ad42e4a8ca32e56b0a99fa1e65ecc8dbc113b77ea17b1dbe3de035b6f4348`.
  No item 22 file differs from committed checkpoint 23A state `1d774fc`.
  `git diff --check` and Python bytecode compilation passed.

The engineering preparation is therefore internally verified, but checkpoint
23B remains in progress. It cannot close until Adam identifies the owning and
potential sponsor organisation and real authorised external reviewers complete
the applicable private records. No outreach has been sent and no downstream
work is approved.

## Checkpoint 23B candidate reference source survey

Adam approved a research-only route on 2026-08-19: investigate as far as public
evidence allows, contact nobody, and keep checkpoint 23B open as a shelf-ready
brief rather than closing it. He confirmed on the same date that there is no
legal entity behind the project, that he has no university or clinician
connection, and that he wanted to know whether the work could be done well
using public internet access alone.

This survey answers the part of that question which is answerable without
contacting anybody: **does the independent human reference evidence item 23
requires exist in public, and may this project lawfully use it?**

The machine-checkable result is `source_survey/`, whose registry and 27 records
validate with `python3 -m motor_speech_voice.validate_source_survey`. The
records state what a source could supply, what it may lawfully be used for, and
whether it can be obtained. They select nothing. A record may say a source
`fails` a truth requirement or that the question is `unresolved`; the schema
cannot express that a source *meets* one, because that judgement belongs to the
independent governance roles and not to a survey.

### Why this question was worth a checkpoint

Checkpoint 23A reviewed the clinical and measurement literature thoroughly and
left a specific gap open: representative, consented and commercially lawful
recordings, and independent task, timing, perceptual, functional and clinical
truth. Nobody had asked what actually exists. Item 22 showed what that question
is worth. Its open evidence search "changed the plan more than any outstanding
enquiry would have", because establishing that the whole field of English
corpora with expert phone-level annotation is nine datasets, of which one is
commercially usable here, settled the question permanently instead of leaving it
to optimism.

### What the three lanes need, and what exists

| Lane | Required truth | Located in public | Usable here |
|---|---|---|---|
| Motor task timing and accuracy | Two blinded trained annotators marking cycles and errors, with adjudication | No source | None |
| Perceptual voice | Several blinded qualified raters under a standardised protocol, individual ratings and disagreement retained | One candidate | One, unresolved |
| Intelligibility | Several blinded unfamiliar listeners transcribing orthographically under a fixed condition, retained per listener | Several of the right shape | None |
| Australian English, any lane | Any of the above in the intended variety | None | None |

**The motor lane has no reference truth in public, at any licence and at any
price.** Rapid-syllable recordings exist in quantity. EWA-DB holds 1,649 Slovak
speakers performing a `pataka` task, ALOIS-DB 258, NeuroVoz 112 Castilian
Spanish speakers, VOC-ALS 153 Italian speakers, and PC-GITA a reported 100
Colombian Spanish speakers. Every one of them labels the recordings with a
diagnosis, a clinical rating-scale score, or both.
That is population description. This plan already states that a diagnosis may
describe a study population but is not the numeric ground truth for a primitive,
and the survey is the first time that rule has decided anything. EWA-DB's manual
annotation, which sounds like the exception, is corrected automatic transcription
plus tags for phenomena such as hesitation; it marks no syllable boundary, count,
onset or task error. The one located set that does carry the required evidence,
92 neurotypical adults with two independent annotators marking voice onset times
and vowel durations and boundaries on alternating and sequential tasks, has no
public release at all: the paper carries no data availability statement and the
MIT-licensed code repository ships a model and no data. The ONDRI cohort, which
is the other route, states in print that its inter-annotator agreement is not
available, so its reference cannot report its own uncertainty.

A separate group of deposits looks like a solution and is not one. Several
openly licensed CC BY 4.0 records hold diadochokinetic rate measures, syllable
rates and extracted voice-onset-time features with **no audio at all**. A
published table of numbers from somebody else's protocol cannot check an
implementation, because there is no recording to run the implementation on, and
it is not a reference range for a different task, population or capture path.

**The voice lane has exactly one candidate, and its ceiling is measured.** The
Perceptual Voice Qualities Database is CC BY 4.0, downloadable with no contact,
no account and no agreement, and holds 296 recordings rated by 19 expert raters
across six blocks of three or four listeners. Whether the distributed ratings
file retains individual rater rows or only combined values could not be settled
without opening it, and no acquisition is authorised, so the survey records that
as unresolved rather than assuming either way. Two further facts bind anything
built on it. Its own published reliability analysis pooled ratings across blocks
without accounting for block-specific variability, which risks inflating the
reported reliability. And an independent re-rating by eight speech-language
pathologists on a curated 30-sample subset measured what trained clinicians
actually agree on:

| CAPE-V feature | Inter-rater ICC, vowels | Inter-rater ICC, sentences |
|---|---|---|
| Overall severity | 0.79 good | 0.87 good |
| Breathiness | 0.76 good | 0.70 moderate |
| Roughness | 0.60 moderate | 0.56 moderate |
| Strain | 0.51 moderate | 0.66 moderate |
| Pitch | 0.34 poor | 0.24 poor |
| Loudness | 0.47 poor | 0.47 poor |

Two consequences follow and both are binding. **Pitch and loudness have no
reliable human reference here**, so no candidate measure may be graded against
them; the existing item 20 pitch primitive gains nothing by this route. And on
the most reliable feature the median absolute difference between raters was 14.8
points on vowels and 12.5 on sentences on a 100-point scale, so no future claim
of finer resolution than that can be supported. The re-rating also records that
the source contains incomplete samples, reading errors, audible clinician
instructions and inconsistent recording conditions, that only 187 of its 296
samples carry a specified diagnosis, and that the material is weighted toward
euphonic and mildly impaired voices.

Every other perceptual source fails for a stated reason rather than for want of
looking. The GRB label set attached to the Saarbrücken Voice Database is CC BY
4.0 and openly downloadable, and comes from a **single evaluator**; this plan
states that one clinician cannot substitute, so a free single-rater label set
does not become perceptual truth by being free. NeuroVoz's GRBAS is likewise one
expert, under a non-commercial no-derivatives licence. APROCSA is reported to have used
five raters and released **consensus** values, which would destroy exactly the
disagreement this plan requires be retained; that report was not confirmed at
source and its record says so. The Saarbrücken audio itself, 2,000-plus German
speakers under CC BY 4.0, carries no perceptual rating; VOICED under ODC-BY
carries diagnoses and participant-reported instruments, which are a separate
truth class; and Bridge2AI-Voice, the largest and newest adult voice collection
found at 833 participants, has no rapid-syllable task, no perceptual rating,
credentialed access, a signed agreement and no stated commercial permission.

**The intelligibility lane has sources of the right shape and none this project
may use.** The Speech Accessibility Project, about 999 participants and 1,500
hours, does permit commercial development, and its data use agreement requires
two signatures, one from an authorised representative of the user's
organisation. That is the missing legal entity blocking a route in the most
concrete possible way: the commercial permission is not the obstacle, the
countersignature is. TORGO states verbatim that "Use of this database is free
for academic (non-profit) purposes", which excludes a commercial product
backend. TalkBank and PhonBank, which hold the one located corpus carrying per
listener judgements from unfamiliar crowd listeners, are CC BY-NC-SA 3.0 and
grant clinical-corpus passwords only to full-time faculty or ASHA-certified
clinicians; that corpus is also children, and therefore outside the approved
adults-first scope. UA-Speech's distribution host resolves in DNS and did not
accept a connection. And an Open Science Framework project holding orthographic
transcriptions from **70 unfamiliar listeners**, the closest openly visible match
to the requirement, has **no licence assigned at all**. Public visibility is not
a licence; absent a grant, nothing has been permitted.

One source deserves recording as a warning rather than a lead. The Clarity
Prediction Challenge data has per-listener transcriptions with word-level
correctness under a declared listening condition, which is precisely the file
shape item 23 wants. It measures how well a hearing-aid algorithm renders speech
to a hearing-impaired listener. Using it as talker intelligibility evidence
would attribute the listener's hearing loss and the processing chain to the
speaker. Matching the shape of the evidence is not the same as answering the
question.

**Australian English remains unavailable.** No Australian source carrying any of
the three truth classes was located. Direct DNS and HTTP checks on 2026-08-19
confirmed that `alveo.edu.au`, `app.alveo.edu.au`, `austalk.edu.au` and
`bigasc.edu.au` all still fail to resolve, reproducing exactly what item 22
recorded on 2026-07-29. The one large active Australian corpus covers children
and is outside the approved scope.

### Claims this survey corrected

Three published or reported availability claims were checked and did not hold.
Item 22 established that this matters: a disproved claim is worse than a missing
one because it looks checked.

- EWA-DB's Scientific Data paper states the database is publicly available at
  ELDA and at Zenodo. The Zenodo deposit is access-restricted, records no
  licence and lists no files. The ELDA half is correct, and better than
  expected: ELRA-S0489 offers both a non-commercial and a commercial licence at
  0.00 EUR, requiring an account and a signed agreement rather than a
  negotiation.
- A discovery sweep run during this checkpoint reported AusTalk and Alveo as
  live with working corpus and licence pages. Direct checking on the same day
  contradicted it on every host. The report was rejected. It is recorded because
  an unverified availability claim about the one Australian corpus this project
  would most want is exactly the error that costs weeks.
- Secondary descriptions of the PVQD report four raters with one rating only 16
  percent of cases. The open-access re-rating paper, read at source, reports 19
  expert raters across six blocks. The unread figure is not relied on.

Six records carry a recorded conflict in total, four of them licence strings
that disagree between a repository page and a publication or catalogue. In every
case the repository page is treated as authoritative and the disagreement is
kept in the record rather than resolved, because resolving it would mean
choosing which source to believe without reading the terms that govern.

### What public research alone can and cannot settle

Checkpoint 23B lists thirteen required deliverables. Public research can complete
some of them and cannot begin others. Recording which is which prevents a large
body of honest work being mistaken for progress toward acceptance.

| 23B deliverable | Reachable by public research alone |
|---|---|
| Recorded adults-first scope and child prohibition | Yes, already recorded |
| Source and commercial-rights review, including every proposed transfer | Yes, this survey |
| Prospective sampling inputs and representation targets | Partly; the statistical plan needs a statistician |
| Documented preliminary Australian classification and trial-pathway assessment | Partly; a documented reading is not a regulatory determination |
| Signed intended-use, population, user, action and prohibited-use statement | No, requires signatures |
| Named paid lived-experience governance and independent professional roles | No, requires people |
| Conflict register and decision-rights matrix | No, requires named parties |
| Professionally reviewed task, burden, access, stop and safety protocol | No, requires professional review |
| Construct-specific annotation, listener and clinical-reference manuals | No, requires the relevant professionals |
| Institution pathway and prospective HREC review | No, requires an institution and an ethics body |
| Privacy impact assessment and responsible-entity matrix | No, requires a legal entity to be the entity |
| Versioned split allocation before pilot access | Not yet; there is no pilot to allocate |
| Recorded `selection` or `no_selection` | No; a selection requires the reviews above |

The ceiling is therefore explicit. Research of this kind can produce a
well-founded decision and an accurate map of what is and is not possible. It
cannot produce checkpoint 23B acceptance, because acceptance is defined as
written review by accountable roles, and no amount of public evidence
substitutes for that.

### What this changes

Nothing is selected, nothing is acquired and no lane moves. Four things are now
established rather than assumed.

1. **The motor-speech question cannot be advanced through public data at all.**
   Any future rapid-syllable timing or accuracy claim depends on prospective
   collection with recruited participants and paid trained annotators, which is
   exactly the work checkpoint 23B cannot authorise without professional
   governance and ethics review. There is no cheaper path and no partial one.
2. **The voice question has one usable reference and a measured ceiling.** If
   independent voice governance ever accepts it, work against it is bounded by
   roughly 12 to 15 points of ordinary clinician disagreement on a 100-point
   scale, and pitch and loudness are excluded outright.
3. **The absent legal entity is now a demonstrated blocker, not a formality.**
   It is the specific reason the largest relevant modern corpus cannot be
   requested.
4. **One question is answerable and cheap.** Whether the PVQD distributes
   individual rater rows decides whether the single open perceptual candidate is
   usable at all. It needs one openly licensed spreadsheet to be opened, and
   that is an owner decision rather than an agent one.

### What this survey deliberately did not do

Two omissions are choices rather than gaps, and are recorded so nobody treats
them as oversights.

It did not repeat checkpoint 23A's clinical and measurement literature review.
That review already established the heterogeneity of rapid-syllable tasks across
360 articles, the limits of maximum-performance tasks as proxies for ordinary
speech, and the multidimensional nature of voice assessment. Repeating it would
have added length and no evidence.

It did not assemble normative variability figures for rapid-syllable rate in
healthy adults, which would be needed to know whether any future change could be
meaningful. That question belongs with measurement error and smallest detectable
change at checkpoints 23C and 23D, it cannot be answered without a task and a
capture path, and both remain unselected. Gathering published normative ranges
now would produce numbers from other people's protocols with no defined task to
attach them to, which is the same error the derived-measure deposits above
represent.

One question was left open that could have been closed cheaply. Whether the
PVQD's ratings file retains individual rater rows needs one openly licensed
spreadsheet to be opened. Acquiring anything, even a small openly licensed
label file, is an owner decision rather than an agent one, and the survey states
the question rather than quietly resolving it.

The survey creates no runtime package, task, artifact, screen or product output,
imports nothing into the pipeline, acquires no data, contacts nobody and spends
nothing. Checkpoint 23B remains in progress.

## Checkpoint 23B source survey engineering verification

Verification ran on 2026-08-19 under the pinned Miniforge interpreter. It
verifies the survey artifact and its boundaries. It is not checkpoint 23B
acceptance, professional review, sponsor authority, ethics approval, participant
permission, an acquisition decision or a candidate selection.

- `python3 -m motor_speech_voice.build_source_survey` wrote 27 records and the
  registry. `python3 -m motor_speech_voice.validate_source_survey` passed,
  reporting 27 sources surveyed, 11 obtainable with no contact, account or
  agreement, 10 carrying a licence that permits commercial use, none recorded as
  meeting an item 23 truth requirement and none selected.
- `python3 -m unittest tests.test_motor_speech_voice_source_survey` passed 31
  tests. They prove the schema cannot express a met truth requirement, that a
  non commercial source, an unlicensed source, a source needing an agreement and
  an unverified report each cannot be described as open, that a direct
  verification claim without a dated inspected material is refused, that a
  record cannot record a selection or authorise acquisition, that the registry
  cannot hide, invent or overstate a record, that no cross source rule may be
  weakened, and that each lane conclusion and the limitations survive.
- The three item 23 suites together, `tests.test_motor_speech_voice_governance`,
  `tests.test_motor_speech_voice_final_decision` and
  `tests.test_motor_speech_voice_source_survey`, passed 91 tests.
- All nine repository validators passed: `voice_prosody.validate`,
  `fluency_events.validate`, `assessment.validate`,
  `assessment.validate_pronunciation`, `data_model.validate`,
  `progress_model.validate`, `speech_sound_patterns.validate_final_acceptance`,
  `motor_speech_voice.validate_governance` and
  `motor_speech_voice.validate_source_survey`.
- The full public suite ran 820 tests in 72.351 seconds, excluding only the
  optional private variety-probe rebuild. 803 passed and 17 errored, all of them
  in `tests.test_speech_sound_final_acceptance` and all raising the same
  `normal pipeline version differs from frozen baseline`. **Those failures are
  not caused by this checkpoint.** Clean detached worktrees prove it: at
  `16c5519` that module runs 40 tests and passes, and at `800d47e`, the current
  `HEAD`, it collects 33 and errors 17. Commit `800d47e` raised
  `PIPELINE_VERSION` from `0.10.1` to `0.11.0`, while item 22's frozen
  `final-evidence-v1.0.0.json` records `frozen_pre_22h_pipeline_version` as
  `0.10.1` and `final_acceptance.py` compares the two. The committed report still
  validates, because its validator reads the recorded report rather than
  rebuilding from live state; only the rebuild path fails. Repairing it is a
  separate decision, because the item 22 closure is an immutable historical
  snapshot and must not be edited to make a test pass.
- A `caffeinate -dimsu` conversation run used Adam's 108 second test recording,
  an isolated temporary output, no `--me` and no session context. Run
  `20260819T0842445cad325d` completed every stage in 494 seconds. The evaluator
  failed its semantic claim checks on both attempts and degraded safely, so
  coaching prose was withheld and the safe unavailable report was exposed, which
  matches the behaviour recorded at the previous checkpoint.
- A `caffeinate -dimsu` solo run used Adam's 141 second solo recording, an
  isolated temporary output, no `--me` and no session context. Run
  `20260819T08511977000214` completed every stage in 240 seconds and released a
  verified evaluation whose unavailable dimensions carry explicit reasons.
- An artifact scan for item 23 terms across both runs found no governance,
  survey, candidate source or motor speech field. The single match was
  `reference_truth_status` in `fluency_events.json`, which is the committed item
  21 field whose value is `not_reference_truth`; that is the artifact declaring
  what it is not, and it predates this work.
- Before and after both real runs, `history.json` remained
  `156b418a9c83de0c860eaba06bd10e714cd00da8c200e99a268546c7651d0ed5`,
  `progress.md` remained
  `1b05ca629d342825db45534d1d7ddeeb184f105ad56e1f74c6c6bd6757b91347`,
  and the composite SHA 256 for all 32 normal `output` files remained
  `756ad42e4a8ca32e56b0a99fa1e65ecc8dbc113b77ea17b1dbe3de035b6f4348`.
- No item 22 file changed. `governance-contract-v1.0.0.json`, `governance.py`
  and `final_decision.py` are untouched, so the immutable in-progress contract
  and its canonical digest are unaffected. The survey directory contains JSON
  records only, the planned private evidence root does not exist, and the active
  pipeline contains no item 23 import. `git diff --check` and bytecode
  compilation passed.

Nothing was downloaded, nobody was contacted, no account was created, no terms
were accepted and nothing was spent. Checkpoint 23B remains in progress.

## Checkpoint 23B measurement and sampling input package

Checkpoint 23B's seventh deliverable is a prospective acquisition, sample size,
representation, split and statistical plan. Public research cannot produce that
plan. A plan needs an independent statistician, a selected construct and pilot
variance, and item 23 has none of the three. What public research can produce is
the set of inputs that statistician would have to be given, written down once per
provisional construct so the question is ready the day a real statistician
exists.

The machine-checkable result is `measurement_plan/`, whose twelve records and
registry validate with `python3 -m motor_speech_voice.validate_measurement_plan`.
There is one record for every row of the checkpoint 23A provisional construct
register. Each states the narrowest defensible observation exactly as the
register words it, the truth class that would have to establish it, what the
source survey found about obtaining that truth, the variation a design would
have to separate, the inputs only a statistician can supply, the reporting
standards that would govern the result, and what blocks the question today.

Two structural rules make the artifact hard to misread later.

**A record may contain no JSON number at all.** Every legitimate quantity in this
material lives inside a citation or a formula written as words, so a bare number
would be something computed, and this package computes nothing. The validator
refuses one and reports where it was.

**The computed sample size is typed `null` in the schema.** The plan already
says that thirty or one hundred is not a scientific plan; this makes that
structural rather than aspirational. A sample size cannot be written into a
record even by accident.

### What the package says about each lane

| Governance lane | Questions | Reference position |
|---|---|---|
| Motor speech | 2 | No qualifying public source at any licence and at any price |
| General speech | 2 | Not surveyed; public availability unknown |
| Voice | 3 | One open perceptual candidate with a measured agreement ceiling |
| Controlled intelligibility | 2 | Sources of the right shape, none lawfully usable here |
| Participant report | 2 | Not applicable; the participant is the only valid source |
| Clinical or laryngeal reference | 0 | Not required, because no clinical claim is proposed |
| Unassigned | 1 | The register row does not map onto one lane, and an agent may not assign it |

The acoustic articulation row is deliberately left unassigned. It could sit in
the motor lane or the general speech lane, the register does not say, and
choosing would be a governance act rather than a clerical one.

### The validator cross-checks the source survey, and that caught two errors

A record's reference availability must agree with what the checkpoint 23B source
survey actually recorded, and the validator enforces it. Building the package
surfaced two modelling errors that the prose alone would have hidden.

The first was conflating a source's truth adequacy with its obtainability. The
one located set carrying two independent annotators on rapid syllable material is
`unresolved` on whether it meets the truth requirement, and simultaneously has no
public release at all. It is an open question and not a candidate.

The second was conflating obtainability with lawful usability. The closest openly
visible intelligibility collection is downloadable and carries no licence, so it
is obtainable and nothing about it has been permitted.

The rule now defers to the survey's own combined judgement, its
`open_but_truth_class_unresolved` eligibility decision, which exactly one of the
twenty seven sources carries. That keeps the two artifacts from drifting apart on
the definition, and it reproduces the survey's own finding that the voice lane
has exactly one candidate.

### Method facts that bind later work

**There are two standard error of measurement formulas and they are not
interchangeable.** One is reliability based, the sample standard deviation times
the square root of one minus the reliability, and it moves with how heterogeneous
the sample is. The other is agreement based and is the within-subject standard
deviation, the square root of the residual mean square from a one-way analysis of
variance, in the units of the measurement. Which one a study uses is an input,
because the same data gives different numbers.

**The smallest detectable change is 1.96 times the square root of two times the
standard error of measurement**, equivalently 2.77 times the within-subject
standard deviation. Reporting a change smaller than that as real is a measurement
error rather than a finding.

**The familiar intraclass correlation bands are conditional and are routinely
quoted as though they were not.** Their authors state that there are no standard
values for acceptable reliability, that they assume roughly thirty heterogeneous
samples and at least three raters, that a low value can reflect a homogeneous
sample rather than poor agreement, and that the confidence interval rather than
the point estimate should decide the level. This matters directly here, because
this repository already quotes those bands when reporting the one open perceptual
voice source's agreement ceiling.

**Every recognised reliability sizing method needs an anticipated reliability or
prior variance components as an input.** None of them can produce it. That single
missing quantity is why the deliverable cannot be completed rather than merely
being unfinished.

### What this package deliberately did not do

It did not choose a construct, a task, an estimand, a statistic, a threshold or a
design, and the schema cannot express any of those choices.

It did not gather published normative variability figures. Checkpoint 23B's
source survey already recorded why: numbers from other people's protocols with no
defined task to attach them to are the same error as the derived-measure deposits
that carry no audio.

It did not resolve which of the twelve questions is worth asking. The governance
group may reject the entire register, in which case some of these records
describe questions nobody will ever ask.

## Checkpoint 23B documented Australian regulatory and privacy reading

Checkpoint 23B's ninth and twelfth deliverables are a privacy impact assessment
and a documented preliminary Australian classification and clinical trial pathway
assessment. Neither can be produced here. A privacy impact assessment names the
responsible entity and there is none, and a classification assessment must be
documented by a qualified Australian specialist. What public research can produce
is an accurate reading of the public rules with the operative wording quoted and
the open questions named.

The machine-checkable result is `regulatory_reading/`, whose sixteen records and
registry validate with
`python3 -m motor_speech_voice.validate_regulatory_reading`. Every record is a
documented reading by a non lawyer, records eighteen open questions and three
source conflicts, and names at least one accountable human role that must
actually settle it. The schema cannot express that a record is advice, a
determination or an approval.

### The reading is organised as a ladder, because the answer follows the claim

Australian medical device regulation turns on intended purpose rather than on
technology. The same speech measurement sits in a different place depending only
on what is claimed for it, so a single verdict would be less true and less
useful than locating where the answer changes.

| Rung | Intended purpose | Position |
|---|---|---|
| One, occupied today | Firewalled developer research, nothing shown to anyone, nothing supplied | Likely outside the medical device definition |
| Two, hypothetical | Consumer communication coaching, no claim about any disease or condition | May be a device, and may be excluded |
| Three, hypothetical | Consumer feature telling a person their speech may indicate a condition worth professional assessment | A device, with no exclusion available |

The validator pins rung three and refuses a ladder that stops getting stricter or
whose occupied rung has moved. Softening the screening rung later is the specific
failure this guards against.

### What the reading found

**The regulator's own example is this ladder in another organ system.** An app
that measures and displays heart rate for fitness is not a device; the same app
that detects bradycardia or tachycardia is. The measurement did not change, the
claim did. Intended purpose is read off labelling, instructions, advertising and
technical documentation, so a sentence on a marketing page is a regulatory act.

**Checkpoint 23E's described action is close to verbatim the regulator's
definition of screening.** Classification rule 4.5 defines screening as detecting
potential disease indicators in otherwise healthy, asymptomatic individuals in
order to determine whether a confirmatory diagnostic test is warranted. Checkpoint
23E contemplates indicating whether a professional assessment route should be
studied. Those are the same sentence in different words.

**The reading for a consumer facing screening result is Class IIb.** Rule
4.5(1)(d) applies where the device gives the screening result to the user and the
condition is serious, which is the same class the regulator's own examples give
to diagnosing emphysema from a CT scan. Routing the information to a health
professional instead drops it one class to Class IIa under rule 4.5(2)(b).

**That mitigation may not be available, for a genuinely non obvious reason.** The
Regulations' definition of health professional names ten occupations and
otherwise requires registration under a state or territory law. Speech pathology
is neither. The national practitioner regulator states in its own words that
speech pathologists are among those working in healthcare who are not registered
health practitioners. A designer would reasonably assume that routing a result to
a speech pathologist is the cautious choice; under this reading it may not reduce
the regulatory burden at all.

**The clinical decision support exemption is closed three times over.** It is
unavailable for software providing decision support directly to patients or any
non health professional user, the regulator states plainly that an AI-enabled
clinical decision support system will not meet the exemption criteria, and its
first criterion turns on the same health professional definition.

**The wellness and coaching exclusions have different thresholds, and the
multiple function rule is the sharp edge.** Item 14B is lost only for a serious
disease or condition; item 14C is lost for diagnosis, prognosis or a treatment
decision about any condition, serious or not. Every function of a product must
meet the exclusion criteria, so one screening feature inside an otherwise
excluded coaching product takes the whole product out.

**The self-management exclusion is the one least likely to cover a future speech
support mode.** Item 14A applies only to a condition that is not serious, and the
regulator's own test for serious is whether a professional is needed to evaluate
and treat it effectively. The product vision already places speech support later
and behind professional involvement; this is an independent second reason for
that ordering, and it is not improved by better measurement.

**The missing legal entity now blocks three separate routes concretely.** The
source survey found it blocking the largest relevant intelligibility corpus
through a data use agreement countersignature. A clinical trial notification is
submitted by the Australian clinical trial sponsor and needs an ethics decision
and an institution as approving authority. And a medical device sponsor must be
an Australian legal entity. Supply includes free supply through a website or app
store, so charging nothing does not avoid it.

**The clinical trial question is structurally unanswerable here.** The regulator
states that the researcher must consult their ethics committee to determine
whether the study is a clinical trial and that it does not give advice on the
question. Obtaining an ethics committee is itself unresolved, so the regulatory
route waits on the ethics route and the ethics route is the harder one.

### Privacy, and one exposure this repository had not recorded

**The protection an unincorporated individual actually has is section 7B(1)**,
which exempts acts done other than in the course of a business carried on by the
individual. It is not the small business exemption and not the personal affairs
carve-out, which is narrower and probably does not cover building a research
corpus. Section 7B(1) stops covering the work the moment any business is carried
on, and the health service limb removes small business operator status at any
turnover including zero.

**Speech recordings can be sensitive information by the shortest route, and it
needs no health service.** Health information covers information or an opinion
about the health, including an illness, disability or injury, of an individual. A
recording that evidences a speech or neurological condition is on its face that.
The biometric route is narrower than it looks, because it is conditional on use
for automated verification or identification, though the separate biometric
template limb carries no such condition and is undefined in the Act.

**A statutory tort of serious invasion of privacy has been in force since 10 June
2025, and nothing in the repository recorded it.** It runs against another
person, with no entity requirement, no turnover threshold and no privacy
principle analysis. It is actionable without proof of damage, and the court is
directed to consider the means and technology used and the purpose. Every shield
in the other privacy records is irrelevant to it. It applies to Adam personally
today and would not be removed by forming a company. It belongs in the future
privacy impact assessment as its own item, because compliance with the privacy
principles is not a defence to it.

**Queensland treats recording and sharing as two questions with two answers.** A
party to a private conversation may record it. The same party then commits an
offence by communicating or publishing the record, or any statement prepared from
it, to any other person without the consent of all other parties. Handing
recordings or transcripts to annotators and listeners is on its face that second
act. Whether a consented research session is a private conversation at all is a
prior question that a lawyer must read against the actual consent materials. The
practical consequence is that consent must cover onward sharing, not only
recording.

**Commonwealth interception law does not apply to local capture.** The
prohibition is confined to a communication passing over a telecommunications
system, and the definition requires the recording to occur in its passage over
that system. This narrows an open item the plan previously listed to the case
where a session is conducted over a call.

### Ethics review has no guaranteed route

No Australian body is obliged to review an unaffiliated individual's research.
The national guidance goes no further than saying such researchers may contact
committees and discuss matters with them. Two Queensland universities checked
directly show the spread: one will not review a project with no involvement of
its own and requires one of its own staff as chief investigator, the other states
flatly that it does not accept applications from unaffiliated researchers.

The National Statement's compliance duties are addressed to institutions
throughout. Its one sentence written for a researcher with no institution points
to requesting an exemption from an ethics review body, and a separate paragraph
blocks exemption for research using personal information without consent.

Whether this research would be more than low risk, and so require a full
committee, is not obvious either way. A study in which trained listeners rate
individuals' speech must be assessed against harm categories that include
psychological harm and devaluation of personal worth.

One vocabulary correction: the 2025 National Statement does not use the term
negligible risk anywhere. The lower risk band is now low risk or minimal risk.
Any note using the older term is out of date.

### Conflicts recorded rather than resolved

Three source conflicts are on record. The excluded goods instrument's coaching
item does not list screening while the regulator's guidance for the same
exclusion does. The regulator's consumer facing biometric page states flatly that
voice is sensitive biometric information while the statute and its own principle
guidelines carry a purpose qualifier. And the national ethics body's main page
states the 2025 National Statement came into effect on 23 June 2026 while its own
update FAQ still says early 2026, date to be advised. In each case both are
recorded and neither is preferred, because resolving a conflict means choosing
which source to believe.

### What this reading is not

It is not the privacy impact assessment or the classification assessment the
checkpoint requires, it is not legal or regulatory advice, it names no condition,
and it does not say that any rung of the ladder is safe to build. Rungs two and
three are hypothetical and neither is proposed.

## Checkpoint 23B deliverable ledger

A large amount of honest public research has now been done, and none of it moves
the checkpoint closer to acceptance. `checkpoint-23b-ledger-v1.0.0.json` exists
so that volume cannot be mistaken for progress. It validates with
`python3 -m motor_speech_voice.validate_checkpoint_ledger`.

Of the thirteen required deliverables, **two are complete, three were advanced
but remain unfinished, and eight are blocked on a named human role.**

The two complete ones are the recorded adults-first scope, which an owner
decision alone could settle, and the source and commercial rights review.
Complete does not mean favourable: the rights review's finding is that the motor
lane has no qualifying public source at any licence and at any price.

The three partial ones are the sampling and statistical plan, the privacy impact
assessment and the Australian classification and trial pathway assessment. Each
is blocked on a person rather than on information: a statistician, a legal entity
and a regulatory specialist respectively.

The validator refuses a ledger that closes the checkpoint, claims a selection, a
contact, a spend or an acquisition, marks a deliverable complete without evidence
that exists on disk, marks one unfinished without naming who must finish it, or
leaves nothing blocked at all. A checkpoint with nothing blocked would be one
public research could close by itself, and this one cannot be.

## Checkpoint 23B measurement, regulatory and ledger engineering verification

Verification ran on 2026-08-20 under the pinned Miniforge interpreter. It
verifies these three artifacts and their boundaries. It is not checkpoint 23B
acceptance, professional review, legal or regulatory advice, sponsor authority,
ethics approval, participant permission or a candidate selection.

- `python3 -m motor_speech_voice.build_measurement_plan` wrote 12 records and the
  registry, one for every row of the checkpoint 23A construct register.
  `python3 -m motor_speech_voice.validate_measurement_plan` passed, reporting that
  no construct, task, estimand, statistic or threshold is selected and that no
  sample size is computed.
- `python3 -m motor_speech_voice.build_regulatory_reading` wrote 16 records and
  the registry across six domains.
  `python3 -m motor_speech_voice.validate_regulatory_reading` passed, reporting 18
  open questions and 3 source conflicts recorded rather than resolved, and no
  determination, approval or advice.
- `python3 -m motor_speech_voice.build_checkpoint_ledger` wrote the ledger.
  `python3 -m motor_speech_voice.validate_checkpoint_ledger` passed, reporting 2
  deliverables complete, 3 advanced but unfinished and 8 blocked on a named human
  role, with checkpoint 23B still in progress.
- The three new focused suites passed 88 tests: 38 for the measurement inputs, 28
  for the regulatory reading and 22 for the ledger. They prove that a JSON number
  anywhere in a measurement record is refused, that a selected construct, estimand,
  claim level or computed sample size is refused, that dropping an honest blocker
  is refused, that a reference availability claim disagreeing with the source
  survey is refused, that a reading claiming to be advice, a determination or an
  authority is refused, that a reading resting only on secondary description is
  refused, that softening or flattening the intended purpose ladder is refused,
  that no reading names a condition, and that a ledger which closes the
  checkpoint, invents evidence or leaves nothing blocked is refused.
- All six item 23 suites together passed 179 tests.
- All twelve repository validators passed: `voice_prosody.validate`,
  `fluency_events.validate`, `assessment.validate`,
  `assessment.validate_pronunciation`, `data_model.validate`,
  `progress_model.validate`, `speech_sound_patterns.validate_final_acceptance`,
  `motor_speech_voice.validate_governance`,
  `motor_speech_voice.validate_source_survey`,
  `motor_speech_voice.validate_measurement_plan`,
  `motor_speech_voice.validate_regulatory_reading` and
  `motor_speech_voice.validate_checkpoint_ledger`.
- The full public suite ran 893 tests and passed, excluding only the optional
  private variety-probe rebuild. The same command on the unchanged tree before
  this work ran 805, so the difference is exactly the 88 tests added here and
  nothing else moved.
- A `caffeinate -dimsu` conversation run used Adam's 108 second test recording, an
  isolated temporary output, no `--me` and no session context. Run
  `20260820T1040187ebd1888` passed the audio quality gate and completed all 13
  following stages. The evaluator failed its semantic claim checks on both
  attempts and degraded safely, so coaching prose was withheld and the safe
  unavailable report was exposed, which matches the behaviour recorded at the
  previous checkpoint.
- A `caffeinate -dimsu` solo run used Adam's 141 second solo recording, an
  isolated temporary output, no `--me` and no session context. Run
  `20260820T1046430fc552b3` completed all 11 stages. **This run degraded where the
  2026-08-19 solo run released a verified evaluation.** That difference is not
  caused by this work and must not be recorded as if it were: no pipeline file was
  touched, all three validators confirm no item 23 import reaches the runtime
  package, and the evaluator is a remote enrichment stage whose output varies
  between runs. The safety property held in both cases, which is that unverified
  coaching prose is withheld rather than released.
- The combined regression report passed its software snapshot, 4 of 4 real
  conversation artifact checks, 5 of 5 real solo artifact checks and every
  synthetic attribution, timing, renderer, metric and condition control.
- An artifact scan for item 23 terms across both runs found no measurement,
  regulatory, ledger, survey, governance or motor speech field. The only prior
  match, `reference_truth_status` in `fluency_events.json`, still carries the
  committed item 21 value `not_reference_truth`, which is the artifact declaring
  what it is not.
- Before and after both real runs, `history.json` remained
  `156b418a9c83de0c860eaba06bd10e714cd00da8c200e99a268546c7651d0ed5`,
  `progress.md` remained
  `1b05ca629d342825db45534d1d7ddeeb184f105ad56e1f74c6c6bd6757b91347`,
  and the composite SHA 256 for all 32 normal `output` files remained
  `756ad42e4a8ca32e56b0a99fa1e65ecc8dbc113b77ea17b1dbe3de035b6f4348`.
- No item 22 file changed, and no file under `assessment`, `data_model`,
  `progress_model`, `voice_prosody` or `fluency_events` changed.
  `governance-contract-v1.0.0.json`, `governance.py` and `final_decision.py` are
  untouched, so the immutable in-progress contract and its canonical digest are
  unaffected. The three new directories contain JSON records only, the planned
  private evidence root does not exist, and the active pipeline contains no item
  23 import. `git diff --check` and bytecode compilation passed.

Nothing was downloaded, nobody was contacted, no account was created, no terms
were accepted and nothing was spent. Checkpoint 23B remains in progress, and this
work moved two of its thirteen deliverables from not started to as far as public
research can reach while proving the other eleven still need people.
