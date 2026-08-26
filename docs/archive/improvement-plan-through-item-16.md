# Archived Speech Analysis Pipeline Improvement Plan Through Item 16

This is the complete historical plan preserved after Phase A and Item 16 were
finished. It contains the original work descriptions, acceptance evidence, and
research list. It is not the live work queue. Use `improvement-plan.md` for
current instructions.

This document is the implementation specification and ordered work queue for
the speech analysis engine. Read `AGENTS.md` before changing anything. Its
workflow agreement is binding. Read `project-purpose.md` for the product intent;
this plan remains the authority for implementation order and acceptance.

The engine is intended to become the measurement core of a communication
coaching application. The first product path is primarily one person recording
themselves for a concrete goal such as a university demonstration, spoken
exam, interview, presentation, date, or confidence practice. An optional
conversation path may later analyse an uploaded recording containing the user
and another consenting speaker.

Longer term, the same foundation may support carefully validated screening and
practice for speech differences or disorders. That ambition changes the
engineering standard now: the pipeline must preserve uncertainty, distinguish
observation from interpretation, work across different voices and recording
conditions, and be testable against truth that did not come from the pipeline
itself.

---

## Status, updated 2026-07-19

### Completed foundation

| Work | Status |
|------|--------|
| 1. Deterministic language metrics | DONE |
| 2. Word boundary clipping | DONE |
| 3. Prototype history and progress layer | DONE |
| 4. Verifier upgrades | DONE |
| 5. WhisperX transcript cross check | REMOVED by owner |

### Active work queue

Phase A is a hard gate. Do not begin Phase B, add new clinical style metrics,
or design the application UI until every Phase A item and its exit gate pass.

| Work | Status |
|------|--------|
| 6. Gemini structured outputs | DONE |
| 7. LLM failure contracts and enrichment status | DONE |
| 8. Explicit inputs and isolated run outputs | DONE |
| 9. Reproducible execution and provenance | DONE |
| 10. Solo first execution path | DONE |
| 11. Audio quality gate | DONE |
| 12. Measurement evidence and uncertainty | DONE |
| 13. Evidence linked evaluation and verification | DONE |
| 14. Truth labelled regression harness | DONE |
| 15. Reliability and fairness audit | DONE |

### Phase B approved work

| Work | Status |
|------|--------|
| 16. Assessment task manifest | DONE |

Item 17 remains a roadmap commitment and needs separate owner approval before
implementation.

Later phases are roadmap commitments, not permission to implement them. Each
must receive a detailed evidence review and owner approval after Phase A.

---

## 1. Product and measurement boundaries

### 1.1 Product modes

The eventual product has three related but distinct purposes:

1. **Performance coaching:** preparation for a specific event or conversation.
2. **Longitudinal growth:** communication confidence and skill development over
   repeated sessions.
3. **Speech support:** condition specific screening, practice, and progress
   measurement, introduced only after appropriate validation.

These modes may share low level measurements, but they must not share
unqualified interpretations. A pause can reflect planning, emphasis, anxiety,
a language difference, a motor speech difficulty, or recording failure. The
system records what happened first and interprets it only with relevant
context and evidence.

### 1.2 Recording modes

- **Solo is the primary product path.** The account holder is always
  `SPEAKER_00`. Onboarding and most practice recordings expect one voice.
- **Conversation is optional.** It retains diarization, attribution, inline
  backchannels, and the Gemini referee. It must be explicitly selected by the
  product rather than silently inferred for high stakes analysis.
- **Auto detection is developer convenience only.** It may remain available in
  the command line, but production sessions must declare their intended mode.
- A solo assessment that contains a sustained second voice is contaminated. It
  must warn or request a new recording rather than quietly treating the other
  person as the user.

### 1.3 Levels of claim

Every future output belongs to one of these levels:

1. **Measured observation:** directly computed from audio or transcript, such
   as five sound repetitions or a 1.2 second pause.
2. **Coaching interpretation:** a context dependent explanation, such as a
   pause weakening the opening of an interview response.
3. **Screening hypothesis:** a repeated pattern that may warrant targeted
   assessment, stated with uncertainty and alternatives.
4. **Clinical conclusion:** diagnosis or treatment guidance supported by an
   appropriate reference standard, validation, intended purpose, and clinical
   governance.

The current engine may produce levels 1 and 2. Later phases may introduce
level 3. Level 4 is outside the current implementation authority.

### 1.4 Core scientific rules

- Do not turn missing or unreliable data into a score.
- Do not use agreement between several general purpose LLMs as clinical truth.
- An LLM may interpret or explain evidence; it may not be the sole measurement
  instrument for a clinical style claim.
- Prefer a personal baseline for improvement. Normative comparisons require a
  representative reference population and must not confuse accent, dialect,
  age, gender, language, or disability with poor communication.
- Store primitive measurements before inventing composite scores. A combined
  index needs a documented target construct and empirical calibration.
- Test accuracy separately from reliability. A stable measurement can still be
  wrong, and a correct average can still be too noisy for individual progress.
- Preserve provenance and uncertainty all the way into the final report.
- Separate development, tuning, and evaluation data. Never report performance
  on data used to choose thresholds or prompts.
- A regression fixture copied from current output protects software stability,
  not scientific truth. Human or independently established reference labels
  are required for validity claims.

### 1.5 Learning and progression contract

- The canonical learning unit is: declared task, first attempt, evidence linked
  finding, versioned exercise, repeat attempt, measured change, and later
  transfer to a related situation.
- Store the person's goal, task and prompt version, preparation level, context,
  recording quality, self report, exercise version, and outcome with each
  learning unit. A recording without this context is evidence, but it is not a
  comparable progress observation.
- Compare equivalent tasks and conditions for longitudinal change. Keep natural
  real world recordings useful without silently comparing unlike situations.
- Game rewards may recognise practice and consistency. Skill mastery requires
  repeatable evidence beyond measurement error and must remain separate from
  experience points, streaks, or cosmetic rewards.
