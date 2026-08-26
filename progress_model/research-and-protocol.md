# Personal baseline and meaningful change protocol

Updated: 2026-07-19

## Decision

The backend can now represent and evaluate a personal baseline, but no current
speech metric is released for personal progress. The evaluator must return an
explicit unavailable result until a metric has its own repeated production
study, measurement error, natural variation, meaningful change evidence and
independent evaluation.

This is deliberate. One recording describes one performance. It cannot say
what is normal for a person, and two different numbers do not prove that the
person changed.

## Why a percentage rule was removed

The old prototype called a difference within five percent steady. That number
did not come from a repeated speech study and treated unlike units as though
they had the same error. It is removed. Words per minute, event counts, pitch,
pause time and user reports need different evidence and cannot share one
percentage threshold.

COSMIN separates reliability from measurement error. Measurement error is the
systematic and random error not caused by true change. It recommends estimating
continuous score error from stable repeated measurements using quantities such
as SEM, smallest detectable change or limits of agreement. A correlation or
repeatability coefficient alone does not tell us how large an individual
change must be.

## Comparable observations

An observation may join a baseline only when it belongs to the same account,
declared communication context, versioned task and prompt, language, recording
mode, quality policy and currently validated capture conditions. Preparation
and accommodations remain visible. Different contexts, prompts, devices or
accessibility conditions may become comparable later only after direct
validation; the current software does not silently assume they are equivalent.

The current baseline candidate role is a first attempt taken with the strict
baseline quality policy. A same day repeat after practice is useful practice
evidence, but it is not added back into the person's prepractice baseline.
Every durable record must also declare whether it is collecting baseline,
checking change, recording practice, checking retention or checking transfer.
The backend never guesses that intent from the order of files.

## A baseline is a range

Each metric release profile must define its required number of observations,
sessions and days from development evidence. There is no global minimum and one
recording is never enough by default. When eligible observations exist, the
backend retains every value and can describe the median and observed range.
It does not silently delete an inconvenient observation or turn the range into
a norm for other people.

The FDA's draft patient focused guidance notes that a protocol should clearly
define baseline and specify how multiple baseline observations are combined.
Speech research supports this caution: reliability varies by task and feature,
multiple samples can improve reliability, and consumer devices can affect some
features more than others. Those studies inform the protocol but do not supply
thresholds for this product's different tasks and metrics.

## Detectable is not automatically meaningful

For a released metric, the evaluator compares the current value with the
personal baseline centre and keeps these questions separate:

1. Is the difference larger than estimated measurement error?
2. Is it larger than expected natural within person variation?
3. Is it larger than a separately justified meaningful change boundary?

The final credible change boundary is the largest applicable boundary, and the
observed difference must strictly exceed it. FDA's draft guidance recommends
anchor based evidence for meaningful score differences and says distribution
based methods such as standard deviations or SEM are insufficient on their own
because they do not directly represent the person's voice. A future release
profile therefore needs suitable user or real world anchors as well as error
estimates.

Even a credible increase or decrease is not automatically improvement. The
meaning of direction depends on the person's goal and the construct. Faster,
louder, lower pitched, more fluent or more conventionally accented speech is
never globally labelled better.

## Separate evidence streams

The report keeps seven sections separate:

- baseline readiness;
- speech measurements;
- user declared confidence, difficulty, representativeness and usefulness;
- user declared real world outcomes;
- practice and exercise completion;
- retention and transfer evidence for future mastery;
- recording and verification quality.

User reports can explain the person's experience but do not overwrite speech
measurements. Speech numbers cannot invent confidence or usefulness. Practice
can be recognised without claiming skill mastery. Run quality protects the
evidence but is not itself communication improvement.

## Retention, transfer and mastery

A same day repeat shows only what happened during that practice session.
Future mastery needs both a later day retention attempt and a suitable new
prompt transfer attempt. They remain separate records. Exact mastery thresholds
are still blocked until a skill specific policy and outcome evidence exist.

## Release gate

`reliability-registry-v1.1.0.json` intentionally contains no approved metric
profiles. A future profile must predeclare comparable conditions, baseline
requirements, algorithm versions, individual measurement error, natural
variation and meaningful change. Development and held out evaluation
participants must be separated, representative conditions and subgroups must
be reported, the sample size and held out results must be auditable, and a
measurement specialist plus Adam must approve release. Adam's recordings
cannot set the release threshold.

## Sources

- COSMIN Manual version 2, measurement error section:
  <https://www.cosmin.nl/wp-content/uploads/COSMIN-manual-V2_final.pdf>
- FDA draft Patient Focused Drug Development Guidance 4, baseline and
  meaningful score difference sections:
  <https://www.fda.gov/media/166830/download>
- Bland and Altman, agreement and repeated measurements:
  <https://doi.org/10.1177/096228029900800204>
- Multi day remote speech reliability study:
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC11293000/>
- Cross device and test retest speech acoustic reliability study:
  <https://pubmed.ncbi.nlm.nih.gov/39738817/>
