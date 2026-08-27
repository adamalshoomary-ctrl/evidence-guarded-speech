# Current Project State

Updated: 2026-08-26

## Start here

- **Nothing is approved right now.** Ask Adam what outcome he wants before
  proposing or starting anything.
- The project changed direction on 2026-08-22, from commercial product backend to
  open research with no monetisation plan, permanently. See below.
- The last completed work was **item R5**, deciding what the system's final
  output is, finished 2026-08-24. **`master.json` is now the output.** A run
  produces the measurement record and stops; the listener, the interpretation
  and the claim verifier run only under `--interpret`. The five language model
  scores of a person are deleted and nothing replaces them. Full account in
  `improvement-plan.md` item R5. It is commit `134194b`.
- **The public release happened on 2026-08-26 and is done.** The sanitized
  snapshot built by item R4 is now published at
  <https://github.com/adamalshoomary-ctrl/evidence-guarded-speech>, public,
  GPL 3.0 or later, first commit `dd7274c`, withholding 41 of 2,844 files. It is
  tagged `v0.1.0` and archived by Zenodo. **The concept DOI is
  `10.5281/zenodo.22106996`**, which always resolves to the newest version and is
  the one to cite; `10.5281/zenodo.22106997` is the version DOI for `v0.1.0`.
  Both are recorded in `CITATION.cff`. Do not create the repository, the tag or
  the archive again: they exist. Read the release hazards below before rebuilding
  the snapshot. Before that, item
  R3 was the offline transcription path, which made the pipeline runnable with no
  paid credentials and found a cross provider defect: a forced alignment score was
  being compared against a threshold calibrated for an ASR posterior. Item R2 computed
  the variety probe's uncertainty, removing the last live per consonant result
  and leaving exactly one surviving test in the whole analysis. If
  `git status` is dirty when you arrive, that work may be uncommitted; ask Adam
  before touching it, and never commit yourself.
- **R6, the honest account, was written on 2026-08-26 as `findings.md`**, and
  `README.md` now points to it. It leads with the self correction, makes only
  the narrow integration and licence claim that survived
  `prior-art-2026-08-24.md`, and relates the project to arXiv 2606.16019 and
  2606.11639. **It is not yet published.** Publishing needs a snapshot rebuild,
  which runs into the two release tool defects below, and Adam has a privacy
  decision to make first about four quoted claims derived from his own
  recording. Both are set out in `improvement-plan.md` item R6. **This
  repository is never made public; R4 produced a different one.**
- **Three things were found while writing the account, by recomputing rather
  than rereading.** One was a false claim in this file about a default run
  making no remote call, now corrected below. The other two are code defects and
  are **not fixed**: a solo run reports the referee stage as `pending` forever,
  and a claim whose only evidence is a listener perception can be typed
  `measured_observation`, so a model's subjective impression can enter the
  machine readable ledger in the same truth class as a timestamp. The second is
  the one worth attention. Neither is approved work; both are described in
  `findings.md` section 9.
- **The goal is a public repository with a citable release and an honest written
  account, not a peer reviewed paper.** Adam declined the paper route on
  2026-08-23. He also declined a public API or hosted service, permanently. Both
  decisions and their reasons are in `improvement-plan.md` sections 5a and 5b; do
  not re propose either as though it were open.

Short handoff for a new agent: where the project is, what exists, what does not,
and what may happen next. `improvement-plan.md` is the authority for order and
engineering rules. `audit-2026-08-22.md` holds the full evidence behind the
direction change and every finding recorded during it; read it when you need the
detail, not by default.

## The direction change of 2026-08-22

The project was previously the measurement backend for a planned commercial
communication coaching application. **It is now an open research project with no
monetisation plan, permanently.** Adam decided this on 2026-08-22 after a full
repository audit.

Four consequences bind all later work.

