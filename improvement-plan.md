# Improvement plan

The live guarded roadmap. It is not approval to begin a listed item. Read
`AGENTS.md`, `current-state.md` and `project-purpose.md` first. Completed history
is preserved in `docs/archive/improvement-plan-through-item-16.md` and
`docs/archive/phase-b-completion.md`. The full evidence behind the current
direction is in `audit-2026-08-22.md`.

## Current status, updated 2026-08-26

| Work | Status |
|------|--------|
| Foundation and Phase A | DONE |
| Onboarding, identity and personal baseline | ENGINEERING COMPLETE |
| Item 20, voice and prosody primitives | ENGINEERING COMPLETE, release locked |
| Item 21, timestamped speech event candidates | ENGINEERING COMPLETE, release locked |
| Item 22, articulation and phonological patterns | ENGINEERING COMPLETE on a recorded no selection. **Variety probe defects repaired and uncertainty computed 2026-08-23; report is now `variety-probe-v1.2.0.json`. Items R1 and R2 done** |
| Item 23, motor speech and voice | **SHELVED.** Checkpoint 23A complete, 23B blocked on named human roles. Do not continue |
| Item 24, personalised recognition for atypical speech | SHELVED with item 23 |
| Former Phases D and E, coaching product and clinical validation | **REMOVED.** The project has no product and makes no clinical claim |
| Research release track | R1 through R5 DONE. **The public repository, the `v0.1.0` tag and the Zenodo DOI all exist as of 2026-08-26 and must not be created again.** R6, the honest account, is **written** as `findings.md` on 2026-08-26 and **not yet published**: putting it in the public repository needs a snapshot rebuild, and the two release tool defects stand in the way |

`speech_sound_patterns/engineering-plan.md` is the authority for item 22 and
carries every checkpoint's brief, numbers and acceptance evidence.
`motor_speech_voice/engineering-plan.md` is the corresponding authority for the
shelved item 23.

## 1. Measurement boundaries

Every output belongs to one of three claim levels:

1. **measured observation** with provenance and uncertainty;
2. **interpretation**, marked as such and mechanically verified against stored
   evidence;
3. **screening or clinical conclusion**, which this project does not produce and
   which no roadmap item leads to.

Binding scientific rules:

- Never turn missing or unreliable evidence into a score.
- Keep measurements, listener perceptions, interpretations and outcomes separate.
  Never pool truth classes.
- A language model may explain evidence but may not create measurement truth.
- Prefer declared references over inferred ones. Never classify a speaker's
  accent.
- Where documented varieties legitimately differ, the opportunity is unscorable.
  A variety mismatch may be excluded and never subtracted.
- Accuracy and reliability are different. A repeatable measurement can still be
  wrong.
- Development, tuning and evaluation data are separated by participant.
- A software snapshot is not independent truth, and agreement between two systems
  is not evidence.
- Sources overlapping a candidate's training lineage cannot qualify that
  candidate. **The rule was never applied to the variety probe's own scoring
  model. Item R2 declared that overlap rather than resolving it; resolving it is
  deferred and is described in section 5a.**
- Freeze the analysis before looking at the result. A recorded no selection is a
  legitimate completed outcome.
- New metrics require a construct definition, task, confounders, failure
  behaviour, truth source and validation plan.
- Preserve raw evidence needed for audit.

## 2. Current engine

Supports explicit solo and conversation runs; isolated input and output
directories; audio quality preflight; transcription, speech timing, pauses,
attribution, acoustics and language measurements; evidence and uncertainty
metadata beside measurements; optional enrichment with safe failure states;
evidence linked claims with independent verification; reproducible provenance and
pinned dependencies; truth separated regression tests; reliability and fairness
audit infrastructure; and versioned research contracts and validators for
onboarding, pronunciation research, data model, personal baselines, voice and
prosody, fluency events and speech sound patterns.

Important current limitations:

- The available real recordings are Adam's own and are not representative
  validation data. **They cannot enter the public snapshot.**
- Fairness is `not_evaluated`. Missing subgroup evidence is not a fairness pass.
- Personal progress metrics remain blocked because repeated human productions,
  measurement error, natural variation and meaningful change are not established.
- Pronunciation research has no active word pack, selected provider, human
  labelled benchmark result or released measurement.
- The variety probe was repaired at item R1 and its uncertainty computed at item
  R2. Its live report is `variety-probe-v1.2.0.json`; versions 1.0.0 and 1.1.0 are
  superseded and fail validation. Nothing at group level is distinguishable from
  zero, the `t` differential fails correction, and one per consonant result
  survives, `ð` for British speakers, carrying a lexical confound that stops it
  being a claim about British English.
- Transcription has an offline path as of item R3, chosen with
  `--transcriber local` and never used as a fallback. It cannot detect a second
  voice in a solo recording and cannot run the four fluency families that need a
  word level ASR confidence, and it declares both as unavailable rather than
  returning nothing. Conversation mode still needs a Hugging Face token for
  diarization; a solo run **on that path** needs no credentials at all. The
  default transcriber is AssemblyAI, so a run with no flags is not the
  credential free path.
- The pipeline's output is `master.json`. The language model interpretation
  layer is opt in through `--interpret` as of item R5, produces no score and no
  rating of a person, and states in its own verification report what that
  verification does not demonstrate.

Protected renderer constants may change only through a separate labelled
calibration study:

