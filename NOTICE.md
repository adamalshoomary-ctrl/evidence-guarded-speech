# Notices and attribution

Copyright (C) 2026 Adam Al Shoomary.

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

The two regression fixture recordings are the only third party audio in this
repository. They are assembled from LibriSpeech, under CC BY 4.0.

Releases up to `v0.4.0` also carried the research code and derived evidence from
the Montreal Forced Aligner dictionaries, English Wiktionary, Common Voice,
SpeechOcean762, Common Phone and the acted clear speech corpus. That material
left the main branch on 2026-09-23. Its attribution travels with it in the
`NOTICE.md` at tag `v0.4.0`.

### LibriSpeech, OpenSLR 12

> Cite Panayotov et al., LibriSpeech, ICASSP 2015, and retain CC BY 4.0
> attribution.

Licence CC BY 4.0. LibriSpeech is built from LibriVox public domain audiobooks.
The regression fixture recordings distributed with this repository are assembled
from the `dev-clean` development split, and the fixture manifest names every
speaker, chapter and utterance used. See `regression/fixtures/README.md`.

## Pretrained models

None of these weights is redistributed here. They are downloaded at run time
and are listed so their terms are visible before a run starts.

| Model | Role | Licence |
|---|---|---|
| `pyannote/speaker-diarization-3.1` | speaker diarization | MIT weights, **gated**: needs a Hugging Face token and manual licence acceptance |
| `Systran/faster-whisper-small` | local transcription | MIT |
| torchaudio `WAV2VEC2_ASR_BASE_960H` | forced alignment on the local path | **licence not independently verified by this project** |
| `silero_vad` | voice activity detection | MIT |

One honest caveat. The pipeline models are pinned by identifier and not by
repository revision, which is a reproducibility gap this project has not closed.

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
