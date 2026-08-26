# About this repository

This is the public form of a private research repository. It carries the code,
the contracts, the evidence and the record of what was decided. It does not
carry the recordings that project was built on, or anything derived from them.

Start with `project-purpose.md` for what this project claims and refuses,
`README.md` for how to run it, and `AGENTS.md` for the working rules.

## Why a separate repository rather than a cleaned one

The working repository tracks the owner's own recordings, a two speaker
conversation involving another person, and full transcripts and evaluations
derived from them, in its working tree **and in its git history**. Deleting a
file from a tree does not remove it from history. A history rewrite was
considered and rejected: it changes every commit hash anyway, so it preserves
nothing worth keeping, and it cannot prove completeness. This repository was
built fresh instead, so its history has one origin and nothing behind it.

## What was removed

41 of 2844 tracked files were left behind.

| Removed | Why |
|---|---|
| `audio/` | The owner's own recordings, and one of them carries a second person who consented to being recorded and was never asked about publication. |
| `output/` | Full transcripts, evaluations and derived measurements of those recordings, including a zip that duplicates an entire run. |
| `history.json` | The owner's personal longitudinal record. |
| `progress.md` | The same record in prose. |
| `regression/truth/real_conversation.json` | Truth labels for an excluded recording, pinned to its exact byte hash. The openly licensed fixture_conversation record replaces it. |
| `regression/truth/real_solo.json` | The same for the solo recording. The fixture_solo record replaces it. |
| `release/snapshot-contract-v1.0.0.json` | The contract lists, as literal strings, exactly the private material it removes. Publishing it would republish every one of them, which is the same mistake the privacy validator made when its deny list named the owner's recording inline. The rule identifiers, their reasons and how often each fired travel instead, in release/snapshot-provenance.json. |
| `release/overlay/AGENTS.md` | The overlay is copied into place as AGENTS.md, so shipping it a second time under its build path would only duplicate it. |

A small number of strings were also replaced across the surviving files: a place
name, some machine local paths, a cloud resource name, a run identifier and a
few third party email addresses. Every replacement, and its reason, is listed in
`release/snapshot-provenance.json`, together with how many times each one fired
when this snapshot was built. The strings themselves are not listed, for the
obvious reason: a list of the private strings that were removed would be a list
of the private strings.

## What the removals cost you

- **The regression records pinned to the owner's recordings are gone.**
  `regression/fixtures/` holds openly licensed replacements assembled from
  LibriSpeech. They prove the pipeline runs. They validate nothing: they are read
  audiobook speech taking turns, with no overlap, no interruption and no
  disfluency.
- **`speech_sound_patterns/accent_contrast.py` cannot run**, because its whole
  design is holding one speaker constant across two accent targets. The frozen
  result of the single run that was made is committed and readable.
- **`.research_data/` was never tracked and is not here.** The part needed to
  reproduce the one published analysis has been extracted and pseudonymised into
  `speech_sound_patterns/variety-probe-evidence/`.
- **No finished pipeline run is committed.** Produce one from a fixture.

## What you can check for yourself

```text
python3 -m speech_sound_patterns.variety_probe_score --output /tmp/report.json
python3 -m speech_sound_patterns.validate_variety_probe /tmp/report.json
```

About two minutes, needing only `numpy`. The result is byte identical to the
committed report. Read the report's uncertainty block before quoting any number
from it: nothing at group level is distinguishable from zero, and the single
result that survives multiple comparison correction carries a lexical confound
that stops it being a claim about British English.

## Licence

GPL 3.0 or later. See `LICENSE`, and `NOTICE.md` for third party attribution.
