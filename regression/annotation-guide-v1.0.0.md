# Speech regression annotation guide, version 1.0.0

## Purpose

Truth labels describe what an independent reviewer or a controlled generator
established. They are not copied from pipeline output. A software snapshot only
records current behaviour and cannot be used as evidence that the behaviour is
correct.

## Required provenance

Every truth file records the exact audio hash where audio exists, reference
source, annotator role, guide version, annotation date, adjudication status,
and whether the labels were created independently from the pipeline.

`single_annotator_reviewed` means one identified human reviewed every included
label. `adjudicated` means disagreements between reviewers were resolved.
`synthetic_ground_truth` is reserved for facts fixed directly by generator
parameters. Draft or pending labels cannot produce a passing validity result.

## Labels

- Speaker labels identify the audible speaker, not the provider cluster.
- Word timing marks the audible beginning and end of a selected word. The
  default comparison tolerance is 0.10 seconds for real recordings and 0.02
  seconds for generated controls.
- Overlap is present when two voices are simultaneously audible.
- A backchannel is a short listener response inside another person's continuing
  turn. All backchannels in an evaluated interval must be labelled so false
  positives and false negatives can both be reported.
- A pause is an audible within speech silence. Record its start, end, and the
  tolerance appropriate to the annotation method.
- Renderer events are `drag`, `loud`, `uptalk`, or `filler`. An exhaustive
  interval must include both present and absent events so the harness can report
  false positives and false negatives.
- Metric truth records the primitive reference, unit, value, and metric specific
  tolerance. A pipeline value is never its own reference.
- Quality truth records the designed signal condition or an independent audio
  measurement and the expected quality status.
- Verification truth records whether a deliberately valid or invalid evidence
  package should pass.

## Scope and percentages

Each file declares its evaluated coverage. A result may only describe that
coverage. Every percentage must include its numerator, denominator, and named
reference source. Unlabelled regions are not counted as correct, incorrect, or
exhaustively negative.