- **Non commercial sources are now usable, and this is the main practical gain.**
  Commercial licensing was the binding constraint on this project's evidence for
  its entire life. Releasing it unblocks the Unisyn Australian reference lexicon,
  Mitchell and Delbridge, L2 ARCTIC, the Speech Accent Archive, MD_NLP, MAE VoiS,
  Sydney Speaks and Buckeye.
- **The unlock does not reach the hardest gap.** Only three corpora anywhere carry
  expert phone level pronunciation annotation: SpeechOcean762 (CC BY 4.0, Mandarin
  first language), L2 ARCTIC (non commercial, second language speakers) and EpaDB
  (Spanish first language). For first language English varieties the only sources
  are TIMIT (paid, and possibly not licensable to an individual) and Buckeye (free,
  non commercial, forty speakers from one city). **No expert Australian produced
  phone truth exists at any licence and at any price.** That standing fact survives
  the direction change unchanged.
- **The direction is one way.** Evidence built on non commercial sources can never
  underwrite a commercial product. Do not propose work that assumes otherwise.
- **The licence is GPL 3.0 or later**, because `praat-parselmouth` is GPL and is a
  hard runtime dependency of the acoustics stage. Item R4 added the `LICENSE`
  file, alongside `NOTICE.md` and `CITATION.cff`.

## The publication route, and the hard rule attached to it

**This repository must never be made public.** Not by flipping a setting, not
after deleting files. It tracks Adam's recordings, a two speaker conversation,
and full transcripts and evaluations derived from them, in the working tree **and
in Git history**. `audio/the owner's conversation recording 2.m4a` is the largest object in the
repository and exists only in history.

The route is a **separate sanitized snapshot**: fresh `git init`, no old remote,
none of `audio/`, `output/`, `history.json` or `progress.md`, and a synthetic
fixture replacing the personal recordings so an outsider can actually run the
pipeline. A history rewrite is rejected: it changes all 73 commit hashes anyway,
so it preserves nothing worth keeping, and it cannot prove completeness.

Credential hygiene is clean and was verified rather than assumed: `.env` has never
been tracked in any of the 73 commits, and a search of every reachable Git object
for the twelve live key values returns nothing.

## Facts that decide what happens next

Standing conclusions a new agent needs before proposing anything.

- **The claim ledger is good engineering and is not a novel contribution, and
  this was checked rather than assumed.** `prior-art-2026-08-24.md` is the record.
  statcheck has mechanically recomputed numbers stated in prose since 2015 and is
  embedded in journal peer review; Wiseman et al. 2017 verified generated numbers
  against source records; Proof-Carrying Numbers specified this repository's
  numeric verifier generically in September 2025; and SpeakerCard-1M did tool
  first, model last, then entailment checking of prose against structured
  premises, in speech, in June 2026. Open implementations of the general pattern
  are commodity. **The only surviving claim is about integration and licence**, in
  the exact wording held in the plan's item R6. Do not restore the wider claim.
- **Verification is only as interesting as the model's freedom to be wrong.** The
  R5 acceptance runs verified 18 of 18, 24 of 24 and 16 of 16 claims with zero
  issues and caught nothing. In production the verifier has never caught
  anything; the only demonstrated catch is the synthetic `wrong_speaker_claim`
  case in the regression harness. A clean verification report is not evidence of
  a strong verifier, and the failure that matters, unsupported interpretation
  rather than arithmetic, is one a numeric verifier cannot catch at all. Since
  R5, `verification.md` says all of this in the report itself.
- **The claim ledger cannot simply be deleted.** `claim_ledger`,
  `evaluation_claims` and `verification.md` are named inside nine, one and one
  checksum pinned item 22 records, including the final acceptance contract and the
  final evidence report. Deleting them would leave frozen evidence naming things
  that do not exist. The coaching release boundary keys inside those pinned
  records are frozen for the same reason and stay as they are.