- `DRAG_RATIO = 2.6`, `DRAG_MIN_S = 0.50`, `DRAG_PERCENTILE = 95`
- `LOUD_DB_ABOVE = 5.5`, `RISE_RATIO = 1.18`, `RISE_MIN_HZ = 15`

## 3. Binding engineering workflow

- Follow `AGENTS.md`, work on one approved improvement at a time, preserve plan
  order.
- **Never commit or push.** Adam performs every commit.
- Explain an item simply before beginning and wait for Adam's explicit go.
- Run proportionate tests and a full isolated pipeline acceptance recording
  between implementation items unless Adam approves a documentation only
  exception. Real runs with his recordings are pre approved at his cost.
- Never append test runs to `history.json` or `progress.md`.
- Do not rename output files, remove `master.json` fields, weaken verification, or
  alter protected renderer thresholds as a side effect.
- Do not reintroduce a score, rating, index, level or summary number describing a
  person. Item R5 deleted five of them on 2026-08-24 and introduced no
  replacement.
- Every stage must remain runnable from the repository root, and every changed
  Python file must compile.
- Transcription is load bearing. Other enrichments retry once, then degrade with
  an explicit safe status.
- Report a 429 quota response and do not hammer retries.
- Tests and acceptance runs use isolated output directories.

## 4. Completed work summary

Foundation items 1 through 5 added deterministic language measurements, word
boundary correction, prototype history and stronger numeric verification.

Items 6 through 15 made the engine structured, failure safe, isolated,
reproducible, solo ready, quality gated, uncertainty aware, evidence linked,
regression tested and auditable for reliability and fairness.

The contract phase defined the onboarding assessment, locked pronunciation and
intelligibility research, durable account and session identity, separate consent
and data controls, and evidence gated personal baselines. Detailed decisions are
archived in `docs/archive/phase-b-completion.md`.

Items 20, 21 and 22 are engineering complete and scientifically release locked.
Item 22 recorded `no_selection` twice under unchanged gates, wrote that down as a
closed decision, corrected its own evidence record after an open search disproved
claims it had stated as fact, acquired an openly licensed reference stack, measured
the reference variety probe, and sealed all held out participants without scoring
them.

## 5. Research release track

**None of this is approved.** Each item needs its own explicit go.

Adam settled the scope on 2026-08-23. **The target is a clean public repository
with a citable release and an honest written account, not a peer reviewed paper.**
A peer reviewed submission was considered and declined: it needs a phonetician
collaborator, carries real rejection risk, and would take six to twelve months for
credit the smaller route mostly delivers. The smaller route is the floor and the
ceiling until Adam says otherwise.

Two consequences bind the order below. Statistics are still done properly, because
publishing a wrong number is worse than publishing nothing, but they stop at
honest intervals rather than at what a reviewer would demand. And the release
itself is the deliverable, so anything that does not make the release better is
deferred rather than sequenced.

### R1. Repair the variety probe defects — **DONE, 2026-08-23**

The published numbers were wrong and are now corrected. Outcome in
`audit-2026-08-22.md` section 6. Two findings were retracted rather than
refined, and the rescored evidence is the basis for everything below.

What was done:

1. Applied the `prompt_pack.py` normalisation table to the probe inventory, then
   applied the table's own test, that a phone the model never emits must not be
   scored, across the whole inventory rather than to one phone. It caught six
   families: the five conditioned palatals and the glottal stop. The glottal stop
   is excluded rather than renamed, because coda t glottalling is a real variety
   difference and renaming it would subtract the difference.
2. Diagnosed pre consonantal coda `ɹ`. It is a segmentation mismatch, not a model
   weakness: the aligner writes vowel plus `ɹ` as two segments and the model
   carries six combined tokens, so the expected standalone segment owned no
   frames. Merged, with the 9 percent that has no combined token left unscorable.
3. Rebuilt the sample, byte identical in selection, and rescored all 2,400 clips.
4. Regenerated the report as `variety-probe-v1.1.0.json` and reworked the
   validator, which previously required the retracted rhotic effect to be
   positive and now refuses it. Superseded evidence, sample and report retained.

Deliberately not done, because both would be scope expansion after seeing
results: scoring the merged r token, which would move the probe past its frozen
consonants only contract, and adding the aspirated stops `pʰ tʰ kʰ`, which are in
the sequence and have never been scored. The second is a pre existing scope limit
that produces no false flags. Both are recorded, neither is a defect.

Out of scope and untouched: any gate, the sealed held out participants, system
selection, and the frozen SpeechOcean762 benchmark.

### R2. Establish uncertainty — **DONE, 2026-08-23**

The probe reported point estimates and nothing beside them. It now reports what
they are worth. Everything below read
`.research_data/speech_sound_patterns/variety-probe/evidence/`, the stored per
clip evidence, so there was no re inference, no acquisition and no cost.

The rules that could have been bent to rescue a result were frozen first, in
`speech_sound_patterns/variety-probe-uncertainty-contract-v1.0.0.json`, before a
single interval existed. Only denominators were inspected before freezing, and
one count in that contract was got wrong and is corrected in the open inside it.

What was done:

1. Speaker clustered bias corrected and accelerated bootstrap intervals, 10,000
   resamples, stratified within source, one resample serving every reference,
   threshold and consonant so the paired design stays paired. Percentile
   intervals published beside them.