- The internal evidence system may be detailed while the eventual interface
  presents one challenge, one useful finding, one exercise, and one clear next
  step at a time.

---

## 2. Current system

One audio file in `/audio` becomes a verified speech coaching analysis in
`/output`. The current command is:

```text
python3 pipeline/run_all.py --speakers 2
```

Add `--me SPEAKER_00` only when intentionally recording the run in
`history.json` and `progress.md`.

### 2.1 Current stages

1. **Extractors in parallel**
   - `diarize.py`: pyannote speaker diarization.
   - `transcribe.py`: AssemblyAI verbatim transcript, word timestamps,
     disfluencies, confidence, and optional expected speaker count.
   - `align.py`: WhisperX timing used for within word rendering evidence.
   - `pauses.py`: Silero VAD speech chunks and silences.
2. `acoustics.py`: Parselmouth and Librosa pitch, loudness, jitter, shimmer,
   coarse timeline, and fine pitch track.
3. `merge.py`: attribution, renderer, backchannels, deterministic metrics,
   `master.json`, and `words_attributed.json`.
4. `referee.py`: Gemini label only corrections for conversations, followed by
   `merge.py --rebuild`. It is skipped for solo recordings.
5. `listener.py`: Gemini listens to the audio, enriches turns and moments, and
   audits sampled renderer effects.
6. `evaluate.py`: Gemini produces the coaching report from instrumented data.
7. `verify.py`: checks numeric report claims against `master.json`.
8. `history.py`: optionally records one identified speaker and renders progress.

All current Gemini calls use `gemini-3.5-flash` with high thinking through the
`google-genai` SDK.

### 2.2 Current calibrated renderer

The following constants are protected until a new labelled calibration study
explicitly replaces them:

- `DRAG_RATIO = 2.6`
- `DRAG_MIN_S = 0.50`
- `DRAG_PERCENTILE = 95`
- `LOUD_DB_ABOVE = 5.5`
- `RISE_RATIO = 1.18`
- `RISE_MIN_HZ = 15`

### 2.3 Known limitations

- Inputs and outputs are fixed shared directories, so stale files can leak
  between runs and concurrent user sessions are impossible.
- The test corpus contains only one two speaker recording and one solo
  recording. There is no clean studio, controlled task, accent, device, or
  atypical speech coverage.
- Current golden set planning freezes pipeline output rather than independent
  truth.
- Most metrics have no explicit confidence, availability reason, task
  suitability, or source lineage.
- Audio conditions are described after analysis, not used to prevent invalid
  measurements before analysis.
- `requirements.txt` is unpinned and exact provider model behavior is not fully
  recorded in output metadata.
- LLM failure behavior is inconsistent: the referee degrades safely, the
  listener can stop the pipeline, and the evaluator has no common retry and
  degradation contract.
- Verification establishes numeric traceability, not that a source measurement
  is accurate or that the surrounding interpretation is supported.
- Coaching scores are useful prototypes but are not validated clinical or
  longitudinal outcome measures.

---

## 3. Binding engineering rules

These rules apply to every remaining item.

- Follow `AGENTS.md`: one improvement at a time, in order, with the owner
  committing between improvements.
- Never commit or push. The owner performs every commit.
- Run a full pipeline acceptance recording between items unless the item is
  documentation only and the owner explicitly agrees otherwise.
- Do not append test runs to `history.json` or `progress.md`. Use `--me` only
  when intentionally testing history and tell the owner before doing so.
- Do not change protected renderer thresholds as a side effect of other work.
- Do not rename output files or remove fields from `master.json`. Additive,
  versioned fields are allowed.
- Keep every stage runnable standalone from the repository root.
- Every changed Python file must pass `python3 -m py_compile`.
- Transcription is load bearing. Other remote or LLM enrichments retry once and
  then degrade gracefully with explicit status rather than crashing the run.
- A 429 `RESOURCE_EXHAUSTED` response is reported to the owner. Do not hammer
  retries.
- Nothing may weaken `verify.py`, the renderer audit, or traceability.
- Tests must use isolated temporary output directories. They must not overwrite
  the owner's latest report or longitudinal data.
- Keep raw evidence, recording quality, deterministic measurements, listener
  perceptions, coaching interpretations, and user outcomes separate. An LLM
  opinion or user correction must not silently become a truth label.
- Partition future development and evaluation data by participant, not by
  recording, so one person's voice cannot appear on both sides of a validity
  test. Preserve label source, annotator role, uncertainty, and adjudication.
- New metrics require a written construct definition, required task, known
  confounders, failure behavior, and validation plan.
- New thresholds must be chosen on development data and evaluated on separate
  data. Do not tune against the final golden evaluation set.
- Preserve raw provider outputs needed to reproduce or audit a result, subject
  to the future data retention policy.

---

## 4. Completed foundation history

### 1. Deterministic language metrics, DONE

`language_metrics()` in `merge.py` adds per speaker hedges, questions,
pronoun balance, immediate repetition, and vocabulary variety on both fresh and
rebuild passes. The discourse filler heuristic for “like” is documented.
Questions use raw ASR punctuation so renderer added uptalk question marks are
excluded. The evaluator knows these fields exist.

Acceptance evidence on the two speaker recording:

- Metrics and phrase breakdowns appeared in `master.json`.
- The evaluator cited the new fields.
- Verification remained at or near 100 percent.
- Solo verification remains untested because no solo recording exists.

### 2. Word boundary clipping, DONE

`merge.py` clips an ASR word end time to the end of the VAD speech chunk that
contains the word start. This prevents following silence from becoming a false
word drag. Numeric words may retain `held_s` but are not letter stretched.

Acceptance evidence on the two speaker recording:

- Thirteen word ends were clipped.
- The false multi second drag on “are” disappeared.
- The listener audit retained 100 percent drag agreement.
- No protected renderer threshold changed.

### 3. Prototype history and progress layer, DONE

