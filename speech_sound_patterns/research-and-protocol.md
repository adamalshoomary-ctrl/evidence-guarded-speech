# Speech sound production and pattern research protocol

Version: 1.5.0
Status: final engineering acceptance complete on the sealed no-selection path,
scientific release locked

> **2026-08-22.** The project is now open research with no monetisation plan,
> permanently. Every exclusion below that rests on commercial rights alone is
> historical, including L2 ARCTIC and TalkBank. Exclusions on methodological
> grounds, on access grounds, or on cost stand unchanged. The checkpoint 22E8
> variety probe numbers referenced here are superseded pending the defect repair
> recorded in `audit-2026-08-22.md`.
Owner approval: engineering lane approved on 2026-07-20; sealed final
no-evaluation resolution approved on 2026-08-12

## Decision

No articulation detector, phonological pattern detector, provider, task, score
or coaching output is active. Developer-only offline candidate engineering may
proceed checkpoint by checkpoint, but scientific and product use remain locked.

The central safety rule is simple: a transcript difference is not a speech
sound difference. A speech sound difference is not automatically an error. A
repeated difference is not automatically a disorder. Each step needs its own
evidence.

The existing controlled pronunciation protocol remains the task foundation.
Its word pack is empty and professionally unreviewed, so this protocol cannot
activate a task or produce a pipeline artifact. The two owner recordings can
support future integration checks only. They cannot establish accuracy,
reliability, fairness, meaningful patterns or population performance.

## What the constructs mean

This protocol keeps four things separate.

### Speech sound production observation

This is a timestamped human record of what sound appears to have been produced
in one known opportunity. It describes the audio. It does not say that the
production was wrong, explain why it occurred or diagnose anything.

The research units are consonants, vowels, diphthongs, consonant clusters and
syllable shapes. Position and surrounding sounds matter because the same sound
can be produced differently across word positions and phonetic contexts.

### Target relation observation

This compares the retained production record with every professionally
accepted form of the intended word. Possible research outcomes are accepted
variant, observed substitution, deletion, insertion, distortion, uncertain or
unscorable.

The word "observed" is important. These are descriptive comparison records,
not diagnoses or explanations. An unresolved legitimate form is unscorable.
It never becomes an error by default.

### Phonological pattern hypothesis

A pattern is a repeated relationship across multiple eligible opportunities,
words and sound contexts. ASHA describes phonological patterns as systematic
changes affecting classes of sounds, combinations or syllable structures.
One word, one transcript disagreement or repeated copies of one recording
cannot establish a pattern.

No active pattern registry or numeric minimum is defined in version 1. Those
need qualified professional design and development data. A future pattern
record must show all support and opportunity counts, distinct words, contexts,
tasks and sessions. Even a well-supported descriptive pattern does not establish
a disorder, severity, cause or treatment need.

### ASR disagreement

ASR turns audio into words. It is designed to recover likely text, not to
provide a faithful phonetic transcription. It may normalize a production to the
expected word, produce a different word, insert or delete material, or behave
differently across speech varieties and speaker groups.

An ASR disagreement may send an interval for manual review. It cannot create a
speech sound concern. Confidence is not the probability that a phone was
produced, and agreement between automatic systems is not truth.

Koenecke and colleagues found substantial word error rate disparities across
five commercial ASR systems in their study. Tatman also found accuracy
differences across dialect and gender groups. These studies do not predict the
performance of the current provider on this product, but they demonstrate why
locally stratified validation is required rather than assuming a transcript
error belongs to the speaker.

