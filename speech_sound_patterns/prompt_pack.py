"""Checkpoint 22F conservative research prompt pack.

Every item 22 measurement so far has read other people's recordings against other
people's sentences. To ask whether a person produced the ``s`` at the start of
*safe*, two things must exist first: a known word they were asked to say, and a
defensible written statement of what that word's consonants are. Neither exists
in this project. This module builds the second one for twenty chosen words.

The pack is a written list. It records nothing about any speaker, scores nobody,
selects nothing and produces no artifact. Checkpoint 22G, which builds the
candidate extractor, has nothing to point at until it exists.

Three rules carry the weight here:

- **Two documented varieties, unioned, never averaged.** Every word must carry a
  British broad transcription in the Montreal Forced Aligner English (UK)
  dictionary *and* an Australian tagged pronunciation in Wiktionary. Where the
  two agree the position is scorable. Where they disagree it is unscorable, and
  neither form is an error. A variety mismatch may be excluded but never
  subtracted.
- **Broad phonemes, not the aligner's allophones.** The aligner writes
  aspiration, palatalisation, labialisation, dentality and dark l as separate
  symbols. Those are transcription detail, not different sounds, and the
  protocol makes broad IPA the default because finer detail reduces agreement.
  Every normalisation below carries a written reason, and a symbol neither table
  names refuses the word rather than being dropped.
- **Refuse where the varieties genuinely differ.** Post-vocalic rhotics,
  flapping and glottalling contexts, postvocalic l and the dental fricatives are
  unscorable, each citing evidence recorded inside this repository. That list is
  this project's own construction and is not claimed to be complete.

No target here is machine generated. Every phoneme traces to a published
dictionary entry or a Wiktionary entry, which is why no grapheme-to-phoneme
model appears anywhere in this file.
"""

from __future__ import annotations

import json
from pathlib import Path

from .corpus_manifest import REPOSITORY_ROOT
from .variety_reference import (
    DICTIONARY_ROOT,
    load_australian_overlay,
    load_dictionary,
    load_model_vocabulary,
    normalise,
    vocabulary_index,
)

PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
PACK_ROOT = PRIVATE_ROOT / "prompt-pack"
CONTRACT_PATH = Path(__file__).with_name("prompt-pack-contract-v1.0.0.json")
PACK_PATH = Path(__file__).with_name("research-prompt-pack-v1.0.0.json")

BRITISH_DICTIONARY = "english_uk_mfa"


class PromptPackError(ValueError):
    """Raised when an expected pronunciation cannot be established honestly.

    A refusal carries a stable code as well as a sentence. The code is what the
    eligible pool counts by, because counting by message would put a stray
    Wiktionary character into a committed file and would split one reason across
    as many buckets as there are odd symbols.
    """

    def __init__(self, message, code="unreadable_source_material"):
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------
# The pack's alphabet
# --------------------------------------------------------------------------

# Broad phonemic English consonants. Two of these, the dental fricatives, are
# recognised here so that a word containing them can still be read, and are then
# refused as opportunities by a variety rule below. Recognising a sound and
# scoring it are different things.
ENGLISH_CONSONANTS = frozenset(
    "p b t d k ɡ m n ŋ f v θ ð s z ʃ ʒ h l ɹ j w tʃ dʒ".split()
)

DENTAL_FRICATIVES = frozenset({"θ", "ð"})


# --------------------------------------------------------------------------
# Montreal Forced Aligner English (UK) -> broad phoneme
# --------------------------------------------------------------------------