`run_all.py --me SPEAKER_XX` invokes `history.py` after verification. It stores
the selected speaker's computed metrics, coaching scores, renderer audit, and
verification percentage in `history.json`, then deterministically renders
`progress.md` once at least two records exist.

The two records currently in `history.json` are disposable acceptance test
records. The owner is `SPEAKER_00`. Do not delete or alter them without a
separate explicit instruction.

This implementation is a prototype. Phase B will replace its assumption that a
speaker label is a durable user identity and will separate progress by task and
context.

### 4. Verifier upgrades, DONE

`verify.py` excludes prescriptive numbers in “One drill” sections and checks
the sign of claims such as dB above or below a speaker baseline. Magnitudes with
the wrong sign appear in a distinct `WRONG DIRECTION` section. The verifier
reports problems without crashing because the report is the product.

On the latest real report it correctly rejected an evaluator generated 19.12
second duration that had been derived by subtracting timestamps.

### 5. WhisperX transcript cross check, REMOVED

The owner removed this feature after end to end testing. WhisperX small was the
weaker transcript on real recordings, so its disputes mostly added false doubt.
Do not reintroduce transcript voting without a new adjudication design and
owner approval.

WhisperX remains an optional timing source for expressive rendering. Its text
must not silently replace the load bearing AssemblyAI transcript.

---

## 5. Phase A, trustworthy measurement foundation

Complete every item in this section before Phase B.

### 6. Gemini structured outputs, DONE

**Purpose:** Remove avoidable JSON formatting failures without changing the
meaning or downstream shapes of Gemini enrichment.

**Work:**

- Define exact response schemas for `referee.py` and `listener.py` using the
  `google-genai` SDK structured output support and JSON response MIME type.
- The referee schema must preserve `edits`, `from_i`, `to_i`, `speaker`, and
  `reason`.
- The listener schema must preserve turn findings, six emotion values, notes,
  moments, contradictions, overall impressions, audio conditions, and renderer
  audit results.
- Remove regex markdown fence stripping from both files.
- Keep one retry for provider, schema, and semantic failure.
- Keep all semantic validation: valid turn IDs, speaker membership, edit span
  cap, total edit cap, and transcript immutability.
- Do not convert open ended observations into restrictive enums merely to make
  schema validation easier.

**Acceptance:**

- Both steps use enforced JSON output and no fence stripping.
- Downstream `listener.json`, `words_attributed.json`, and `master.json` shapes
  remain compatible.
- Invalid speaker labels, turn IDs, or edit spans are still rejected.
- Referee failure still leaves original labels intact.
- Full two speaker pipeline completes with verification and renderer audit at
  their existing quality levels.

### 7. LLM failure contracts and enrichment status, DONE

**Purpose:** Make remote enrichment optional, observable, and consistent.

**Work:**

- Introduce one shared retry policy for referee, listener, and evaluator:
  initial request, one retry, then explicit degradation.
- Distinguish provider failure, quota exhaustion, timeout, empty response,
  schema failure, and semantic validation failure.
- Add an additive `meta.enrichment_status` object to `master.json` with status,
  attempts, model ID, and a safe error category for each LLM stage.
- Listener failure must preserve the un-enriched `master.json`, record that
  audio interpretation and renderer audit are unavailable, and allow objective
  evaluation or a clearly limited report to continue.
- Evaluator failure must preserve all measurement artifacts and produce an
  explicit unavailable evaluation and verification state rather than erase or
  corrupt prior files.
- Never reuse a stale enrichment file from an earlier run.

**Acceptance:**

- Offline or mocked failures for each LLM stage exercise the degradation path.
- The pipeline never presents stale enrichment as current.
- A 429 performs no more than the allowed retry and is clearly reported.
- A successful real run retains current output content and shapes plus status
  metadata.

### 8. Explicit inputs and isolated run outputs, DONE

**Purpose:** Make runs safe for regression testing, future accounts, and an app
wrapper.

**Work:**

- Add explicit audio and output directory arguments at the runner level and
  thread them through every active stage.
- Preserve the current `/audio` and `/output` defaults for command line
  compatibility, but stop relying on “first file found” when an explicit input
  is supplied.
- Give each non-legacy run a run ID and isolated output directory option.
- Write stage outputs atomically so an interruption cannot leave a valid
  looking half-written JSON file.
- Start each run with a manifest of expected outputs and never consume an
  undeclared file from another run.
- Make the test harness use temporary run directories.

**Acceptance:**

- Two runs can execute against different audio and output directories without
  sharing artifacts.
- A deliberately planted stale listener or transcript file is not consumed.
- The existing root command remains usable.
- No test changes root `output`, `history.json`, or `progress.md`.

### 9. Reproducible execution and provenance, DONE

**Purpose:** Make every number traceable to the code, model, prompt, dependency,
and input that produced it.

**Work:**

- Define a pipeline version and bump policy.
- Pin direct dependency versions and create a reproducible lock or constraints
  mechanism for the tested environment.
- Add `meta.provenance` containing at minimum:
  - pipeline version and source revision when available;
  - audio filename, byte hash, duration, codec, sample rate, and channels;
  - start and completion times;
  - exact provider and local model IDs;
  - relevant model configurations;
  - prompt and response schema versions;
  - package and Python versions;
  - per stage duration and status.
- Put model IDs and prompt versions in one maintained configuration location
  rather than duplicating unnamed strings across scripts.
- Record whether a provider model is version pinned or a moving alias.
- Never store API secrets in provenance.

**Acceptance:**

- A reviewer can identify the exact input and implementation family behind
  every report without reading terminal logs.
- Repeating a run records the same input hash and configuration when unchanged.
- All active model IDs in the output match those actually invoked.
- Full pipeline runtime is visible by stage.

### 10. Solo first execution path, DONE

**Purpose:** Make the common one user case faster, simpler, and less error
prone while retaining optional conversation analysis.

**Work:**

- Add an explicit recording mode: `solo`, `conversation`, or `auto`.
- Keep `auto` for developer compatibility; the future app must always choose a
  declared mode.