2. The per consonant analysis now aggregates per speaker and then averages,
   matching the group level analysis, which it previously did not.
3. Multiple comparison correction inside families declared in advance, with
   uncorrected, Benjamini Hochberg and Bonferroni published together. Thresholds
   and the second reference were declared as sensitivity dimensions rather than
   family members, with the reason written down, and a sceptical family spanning
   the whole grid is computed and published regardless of what it shows.
4. The threshold sweep reported as a curve with bands.
5. The Common Voice training lineage overlap **declared, not resolved**.
6. The detectable effect stated from the observed spread rather than assumed.

**What it found.**

- **Nothing at group level is distinguishable from zero.** All five pre
  registered comparisons have intervals containing zero and none reaches
  significance even uncorrected. This design could only reliably detect an
  Australian differential of about 0.0146 and the observed one is 0.0039, so it
  is a look too small to tell rather than a demonstration of no difference.
- **The `t` differential does not survive**, which is the question this item was
  created to answer. It reaches the uncorrected five percent level at one
  threshold only, the one designated for per consonant reporting, is not
  significant at three of the other four, changes sign at the fifth, sits below
  the smallest difference detectable for that consonant, and is removed by both
  corrections across its declared family of 22.
- **One test survives correction and it is British.** `ð`, British minus American
  under the American reference, holds its sign and rough size at all five
  thresholds and under both references and survives Benjamini Hochberg and
  Bonferroni alike. It is reported with the confound that stops it being a claim
  about British English: the groups read effectively disjoint prompt sets, 34
  shared prompts out of hundreds, so variety is confounded with lexical material.
- **The two references do not create the same scoring opportunities.** Only 8 of
  25 consonants keep their opportunity count within two percent across the swap.
  The `t` target gains about 28 percent under the British reference. Most cross
  reference comparisons are therefore not like for like, and this withdraws the
  support for one sentence of the version 1.1.0 report, that the `t` gap nearly
  disappears under the repaired reference.

The report is `variety-probe-v1.2.0.json`. Versions 1.0.0 and 1.1.0 stay
committed and deliberately no longer validate. The validator's requirement
inverted deliberately: it previously required `uncertainty_state` to stay
`not_computed` and now refuses a report that has lost it, refuses a family
widened after the fact, refuses a survivor list its own members do not support,
and refuses the surviving result stripped of its confound.

**Scaled down from the earlier plan, and still deferred:** a logistic mixed
effects model and a prompt matched robustness check on the 34 shared prompts were
listed when the target was a peer reviewed paper. They remain good work and
remain unnecessary for an honest public release. Do them only if Adam reopens the
paper route.

### R3. Offline path — **DONE, 2026-08-23**

The pipeline runs with no paid credentials. `--transcriber local` transcribes on
the machine instead of sending audio to AssemblyAI, and writes the same
`transcript.json` shape, so no later stage changed.

**There is no fallback between the two paths.** A missing key fails the run. The
two do not produce the same evidence, and a record that could have come from
either is not a record at all, so every run states which produced it in the
transcript and in provenance.

What the measurement decided, rather than the assumption. Whisper tidies speech
up and this project measures the untidy parts, so the local path was tested
before it was chosen. Disfluency retention turned out to be a decoding problem
and not a model size one: unprimed, both a small and a large model returned none
of the reference recording's five filled pauses, and primed with a short prompt
of filled words, both returned all five. The large model cost five times the
runtime and a three gigabyte download to move word agreement by about half a
percentage point, so the local path uses the small model with priming. Its own
cost runs the other way: it reported eight filled pauses where AssemblyAI
reported five, and whether the extra three were missed by one system or invented
by the other cannot be settled without someone listening.

Two capabilities do not survive the switch, and both are **declared unavailable
rather than silently returning nothing**, because a zero would read as none
found when the truth is not measured.

- **Second voice detection in solo recordings.** Whisper produces no speaker
  labels and the contamination check reads them. It now records
  `no_speaker_clusters_available_v1` and says the recording was not checked at
  all. Conversation attribution is unaffected, because it comes from diarization.
- **The four text derived fluency families.** This one was found by running the
  path rather than by reading the code, and it is the substantive result of the
  item. The forced aligner's per word score is not an ASR confidence: it is a
  different quantity on a different scale, and the fluency contract's eligibility
  floor was calibrated against a provider's posterior. On a real recording the
  aligner scored a genuine repeated phrase at 0.307 and 0.154, so thresholding it
  as a confidence **discarded a real repetition while appearing to work**. The
  local path now writes that score as `alignment_score`, emits no `confidence`,
  and the four families that need one report themselves unavailable. The fifth,
  prolonged sounds, reads timing and returned the same candidates on both paths.
  **No fluency threshold was retuned.** Recalibrating a release locked contract
  to a new provider's numbers is exactly the accommodation this project refuses.

The evidence is `docs/offline-transcription.md` and
`docs/offline-transcription-comparison-v1.0.0.json`. The fluency artifact schema
and algorithm versions moved to 1.1.0 because behaviour differs on an input that
only became reachable here.

Also recorded: the pyannote gate is documented rather than removed, so the fully
credential free configuration is the solo path.

### R4. Sanitized public snapshot and a citable release — **DONE, 2026-08-24. PUBLISHED 2026-08-26**

1. Add a `LICENSE` recording GPL 3.0 or later, plus attribution for the MFA
   dictionaries and Wiktionary derived material.
