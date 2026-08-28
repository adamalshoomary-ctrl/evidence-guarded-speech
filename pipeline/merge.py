"""
Step: the merger (v4). Listener no longer consumed here -
the listener now runs AFTER merge and enriches master.json directly.
Combines all extractor outputs into ONE master document.

New in v3:
- word attribution by OVERLAP SHARE (not midpoint) against diarization turns
- sliver diarization turns (<0.3s) suppressed before assignment
- SMOOTHING: single-word speaker flips inside another speaker's run are
  reabsorbed unless the word's own pitch strongly supports the flip
- PITCH VOTER: where diarization and AssemblyAI disagree on a word, the
  word's measured pitch votes using each speaker's pitch profile
- BACKCHANNELS: short interjections ("yeah", "no way?") inside another
  speaker's run are rendered inline as [SPK: "..."] instead of shattering
  the turn - and counted as an engagement metric
- COMPUTED METRICS per speaker: deterministic numbers (filler rate, uptalk
  count, WPM, talk share, backchannels...) for stable, anchorable scoring
- Recalibrated thresholds (less sensitive): DRAG 1.9->2.3 with a 0.40s
  floor, CAPS +4.0->+5.5 dB, uptalk 1.12->1.18 with a 15 Hz floor

Saves /output/master.json and /output/master_preview.txt
Run:  python3 pipeline/merge.py
"""

import argparse
import json
import statistics
import sys
from copy import deepcopy
from pathlib import Path

from llm_contract import initial_enrichment_status
from measurement_evidence import (
    ASR_CONFIDENCE_THRESHOLD,
    build_measurement_metadata,
    is_low_asr_confidence,
)
from run_context import add_run_arguments, context_from_args

REPO_ROOT = Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser()
parser.add_argument("--rebuild", action="store_true",
                    help="reload speaker labels from words_attributed.json "
                         "(after referee.py edits) instead of re-attributing")
add_run_arguments(parser)
args = parser.parse_args()
context = context_from_args(args, REPO_ROOT)
OUT = context.output_dir

# ---- calibration knobs (v3: desensitised) --------------------------------
PAUSE_MIN = 0.7
DRAG_RATIO = 2.6          # floor: word must run 2.6x its expected length...
DRAG_MIN_S = 0.50         # ...AND at least 0.50s absolute
DRAG_PERCENTILE = 95      # ...AND be in this speaker's top 5% most-stretched words
LOUD_DB_ABOVE = 5.5       # dB above the speaker's own median for CAPS
RISE_RATIO = 1.18         # end-pitch vs start-pitch for uptalk...
RISE_MIN_HZ = 15.0        # ...AND at least +15 Hz absolute
SLIVER_S = 0.30           # diarization turns shorter than this are noise
BACKCHANNEL_MAX_S = 1.6   # interjection length cap
BACKCHANNEL_MAX_WORDS = 4
FILLERS = {"um", "uh", "erm", "hmm", "mm", "uhm", "er"}
VOWELS = "aeiou"

def load(name, required=True):
    p = context.output_path(
        name, required=required or context.run_id is not None
    )
    if not p.exists():
        if required:
            sys.exit(f"ERROR: missing {p} - run earlier steps first")
        return None
    return json.loads(p.read_text(encoding="utf-8"))

diar = load("diarization.json")
transcript = load("transcript.json")
alignment = load("alignment.json", required=False)
vad = load("vad.json")
acoustics = load("acoustics.json")
audio_quality = load("audio_quality.json", required=False)

words = transcript.get("words", [])

# ASR word end-times sometimes swallow the silence after a word, producing
# false drags (a "5.25s held" word that is really a ~1s word + ~4s pause).
# Before any duration is computed, clip each word's end to the end of the
# VAD speech chunk containing its start. Words whose start lies in silence
# (between chunks) are left unchanged.
speech_chunks = vad.get("speech_chunks", [])
clipped_count = 0
for w in words:
    w["start_s"] = w["start"] / 1000.0
    w["end_s"] = w["end"] / 1000.0
    for ch in speech_chunks:
        if ch["start"] <= w["start_s"] <= ch["end"]:
            if w["end_s"] > ch["end"]:
                w["end_s"] = ch["end"]
                clipped_count += 1
            break
    w["dur"] = max(w["end_s"] - w["start_s"], 0.001)
    w["mid"] = (w["start_s"] + w["end_s"]) / 2
