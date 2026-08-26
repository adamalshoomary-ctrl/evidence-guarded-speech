# Speech measurement starting assessment research and protocol

Version: 1.0.0  
Status: pilot design, not validated  
Reviewed with the owner: 2026-07-19

## Decision summary

The first assessment is a roughly ten minute English speech measurement
sample. It creates a provisional starting profile, not a diagnosis, permanent
level, overall communication score, or comparison with other people.

The owner approved these boundaries:

- the backend has no age gate, does not collect exact age, and uses no age
  norms;
- English is the first launch language, with separate versioned language packs
  required later;
- sustained sounds and repeated phrase probes are optional research tasks;
- rapid syllable and pronunciation word tasks stay locked until their later
  evidence work is approved;
- this item defines the protocol only and designs no interface.

The normal assessment contains a technical check, a fixed-content sample, a
natural sample, a personally meaningful sample, a short separated repeat, and
self report. These task types remain separate because they answer different
questions.

## Why these tasks exist

| Task | Why it is included | What it cannot establish |
|---|---|---|
| Goal, context, consent and accommodations | Coaching must relate to a situation the person values and record factors that change task meaning. | It is not acoustic evidence and must not be replaced by inferred context. |
| Five seconds of quiet plus comfortable speech | Detects microphone and room failure before it becomes a statement about the person. | Uncalibrated amplitude is not true vocal sound pressure level. |
| Fixed English reading | Holds content reasonably stable for task-specific pace, pause and prosody observations. | It also depends on literacy and preparation and cannot represent spontaneous communication. |
| Spoken repetition alternative | Gives access when reading is unsuitable. | Hearing, memory and playback affect it, so it is not equivalent to reading. |
| Spontaneous explanation | Samples natural planning, language and delivery on a familiar low-risk topic. | Topic knowledge, language, anxiety and cognitive load remain mixed together. |
| Goal-specific response | Samples the interview, presentation, exam, demonstration, important conversation or confidence context the person values. | Different goals and prompt difficulty cannot rank people or be silently compared. |
| Short anchor repeat | Provides narrow within-session repeat evidence after intervening tasks. | It cannot establish day-to-day stability, improvement, retention or mastery. |
| Self reflection | Records difficulty, representativeness and temporary context from the person. | Self report remains separate from measurements and listener perceptions. |

The fixed passage and all task instructions are original repository text. The
protocol does not reproduce or call itself CAPE-V or another licensed test.

## Evidence behind the task pattern

