# User, session, task, and context data protocol

Version: 1.0.0  
Status: backend contract, not a database  
Owner design approval: 2026-07-19

## Decision

The future application needs stable records before it needs screens or a
database. This protocol defines those records and their relationships. It does
not choose a database, authentication provider, service API, retention period,
or frontend technology.

`SPEAKER_00` remains a local label inside one recording. It is never a durable
person identifier. A stable opaque `account_id` owns sessions and user data. A
product `session_id`, a task `attempt_id`, a recording ID, and a pipeline
`run_id` are separate because one product session may contain several tasks,
recordings, and analysis runs.

## Why the records are separate

| Record | What it means | Why it cannot be merged with another record |
|---|---|---|
| Account | The stable owner of their product data. | A speaker label can change between recordings. |
| Communication context | A goal and situation such as interview or presentation. | Performance in unlike situations is not automatically comparable. |
| Session | One period of product activity for one account and context. | One account can have many sessions. |
| Task definition | Versioned instructions and prompt content. | Content changes can change measurement meaning. |
| Task attempt | One immutable production of one task. | A retry must not overwrite weaker or earlier evidence. |
| Exercise assignment | The versioned practice chosen after an attempt. | Later change cannot be attributed without knowing what happened between attempts. |
| Recording asset | Audio ownership, participants, consent state, and storage state. | Audio can have retention rules different from derived artifacts. |
| Analysis run | One pipeline execution and its provenance. | Reanalysis may occur without a new human attempt. |
| Consent event | One purpose-specific grant, decline, or withdrawal. | New consent cannot erase the earlier historical decision. |
| Data request | Export, correction, or deletion request history. | Completion and exceptions must be auditable. |

Every user-owned record is discoverable from `account_id`. Shared task
definitions are versioned content referenced by user records; they are not
copied into or deleted with every account.

## Attempts and the learning chain

An attempt has one of five roles:

1. `first`;
2. `matched_repeat`;
3. `post_exercise_repeat`;
4. `retention`; or
5. `transfer`.

A first attempt has no parent. Every later attempt links to the earlier attempt
it follows. A post-exercise repeat also links to the versioned exercise.
Retention and transfer stay distinct. No attempt is replaced, and the system
cannot silently retain only the best result.

The relationship is:

```text
first attempt -> exercise -> repeat -> later retention -> suitable new prompt
                                                      -> transfer
```

This structure does not prove progress. The separate personal progress protocol
defines the required comparison and release evidence. Its production registry
currently releases zero speech metrics because measurement error and normal
variation have not been established.

## Context and comparability

The first context categories are interview, spoken exam, presentation,
demonstration, important conversation, social practice, everyday confidence,
conversation, and custom.

A context stores the person's declared goal, audience, and environment. The
task attempt separately stores task and prompt versions, language, preparation,
accommodations, self-report, capture device class, technical environment,
quality policy, and pipeline provenance.

Declared context and technical observation never overwrite one another. The
model does not collect exact age, infer diagnosis, or permit a hardware device
fingerprint. Fairness metadata remains a separate consent purpose.

History comparisons are scoped by both stable account and stable context.
Legacy records with only `speaker_label` are retained as personal audit data
but are not silently assigned to a new account or context.

## Participants and speaker labels

Each recording has exactly one account holder, locally labelled `SPEAKER_00`.
A solo recording contains only that participant. Conversation mode requires at
least one separately consented participant and a user-confirmed speaker map.

Other participants receive session-scoped opaque IDs. They do not receive a
durable account identity unless they separately authenticate and consent. This
prevents the system from inventing an identity for another voice.

## Consent events

The separate purposes are:

- speech measurement processing;
- raw audio retention;
- human review;
- research collection;
- model improvement; and
- fairness metadata.

Every recorded participant has one explicit effective decision for every
purpose in the runtime snapshot. Coaching processing must be granted before a
product-context run. All optional purposes can be declined without reducing
access to anything else. Choices default to declined, use a versioned notice,
and record whether the person or an authorised representative made the choice.

Consent history is append-only. A later withdrawal changes future permitted
use but does not falsify the earlier record. Consent is never inferred from a
voice, from continued product use, or from another consent choice.

The design follows current OAIC guidance that collection should be necessary
and proportionate, and that consent should be informed, voluntary, current,
specific, and withdrawable. [OAIC APP 3 guidance](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-3-app-3-collection-of-solicited-personal-information),
[OAIC consent guidance](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-b-key-concepts)

## Export, correction, and deletion readiness

An export is a versioned machine-readable account bundle containing sessions,
contexts, attempts, exercise assignments, recording metadata, analysis and
provenance, measurements, interpretation artifacts, self-reports, consent events,
correction statements, and data-request history. Shared task content is
included by reference. Identity verification is required before release.

Correction can update incorrect facts or attach a disagreement statement. It
does not silently rewrite historical speech, task, measurement, or interpretation
evidence. This preserves what the system actually knew and reported at the
time while keeping corrected information visible. [OAIC APP 13 guidance](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-13-app-13-correction-of-personal-information)

Deletion starts from `account_id` and records a status for every target:
sessions, contexts, attempts, exercises, audio, analysis artifacts, derived
measurements, provider copies, applicable research copies, and backup expiry.
Any legal or operational retention exception must be explicit. This contract
does not invent the public retention periods or perform deletion. OAIC guidance
requires reasonable security and destruction or de-identification when
personal information is no longer needed for a permitted purpose.
[OAIC APP 11 guidance](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information)

## Runtime pipeline context

Developer runs remain possible without product context. A future application
or controlled integration can pass a validated context with:

```text
python3 pipeline/run_all.py \
  --mode solo \
  --audio AUDIO_PATH \
  --session-context CONTEXT_PATH
```

The runner copies the validated snapshot to `session_context.json` and stores
its stable references and canonical SHA-256 in provenance. The full context is
not treated as pipeline configuration truth until validation succeeds.

A durable history write additionally uses `--me SPEAKER_00`. It is rejected
without a session context. The history record stores account, session, context,
task, prompt, and attempt IDs. The personal progress protocol also requires the
attempt to state whether it is collecting baseline, checking change, recording
practice, checking retention, or checking transfer. Optional usefulness and
real world outcome reports remain user declared and separate from speech
measurements. The speaker label remains only the local measurement selector.
Tests never append to the owner's history.

Validate the model and an optional context with:

```text
python3 -m data_model.validate
python3 -m data_model.validate data_model/session-context-example-v1.0.0.json
```

The example contains fictional opaque identifiers and no real user data.
