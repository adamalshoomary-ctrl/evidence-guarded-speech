# Open stack acquisition runbook, checkpoint 22E7

Checkpoint 22E7 acquires and proves data. It selects nothing, scores nothing,
applies no gate and changes no pipeline behaviour. If a command in this runbook
wants to run a candidate system or read a held-out speaker, it is the wrong
command.

Two kinds of source arrive here. Four are pronunciation lexicons, which have no
speakers and therefore no participant split. Three are accent subsets of one
Common Voice release, which have speakers and are split exactly as the
Australian subset already was.

## Why the numbers are generated and not typed

Every count, phone inventory and checksum in the committed manifests is produced
by reading the acquired bytes. This is not tidiness. Three figures this
repository had recorded as fact were wrong when they were checked, and each was
wrong because somebody had read a number off a web page and carried it forward.

- The Montreal Forced Aligner dictionaries were recorded with 99 and 73 phones.
  The pages list 91 and 77, and the files carry one more than that each, the
  aligner's own spoken noise phone `spn`. An earlier search had recorded 103.
- The published word counts are short by exactly the aligner's special tokens:
  `<unk>`, `<cutoff>`, `[bracketed]` and `[laughter]`.
- The Australian tagged Wiktionary entries were recorded as roughly 2,700. There
  are 5,347 words carrying 11,328 Australian tagged pronunciations.

## Acquire

```sh
python3 -m speech_sound_patterns.acquire_open_stack --all
```

Each file streams into the gitignored private root and is then proved three
ways, all of which must hold. Its size must equal the size the publisher
declares. Its SHA256 is recomputed by re-reading the finished file from disk,
rather than trusting anything the network reported while the bytes were moving.
And where the source publishes a digest, as Mozilla Data Collective does, that
digest must match. A file failing any of the three is deleted rather than kept,
because a plausible looking truncated corpus is worse than a missing one.
Licence and terms pages are captured on the same day and hashed beside the data.

Large downloads resume rather than restart. The American male subset dropped at
7.75 of its 10.39 gigabytes on the first attempt, and a transfer that size cannot
begin again every time a connection blinks. Each retry requests a fresh URL,
because a presigned link expires while the earlier attempt is still running, and
a server that answers a range request with the whole body again restarts the file
instead of appending to it.

Two sources are deliberately pinned rather than tracked:

- WikiPron publishes a continuously updated scrape, so the branch tip is not a
  version. Both scrapes are pinned to commit `d282e848`, which is itself the
  commit that changed the English dialect selectors.
- Kaikki regenerates weekly and publishes no checksum, so the acquired archive
  is the only fixed record of those exact bytes. Its version is the underlying
  enwiktionary dump date, which is stable even though the file is not.

`MDC_API_KEY` comes from the gitignored `.env`. It is read into a request header
and never printed, logged or written into any record.

**No Australian speech is acquired.** It has been held, hashed, licence verified
and participant split since 2026-07-21, and only 30 of its 55,922 clips have
ever been used. Do not acquire the older version 24 Australian subset either; it
is a curated snapshot of an earlier release of the same speech.

## Derive the Australian reference overlay

The tag vocabulary is measured before any tag is selected, because Wiktionary's
accent templates reach Wiktextract as free text and a guessed tag name would
build the wrong reference silently.

```sh
python3 -c "from speech_sound_patterns.corpus_audit import kaikki_accent_tag_census as c; \
print(sorted(c('.research_data/speech_sound_patterns/corpora/wiktionary_australian_kaikki/kaikki.org-dictionary-English.jsonl.gz')['tags'].items(), key=lambda i: -i[1])[:30])"
```

The extraction carries 220 distinct pronunciation tags and exactly three are
Australian: `Australian`, `Australia` and `General-Australian`. `New-Zealand`
often co-occurs and is not treated as Australian on its own. Wiktextract's
separate `raw_tags` are counted separately and are not selectable, so the census
and the extraction agree on the same vocabulary.

```sh
python3 -c "from speech_sound_patterns.corpus_audit import extract_kaikki_australian as e; \
print(e('.research_data/speech_sound_patterns/corpora/wiktionary_australian_kaikki/kaikki.org-dictionary-English.jsonl.gz', \
'.research_data/speech_sound_patterns/lexicons/wiktionary-australian-tagged.json', \
['Australian','Australia','General-Australian']))"
```