print(f"Word-boundary clipping: {clipped_count} word end-times clipped "
      f"to VAD speech-chunk boundaries")

# sliver handling: too-short turns don't define structure, but they are
# kept as EVIDENCE of quick interjections
d_turns = [t for t in diar["turns"] if t["duration_s"] >= SLIVER_S]
slivers = [t for t in diar["turns"] if t["duration_s"] < SLIVER_S]
if not d_turns:
    d_turns = diar["turns"]
    slivers = []
n_speakers = len({t["speaker"] for t in d_turns})
solo = n_speakers <= 1
pauses = vad.get("pauses", [])
timeline = acoustics.get("timeline", [])
pitch_track = acoustics.get("pitch_track", [])

def overlap(a1, a2, b1, b2):
    return max(0.0, min(a2, b2) - max(a1, b1))

def loudness_at(t):
    if not timeline:
        return None
    idx = min(range(len(timeline)), key=lambda i: abs(timeline[i]["t"] - t))
    return timeline[idx]["loudness_db"]

def pitch_window(t1, t2):
    vals = [hz for t, hz in pitch_track if t1 <= t <= t2 and hz > 0]
    return statistics.mean(vals) if vals else None

# ------------------------------------------- 1. attribution by overlap share
def owners_at(t):
    return [d["speaker"] for d in d_turns if d["start_s"] <= t <= d["end_s"]]

for w in words:
    if solo:
        w["final_speaker"] = d_turns[0]["speaker"]
        w["speaker_confidence"] = "high"
        w["overlap_speech"] = False
        continue
    shares = {}
    for d in d_turns:
        ov = overlap(w["start_s"], w["end_s"], d["start_s"], d["end_s"])
        if ov > 0:
            shares[d["speaker"]] = shares.get(d["speaker"], 0.0) + ov
    w["overlap_speech"] = len(shares) > 1
    if len(shares) == 1:
        w["final_speaker"] = next(iter(shares))
        w["speaker_confidence"] = "high"
    elif len(shares) > 1:
        ranked = sorted(shares.items(), key=lambda x: -x[1])
        w["final_speaker"] = ranked[0][0]
        # confident only if the winner covers clearly more of the word
        w["speaker_confidence"] = ("high" if ranked[0][1] >= 0.7 * w["dur"]
                                   else "low-overlap")
    else:
        w["final_speaker"] = None
        w["speaker_confidence"] = "unassigned"

for w in words:
    if w["final_speaker"] is None:
        nearest = min(d_turns, key=lambda d: min(abs(d["start_s"] - w["mid"]),
                                                 abs(d["end_s"] - w["mid"])))
        w["final_speaker"] = nearest["speaker"]
        w["speaker_confidence"] = "low-nearest"

# --------------------------------------- 2. pitch profiles + pitch voter
pitch_profile = {}
pitch_observation_counts = {
    speaker: 0 for speaker in {w["final_speaker"] for w in words}
}
phase_c_summaries = (
    (acoustics.get("voice_prosody") or {}).get("speakers") or {}
)
if not solo:
    for spk in {w["final_speaker"] for w in words}:
        vals = []
        for w in words:
            if w["final_speaker"] == spk and w["speaker_confidence"] == "high":
                p = pitch_window(w["start_s"], w["end_s"])
                if p:
                    vals.append(p)
        pitch_observation_counts[spk] = len(vals)
        if len(vals) >= 5:
            pitch_profile[spk] = statistics.median(vals)

def pitch_vote(w):
    """Return the speaker whose pitch profile best matches this word, or None."""
    if len(pitch_profile) < 2:
        return None
    p = pitch_window(w["start_s"], w["end_s"])
    if not p:
        return None
    dists = {spk: abs(p - med) for spk, med in pitch_profile.items()}
    ranked = sorted(dists.items(), key=lambda x: x[1])
    # decisive only if clearly closer to one profile
    if ranked[0][1] * 1.6 < ranked[1][1]:
        return ranked[0][0]
    return None