- **Two defects were found while building R5, and both are fixed.** The evidence
  catalog contains no citeable path for audio quality or for an unavailable
  measurement, so the old evaluator prompt's own quality and measurement
  discipline rules asked for statements that could not carry evidence and
  therefore could not pass the claim ledger. That is a plausible contributor to
  the repeated `semantic_validation_failure` degradations in this repository's
  stored runs. A deterministic run record, rendered from `master.json` by code
  and excluded from claim checking, now states the conditions rather than asking
  a model to report on its own run. Separately, on a real run the provider
  returned the whole report as one line carrying 34 escaped line breaks; it
  rendered as a wall of text and still passed claim checking, because every
  marker was present and in order. It happened twice in five real evaluator
  responses, with a different placeholder each time, backslash n and slash n. A
  narrow repair restores the breaks only when the report has no real line break
  at all and a placeholder appears at least twice, and the ledger records that
  it happened. The general point is the useful one: the verifier checks the
  claims, not whether the artifact is readable.
- **The evaluator still degrades sometimes, and R5 reduced that rather than
  fixing it.** One acceptance run failed both attempts, on
  `numeric_claim_without_direct_value` and then on a repeated claim marker, and
  degraded safely: an explicit unavailable report carrying the full run record,
  with `master.json` untouched. The prompt's marker and numeral rules were then
  made explicit and the next three runs passed first time with zero issues.
  Three passes are not a reliability measurement. Do not describe this as
  solved.
- **`progress.md` has been violating a contract for five weeks.** It renders
  "Clarity: 55 -> 63 (improving)" from language model scores parsed by regular
  expression. It was last written 2026-07-18; the personal progress contract
  landed 2026-07-20 and forbids exactly those improving and slipping labels.
  Nothing in the current code emits them. Item R5 deleted the scores, so nothing
  can produce that line again, but **the stale file itself still says it.**
  Regenerating it means running the current renderer over Adam's real
  `history.json`, which is his personal data, so it was left for him to decide.
  The file is already excluded from the public snapshot.

- **Two narrow redistribution permissions now exist, and nothing else moved.**
  `release/redistribution-decision-v1.0.0.json` permits LibriSpeech audio for the
  regression fixture, and Common Voice derived non audio evidence for the probe
  bundle. It qualifies the item 22 manifests rather than editing them, and those
  manifests stay exactly as they were. **No Common Voice audio may be
  redistributed, ever**, and no other source gained anything. Sending Adam's own
  audio to any external provider is still excluded entirely.
- **The public snapshot is rebuilt, never edited by hand.** Anything that should
  differ between this repository and the public one belongs in the snapshot
  contract as a declared exclusion, substitution or overlay. An overlay whose
  private original has changed fails the build rather than falling silently
  behind it. Run `python3 -m release.build_snapshot` then
  `python3 -m release.verify_snapshot`, and never publish without the second.

- **Two release tools now have known defects, both found on 2026-08-26 during the
  first real release. Read this before rebuilding the snapshot.** Neither is
  fixed, and fixing them is unstarted work needing Adam's go.
  - **`build_snapshot --force` deletes the destination directory including its
    `.git`.** That was harmless when the snapshot had never been published. It is
    not harmless now: it destroys the local commit history and the `origin`
    remote of a repository that is public. It happened once, on 2026-08-26, and
    was recovered only because the commit was already pushed. **Do not run
    `--force` against `../evidence-guarded-speech`.** Build to a scratch
    directory with `--destination`, then `rsync -a --delete --exclude='.git/'`
    into place. If a wipe does happen, recover with `git remote add origin`, the
    repository URL, `git fetch origin --tags`, then `git reset --soft
    origin/main`.
  - **`verify_snapshot` refuses every release after the first.** Its `scan_git`
    section asserts the snapshot has no remote and no commits, which was true
    exactly once. Both findings are now permanent and expected, and the four
    checks that actually protect privacy, private content, structure, fixtures
    and evidence bundle, still pass and still matter. Read those four rather than
    the overall verdict, and do not let a check nobody can satisfy become a check
    that is always overridden. It should learn the difference between a first
    publication and an update.