# Every symbol the British dictionary uses. An entry maps to a phoneme and says
# why. Aspiration, palatalisation, labialisation, palatal place, dentality,
# darkness and syllabicity are all predictable detail rather than separate
# English sounds, and the protocol's default representation is broad.
ALIGNER_CONSONANTS = {
    "p": ("p", None),
    "pʰ": ("p", "aspiration is predictable in a stressed onset"),
    "pʲ": ("p", "palatalisation before a front vowel is predictable"),
    "pʷ": ("p", "labialisation before a rounded vowel is predictable"),
    "b": ("b", None),
    "bʲ": ("b", "palatalisation before a front vowel is predictable"),
    "t": ("t", None),
    "tʰ": ("t", "aspiration is predictable in a stressed onset"),
    "tʲ": ("t", "palatalisation before a front vowel is predictable"),
    "tʷ": ("t", "labialisation before a rounded vowel is predictable"),
    "t̪": ("θ", "the aligner writes the fricative of bath and both as a dental stop"),
    "d": ("d", None),
    "dʲ": ("d", "palatalisation before a front vowel is predictable"),
    "d̪": ("ð", "the aligner writes the consonant of the and that as a dental stop"),
    "k": ("k", None),
    "kʰ": ("k", "aspiration is predictable in a stressed onset"),
    "kʷ": ("k", "labialisation before a rounded vowel is predictable"),
    "c": ("k", "the palatal stop is the velar stop before a front vowel"),
    "cʰ": ("k", "the palatal stop is the velar stop before a front vowel"),
    "cʷ": ("k", "the palatal stop is the velar stop before a front vowel"),
    "ɡ": ("ɡ", None),
    "ɡʷ": ("ɡ", "labialisation before a rounded vowel is predictable"),
    "ɟ": ("ɡ", "the palatal stop is the velar stop before a front vowel"),
    "ɟʷ": ("ɡ", "the palatal stop is the velar stop before a front vowel"),
    "m": ("m", None),
    "mʲ": ("m", "palatalisation before a front vowel is predictable"),
    "m̩": ("m", "syllabic m is the plain nasal carrying a syllable"),
    "n": ("n", None),
    "n̩": ("n", "syllabic n is the plain nasal carrying a syllable"),
    "ɲ": ("n", "the palatal nasal is the alveolar nasal before a front vowel"),
    "ŋ": ("ŋ", None),
    "f": ("f", None),
    "fʲ": ("f", "palatalisation before a front vowel is predictable"),
    "v": ("v", None),
    "vʲ": ("v", "palatalisation before a front vowel is predictable"),
    "vʷ": ("v", "labialisation before a rounded vowel is predictable"),
    "θ": ("θ", None),
    "ð": ("ð", None),
    "s": ("s", None),
    "z": ("z", None),
    "ʃ": ("ʃ", None),
    "ʒ": ("ʒ", None),
    "h": ("h", None),
    "ç": ("h", "the palatal fricative is h before a front vowel, as in him and adhere"),
    "l": ("l", None),
    "ɫ": ("l", "dark l is l in a coda; the frozen local model never emits it for English"),
    "ɫ̩": ("l", "syllabic dark l is l carrying a syllable"),
    "ʎ": ("l", "the palatal lateral is l before a front vowel"),
    "ɹ": ("ɹ", None),
    "j": ("j", None),
    "w": ("w", None),
    "tʃ": ("tʃ", None),
    "dʒ": ("dʒ", None),
}

# Syllabic consonants are recognised so the word can be read, and then refused as
# opportunities, because reductions are outside the first measurable scope.
ALIGNER_SYLLABIC = frozenset({"m̩", "n̩", "ɫ̩"})

ALIGNER_VOWELS = frozenset(
    "ə ɪ ɛ a i ɒ ej əw aj iː ɐ ɑː ɒː ʉː ɜː ʊ aw ɛː ɔj ʉ ɑ ɜ e".split()
)

# Recognised, and fatal to the word rather than silently mapped.
ALIGNER_REFUSED = {
    "ʔ": "the aligner records a glottal variant here, which the first measurable scope excludes",
    "spn": "spoken noise is aligner machinery, not a phone",
    "<unk>": "aligner machinery, not a phone",
    "<cutoff>": "aligner machinery, not a phone",
    "[bracketed]": "aligner machinery, not a phone",
    "[laughter]": "aligner machinery, not a phone",
}


# --------------------------------------------------------------------------
# Wiktionary Australian tagged transcriptions -> broad phoneme
# --------------------------------------------------------------------------

