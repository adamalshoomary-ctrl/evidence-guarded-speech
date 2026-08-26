# Candidate evidence assembler runbook, checkpoint 22G

Checkpoint 22G creates a private developer artifact from already computed
evidence for known prompt-pack words. It is an evidence assembler, not a speech
sound detector. It runs no model, makes no network request, reads no held-out
participant, selects no threshold or relation rule, and changes no normal
pipeline artifact.

The governing files are:

- `candidate-artifact-contract-v1.0.0.json`, frozen before the implementation;
- `candidate-evidence-v1.0.0.json`, the committed safe aggregate adequacy audit;
- `research-contract-v1.6.0.json`, the historical checkpoint 22G amendment over
  unchanged version 1.5; version 1.7 is now the active final contract;
- `candidate_artifact.py`, the manifest, artifact and repeated-evidence rules;
- `extract_candidates.py`, the explicit offline command; and
- `validate_candidates.py`, the contract, report and optional private artifact
  validator.

No private `speech_sound_candidates.json` is committed. Private manifests,
source evidence and assembled artifacts stay under
`.research_data/speech_sound_patterns/candidates`.

## Why no rule exists

The evidence adequacy gate runs before any threshold or repeated-relation rule
search. The permitted evidence contains:

| Partition | Pack-word occurrences | Participants | Distinct pack words | Positive | Negative | Unscorable |
|---|---:|---:|---:|---:|---:|---:|
| Development | 12 | 12 | 5 | 1 | 24 | 2 |
| Threshold tuning | 8 | 8 | 3 | 0 | 20 | 1 |

Every matching word is embedded in a sentence instead of elicited by the
controlled isolated-word task. No participant supplies two distinct pack words,
and the truth is a coarse expected-target relation rather than an exact produced
phone and feature relation. The prompt pack reconstructs 49 expected sound
opportunities, 45 scorable and 4 unscorable, but a task-matched repeated-support
denominator does not exist.

The frozen decision is therefore
`no_rule_selected_task_matched_evidence_unavailable`. The current artifact
cannot emit `possible_relation_candidate` or `repeated_relation_candidate`.
Supplying an arbitrary rule dictionary is rejected.

## Allowed sources

The manifest source record must match one of two exact profiles.

`synthetic_fixture` is for structural tests only:

```json
{
  "source_id": "synthetic_fixture",
  "manifest_state": "synthetic_fixture",
  "licence_state": "not_applicable_synthetic",
  "role": "structural_testing_only",
  "external_transfer": false
}
```

Every path and evidence reference must be null. It uses the
`functional_integration` project split and cannot support selection, accuracy or
population evidence.

`adam_controlled_recordings` is for local functional integration only:

```json
{
  "source_id": "adam_controlled_recordings",
  "manifest_state": "owner_controlled_local",
  "licence_state": "owner_authorised_local_functional_integration",
  "role": "functional_integration_only",
  "external_transfer": false
}
```

It also uses `functional_integration` and cannot fill the failed development or
tuning evidence gate. Audio must be copied into the private research root and
bound by its content SHA256. Audio-quality, ASR, alignment and local-system
evidence must use:

```json
{
  "path": ".research_data/speech_sound_patterns/PRIVATE_FILE",
  "sha256": "64 lowercase hexadecimal characters"
}
```

Cached provider evidence and insertion evidence require the same binding when
present. A proposal may inherit the checksum-bound raw system record or carry
its own reference. The command reads no path before the manifest scope, source,
task and split have passed validation.

SpeechOcean is not an extractor trial source. Its sentence recordings are
checksum bound only for the safe aggregate adequacy audit and cannot masquerade
as the controlled written-word task. The audit uses the development-and-tuning
whitelist that records zero held-out participants; it never opens the full split
assignment containing held-out identities.

## Manifest boundary

A manifest must be a new explicit JSON file below:

```text
.research_data/speech_sound_patterns/candidates/manifests
```

