# Checkpoint 23B governance runbook

This runbook checks the public fail-closed state. It does not contact anyone,
create research evidence, open private files or authorise participant work.

## Validate the current contract

From the repository root:

```text
python3 -m motor_speech_voice.validate_governance
```

The valid in-progress result says:

- adults first is recorded;
- every lane is unselected;
- the legal sponsor and external governance are unresolved;
- no contact, spending, participant work, data use or implementation is
  authorised;
- the active pipeline contains no item 23 import or contract binding.

Version 1.0.0 is an immutable in-progress snapshot. Its validator binds every
current JSON leaf through canonical SHA 256, then checks the safety structure
and scans the runtime `pipeline` package for an item 23 import. Changing even an
apparently descriptive value requires a new reviewed contract version and a new
validator; it cannot quietly turn this record into approval.

Run its focused tests with:

```text
python3 -m unittest tests.test_motor_speech_voice_governance -v
```

## Validate the candidate reference source survey

```text
python3 -m motor_speech_voice.validate_source_survey
```

The valid result reports how many sources were surveyed, how many are
obtainable with no contact, account or agreement, and how many carry a licence
permitting commercial use, then states that no source is recorded as meeting an
item 23 truth requirement, that nothing is selected and that no acquisition is
authorised. It prints each lane's answer.

The survey records what a public source could supply and under what terms. It
is not an acquisition decision, a rights opinion or a judgement that any source
is scientifically or ethically suitable. Acquiring any surveyed source needs its
own owner decision, and for a source requiring an account, a signed agreement or
a fee, that decision includes accepting those terms.

Run its focused tests with:

```text
python3 -m unittest tests.test_motor_speech_voice_source_survey -v
```

## Validate the measurement and sampling input package

```text
python3 -m motor_speech_voice.validate_measurement_plan
```

The valid result reports how many provisional constructs are recorded, states
that no construct, task, estimand, statistic or threshold is selected, states
that no sample size is computed, and prints each governance lane's reference
position.

The package records the inputs an independent statistician would need before a
study could be designed. It is not a statistical plan and cannot become one by
being extended. Two rules keep it that way: a record may contain no JSON number
at all, and the computed sample size is typed null in the schema so one cannot be
written even by accident. The validator also cross-checks every reference
availability claim against the checkpoint 23B source survey and refuses a record
that disagrees with it.

Rebuild with `python3 -m motor_speech_voice.build_measurement_plan`. Run its
focused tests with:

```text
python3 -m unittest tests.test_motor_speech_voice_measurement_plan -v
```

## Validate the documented regulatory and privacy reading

```text
python3 -m motor_speech_voice.validate_regulatory_reading
```

The valid result reports how many questions were read across how many domains,
how many open questions and source conflicts are recorded rather than resolved,
states that no determination, approval or advice is recorded, and prints the
three rungs of the intended purpose ladder with their positions.

Every record is a documented reading of public sources by a non lawyer. It is
never advice, a determination, an approval or a defence. Every record must rest
on at least one source read directly at the source, must name at least one
accountable human role that has to settle it, and must name what it could not
settle. The validator pins the screening rung of the ladder and refuses a ladder
that stops getting stricter as the claim gets stronger, which is the specific way
this artifact could be softened later.

Sources change. Every record carries the currency the source states and the date
it was read. A stale reading is redone, not trusted.

Rebuild with `python3 -m motor_speech_voice.build_regulatory_reading`. Run its
focused tests with:

```text
python3 -m unittest tests.test_motor_speech_voice_regulatory_reading -v
```

## Validate the checkpoint deliverable ledger

```text
python3 -m motor_speech_voice.validate_checkpoint_ledger
```

The valid result reports all thirteen required deliverables, how many are
complete, advanced but unfinished, and blocked on a named human role, and repeats
that checkpoint 23B remains in progress and that acceptance is written review.

The ledger exists so a large body of honest public research cannot be mistaken
for progress toward acceptance. The validator refuses a ledger that closes the
checkpoint, claims a selection, a contact, a spend or an acquisition, marks a
deliverable complete without evidence that exists on disk, marks one unfinished
without naming who has to finish it, or leaves nothing blocked at all.

Rebuild with `python3 -m motor_speech_voice.build_checkpoint_ledger`. Run its
focused tests with:

```text
python3 -m unittest tests.test_motor_speech_voice_checkpoint_ledger -v
```

## Public and private evidence boundary

The public repository may contain:

- role requirements and decision rights;
- public source links and public professional profiles;
- blank review, conflict and due-diligence templates;
- aggregate lane decisions, reasons and release boundaries;
- hashes of privately retained signed evidence where the responsible
  institution and privacy review permit that design.

