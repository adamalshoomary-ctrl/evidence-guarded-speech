# Item 22 speech sound research engineering plan

Status: checkpoint 22H final report passed on the sealed no-selection path;
item 22 completion is mechanically determined by the valid immutable
post-report repository closure

> **Read this first, 2026-08-22.** Two things changed after this plan was
> written and both bear on how it should be read.
>
> **The project is now open research with no monetisation plan, permanently.**
> Every commercial constraint recorded below is therefore historical. Sources
> excluded on non commercial grounds alone, including Unisyn, Mitchell and
> Delbridge, L2 ARCTIC, the Speech Accent Archive, MD_NLP, MAE VoiS and Sydney
> Speaks, are now permitted subject to their own manifests and Adam's go.
> Exclusions on methodological grounds, such as CoANZSE, and on access grounds,
> such as AusTalk, stand unchanged.
>
> **The checkpoint 22E8 reference variety probe was repaired on 2026-08-23 and
> every 22E8 number below is superseded.** Mapping version 1.2.0 corrected six
> phone families the frozen model never produces for English and merged post
> vocalic r into the model's own combined token. The sample was rescored with a
> byte identical selection. Roughly half of every flag was noise, the reported
> rhotic effect does not exist, and the recorded mechanism that the reference
> swap only worked by declining to score was itself an artifact of the defect.
> The current report is `variety-probe-v1.1.0.json`; version 1.0.0 remains as the
> superseded record and no longer validates. Numbers in `audit-2026-08-22.md`
> section 6.
>
> Nothing else in this plan is retracted. The gates, the recorded no selection,
> the sealed held out participants and the frozen SpeechOcean762 benchmark all
> stand.

Planning decision date: 2026-07-20

Dataset decision update: 2026-07-21

Scientific and product release: locked

## Simple decision

Item 22 may be engineered without hiring participants, speech pathologists or
phonetic reviewers now. A commercially usable public evidence stack can cover
expert phone-relation development, exact timing tests, broad phone-processing
tests and Australian English false-concern tests. Local models and a small paid
API comparison can produce developer-only review candidates.

This does not lower the release standard. Engineering completion and scientific
release are different gates:

- Engineering completion has two possible paths. A selected method would need a
  reproducible offline extractor, structured evidence, tests, held-out
  public-corpus results, explicit abstention and a safe integration check. The
  later frozen evidence selected no method. Adam approved the conservative
  no-selection path on 2026-08-12: held-out evidence stays sealed, every held-out
  metric is explicitly unavailable, and engineering may close only after the
  repository acceptance and post-report closure prove the inactive boundaries.
- Scientific release means that the system has representative evidence for the
  intended population and task, including legitimate varieties and independent
  human references.
- Product release means that a separately approved task may show a carefully
  supported result to a user.

Only the first gate is in scope. Coaching, scoring, personal progress,
screening, diagnosis, severity, treatment and clinical pattern names remain
blocked.

## Why this is offline first

The current solo and conversation recordings do not establish which exact word
the speaker intended. ASR is not allowed to invent that intent. Item 22 will
therefore begin as an explicit research tool for short controlled-word clips
whose prompts are known.

It will not be added to normal `pipeline/run_all.py` execution in the first
engineering release. A later assessment runner may call it only after that
runner and its task contract receive separate approval. A full normal pipeline
run remains an acceptance check for regressions and for confirming that no
speech-sound output leaks into ordinary coaching.

## Durable acquisition and account register

These requests must not be forgotten. Adam owns the accounts, purchases and
licence agreements. API keys belong only in `.env`, never in a committed file.

