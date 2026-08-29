# Speech analysis pipeline

**New readers should start with `findings.md`**, the honest account of what was
built, what was measured, what was found, what was retracted, and what could not
be established at all. It is the document that says what this repository
actually demonstrates.

For where the work stands, what is deferred and what was decided against,
read `PROJECT-STATUS.md`. For what this project is and refuses to claim read
`project-purpose.md`. This README is the technical operating reference.

This is an open research project with no monetisation plan. Any prose below that
implies a product, an app or a user is stale text from before the 2026-08-22
direction change and should be reported as a defect.

## What you need before anything runs

- **Python 3.12 or newer.**
- **ffmpeg, and it is not a Python package.** Every run shells out to `ffmpeg`
  and `ffprobe`, from the quality preflight, the pause detector, the diarizer,
  the acoustics stage and the provenance stage. `pip` cannot supply them.
  Install with `brew install ffmpeg` on macOS, `sudo apt install ffmpeg` on
  Debian or Ubuntu, or from <https://ffmpeg.org/download.html> on Windows.
  Check it with `ffmpeg -version`. Without it the preflight stops the run and
  names the missing program.
- **About 6 GB of disk**, mostly model weights fetched on the first run.

Then install the exact tested environment with:

```text
python3 -m pip install -r requirements.txt -c constraints.txt
```

Run the test suite to confirm the installation:

```text
python3 -m unittest discover -s tests -t .
```

That is the whole suite, 1,021 tests. Some skip when optional evidence or
credentials are absent, and the skips are reported rather than hidden.

The pipeline's output is `master.json`: the measurements, the provenance of
every input, the uncertainty beside every number, and an explicit refusal
wherever the evidence was inadequate. A run stops there. The optional language
model interpretation layer, which describes those measurements in prose and
then has its claims verified against them, runs only when you ask for it with
`--interpret`. It produces no score and no rating of anybody.

Run a declared solo recording with:

```text
python3 pipeline/run_all.py --mode solo --audio "regression/fixtures/solo.wav"
```

By default transcription goes to AssemblyAI and needs a paid key. To run with
no paid credentials, add `--transcriber local`, which transcribes on this
machine instead:

```text
python3 pipeline/run_all.py --mode solo --audio "regression/fixtures/solo.wav" --transcriber local
```

There is no fallback between the two paths. A missing key fails the run rather
than quietly switching, because the two do not produce the same evidence and
every record states which produced it. The local path also cannot do two things
the provider path can, and it declares both as unavailable rather than returning
nothing: second voice detection in solo recordings, and the four fluency event
families that need a word level ASR confidence. Conversation mode still needs a
Hugging Face token for diarization; a solo run on the local path needs no
credentials at all. Remember that the default transcriber is AssemblyAI, so a
run with no flags is not the credential free path.
`docs/offline-transcription.md` carries the measurement behind all of this.

On a laptop running on battery, prefix the command with `caffeinate -dimsu`. A
maintenance sleep part way through drops the network and makes the remote
enrichment stages fail for reasons unrelated to the pipeline. Stage durations in
the log are wall clock and include any sleep, while the enrichment deadlines
count only awake time, so a run that slept looks far slower than it was.

Add `--interpret` to also run the listener, the interpretation and the claim
verifier:

```text
python3 pipeline/run_all.py --mode solo --audio "regression/fixtures/solo.wav" --transcriber local --interpret
```

Every run begins with a deterministic audio quality preflight. The default
`--quality-policy lenient` continues usable recordings with explicit signal
warnings. Use `--quality-policy baseline` for a controlled assessment that must
reject signal conditions which would invalidate its measurements. Audio over
30 minutes is rejected unless `--long-ok` is supplied. When `/audio` contains
more than one supported file, select one explicitly with `--audio`.

The threshold set is versioned as `generated-fixtures-1.0.0`. It is an
operational starting point verified with generated audio, not scientific
validation and not a normative definition of a good voice.

The preflight writes 14 checks into `audio_quality.json`, and all 14 are listed
below. A healthy run writes all 14. A run that stops early writes fewer, because
three of the checks can end the run where they stand: an unreadable file, an
unusable duration, and audio that will not decode. An unreadable file writes 1
check and stops. Audio under five seconds writes 2 and stops.

Two of the 14 have no boundary to fail against. `codec_support` records which
codec actually decoded, and `background_speech_preflight` is always deferred to
the later solo check, so both always report `pass` once they are reached.

