# An honest account

What was built, what was measured, what was found, and what could not be
established at all.

This is the written record of an open research project on evidence guarded
speech measurement. It is not a paper and it is not a submission. It is the
document a reader should start from if they want to know what this repository
actually demonstrates, which is considerably less than the amount of machinery
in it might suggest.

The project has no product, no users and no monetisation plan. It makes no
screening or clinical claim, and no part of its roadmap leads to one. Its
audience is researchers and engineers working on pronunciation assessment,
measurement fairness and reproducibility in speech technology.

Software and evidence: <https://github.com/adamalshoomary-ctrl/evidence-guarded-speech>,
GPL 3.0 or later, DOI [10.5281/zenodo.22106996](https://doi.org/10.5281/zenodo.22106996).

---

## 1. The short version

**What exists.** A Python speech measurement engine that turns one recording
into a measurement record in which every number carries its provenance, its
uncertainty and the conditions that produced it, and in which a measurement
that cannot be supported is declared unavailable rather than returned as a
zero. Beside it sit versioned research contracts, licence audited corpus
manifests, a pre registered dialect comparison experiment with its full
evidence, and the record of a system selection that selected nothing.

**The one claim this project makes about its own novelty**, narrowed after a
prior art check that cost it a better sounding claim:

> No open, reusable harness combines provenance on inputs, per measurement
> uncertainty, explicit abstention, and verification of generated claims, for
> speech measurement.

That is a claim about integration and licence. It is not a claim about
invention. Every individual component has substantial prior art and section 7
names it.

**The main empirical result is a null.** A comparison of 2,400 clips from 1,200
speakers, asking whether a pronunciation scorer built on an American English
reference flags Australian speakers more often than American speakers, found
nothing at group level. **All five hypotheses pre registered before the run were
group level, and none of them survives.** A further 43 per consonant tests were
declared before any p value was computed but after the run, and of those exactly
one survives multiple comparison correction. It is not about Australian
speakers.

**The strongest material here is the self correction.** Three times this
project checked its own work and lost something it wanted to keep. The largest
positive finding it ever produced was retracted after its own method was turned
on itself. Its published figures have been wrong five separate times. Its most
attractive novelty claim did not survive contact with the literature. Section 2
is that record, and it leads because it is the part most projects omit.

**What could not be established is a result in itself.** No expert produced
phone level annotation of any first language Australian English variety exists,
at any licence and at any price. Rhoticity, the sharpest consonantal difference
between Australian and American English, turns out to be unmeasurable by this
entire class of system. Both are reported in section 6 as findings rather than
as excuses.

---

## 2. Three times this project was wrong

### 2.1 The headline finding was retracted

Until 2026-08-23 this project's central positive result was that a
pronunciation scorer using an American English reference flags Australian
speakers on the rhotic about three percentage points more often than it flags
American speakers. That was the finding that made the whole exercise look
worthwhile.

It does not exist.

The Australian minus American differential on the rhotic under the American
reference is **−0.0004**, against a previously published **+0.0300**.

The cause was a segmentation disagreement, not an accent. The Montreal Forced
Aligner writes pre consonantal coda r as its own phone. The frozen scoring
model carries it inside a combined vowel token and never emits it separately.
The expected standalone segment therefore owned no frames and was flagged at
**96.6 percent in every group alike**, to three decimal places, including the
American control against its own native reference. The apparent accent effect
was that identical impossible rate multiplied by how often each group's prompts
happened to contain the context. It was a property of the measurement, and the
measurement was broken.

The same class of defect had been found once before, in dark l, and fixed at the
previous mapping version. The audit found it five more times. **Six phone
families in total** were being scored against targets the model never produces
for English: the conditioned palatal series c, ɟ, ɲ, ç and ʎ, each flagged at or
within half a point of 100 percent in every group, plus the glottal stop.

The rhotic is a separate problem and the distinction matters for section 6.2.
The palatals and the glottal stop are phones the model **never emits**. Post
vocalic r is a **segmentation disagreement**: the model does emit it, inside a
combined token, and the reference expects it as a segment of its own. Those six
families together supplied **38.9 percent** of every flag the superseded probe
produced. The rest of the reduction is the rhotic.

The correction rescored all 2,400 clips. The rebuilt sample is byte identical
in clip selection, order, speakers, exclusions and seed, so before and after are
directly comparable. 68.3 percent of expected phone sequences changed, 3,277 of
4,800.

| flag rate, threshold minus one | before | after |
|---|---|---|
| American control | 0.1664 | **0.0863** |
| Australian | 0.1629 | **0.0823** |
| British | 0.1779 | **0.0944** |

**Roughly half of every flag this probe had ever produced was noise.** These
are native speakers reading known text, so almost every flag is a false concern
by construction, and half of them were not even about the speakers.

A second retraction came with the first. The superseded report had concluded
that swapping to a non rhotic reference only lowered the flag rate by declining
to score, because the American control moved when it should have stayed put.
That mechanism was the same artifact: post vocalic r was scored and always
failed under the American reference, while the non rhotic reference stopped
creating the opportunity at all. With that segment excluded under both
references the asymmetry disappears, and the control stays approximately in
place, which is what the contract had predicted before the run.

Scoring opportunities fell only 1.5 percent, from 22,350 to 22,012 in the
control, because the palatals were renamed to their broad phonemes rather than
discarded. The opportunity ratio across the two references is 1.034, 1.033 and
1.038 in the three groups, so **no group is differentially disadvantaged by the
abstention**, which is the property that matters when a measurement is allowed
to decline to score.

That aggregate stability conceals large movement underneath it, and section 4.1
does not let the aggregate stand in for the parts: individual consonants move by
far more than three percent between the two references, in both directions, and
only eight of them are stable enough to be compared across references at all.

The superseded reports remain committed, with their hashes, and they no longer
validate. The validator now fails the build if either retracted finding is ever
recorded as holding again.

### 2.2 The evidence record was corrected after an open search disproved it

Published figures in this repository have been wrong **five separate times**:
the aligner phone counts recorded at one checkpoint, word counts taken from a
publisher's own pages, the size of the Australian tagged Wiktionary pool, the
rhotic finding above, and the claim that a default run makes no remote call.

The fifth is the youngest and it belongs in this list rather than in a footnote.
It was found while this document was being written, it is set out in section 9,
and an earlier version of this document recorded it there while still counting
four here. That is the same failure in miniature: a corrected fact sitting
beside an uncorrected summary of it. The count was fixed on 2026-08-27.

The pattern in four of the five is the same: a number was taken from a source
that asserted it, rather than computed from the thing itself. The standing rule
that came out of it is that published figures are recomputed rather than
carried forward.

One case is worth stating separately because it moved from "undocumented" to
"disproved". A candidate lane in the pronunciation system search was a
grapheme to phoneme model advertised as producing Australian broad IPA. Its
claimed training source was checked rather than accepted: WikiPron defines
English with two dialects only, UK and US, and the named Australian dataset
does not exist. The lane's rejection reason was rewritten from an undocumented
training source to a disproved one. No verdict moved, but the record now says
something true instead of something merely cautious.

### 2.3 The best claim did not survive the literature

Before writing any account, this project intended to claim that its evidence
linked claim machinery, in which a language model writes prose over a
structured measurement record and a checker mechanically verifies the model's
numeric claims against that record, was a novel contribution.

That was checked on 2026-08-24. It does not survive, and it is not close.

- **statcheck** (Nuijten et al., 2015 onward) has extracted statistics from
  psychology papers and recomputed them from the reported test statistics for a
  decade, flagging inconsistencies and decision flipping inconsistencies at a
  reported 96.2 to 99.9 percent classification accuracy. It is GPL and it is
  embedded in peer review at journals including *Psychological Science*. This is
  the same idea, ten years earlier, without the model.
- **Wiseman et al. 2017** and **PARENT** (Dhingra et al. 2019) established
  verifying generated text against the source records it was generated from.
- **Proof-Carrying Numbers** (Solatorio, World Bank, September 2025,
  arXiv 2509.06902, CC BY-SA 4.0) specifies this repository's numeric verifier
  generically and domain agnostically: numbers emitted as claim bound tokens,
  each checked against a declared policy of exact, rounded or tolerance, fail
  closed, unverified numbers left unmarked. A year before this repository built
  it.
- **SpeakerCard-1M** (Peng et al., BUT Speech@FIT, arXiv 2606.03283,
  2 June 2026) does the whole architecture in speech: ten acoustic probes
  populate a structured schema, a constrained model sees only the structured
  fields and never the raw audio, and the generated cards are checked against
  their structured premises by natural language inference.

That date is worth one footnote, because `prior-art-2026-08-24.md` records
SpeakerCard-1M as 28 June and it is 2 June. The arXiv identifier sequence
settles it: 2606.03283 sits far below 2606.11639 and 2606.15325, which are 10
and 13 June. The correction does not change the conclusion, and it is noted
because a record kept so nobody researches the question again should have the
date right.

Eleven days after SpeakerCard-1M, *Prior over Evidence* (arXiv 2606.15325,
13 June 2026) arrived at this project's own thesis in its authors' words: that
current general purpose models are more reliable as verbalisers of externally
computed evidence than as standalone diagnostic engines. Two independent groups,
eleven days apart, in speech. That is a converging front and not an empty field.
Open implementations of the general pattern are commodity.

The claim was narrowed to the integration and licence sentence in section 1,
and the wider version is not made anywhere.

The record of that check is `prior-art-2026-08-24.md`, kept so nobody
researches it again, and so the narrowing is visible rather than quiet.

---

## 3. What was built

### 3.1 The measurement engine

A run takes one audio file and produces `master.json`, a measurement record.
That is the output. As of 2026-08-24 the language model layer is opt in and off
by default: a run with no flags produces measurements, provenance, uncertainty
and abstention, and stops.

Stage order, verified against the code rather than the documentation:

**Both modes** begin with an audio quality preflight (14 distinct checks) whose
verdict can reject the run outright. Then, in parallel: transcription, letter
level timing alignment, and pause detection. Conversation mode adds speaker
diarization to that parallel group; solo mode instead runs a solo timing and
contamination check afterwards.

Then, sequentially: acoustic measurement, the merge that produces
`master.json`, and timestamped speech event candidates. Conversation mode
inserts a speaker label referee and a merge rebuild between the merge and the
event candidates.

The dependencies are named rather than implied. Transcription is either
AssemblyAI or a local Whisper model. Alignment and the local transcription path
use WhisperX with `Systran/faster-whisper-small`, with the per language
alignment model resolved from WhisperX's own defaults. Diarization uses
`pyannote/speaker-diarization-3.1` behind a Hugging Face token. Pause detection
uses Silero VAD. Acoustics uses Praat through parselmouth, **which is why the
licence is GPL 3.0 or later** and cannot be made permissive without removing
that dependency first.

Three stages call Gemini, and **only two of them are optional**. The referee is
the exception: it corrects speaker labels *inside* `master.json` rather than
commenting on them, so it is measurement, and making it opt in would have
silently changed default speaker attribution. It therefore runs by default in
conversation mode. The listener and the interpretation are the two behind
`--interpret`; the claim verifier that runs after them is deterministic code and
calls no model at all.

**Transcription is load bearing and deliberately so: it fails the run.** The
three model stages are not. Each retries exactly once and then records an
explicit status and error category in `master.json`, leaving every objective
artifact intact. Both a request level timeout and an outer deadline apply, so a
call that never returns becomes a `timeout` and degrades rather than stalling
the run indefinitely.

There is **no fallback between transcription paths**. A missing key fails the
run rather than quietly switching to the local model, because the two do not
produce the same evidence and a record that could have come from either is not
a record.

### 3.2 What the interpretation layer is, and what was deleted from it

`--interpret` adds three stages: a listener, an interpretation, and a claim
verifier. Without the flag none of them run and none of their files exist.

Until 2026-08-24 the pipeline ended by asking a language model to score a person
0 to 99 on CLARITY, WIT, WARMTH, PRESENCE and STORY. **Those five scores have
been deleted and nothing replaced them.** They were language model output parsed
by regular expression against hand written anchors. They were never validated as
measurement scales, and they presumed an audience of people seeking feedback on
their speaking, which this project states in as many words that it does not
have. The prompt that produced them opened with "You are an elite speech and
communication coach".

Deleting them made the verification layer strictly stricter rather than weaker.
The `prescription` claim type was withdrawn rather than renamed: it was the only
claim type permitted to exist with no evidence, and it existed so the report
could tell a person what to practise. Every claim now requires evidence.

What remains: the model describes measurements. It has no persona, produces no
number of its own, and may not make a claim about a measurement the pipeline
declared unavailable or low quality. Every statement carries a claim marker
resolving to an entry in an evidence catalog, and the checks cover path
existence, speaker ownership, turn and timestamp containment, measurement
availability and quality, exact numeric values, and signed direction.

`evaluation.md` opens with a run record that the **pipeline** writes from
`master.json`, not the model: conditions, every warning with what it affects,
and every withheld measurement with its reason. Availability is a deterministic
fact about a run, so code reports it rather than asking a model to report on
itself. That block is excluded from claim checking, because verifying it
against `master.json` would only verify the renderer against itself.

### 3.3 The research contracts

Beside the engine sit versioned, validated contracts that constrain what may be
claimed. They are the part of this repository that took the most work and
produce the fewest results, which is the intended ratio.

- **Voice and prosody.** Timestamped per speaker fundamental frequency and
  recorder level evidence, task and consent gates, octave error checks, and
  explicit refusal to infer pitch perception, gender, confidence, personality
  or voice health from any of it. No combined index is permitted. Cross device
  comparison is blocked pending validation that does not exist.
- **Fluency events.** Timestamped repetition and prolonged sound candidates,
  each carrying source evidence, alternative explanations, uncertainty and a
  review state. The automated output is a *candidate*, never a confirmed event.
  Possible blocks are deliberately manual, because silence cannot establish a
  block. Absence is explicitly not evidence of fluency. The artifact never
  reaches the interpretation layer, the claim ledger, history or progress.
- **Speech sound patterns.** Research contract version 1.7, licence audited
  manifests for 22 corpora, a fail closed provider register, a frozen benchmark,
  two frozen comparisons, the selection record, the reference variety probe, and
  the immutable repository closure. There is no active task, no selected system,
  no pipeline stage and no released artifact.
- **Motor speech and voice.** Shelved, and kept as completed evidence for why
  this project makes no clinical claim. Its deliverable ledger records eight of
  thirteen deliverables blocked on a named accountable human role that does not
  exist. Section 6.6 says why that is structural rather than administrative.

---

## 4. What was measured

### 4.1 The reference variety probe

**The question.** If you score Australian speakers with a pronunciation system
whose reference is American English, does it flag them more often than it flags
American speakers? And does swapping to a non rhotic reference closer to
Australian English reduce that?

**The design.** 2,400 clips from 1,200 speakers, 300 per group, drawn from
Common Voice release 26 with deterministic seeded sampling. Four groups:
Australian English, British Isles English, American male and American female,
the last two pooled as a 600 speaker control. Every speaker is scored twice,
once against the Montreal Forced Aligner English (US) dictionary and once
against English (UK), so the two conditions differ in reference variety alone
and share one phone alphabet. All four groups are participant split and sealed
by the same code, with zero cross split overlap.

The scoring model is `facebook/wav2vec2-lv-60-espeak-cv-ft`, frozen. A flag is
raised when a scoring opportunity falls below a threshold; five nested
thresholds are reported as a sensitivity curve rather than as five chances to
find an effect.

**The pre registration is the strongest part of the design, and its limit is
stated rather than glossed.** The contract is a separate committed file and the
loader refuses to run if any release boundary is open. **Only the five group
level hypotheses were pre registered before the run.** The per consonant
analysis was not, and its headline consonant was chosen after seeing which one
was largest. That is why the two are held in separate families: pooling a pre
registered test with an exploratory selection would penalise the first for the
second's freedom and let the second hide inside the first. All four families
were fixed before any p value was computed, and the contract forbids moving a
test between families, or splitting or merging a family, after an outcome is
seen. Crucially, the family that contains the
consonant chosen *because it looked largest* is corrected across all 22
consonants it was chosen from, so the multiplicity created by the choice is paid
for. A deliberately harsher sensitivity family of all 430 tests in the full grid
is computed and published whatever it shows, so that declaring the primary
family cannot be mistaken for choosing the lenient answer.

Uncertainty is a speaker clustered bias corrected and accelerated bootstrap at
10,000 resamples, with speaker label permutation at 10,000 permutations, one
resample serving every reference, threshold and consonant. **The unit of
analysis is the speaker, not the clip.**

**The results.**

At threshold minus one, under the American reference, mean of per speaker flag
rates:

| group | speakers | flag rate |
|---|---|---|
| American control | 600 | 0.086257 |
| Australian | 300 | 0.082325 |
| British | 300 | 0.094377 |

The Australian minus American differential is **−0.003932**. It is *negative*.
The probe's central prediction, that an American reference penalises Australian
speakers, **failed**, and correcting the phone mapping made it slightly more
negative rather than less. That is recorded as a failed prediction rather than
reinterpreted, and the validator fails the build if it is ever written up as
having held.

**Nothing at group level is distinguishable from zero.** All five pre registered
group level intervals contain zero, the smallest uncorrected p value is 0.143,
and none survives correction. This is a null and not a caveat attached to
something else.

It is also a *small* null. The minimum difference this design could reliably
detect at 80 percent power is about 0.0146, and the observed differential is
about 0.0039. **This is a look too small to tell, not a demonstration that the
two groups are scored alike.** The report says so in those words.

**One test out of the 48 in the three reported families survives correction, and
it is not about Australians.**
Under the American reference, British speakers are flagged more often than the
American control on the voiced dental fricative ð: point estimate **+0.0486**,
95 percent interval **[0.0187, 0.0826]**, uncorrected p **0.0005**, surviving
both Benjamini Hochberg and the stricter Bonferroni within its declared family.
It holds its sign and rough size at all five thresholds and under both
references, and it is one of only eight consonants whose opportunity count is
stable across the two references, so it is compared like with like.

In the harshest sensitivity family, 430 tests, exactly one survives Bonferroni,
and it is the same consonant in the same group at a different threshold, minus
two rather than minus one.

**That sentence is true and it was not the whole picture, which this account
corrected on 2026-08-27.** Under Benjamini Hochberg, 16 of the 430 survive, and
8 of those 16 sit on one consonant: the affricate dʒ, under the British
reference, negative in both non American groups. Australian minus American runs
between −0.098 and −0.121 across the five thresholds; British minus American
runs between −0.107 and −0.132. Every one of the ten intervals excludes zero,
and both effects are larger than the minimum difference this design could
reliably detect for that consonant, which is 0.068 and 0.082. They are the
largest differentials anywhere in the probe.

The report does not promote them to findings and gives two reasons. Nobody
declared them before the run. And dʒ is one of the 17 consonants whose
opportunity count moves between the two references, gaining about nine percent
under the British one, so the comparison that produces them is not like with
like and the changed denominator is a live explanation for the whole effect.
They are published in full so that a later pre declared analysis can test them
properly. That reasoning stands, and this account is not overturning it.

What was wrong was the reporting. This document gave the primary families under
both corrections and the sensitivity family under the stricter one alone, which
left a reader with the impression that the harsh analysis found almost nothing.
The sensitivity family exists so that declaring a primary family cannot be
mistaken for choosing the lenient answer. Reporting it selectively defeats the
purpose of publishing it.

**What that result is not** is evidence about British English. The groups read
effectively disjoint prompt sets, 34 shared prompts out of hundreds, so variety
is confounded with lexical material. And there is no expert phone truth to check
any of it against. It is a stable, corrected, unexplained differential in a flag
rate, which is a property of this measurement and not of the speakers, and it is
reported as exactly that.

**The consonant that used to be the result is gone.** After the mapping repair,
t was the largest single per consonant differential and was carried forward as
the one live finding. Once uncertainty was computed it did not survive.

Computing the uncertainty also changed the estimate itself, and that is worth
separating out. The superseded analysis pooled every token in a group and
applied **no speaker clustering at all**. The current one computes a rate per
speaker and then averages, matching the group level analysis. The t differential
is **+0.0269 pooled** and **+0.0362 per speaker**. Both numbers are in the
record; only the second is the one the intervals and the corrections were
computed on, and it is the one that belongs in a sentence about whether the
effect survives.

On that estimate: t is +0.036223, 95 percent interval **[0.0020, 0.0748]**,
uncorrected p **0.045**, which reaches the five percent level at exactly one of
five thresholds and at no other, and changes sign at minus three. Both
corrections remove it across its declared family of 22. Its effect size sits
**below the 0.0531 minimum this design could reliably detect for that
consonant**.

And it is not even the largest movement in its own family. **dʒ runs to
−0.0554**, half again as large and in the opposite direction, with j at −0.0436,
ŋ at −0.0266 and ɡ at −0.0263 also negative, while tʃ at +0.0350 nearly matches t
in the same direction. A consonant picked out as the largest effect in a family
whose spread looks like that is a threshold artefact at the noise floor, and
that is the honest reading.

**A comparison that cannot be made.** The two references do not create the same
scoring opportunities. Only 8 of 25 consonants keep their opportunity count
within two percent across the two references; the t target gains about 28
percent under the British reference. So a cross reference comparison for any
consonant outside those eight is not like with like, and an apparent effect
there may be the changed denominator rather than the speakers. This was not
known when the previous version was written, and it withdrew the support for one
of its sentences.

**Declared confounds**, stated rather than discovered by a reader: recording
quality varies across contributors; both American subsets are filtered to a
declared gender while the other two are not; the British subset pools England,
Scotland, Wales and Ireland and is broader than the reference describes; self
reported accent is context and not phonetic truth; the dictionaries describe
varieties and not individuals, so a flag may be a legitimate personal variant;
and the aligner writes conditioned palatal allophones as separate phones, so a
vowel difference can surface as a consonant difference. One contributor who
declared different varieties on different clips is excluded from every group by
a frozen exclusion record. No other pair of subsets shares a speaker or a clip.

**A conflict of interest in the evidence, declared and not resolved.** The
scoring model is fine tuned on Common Voice, and this probe evaluates entirely
on Common Voice speakers. This project's own rules disqualify a different model
elsewhere for exactly that reason, and the rule was never applied here. The
declaration, in one line: the direction of the bias is unknown, it plausibly
favours the control group, and the observed result runs against it, so the null
is conservative rather than suspect.

The mechanism matters and is worth spelling out. Common Voice English skews
American and British, so the model has plausibly heard far more of the control
group's speech, which would fit them better and flag them less. That is a group
dependent effect. **The argument that one model scoring everybody makes the
overlap cancel is therefore wrong, and it is not made here.** What protects this
particular result is only its direction: the American control is flagged more
often than the Australian group, 0.0863 against 0.0823, which is the opposite of
what the bias predicts. **That protection does not transfer.** A future
differential running the way the bias predicts would be uninterpretable under
the same reasoning, and resolving it properly needs a second phone model with no
Common Voice lineage rescoring the same 2,400 clips.

### 4.2 The search for a pronunciation scorer, which selected nothing

Before the probe, this project ran a full candidate search for a system that
could flag a pronunciation concern well enough to be used. **It selected
nothing, twice, under gates that were never moved.**

Five gates, inherited unchanged: minimum precision point estimate 0.75, minimum
precision Wilson 95 lower bound 0.5, minimum recall 0.2, minimum true positives
7, maximum 0.01 false concerns per scorable opportunity, and both the
development and the tuning partition had to pass.

Fourteen lanes were considered. Seven were blocked, five rejected, one is
research only and one supporting only. The strongest candidate was this
project's own segmentation free approach, which held development precision at
**0.751** against the 0.75 minimum and then missed development recall at
**0.189** against the 0.200 minimum, with threshold tuning precision falling to
0.622. The strongest external candidate passed 8 of 10 checks. **No paid
external provider added anything the free local stack had not already
provided.**

Two things make this outcome interpretable rather than merely disappointing.

An exploratory analysis scored each of the **five original expert human
reviewers** as though the reviewer were the candidate system. **Three of the five
pass every gate on both partitions.** So the gates sit at roughly competent human
level rather than being unreachable. That analysis is context and no gate was
moved on the strength of it in either direction.

And a portion of every error measured is reviewer disagreement rather than
candidate error: Fleiss kappa across the five reviewers is **0.566** on
development adults and **0.520** on tuning adults.

**The honest qualification, which the record states itself: 11 of the 14 lanes
were never measured.** They were blocked by access, licence, provenance,
provider terms, an owner decision or the lane's own role. Their verdicts record
why nothing is known about them, not that they were tried and found wanting. A
`no_selection` reached partly because most candidates could not be obtained is a
weaker result than one reached by measuring them all, and it is reported that
way.

All 26 held out adults and 24 held out children remain sealed. All 40
predeclared held out measures are explicitly **unavailable**, which is not zero,
not a pass and not a failure. The access audit records zero audio files read,
zero labels read, zero participant identities read and zero provider
transmissions.

Everything measured in that comparison rests on SpeechOcean762, which is
Mandarin first language read speech assessed against American English. **No
result from it transfers to Australian speakers.**

### 4.3 The offline path, and a defect found only by running it

A local transcription path was added so the pipeline runs with no paid
credentials. Whether that costs measurement quality is a question about
evidence, so it was measured before the model and the decoding options were
chosen. Neither transcriber is truth: no expert verbatim transcript of the test
recordings exists, so every figure below is agreement between two systems, which
this project does not treat as evidence that either is correct.

The interesting result was that **disfluency retention is set by the decoding
prompt, not by model size.** Against a reference transcript of 278 words
carrying 5 filled pauses, both a small and a large model returned **none** of
the five unprimed, and **all five** when primed. The large model cost five times
the runtime and a three gigabyte download to move word agreement by about half a
percentage point. So the local path uses the small model with a short priming
prompt. Its cost runs the other way: primed, it reported 8 filled pauses where
the provider reported 5, and whether the provider missed them or the local model
invented them **cannot be settled from this evidence** and is not settled.

The defect found by running the path is the more useful part.

**A forced alignment score is not an ASR confidence, and this repository was
comparing one against a threshold calibrated for the other.** The fluency
contract refuses a word whose ASR confidence falls below 0.5, a floor calibrated
against a provider's posterior. The local path's aligner emits a per word score
on an entirely different scale. On a real recording it scored a genuine repeated
phrase at **0.307 and 0.154**, so the eligibility rule **discarded a real
repetition while appearing to work perfectly**.

The repair was to stop pretending they are the same quantity. The local path now
writes `alignment_score`, emits no `confidence` at all, and the four fluency
families that need one declare themselves unavailable rather than returning zero
candidates. **No threshold was retuned**, because there is nothing to retune it
against. Anything adding a second provider to this pipeline should check the
same question before trusting a field name.

Two capabilities are genuinely lost on the local path, and both are declared
unavailable rather than silently returning nothing, because a zero here would
read as "none found" when the truth is "not measured": second voice detection in
solo recordings, and the four text derived fluency families.

---

## 5. What verification actually demonstrates, which is less than it looks

This is the part most likely to be over read, so it is stated plainly and the
software says it too, inside the generated report rather than only here.

**Verification is only as interesting as the model's freedom to be wrong.**

Once the five invented scores were deleted, the interpretation layer became
incapable of producing a number of its own. Its numeric claims are therefore
largely restatements of values it was handed. A clean verification report mostly
shows that a copy operation copied correctly.

Three consecutive acceptance runs verified every claim they contained with zero
issues. A further run made on 2026-08-26 purely to check this section verified
**11 of 11 with zero issues on the first attempt**. That is not evidence of a
strong verifier; it is evidence that the task was easy.

**In production this verifier has never rejected a claim.** The only
demonstrated catch is a synthetic case in the regression harness, where a claim
deliberately attributed to the wrong speaker is pinned to fail.

And the failure that matters most is one a numeric verifier **cannot catch at
all**. An unsupported interpretation carries no arithmetic. That is precisely
the failure mode *Prior over Evidence* (Wang and Sun, arXiv 2606.15325, June
2026) measured at **39.6 percent of judged cells containing internally coherent
reasoning supporting a wrong rating**, against 15.8 percent coherent and correct.

The run made while writing this section demonstrates it concretely. Of its 11
verified claims, 8 were typed as measured observations and 3 as
interpretations. The three interpretations were:

> The setting is inferred to be an informal, low-stakes ad-hoc solo recording
> where the speaker is completing a series of spoken prompts

> The 5.8 dB increase in volume observed at 17.67 seconds on the word
> 'describe' could indicate that the speaker was deliberately emphasizing
> prompt instructions as they read them aloud

> The overall turn loudness of 4.8 dB below the speaker's baseline might suggest
> a highly close microphone proximity or an exceptionally quiet local
> environment during recording

All three passed. The second and third attribute an intention and a physical
recording environment to a person from a loudness value. The first is a claim
about the situation the speaker was in, and its single piece of supporting
evidence is a field named `scenario.inferred`. **The verifier confirms that the
inference exists. It has no way to confirm that the inference is right.** The
numbers in these claims, 5.8 dB and 4.8 dB, are correct, checked, and entirely
beside the point.

**A specification gap found the same way, and it is the sharpest thing in this
section.** One claim in that run reads:

> A listener's overall impression describes the speaker's delivery as a very
> soft, breathy whisper with extremely low energy and a slow pace punctuated by
> long silences

It is typed `measured_observation`. Its only evidence is a reference of source
`listener_perception`.

The prose is honest, and the model did exactly what it was told. The evidence
source classes are tracked properly and each carries its own integrity rule: a
listener perception is refused if the listener stage did not complete, inferred
context must cite an inferred path, and a screening hypothesis is rejected
outright at any level. But **nothing ties a claim's declared type to the class
of evidence underneath it**, and the prompt's own definition makes this correct
rather than wrong, because it says to use `measured_observation` when a
statement "restates or describes a stored value" and a listener impression is a
stored value.

The consequence is narrow but real. A reader of the prose is not misled. A
downstream consumer filtering the machine readable ledger for
`measured_observation` would receive a language model's subjective impression of
how somebody sounded, sitting in the same class as a timestamp. This project's
binding rule is to keep measurements, listener perceptions, interpretations and
outcomes separate and never to pool truth classes. At the level of the evidence
reference that rule holds. At the level of the claim type it is not enforced.

**This was closed in `v0.2.0` on 2026-08-28 and section 9 records the closure.**
The gap and the run that demonstrated it are left standing above, because the
account of what was found is the point of this document. What changed is that a
measured observation now has to rest on evidence this pipeline measured. What
did not change is everything else in this section: the verifier still cannot
tell a sound interpretation from an unsound one.

Two further honesties about the layer.

The model still degrades sometimes, and this was reduced rather than fixed. One
acceptance run failed both attempts and degraded safely to an explicit
unavailable report with the measurement record untouched. The prompt rules were
then made explicit and the runs that followed passed first time. **A handful of
passes is not a reliability measurement and this is not solved.**

And on two of five real responses the provider returned the entire report as a
single line with its line breaks written as a literal placeholder. It rendered
as a wall of text and **passed claim checking**, because every marker was present
and in order. A narrow deterministic repair now restores the breaks and records
that it happened. The general point is the useful one: **the verifier checks the
claims, not whether the artifact is readable.**

---

## 6. What could not be established

These are results. They are the reason several attractive things in this
repository stop where they do.

### 6.1 There is no expert Australian phone truth, at any licence and at any price

Only three corpora anywhere carry expert phone level pronunciation annotation:
SpeechOcean762 (Mandarin first language), L2 ARCTIC (second language speakers)
and EpaDB (Spanish first language). For first language English varieties the
only sources are TIMIT, which is paid, and Buckeye, which is forty speakers from
one city. **No expert produced phone level annotation of Australian English
exists.** This survived the project's direction change unchanged, because it was
never a licensing problem.

This is now confirmed by an independent source. Metzger et al.
(arXiv 2606.16019, June 2026) assembled what is effectively every expert phone
annotated English corpus in existence for their benchmark: TIMIT, EpaDB, PSST,
L2-ARCTIC, SpeechOcean, Buckeye, DoReCo and ISLE, 1,171 speakers and 80 hours.
The native English varieties they obtain are 8 United States dialects, Columbus
Ohio, and Southern British at two speakers and 0.79 hours. **Zero Australian.**
An independent group assembling a benchmark for exactly this purpose hit exactly
the same wall.

The consequence for everything above: this project cannot report accuracy,
sensitivity or specificity for anything, because there is nothing to measure
against. Every result in section 4 is a differential in a flag rate between
groups, which is a property of the measurement, and never an error rate against
truth.

### 6.2 Rhoticity is not measurable by this class of system

Post vocalic r is excluded under both references, because the reference and the
model disagree about whether it is a segment at all. It is the sharpest
Australian and American consonantal difference, and **this class of system
cannot evaluate it.** That is the substantive finding hiding inside the
retraction in section 2.1: the defect was not merely an implementation error, it
was the measurement's way of reporting that the thing being asked about is
outside what it can see.

### 6.3 The reference is a dictionary, and a dictionary is not truth

The expected phone sequence in this experiment comes from a pronunciation
dictionary. It describes a documented variety, not the individual in the
recording, so a flag may reflect a legitimate personal or regional variant.

The concurrent literature reaches the same conclusion independently. Bao, Saha
and Patwari (arXiv 2606.11639, June 2026) generate their reference sequences
with a grapheme to phoneme pipeline and state in their limitations that the
resulting ground truth "often reflects standardized pronunciation, which can
encode biases of what constitutes 'correct' speech", that this "will naturally
increase the error rates for accented speech, dialectal variation, and
non-canonical pronunciations, where no single canonical phonemic form may
exist", and that even a softened error metric "may reflect annotation artifacts
rather than true model error". Metzger et al. reach it from the training side:
high quality human labels are what let a model generalise to unseen dialects,
and "this cannot be achieved by scaling machine labels alone".

Three independent groups, in the same year, describing the same limitation.
This project's contribution to that agreement is a demonstration of how badly it
can go: the retracted rhotic finding is a fully worked example of a
dictionary reference manufacturing an accent effect that was not there.

### 6.4 A variety mismatch may be excluded but never subtracted

Running Australian speakers through an American scorer and then correcting the
result using knowledge of their accent is rejected as a method. The effect is
systematic, its size cannot be measured without expertly labelled Australian
speech, and a repeatable system doing it would report the same unfounded
concern every time while its repeatability made the error look like evidence.

Relatedly, this project does not classify a speaker's accent. A reference
variety is declared by whoever runs the analysis. Inferring someone's identity
and then deciding how their speech ought to sound is a harm it will not
introduce.

### 6.5 Fairness is not evaluated, and that is not a fairness pass

The audit reports fairness as `not_evaluated`. Missing subgroup evidence is not
evidence of fairness. No representative validity study supports ranking people,
and ranking is blocked.

### 6.6 There is no validated progress metric, and no clinical anything

Personal progress remains blocked because repeated human productions,
measurement error, natural variation and meaningful change are not established
for any of these measures. Independently validated voice, prosody or event
detection accuracy does not exist here either.

The motor speech and voice work is shelved for reasons that are structural
rather than administrative: the lane has no qualifying reference source in
public at any licence and at any price, acceptance is defined as written review
by accountable human roles that do not exist, and Queensland recording law and
Australian ethics review follow the author personally regardless of licence. It
stands as completed evidence for why this project makes no clinical claim.

---

## 7. How this relates to other work

### 7.1 On the claim verification machinery

Not novel, and section 2.3 has the record. The lineage runs statcheck 2015,
Wiseman et al. 2017, PARENT 2019, Proof-Carrying Numbers 2025, SpeakerCard-1M
2026. Open implementations of general purpose factuality and claim checking are
commodity: OpenFactCheck, MedVAL, RadFact, GREEN, and a decade of radiology
report factuality metrics.

A deterministic core with an optional constrained model layer is likewise a
normal 2026 architecture and not an unusual one, actively advocated across
several fields in the same period.

**No claim is made to the invention of evidence guarded machine learning**, and
it would be a false one. Data statements (Bender and Friedman 2018), datasheets
for datasets, model cards, and decades of selective prediction and conformal
prediction literature all precede this project and cover the ground of declaring
provenance, declaring limits and declining to answer. What is described here is
an application of those ideas to phone level speech measurement with a working
implementation, not their origin.

Where the field is genuinely thin is narrower: deterministic rather than model
judged verification of numerals as a first class artifact, and the application
of the whole pattern to speech and voice. SpeakerCard-1M does the architecture
for speaker traits, **with no uncertainty and no abstention**.

Hence the single claim, restated: no open, reusable harness combines provenance
on inputs, per measurement uncertainty, explicit abstention, and verification of
generated claims, for speech measurement. Checked against openSMILE,
Parselmouth, DisVoice, Surfboard, speechmetrics, VERSA, SpeechBrain, ESPnet3,
OpenDBM and TELL 2.0: every one returns a number and stops.

Worth recording alongside it: **abstention in speaking assessment is solved
commercially and undocumented publicly.** ETS holds patents on non scorable
response filters covering audio quality, insufficient speech, off topic, wrong
language and plagiarised content. It is a genuine abstention architecture with
per criterion evidence, and it is proprietary. The academic literature on model
based speech feedback largely does not abstain at all.

### 7.2 On the two dialect papers this account was required to read

**Bao, Saha and Patwari, arXiv 2606.11639**, evaluate bias in two open IPA
producing recognisers across languages and demographic groups, comparing model
output against grapheme to phoneme references using standard phone error rate
and a proposed Soft PER that gives zero penalty to linguistically similar
substitutions, built from AlloVera and PHOIBLE into 62 equivalence classes over
254 phones.

This is the closest published neighbour to the variety probe, and the
relationship is worth stating precisely.

- **Their Soft PER is prior art for the idea behind this project's phone
  normalisation table**, and it is more principled in construction, being
  derived from published allophone and articulatory feature resources rather
  than assembled by hand.
- **The two approaches differ in what they do with an unscorable opportunity.**
  Soft PER reduces the penalty for a substitution judged acceptable. This
  project excludes the opportunity and reports it as excluded, and forbids
  subtracting an estimated variety effect from a score. Both are defensible;
  they are not the same operation, and this project's rule is the more
  conservative one.
- **They report speaker level mean error rates but no confidence intervals**,
  and several of their demographic groups are small: the ethnicity breakdown
  runs n=23, 15, 14 and 6 speakers, with reported disparities as small as
  +0.012. This project's own experience is the direct commentary here, and it is
  offered as a caution rather than a criticism, because this project made the
  same mistake first. Its largest per consonant differential looked like the one
  live result in the comparison until speaker clustered intervals and a
  multiplicity correction were computed, at which point it disappeared, and
  another consonant half again as large turned out to run the other way. Point
  estimates at this scale are not stable enough to read without intervals, and
  pooling tokens instead of clustering by speaker changes them too.
- **Their findings and this project's are consistent.** They find persistent
  disparities by accent, ethnicity and age that survive tolerant matching, and
  limited evidence of gender disparity. This project found nothing
  distinguishable from zero at group level for Australian versus American
  speakers, in a design whose minimum detectable difference was about 0.0146.
  Those are not in conflict: this project's null is explicitly a look too small
  to tell.

**Metzger, Srivastava and Mukhamedvaleev, arXiv 2606.16019**, ask how phonetic
transcription performance scales with human versus grapheme to phoneme
supervision, and find a threshold: machine generated labels help only below
roughly 20 to 30 hours of human annotation, beyond which they add nothing and
**can reduce cross dialect robustness**, while ASR pretraining improves out of
domain generalisation without introducing label bias.

Two things follow for this project. First, their corpus table is the best
available external confirmation that no expert annotated Australian English
exists, as section 6.1 sets out. Second, their result explains the mechanism
behind this project's central methodological problem: a dictionary derived
reference biases toward standard speech patterns, and quantity does not fix it.
This project's retracted rhotic finding is what that bias looks like when it is
mistaken for a result.

Neither paper is contradicted by anything here, and neither contradicts
anything here.

**One caveat about this section specifically.** Every other figure in this
document can be checked against a stored record in this repository. The figures
in this section cannot: the speaker counts, hours, equivalence class counts and
group sizes come from the two papers themselves, read on 2026-08-26. They are
reported as read and a reader should check them at the source rather than take
this document's word for them.

---

## 8. What a reader can check, and how to disagree

The point of publishing is that someone can obtain this, run it, and reach a
different conclusion on the evidence.

- **The probe is reproducible without any audio.** A 4.75 MB pseudonymised
  evidence bundle of 2,400 records from 1,200 speakers regenerates the full probe
  report **byte for byte** in about two minutes, needing only numpy. Its manifest
  pins the sha256 of the report it reproduces, so the claim is checkable rather
  than asserted, and it was checked on 2026-08-26. No audio is redistributed and
  none may be. The stored evidence originally carried each contributor's verbatim
  corpus identifier, which joins straight back to the public dataset; the bundle
  mints opaque keys and the mapping is never written to disk.
- **The superseded reports are still there,** with their hashes, so the
  correction in section 2.1 can be audited rather than taken on trust. They no
  longer validate, deliberately.
- **1,000 unit tests**, all passing, run on 2026-08-27. In the public
  repository 92 of them skip, because they need the private research corpora,
  the working repository's git history, or the snapshot contract, which is not
  published. They skip **with the reason stated** rather than erroring or
  quietly passing, which is the same discipline the pipeline applies when it
  declares a measurement unavailable.

  **Two of them did not skip, and failed here from the first release until
  2026-08-27.** The tests that need the working repository's history were gated
  on whether a git history existed at all. A freshly built snapshot has no
  commits, so they skipped during every verification and the release looked
  clean. This repository accumulates commits of its own, so in the copy anybody
  actually cloned the gate opened, the tests looked for commits that exist only
  in the private repository, and two failed. The gate now asks whether it is
  running inside a published snapshot rather than counting commits. The way it
  was found is the point: the suite was run inside the synced public repository
  instead of inside the scratch build, which is the only place the difference is
  visible.
- **The regression harness keeps three kinds of evidence separate**: unit tests
  for local rules, a replaceable software snapshot that detects changed
  behaviour but is not truth, and independent truth files carrying their source,
  annotator role, guide version, date and adjudication status. The `--bless`
  flag can replace only the software snapshot; it cannot create or change a
  truth label.
- **What is withheld, and why.** The public repository is a rebuilt sanitized
  snapshot, never edited by hand: as computed on 2026-08-27, **2,802 files are
  published and 44 are withheld** under a declared contract that names every
  exclusion, substitution and overlay with its reason. Most of the withheld
  material is personal recordings, transcripts and derived measurements of the
  author and of one other person who consented to being recorded and was never
  asked about publication. Three of the 44 are not private at all: the working
  repository's status page, its roadmap and its working agreement with its
  owner, which say nothing a reader here needs and which `PROJECT-STATUS.md`
  replaces. The regression fixtures
  are openly licensed substitutes assembled from development split speakers
  only, so publishing one cannot expose a sealed split.
- **Frozen records are copied unmodified**, and which files are frozen is
  computed rather than listed, because a hand written exemption list goes stale
  the first time a new record is frozen. Of the files the contract selects for
  publication, **68 have their hash pinned by another**, computed on 2026-08-27
  with the builder's own function. A substitution that would have
  fired inside one is reported rather than applied, because a published
  repository whose own integrity checks fail would be worse than one carrying an
  untidy string.

**Where to disagree first**, in the author's own view: the exclusion rule in
section 6.4 is a judgement, not a theorem. A reader who thinks a variety
mismatch can be estimated and subtracted would design this differently, and the
sensitivity family is published in full so that such a reader can see what the
harsher analysis shows without taking this contract's word for anything.

---

## 9. Three defects found while writing this account

All three were found by checking rather than by reading, which is the same
method that produced section 2. They are recorded here rather than quietly
repaired.

**A documentation claim that a default run makes no remote call was false, and
is now corrected.** The private repository's status summary stated that a
default solo run "makes no remote call at all and finishes in about 70 seconds".
The default transcriber is AssemblyAI, so a run with no flags uploads audio to a
paid provider. The claim holds only with `--transcriber local`, a scope the
roadmap stated correctly and the summary had dropped. A real solo run on that
machine with `--transcriber local` and no interpretation layer completed in 88
seconds and made no remote call. The line was corrected on 2026-08-26. It is
recorded here because a project whose central discipline is not carrying figures
forward should say when its own summary did exactly that.

**The runtime figures were scattered across three documents, and none of them
said what it measured.** One recorded "solo 261 seconds against 212 with
AssemblyAI", measured before the interpretation layer became opt in, so it
describes a run that included stages a default run no longer performs. Another
said about 70 seconds. The measured value on 2026-08-26 was 88. Three numbers,
three different things, no conditions attached to any of them.

They were measured again on 2026-08-27 under stated conditions, on the same
machine, on a 141 second solo recording, with no interpretation layer and
nothing else running:

| Path | Wall clock |
|---|---|
| solo, `--transcriber local`, no remote call | 68 seconds |
| solo, `--transcriber assemblyai` | 58 seconds |

The local path costs about ten seconds more than the paid one on this recording,
which is the useful comparison and is much narrower than the older figures
suggest. Treat any of these numbers as a property of one machine on one
recording. The same local run measured 88 seconds a day earlier under the same
flags, which is the honest reason to state conditions rather than to quote a
runtime as though it were a measurement of the software.

**A solo run reports a stage as pending that will never run.** The enrichment
status block initialises the speaker label referee as `pending`. Solo mode never
schedules that stage, so a completed solo `master.json` permanently describes it
as about to happen. This is the same defect that was identified and fixed for
the other two model stages, which correctly report `not_requested`, left behind
for the referee in the one mode that never calls it.

**Closed in `v0.2.1`, on 2026-08-28.** A solo run starts the referee as
`not_requested`, the same word the other two stages already used, and a
conversation run still reports it truthfully. The finding above is left standing
as what was found. What made it worth fixing rather than tolerating is that the
provenance block in the same file already recorded the referee as not invoked in
solo mode, so one `master.json` carried two records of one fact that contradicted
each other.

**Claim type and evidence class are not tied together**, so a language model's
subjective impression can be recorded in the machine readable ledger as a
measured observation. Section 5 sets this out in full, with the claim from a
real run that demonstrates it. It is a specification gap rather than a model
failure: the prompt's own definition of `measured_observation` permits it, and
no check in the verifier refuses it.

**Closed in `v0.2.0`, on 2026-08-28.** A measured observation must now rest on a
computed metric, a turn, a word effect or a pause; a listener perception, a
declared scenario or an inferred one makes the claim an interpretation, and the
verifier refuses anything else as `claim_type_evidence_mismatch`. The finding
above is left standing as what was found. Before the fix, a run on the published
code typed five listener backed claims as measured observations in one report
and verified all of them without an issue. After it, four runs produced no
measured observation resting on anything this pipeline did not measure.

Neither code defect was fixed when this account was written, because it was
written under a documentation only scope and a document that quietly changed the
system it describes would be the wrong kind of honest. Both were fixed
afterwards, in the two releases named above, and the findings are left as they
were found.

---

## 10. What would change the picture

Listed because they are cheap to restart and because naming them is part of
being honest about what is missing.

- **A second phone model with no Common Voice lineage**, rescoring the same
  2,400 clips. This is what would turn the declaration in section 4.1 into a
  resolution. Until then, any future differential running the way the lineage
  bias predicts is uninterpretable.
- **More Australian speakers**, which is harder than it sounds. The eligible
  pool in this corpus is 674 speakers and the probe already samples 45 percent
  of it. The design's minimum detectable difference will not fall much without a
  different source.
- **The newly available references.** Refusing commercial intent released a
  number of non commercial sources, including an Australian reference lexicon
  and large collections of Australian speech. None of them solves section 6.1.
- **Measuring the model instead of the person.** Run several models over the
  same measurement records and publish how often each makes claims the evidence
  does not support. This is the one route by which the claim verification layer
  becomes a finding rather than a component, it has a ready made comparison in
  *Prior over Evidence*, and it has no human subject. **Nothing in this document
  claims that result in advance of doing it.**

---

## 11. Standing conclusions

- Negative results are outputs. A recorded `no_selection` under unchanged gates
  is a completed result, and it does not authorise a weaker gate, more threshold
  searching, or an early look at sealed participants.
- Accuracy and reliability are different. A repeatable measurement can still be
  wrong, and a repeatable *error* is the most dangerous kind, because
  repeatability makes it look like evidence.
- A software snapshot is not independent truth, and agreement between two
  systems is not evidence that either is correct.
- A language model may explain evidence. It may not create measurement truth.
- Missing evidence is never turned into a score. Unavailable is not zero, not a
  pass and not a failure.
- Freeze the analysis before looking at the result, and pay for the multiplicity
  you created by choosing what to look at.
- The most valuable single finding this project produced is that no candidate
  system passed its gates. The second is that its own best result was an
  artifact of its own method, and it found that out by turning the method on
  itself.

---

*Prepared 2026-08-26. Every figure in this document except those in section 7.2,
which come from two external papers and are marked as such, was taken from the
stored evidence records rather than carried forward from earlier prose, because
published figures in this repository have been wrong five times.*

*The draft was then checked against those same records a second time, which was
worth doing: it caught this document quoting the t differential at the
superseded pooled aggregation of +0.0269 inside a sentence about the per speaker
analysis that produced +0.0362, overstating how much of the design was pre
registered, and understating the spread of opposite signed effects around the
consonant it was dismissing. All three are corrected above. A document about a
project that kept finding its own numbers wrong was not going to be the
exception.*
