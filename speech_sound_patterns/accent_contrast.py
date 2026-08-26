"""Accent contrast demonstration on one owner recording.

Adam read the same eight sentences twice in one recording, once in his native
Australian accent and once aiming at American. Holding speaker, words, room and
microphone constant isolates the variety effect that is otherwise tangled with
speaker differences.

The question is narrow: when only the accent target changes, how does an
external scorer's output move, and does it move on the two control sentences of
dialect stable consonants where the dictionaries agree? Movement on the control
sentences is evidence that a variety mismatch does not stay confined to the
sounds that differ, which is the locality argument recorded in
``research-and-protocol.md``.

This is a demonstration, never a measurement. One speaker is not a population,
a performed American accent is not a native American accent, and neither pass
carries expert human phone labels, so no production here is known to be correct
or incorrect. Nothing produced by this module may become accuracy evidence, a
threshold, a selection input, a validation or a gate result.

Sending this recording to Azure required an explicit owner grant pinned to the
exact file hash, recorded under ``owner_audio_decisions`` in the corpus to
provider transfer review. The gate is checked here before any request.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
import wave
from datetime import datetime, timezone
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parent
RECORDING_PATH = REPOSITORY_ROOT / "audio" / "accent" / "owner-accent-contrast-recording.m4a"
RECORDING_SHA256 = "da530382502dafc3f27c0a9bb706df023a36eafe9f1d47dc1e33f413b277ecc4"
PRIVATE_ROOT = (
    REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns" / "accent_contrast"
)
SEGMENT_ROOT = PRIVATE_ROOT / "segments"

LANE_ID = "azure_speech"

# The script as written in audio/accent-contrast-script.md. Both passes say
# these same words; the respelling in the script was only a reading aid, so the
# reference text handed to a scorer is identical for both passes. That identity
# is what makes the comparison meaningful.
SENTENCES = (
    {
        "sentence_id": "s1",
        "text": "I can't dance in that class after the last chance.",
        "probe": "bath_vowel_split",
        "is_control": False,
    },
    {
        "sentence_id": "s2",
        "text": "The car park is far from the corner store.",
        "probe": "rhoticity",
        "is_control": False,
    },
    {
        "sentence_id": "s3",
        "text": "The waiter put a little better water on the table.",
        "probe": "intervocalic_t_flapping",
        "is_control": False,
    },
    {
        "sentence_id": "s4",
        "text": "The new tutor changed the schedule on Tuesday.",
        "probe": "yod_dropping_and_lexical",
        "is_control": False,
    },
    {
        "sentence_id": "s5",
        "text": "She bought fresh fish and cheap cheese at the shop.",
        "probe": "dialect_stable_fricatives_and_affricates",
        "is_control": True,
    },
    {
        "sentence_id": "s6",
        "text": "I go home to the same place every night now.",
        "probe": "goat_face_price_mouth_vowels",
        "is_control": False,
    },
    {
        "sentence_id": "s7",
        "text": "It is not necessary to bring the dog off the path.",
        "probe": "reduced_versus_full_endings",
        "is_control": False,
    },
    {
        "sentence_id": "s8",
        "text": "Pick up the big black box and put it back.",
        "probe": "dialect_stable_stops",
        "is_control": True,
    },
)

PASSES = (
    {"pass_id": "australian", "marker": "australian version"},
    {"pass_id": "american", "marker": "american version"},
)


def normalize(text: str) -> str:
    """Fold text to bare lowercase words for matching against a transcript."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", folded.lower()).strip()


def sentence_words(sentence) -> list[str]:
    return normalize(sentence["text"]).split()


def expected_word_sequence():
    """Every word the recording should contain, in order, across both passes."""
    sequence = []
    for pass_spec in PASSES:
        sequence.extend(normalize(pass_spec["marker"]).split())
        for sentence in SENTENCES:
            sequence.extend(sentence_words(sentence))
    return sequence


