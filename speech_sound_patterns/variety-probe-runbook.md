# Reference variety probe runbook, checkpoint 22E8

Checkpoint 22E8 measures whether this project's American expected-phone
reference flags Australian and British speakers more often than American
speakers, and what changes when the reference variety is repaired. It selects
nothing, applies none of the five frozen gates, and touches neither the frozen
benchmark nor the selection record.

The committed artifacts are `variety-probe-contract-v1.0.0.json`, frozen before
any speaker was scored, `variety-probe-uncertainty-contract-v1.0.0.json`, frozen
before any interval was computed, and `variety-probe-v1.2.0.json`, the report.
`variety-probe-v1.0.0.json` and `variety-probe-v1.1.0.json` stay committed as
superseded records and deliberately no longer validate.

## What the result was

Read the report's `findings` before its numbers. In summary:

1. **The central prediction failed for Australian speakers.** At group level the
   American reference did not flag them more often than the American control.
   The differential is negative at all five thresholds, before and after the
   phone mapping correction. That is recorded as a wrong prediction rather than
   reinterpreted.
2. **It held for British speakers**, at plus 0.0115 under the American reference
   and plus 0.0053 under the repaired one, so the repair roughly halved it. This
   is the informative middle case, because British is the variety the repaired
   reference actually describes.
3. **The group mean hid a real per consonant effect.** On the rhotic and on `t`,
   the two consonants where the varieties genuinely differ, Australian speakers
   were flagged about three points more often than American speakers under the
   American reference, and both differences collapse to roughly zero under the
   repaired reference. A mean across roughly thirty consonants cannot see an
   effect carried by three of them, so the checkpoint's hypothesis was sound and
   its headline statistic was not.
4. **The repair removes opportunities rather than improving fit.** Australian
   rhotic opportunities fall from 1,013 to 664 under the non-rhotic reference,
   and the American control's rhotic flag rate falls just as steeply, from 0.306
   to 0.044. A non-rhotic reference stops expecting a coda r for everybody. That
   is legitimate under this project's own rule, because where varieties genuinely
   differ the opportunity is unscorable and a mismatch may be excluded but never
   subtracted. It is not evidence that the reference now describes Australian
   speakers more accurately, and the report makes no such claim.

## Reproduce

Everything below reads only development partitions. No held-out or threshold
tuning speaker is touched, in any group.

```sh
python3 -c "import json,pathlib; from speech_sound_patterns import variety_probe as vp; \
s=vp.build_sample(); \
pathlib.Path('.research_data/speech_sound_patterns/variety-probe/sample.json').write_text(json.dumps(s,indent=2,sort_keys=True,ensure_ascii=False)+'\n'); \
print(vp.extract_sample_clips(s)); print(vp.canonicalise_clips(s))"
```

```sh
caffeinate -dimsu python3 -m speech_sound_patterns.variety_probe_run
```

The run takes about three and a half hours for 2,400 clips on this machine, measured at 5.3 seconds per clip on 2026-08-23, and
writes one file per clip, so an interruption resumes instead of restarting. Run
it under `caffeinate`, and note that closing a laptop lid sleeps the machine
regardless of `caffeinate`; the run pauses rather than failing.

```sh
python3 -m speech_sound_patterns.validate_variety_probe
python3 -m unittest tests.test_speech_sound_variety_probe
```

## Why the sample is shaped this way

- **Equal groups.** The four subsets differ in size by a factor of seven. Three
  hundred speakers and two clips each are drawn from every one, so a per
  consonant rate is not dominated by whichever group is largest.
- **Paired.** A clip is kept only if both dictionaries cover its prompt whole,
  and is then scored under both references or neither. Comparing two references
  on two different samples would confound the reference with the sample. Paired
  coverage is about 77 percent of development prompts; the commonest refusals
  are contractions and possessives the dictionaries lack, and inventing a
  pronunciation for those would be generating a target rather than reading one.
- **Per speaker, then averaged.** A contributor who recorded more clips cannot
  pull a group's rate toward their own voice.
