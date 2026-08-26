# The offline transcription path

The pipeline can transcribe on this machine instead of sending audio to
AssemblyAI, so it runs with no paid credentials.

```
python3 pipeline/run_all.py --mode solo --audio AUDIO_PATH --transcriber local
python3 pipeline/run_all.py --mode conversation --speakers 2 --transcriber local
```

`--transcriber assemblyai` remains the default, so nothing about an existing run
changes unless the flag is passed.

## The rule that matters most

**There is no fallback between the two paths.** A missing AssemblyAI key fails
the run; it never quietly switches to the local model. The two do not transcribe
the same way, they do not produce the same evidence, and a record that could
have come from either is not a record at all. Every run states which one
produced it, in `transcript.json` and in the provenance block of `master.json`.

## What it costs, measured rather than assumed

Measured on 2026-08-23 against the AssemblyAI transcript of the same two
recordings. **Neither transcriber is truth.** No expert verbatim transcript of
these recordings exists, so everything below is agreement between two systems,
which this project does not treat as evidence that either is correct.

### Choosing the model, and the decoding prompt

Whisper is trained to tidy speech up, and this project measures the untidy
parts. That turned out to be a decoding problem rather than a model size
problem. On the solo recording, against an AssemblyAI reference of 278 words
carrying 5 filled pauses:

| model | disfluency priming | seconds | words | filled pauses | word agreement | reference pauses kept |
|---|---|---|---|---|---|---|
| small | no | 32.1 | 269 | 0 | 0.9653 | 0 of 5 |
| small | **yes** | 21.5 | 282 | 8 | 0.9679 | **5 of 5** |
| large-v3 | no | 173.7 | 270 | 1 | 0.9708 | 0 of 5 |
| large-v3 | yes | 115.6 | 277 | 8 | 0.9694 | 5 of 5 |

Unprimed, both models returned **none** of the five filled pauses. Primed, both
returned **all five**. The large model cost five times the runtime and a three
gigabyte download to move word agreement by about half a percentage point.

So the local path uses `small` with a short priming prompt of filled words and
discourse markers. The prompt names nothing about any recording's content, so it
cannot steer a transcript toward a subject.

Its cost is the other direction: primed, the local path reported **8** filled
pauses where AssemblyAI reported 5, and the three extra are insertions with no
counterpart. Whether AssemblyAI missed them or Whisper invented them **cannot be
settled from this evidence** and is not settled here. It would need someone
listening to the audio.

The timings are single runs on one machine and are not a benchmark. The primed
small run being faster than the unprimed one is model caching.

### The two recordings end to end

Full pipeline runs of both recordings through both paths:

| run | words | fluency candidates | text derived families |
|---|---|---|---|
| solo, AssemblyAI | 279 | 5 | available |
| solo, local | 282 | 4 | **unavailable** |
| conversation, AssemblyAI | 236 | 7 | available |
| conversation, local | 207 | 4 | **unavailable** |

The solo recording came out slightly longer on the local path and the
conversation recording about twelve percent shorter. One recording each way is
not a rate, and no claim is made about which transcript is closer to what was
said.

The candidate counts differ because four of the five families are switched off
rather than run on evidence they cannot use. That difference is declared in the
artifact, so a reader comparing two runs can see it instead of inferring it from
a smaller number.

## What the local path cannot do

Two capabilities depend on evidence the local path does not produce. Both are
**declared as unavailable rather than silently returning nothing**, because a
zero here would read as "none found" when the truth is "not measured".

### Second voice detection in solo recordings

Whisper produces no speaker labels. The solo contamination check reads them, so
it records:

```
"status": "unavailable"
"method": "no_speaker_clusters_available_v1"
```

with a warning saying the recording has not been checked for a second voice at
all. A solo baseline recorded through the local path has **not** been screened
for contamination.

Conversation attribution is unaffected, because it comes from diarization rather
than from the transcriber.

### The text derived fluency event families

This is the subtler one and it was found by running the path rather than by
reading the code.

The forced aligner produces a per word score. It is **not** an ASR confidence:
it is a different quantity on a different scale, and the fluency contract's
eligibility floor of 0.5 was calibrated against a provider's ASR posterior. On a
real recording the aligner scored a genuine repeated phrase at 0.307 and 0.154,
so thresholding it as though it were a confidence **discarded a real repetition
while appearing to work**.

The local path therefore writes that score as `alignment_score` and emits no
`confidence` at all. Four of the five fluency families need one, so they report:

```
"text_derived_families": "unavailable"
```

The fifth family, prolonged sounds, reads timing rather than text and is
unaffected. It returned the same candidates on both paths.

**No fluency threshold was retuned for the local path.** Recalibrating a
release locked contract to a new provider's numbers would be exactly the kind of
quiet accommodation this project exists to refuse.

## Credentials still needed

| mode | AssemblyAI | Hugging Face token | Gemini |
|---|---|---|---|
| solo, local transcriber | not needed | not needed | optional, degrades safely |
| conversation, local transcriber | not needed | **needed** | optional, degrades safely |

Solo is fully credential free. Conversation still needs a Hugging Face token and
manual acceptance of the pyannote licence, because diarization uses a gated
model. The local transcription stage itself deliberately uses Silero for voice
activity rather than the WhisperX default, which is pyannote, so the stage whose
job is to need no credentials does not need one.

## A cost worth knowing about

A local run transcribes the audio twice: once in the transcription stage and
once inside the alignment stage, which has always run its own local model. They
run in parallel and are independent by design, so the wall clock cost is small,
but the work is duplicated. Sharing one inference between the two stages would
couple them and is not done.

Observed wall clock on this machine: solo 261 seconds against 212 with
AssemblyAI, conversation 387 against 349.
