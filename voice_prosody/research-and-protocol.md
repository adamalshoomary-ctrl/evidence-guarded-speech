# Voice and prosody primitive research and protocol

Version: 1.0.0  
Status: engineering active, scientific release locked  
Updated: 2026-07-20

## Decision

Phase C begins with low level acoustic observations, not a voice score or a
judgement about how somebody should sound. The pipeline may measure estimated
fundamental frequency, digital recorder level and their timestamped behaviour.
It may calculate task-specific CPPS as research evidence. Jitter and shimmer
are limited to the separately consented sustained-vowel research task.

The item does not introduce a remote or generative AI service. These
measurements are local, deterministic and version pinned. A future model may be
evaluated only if it improves held-out reference performance and preserves
explicit failure behaviour. Agreement between algorithms is a quality warning,
not truth.

No output in this item means confident, nervous, expressive, monotone, shaky,
healthy, disordered, masculine, feminine, professional, good or bad. No
primitive enters a combined score, personal progress, ranking, screening,
diagnosis or high-stakes decision.

## Why the legacy acoustic output is not enough

The legacy stage was useful for a prototype renderer, but it is not a valid
measurement contract:

- it called digital level relative to the file maximum `loudness_db`, although
  it is neither sound pressure level nor calibrated perceived loudness;
- it sampled level every 500 ms and pitch every 50 ms, which is coarse for
  timestamped prosody;
- it summarized pitch variation with ordinary standard deviation in hertz,
  which is register dependent and sensitive to tracking errors;
- it concatenated separated diarization regions before cycle-level analysis,
  creating waveform boundaries that the speaker did not produce;
- it applied jitter and shimmer to ordinary connected speech;
- it used whole-file duration as though it were usable voiced evidence;
- it mixed speakers in whole-conversation summaries and allowed the result to
  remain citeable with only a warning;
- it did not store the task, device context, exact pitch configuration, valid
  voiced frames, rejected evidence or structured failure reason;
- its notes equated low pitch variation with monotone speech and high
  perturbation with a shaky voice.

The protected renderer continues to receive its existing compatibility tracks
and thresholds. Item 20 adds a separate measurement path so improved evidence
does not silently change renderer behaviour.

## Construct definitions

### Fundamental frequency

Fundamental frequency, or F0, is the algorithm's estimate of the repetition
frequency of a periodic acoustic signal during voiced speech. It is measured in
hertz. It is related to perceived pitch but is not identical to it.

The pipeline stores the timestamped contour as primary evidence. Summaries are
the median and robust percentiles of eligible voiced frames. Distribution span
is the fifth-to-ninety-fifth percentile distance converted to semitones. This
is labelled a distribution span, not intonation range or expressiveness,
because global percentiles do not identify linguistically meaningful pitch
targets.

Pitch settings materially change the result. The artifact therefore stores the
floor, ceiling, time step, voicing threshold, silence threshold, boundary hits,
pitch strength and suspected octave jumps. Values at silence are `null`, never
zero hertz.

Tracking uses two declared passes. A broad 50 to 800 hertz pass estimates each
speaker's median without using gender or identity. A second raw-autocorrelation
pass uses a symmetric three-times range around that median, bounded by the
broad limits. The artifact stores the actual per-speaker floor and ceiling.
This reduces octave errors seen in the real conversation while retaining an
explicit boundary failure state. It is an engineering safeguard, not natural
voice-range validation.

The contour also counts both sudden octave jumps and persistent clusters near
one octave from the speaker median. A cluster is only an error candidate, not
proof. If it is large enough to distort distribution tails, those percentiles
and the span become unavailable while a robust median may remain observable.

Praat documents pitch range as the most important pitch-analysis setting and
explains the time-resolution tradeoff. Its current guidance distinguishes
filtered autocorrelation for intonation from cross-correlation for voice
analysis. The installed Parselmouth build contains an older Praat engine, so
item 20 names and pins the actual raw-autocorrelation implementation rather
than claiming the newer filtered method.

