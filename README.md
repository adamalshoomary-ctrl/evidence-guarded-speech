# Evidence guarded speech measurement

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22106996.svg)](https://doi.org/10.5281/zenodo.22106996)
[![tests](https://github.com/adamalshoomary-ctrl/evidence-guarded-speech/actions/workflows/tests.yml/badge.svg)](https://github.com/adamalshoomary-ctrl/evidence-guarded-speech/actions/workflows/tests.yml)

Turn one recording into a measurement record where every number carries its
provenance and its uncertainty, and where a measurement the evidence cannot
support is marked unavailable instead of guessed.

It gives nobody a score, a rating or feedback on how well they speak. It makes
no screening or clinical claim. `project-purpose.md` sets out what it refuses
and why.

Open research. GPL 3.0 or later. No product and no monetisation plan.

## Run it in three steps

You need Python 3.12 or newer and ffmpeg. Neither pip nor this repository can
install ffmpeg for you.

```text
python3 -m pip install -r requirements.txt -c constraints.txt
python3 -m unittest discover -s tests -t .
python3 pipeline/run_all.py --mode solo --audio "regression/fixtures/solo.wav" --transcriber local
```

That third command needs no credentials and no network. It runs on a recording
that ships with the repository and writes `output/master.json` in about 90
seconds. Read `output/master_preview.txt` first.

**The full test suite runs on Linux, macOS and Windows on every push**, on
Python 3.12, and the badge above reports the result. All 227 tests run on all
three and none fail. Six of them check the release contract, which stays in the
private working repository, so here they skip and say why.

`constraints.txt` pins the dependency versions. The pinned closure was first
built on macOS arm64, and Linux and Windows install the same pins and pass. Open
an issue if yours does not.

## Where to read next

- `findings.md` is the account of what was measured, what was retracted and
  what could not be established. Start there to judge the work.
- `PROJECT-STATUS.md` says where the work stands, what is deferred, and
  what was decided against.
- `project-purpose.md` states the claims and the refusals.
- `AI-ASSISTANCE.md` records how much of this was written with generative AI.
- `CONTRIBUTING.md` and `SECURITY.md` cover issues and reporting.

The rest of this README is the operating reference: every command, every
artifact and every contract.

## Data and licence

GPL 3.0 or later, because `praat-parselmouth` is GPL and the acoustics stage
depends on it. `NOTICE.md` carries third party attribution.

The recordings this project was built on are not here and never will be. They
are one person's own voice and a conversation with somebody who agreed to be
recorded and was never asked about publication. What ships instead:

| Data | Source | Licence |
|---|---|---|
| `regression/fixtures/` | LibriSpeech | CC BY 4.0 |

The research behind `findings.md`, including the pseudonymised probe evidence
bundle that regenerates the published report, is at tag `v0.4.0`. See
[Research at v0.4.0](#research-at-v040). `CITATION.cff` holds the full source
records with their DOIs.

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

That is the whole suite, 227 tests. Six skip here with their reason printed,
because the release contract they check is not published.

## Credentials

Three keys exist and which ones a command needs depends on the command. Copy
`.env.example` to `.env` beside it, fill in the values you have, and keep only
the lines you need. **`.env` is plain text and is not encrypted**, the same
posture as any other command line tool; make it readable only by you with
`chmod 600 .env`.

| Variable | What it does | Needed by | Issued at |
|---|---|---|---|
| `ASSEMBLYAI_API_KEY` | transcribes the recording | every run except `--transcriber local` | <https://www.assemblyai.com/dashboard/signup> |
| `HF_TOKEN` | downloads the speaker diarization model | `--mode conversation` only | <https://huggingface.co/settings/tokens> |
| `GEMINI_API_KEY` | runs the language model stages | `--interpret`. Optional in conversation mode, where the speaker label referee uses it | <https://aistudio.google.com/apikey> |

**The Hugging Face token is not sufficient on its own.** Accept the model user
agreement at <https://hf.co/pyannote/speaker-diarization-3.1> first, or the
download returns a bare 401 that does not explain itself.

**You can run this with no credentials at all.** A solo recording on the local
transcriber makes no remote call and needs no key:

```text
python3 pipeline/run_all.py --mode solo --audio "regression/fixtures/solo.wav" --transcriber local
```

Every run checks the keys its flags will need **before** it starts, and stops in
well under a second naming the missing variable. Nothing downloads and no
provider is billed. A key that only serves a stage nobody asked for produces a
note rather than a stop, and that stage records itself as unavailable.

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
verifier. It needs `GEMINI_API_KEY`, and the run stops immediately without one
rather than transcribing first and reporting the layer unavailable at the end:

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

Every measurement is labelled experimental, and each one records that it may
not be used to track change over time. The pipeline has no repeated same person
study from which to estimate measurement error, natural variation or meaningful
change. Personal history and progress tracking were removed on 2026-09-23, and
the five language model scores the old trend rule once followed were deleted on
2026-08-24. A single recording can still be described.

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
listener, the interpretation and the claim ledger, and it
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

## Research at v0.4.0

On 2026-09-23 this repository was cut down to the measurement tool. Three bodies
of research left the main branch, and all of them are still published, byte for
byte, at tag `v0.4.0`, DOI
[10.5281/zenodo.22167605](https://doi.org/10.5281/zenodo.22167605):

- the speech sound pattern work, including the reference variety probe that
  `findings.md` reports and its pseudonymised evidence bundle;
- the motor speech and voice evidence programme, shelved before it left;
- the onboarding and pronunciation assessment protocols.

The published probe report still reproduces from the tag, with no audio, in
about two minutes:

```text
git checkout v0.4.0
python3 -m speech_sound_patterns.variety_probe_score --output /tmp/report.json
python3 -m speech_sound_patterns.validate_variety_probe /tmp/report.json
git checkout main
```

That checkout needs `numpy` and `jsonschema`. The main branch no longer
installs `jsonschema`, because nothing on it imports the package.

## Backend contracts

Validate the future backend account, session, task, context, consent, export,
and deletion contract with:

```text
python3 -m data_model.validate
python3 -m data_model.validate data_model/session-context-example-v1.1.0.json
```

The data model is a versioned contract, not a database or a service API. A
context aware run may pass `--session-context CONTEXT_PATH`. The runner
stores the validated snapshot as `session_context.json` and places its stable
account, session, context, attempt, recording references and canonical hash in
provenance. Context-free developer runs continue to work.

Solo mode always assigns the account holder to `SPEAKER_00`. It uses Silero
speech activity instead of pyannote speaker diarization and skips the Gemini
referee. If the transcription provider detects multiple speaker clusters, the
report contains a contamination warning.

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