- **Five thresholds, not one.** No operating point has ever passed a gate in
  this project, so quoting one would imply a choice nobody has earned. A real
  differential holds across the range.
- **One inference per clip.** The model runs once and both references are scored
  against that single result, so nothing but the reference differs between the
  two conditions.
- **One American group from two subsets.** Neither the male nor the female
  subset may stand alone, or accent and speaker gender would vary together.
- **One contributor excluded.** They appear in both the American male and
  British subsets, having declared different varieties on different clips, and a
  speaker in both a group and its control would shrink the difference being
  measured.

## The phone mapping, and the two corrections it needed

Both aligner dictionaries are read into the frozen model's own vocabulary. Most
phones are already there verbatim; the rest are listed in
`variety_reference.PHONE_SUBSTITUTIONS` with a written reason each, and an
unlisted phone is an error rather than a silent drop.

Mapping version 1.1.0 corrected two entries **after** the first run exposed
them. Both were the same mistake, preserving the aligner's symbol where its
function mattered:

| Phone | Was | Now | Why |
|---|---|---|---|
| `ɫ` | `ɫ` | `l` | The model emits `ɫ` zero times across 25 clips while emitting `l` 28 times. Expecting it flagged 100.0 percent of those opportunities in every group. |
| `ɫ̩` | `ɫ` | `l` | Resolved to the same unusable token. |
| `d̪` | `d` | `ð` | The aligner writes *the*, *that* and *this* with a dental stop at 0.99 probability, where the model uses the fricative. This mis-expected the most frequent consonant context in English, flagging about half of some 1,300 `d` opportunities. |

Neither defect faked an accent difference, because both hit every group equally.
They inflated the baseline flag rate by about seven points, which is how they
were caught: the contract's control-group test asked why the repair had moved
the American group, and the answer was partly these.

Mapping version 1.2.0 then found six more of the same, and one of a different
kind. The direction change audit re-derived every published figure from the
retained evidence and found that most flags came from phones the model never
produces for English.

| Phone | Was | Now | Why |
|---|---|---|---|
| `c`, `cʰ`, `cʷ` | itself | `k` | Flagged 419 of 419 under the American reference and 336 of 336 under the British, at 100.0 percent in every group. The aligner writes the palatal stop for the velar stop before a front vowel. |
| `ɟ`, `ɟʷ` | itself | `ɡ` | 308 of 308 and 155 of 155, 100.0 percent everywhere. |
| `ɲ` | itself | `n` | 756 of 760, 99.5 percent, and 100.0 percent in the Australian group. |
| `ç` | itself | `h` | 611 of 612, 99.8 percent. The version 1.1.0 secondary analysis excluded the other four palatals and missed this one. |
| `ʎ` | itself | `l` | 857 of 857 and 747 of 747, 100.0 percent everywhere. |
| `ʔ` | scored | **excluded** | 176 of 176 under the British reference. Not renamed: coda t glottalling is a real variety difference, so mapping it to `t` would subtract the difference instead of excluding it. |

An 80 clip decode confirmed the mechanism in the same form version 1.1.0 used
for dark l: the model emits `ʎ`, `ɟ`, `c`, `cʰ`, `ç` and `ʔ` **zero** times and
`ɲ` once, while emitting `l` 105 times, `ɡ` 23, `k` 78, `n` 217 and `h` 41.

The seventh correction is not a symbol mismatch but a **segmentation** one. The
aligner writes *arts* as `ɑ ɹ t s`, treating post-vocalic r as its own segment.
The model carries six combined tokens, `ɑːɹ ɔːɹ oːɹ ɛɹ ɪɹ ʊɹ`, and emits them as
single units, so the expected standalone `ɹ` owned no frames and was flagged
**96.6 percent of the time in every group, identical to three decimal places**,
including rhotic American speakers who unambiguously produce it. The dictionary
uses both conventions: 11,047 entries as `ɚ`/`ɝ`, which always worked, and 6,684
as vowel plus `ɹ`, which never could. *performed* = `pʰ ɚ f ɒ ɹ m d` contains one
of each.