2. Fresh `git init` in a separate directory, no old remote, excluding `audio/`,
   `output/`, `history.json` and `progress.md`.
3. Replace the personal recordings with a synthetic or openly licensed fixture and
   repoint `regression/truth/`, `README.md`, `AGENTS.md` and the engineering plan.
4. Strip `the owner's home directory` paths, AssemblyAI CDN URLs and transcript job
   identifiers.
5. Declare `panphon` and `espnet2`, or state that they belong to isolated research
   environments.
6. Verify with the checks recorded in `audit-2026-08-22.md` section 3 before any
   first push.
7. Tag a version and archive it for a DOI, and add `CITATION.cff`.

**This repository is never made public. R4 produces a different repository.**

**What was built.** `release/` holds the whole transformation, declared rather
than scripted: a snapshot contract naming every exclusion, substitution and
overlay with its reason, a builder, and a verifier that refuses a snapshot the
contract did not describe. The snapshot is a separate repository, staged and
uncommitted, at `../evidence-guarded-speech`. 41 of 2,835 files are withheld.

Four things are worth carrying forward.

- **The fixture problem was a licensing problem.** Both candidate sources on
  disk were marked `rehosting_permitted: false` by this project's own manifests.
  LibriSpeech's block turned out to be a conservative default rather than a legal
  one, because it is CC BY 4.0 with no terms of service layered on top, and
  Common Voice's is real, because access came through a platform contract. The
  decision, its scope and its reasoning are in
  `release/redistribution-decision-v1.0.0.json`, which qualifies the manifests
  rather than editing them. The fixtures are assembled from development split
  speakers only, so publishing one cannot expose a sealed split.
- **The probe is now reproducible by anyone.** A 5 MB pseudonymised evidence
  bundle regenerates `variety-probe-v1.2.0.json` byte for byte in about two
  minutes, needing only numpy. No audio is redistributed and none may be. Stored
  evidence carried each contributor's verbatim Common Voice identifier, which
  joins straight back to the public corpus; the bundle mints opaque keys, and the
  mapping is never written to disk.
- **Frozen records are copied unmodified, and that is computed rather than
  listed.** 69 tracked files have their hash pinned by another. Substituting a
  string inside one broke the selection record and the final acceptance contract
  on the first attempt. The builder now identifies pinned files and reports the
  substitutions it withheld instead of applying them, because a published
  repository whose own integrity checks fail is worse than one carrying a cloud
  resource name.
- **What cannot be published now says so.** 86 tests need either the private
  research corpora or the working repository's git history. They skip with the
  reason rather than erroring, in the same way the pipeline declares a
  measurement unavailable rather than returning a zero. The snapshot runs the
  same 974 tests as this repository.

**All of that is now done.** On 2026-08-26 Adam made the first commit `dd7274c`,
created <https://github.com/adamalshoomary-ctrl/evidence-guarded-speech> as a
public repository, pushed it, tagged `v0.1.0`, and enabled the Zenodo archive
before creating the release, which is the order that matters because Zenodo only
mints a DOI for a release published after its switch is on. The concept DOI is
`10.5281/zenodo.22106996` and the `v0.1.0` version DOI is
`10.5281/zenodo.22106997`; both are recorded in `CITATION.cff`, whose repository
URL is no longer a placeholder. **None of it may be done again.**

The release also found two defects in the release tooling itself. They are
described in `current-state.md`, they are not fixed, and fixing them is unstarted
work: `build_snapshot --force` destroys the destination's `.git`, which is now
the git history of a public repository, and `verify_snapshot` refuses every
release after the first because it asserts the snapshot has no remote and no
commits.

Publishing also starts the six month public history clock that JOSS requires, at
no cost, which is the only reason to care about the clock while the paper route
is closed.

### R5. Decide what the system's final output is — **DONE, 2026-08-24**

This was the last engineering item. It ran before the written account, because
the account describes the system and the system has now changed.

**The problem.** The pipeline currently ends by asking a language model to score a
person 0 to 99 on CLARITY, WIT, WARMTH, PRESENCE and STORY. Those scores are
language model output parsed by regular expression against hand written anchors.
They are not validated measurement scales, they presume an audience of people
wanting feedback on their speaking, and `project-purpose.md` says in as many
words that this project's audience is researchers and engineers and **not people
seeking feedback on their speaking**. `pipeline/evaluate.py` still opens its
prompt with "You are an elite speech and communication coach".

**Do not start from the recommendation that was put to Adam.** It argued that the
scores should go but that the claim ledger is the most publishable thing in this
repository and must be kept so it has something to verify. The first half is
right. **The second half was checked on 2026-08-24 and does not survive.** Read
`prior-art-2026-08-24.md` before touching anything here. In one paragraph: the
pattern is statcheck's, from 2015, embedded in journal peer review; Wiseman et al.
2017 verified generated numbers against source records; Proof-Carrying Numbers
specified this project's exact verifier generically in September 2025; and
SpeakerCard-1M did tool first, model last, then entailment checking of the prose
against the structured premises, in speech, in June 2026. Open implementations of
the general pattern are commodity.

#### What was decided, and why

**1. Delete the five scores. Keep the claim ledger and the verifier.**

