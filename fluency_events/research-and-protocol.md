# Timestamped speech event candidate research and protocol

Version: 1.0.0  
Status: engineering active, scientific release locked  
Updated: 2026-07-20

## Decision

The pipeline may surface separate, timestamped **candidates** for observable
sound or syllable repetition, whole word repetition and prolonged sound. It
also preserves phrase repetition as a separate context event. It does not call
any automatic result a confirmed stuttering event.

Possible blocks remain unavailable to automation in this version. A silent
interval does not reveal whether a speaker was unable to initiate an intended
sound, was thinking, breathing, yielding a turn, or was affected by an audio
dropout. A trained reviewer or speaker may add a timestamped possible-block
observation, but one review is not reference truth and cannot create a
diagnosis.

The module is a local deterministic post-processing stage. It uses the
existing AssemblyAI verbatim transcript, final speaker attribution and
WhisperX character timing. It adds no API or generative model. Candidate data
is stored in `fluency_events.json` and is intentionally excluded from the
listener, the interpretation, the claim ledger, history and progress.

No output means that a candidate met the rules in this contract. It does not
mean that the person stutters, that the event was involuntary, that the speech
was or was not fluent, or that an event has a cause. Candidate absence does
not establish fluent speech.

## Why this is separate from the old repetition and drag measurements

The existing `repetition_count` finds adjacent repeated tokens or a repeated
two-token sequence. It was designed as a broad language observation. It
cannot tell a single-syllable repetition from a multiple-syllable repetition,
intentional emphasis, turn management, self-repair or an ASR duplication.

The existing renderer `drag_count` finds a whole word that is unusually long
relative to the speaker's character timing baseline. It is useful for
expressive spelling. It does not localise a sound and cannot distinguish an
ordinary emphasis, expressive lengthening, speech technique, accent pattern,
word-boundary error or stuttering-like prolongation.

Item 21 does not rename or reinterpret those protected measurements. It adds a
separate evidence path with event-specific timestamps, source evidence,
alternative explanations, an uncertainty state and a manual review record.

## Observable event definitions

ASHA describes overt stuttering characteristics as monosyllabic whole-word
repetitions, sound or syllable repetitions, prolongations where emphasis is
not the goal, and blocks. ASHA also makes clear that a comprehensive
assessment is wider than an event count: it considers multiple tasks and
situations, background, covert features, reactions, impact and differential
diagnosis. This backend implements only guarded observations, not that
assessment.

