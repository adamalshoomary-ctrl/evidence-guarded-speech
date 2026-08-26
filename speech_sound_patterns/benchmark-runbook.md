# Checkpoint 22D benchmark reproduction runbook

This procedure recreates the developer-only benchmark evidence on the current
macOS ARM machine. It never runs from the normal pipeline. Raw corpora, audio,
expert records, model outputs, alignments and row-level scores stay inside the
gitignored `.research_data/speech_sound_patterns/benchmark` directory.

Do not inspect or score held-out participants, upload any audio, pass `--me`,
or interpret automatic agreement as pronunciation truth. Recreating a completed
run requires a new empty private benchmark evidence directory; never overwrite
or delete the existing evidence merely to make a command pass.

## 1. Verify the frozen inputs

From the repository root, verify the private corpora and committed rules:

```sh
python3 -m speech_sound_patterns.validate_corpora --verify-private
python3 -m speech_sound_patterns.validate_benchmark
```

The benchmark contract and phone map must validate before sampling. The private
sample manifest must recreate SHA256
`e856b2fef404cd28c9d09c6748797e1c6b888361c83c8d62f47ebf2560e03b98`.

## 2. Recreate the private sample

Use the same `ffmpeg`, pinned models and isolated environments prepared by
`feasibility-runbook.md`:

```sh
python3 -m speech_sound_patterns.prepare_benchmark \
  --ffmpeg "$(command -v ffmpeg)"
```

The preparer selects 480 SpeechOcean clips, 25 Acted Clear fixtures, 30 Common
Phone clips and 30 Australian Common Voice clips. Selection uses only frozen
participant assignments and identifiers. It does not use expert labels, scores
or model output, and it does not decode held-out expert records.

## 3. Run PhoneticXEUS in bounded MPS processes

The full benchmark uses two exact repeats for every clip, offline model loading,
one thread and disabled silent MPS fallback. Run small resumable chunks to avoid
macOS swap pressure. Repeat the command until it reports all 565 clips complete:

```sh
REPO_ROOT="$(pwd)"
PRIVATE_ROOT="$REPO_ROOT/.research_data/speech_sound_patterns"
PHONE_ENV="$PRIVATE_ROOT/environments/phoneticxeus-8d83dee-osx-arm64"

env -i HOME="$PRIVATE_ROOT/sandbox_home" \
  PATH="$PHONE_ENV/bin:/usr/bin:/bin" PYTHONPATH="$REPO_ROOT" \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 OMP_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 PYTORCH_ENABLE_MPS_FALLBACK=0 \
  "$PHONE_ENV/bin/python" -m speech_sound_patterns.benchmark_phoneticxeus \
  --backend mps --repeats 2 --max-new-clips 15
```

Each invocation validates every existing per-clip record before continuing.
The final invocation writes `phoneticxeus-benchmark-process.json`. A process
that reports a safely paused chunk is incomplete and must not be summarized.

## 4. Run MFA on the same cross-system subset

MFA receives only the 109 transcript-known clips predeclared by the benchmark
contract. It repeats one Acted Clear clip in each of five speaking conditions.
Temporary alignment databases are removed immediately; raw alignment JSON and
logs remain private.

```sh
env -i HOME="$PRIVATE_ROOT/sandbox_home" PATH="/usr/bin:/bin" \
  PYTHONPATH="$REPO_ROOT" PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  /usr/bin/python3 -m speech_sound_patterns.benchmark_mfa
```

## 5. Score only supported reference classes

```sh
python3 -m speech_sound_patterns.score_benchmark
```

The scorer retains all five SpeechOcean reviewer records. It requires four
matching reviewers for a scorable target, keeps explicit insertions separate,
and leaves disputed or unsupported phones unscorable. Private opportunity rows
and private aggregates are checksum bound to the sample and local-system output.

## 6. Regenerate and validate the safe aggregate report

```sh
python3 -m speech_sound_patterns.summarize_benchmark
python3 -m speech_sound_patterns.validate_benchmark
python3 -m speech_sound_patterns.validate
python3 -m unittest tests.test_speech_sound_benchmark
```

The committed report may contain aggregates only. The validators reject private
paths, clip-level material, held-out results, pooled adult and child relation
metrics, a selected system or threshold, any product release claim, or a next
checkpoint that bypasses owner approval. If a legitimate full rerun changes the
result, create new report and contract versions; do not silently replace version
1.0 evidence.

