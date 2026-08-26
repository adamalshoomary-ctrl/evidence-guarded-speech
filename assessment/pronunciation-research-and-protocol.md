# Controlled pronunciation and intelligibility research protocol

Version: 1.0.0  
Status: research only, not validated  
Owner design review: approved to implement on 2026-07-19

## Decision

No pronunciation provider or model is approved. The controlled word task stays
outside the normal onboarding assessment and cannot affect coaching, progress,
ranking, screening or diagnosis.

The repository now defines the task, evidence, comparison and failure rules
needed for a future independent study. It does not contain an active word pack
or pronunciation measurement. The exact words and accepted pronunciation
variants need qualified phonetic or speech pathology review and owner approval
before anyone records the task.

This boundary is deliberate. The current repository has no representative
human-labelled pronunciation corpus. Adam's recordings can help development,
but they cannot establish performance for other accents, dialects, devices,
voice ranges or speech differences.

## The two constructs

### Listener intelligibility

Listener intelligibility means the word an independent listener actually
understands. A listener hears only one participant attempt, without seeing the
prompt, expected word, system answer or speaker identity, and types the word
they heard. Every response and disagreement is retained.

This is not an accent rating and it is not a rating of how easy the speech felt
to understand. Research has shown that accentedness, perceived difficulty and
actual word understanding are related but separate. A strong accent can remain
highly intelligible. [Munro and Derwing, 1995](https://doi.org/10.1111/j.1467-1770.1995.tb00963.x)

### Phonetic observation

Phonetic observation means a broad IPA record of the sounds produced in a
controlled word attempt. At least two qualified reviewers independently
transcribe the audio while blind to every automatic system output. Their
original transcriptions remain stored, and a documented adjudication may add a
reference result without erasing disagreement.

The reviewers consider legitimate accent, dialect and language-transfer
patterns before applying an error label. ASHA guidance likewise requires
language and dialect rules, phonetic context and linguistic background to be
considered rather than comparing everyone with one mainstream English variety.
[ASHA speech sound guidance](https://www.asha.org/practice-portal/clinical-topics/articulation-and-phonology/)

Listener intelligibility and phonetic observation are never merged into one
pronunciation score. One describes what was understood. The other describes
the produced sound evidence.

## Controlled word task

The future pilot is a short English solo task targeting 20 to 40 familiar
words and about two minutes of recording. The exact list is intentionally
empty in version 1 because it has not received professional review.

The normal path shows one written word at a time. A recorded prompt alternative
supports someone for whom reading is unsuitable. These modes are not considered
equivalent: reading ability and word familiarity affect the written task,
while hearing, memory and prompt imitation affect the spoken alternative.

Prompt audio must end before the participant recording begins. Research
listeners must never hear the prompt. The task uses the strict baseline audio
quality policy and stops when the participant asks, becomes fatigued or
distressed, uses an unsupported language, or repeatedly cannot obtain usable
audio.

Research collection, human review and raw audio retention remain separate
consent choices. A person who skips the task loses no normal coaching access.

## Word pack and pronunciation variants

Before activation, qualified reviewers must:

1. choose familiar and culturally suitable words;
2. document which sound and word position each item probes;
3. cover sounds in more than one context where pack length permits;
4. record legitimate word-specific variants across the supported English
   varieties;
5. mark unresolved variants unscorable rather than forcing a default;
6. review both the written word and recorded prompt; and
7. obtain a separate owner approval.

Self-reported English variety is useful context, not automatic truth. The
accepted set is a union of reviewed legitimate forms, not a choice of the
closest American, British, Australian or other prestige model.

## Primitive evidence and denominators

Each presented word is an expected word opportunity, even if it is omitted.
A scorable word opportunity is what remains after documented technical and
evidence exclusions. Expected and scorable sound opportunities use the same
distinction after applying the reviewed variant set.

Word outcomes remain separate:

- understood as intended;
- a different word heard;
- omission;
- addition;
- uncertain; and
- unscorable.

Sound outcomes also remain separate:

- accepted variant;
- substitution;
- deletion;
- insertion;
- break;
- uncertain; and
- unscorable.

Insertions and added words are separate counts. They never silently alter the
expected-opportunity denominator. Missing or excluded evidence never becomes a
zero. Every result retains the trial, stimulus, elicitation mode, audio segment,
quality, variant-set version, human references, raw system outputs and versioned
provenance.

## Candidate comparison

The candidates cover different technical approaches, but none supplies truth.

| Candidate | Useful research output | Main limitation in this product |
|---|---|---|
| Microsoft Azure Pronunciation Assessment | Scripted word and phoneme results, omissions, insertions and locale metadata | Its documented accuracy construct is closeness to native-speaker pronunciation, features vary by locale, and the model is a changing black box. |
| SpeechAce | Word, syllable and phoneme results, a `sound_most_like` field and custom phoneme input | Its model is proprietary, documented dialect options are narrow, and provider validation is not independent local truth. |
| SpeechSuper | Word and phoneme results plus insertion, deletion and substitution outputs | It describes alignment with native English patterns, remains proprietary, and local subgroup performance is unknown. |
| Local alignment and phone-recognition baseline | Inspectable alignments, hypotheses, dictionaries, models and code versions | Forced alignment can make the expected text fit the audio; a phone recognizer is not a validated assessment; dictionaries can encode accent bias. |
| Current ASR word baseline | Unknown-word transcript and confidence | ASR disagreement can help test word recognition but cannot identify phonetic truth. |

Current capability descriptions come from the providers' documentation:
[Microsoft](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment),
[SpeechAce](https://docs.speechace.com/),
[SpeechSuper](https://docs.speechsuper.com/) and
[Montreal Forced Aligner](https://montreal-forced-aligner.readthedocs.io/en/v3.4.1/user_guide/index.html).

The same frozen recording must be sent to every candidate. Raw responses,
locale or dialect settings, model versions, SDK or API versions, dictionaries
and code versions are retained. Agreement between two or more automatic
systems is still only agreement.

`assessment/pronunciation_benchmark.py` provides the offline comparison
scaffold. It accepts only records tied to the independent listener and phonetic
reference, enforces participant-exclusive splits, and reports research counts,
coverage, agreement, issue precision and recall, and accepted-variant false
concerns. It cannot create a product-facing result.

## Independent evaluation

Participants are separated across development, threshold tuning and held-out
evaluation. A participant can appear in only one split. Human annotators are
blind to provider outputs, and candidate systems receive the same recordings.

Thresholds are chosen using development and tuning participants, then frozen
before the held-out evaluation. The study must report:

- agreement with the blind listener reference;
- sound-issue precision, recall and F1;
- false concerns on accepted accent and dialect variants;
- abstention and coverage;
- calibration of any retained confidence;
- exact same-input repeatability;
- repeated human-production reliability; and
- uncertainty and results by English variety, first-language background,
  voice range, device, audio quality, speech difference and elicitation mode.

The participant and listener sample sizes must be justified before collection.
No numeric release threshold is invented from the current owner recordings.

## Failure and release behavior

Poor audio, an unsupported language or variety, ASR or alignment conflict, too
few opportunities, unresolved human disagreement, remote failure and missing
provider version all produce an explicit `unavailable` result. One resolvable
technical failure may be retried once. There is no fallback score and no LLM
pronunciation judgment.

Normal coaching remains blocked. A future separately approved release could at
most make a high-confidence, word-specific observation supported by listener
and phonetic evidence, link it to audio, and avoid any accent judgment. Overall
scores, progress, ranking, screening and diagnosis remain outside this
protocol.

The complete machine-readable contract is
`assessment/pronunciation-research-v1.0.0.json`. Validate it with:

```text
python3 -m assessment.validate_pronunciation
```
