"""The snapshot contract decides what leaves this machine, so it is tested.

These checks are structural rather than behavioural. They do not build a
snapshot. They assert that the contract still describes a publication whose
internal working documents stay behind and whose public replacement exists,
which is the arrangement item P1 put in place on 2026-08-27 after the first
release published a status page saying the thing it contained was unpublished.

The overlay source hashes are deliberately not checked here. The builder checks
them and refuses, which is the moment that matters. Checking them again in the
test suite would turn every ordinary edit to a private status document into a
failing test run, and a guard people learn to ignore is worse than no guard.
"""

import json
import unittest
from pathlib import Path

from release.verify_snapshot import _flatten


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = REPO_ROOT / "release" / "snapshot-contract-v1.0.0.json"

INTERNAL_DOCUMENTS = ("AGENTS.md", "current-state.md", "improvement-plan.md")


@unittest.skipUnless(
    CONTRACT.is_file(),
    "the snapshot contract is not published: it names, as literal strings, "
    "exactly the private material it removes, so it stays in the working "
    "repository. These checks run there.",
)
class SnapshotContractTests(unittest.TestCase):

    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_internal_working_documents_are_excluded(self):
        excluded = set(self.contract["source_selection"]["excluded_paths"])
        for name in INTERNAL_DOCUMENTS:
            with self.subTest(document=name):
                self.assertIn(name, excluded)

    def test_every_exclusion_carries_a_written_reason(self):
        selection = self.contract["source_selection"]
        for name in selection["excluded_paths"]:
            with self.subTest(document=name):
                self.assertIn(name, selection["why_excluded"])
                self.assertTrue(selection["why_excluded"][name].strip())

    def test_overlays_declare_a_publish_path_and_their_sources(self):
        for overlay in self.contract["overlays"]:
            with self.subTest(overlay=overlay.get("overlay")):
                self.assertTrue(overlay["publish_as"])
                self.assertTrue((REPO_ROOT / overlay["overlay"]).is_file())
                self.assertTrue(overlay["sources"])
                for source in overlay["sources"]:
                    self.assertTrue((REPO_ROOT / source["path"]).is_file())
                    self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")

    def test_an_overlay_is_not_published_twice(self):
        """The overlay's own build path must not also travel as a file."""
        excluded = set(self.contract["source_selection"]["excluded_paths"])
        for overlay in self.contract["overlays"]:
            with self.subTest(overlay=overlay["overlay"]):
                self.assertIn(overlay["overlay"], excluded)

    def test_the_public_status_page_replaces_the_private_ones(self):
        overlays = {o["publish_as"]: o for o in self.contract["overlays"]}
        self.assertIn("PROJECT-STATUS.md", overlays)
        sources = {s["path"] for s in overlays["PROJECT-STATUS.md"]["sources"]}
        self.assertEqual(sources, {"current-state.md", "improvement-plan.md"})

    def test_every_substitution_restricted_to_a_file_names_a_real_one(self):
        for rule in self.contract["substitutions"]:
            for name in rule.get("files") or []:
                with self.subTest(rule=rule["id"], file=name):
                    self.assertTrue((REPO_ROOT / name).is_file())


class PrivateStringMatchingTests(unittest.TestCase):
    """A line wrap must not hide a private string from the verifier.

    A place name inside a quoted command was wrapped across two lines by an
    ordinary text reflow. Both the substitution engine and the privacy check
    compare literal substrings, so neither saw it, and it sat in the public
    repository through six releases while the verifier reported private content
    clean. Found 2026-08-28.

    The real string is not used here. It is on the deny list the verifier
    reads, and a test that hardcodes the private value publishes it in the
    test file, which is the same defect wearing a different hat. A stand in
    with the same shape, two words either side of a space, exercises the same
    code path.
    """

    SECRET = "hobart glenorchy"

    def test_a_contiguous_private_string_is_still_found(self):
        haystack = f"the file audio/{self.SECRET}.m4a was used"
        self.assertIn(self.SECRET, _flatten(haystack))

    def test_a_private_string_split_by_a_newline_is_found(self):
        first, second = self.SECRET.split(" ")
        haystack = f"the file audio/{first}\n  {second}.m4a was used"
        self.assertNotIn(self.SECRET, haystack)
        self.assertIn(self.SECRET, _flatten(haystack))

    def test_a_private_string_split_by_any_whitespace_run_is_found(self):
        first, second = self.SECRET.split(" ")
        for gap in ("\n", "\n  ", "\t", "  \n\t "):
            with self.subTest(gap=repr(gap)):
                self.assertIn(self.SECRET, _flatten(f"audio/{first}{gap}{second}"))

    def test_flattening_does_not_join_words_that_were_never_adjacent(self):
        first, second = self.SECRET.split(" ")
        haystack = f"{first} is one word and {second} sits on another line"
        self.assertNotIn(self.SECRET, _flatten(haystack))


if __name__ == "__main__":
    unittest.main()
