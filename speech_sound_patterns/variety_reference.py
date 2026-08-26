"""Checkpoint 22E8 expected-phone references, with the variety declared.

Every reference in this project has been American. For SpeechOcean762 that is
correct, because its reviewers judged against American English. For an Australian
speaker it is a defect, and this module is where the variety stops being an
unstated assumption and becomes an input.

A reference here is a pronunciation dictionary read into the frozen Meta CTC
model's own phone vocabulary. Two are built and neither replaces the other:

- ``american``, from the Montreal Forced Aligner English (US) dictionary;
- ``british``, from English (UK), optionally overlaid with the Australian tagged
  Wiktionary entries.

Both come from one publisher in one phone alphabet, so the two paths differ in
variety and in almost nothing else. That is deliberate. Two references differing
in alphabet as well as in accent could not produce an interpretable difference.

Nothing here scores a speaker, selects a system or moves a gate. It turns known
words into the phone sequence a documented variety would expect, and refuses to
guess when it cannot.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from .corpus_manifest import REPOSITORY_ROOT

PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
DICTIONARY_ROOT = PRIVATE_ROOT / "corpora" / "mfa_english_dictionary"
AUSTRALIAN_OVERLAY = PRIVATE_ROOT / "lexicons" / "wiktionary-australian-tagged.json"
MODEL_VOCAB = (
    PRIVATE_ROOT / "models" / "meta-wav2vec2-c69750f" / "vocab.json"
)

VARIETIES = {
    "american": {"dictionary": "english_us_mfa", "overlay": None},
    "british": {"dictionary": "english_uk_mfa", "overlay": "australian"},
}

# The aligner's own machinery, not speech. A word needing one of these cannot be
# given an expected pronunciation and is refused rather than approximated.
ALIGNER_TOKENS = frozenset({"spn", "<unk>", "<cutoff>", "[bracketed]", "[laughter]"})

MAPPING_VERSION = "1.2.0"

# Version 1.1.0 corrected two entries after the version 1.0.0 probe run exposed
# them. Both were the same mistake: the aligner's symbol was preserved where its
# function should have been. Neither was found by reading the table, and neither
# faked an accent difference, because both hit every speaker group equally. They
# inflated the baseline flag rate instead, which is how they were caught.
MAPPING_AMENDMENTS = {
    "1.1.0": {
        "prompted_by": "the version 1.0.0 probe run, whose report is retained at .research_data/speech_sound_patterns/variety-probe/report-mapping-v1.0.0.json, SHA256 392c610d4cc1c87bda283e0cf4696afe5a614b95c48c5a4417a3525cbfa445c5",
        "corrections": {
            "ɫ": {
                "was": "ɫ",
                "now": "l",
                "evidence": "The frozen model emits ɫ zero times across 25 clips while emitting l 28 times. The token exists in the vocabulary and the model never uses it for English, so expecting it guaranteed a flag: 100.0 percent of ɫ opportunities were flagged in all three speaker groups.",
            },
            "ɫ̩": {
                "was": "ɫ",
                "now": "l",
                "evidence": "Follows the ɫ correction, since it resolved to the same unusable token.",
            },
            "d̪": {
                "was": "d",
                "now": "ð",
                "evidence": "The aligner transcribes the, that and this with d̪ at 0.99 probability, and the model uses ð for exactly those words. Mapping on symbol shape rather than function mis-expected the most frequent consonant context in English, which is why d was flagged in roughly half of about 1,300 opportunities.",
            },
        },
    },
    "1.2.0": {
        "prompted_by": "the 2026-08-22 direction change audit, which re-derived every published probe figure from the retained per clip evidence and found that most flags came from phones the model never produces for English. The superseded report is retained at .research_data/speech_sound_patterns/variety-probe/report-mapping-v1.1.0.json, SHA256 8156ce119af6b879b37f70b30a132fffab130e3e93638c2d41fa32043b856ee8",
        "corrections": {
            "c": {
                "was": "c",
                "now": "k",
                "evidence": "Flagged in 419 of 419 American reference opportunities and 336 of 336 British reference opportunities, at an identical 100.0 percent in the American control and in both comparison groups. The aligner writes the palatal stop for the velar stop before a front vowel. This is the dark l situation exactly: the token is in the model vocabulary and the model never uses it for English.",
            },
            "c\u02b0": {
                "was": "c\u02b0",
                "now": "k",
                "evidence": "Follows the c correction. Aspiration is predictable in a stressed onset and was already treated that way for the plain velar stop.",
            },
            "c\u02b7": {
                "was": "c",
                "now": "k",
                "evidence": "Previously resolved to c, which is itself unusable, so the labialisation entry inherited the defect rather than fixing it.",
            },
            "\u025f": {
                "was": "\u025f",
                "now": "\u0261",
                "evidence": "Flagged in 308 of 308 American reference opportunities and 155 of 155 British reference opportunities, at 100.0 percent in every speaker group. The voiced counterpart of the c correction.",
            },
            "\u025f\u02b7": {
                "was": "\u025f",
                "now": "\u0261",
                "evidence": "Previously resolved to \u025f, which is itself unusable, so the labialisation entry inherited the defect.",
            },
            "\u0272": {
                "was": "\u0272",
                "now": "n",
                "evidence": "Flagged in 756 of 760 American reference opportunities, 99.5 percent, and at 100.0 percent in the Australian group. The palatal nasal is the alveolar nasal before a front vowel.",
            },
            "\u00e7": {
                "was": "\u00e7",
                "now": "h",
                "evidence": "Flagged in 611 of 612 American reference opportunities, 99.8 percent, and 398 of 398 under the British reference. The palatal fricative is h before a front vowel, as in him and adhere. The checkpoint 22E8 secondary analysis excluded the other four palatals and missed this one.",
            },
            "\u028e": {
                "was": "\u028e",
                "now": "l",
                "evidence": "Flagged in 857 of 857 American reference opportunities and 747 of 747 British reference opportunities, at 100.0 percent in every group. The palatal lateral is l before a front vowel.",
            },
        },
        "note": "These five phone families and the glottal stop together supplied 38.9 percent of every flag the version 1.1.0 probe produced. Because they hit every speaker group at the same rate, they did not fake an accent difference directly. They inflated the baseline and, through differences in how often each group's prompts contained them, distorted the per consonant comparison that the checkpoint reported as its headline finding. The normalisation table in speech_sound_patterns/prompt_pack.py had already recorded the correct target for all five, with a written reason each, one checkpoint later. It was never applied back to the probe.",
    },
}

# Montreal Forced Aligner phones that the frozen model vocabulary does not carry
# verbatim, or carries but never uses. Most of the British inventory needs no
# entry here; these are the rest, and every one is a notation, allophone or
# vocabulary-coverage difference rather than a different sound. An unlisted phone
# is an error, never a silent drop.
PHONE_SUBSTITUTIONS = {
    # The aligner writes closing diphthongs with a glide; the model writes them
    # with a vowel. Same diphthong, different spelling.
    "aj": ("aɪ", "glide notation for the same closing diphthong"),
    "aw": ("aʊ", "glide notation for the same closing diphthong"),
    "ej": ("eɪ", "glide notation for the same closing diphthong"),
    "ɔj": ("ɔɪ", "glide notation for the same closing diphthong"),
    "əw": ("əʊ", "glide notation for the same closing diphthong"),
    "ow": ("oʊ", "glide notation for the same closing diphthong"),
    # Labialisation before a rounded vowel is a predictable allophone of the
    # plain stop, and the model vocabulary has no labialised series at all.
    "pʷ": ("p", "labialisation is a predictable allophone of the plain stop"),
    "tʷ": ("t", "labialisation is a predictable allophone of the plain stop"),
    "kʷ": ("k", "labialisation is a predictable allophone of the plain stop"),
    "cʷ": ("k", "labialisation is a predictable allophone, and the palatal stop is the velar stop before a front vowel"),
    "ɟʷ": ("ɡ", "labialisation is a predictable allophone, and the palatal stop is the velar stop before a front vowel"),
    "ɡʷ": ("ɡ", "labialisation is a predictable allophone of the plain stop"),
    "vʷ": ("v", "labialisation is a predictable allophone of the fricative"),
    # Syllabic consonants fall back to the plain consonant.
    "m̩": ("m", "the vocabulary has no syllabic m"),
    "ɫ̩": ("l", "the vocabulary has no syllabic l and never emits dark l"),
    # Dark l. Corrected at mapping version 1.1.0: the token is in the vocabulary
    # and the model never emits it, so expecting it flagged every opportunity.
    "ɫ": ("l", "the model never emits dark l for English, only plain l"),
    # The conditioned palatal series. Corrected at mapping version 1.2.0 for
    # exactly the dark l reason: every one of these is in the model vocabulary,
    # the model never uses any of them for English, and each was flagged at or
    # within half a point of 100 percent in every speaker group including the
    # American control. The aligner writes them where English has a plain
    # consonant before a front vowel. Targets follow the normalisation table in
    # prompt_pack.py, which recorded the same decisions one checkpoint later.
    "c": ("k", "the palatal stop is the velar stop before a front vowel"),
    "cʰ": ("k", "the palatal stop is the velar stop before a front vowel"),
    "ɟ": ("ɡ", "the palatal stop is the velar stop before a front vowel"),
    "ɲ": ("n", "the palatal nasal is the alveolar nasal before a front vowel"),
    "ç": ("h", "the palatal fricative is h before a front vowel, as in him"),
    "ʎ": ("l", "the palatal lateral is l before a front vowel"),
    # Corrected at mapping version 1.1.0. The aligner uses the dental stop for
    # the consonant of the, that and this, where the model uses the fricative.
    "d̪": ("ð", "the aligner writes the consonant of the and that as a dental stop"),
    "ɒː": ("ɔː", "the vocabulary has no long open back rounded vowel"),
    "ʉː": ("ʉ", "the vocabulary has no length marked barred u"),
    "ɝ": ("ɚ", "the same r coloured vowel, written stressed by the aligner"),
    "ɱ": ("m", "labiodental nasal is a predictable allophone before f and v"),
    "ɾʲ": ("ɾ", "palatalised flap is a predictable allophone of the flap"),
    "ɾ̃": ("ɾ", "nasal flap is a predictable allophone of the flap"),
}

# Model tokens that are vowels, restricted to what the two dictionaries can
# actually reach after substitution. Needed because post-vocalic is a position,
# not a symbol, and the rhotic rule below turns on it.
MODEL_VOWELS = frozenset(
    "a aɪ aʊ e eɪ i iː oʊ æ ɐ ɑ ɑː ɒ ɔɪ ɔː ə əʊ ɚ ɛ ɛː ɜ ɜː ɪ ʉ ʊ".split()
)

# The dictionary and the model disagree about whether post-vocalic r is its own
# segment. The dictionary writes "arts" as ɑ ɹ t s, two segments. The frozen
# model carries a single token, ɑːɹ, and emits it as one unit, so the expected
# standalone ɹ owns no frames and every opportunity was flagged: 96.6 percent in
# the American control, the Australian group and the British group alike, to
# three decimal places. That is a segmentation mismatch, not an accent effect,
# and it is the same class of defect as the d̪ correction at mapping version
# 1.1.0: matching on symbol shape rather than on function.
#
# Merging restores a correct expected sequence, which matters for the neighbours
# as well, because a segment the model never produces distorts the alignment of
# everything around it. Five correspondences cover 90.7 percent of the class.
# The model also carries oːɹ, which no Montreal Forced Aligner English vowel
# reaches, so nothing maps to it.
POST_VOCALIC_RHOTIC_MERGES = {
    ("ɒ", "ɹ"): ("ɔːɹ", "NORTH and FORCE, as in for and north"),
    ("ɔː", "ɹ"): ("ɔːɹ", "NORTH and FORCE, reached through the ɒː substitution"),
    ("ɑ", "ɹ"): ("ɑːɹ", "START, as in arts and park"),
    ("ɑː", "ɹ"): ("ɑːɹ", "START, where the dictionary writes the long vowel"),
    ("ɛ", "ɹ"): ("ɛɹ", "SQUARE, as in there"),
    ("ɪ", "ɹ"): ("ɪɹ", "NEAR, as in here"),
    ("ʊ", "ɹ"): ("ʊɹ", "CURE, as in poor and tour"),
}

# Phones this reference can express but must never score, with the reason.
# Unlike PHONE_SUBSTITUTIONS these are not renamed, because renaming them would
# subtract a real variety difference rather than excluding an unusable one. They
# stay in the expected sequence, so the sequence remains complete and scoreable
# around them, and they never become a target.
UNSCORABLE_PHONES = {
    "ʔ": (
        "the model never emits a glottal stop for English, so every opportunity "
        "was flagged, 176 of 176 under the British reference. Coda t glottalling "
        "is a genuine variety difference, so mapping this to t would subtract "
        "the difference instead of excluding it. prompt_pack.py refuses the "
        "phone outright for the same reason."
    ),
}

# A post-vocalic ɹ that no merge covers, which is the remaining 9.3 percent such
# as fire and hour where the preceding vowel is a diphthong and the model has no
# combined token. The segmentation mismatch still applies, so the opportunity is
# unscorable. It is excluded rather than renamed, for the same reason the glottal
# stop is: a mismatch may be excluded and never subtracted.
UNMERGED_POST_VOCALIC_RHOTIC = (
    "the model merges post-vocalic r into the preceding vowel and has no "
    "combined token for this one, so the expected standalone ɹ owns no frames"
)

# What this checkpoint scores. Consonants only, exactly as every earlier item 22
# measurement. That is not a limitation here but the point: the sharpest British
# and Australian difference from American English, post-vocalic /ɹ/, is itself a
# consonant, and so are t flapping and yod.
# Dark l is absent: nothing maps to it since mapping version 1.1.0, because the
# model never emits it. The conditioned palatal series c, ɟ, ɲ, ç and ʎ is absent
# for the same reason since mapping version 1.2.0, and the glottal stop is absent
# because it is unscorable rather than substitutable.
SCORABLE_CONSONANTS = frozenset(
    "p b t d k ɡ m n ŋ f v θ ð s z ʃ ʒ h l ɹ j w tʃ dʒ ɾ".split()
)

WORD_PATTERN = re.compile(r"[a-z']+")


class VarietyReferenceError(ValueError):
    """Raised when an expected pronunciation cannot be established honestly."""


def normalise(token):
    return unicodedata.normalize("NFC", token)


def load_model_vocabulary(path=MODEL_VOCAB):
    if not Path(path).is_file():
        raise VarietyReferenceError(
            "the frozen model vocabulary is missing; the reference cannot be "
            "expressed in tokens the model does not have"
        )
    return json.loads(Path(path).read_text(encoding="utf-8"))


def vocabulary_index(vocabulary):
    """Index the vocabulary by canonical form rather than by exact bytes.

    The frozen vocabulary is not written in one normal form. Most of it decomposes
    harmlessly, but a few entries are precomposed, and `ç` is one of them. A
    lookup that assumed either form would silently refuse a phone the model
    actually has, which would quietly shrink the reference instead of failing.
    """
    index = {}
    for token in vocabulary:
        index.setdefault(normalise(token), token)
    return index


def map_phone(phone, index):
    """Return the model token for one aligner phone, or fail closed."""
    if phone in ALIGNER_TOKENS:
        raise VarietyReferenceError(f"{phone} is aligner machinery, not a phone")
    token, reason = PHONE_SUBSTITUTIONS.get(phone, (phone, None))
    actual = index.get(normalise(token))
    if actual is None:
        raise VarietyReferenceError(
            f"aligner phone {phone!r} maps to {token!r}, which the frozen model "
            "vocabulary does not contain"
        )
    return actual, reason


def build_phone_mapping(phones, index):
    """Map a whole aligner inventory, recording every decision that was made."""
    direct = {}
    substituted = {}
    refused = {}
    for phone in sorted(phones):
        if phone in ALIGNER_TOKENS:
            refused[phone] = "aligner machinery, not a phone"
            continue
        try:
            token, reason = map_phone(phone, index)
        except VarietyReferenceError as error:
            refused[phone] = str(error)
            continue
        if reason is None:
            direct[phone] = token
        else:
            substituted[phone] = {"token": token, "reason": reason}
    return {
        "direct": direct,
        "substituted": substituted,
        "refused": refused,
        "phones_seen": len(phones),
    }


def load_dictionary(name, root=DICTIONARY_ROOT):
    """Read an aligner dictionary as word to pronunciations, most likely first."""
    path = Path(root) / f"{name}.dict"
    if not path.is_file():
        raise VarietyReferenceError(f"dictionary {name} is not acquired")
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        fields = line.split("\t")
        word = fields[0]
        phones = tuple(fields[-1].split())
        try:
            probability = float(fields[1]) if len(fields) > 2 else 1.0
        except ValueError:
            probability = 1.0
        entries.setdefault(word, []).append((probability, phones))
    return {
        word: [phones for _, phones in sorted(items, key=lambda item: -item[0])]
        for word, items in entries.items()
    }


def dictionary_phones(dictionary):
    return {phone for items in dictionary.values() for item in items for phone in item}


def load_australian_overlay(path=AUSTRALIAN_OVERLAY):
    """Return Australian tagged pronunciations, phonemic transcriptions only.

    A transcription in brackets is a narrower claim about one production than a
    transcription in slashes, so only the phonemic forms are read. The overlay
    is not a second opinion to average with the British reference; where the two
    disagree and the overlay is silent, the opportunity is unscorable.
    """
    if not Path(path).is_file():
        raise VarietyReferenceError("the Australian tagged overlay is not extracted")
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    overlay = {}
    for word, items in document["entries"].items():
        forms = [
            item["ipa"].strip("/")
            for item in items
            if item["ipa"].startswith("/") and item["ipa"].endswith("/")
        ]
        if forms:
            overlay[word] = sorted(set(forms))
    return overlay


def tokenise(sentence):
    """Split a Common Voice prompt into dictionary lookups.

    Quotation marks in a prompt survive the word pattern as bare apostrophes,
    which are then looked up as words and refuse the whole prompt. They carry no
    sound, so they are dropped rather than refused. Contractions and possessives
    that the dictionaries genuinely lack are still refused, because inventing a
    pronunciation for them would be generating a target rather than reading one.
    """
    tokens = WORD_PATTERN.findall(sentence.lower().replace("’", "'"))
    return [token.strip("'") for token in tokens if token.strip("'")]


def _overlay_tokens(forms, index):
    """Map Wiktionary phonemic forms into model tokens, longest symbol first.

    Wiktionary transcriptions carry stress and syllable marks that the model has
    no tokens for. They are dropped, because they are not sounds. Anything left
    that the model does not have makes the whole form unusable rather than
    partially usable.
    """
    usable = []
    for form in forms:
        cleaned = form.replace("ˈ", "").replace("ˌ", "").replace(".", "")
        tokens = []
        position = 0
        while position < len(cleaned):
            for length in (3, 2, 1):
                candidate = cleaned[position : position + length]
                if candidate and normalise(candidate) in index:
                    tokens.append(index[normalise(candidate)])
                    position += length
                    break
            else:
                tokens = None
                break
        if tokens:
            usable.append(tuple(tokens))
    return usable


def word_pronunciation(word, dictionary, index, overlay=None):
    """Return the expected tokens for one word, and why if there are none.

    The overlay never averages with the dictionary and never subtracts from it.
    Where the two agree the opportunity is scorable on the agreed form. Where
    they disagree, the Australian form wins if one exists, because it is the
    variety under test. Where they disagree and the overlay is silent, the
    opportunity is unscorable, which is the rule a variety mismatch always gets:
    it may be excluded, never corrected for.
    """
    entries = dictionary.get(word)
    if not entries:
        return None, "word_not_in_dictionary"
    try:
        base = tuple(map_phone(phone, index)[0] for phone in entries[0])
    except VarietyReferenceError:
        return None, "pronunciation_uses_an_unmappable_phone"
    if overlay is None:
        return base, None
    australian = _overlay_tokens(overlay.get(word, []), index)
    if not australian:
        return base, None
    if base in australian:
        return base, None
    return australian[0], None


def expected_sequence(sentence, dictionary, index, overlay=None):
    """Turn a known prompt into the phone sequence a variety would expect.

    Every word must be known. A sentence with one unknown word is refused whole
    rather than scored on the part that happened to be in the dictionary, because
    the missing word's phones would still be in the audio and would distort the
    likelihood of everything around them.
    """
    words = tokenise(sentence)
    if not words:
        return None, "prompt_has_no_words"
    tokens = []
    word_spans = []
    for word in words:
        pronunciation, reason = word_pronunciation(word, dictionary, index, overlay)
        if pronunciation is None:
            return None, reason
        pronunciation = merge_post_vocalic_rhotics(pronunciation, index)
        word_spans.append(
            {"word": word, "start": len(tokens), "end": len(tokens) + len(pronunciation)}
        )
        tokens.extend(pronunciation)
    return {"tokens": tokens, "words": word_spans}, None


def merge_post_vocalic_rhotics(pronunciation, index=None):
    """Join a vowel and a following post-vocalic ɹ into the model's own token.

    Applied inside one word, so word spans stay correct and a following word
    beginning with a vowel cannot pull an onset ɹ into a merge it does not
    belong in. A ɹ before a vowel is an onset and is never merged.
    """
    tokens = list(pronunciation)
    merged = []
    position = 0
    while position < len(tokens):
        token = tokens[position]
        following = tokens[position + 1] if position + 1 < len(tokens) else None
        after = tokens[position + 2] if position + 2 < len(tokens) else None
        if (
            following == "ɹ"
            and (after is None or after not in MODEL_VOWELS)
            and (token, "ɹ") in POST_VOCALIC_RHOTIC_MERGES
        ):
            combined = POST_VOCALIC_RHOTIC_MERGES[(token, "ɹ")][0]
            if index is None or index.get(normalise(combined)) is not None:
                merged.append(combined)
                position += 2
                continue
        merged.append(token)
        position += 1
    return tuple(merged)


def is_post_vocalic_rhotic(tokens, position):
    """Whether the ɹ at this position follows a vowel and precedes no vowel."""
    if tokens[position] != "ɹ" or position == 0:
        return False
    if tokens[position - 1] not in MODEL_VOWELS:
        return False
    following = tokens[position + 1] if position + 1 < len(tokens) else None
    return following is None or following not in MODEL_VOWELS


def consonant_targets(tokens):
    """Index every scorable consonant opportunity in an expected sequence.

    A post-vocalic ɹ that survived merging is skipped. The model has no combined
    token for it, so the expected segment owns no frames and the opportunity is
    unscorable rather than wrong.
    """
    targets = []
    for position, token in enumerate(tokens):
        if token not in SCORABLE_CONSONANTS:
            continue
        if token == "ɹ" and is_post_vocalic_rhotic(tokens, position):
            continue
        targets.append({"index": position, "token": token})
    return targets