- **The reference variety probe was repaired on 2026-08-23 and its numbers
  changed materially. `variety-probe-v1.2.0.json` is the report; versions 1.0.0 and
  1.1.0 are superseded records and no longer validate.** Mapping version 1.2.0 corrected
  six phone families the frozen model never produces for English, five conditioned
  palatals plus the glottal stop, and merged post vocalic r into the model's own
  combined token after establishing that the aligner writes it as a separate
  segment and the model does not. The whole sample was rescored, 2,400 clips, and
  the selection is byte identical to the superseded run, so the two are directly
  comparable. **Roughly half of every flag the probe previously produced was
  noise:** the American control flag rate falls from 0.1664 to 0.0863. Only
  1.5 percent of scoring opportunities were lost, because the palatals were
  renamed rather than discarded.

- **Two of the superseded report's findings were retractions, not refinements.**
  The rhotic effect does not exist: the Australian minus American onset rhotic
  differential is now −0.0004 against a previously reported +0.0300, because the
  old figure was pre consonantal coda r flagged at 96.6 percent in every group
  including the American control, multiplied by how often each group's prompts
  contained the context. And the recorded mechanism, that the reference swap only
  worked by declining to score, was itself an artifact of the same defect. The
  validator now refuses both if they return. Full numbers in
  `audit-2026-08-22.md`.
- **Item 22 reached a valid no selection outcome and nothing may reopen its
  gates.** Two frozen comparisons and a closed selection record all recorded
  `no_selection`. No candidate passed the unchanged gates, nothing is frozen
  forward, and no paid provider beat the free local stack. Three of the five
  original expert reviewers pass the current gates when scored as candidates, so
  the gates sit at roughly competent human level. A documented `no_selection` is a
  legitimate completed result and does not authorise more threshold searching, a
  weaker gate, or an early look at the sealed held out participants.
- **All 26 held out adults and 24 held out children remain sealed**, and all 40
  predeclared held out measures are explicitly unavailable, never zero, a pass or
  a failure. No private split, participant identity, label, audio or derived row
  has been opened.
- **Item 23 is shelved, and the reason is structural rather than administrative.**
  Only 5 of its 27 surveyed sources were blocked on commercial grounds, so the
  direction change barely helps it. It is blocked because the motor lane has no
  qualifying reference source in public at any licence and at any price, because
  acceptance is defined as written review by accountable human roles, and because
  Queensland recording law and Australian ethics review follow Adam personally
  regardless of licence. Its deliverable ledger records eight of thirteen
  deliverables blocked on a named human. It stays as completed evidence for why
  this project makes no clinical claims. Do not continue it.
- **Every reference this project measures against is American, and Australian
  English is non rhotic and far closer to British.** Checkpoint 22E8 performed the
  repair. The frozen SpeechOcean762 benchmark was deliberately not touched, because
  its reviewers judged against American English and an American reference is
  correct there.
- **Rhoticity is not measurable by this method, and that is the substantive
  finding.** Post vocalic r is excluded under both references, because the
  reference and the model disagree about whether it is a segment at all. It is the
  sharpest Australian and American consonantal difference and this class of system
  cannot evaluate it. With that segment removed the reference swap now leaves the
  American control approximately in place, +0.0025, while the Australian and
  British groups fall slightly, −0.0020 and −0.0015, which is the direction the
  contract predicted before the run. **Those movements are around a fifth of a
  percentage point and no claim rests on them** until speaker clustered intervals
  exist.
- **A variety mismatch may be excluded but never subtracted.** Running Australians
  through an American scorer and correcting the result using knowledge of their
  accent is rejected as a scoring method: the effect is systematic, its size cannot
  be measured without expertly labelled Australian speech, and a repeatable system
  doing this would report the same unfounded concern every time while its
  repeatability made the error look like evidence.
