# Notices and attribution

Copyright (C) 2026 Adam Alshoomary.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. See [`LICENSE`](LICENSE) for the full text.

SPDX identifier: `GPL-3.0-or-later`.

## Why this licence and not a permissive one

`praat-parselmouth` is licensed GPL 3.0 or later, it statically embeds Praat's
GPL C++ sources, and it is a hard runtime dependency of the acoustics stage
(`pipeline/acoustic_primitives.py`, `pipeline/acoustics.py`). Distributing this
work under a permissive licence would require removing that dependency first.

Nothing in the pinned dependency closure conflicts with GPL 3.0 or later. The
Apache 2.0 packages in the closure are the reason the tag is *3.0 or later*
rather than *2.0*: Apache 2.0 is incompatible with GPLv2 and compatible with
GPLv3.

## Data and reference material

None of the corpora below is redistributed here. Only derived, non audio
material appears in this repository, and each item states what was derived.

### Montreal Forced Aligner English pronunciation dictionaries v3.1.0

> Montreal Forced Aligner English pronunciation dictionaries v3.1.0 by
> McAuliffe and Sonderegger, reused under CC BY 4.0.

Licence CC BY 4.0. Citation: McAuliffe, Michael and Sonderegger, Morgan.
English MFA dictionaries v3.1.0, Montreal Forced Aligner published models, 2024.
The `english_us_mfa` and `english_uk_mfa` dictionaries are the American and
British reference varieties throughout the reference variety probe. Derived
material appearing here: phone inventories, opportunity counts, and the phone
tokens carried in the published probe evidence bundle.

### English Wiktionary, via WikiPron and Wiktextract

> Entries extracted from English Wiktionary by Wiktextract and reused under
> Wiktionary's CC BY SA terms.

Licence CC BY-SA 4.0. This is the only share alike input in the project. It is
one way compatible into GPL 3.0, which is the compatibility path relied on here.
The verbatim transcriptions are deliberately not distributed: the research
prompt pack records per phoneme opportunity structure only, and its own
`distribution_boundary` block lists the full expected phone sequences and the
eligible word pool as withheld. WikiPron commit
`d282e848a211ea31cfd730f0ced8bc8cdab9e83d`.

### LibriSpeech, OpenSLR 12

> Cite Panayotov et al., LibriSpeech, ICASSP 2015, and retain CC BY 4.0
> attribution.

Licence CC BY 4.0. LibriSpeech is built from LibriVox public domain audiobooks.
The regression fixture recordings distributed with this repository are assembled
from the `dev-clean` development split, and the fixture manifest names every
speaker, chapter and utterance used. See `regression/fixtures/README.md`.

### Common Voice 26.0, via Mozilla Data Collective

Dataset licence CC0 1.0, so no attribution is required. It is recorded anyway.
Citation: Mozilla Data Collective Curators, Common Voice Scripted Speech 26.0,
datasets `cmrt710620013mm071t45y6wb` (Australian English),
`cmrt6zrob000zmm07yqwjlpwi` (British English),
`cmrt6zbgx000vmm07hfuefigk` (American English male) and
`cmrt70j4z001qmm07nvfsmgmr` (American English female).

**No Common Voice audio is redistributed here, and none may be.** The dataset
content is CC0, but access was obtained under the Mozilla Data Collective
consumer terms of 2026-05-06, which prohibit hosting a Dataset outside the
platform and prohibit re identifying contributors. The published probe evidence
bundle carries derived scores only, with contributor identifiers replaced by
opaque per bundle keys. See `speech_sound_patterns/variety-probe-evidence/README.md`.

### SpeechOcean762 v1.2.0

> Cite Zhang et al., SpeechOcean762, Interspeech 2021, and retain CC BY 4.0
> attribution.

Licence CC BY 4.0. Used for the frozen benchmark. Derived material appearing
here: the benchmark phone map between the SpeechOcean762 ARPAbet reference
inventory and a candidate IPA inventory.