def split_passes(words):
    """Split the aligned word stream at the spoken pass markers.

    Returns a list of (pass_id, offset, words) triples. A marker that is not
    found is an error rather than a silent guess, because mislabelling which
    pass a segment came from would invert the entire comparison.
    """
    tokens = [token for token, _, _ in words]
    boundaries = []
    for pass_spec in PASSES:
        marker = normalize(pass_spec["marker"]).split()
        index = _find_subsequence(tokens, marker)
        if index is None:
            raise ValueError(
                f"the spoken marker {pass_spec['marker']!r} was not found; the "
                "passes cannot be told apart"
            )
        boundaries.append((pass_spec["pass_id"], index, index + len(marker)))

    boundaries.sort(key=lambda item: item[1])
    passes = []
    for position, (pass_id, start, after_marker) in enumerate(boundaries):
        end = (
            boundaries[position + 1][1]
            if position + 1 < len(boundaries)
            else len(words)
        )
        passes.append((pass_id, after_marker, words[after_marker:end]))
    return passes


def _find_subsequence(tokens, wanted):
    for index in range(len(tokens) - len(wanted) + 1):
        if tokens[index : index + len(wanted)] == wanted:
            return index
    return None


def locate_sentences(pass_words, minimum_matched_ratio=0.6):
    """Locate each scripted sentence inside one pass.

    Uses a tolerant sequence match rather than exact equality, because a real
    reading contains omissions, substitutions and retries. Every departure is
    recorded rather than smoothed away: a sentence whose matched word ratio
    falls below the floor is marked not comparable instead of being scored as
    though it were clean.
    """
    from difflib import SequenceMatcher

    observed = [token for token, _, _ in pass_words]
    cursor = 0
    located = []
    for sentence in SENTENCES:
        wanted = sentence_words(sentence)
        window = observed[cursor : cursor + len(wanted) * 3 + 6]
        matcher = SequenceMatcher(None, wanted, window, autojunk=False)
        blocks = [block for block in matcher.get_matching_blocks() if block.size]
        matched = sum(block.size for block in blocks)
        ratio = matched / len(wanted) if wanted else 0.0

        if not blocks or ratio < minimum_matched_ratio:
            located.append(
                {
                    **sentence,
                    "found": False,
                    "matched_ratio": round(ratio, 3),
                    "note": "not found in this pass",
                }
            )
            continue

        first = cursor + blocks[0].b
        last = cursor + blocks[-1].b + blocks[-1].size - 1
        spoken = observed[first : last + 1]
        located.append(
            {
                **sentence,
                "found": True,
                "matched_ratio": round(ratio, 3),
                "first_word_index": first,
                "last_word_index": last,
                "start_s": pass_words[first][1],
                "end_s": pass_words[last][2],
                "spoken_words": spoken,
                "exact": spoken == wanted,
                "note": None if spoken == wanted else "spoken words differ from script",
            }
        )
        cursor = last + 1
    return located


def load_aligned_words(alignment_path: Path):
    """Return (word, start, end) triples from a pipeline alignment artifact."""
    document = json.loads(Path(alignment_path).read_text(encoding="utf-8"))
    words = document.get("words")
    if words is None:
        for key in ("segments", "word_segments"):
            if key in document:
                words = [
                    word
                    for segment in document[key]
                    for word in segment.get("words", [])
                ]
                break
    if not words:
        raise ValueError(f"no aligned words found in {alignment_path}")

    triples = []
    for word in words:
        start = word.get("start")
        end = word.get("end")
        if start is None or end is None:
            continue
        # One aligned word can normalize to several tokens, because folding
        # strips apostrophes and "can't" becomes "can t". Emit each token
        # separately so the observed stream tokenizes exactly like the script,
        # and let the sub-tokens share the parent word's timing.
        for token in normalize(
            str(word.get("word") or word.get("text") or "")
        ).split():
            triples.append((token, float(start), float(end)))
    return triples


# Padding around each cut so a segment does not clip the first or last sound.
SEGMENT_PAD_S = 0.20