[Koenecke et al., 2020](https://doi.org/10.1073/pnas.1915768117),
[Tatman, 2017](https://aclanthology.org/W17-1606/)

## Language, accent and dialect boundary

Everyone has an accent. Accent and dialect forms are natural language
differences, not communication disorders. Intelligibility, comprehensibility
and accentedness are also different constructs. Listener bias can affect the
latter two and must not be turned into a speaker impairment.

The accepted reference for one word must be a versioned union of professionally
reviewed forms across the supported English varieties. It is not the closest
American, British, Australian or other prestige form. A self-reported variety
provides useful context but does not select a single canonical pronunciation or
prove that every production belongs to that variety.

When the review team lacks relevant language or variety knowledge, it must use
a suitably qualified reviewer or linguistic broker. If a legitimate form is
not represented or remains disputed, the opportunity is unscorable.

This follows ASHA guidance that speech sound assessment must consider the
phonemic, allophonic and rule systems of the person's languages and dialects,
and that comparison with one mainstream English variety cannot determine a
disorder. Speech Pathology Australia's current position also requires
culturally safe and responsive research and practice rather than treating one
professional or cultural perspective as universal.

[ASHA speech sound guidance](https://www.asha.org/practice-portal/clinical-topics/articulation-and-phonology/),
[ASHA accent guidance](https://www.asha.org/practice-portal/professional-issues/accent-modification/),
[Speech Pathology Australia position statement](https://www.speechpathologyaustralia.org.au/Common/Uploaded%20files/Smart%20Suite/Smart%20Library/e0f18c12-a0d6-4a44-a9c3-2bbd9436e37f/2025_Culturally-responsive-speech-pathology-practice.pdf)

### A variety mismatch may be excluded, never subtracted

A recurring and reasonable proposal is to run speakers of one variety through a
scorer built for another, then correct the result using knowledge of the
speaker's variety. An Australian saying `can't` as /kaːnt/ is flagged by a
General American scorer expecting /kænt/; because we know the speaker is
Australian, we know the production was correct, so it seems we could simply
subtract that difference and trust what remains.

The principle behind this is right and is already required above: the accepted
reference is a union of professionally reviewed forms, not one prestige form.
The correction is what fails, for four reasons.

1. **Coverage.** Almost all variety difference lives in vowels. Excluding every
   sound where the varieties differ leaves little beyond consonants, so the
   correction does not recover the evidence it appears to promise.
2. **Locality, and the evidence against it.** The expectation was that a
   scorer, judging acoustic context spanning neighbouring sounds, would let an
   unfamiliar vowel depress confidence in adjacent consonants, so the mismatch
   could not be cleanly excised. A single speaker demonstration on 2026-07-25
   did not support that at sentence scale. Natural Australian speech scored on
   a General American model produced ten phones below 80, nine of them on
   divergence points written down before the scores were read, and none of
   them on the dialect stable control sentence. The affected set was
   enumerable: the r coloured vowel, the BATH vowel, dark l and final t.
   Locality is therefore recorded as **unsupported at this sample size** rather
   than as an established reason. It is one speaker, one session and 27 control
   phones with no expert labels, so it cannot settle the question either way.
   Reasons one, three and four do not depend on it and remain binding.
3. **Magnitude.** Subtracting an effect requires knowing its size. Estimating
   it requires expertly labelled speech in the speaker's own variety. Where
   that evidence does not exist, any correction is an invented constant wearing
   the appearance of a measurement.
4. **Direction.** A variety effect is systematic, not random. It moves every
   speaker of that variety the same way, so more data does not average it out.
   A repeatable system would therefore report the same unfounded concern about
   the same population every time, and its repeatability would make the error
   look like evidence.

Point four is the decisive one. It is the precise mechanism by which a
measurement system tells a whole community that its ordinary speech is
disordered, which this protocol exists to prevent.

The permitted handling is exclusion, not correction. Where the supported
varieties legitimately differ, the opportunity is `unscorable` and is reported
as such, consistent with the rule above. Where they agree, a cross variety
scorer may raise a candidate for human review but never a finding. Recording an
opportunity as unscorable is honest. Adjusting it by an unmeasured constant is
not.

The 2026-07-25 demonstration appeared to make exclusion look more workable than
first argued, because the affected phones formed a short predictable list. That
reading was too confident and is corrected here. With one speaker and no
induced errors, "these phones are dialect stable" and "this speaker articulates
these phones well" predict identical data, and no base rate exists for how
often an ordinary speaker falls below any threshold on a commercial scorer. The
clean control sentence is therefore consistent with the exclusion argument but
does not evidence it.

Exclusion is not validated, and a literature review on 2026-07-25 found
specific reasons for caution.

- **Exclusion is an established clinical method, not a novel one.** Contrastive
  analysis is the named technique, and the Percentage of Consonants Correct
  scoring rules state directly that dialectal variations are not scored as
  errors. The Diagnostic Evaluation of Language Variation was built on
  noncontrastive items for the same reason. The principle is sound and
  long standing.
- **The one quantified trial of the manoeuvre traded one error for a worse
  one.** Hendricks and Adlof, LSHSS 2017, applied dialect modified scoring for
  African American English speakers: false positives fell from 52 to 36
  percent, but false negatives rose from 12 to 36 percent and the negative
  likelihood ratio worsened from .25 to .57. They warned that universal
  application risks dangerous under identification. That study is about
  language rather than articulation, so it does not transfer directly, but the
  failure mode it names is the one this project would inherit, and it is the
  more harmful direction. A missed difficulty is invisible; a false concern is
  at least arguable.
- **The nearest published software analogue did not work.** A June 2026
  evaluation of phone recognisers introduced an error metric tolerating
  linguistically similar phone substitutions, which is structurally the same
  move as excluding known divergences, and still found persistent demographic
  disparities after accounting for acceptable phonemic variation.
- **Speech technology does not solve this by exclusion.** The established
  engineering response to variety mismatch is to change the reference, through
  accent specific pronunciation lexicons and accent aware models, keeping every
  opportunity in the scored set. No published work excludes opportunities from
  an automatic score. This matters for provider choice: a provider that accepts
  no custom lexicon forecloses the method the field actually uses.

The remaining obstacle is unchanged and decisive. No automatic method can tell
an ordinary Australian feature from a genuine production difficulty at any
single opportunity: a weak final t is equally consistent with Australian t
glottalling and with a real difficulty, and nothing short of expert human
labelling of Australian speech separates them. Until that evidence exists, an
excluded opportunity is reported as unscorable and never as evidence of correct
production.

No list of dialect stable versus dialect sensitive English segments exists in
ASHA or Speech Pathology Australia guidance, so any such list this project uses
is its own construction and must be labelled as such. Broad class claims do not
survive scrutiny: fricatives are not a safe class, because the dental
fricatives are subject to fronting in Australian and British English and to
stopping in other varieties.

Two further observations from that demonstration bind later work. The utterance
level score sat between 95 and 99 for the same clips whose phone level flagged
Australian features, so an overall score conceals a variety effect that the
phone level records; work that reads only a headline score will not see this.
And a score only locale, which returns a low number without naming the phone,
cannot be audited for this problem at all, because what the scorer believed was
said cannot be recovered.

## Tasks and lexical intent

The future primary research task is the locked controlled word task in
`assessment/pronunciation-research-v1.0.0.json`. A versioned presented stimulus
provides lexical intent. Its written and recorded prompt modes remain different
because reading, familiarity, hearing, memory and imitation change task
meaning.

Single words provide identifiable opportunities in planned phonetic contexts.
They do not prove what happens in connected speech. Sentence or connected
speech samples are therefore secondary transfer evidence and need their own
task definition and independent intended-word confirmation.

Spontaneous speech is context only in version 1. The person's intended word can
be unknown, reduced forms and self-repairs are common, and ASR cannot fill that
gap. No target relation or pattern may be inferred from the current ad hoc solo
or conversation recordings.

Task modes are not pooled. Repeated productions are required, but this protocol
does not invent a repetition count or a minimum pattern threshold before
professional design and development evidence exist.

## Two-pass human reference

Human transcription is essential but imperfect. Mallaband's 2024 study of 12
paediatric speech and language therapists reported an average agreement of
56.3% on one disordered speech sample, with lower agreement for vowels than
consonants. That result comes from a small, specific study and is not a universal
reliability estimate. It does show why one transcription cannot silently become
truth.

The future reference process therefore has two passes:

1. At least two qualified reviewers independently transcribe the audible
   production without seeing the expected word, accepted variants or automatic
   outputs.
2. Reviewers then see the intended word and full accepted variant set and
   separately record the target relation.

The original records and every disagreement remain stored. A documented
adjudication may add a reference result without overwriting either reviewer.
Reviewer training and competence for the relevant language varieties are
recorded.

Broad IPA is the default research representation because greater transcription
detail can reduce agreement. Narrow IPA or ExtIPA may be necessary for some
questions, but it needs a separate fit-for-purpose protocol, training and
reliability study. The official IPA remains the symbol authority.

Blind listener transcription remains separate. It answers which word a
listener understood, not which phones were produced.

[Mallaband, 2024](https://doi.org/10.1111/1460-6984.13043),
[RCSLT-endorsed transcription guidance](https://www.rcslt.org/wp-content/uploads/media/docs/clinical-guidance/bsltru-good-practice-guidelines-transcription.pdf),
[International Phonetic Association](https://www.internationalphoneticassociation.org/content/ipa-chart)

## Automatic candidate research

No candidate system is selected. The future comparison may include the current
ASR as a word baseline and an inspectable alignment or phone-recognition
baseline. Candidate provider outputs from the pronunciation protocol may also
be retained for research.

Every candidate receives the same frozen recording. Raw outputs, configurations
and versions are retained. Reference reviewers remain blind to them.

Expected-text forced alignment may help locate an interval, but fitting the
expected sequence to audio does not verify that sequence. A phone recognizer is
also a candidate system rather than a phonetic reference. A provider's
pronunciation score remains its model output, not this product's measurement.
Microsoft's current documentation explicitly states that its pronunciation
assessment depends on speech-to-text accuracy, submitted reference text, audio
conditions, local thresholds and evaluation in the intended scenario.

The broader automatic pronunciation literature also reports scarce and
imbalanced data, multiple competing constructs and a lack of consensus labels
and evaluation. This protocol does not import a language-learning system's
native-likeness objective into communication coaching.

[Microsoft characteristics and limitations](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/pronunciation-assessment/characteristics-and-limitations-pronunciation-assessment),
[El Kheir et al., 2023](https://aclanthology.org/2023.findings-emnlp.557/)

## Primitive evidence and failure behavior

Every future trial retains the participant, session, attempt, stimulus, task,
timestamps, audio quality, intended-word source, blind listener records, blind
production records, variant version, relation reviews, raw automatic outputs,
review state and provenance.

Expected and scorable word and sound opportunities remain separate. Insertions
are separate observations. A pattern must expose its support and eligible
opportunity counts. Missing evidence never becomes zero.

Poor audio, unsupported language or variety, unknown intended word, missing
variant review, insufficient opportunities, unresolved human disagreement and
missing provider versions produce `unavailable`. ASR or alignment conflict
requires manual review or becomes unavailable. There is no default accent,
zero, LLM judgment or guessed phone fallback.

Two further conditions produce `unavailable` for the affected system alone, both
established at checkpoint 22E4B when a larger sample exposed them. First, a
recording longer than a system's own declared input length is not scored by that
system. Truncating it to fit would drop real speech and turn every target in the
dropped region into an invented deletion concern, which is worse than having no
evidence, so the recording is recorded as unprocessable with its reason and every
target in it abstains for that system while every other system still sees it.
Second, a system that returns different output for a byte identical repeated
request has not demonstrated a result for that recording, so its targets abstain
rather than entering a metric. Both conditions must be visible in the reported
coverage and abstention counts rather than silently reducing a denominator, and
neither may be applied selectively after seeing how a system scored.

Research collection, human review and raw audio retention require separate
consent. Fairness metadata has its own consent purpose. Declining research must
not reduce ordinary coaching access.

## Independent validation

Development, threshold tuning and held-out evaluation participants remain
separate. Thresholds are frozen before held-out evaluation. Sample sizes for
participants, listeners and reviewers are justified before collection.

Required reporting includes:

- phone-relation precision, recall and F1 by outcome;
- false concerns on accepted language, accent and dialect variants;
- an ASR attribution matrix separating ASR-only errors from human-confirmed
  production differences;
- false concerns per scorable opportunity;
- abstention, unscorable rate and coverage;
- calibration if any confidence is retained;
- exact same-input repeatability;
- repeated human-production reliability;
- human inter- and intra-reviewer agreement;
- pattern-level results only after professional approval of a pattern registry;
  and
- uncertainty by language variety, first-language background, multilingual
  status, task, phonetic context, voice range, device, audio quality, speech
  difference and consented target-population strata.

No release thresholds are set in version 1. They must be chosen on development
and tuning data, then evaluated once on held-out participants. API agreement and
the owner recordings cannot establish reference truth.

## Release and scope

Automatic candidate collection in the normal pipeline, coaching, personal
progress, ranking, screening, diagnosis, severity and treatment remain blocked.
The private offline assembler and safe aggregate research reports are developer
evidence only. There is no active task, selected system, emitted relation,
normal-pipeline speech-sound artifact or product output.

Motor speech and voice screening belong to item 23. Personalised recognition
belongs to item 24. Oral mechanism examination, hearing assessment, clinical
differential diagnosis, cause and treatment are outside this protocol.

Under the active version 1.7 machine-readable contract, a developer-only
engineering lane is permitted when its source, licence, task and artifact gates
are satisfied. Scientific and product release remain blocked until qualified
speech pathology and phonetic review, an active professionally reviewed task
and variant pack, a written annotation guide, representative independent
evidence, predeclared validation gates, privacy and provider review, and a new
owner approval exist. Any later product release requires another separate
approval.

## Later engineering planning decision

Further research on 2026-07-20 found a safe way to separate engineering from
release. Adam approved the guarded plan, and checkpoints 22A through 22G were
completed in order. On 2026-08-12 Adam approved the conservative final path:
because no method qualified, held-out evidence would remain sealed and every
held-out result would be reported as unavailable.

Existing public expert-labelled corpora may support a developer-only candidate
extractor without hiring new participants or reviewers. Version 1.2 therefore
permits offline automatic candidate engineering while keeping professional
review, representative independent evidence and a separate owner decision
mandatory for scientific or product release. Versions 1.0 through 1.2 remain
unchanged historical contracts.

Version 1.3 records the completed local feasibility checkpoint without
activating that extractor. Exact isolated environments ran MFA, PhoneticXEUS
and PanPhon on a fixed development-only sample. Their raw outputs remain
private; `local-feasibility-v1.0.0.json` contains only aggregate runtime,
resource, repeatability and mapping evidence. This checkpoint did not evaluate
accuracy, inspect held-out labels, select a candidate system or relax a release
gate. PhoneticXEUS commercial use remains blocked pending complete model and
training-data provenance review.

Version 1.4 records the completed development and tuning benchmark without
activating an extractor. A frozen 565-clip sample kept SpeechOcean expert phone
relations, Acted Clear human-corrected timing, Common Phone automatic
alignments and Australian Common Voice sentence robustness as separate evidence
classes. All five SpeechOcean reviewer records and their disagreements were
retained. Development and tuning participants, adults and children, and every
metric denominator were reported separately. No held-out participant or label
was accessed.

The current greedy PhoneticXEUS relation path produced high recall but far too
many false concerns and very low exact supporting relation agreement. It is not
eligible for selection in its present form. MFA supplied timing evidence only,
and Common Phone and Common Voice supplied system-disagreement evidence only.
No candidate system or threshold was selected. The benchmark did not run a paid
provider, create a prompt pack or candidate artifact, or support scientific or
product release.

Version 1.5 binds version 1.4 as an unchanged historical baseline and records
the completed conservative repair. The candidate runners received an
expected-only manifest with no expert outcomes. Constrained PhoneticXEUS
numeric and contextual calibration, a repeated-relation filter, and a
separately screened full-precision Meta wav2vec2 phoneme model were evaluated
without weakening the frozen gates. The strongest Meta exact operating point
passed all tuning gates and four of five development gates. Development recall
was 0.183824 against the predeclared 0.200 minimum. None of 2,957 distinct
score boundaries passed every gate on both partitions. The held-out set stayed
sealed, no paid provider was run, and no system, threshold, extractor or
artifact was selected.

The dataset decision was refined on 2026-07-21 after a licence and annotation
audit. SpeechOcean762 is the primary public expert phone-relation benchmark.
Acted Clear Speech supplies a tiny hand-corrected phone-boundary fixture. Common
Phone supplies broad automatic phone and timing engineering evidence. Common
Voice Australian English supplies Australian accent, microphone, abstention
and false-concern stress evidence. Small LibriSpeech subsets may support scale
and determinism checks. These truth classes remain separate and source lineage
or candidate-model training overlap prevents a result from being described as
independent evidence. The real identifier audit found 264 speakers and 521
clips shared by Common Phone and the current Australian Common Voice package;
all 264 speakers are excluded from the Common Phone project splits.

The plan proposes Montreal Forced Aligner, PhoneticXEUS and PanPhon as the local
candidate stack. Azure, SpeechAce and SpeechSuper may be compared as optional
raw systems but cannot become truth through agreement. A corpus is uploaded to
a provider only when both the corpus terms and provider terms permit it.

Macquarie Dictionary Australian English Pronunciation Data remains unlicensed.
Adam declined acquisition enquiries on 2026-07-28, so reopening that path needs
a new owner decision. It may materially strengthen the Australian word-variant
reference if its sample, price and licence are suitable. TIMIT is rejected for
current engineering: the Academic Torrents copy supplies no reuse licence and
the official commercial route adds too little value for its cost. L2-ARCTIC and
selected TalkBank resources remain blocked unless their exact commercial rights
are obtained. No GPU rental is approved.

The implementation order, account requests, licence decisions, evidence roles,
lineage rules and acceptance gates are in
`speech_sound_patterns/engineering-plan.md`. The manifest, feasibility and
benchmark implementations do not activate a task, provider, extractor or
artifact and do not change any release block above.

The active machine-readable contract after checkpoint 22H is
`speech_sound_patterns/research-contract-v1.7.0.json`. The unchanged
`speech_sound_patterns/research-contract-v1.0.0.json` records the earlier
research-design-only boundary, and version 1.1 records the approved engineering
lane before source acquisition. Version 1.2 makes the validated source registry
authoritative without weakening scientific or product release gates. Version
1.3 adds only the release-locked local feasibility evidence. Version 1.4 adds
the release-locked development and tuning benchmark and makes version 1.3 an
unchanged historical checkpoint. Version 1.5 binds version 1.4 unchanged and
adds the release-locked repair and no-selection decision. Version 1.6 binds
version 1.5 byte-for-byte unchanged and adds only the private, release-locked
candidate evidence assembler. Its adequacy audit failed before any rule search,
so no system, mapping, feature relation, threshold, provider configuration or
repeated minimum exists. Version 1.7 binds version 1.6 unchanged and records the
final sealed no-evaluation outcome. All 26 held-out adults and 24 held-out
children remained sealed because no eligible method existed. Its 40
predeclared held-out measures are unavailable, not zero, a pass or a failure.
The final report also proves that the ordinary conversation pipeline remains
unchanged and contains no speech-sound output. Historical versions remain
loadable records; the active validator is intentionally version specific.
Validate the active contract, corpus registry, aggregate benchmark, candidate
evidence and immutable final repository closure with:

```text
python3 -m speech_sound_patterns.validate
python3 -m speech_sound_patterns.validate_corpora
python3 -m speech_sound_patterns.validate_benchmark
python3 -m speech_sound_patterns.validate_candidates
python3 \
  -m speech_sound_patterns.validate_final_acceptance
```

The last command fails unless `repository-closure-v1.0.0.json` binds the full
post-report public repository. Engineering closure does not establish detector
accuracy, Australian English correctness, population performance, fairness,
clinical validity or product benefit. Every scientific and product release gate
remains locked.