Deleting them is not actually available. `claim_ledger`, `evaluation_claims` and
`verification.md` are named inside **nine, one and one checksum pinned item 22
records** respectively, including `final-acceptance-contract-v1.0.0.json` and
`final-evidence-v1.0.0.json`, mostly as release boundaries saying the fluency
artifact never reaches them. Removing them would leave frozen evidence naming
things that do not exist, and item R4 established that pinned records are copied
byte for byte rather than edited. Verified with
`release.build_snapshot.checksum_pinned`.

That is the reason to keep them. Not that they are novel.

**2. `master.json` becomes the default output. The interpretation layer becomes
opt in and is off by default.**

This is a normal research tooling architecture and not an odd one; the evidence
is in `prior-art-2026-08-24.md`. A run with no flag produces measurements,
provenance, uncertainty and abstention, and stops. The listener, evaluator,
referee, claim ledger and verifier run only when explicitly asked for.

**3. The model describes the measurements. It does not judge the person.**

Rewrite the prompt so the model has no persona, no scores, and no licence to
characterise the speaker. Everything it says must resolve to an entry in the
evidence catalog, and it may not make a claim about a measurement the pipeline
declared unavailable or low quality.

**4. Fold in the coaching vocabulary that is free to move, and leave what is
frozen.**

Checked on 2026-08-24 with `release.build_snapshot.checksum_pinned`:

- **Free to rename**, no pinned record names them: `coaching_interpretation`,
  `single_recording_coaching`, `coaching_processing`,
  `coaching_scores_are_progress_measures`, `research_only_not_coaching_evidence`,
  `stat_scores`, the five score names, and the `--quality-policy coaching` value.
  Rename them. Bump the schema version of any versioned contract that carries
  them, and record the old name as superseded inside the new version.
- **`--quality-policy coaching` is also actively misleading**, because it is the
  lenient policy that warns where `baseline` fails. `lenient` is the honest name.
  The pinned record that mentions `quality_policy` carries the value `baseline`,
  so renaming the other value breaks nothing.
- **Frozen and left alone**: the release boundary keys inside pinned item 22
  evidence, `"coaching": false` in `candidate-evidence-v1.0.0.json`,
  `final-evidence-v1.0.0.json`, `local-benchmark-v1.0.0.json` and
  `local-benchmark-repair-v1.0.0.json`, and
  `coaching_progress_screening_or_diagnosis_output` in
  `variety-probe-v1.2.0.json`. They are negations recording that those items
  release no coaching output, they remain true, and editing them would break the
  records that pin their hashes.

**5. State plainly what verification does and does not demonstrate.**

Once the scores are gone the model's numeric claims are largely restatements of
`master.json`, so the verifier is checking that a copy operation copied
correctly. The last acceptance run found 6 numeric claims, verified 6 and caught
nothing; the only demonstrated catch is the synthetic `wrong_speaker_claim` case
in `regression/harness.py`. **Verification is only as interesting as the model's
freedom to be wrong.** Say so in the artifact and in the account, rather than
letting a clean verification report imply more than it earned.

#### Consequences, checked rather than assumed

- **`history.json` and `progress.md` cost almost nothing, and one of them is
  already broken.** Both were last written 2026-07-18. The personal progress
  contract landed 2026-07-20 and forbids
  `improving_and_slipping_labels_allowed_without_goal_specific_evidence`, yet
  `progress.md` still reads "Clarity: 55 -> 63 (improving)". Nothing in the
  current code emits that; it is a five week old artifact violating a contract the
  code now enforces. Both files are already excluded from the public snapshot.
  Removing the scores empties `stat_scores` and lets `pipeline/history.py`
  `extract_scores` be deleted, which is a duplicated regular expression parser
  whose own comment admits it mirrors `evaluate.py`.
- **The regression fixtures are untouched.** `fixture_conversation` and
  `fixture_solo` check only `master.json` meta: recording type, speaker count,
  duration and byte hash. `synthetic_controls` covers valid and invalid evidence
  verification and the deterministic snapshot pins `valid_claim: pass` and
  `wrong_speaker_claim: fail`. Those survive because the verifier survives.
- **A real acceptance run is required and the offline path will not do.**
  Changing the prompt changes `evaluation.md`, the claim ledger and the numeric
  claim count, and the listener and evaluator need a provider. Run the
  conversation recording with the provider path, then run the regression harness.
- **The public snapshot must be rebuilt afterwards**, and the overlay hash for
  `AGENTS.md` re recorded if that file changes.

#### Out of scope

The five scores are deleted rather than replaced. No new scale, index or summary
number is introduced. No gate, threshold, frozen contract or sealed participant
is touched. The variety probe is not reopened.

#### What was built

**The default output is the measurement record.** `python3 pipeline/run_all.py`
now produces `master.json` and stops. A side effect worth having: a default solo
run with `--transcriber local` now makes no remote call at all and finishes in
about 70 seconds, where before it always called the listener and the evaluator
and degraded them when no key was present. The listener, the interpretation and the
claim verifier run only under `--interpret`, and none of their files are even
declared as expected outputs otherwise.

**The referee stays on by default, and that departs from the brief above.** The
brief listed it among the stages becoming opt in. It corrects speaker labels
inside `master.json` rather than commenting on them, so it is measurement, and
making it optional would have changed default speaker attribution silently.
Adam took the recommendation on 2026-08-24.

