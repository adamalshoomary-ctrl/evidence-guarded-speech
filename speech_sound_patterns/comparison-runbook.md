# Frozen comparison reproduction runbook, checkpoints 22E4 and 22E4B

This procedure reproduces the developer-only comparison evidence on the current
macOS ARM machine. It never runs from the normal pipeline. Raw corpora, audio,
expert records, model outputs, provider responses and row-level scores stay
inside the gitignored `.research_data/speech_sound_patterns` directory.

Do not inspect or score held-out participants, transmit any child clip, pass
`--me`, or read an expert outcome before every candidate output is complete.
Recreating a completed run requires a new empty private evidence directory;
never overwrite or delete existing evidence merely to make a command pass.

**Two frozen comparisons exist.** Checkpoint 22E4, contract and report version
1.0.0, is the first look on 480 clips. Checkpoint 22E4B, version 1.1.0, is the
powered replication on 2,280 clips covering every non held-out adult. Every
command below defaults to the powered checkpoint 22E4B sample; add
`--comparison-version 1.0.0` to address the checkpoint 22E4 record instead. The
version 1.0.0 contract, report and private evidence are never edited or rerun.

Sections 1 through 7 are the checkpoint 22E4 procedure as it was run. Section 8
is the additional preparation checkpoint 22E4B needs before those same commands
can be pointed at the powered sample.

## 1. Verify the frozen rules and inputs

```sh
python3 -m speech_sound_patterns.validate_corpora --verify-private
python3 -m speech_sound_patterns.validate_benchmark
python3 -m unittest tests.test_speech_sound_comparison
```

The contract must validate, the private expected-only manifest must still hash
to `c918feff...5331da`, and the private expert relation evidence must still hash
to `571e04f1...e344d96`. The test suite additionally reproduces the committed
checkpoint 22D greedy numbers through this checkpoint's own scoring code, so a
silent redefinition of precision, recall, a denominator or an abstention fails
before anything runs.

## 2. Run the segmentation-free GOP lane

Runs over all 480 frozen clips with two exact repeats, in the pinned Meta ONNX
environment prepared by `benchmark-runbook.md` step 8.

```sh
REPO_ROOT="$(pwd)"
PRIVATE_ROOT="$REPO_ROOT/.research_data/speech_sound_patterns"
META_ENV="$PRIVATE_ROOT/environments/meta-wav2vec2-onnx-c69750f"

env SPEECH_SOUND_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  OMP_NUM_THREADS=1 PYTHONPATH="$REPO_ROOT" \
  "$META_ENV/bin/python" -m speech_sound_patterns.comparison_sfgop
```

The runner is resumable with `--max-new-clips`. Every invocation re-verifies
each finished clip against the manifest before adding another, so a paused run
cannot drift. It writes `sfgop-comparison-process.json` only when all 480 clips
are complete.

## 3. Run the POWSM free-phone lane

Runs over the 480 frozen clips plus the 85 Acted Clear, Common Phone and
Australian Common Voice clips. The pinned checkpoint's pickle is audited opcode
by opcode before any weight loads.

```sh
POWSM_ENV="$PRIVATE_ROOT/environments/powsm-21ffa41-venv"

env SPEECH_SOUND_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  OMP_NUM_THREADS=1 \
  "$POWSM_ENV/bin/python" speech_sound_patterns/comparison_powsm.py
```

## 4. Run the supporting-only CommonPhone lane

Supporting evidence only. It runs on the SpeechOcean clips alone, because its
training lineage overlaps Common Phone and Australian Common Voice, and it can
never contribute to a selection gate.

```sh
CP_ENV="$PRIVATE_ROOT/environments/commonphone-e856cb9-venv"

env SPEECH_SOUND_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  OMP_NUM_THREADS=1 \
  "$CP_ENV/bin/python" speech_sound_patterns/comparison_commonphone.py
```

## 5. Run the Azure comparison lane

This is the only step that sends audio off the machine. Check the gates first,
without sending anything:

