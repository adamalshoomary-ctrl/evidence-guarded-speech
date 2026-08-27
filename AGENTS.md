# Working in this repository (read me first, whatever agent you are)

Open research project on evidence guarded speech measurement. One audio file
becomes a measurement record whose every claim is traceable to stored evidence.

**This is not a product and there is no monetisation plan.** That was settled on
2026-08-22 and it is permanent. If you find prose anywhere in this repository
that describes an app, a user, a launch, a customer or a commercial constraint,
it is stale text that survived the direction change. Treat it as a defect and
say so. Do not plan work from it.

Read `README-SNAPSHOT.md` first if you have just arrived. It says what this
repository is, what was removed from it before publication, and what that
removal costs you.

Then read `findings.md`. It is the honest account of what was built, what was
measured, what was retracted, and what could not be established at all. It is
the shortest route to knowing what this repository actually demonstrates, which
is less than the amount of machinery here suggests.

Releases are archived. Cite the concept DOI `10.5281/zenodo.22106996`, which
always resolves to the newest version; `CITATION.cff` carries it along with the
version specific DOI for each tag.

Then read these short sources in order:

1. this file;
2. `current-state.md`;
3. `project-purpose.md`;
4. `improvement-plan.md`.

Then read only the technical material relevant to what you are doing: the needed
parts of `README.md`, active source, tests, schemas, and item specific research.
Do not read archived plans, generated output, or every unrelated source file
unless the task genuinely requires it.

Run a conversation recording:

```text
python3 pipeline/run_all.py --mode conversation --speakers 2 --audio regression/fixtures/conversation.wav
```

Run a solo recording:

```text
python3 pipeline/run_all.py --mode solo --audio regression/fixtures/solo.wav
```

Add `--transcriber local` to run without a paid AssemblyAI key. It is never a
fallback: a missing key fails the run. See `docs/offline-transcription.md` for
what the local path cannot measure, and use the provider path for any run whose
result you intend to compare with an earlier one. Conversation mode needs a
Hugging Face token for diarization; solo mode with `--transcriber local` needs no
credentials at all.

`--me` and `--session-context` append a run to a personal history. There is no
personal history in this repository and none should be created in it.

## The four standing constraints

These decide what work is legitimate. Full evidence is in `current-state.md`.

1. **Non commercial is permanent, and it cuts both ways.** Sources blocked on
   commercial grounds alone are available. Evidence built on them can never
   underwrite a commercial product. Do not propose work that depends on
   reopening this.
2. **The licence is GPL 3.0 or later.** `praat-parselmouth` is GPL and is a hard
   runtime dependency of the acoustics stage. Do not propose a permissive
   relicence without removing that dependency first. See `NOTICE.md`.
3. **No personal recording enters this repository.** It was built by removing
   them. Do not add audio of an identifiable person, do not commit pipeline
   output over such audio, and do not add a personal progress file.
4. **No screening or clinical claim, ever.** No roadmap item leads to one.

## What is not here, and what that costs you

This is a sanitized snapshot of a private working repository. The removals are
real and you should know what they cost before you trust a result.

- **The owner's own recordings are gone**, and the regression records that were
  pinned to them with them. `regression/fixtures/` holds openly licensed
  replacements assembled from LibriSpeech. They are read audiobook speech taking
  turns, not conversation, so they carry no overlap, no interruption and no
  disfluency. They establish that the pipeline runs. They validate nothing.
- **`speech_sound_patterns/accent_contrast.py` cannot run.** It analyses the
  owner reading a script twice in two accents, and no substitute recording can
  stand in for an analysis whose whole design is holding the speaker constant.
  The frozen result of the single run that was made is committed at
  `speech_sound_patterns/accent-contrast-v1.0.0.json` and is readable without
  rerunning anything.
- **`.research_data/` is not here and never was tracked.** It is about 24 GB of
  corpora, decoded clips, model snapshots and licence snapshots. Anything
  reading it will fail. The one part that mattered for reproducing a published
  result has been extracted, pseudonymised and committed as
  `speech_sound_patterns/variety-probe-evidence/`.
- **Committed pipeline output is gone.** Nothing in the repository shows you a
  finished run. Produce one yourself from a fixture.

## Reproducing the published analysis

The reference variety probe is the one substantive analysis this repository
publishes, and it is reproducible from what is here:

```text
python3 -m speech_sound_patterns.variety_probe_score --output /tmp/report.json
python3 -m speech_sound_patterns.validate_variety_probe /tmp/report.json
```

About two minutes, needing only `numpy`. The result is byte identical to the
committed `speech_sound_patterns/variety-probe-v1.2.0.json`. Read
`speech_sound_patterns/variety-probe-evidence/README.md` for what the evidence
can and cannot establish, and read the report's own uncertainty block before
quoting any number from it: nothing at group level is distinguishable from zero.

## Engineering rules

- Work on one improvement at a time and preserve the order in
  `improvement-plan.md`. A roadmap entry is not approval to begin it.
- Run proportionate tests and a full isolated pipeline run between
  implementation items. Tests and acceptance runs use isolated output
  directories.
- Do not rename output files, remove `master.json` fields, weaken verification,
  or alter the protected renderer thresholds as a side effect. Those constants
  may change only through a separate labelled calibration study.
- Every stage must remain runnable from the repository root, and every changed
  Python file must compile.
- Transcription is load bearing. Other enrichments retry once, then degrade with
  an explicit safe status.
- Report a provider quota response rather than hammering retries.
- Preserve raw evidence needed for audit. A recorded no selection is a
  legitimate completed outcome, not a failure to be fixed.

## Environment facts

- Credentials are read from a gitignored `.env` by variable name only. No key
  value has ever been committed, and every reachable object in the private
  repository's history was searched for the live values before this snapshot was
  built.
- A full conversation run takes a few minutes on a laptop, because diarization
  is the long pole. Run it in the background and check the output when done.
- **Prefix a real run with `caffeinate -dimsu` on a Mac running on battery.** A
  maintenance sleep part way through drops the network and makes the remote
  enrichment stages fail for reasons that have nothing to do with the code. Stage
  durations in the log are wall clock and include the sleep, while the enrichment
  deadlines count only awake time, so the two disagree wildly and the run looks
  broken when it is not.