**The five scores are gone**, with the prompt's persona, its rubric, its drill,
and the duplicated regular expression parser that read the scores in both
`evaluate.py` and `history.py`. `HISTORY_RECORD_VERSION` is 3.0.0 and writes no
`stat_scores`. Existing 2.0.0 records are left exactly as they are.

**The `prescription` claim type was withdrawn rather than renamed.** It was the
only claim type permitted to exist with no evidence, and it existed so the
report could tell a person what to practise. Every claim now requires evidence,
which makes verification strictly stricter rather than weaker. Claim ledger
schema is 1.1.0; `coaching_interpretation` became `interpretation`.

**A deterministic run record now opens `evaluation.md`.** Removing the model's
licence to characterise the run would otherwise have lost information, because
audio quality, contamination, enrichment outcome and measurement availability
could no longer be stated by anything. They are facts about the run, so code
renders them from `master.json`: conditions, every warning with what it affects,
and every withheld measurement with its reason. The block is delimited by HTML
comments and excluded from claim checking, because verifying it against
`master.json` would verify the renderer against itself. The evaluator refuses
any model report containing an HTML comment, so nothing can smuggle prose in
through the delimiters.

**Two things were found while building it, neither in the brief.**

- The evidence catalog contains no path for audio quality or for an unavailable
  measurement, so the old prompt's own quality and measurement discipline rules
  asked for statements that could not carry evidence and therefore could not
  pass the ledger. That is a plausible contributor to the repeated
  `semantic_validation_failure` degradations in this repository's stored runs.
  The deterministic record removes the demand rather than relaxing the check.
- A default run left `listener` and `evaluator` at status `pending`, which
  describes a stage about to happen. They are now `not_requested`, and each
  stage sets itself `pending` when it actually starts.

**A third defect appeared only because real runs were done, and it is worth
recording.** On two of five real evaluator responses the provider returned the
whole markdown report as a single line, with its line breaks written as a
literal placeholder: backslash n on one run, slash n on another. It renders as
a wall of text and **passes claim checking**, because every marker is present
and in order, so nothing in the verifier notices. A narrow deterministic repair
now restores the breaks, firing only when the report contains no real line
break at all and a placeholder appears at least twice, and `evaluation_claims.
json` records that it happened rather than repairing it silently. This is a
small instance of the general point: the verifier checks the claims, not
whether the artifact is readable.

**The evaluator still degrades sometimes, and that was not fixed, only reduced.**
One acceptance run failed both attempts, on `numeric_claim_without_direct_value`
and then on a repeated claim marker, and degraded safely to an explicit
unavailable report with the run record intact and `master.json` untouched. The
prompt's marker and numeral rules were made explicit and the next runs passed
first time at 18, 24 and 24 claims with zero issues, but three passes are not a
reliability measurement and this should not be described as solved.

**`verification.md` now states what it does not demonstrate**, in the report
itself rather than only in the plan: that the model's numeric claims are largely
restatements of values it was handed, that verification is only as interesting
as the model's freedom to be wrong, that in production it has never rejected a
claim, and that the failure that matters carries no arithmetic at all.

**Renamed vocabulary, with every version bumped and the old name recorded as
superseded inside the new version.** `--quality-policy coaching` became
`lenient`, which is what it always was. Contracts at 1.1.0: the data model, the
assessment manifest, the progress model and its reliability registry, fluency
events, and voice prosody. `coaching_processing` became
`speech_measurement_processing`; `single_recording_coaching` and
`single_session_coaching` became `..._interpretation`; the release limit
`coaching_interpretation` became `released_interpretation`;
`coaching_scores_are_progress_measures` became
`model_scores_are_progress_measures`; the assessment's `product_scope` became
`protocol_scope` and its protocol identity, title and purpose stopped
describing a coaching product. **Every frozen name was left alone**, verified
with `release.build_snapshot.checksum_pinned` against 73 pinned files rather
than assumed: the item 22 release boundaries, and the three `normal_coaching`
keys inside the pinned `assessment/pronunciation-research-v1.0.0.json`.

**Acceptance.** 994 unit tests pass, up from 974. Full conversation runs on the
real recording through the provider path, both default and `--interpret`. The
regression harness passes its software snapshot and its synthetic controls,
including the deterministic pins `valid_claim: pass` and
`wrong_speaker_claim: fail`, which are the verifier's only demonstrated catch,
and `real_conversation` passes 4 of 4 artifact checks against a real run. The
public snapshot rebuilds and verifies clean, 2,803 files published and 41
withheld, and its own suite runs the same 994 tests with the same 86 documented
skips. It was built to a scratch directory rather than over
`../evidence-guarded-speech`, because that snapshot is staged, uncommitted and
Adam's to commit; the real rebuild belongs after his commit here.

**What was deliberately not done.** `progress.md` still contains the five week
old "Clarity: 55 -> 63 (improving)" line. Nothing in the code can emit it now,
and the file is excluded from the public snapshot, but the stale file itself
survives. Regenerating it means running the current renderer over Adam's real
`history.json`, which is his personal data, so it is his call and not a side
effect of this item.

### R6. The honest account — **WRITTEN, 2026-08-26. NOT YET PUBLISHED**

**What was built.** `findings.md` at the repository root, 1,044 lines, plus
a pointer to it at the top of `README.md` so a reader arriving at the public
repository finds the account before the operating reference. It leads with the
self correction, states the narrowed claim in the exact required wording, and
relates the project to arXiv 2606.16019 and 2606.11639, both of which were read
in full rather than from their abstracts.

