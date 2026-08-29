# Project purpose

## What this is

An open research project on speech measurement that records where its evidence
came from and refuses to produce a result when the evidence, the reference or
the validation is inadequate.

The working name for that idea is evidence guarded measurement. The system
measures what it can, states the provenance of every input, carries uncertainty
beside every number, and abstains explicitly rather than emitting a confident
value it cannot support.

This is not a product and there is no monetisation plan. That decision was made
on 2026-08-22 and it is permanent. It is not a pause, and no later phase
reopens it.

## Why the decision matters technically

Non commercial licensing was the binding constraint on this project's evidence
for its entire life. Refusing commercial intent releases it. Sources previously
excluded on commercial grounds alone become available, including an Australian
English reference lexicon and large collections of Australian speech.

The reverse also holds and is why the decision has to be permanent. Evidence
built on non commercial sources can never underwrite a commercial product. Any
result produced from here is a one way door.

## What the project claims

Three levels, and the boundary between them is the point of the project.

1. **Measured observation.** A number with its provenance, its uncertainty and
   the conditions under which it was produced. The project makes these claims.
2. **Interpretation.** An explanation of what an observation may mean, marked as
   interpretation and traceable to the observations it rests on. The project
   makes these claims and verifies them mechanically against stored evidence.
3. **Screening or clinical conclusion.** Any statement that a person's speech
   may indicate a condition. **The project does not make these claims and no
   roadmap item leads to them.**

## What the project refuses

- It does not rank people, and it does not infer age, race, ethnicity,
  nationality, gender, diagnosis, personality, honesty or professionalism from
  voice.
- It does not classify a speaker's accent. A reference variety is declared by
  whoever runs the analysis. Inferring someone's identity and then deciding how
  their speech ought to sound is a harm the project will not introduce.
- It does not treat one variety of English as correct. Where documented
  varieties legitimately differ, the opportunity is unscorable and is reported
  as unscorable. A variety mismatch may be excluded and never subtracted.
- It does not turn missing or unreliable evidence into a score.
- It does not treat agreement between two systems as truth.

## Scientific rules that bind every item

- Keep measurements, listener perceptions, interpretations and outcomes
  separate. Never pool truth classes.
- A language model may explain evidence. It may not create measurement truth.
- Accuracy and reliability are different. A repeatable measurement can still be
  wrong.
- Development, tuning and evaluation data are separated by participant.
- A software snapshot is not independent truth.
- Sources overlapping a candidate's training lineage cannot qualify that
  candidate.
- Freeze the analysis before looking at the result. A recorded no selection is a
  legitimate completed outcome.
- Preserve raw evidence needed for audit.

## What success looks like

Not a score, and not a finished application. Success is a public artifact that
an independent person can obtain, run, check and disagree with:

- a reproducible audit of how pronunciation measurement behaves across declared
  English reference varieties, with its uncertainty stated honestly;
- an open implementation of the provenance, abstention and claim verification
  machinery, which does not currently exist as open infrastructure in this
  field;
- an honest record of what was tried, what failed and what could not be
  established at all.

Negative results are outputs, not failures. The most valuable finding this
project has produced so far is that no candidate system passed its gates.

## Audience

Researchers and engineers working on pronunciation assessment, speech
measurement fairness, and reproducibility in speech technology, and anyone else
curious enough to clone the repository and run a command.

Adam widened this on 2026-08-28. Only who may run it changed. The project still
gives nobody feedback on their speaking, and everything above under what it
claims and what it refuses stands unaltered. A reader who arrives wanting to
know how well they speak will not find out here, by design.