## 7. Reproduce the conservative repair

The repair keeps the frozen baseline unchanged. First create the label-blind
input containing audio identity, expected phones and indexes but no expert
outcomes:

```sh
python3 -m speech_sound_patterns.prepare_benchmark_repair
```

The expected-only manifest must recreate SHA256
`c918feffa7c0a3a3fa99ce7a9e028621e8fb002980777297f30088e5975331da`.
Run the pinned PhoneticXEUS constrained CTC extractor from its existing isolated
environment until all 480 clips complete, then run the three frozen adult
calibration stages:

```sh
REPO_ROOT="$(pwd)"
PRIVATE_ROOT="$REPO_ROOT/.research_data/speech_sound_patterns"
PHONE_ENV="$PRIVATE_ROOT/environments/phoneticxeus-8d83dee-osx-arm64"

env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 OMP_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 PYTORCH_ENABLE_MPS_FALLBACK=0 \
  PYTHONPATH="$REPO_ROOT" "$PHONE_ENV/bin/python" \
  -m speech_sound_patterns.benchmark_phoneticxeus_ctc

python3 -m speech_sound_patterns.calibrate_benchmark_repair
python3 -m speech_sound_patterns.calibrate_benchmark_repair_context
python3 -m speech_sound_patterns.score_benchmark_repair_repeated
```

These commands may read the private expert relation evidence only after the
candidate features are complete. They may use development labels for grouped
model selection and tuning labels for the threshold, but never held-out labels
or outputs.

## 8. Reproduce the final local alternative

The Meta comparison uses the full precision ONNX conversion of
`facebook/wav2vec2-lv-60-espeak-cv-ft`, not a pickle checkpoint or a quantized
variant. The repository revision is
`c69750f5043e5e1f8a71ab95dd3b98338c280c92`; the model file must recreate
SHA256 `93265694093f5f91497181ed9d7791f43bc818d2e23c46caf988fd9b8b1a1fba`.
Create its private environment from the committed exact package list:

```sh
REPO_ROOT="$(pwd)"
PRIVATE_ROOT="$REPO_ROOT/.research_data/speech_sound_patterns"
META_ENV="$PRIVATE_ROOT/environments/meta-wav2vec2-onnx-c69750f"
python3 -m venv "$META_ENV"
"$META_ENV/bin/python" -m pip install \
  -r speech_sound_patterns/environments/meta-wav2vec2-onnx-c69750f-pip.txt
```

Download only the four checksum-pinned files into
`$PRIVATE_ROOT/models/meta-wav2vec2-c69750f`, then run offline:

```sh
META_MODEL="$PRIVATE_ROOT/models/meta-wav2vec2-c69750f"
META_REVISION="c69750f5043e5e1f8a71ab95dd3b98338c280c92"
META_SOURCE="https://huggingface.co/onnx-community/wav2vec2-lv-60-espeak-cv-ft-ONNX/resolve/$META_REVISION"
mkdir -p "$META_MODEL/onnx"
curl -fL --output "$META_MODEL/onnx/model.onnx" \
  "$META_SOURCE/onnx/model.onnx"
for META_FILE in config.json preprocessor_config.json vocab.json
do
  curl -fL --output "$META_MODEL/$META_FILE" "$META_SOURCE/$META_FILE"
done

env SPEECH_SOUND_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONHASHSEED=0 OMP_NUM_THREADS=1 PYTHONPATH="$REPO_ROOT" \
  "$META_ENV/bin/python" -m speech_sound_patterns.benchmark_meta_ctc

python3 -m speech_sound_patterns.calibrate_benchmark_repair_meta
python3 -m speech_sound_patterns.score_benchmark_repair_meta_threshold
python3 -m speech_sound_patterns.summarize_benchmark_repair
python3 -m speech_sound_patterns.validate_benchmark
python3 -m speech_sound_patterns.validate
```

The extractor supports deterministic disjoint `--shard-count` and
`--shard-index` runs. After every shard finishes, run the command once without
shard arguments; it verifies all existing clip records and writes the one
complete process summary. The final aggregate report must pass
`validate_repair_report` and contain no private identifiers, rows, audio,
alignments, logits or probabilities.