Every figure in it was recomputed from the stored evidence records rather than
carried forward from prose. That found three things, recorded in the account's
own section 9:

- **A false claim in `current-state.md`, now corrected.** It said a default solo
  run makes no remote call. `DEFAULT_TRANSCRIBER` is `assemblyai`, so that holds
  only with `--transcriber local`. This plan stated the scope correctly and the
  summary dropped it.
- **A solo run reports the referee as `pending` forever.** Solo mode never
  schedules that stage, so `initial_enrichment_status` leaves it describing a
  stage that will never happen. This is the defect R5 fixed for the listener and
  the evaluator, left behind for the referee. **Not fixed.**
- **Claim type is not tied to evidence class.** A claim whose only evidence has
  source `listener_perception` can be typed `measured_observation`, and both the
  prompt's definition and the verifier permit it, so a model's subjective
  impression can sit in the ledger in the same class as a timestamp. Found on a
  real run. **Not fixed**, and it is the more interesting of the two.

**The draft was fact checked against the stored records a second time, and that
pass earned its place.** It found the account quoting the t differential at the
superseded pooled aggregation, +0.0269, inside a sentence describing the per
speaker analysis that produced +0.0362; the same error for v; a claim that all
48 tests were pre registered when only the 5 group level ones were declared
before the run; "the three optional model stages use Gemini" when the referee is
not optional; the sensitivity family survivor described as at a neighbouring
threshold when it is two steps away; and a pinned file count of 75 taken over
all tracked files rather than 68 over the files the contract selects. All are
corrected, and the account's closing note records the three that mattered rather
than hiding them.

It also found that `prior-art-2026-08-24.md` dates SpeakerCard-1M to 28 June
2026. It is 2 June: the arXiv identifier 2606.03283 sits far below 2606.11639
and 2606.15325, which are 10 and 13 June. The conclusion is unaffected. That
file is otherwise accurate; its three load bearing citations were checked
against arXiv directly and all three match.

Two figures could not be verified and are therefore not asserted in the account:
this plan and `current-state.md` disagree on the acceptance run claim counts, 18,
24 and 24 against 18, 24 and 16, and neither is recoverable from a committed
artifact. The account says three consecutive runs passed with zero issues and
gives the count only for a run made on 2026-08-26 to check that section, which
verified 11 of 11.

**Acceptance.** 994 unit tests pass. A real solo run through the local path
completed in 88 seconds with no remote call, and a second with `--interpret`
completed in 167 seconds. The regression harness passes its software snapshot
and its synthetic controls, including the pins `valid_claim: pass` and
`wrong_speaker_claim: fail`. `findings.md` carries no forbidden identifier under
the snapshot contract's own token and pattern checks.

**What remains, and it is Adam's call.** The account exists in this repository
and is not yet in the public one. Publishing it means rebuilding the snapshot,
which runs into the two known release tool defects recorded in
`current-state.md`: `build_snapshot --force` would destroy the public
repository's `.git`, and `verify_snapshot` refuses every release after the
first. Neither is fixed. Those should be dealt with properly rather than
overridden, so publication is deliberately left as a separate decision.

**One privacy question for Adam before any publication.** Section 5 quotes four
claims from a real run on his own solo recording, including a model's
characterisation of his delivery as "a very soft, breathy whisper with extremely
low energy". They are the concrete evidence for the sharpest finding in the
account and the section is much weaker without them, but they are derived
personal content about him and publishing them is his decision, not a side
effect of this item.

#### The original brief

A written record of what was built, what was measured, what was found, and what
could not be established at all. Not a paper and not a submission.

The material that matters most is the part most projects omit: item 22 recorded
`no_selection` twice under unchanged gates, the evidence record was corrected
after an open search disproved claims this repository had stated as fact, and the
variety probe's headline finding was retracted after its own method was applied to
itself. Two of those three are documented self correction. That is the strongest
thing here and it should lead.

Read arXiv 2606.16019 and arXiv 2606.11639 first and say plainly how this relates
to them. Both are about phonetic transcription and phoneme recogniser bias, which
is the variety probe's subject matter.

**The novelty claim this item used to carry was checked on 2026-08-24 and had to
be narrowed. Read `prior-art-2026-08-24.md` before writing a word of this.** The
earlier instruction was to claim a reusable audit and abstention harness for
pronunciation measurement, which does not exist as open infrastructure. That
sentence is defensible only as a claim about **integration and licence**, and only
in this exact form:

> No open, reusable harness combines provenance on inputs, per measurement
> uncertainty, explicit abstention, and verification of generated claims, for
> speech measurement.

Everything narrower than that is taken. Cite rather than ignore: statcheck, which
has mechanically recomputed numbers stated in prose since 2015 and sits inside
journal peer review; Wiseman et al. 2017 and PARENT, which verify generated text
against source records; Proof-Carrying Numbers, which specified this repository's
numeric verifier generically in September 2025; and SpeakerCard-1M, which did tool
first, model last, then entailment checking against structured premises, in
speech, in June 2026.

Do not claim the invention of evidence guarded machine learning, which has
substantial prior art in data statements, datasheets, model cards and the
selective prediction literature. Do not claim the claim ledger is novel. And do
not let a clean verification report imply more than it earned: in production the
verifier has caught nothing, because verification is only as interesting as the
model's freedom to be wrong.