# --------------------------------------------- 3. smoothing pass
# (skipped in --rebuild mode: labels come from the referee)
# reabsorb single-word (or very short) flips sandwiched inside a same-speaker
# run, unless pitch decisively supports the flip
if not solo and not args.rebuild:
    for i in range(1, len(words) - 1):
        w, prev, nxt = words[i], words[i - 1], words[i + 1]
        if (prev["final_speaker"] == nxt["final_speaker"]
                and w["final_speaker"] != prev["final_speaker"]
                and w["dur"] <= 0.6
                and w["speaker_confidence"] != "high"):
            voted = pitch_vote(w)
            if voted != w["final_speaker"]:
                w["final_speaker"] = prev["final_speaker"]
                w["speaker_confidence"] = "smoothed"

    # pitch voter on remaining low-confidence words where AAI disagrees
    for w in words:
        if w["speaker_confidence"].startswith("low"):
            voted = pitch_vote(w)
            if voted and voted != w["final_speaker"]:
                w["final_speaker"] = voted
                w["speaker_confidence"] = "pitch-voted"

# ---------------------------------- 3b. sliver evidence + save/load labels
WORDS_FILE = context.output_path(
    "words_attributed.json", required=args.rebuild
)

if args.rebuild and WORDS_FILE.exists():
    edited = json.loads(WORDS_FILE.read_text(encoding="utf-8"))
    if len(edited) == len(words):
        for w, e in zip(words, edited):
            w["final_speaker"] = e["speaker"]
            w["speaker_confidence"] = e.get("confidence", w["speaker_confidence"])
            w["interjection_candidate"] = e.get("interjection_candidate", False)
        print(f"Rebuild: loaded {len(words)} referee-checked labels")
    else:
        print("WARNING: words_attributed.json length mismatch - ignoring, "
              "using fresh attribution")
else:
    # flag words overlapping a DIFFERENT speaker's sliver: likely interjections
    for w in words:
        w["interjection_candidate"] = False
        if solo:
            continue
        for s in slivers:
            if (overlap(w["start_s"], w["end_s"], s["start_s"], s["end_s"]) > 0
                    and s["speaker"] != w["final_speaker"]):
                w["interjection_candidate"] = True
                if w["speaker_confidence"] == "high":
                    w["speaker_confidence"] = "sliver-flagged"
                break
    context.write_json("words_attributed.json", [
        {"i": i, "text": w["text"],
         "start_s": round(w["start_s"], 2), "end_s": round(w["end_s"], 2),
         "speaker": w["final_speaker"], "confidence": w["speaker_confidence"],
         "asr_confidence": w.get("confidence"),
         "interjection_candidate": w["interjection_candidate"]}
        for i, w in enumerate(words)], indent=None)

# ------------------------------------------ 4. per-speaker baselines
speakers = sorted({w["final_speaker"] for w in words})
baseline = {}
for spk in speakers:
    sw = [w for w in words if w["final_speaker"] == spk]
    rates = [w["dur"] / len(w["text"].strip(".,?!'\"").strip())
             for w in sw
             if len(w["text"].strip(".,?!'\"").strip()) >= 3 and w["dur"] > 0]
    louds = [loudness_at(w["mid"]) for w in sw]
    louds = [x for x in louds if x is not None]
    baseline[spk] = {
        "sec_per_char": statistics.median(rates) if rates else 0.08,
        "median_db": statistics.median(louds) if louds else -15.0,
    }