- In solo mode assign the account holder deterministically to `SPEAKER_00`.
- Avoid the full pyannote diarization and Gemini referee when one speaker is
  declared. Build the compatible single speaker timing structure from existing
  speech activity and transcript evidence.
- Retain per speaker acoustics over speech regions rather than analysing long
  silence as voice.
- Add a lightweight contamination check for a sustained second voice. A likely
  second speaker warns or rejects a baseline assessment rather than silently
  changing user identity.
- Conversation mode must preserve current diarization, attribution, referee,
  backchannel, and optional identity selection behavior.

**Acceptance:**

- A real solo recording produces `SPEAKER_00`, skips pyannote and referee, and
  completes all applicable stages.
- Solo output retains compatible `master.json` fields and correct
  `recording_type`.
- Solo runtime is materially lower than conversation runtime.
- The existing two speaker recording still passes in conversation mode.
- A solo recording containing a clear sustained second voice produces an
  explicit contamination warning.

### 11. Audio quality gate, DONE

**Purpose:** Prevent microphone and environment failure from masquerading as a
speech characteristic.

**Work:**

- Add a deterministic preflight stage before expensive extraction.
- Validate file readability, duration, codec, sample rate, channels, and
  nonempty audio.
- Implement the previously planned guards:
  - clear error for no audio;
  - reject audio under 5 seconds;
  - explicit input selection when more than one file exists;
  - warn above 30 minutes and require `--long-ok`.
- Measure and store at minimum clipping, peak and RMS level, near silence,
  speech proportion, a documented signal to noise proxy, and channel handling.
- Detect conditions that invalidate specific measurements, including heavy
  background speech, severe reverberation or unstable recording level where
  feasible.
- Produce per check `pass`, `warn`, `fail`, value, threshold version, and a
  plain language reason.
- Add an explicit `--quality-policy coaching|baseline` runner option. Keep
  `coaching` as the command line default for compatibility; a future product
  session must declare its policy.
- Broken, empty, under five second, and disallowed long inputs stop before
  expensive analysis. Signal problems such as noise or poor level may continue
  with clear warnings under `coaching`, but must request a new recording when
  they invalidate a controlled `baseline`.
- Choose and document provisional thresholds using dedicated generated
  development fixtures. Do not copy arbitrary values from a single paper or
  either of the owner's recordings, and do not present these operational
  thresholds as scientific validation.

**Acceptance:**

- Generated clean, clipped, near silent, noisy, too short, too long, and
  multi-file fixtures reach the expected deterministic outcome under both
  quality policies.
- Failed quality checks prevent dependent metrics from being reported as
  trustworthy.
- Quality status and limitations appear in `master.json` before LLM analysis.
- Owner approved exception for this item: do not run the owner's mall or solo
  recordings. Acceptance uses generated audio fixtures. A real recording run
  remains deferred until the owner separately approves it.

**Acceptance evidence, 2026-07-18:**

- Generated clean, clipped, near silent, noisy, quiet, short, long, unreadable,
  stereo, and multi-file cases passed their expected checks.
- Coaching continues usable imperfect audio with named limitations. Baseline
  rejects signal conditions that invalidate controlled measurement.
- A generated rejected input produced the quality report and failed manifest,
  then stopped before transcription or any remote stage.
- Quality results enter provenance and `master.json`; listener and evaluator
  instructions require warnings to limit affected claims.
- All 22 repository tests pass and every Python file compiles. No owner audio,
  remote API, history file, or progress file was used.

### 12. Measurement evidence and uncertainty, DONE

**Purpose:** Make “unknown” a first class result and prevent precise looking
numbers from outrunning their evidence.

**Work:**

- Keep current `computed_metrics` values for compatibility and add a parallel,
  versioned measurement metadata structure.
- For every reported metric record:
  - construct and unit;
  - source stage and source fields;
  - required recording task or mode;
  - availability status;
  - confidence or quality category with documented meaning;
  - sample size or analysed duration;
  - warnings and known confounders;
  - algorithm and threshold version.
- Propagate ASR word confidence into `low_confidence_words` with
  `why="asr-low-confidence"` using a documented threshold evaluated on
  development data.
- Distinguish transcription uncertainty, speaker uncertainty, acoustic
  uncertainty, insufficient sample, and audio quality failure.
- Do not replace missing values with zero.
- Define minimum sample requirements for rate, pitch, voice quality, language,
  and turn based metrics.

**Acceptance:**

- Every displayed computed metric can be traced to evidence and quality.
- Short or unsuitable samples produce unavailable values with reasons.
- Low confidence ASR words are visible to downstream consumers.
- The evaluator is instructed not to build major conclusions on unavailable or
  low quality measurements.

**Acceptance evidence, 2026-07-18:**

- Every existing computed metric and per speaker voice measurement receives a
  versioned record containing its source, requirements, availability, quality,
  sample, warnings, confounders, algorithm, and threshold version.
- Generated short samples preserve legacy numeric fields but mark unsuitable
  rates and other dependent measurements unavailable with a reason.
- ASR confidence below the provisional 0.50 cutoff produces a separate
  `why="asr-low-confidence"` word flag and transcription uncertainty record.
- Transcription, speaker, acoustic, insufficient sample, and audio quality
  uncertainty remain separate machine readable categories.
- The listener receives compact quality limits. The evaluator must ignore
  unavailable values, cannot anchor conclusions to low quality values, and may
  return `Not assessed`. Progress excludes unavailable and low quality values.
- All 30 repository tests pass and every Python file compiles. Per the owner's
  direction, verification used generated fixtures and no owner recording,
  remote API, history file, or progress file.

### 13. Evidence linked evaluation and verification, DONE

**Purpose:** Extend honesty checking from “this number exists somewhere” to
“this conclusion cites the evidence it actually uses.”

**Work:**

- Preserve `evaluation.md` for human reading and add a machine readable claim
  ledger.