def extract_segments(recording_path, located_by_pass, output_root):
    """Cut one 16 kHz mono clip per located sentence, ready for the endpoint."""
    import librosa
    import numpy as np

    audio, rate = librosa.load(str(recording_path), sr=16000, mono=True)
    output_root.mkdir(parents=True, exist_ok=True)

    segments = []
    for pass_id, located in located_by_pass:
        for sentence in located:
            if not sentence["found"]:
                continue
            start = max(0.0, sentence["start_s"] - SEGMENT_PAD_S)
            end = min(len(audio) / rate, sentence["end_s"] + SEGMENT_PAD_S)
            clip = audio[int(start * rate) : int(end * rate)]
            path = output_root / f"{pass_id}_{sentence['sentence_id']}.wav"
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(rate)
                handle.writeframes(
                    (np.clip(clip, -1.0, 1.0) * 32767).astype("<i2").tobytes()
                )
            segments.append(
                {
                    "pass_id": pass_id,
                    "sentence_id": sentence["sentence_id"],
                    "probe": sentence["probe"],
                    "is_control": sentence["is_control"],
                    "reference_text": sentence["text"],
                    "exact": sentence["exact"],
                    "note": sentence["note"],
                    "duration_s": round(len(clip) / rate, 3),
                    "path": path,
                }
            )
    return segments