- An ASHA expert panel recommends a short background-noise sample, controlled
  microphone placement, comfortable sustained vowels of three to five seconds
  repeated three times, and connected speech for instrumental voice
  assessment. It also warns that uncalibrated amplitude cannot be treated as
  absolute sound pressure level. This supports the capture pattern, not a voice
  diagnosis in this product. [Patel et al., 2018](https://pubs.asha.org/doi/10.1044/2018_AJSLP-17-0009)
- ASHA describes sustained vowels, sentences and running speech as distinct
  parts of professional auditory-perceptual voice assessment. Physicians and
  appropriately trained professionals retain the relevant diagnostic roles.
  [ASHA voice guidance](https://www.asha.org/practice-portal/clinical-topics/voice-disorders/)
- Reading and spontaneous speech produce different respiratory, timing and
  pitch behaviour. A fixed reading sample therefore cannot stand in for
  natural communication. [Task comparison study](https://pmc.ncbi.nlm.nih.gov/articles/PMC2945274/)
- Functional communication depends on the activity, participation goal and
  environment, supporting a user-selected goal task and declared context.
  [WHO ICF](https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health)
- Device, platform and microphone conditions can materially change acoustic
  measurements. Fundamental frequency is often more robust than amplitude,
  jitter, shimmer or several fine timing measures. The manifest therefore
  requires device and quality context and prevents device failures from
  lowering a measurement result. [Telepractice platform study](https://pubmed.ncbi.nlm.nih.gov/34157251/),
  [cross-device study](https://pubmed.ncbi.nlm.nih.gov/39738817/)
- Multilingual and dialectal variation must not be confused with disorder.
  Standardised scores are not valid when the person is not represented by the
  intended language population. This protocol supports English only rather
  than silently applying English tasks to everyone.
  [ASHA multilingual guidance](https://www.asha.org/practice-portal/professional-issues/multilingual-service-delivery/)
- Speech learning can remain specific to trained utterances. A strong repeat of
  the same prompt is not proof that the skill transfers to a new situation.
  [Speech transfer study](https://pubmed.ncbi.nlm.nih.gov/22190628/)
- Practice performance and durable learning are different. Conditions that
  make immediate practice look better can produce weaker later retention or
  transfer. [Schmidt and Bjork](https://doi.org/10.1111/j.1467-9280.1992.tb00029.x)
- The useful level of challenge depends on both the task and the learner; the
  evidence does not justify one universal success percentage.
  [Challenge Point Framework](https://pubmed.ncbi.nlm.nih.gov/15130871/)

The exact ten minute schedule and prompt wording are product design decisions
informed by this evidence. They are not validated universal standards.

## Core session

The target is 540 seconds, with an acceptable range of 480 to 660 seconds.
About five minutes are recorded speech and the remainder covers explanation,
preparation, quality correction, choices and reflection.

1. Context, consent and accommodations, target 60 seconds.
2. Recording check, target 30 seconds.
3. Fixed English reading or the explicitly different spoken alternative,
   target 90 seconds.
4. Spontaneous explanation, target 120 seconds including preparation.
5. Goal-specific response, target 150 seconds including preparation.
6. A short repeat matched to the reading or spoken option used earlier, target
   50 seconds including preparation.
7. Self reflection, target 40 seconds.

At most one optional short repeat may be requested when technical,
transcription, speaker or sample uncertainty may be resolved. It may never be
triggered because the system dislikes the person's style or assigns a low skill
interpretation.

## Age, language and accessibility

There is no backend age restriction and no exact age field. This avoids an
unnecessary barrier and prevents age-based scoring. It does not remove the need
for an appropriate public-launch consent and privacy design for a person who
cannot independently understand or provide consent. Australian guidance treats
capacity for people under 18 case by case.
[OAIC children guidance](https://www.oaic.gov.au/privacy/your-privacy-rights/more-privacy-rights/children-and-young-people)

English is the only supported version 1 language. Automatic language detection
is evidence to confirm with the user, not truth. Later languages require their
own prompts, expected text, evidence review and version. Translations are not
assumed comparable.

Before recording, the person can choose spoken or text instructions, extra
preparation time, text sizing and spacing, topic changes, pause and resume, or
the spoken alternative to reading. If an accommodation changes what a timed
measurement means, the recording remains useful but that measurement becomes
unavailable or noncomparable. Clear instructions, alternatives and error
recovery follow the accessibility direction of
[WCAG 2.2](https://www.w3.org/TR/WCAG22/).

The later repeat stays in the same mode: reading pairs with a reading excerpt,
while the spoken alternative pairs with two spoken sentences. The manifest
validator blocks mismatched pairs so an accessibility choice cannot silently
turn back into a reading requirement.

## Consent and data boundaries

Coaching processing, raw audio retention, human review, research collection,
model improvement and optional fairness metadata are separate choices. Every
choice defaults off. Only speech measurement processing is required to run an
assessment. Declining another use cannot reduce access to anything else.

The manifest deliberately does not invent the future app's retention period.
A concrete storage, deletion, processor and overseas disclosure policy must be
approved before public collection. Australian guidance requires necessary and
proportionate collection, clear notice, security, and destruction or
de-identification when information is no longer needed.
[OAIC collection guidance](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-3-app-3-collection-of-solicited-personal-information),
[OAIC notification guidance](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-5-app-5-notification-of-the-collection-of-personal-information),
[OAIC security guidance](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information)

Fairness metadata is private audit evidence only. It cannot choose lessons,
change levels or appear in user-facing scores. Race, ethnicity, nationality,
gender, sex, age, disability, diagnosis, socioeconomic status or identity must
never be inferred from voice. Fairness evaluation later requires representative
participants, deployment-like conditions, uncertainty and affected-community
involvement. [NIST AI RMF](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)

## Optional research and locked tasks

The normal assessment does not contain clinical-looking sound tasks.

- A comfortable sustained `ah`, repeated three times for three to five seconds,
  is defined as optional research. It never affects the interpretation, level,
  progress or
  diagnosis and stops for discomfort, pain, dizziness or unusual shortness of
  breath.
- An ordinary sentence repeated three times is also optional research and is
  not a speed test.
- Rapid syllable sequences remain locked because methods vary with language,
  age and protocol and consumer devices can reduce their reliability.
- Pronunciation word packs remain locked until legitimate accent and dialect
  variants, independent human phonetic truth and professional review exist.

The separate research method and provider comparison are defined in
`pronunciation-research-and-protocol.md`. This does not unlock the task: its
word list still requires professional variant review, independent human
labelled evaluation and a separate owner release decision.

These tasks require separate research consent. Skipping them never blocks the
assessment.

## Progression handoff

The assessment may later choose one provisional first skill and explain why in
one sentence. It may not create an overall communication score.

- A same-day attempt records practice completion.
- Success on a later day supplies retention evidence.
- Success with a suitable new prompt supplies transfer evidence.
- Mastery requires both later retention and transfer.

No exact mastery threshold is defined in this item because the current metrics
remain blocked from progress by the reliability policy. Later work must validate
metric-specific change rules before they unlock a skill.

Game rewards should recognise practice, returning later, reflection, harder
contexts and demonstrated transfer. They must not reward endlessly increasing
loudness, pitch or speed, eliminating every pause or filler, or moving toward a
preferred accent. Points and streaks remain separate from skill mastery.

## Machine-readable contract

`manifest-v1.1.0.json` stores:

- protocol, task, prompt and content versions;
- supported language and explicit no-age-gate policy;
- task purpose, construct, expected text, timing and preparation;
- recording quality policy, repetitions, retries and stop conditions;
- enabled measurements and their release limits;
- accommodations and task-specific comparability limits;
- separate consent requirements;
- optional research and future-locked tasks;
- the cautious handoff from assessment to later progression.

`python3 -m assessment.validate` checks that unknown measurements, diagnostic or
ranking use, unvalidated progress, research tasks in the core session, missing
consent, unlocked future tasks, unsupported languages, incorrect content counts
unsafe repeat pairings and unsafe total duration cannot enter the protocol
silently.

The manifest schedules tasks only. It does not record audio, run the existing
pipeline, store a user, render screens, choose a lesson, or claim that the
assessment is scientifically validated.
