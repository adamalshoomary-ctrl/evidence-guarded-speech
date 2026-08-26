import unittest

from pipeline.voice_safety import unsupported_voice_inferences


class VoiceSafetyTests(unittest.TestCase):
    def test_rejects_mental_health_identity_and_personality_inferences(self):
        text = (
            "The flat voice sounds exhausted and nervous, showing cognitive "
            "load, low confidence, and possible vocal damage."
        )
        codes = set(unsupported_voice_inferences(text))
        self.assertTrue({
            "flat_voice_judgment", "fatigue", "nervousness",
            "cognitive_load", "confidence", "vocal_health",
        }.issubset(codes))

    def test_allows_directly_audible_noncausal_observations(self):
        text = (
            "A 1.2 second pause is followed by an audible sigh. The final "
            "word has a rising contour and the next phrase is quieter."
        )
        self.assertEqual(unsupported_voice_inferences(text), [])

    def test_scans_nested_structured_output(self):
        value = {"moments": [{"observation": "The voice sounds feminine."}]}
        self.assertEqual(
            unsupported_voice_inferences(value), ["gender_identity"]
        )


if __name__ == "__main__":
    unittest.main()
