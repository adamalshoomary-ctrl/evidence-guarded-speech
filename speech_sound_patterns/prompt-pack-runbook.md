# Research prompt pack runbook, checkpoint 22F

Checkpoint 22F builds the conservative research prompt pack: twenty chosen
English words and the consonant opportunities inside them. It records nothing
about any speaker, scores nobody, selects nothing, applies none of the five
frozen gates and produces no artifact.

The committed artifacts are `prompt-pack-contract-v1.0.0.json`, frozen before any
word was read out of a dictionary, and `research-prompt-pack-v1.0.0.json`, the
pack itself.

## What this is for

Every item 22 measurement so far has read other people's recordings against other
people's sentences. To ask whether a person produced the `s` at the start of
*safe*, two things must exist first: a known word they were asked to say, and a
defensible written statement of what that word's consonants are. Neither existed
in this project. Checkpoint 22G, which builds the candidate extractor, has
nothing to point at until this pack exists.

**This is not the product's onboarding word pack.** The word pack in
`assessment/pronunciation-research-v1.0.0.json` is still empty and still
`awaiting_professional_review`, and the pack validator fails if that ever stops
being true while this developer pack exists.

## What the pack contains

| | |
|---|---|
| Words | 20 |
| Consonant opportunities | 62 |
| Scorable | 61 |
| Unscorable | 1 |
| Consonants probed | 21 |
| Consonants reaching two or more word positions | 20 |
| Eligible pool the twenty were chosen from | 2,578 words |

The words are *pumpkin, handbook, mangrove, nonstop, jukebox, forward, beyond,
yellow, leg, range, torch, wizard, cash, safe, gravy, sugar, song, zero, child*
and *dam*. Each carries a British broad transcription in the Montreal Forced
Aligner English (UK) dictionary and an Australian tagged Wiktionary
pronunciation, and the contract records why each was chosen.

## The four things worth reading before the numbers

1. **The pack is expressed in broad phonemes, not in the aligner's symbols.** The
   aligner writes aspiration, palatalisation, labialisation, dentality, dark l and
   syllabicity as separate phones. Those are transcription detail rather than
   separate English sounds, and the protocol makes broad IPA the default because
   finer detail reduces transcriber agreement. Every normalisation carries a
   written reason and an unlisted symbol refuses the word rather than being
   dropped. Two entries repeat a lesson checkpoint 22E8 paid for: the aligner's
   dental stops are the consonants of *the* and *bath*, so they map to the
   fricatives rather than to `d` and `t`.
2. **Where the varieties differ, the pack declines to score.** Post-vocalic
   rhotics, flapping and glottalling contexts, postvocalic l and the dental
   fricatives are all unscorable, each citing evidence recorded inside this
   repository. That list is this project's own construction, because no ASHA or
   Speech Pathology Australia guidance enumerates dialect stable English
   segments, and it is not claimed to be complete.
3. **The rhotic rule reads zero, and that is the finding rather than a gap.**
   Across the whole eligible pool the post-vocalic rhotic rule refuses nothing,
   because under a non-rhotic British reference the opportunity mostly does not
   exist to be refused. This is the mechanism checkpoint 22E8 recorded: the
   repair works by declining to ask rather than by fitting better. An American
   reference would have created those opportunities, and the pack would then have
   had to refuse them.
4. **The union rule had almost nothing to union here.** Nineteen of the twenty
   words carry exactly one documented form of each variety, because requiring
   every documented form to agree tends to select words that have only one. The
   rule's real effect is visible in the pool, where 272 words were refused for
   disagreeing on how many consonants they have and 377 opportunities were
   refused for disagreeing on identity. The pack says so in its own limitations,
   so the safeguard is not mistaken for work it did not do.

## Reproduce

Nothing here touches audio, a speaker, a split or a gate.

```sh
python3 -m speech_sound_patterns.build_prompt_pack
```

That writes the committed pack and, into gitignored storage, the private record
holding the verbatim British and Australian forms and the whole eligible pool.
That material is the derived lexicon and stays server side: Wiktionary derived
material is share alike, and share alike attaches when adapted material is
distributed rather than when it is used internally. The committed pack carries
the consonant opportunities and no vowels, which is the pack's own measurement
target rather than a pronunciation dictionary.

```sh
python3 -m speech_sound_patterns.build_prompt_pack --check
python3 -m speech_sound_patterns.validate_prompt_pack
python3 -m unittest tests.test_speech_sound_prompt_pack
```

`--check` rebuilds the pack and compares it with the committed file byte for
byte, and one test does the same, skipping only when the acquired references are
absent from the machine. The committed numbers are generated, never typed.

## Why the words were chosen by hand

The eligible pool is 2,578 words wide against a pack of twenty, so almost any
mechanical ranking would have been a familiarity measurement this project does
not hold. The choice is therefore made openly: the contract names the twenty
words with a reason each, frozen before any dictionary was read, and the builder
then verifies every one against every mechanical rule and refuses the whole build
if one does not pass. The pack reports the size and shape of the pool so a reader
can see the twenty were chosen from thousands rather than being the only twenty
that worked.

## What the pack cannot do

- It is not professionally reviewed, and says so. Qualified phonetic or speech
  pathology review, review by people familiar with the supported English
  varieties, familiarity and cultural review, recorded prompt review and a
  separate owner approval are all unmet.
- A lexicon proposes how a word may be said and never observes how anybody said
  it, so nothing here is truth about a pronunciation. All four reference sources
  keep `truth_class: unavailable`.
- Only the written word mode is built. The recorded prompt alternative is left
  empty deliberately: a spoken prompt carries the speaker's own variety, so
  recording one here would have the person imitating an accent rather than saying
  a word.
- `/h/` reaches one word position rather than two, because English `/h/` occurs
  only in syllable onsets and the pool's single medial candidate is not an
  ordinary prompt. `/ʒ/` is not probed at all, for the same kind of reason. Both
  are declared rather than hidden.
- Twenty words cannot establish that any consonant is produced typically or
  atypically by anybody. The pack creates opportunities. It measures nothing.