WIKTIONARY_CONSONANTS = {
    "p": "p",
    "b": "b",
    "t": "t",
    "d": "d",
    "k": "k",
    "ɡ": "ɡ",
    "m": "m",
    "n": "n",
    "ŋ": "ŋ",
    "f": "f",
    "v": "v",
    "θ": "θ",
    "ð": "ð",
    "s": "s",
    "z": "z",
    "ʃ": "ʃ",
    "ʒ": "ʒ",
    "h": "h",
    "l": "l",
    "ɫ": "l",
    "ɹ": "ɹ",
    "r": "ɹ",
    "j": "j",
    "w": "w",
    "tʃ": "tʃ",
    "t͡ʃ": "tʃ",
    "dʒ": "dʒ",
    "d͡ʒ": "dʒ",
}

WIKTIONARY_VOWELS = frozenset(
    "ə ɪ æ e i ʉ ɔ ɐ ɑ o ɜ ʊ a ɛ ɒ ʌ u ɘ ɵ œ y ä õ".split()
)

# Stress, syllable and length marks carry no consonant identity and are dropped.
WIKTIONARY_DROPPED_MARKS = "ˈˌ.ː"

# Narrow quality marks that Wiktionary contributors sometimes place inside a
# phonemic transcription. They are dropped only when they sit on a vowel, which
# this pack does not score. On a consonant they refuse the form, because a narrow
# claim about a consonant is exactly what must not be silently discarded.
WIKTIONARY_VOWEL_DIACRITICS = "̯̝̞̟̈"


# --------------------------------------------------------------------------
# Reading a word out of each source
# --------------------------------------------------------------------------


def segment_aligner_form(form):
    """Turn one aligner pronunciation into broad segments, or fail closed."""
    segments = []
    for symbol in form:
        symbol = normalise(symbol)
        if symbol in ALIGNER_REFUSED:
            raise PromptPackError(
                ALIGNER_REFUSED[symbol], "refused_symbol_in_a_documented_form"
            )
        if symbol in ALIGNER_VOWELS:
            segments.append({"kind": "vowel"})
            continue
        entry = ALIGNER_CONSONANTS.get(symbol)
        if entry is None:
            raise PromptPackError(
                f"aligner symbol {symbol!r} is in neither normalisation table",
                "unreadable_symbol_in_a_documented_form",
            )
        segments.append(
            {
                "kind": "consonant",
                "phoneme": entry[0],
                "syllabic": symbol in ALIGNER_SYLLABIC,
            }
        )
    return segments


def segment_wiktionary_form(form):
    """Turn one Wiktionary phonemic transcription into broad segments.

    Longest symbol first, because a tie barred affricate is three characters and
    its first character is a stop the table also knows. Anything the tables do
    not name refuses the form whole; a partly readable transcription is not a
    readable one.
    """
    kept = []
    for character in normalise(form):
        if character in WIKTIONARY_DROPPED_MARKS:
            continue
        if character in WIKTIONARY_VOWEL_DIACRITICS:
            if not kept or kept[-1] not in WIKTIONARY_VOWELS:
                raise PromptPackError(
                    "a narrow quality mark sits on a consonant, which is a "
                    "claim this pack may not discard",
                    "narrow_quality_mark_on_a_consonant",
                )
            continue
        kept.append(character)
    cleaned = "".join(kept)
    segments = []
    position = 0
    while position < len(cleaned):
        for length in (3, 2, 1):
            candidate = cleaned[position : position + length]
            if not candidate:
                continue
            if candidate in WIKTIONARY_CONSONANTS:
                segments.append(
                    {
                        "kind": "consonant",
                        "phoneme": WIKTIONARY_CONSONANTS[candidate],
                        "syllabic": False,
                    }
                )
                position += length
                break
            if candidate in WIKTIONARY_VOWELS:
                segments.append({"kind": "vowel"})
                position += length
                break
        else:
            raise PromptPackError(
                f"Wiktionary symbol {cleaned[position]!r} is in neither "
                "normalisation table",
                "unreadable_symbol_in_a_documented_form",
            )
    if not segments:
        raise PromptPackError(
            "the transcription holds no readable segments",
            "unreadable_symbol_in_a_documented_form",
        )
    return segments


