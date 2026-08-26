# Phase B completion record

Archived: 2026-07-20

This file preserves the completed Phase B decisions and acceptance evidence.
It is historical context, not the live work queue. Read `current-state.md` and
`improvement-plan.md` first.

## Outcome

Phase B completed the backend definitions for onboarding, pronunciation
research, durable identity and consent, and credible personal progress. It did
not build application screens, accounts, a database, an active pronunciation
measurement, or a released personal progress metric.

## English onboarding assessment

The versioned assessment manifest defines a roughly ten minute English solo
assessment containing context and consent, a recording check, reading or a
spoken alternative, natural speech, goal specific speech, a matched repeat and
reflection.

It includes accessibility alternatives, separate consent rules, cautious
progression handoff and optional research probes. There is no backend age gate,
exact age field, age norm, overall score, diagnosis, ranking or application UI.

Primary records:

- `assessment/manifest-v1.0.0.json`
- `assessment/research-and-protocol.md`

Acceptance evidence is also retained in
`docs/archive/improvement-plan-through-item-16.md`.

## Pronunciation and intelligibility research

The research protocol separates blind listener word understanding from human
phonetic reference and accent. Qualified independent reviewers, retained
disagreement and documented adjudication are required for phonetic truth.
Commercial providers, local methods and ASR remain candidates rather than
reference truth.

The active word pack and provider selection remain empty. Normal coaching,
individual progress, ranking, screening and diagnosis remain locked until a
professionally reviewed word pack and independent held out evaluation exist.

Primary records:

- `assessment/pronunciation-research-v1.0.0.json`
- `assessment/pronunciation-research-and-protocol.md`

Acceptance evidence: the protocol validator, offline benchmark and mutation
tests passed. The full 109 test suite passed. The isolated real conversation
pipeline completed without history writes and its objective artifact passed
all four real recording checks. Optional coaching safely degraded when claims
failed verification.

## User, session, task and context records

The backend data contract defines opaque account, session, context, task,
attempt, recording, analysis, consent and data request records. Local speaker
labels never become durable identity. Attempts are immutable and first,
exercise, repeat, retention and transfer evidence remain linked without being
overwritten.

Consent for service processing, recording retention, research, model
improvement, human review and fairness metadata remains separate. Export,
correction and deletion boundaries are defined before application launch.

Primary records:

- `data_model/contract-v1.0.0.json`
- `data_model/research-and-protocol.md`

Acceptance evidence: the contract and example validators, all 130 unit tests
and synthetic controls passed. A nonpersonal runtime check copied valid context
and rejected history without stable identity. The isolated real conversation
pipeline completed without personal history writes and its objective artifact
passed all four real recording checks.

## Personal baseline and meaningful change

The progress protocol requires explicit recording intent and comparable
account, context, task, prompt, language, mode, quality, capture, preparation
and accommodation conditions. A future metric profile defines its own required
observations, sessions and days. One recording is never a baseline by default.

A credible change must strictly exceed individual measurement error, expected
natural variation and a separately justified meaningful change boundary.
Increases and decreases are not automatically improvement or decline. Speech
measurements, user reports, real world outcomes, practice, mastery and run
quality remain separate.

The production registry releases zero metrics because the required repeated
participant evidence does not exist. Same day repeats are practice. Future
mastery requires separate later retention and suitable new prompt transfer.

Primary records:

- `progress_model/contract-v1.0.0.json`
- `progress_model/reliability-registry-v1.0.0.json`
- `progress_model/research-and-protocol.md`

Acceptance evidence: the progress and data model validators, all 146 unit tests
and synthetic controls passed. An isolated fictional history test wrote only
temporary files and returned `metric_not_released`. The strict baseline gate
correctly rejected the real solo recording because of recording quality. The
full isolated solo coaching pipeline completed without history writes and its
objective artifact passed all five real solo checks. Optional coaching safely
degraded when claims failed verification.

## Locks that remain binding

- Pronunciation measurement remains locked pending professional word pack
  review and independent human labelled evaluation.
- Personal progress metrics remain locked pending representative repeated
  production studies, measurement error, natural variation, meaningful change
  and held out evaluation.
- Fairness remains `not_evaluated` without representative consented evidence.
- Ranking, screening, diagnosis, treatment and high stakes use remain blocked.
- Phase C and application work require a new explicit decision from Adam.