It binds the frozen prompt pack, declares `network_access: false`,
`held_out_access: false` and `normal_pipeline: false`, and uses task
`controlled_word_research_en_v1` with elicitation mode `written_word`. Each trial
must retain stable participant, session, attempt, trial and stimulus identifiers;
the known presented word; audio and quality provenance; raw ASR and alignment;
every local system result for every prompt-pack opportunity; optional cached
provider evidence; and separate insertion observations.

The ASR hypothesis never supplies the intended word. The intended word comes
only from the versioned presented stimulus and must be one of the twenty frozen
pack words.

## Assemble one private artifact

The output directory must be a new path below:

```text
.research_data/speech_sound_patterns/candidates
```

It cannot overlap the manifests directory, an existing artifact, the normal
root `output`, or an ancestor carrying pipeline sentinels such as `master.json`
or `run_manifest.json`.

```sh
SPEECH_SOUND_OFFLINE=1 python3 -m speech_sound_patterns.extract_candidates \
  --manifest .research_data/speech_sound_patterns/candidates/manifests/MANIFEST.json \
  --output-dir .research_data/speech_sound_patterns/candidates/NEW_OUTPUT \
  --acknowledge-developer-only
```

The command writes exactly:

```text
NEW_OUTPUT/speech_sound_candidates.json
```

It writes atomically and never overwrites. The artifact preserves raw evidence
and separates:

- word-level ASR disagreement from sound-level evidence;
- expected sound opportunities from insertion observations;
- unavailable evidence from unsupported contexts;
- documented reference disagreement from model conflict;
- raw system proposals from reviewed relation truth; and
- a generic repeated-evidence audit from any named pattern, clinical inference
  or coaching result.

Insertion observations never increase the expected sound denominator. Repeated
support deduplicates repeated rows for the same recording and opportunity, keeps
distinct opportunities in one recording distinct, and excludes unscorable
reference variants from the eligible denominator. With the current frozen
decision it audits structure only and emits nothing.

## Validate

Validate the committed contract and aggregate report without reading a private
artifact:

```sh
python3 -m speech_sound_patterns.validate_candidates
```

That command says explicitly that no private artifact was supplied or checked.
Validate one private artifact against the exact manifest from which it was
built:

```sh
python3 -m speech_sound_patterns.validate_candidates \
  --manifest .research_data/speech_sound_patterns/candidates/manifests/MANIFEST.json \
  --artifact .research_data/speech_sound_patterns/candidates/NEW_OUTPUT/speech_sound_candidates.json
```

Manifest-backed validation checks the manifest checksum, rechecks every private
evidence checksum, rebuilds the artifact and requires exact equality. A
self-consistent edit to copied raw evidence therefore cannot certify itself.

Run the focused tests and every item 22 validator:

```sh
python3 -m unittest tests.test_speech_sound_candidates
python3 -m speech_sound_patterns.validate
python3 -m speech_sound_patterns.validate_corpora
python3 -m speech_sound_patterns.validate_benchmark
python3 -m speech_sound_patterns.validate_comparison
python3 -m speech_sound_patterns.validate_selection
python3 -m speech_sound_patterns.validate_variety_probe
python3 -m speech_sound_patterns.validate_prompt_pack
python3 -m speech_sound_patterns.validate_candidates
```

## What this cannot establish

- A raw proposal is not a produced-phone truth, an error, a correctness result
  or a reviewed target relation.
- Agreement between automatic systems is not human truth and does not select a
  rule.
- One token or one word cannot establish repetition.
- Repetition is not a named phonological pattern, cause, severity, diagnosis,
  screening result or treatment recommendation.
- Synthetic fixtures and Adam's recordings cannot repair the missing
  task-matched development and tuning evidence.
- The unreviewed research prompt pack is not the product onboarding task.
- Nothing here enters listener, evaluator, claim ledger, coaching, history,
  progress or any user-facing result.