def read_word(word, dictionary, overlay):
    """Return every documented British and Australian reading of one word.

    The verbatim form travels beside the segments, because the pack's private
    record keeps what the publishers actually wrote and the committed pack keeps
    only the consonant opportunities derived from it.
    """
    british = dictionary.get(word)
    if not british:
        raise PromptPackError(
            "the word is not in the British reference dictionary",
            "absent_from_the_british_reference",
        )
    australian = overlay.get(word)
    if not australian:
        raise PromptPackError(
            "the word carries no Australian tagged pronunciation",
            "no_australian_tagged_pronunciation",
        )
    readings = []
    for form in british:
        readings.append(("british", " ".join(form), segment_aligner_form(form)))
    for form in australian:
        readings.append(("australian", form, segment_wiktionary_form(form)))
    return readings


# --------------------------------------------------------------------------
# Consonant opportunities
# --------------------------------------------------------------------------


def consonant_frame(segments):
    """Describe every consonant in one reading by position and context."""
    frame = []
    for index, segment in enumerate(segments):
        if segment["kind"] != "consonant":
            continue
        frame.append(
            {
                "phoneme": segment["phoneme"],
                "syllabic": segment["syllabic"],
                "position": (
                    "initial"
                    if index == 0
                    else "final"
                    if index == len(segments) - 1
                    else "medial"
                ),
                "prevocalic": index + 1 < len(segments)
                and segments[index + 1]["kind"] == "vowel",
                "postvocalic": index > 0 and segments[index - 1]["kind"] == "vowel",
            }
        )
    return frame


def variety_refusal(entry):
    """Return the variety rule that refuses this opportunity, or None.

    Every rule cites evidence recorded inside this repository. The list is this
    project's own construction, because no external guidance enumerates dialect
    stable English segments, and it is not claimed to be complete.
    """
    if entry["syllabic"]:
        return "syllabic_consonant_reduction"
    phoneme = entry["phoneme"]
    if phoneme == "ɹ" and not entry["prevocalic"]:
        return "post_vocalic_rhotic"
    if phoneme in ("t", "d") and entry["postvocalic"] and entry["prevocalic"]:
        return "intervocalic_flapping_context"
    if phoneme == "t" and not entry["prevocalic"]:
        return "coda_t_glottalling"
    if phoneme == "l" and not entry["prevocalic"]:
        return "coda_l_vocalisation"
    if phoneme in DENTAL_FRICATIVES:
        return "dental_fricative_variation"
    return None


def opportunities(readings):
    """Compare every documented reading position by position.

    A word whose readings disagree on how many consonants they contain is
    refused whole, because positions that cannot be aligned cannot be compared.
    A word whose readings disagree at one position keeps the rest and marks that
    one unscorable.
    """
    frames = [consonant_frame(segments) for _, _, segments in readings]
    lengths = {len(frame) for frame in frames}
    if len(lengths) != 1:
        raise PromptPackError(
            "the documented readings disagree on how many consonants the word "
            "has, so their positions cannot be aligned",
            "documented_readings_disagree_on_consonant_count",
        )
    count = lengths.pop()
    if count == 0:
        # A word made only of vowels carries nothing this pack can probe, and
        # admitting it would put an empty opportunity list into the pool.
        raise PromptPackError(
            "the word has no consonant this pack could probe",
            "no_consonant_opportunity",
        )
    results = []
    for index in range(count):
        entries = [frame[index] for frame in frames]
        agreed = all(entry == entries[0] for entry in entries)
        if not agreed:
            results.append(
                {
                    "opportunity": index,
                    "phonemes_documented": sorted({entry["phoneme"] for entry in entries}),
                    "state": "unscorable",
                    "reason": "documented_variant_disagreement",
                }
            )
            continue
        entry = entries[0]
        reason = variety_refusal(entry)
        results.append(
            {
                "opportunity": index,
                "phoneme": entry["phoneme"],
                "position": entry["position"],
                "prevocalic": entry["prevocalic"],
                "postvocalic": entry["postvocalic"],
                "syllabic": entry["syllabic"],
                "state": "unscorable" if reason else "scorable",
                "reason": reason,
            }
        )
    return results


