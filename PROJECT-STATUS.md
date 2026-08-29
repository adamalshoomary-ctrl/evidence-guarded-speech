# Where this project stands

Last updated 2026-08-29, for release `v0.3.1`.

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

Generative AI wrote most of the code and documents here, directed by one
person who made every decision and every commit. `AI-ASSISTANCE.md` sets out
what that means and what to check instead of trusting the process.

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

## Known defects, recorded rather than hidden

Three were found on 2026-08-26 while writing the account, by checking the code
rather than rereading the prose. Two more were found on 2026-08-27 the same way,
and three more on 2026-08-28 by walking this repository as a stranger would.
**Five of them are now fixed and the rest are not.**

Fixed in `v0.3.0`, on 2026-08-28: **a run now checks its credentials before it
spends anything.** Three keys exist and nothing outside the Python source named
them. A newcomer running the first command in the README was told
`ASSEMBLYAI_API_KEY not found in .env`, naming a file that does not exist, that
nothing creates, that nothing templates, and whose required location was stated
nowhere. Worse, the runner read no credential at all: each stage loaded its own
key when it ran, and the stages that need one run last. So somebody holding a
transcription key and no model key paid for a full transcription, waited for a
model download, and was then told the interpretation was unavailable, without
the message ever naming the key they could have added in thirty seconds. The
runner now works out which keys the given flags will need and stops in well
under a second, naming each missing variable and where it is issued, before
anything downloads or bills. A key serving a stage nobody asked for produces a
note instead, and that stage records itself as unavailable as before. There is
a `.env.example` to copy, and the README carries a credentials table, the
Hugging Face model agreement step that a token alone does not satisfy, and the
credential free command as a first class option.

Fixed in `v0.2.3`, on 2026-08-28: **the documented commands now run, and the
prerequisites are stated.** Four of the six commands printed in this
repository's own documentation crashed in a fresh copy of it. Three causes.
Commands that named no recording died on a raw Python traceback, because they
read whichever file sits in `audio/` and no audio is published here; they now
say so and name a shipped example instead. `ffmpeg` was never listed as a
requirement, and because a missing program fails the same way an unreadable file
does, the preflight blamed the shipped example rather than the absent program; it
now names ffmpeg and says how to install it on each platform. The reproduction
instructions said the two verification commands need "only numpy", which was
wrong: they need `jsonschema` too, established by blocking each package in turn.
**That makes six times a published figure here has been wrong**, and the count is
corrected in `findings.md` section 2.2. There is no documented way to run the
tests either, so the README now gives one.

Fixed in `v0.2.2`, on 2026-08-28, and **this one affected you rather than the
project**: **releases `v0.1.0` through `v0.2.1` invited their own users to
commit their own voice recordings.** The `.gitignore` published with them listed
five entries and none of them covered `audio/`, `output/`, `history.json` or
`progress.md`. The pipeline writes `output/` at the repository root by default,
and that directory holds the full transcript of whatever was recorded. So
somebody who followed the instructions, put a recording in `audio/` and ran the
tool was shown their own voice and its transcript as ordinary pending changes,
presented by a desktop git client as a tick box like any other. This repository
exists as a separate sanitized snapshot **because** exactly that material
reached the private working repository's history and can never be taken out of
it, which makes leading a reader into the same trap the worst defect found so
far. All four paths are now ignored. **If you cloned this repository before
`v0.2.2` and ran it, check your own copy**: `git log --stat` for anything under
`audio/` or `output/`, and remember that removing such a file in a later commit
does not remove it from history.

Fixed in `v0.2.0`, on 2026-08-28: **a claim's type is now tied to the class of
evidence beneath it.** A claim typed a measured observation must rest on a
computed metric, a turn, a word effect or a pause. A listener's impression of
how somebody sounded is an interpretation, and so is anything resting on the
recording's setting. The defect was reproduced on the code published as
`v0.1.2` before it was repaired: one run typed five listener backed claims as
measured observations and verified all of them without an issue. `findings.md`
sections 5 and 9 keep the original finding and record the closure beside it.
**This does not make the verifier able to judge whether an interpretation is
sound. Nothing here does, and section 5 of the account explains why a verifier
of this kind cannot.**

Fixed in `v0.2.1`, on 2026-08-28: **a solo run no longer reports a stage as
pending that will never run.** The speaker label referee was initialised as
pending for every run, and solo mode never schedules it, so a finished solo
measurement record described it as about to happen. It now starts not requested,
the same word the other two model stages already used. The provenance block in
the same file already recorded the referee as not invoked in solo mode, so this
ends a measurement record carrying two accounts of one fact that disagreed.

Still open:

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