| Resource | Why it matters | Adam action | Status | Blocks initial engineering |
|---|---|---|---|---|
| [Macquarie Dictionary Australian English Pronunciation Data](https://www.macquariedictionary.com.au/pronunciations/) | More than 139,000 IPA entries, documented Australian variants and almost 30,000 Australian pronunciation recordings. This is the strongest identified Australian reference pack. | None under the standing owner decision. Reopening requires Adam to approve an enquiry. | NOT LICENSED. Adam declined acquisition enquiries on 2026-07-28. Open references remain the engineering fallback and cannot establish produced-phone truth. | No. |
| [Australian National Database of Spoken Language, ANDOSL](https://researchdata.edu.au/australian-national-database-spoken-language/124997) | Australian recordings with phonetic, phonemic and word annotations across documented Australian accent groups. This was believed to be the strongest existing Australian phone-labelled reference set. | None. The owner declined acquisition enquiries on 2026-07-28. | REJECTED 2026-07-28, manifested at 22E6 as `andosl`. The Research Data Australia record states the licence as private research and study only, all other use by permission, with intellectual property held by Macquarie University and A/Prof Steve Cassidy as manager, rechecked 2026-07-29. Commercial use is prohibited, so this lane is closed rather than pending. `andosl.anu.edu.au` still carries a domain name alias chain to an ANU address but nothing answers on port 80 or 443, so the earlier note that it does not resolve was imprecise and its conclusion held. | No. An equivalent independently and expertly labelled Australian set may substitute. |
| [Mozilla Data Collective](https://mozilladatacollective.com/) | Supplies every speaker group the checkpoint 22E8 bias probe compares, all from one release, one platform and one validation process, which is what controls the recording quality confound. | Keep the private account and API credential secure. Accept new terms again only if a later release requires it. | TERMS ACCEPTED AND ALL FOUR ACCENT SUBSETS HELD AND VERIFIED. Australian English since 2026-07-21; British Isles English, American English (Male) and American English (Female) acquired 2026-07-29, the female subset after Adam accepted its terms that day to close the gender confound. Each archive matches its published SHA256 and each is participant split with its held-out speakers sealed. | No. |
| [TIMIT through the Linguistic Data Consortium](https://catalog.ldc.upenn.edu/LDC93S1) | Hand-verified phone and word timing, but the official licence is restricted and the public torrent supplies no reuse rights. Acted Clear Speech and Common Phone cover its useful engineering roles without this risk. | Do not download the torrent, create an LDC account or purchase TIMIT for current engineering. | REJECTED FOR CURRENT ENGINEERING | No. |
| [Microsoft Azure Speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment) | Core external score comparator. `en-AU` is useful for Australian false-concern stress testing, but named and N-best spoken phones are documented only for `en-US`; therefore Azure is not a truth anchor and the locales remain separate. | Confirm the existing Azure account, create a Speech resource in Australia East, and place its key and region in `.env`. | RESOURCE `a private Azure Speech resource` CREATED IN AUSTRALIA EAST (FREE F0), CREDENTIALS IN `.env` AND VERIFIED WITH A HARMLESS TOKEN REQUEST 2026-07-24 | Yes for the Azure role only. |
| [ELSA Scripted V3](https://api-external-doc.elsanow.co/Scripted-api-info) | Conditional external exact-substitution candidate. It has the best documented produced-phone field found for adult non-native speech, but access requires an NDA and the public contract, retention, region, training use, deletion/insertion behavior and real response semantics are not sufficient. | Complete the API enquiry and NDA, obtain a token, a real substitution response, deletion and insertion semantics, and written benchmark, publication, region, retention, deletion and training-use answers. | ENQUIRY, NDA, TOKEN AND WRITTEN PERMISSION NEEDED | Yes for the ELSA role only. |
| [iFLYTEK Global Pronunciation Assessment](https://global.xfyun.cn/doc/voiceservice/ise/API.html) | Experimental public-corpus comparator. Its English response flags missed, added, repeated and replaced phones but names only the expected phone, not the produced replacement; the documented child/adult group switch does not apply to the English tasks needed here. It cannot supply exact relation truth or the child lane. | None. Adam declined this lane. | DECLINED BY ADAM 2026-07-25 BEFORE ANY AUDIO WAS SENT, ON REPUTATIONAL AND UNAUDITABLE PRIVACY GROUNDS. Account, 100,000 free calls to 2026-10-22 and credentials verified 2026-07-24 all remain, but the register status is `owner_declined` with a blocked audio policy. Reopening needs a new explicit owner decision. | No. Its removal costs only this experimental role. |
| [Segmentation-free GOP](https://arxiv.org/abs/2507.16838) | Core local repair. It directly removes the forced phone-boundary dependency implicated in 22D's recall miss, its method core is label-blind and training-free over a CTC phone model, and the paper is CC BY 4.0. The authors' repository has no code licence, so its code and trained SpeechOcean scoring heads cannot be used. | Email the NTNU authors for a code and checkpoint licence, while planning an independent implementation of the published equations on the Apache-2.0 Meta phone model regardless of their answer. | CLEAN IMPLEMENTATION APPROVED IN PLAN, AUTHOR LICENCE OPTIONAL | Yes for the primary local repair. |
| [POWSM](https://huggingface.co/espnet/powsm) | Core local free-phone comparator. The released model is explicitly CC BY 4.0, has a documented model card and standard ESPnet artifacts, and emits unconstrained phones, so it can challenge the expected-phone-conditioned GOP from a different architecture. IPAPack++ and G2P-derived training lineage must still be recorded and kept separate from independent truth. | No account is needed. Pin the exact revision, audit IPAPack++ lineage, and measure the 16 kHz, 20-second-window and Mac runtime constraints before benchmark use. | REVISION 21ffa410 PINNED, PICKLE AUDIT CLEAN, LINEAGE RECORDED, FEASIBILITY PASSED 2026-07-24 | Yes for the second core local candidate unless lineage or runtime fails closed. |
| [ZIPA](https://github.com/lingjzhu/zipa) | Conditional local free-phone candidate. The code repository is MIT and Apple-Silicon-friendly ONNX artifacts exist, but the separate public model repositories do not carry an explicit model-weight licence or adequate model-card provenance. This is why ZIPA is conditional while POWSM is core: POWSM's released weights themselves have an explicit CC BY 4.0 licence and documented packaging; ZIPA's code licence does not automatically license its weights. | Ask the authors to add or confirm a commercially usable licence and provenance for the exact checkpoint. Do not load or benchmark the weights until that is resolved. | CODE LICENSED, MODEL WEIGHTS LICENCE MISSING | No. It advances only after the weight gate passes. |
| [Wav2Vec2 CommonPhone](https://huggingface.co/pklumpp/Wav2Vec2_CommonPhone) | Supporting-only local comparator. Its CC0 weights and safetensors create little legal or loading friction, but it was trained on Common Phone, which derives from Common Voice. The project's Common Phone and Australian Common Voice evidence are therefore non-independent and cannot qualify this model for selection. | No account is needed. Pin the exact revision and use it only on sources whose manifests prove independence from its training lineage. | PUBLIC CC0 WEIGHTS, NON-INDEPENDENT ON TWO PROJECT SOURCES | No. |
| [UNSW Speech Attributes](https://huggingface.co/spaces/mostafaashahin/Speech-Attributes) | Research-only articulatory candidate. It can describe voicing, place, manner and vowel-feature differences, which is complementary to phone scoring, but the actual adult and Australian child checkpoints have no model licence, model card or training statement and the published method uses restricted or non-commercial corpora. | Send one combined UNSW enquiry covering the exact checkpoint licence and training rights together with AusKidTalk access. Do not load a checkpoint until the written answer permits it. | CODE LICENCE VISIBLE, CHECKPOINT AND DATA RIGHTS BLOCKED | No. |
| [Child phoneme model](https://huggingface.co/lijialudew/wav2vec_children_ASR) | Conditional child feasibility candidate, not a validated assessor. Its Hugging Face model card explicitly labels the repository `openrail`, and the weights were fine-tuned through LibriSpeech, MyST and Providence for child phoneme representations and vocalization classification, not verified pronunciation assessment. OpenRAIL is not equivalent to unrestricted commercial permission, and the derived-weight rights of MyST and Providence must be resolved. | Review the exact OpenRAIL terms and obtain written confirmation of checkpoint and training-corpus rights if the terms are ambiguous. Do not claim child validity from the model's name or public download. | OPENRAIL TAG CONFIRMED, EXACT USE AND DERIVED-DATA RIGHTS UNRESOLVED | No. |
| [AusKidTalk](https://link.springer.com/article/10.1007/s10579-026-09929-5) | Australian child evidence acquisition and collaboration path, not a ready scoring system. It is directly relevant to ages 3 through 12 and includes typical and disordered speech, but current access is research-only through a data custodian and the published annotation is orthographic; phone annotation and commercial or derived-model rights are not established. | Include corpus access, phone-level annotation availability, aggregate benchmarking, commercial research and derived-model rights in the combined Shahin and Ahmed enquiry. | RESEARCH ACCESS REQUEST AND RIGHTS CLARIFICATION NEEDED | No. |
| [Bookbot Australian G2P](https://huggingface.co/bookbot/byt5-small-wikipron-eng-latn-au-broad) | Conditional prompt-target tool, not a scorer. It is Apache 2.0 and its name claims an Australian broad-IPA WikiPron variant. | None. Do not use it to propose targets. | PROVENANCE DISPROVED, NOT MERELY UNVERIFIED. Reverified at 22E6 on 2026-07-29: WikiPron's own language configuration defines English with exactly two dialects, `uk` and `us`, and its scrape directory holds only the four UK and US English files. The model repository's card data names no training dataset at all, so the Australian claim rests entirely on the model name. The register records this as `training_data_claim_state: disproved`, the lane fails closed on lineage rather than on licence, and its status stays `conditional` by the owner's decision of 2026-07-29. | No. Wiktionary's own Australian-tagged entries replace this role and can be inspected directly. |
| [SoapBox Labs](https://docs.soapboxlabs.com/technical-docs/online-technical-documentation/) | Rejected-unobtainable for current engineering. Curriculum Associates acquired SoapBox, no public developer acquisition path remains, and current evidence does not support relying on a new external contract. Its documented default product-improvement logging also contradicts the earlier immediate-deletion assumption. | Do not seek credentials or upload audio. Reconsider only if Curriculum Associates supplies a written external API offer and acceptable terms. | REJECTED UNOBTAINABLE | No. |
| [SpeechAce](https://www.speechace.com/api-plans) | Technically valuable custom-phone and sound-most-like evidence. | Do not create an account or upload audio unless SpeechAce grants a written waiver for comparative evaluation and aggregate publication. | CONDITIONALLY BLOCKED BY CURRENT TERMS | No. |
| [SpeechSuper](https://www.speechsuper.com/terms.html) | Its current terms prohibit the planned comparative evaluation. | Do not create an account or upload benchmark audio. | REJECTED UNDER CURRENT TERMS | No. |
| [L2-ARCTIC](https://psi.engr.tamu.edu/l2-arctic-corpus/) | Manual substitution, deletion and addition labels from three annotators across six first languages, which is the L1 diversity SpeechOcean762 lacks. Its CC BY-NC licence is not safe for this commercial product's engineering without written permission. | None for now. The corpus page names a licensing contact for uses outside CC BY-NC, so this is askable rather than closed, but the owner declined acquisition enquiries on 2026-07-28. | BLOCKED BY LICENCE, REOPENABLE BY ONE EMAIL THE OWNER HAS DECLINED TO SEND | No. SpeechOcean762 replaces its current role. |
| [TalkBank](https://talkbank.org/phon/) | Selected clinical resources could later test data structures, but access and commercial-use terms are corpus and role specific. | Do not download or use a corpus until its exact terms and participant restrictions are approved in writing. | BLOCKED PENDING SOURCE-SPECIFIC RIGHTS | No. |

### Open evidence search of 2026-07-28, and the owner decisions it produced

After checkpoint 22E5 recorded `no_selection`, three independent deep searches
were run over the openly licensed landscape, because every earlier acquisition
route depended on an enquiry nobody had answered. The searches changed the plan
more than any correspondence would have.

**Owner decisions, 2026-07-28.** Adam declined to send acquisition enquiries and
directed that this work proceed on openly licensed sources alone. He also
declined to purchase the ISLE corpus at its listed commercial price. These are
standing decisions: the drafted enquiries stay on record and remain available if
he changes his mind, but no lane may wait on one, and no plan step may be
blocked by one. Non-commercially-licensed material remains excluded, which is the
same rule that already rejected TIMIT and L2-ARCTIC rather than a new
restriction.

**The open stack this unlocks.** Every item below permits commercial use, needs
no correspondence, and at most needs a free account.

| Source | Licence | What it gives |
|---|---|---|
| Common Voice Scripted Speech 26.0 Australian English | CC0 | **Already acquired, verified and split since 2026-07-21.** 55,922 clips from 804 self-identified Australian speakers, participant-disjoint splits already audited at 754 development, 16 tuning and 34 sealed held out. The only unambiguously commercially clean Australian speech that exists, and this project has held it all along. Orthographic transcripts only. The search independently rediscovered it as a version 24 subset on the same platform; that older subset is redundant and must not be downloaded. |
| [WikiPron `eng_latn_uk_broad`](https://github.com/CUNY-CL/wikipron) | CC BY-SA | **Acquired 2026-07-29**, pinned to commit `d282e848`. 106,688 entries over 81,545 words, confirmed exactly. Recounted at acquisition it proved 6.85 percent post-vocalic rhotic with a 239 symbol inventory, so it supplements the British reference rather than replacing the American one. The matched `eng_latn_us_broad` scrape was acquired beside it, at 18.48 percent, so that comparison is measured and not asserted. |
| [Wiktionary Australian-tagged entries](https://kaikki.org/dictionary/rawdata.html) | CC BY-SA | **Acquired 2026-07-29** from the extraction of the enwiktionary dump dated 2026-07-06. The tag vocabulary was censused before any tag was chosen: 220 pronunciation tags exist and exactly three are Australian. They yield **5,347 words carrying 11,328 Australian tagged pronunciations**, not the roughly 2,700 recorded here before, of which 3,166 also carry a British reference. |
| [Montreal Forced Aligner English dictionaries v3.1.0](https://mfa-models.readthedocs.io/) | CC BY 4.0 | **Acquired 2026-07-29**, all three of English (UK), English (US) and generic English. The 22E6 phone counts of 99 and 73 were both wrong; the pages list 91 and 77 and the files carry one more each, the spoken noise phone `spn`. The word counts exceed the published figures by exactly the aligner's special tokens. **English (UK) is the chosen British referenced path** at 0.01 percent post-vocalic rhotic against English (US) at 23.58 percent, in one shared phone alphabet. There is still no Australian English dictionary. |
| [Macquarie University phonemic transcription guide](https://www.mq.edu.au/faculty-of-medicine-health-and-human-sciences/departments-and-schools/department-of-linguistics/our-research/phonetics-and-phonology/speech/phonetics-and-phonology/transcription/phonemic-broad-transcription-of-australian-english) | Document is theirs; the inventory is a fact | Fixes the Australian target phone inventory without licensing anything. |

**The reference variety defect this exposed.** Australian English is non-rhotic
and phonologically far closer to British Received Pronunciation than to General
American, yet every reference in this project is American. A large share of any
unfair flag against an Australian speaker is therefore not subtle accent
modelling at all: it is post-vocalic `r`, BATH, LOT and THOUGHT, and `t`
flapping. This costs nothing to repair and no rule was ever blocking it. It was
simply never looked for, which is the honest lesson of this search.

The repair may not touch the frozen benchmark. SpeechOcean762 was annotated
against American English by its own reviewers, so an American reference is
correct there, and changing it would redefine truth and break comparability with
the gates. The repair applies to Australian-facing work from checkpoint 22E8
onward.

**A distribution boundary that follows from CC BY-SA.** ShareAlike attaches when
adapted material is distributed, not when it is used internally. Deriving phone
targets and keeping them server-side is inside the licence. Shipping a derived
lexicon inside a mobile application is distribution, and ShareAlike plausibly
attaches to it. The lexicon therefore stays server-side, and that constraint is
recorded now, while it is free, rather than after an application exists.

**Mozilla Data Collective is larger than this project has treated it.** It now
publishes several hundred curated datasets across more than 300 languages, and it
splits Common Voice release 26.0 by accent, so American, British Isles, Scottish
and Australian English subsets all exist side by side under CC0. That last fact
is what makes the checkpoint 22E8 probe rigorous rather than suggestive, because
comparing accent subsets of one release controls the recording-quality confound
that comparing two different corpora cannot. The platform also hosts community
stuttered-speech datasets in English and Mandarin. Those are irrelevant to item
22 and are recorded here as a lead for item 21, whose scientific release is
blocked precisely for want of independently annotated event data; acting on them
needs its own owner decision and its own evidence review.

**Ruled out, with reasons, so none of these is re-investigated.**

- **AusTalk is unobtainable.** `alveo.edu.au`, `app.alveo.edu.au`,
  `support.alveo.edu.au` and `austalk.edu.au` all fail to resolve, and the
  collection is not in LDaCA either: its catalogue returns 21 collections and
  AusTalk is not among them. There is no application form, no registration and
  no click-through. What its manual annotation contains stays UNKNOWN and fails
  closed, which is moot while no access route exists.
- **CoANZSE is rejected on two independent grounds.** Its published terms offer
  it free for research, education and scholarship and prohibit redistribution and
  commercial use, and its audio belongs to hundreds of local councils, so those
  rights were never the author's to grant. Separately, it was force-aligned with
  an American acoustic model trained on LibriSpeech, so its alignment errors
  would correlate with exactly the Australian and American differences this
  project needs to measure and it would manufacture the bias it was brought in to
  detect. The 2026-07-28 note that it carried no stated licence at all was wrong
  and was corrected at 22E6; the verdict did not change.
- **Mitchell and Delbridge, the Speech Accent Archive, MD_NLP, MAE-VoiS and
  Sydney Speaks are all non-commercial** and are excluded on that basis alone.
  Mitchell and Delbridge is recorded here as the strongest Australian resource
  the project cannot use: 7,736 speakers at 330 schools in every state and
  territory, each reading two fixed consonant-rich sentences, downloadable
  anonymously, and CC BY-NC 4.0.
- **The expert-labelled field is nine datasets and one is usable.** A June 2026
  survey assembled every English corpus carrying human expert phonetic
  annotation: TIMIT, Buckeye, ISLE, L2-ARCTIC scripted and spontaneous,
  SpeechOcean762, EpaDB, PSST and DoReCo. All nine were licence-checked.
  SpeechOcean762 is the only one this project may use commercially. The
  single-corpus dependency is therefore a property of the world, not an omission
  in this plan, and it must be stated as a limitation wherever results are
  reported.
- **ISLE was the one purchasable exception and the owner declined it.** ELRA
  lists it at EUR 1,500 for non-members with a standing commercial agreement
  template, and its German and Italian speakers would have been maximally
  independent of SpeechOcean762's Mandarin. It also publishes its own
  inter-annotator agreement, roughly 55 percent on error identity and 70 percent
  on error localisation, which would have supplied a human ceiling from an
  independent team. Recorded as owner declined on cost grounds, reopenable only
  by a new explicit owner decision.
- **Speak and Improve 2025 is dead twice over.** Its only pronunciation layer is
  word level, its annotators were instructed to ignore accent, and its licence
  excludes any use forming part of a product that is sold.
- **The Speech Accessibility Project permits commercial use** under a signed
  agreement, which is rare, but supplies orthographic transcripts and perceptual
  scales rather than phone labels. It is irrelevant to item 22 and worth
  remembering for item 24.
- **espeak-ng has no Australian English at all**, Edinburgh's Combilex has no
  Australian variant, Unisyn's Australian accents are non-commercial, and the
  `australian-lexicon` repository is Australian spelling with machine-generated
  British pronunciations and no licence. OpenSLR, Hugging Face and Zenodo contain
  no Australian speech corpus and no second pronunciation-scoring resource.

### Checkpoint 22E credential handoff

Adam retains ownership, billing, legal acceptance and recovery control for
every account. Full technical access for this work means narrowly scoped API
credentials in the repository's gitignored `.env`; it does not mean an account
password, multifactor code, recovery code, personal payment credential or
permission to change billing.

Use these exact local variable names:

```dotenv
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=australiaeast
AZURE_SPEECH_ENDPOINT=

ELSA_API_TOKEN=

IFLYTEK_APP_ID=
IFLYTEK_API_KEY=
IFLYTEK_API_SECRET=
```

`AZURE_SPEECH_ENDPOINT` is optional unless the Azure resource or later SDK
requires its custom endpoint. No SoapBox credential is requested. No Hugging
Face token or other account is required for the currently public local
candidates.

For each external provider, Adam must also retain the provider's written
permission or contract covering this comparative benchmark, aggregate result
publication, the permitted audio sources, processing and storage region,
retention and deletion, model-training use and output ownership. The ELSA NDA
must be accepted by Adam, not by an agent.

For segmentation-free GOP, email `an address recorded privately` and copy
`an address recorded privately`. Ask whether the repository code and any relevant
checkpoint may be used, modified and redistributed in commercial research and
product engineering. This answer may make reproduction easier, but it does not
block the clean implementation from the CC BY 4.0 paper.

Send one combined UNSW enquiry to `an address recorded privately` and
`an address recorded privately`. Ask both whether the Speech Attributes adult and
Australian child checkpoints may be used commercially, what their training
corpora and derived-weight rights are, and whether an explicit model licence
can be added. In the same message, ask for AusKidTalk data-custodian access,
available phone-level annotations or models, permitted aggregate benchmarking,
commercial research, model training, derived-model deployment, retention and
redistribution terms. These local and acquisition paths require no API secret.

ZIPA requires an explicit licence for the exact model weights, not merely the
MIT licence on the code. POWSM and Wav2Vec2 CommonPhone require no owner
account, but their exact revisions, licences and training lineage must be
recorded before use. The child phoneme model requires an exact OpenRAIL and
training-data-rights review; public download is not permission by itself.

Written permissions and source evidence belong in the private gitignored
`.research_data/provider-permissions/` directory. Save the complete provider or
author response, its date, sender and the question it answered. Commit only a
non-secret manifest summary.

An agent may confirm that a variable exists and authenticate a harmless request
after explicit approval, but must never print a secret. Missing permission,
unknown provenance or an unavailable credential blocks only that lane; it does
not lower the benchmark gates or silently substitute another system.

### Mozilla Data Collective agent handoff

- The local gitignored `.env` uses `MDC_API_KEY`. An agent may check that the
  variable exists but must never print, log, commit or copy its value into an
  artifact.
- Dataset terms must be accepted through the Mozilla Data Collective website
  before API download. The API cannot perform that legal acceptance.
- Use the official `datacollective` Python client only as pinned acquisition
  tooling. It is a beta client, not a production pipeline dependency.
- Resolve the canonical current Australian English dataset page and dataset ID
  at acquisition time. Record its metadata, API checksum, independently
  calculated archive checksum and accepted terms before extraction.
- Download only after checkpoint 22B receives explicit approval, into private
  gitignored corpus storage. Never commit or rehost the archive.

There is no GPU rental in the approved plan. Local inference runs sequentially
first. A cloud GPU requires a later owner decision only if measured local speed
or memory makes the agreed evaluation impractical.

### What to ask Macquarie

Request a small machine-readable sample and written answers to these questions:

1. What is the price for research now and a future commercial product?
2. Does the sample include every standard and variant Australian pronunciation,
   IPA, regional labels, audio identifiers and version information?
3. May the repository store a versioned subset for its controlled research word
   pack?
4. May the software transform Macquarie IPA into an internal feature and phone
   representation?
5. May derived task packs and model inputs be used commercially without
   redistributing the original database or audio?
6. What attribution, caching, update and deletion conditions apply?

### What to ask the ANDOSL custodian

Request a small machine-readable sample and written answers to these questions:

1. Who currently controls access and licensing for the recordings and every
   annotation layer?
2. May the data be used for commercial research, acoustic-model training and
   evaluation?
3. May trained models, derived features and aggregate benchmark results be
   retained and deployed without redistributing the source recordings or
   annotations?
4. Which speaker, region, accent-group and recording-condition metadata may be
   used for participant-exclusive evaluation and fairness analysis?
5. May approved cloud providers receive selected clips, or must every use stay
   local?
6. What attribution, storage, security, deletion and licence-termination duties
   apply?

If suitable rights cannot be obtained, commission an equivalent blinded
Australian set with expert phone labels. ANDOSL is preferred evidence, not an
absolute dependency on completing Phase C.

Do not treat a normal website or app subscription as permission to copy data
into the repository. The separate data licence must explicitly allow the
planned use.

### Why TIMIT is rejected and what replaces it

The Academic Torrents copy does not include a dataset licence. A file being
downloadable does not grant permission to use it. The official LDC non-member
agreement is for non-commercial work and requires a for-profit user to obtain
the appropriate membership and pay applicable fees before a resulting
commercial product is released. Current standard for-profit membership is far
beyond the value TIMIT would add here.

Do not download or retain the torrent. TIMIT did not contain the target
speech-sound relation truth item 22 needs anyway. Its useful jobs are replaced
by:

- Acted Clear Speech for a tiny hand-corrected phone-boundary fixture;
- Common Phone for broad automatic phone and timing engineering; and
- Common Voice Australian English and small LibriSpeech subsets for robustness
  and false-concern testing.

### Copy and paste request drafts

Macquarie request, through its contact form or `an address recorded privately`:

```text
Subject: Australian English Pronunciation Data licensing enquiry

Hello,

I am developing a speech measurement research system and would like to assess
the Macquarie Dictionary Australian English Pronunciation Data for a future
commercial product.

Could you please provide a small machine-readable sample and a quote for
research and commercial licensing? I would also like to confirm whether the
licence can permit us to store a versioned subset for a controlled word task,
transform the supplied IPA into an internal phone and feature representation,
use derived task packs and model inputs commercially without redistributing the
original database or audio, and retain the required source and version
provenance.

Could the sample show standard and variant pronunciations, IPA, any regional
labels, audio identifiers and version information? Please also explain the
attribution, caching, update and deletion conditions.

We are not requesting custom recordings or clinical advice at this stage.

Thank you,
Adam
```

## Evidence sources and their jobs

No single corpus is allowed to answer every question.

| Evidence source | Allowed job | Forbidden interpretation |
|---|---|---|
| [SpeechOcean762 v1.2.0](https://www.openslr.org/101/), CC BY 4.0 | Primary participant-exclusive development, tuning and held-out benchmark for explicit expert phone relations. Retain all five original expert records and disagreements. | Its Mandarin-first-language population, single expected pronunciation and accent/native-likeness rubric cannot define acceptable English or Australian truth. Scalar scores are not error labels. |
| [Acted Clear Speech](https://datashare.ed.ac.uk/handle/10283/343), CC BY 3.0 | Tiny exact regression fixture using its hand-corrected phone boundaries across five speaking conditions. | One British male and 125 clips cannot estimate population accuracy, accent performance or speech-sound relation accuracy. |
| [Common Phone 1.0](https://zenodo.org/records/5846137), CC0 | Broad phone-recogniser, parser, timing, device and repeatability engineering using its speaker-exclusive English splits. | Its IPA TextGrids were created automatically from prompted text. They are not human truth and cannot validate substitutions, deletions, insertions or accepted variants. |
| [Common Voice Australian English](https://mozilladatacollective.com/), CC0 | Australian English accent, microphone, ASR-disagreement, abstention and false-concern stress tests using the latest available scripted-speech release. | A validated sentence is not phone truth. Accent is self-reported, and this set does not supply lexical Australian variants or phone timestamps. |
| [LibriSpeech](https://www.openslr.org/12), CC BY 4.0 | Small official development or test subsets only when needed for scale, runtime, determinism and ordinary read-speech regression. | Audiobook transcripts are not phone-production truth and its population cannot establish Australian or product-task performance. |
| Macquarie pronunciation data, if licensed | Authoritative Australian word-specific reference variants and Australian reference audio. | A dictionary entry does not prove what one participant produced and does not cover every world English variety. |
| ANDOSL, if licensed, or an equivalent newly collected expert set | Australian phone, phoneme and word evidence for checking what speakers produced across accepted Australian accent variation. | Rights must cover commercial research and derived models. Existing annotations still require an independent audit, participant-exclusive splits and current expert review. |
| Adam's controlled recordings | Functional integration, repeated-run, microphone and deliberately spoken contrast checks. | They cannot establish accuracy, fairness or population performance. |
| TIMIT, L2-ARCTIC and selected TalkBank resources | Manifested only as rejected, licence-blocked or rights-pending sources unless their exact commercial rights change. | Availability on a mirror, an access form or an academic-use licence is not commercial permission. Restricted data cannot enter the repository or benchmark. |

The initial stack stays deliberately small. VCTK may be added later if a
controlled same-text multi-accent regression is still missing. EdAcc or
OpenSLR83 may be added later if spontaneous or regional English ASR stress
testing remains under-covered and their share-alike duties are acceptable.
VoxCommunis currently adds no English corpus, and CMU ARCTIC is excluded until
the licence of every selected voice is verified. None should be downloaded just
because it is available; a new source must fill a measured evidence gap.

### Manifest, lineage and independence rules

Every corpus receives a machine-readable manifest containing:

- canonical source URL, release or commit pin, archive checksum, retrieval date,
  citation, licence identifier and canonical licence URL;
- a retained record of the accepted access terms, attribution duties,
  redistribution limits, account-termination or deletion duties and any
  prohibition on reidentification;
- access state, commercial-use state, permitted jobs, forbidden jobs, source
  population, annotation construct and known limitations;
- private local storage location plus participant and clip identifiers; and
- deterministic participant-exclusive development, tuning and frozen held-out
  splits, including separate reported strata such as child and adult where the
  source supplies them.

Raw speech data is gitignored and never committed. Exact ages and unnecessary
personal metadata are not copied into committed manifests.

The manifest also records source lineage and known candidate-model training
overlap. Common Phone 1.0 was derived from Common Voice 7, so those sources are
not independent evidence. Duplicate speakers or clips may never cross splits,
including across known related sources. A benchmark cannot be described as
independent accuracy evidence when the evaluated model was trained on that
benchmark. Automatic alignments, human boundaries, expert phone relations and
sentence validation remain separate truth classes and are never pooled into
one accuracy number.

## Candidate systems

### Checkpoint 22D local baseline components

1. Montreal Forced Aligner locates expected word and phone intervals and
   reports alignment fit. It never verifies that the expected phone occurred.
2. PhoneticXEUS supplies an unconstrained IPA phone sequence, frame-level
   evidence and alternatives. It is a candidate model, not reference truth.
3. PanPhon maps IPA observations into explicit articulatory features such as
   place, manner and voicing. It compares symbols but does not listen to audio.
4. WhisperX remains a separate word-recognition baseline. Its transcript is not
   lexical intent or phone truth.

Model identifiers, checksums, licences, phone inventories, mapping tables,
settings and raw outputs must be versioned. Models run sequentially on the
current machine. The feasibility spike measures installation risk, peak memory,
runtime and deterministic repeatability before the architecture is committed.

### Approved role-based comparison

Checkpoint 22E does not compare interchangeable providers. Each role below has
a specific evidence purpose and a reason for its assignment:

1. **Core local repair, segmentation-free GOP:** this directly attacks 22D's
   forced-boundary weakness and can be implemented label-blind from a CC BY 4.0
   method on the already-screened Apache-2.0 Meta phone model. The unlicensed
   author repository and SpeechOcean-trained GOPT head are excluded.
2. **Core local free-phone comparator, POWSM:** its released weights have an
   explicit CC BY 4.0 licence and documented ESPnet packaging, and its
   unconstrained phone sequence tests a different architecture from
   expected-phone-conditioned GOP. Core means it must receive a fair
   feasibility attempt; it does not mean selected or true.
3. **Core external score comparator, Azure:** it has the strongest verified
   operational, regional and privacy position and supports `en-AU`, but
   Australian output is score evidence, not the actual produced phone.
   `en-US` named and N-best phones are a separate dialect-limited evidence
   class, never a substitute for `en-AU`.
4. **Conditional external exact-substitution candidate, ELSA:** its documented
   `phoneme_error_arpabet` field is the strongest produced-phone field found,
   but NDA access, publication permission, region, retention, training use and
   deletion/insertion semantics must be confirmed from a real response and
   written terms first.
5. **Experimental public-corpus comparator, iFLYTEK: declined by Adam on
   2026-07-25.** It cheaply flags error types and exposes boundaries, but its
   English response does not name the produced replacement phone and its
   documented child/adult switch is not available for the needed English task.
   Adam declined the lane before checkpoint 22E3 sent any audio, on
   reputational and unauditable privacy grounds. The account, free quota and
   verified credential remain, so the lane can be reopened, but only by a new
   explicit owner decision. Until then it receives no audio of any kind.
6. **Conditional local free-phone candidate, ZIPA:** its code is MIT and ONNX
   makes local CPU feasibility promising, but the separately distributed model
   weights have no explicit licence or adequate provenance. ZIPA is
   conditional while POWSM is core specifically because POWSM licenses the
   released weights under CC BY 4.0; ZIPA currently licenses only code.
7. **Supporting-only local comparator, Wav2Vec2 CommonPhone:** CC0 weights and
   safetensors make it easy to inspect safely, but it was trained on Common
   Phone, derived from Common Voice. It cannot provide independent selection
   evidence on this project's Common Phone or Australian Common Voice sources.
8. **Research-only articulatory candidate, UNSW Speech Attributes:** its
   attribute outputs could explain place, manner, voicing and vowel-feature
   differences beyond a phone score, but the actual adult and Australian child
   checkpoints lack a model licence and training statement and the published
   method touches restricted or non-commercial corpora.
9. **Conditional child feasibility candidate, `wav2vec_children_ASR`:** the
   [model card explicitly reports an OpenRAIL licence](https://huggingface.co/lijialudew/wav2vec_children_ASR)
   and MyST and Providence fine-tuning. OpenRAIL is not an unrestricted
   commercial grant, derived-data rights remain unresolved, and the published
   use is child phoneme representation and vocalization classification rather
   than validated pronunciation assessment.
10. **Australian child acquisition and collaboration, AusKidTalk:** it covers
    Australian children and typical and disordered speech, but current
    data-custodian access is research-only and the current release describes
    orthographic rather than completed phone-level annotation. It informs a
    future child evidence base; it is not a ready detector.
11. **Conditional prompt-target support, Bookbot Australian G2P:** it can
    propose Australian broad-IPA targets for 22F and is Apache 2.0, but its
    model card does not document the training and evaluation datasets
    sufficiently. It is not an acoustic scorer and cannot define accepted
    variants without independent Australian reference validation.
12. **Rejected-unobtainable, SoapBox:** there is no dependable public path to a
    new developer contract after the Curriculum Associates acquisition, and
    the earlier immediate-deletion assumption conflicts with documented
    default product-improvement logging. No account or audio is requested.

SpeechAce remains a conditional reserve because its custom-phone and
sound-most-like fields match the task, but it requires a written waiver from
its comparative-evaluation and publication restrictions. SpeechSuper remains
rejected because its current terms prohibit the planned comparison. Alibaba,
Tencent, Language Confidence, Chivox, ETS and Pearson remain documented
reserves or rejects rather than active lanes.

A lane proceeds only when its provider terms, corpus rights, privacy, model
licence, training provenance and source independence permit the exact declared
role. Adam's approval cannot waive a third party's rights.

The comparison must:

1. use a fixed participant-exclusive public-corpus subset;
2. predeclare fields, phone mappings, metrics and failure handling;
3. retain raw responses, request settings, service version when exposed, date
   and region;
4. compare exact relation precision, recall, false concerns, abstention and
   coverage against existing expert records;
5. keep every locale and child or adult setting separate rather than choosing
   whichever gives a convenient score;
6. ignore overall pronunciation, fluency, prosody and native-likeness scores;
7. select or retain a lane only if it passes the frozen development and tuning
   gates or has a clearly bounded supporting or research-only role;
8. remain reproducible from cached responses if a provider later changes.

Agreement among APIs is not truth. A provider may become optional supporting
evidence, but the developer artifact must remain usable when every remote
provider is unavailable. No personal recording is sent remotely without a
separate privacy and consent decision.

### Model lineage and independence manifest rules

Every model and every evidence source must have a machine-readable manifest
entry with:

- exact model identifier, immutable revision, file hashes and serialization
  format;
- code licence, exact model-weight licence and evidence for both;
- training, fine-tuning, validation and reported test datasets;
- parent models, derived datasets and synthetic or G2P label sources;
- known or possible participant, recording and source-corpus overlap;
- `independent`, `supporting_only`, `blocked` or `unknown` status for every
  benchmark source;
- permitted role and prohibited claims; and
- the dated evidence that supports each field.

Unknown weight licensing, unknown training provenance or unknown overlap fails
closed. A code-repository licence does not automatically license separately
hosted weights. A model card tag does not erase restrictions inherited from
training data.

The Wav2Vec2 CommonPhone entry must state explicitly that the model was trained
on Common Phone and that Common Phone derives from Common Voice. Therefore:

- this project's Common Phone evidence is non-independent;
- this project's Australian Common Voice evidence is also non-independent;
- neither source may count toward selection gates, a headline result or
  corroboration of this model; and
- the model may advance only on independently manifested evidence sources.

POWSM and ZIPA both derive from the IPAPack++ family and G2P-derived phone
labels. That relationship must be recorded so agreement between them is not
treated as independent confirmation. POWSM remains core because its exact
released weights have an explicit licence; ZIPA remains conditional because
its exact weights do not.

### Negative findings and expectation ceiling

The following are recorded rejections, not forgotten candidates:

- Audio-native large multimodal models are not phone-level assessors for this
  task. A [2025 GPT-4o study](https://arxiv.org/abs/2503.11229) left about
  48 percent of phoneme items unscored and reported inconsistent behavior
  across runs. No current Gemini pronunciation-assessment feature supplies the
  required exact phone relation.
- Google Cloud's earlier pronunciation-assessment preview did not become a
  current supported phone-level product. The
  [current Google Cloud Speech-to-Text release notes](https://cloud.google.com/speech-to-text/docs/release-notes)
  document transcription, adaptation and timestamps rather than the required
  expected-to-produced phone relation.
- [AWS Transcribe](https://docs.aws.amazon.com/transcribe/latest/dg/what-is.html)
  and OpenAI speech services do not expose the required phone-level
  pronunciation relation. General ASR, timestamps or confidence are not
  substitutes.
- Torchaudio MMS forced-alignment weights are CC BY-NC and Allosaurus is
  GPL-3.0, so they do not fit this proprietary commercial engineering path.
- A checkpoint trained on L2-ARCTIC, TIMIT or another restricted source is
  blocked unless the exact commercial and derived-model rights are proved.

SpeechOcean762 was scored by multiple experts, and
[later benchmark literature](https://arxiv.org/abs/2601.01745) reports
phone-level expert consistency within the roughly 0.55 to 0.65 correlation
band. This is a practical expectation ceiling and a warning against pretending
that one API can reveal objective phonetic truth. It is not a replacement for
the project's event-level gates.

It is expected and acceptable that no candidate may pass all frozen
development and tuning requirements. `no_selection` is a complete, legitimate
and publishable 22E outcome when every lane's evidence and rejection reason are
recorded. `research_only` and `supporting_only` are also legitimate outcomes.
Precision, Wilson lower bound, false-concern, recall and true-positive gates
remain unchanged; none may be lowered to force a winner.

## Initial measurable scope

The first engineering release supports only controlled, isolated English words
with known prompts and acceptable audio.

Included research opportunities:

- conservative consonant substitutions;
- conservative consonant deletions;
- conservative consonant insertions;
- timestamps and source intervals;
- alternative candidate phones and feature relations;
- ASR-only disagreement;
- candidate-system conflict;
- known reference variant;
- insufficient evidence; and
- unavailable with explicit reasons.

Explicitly unavailable in the first release:

- vowel and diphthong judgements;
- distortions requiring narrow IPA or clinical auditory judgement;
- post-vocalic `r` and other strongly variety-sensitive opportunities;
- flaps, glottal variants, reductions and unresolved allophones;
- spontaneous and connected-speech target relations;
- named articulation or phonological processes;
- developmental expectations;
- disorder, cause, severity, treatment or improvement; and
- a pronunciation or communication score.

Excluded capability is reported as `unsupported`, never as normal, correct or
zero.

## Artifact and uncertainty design

The planned developer artifact is `speech_sound_candidates.json`. It is
produced only by an explicit research command with a versioned prompt pack. It
is not a normal pipeline artifact in the first release.

Each opportunity retains:

- corpus or participant, session, attempt, trial and stimulus identifiers;
- intended-word source and every reference variant considered;
- timestamps, audio quality and exclusion reasons;
- raw ASR, alignment, local phone-recognition and optional provider evidence;
- expected and alternative phones with explicit mapping provenance;
- candidate-system agreement and conflict without converting agreement to
  truth;
- candidate state and all alternative explanations;
- uncertainty and abstention reason;
- model, dictionary, corpus, API and code versions; and
- downstream exclusion flags.

Allowed automatic states are:

- `possible_relation_candidate`;
- `asr_only_disagreement`;
- `candidate_system_conflict`;
- `known_reference_variant`;
- `insufficient_evidence`;
- `unsupported`; and
- `unavailable`.

The word `error` is not an automatic state.

## Repeated-relation evidence

Item 22 must build the data structure needed for future pattern work, but it
will not invent named clinical patterns.

A research summary may group the same feature-level candidate relation across
distinct words, positions, contexts and sessions. It must expose every support
and opportunity count. The minimum evidence rule is selected on development
and tuning speakers, frozen before held-out evaluation and documented with its
precision, false-concern and abstention trade-off. It cannot be chosen from
Adam's recordings or the final evaluation speakers.

The output is a `repeated_relation_candidate`, not a phonological-process label
and not a disorder. No pattern output enters coaching or personal progress.

## Ordered implementation checkpoints

Only one checkpoint is changed and reviewed at a time. Adam commits each
completed checkpoint before the next begins.

### 22A. Amend the guarded contract

- Create a new versioned contract that separates developer-only candidate
  engineering from scientific and product release.
- Keep every ASR, language-variety, uncertainty and downstream prohibition.
- Add explicit source, licence, provider, task and artifact states.
- Update validators and mutation tests before any extractor exists.

Acceptance: the new contract validates, unsafe mutations fail, the old contract
remains historically understandable, and no candidate code or task is active.

### 22B. Add corpus and licence manifests

- Add schemas and validators for the complete manifest, terms, lineage,
  independence, privacy and participant-exclusive split rules above.
- Create manifests for SpeechOcean762 v1.2.0, Acted Clear Speech, Common Phone
  1.0 and the current Common Voice Australian English release. Add only the
  small official LibriSpeech subsets that a declared engineering test needs.
- Preserve each source's original split as provenance, then create deterministic
  participant-exclusive development, tuning and frozen held-out splits for this
  research. Do not pool child and adult SpeechOcean results.
- Audit the real annotation fields before accepting a source's role. For
  SpeechOcean, retain all five reviewer phone records and explicit phone
  relations, preserve disagreement, and reject direct import of its accent or
  native-likeness judgements.
- Record Common Phone and Common Voice lineage, detect clip and participant
  overlap, and record known training overlap for every candidate model.
- Manifest Macquarie as pending; TIMIT as rejected; and L2-ARCTIC and TalkBank
  as blocked unless written rights later change.
- Create version 1.2 as the successor to the active source register so the new
  source states are authoritative. Keep version 1.1 as an unchanged historical
  snapshot, point the validator to version 1.2, and add mutation tests without
  weakening any scientific or product-release gate.

Acceptance: every permitted source has verified canonical terms and checksums;
every annotation is assigned only a role it can support; no participant or
duplicate clip crosses splits; related or model-seen data cannot be called
independent; restricted data cannot be committed, uploaded or used for a
forbidden job; and an unknown licence, access or lineage state fails closed.
The version 1.2 contract validates, unsafe source-state mutations fail, and
version 1.1 remains unchanged.

Completion evidence on 2026-07-21: all five permitted public packages were
downloaded from their canonical sources into gitignored storage and verified;
real metadata and annotation fields were audited; deterministic private split
indexes were frozen; and Macquarie, TIMIT, L2-ARCTIC and TalkBank were
manifested without acquiring restricted data. The Common Phone lineage audit
found 264 participant identifiers and 521 clip identifiers also present in the
current Australian Common Voice release. All 264 speakers were excluded from
Common Phone use, leaving 4,506 development, 740 threshold-tuning and 751
held-out speakers. Contract version 1.2, both manifest schemas, private-evidence
validation and unsafe-mutation tests pass. No task, extractor or artifact was
activated.

### 22C. Run the local feasibility spike

- Install and pin Montreal Forced Aligner, PhoneticXEUS and PanPhon in an
  isolated research environment.
- Measure CPU or MPS runtime, peak memory, model download size and repeatability
  on short clips from the manifested SpeechOcean, Acted Clear, Common Phone and
  Australian Common Voice sources, plus owner-controlled integration clips.
- Freeze phone inventory and IPA mapping decisions only after inspecting real
  outputs.

Acceptance: the selected local stack fits this machine, produces versioned raw
outputs and repeats exactly enough for the declared evidence. If it fails, the
checkpoint stops for a method decision; it does not rent a GPU automatically.

Completion evidence on 2026-07-21: exact isolated macOS ARM environments pin
MFA 3.4.1, PhoneticXEUS revision
`8d83dee94817a07dc150f87d08f7e0ee01bdb66d` and PanPhon 0.22.2. A fixed sample
contains 13 short clips selected without labels or outputs from frozen
development participants, a timing fixture and one owner-controlled integration
recording. No held-out participant or accuracy label was inspected. The raw
manifest, audio, transcripts, model outputs and logs remain gitignored.

MFA produced 36 fresh alignments for 12 transcript-known clips. Canonical word
and phone intervals were exact across all three repeats. Median alignment time
was 15.928807 seconds, real-time factor was 3.642981, maximum resident set was
987,414,528 bytes and no swap occurred. Three clips contained an unknown phone
interval and one contained an unlabeled export interval; both states are
preserved. The pinned English US ARPA model is General American read-speech
timing evidence conditioned on expected text. It cannot establish produced
phones, Australian variants or correctness. The broader global English MFA
model was rejected because its declared training sources include
non-commercial corpora under terms incompatible with this project's commercial
engineering role.

PhoneticXEUS ran 130 warm MPS inferences over all 13 clips and three fresh MPS
processes. Raw logits, frame paths and collapsed phone paths were exact within
and across those processes. MPS inference real-time factor was 0.152209 and its
largest measured peak memory footprint was 4,856,189,680 bytes. Fifteen
single-threaded CPU inferences across a five-source subset repeated exactly;
CPU and MPS frame paths and collapsed tokens agreed on every comparison clip,
while maximum raw-logit drift was 0.0001792908. The model exposes a fixed
424-phone inventory plus four special tokens, greedy tokens and contextual CTC
logits. It does not expose official phone timestamps, calibrated confidence or
sequence alternatives. Its model-card licence metadata says Apache 2.0, but the
pinned snapshot lacks a complete licence and training-data provenance bundle,
and several available corpora overlap its model lineage. Product and commercial
release use therefore remains blocked pending a separate provenance decision.

All 55 distinct PhoneticXEUS phone tokens observed in this sample mapped to one
exact atomic PanPhon segment after NFD normalization. Unknown, composite and
special tokens fail closed. Weighted feature distance is prohibited because
PanPhon 0.22.2 ships 24 features but an incompatible 22-entry weight file.
Contract version 1.3 records only this local feasibility advance. The aggregate
report is `local-feasibility-v1.0.0.json`; exact environments are under
`environments/`. No task, candidate extractor, artifact, system selection,
accuracy claim, coaching, progress, screening or diagnosis was created.

The required normal two-speaker conversation pipeline also completed in an
isolated output directory without `--me`. The existing evaluator failed closed
after claim-ledger semantic validation errors, while objective artifacts and
verification remained available. The run produced no speech-sound artifact or
master field, and the before-and-after hashes of `history.json` and
`progress.md` were identical.

### 22D. Build the benchmark harness

- Parse existing expert labels without rewriting them as product truth.
- If ANDOSL rights are obtained, add it as high-value Australian phone-labelled
  evidence. Otherwise reserve the same role for an equivalent independently
  and expertly labelled Australian set.
- Run local systems on the same frozen clips.
- Calculate relation-level precision, recall, F1, false concerns, abstention,
  coverage, repeatability and uncertainty only against supported reference
  classes. Report human relations, hand-corrected boundaries, automatic
  alignments and sentence-level robustness separately.
- Report SpeechOcean reviewer agreement and adult and child results separately.
  Mark unsupported or disputed relations unscorable rather than forcing a
  binary answer.

Acceptance: development and tuning are separate from held-out speakers, all
denominators are visible, and the final set remains untouched.

Completion evidence on 2026-07-23: the frozen benchmark contains 565 clips
selected without labels or candidate outputs. SpeechOcean contributes 480 clips
from 16 development and 8 tuning participants, stratified by source adult or
child group and source sex. Acted Clear contributes 25 one-speaker timing
fixtures. Common Phone and Australian Common Voice each contribute 20
development and 10 tuning participants with one clip each. The private sample
manifest is checksum pinned. It contains no held-out participant, and the
preparation and report validators reject held-out access or result fields.

The harness retains all five SpeechOcean expert records. It parses plain,
braced, parenthesised and inserted-phone notation without collapsing disputed
states, requires four matching reviewers for a scorable target relation, keeps
explicit insertions separate, and leaves vowels, diphthongs, post-vocalic R,
unresolved allophones and disputed labels unscorable. It reports development
and tuning separately and splits source adults from children. Raw labels,
audio, logits, alignments and row-level evidence remain private.

The frozen greedy PhoneticXEUS path repeated exactly on all 565 clips, but it
was not selected. Relation precision was 0.170520 for development adults,
0.004762 for development children, 0.096774 for tuning adults and 0.020942 for
tuning children. Its corresponding false-positive counts were 574, 418, 308
and 187. Recall was high, but child recall had only two and four positive
reference opportunities, and the false-concern burden makes this path unsafe.
Only five of 46 aggregate expert substitutions across all four partitions were
exact supporting relation matches.

MFA completed the same frozen 109-clip cross-system subset and repeated one
Acted Clear clip in each speaking condition exactly. On the one-speaker Acted
Clear fixture, 357 of 363 clean consonant reference labels matched; matched
start and end boundary median absolute errors were 0.007206 and 0.006877
seconds. This cannot establish phone-relation or population accuracy. Common
Phone and Common Voice results remain candidate-system disagreement only, not
phone truth. No weighted PanPhon distance was used.

`benchmark-contract-v1.0.0.json`, `benchmark-phone-map-v1.0.0.json` and
`local-benchmark-v1.0.0.json` freeze the rules, mapping and aggregate result.
The conservative repair then ran label-blind expected-phone CTC evidence over
all 480 relation clips, with two exact inference repeats per clip. Numeric and
contextual PhoneticXEUS calibration reached development grouped average
precision of 0.327120 and 0.450154. A frozen repeated-relation filter tested 600
configurations and still did not pass every gate.

A separately screened full-precision ONNX conversion of Meta's
`facebook/wav2vec2-lv-60-espeak-cv-ft` model ran the same 480 clips and 960
inference passes. Its contextual calibration reached development grouped
average precision of 0.580833. At the closest exact operating point, tuning
passed all five gates with 15 true positives and 5 false positives.
Development passed four of five with 25 true positives and 7 false positives;
recall was 0.183824 against the frozen 0.200 minimum. All 2,957 distinct score
boundaries were evaluated, and none passed all five gates on both partitions.
The gates were not lowered, the held-out set stayed sealed, and no system or
threshold was selected.

Contract version 1.5 binds the unchanged version 1.4 baseline and the safe
aggregate repair report. No provider, task, prompt pack, extractor, candidate
artifact, coaching output, progress metric or release gate was activated.

The required normal two-speaker conversation pipeline completed in an isolated
output directory without `--me`. The final post-repair run completed in 446
seconds. Every objective measurement stage passed. The evaluator safely
degraded after two semantic validation failures, leaving objective artifacts
intact and coaching unavailable. The run produced no speech-sound artifact or
master field, and the before-and-after hashes of `history.json` and
`progress.md` were identical.

### 22E. Run the staged role-based comparison

Checkpoint 22E is divided into five separately reviewed and committed
subcheckpoints. None may inspect the held-out set.

#### 22E1. Access, rights and privacy preflight

- Verify each account and credential without printing a secret.
- Obtain written comparative-benchmark and aggregate-publication permission
  wherever public terms do not already permit it.
- Record processing and storage region, audio and result retention, deletion,
  training use, subprocessors, output ownership, model-change behavior and
  exact phone-field semantics.
- Confirm that each selected corpus may be sent to each named provider.
- Email the NTNU authors about repository code and checkpoint licensing, but
  do not make their reply a blocker for the independent segmentation-free GOP
  implementation.
- Confirm the exact POWSM revision, licence and IPAPack++ lineage.
- Treat ZIPA as blocked until the exact model weights have a usable licence and
  provenance, regardless of the code repository's MIT licence.
- Give Wav2Vec2 CommonPhone source-specific independence states that bar Common
  Phone and Australian Common Voice from its selection evidence.
- Send the combined UNSW enquiry covering Speech Attributes checkpoint
  licensing and training provenance plus AusKidTalk access and rights.
- Resolve the child model's exact OpenRAIL conditions and the derived-weight
  rights of MyST and Providence before downloading or loading it.
- Verify Bookbot Australian G2P provenance before it may propose 22F targets.
- Create provider, model and evidence-source registers whose unknown or
  prohibited state fails closed.

Acceptance: every role in the approved register is `ready`, `conditional`,
`blocked`, `supporting_only`, `research_only` or `rejected` with its specific
reason and written evidence. Source overlap is explicit. No audio has left the
machine and no new large candidate checkpoint has been loaded.

#### 22E2. Local research feasibility

- Independently implement the segmentation-free GOP equations from the
  CC BY 4.0 paper on the pinned
  `facebook/wav2vec2-lv-60-espeak-cv-ft` phone model. Do not copy the
  unlicensed repository code or use its SpeechOcean-trained score-regression
  layers.
- Pin POWSM's exact revision in an isolated environment and audit its model
  card, package, IPAPack++ lineage and serialization before loading.
- Admit ZIPA only if 22E1 resolved the exact weight licence and provenance.
- Admit Wav2Vec2 CommonPhone only as supporting evidence on sources manifested
  independent of Common Phone and Common Voice.
- Admit UNSW Speech Attributes and the child phoneme model only if 22E1
  resolved their exact checkpoint and derived-data rights. Security-review
  each serialization before loading.
- Use only non-held-out, label-blind clips.
- Measure output shape, phone or attribute mapping, repeatability, runtime,
  peak memory and safe failure on this Mac.
- Keep expected-phone scores, unconstrained phone recognition and UNSW
  articulatory explanations as separate evidence classes.

Acceptance: every admitted local candidate is reproducible, safely loadable,
legally usable and lineage-manifested for its declared role, or it is blocked
or rejected without weakening the plan. A failed core feasibility attempt is
reported, not silently replaced.

Completion evidence on 2026-07-24: the segmentation-free GOP equations were
independently implemented in `sfgop.py` from the CC BY 4.0 paper over the
frozen Meta ONNX phone model, with no code from the unlicensed repository and
no SpeechOcean-trained head. The junction computation was proven equal to
brute-force CTC path enumeration at nine decimal places in unit tests,
including repeated-label, multi-token, whole-sequence and deletion edge
cases. On 24 label-blind development clips it scored 283 consonant targets
and left 184 unscorable, with exact two-repeat outputs, zero
forward-backward and junction self-check differences, real-time factor
1.400371 for two repeats and peak memory 1,799,569,408 bytes. Its outputs
include per-target GOP-AF and GOP-AF-SD log posteriors, deletion posteriors
and top alternative candidate phones. POWSM revision 21ffa410 was pinned in
an isolated environment; its checkpoint pickle was audited opcode by opcode
before load and contained only safe tensor-reconstruction globals; four-clip
inference with beam size one repeated exactly at real-time factor 1.356063
for two repeats with peak memory 3,068,035,072 bytes, and the register lane
was promoted to ready. Wav2Vec2 CommonPhone was pinned using safetensors
only, its published CC0 harness architecture and IPA table were adapted with
recorded provenance, and four-clip inference repeated exactly at real-time
factor 0.369054 for two repeats with peak memory 2,945,826,816 bytes; its
supporting-only role and non-independence from Common Phone and Australian
Common Voice remain enforced by the register. ZIPA, UNSW Speech Attributes
and the child phoneme model were not downloaded or run because their licence
or rights blockers remain unresolved. The committed aggregate report is
`local-research-feasibility-v1.0.0.json`; raw outputs remain private. No
audio left the machine, no held-out participant was touched, no accuracy was
measured and no system was selected.

The required normal two-speaker conversation pipeline acceptance run
completed in an isolated output directory without `--me` in 357 seconds with
exit code zero. Every objective measurement stage passed, and the evaluator
verified all 25 claims with zero claim issues and all seven legacy numeric
checks traced to the data, an improvement over the degraded evaluator states
recorded at 22C and 22D. The run produced no speech-sound artifact or master
field, and the before and after hashes of `history.json` and `progress.md`
were identical.

#### 22E3. External schema smoke tests

- Use only the smallest development-only clips that corpus and provider terms
  permit.
- Confirm Azure `en-AU` scores and word miscues separately from Azure `en-US`
  named and N-best spoken phones.
- Confirm ELSA phone timing, decisions and `phoneme_error_arpabet` semantics.
  Require at least one real substitution response and documented deletion and
  insertion behavior before treating it as exact-relation evidence.
- Confirm iFLYTEK phone boundaries and missed, added, repeated and replaced
  flags without assuming that a replacement flag names the observed phone.
  Send public-corpus audio only.
- Record SoapBox as `rejected_unobtainable`; do not seek credentials or send
  audio.
- Repeat identical requests where terms permit and record service date, region,
  settings, response schema and version when exposed.

Acceptance: only lanes whose real response fields support a predeclared
comparison advance. Marketing claims and overall scores cannot qualify a lane.

Completion evidence on 2026-07-25: the separate corpus to provider transfer
review that every corpus manifest demands was written first, in
`corpus_manifests/provider-transfer-review-v1.0.0.json`. It permits four public
corpora to reach Azure, records Australian Common Voice as permanently barred
because its manifest blocks provider transfer, and records ELSA and iFLYTEK as
not permitted. `audio_permitted` in the provider register now consults that
review, so being an eligible source is necessary but no longer sufficient, and
a lane that gains an eligible source without a written decision fails closed.
Adam declined the iFLYTEK lane on reputational and unauditable privacy grounds
before implementation began, so it moved to `owner_declined` with a blocked
audio policy and no eligible sources. ELSA received no audio and stays
conditional; an access, permissions and semantics enquiry was drafted for Adam
to send. SoapBox received no contact and no credential request.

The predeclared contract is `external-smoke-contract-v1.0.0.json`, written
before any request. It bound the sample to the frozen expected-only manifest
from checkpoint 22D, so selection was label blind, and it excluded child
strata, tuning clips and held-out clips under data minimisation. Five
development adult SpeechOcean762 clips were sent twice to Azure `en-AU` and
twice to `en-US`, twenty requests in total, all returning HTTP 200 from the
australiaeast resource.

Both locales repeated exactly: every score and phone name was identical across
repeats with zero tolerance, excluding only the per request identifier. The
two locales returned different utterance accuracy scores on the same audio,
with a maximum absolute difference of 27 points, which confirms the locale
parameter selects a genuinely different model and hardens the rule that
locales are never pooled.

The decisive finding is that `en-AU` emits `Phoneme`,
`NBestPhonemes[].Phoneme` and `Syllables[].Syllable` as empty strings beside
real accuracy scores. The keys exist, so a parser checking key presence rather
than phone identity would have silently manufactured empty produced phones for
Australian English. `en-AU` therefore advanced as `score_only`. `en-US` with
`PhonemeAlphabet` IPA returned named expected phones, five named and scored
candidate phones per position, syllable groups with graphemes, and word error
types including both `Omission` and `Insertion`, so it advanced as
`exact_relation_capable`. `PhonemeAlphabet` and `NBestPhonemeCount` are
honoured over the REST short audio header even though the REST reference does
not document them.

The safe aggregate report is `external-schema-smoke-v1.0.0.json`; raw
responses stay private. No accuracy was measured, no expert label was read, no
held-out participant was touched, no system was selected and no threshold was
set. The practical consequence for checkpoint 22E4 is that Azure cannot supply
exact relation evidence in the Australian variety at all, only in a General
American model, which must be recorded as a limitation rather than worked
around.

The required normal two-speaker conversation pipeline acceptance run completed
in an isolated output directory without `--me`, exit code zero, with 457
seconds of stage time. Every objective measurement stage passed. The evaluator
degraded safely after two semantic validation failures, the first a missing
claim marker and the second a `wrong_speaker` claim-ledger verification
failure, so coaching and claim verification were unavailable while every
objective artifact stayed intact. This repeats the degraded evaluator states
seen at 22C and 22D rather than the clean evaluator seen at 22E2, which
confirms the degradation is intermittent enrichment behavior and not a
regression introduced by this checkpoint. The run produced no speech-sound
artifact or master field, and the before and after hashes of `history.json`
and `progress.md` were identical.

#### Standing consequence of 22E3 for the Australian variety

Checkpoint 22E3 established that Azure `en-AU` cannot name a produced phone and
that Azure `en-US` names phones only against a General American target. It also
established that Azure accepts no custom expected phone sequence, lexicon or
accepted variant: `ReferenceText` takes words only, and `ScenarioId` selects a
customised point system rather than a custom reference pronunciation. There is
therefore no way to tell Azure that the speaker is Australian.

The obvious objection, that the empty Australian phone names were a calling
mistake rather than a real limit, was tested rather than argued. A controlled
probe in `azure_locale_probe.py` sent one identical public corpus clip under
six settings. `en-AU` named zero of 17 phone positions under the IPA alphabet,
under the SAPI alphabet and under the default; `en-GB` named zero as well; and
`en-US` named 17 of 17 under both alphabets, returning `ð æ t w ʌ z` for IPA
and `dh ae t w ah z` for SAPI on the same audio. Phone naming therefore depends
on the locale alone. The alphabet parameter is honoured, SAPI works, and the
request is correct. Microsoft documents the same limitation, and other
customers report identical empty fields for `en-GB`, `ar-SA` and `ja-JP`.

This also corrects a natural misreading. `en-AU` is not a broken or stubbed
`en-US`. It is a genuine Australian calibrated scorer, and the owner
demonstration showed it behaving that way: the same natural Australian speech
averaged 98.5 on `en-AU` against 95.6 on `en-US`, and `en-AU` did not penalise
the non rhotic vowel or the BATH vowel at all. The trade is real rather than a
pure loss. For a score on Australian speech `en-AU` is the better instrument;
for naming what was actually produced no Azure locale serves Australians.

The proposal to run Australian speakers through `en-US` and then correct the
result using knowledge of their variety is rejected as a scoring method. The
reasoning is recorded in the language, accent and dialect boundary section of
`research-and-protocol.md`: coverage, locality, magnitude and direction. The
decisive point is direction. A variety effect is systematic, so a repeatable
system would report the same unfounded concern about Australians every time and
its repeatability would make the error look like evidence.

A single speaker owner demonstration on 2026-07-25, recorded in
`accent-contrast-v1.0.0.json`, tested the locality part of that reasoning and
did not support it. Natural Australian speech on `en-US` produced ten phones
below 80, nine on divergence points declared before the scores were read, and
none on the dialect stable control sentence. The affected set was short and
predictable: the r coloured vowel, the BATH vowel, dark l and final t. Locality
is downgraded to unsupported at this sample size and the write up was corrected
accordingly. Exclusion therefore looks more workable than first argued, but is
still not validated, because nothing automatic separates an ordinary Australian
feature from a genuine production difficulty at any single opportunity.

That demonstration also showed the utterance score sitting between 95 and 99 on
the same clips whose phone level flagged Australian features. Checkpoint 22E4
must therefore read phone level evidence and never an overall score, which the
contract already requires for other reasons.

Two further engineering facts close the obvious workarounds:

- **The hybrid does not align.** Taking the score from `en-AU` and the phone
  name from `en-US` fails because the two references disagree on phone count,
  not merely phone identity. Rhoticity alone changes `car` from three expected
  phones to two, so positions cannot be matched, and a name from one model
  glued to a score from another is an unvalidated composite that neither the
  vendor nor this project supports.
- **The benchmark cannot stand in for the missing evidence.** SpeechOcean762 is
  Mandarin first language learners assessed against American English. Whatever
  22E4 establishes about `en-US` is established on that population. Carrying it
  to Australian adults is a second unvalidated leap and must not be made.

#### Where the Australian variety effort should be spent

A 2026-07-25 literature review settled the direction. Speech technology does
not answer variety mismatch by dropping opportunities; it changes the
reference, through accent specific pronunciation lexicons and accent aware
models, keeping every opportunity scored. Azure forecloses that method entirely
because it accepts no custom lexicon. The local lanes do not, because this
project controls their targets.

The conclusion is therefore not to build a divergence mask to rescue the Azure
`en-US` lane. It is to build the Australian reference that checkpoint 22F
already requires, and to spend it on the local segmentation-free GOP and POWSM
lanes where an Australian target can actually be set. Azure remains what the
register already says it is, a comparator reporting General American evidence
against General American targets.

Two findings bound any future exclusion work, recorded in full in
`research-and-protocol.md`: the one quantified clinical trial of dialect
adjusted scoring tripled false negatives while reducing false positives, and
the nearest published software analogue failed to remove the bias it targeted.
Under identification is the more harmful direction for this product and the
harder failure to notice.

Resource status for the Australian reference: Unisyn from CSTR Edinburgh is the
only source from which an Australian and American divergence list falls out
mechanically, and its non commercial licence blocks it here. Montreal Forced
Aligner ships no Australian dictionary. Macquarie therefore remains the real
acquisition target, with the open Bookbot Australian lexicons worth evaluating
under their existing conditional register status. No ready made Australian and
American divergence list was found anywhere, and no ASHA or Speech Pathology
Australia guidance enumerates dialect stable segments, so any such list is this
project's own construction and must be labelled that way.

No independent audit of any commercial pronunciation scorer against non
American native English varieties was found, and Microsoft's own pronunciation
assessment limitations page carries no accent or dialect fairness statement and
no per locale accuracy breakdown. The absence of an audit is not evidence of
absence of bias.

Permitted handling for every later subcheckpoint: exclude, do not correct.
Where Australian and American references legitimately differ, the opportunity
is unscorable and is reported as unscorable. Where they agree, `en-US` may
raise a candidate for human review and never a finding. The real unlock is
expertly labelled Australian speech, which is why ANDOSL, AusKidTalk and the
Macquarie request remain the acquisition priorities, and why the local
segmentation-free GOP and POWSM lanes are core while Azure is only a
comparator. POWSM in particular recognises phones without being given a target,
so it carries no foreign prestige reference to fail against.

#### 22E4. Frozen development and tuning comparison

- Run eligible lanes on the same frozen participant-exclusive clips.
- Apply the unchanged 22D precision, Wilson lower-bound, false-concern, recall
  and true-positive gates separately to development and tuning.
- Exclude any model and source pair whose manifest is `supporting_only`,
  `blocked`, `unknown` or non-independent from selection-gate calculations.
- Preserve adult and child results, locales, exact relation evidence,
  score-only concern evidence and articulatory evidence as separate classes.
- Report provider failure, abstention, coverage, cost, latency and
  repeatability.
- Do not choose a threshold that merely performs best after seeing tuning
  outcomes; use the predeclared selection procedure.
- Treat the roughly 0.55 to 0.65 expert-agreement correlation band as
  expectation calibration only. It cannot lower an event-level gate.

Acceptance: all denominators and failures are visible, no held-out participant
or label is accessed, and no provider output becomes reference truth.

Completion evidence on 2026-07-26: the rules were frozen first, in
`comparison-contract-v1.0.0.json`, before any lane ran. It pins the frozen
inputs by hash, inherits the five 22D gates unchanged, fixes the threshold
procedure and the closest-point reporting rule, names every candidate with its
role, and lists every excluded lane with its reason. The metric code is not a
reimplementation: binary scoring reuses `score_binary_rows` and the gates reuse
`selection_gate_results`, and a test reproduces the committed 22D greedy numbers
through this checkpoint's own code, matching every count, precision, recall,
false-concern rate and Wilson interval exactly. Without that, a silent
redefinition of a denominator or an abstention could have moved a result.

Seven candidates across four lanes ran on the same frozen 480 clips. Every lane
repeated every input exactly with zero tolerance. Segmentation-free GOP scored
all 5,478 scorable targets, matching the expert relation rows one for one;
POWSM covered 565 clips including the 85 non-gate clips; the supporting-only
CommonPhone model covered the 480; and Azure received the 240 adult clips twice
in each of two locales, 960 requests, all returning HTTP 200 with no retry, no
failure and exact repetition on all 240 clips in both locales.

**No candidate passed every unchanged gate, so the recorded decision is
`no_selection`.** The committed report is `frozen-comparison-v1.0.0.json`.

The strongest candidate is GOP-AF-SD, the segmentation-free GOP score whose
denominator includes the deletion lattice, at eight of ten checks. It passes all
five gates on development adults: precision 0.757 against the 0.75 minimum,
Wilson lower bound 0.599 against 0.5, false concerns 0.0046 per opportunity
against the 0.01 maximum, recall 0.206 against 0.200, and 28 true positives
against the minimum of seven. On threshold tuning it fails precision, 0.667
against 0.75, and the Wilson lower bound, 0.417 against 0.5, while passing the
other three. GOP-AF, the substitution-only variant, reached six of ten and is
the weaker of the two on both partitions.

Azure `en-US` per-phone accuracy scores reached seven of ten. Its only passing
operating point flags a phone when the returned accuracy score is zero, which
is right about seven times in ten on both partitions: development precision
0.696 with 32 true positives, tuning precision 0.692 with nine. It fails the
0.75 precision point estimate on both partitions and the Wilson lower bound on
tuning. Coverage is 0.927 and 0.953, with the abstentions caused by the two
lexicons expecting different phones.

Azure `en-AU` produced **no scorable evidence at all**. Word alignment
succeeded on 1,698 of 1,702 reference words, but the locale named zero of its
5,302 phone positions, so no returned score can be attached to a known target
without assuming a correspondence the response does not support. This is
recorded as evidence unavailable rather than as a gate failure, because the
lane never reached the gates. It is the same limitation 22E3 found on five
clips, now confirmed on the full adult set.

The two free-phone relation paths failed the way the 22D greedy path failed.
POWSM reached four of ten with false concerns at 0.204 and 0.182 per
opportunity, twenty times the permitted maximum, and precision of 0.190 and
0.139 despite recall of 0.783 and 0.906. Azure `en-US` named candidate phones
reached four of ten on the same pattern. The known affricate mismatch, where a
free-phone model emits the two component phones against a single tie-barred
reference token, turned 32 of 35 adult affricate targets into false concerns
but accounts for only 5.5 per cent of POWSM's 581 adult false concerns;
removing it entirely would still leave a false-concern rate eighteen times the
gate. The mismatch is real and is reported per candidate, but it is not the
reason these paths failed.

Two findings bound how this result should be read. First, the threshold tuning
partition holds 34 positive opportunities and the reported operating points
raise about fifteen concerns on it, so one further false concern moves precision
by roughly five points; a gate outcome there is fragile. Second, this is the
mirror image of 22D, where the strongest candidate passed every tuning gate and
missed a development gate. Two failures in opposite directions around the same
lines indicate performance sitting close to the gates rather than one fixable
defect, and neither result licenses moving a gate.

The secondary sources produced non-gate evidence only. POWSM returned output on
all 25 Acted Clear, all 30 Common Phone and all 30 Australian Common Voice
clips. That Australian evidence exists only because the lane is local; the
Australian Common Voice manifest blocks provider transfer, so no external lane
saw Australian speech and none can. Segmentation-free GOP was not run on those
sources because it needs an expected phone sequence and no Australian
pronunciation lexicon has been acquired yet, which is checkpoint 22F's work.

Cost and privacy: the three local lanes cost nothing and ran offline. Azure ran
on the existing Free F0 Australia East resource with no observed charge, mean
latency 0.72 seconds for `en-AU` and 0.91 for `en-US`. Only clip audio and the
intended reference text were transmitted. No child clip, no held-out clip, no
Australian Common Voice clip and no owner recording left the machine, and the
prohibited overall, fluency, completeness and prosody scores were discarded at
the response boundary before anything reached disk.

The required normal two-speaker conversation pipeline acceptance run completed
in an isolated output directory without `--me`, exit code zero, in 360 seconds.
Every objective measurement stage passed. The evaluator degraded safely after
two semantic validation failures, a claim ledger numeric and timestamp
verification failure followed by a claim missing its evidence references, so
coaching and claim verification were unavailable while every objective artifact
stayed intact. This repeats the intermittent enrichment behavior recorded at
22C, 22D and 22E3 rather than a regression introduced here. The run produced no
speech-sound artifact and no speech-sound field in `master.json`, the root
`output` directory was untouched, and the before and after hashes of
`history.json` and `progress.md` were identical.

#### 22E4B. Powered replication before any selection record

Owner instruction, 2026-07-26: do this before 22E5.

**Why.** The frozen comparison used a fraction of the labelled adult speech this
project already holds. The whole outcome turned on 34 positive opportunities in
the threshold tuning partition, where the strongest candidate raised fifteen
concerns and needed twelve. A difference of two flags separated a pass from a
fail. That sample size came from the checkpoint 22D compute budget, not from a
scientific argument, and two of the five gates, the Wilson lower bound and the
minimum true positive count, are explicitly sample size penalties. The correct
reading of `no_selection` is therefore that the estimate is underpowered, not
that the method is settled.

**Unused evidence already acquired, licensed and manifested,** from
`.research_data/speech_sound_patterns/splits/speechocean762-v1.2.0.json`:

| Partition | Adult participants available | Used at 22E4 |
|---|---|---|
| development | 77 | 8 |
| threshold_tuning | 25 | 4 |
| held_out_evaluation | 26 | 0, and it stays sealed |

**Three findings that bound how this replication must be run.**

1. *The gates sit at roughly competent human level and must not move.* An
   exploratory analysis scored each of the five original SpeechOcean762
   reviewers as though the reviewer were the candidate system, against the same
   four of five consensus and through the same frozen scoring code. Three of
   five reviewers pass every gate on both partitions, with precision 0.909 and
   0.872, 0.949 and 0.786, and 0.920 and 0.964. Two fail on precision and false
   concerns, at 0.749 and 0.733, and 0.704 and 0.660. The measurement is
   deliberately generous to the human, because each reviewer's own vote is
   inside the consensus they are scored against. The strongest machine
   candidate, at 0.757 and 0.667, sits exactly where the two weakest reviewers
   sit. A gate that three of five experts clear cannot be called unattainable,
   so no gate may be lowered on the grounds that nobody could reach it.
2. *The truth is moderately agreed and the base rate is low.* Fleiss kappa
   across the five reviewers is 0.566 for development adults and 0.520 for
   tuning adults, and the positive rate is 0.0685 and 0.0346. Both numbers are
   in the committed `local-benchmark-v1.0.0.json`. Low prevalence with noisy
   labels makes precision the hardest quantity to earn, and it is why a handful
   of false concerns moves the result so far.
3. *Do not expect a large jump from swapping models.* Published phone level
   mispronunciation detection sits near 0.70 F1 on the comparable task, which
   is close to what this benchmark already measures, so the realistic gains are
   in evidence quality and task design rather than in a better checkpoint.

**What to run.** Extend the participant sample toward the full non held out
adult pool, keeping the existing participant exclusive split assignments, and
rerun every eligible lane. Keep the two exact repeats and the zero numeric
tolerance.

**Discipline that makes this legitimate rather than a retry until it passes.**

- Declare in writing, before running, that this replaces an underpowered
  estimate, and that whatever it produces is the reported result.
- Freeze the rules again in a new contract version. Do not edit
  `comparison-contract-v1.0.0.json` or `frozen-comparison-v1.0.0.json`; they are
  the record of the first look.
- Change no gate, no decision rule, no alignment rule and no abstention rule.
- The held out participants stay sealed until 22H regardless of the outcome.
- If the powered estimate still fails, that is the answer, and 22E5 records it.

**Practical checks before starting.**

- The larger external volume needs a new corpus to provider transfer review
  version, because the committed 22E4 plan authorises 240 clips. Confirm
  whether the expanded request count exceeds the Free F0 tier and tell Adam the
  answer rather than assuming it.
- Runtime at 22E4 was about two hours per local lane for 480 clips under
  contention. Scale accordingly and run in the background.

**What not to do.** Do not narrow the scored consonant set to chase precision.
The strongest candidate's development false concerns are spread thinly across
seven different phones, two on D, two on T, and one each on DH, HH, NG, P and V,
so there is no concentrated blind spot to remove, and cutting targets would
lower recall and the true positive count, which are two other gates. Narrowing
the *task* to controlled prompts remains a separate and still sound idea, and
that is checkpoint 22F's job.

**In parallel, not blocking.** Send the Australian evidence enquiries now, since
ANDOSL, AusKidTalk and Macquarie all have long lead times and none of them
affects this benchmark, which is Mandarin first language speech assessed against
American English. Australian data fixes Australian fairness; it does not fix
phone level accuracy here.

Acceptance: a new frozen contract, a powered participant sample, unchanged
gates, a single reported run, the held out set untouched, and an explicit
statement of whether the earlier near miss survived the larger sample.

**Completion evidence on 2026-07-27. The recorded decision is `no_selection`
again, and the checkpoint 22E4 near miss did not survive the larger sample.**

The rules were frozen in two documents before anything existed to measure. The
sample rules went into `benchmark-powered-sample-contract-v1.0.0.json` before the
sample was built, carrying the written declaration that this replaces an
underpowered estimate, that whatever it produces is the reported result, and that
no gate may move. The comparison rules went into `comparison-contract-v1.1.0.json`
before any lane ran, pinning the powered inputs by hash and copying all five
gates across unchanged. `comparison-contract-v1.0.0.json` and
`frozen-comparison-v1.0.0.json` were not edited; both remain byte-preserved and
the version-aware comparison validator still accepts them.

The powered sample holds 2,280 SpeechOcean clips, 2,040 adult and 240 child, from
every one of the 77 development adults and 25 threshold tuning adults. All 480
checkpoint 22E4 clips reappear in it under their original split and stratum,
which the preparer verifies before it will finish, so the powered sample is a
proven superset of the first look rather than a fresh draw. The child sample was
deliberately held at its checkpoint 22D size by owner decision, because the gates
are adult only. The 26 held out adults were never touched.

Two proofs establish that the numbers are comparable with the numbers they
replicate. The powered truth extractor reproduces all 5,478 committed checkpoint
22D relation rows exactly before it may write anything, so the consensus rule,
the scorable scope and the positive, negative and unscorable states cannot have
been redefined. Separately, re-scoring the checkpoint 22E4 evidence and
rebuilding its entire committed report through the version aware code reproduces
both files byte for byte, so the refactor moved no metric, alignment, abstention
or denominator.

Adult scorable opportunities rose from 1,971 to 18,565 on development and from
984 to 5,976 on threshold tuning. Positive opportunities rose from about 136 to
844 and from 34 to 138.

**The result.** Segmentation-free GOP with the deletion lattice fell from eight
of ten checks to seven. Its development precision barely moved, 0.757 to 0.751
against the 0.75 minimum, on 160 true positives rather than 28, but its
development recall fell from 0.206 to 0.189 against the 0.200 minimum, and its
tuning precision fell from 0.667 to 0.622. The two gates that are explicit sample
size penalties moved decisively in its favour, the development Wilson lower bound
from 0.599 to 0.689 and the tuning bound from 0.417 to 0.476, so the candidate
received exactly the advantage a powered replication exists to give it and still
failed on the point estimates and on recall, which are not sample size penalties.
The correct reading is that the checkpoint 22E4 estimate was not noise, but the
inference that two flags separated it from a pass was.

Azure `en-US` per-phone accuracy scores are now nominally the strongest candidate
at eight of ten, up from seven, but every point of that gain came from the Wilson
lower bound rising with the sample. Its precision point estimate is flat and
clearly short of the gate on both partitions, 0.696 to 0.703 on development and
0.692 to 0.679 on tuning. That is a stable failure rather than a near miss.

Azure `en-AU` again produced no scorable evidence. It named zero of 44,335 phone
positions while `en-US` named 42,903 of 42,903. At checkpoint 22E4 the same
comparison was zero of 5,302. The standing conclusion that no external lane can
supply Australian variety exact relation evidence is now demonstrated at scale
rather than inferred from a small sample.

The three free-phone relation paths, POWSM, Azure named relations and the
supporting-only CommonPhone model, each reached four of ten on the same pattern
as checkpoint 22E4: high recall and very poor precision.

**Two failure modes appeared only at this scale, and both are recorded rather
than smoothed over.** One clip is 20.408 seconds and the pinned POWSM checkpoint
declares `preprocessor_conf.speech_length: 20`, so the model cannot accept it.
Truncating would have dropped real speech and turned the dropped region into
invented deletion concerns at every target in it, so the clip is recorded as
unprocessable with its reason and its 19 targets abstain for that lane alone;
every other lane still saw the clip. One Azure `en-US` configuration of 4,080
returned different content for a byte identical repeated request, both responses
HTTP 200. The frozen contract grants zero numeric tolerance, so that clip's 16
targets abstain for the Azure candidates rather than letting a non-reproducible
response into the metrics. Both decisions were taken blind to any result, both
are visible in the committed coverage and abstention counts, and neither could
change an outcome. The runners can no longer claim an exact repeat they never
performed.

Cost and privacy: the three local lanes cost nothing and ran offline. Azure sent
8,160 requests, all HTTP 200 with no retry and no failure, 2,040 adult clips twice
in each of two locales, 9.72 audio hours in total. The Australia East resource was
moved from the free F0 tier to standard S0 before the run, because the free tier
allows five audio hours a month and would have truncated it; the owner made that
change and approved the cost, about A$14 at the A$1.4492 standard rate against
A$289.83 of remaining account credit. Only clip audio and the intended reference
text were transmitted. No child clip, held out clip, Australian Common Voice clip
or owner recording left the machine, and the prohibited overall, fluency,
completeness and prosody scores were discarded at the response boundary.

The committed report is `frozen-comparison-v1.1.0.json`. The corpus to provider
transfer review moved to version 1.2.0 to authorise the larger volume in writing
before any request was built; versions 1.0.0 and 1.1.0 stay on disk and are still
validated.

The required normal two-speaker conversation pipeline acceptance run completed in
an isolated output directory without `--me`, exit code zero, in 357 seconds.
Every objective measurement stage passed. The evaluator degraded safely after two
semantic validation failures, a claim marker mismatch followed by an omitted stat
outcome, so coaching and claim verification were unavailable while every
objective artifact stayed intact. This repeats the intermittent enrichment
behavior recorded at 22C, 22D, 22E3 and 22E4 rather than a regression introduced
here. The run produced no speech-sound artifact and no speech-sound field in
`master.json`, the root `output` directory was untouched, and the before and
after hashes of `history.json` and `progress.md` were identical.

Sources for the external claims above: the corpus and its five expert
annotation design, https://arxiv.org/abs/2104.01378; current phone level
mispronunciation detection performance near 0.70 F1,
https://arxiv.org/abs/2511.20107 and
https://www.emergentmind.com/topics/mispronunciation-detection-and-diagnosis-mdd.
The reviewer ceiling analysis is this project's own, computed from the private
five reviewer records in `speechocean-relation-evidence.json` through
`comparison.partition_metrics`, and is exploratory context rather than committed
evidence.

#### 22E5. Selection and rejection record

- Assign every lane one of `selected_candidate`, `supporting_only`,
  `research_only`, `blocked` or `rejected`.
- Record incremental value beyond the 22D local baseline and all legal,
  privacy, Australian-variety, child/adult, operational and cost limitations.
- Freeze any selected mapping, feature, threshold and provider configuration
  before 22F and the later held-out evaluation.
- Permit a local-only decision if no remote provider adds safe value.
- Record `no_selection` if nothing passes all unchanged gates. This completes
  22E honestly; it does not trigger more threshold searching or a weaker gate.

Acceptance: a written decision and role-specific reason exists for every entry
in the approved register plus conditional SpeechAce and rejected SpeechSuper.
`no_selection` is accepted when warranted. No system is selected from
marketing, prestige, agreement with another model, source-overlapping evidence
or overall pronunciation scores.

**Completion evidence on 2026-07-28. The recorded decision is `no_selection`,
and the search for a pronunciation concern detector is closed rather than
paused.**

The committed record is `selection-record-v1.0.0.json`. All fourteen register
lanes carry a verdict, a written reason, an incremental-value statement against
the checkpoint 22D local baseline, all six required limitation classes, and the
conditions that would reopen them. SpeechAce and SpeechSuper are register lanes,
so the acceptance criterion is met by the same fourteen. The verdicts are seven
`blocked`, five `rejected`, one `research_only` and one `supporting_only`.

Only three lanes were ever measured against the gates. Segmentation-free GOP is
`research_only` at seven of ten checks: free, local, deterministic, no licence or
provenance risk, the smallest margin of failure of any lane, and the obvious
thing to retest under the narrower task that 22F creates. POWSM is `rejected` at
four of ten, failing structurally rather than by tuning, because an unconstrained
phone sequence cannot be conditioned on the expected phone and a legitimate
variant therefore reads as a concern. Azure is `rejected` at eight of ten on its
`en-US` accuracy scores, whose precision is flat and clearly short at 0.703 and
0.679, with `en-AU` producing no scorable evidence at all. The remaining eleven
lanes were never measured, and their verdicts say why nothing is known about
them rather than implying they were tried and found wanting.

No paid external provider added value beyond the free local stack. The
checkpoint 22D repair reached nine of ten checks at its closest point and still
selected nothing; nothing in checkpoint 22E beat it. A local-only outcome was
permitted and is what the evidence produced, except that the local candidates did
not pass either.

Nothing is frozen forward, because nothing was selected. The record states that
explicitly: `selected_mapping`, `selected_feature`, `selected_threshold` and
`selected_provider_configuration` are all null, and the validator refuses any
other value while the selected lane list is empty. What is carried forward is the
five unchanged gates, the phone map and consensus rule, the participant-exclusive
splits including the 26 sealed held-out adults, both frozen comparison contracts
and reports, the corpus manifests and transfer review, the provider register, and
the local implementations as developer research code. What is not carried forward
is any operating point, threshold, candidate-proposed phone mapping or provider
configuration, and the checkpoint 22E4 near miss that the powered replication did
not reproduce.

Four guards make the record hard to weaken: every verdict is pinned in
`selection_record.LANE_DECISION_PROFILES` so changing one is a code and test
change; a verdict may not contradict the lane's register status, so nothing
conditional, blocked, declined or rejected can be recorded as selected;
`selected_candidate` is reachable only when the committed powered comparison
reports a candidate on that lane passing every unchanged gate on both partitions,
and none does; and the record pins the register and all four committed reports by
hash, so editing any of them invalidates the record instead of leaving a stale
verdict standing. A test rebuilds the record from that evidence and requires it
to reproduce the committed file byte for byte.

Owner decisions carried into this record on 2026-07-28: no written-permission
reply had arrived from ELSA, UNSW, the ZIPA authors, the child model or the
AusKidTalk custodian, so every one of those lanes stays `blocked` with its
outstanding blockers intact; the Azure Australia East resource stays on the
standard S0 tier, so its recurring cost is recorded as an operational limitation
rather than removed; and ELSA stays open as `blocked` rather than being closed
out like iFLYTEK, because its documented substituted-phone field is still the
strongest such field found in any external product.

One error in the committed evidence was found and corrected. The powered
comparison report described this checkpoint's Azure monetary cost as free F0,
which understated it: the resource had been moved to standard S0 before that run,
at a cost of about A$14, as the checkpoint 22E4B section above already recorded.
The owner directed on 2026-07-28 that the report be corrected rather than
annotated, so the summariser now carries a per comparison Azure cost and
`frozen-comparison-v1.1.0.json` was regenerated. The regeneration is auditable
rather than a hand edit: the report rebuilds byte for byte from the unchanged
private scored evidence, exactly one field differs from the previous file, and
`frozen-comparison-v1.0.0.json` still rebuilds byte for byte with its original
free F0 wording, which was accurate for its 240 clip volume. No metric,
denominator, gate, coverage count or decision moved.

The required normal two-speaker conversation pipeline acceptance run completed in
an isolated output directory without `--me`, exit code zero, in 343 seconds. All
thirteen stages reported OK. The evaluator degraded safely after a semantic
validation failure, so coaching and claim verification were unavailable while
every objective artifact stayed intact, repeating the intermittent enrichment
behavior recorded at 22C, 22D, 22E3, 22E4 and 22E4B rather than a regression
introduced here. The run produced no speech-sound artifact and no speech-sound
field in `master.json`, the root `output` directory was untouched, and the before
and after hashes of `history.json` and `progress.md` were identical.

A separate defect appeared during this checkpoint and is recorded rather than
quietly retried away. A first attempt at the same acceptance run hung in the
listener stage for 3 hours 54 minutes on a single remote call and had to be
stopped. `llm_contract.run_with_retry` catches exceptions and retries once, but
carried no wall-clock timeout, so a request that never returned never became a
failure and the documented degrade path never fired; `run_all` then treated the
stopped stage as fatal rather than degrading, so that attempt produced no usable
artifacts. The rerun above is the reported acceptance run. **Adam approved the
fix on 2026-07-29**; see the pipeline robustness note at the end of checkpoint
22E6.

#### 22E6. Correct the evidence record

The open evidence search disproved several facts this repository states as
committed record. A plan that carries a disproved claim is worse than one that
carries a gap, because the claim looks checked. This checkpoint corrects the
record and nothing else. It runs no model, acquires no data and measures nothing.

- Move the provider register to version 1.2.0 at checkpoint 22E6, correcting the
  Bookbot lane's training-data claim from unverified to disproved, with the
  evidence that WikiPron defines no Australian English dialect. Only the reason
  changes; the lane's verdict does not. This brief originally said the lane
  "stays `blocked`", which described its checkpoint 22E5 verdict rather than its
  register status: the register status is `conditional`, and Adam decided on
  2026-07-29 that it stays `conditional`.
- Correct the ANDOSL and L2-ARCTIC acquisition rows, and record ISLE, Mitchell
  and Delbridge, the Speech Accent Archive, AusTalk, CoANZSE and the open stack
  as new register entries with their licences and verdicts.
- Record the standing owner decisions of 2026-07-28: no acquisition enquiries,
  no ISLE purchase, openly licensed sources only.
- Update the checkpoint 22E5 selection record so the Bookbot verdict cites the
  disproved provenance rather than the unverified one. The verdict itself does
  not change, so the pinned decision stays `blocked`.
- Preserve every earlier register and report version unedited.

Acceptance: no committed document asserts a claim the search disproved, every
new source carries a licence and a verdict, the register and selection record
validators still pass fail closed, and the historical versions remain
byte-preserved and accepted through their explicit version-aware paths.

**Completion evidence on 2026-07-29. COMMITTED.** Nothing was run, acquired or
measured. Every claim below was checked against its own source on the day it was
written, which is the point of the checkpoint.

*The Bookbot lane's training source is recorded as disproved rather than
unverified.* The disproof was verified independently rather than inherited:
WikiPron's own language configuration defines English with exactly two dialects,
`uk` mapped to UK or Received Pronunciation and `us` mapped to US or General
American, and its scraped data directory holds `eng_latn_uk_broad`,
`eng_latn_uk_narrow`, `eng_latn_us_broad` and `eng_latn_us_narrow` and no
Australian file of any kind. The model repository's own card data names no
training dataset at all, so the Australian claim rested entirely on the model
name. Both are recorded as dated evidence on the lane. The lane's status stays
`conditional` on the owner's explicit decision of 2026-07-29 rather than moving
to `blocked`; what changed is its reason, its lineage claim state and its
blockers, which no longer ask anyone to verify a dataset that does not exist.

*The register is version 1.2.0 at schema 1.2.0.* Versions 1.0.0 and 1.1.0 stay
on disk unedited, and `assert_historical_register` holds each to its own schema
and to the checkpoint that wrote it, so a superseded register cannot be
relabelled or quietly edited. The schema gained `training_data_claim_state` on
every lane carrying model lineage, with values `documented`, `unverified`,
`disproved` or `not_applicable`. The state is pinned per lane in code, a lane
with a disproved claim can never be `ready` and can never leave its blockers
empty, and a test fails if any lane names a WikiPron Australian dataset as
though it existed.

*The standing owner decisions of 2026-07-28 are in the register.* They were
living in prose only, which is how a later agent reasonably proposes undoing a
decision it has never seen. `no_acquisition_enquiries`, `no_isle_purchase` and
`openly_licensed_sources_only` each carry their scope, their consequence and
what would reopen them; dropping one or re-dating one fails validation. Four
lanes whose blockers assumed an enquiry somebody intended to send, ELSA, ZIPA,
UNSW Speech Attributes and AusKidTalk, now say plainly that the enquiry was
declined and that only a new owner decision changes that.

*Nine sources entered the corpus registry with a licence and a verdict.* Six are
closed: ANDOSL, AusTalk, ISLE, Mitchell and Delbridge, the Speech Accent Archive
and CoANZSE. Three are the openly licensed stack checkpoint 22E7 acquires:
WikiPron British broad, the Australian-tagged Wiktionary entries through Kaikki,
and the Montreal Forced Aligner English dictionaries. The open stack is recorded
as `access_pending` with an empty archive list and no local storage, so nothing
can pretend to be acquired before it is, and all nine are `provider_transfer`
blocked, so none can ever become eligible for an upload.

*Three claims from the search itself were wrong and are corrected here.* CoANZSE
does publish terms: it is offered free for research, education and scholarship
and prohibits redistribution and commercial use, so the note that it carried no
licence at all was wrong. Its rejection is unchanged and now rests on two
independent grounds instead of a mistaken one. `andosl.anu.edu.au` still carries
a domain name alias chain to an Australian National University address, so
"no longer resolves" was imprecise; nothing answers on port 80 or 443, so the
conclusion held. The Montreal Forced Aligner figures of 42,352 words and 103
phones match the generic English dictionary on words and not on phones, which
lists 99, so the inventory is recomputed at acquisition rather than carried
forward. The published English varieties are generic, UK, US, India, Nigeria and
Nonnative: there is no Australian English dictionary, which matters for 22E8.

*The selection record was reissued as version 1.1.0.* It had to be: the record
pins the register by hash, so correcting the register correctly invalidated the
old record rather than leaving a stale verdict standing. Version 1.0.0 stays
unedited and stays pinned to the register it was written against, and both
versions rebuild byte for byte from their own evidence. No verdict moved, the
decision is still `no_selection`, and a test proves that exactly one lane's
written reason differs between the two. The record's next checkpoint changed
from 22F to 22E7, because the plan inserted three checkpoints in front of it.

*The planning documents were also slimmed, on the owner's instruction.* The same
checkpoint narratives were being restated in `current-state.md`, in
`improvement-plan.md` and in `README.md`, so all three now point here instead.
`current-state.md` fell from 562 lines to 254 and `improvement-plan.md` from 630
to 433, and the README's item 22 section lost about two thirds of its length.
Nothing was archived and no fact was dropped: every removed passage was checked
against this plan first, which is now the single home of that detail.

The required normal two-speaker conversation pipeline acceptance run completed in
an isolated output directory without `--me`, in 367 seconds, with all thirteen
stages reporting OK. The listener returned normally in 26 seconds, so the hang
recorded at checkpoint 22E5 did not recur; the missing request timeout behind it
is still unfixed and still needs its own owner decision. The evaluator degraded
safely on its second attempt with `semantic_validation_failure`, so coaching and
claim verification were unavailable while every objective artifact stayed intact,
repeating the intermittent enrichment behaviour recorded since 22C rather than a
regression introduced here. The run produced no speech-sound artifact and no
speech-sound field in `master.json`, the root `output` directory was untouched,
and the before and after hashes of `history.json` and `progress.md` were
identical.

*The enrichment hang recorded at checkpoint 22E5 was fixed on the owner's
instruction, immediately after this checkpoint was committed.* It is a pipeline
robustness fix rather than item 22 work, so it is noted here only because this
plan is where the defect was recorded. Remote enrichment now carries two
deadlines. The provider client aborts its own request at 240 seconds, which
produces a clean classifiable timeout and frees the connection. An outer
deadline of 300 seconds in `run_with_retry` is the backstop for whatever the
client cannot see, and it is deliberately the longer of the two so the clean
failure happens first. Both count elapsed awake time, because a system sleep
suspends the process rather than consuming the budget. A hung call therefore becomes a `timeout`, retries once
and then degrades with an explicit status, which is what the contract always
claimed it did. Transcription is load bearing and is not covered: it must fail
the run rather than degrade. `tests/test_llm_contract_timeout.py` proves a hung
call degrades in bounded time, that a slow but successful call is not cut off,
and that the existing failure categories are neither swallowed nor relabelled.
The pipeline version moved to 0.10.1, a patch, because no measurement meaning or
output shape changed.

Its own acceptance run completed in 405 seconds with all thirteen stages
reporting OK. What it had to prove is that a healthy call still succeeds with a
client timeout in place, and it did: the referee completed on attempt 1 in 21
seconds and the listener on attempt 1 in 34 seconds. No timeout fired anywhere,
which is the correct result, because nothing hung. The evaluator degraded with
`semantic_validation_failure` after 123.8 and 77.6 seconds, both far inside the
deadline, repeating the long standing behaviour recorded since 22C. The run
produced no speech-sound artifact or master field, left the root `output`
directory untouched, and left `history.json` and `progress.md` byte identical.

Two verification details are worth keeping, because both were learned the hard
way on the same afternoon. First, the run's recorded source tree hash matches the
live source exactly. An earlier attempt was discarded instead of reported,
because `build_initial_provenance` hashes the active source once at launch and
two source files had been edited while it ran, so its provenance no longer
described the code it exercised. Second, the attempt durations now printed in the
log summed to 201.4 seconds against a 202.9 second wall clock for that stage, a
1.5 second difference. That agreement is the evidence that the machine stayed
awake. An earlier run without `caffeinate` reported a 2,418 second evaluator
stage while `pmset` showed 1,587 seconds of system sleep inside it, which made a
correctly bounded deadline look broken for half an hour. Real runs belong under
`caffeinate -dimsu`, and `AGENTS.md` now says so.

#### 22E7. Acquire the open stack

Mirror checkpoint 22B's discipline on the newly approved openly licensed
sources. This checkpoint acquires and proves data. It selects nothing, scores
nothing and changes no pipeline behavior.

- Acquire WikiPron `eng_latn_uk_broad`, the Australian-tagged Wiktionary entries
  through Kaikki, and the Montreal Forced Aligner English dictionary.
- **Do not acquire any Australian speech.** Common Voice Scripted Speech 26.0
  Australian English has been held, hashed, licence-verified and
  participant-split since 2026-07-21, and checkpoint 22D used 30 clips of the
  55,922 available. The Australian half of this checkpoint was finished before it
  was written. Re-verify the existing archive checksum and move on. In
  particular, do not acquire the older version 24 Australian subset published for
  Everything Open 2026; it is a curated snapshot of an earlier release of the
  same speech.
- Acquire the comparison accent subsets of the same release 26.0. Terms were
  accepted by Adam on 2026-07-28 for the datasets below, all CC0, all on Mozilla
  Data Collective. Download through the documented REST endpoint using
  `MDC_API_KEY` from the gitignored `.env`; the key's value must never be
  printed, logged or committed.

| Dataset | Mozilla Data Collective ID | Role at 22E8 |
|---|---|---|
| Common Voice Scripted Speech 26.0 Australian English | `mdc_cmrt710620013mm071t45y6wb` | Already held since 2026-07-21. The group under test. |
| Common Voice Scripted Speech 26.0 British English | `cmrt6zrob000zmm07yqwjlpwi` | The variety the repaired reference actually describes. Should improve most cleanly. |
| Common Voice Scripted Speech 26.0 American English (Male) | `cmrt6zbgx000vmm07hfuefigk` | The reference variety, and the control that should stay flat under the repair. |
| Common Voice Scripted Speech 26.0 English, full release | `cmqim2hn800ssnr07gvmpcnwu` | Not required. Acquire only if a needed accent subset turns out to be unpublished, and check its size before starting: the Australian subset alone is 2.08 GB for 55,922 clips. |

- **The American subset is currently male only, and that is a confound, not a
  detail.** Accent and speaker gender would vary together, so a difference
  between the Australian and American groups could be either. Before this
  comparison may run, acquire the matching American English female subset, or
  derive both American groups from the full English release. If neither is
  possible, the American comparison is reported as gender-confounded and the
  British comparison carries the argument instead. Do not quietly proceed with
  the male-only set.
- Manifest each with the same fields as the Australian subset, and carry across
  the same lineage constraint: every Common Voice derived source is
  non-independent of the Wav2Vec2 CommonPhone training lineage and is barred from
  that model's selection evidence.
- Apply the same participant-split discipline to every new subset. The supplied
  train, dev and test files map to development, threshold tuning and sealed
  held-out exactly as the Australian subset already does, and no held-out speaker
  in any subset may be read before 22H.
- Manifest each one the way the existing corpora are manifested: exact source
  URL, retrieval date, independently computed archive checksum, licence text
  captured at acquisition, permitted role and prohibited claims.
- Record the lineage relationships that already matter. The Australian Common
  Voice subset overlaps the Wav2Vec2 CommonPhone training lineage exactly as the
  existing Common Voice manifest records, so it stays barred from that model's
  selection evidence.
- Record the ShareAlike distribution boundary in the manifests themselves, so a
  later agent building an application cannot ship a derived lexicon without
  meeting it.
- Everything stays in private gitignored storage. Nothing is rehosted.

Acceptance: every acquired source has a fail-closed manifest with licence
evidence, checksums recomputed independently of the download, a declared role
and its prohibited uses. An unlicensed or unhashed source is an error. No
measurement is performed.

**Completion evidence on 2026-07-29.** Seven sources were acquired, proved and
manifested. Nothing was scored, no gate was applied and no system was selected.

*Every published figure this checkpoint could check was recounted, and most were
wrong.* That is the whole reason the plan said to recompute rather than carry
numbers forward, and it earned its place three times over. The Montreal Forced
Aligner word counts are short by exactly the aligner's own special tokens:
English (UK) publishes 46,163 words and the file holds 46,167 head words, the
extra four being `<unk>`, `<cutoff>`, `[bracketed]` and `[laughter]`, and generic
English publishes 42,352 against 42,353. Both files carry one phone more than
their published list, the spoken noise phone `spn`. The phone counts recorded at
22E6 were simply wrong: 73 and 99 were recorded, the pages list 77 and 91, and
the 2026-07-28 search's 103 was wrong as well. The Australian tagged Wiktionary
entries were recorded as roughly 2,700; there are **5,347 words carrying 11,328
Australian tagged pronunciations**, of which 4,380 are ordinary words rather than
affixes or contractions and 3,166 also carry a British reference. Against a pack
of about twenty chosen words that pool is ample by two orders of magnitude, which
is what 22F needed to know.

*The plan's assumed British reference did not survive its own measurement.* The
brief expected WikiPron `eng_latn_uk_broad` to carry the British referenced
expected-phone path. It should not. Rhoticity was measured properly, counting
only rhotics that follow a vowel and do not precede one, because counting every
rhotic would call British English rhotic on the strength of the onset `r` in
*red*. MFA English (UK) places a post-vocalic rhotic in 0.01 percent of entries
and MFA English (US) in 23.58 percent, which is exactly how a real British and
American pair should behave. WikiPron's British scrape sits at 6.85 percent
against its own American counterpart's 18.48 percent, so its variety tag carries
real signal and it is nowhere near non-rhotic, and its inventory holds 239
distinct symbols including sounds English does not use, because volunteers add
loanword pronunciations. **English (UK) is therefore the British reference and
the WikiPron scrape is a supplement to it.** That boundary is a prohibited role
in the manifest, `primary_british_reference_without_an_inventory_repair`, and a
test fails if it is removed.

*Two sources were acquired beyond the brief, each to make a comparison mean what
it claims.* MFA English (US) is held so the British and American reference paths
share one phone alphabet; two paths differing in alphabet as well as in variety
could not produce an interpretable difference at 22E8. WikiPron
`eng_latn_us_broad` is held one level up for the same reason: without it, every
statement above about how British the British scrape is would be an assertion
rather than a measurement. Both are small text files and both carry their own
manifest, role and prohibitions.

*The gender confound is closed rather than reported.* Adam accepted terms for
Common Voice 26.0 American English (Female), dataset `cmrt70j4z001qmm07nvfsmgmr`,
on 2026-07-29, so the American group is built from both halves instead of being
declared confounded. Neither half may stand alone: `american_comparison_from_one_gender_alone`
is a prohibited role on both, and the registry validator fails if either subset
is absent. One asymmetry remains and is recorded rather than absorbed: the
American subsets are filtered to a declared gender while the Australian and
British subsets apply no gender filter, so American contributors who declared no
gender are excluded where the others' are not.

*One contributor was found in two comparison groups, and is excluded from both.*
The four-way identifier audit found a single speaker in both the American male
and British subsets, with 30 clips declared "England English" and 1 declared
"United States English", no shared clip, both in the development partition.
Common Voice asks for accent per clip and accepts more than one answer, so this
is a property of the source rather than a packaging error. A speaker in both a
comparison group and its control would shrink the very difference 22E8 measures,
and assigning them to whichever group they recorded more clips for would be
arithmetic papering over an ambiguity that is in the evidence. Both manifests
record the exclusion and pin the frozen exclusion record by hash, and 22E8 must
honour it. Every other pair shares no speaker and no clip.

*The comparison groups and their splits.* British Isles English holds 215,340
clips from 3,543 speakers; American male 295,743 clips from 5,705 speakers;
American female 115,209 clips from 1,795 speakers; and the Australian subset
already held is 55,922 clips from 804 speakers. Every subset went through the
same `audit_common_voice` function rather than a parallel one, because a
comparison between groups is only fair if every group was split, deduplicated and
sealed by identical code. Supplied train, dev and test map to development,
threshold tuning and sealed held-out evaluation, no client identifier crosses a
split in any subset, and no held-out speaker was read.

*Proof of acquisition is deliberately not self-referential.* Each file must match
the size its publisher declares, its SHA256 is recomputed here by re-reading the
finished file from disk rather than trusting anything the network reported, and
where a publisher states a digest it must match. A file failing any of the three
is deleted rather than kept, because a plausible looking truncated corpus is
worse than a missing one. That guard fired for real: the American male download
stopped at 7,747,469,312 of 10,394,299,015 bytes and the partial file was
discarded. Downloads now resume from what arrived and request a fresh URL each
attempt, because a presigned link expires while the earlier attempt is still
running; the retry completed and matched the published digest exactly. Three
tests cover the recovery path, including a server that ignores a range request
and restarts the body, which must not be concatenated onto the existing bytes.

*Two sources are pinned because their publishers do not version them.* WikiPron
publishes a continuously updated scrape, so both files are pinned to commit
`d282e848a211ea31cfd730f0ced8bc8cdab9e83d`, which is itself the commit that
changed the English dialect selectors and would have silently altered an unpinned
reference. Kaikki regenerates weekly and publishes no checksum, so the acquired
archive is the only fixed record of those bytes and its version is the underlying
enwiktionary dump date of 2026-07-06. The Mozilla Data Collective terms page is
served with a per-request build identifier, so two captures of word for word
identical terms produce different digests; `access.terms_version` is the stable
identifier of what was agreed and the digest pins the bytes retrieved on the day.

*The committed numbers are generated, not typed.* `build_open_stack_manifests.py`
produces every manifest by reading the acquired files, and a test rebuilds each
one and compares it byte for byte with the committed copy whenever the private
material is present. One absent source skips only itself rather than disabling
the check for the rest. Four manifests replace their 22E6 pending versions and
three are new; the registry holds 22 sources; and a lexicon is exempted from
participant split rules through an explicit `is_lexicon` profile flag, so a
speech corpus can still never skip its split.

*Acquiring a lexicon does not give it a truth class.* All four reference sources
keep `truth_class: unavailable` after acquisition exactly as they had it before,
and only the reason changed: not that the material could not be obtained, but
that a word list proposes how a word may be said and never observes how anybody
said it. No new schema value was invented to make that look better.

The whole suite passes at 513 tests, including 41 in
`tests/test_speech_sound_corpus_manifests.py`, of which 19 are new. Every
validator still passes fail closed and the selection record still reports
`no_selection`. `open-stack-runbook.md` reproduces the checkpoint.

The required normal two-speaker conversation pipeline acceptance run completed in
an isolated output directory without `--me`, in 340 seconds under `caffeinate`,
with all fourteen stages reporting complete. The listener returned normally on
its first attempt in 26.8 seconds. The evaluator degraded safely with
`semantic_validation_failure` after 80.9 and 62.6 seconds, so coaching and claim
verification were unavailable while every objective artifact stayed intact,
repeating the intermittent enrichment behaviour recorded since 22C rather than a
regression introduced here. Both attempts finished far inside the 300 second
deadline, and their durations sum to 143.5 seconds against a 144.9 second stage
wall clock, a 1.4 second difference, which is the evidence that the machine
stayed awake. The run produced no speech-sound artifact and no speech-sound field
in `master.json`, the root `output` directory was untouched, and the before and
after hashes of `history.json` and `progress.md` were identical.

#### 22E8. Repair the reference variety and probe Australian bias

The project has been scoring speakers against an American reference. For
SpeechOcean762 that was correct, because its reviewers judged against American
English. For an Australian speaker it is a defect, and it is one this project has
never measured because it has never run on Australian speech at all.

- Build a British-referenced expected-phone path from the Montreal Forced Aligner
  English (UK) dictionary, kept strictly separate from the American path built
  from English (US). Neither replaces the other; the variety becomes an explicit
  declared input. **This is a change from the original brief, made on 22E7
  evidence rather than preference.** The brief expected WikiPron
  `eng_latn_uk_broad` to carry this path. Measured, that file places a
  post-vocalic rhotic in 6.85 percent of its entries against the aligner
  dictionary's 0.01 percent, and carries 239 distinct symbols against its 78,
  because volunteers add loanword pronunciations. It supplements the British
  reference for coverage and variants; it is not fit to be it. The two aligner
  dictionaries also share one phone alphabet, so the two reference paths differ
  in variety alone, which the original pairing could not have guaranteed.
- Overlay the Australian-tagged Wiktionary entries where they exist. Where the
  British and Australian references disagree and no Australian entry exists, the
  opportunity is `unscorable`. Where they agree, it is scorable.
- The comparison accent subsets are already held. Checkpoint 22E7 acquired
  British Isles English, American English (Male) and American English (Female) of
  release 26.0, all CC0, all split and sealed. **The American group is built from
  both gender subsets and neither may stand alone.** One contributor appears in
  both the American male and British subsets, having declared different varieties
  on different clips; the frozen exclusion record names them and this checkpoint
  must exclude them from both groups.
- Run the existing segmentation-free GOP path over the development partitions of
  the Australian, British Isles and American subsets, under both the American
  reference and the British and Australian reference. Report the per-consonant
  flag rate for every speaker group under every reference. Held-out speakers in
  every subset stay sealed.

**Why the accent subsets matter more than the probe itself.** The confound that
would otherwise ruin this measurement is recording quality: microphone and
environment vary between contributors, and a difference between two corpora
recorded in different decades on different equipment says nothing about accent.
Comparing accent subsets *of the same release, collected on the same platform,
from the same prompt pool, under the same validation process* removes almost all
of that. What remains is the variable of interest.

That design also makes the result falsifiable in both directions rather than
merely suggestive. Under an American reference, Australian and British speakers
should be flagged more often than American speakers, and if they are not, the
premise of this checkpoint is wrong and must be recorded as wrong. Under the
British and Australian reference, the Australian and British gap should shrink
while the American group stays roughly unchanged, and if the American group also
moves the repair is doing something other than what it claims. British Isles is
the informative middle case: it is the variety the new reference actually
describes, so it should improve most cleanly, and the Australian residual after
repair is then a fair estimate of what genuinely Australian reference data would
still be worth.

**What this can and cannot establish, declared before it runs.** These are
native speakers reading known text, so a flag is presumed a false concern rather
than a detected error. That makes this a false-concern and differential-rate
measurement. It can demonstrate that the system flags Australian speakers more
often than the comparison group, and it can demonstrate whether the reference
repair reduces that gap. It cannot establish that the system correctly detects a
genuine Australian mispronunciation, because no Australian expert phone labels
exist in this project or, so far as the search could establish, in any
commercially usable form anywhere. Nothing here is a selection, and the five
frozen gates are not applied, because this is not a detection benchmark.

Recording quality is a confound and must be reported as one, not silently
absorbed: microphone and environment vary across Common Voice contributors, and
a difference between two reference paths on the same audio is far better
evidence than a difference between two corpora.

Acceptance: a versioned report giving per-consonant flag rates under each
reference, the differential against the comparison group, the change produced by
the repair, declared confounds, and an explicit statement that no detection
accuracy claim is made. The held-out set stays sealed. No gate moves. No system
is selected.

**Completion evidence on 2026-07-30.** 2,400 clips from 1,200 speakers, 300 per
subset and two clips each, all from development partitions, each scored under
both references. The committed artifacts are `variety-probe-contract-v1.0.0.json`,
frozen before any speaker was scored, and `variety-probe-v1.0.0.json`.
`variety-probe-runbook.md` reproduces it.

*The central prediction failed, and is recorded as failed.* The contract
predicted that the American reference would flag Australian speakers more often
than American speakers. It did not. The Australian differential is **negative at
all five thresholds**, minus 0.0035 at the reporting threshold, before and after
a phone mapping correction, and negative again with the conditioned palatal
series excluded. The contract obliged this to be written down as a wrong
prediction rather than explained away, and the report's validator now fails if
anyone records it as held.

*It held for British speakers, which is the case that carries the argument.*
British speakers were flagged plus 0.0115 above the American control under the
American reference and plus 0.0053 under the repaired one, so the repair roughly
halved the gap. This is the informative middle case behaving as predicted,
because British is the variety the repaired reference actually describes.

*The group mean was the wrong statistic, and hid a real effect.* On the two
consonants where the varieties genuinely differ, the predicted penalty is present
and large. Under the American reference, Australian speakers were flagged 0.030
more often than American speakers on the rhotic and 0.030 more often on `t`.
Under the repaired reference `t` falls to plus 0.002 and the rhotic to minus
0.008. A mean across roughly thirty consonants cannot see an effect carried by
three of them. **The checkpoint's hypothesis was sound and its headline statistic
was not**, and that only surfaced because the contract required per-consonant
reporting alongside the group mean.

*The repair works by declining to ask, not by fitting better.* This is the
finding the contract's control-group test was for. The repaired reference lowered
the flag rate in every group including the American control it should have left
alone, by about 2.9 points. The mechanism is visible in the rhotic: Australian
rhotic opportunities fall from 1,013 to 664, and the American control's own
rhotic flag rate falls from 0.306 to 0.044, because a non-rhotic reference stops
expecting a coda r **for everybody, including the Americans who produce it**.
That is legitimate under this project's standing rule, since where varieties
genuinely differ the opportunity is unscorable and a mismatch may be excluded but
never subtracted. It is not evidence that the reference now describes Australian
speakers more accurately, and the report makes no such claim. The honest headline
is that the American reference over-flags non-American speakers on the specific
consonants where varieties differ, and that a British reference removes those
false concerns by declining to score them.

*Two phone mapping defects were found by the measurement and corrected in the
open.* Both were the same mistake, preserving the aligner's symbol where its
function mattered. `ɫ` was expected although the frozen model emits it zero times
across 25 clips while emitting `l` 28 times, so 100.0 percent of those
opportunities were flagged in every group. `d̪` was mapped to `d` when the
aligner uses it for the consonant of *the*, *that* and *this* at 0.99 probability
and the model uses `ð`, which mis-expected the most frequent consonant context in
English and flagged about half of some 1,300 opportunities. Neither faked an
accent difference, because both hit every group equally; they inflated the
baseline by about seven points, which is how the control-group test caught them.
Phone mapping version 1.1.0 corrects them, cites the first run as the evidence
that prompted it, and the first run is retained in full at
`report-mapping-v1.0.0.json`, SHA256 `392c610d…`, with its evidence and sample.
The clip set is identical between the two runs, so the versions are directly
comparable, and the differentials moved by less than 0.0005. Correcting a mapping
and presenting clean numbers as though nothing had happened would have hidden the
most instructive part of this checkpoint.

*What was not done.* No gate was applied, the frozen benchmark and the selection
record were untouched, no system, threshold or reference was selected, no
held-out or threshold-tuning speaker was read in any group, and the pipeline is
unchanged. `tests/test_speech_sound_variety_probe.py` adds 23 tests, including
that a failed prediction cannot be relabelled as held, that a release boundary
cannot be opened, that the recorded mechanism must match the opportunity counts,
and that the declared confounds and stated limits cannot be emptied. The whole
suite passes at 536 tests and all six validators pass fail closed.

The required normal two-speaker conversation pipeline acceptance run completed in
an isolated output directory without `--me`, in 316 seconds under `caffeinate`,
with all fourteen stages reporting complete. The listener returned normally on
its first attempt in 24.0 seconds. The evaluator degraded safely with
`semantic_validation_failure` after 67.6 and 47.5 seconds, both far inside the
300 second deadline, repeating the intermittent enrichment behaviour recorded
since 22C rather than a regression introduced here. The run produced no
speech-sound or variety-probe artifact and no such field in `master.json`; the
only matches for the word variety are the long standing `vocab_variety` language
metric. The root `output` directory was untouched and the before and after hashes
of `history.json` and `progress.md` were identical.

#### 22E8 uncertainty, computed at item R2

Checkpoint 22E8 reported point estimates and nothing beside them. Item R2 of the
research release track computed what they were worth, from the same stored
per clip evidence, with no re inference, no acquisition and no new provider.

The rules that could have been bent to rescue a result were frozen first, in
`variety-probe-uncertainty-contract-v1.0.0.json`: the multiple comparison
families, the consonant inclusion rule, the resampling design and the seed, all
declared before a single interval existed. Only denominators were inspected
before freezing.

Method: speaker clustered bias corrected and accelerated bootstrap at 10,000
resamples, stratified within source so a resample cannot vary the American
group's male and female balance; one resample serving every reference,
threshold and consonant so the paired design stays paired; speaker label
permutation tests at 10,000 permutations, conditioned on which speakers had an
opportunity; and all three of uncorrected, Benjamini Hochberg and Bonferroni
published together. The per consonant analysis was changed to aggregate per
speaker then average, matching the group level analysis, which it previously did
not.

Outcome. Not one of the five pre registered group level comparisons is
distinguishable from zero, uncorrected or otherwise. The `t` differential, the
only per consonant result the mapping repair left standing, fails: significant at
one threshold only, sign reversed at minus three, below the smallest difference
this design could reliably detect for that consonant, and removed by both
corrections across its declared family. One test survives correction, `ð` for
British speakers under the American reference, stable across every threshold and
both references; it is reported with the disjoint prompt confound that stops it
being a claim about British English. A fourth result emerged from the work
itself: only 8 of 25 consonants keep their opportunity count within two percent
across the reference swap, so most cross reference comparisons are not like for
like, which withdraws the support for one sentence of the version 1.1.0 report.

The Common Voice training lineage overlap is **declared, not resolved**.
Resolving it needs a second phone model with no Common Voice lineage rescoring
the same 2,400 clips, which is deferred. The declaration is that the direction of
that bias is unknown, plausibly favours the control group, and that the observed
result runs against it, which makes the null conservative rather than suspect.

The report is `variety-probe-v1.2.0.json` at schema version 1.2.0. Versions 1.0.0
and 1.1.0 stay committed and deliberately no longer validate. The validator's
requirement inverted deliberately: it previously required the uncertainty state
to remain `not_computed` and now refuses a report that has lost it.

### 22F. Create the conservative research prompt pack

The two sources this checkpoint was originally written around are both gone.
Macquarie was never licensed and the owner declined to ask; Bookbot's claimed
provenance was disproved at 22E6. The pack is instead built from the open stack
acquired at 22E7, which changes its shape in one important way: the pack is
deliberately about twenty words, so the Australian-tagged Wiktionary entries are
not a thin dictionary but an ample pool. That pool was written here as roughly
2,700 before it was counted; 22E7 recounted it at 5,347 words carrying 11,328
pronunciations, of which 3,166 also carry a British reference, and the corrected
figure is used from here rather than the estimate. **We choose the words.**
Coverage of general vocabulary is irrelevant here; coverage of twenty
consonant-focused words we select is what matters.

- Select consonant opportunities supported by the acquired references, choosing
  words that carry both a British broad transcription and an Australian tag.
- Union the British reference with the Australian-tagged variants. Where they
  disagree and no Australian entry exists, the opportunity is unscorable.
- Do not use a generated target. Bookbot is barred, and no grapheme-to-phoneme
  model may define an accepted pronunciation.
- Mark disagreements, missing varieties and sensitive contexts unscorable.
- Keep written and recorded-prompt modes separate.
- Restate that the derived lexicon stays server-side, per the ShareAlike
  boundary recorded at 22E7.

Acceptance: the pack is versioned, phonetic opportunities are auditable,
licence provenance is complete for every accepted variant, no target is machine
generated and unsupported cases fail closed. This is a developer research pack,
not the active onboarding pronunciation task.

**Completion evidence on 2026-07-31.** Twenty words carrying 62 consonant
opportunities, 61 scorable and 1 refused, probing 21 consonants of which 20 reach
two or more word positions. The committed artifacts are
`prompt-pack-contract-v1.0.0.json`, frozen before any word was read out of a
dictionary, and `research-prompt-pack-v1.0.0.json`. `prompt-pack-runbook.md`
reproduces it. Nothing was scored, no speaker was read and no gate was applied.

*The pack is expressed in broad phonemes, and that was a decision rather than a
convenience.* The Montreal Forced Aligner dictionaries are narrower than the
brief assumed: English (UK) writes aspiration, palatalisation, labialisation,
dentality, dark l and syllabicity as separate phones, so its 78 symbols include
`tʰ`, `tʲ`, `c`, `ʎ`, `ɲ` and `ç` where English has `t`, `k`, `l`, `n` and `h`.
Scoring at that level would have asked a speaker to produce an allophone, and the
protocol makes broad IPA the default precisely because finer detail reduces
transcriber agreement. Every one of the 55 normalisation entries carries a
written reason, an unlisted symbol refuses the word rather than being dropped,
and a test asserts that every symbol the British dictionary actually uses is
named. Two entries repeat the lesson 22E8 paid for: the aligner's dental stops
are the consonants of *the* and *bath*, so `d̪` maps to `ð` and `t̪` to `θ`
rather than to `d` and `t`.

*The rhotic exclusion rule refuses nothing, and that is the finding.* Across the
whole eligible pool the post-vocalic rhotic rule fires zero times, because under
a non-rhotic British reference the opportunity does not exist to be refused. That
is the same mechanism 22E8 recorded from the other side: the repair works by
declining to ask rather than by fitting better. The pool report carries the zero
explicitly rather than omitting the key, because a rule that never fires and a
rule nobody wrote look identical in an absent field. The rules that do fire
across the pool are coda `t` at 417 opportunities, documented variant
disagreement at 377, intervocalic flapping at 367, coda `l` at 271 and the dental
fricatives at 70, against 7,709 scorable.

*The union rule had almost nothing to union, and the pack says so.* Nineteen of
the twenty words carry exactly one documented British form and one documented
Australian form, because requiring every documented form to agree tends to select
words that have only one. The safeguard's real effect is visible in the pool,
where 272 words were refused outright for disagreeing on how many consonants they
have. Recording that is the point: a rule stated in a contract and never
exercised in the artifact it governs would read as protection it did not
provide, and the validator fails if that limitation is removed.

*The eligible pool is 2,578 words and the constraint is Wiktionary's coverage,
not the aligner's.* Of the British dictionary's 46,167 head words, 42,735 carry
no Australian tagged pronunciation at all, which is 93 percent and by far the
largest refusal. A further 278 are affixes or contractions, 203 carry a symbol
neither normalisation table names, 95 carry a glottal variant in a documented
form, 272 fail the consonant count alignment and 6 hold no consonant at all.
Many ordinary words fall out
this way: *dog*, *house*, *apple*, *money* and *bottle* have no Australian tag.
Against a pack of twenty that pool is still ample by two orders of magnitude,
which is exactly what the brief predicted, but the shape of the loss is worth
recording because it will bind 22G's word supply too.

*The words were chosen by hand, openly, and then verified mechanically.* The
brief says we choose the words, and a pool 129 times the size of the pack makes
any automatic ranking a familiarity measurement this project does not hold. The
contract therefore names the twenty with a reason each, frozen before any
dictionary was read, and the builder refuses the whole build if one of them fails
any rule. A test confirms that substituting a word that is not eligible fails
closed. The pack reports the pool's size and refusal shape so the choice can be
seen as a choice.

*What the pack refuses to be.* `/h/` reaches one word position rather than two,
because English `/h/` occurs only in syllable onsets and the pool's single medial
candidate, *adhere*, is not an ordinary prompt; `/ʒ/` is not probed at all,
because it appears word-medially in three pool words and nowhere else. Both are
declared shortfalls in the contract and the validator fails if either is dropped.
The recorded prompt mode is deliberately not built, because a spoken prompt
carries the speaker's own variety and would have the person imitating an accent
rather than saying a word. And the onboarding word pack in
`assessment/pronunciation-research-v1.0.0.json` is untouched, still empty and
still awaiting professional review; the pack validator reads that file and fails
if it ever stops being true.

*The derived lexicon stays server-side.* The committed pack carries the twenty
words and their consonant opportunities with position, context, state and reason.
The verbatim British and Australian forms, the full phone sequences including
vowels, and the whole eligible pool are written to gitignored storage, because
that material is the derived lexicon and Wiktionary derived material is share
alike. What is committed is the pack's own measurement target, carries no vowels,
and is what makes an opportunity auditable at all.

`tests/test_speech_sound_prompt_pack.py` adds 63 tests, including that a refused
opportunity cannot be relabelled scorable while its own recorded position and
context still refuse it, that a declared coverage shortfall cannot be dropped,
that the derived lexicon boundary cannot be opened, that filling the onboarding
word pack invalidates this one, and that the committed pack rebuilds byte for
byte. Both the prevocalic and postvocalic contexts and the syllabic flag are
recorded beside every opportunity for that reason: a rule the validator cannot
re-derive is one that can be edited away. The whole suite passes at 599 tests and
all seven validators pass fail closed.

The required normal two-speaker conversation pipeline acceptance run completed in
an isolated output directory without `--me`, in 370 seconds under `caffeinate`,
with all fourteen stages reporting complete. The listener returned normally on
its first attempt in 33.0 seconds. The evaluator degraded safely with
`semantic_validation_failure` after 103.6 and 70.8 seconds, both far inside the
300 second deadline, repeating the intermittent enrichment behaviour recorded
since 22C rather than a regression introduced here; their durations sum to 174.4
seconds against a 176 second stage wall clock, a 1.6 second difference, which is
the evidence that the machine stayed awake. The run produced no speech-sound and
no prompt-pack artifact, and `master.json` carries no field matching
`speech_sound`, `prompt_pack`, `phoneme` or `scorable`; the only substring
matches for variety and opportunity are the long standing `vocab_variety` and
`response_opportunity_count` language metrics. The root `output` directory was
untouched and the before and after hashes of `history.json` and `progress.md`
were identical. An earlier run of the same acceptance on 2026-07-31 completed
equally cleanly in 383 seconds; it was rerun because three small refinements
landed after it, and although none of them is reachable from the pipeline, which
imports nothing from `speech_sound_patterns`, an acceptance run on code that is
not the committed code is not an acceptance run.

### 22G. Build candidate extraction and repeated-relation evidence

- Produce the validated developer artifact and allowed states.
- Preserve raw evidence and alternative explanations.
- Add the generic repeated-relation summary without named clinical patterns.
- Keep the artifact outside listener, evaluator, claims, coaching, history,
  progress, screening and diagnosis.

Acceptance: tests cover substitutions, deletions, insertions, variants,
conflicts, bad audio, unsupported contexts, missing models and provider
failure. One token and one word can never create repeated-relation evidence.

**Implementation result, 2026-08-03, committed.** The checkpoint is implemented,
verified and committed. It did not select a candidate
system or weaken a gate. Before any threshold or repeated-rule search, the
checksum-bound adequacy audit inspected only the already permitted development
and tuning evidence and stopped:

- development contains 12 adult prompt-pack word occurrences from 12
  participants, across 5 pack words, with 1 positive, 24 negative and 2
  unscorable coarse target labels;
- tuning contains 8 occurrences from 8 participants, across 3 pack words, with
  0 positive, 20 negative and 1 unscorable label;
- no participant supplies two distinct prompt-pack words;
- every matching word is embedded in a multiword sentence rather than elicited
  by the controlled isolated-word task;
- the truth is a coarse expected-target relation, not an exact produced phone or
  feature relation; and
- the pack reconstructs 49 expected sound opportunities, 45 scorable and 4
  unscorable, but there is no task-matched candidate support denominator.

The decision is therefore
`no_rule_selected_task_matched_evidence_unavailable`. No system, mapping,
feature rule, provider configuration, threshold or repeated-relation minimum was
searched or selected, and the 26 held-out adults remained sealed.

`candidate-artifact-contract-v1.0.0.json` freezes that negative decision before
the assembler can run. `candidate_artifact.py` and `extract_candidates.py`
implement a private, offline, no-overwrite artifact with word evidence, sound
opportunities, insertions, raw system proposals, alternative explanations,
uncertainty, abstention, provenance and denominators. All automatic sound states
fail closed. The possible-relation and repeated-relation structures exist for
auditing, but both emission paths are disabled and an arbitrary rule dictionary
is rejected. Repetition counts a stable recording and opportunity index once,
requires matching participant, task, pack, elicitation mode and relation, keeps
distinct tokens in one recording distinct, excludes unscorable variants from the
eligible denominator, and cannot count insertion observations as expected
sounds.

Source provenance is exact rather than declarative. The current extractor
accepts only a synthetic structural fixture or Adam's owner-controlled recording
for local functional integration. Both are barred from selection evidence.
Every real audio and evidence lane must be checksum bound under the private
research root. SpeechOcean remains bound by the corpus registry, licence,
development-and-tuning whitelist, source reference and expert relation hashes
for the aggregate adequacy audit, but its sentence recordings cannot masquerade
as the controlled written-word task. The full participant split file, which
contains held-out identities, is never opened.

Verification is complete:

- all eight fail-closed validators pass;
- the full suite passes at 694 tests;
- adversarial type mutation covered 655 manifest mutations and 5,885 artifact
  mutations without an uncaught exception;
- the committed prompt pack is byte and checksum bound even when a caller
  supplies an in-memory pack;
- the standalone validator distinguishes validating the contract and aggregate
  report from validating a supplied private manifest-backed artifact; and
- the normal pipeline still imports no candidate extractor module or speech
  sound artifact.

The required real two-speaker conversation regression ran under `caffeinate`
with no `--me` and a fresh isolated output directory. Run
`20260803T133657cdc40dc7` completed all 14 stages in 356 seconds. Diarization
took 139.014 seconds, listener enrichment completed normally in 26.631 seconds,
and the evaluator rejected two unsafe drafts after 52.7 and 113.7 seconds before
degrading safely with `semantic_validation_failure`. Objective artifacts
remained intact. No file or field matching `speech_sound`, `prompt_pack`,
`phoneme`, `scorable`, `candidate_artifact` or `repeated_relation` appeared in
the master, evaluation or verification outputs. Root `history.json` remained
`156b418a9c83de0c860eaba06bd10e714cd00da8c200e99a268546c7651d0ed5`,
root `progress.md` remained
`1b05ca629d342825db45534d1d7ddeeb184f105ad56e1f74c6c6bd6757b91347`,
and the combined checksum of the existing root `output` files remained
`c867456300077037098d4ee9dd2f7946ab8b05b40829afa50ea801305aa8cf4f`.
Checkpoint 22H later received separate explicit owner instruction and is
recorded below. This 22G evidence remains unchanged.

### 22H. Held-out and repository acceptance

- Freeze the absence of a selected system, candidate output mapping, feature
  rule, provider configuration, threshold and repeated minimum, plus the
  inactive prompt pack, before repository acceptance.
- Apply Adam's 2026-08-12 approved no-selection resolution. Do not open the
  private split assignment, participant identities, labels, audio or derived
  rows. Report every predeclared held-out metric as unavailable because there
  is no eligible method to evaluate. Unavailable is not zero, pass or failure.
- Keep expert relation accuracy, timing-fixture performance and robustness
  evidence separate; do not combine them into one headline score.
- Record owner integration as unavailable. The repository contains no
  task-matched controlled written-word recording, and ordinary conversation,
  solo and accent-contrast sentence recordings cannot substitute.
- Run the full normal conversation pipeline in an isolated output directory
  without `--me` and verify no speech-sound evidence enters coaching or root
  history.
- After the aggregate report, active research contract and documentation are
  final, rerun all non-destructive acceptance checks and bind the post-report
  public repository in an immutable no-overwrite closure.

Acceptance: all predeclared metrics and limitations are reported, ordinary
pipeline behavior is unchanged, personal files are untouched, and scientific
and product release remain explicitly locked. This resolution is conditional
until the aggregate report and repository closure both validate.

**Implementation result, 2026-08-12.** Adam approved the conservative sealed
path before implementation. `final-acceptance-contract-v1.0.0.json` froze the
absence of a selected system, mapping, feature rule, provider configuration,
threshold and repeated minimum, bound every historical input and source
manifest, and predeclared the exact unavailable held-out surface before the
runner was used.

The aggregate `final-evidence-v1.0.0.json` passed. No private split,
participant identity, label, audio or derived held-out row was opened. All 40
predeclared held-out measures carry `availability: unavailable`, null numerator,
denominator, value, uncertainty and gate result, and the reason
`not_evaluated_no_selected_candidate`. None is presented as zero, pass or
failure. The sealed source facts remain visible without becoming results: 15
adult female, 11 adult male, 10 child female and 14 child male participants.
Source-specific expert relation evidence, human-corrected timing evidence,
automatic alignment evidence, sentence-audio robustness and pronunciation
reference forms remain separate truth classes. Model overlap and the absence of
expert Australian produced-phone relation evidence remain explicit.

The real two-speaker conversation pipeline ran under `caffeinate` in a fresh
isolated directory without `--me` or session context. All 14 stages completed in
382.927 seconds and the process completed in 383.184 seconds. The referee and
listener completed normally. The evaluator made two attempts and used its
existing safe `semantic_validation_failure` unavailable state. All four
independent regression checks passed. The expected 15 required and 2 optional
artifacts were accounted for, no item 22 import, stage, filename, key or strong
content token leaked, and `history.json`, `progress.md`, the existing root
`output` and the pre-run public repository stayed byte-identical. The focused
acceptance suite passed 35 tests and the full suite passed 729, both with zero
skips at the acceptance run. No quota exhaustion occurred.

Owner functional integration is recorded as
`not_performed_no_task_matched_owner_recording_available`. The repository has no
controlled written-word owner recording for the frozen task, and ordinary solo,
conversation and accent-contrast sentence recordings were not substituted.
Research contract version 1.7 binds version 1.6 unchanged and records this
no-selection final state without opening a release. The final aggregate report
is still not the completion boundary by itself: item 22 becomes engineering
complete only when `repository-closure-v1.0.0.json` exists and the final
validator accepts its immutable post-report snapshot.

## Item 22 engineering definition of done

Item 22 may be called engineering complete only when all checkpoints above are
committed separately, the final evidence report exists and the post-report
repository closure validates. On the approved no-selection path, completion
means:

- a validated developer-only contract and artifact;
- a reproducible local evidence assembler that remains unable to emit an
  automatic relation without adequate task-matched evidence;
- a documented no-selection decision, with no provider or local method
  misrepresented as selected;
- participant-exclusive development and tuning results plus explicit unavailable
  held-out records, with truth class, source lineage, model overlap and sealed
  adult and child population strata reported;
- an Australian variant strategy with Macquarie status and ANDOSL or equivalent
  expert-evidence status recorded;
- explicit unsupported and unavailable behavior;
- generic repeated-relation evidence without clinical labels;
- no leakage into user-facing or longitudinal systems; and
- a clean full pipeline acceptance run.

It does not mean population validation, clinical validity or product release.

## Effect on later work

- The controlled pronunciation research in Phase B may later reuse the
  manifest framework, recorded Macquarie licence status, Australian corpus stress evidence,
  prompt-pack provenance and provider bake-off. It remains a separate task and
  release decision.
- Item 23 is scientifically independent. It is waiting only because repository
  workflow requires item 22 to be completed before the next roadmap item.
- Item 24 may later reuse the manifest framework and system-level evidence from
  Common Phone, Common Voice, Acted Clear Speech and LibriSpeech, but
  personalised recognition requires its own task-specific participants,
  splits and frozen held-out evaluation. Item 22 held-out data cannot silently
  become item 24 tuning data, and no item 22 result approves item 24.
- No account, licence or item 22 result automatically approves items 23, 24 or
  any clinical feature.

## Spending and privacy boundaries

- No purchase, subscription, external request or GPU rental is automatic.
- Adam creates accounts and accepts terms.
- Spend is approved immediately before a fixed benchmark run so subscriptions
  are not wasted.
- Public-corpus licences and provider terms are checked together before audio
  leaves the machine.
- Personal audio stays local unless a separate consent and privacy decision
  explicitly permits a named provider and purpose.
- Raw licensed data, credentials and provider responses that prohibit
  redistribution are gitignored and represented only by safe manifests.
- No corpus is obtained from Academic Torrents or another unlicensed mirror.
- Mozilla Data Collective access terms are recorded with the corpus manifest,
  including redistribution, reidentification and account-termination duties.

The governing scientific boundaries remain in
`speech_sound_patterns/research-and-protocol.md`. Checkpoint 22H makes
`speech_sound_patterns/research-contract-v1.7.0.json` active. It binds version
1.6 byte-for-byte unchanged and adds the release-locked final contract, safe
aggregate report and mechanically required repository closure. Earlier
contracts remain unchanged historical records; the active research validator
is version specific. No product research task or user-facing artifact is
active, and the private extractor cannot emit a relation under the no-selection
decision. No later roadmap item is approved, and every third-party right must
pass independently. The temporary
checkpoint 22E provider verification handoff was absorbed into this plan, the
acquisition register and the lane reasons, and was deleted on 2026-07-29 with
Adam's approval, exactly as its own closing section asked once that was true.
