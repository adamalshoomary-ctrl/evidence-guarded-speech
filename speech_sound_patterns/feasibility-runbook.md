# Checkpoint 22C reproduction runbook

This runbook reproduces the local feasibility evidence. It is developer-only,
macOS ARM specific and never runs from the normal pipeline. Raw corpora, audio,
transcripts, models, logits and logs stay below the gitignored
`.research_data/speech_sound_patterns` directory.

The frozen report is not an accuracy benchmark. Do not inspect tuning or
held-out labels, pass `--me`, upload audio, or treat automatic agreement as
truth.

## 1. Verify private corpora

From the repository root:

```sh
python3 -m speech_sound_patterns.validate_corpora --verify-private
```

The five permitted packages and their private participant assignments must
already match the committed manifests. The preparation command later fails
unless it recreates private sample manifest SHA256
`655c8ba92d56b6804b453397f7919cb57ed4875d035f2884493a7c7e63e938fa`.

## 2. Recreate the isolated environments

```sh
REPO_ROOT="$(pwd)"
PRIVATE_ROOT="$REPO_ROOT/.research_data/speech_sound_patterns"
MFA_ENV="$PRIVATE_ROOT/environments/mfa-3.4.1-osx-arm64"
PHONE_ENV="$PRIVATE_ROOT/environments/phoneticxeus-8d83dee-osx-arm64"

conda create -y -p "$MFA_ENV" \
  --file speech_sound_patterns/environments/mfa-3.4.1-osx-arm64-explicit.txt
conda create -y -p "$PHONE_ENV" \
  --file speech_sound_patterns/environments/phoneticxeus-8d83dee-osx-arm64-explicit.txt
"$PHONE_ENV/bin/python" -m pip install --require-hashes \
  -r speech_sound_patterns/environments/phoneticxeus-8d83dee-pip.txt
```

These explicit conda files are platform locks, not cross-platform environment
descriptions.

## 3. Acquire only the pinned models

```sh
MFA_MODELS="$PRIVATE_ROOT/models/mfa"
XEUS_REVISION="8d83dee94817a07dc150f87d08f7e0ee01bdb66d"
XEUS_MODEL="$PRIVATE_ROOT/models/phoneticxeus/$XEUS_REVISION"

MFA_ROOT_DIR="$MFA_MODELS" "$MFA_ENV/bin/mfa" model download acoustic \
  english_us_arpa --version 3.0.0
MFA_ROOT_DIR="$MFA_MODELS" "$MFA_ENV/bin/mfa" model download dictionary \
  english_us_arpa --version 3.0.0

"$PHONE_ENV/bin/hf" download changelinglab/PhoneticXeus \
  --revision "$XEUS_REVISION" --local-dir "$XEUS_MODEL" \
  --include README.md config.json config_tree.log configuration_phoneticxeus.py \
  ipa_vocab.json model.safetensors modeling_phoneticxeus.py 'src/**'
```

Do not download or use the pickle checkpoint. The probes verify the model tree,
weight, acoustic-model and dictionary checksums before inference.

## 4. Recreate the frozen private sample

```sh
python3 -m speech_sound_patterns.prepare_feasibility \
  --ffmpeg "$(command -v ffmpeg)" \
  --owner-audio "$REPO_ROOT/regression/fixtures/solo.wav"
```

Selection uses frozen development participants and a fixed hash seed. It does
not use labels, scores or model outputs. The owner clip has unknown intended
text and is therefore ineligible for MFA.

## 5. Run the probes

Every neural process must use an empty credential environment, offline model
loading, deterministic single-threaded CPU scheduling and no silent MPS
fallback. Use separate output directories for the ten-repeat MPS run, two
one-repeat fresh MPS runs and the three-repeat five-source CPU subset. Wrap
each command with `speech_sound_patterns.measure_feasibility_process`; this
captures macOS `time -l` output privately and binds it to the produced JSON
checksum.

The underlying neural command is:

```sh
env -i PATH="$PHONE_ENV/bin:/usr/bin:/bin" PYTHONPATH="$REPO_ROOT" \
  HOME="$PRIVATE_ROOT/sandbox_home" \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 OMP_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 PYTORCH_ENABLE_MPS_FALLBACK=0 \
  "$PHONE_ENV/bin/python" -m speech_sound_patterns.phoneticxeus_probe \
  --manifest "$PRIVATE_ROOT/feasibility/sample-manifest-v1.0.0.json" \
  --model "$XEUS_MODEL" --output OUTPUT_DIRECTORY \
  --backend BACKEND --repeats REPEAT_COUNT
```

Use these exact cases:

- `mps-full-warm`, backend `mps`, 10 repeats, all clips;
- `mps-cold-2`, backend `mps`, one repeat, all clips;
- `mps-cold-3`, backend `mps`, one repeat, all clips;
- `cpu-source-subset`, backend `cpu`, three repeats, with safe IDs
  `acted_clear_speech_2013_001`, `common_phone_1_0_001`,
  `common_voice_26_australian_english_001`,
  `owner_controlled_integration_001` and `speechocean762_001`.