# adaptive drag threshold: for each speaker, a word only counts as a drag
# if its stretch-ratio is an OUTLIER for that speaker in this recording -
# the top (100-DRAG_PERCENTILE)% - never below the DRAG_RATIO floor.
drag_threshold = {}
for spk in speakers:
    ratios = []
    for w in words:
        if w["final_speaker"] != spk:
            continue
        core = w["text"].strip(".,?!'\"").strip()
        if len(core) >= 3 and w["dur"] > 0:
            expected = baseline[spk]["sec_per_char"] * len(core)
            if expected > 0:
                ratios.append(w["dur"] / expected)
    if len(ratios) >= 20:
        ratios.sort()
        idx = int(len(ratios) * DRAG_PERCENTILE / 100)
        idx = min(idx, len(ratios) - 1)
        drag_threshold[spk] = max(DRAG_RATIO, ratios[idx])
    else:
        drag_threshold[spk] = DRAG_RATIO

# ------------------------------------------------ 5. expressive rendering
all_chars = []
if alignment:
    for seg in alignment.get("segments", []):
        for c in seg.get("chars", []):
            if "start" in c and "end" in c:
                all_chars.append(c)

def longest_vowel_in(s, e):
    inside = [c for c in all_chars
              if c["start"] >= s - 0.05 and c["end"] <= e + 0.05
              and c["char"].strip().isalpha()]
    if not inside:
        return None
    vs = [c for c in inside if c["char"].lower() in VOWELS]
    pool = vs if vs else inside
    return max(pool, key=lambda c: c["end"] - c["start"])["char"].lower()

def stretch(word, letter, extra=3):
    i = word.lower().rfind(letter) if letter else -1
    if i == -1:
        for j in range(len(word) - 1, -1, -1):
            if word[j].lower() in VOWELS:
                i = j
                break
        if i == -1:
            i = len(word) - 1
    i = max(0, min(i, len(word) - 1))
    return word[:i + 1] + word[i].lower() * extra + word[i + 1:]

def render_word(w, is_phrase_final):
    text = w["text"]
    core = text.strip(".,?!'\"").strip()
    if not core:
        return text, {}
    spk = baseline[w["final_speaker"]]
    fx = {}

    if core.lower() in FILLERS:
        fx["filler_s"] = round(w["dur"], 2)
        if w["dur"] >= 0.9:
            return text.replace(core, core[0] * 3 + core[1:] * 3), fx
        if w["dur"] >= 0.5:
            return text.replace(core, core[0] * 2 + core[1:] * 2), fx
        return text, fx

    expected = spk["sec_per_char"] * len(core)
    if (len(core) >= 3 and expected > 0
            and w["dur"] >= DRAG_MIN_S
            and w["dur"] / expected >= drag_threshold[w["final_speaker"]]):
        # stretch the spelling only for alphabetic words - repeating digits
        # ("2:20" -> "2:20000") reads as a different number. Numeric drags
        # still count and still carry held_s.
        if any(c.isalpha() for c in core):
            text = text.replace(core, stretch(core, longest_vowel_in(w["start_s"], w["end_s"])))
        fx["held_s"] = round(w["dur"], 2)

    db = loudness_at(w["mid"])
    if db is not None and db >= spk["median_db"] + LOUD_DB_ABOVE:
        text = text.upper()
        fx["loud_db_above_avg"] = round(db - spk["median_db"], 1)

    ends_statement = text.rstrip().endswith((".", "!")) or is_phrase_final
    if ends_statement and "?" not in text and w["dur"] >= 0.15:
        first = pitch_window(w["start_s"], w["start_s"] + w["dur"] * 0.4)
        last = pitch_window(w["end_s"] - w["dur"] * 0.4, w["end_s"])
        if (first and last and last / first >= RISE_RATIO
                and last - first >= RISE_MIN_HZ):
            fx["rising_pitch_hz"] = [round(first, 1), round(last, 1)]
            text = text.rstrip().rstrip(".!") + "?"

    return text, fx

# --------------------------------- 6. group words into runs + backchannels
runs = []
cur = None
for w in words:
    if cur is None or cur["speaker"] != w["final_speaker"]:
        if cur:
            runs.append(cur)
        cur = {"speaker": w["final_speaker"], "words": [w]}
    else:
        cur["words"].append(w)
if cur:
    runs.append(cur)

for r in runs:
    r["start_s"] = r["words"][0]["start_s"]
    r["end_s"] = r["words"][-1]["end_s"]
    r["dur"] = r["end_s"] - r["start_s"]