### Common Phone 1.0

Licence CC0 1.0. Klumpp et al., Common Phone 1.0, Zenodo record 5846137.

### Acted clear speech corpus

> Cite Catherine Mayo, Acted clear speech corpus, DOI 10.7488/ds/138, under
> CC BY 3.0.

## Code adapted from other projects

`speech_sound_patterns/comparison_commonphone.py` contains a 101 symbol IPA
symbol table copied verbatim, and an adapted decoding architecture, from
`github.com/PKlumpp/phd_model`, `phonetics/ipa.py`, commit
`dfff4848baf1a6698c245e83f8768a577c353558`, licensed CC0 1.0.

## Pretrained models

None of these weights is redistributed here. They are downloaded at run time
and are listed so their terms are visible before a run starts.

| Model | Role | Licence |
|---|---|---|
| `pyannote/speaker-diarization-3.1` | speaker diarization | MIT weights, **gated**: needs a Hugging Face token and manual licence acceptance |
| `Systran/faster-whisper-small` | local transcription | MIT |
| torchaudio `WAV2VEC2_ASR_BASE_960H` | forced alignment on the local path | **licence not independently verified by this project** |
| `silero_vad` | voice activity detection | MIT |
| `espnet/powsm` | research lane phone comparator | CC BY 4.0 |
| `pklumpp/Wav2Vec2_CommonPhone` | research lane phone recognizer | CC0 1.0 |
| `onnx-community/wav2vec2-lv-60-espeak-cv-ft-ONNX` | probe phone posteriors | Apache 2.0 declared |
| `changelinglab/PhoneticXeus` | feasibility only, quarantined | Apache 2.0 declared, provenance incomplete |

Two honest caveats. The core pipeline models are pinned by identifier and not by
repository revision, which is a reproducibility gap this project has not closed.
And the scoring model behind the reference variety probe is fine tuned on Common
Voice while the probe evaluates on Common Voice speakers, which this project's
own rules disqualify elsewhere; that overlap is declared rather than resolved,
and the declaration travels with the report.

## Copyleft and reciprocal dependencies

Beyond `praat-parselmouth`, the pinned closure contains:

- `soxr` (LGPL 2.1 or later), which bundles libsoxr;
- `certifi` and `tqdm` (MPL 2.0), file level copyleft, GPL compatible;
- `regex` (Apache 2.0 and CNRI-Python);
- `llvmlite` (BSD 2-Clause and Apache 2.0 with LLVM exception).

Everything else in the 129 package closure is MIT, BSD, Apache 2.0, ISC, PSF or
public domain equivalent.

`ffmpeg` and `ffprobe` are invoked as separate programs for container probing and
decoding. They are not linked into this work. A GPL build of ffmpeg is common and
carries its own terms.

## Research environments outside the pinned closure

`speech_sound_patterns/environments/` holds lockfiles for five isolated research
environments that are not part of the runnable pipeline: Montreal Forced Aligner
3.4.1 (MIT), PhoneticXEUS, POWSM, Common Phone, and the Meta wav2vec2 ONNX lane.
Two packages are imported by that isolated research code and are not part of the
pipeline requirements: `panphon` (MIT, pinned at 0.22.2 with wheel and data file
hashes in `speech_sound_patterns/feasibility.py`) and `espnet2` (Apache 2.0,
pinned as `espnet==202511` in the POWSM environment lockfile).

## A correction worth recording

`speech_sound_patterns/provider_register/provider-register-v1.2.0.json` records a
rejection of the Allosaurus phone recognizer on the ground that GPL 3.0 copyleft
was incompatible with a commercial product. That reasoning belonged to a
commercial direction this project abandoned on 2026-08-22, and it was already
inconsistent with a codebase depending on GPL parselmouth. The rejection record
is left in place because it is history, but it no longer holds on licence
grounds.
