# How this project was built

Generative AI wrote most of what is in this repository. The code, the tests,
the research contracts, the documents and much of the analysis came out of long
working sessions with large language models, directed by one person.

That person is Adam Al Shoomary. He set the direction, approved every item
before it started, made every decision the models put to him, and made every
commit himself. No model has ever committed to this repository or published a
release.

## Why this page exists

A project whose whole subject is declaring where evidence came from should
declare where its own code came from. The Journal of Open Source Software now
asks research software to disclose this. It would be strange to build machinery
for provenance and stay quiet about your own.

## What a reader should do with that

Judge the evidence, not the process.

Every number this repository publishes can be recomputed from data it ships.
The variety probe report rebuilds byte for byte in about two minutes from a
4.75 MB evidence bundle. The claim verifier checks a model's prose against the
stored measurements it cites. The release verifier refuses a snapshot carrying
private material. 1,036 tests run on one command. None of that asks you to
trust how the code was written.

`findings.md` is the sharper test. It records three occasions where this
project checked its own work and lost something it wanted to keep: a headline
result retracted after the method was turned on itself, a novelty claim cut
back after a prior art search, and six published figures that turned out to be
wrong. Read those and decide for yourself whether the work is careful.

## What the models were not allowed to do

- Decide anything. Every item in the plan waited for Adam's explicit approval.
- Commit or push. Both are his, in GitHub Desktop.
- Create measurement truth. A language model may explain evidence in this
  system and may not produce it. The claim verifier exists to enforce that
  boundary, and `findings.md` section 5 explains what it cannot catch.
- Loosen a gate, reopen a frozen record, or look at held out data.

## What this does not claim

Disclosure is not a quality argument. Code written this way can be wrong in
ways nobody notices, and this project has found several of its own errors late.
The honest position is that the machinery and the tests are the check, and both
are published so you can run them yourself.