# a run is a backchannel if it's short, few words, and sits between two runs
# of the SAME other speaker (i.e. it interrupts a continuing thought)
backchannel_counts = {s: 0 for s in speakers}
for i in range(1, len(runs) - 1):
    r, prev, nxt = runs[i], runs[i - 1], runs[i + 1]
    if (prev["speaker"] == nxt["speaker"]
            and r["speaker"] != prev["speaker"]
            and r["dur"] <= BACKCHANNEL_MAX_S
            and len(r["words"]) <= BACKCHANNEL_MAX_WORDS):
        r["backchannel"] = True
        backchannel_counts[r["speaker"]] += 1

# ------------------------------------------------- 7. build merged turns
def pause_between(t1, t2):
    best = 0.0
    for p in pauses:
        if p["starts_at"] >= t1 - 0.2 and p["ends_at"] <= t2 + 0.2:
            best = max(best, p["duration"])
    return best

turns = []
current = None
prev_end = None
effect_totals = {s: {"fillers": 0, "drags": 0, "loud": 0, "uptalk": 0}
                 for s in speakers}


def append_word_uncertainty(turn, word):
    """Preserve speaker and ASR uncertainty as separate downstream flags."""
    if word["speaker_confidence"] not in ("high", "smoothed", "referee"):
        turn["low_confidence_words"].append({
            "word": word["text"], "t": round(word["start_s"], 2),
            "speaker": word["final_speaker"],
            "why": word["speaker_confidence"],
        })
    if is_low_asr_confidence(word):
        turn["low_confidence_words"].append({
            "word": word["text"], "t": round(word["start_s"], 2),
            "speaker": word["final_speaker"],
            "why": "asr-low-confidence",
            "asr_confidence": word.get("confidence"),
            "threshold_below": ASR_CONFIDENCE_THRESHOLD,
        })

for ri, r in enumerate(runs):
    is_bc = r.get("backchannel", False)
    rendered_words = []
    for wi, w in enumerate(r["words"]):
        phrase_final = (wi == len(r["words"]) - 1)
        piece, fx = render_word(w, phrase_final)
        rendered_words.append((w, piece, fx))
        if fx:
            et = effect_totals[w["final_speaker"]]
            if "filler_s" in fx:
                et["fillers"] += 1
            if "held_s" in fx:
                et["drags"] += 1
            if "loud_db_above_avg" in fx:
                et["loud"] += 1
            if "rising_pitch_hz" in fx:
                et["uptalk"] += 1

    if is_bc and current is not None:
        # weave into the surrounding speaker's turn inline
        bc_text = " ".join(p for _, p, _ in rendered_words)
        current["expressive_text"] += f' [{r["speaker"]}: "{bc_text}"]'
        for w, piece, fx in rendered_words:
            if fx:
                fx["word"] = w["text"]
                fx["t"] = round(w["start_s"], 2)
                fx["speaker"] = w["final_speaker"]
                fx["backchannel"] = True
                current["word_effects"].append(fx)
            append_word_uncertainty(current, w)
        continue

    spk = r["speaker"]
    gap = pause_between(prev_end, r["start_s"]) if prev_end is not None else 0.0
    if current is None or current["speaker"] != spk:
        if current:
            turns.append(current)
        current = {
            "speaker": spk,
            "start_s": round(r["start_s"], 2),
            "end_s": round(r["end_s"], 2),
            "expressive_text": "",
            "word_effects": [],
            "low_confidence_words": [],
        }
        if gap >= PAUSE_MIN:
            current["pause_before_s"] = round(gap, 2)
    else:
        if gap >= PAUSE_MIN:
            current["expressive_text"] += f" ... [{gap:.1f}s]"
        current["end_s"] = round(r["end_s"], 2)

    last_end = None
    for w, piece, fx in rendered_words:
        if last_end is not None:
            g = pause_between(last_end, w["start_s"])
            if g >= PAUSE_MIN:
                current["expressive_text"] += f" ... [{g:.1f}s]"
        current["expressive_text"] = (current["expressive_text"] + " " + piece).strip()
        if fx:
            fx["word"] = w["text"]
            fx["t"] = round(w["start_s"], 2)
            fx["speaker"] = w["final_speaker"]
            current["word_effects"].append(fx)
        append_word_uncertainty(current, w)
        last_end = w["end_s"]
    prev_end = r["end_s"]