# --------------------------------------------------------------------------
# Eligibility and the pool the twenty were chosen from
# --------------------------------------------------------------------------


def is_ordinary_word(word):
    """Affixes, contractions and aligner tokens are not prompts."""
    return word.isalpha() and len(word) >= 3


def describe_word(word, dictionary, overlay):
    """Return the opportunities for one word, or the reason there are none."""
    try:
        readings = read_word(word, dictionary, overlay)
        return opportunities(readings), readings, None
    except PromptPackError as error:
        return None, None, (error.code, str(error))


# Every reason a whole word can be refused. Reported with zeros for the same
# reason the opportunity reasons are: a guard that never fires is evidence that
# it held, and an absent key would be indistinguishable from a guard nobody
# wrote.
WORD_REFUSAL_REASONS = (
    "not_an_ordinary_word",
    "absent_from_the_british_reference",
    "no_australian_tagged_pronunciation",
    "refused_symbol_in_a_documented_form",
    "unreadable_symbol_in_a_documented_form",
    "narrow_quality_mark_on_a_consonant",
    "documented_readings_disagree_on_consonant_count",
    "no_consonant_opportunity",
)


def build_pool(dictionary, overlay):
    """Every word the mechanical rules admit, and why the rest were refused.

    The twenty chosen words are a human choice, so the honest way to show that
    they were chosen rather than merely available is to report the size and
    shape of what they were chosen from.
    """
    eligible = {}
    refusals = {reason: 0 for reason in WORD_REFUSAL_REASONS}
    for word in sorted(dictionary):
        if not is_ordinary_word(word):
            refusals["not_an_ordinary_word"] += 1
            continue
        found, _, refusal = describe_word(word, dictionary, overlay)
        if found is None:
            code = refusal[0]
            if code not in refusals:
                # A code the reported table does not name would vanish from the
                # pool report, which is the one place these refusals are visible.
                raise PromptPackError(
                    f"refusal code {code!r} is not in the reported table",
                    "unlisted_refusal_code",
                )
            refusals[code] += 1
            continue
        eligible[word] = found
    return eligible, refusals


# Every reason an opportunity can be refused, so the pool report can carry a
# zero rather than an absence. A rule that never fires is a finding, not a gap
# in the report.
OPPORTUNITY_REFUSAL_REASONS = (
    "post_vocalic_rhotic",
    "intervocalic_flapping_context",
    "coda_t_glottalling",
    "coda_l_vocalisation",
    "dental_fricative_variation",
    "syllabic_consonant_reduction",
    "documented_variant_disagreement",
)


def refusal_counts(eligible):
    """How often each variety rule fires across the whole eligible pool.

    The twenty chosen words deliberately avoid most of these contexts, so
    counting refusals inside the pack alone would make the rules look
    theoretical. They are not: this is how much they remove at scale. Every
    reason is reported including the ones that never fire, because the rhotic
    reading zero is itself the point: under a non-rhotic British reference the
    opportunity mostly does not exist to be refused.
    """
    counts = {reason: 0 for reason in OPPORTUNITY_REFUSAL_REASONS}
    scorable = 0
    for found in eligible.values():
        for item in found:
            if item["state"] == "scorable":
                scorable += 1
            else:
                counts[item["reason"]] += 1
    return {"scorable": scorable, "unscorable_by_reason": counts}


# --------------------------------------------------------------------------
# Building the pack
# --------------------------------------------------------------------------


def load_contract(path=CONTRACT_PATH):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    boundaries = contract["release_boundaries"]
    if any(boundaries[flag] for flag in boundaries):
        raise PromptPackError(
            "the pack contract must keep every release boundary closed",
            "open_release_boundary",
        )
    return contract


def expressible_in_local_vocabulary(phonemes, index):
    """Check the pack's phonemes exist in the one local phone vocabulary held.

    This is a sanity check, not a selection. No system is selected, and the pack
    is expressed in the published dictionaries' own alphabet rather than in any
    model's tokens. But a pack whose targets no held system could ever name
    would be unusable in principle, and that is worth knowing before 22G starts
    rather than after.
    """
    missing = sorted(phoneme for phoneme in phonemes if normalise(phoneme) not in index)
    return missing