The public repository must not contain:

- signatures, private email, phone or address details;
- contracts, invoices, identity documents or certification evidence supplied
  privately;
- participant identities, consent forms, recordings or row-level evidence;
- confidential professional, legal, ethics, security or regulatory advice;
- HREC portal exports or credentials.

If external review is later authorised, its approved private evidence root is
planned as `.research_data/motor_speech_voice/23b/`. That directory is already
gitignored, but it must not be created or populated until the responsible entity,
access, retention, backup and deletion design are approved. Gitignore is not a
privacy or security control.

## Change control

Before Adam commits this version, factual corrections may update version 1.0.0.
After commit, do not rewrite it to imply that a person was contacted, appointed
or approved. Issue a new contract and decision-record version that binds:

- the previous public contract hash;
- private evidence hashes or institution-issued identifiers where lawful;
- each lane's independent decision;
- conflicts, recusals and dissent;
- whether any participant, private participant, private governance or held-out
  evidence was accessed, with those categories kept separate;
- downstream states and every release boundary.

A name in the shortlist is not an appointment. A sent message is not a written
review. An HREC decision is not site or institutional governance authorisation.
Professional advice is not regulatory approval. The validator must continue to
fail closed across those distinctions.

Use `governance-record-templates.md` for the minimum record content after the
owner and responsible organisation authorise completion. An institution's own
mandatory form takes precedence, but it does not remove the contract's separate
role, conflict, evidence and lane-decision requirements.

`final_decision.py` defines the separate machine validator for a future final
23B artifact. Its test fixtures are invented structures used only to test the
rules. They are not evidence, decisions or candidate selections. The final
validator requires the immutable parent-contract fingerprint, all lane records,
the exact signed-artifact digest and a separately calculated evidence-node hash,
opaque nonidentifying assignments, scoped role and conflict decisions, every
applicable governed deliverable and structured authority outcomes. The node
hash covers the artifact digest plus the declared issuer, subject, scope,
candidate and dependencies. Every dependency node hash must resolve to that
exact parent or one manifest record, the graph must be chronological and
acyclic, and the owner-issued overall decision must bind the complete cited
package. A selected lane decision also binds its exact candidate specifications,
authorities, deliverables, competence records, conflicts, signed reference-truth
decision and signed role decisions. Candidate-neutral evidence cannot import a
different lane, and closed-lane blocker evidence depends on exactly the parent.
This prevents a later public record from being silently swapped or relabelled
without changing its node and every dependent node.

The artifact has exactly one product-owner assignment. Every owner-issued
record and product-owner role decision uses it. Developer and candidate-vendor
organisations cannot supply approvals or signed blockers. Construct, task,
reference truth, threshold, data custody and release use distinct assignments
and organisations. The reference-truth owner has an exact candidate-bound
private decision, not an unused placeholder appointment.

A required participant-report or clinical/laryngeal reference uses distinct
construct, task and measure records. Its accountable roles cover both the
selected lane and the reference lane, the reference lane cites those role
decisions, and their project decisions bind the exact reference protocol or
manual. Reference construct, task and measure nodes have exact reference-only
scope; the reference lane decision has exact selected-plus-reference scope.
Every real conditional reference owner joins the organisation-separation matrix,
including when both conditional references are required. A closed lane may cite
only a lane-appropriate blocker; evidence for a different candidate lane cannot
be hidden directly or transitively inside that closure. CTN or CTA also forces
the HREC and site-authorisation gates, and site authorisation exactly depends on
both the ethics decision and site-applicability determination.

The validator checks structure, identity tokens, declared responsibility,
public node integrity and hash linkage. It cannot read a private opinion, verify
a private signature or prove that its substance is professionally correct. The
responsible institution and independent release group must verify that the
private bytes and signature expressly attest the public node claims before the
metadata is entered, and must verify authority and meaning. An artifact hash
match proves only that the same bytes were referenced. A valid public node is
not ethics, legal, clinical, statistical, security or regulatory approval.

The validator permits exactly one candidate lane to become 23C-eligible while
an unrelated lane rejection remains preserved, and it keeps scores, thresholds,
participant data, releases, implementation and 23C approval closed. No final
artifact exists today.

## Conditions for a final 23B decision

The checkpoint may end with `selection` only when all applicable independent
roles have provided the evidence and signed decisions required by the
governance contract. A lane may independently record `no_selection` without
blocking an unrelated lane.

If any required benefit, professional, participant, institution, ethics,
privacy, rights, security, statistical or regulatory question remains
unresolved, the final result is `no_selection`. It must set later dependent
checkpoints to `not_applicable` and prove that participant and held-out evidence
was not accessed.