## Split the speech subsets

Every Common Voice subset goes through one function, `audit_common_voice`, and
not a parallel one per group. A comparison between speaker groups is only fair
if every group was split, deduplicated and sealed by identical code.

```sh
python3 -c "from speech_sound_patterns.corpus_audit import extract_common_voice_metadata, audit_common_voice; \
extract_common_voice_metadata(ARCHIVE, METADATA_ROOT); \
print(audit_common_voice(METADATA_ROOT, ASSIGNMENT_PATH, source_id=SOURCE_ID))"
```

Only the three split TSVs are taken out of each archive. The clips stay
compressed, which is why acquisition costs one archive per subset rather than
twice that. The supplied train, dev and test files map to development, threshold
tuning and sealed held-out evaluation, and **no held-out speaker in any subset
may be read before 22H.**

Group overlap is then checked across every subset:

```sh
python3 -c "from speech_sound_patterns.corpus_audit import audit_common_voice_group_overlap as o; \
print(o({SOURCE_ID: METADATA_ROOT, ...}))"
```

A contributor appearing in both the group under test and its control would not
merely duplicate evidence. It would flatten the very difference checkpoint 22E8
exists to measure, so this fails closed rather than warning.

## Rebuild and validate

```sh
python3 -m speech_sound_patterns.build_open_stack_manifests
python3 -m speech_sound_patterns.validate_corpora --verify-private --rehash-archives
python3 -m unittest tests.test_speech_sound_corpus_manifests
```

The builder without `--write` checks that the committed manifests still rebuild
exactly from the acquired evidence, and a test asserts the same thing whenever
the private material is on the machine. `--rehash-archives` recomputes every
local archive digest, which is slow and is the check worth running after any
disk trouble.

Reverify with `--skip-licence-capture`. The Mozilla Data Collective terms page
is served with a per-request build identifier in its markup, so two captures of
word for word identical terms produce different digests. A recapture therefore
changes the recorded terms digest and the manifests must be rebuilt after one.
The stable identifier of what was agreed is `access.terms_version`; the digest
pins the exact bytes retrieved on the day and nothing more.

## What this checkpoint chose, and on what evidence

The plan left one decision to acquisition: which file carries the British
referenced expected-phone path. It was decided by measuring how often each
candidate places a rhotic after a vowel and not before one, which is the sharpest
single British and Australian difference from American English. Counting every
rhotic would have proved nothing, because non-rhotic varieties still have the
onset r in *red*.

| Reference | Post-vocalic rhotic entries | Distinct symbols |
|---|---|---|
| MFA English (UK) | 0.01 percent | 78 |
| WikiPron `eng_latn_uk_broad` | 6.85 percent | 239 |
| MFA English (generic) | 7.42 percent | 92 |
| WikiPron `eng_latn_us_broad` | 18.48 percent | 240 |
| MFA English (US) | 23.58 percent | 79 |

The two aligner dictionaries behave as a real British and American pair should.
The WikiPron British scrape is meaningfully less rhotic than its American
counterpart, so its variety tag carries real signal, but it is nowhere near
non-rhotic and its inventory holds symbols English does not use, because
volunteers add loanword pronunciations. It is therefore a supplement to the
British reference and not the British reference, and that boundary is a
prohibited role in its manifest rather than a note somebody may overlook.

MFA English (US) is held as the American counterpart for one reason: two
reference paths that differed in phone alphabet as well as in variety could not
produce an interpretable difference at 22E8. The matched WikiPron American
scrape is held for the same reason, one level up: without it, every statement
above about how British the British scrape is would be an assertion rather than a
measurement.

## What this checkpoint does not do

- It measures no speaker and produces no flag rate. That is 22E8.
- It builds no reference path and unions no variants. That is 22E8.
- It selects no word pack. That is 22F.
- It applies none of the five frozen gates and touches neither the frozen
  benchmark nor the selection record, both of which remain correct against
  American English because SpeechOcean762's reviewers judged against it.
- It reads no held-out speaker, in any subset.
- It sends nothing to any provider. Every source here is `provider_transfer`
  blocked, and a test asserts it.