- Each factual coaching observation must cite one or more stable references:
  metric path, turn ID, word effect, pause marker, listener finding, or declared
  scenario evidence.
- Label each claim as measured observation, coaching interpretation, screening
  hypothesis, or prescription.
- The verifier must check reference existence, speaker ownership, timestamp
  containment, metric availability, direction, and numeric equality where
  applicable.
- Subjective listener impressions must be identified as perceptions, not
  measurements.
- User self report and inferred emotion must never be presented as the same
  evidence source.
- Prescriptive drill numbers remain excluded from data claim verification but
  stay labelled as prescriptions.

**Acceptance:**

- A deliberately wrong speaker reference, nonexistent turn, unavailable
  metric, flipped dB direction, and derived timestamp duration are all caught.
- Verification reports both claim traceability and measurement quality.
- The report remains readable and useful when listener enrichment is
  unavailable.
- Existing honesty guarantees are strengthened, never weakened.

**Acceptance evidence, 2026-07-19:**

- `evaluation.md` remains readable and now links every substantive statement
  to a versioned record in `evaluation_claims.json` using sequential claim IDs.
- The evaluator receives an exact evidence catalog and returns schema checked
  JSON. Local semantic checks reject uncited lines, mismatched claim text,
  unsupported references, and claim levels outside current authority before a
  report is accepted.
- `verification.json` and `verification.md` check paths, evidence source,
  speaker ownership, turn identity, timestamp containment, availability,
  measurement quality, direct numeric equality, and signed direction. The
  earlier whole report numeric check remains as an additional safety net.
- Generated adversarial fixtures catch wrong speakers, missing turns,
  unavailable and low quality metrics, reversed dB direction and sign,
  timestamp derived durations, uncited prose, source conflation, and timestamps
  outside their turns.
- Objective claims remain usable when listener enrichment is unavailable.
  Listener perception, declared user context, inferred context, and
  prescriptions stay explicitly separate.
- All 48 repository tests pass and every Python file compiles. Per the owner's
  direction, verification used generated fixtures and no owner recording,
  remote API, history file, or progress file.

### 14. Truth labelled regression harness, DONE

**Purpose:** Detect software regressions and measure correctness against
independent reference truth.

**Work:**

- Create `tests/` and an isolated regression runner.
- Separate three test layers:
  1. unit and invariant tests for deterministic functions;
  2. frozen software regression snapshots;
  3. human or independently labelled validity fixtures.
- A `--bless` operation may create or update software snapshots, but it may not
  create human truth labels.
- Human truth must record annotator identity or role, annotation guide version,
  date, and adjudication status.
- The initial labelled set must cover:
  - the current two speaker recording;
  - a solo recording;
  - clean and noisy audio;
  - overlap and short backchannels;
  - known pauses and renderer events;
  - deliberately controlled fast, slow, loud, quiet, and monotone samples.
- Later phases add diverse accents, devices, ages, languages, and consenting
  atypical speech.
- Compare speaker attribution, word timing, pauses, renderer effects, metric
  values, quality status, and verification results with metric appropriate
  tolerances.
- Report false positives and false negatives, not only aggregate agreement.

**Acceptance:**

- Blessing then rerunning a software snapshot passes.
- Changing a protected renderer threshold fails with a clear diff.
- A deliberately wrong human label is not silently overwritten by `--bless`.
- Tests run without changing production outputs or personal history.
- Each measured acceptance percentage states its denominator and reference
  source.

**Acceptance evidence, 2026-07-19:**

- The isolated `regression` runner keeps unit tests, replaceable software
  snapshots, and independent truth files separate. `--bless` writes only the
  software snapshot and cannot create or replace truth labels.
- Every truth file records its source, annotator role, guide version, date,
  adjudication status, independence from the pipeline, coverage, and known
  limitations. The exact audio byte hashes bind the real solo and conversation
  labels to their recordings.
- Real recording truth deliberately covers only facts declared independently
  by the repository owner plus container duration: conversation passed 4 of 4
  checks and solo passed 5 of 5. It does not pretend that pipeline transcripts
  or renderer output are human truth.
- Generated ground truth covers clean, noisy, loud, quiet, fast, slow,
  monotone, overlap, short backchannel, pause, renderer, speaker attribution,
  word timing, metric values, and valid and invalid verification cases.
- Generated controls passed 3 of 3 speaker labels, 3 of 3 word timing checks,
  3 of 3 renderer precision opportunities, 3 of 3 renderer recall
  opportunities, 4 of 4 metric tolerances, and 11 of 11 condition checks. The
  renderer result contained zero false positives out of 3 detected events and
  zero false negatives out of 3 reference events.
- Tests prove that blessing then rerunning a snapshot passes, a simulated
  protected threshold change produces a path specific diff, and a deliberately
  wrong human label remains unchanged and fails even when a snapshot is
  blessed.
- The real conversation and solo pipelines both completed under pipeline
  version 0.5.9 with the same source hash. Conversation verified 28 of 28
  evidence linked claims and 12 of 12 legacy numeric claims. Solo verified 22
  of 22 evidence linked claims and 9 of 9 legacy numeric claims.
- All 61 repository tests pass and every Python file compiles. All harness and
  acceptance outputs used isolated temporary directories. Neither real run
  passed `--me`, and `output`, `history.json`, and `progress.md` were unchanged.

### 15. Reliability and fairness audit

**Purpose:** Establish whether measurements are stable enough to track one
person and whether performance varies materially across groups or conditions.

**Work:**

- Build a repeatability protocol with:
  - identical audio repeated through the same version;
  - the same recording across supported devices and encodings;
  - repeated productions by the same speaker in stable conditions;
  - expected deliberate behavior changes.
- Deterministic stages must be exactly repeatable on identical input.
- For repeated human productions, predefine metric specific acceptable error,
  intraclass agreement or limits of agreement, and smallest change worth
  interpreting. Do not use one universal tolerance.