def coverage(pack_words):
    """Which positions each probed consonant reaches across the whole pack."""
    seen = {}
    for entry in pack_words:
        for item in entry["opportunities"]:
            if item["state"] != "scorable":
                continue
            seen.setdefault(item["phoneme"], set()).add(item["position"])
    return {phoneme: sorted(positions) for phoneme, positions in sorted(seen.items())}


def build_pack(contract=None, dictionary_root=DICTIONARY_ROOT):
    """Verify every chosen word against every rule and assemble the pack.

    Nothing here chooses a word. The contract chose them, before any dictionary
    was read, with a written reason each. This verifies that choice and refuses
    the whole build if one word does not pass.
    """
    contract = contract or load_contract()
    boundaries = contract["release_boundaries"]
    if any(boundaries[flag] for flag in boundaries):
        # Checked here as well as in load_contract, because a contract handed in
        # directly must clear the same bar as one read off disk.
        raise PromptPackError(
            "the pack contract must keep every release boundary closed",
            "open_release_boundary",
        )
    dictionary = load_dictionary(BRITISH_DICTIONARY, root=dictionary_root)
    overlay = load_australian_overlay()
    index = vocabulary_index(load_model_vocabulary())

    chosen = [item["word"] for item in contract["word_selection"]["words"]]
    if len(set(chosen)) != len(chosen):
        raise PromptPackError("the contract lists a word twice")
    if len(chosen) != contract["word_selection"]["target_word_count"]:
        raise PromptPackError(
            f"the contract lists {len(chosen)} words against a target of "
            f"{contract['word_selection']['target_word_count']}"
        )

    words = []
    private = {}
    for item in contract["word_selection"]["words"]:
        word = item["word"]
        found, readings, refusal = describe_word(word, dictionary, overlay)
        if found is None:
            raise PromptPackError(
                f"chosen word {word!r} is not eligible: {refusal[1]}",
                "chosen_word_is_not_eligible",
            )
        words.append(
            {
                "word": word,
                "written_prompt": word,
                "selection_reason": item["reason"],
                "british_forms": sum(
                    1 for source, _, _ in readings if source == "british"
                ),
                "australian_forms": sum(
                    1 for source, _, _ in readings if source == "australian"
                ),
                "opportunities": found,
                "scorable_opportunities": sum(
                    1 for entry in found if entry["state"] == "scorable"
                ),
            }
        )
        private[word] = {
            "british_forms": [
                form for source, form, _ in readings if source == "british"
            ],
            "australian_forms": [
                form for source, form, _ in readings if source == "australian"
            ],
        }

    reached = coverage(words)
    missing = expressible_in_local_vocabulary(reached, index)
    if missing:
        raise PromptPackError(
            "the pack probes phonemes the one locally held phone vocabulary "
            f"cannot express: {missing}"
        )

    shortfalls = {
        item["phoneme"]: item
        for item in contract["coverage_requirement"]["declared_shortfalls"]
    }
    for phoneme, positions in reached.items():
        if len(positions) >= 2:
            continue
        declared = shortfalls.get(phoneme)
        if declared is None or declared["positions_achieved"] != len(positions):
            raise PromptPackError(
                f"{phoneme} reaches {len(positions)} position(s) and the contract "
                "does not declare that shortfall"
            )
    for phoneme, declared in shortfalls.items():
        if declared["positions_achieved"] != len(reached.get(phoneme, [])):
            raise PromptPackError(
                f"the contract declares {phoneme} at "
                f"{declared['positions_achieved']} position(s) and the pack "
                f"reaches {len(reached.get(phoneme, []))}"
            )

    eligible, refusals = build_pool(dictionary, overlay)
    for word in chosen:
        if word not in eligible:
            raise PromptPackError(f"chosen word {word!r} is not in the eligible pool")

    pack = {
        "schema_version": "1.0.0",
        "pack_id": "speech_sound_patterns_research_prompt_pack_v1",
        "pack_version": "1.0.0",
        "checkpoint": "22F",
        "status": "developer_research_pack_not_reviewed_not_active",
        "contract_id": contract["pack_contract_id"],
        "elicitation_modes": {
            "written_word": contract["elicitation_modes"]["written_word"]["state"],
            "recorded_prompt_alternative": contract["elicitation_modes"][
                "recorded_prompt_alternative"
            ]["state"],
            "modes_are_comparable": False,
        },
        "references": {
            "british": {
                "source_id": "mfa_english_dictionary",
                "file": f"{BRITISH_DICTIONARY}.dict",
            },
            "australian_overlay": {
                "source_id": "wiktionary_australian_kaikki",
                "transcriptions_used": "phonemic only",
            },
            "machine_generated_targets": False,
        },
        "words": words,
        "totals": {
            "words": len(words),
            "opportunities": sum(len(entry["opportunities"]) for entry in words),
            "scorable_opportunities": sum(
                entry["scorable_opportunities"] for entry in words
            ),
            "unscorable_opportunities": sum(
                len(entry["opportunities"]) - entry["scorable_opportunities"]
                for entry in words
            ),
            "words_with_more_than_one_documented_form": sum(
                1
                for entry in words
                if entry["british_forms"] + entry["australian_forms"] > 2
            ),
        },
        "coverage": reached,
        "declared_shortfalls": contract["coverage_requirement"]["declared_shortfalls"],
        "eligible_pool": {
            "words": len(eligible),
            "why_this_is_reported": (
                "The twenty words are a human choice. Reporting the size and "
                "shape of the pool they were chosen from is how that choice "
                "stays auditable."
            ),
            "refusals_by_reason": refusals,
            "opportunity_refusals_across_the_pool": refusal_counts(eligible),
        },
        "content_screen": contract["sensitive_content_screen"],
        "unmet_activation_requirements": contract["unmet_activation_requirements"],
        "distribution_boundary": {
            "derived_lexicon_stays_server_side": True,
            "what_stays_private": contract["distribution_boundary"][
                "what_stays_private"
            ],
            "attribution_required": contract["distribution_boundary"][
                "attribution_required"
            ],
        },
        "limitations": [
            "A lexicon proposes how a word may be said and never observes how anybody said it, so nothing in this pack is truth about a pronunciation.",
            "The pack is not professionally reviewed. Familiarity, cultural suitability and the phonetic content of every item all still require qualified review.",
            "The variety sensitive exclusion list is this project's own construction, built from evidence recorded in this repository, and is not claimed to be complete. A consonant marked scorable here may still carry variety sensitivity nobody has measured.",
            "Australian tagged Wiktionary entries are volunteer annotations, and many carry other variety tags beside the Australian one, so they are shared pronunciations rather than distinctively Australian ones.",
            "The union rule has almost nothing to union inside this pack, because requiring every documented form to agree tends to select words that have only one. The rule's real effect is visible in the eligible pool rather than in the twenty, and this limitation exists so the safeguard is not mistaken for work it did not do here.",
            "Opportunities are counted under a non-rhotic British reference. An American reference would create post-vocalic rhotic opportunities this pack deliberately does not carry, which is the mechanism checkpoint 22E8 recorded: the repair works by declining to ask rather than by fitting better.",
            "Only the written word mode is built. The recorded prompt alternative is a different task with different confounders and is not equivalent to it.",
            "Twenty words cannot establish that any consonant is produced typically or atypically by anybody. The pack creates opportunities; it measures nothing.",
        ],
        "release_boundaries": contract["release_boundaries"],
    }
    record = {
        "schema_version": "1.0.0",
        "record_id": "speech_sound_patterns_research_prompt_pack_private_record_v1",
        "pack_version": pack["pack_version"],
        "why_this_is_not_committed": (
            "Wiktionary derived material is share alike, and share alike "
            "attaches when adapted material is distributed rather than when it "
            "is used internally. The verbatim forms and the eligible pool are "
            "the derived lexicon and stay server side."
        ),
        "chosen_words": private,
        "eligible_pool": eligible,
    }
    return pack, record