if current:
    turns.append(current)

for i, t in enumerate(turns, 1):
    t["turn_id"] = i

# per-turn acoustics
def build_mapping(segments, get_spk, get_range):
    votes = {}
    for seg in segments:
        s, e = get_range(seg)
        lab = get_spk(seg)
        for d in d_turns:
            votes.setdefault(lab, {})
            votes[lab][d["speaker"]] = votes[lab].get(d["speaker"], 0.0) + \
                overlap(s, e, d["start_s"], d["end_s"])
    mapping, used = {}, set()
    claims = [(score, lab, spk) for lab, v in votes.items()
              for spk, score in v.items()]
    for score, lab, spk in sorted(claims, reverse=True):
        if lab not in mapping and spk not in used:
            mapping[lab] = spk
            used.add(spk)
    for lab, v in votes.items():
        if lab not in mapping and v:
            mapping[lab] = max(v, key=v.get)
    return mapping


for t in turns:
    mids = [tt for tt in timeline if t["start_s"] <= tt["t"] <= t["end_s"]]
    louds = [m["loudness_db"] for m in mids]
    pitches = [m["pitch_hz"] for m in mids if m["pitch_hz"]]
    spk_base = baseline[t["speaker"]]
    t["acoustics"] = {
        "loudness_vs_own_avg_db": round(statistics.mean(louds) - spk_base["median_db"], 1) if louds else None,
        "pitch_mean_hz": round(statistics.mean(pitches), 1) if pitches else None,
    }

moments = []  # filled by the listener enrichment step

# ------------------------------ 8a. deterministic language metrics helpers
# Hedges: longest-phrase-first greedy scan over each speaker's normalized
# word tokens, so "you know what I mean" counts once (not also "you know").
HEDGE_PHRASES = [
    "you know what i mean", "kind of", "sort of", "or something",
    "or whatever", "i think", "i guess", "you know",
    "kinda", "sorta", "maybe", "basically", "literally", "honestly",
]
_HEDGE_TOKENS = sorted((tuple(p.split()) for p in HEDGE_PHRASES),
                       key=len, reverse=True)
FIRST_PERSON = {"i", "me", "my"}
SECOND_PERSON = {"you", "your"}


def _norm_token(text):
    return text.strip(".,?!'\";:").lower()


def _hedge_at(tokens, i):
    """Longest hedge phrase starting at token i, or None."""
    for pt in _HEDGE_TOKENS:
        if tuple(tokens[i:i + len(pt)]) == pt:
            return " ".join(pt)
    return None