- Separate natural day to day variation from pipeline measurement error.
- Audit word error, speaker error, unavailable rate, and key metric error by
  available language, accent, age band, voice range, device, audio quality, and
  speech difference metadata.
- Report subgroup sample sizes and uncertainty. Do not claim fairness from an
  unrepresentative or tiny sample.
- Add documented release gates for any metric used to rank, screen, or guide a
  high stakes decision.

**Acceptance:**

- The audit produces a versioned machine readable result and readable report.
- Exact repeatability failures block Phase A completion.
- Metrics too noisy for individual progress are hidden or labelled
  experimental rather than trended.
- Known subgroup gaps are visible and attached to affected measurements.
- No diagnostic accuracy, sensitivity, or specificity is claimed without an
  independent reference standard and held out evaluation data.

**Acceptance evidence, 2026-07-19:**

- The isolated audit writes versioned `reliability_fairness.json` and a short
  `reliability_fairness.md`. Its deterministic stages ran twice from identical
  frozen evidence with zero differences. Every deliberate generated fast,
  slow, loud, quiet, noisy, monotone, attribution, renderer, and verification
  control passed.
- Two complete solo runs used the same audio bytes, pipeline version 0.6.0,
  and source hash. They had zero pairwise transcript differences out of 275
  words, zero speaker label differences out of 275 index matched words, and
  zero computed metric differences. These are repeatability observations, not
  word or speaker error rates, because neither run is independent truth.
- The same solo audio decoded from AAC into PCM WAV had the same duration and
  produced zero pairwise transcript, speaker label, or computed metric
  differences. No second recording device exists in the current data, so
  device repeatability remains explicitly untested.
- The repository has no suitable stable condition repeated human productions.
  Natural day to day variation therefore cannot be separated from measurement
  error. Every metric now carries a metric appropriate prespecified analysis,
  remains labelled experimental for progress, and is blocked from longitudinal
  trending until its measurement error and smallest detectable change are
  established. Coaching scores are also no longer trended.
- The audit counts unavailable measurements per recording but reports word
  error, speaker error, and real speech metric error as unavailable because no
  independent subgroup references exist. Language, accent, age band, voice
  range, device, audio quality, and speech difference coverage each show their
  independent participant count and uncertainty state.
- There are zero consented, independently identified participants with the
  metadata needed for subgroup comparison. The result is `not_evaluated`, not
  a fairness pass, and every affected measurement exposes the missing subgroup
  coverage. Empty known gap lists explicitly do not mean equal performance.
- Release gates block personal progress, ranking, screening, and high stakes
  decisions. Single recording coaching remains allowed only with its existing
  evidence and quality limits. No diagnostic accuracy claim is made.
- The final real conversation and solo pipelines completed in isolated
  directories. Conversation verified 33 of 33 evidence linked claims and 10 of
  10 legacy numeric claims. The independent regression suite passed both real
  recordings and all generated truth checks.
- All 68 repository tests pass and every Python file compiles. No run passed
  `--me`; root `output`, `history.json`, and `progress.md` were unchanged.

---

## 6. Phase A exit gate

All conditions below must pass before Phase B begins:

- Items 6 through 15 are complete in order and committed by the owner.
- The real two speaker recording completes in declared conversation mode.
- A real solo recording completes in declared solo mode without pyannote or
  referee and without appending history.
- Every changed Python file compiles.
- Remote enrichment failure leaves a valid, explicitly limited measurement
  result.
- Inputs and outputs are isolated and stale artifact tests pass.
- Provenance identifies the input, code, models, prompts, schemas, packages,
  stage status, and runtime.
- Audio quality fixtures pass their expected gates.
- Measurement metadata exposes availability, evidence, quality, and warnings.
- Evaluation claims have valid evidence references and verification does not
  regress.
- The regression harness contains independently labelled solo and conversation
  truth, not only blessed snapshots.
- Repeatability results establish which metrics are safe to trend.
- Fairness reporting exists even if the initial dataset is too small to draw
  conclusions; the limitation must be explicit.
- Protected renderer thresholds and legacy stages remain untouched.

Phase A does not make the product clinically validated. It makes the engine
auditable, testable, reproducible, solo ready, and safe to extend.

---

## 7. Phase B roadmap, onboarding assessment and personal baseline

Do not implement this phase until the Phase A exit gate passes and the owner
approves a detailed protocol review.

### 16. Assessment task manifest

Design a roughly ten minute English onboarding session. The backend protocol
should precede visual application design. It has no backend age gate, collects
no exact age, and uses no age norms. Public launch consent and privacy work must
still support people who cannot independently consent.

Core task families:

1. microphone and room calibration;
2. goals, language, context, and self report;
3. a standard reading passage or explicitly different spoken alternative;
4. spontaneous explanation;
5. a goal specific task such as an interview response or demonstration;
6. a short repeat matched to the reading or spoken option selected earlier;
7. self reflection;
8. at most one adaptive follow up selected from technical or measurement
   uncertainty, never a low skill interpretation.

Each task needs a manifest containing prompt version, intended construct,
required language, expected text where relevant, duration, quality requirements,
metrics enabled, accommodations, retries, valid comparisons, and stop
conditions. Consent for coaching, raw audio retention, human review, research,
model improvement, and fairness metadata remains separate and defaults off.

A comfortable sustained sound and an ordinary repeated phrase are optional
research tasks only. They require separate consent and cannot affect coaching.
Rapid syllable and pronunciation tasks remain locked for later evidence work.

The manifest also defines preparation level, challenge dimensions, repeat task
rules, and an appropriate transfer task. Difficulty may increase through less
preparation, tighter time, unfamiliar prompts, follow up questions,
interruptions, or more demanding situations without changing several factors
at once.

The baseline occurs in controlled quiet conditions. Later real world sessions
measure functional communication in context and must not be compared to the
quiet baseline without recording the context difference.

**Acceptance:**

- A versioned machine readable manifest defines every core, alternative,
  adaptive, research, and locked task.