| Check | Provisional boundary | Meaning |
|------|----------------------|---------|
| `file_readability` | a readable audio stream | No readable stream stops the run under both policies |
| `duration` | 5 seconds to 30 minutes | Shorter audio stops; longer audio needs `--long-ok` |
| `sample_rate` | at least 16 kHz | Lower rates limit timing and acoustic evidence |
| `channel_handling` | 1 or 2 channels | More channels are downmixed to mono and may hide a per channel problem |
| `decoded_audio` | nonempty, framable samples | Audio that will not decode stops the run under both policies |
| `codec_support` | decodable by the installed ffmpeg | Records the codec that actually decoded, no threshold |
| `clipping` | less than 0.1 percent of samples | More clipping limits loudness, pitch, and voice quality |
| `peak_level` | between minus 45 and minus 0.5 dBFS | Flags very quiet or nearly saturated input according to policy |
| `rms_and_near_silence` | above minus 35 dBFS | Lower levels warn; minus 60 dBFS is treated as near silence |
| `rms_and_near_silence` | near silent frames under 98 percent | Almost entirely silent input stops |
| `speech_proportion` | at least 10 percent | Adaptive frame energy proxy, not speaker detection |
| `signal_to_noise_proxy` | at least 12 dB | Difference between high and low frame energy, not calibrated SNR |
| `recording_level_stability` | no more than 12 dB active frame spread | Flags strongly changing recording level; unavailable under 10 active frames |
| `reverberation_risk_proxy` | no more than 0.60 tail ratio | Flags persistent energy after clear speech offsets; unavailable under 3 clear offsets |
| `background_speech_preflight` | none, always deferred | A waveform cannot identify another speaker, so solo mode checks this after transcription |

The RMS level and the near silent frame ratio share the single
`rms_and_near_silence` check, which is why the table has 15 rows for 14 checks.
They are listed apart because they behave differently: a low level warns, and
near silence stops the run.

Signal problems warn and continue under `lenient`; the same problems fail a
controlled `baseline`. Broken, unreadable, effectively silent, too short, and
unapproved long inputs stop under both policies. Background speakers cannot be
identified reliably from a deterministic waveform preflight, so solo mode
retains its later transcription provider contamination check.

Every `master.json` also contains `measurement_metadata` beside the unchanged
`computed_metrics`. Before a number is used, this record says where it came
from, whether enough evidence exists, its quality, known warnings and
confounders, and the algorithm and threshold versions. An old numeric value may
remain for compatibility while its metadata says `unavailable`; evaluators and
progress tracking must then ignore it rather than treating it as zero.

There are 10 minimum evidence rules in `pipeline/measurement_evidence.py`, and
all 10 are listed below. They cover the 24 metrics defined in the same file.
Rates and language patterns share one rule, so the table has 9 rows.

| Measurement family | Minimum evidence |
|------|------|
| Basic word and time totals | 1 word and 0.5 seconds of attributed speech |
| Rates and basic language patterns | 20 words and 10 seconds of attributed speech |
| Vocabulary variety | 50 words and 20 seconds of attributed speech |
| Speaker pitch | 5 confidently attributed pitch observations |
| Loudness events | 5 acoustic timeline points |
| Turn measures | 3 attributed turns |
| Average response pause | 2 response opportunities |
| Voice quality | 3 seconds of analysed speech |
| Pronoun balance ratio | 20 words and at least 1 second person word |