def language_metrics(sw, own_turn_count, minutes):
    """Deterministic language metrics for one speaker.

    sw: that speaker's words in chronological order (final attributions).

    "like" heuristic (v1, per spec): "like" only counts as a hedge when it
    looks like a discourse filler - i.e. it is sentence-initial (first word,
    or previous word ends with . ? !), follows a comma, follows a real pause
    (>=0.5s gap from the speaker's previous word - also covers turn starts),
    or is adjacent to another counted hedge. "I like X" therefore does not
    count.

    Questions: a word whose RAW ASR text ends with "?" ends a question
    sentence. Renderer uptalk adds "?" only to expressive_text, never to the
    raw word, so uptalk is excluded automatically.
    """
    tokens = [_norm_token(w["text"]) for w in sw]

    breakdown = {}
    hedge_count = 0
    i = 0
    last_hedge_end = -1  # index just past the most recent counted hedge
    while i < len(tokens):
        m = _hedge_at(tokens, i)
        if m:
            breakdown[m] = breakdown.get(m, 0) + 1
            hedge_count += 1
            i += len(m.split())
            last_hedge_end = i
            continue
        if tokens[i] == "like":
            prev_raw = sw[i - 1]["text"].rstrip() if i else ""
            sentence_initial = i == 0 or prev_raw.endswith((".", "?", "!"))
            after_comma = prev_raw.endswith(",")
            after_pause = (i > 0
                           and sw[i]["start_s"] - sw[i - 1]["end_s"] >= 0.5)
            near_hedge = (last_hedge_end == i
                          or (i + 1 < len(tokens)
                              and _hedge_at(tokens, i + 1) is not None))
            if sentence_initial or after_comma or after_pause or near_hedge:
                breakdown["like (filler)"] = breakdown.get("like (filler)", 0) + 1
                hedge_count += 1
                last_hedge_end = i + 1
        i += 1

    question_count = sum(1 for w in sw if w["text"].rstrip().endswith("?"))

    first = sum(1 for t in tokens if t.split("'")[0] in FIRST_PERSON)
    second = sum(1 for t in tokens if t.split("'")[0] in SECOND_PERSON)

    reps = 0
    for j in range(len(tokens) - 1):
        if tokens[j] and tokens[j] == tokens[j + 1]:
            reps += 1
    for j in range(len(tokens) - 3):
        if (tokens[j] and tokens[j] != tokens[j + 1]
                and tokens[j] == tokens[j + 2]
                and tokens[j + 1] == tokens[j + 3]):
            reps += 1

    clean = [t for t in tokens if t]
    vocab_variety = (round(len(set(clean)) / len(clean), 3)
                     if len(clean) >= 50 else None)

    return {
        "hedge_count": hedge_count,
        "hedges_per_min": round(hedge_count / minutes, 2),
        "hedge_breakdown": breakdown,
        "question_count": question_count,
        "question_ratio": (round(question_count / own_turn_count, 2)
                           if own_turn_count else 0.0),
        "pronoun_balance": {
            "i_me_my": first,
            "you_your": second,
            "ratio": round(first / second, 2) if second else None,
        },
        "repetition_count": reps,
        "repetition_rate": round(reps / minutes, 2),
        "vocab_variety": vocab_variety,
    }


# --------------------------------------- 8. deterministic computed metrics
total_talk = sum(t["end_s"] - t["start_s"] for t in turns) or 1.0
computed = {}
# active time per speaker = sum of their run SPANS (includes natural
# inter-word gaps) - realistic basis for WPM, unlike summed word durations
span_time = {s: 0.0 for s in speakers}
for r in runs:
    span_time[r["speaker"]] = span_time.get(r["speaker"], 0.0) + r["dur"]
for spk in speakers:
    sw = [w for w in words if w["final_speaker"] == spk]
    talk_s = max(span_time.get(spk, 0.0), sum(w["dur"] for w in sw))
    minutes = max(talk_s / 60.0, 1e-6)
    et = effect_totals[spk]
    own_turns = [t for t in turns if t["speaker"] == spk]
    long_pauses = [t.get("pause_before_s", 0) for t in own_turns
                   if t.get("pause_before_s")]
    computed[spk] = {
        "talk_time_s": round(talk_s, 1),
        "talk_share_pct": round(100 * talk_s /
                                max(sum(max(span_time.get(s, 0.0),
                                            sum(x["dur"] for x in words
                                                if x["final_speaker"] == s))
                                        for s in speakers), 1e-6), 1),
        "words": len(sw),
        "wpm": round(len(sw) / minutes, 1),
        "filler_count": et["fillers"],
        "fillers_per_min": round(et["fillers"] / minutes, 2),
        "drag_count": et["drags"],
        "loud_spike_count": et["loud"],
        "uptalk_count": et["uptalk"],
        "uptalk_per_min": round(et["uptalk"] / minutes, 2),
        "backchannels_given": backchannel_counts.get(spk, 0),
        "avg_response_pause_s": round(statistics.mean(long_pauses), 2) if long_pauses else 0.0,
        "median_pitch_hz": round(pitch_profile.get(spk), 1) if pitch_profile.get(spk) else None,
    }
    computed[spk].update(language_metrics(sw, len(own_turns), minutes))