- **The British reference is the Montreal Forced Aligner English (UK) dictionary,
  not the WikiPron scrape.** The scrape places a post vocalic rhotic in 6.85 percent
  of entries against the dictionary's 0.01 percent, and carries 239 symbols against
  its 78. English (US) is held as the American counterpart so both paths share one
  phone alphabet and differ in variety alone.
- **The pack is written in broad phonemes, because the aligner's dictionary is
  narrower than English.** The normalisation table in
  `speech_sound_patterns/prompt_pack.py` is the authority, every entry carries a
  written reason, and an unlisted symbol refuses the word rather than being dropped.
  Anything reading these dictionaries should use it rather than starting a second
  table. This is also the fix for the probe defect above.
- **One Common Voice contributor is excluded from every comparison group**, having
  declared different varieties on different clips. A frozen exclusion record names
  them. No other pair of subsets shares a speaker or a clip.
- **All four speaker groups are split and sealed.** Common Voice release 26.0
  supplies Australian English at 55,922 clips from 804 speakers; British Isles at
  215,340 from 3,543; American male at 295,743 from 5,705; American female at
  115,209 from 1,795. All CC0, all matching published checksums, all split by the
  same code. Do not acquire the full 94.64 GB English release. Note that the
  Australian eligible pool is only 674 speakers, so the probe already samples
  45 percent of it and more speakers is not cheaply available.
- **Self reported accent is context, not phonetic truth**, and Common Voice carries
  no phonetic annotation at all.
- **No external lane can supply Australian variety exact relation evidence.** Across
  the powered adult set Azure `en-AU` named zero of 44,335 phone positions while
  `en-US` named 42,903 of 42,903. `en-AU` emits its phone name keys as empty strings
  beside real scores, so it can never attach a score to a known target.
- **Published figures in this repository have been wrong four times, so they are
  recomputed rather than carried forward.** The aligner phone counts at 22E6, the
  word counts on the publisher's own pages, the size of the Australian tagged
  Wiktionary pool, and now the variety probe's rhotic finding were all wrong.
- **The t differential survived the correction and is the one live per consonant
  result.** Australian speakers are flagged more often than the American control on
  t under the American reference, +0.0269, and the gap nearly vanishes under the
  repaired reference, +0.0037. It is the largest single per consonant differential
  in the comparison. It is also not clearly separable from noise: v runs −0.0254 in
  the opposite direction. No claim may be made about it until uncertainty exists.

- **The scoring model shares lineage with the evaluation data, and item R2
  declared that rather than resolving it.**
  `facebook/wav2vec2-lv-60-espeak-cv-ft` is fine tuned on Common Voice and the probe
  evaluates entirely on Common Voice 26 speakers. The engineering plan disqualifies
  Wav2Vec2 CommonPhone for exactly this reason and the rule was never applied here.
  The declaration, in one line: **direction unknown, plausibly favours the control
  group, and the observed result runs against it**, so the null is conservative
  rather than suspect. The mechanism matters. Common Voice English skews American
  and British, so the model has plausibly seen far more of the control group's
  speech, which would fit them better and flag them less. That is a group dependent
  effect, so the claim that one model scoring everybody cancels the overlap is
  wrong and is not made. What protects the result is that the American control is
  flagged more often than the Australian group, 0.0863 against 0.0823, which is the
  opposite of what the bias predicts. **That reasoning does not transfer to a
  future differential running the way the bias predicts.** Resolving it needs a
  second phone model with no Common Voice lineage rescoring the same 2,400 clips,
  and is deferred in `improvement-plan.md` section 5a.
