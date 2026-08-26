# Reference variety probe evidence

The per clip evidence behind `../variety-probe-v1.2.0.json`. It is here so the
report can be checked by someone who does not have the private research data.

## Reproduce the report

```bash
python3 -m speech_sound_patterns.variety_probe_score --output /tmp/report.json
```

About two minutes. It needs `numpy` and nothing else: no audio, no model, no
download, no credentials, no GPU. Then compare:

```bash
python3 -m speech_sound_patterns.validate_variety_probe /tmp/report.json
```

The result is byte identical to the committed report. That is asserted, and it
was checked rather than assumed, in `release/redistribution-decision-v1.0.0.json`.

## What is in here

2,400 records, one per clip, in four directories named for the declared accent
group. Each record carries the clip's frame count, and for each of the two
reference varieties a canonical log likelihood and one entry per expected phone
target giving the phone token, its index in the expected sequence, and its
goodness of pronunciation score.

`bundle-manifest.json` records the counts, the total size and a composite hash
over the whole bundle.

## What is deliberately not in here

No audio. No prompt text and no transcript. No Common Voice metadata. No
contributor identifier, and no mapping that could recover one.

The `participant` field is an opaque key minted for this bundle. The stored
evidence it was built from carries each contributor's verbatim Common Voice
`client_id`, which joins directly against the public corpus and would recover
that person's entire clip history, declared accent, age and gender. The mapping
from a real identifier to a bundle key is not written to disk anywhere.

The keys are not arbitrary. They are globally unique across all four
directories, because one scoring function groups by the participant value alone
while every other call site groups by source and participant together, and they
preserve the sort order of the original identifiers, because the speaker
clustered bootstrap indexes speakers in sorted order. Change either property and
the published intervals move.

## Licensing

The underlying speech is Common Voice 26.0, licensed CC0 1.0, accessed through
the Mozilla Data Collective under its consumer terms of 2026-05-06. **Those
terms prohibit hosting the dataset elsewhere and prohibit re identifying
contributors, so no Common Voice audio is redistributed here and none may be.**
This bundle is a derived measurement record rather than the dataset.

The phone tokens are written in the Montreal Forced Aligner English phone set:

> Montreal Forced Aligner English pronunciation dictionaries v3.1.0 by McAuliffe
> and Sonderegger, reused under CC BY 4.0.

Full attribution is in `NOTICE.md` at the repository root.

## What this evidence cannot establish

It carries no human judgment of any kind. Nobody listened to these clips and
nobody labelled a phone in them. A flag is a model's disagreement with a
dictionary, and these are native speakers reading known text, so a flag is
presumed a false concern rather than a pronunciation error.

The scoring model shares training lineage with the evaluation data, and the
report declares that rather than resolving it. Nothing at group level in the
report is distinguishable from zero.