These rules are versioned generated fixture safeguards, not validated norms.
[AssemblyAI documents word confidence](https://www.assemblyai.com/docs/pre-recorded-audio/guides/detecting-low-confidence-words)
on a 0 to 1 scale and leaves the cutoff to each application. This pipeline
visibly flags words below the provisional 0.50 cutoff. The cutoff is not
calibrated accuracy and must be evaluated later against independently corrected
transcripts.

## The optional interpretation layer

`--interpret` adds three stages: the listener, the interpretation, and the
claim verifier. Without it none of them run and none of their files are
produced.

The interpretation describes what was measured. It does not rate, score, rank
or grade anybody, it has no persona, and it prescribes nothing. Five language
model scores of a person, CLARITY, WIT, WARMTH, PRESENCE and STORY, were
deleted on 2026-08-24: they were model output parsed by regular expression
against hand written anchors, never validated as measurement scales, and aimed
at an audience this project states it does not have.

`evaluation.md` opens with a run record written by the pipeline from
`master.json`, not by the model: recording conditions, audio quality warnings
and their consequences, enrichment outcome, and every measurement withheld from
the interpretation with the reason. Availability is a deterministic fact about
the run, so code reports it rather than asking a model to report on itself. The
block is delimited by HTML comments and excluded from claim checking, because
verifying it against `master.json` would verify the renderer against itself.

Below it, every statement the model makes ends with a claim marker such as
`[C003]`. The machine readable records live in `evaluation_claims.json`, where
each claim is labelled a measured observation, an interpretation or a screening
hypothesis, and points to exact evidence. There is no claim type that may exist
without evidence: the prescription type, which existed so the report could tell
a person what to practise, was withdrawn with the scores. `verification.json`
independently checks those links and `verification.md` gives a human summary.
The checks cover path existence, speaker ownership, turn and timestamp
containment, measurement availability and quality, exact numeric values, and
signed direction. They also cover the claim's own type: only a computed
metric, a turn, a word effect or a pause may support a measured observation,
so a listener's impression of how somebody sounded is an interpretation
however plainly it is stated, and so is anything resting on the setting. Until
2026-08-28 nothing tied the two together, and a real run typed a listener's
impression as a measurement. Unavailable and low quality legacy values remain in
`master.json` for auditing but are replaced with `null` in the temporary
model input and omitted from its allowed evidence catalog.

**What verification does not demonstrate, and the report says so itself.** With
the scores gone, the model's numeric claims are largely restatements of values
it was handed, so a clean report mostly shows that a copy operation copied
correctly. Verification is only as interesting as the model's freedom to be
wrong. In production it has never rejected a claim; the only demonstrated catch
is a synthetic case in the regression harness. The failure that matters most,
an interpretation the evidence does not support, carries no arithmetic at all,
so nothing in the verifier can detect it.

The three remote enrichment stages, referee, listener and evaluator, may safely
become unavailable. Each retries once and then records an explicit status and
error category in `master.json`, leaving every objective artifact intact.
Enrichment is bounded in time as well: the provider client aborts its own
request after `ENRICHMENT_REQUEST_TIMEOUT_S`, and an outer deadline of
`ENRICHMENT_ATTEMPT_DEADLINE_S` in `pipeline/llm_contract.py` catches anything
the client cannot see, so a request that never returns becomes a `timeout` and
degrades rather than stalling the run. Both count awake time rather than time on
the wall, so a stage that slept reports a longer duration than its deadline. Transcription is load
bearing and is deliberately not covered by this: it must fail the run instead.

Run the isolated regression harness with:

```text
python3 -m regression.run --synthetic-only
```

The harness keeps three kinds of evidence separate. Unit tests protect local
rules. The replaceable software snapshot detects changed behaviour but is not
truth. Files under `regression/truth` contain independent reference facts with
their source, annotator role, guide version, date, adjudication status, and
coverage. `--bless` can replace only the software snapshot; it cannot create or
change truth labels. The generated controls cover clean, noisy, loud, quiet,
fast, slow, monotone, overlap, backchannel, pause, renderer, and verification
cases. Real recording truth is intentionally limited to facts the repository
owner declared independently of the pipeline.

To evaluate isolated real runs, supply their artifact directories explicitly:

```text
python3 -m regression.run \
  --artifact real_conversation=CONVERSATION_OUTPUT \
  --artifact real_solo=SOLO_OUTPUT \
  --report-dir REGRESSION_REPORT_OUTPUT
```

Run the reliability and fairness audit only against isolated completed outputs:

```text
python3 -m reliability.run \
  --repeat-output first=FIRST_OUTPUT \
  --repeat-output second=SECOND_OUTPUT \
  --encoding-output original=ORIGINAL_OUTPUT \
  --encoding-output converted=CONVERTED_OUTPUT \
  --artifact conversation=CONVERSATION_OUTPUT \
  --report-dir AUDIT_REPORT_OUTPUT
```

`reliability_fairness.json` is the machine readable result and
`reliability_fairness.md` is the short report. An exact mismatch in a
deterministic stage fails the audit. Remote transcript differences are reported
as pairwise disagreement, not as error, because neither transcript is truth.

Every measurement is currently labelled experimental for personal progress.
The pipeline has no suitable repeated same person study from which to estimate
measurement error, natural variation or meaningful change, so `progress.md`
does not trend delivery metrics. The old generic five percent trend rule has
been removed, and the five language model scores it once also trended were
deleted on 2026-08-24. This does not prevent describing a single recording. It
prevents an unproven difference from being called personal improvement.

Fairness results remain `not_evaluated` until independently labelled data from
enough independent participants covers the intended languages, accents, ages,
voice ranges, devices, audio conditions, and speech differences. Missing group
results never mean equal performance. Participant metadata is counted only
when its source and consent for the fairness audit are recorded. The current
release gates block ranking, screening, and high stakes decisions. The
statistical separation of reliability and measurement error follows the current
[COSMIN guidance](https://www.cosmin.nl/wp-content/uploads/COSMIN-manual-V2_final.pdf),
while the requirement for representative evaluation and documented fairness
results follows the [NIST AI Risk Management Framework](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/).

Validate the task aware voice and prosody contract with:

```text
python3 -m voice_prosody.validate
```

The acoustic stage now writes an additive `voice_prosody` section in
`acoustics.json`. Its primary evidence is a 10 ms timestamped contour containing
F0 or null, pitch strength, digital recorder level in dBFS, speaker, contiguous
region and quality flags. Per speaker summaries contain robust F0 percentiles,
a semitone distribution span, recorder level percentiles, sample counts,
diagnostics and an availability state. A two pass adaptive pitch tracker and
explicit octave error gates prevent suspicious contour tails from silently
becoming ordinary values.

These are low level observations, not a voice or prosody score. F0 is not
perceived pitch, dBFS is not calibrated vocal loudness, and a percentile span
is not expressiveness or monotonicity. Context free solo runs are labelled
`unknown_ad_hoc` and noncomparable. Conversation evidence uses exclusive
per speaker regions and excludes overlap and region edges. CPPS is research
only. Jitter and shimmer require the versioned sustained vowel task, separate
research consent and three valid repetitions; they remain unavailable to the
interpretation. Personal progress, cross device comparison, ranking, screening,
diagnosis and every combined index remain blocked.

The two owner recordings provide functional integration evidence only. They do
not validate acoustic accuracy, device equivalence, fairness, task meaning or
personal change. The full research and release programme is documented in
`voice_prosody/research-and-protocol.md`.

Validate the timestamped speech event candidate contract with:

```text
python3 -m fluency_events.validate
```

After final speaker attribution, the pipeline now writes the separate
`fluency_events.json` artifact. It may contain timestamped review candidates
for sound or syllable repetition, unclassified whole word repetition,
prolonged sound and phrase repetition context. Every candidate preserves its
transcript or alignment source, alternative explanations, uncertainty and an
`unreviewed` state. Whole word syllable class is manual, and possible block
automation is unavailable because silence alone cannot establish a block.

These are engineering candidates, not confirmed stuttering events. Candidate
absence does not establish fluent speech. The artifact is excluded from the
listener, the interpretation, the claim ledger, history and progress, and it
does not create a released rate, severity score, screening result or diagnosis.
Structured review packets can confirm, reject, relabel or add observable
events while retaining reviewer role and disagreement; one review never
becomes reference truth. No new API is used. The research, annotation and held
out validation programme is documented in
`fluency_events/research-and-protocol.md`.

Apply a prepared structured review packet without overwriting the original:

```text
python3 -m fluency_events.review fluency_events.json REVIEW_PACKET.json \
  --output fluency_events_reviewed.json
```

Validate the versioned onboarding assessment blueprint with:

```text
python3 -m assessment.validate
```

Validate the separate controlled pronunciation and intelligibility research
contract with:

```text
python3 -m assessment.validate_pronunciation
```

## Speech sound patterns

This is release locked developer engineering. It has no pipeline stage, no
artifact in `master.json`, no detector, no score and no released output, and
nothing it produced may reach the interpretation, progress, screening or
diagnosis. Its
contract defines how future work must keep source audio, intended words, blind
listener records, blind human production transcriptions, reviewed legitimate
accent and dialect variants, ASR outputs and adjudication separate. ASR
disagreement cannot create a speech sound concern, one opportunity cannot create
a phonological pattern, and unresolved language or variety forms remain
unscorable.

**Two frozen comparisons and a closed selection record all recorded
`no_selection`.** No candidate system or threshold was selected, nothing is
frozen forward, and no paid provider added value beyond the free local stack.
Checkpoint 22E6 then corrected the evidence record after an open search disproved
claims this repository stated as fact, most importantly the Bookbot lane's
Australian training source: WikiPron defines English with two dialects only, UK
and US, so the dataset that model's name advertises does not exist.

**Checkpoint 22E7 acquired the openly licensed reference stack and the comparison
accent groups, and measured nothing.** Four pronunciation lexicons and four
Common Voice accent subsets are held, each with a licence snapshot, a size and
digest matching its publisher, a declared role and its prohibited uses. The
checkpoint acquired three of those four subsets. The Australian one was already
held, hashed and split on 2026-07-21, so it was rechecked rather than fetched
again. The four subsets form three accent groups, because the American group is
built from a male and a female subset and neither may stand alone. Two findings
from it bind later work. The British reference is the Montreal Forced
Aligner English (UK) dictionary rather than the WikiPron scrape the plan assumed,
because the scrape is 6.85 percent post-vocalic rhotic against the dictionary's
0.01 percent. And most published figures the checkpoint checked were wrong,
including two this repository had recorded itself, so every count in those
manifests is generated from the acquired bytes and a test rebuilds them byte for
byte.

`speech_sound_patterns/engineering-plan.md` is the authority. It holds every
checkpoint's brief, numbers, acceptance evidence and limitations, and the
acquisition and account register. The reasoning behind the constructs and the
variety safeguards is in `speech_sound_patterns/research-and-protocol.md`.

Committed artifacts, all under `speech_sound_patterns/`, each beside the
contract that was frozen before it ran:

| Artifact | What it holds |
|---|---|
| `local-feasibility-v1.0.0.json` | Pinned MFA, PhoneticXEUS and PanPhon environments fit this machine and repeat. |
| `local-research-feasibility-v1.0.0.json` | Segmentation-free GOP, POWSM and CommonPhone repeat exactly on label-blind clips. |
| `local-benchmark-v1.0.0.json` | The frozen local stack measured on development and tuning participants only. |
| `local-benchmark-repair-v1.0.0.json` | The label-blind repair. Its closest point passed nine of ten checks and still selected nothing. |
| `external-schema-smoke-v1.0.0.json` | Field presence, repeatability and outcomes from the only real external requests. |
| `frozen-comparison-v1.0.0.json` | Every eligible lane against the unchanged gates on 480 frozen clips. `no_selection`. |
| `frozen-comparison-v1.1.0.json` | The same, replicated on every non held out adult. `no_selection` again. |
| `selection-record-v1.1.0.json` | A verdict, reason, incremental value, six limitation classes and reopening conditions for all fourteen lanes. |
| `provider_register/provider-register-v1.2.0.json` | The fail-closed authority on what each lane may be, and the standing owner decisions. |
| `variety-probe-v1.0.0.json` | The reference variety probe. Its central prediction failed and is recorded as failed. |
| `research-prompt-pack-v1.0.0.json` | Twenty chosen words and the consonant opportunities in them. Not reviewed, not active, not a validated pack. |
| `candidate-evidence-v1.0.0.json` | The task-matched adequacy audit and its no-rule decision. It contains safe aggregates only. |
| `final-evidence-v1.0.0.json` | Final no-selection acceptance, 40 explicitly unavailable held-out measures and the normal-pipeline regression result. |
| `repository-closure-v1.0.0.json` | The immutable post-report repository snapshot. Its valid presence is the mechanical item 22 completion record. |
| `corpus_manifests/` | Licence, provenance, split and role for all 22 sources, and the corpus to provider transfer review. |

Raw audio, labels, logits, alignments, provider responses, threshold grids and
per participant rows stay private under `.research_data`. Earlier versions of any
contract, report, register or record stay on disk byte-for-byte unedited and
remain loadable as historical records. The active version-specific validator
validates the active contract. The 26 sealed held-out adults and 24 sealed
held-out children have never been read for checkpoint 22H.

Checkpoint 22G is committed. It added `candidate-artifact-contract-v1.0.0.json`,
the safe aggregate `candidate-evidence-v1.0.0.json`,
`research-contract-v1.6.0.json`, and the private offline evidence assembler.
Checkpoint 22H adds the frozen final acceptance contract, the safe aggregate
final evidence, research contract version 1.7 and the post-report repository
closure. `research-contract-v1.7.0.json` is the active contract, loaded by
`speech_sound_patterns/contract.py`. No private candidate or acceptance artifact
is committed.

**Audio leaves this machine in exactly one place.** Checkpoint 22E3 sent public
research corpus audio to Azure, and nothing else has ever been sent. Adam's own
recordings never leave, and that exclusion is written into the review rather than
assumed. Two documents gate every request: the corpus to provider transfer review
at `speech_sound_patterns/corpus_manifests/provider-transfer-review-v1.2.0.json`,
which decides one named corpus and one named provider at a time, and the
predeclared `speech_sound_patterns/external-smoke-contract-v1.0.0.json`. A pair
that is not reviewed is prohibited.

Validate everything without sending anything or running a model:

```text
python3 -m speech_sound_patterns.validate
python3 -m speech_sound_patterns.validate_corpora
python3 -m speech_sound_patterns.validate_benchmark
python3 -m speech_sound_patterns.validate_comparison
python3 -m speech_sound_patterns.validate_selection
python3 -m speech_sound_patterns.validate_variety_probe
python3 -m speech_sound_patterns.validate_prompt_pack
python3 -m speech_sound_patterns.validate_candidates
python3 -m speech_sound_patterns.validate_final_acceptance
```

Inspect the external gates and the planned requests, still without sending:

```text
python3 -m speech_sound_patterns.azure_smoke --dry-run
```

Running it without `--dry-run` sends audio and needs a fresh owner decision.
`--summarize-from PATH` rebuilds the smoke report from retained responses
instead of sending anything again. `comparison_azure` refuses to run at all,
`--dry-run` included, while completed Azure comparison evidence exists, so the
committed comparison cannot be overwritten by an accidental rerun.

**Checkpoint 22E8 measured the reference variety probe, and its headline
prediction failed.** Across 2,400 clips from 1,200 speakers in four accent
groups, the American reference did not flag Australian speakers more often than
American speakers at group level, and that is recorded as a wrong prediction
rather than reinterpreted. It did flag British speakers more, and the repaired
reference halved that. On the two consonants where the varieties genuinely
differ, the rhotic and `t`, Australian speakers were flagged about three points
more often under the American reference and the gap collapses under the repaired
one, so the hypothesis was sound and the group mean was too diluted to see it.
The repaired reference lowers flag rates in every group, including the American
control, because a non-rhotic reference stops expecting a coda r for everybody.
That removes false concerns by declining to score them; it is not evidence that
the system is now fairer to Australian speakers, and no such claim is made.

**Checkpoint 22F built the conservative research prompt pack.** Twenty chosen
English words carry 62 consonant opportunities, 61 scorable and 1 refused,
probing 21 consonants of which 20 reach two or more word positions. Every word
carries a British broad transcription in the Montreal Forced Aligner English (UK)
dictionary and an Australian tagged Wiktionary pronunciation, no target is
machine generated, and where the two varieties genuinely differ the opportunity
is unscorable rather than corrected. The post-vocalic rhotic rule refuses nothing
anywhere in the eligible pool, because under a non-rhotic British reference that
opportunity does not exist to be refused, which is the checkpoint 22E8 mechanism
seen from the other side. **This is not a reviewed onboarding word pack**,
which is still empty and still awaiting professional review; the pack validator
reads that file and fails if it ever stops being true. Build and check it with:

```text
python3 -m speech_sound_patterns.build_prompt_pack --check
```

The derived lexicon stays server side. The committed pack carries the words and
their consonant opportunities; the verbatim forms, the vowels and the whole
eligible pool are written to gitignored storage, because Wiktionary derived
material is share alike and share alike attaches on distribution.
`speech_sound_patterns/prompt-pack-runbook.md` explains the rest.

**Checkpoint 22G assembles evidence and selects nothing.** The permitted
development and tuning evidence is not the controlled isolated-word task, no
adult participant supplies two different prompt-pack words, and the exact
produced feature-relation truth needed for a rule does not exist. The adequacy
gate therefore stopped before threshold or repeated-rule search. The assembler
preserves raw proposals, conflicts, unavailable evidence, unsupported contexts
and reference variants, but the current contract cannot emit a possible relation
or repeated relation.

The command is deliberately offline, explicit and private:

```text
SPEECH_SOUND_OFFLINE=1 python3 -m speech_sound_patterns.extract_candidates \
  --manifest .research_data/speech_sound_patterns/candidates/manifests/MANIFEST.json \
  --output-dir .research_data/speech_sound_patterns/candidates/NEW_OUTPUT \
  --acknowledge-developer-only
```

It never overwrites an output, never enters the normal pipeline, and accepts only
exact synthetic structural fixtures or Adam recordings used for local functional
integration. A real recording and its evidence must be checksum bound inside the
private research root. `speech_sound_patterns/candidate-extractor-runbook.md`
documents the manifest and validation procedure.

**Checkpoint 22H closes engineering without inventing held-out performance.**
No system, mapping, feature rule, provider configuration, threshold or repeated
minimum qualified in the earlier work, so there was no eligible method to test.
Adam approved keeping the held-out evidence sealed on 2026-08-12. The final
report therefore records every one of its 40 predeclared held-out measures as
`unavailable`, with no numerator, denominator, value, interval or gate result.
That is not zero, a pass or a failure.

The real two-speaker conversation pipeline also ran in a new isolated directory
under `caffeinate`, without `--me`. All 14 stages completed, the independent
regression checks passed, the listener and referee completed, and the evaluator
used its existing safe unavailable state after two semantically invalid drafts.
No speech-sound module, artifact, key or content leaked into the ordinary
pipeline, and personal history, progress and the existing root output were
unchanged. No task-matched controlled written-word owner recording exists, so
owner integration is explicitly unavailable rather than replaced with ordinary
solo, conversation or accent-sentence audio.

Validate the complete public result with the acceptance interpreter:

```text
python3 \
  -m speech_sound_patterns.validate_final_acceptance
```

The validator requires `repository-closure-v1.0.0.json`. The closure binds the
final contract, aggregate report, active research contract, tests and the full
post-report public repository while excluding only itself. If that file is
absent or validation fails, item 22 is not complete. The private rebuild and
one-time finalizer commands are documented in
`speech_sound_patterns/final-acceptance-runbook.md`. This is engineering closure
only: detector accuracy, Australian English correctness, population validity,
fairness, clinical validity and every scientific release remain unestablished
and locked.

The closure is a historical snapshot, not a command to prevent every later
roadmap commit. Once the repository advances, validation finds the ancestor
commit containing the exact unchanged closure and reconstructs that Git tree.
The historical digest and file count must still match; the closure JSON is never
overwritten. This preserves item 22 while allowing later approved work.

Reacquire and reprove the open reference stack, which downloads but measures
nothing. `speech_sound_patterns/open-stack-runbook.md` explains every step and
the evidence behind the checkpoint's one real choice:

```text
python3 -m speech_sound_patterns.acquire_open_stack --all
python3 -m speech_sound_patterns.build_open_stack_manifests
python3 -m speech_sound_patterns.validate_corpora --verify-private --rehash-archives
```

```text
python3 -m unittest tests.test_speech_sound_feasibility
python3 -m unittest tests.test_speech_sound_benchmark
python3 -m unittest tests.test_speech_sound_benchmark_repair
python3 -m unittest tests.test_speech_sound_corpus_manifests
python3 -m unittest tests.test_speech_sound_provider_register
python3 -m unittest tests.test_speech_sound_external_smoke
python3 -m unittest tests.test_speech_sound_comparison
python3 -m unittest tests.test_speech_sound_powered_sample
python3 -m unittest tests.test_speech_sound_selection_record
python3 -m unittest tests.test_speech_sound_variety_probe
python3 -m unittest tests.test_speech_sound_prompt_pack
python3 -m unittest tests.test_speech_sound_candidates
python3 -m unittest tests.test_speech_sound_final_acceptance
```

Those tests do more than check shapes. The powered truth extractor must
reproduce all 5,478 committed checkpoint 22D relation rows before it may write
anything; one test rebuilds the entire committed checkpoint 22E4 report through
the current version aware code and requires an exact match; another rebuilds each
selection record version byte for byte from its own evidence. A metric,
alignment, abstention, denominator or verdict therefore cannot drift unnoticed.

Private reproduction procedures, none of which are needed to read the committed
evidence, are in `speech_sound_patterns/feasibility-runbook.md`,
`benchmark-runbook.md`, `external-smoke-runbook.md`, `comparison-runbook.md`,
`selection-record-runbook.md`, `open-stack-runbook.md`, `variety-probe-runbook.md`
`prompt-pack-runbook.md`, `candidate-extractor-runbook.md` and
`final-acceptance-runbook.md`.

## Motor speech and voice evidence

Checkpoint 23A's evidence review, engineering plan and repository acceptance are
complete in the working tree. It adds no
runtime package, recording task, detector, score, threshold, provider call or
ordinary pipeline output. Validate the existing pipeline with its existing
commands; there is no item 23 command to run.

For this repository's currently undefined intended use, the review does not
justify a general motor speech detector or automatic voice health screen from an
ordinary recording. It leaves a tightly controlled rapid-syllable research
question for independent professionals and people with lived experience to
accept or reject. No task or protocol is selected and the onboarding task remains
locked. Controlled connected-speech timing, unfamiliar-listener intelligibility,
participant report and the existing item 20 voice primitives answer separate
questions and cannot be combined into one score or used to infer cause,
disorder, severity or diagnosis.

Redenlab was investigated from public sources as a possible Australian adviser
or vendor. It was not contacted or selected and is not an independent clinical,
ethics, regulatory or truth authority.

Adam approved checkpoint 23B planning with adults first on 2026-08-14. The
public governance package and machine-checkable contract keep motor speech,
voice, participant report, controlled intelligibility and clinical reference as
independent unselected lanes. The legal sponsor and every external authority
remain unresolved. Nobody has been contacted and all participant work, data
use, spending, implementation and external transfer remain unapproved.

Validate that state with:

```text
python3 -m motor_speech_voice.validate_governance
```

On 2026-08-19 Adam confirmed there is no legal entity behind the project and no
institutional or clinical connection, and approved a research only route that
contacts nobody. The candidate reference source survey records what public
sources could supply the independent human reference evidence item 23 needs,
what they may lawfully be used for, and whether they can be obtained at all.
It covers 27 sources across rapid syllable task timing and accuracy, perceptual
voice judgement and unfamiliar listener intelligibility. It selects no source,
acquires nothing and authorises no acquisition, and its schema cannot express
that a source meets an item 23 truth requirement, because that judgement belongs
to the independent governance roles.

Validate it with:

```text
python3 -m motor_speech_voice.validate_source_survey
```

Rebuild it from the recorded findings with:

```text
python3 -m motor_speech_voice.build_source_survey
```

The same research only route then produced the two remaining deliverables public
research could reach, and a ledger recording that everything else needs a person.

The measurement and sampling input package records, once for each of the twelve
provisional constructs, what a future study would estimate, what variation a
design would have to separate, which inputs only an independent statistician can
supply and why, and what blocks the question today. It is not a statistical plan
and structurally cannot become one: a record may contain no JSON number at all,
and the computed sample size is typed null in its schema.

```text
python3 -m motor_speech_voice.validate_measurement_plan
python3 -m motor_speech_voice.build_measurement_plan
```

The documented Australian regulatory and privacy reading reads sixteen questions
against public primary sources along a three rung intended purpose ladder:
firewalled developer research, hypothetical consumer coaching, and a hypothetical
consumer feature suggesting professional assessment. Only the first rung is
occupied. Every record quotes the operative wording, records when it was read,
names what it could not settle and names the accountable human role that must
settle it. It is a reading by a non lawyer and is never advice, a determination
or an approval.

```text
python3 -m motor_speech_voice.validate_regulatory_reading
python3 -m motor_speech_voice.build_regulatory_reading
```

The deliverable ledger records all thirteen of checkpoint 23B's requirements as
two complete, three advanced but unfinished and eight blocked on a named human
role, so a large body of honest public research cannot be mistaken for progress
toward acceptance.

```text
python3 -m motor_speech_voice.validate_checkpoint_ledger
python3 -m motor_speech_voice.build_checkpoint_ledger
```

The full evidence review, source list, Australian safety and governance
boundaries, candidate and deferral register, truth architecture, source survey
findings, measurement input package, regulatory and privacy reading, deliverable
ledger and ordered 23B through 23F acceptance plan are in
`motor_speech_voice/engineering-plan.md`.
The active decision package and safe evidence-handling procedure are in
`motor_speech_voice/governance-review-package.md` and
`motor_speech_voice/governance-runbook.md`. Blank records for future human role,
conflict, intended-use, institution, privacy, statistical, regulatory and lane
decisions are in `motor_speech_voice/governance-record-templates.md`; none is an
approval. `motor_speech_voice/final_decision.py` defines, but does not create,
the fail-closed final 23B decision shape. It requires one accountable owner,
separate controlling organisations, exact signed-artifact and evidence-node
hashes, exact lane scopes and a closed dependency chain to an owner-issued
overall decision. Private signatures and professional substance still require
authorised human verification.

## Backend contracts

Validate the future backend account, session, task, context, consent, export,
and deletion contract with:

```text
python3 -m data_model.validate
python3 -m data_model.validate data_model/session-context-example-v1.0.0.json
```

The data model is a versioned contract, not a database or a service API. A
context aware run may pass `--session-context CONTEXT_PATH`. The runner
stores the validated snapshot as `session_context.json` and places its stable
account, session, context, attempt, recording references and canonical hash in
provenance. Context-free developer runs continue to work.

Validate the personal baseline and meaningful change protocol with:

```text
python3 -m progress_model.validate
```

The production reliability registry intentionally releases zero speech
metrics. A future metric needs its own comparable conditions, repeated human
production evidence, individual measurement error, natural variation, user
relevant meaningful change boundary and independent evaluation. The backend
keeps baseline status, speech change, user reports, real world outcomes,
practice, mastery and run quality separate. Synthetic tests exercise the
future calculation without supplying a production threshold.

The manifest in `assessment/manifest-v1.1.0.json` defines a roughly ten minute
English solo session containing context and consent, a recording check, a fixed
reading or spoken alternative, natural speech, a goal-specific response, a
short repeat and self reflection. It has no backend age gate and uses no age
norms. It schedules and limits future work; it does not record audio or provide any
interface.

Every task declares its purpose, prompt version, expected text where relevant,
duration, preparation, audio quality policy, candidate measurements,
accommodations, retry rules, stop conditions and valid comparisons. Current
measurements remain blocked from progress. Optional sustained voice and repeated
phrase probes require separate research consent and cannot affect the
released interpretation.
Rapid syllable and pronunciation tasks remain locked. The evidence and design
decisions for onboarding are documented in
`assessment/research-and-protocol.md`. The pronunciation research method,
human reference rules, provider comparison and release blocks are documented
in `assessment/pronunciation-research-and-protocol.md`. It contains no active
word pack, selected provider or user-facing pronunciation measurement.

Solo mode always assigns the account holder to `SPEAKER_00`. It uses Silero
speech activity instead of pyannote speaker diarization and skips the Gemini
referee. If the transcription provider detects multiple speaker clusters, the
report contains a contamination warning.

`SPEAKER_00` is local to one recording and is never durable identity. A history
write using `--me` now also requires `--session-context`; its stable account and
communication context scope prevent unrelated people or goals from being
silently compared. Existing personal history files are not migrated or
rewritten automatically. The context must explicitly label the attempt as
baseline collection, a change check, practice, retention or transfer. The
backend never guesses this from recording order.

Run a conversation recording with:

```text
python3 pipeline/run_all.py --mode conversation --speakers 2 --audio "regression/fixtures/conversation.wav"
```

Leave `--audio` out and the runner reads whichever single recording sits in
`audio/`. That is convenient on a machine that has one and an error on a fresh
copy of this repository, which publishes no audio. Conversation mode also needs
a Hugging Face token for diarization, so it is not the credential free path.

`--mode auto` remains the command line default for compatibility. Declaring
`--speakers 1` with auto selects the solo path; otherwise auto retains the
conversation analysis path. Callers should explicitly choose solo or
conversation mode.

## Pipeline version policy

The maintained version lives in `pipeline/pipeline_config.py`. Before version
1.0, the pipeline uses semantic versioning with these rules:

- Increase the major version for incompatible artifact or measurement meaning
  changes.
- Increase the minor version for additive fields, new stages, model changes,
  prompt changes, or intended measurement behavior changes.
- Increase the patch version for fixes that do not intentionally change
  measurement meaning or output compatibility.

Prompt and response schema versions are maintained beside the pipeline version
and must change whenever their corresponding contract changes. Each run stores
the pipeline version, exact active source hash, dependency versions, prompt and
schema versions, model identifiers, input hash, audio properties, and stage
runtime in `output/run_manifest.json` and `master.json`.