- [Praat pitch methods](https://praat.org/manual/Pitch.html)
- [Praat pitch configuration](https://praat.org/manual/Intro_4_2__Configuring_the_pitch_contour.html)
- [Boersma, 1993](https://www.fon.hum.uva.nl/paul/papers/Proceedings_1993.pdf)
- [de Cheveigne and Kawahara, 2002](https://pubs.aip.org/jasa/article/111/4/1917/547221/YIN-a-fundamental-frequency-estimator-for-speech)

### Digital recorder level

Recorder level is root mean square digital amplitude expressed in dBFS, where
full scale is the recording system's digital maximum. It is not physical sound
pressure level. It changes with microphone sensitivity, distance, angle, gain,
automatic gain control, noise processing, codec and room.

The pipeline may store dBFS percentiles and within-capture percentile span. It
must not label them vocal SPL or compare absolute level across devices. True
dB SPL remains unavailable without calibration of the complete recording chain
against an appropriate acoustic reference.

- [ASHA instrumental voice protocol](https://pubs.asha.org/doi/10.1044/2018_AJSLP-17-0009)
- [Praat sound pressure calibration](https://praat.org/manual/sound_pressure_calibration.html)
- [Švec and Granqvist, 2018 calibration guidance](https://pubmed.ncbi.nlm.nih.gov/26161588/)

### Cepstral peak prominence

Smoothed cepstral peak prominence, or CPPS, describes the prominence of the
dominant periodic peak above a cepstral background trend. The algorithm and
task materially affect its value. CPPS from a sustained vowel, fixed reading
and spontaneous speech are not interchangeable.

ASHA recommends cepstral measures because they can be applied to sustained
vowels and connected speech and are less restricted than traditional
perturbation measures. Item 20 nevertheless keeps CPPS research only. It does
not copy a clinical cutoff or interpret a value as dysphonia, breathiness or a
voice disorder.

- [ASHA instrumental voice protocol](https://pubs.asha.org/doi/10.1044/2018_AJSLP-17-0009)
- [Praat CPPS algorithm](https://praat.org/manual/PowerCepstrogram__Get_CPPS___.html)
- [Murton, Hillman and Mehta, 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7893528/)
- [Murton et al., 2023](https://www.isca-archive.org/interspeech_2023/murton23_interspeech.html)

### Jitter and shimmer

Local jitter estimates cycle-to-cycle period perturbation. Local shimmer
estimates cycle-to-cycle amplitude perturbation. They depend on valid pulse
detection and a nearly periodic, steady signal. They are not general connected
speech or conversation measures.

The only eligible task is three comfortable three-to-five-second sustained
`ah` repetitions with separate research consent. Each continuous repetition is
analysed independently. Onset and offset are excluded through a prespecified
middle segment. Values are aggregated only after the separate repetition
results are retained. No calculation crosses a silence, speaker change,
overlap or artificial join.

The device evidence for jitter and especially shimmer is inconsistent. They
remain research only even when the software produces a number.

- [Praat jitter guidance](https://praat.org/manual/Voice_2__Jitter.html)
- [Praat shimmer guidance](https://praat.org/manual/Voice_3__Shimmer.html)
- [Brockmann-Bauser et al., 2019](https://pubmed.ncbi.nlm.nih.gov/30779425/)
- [Fahed et al., 2022](https://doi.org/10.1016/j.jvoice.2022.10.006)

## Task separation

Every value belongs to one task ID, task version, prompt version and attempt.
The following tasks cannot be silently pooled:

- fixed reading controls words and phonetic content but depends on literacy,
  preparation and the passage;
- listen-and-repeat adds hearing, memory, playback and imitation effects and is
  not equivalent to reading;
- spontaneous speech is natural but depends on content, planning, language,
  emotion, topic and context;
- goal-specific speech also depends on the declared real-world situation;
- conversation contains interaction, overlap, attribution uncertainty and
  short fragments, so only exclusive contiguous speaker regions are eligible;
- repeated phrases are prompt specific and provide within-session consistency
  evidence only;
- a sustained vowel deliberately samples steady phonation and cannot represent
  ordinary prosody or communication.

A developer run without a session context remains supported, but its task is
`unknown_ad_hoc` and it is noncomparable. Context-free values can test software
operation and describe one capture; they cannot establish progress or a task
norm.

## Device and capture limits

Frequency-derived features often transfer across consumer devices better than
amplitude and perturbation features, but no device class is assumed equivalent.
Room, distance and processing can matter as much as the microphone.

The runtime stores the existing nonidentifying device class, platform,
microphone category and source. It does not collect a hardware fingerprint.
Unknown automatic gain control, echo cancellation, noise suppression or codec
processing remains an explicit limitation.

Research has found:

- mean F0 and CPPS can show acceptable smartphone agreement while jitter and
  shimmer show problematic random error;
- mobile-device agreement is stronger for frequency-derived measures than HNR
  and shimmer in several structured tasks;
- device proximity can bias amplitude and sometimes F0;
- room acoustics and background noise can affect measures more than microphone
  choice;
- lossy compression can alter jitter, shimmer, HNR and CPPS;
- a 2024 crossed-device study found F0 and CPP comparatively reliable for
  sustained phonation, but not every feature or task generalized.

Sources:

- [Influence of smartphones and software, 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5536725/)
- [Smartphone bias and random error, 2019](https://pubmed.ncbi.nlm.nih.gov/30779425/)
- [Room and microphone reproducibility, 2018](https://pubmed.ncbi.nlm.nih.gov/30471944/)
- [Voice analytics in the wild, 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10228884/)
- [Cross-device and test-retest reliability, 2024](https://doi.org/10.3758/s13428-024-02584-0)
- [VoIP and compression effects, 2010](https://pmc.ncbi.nlm.nih.gov/articles/PMC2945273/)
- [Opus compression effects, 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC11529786/)

## Failure behaviour

Every primitive has an availability state and exact reason. Relevant reasons
include:

- task unknown or ineligible;
- research consent missing;
- insufficient voiced frames or duration;
- fewer than three valid sustained-vowel repetitions;
- clipping, low level, low signal-to-noise proxy or reverberation risk;
- level instability or unknown gain processing;
- overlap or speaker attribution uncertainty;
- pitch floor or ceiling hits;
- suspected octave errors or implausible contour discontinuity;
- codec or capture condition not validated;
- algorithm failure.

Missing or rejected evidence is `null`. It never becomes zero, a normal value,
a score or an LLM estimate. A whole-recording conversation summary is not
person-level evidence.

## Validation programme

### Deterministic software controls

Generated signals have known F0, pitch glides, digital level changes, silence,
noise, clipping, pitch-range edges, octave-confusion stress and separated
regions. They test numerical behaviour and explicit failure. They do not
validate human voice meaning.

Frozen Praat outputs can cross-check implementation, but Parselmouth and Praat
share an engine and therefore do not form independent truth.

### Natural pitch and voicing reference

Pitch tracking must be evaluated on participant-disjoint data with a
simultaneous laryngograph or electroglottograph reference, such as PTDB-TUG,
plus trained review of disagreements. Report voicing precision and recall,
median and tail error in cents, gross pitch error, octave doubling and halving,
and abstention. An EGG reference is evidence, not perfect truth.

- [PTDB-TUG corpus paper](https://www.spsc.tugraz.at/system/files/InterSpeech2011Master_0.pdf)

### Device validation

The same production must be recorded simultaneously with a calibrated
reference chain and representative phones and laptops. Device, platform,
capture path, codec, distance, angle, room, noise and processing state are
varied deliberately. Bias and limits of agreement are reported against
predeclared intended-use tolerances. Correlation or a nonsignificant difference
does not prove agreement.

- [Bland and Altman, 1986](https://pubmed.ncbi.nlm.nih.gov/2868172/)
- [GRRAS reporting guidance](https://pubmed.ncbi.nlm.nih.gov/21130355/)

### Task and human repeatability

Independent participants repeat fixed reading, spontaneous speech, repeated
phrases and approved probes across sessions and days. Development participants
set metric-specific minimum evidence and error limits. The algorithm and
limits are frozen before held-out evaluation. Task, device, room, voice range,
language, accent, audio quality and speech differences are reported rather
than hidden.

Adam's two recordings are functional integration evidence only. They cannot
establish acoustic accuracy, task validity, device equivalence, fairness,
natural variation or meaningful personal change.

## Release gate

A primitive may leave research status only after its construct, task, unit,
algorithm, settings, confounders and failure behaviour are fixed; synthetic
correctness and exact-input repeatability pass; independent reference accuracy,
task repeatability and device agreement meet prespecified bounds on held-out
participants; subgroup uncertainty is reported; and the pipeline abstains when
conditions are unsuitable.

After item 20, personal progress, cross-device progress, combined indices,
ranking, screening, diagnosis, clinical cutoffs and high-stakes decisions all
remain blocked. Later roadmap items require their own owner approval.

## Engineering acceptance for item 20

Item 20 is engineering complete only when:

1. the machine-readable contract validates and is included in provenance;
2. acoustic extraction is importable, deterministic and task aware;
3. no cycle-level calculation crosses a separated region;
4. new timestamped frames store F0, pitch strength, dBFS, speaker, region and
   quality flags at the original recording time;
5. robust per-speaker summaries expose real voiced evidence and failure state;
6. legacy renderer tracks and all six protected thresholds remain unchanged;
7. unsupported jitter and shimmer are unavailable rather than ordinary-speech
   evidence;
8. device and task context are visible, with unknown context noncomparable;
9. synthetic correctness, task gating, quality degradation, compatibility,
   provenance and exact-repeatability tests pass;
10. isolated solo and conversation pipeline runs complete without `--me`, do
    not change personal history, and satisfy their real-recording truth checks.
