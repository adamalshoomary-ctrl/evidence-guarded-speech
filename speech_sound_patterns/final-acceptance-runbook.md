# Final repository acceptance runbook, checkpoint 22H

Checkpoint 22H closes item 22 engineering on the frozen no-selection path. No
candidate system, mapping, feature rule, provider configuration, threshold or
repeated minimum qualified. There is therefore no eligible method to evaluate,
and the held-out participants remain sealed.

`not_performed` means the held-out result is unavailable. It is not zero, a
pass, a failure or permission to tune. Any later access needs a new contract and
Adam's explicit approval.

## Governing files

- `final-acceptance-contract-v1.0.0.json` was frozen before the acceptance
  implementation and binds every historical input and corpus manifest.
- `final_acceptance.py` validates the contract, private proof and safe aggregate
  report. It also implements the protected-state and leakage checks.
- `run_final_acceptance.py` runs the validators, compilation, tests, isolated
  conversation pipeline and independent regression fixture.
- `validate_final_acceptance.py` validates the frozen contract and final report.
- `final-evidence-v1.0.0.json` is the aggregate report written only after every
  required check passes.

Raw logs, pipeline artifacts and the private acceptance manifest remain below:

```text
.research_data/speech_sound_patterns/final_acceptance
```

They are gitignored. The aggregate report contains no transcript, participant
identifier, audio path or hash, provider response, row-level evidence or private
path.

## Validate the frozen contract without running anything

```sh
python3 \
  -m speech_sound_patterns.validate_final_acceptance --contract-only
```

This reads public repository artifacts only. It does not open the private split
assignment, held-out identities, labels, audio or derived rows.

After later roadmap work is committed, the current repository is expected to
differ from the item 22 closure. The validator then locates the ancestor commit
containing the exact unchanged closure bytes, reconstructs that commit's full Git
tree excluding only the closure path, and requires its file count and canonical
content digest to match the frozen closure. It does not rewrite, replace or
advance `repository-closure-v1.0.0.json`. A changed closure, missing ancestor or
historical tree mismatch fails closed.

## Run final acceptance once

Choose a new run identifier. The command refuses an existing private run and
refuses to replace an existing final report.

```sh
python3 \
  -m speech_sound_patterns.run_final_acceptance \
  --run-id NEW_UNIQUE_RUN_ID \
  --acknowledge-engineering-only
```

The run identifier must use `22h_YYYYMMDDTHHMMSS`. The contract calls the
interpreter `acceptance_python` and the private evidence records its actual
implementation, version, executable name and executable checksum. Shell
`python3` is not used as an evidence claim because it points to a different,
dependency-free interpreter on this machine.

The runner itself launches the real conversation pipeline through
`caffeinate -dimsu`. It uses:

- conversation mode with two speakers;
- the existing independently registered conversation fixture;
- a new isolated private output directory;
- no `--me`;
- no session context; and
- no held-out speech-sound evidence.

The normal pipeline's established providers may safely degrade only through
their existing explicit failure contract. Transcription and the objective
pipeline remain load bearing. A 429 or `quota_exhaustion` is reported and the
acceptance run is not repeated to chase a different result.

An ordinary solo, conversation or accent-contrast sentence recording is not
the frozen written-word task. Checkpoint 22H accepts no optional owner input,
because no eligible recording exists and a broad private path cannot
independently prove that a file is not held-out evidence. The recorded status is
`not_performed_no_task_matched_owner_recording_available`.

## What the runner proves

Before any check, it recursively snapshots `history.json`, `progress.md` and
the existing root `output`. It then requires:

- every item 22 validator to pass;
- the final contract validator to pass;
- Python compilation to pass;
- the focused adversarial tests and complete test suite to pass;
- all fourteen normal conversation stages to complete;
- the independent real-conversation regression fixture to pass;
- every required artifact to exist and no unexpected artifact to appear;
- remote enrichment either to complete or to use its explicit safe unavailable
  state;
- verification to pass or to be explicitly unavailable for the same safe
  evaluator failure;
- no normal pipeline import, stage, filename, JSON key or strong content token
  belonging to item 22; and
- the protected personal files and root output to remain byte-identical.

It also requires the active pipeline source, pipeline version, model registry
and prompt registry to match the frozen pre-22H baseline. Every tracked or
nonignored public repository file is checksummed before and after the run. Raw
logs, pipeline artifacts and the independent regression report are enumerated,
checksummed in the private manifest and rehashed during private validation.

Failure writes only a private failure record and no public report. Success
writes the private acceptance manifest and the aggregate report, rebuilds the
report from the private manifest, and requires byte-for-byte equality.

The report is not the final repository boundary by itself. Contract v1.7,
tests and documentation are written after it, so one last immutable repository
closure must bind that post-report public state. Until that closure exists, the
ordinary validator fails and Item 22 is not complete.

## Close the post-report repository state

After the final report, research contract v1.7, tests and documentation are all
final, run:

```sh
python3 \
  -m speech_sound_patterns.finalize_repository_closure \
  --acceptance-manifest .research_data/speech_sound_patterns/final_acceptance/RUN_ID/acceptance-manifest.json \
  --acknowledge-engineering-only
```

The finalizer requires the same checksum-identified Python used by acceptance,
revalidates the private raw proof, reruns every validator, compilation and both
test commands at their frozen minimum counts with zero skips, revalidates the
private proof again, confirms personal and public state stayed unchanged, then
writes `repository-closure-v1.0.0.json` without overwrite. The closure excludes
only its own path when checksumming the complete tracked and nonignored public
repository snapshot.

## Validate the completed result

Validate the public artifacts only:

```sh
python3 \
  -m speech_sound_patterns.validate_final_acceptance
```

This command requires the repository closure. Before closure, the finalizer
uses the explicit `--pre-closure` audit mode with the private manifest; that
mode validates the evidence but does not call Item 22 complete.

Also reproduce the report from the exact private proof:

```sh
python3 \
  -m speech_sound_patterns.validate_final_acceptance \
  --manifest .research_data/speech_sound_patterns/final_acceptance/RUN_ID/acceptance-manifest.json
```

## What completion does not mean

Engineering completion does not establish detector accuracy, Australian
English correctness, repeated-relation validity, population performance,
fairness, clinical validity or user benefit. There is still no active product
task, selected system, emitted relation, normal-pipeline speech-sound artifact,
score, coaching, progress, screening, diagnosis, severity or treatment output.
Scientific and product release remain locked.