- **A forced alignment score is not an ASR confidence, and item R3 found this
  repository comparing one against a threshold meant for the other.** The
  fluency contract refuses a word whose ASR confidence falls below 0.5, a floor
  calibrated against a provider's posterior. The local transcription path's
  aligner emits a per word score on a different scale entirely, and on a real
  recording it scored a genuine repeated phrase at 0.307 and 0.154, so the
  eligibility rule **discarded a real repetition while appearing to work**. The
  local path now writes `alignment_score`, emits no `confidence`, and the four
  fluency families that need one declare themselves unavailable rather than
  returning zero candidates. No threshold was retuned. Anything adding a second
  provider to this pipeline should check the same question before trusting a
  field name.
- **The enrichment hang is fixed.** Remote enrichment now has two deadlines: the
  provider client aborts its own request first, and an outer deadline in
  `run_with_retry` catches whatever the client cannot see. A hung call becomes a
  `timeout` failure, retries once, then degrades with an explicit status.
  Transcription is load bearing and is deliberately not covered: it must fail the
  run. Both deadlines count awake time, so run real recordings under `caffeinate`.
- **The field is more occupied than this project assumed.** Dialect fairness in
  speech is an active area in 2026 with a funded startup publishing in it. The
  defensible contribution is a reusable audit and abstention harness for
  pronunciation measurement, which does not exist as open infrastructure. It is not
  the invention of evidence guarded machine learning, which has substantial prior
  art. See `audit-2026-08-22.md`.

## What exists

A Python speech measurement engine. It runs solo or conversation recordings,
checks audio quality, extracts speech evidence, keeps uncertainty and provenance,
safely degrades remote enrichment, verifies claims against stored evidence, runs
regression checks, and audits reliability and fairness evidence. `README.md` has
the commands and artifacts.

Beside it are versioned research contracts and validators:

- **Onboarding and identity:** an English onboarding assessment, a locked
  pronunciation research protocol, stable account and session records with
  separate consent, and a personal progress protocol whose registry releases zero
  speech metrics.
- **Item 20, voice and prosody:** timestamped per speaker F0 and recorder level
  evidence, task and consent gates, octave error checks, research only sustained
  vowel measures, and safeguards against unsupported mental, identity and health
  inferences. No released score or interpretation.
- **Item 21, fluency events:** timestamped repetition and prolonged sound
  candidates with source evidence, alternative explanations, uncertainty and review
  state. Possible blocks are deliberately manual, because silence cannot establish
  a block. The artifact never reaches the listener, evaluator, claim ledger,
  history or progress.
- **Item 22, speech sound patterns:** research contract version 1.7, licence safe
  corpus manifests for 22 sources, a fail closed provider register, a frozen
  benchmark and its conservative repair, two frozen comparisons, the selection and
  rejection record, the acquired open reference stack with three comparison accent
  groups, the reference variety probe, a twenty word developer research prompt pack,
  the private offline evidence assembler, the frozen final acceptance contract and
  the immutable repository closure. There is no active task, selected system,
  pipeline stage or released artifact.
- **Item 23, motor speech and voice:** the evidence review, intended use ladder,
  governance contract, 27 source survey, measurement input package, Australian
  regulatory reading and deliverable ledger. It creates no runtime package, task,
  artifact or output, and it is shelved. `motor_speech_voice/engineering-plan.md`
  remains its authority if it is ever revisited.

Item 22's committed evidence is release locked developer engineering. It measured
local fit, repeatability, response shapes and gate outcomes. It did not establish
phone accuracy, acceptable variants or user facing correctness.

- **The verifier is now checking an easier task, on purpose, and the report says
  so.** The R5 acceptance run verified 18 of 18 claims with 0 issues on the first
  attempt. That is not evidence of a strong verifier. With the scores gone the
  model's numeric claims are largely restatements of values it was handed, so a
  clean report mostly shows that a copy operation copied correctly.
  `verification.md` now carries that statement itself rather than leaving a
  reader to infer more than the number earned. The residual soft spot is visible
  in the same run: an interpretation claim reading "might indicate an attempt to
  persuade or encourage the listener" passed every check, because it is marked as
  an interpretation, cites real evidence and contains no arithmetic. A numeric
  verifier cannot catch that class of claim at all, which is exactly the failure
  Prior over Evidence measured at 39.6 percent.