The account should say that the prior art check happened, that it cost the
project its most attractive claim, and that the claim was narrowed rather than
quietly dropped. That is a third documented self correction and it belongs beside
the other two.

## 5a. Deferred, with reasons

Neither is abandoned. Both lost their justification when the paper route closed,
and both are cheap to restart.

- **Acquiring the newly unblocked references.** Unisyn for a real Australian
  reference lexicon, Mitchell and Delbridge for 7,736 Australian speakers reading
  fixed sentences, L2 ARCTIC and Buckeye for the first usable expert phone level
  truth. All are now permitted by the direction change and all need their own
  manifest, licence snapshot and Adam's go. **Deferred 2026-08-23** because they
  were mainly there to strengthen a paper. Revisit after R6, when the released
  thing shows whether going further is worth it. Note what they still would not
  solve: no expert Australian produced phone truth exists at any licence and at
  any price. CoANZSE stays excluded on methodological grounds, because it was
  force aligned with an American model and would manufacture the bias it was
  brought in to detect, and AusTalk has no access route at all.
- **Rescoring the probe with a lineage independent phone model.** The scoring
  model `facebook/wav2vec2-lv-60-espeak-cv-ft` is fine tuned on Common Voice and
  the probe evaluates entirely on Common Voice 26 speakers, which this project's
  own rules disqualify elsewhere. Item R2 **declared** the overlap rather than
  resolving it, because resolving it needs a second phone recognition model with
  no Common Voice lineage rescoring the same 2,400 clips, which is a fresh
  inference pass and a new model manifest. **Deferred 2026-08-23.** The
  declaration that stands in its place: the direction of the bias is unknown, it
  plausibly favours the control group because Common Voice English skews American
  and British, and the observed result runs against it, so the null is
  conservative rather than suspect. That reasoning does not transfer to a future
  differential running the way the bias predicts, and such a result would need
  this item done first.
- **Measuring the model instead of the person.** The one route by which the
  claim ledger becomes a finding rather than a component: run several models over
  the same measurement records and publish how often each makes claims the
  evidence does not support. It has no human subject, no clinical exposure and a
  ready made comparison in *Prior over Evidence*, which measured 39.6 percent
  coherent but wrong reasoning across three models. **Deferred 2026-08-24** because
  it is paper shaped work and the paper route is closed, and because it needs
  several providers and their own transfer decisions. Nothing in R5 or R6 may
  claim this result in advance of doing it.

- **Extracting the audit and abstention harness.** The provenance, claim ledger and
  verification machinery is the reusable part and is the project's most defensible
  contribution. Deferred until the release establishes that anyone wants it. The
  0 to 99 CLARITY, WIT, WARMTH, PRESENCE and STORY scores in
  `pipeline/evaluate.py` must never enter it: they are language model output parsed
  by regular expression against hand written anchors, and are not validated
  measurement scales. The claim verification layer around them is the asset.

## 5b. Decided against

Recorded so they are not re proposed as though they were open questions.

- **A public API or hosted service.** Declined 2026-08-23. Every call would cost
  Adam money with no way to recover it, it would make him custodian of strangers'
  voice recordings under a statutory privacy tort that applies to him personally,
  and a free consumer facing service sits far closer to the regulated category than
  distributing source code does. The project has readers, not users. Ship a library
  and a command line tool that people run themselves. A Hugging Face Space with
  fixed example clips and no upload is an acceptable later demo; an API is not.
- **A peer reviewed paper.** Declined 2026-08-23 in favour of the smaller route.
  Reopenable, and R2 deliberately leaves the harder statistics listed rather than
  deleted so the route is cheap to restart.

## 6. Shelved and removed work

- **Item 23, motor speech and voice.** Shelved 2026-08-22. Blocked because the
  motor lane has no qualifying reference source in public at any licence and at any
  price, because acceptance requires written review by accountable human roles that
  do not exist, and because Queensland recording law and Australian ethics review
  follow Adam personally regardless of licence. It stands as completed evidence for
  why this project makes no clinical claim. Do not continue it.
- **Item 24, personalised recognition for atypical speech.** Shelved with item 23.
  It depends on participant work item 23 could not authorise.
- **Former Phase D, coaching loop, exercise registry and outcome validation.**
  Removed. There is no product.
- **Former Phase E, clinical validation and release governance.** Removed. The
  project makes no clinical claim, so there is nothing to validate clinically.

## 7. Deferred and prohibited shortcuts

- Do not restore WhisperX transcript voting without a new adjudication design and
  owner approval.
- Do not restore the removed vocal fry heuristic as a clinical detector.
- Do not create an arbitrary overall communication or prosody score.
- Do not treat agreement between black box APIs as reference truth.
- Do not optimise anyone toward one accent, dialect, voice, pitch or pace.
- Do not build an accent classifier.
- Do not reopen any item 22 gate, unseal held out participants, or select a system
  while repairing the probe.
- Do not propose work that assumes commercial use is possible.

## 8. Definition of done

The research track is complete when an independent person can obtain the public
repository, install it without paid credentials, reproduce the reported analysis
from published data, read an honest account of what was measured and what could
not be established, and disagree with it on the evidence.

Until then, describe this as an open research project on evidence guarded speech
measurement. Not a product, not a coach, and not a substitute for a speech
pathologist.
