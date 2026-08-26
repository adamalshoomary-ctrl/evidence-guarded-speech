# Selection and rejection record runbook, checkpoint 22E5

Checkpoint 22E5 records what was decided about every lane after the two frozen
comparisons. It measures nothing. It runs no model, sends no audio, touches no
provider and reads no held-out participant. If a command in this runbook wants
to run a candidate system, it is the wrong command.

The committed artifact is `selection-record-v1.1.0.json`. Version 1.0.0 stays on
disk unedited: it is the same decision written against the provider register of
its day, before checkpoint 22E6 corrected the Bookbot lane's disproved training
source. Each version pins the register it was written against, both still
validate, and both still rebuild byte for byte. Build or validate an earlier
version with `--record-version`.

## What the record is, and what makes it hard to weaken

The written verdicts, reasons, limitations and reopening conditions live in
`build_selection_record.py`. The numbers do not: gate outcomes are copied out of
the committed powered comparison, and each lane's role, status, audio policy and
outstanding blockers are copied out of the fail-closed provider register.

Four guards hold it in place:

1. `selection_record.LANE_DECISION_PROFILES` pins every lane's verdict and the
   basis it rests on, so changing a verdict is a code change and a test change,
   never a quiet edit to a JSON file.
2. A verdict may not contradict the register. Nothing conditional, blocked,
   declined or rejected can be recorded as selected, and nothing unmeasured can
   claim a measured basis or report a gate count.
3. `selected_candidate` is reachable only when the committed powered comparison
   actually reports a candidate on that lane passing every unchanged gate on
   both partitions. None does.
4. The record pins the register and all four committed reports by hash. Editing
   any of them invalidates the record instead of leaving a stale verdict
   standing.

## Rebuild and validate

```sh
python3 -m speech_sound_patterns.build_selection_record
```

The builder refuses to run if the powered comparison no longer reports
`no_selection`, because the written verdicts were reasoned from that outcome and
would have to be revisited by hand. It validates what it wrote before exiting.

```sh
python3 -m speech_sound_patterns.validate_selection
python3 -m speech_sound_patterns.validate_comparison
python3 -m speech_sound_patterns.validate_benchmark
python3 -m speech_sound_patterns.validate
python3 -m unittest tests.test_speech_sound_selection_record
```

A rebuild must reproduce the committed file byte for byte, and a test asserts
exactly that. If it does not, either the evidence changed or a verdict changed,
and both need an owner decision rather than a rebuild.

## What the record does not do

- It selects nothing. The committed decision is `no_selection`.
- It freezes no mapping, feature, threshold or provider configuration, because
  there is nothing to freeze.
- It does not authorise more threshold searching, a weaker gate, a larger slice
  of the same corpus, or an early look at the 26 sealed held-out adults.
- It releases no detector, score, coaching output, progress metric or product
  behaviour, and the ordinary pipeline is unchanged by it.

## Reopening a lane

Every reopenable lane lists what would reopen it. Meeting those conditions does
not reopen the lane by itself: it makes an owner decision possible. The order is
always the same as it was in checkpoint 22E, namely permission first, then a
frozen contract, then measurement, then a record.