## What does not exist

- **the honest account is now written**, as `findings.md`, on 2026-08-26. It is
  **not yet in the public repository**, and putting it there needs a snapshot
  rebuild that runs into the two release tool defects recorded above. Until it
  is published, the definition of done is not met, because that definition
  requires an outsider to be able to read it;
- any released score, rating, index, level or summary number describing a person.
  Five existed until 2026-08-24 and item R5 deleted them without replacement;
- a fully credential free conversation path. Item R3 added local transcription
  and item R5 made the model layer opt in, so a solo run **with
  `--transcriber local`** and no `--interpret` makes no remote call at all and
  finishes in about 90 seconds, but diarization still uses a gated pyannote
  model and conversation mode still needs a Hugging Face token. **The default
  transcriber is AssemblyAI**, so a run with no flags is not the credential free
  path. An earlier version of this line said a default solo run makes no remote
  call, which was false: it dropped the `--transcriber local` scope that
  `improvement-plan.md` states correctly. Corrected 2026-08-26 while writing
  `findings.md`;
- second voice detection or text derived fluency events on the local
  transcription path. Both are declared unavailable there rather than returning
  nothing, and that is a real capability loss, not a formality;
- independently validated voice, prosody or event detection accuracy;
- a validated personal progress metric;
- a professionally reviewed pronunciation word pack or a selected pronunciation
  system. The 22F research prompt pack is an unreviewed developer list, and the
  reviewed pack it is not a substitute for has never been built;
- any approved motor speech or voice construct, task, participant study,
  independent truth set, detector, threshold or screening result;
- expert produced phone truth for any first language English variety this project
  targets;
- clinical diagnosis or treatment functions, which are permanently out of scope.

## Owner collaboration preferences

- Explain the next item in very simple, concise language before doing it. Say what
  will change, why it matters, and what will not be built. Then wait for Adam's
  explicit permission.
- Research deeply when an item introduces a new measurement or decision. Ask a
  question only when the answer would materially change the result.
- **Never commit or push.** Adam makes every commit. After completing one
  improvement, hand him a plain English commit title and description, then stop
  editing until he confirms.
- Real pipeline test runs with Adam's provided recordings are pre approved at his
  cost through the pipeline's established providers. Run them in isolated output
  directories whenever verification benefits, without asking. Never append test
  runs to `history.json` or `progress.md`.
- Sending public research corpus audio to a named external provider requires a
  written decision in
  `speech_sound_patterns/corpus_manifests/provider-transfer-review-v1.2.0.json`.
  **Sending Adam's own audio to any external provider is excluded entirely.**
- Adam declined the iFLYTEK lane on 2026-07-25. Do not send it audio or propose
  reopening it without asking him directly.
- Adam decided on 2026-07-28 to send no acquisition enquiries and to proceed on
  openly licensed sources alone. **The direction change of 2026-08-22 supersedes
  the commercial half of this decision but not the no enquiries half.** Acquiring
  a non commercial source that needs no correspondence is now in scope; contacting
  anybody still needs his explicit go.

## Useful references

- `project-purpose.md`: what this project is, claims, and refuses.
- `improvement-plan.md`: live boundaries and ordered queue.
- `audit-2026-08-22.md`: the full direction change audit and all findings.
- `prior-art-2026-08-24.md`: what the claim ledger's pattern is prior art for,
  and the one claim about this project that survived the check.
- `README.md`: technical commands and current artifacts.
- `speech_sound_patterns/engineering-plan.md`: **the authority for item 22.**
- `motor_speech_voice/engineering-plan.md`: the authority for item 23, shelved.
- `assessment/`, `data_model/`, `progress_model/`, `fluency_events/`,
  `speech_sound_patterns/research-and-protocol.md`: per area protocols.
