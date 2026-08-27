# Where this project stands

Last updated 2026-08-27, for release `v0.1.2`.

This page is written for someone who has just arrived. It says what state the
work is in, what was deliberately not done and why, and what would have to
change for the deferred parts to be worth restarting. It replaces three
documents that exist only in the private working repository: an internal status
handoff, a roadmap written around a workflow with the owner, and that project's
own working agreement. Older documents here still name the first two by
filename. None of the three is published, and what they said that matters to a
reader is below.

For what the project measured and what it failed to establish, read
`findings.md`. That is the account, and this page does not repeat it.

## The state of the work

The research track is finished. An independent person can obtain this
repository, install it with no paid credentials, reproduce the published
analysis from published data, read an honest account of what was measured, and
disagree with it on the evidence. That was the whole target and it was met on
2026-08-27.

What exists: a Python speech measurement engine that turns one recording into a
measurement record carrying provenance, uncertainty and explicit abstention;
versioned research contracts and validators; licence audited corpus manifests;
a pre registered dialect comparison with its full evidence and a pseudonymised
bundle that reproduces its report; and the record of a system selection that
selected nothing.

What does not exist, stated because the absences are the point:

- any released score, rating, index or summary number describing a person. Five
  existed until 2026-08-24 and they were deleted with nothing put in their place;
- independently validated voice, prosody or event detection accuracy;
- a validated personal progress metric;
- a professionally reviewed pronunciation word pack, or a selected pronunciation
  system;
- expert produced phone level truth for any first language English variety this
  project targets, which `findings.md` section 6.1 reports as a finding rather
  than as an excuse;
- any clinical or screening function. None is planned and no listed work leads
  to one.

## Known defects, unfixed and recorded

Three were found on 2026-08-26 while writing the account, by checking the code
rather than rereading the prose. Two more were found on 2026-08-27 the same way.
None is fixed in this release.

- **A claim's type is not tied to the class of evidence beneath it.** A language
  model's subjective impression can be recorded in the machine readable ledger
  as a measured observation, because the evaluator prompt's own definition
  permits it and no check refuses it. `findings.md` section 5 sets this out with
  a real example. It is the one worth attention.
- **A solo run reports a stage as pending that will never run.** The speaker
  label referee is initialised as pending for every run and solo mode never
  schedules it, so a finished solo measurement record describes it as about to
  happen. Confirmed again on a real run on 2026-08-27.
- **The snapshot builder deletes its destination under `--force`,** including
  that directory's git history. Harmless when this repository did not exist, and
  not harmless now.
- **The snapshot verifier assumes a first publication.** Its git section asserts
  the snapshot has no remote and no commits, which was true exactly once. It
  bites only if you verify a directory that already has a git repository in it,
  which the documented build procedure avoids.
- **The interpretation layer still degrades sometimes.** One acceptance run
  failed both attempts and degraded safely, leaving the measurement record
  untouched. The prompt rules were then made explicit and the runs that followed
  passed first time. A handful of passes is not a reliability measurement, and
  this is not solved.

## What was deferred, and what would make it worth restarting

Deferred means somebody looked at it, decided it was not worth doing yet, and
wrote down what would change that. It does not mean abandoned.

**A second phone model with no Common Voice lineage, rescoring the same 2,400
clips.** The scoring model behind the published probe is fine tuned on Common
Voice and the probe evaluates entirely on Common Voice speakers, which this
project's own rules disqualify elsewhere. The overlap is declared in
`findings.md` section 4.1 rather than resolved. Checked again on 2026-08-27 and
it is harder than it looks: the obvious modern replacements are trained on
IPAPack++, which is built partly from Common Voice, and the Common Voice free
alternatives are forced aligners whose per phone scores sit on a different scale
from an ASR posterior. Comparing one against a threshold calibrated for the
other is a defect this project has already found once in its own code. Restart
this when a differential appears that runs the way the lineage bias predicts,
because such a result would be uninterpretable without it.

**More Australian speakers.** The eligible pool in this corpus is 674 speakers
and the probe already samples 45 percent of it. The design's minimum detectable
difference will not fall much without a different source.

**The newly available reference material.** Refusing commercial intent released
a number of non commercial sources, including an Australian reference lexicon
and large collections of Australian speech. None of them solves the absence of
expert Australian phone truth. Two cautions if any is taken up: an Australian
lexicon adds a third phone inventory to a comparison in which only 8 of 25
consonants already keep their opportunity count stable across two references,
and the one corpus carrying expert phone labels for first language English is
conversational speech, where a flag rate would be driven by casual reduction
rather than by variety.

**Measuring the model instead of the person.** Run several models over the same
measurement records and publish how often each makes claims the evidence does
not support. This is the one route by which the claim verification layer becomes
a finding rather than a component. It has no human subject and it has a ready
made comparison in the literature. Nothing published here claims that result in
advance of doing it.

**Extracting the audit and abstention harness as a library.** The provenance,
claim ledger and verification machinery is the reusable part. It waits until
there is evidence somebody wants it.

## What was decided against, and will not be reopened

- **A public API or hosted service.** Every call would cost the author money
  with no way to recover it, it would make him custodian of strangers' voice
  recordings under a privacy tort that applies to him personally, and a free
  consumer facing service sits far closer to the regulated category than
  distributing source code does. This project has readers, not users. Run the
  command line tool yourself.
- **A peer reviewed paper.** It needs a phonetician collaborator, carries real
  rejection risk, and would take six to twelve months for credit this route
  mostly delivers. Reopenable in principle, and the harder statistics were left
  listed rather than deleted so that restarting is cheap.
- **A commercial product of any kind.** Settled permanently on 2026-08-22. The
  evidence here rests on non commercial sources and can never underwrite one.

## The boundaries that bind everything above

- Every output is a measured observation with provenance and uncertainty, or an
  interpretation marked as such and checked against stored evidence. There is no
  third level. This project makes no screening or clinical claim.
- Missing or unreliable evidence never becomes a score. Unavailable is not zero,
  not a pass and not a failure.
- Measurements, listener perceptions, interpretations and outcomes stay
  separate. They are never pooled.
- A language model may explain evidence. It may not create measurement truth.
- A reference variety is declared by whoever runs the analysis. This project
  does not classify anyone's accent, and it will not build something that
  decides how a person ought to sound after guessing where they are from.
- Where documented varieties legitimately differ, the opportunity is unscorable
  and is reported as unscorable. A variety mismatch may be excluded and never
  subtracted.
- Development, tuning and evaluation data are separated by participant. A
  software snapshot is not independent truth, and two systems agreeing is not
  evidence that either is right.
- A recorded decision to select nothing is a completed result. It does not
  authorise a weaker gate, more threshold searching, or an early look at sealed
  participants.

## Versioning

Every published update gets a tag, a GitHub release and a Zenodo version DOI.
Patch releases carry documentation and metadata. Minor releases carry a change
in behaviour or in a published number. Cite the concept DOI in `CITATION.cff`,
which always resolves to the newest version.