def _comparable_sentences(segments):
    """Sentence ids present and spoken exactly as scripted in both passes.

    Anything else is reported but excluded from the headline comparison, so a
    stumble or a missing sentence cannot masquerade as an accent effect.
    """
    by_sentence = {}
    for segment in segments:
        by_sentence.setdefault(segment["sentence_id"], {})[segment["pass_id"]] = segment
    comparable = set()
    for sentence_id, passes in by_sentence.items():
        if len(passes) == len(PASSES) and all(
            item["exact"] for item in passes.values()
        ):
            comparable.add(sentence_id)
    return comparable


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alignment",
        type=Path,
        default=PRIVATE_ROOT / "pipeline" / "alignment.json",
        help="pipeline alignment artifact providing word timings",
    )
    parser.add_argument(
        "--segments-only",
        action="store_true",
        help="cut the segments and stop without sending anything",
    )
    args = parser.parse_args(argv)

    from dotenv import load_dotenv
    import os

    from speech_sound_patterns.azure_smoke import send_one
    from speech_sound_patterns.external_smoke import (
        load_smoke_contract,
        owner_audio_permitted,
    )
    from speech_sound_patterns.feasibility import canonical_json_bytes, file_sha256
    from speech_sound_patterns.provider_register import lane_status

    load_dotenv(REPOSITORY_ROOT / ".env")

    if not RECORDING_PATH.is_file():
        raise SystemExit(
            "the accent contrast recording is not present. It is the repository "
            "owner reading a script twice in two accents, it is personal audio, "
            "and it is deliberately not published. No substitute recording can "
            "stand in for it, because the analysis holds speaker, words, room "
            "and microphone constant on purpose. The frozen result of the one "
            "run that was made is committed at "
            "speech_sound_patterns/accent-contrast-v1.0.0.json and is readable "
            "without rerunning anything."
        )

    digest = file_sha256(RECORDING_PATH)
    if digest != RECORDING_SHA256:
        raise SystemExit(
            "the recording no longer matches the hash the owner grant pins; "
            "a new explicit owner decision is required"
        )

    words = load_aligned_words(args.alignment)
    located_by_pass = [
        (pass_id, locate_sentences(pass_words))
        for pass_id, _, pass_words in split_passes(words)
    ]
    segments = extract_segments(RECORDING_PATH, located_by_pass, SEGMENT_ROOT)
    comparable = _comparable_sentences(segments)

    print(f"segments cut: {len(segments)}")
    for segment in segments:
        flag = "comparable" if segment["sentence_id"] in comparable else "excluded"
        control = " CONTROL" if segment["is_control"] else ""
        print(
            f"  {segment['pass_id']:10s} {segment['sentence_id']} "
            f"{segment['duration_s']:5.2f}s {flag}{control}"
        )
    print(f"comparable sentence ids: {sorted(comparable)}")

    if args.segments_only:
        print("segments only: nothing was sent")
        return 0

    if lane_status(LANE_ID) != "ready":
        raise SystemExit(f"lane {LANE_ID!r} is not ready")
    if not owner_audio_permitted(LANE_ID, digest):
        raise SystemExit(
            "no owner audio grant pins this exact file for this lane; owner "
            "audio is prohibited by default"
        )

    region = os.environ.get("AZURE_SPEECH_REGION")
    key = os.environ.get("AZURE_SPEECH_KEY")
    if not region or not key:
        raise SystemExit("AZURE_SPEECH_REGION and AZURE_SPEECH_KEY must be set")

    contract = load_smoke_contract()
    import requests

    session = requests.Session()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results = []
    throttled = False
    for configuration in contract["azure_configurations"]:
        if throttled:
            break
        locale = configuration["locale"]
        for segment in segments:
            record = send_one(
                session,
                region,
                key,
                locale,
                contract,
                segment["path"].read_bytes(),
                segment["reference_text"],
            )
            record.update(
                {
                    "locale": locale,
                    "pass_id": segment["pass_id"],
                    "sentence_id": segment["sentence_id"],
                    "probe": segment["probe"],
                    "is_control": segment["is_control"],
                    "comparable": segment["sentence_id"] in comparable,
                }
            )
            results.append(record)
            print(
                f"  {locale} {segment['pass_id']:10s} {segment['sentence_id']}: "
                f"{'ok' if record['ok'] else record.get('failure')}"
            )
            if record.get("failure") == "quota_or_rate_limited":
                print("  stopping: quota or rate limit reported")
                throttled = True
                break
            time.sleep(3.5)

    raw_path = PRIVATE_ROOT / f"azure-raw-{started.replace(':', '')}.json"
    raw_path.write_bytes(
        canonical_json_bytes({"started": started, "results": results})
    )
    print(f"raw responses retained privately at {raw_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(run())


# Known Australian and General American divergence points, written down before
# reading the phone scores so the classification cannot be fitted to them.
PREDICTED_DIVERGENCE = {
    "ɚ": "r coloured vowel; Australian English is non rhotic",
    "ɹ": "post vocalic r; Australian English is non rhotic",
    "ɔɹ": "r coloured vowel; Australian English is non rhotic",
    "æ": "the BATH and TRAP split; Australian uses a long a in class and dance",
    "l": "dark l is commonly vocalised in Australian English, as in table",
    "t": "Australian final and pre pausal t is commonly glottalised or unreleased",
}


def summarize_phones(results, comparable_ids):
    """Aggregate phone scores without exposing per clip detail."""
    import statistics

    buckets = {}
    weak = []
    for result in results:
        if not result.get("ok") or result["sentence_id"] not in comparable_ids:
            continue
        best = result["body"]["NBest"][0]
        phones = [
            phone
            for word in best["Words"]
            for phone in (word.get("Phonemes") or [])
        ]
        key = (result["locale"], result["pass_id"], bool(result["is_control"]))
        buckets.setdefault(key, []).append(phones)
        for word in best["Words"]:
            for phone in word.get("Phonemes") or []:
                if phone["AccuracyScore"] < 80:
                    name = phone.get("Phoneme") or None
                    weak.append(
                        {
                            "locale": result["locale"],
                            "pass_id": result["pass_id"],
                            "sentence_id": result["sentence_id"],
                            "is_control": bool(result["is_control"]),
                            "phone": name,
                            "score": phone["AccuracyScore"],
                            "predicted_divergence": PREDICTED_DIVERGENCE.get(name),
                        }
                    )

    summary = {}
    for (locale, pass_id, is_control), clips in sorted(buckets.items()):
        scores = [phone["AccuracyScore"] for phones in clips for phone in phones]
        summary[f"{locale}|{pass_id}|{'control' if is_control else 'probes'}"] = {
            "phone_count": len(scores),
            "mean_accuracy": round(statistics.mean(scores), 2),
            "weak_under_80": sum(1 for value in scores if value < 80),
        }
    return summary, weak