`POST_VOCALIC_RHOTIC_MERGES` joins the pair into the model's own token, covering
90.7 percent of the class. The remaining 9.3 percent, where the preceding vowel
is a diphthong and no combined token exists, is unscorable. Onset `ɹ` is never
merged and is still scored; it was never part of the defect.

**Consequence.** Post-vocalic r is now unscored under both references, so
rhoticity, the sharpest Australian and American consonantal difference, is not
measurable by this method. That is the substantive result rather than a gap in
it. Scoring the merged token would move the probe past its frozen consonants
only contract after the results were seen, and is deliberately not done.

**The version 1.1.0 run is retained**, at `report-mapping-v1.1.0.json`, SHA256
`8156ce119af6b879b37f70b30a132fffab130e3e93638c2d41fa32043b856ee8`, with
`evidence-mapping-v1.1.0/` and `sample-mapping-v1.1.0.json` beside it. The clip
selection is byte identical across all three runs.

**The first run is retained**, at
`.research_data/speech_sound_patterns/variety-probe/report-mapping-v1.0.0.json`,
SHA256 `392c610d4cc1c87bda283e0cf4696afe5a614b95c48c5a4417a3525cbfa445c5`, with
its evidence directory and sample beside it. The amendment cites it, and the
clip set is identical between the two runs so the versions are directly
comparable. Correcting a mapping and quietly presenting clean numbers would have
hidden the most instructive part of this checkpoint.

## What this cannot establish

These are native speakers reading known text, so a flag is presumed a false
concern rather than a detected error. Nothing here shows that the system
correctly detects a genuine Australian mispronunciation, and no accuracy,
sensitivity or specificity figure is derivable from it. No Australian expert
phone labels exist in this project or, so far as the 2026-07-28 search could
establish, in any commercially usable form anywhere.

The report also carries six declared confounds, including that recording quality
varies across contributors, that both American subsets are filtered to a declared
gender while the other groups are not, and that the British subset pools England,
Scotland, Wales and Ireland. The sixth, that the aligner's conditioned palatal
series can turn a vowel difference into a consonant difference, is addressed at
the source from mapping version 1.2.0: the series is normalised to broad phonemes
before a target is ever selected. The `without_conditioned_palatals` secondary
analysis is retired, because it now filters nothing.

A confound the contract does **not** declare, and a reader will ask about: the
prompt sets are effectively disjoint across groups. Australian speakers read 592
unique prompts and American speakers 1,161, with 34 in common. The design is
paired across references, on the same clip and the same inference, and entirely
unmatched across groups.

Item R2 computed the uncertainty, on the same stored evidence and with no
re inference. Regenerate the report, intervals and all, with:

```
python3 -m speech_sound_patterns.variety_probe_score
```

That draws 10,000 speaker clustered resamples and runs 10,000 permutations per
test, takes a little over two minutes, and is deterministic from the declared
seed. Validate it with `python3 -m speech_sound_patterns.validate_variety_probe`.

What R2 established, in short:

- **Nothing at group level is distinguishable from zero.** All five
  pre registered comparisons have intervals containing zero and none reaches
  significance even uncorrected. The design could only reliably detect an
  Australian differential of about 0.0146 and the observed one is 0.0039, so
  this is a look too small to tell rather than a demonstration of no difference.
- **The `t` differential does not survive.** It reaches the uncorrected five
  percent level at one threshold only, changes sign at minus three, sits below
  the smallest difference detectable for that consonant, and fails both
  corrections across its declared family of 22.
- **One test survives, and it is British.** `ð`, British minus American under
  the American reference, holds across all five thresholds and both references
  and survives Benjamini Hochberg and Bonferroni alike. The disjoint prompt sets
  above are exactly why it is not evidence about British English.
- **The two references do not create the same opportunities.** Only 8 of 25
  consonants keep their opportunity count within two percent across the
  reference swap, so most cross reference comparisons are not like for like.

The multiple comparison families and the consonant inclusion rule were declared
in the uncertainty contract before any of it was computed. Read that contract
before reading a p value here.