The measurement keys have the same names prefixed with `phoneticxeus_`. Store
the combined metrics at
`.research_data/speech_sound_patterns/feasibility/evidence/outer-process-metrics.json`.
For example, the complete measurement wrapper for the full warm run is:

```sh
EVIDENCE="$PRIVATE_ROOT/feasibility/evidence"
METRICS="$EVIDENCE/outer-process-metrics.json"
LOGS="$PRIVATE_ROOT/feasibility/private-logs"

python3 -m speech_sound_patterns.measure_feasibility_process \
  --key phoneticxeus_mps_full_warm \
  --evidence "$EVIDENCE/phoneticxeus/mps-full-warm/phoneticxeus-mps-process.json" \
  --output "$METRICS" --log-root "$LOGS" -- \
  env -i HOME="$PRIVATE_ROOT/sandbox_home" \
  PATH="$PHONE_ENV/bin:/usr/bin:/bin" PYTHONPATH="$REPO_ROOT" \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 OMP_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 PYTORCH_ENABLE_MPS_FALLBACK=0 \
  "$PHONE_ENV/bin/python" -m speech_sound_patterns.phoneticxeus_probe \
  --manifest "$PRIVATE_ROOT/feasibility/sample-manifest-v1.0.0.json" \
  --model "$XEUS_MODEL" \
  --output "$EVIDENCE/phoneticxeus/mps-full-warm" \
  --backend mps --repeats 10
```

Use the same wrapper for the other three neural cases, changing the metric
key, evidence file, output directory, backend, repeat count and CPU clip IDs
exactly as listed above.

Run MFA once over all eligible clips with three repeats:

```sh
env -i HOME="$PRIVATE_ROOT/sandbox_home" PATH="/usr/bin:/bin" \
  PYTHONPATH="$REPO_ROOT" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 /usr/bin/python3 \
  -m speech_sound_patterns.mfa_probe \
  --manifest "$PRIVATE_ROOT/feasibility/sample-manifest-v1.0.0.json" \
  --mfa "$MFA_ENV/bin/mfa" --mfa-root "$MFA_MODELS" \
  --acoustic-model "$MFA_MODELS/pretrained_models/acoustic/english_us_arpa.zip" \
  --dictionary "$MFA_MODELS/pretrained_models/dictionary/english_us_arpa.dict" \
  --output "$PRIVATE_ROOT/feasibility/evidence/mfa/full-three-repeats-v2" \
  --repeats 3
```

Run PanPhon on the full MPS and CPU-subset JSONs, wrapped with measurement key
`panphon_observed_mapping`. It must produce
`evidence/panphon/measured/observed-token-mapping.json`.

```sh
python3 -m speech_sound_patterns.measure_feasibility_process \
  --key panphon_observed_mapping \
  --evidence "$EVIDENCE/panphon/measured/observed-token-mapping.json" \
  --output "$METRICS" --log-root "$LOGS" -- \
  env -i HOME="$PRIVATE_ROOT/sandbox_home" \
  PATH="$PHONE_ENV/bin:/usr/bin:/bin" PYTHONPATH="$REPO_ROOT" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 OMP_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 "$PHONE_ENV/bin/python" \
  -m speech_sound_patterns.panphon_probe \
  --input "$EVIDENCE/phoneticxeus/mps-full-warm/phoneticxeus-mps-process.json" \
  --input "$EVIDENCE/phoneticxeus/cpu-source-subset/phoneticxeus-cpu-process.json" \
  --output "$EVIDENCE/panphon/measured/observed-token-mapping.json"
```

## 6. Regenerate and validate the safe report

```sh
env -i PATH="$PHONE_ENV/bin:/usr/bin:/bin" PYTHONPATH="$REPO_ROOT" \
  HOME="$PRIVATE_ROOT/sandbox_home" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 OMP_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 "$PHONE_ENV/bin/python" \
  -m speech_sound_patterns.summarize_feasibility \
  --manifest "$PRIVATE_ROOT/feasibility/sample-manifest-v1.0.0.json" \
  --evidence-root "$PRIVATE_ROOT/feasibility/evidence" \
  --outer-metrics "$PRIVATE_ROOT/feasibility/evidence/outer-process-metrics.json" \
  --output "$REPO_ROOT/speech_sound_patterns/local-feasibility-v1.0.0.json"

python3 -m speech_sound_patterns.validate
python3 -m unittest tests.test_speech_sound_feasibility
```

The summarizer rejects a different sample, backend, dependency set, repeat
design, model, tensor artifact, PanPhon input, process metric, machine, or
release boundary. If the final report changes after a legitimate full rerun,
create a new report and contract version; do not silently replace version 1.0.