- [ASHA Stuttering, Cluttering, and Fluency Practice Portal](https://www.asha.org/practice-portal/clinical-topics/fluency-disorders/)
- [ASHA assessment in the WHO ICF framework](https://www.asha.org/practice-portal/clinical-topics/fluency-disorders/assessment-of-fluency-disorders-in-the-context-of-the-who-icf-framework/)

FluencyBank separates part-word repetition, single-syllable whole-word
repetition and disrhythmic phonation from multiple-syllable word repetition,
phrase repetition, interjection and revision. Its IISRP documentation says
blocks and prolongations are among the hardest categories to identify
reliably, even with two experienced listeners. The CHAT transcription manual
also keeps repeated segments, prolongations, broken words, blocks, phrase
repetitions, revisions and pauses as different codes.

- [FluencyBank IISRP coding definitions](https://talkbank.org/fluency/access/Password/IISRP.html)
- [TalkBank CHAT disfluency transcription manual](https://talkbank.org/0info/manuals/CHAT.html#Disfluency_Transcription)
- [FluencyBank resource paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC5986295/)

The automatic type `whole_word_repetition_unclassified` is deliberate. The
backend does not use an English pronunciation dictionary or spelling
heuristic to decide syllable count, because dictionary coverage and
pronunciation differ across words, names and English varieties. A trained
audio reviewer can relabel the observation as
`single_syllable_whole_word_repetition`; until then, it remains unclassified.

## Evidence from automatic detection research

SEP-28k provides useful research labels for blocks, prolongations, sound
repetitions, word or phrase repetitions and interjections. It also shows why
this item cannot simply install a classifier and call the output truth:

- its unit is a three-second clip, not an exact event boundary;
- a clip can contain several labels;
- the clips were sampled near pauses, so the label prevalence is not the
  prevalence in ordinary continuous speech;
- the audio is largely podcasts involving people who stutter and is not a
  representative product population;
- three trained non-clinician annotators produced Fleiss kappa of 0.62 for
  word repetition, 0.40 for sound repetition, 0.25 for blocks and only 0.11
  for prolongations;
- the authors explicitly state that blocks are difficult to assess from audio
  alone and block-label results should be speculative;
- the paper notes that ordinary language models may remove repeated
  single-syllable words and that repetitions can also be emphasis.

Those results justify retaining class-specific uncertainty, a natural-pause
alternative, human review and a fully unavailable automatic block detector.

- [Apple SEP-28k research page](https://machinelearning.apple.com/research/stuttering-event-detection)
- [SEP-28k paper](https://arxiv.org/abs/2102.12394)
- [Apple SEP-28k dataset repository](https://github.com/apple/ml-stuttering-events-dataset)

KSoF adds therapy-modified speech and German clinical-session audio. This is a
valuable warning that deliberate fluency techniques can resemble target event
classes and that a model trained on untreated podcast speech may not transfer
to therapy contexts. KSoF is not used as a hidden validation substitute.

- [KSoF dataset paper](https://aclanthology.org/2022.lrec-1.189/)

The review of event-based and interval-based stuttering measurement reports
that method and reliability must be stated rather than assuming that a human
count is an error-free criterion. The validation programme therefore retains
individual annotations and disagreements before adjudication.

- [Valente et al., event and interval measurement review](https://pubmed.ncbi.nlm.nih.gov/24919948/)

## Provider decision

AssemblyAI Universal 3.5 Pro remains the transcript source. The existing
request already enables `disfluencies=True`, speaker labels and word
timestamps. No second transcription request is added.

The current Universal 3.5 Pro documentation says its `prompt` is contextual:
it should describe the audio, while behavioural and formatting instructions
are ignored. Therefore this item does not add an instruction such as “write
every stutter.” Such a prompt would not be a validated detector and could
change the transcript without reference evidence. The exact provider model
used remains recorded in run provenance.

- [AssemblyAI transcript request reference](https://www.assemblyai.com/docs/api-reference/transcripts/submit)
- [AssemblyAI Universal 3.5 Pro prompting](https://www.assemblyai.com/docs/pre-recorded-audio/universal-3-5-pro/prompting)

WhisperX remains a forced-alignment source. Its character label is an aligned
grapheme, not a phonetic transcription. A long aligned character can therefore
surface a `prolonged_sound` candidate, but the evidence explicitly says that
the aligned character is not a confirmed phone.

## Automatic candidate rules

### Whole word repetition

Consecutive normalised transcript tokens from the same final speaker are
grouped into one event when:

- every word has ASR confidence of at least 0.50;
- the gap between consecutive words is at most 1.0 second; and
- every word has a positive timestamp interval.

The timestamp spans all repeated tokens. The artifact retains the original
tokens, word indices, provider confidences, speaker-attribution confidences and
number of excess repetition units. The type remains unclassified until audio
review confirms syllable status and rules out emphasis, repair and ASR error.

### Sound or syllable repetition

Two conservative orthographic patterns can surface a candidate:

- a provider token contains a repeated short prefix before a target word, for
  example `b-b-but`; or
- one or more adjacent short tokens are a prefix of the following longer
  token.

The second pattern receives greater uncertainty because separate tokens may
be word recognition or segmentation errors. Orthography is not phonetic
truth. False start, phonological fragment, intentional sound play and
language or dialect variation remain explicit alternatives.

### Prolonged sound

Eligible alphabetic alignment characters are assigned to the attributed word
with the largest temporal overlap. A candidate requires all of the following:

- at least 20 eligible character intervals for that speaker in the recording;
- aligned character duration of at least 0.25 seconds;
- duration at least four times the speaker's median aligned-character
  duration;
- robust z value of at least 6 using median absolute deviation; and
- alignment score of at least 0.50 when the provider supplies a score.

An elongated provider spelling may also surface a high-uncertainty candidate,
but it is kept distinct in its source evidence.

These thresholds are engineering candidate gates, not clinical cutoffs. They
are deliberately strict to reduce review burden, and they require held-out
event-level validation before any release. Ordinary emphasis, accent or
dialect, speech technique, quotation, singing, ASR timing and forced-alignment
error all remain alternatives.

### Possible block

Automatic detection is disabled. Long silence, a pause before a word, a breath
or an ASR boundary cannot establish a block. A human review packet may add a
timestamped `possible_block` observation based on audio or audiovisual review
and speaker context. The observer role and uncertainty are retained.

## Manual confirmation

Every candidate starts `unreviewed`. The backend accepts a structured review
packet with an opaque reviewer identifier, allowed role, review time,
blinding status and one of these decisions:

- `confirmed_observable_event`;
- `rejected`;
- `relabeled`;
- `uncertain`.

A reviewer can adjust a boundary or add an event that automation cannot
surface. The review record does not overwrite the source candidate. Conflicting
reviews resolve to `uncertain` until adjudication.

The allowed roles are speaker self-report, trained fluency annotator,
speech-language pathologist and research adjudicator. These roles represent
different evidence. A speaker can report their lived experience, but self
report alone is not an independent acoustic reference. One trained reviewer
also remains `not_reference_truth`.

Reference truth for scientific validation requires at least two independent
reviewers trained on a written guide, blind to automatic output, with raw
disagreements retained and a documented adjudication. Diagnosis, severity and
stuttering-score fields are rejected by the review code.

This item supplies the backend review contract and command-line application.
It does not build a user interface, reviewer workforce, clinician service or
database.

## Task, language and fairness limits

Candidate collection is allowed for fixed reading, listen and repeat,
spontaneous speech, conversation and unknown ad hoc speech. Unknown ad hoc
speech remains noncomparable. Sustained-vowel and repeated-phrase research
tasks are excluded. A repeated-phrase task needs a future prompt-aware
protocol so its expected production is not mislabeled as an event.

Transcript-pattern automation is English scope only. It is not claimed to
work for other languages. Even within English, ASR behavior, syllables,
legitimate repetitions, discourse markers and sound patterns vary by accent,
dialect, community and task. No candidate rate, threshold or group norm is
released.

Quality warnings for noise, clipping, reverberation, low signal, overlap,
speaker attribution and contamination are propagated to event uncertainty.
Rejected audio abstains. Low-confidence transcript patterns are suppressed.
Missing candidates never become zeros or evidence of fluent speech.

## Validation programme

Generated timing fixtures prove only deterministic software behavior. Adam's
two recordings prove only that the stage runs in the real pipeline, preserves
timestamps and safeguards, and produces a reviewable artifact. They cannot
prove accuracy, fairness, clinical meaning or generalisation.

Scientific evaluation requires consented, representative continuous speech
with exact event boundaries from the review protocol above. Development and
evaluation participants must be separate. Splits must also prevent the same
podcast, session or source from leaking across training and evaluation.

Report, separately for every event type:

- event precision, recall and F1 under a predeclared temporal matching rule;
- false positive events per speaking minute;
- onset and offset error distributions;
- unavailable and abstention rates;
- inter-reviewer agreement before adjudication;
- performance by task, language and English variety, accent and dialect, age
  band, voice range, device, audio condition and speech difference.

Clip-level agreement on SEP-28k does not satisfy exact timestamp validation.
Agreement between AssemblyAI and WhisperX is not reference truth. A combined
“any event” metric cannot hide weak event classes.

Release remains locked until the intended use and acceptable error costs are
defined with qualified professional and lived-experience input, held-out
results meet predeclared criteria, privacy and consent are approved, and Adam
explicitly approves a later item.

## Failure behavior and prohibited interpretations

- A repeated transcript token may be rhetoric, emphasis, repair or ASR error.
- A repeated fragment may be a false start or segmentation error.
- A long aligned character may be emphasis, technique, accent or alignment
  error.
- A silence may be an ordinary pause and never becomes an automatic block.
- Audio cannot reveal covert avoidance, anticipation, intent, distress,
  impact or diagnosis.
- Event frequency does not by itself measure lived impact or severity.
- Fewer candidates are not automatically better communication.
- No event is sent into the interpretation or personal progress in this item.
- No combined count, percentage, severity score, screening result, diagnosis,
  ranking or high-stakes decision is produced.