```sh
python3 -m speech_sound_patterns.comparison_azure --dry-run
```

It must report 240 clips, both locales, two repeats and 960 planned requests. If
the provider register, the corpus to provider transfer review or the frozen
contract disagree with that plan, it fails closed and sends nothing.

On this machine the completed evidence already exists, so this command now stops
with "completed Azure comparison evidence already exists" before it inspects
anything, `--dry-run` included. That is the intended guard against an accidental
rerun overwriting a committed comparison; the steps above are the record of what
was done, not a script to repeat.

```sh
python3 -m speech_sound_patterns.comparison_azure
```

Only the clip audio and the intended reference text are transmitted. Child
clips, held-out clips, Australian Common Voice and any owner recording are never
transmitted. Overall, fluency, completeness and prosody scores are discarded at
the response boundary before anything is written to disk.

## 6. Score every lane against the frozen expert relations

This is the first step permitted to read an expert outcome, and it refuses to
run unless each lane's process summary reports a complete, exactly repeated,
label-blind run.

```sh
python3 -m speech_sound_patterns.score_comparison
```

## 7. Write and validate the committed report

```sh
python3 -m speech_sound_patterns.summarize_comparison
python3 -m speech_sound_patterns.validate_comparison
python3 -m speech_sound_patterns.validate_benchmark
python3 -m speech_sound_patterns.validate
python3 -m unittest tests.test_speech_sound_comparison
```

The committed report may contain aggregates only. The validators reject private
paths, clip-level or row-level material, held-out results, pooled locales, a
weakened gate, a selection recorded in this checkpoint, a prohibited provider
score, or any product release claim. If a legitimate full rerun changes the
result, create new contract and report versions; do not silently replace version
1.0 evidence.

`validate_comparison` checks both frozen comparisons on every run, so the
checkpoint 22E4 record must keep validating unchanged after checkpoint 22E4B.

## 8. Checkpoint 22E4B, the powered sample

Checkpoint 22E4 recorded `no_selection` on 8 of the 77 available development
adults and 4 of the 25 available threshold-tuning adults, so its threshold-tuning
partition held 34 positive opportunities and a difference of two flags separated
a pass from a fail. Checkpoint 22E4B replicates it on every non held-out adult.
Nothing else changes: the gates, the threshold procedure, the alignment rules,
the truth definition, the candidates and the sealed held-out participants are all
inherited unchanged.

The sample rules are frozen first, before the sample exists, in
`benchmark-powered-sample-contract-v1.0.0.json`. Then:

```sh
python3 -m speech_sound_patterns.prepare_powered_benchmark
python3 -m speech_sound_patterns.prepare_powered_relation_truth
python3 -m speech_sound_patterns.prepare_powered_expected_only
```

The first command streams the corpus archive once and canonicalises 2,280 clips
into `benchmark/v2`, reusing the frozen checkpoint 22D preparer with a larger
sample policy and a different output root. It refuses to finish unless every one
of the 480 checkpoint 22E4 records reappears in the powered sample under its
original split and stratum, so the powered sample is provably a superset of the
first look. The three secondary sources are referenced unchanged rather than
copied, and every referenced file is hash-verified first.

The second command extracts the expert relation truth without running any
candidate system. It refuses to write anything until it has reproduced all 5,478
committed checkpoint 22D relation rows exactly, so the consensus rule, the
scorable scope and the positive, negative and unscorable states cannot have been
redefined. The third command builds the label-blind candidate input, and
`--verify` recomputes it and compares it with the file on disk.

Those three artifacts are then pinned by hash in
`comparison-contract-v1.1.0.json`, which is frozen before any lane runs. After
that, sections 2 through 7 run unchanged: every command already defaults to the
powered sample.

Expect roughly six to eight hours per local lane and about four hours for Azure,
so run them in the background. The Azure dry run must report 2,040 clips, both
locales, two repeats and 8,160 planned requests; anything else means the frozen
contract, the provider register and the transfer review disagree, and it sends
nothing.