measurement_metadata = build_measurement_metadata(
    computed, words, turns, acoustics, audio_quality,
    "solo" if solo else "conversation",
    pitch_observation_counts=pitch_observation_counts,
    contamination=diar.get("contamination"),
)

enrichment_status = initial_enrichment_status(solo=solo)
previous_provenance = None
if args.rebuild:
    previous_master_path = context.output_path("master.json", required=True)
    if previous_master_path.exists():
        try:
            previous_master = json.loads(
                previous_master_path.read_text(encoding="utf-8")
            )
            previous_referee = (previous_master.get("meta", {})
                                .get("enrichment_status", {})
                                .get("referee"))
            if isinstance(previous_referee, dict):
                enrichment_status["referee"] = previous_referee
            candidate_provenance = (previous_master.get("meta", {})
                                    .get("provenance"))
            if isinstance(candidate_provenance, dict):
                previous_provenance = candidate_provenance
        except json.JSONDecodeError:
            pass

master = {
    "meta": {
        "num_speakers": n_speakers,
        "recording_type": "solo" if solo else "conversation",
        "account_holder_speaker": diar.get("account_holder_speaker"),
        "contamination": diar.get("contamination"),
        "audio_duration_s": vad.get("audio_duration_s"),
        "speaking_time_s": vad.get("speaking_time_s"),
        "silence_time_s": vad.get("silence_time_s"),
        "voice_quality_overall": acoustics.get("overall"),
        "per_speaker_voice_quality": acoustics.get("per_speaker"),
        "voice_prosody_context": (
            (acoustics.get("voice_prosody") or {}).get("analysis_context")
        ),
        "per_speaker_voice_prosody": {
            speaker: deepcopy(summary.get("values") or {})
            for speaker, summary in phase_c_summaries.items()
        },
        "voice_prosody_release_limits": (
            (acoustics.get("voice_prosody") or {}).get("release_limits")
        ),
        "audio_quality": audio_quality,
        "audio_conditions": None,  # filled by listener enrichment
        "enrichment_status": enrichment_status,
        "notes": "expressive spelling: CAPS = louder than that speaker's own "
                 "average; stretched letters = held longer than their own pace; "
                 "trailing ? on a statement = measured rising inflection "
                 "(uptalk); ... [Ns] = measured silence; [SPK: \"...\"] inline "
                 "= backchannel interjection while the main speaker continued. "
                 "low_confidence_words separately mark uncertain attribution "
                 "and provisional ASR confidence below 0.50.",
    },
    "speaker_baselines": {
        s: {"sec_per_char": round(b["sec_per_char"], 4),
            "median_loudness_db": round(b["median_db"], 1)}
        for s, b in baseline.items()
    },
    "computed_metrics": computed,
    "measurement_metadata": measurement_metadata,
    "speaker_overall_impressions": {},  # filled by listener enrichment
    "turns": turns,
    "notable_moments": moments,
}
if previous_provenance is not None:
    master["meta"]["provenance"] = previous_provenance

context.write_json("master.json", master)

lines = []
for t in turns:
    pause_note = f"\n        ... [{t['pause_before_s']}s silence] ...\n" if t.get("pause_before_s") else ""
    lines.append(f"{pause_note}[{t['start_s']:>6.1f}s] {t['speaker']}: {t['expressive_text']}")
txt = "\n".join(lines)
context.write_text("master_preview.txt", txt)

bc_total = sum(backchannel_counts.values())
print(f"Done. master.json: {len(turns)} turns ({master['meta']['recording_type']}), "
      f"{bc_total} backchannels woven inline, "
      f"{sum(len(t['low_confidence_words']) for t in turns)} low-confidence words.")
print("Computed metrics:")
for spk, m in computed.items():
    print(f"  {spk}: {m['talk_share_pct']}% talk, {m['wpm']} wpm, "
          f"{m['fillers_per_min']} fillers/min, {m['uptalk_count']} uptalk, "
          f"{m['backchannels_given']} backchannels, "
          f"{m['hedges_per_min']} hedges/min, {m['question_count']} questions")
print("\nPreview:\n")
print(txt[:1500])