- The core session takes roughly ten minutes, supports a spoken alternative to
  reading, and keeps its later repeat in the same mode.
- The protocol produces a provisional coaching profile, not a diagnosis,
  overall score, age comparison, accent judgement, or ranking between people.
- Existing unvalidated measurements remain blocked from progress. Same day
  success records practice only; later retention and a suitable new prompt are
  both required before future mastery.
- Automated validation blocks unknown measurements, unsafe claims, required
  research, mismatched accessible task pairs, missing consent, unsupported
  language, unlocked future tasks, and unsafe duration.
- This item schedules backend tasks only. It does not record audio, build the
  application UI, select lessons, or change current pipeline scoring.

**Acceptance evidence, 2026-07-19:**

- `assessment/manifest-v1.0.0.json` defines a 540 second English solo session
  with seven required steps, original prompts and content, timing,
  preparation, recording quality, measurements, accommodations, retries, stop
  conditions, and comparison limits.
- Reading and spoken standard samples have separate matching repeat tasks. The
  validator confirms that repeat text comes from the correct earlier content
  and prevents an accessibility choice from silently becoming a reading task.
- The manifest has no age gate, exact age field, age norms, overall score,
  clinical authority, ranking, or pronunciation scoring. Every current speech
  measurement remains blocked from progress.
- Optional sustained voice and repeated phrase probes require separate research
  consent and cannot affect coaching. Rapid syllable and pronunciation tasks
  are present only as locked future work.
- `assessment/research-and-protocol.md` separates sourced evidence from product
  decisions and records the approved language, accessibility, consent,
  privacy, progression, and research boundaries.
- The manifest validator passes, all 88 repository tests pass, and every Python
  file compiles.
- The real solo pipeline completed in an isolated temporary directory in 242
  seconds. Objective measurement completed. The evaluator rejected two unsafe
  remote responses and produced its valid limited fallback, with no coaching
  claims to verify. No run passed `--me`; root output, `history.json`, and
  `progress.md` were unchanged.

### 17. Controlled pronunciation and intelligibility

- Evaluate candidate phoneme assessment approaches against human phonetic
  transcription before selecting an API or model.
- Known text enables phoneme, syllable, word, insertion, omission, break, and
  completeness analysis.
- Measure listener intelligibility separately from similarity to a single
  prestige or native accent.
- Preserve legitimate accent and dialect variants.
- Store opportunities and denominators for every sound pattern.

### 18. User, session, task, and context model

- Replace durable identity by speaker label with stable account and session
  identities.
- `SPEAKER_00` remains the account holder within a recording, not the global
  user ID.
- Store declared goal, task type, language, device, environment, recording
  mode, self report, and pipeline version.
- Link first attempts, versioned exercises, repeat attempts, retained change,
  and transfer attempts without overwriting their individual evidence.
- Separate global tendencies from context specific progress streams such as
  interviews, spoken exams, presentations, social practice, and conversation.
- Keep consent for providing the service separate from permission to retain or
  use recordings for research, model development, or human annotation.
- Make data export and deletion technically possible before application launch.

### 19. Personal baseline and meaningful change

- Require enough valid observations before declaring a baseline.
- Model within person ranges rather than treating one recording as normal.
- Pair measured behavior with user reported confidence, anxiety, usefulness,
  and real world outcome.
- Report change only when it exceeds known measurement error and expected
  natural variation.
- Keep practice completion, streaks, and experience rewards separate from
  evidence based skill mastery. Do not rank people globally by voice or
  communication style.
- Never equate louder, faster, lower pitched, or more conventionally accented
  speech with confidence by default.

---

## 8. Phase C roadmap, objective speech pattern modules

Each module is a separate research and validation project. Do not build one
general “speech impediment detector.”

### 20. Voice and prosody primitives

- Keep pitch variation and loudness range as separate primitives first.
- Evaluate robust measures such as smoothed cepstral peak prominence and
  harmonics to noise ratio alongside existing jitter and shimmer.
- Standardise sustained vowel and connected speech tasks.
- Quantify device, room, loudness, voice range, and task sensitivity.
- Defer any combined prosodic variation score until it is calibrated to a
  declared construct on held out data.
- Phrase final creak may be measured descriptively after validation, but it is
  not inherently a defect and must not reduce a general communication score.

### 21. Stuttering like event module

- Detect and timestamp sound repetitions, word repetitions, prolongations,
  possible blocks, and non-stuttering disfluencies separately.
- Combine controlled reading, spontaneous speech, speaker self report, and
  optional manual confirmation.
- Report event type uncertainty and annotator ambiguity.
- Begin as progress measurement and screening evidence, not diagnosis.

### 22. Articulation and phonological pattern module

- Compare expected and observed phonemes on controlled tasks.
- Track substitutions, omissions, additions, distortions where supported, word
  position, consistency, and intelligibility impact.
- Distinguish a stable speech pattern from ASR error and legitimate accent or
  dialect variation.
- Require repeated opportunities before reporting a pattern.

### 23. Motor speech and voice screening modules

- Evaluate rate, regularity, articulatory precision, repeated production
  consistency, voice quality, pitch and loudness control, and task effects.
- Keep dysarthria-like, apraxia-like, and dysphonia-like evidence in separate
  models with separate reference standards.
- Do not infer neurological or structural cause from audio alone.
- Moderate or severe speech may require personalised recognition before other
  measurements are trustworthy.

### 24. Personalised recognition for atypical speech

- Allow user corrected transcripts and controlled phrase collection to adapt
  recognition to the individual.
- Evaluate disorder wide, speaker adapted, and combined approaches on held out
  phrases and spontaneous speech.
- Never use corrected evaluation phrases for training.
- Measure meaning preservation and intelligibility, not only word error rate.

---

## 9. Phase D roadmap, evidence based coaching and outcomes

### 25. Intervention registry

Every exercise must have structured metadata:

- target behavior and intended population;
- evidence source and evidence strength;
- instructions, duration, frequency, and progression;
- required assessment evidence;
- exclusions, cautions, and referral triggers;
- outcome metric and reassessment timing;
- version and clinical reviewer when applicable.

An LLM may select and explain an eligible exercise. It may not invent a
clinical exercise or bypass eligibility rules.

### 26. Coaching loop

The core interaction is:

```text
record -> identify one important behavior -> show audible evidence
       -> practise one suitable exercise -> record again -> measure change
```

Prioritise a small number of meaningful actions over a dashboard of every
available metric. Preserve the user's goal and experience alongside instrument
data. Record the task, finding, selected intervention, repeat attempt, and
outcome as one linked learning unit so the system can learn which exercises help
which people in which contexts.

### 27. Outcome validation

- Test whether exercises change their target measurements beyond measurement
  error.
- Test whether gains transfer from controlled practice to spontaneous speech
  and the user's real goal.
- Test whether gains remain after feedback is removed and after enough time has
  passed to distinguish temporary performance from retained learning.
- Include user reported benefit and adverse experience.
- Do not optimise merely for sounding more typical; optimise for effective,
  comfortable communication and the user's chosen goals.

---

## 10. Phase E roadmap, clinical validation and release governance

Before any diagnostic, monitoring, or treatment claim:

- Define the intended purpose, population, exclusions, user, and decision the
  output supports.
- Obtain qualified speech pathology involvement in construct definition,
  annotation, reference standards, exercise selection, error analysis, and
  release review.
- Use representative, consenting development and external evaluation cohorts.
- Predefine endpoints, acceptable errors, subgroup analyses, and handling of
  indeterminate results.
- Follow applicable diagnostic accuracy and prediction reporting guidance.
- Establish risk management, incident reporting, model change control,
  post-release monitoring, and rollback.
- Determine applicable Australian medical device, privacy, research ethics,
  advertising, and professional requirements before supply.
- Keep general coaching and clinical intended purposes clearly separated in
  product language and functionality.

---

## 11. Deferred and removed ideas

- **WhisperX transcript voting:** removed by owner. Do not reintroduce without
  adjudication.
- **Current vocal fry heuristic:** removed from the active queue. Low pitch,
  jitter, and noise alone are not an adequate clinical creak detector.
- **Arbitrary 0 to 100 prosodic variation index:** deferred until a target
  construct and empirical calibration exist. Raw primitives remain planned.
- **Gemini context caching:** cost optimisation only; reconsider after Phase A.
- **Automatic diagnosis from several APIs:** not an accepted design. Evidence
  fusion may support screening, but repeated black box opinions are not a
  reference standard.
- **One universal communication score:** not planned. Context specific coaching
  and objective measurement remain separate.

---

## 12. Research basis for the revised plan

These sources inform the engineering principles. They do not provide drop-in
thresholds for this product.

- Australian TGA guidance: intended purpose determines whether software or AI
  is regulated as a medical device and what evidence is required.
  <https://www.tga.gov.au/resources/guidance/understanding-how-we-regulate-software-based-medical-devices>
- International good machine learning practice principles emphasise total
  product lifecycle, representative data, human factors, independent testing,
  clear information, and deployed performance monitoring.
  <https://www.fda.gov/medical-devices/software-medical-device-samd/good-machine-learning-practice-medical-device-development-guiding-principles>
- STARD-AI defines transparent reporting expectations for AI diagnostic
  accuracy studies, including participants, index tests, reference standards,
  analysis, and outcomes.
  <https://www.nature.com/articles/s41591-025-03953-8>
- TRIPOD+AI requires transparent reporting of prediction model development and
  evaluation, representative data, full model specification, and public or
  patient involvement.
  <https://www.bmj.com/content/385/bmj-2023-078378>
- The Speech Accessibility Project documents reproducible collection and
  curation of diverse dysarthria, apraxia, dysphonia, and other atypical speech.
  <https://www.isca-archive.org/interspeech_2025/zwilling25_interspeech.html>
- Research has demonstrated large performance disparities between speaker
  groups in commercial ASR, requiring explicit subgroup audits.
  <https://doi.org/10.1073/pnas.1915768117>
- Consumer device and room studies show that acoustic voice measures differ in
  robustness and that recording environment can dominate microphone effects.
  <https://pubmed.ncbi.nlm.nih.gov/30471944/>
- Cross-device speech research found some measures, including fundamental
  frequency and cepstral peak prominence in particular tasks, can be reliable,
  but reliability depends on measure and task.
  <https://pubmed.ncbi.nlm.nih.gov/39738817/>
- COSMIN measurement guidance distinguishes reliability, measurement error,
  validity, meaningful change, and cross-cultural measurement behavior.
  <https://www.cosmin.nl/wp-content/uploads/COSMIN-manual-V2_final.pdf>
- SEP-28k demonstrates both the feasibility of event-level stuttering detection
  and the need for multiple event labels, annotators, and generalisable data.
  <https://arxiv.org/abs/2102.12394>
- Personalised atypical speech recognition research shows the value of
  combining population and individual adaptation while also showing that large
  recognition errors can remain.
  <https://aclanthology.org/2025.emnlp-main.1701/>

---

## 13. Whole programme definition of done

The complete programme is not done when the pipeline produces an impressive
report. It is done only when:

- the measurement engine is reproducible, isolated, quality gated, evidence
  linked, uncertainty aware, and reliable enough for individual change;
- solo and optional conversation paths work on representative recordings;
- onboarding tasks have declared constructs and validated measurements;
- personal progress is separated by context and exceeds known measurement
  error;
- every speech pattern module passes held out, subgroup reported validation;
- exercises are evidence registered and their outcomes are measured;
- clinical claims, if pursued, have appropriate professional governance,
  external validation, regulatory status, and post-release monitoring;
- users can understand what was measured, what was inferred, what is unknown,
  and what action is appropriate.

Until then, describe the system accurately as an evolving communication
measurement and coaching engine, not a diagnostic replacement for a speech
pathologist.
