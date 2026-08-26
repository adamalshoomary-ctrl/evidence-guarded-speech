"""Pure shaping of a local Whisper result into this project's transcript.

Kept separate from `transcribe_local.py` so it can be tested without loading a
speech model. The one rule it enforces is that a word never disappears: forced
alignment leaves some tokens without timing, and dropping those would quietly
shorten a transcript this project calls verbatim.
"""


def timed_words(aligned, fallback_span):
    """Return every word with a start and an end in milliseconds.

    Words the aligner could not time keep their place and borrow timing from
    the segment around them. The count of those is returned so the transcript
    can report it rather than hide it.

    The aligner's per word score is **not** written to `confidence`. That field
    carries a provider's ASR posterior elsewhere in this pipeline, and a forced
    alignment score is a different quantity on a different scale. Downstream
    contracts threshold `confidence` at values calibrated against the posterior,
    so writing the alignment score there would compare two things that are not
    the same measurement. It is kept under its own name, and the absence of an
    ASR confidence is reported honestly by the stages that need one.
    """
    words = []
    borrowed = 0
    for segment in aligned.get("segments", []):
        segment_words = segment.get("words") or []
        if not segment_words:
            continue
        start = segment.get("start")
        end = segment.get("end")
        if start is None or end is None:
            start, end = fallback_span
        span = max(float(end) - float(start), 1e-3)
        step = span / len(segment_words)
        for index, word in enumerate(segment_words):
            text = (word.get("word") or "").strip()
            if not text:
                continue
            has_timing = (
                word.get("start") is not None and word.get("end") is not None
            )
            if has_timing:
                word_start = float(word["start"])
                word_end = float(word["end"])
            else:
                borrowed += 1
                word_start = float(start) + index * step
                word_end = word_start + step
            words.append(
                {
                    "text": text,
                    "start": int(round(word_start * 1000)),
                    "end": int(round(max(word_end, word_start + 0.001) * 1000)),
                    "alignment_score": (
                        round(float(word["score"]), 4)
                        if word.get("score") is not None
                        else None
                    ),
                }
            )
    return words, borrowed
