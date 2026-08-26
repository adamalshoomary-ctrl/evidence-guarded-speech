# Checkpoint 22E3 external schema smoke runbook

This runbook reproduces the external schema smoke evidence. It is the only
procedure in this repository that sends audio to a third party, and it may send
public research corpus audio only. Adam's own recordings in `/audio` are
excluded by written rule and must never be sent to any external provider.

Running the smoke test again is not a routine action. It spends real requests
against Adam's Azure resource and transmits audio off the machine, so it needs
a fresh owner decision each time. Everything below except step 4 is safe and
sends nothing.

## 1. Read the two gates first

- `corpus_manifests/provider-transfer-review-v1.0.0.json` decides one named
  corpus and one named provider at a time. A pair that is not listed is
  prohibited; absence is never permission.
- `external-smoke-contract-v1.0.0.json` was declared before any request. It
  fixes the sample, the parameters, what counts as a present field, what counts
  as repeatable and what each outcome permits checkpoint 22E4 to do.

Neither may be edited to accommodate a result. If a real response contradicts
the contract, the contract is right and the finding is recorded.

## 2. Confirm the gates and the planned requests without sending anything

From the repository root:

```sh
python3 -m speech_sound_patterns.azure_smoke --dry-run
```

This checks that the provider register marks the lane ready, that the register
and the transfer review both permit the exact lane and source pair, that the
predeclared contract validates, that the frozen expected-only manifest still
matches SHA256
`c918feffa7c0a3a3fa99ce7a9e028621e8fb002980777297f30088e5975331da`, and that
every selected clip still matches its recorded audio hash and is 16 kHz mono
16 bit PCM under the 30 second pronunciation assessment limit. It then prints
the planned requests and exits without sending audio.

Selection is deterministic and label blind. It reads split, stratum, duration
and identifier only, so no clip can be chosen because it would flatter or
embarrass a provider. Only the audio and the intended reference text are ever
transmitted; expert reviewer strings, aggregate mispronunciations, reference
phone sequences and private participant identifiers are not.

## 3. Validate the committed evidence

```sh
python3 -m unittest tests.test_speech_sound_external_smoke
python3 -m unittest tests.test_speech_sound_provider_register
```

## 4. Send audio, only with a fresh owner decision

```sh
python3 -m speech_sound_patterns.azure_smoke
```

Credentials come from the gitignored `.env` by variable name and are never
printed, logged or written to any artifact. The run pauses between requests, it
stops rather than hammering retries if the service reports a quota or rate
limit, and it retains every raw response privately under
`.research_data/speech_sound_patterns/external_smoke/azure`.

## 5. Rebuild the report without sending anything again

The committed report can always be regenerated from a retained raw response
file, so a reporting fix never costs another upload:

```sh
python3 -m speech_sound_patterns.azure_smoke \
  --summarize-from .research_data/speech_sound_patterns/external_smoke/azure/RAW.json
```

## What the committed report may contain

`external-schema-smoke-v1.0.0.json` carries aggregate field presence,
capability states, repeatability, advancement outcomes and one locale
distinctness summary. It carries no transcript text, no per clip score and no
participant identifier. `PronScore`, `FluencyScore`, `CompletenessScore` and
`ProsodyScore` are prohibited output classes and the validator rejects a report
containing them.

## What this evidence is not

It is response shape and repeatability evidence. It measures no accuracy,
reads no expert label, touches no held-out participant, selects no system and
sets no threshold. A configuration advances only on observed response fields.
Documentation, marketing, an overall score or agreement with another system can
never qualify a lane.
