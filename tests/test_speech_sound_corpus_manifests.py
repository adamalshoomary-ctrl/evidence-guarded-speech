import copy
import io
import json
import tarfile
import tempfile
import unittest
import unittest.mock
import zipfile
from pathlib import Path

from speech_sound_patterns import acquire_open_stack

from speech_sound_patterns.build_open_stack_manifests import (
    BUILDERS,
    ManifestBuildError,
    manifest_bytes,
)
from speech_sound_patterns.corpus_audit import (
    CorpusAuditError,
    _has_postvocalic_rhotic,
    audit_acted_clear,
    audit_common_phone_archive,
    audit_common_voice_group_overlap,
    audit_wikipron,
    build_common_voice_exclusions,
    assign_stratified_participants,
    assignment_summary,
    build_private_assignment,
    map_source_splits,
)
from speech_sound_patterns.corpus_manifest import (
    MANIFEST_ROOT,
    REPOSITORY_ROOT,
    CorpusManifestValidationError,
    load_registered_manifests,
    validate_manifest,
    validate_private_evidence,
    validate_registered_manifests,
    validate_registry,
)


# The openly licensed reference stack acquired at checkpoint 22E7.
OPEN_STACK = (
    "wikipron_eng_latn_uk_broad",
    "wikipron_eng_latn_us_broad",
    "wiktionary_australian_kaikki",
    "mfa_english_dictionary",
)


class SpeechSoundCorpusManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry, manifests = load_registered_manifests()
        cls.manifests = {item["source_id"]: item for item in manifests}

    def changed_manifest(self, source_id, update):
        result = copy.deepcopy(self.manifests[source_id])
        update(result)
        return result

    def changed_registry(self, update):
        result = copy.deepcopy(self.registry)
        update(result)
        return result

    def test_registered_manifests_are_valid(self):
        self.assertEqual(validate_registered_manifests(), [])

    def test_schema_rejects_unrecognised_manifest_fields(self):
        changed = self.changed_manifest(
            "speechocean762", lambda item: item.update({"unsafe_override": True})
        )
        errors = validate_manifest(changed)
        self.assertTrue(any("Additional properties" in error for error in errors))

    def test_available_source_requires_verified_terms_and_archive_hash(self):
        def update(item):
            item["access"]["terms_state"] = "pending"
            item["archives"][0]["local_sha256"] = None

        errors = validate_manifest(
            self.changed_manifest("common_voice_26_australian_english", update)
        )
        self.assertTrue(any("terms" in error.lower() for error in errors))
        self.assertTrue(any("local_sha256" in error for error in errors))

    def test_restricted_source_cannot_claim_local_data_or_an_archive(self):
        def update(item):
            item["governance"]["local_storage"] = ".research_data/forbidden"
            item["archives"] = copy.deepcopy(
                self.manifests["speechocean762"]["archives"]
            )

        errors = validate_manifest(self.changed_manifest("l2_arctic", update))
        self.assertTrue(any("cannot claim local storage" in error for error in errors))
        self.assertTrue(any("cannot declare archives" in error for error in errors))

    def test_source_truth_class_and_forbidden_roles_fail_closed(self):
        def update(item):
            item["annotation"]["truth_class"] = "expert_phone_relations"
            item["governance"]["prohibited_roles"].remove("phone_relation_truth")

        errors = validate_manifest(self.changed_manifest("common_phone_1_0", update))
        self.assertTrue(any("truth_class" in error for error in errors))
        self.assertTrue(any("source specific prohibited" in error for error in errors))

    def test_unknown_lineage_and_weakened_transfer_rules_fail_closed(self):
        def update(item):
            item["lineage"]["independence_claim"] = "probably_independent"
            item["governance"]["provider_transfer"] = "permitted_for_declared_role"
            item["governance"]["rehosting_permitted"] = True
            item["governance"]["reidentification_prohibited"] = False

        errors = validate_manifest(self.changed_manifest("speechocean762", update))
        self.assertTrue(any("independence_claim" in error for error in errors))
        self.assertTrue(any("provider transfer" in error for error in errors))
        self.assertTrue(any("rehosted" in error for error in errors))
        self.assertTrue(any("reidentification" in error for error in errors))

    def test_participant_overlap_or_unfrozen_evaluation_is_rejected(self):
        def update(item):
            item["participant_split"]["cross_split_overlap_count"] = 1
            item["participant_split"]["frozen_held_out"] = False

        errors = validate_manifest(self.changed_manifest("speechocean762", update))
        self.assertTrue(any("participant overlap" in error for error in errors))
        self.assertTrue(any("freeze held out" in error for error in errors))

    def test_manifest_split_totals_must_equal_aggregate_strata(self):
        def update(item):
            item["participant_split"]["participant_counts"]["development"] += 1

        errors = validate_manifest(self.changed_manifest("speechocean762", update))
        self.assertTrue(any("aggregate strata" in error for error in errors))

    def test_private_paths_cannot_escape_by_traversal(self):
        def update(item):
            item["governance"]["local_storage"] = ".research_data/../.env"
            item["participant_split"]["assignment_artifact"] = (
                ".research_data/../outside.json"
            )

        errors = validate_manifest(self.changed_manifest("speechocean762", update))
        self.assertTrue(any("escapes" in error for error in errors))

    def test_related_sources_cannot_be_declared_independent(self):
        changed = self.changed_manifest(
            "common_phone_1_0",
            lambda item: item["lineage"].update(
                {
                    "derived_from": [],
                    "lineage_group": "unrelated",
                    "independence_claim": "independent_accuracy_evidence",
                }
            ),
        )
        manifests = [
            changed if item["source_id"] == "common_phone_1_0" else item
            for item in self.manifests.values()
        ]
        errors = validate_registry(self.registry, manifests)
        self.assertGreaterEqual(sum("Common Phone" in error for error in errors), 2)

    def test_registry_cannot_pool_truth_classes_or_model_seen_data(self):
        changed = self.changed_registry(
            lambda item: item["cross_source_rules"].update(
                {
                    "truth_classes_may_be_pooled": True,
                    "model_seen_data_count_as_independent": True,
                }
            )
        )
        errors = validate_registry(changed, list(self.manifests.values()))
        self.assertTrue(any("truth_classes_may_be_pooled" in error for error in errors))
        self.assertTrue(
            any("model_seen_data_count_as_independent" in error for error in errors)
        )

    def test_deterministic_stratified_split_is_order_independent(self):
        participants = {
            f"speaker_{index:02d}": "adult_f" if index < 10 else "adult_m"
            for index in range(20)
        }
        reversed_participants = dict(reversed(list(participants.items())))
        first = assign_stratified_participants("example", participants)
        second = assign_stratified_participants("example", reversed_participants)
        self.assertEqual(first, second)
        document = build_private_assignment("example", first)
        summary = assignment_summary(document)
        self.assertEqual(summary["participant_counts"], {
            "development": 12,
            "threshold_tuning": 4,
            "held_out_evaluation": 4,
        })
        self.assertFalse(document["contains_exact_age"])

    def test_source_split_mapping_rejects_a_repeated_participant(self):
        with self.assertRaises(CorpusAuditError):
            map_source_splits(
                {"train": {"same"}, "dev": {"same"}, "test": {"other"}},
                {
                    "train": "development",
                    "dev": "threshold_tuning",
                    "test": "held_out_evaluation",
                },
            )

    def test_private_assignment_hash_and_summary_are_recomputed(self):
        manifest = self.changed_manifest("speechocean762", lambda item: None)
        manifest["access"]["state"] = "rejected"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = Path(".research_data/splits/example.json")
            path = root / relative
            path.parent.mkdir(parents=True)
            assignment = {
                "schema_version": "1.0.0",
                "source_id": "speechocean762",
                "seed": "test",
                "contains_exact_age": False,
                "assignments": {
                    "one": {
                        "project_split": "development",
                        "source_stratum": "adult",
                    },
                    "two": {
                        "project_split": "threshold_tuning",
                        "source_stratum": "adult",
                    },
                    "three": {
                        "project_split": "held_out_evaluation",
                        "source_stratum": "adult",
                    },
                },
            }
            path.write_text(json.dumps(assignment), encoding="utf-8")
            manifest["participant_split"]["assignment_artifact"] = str(relative)
            errors = validate_private_evidence([manifest], repository_root=root)
        self.assertTrue(any("SHA256" in error for error in errors))
        self.assertTrue(any("participant counts" in error for error in errors))
        self.assertTrue(any("split strata" in error for error in errors))

    def test_private_archive_bytes_can_be_rehashed(self):
        manifest = self.changed_manifest("acted_clear_speech", lambda item: None)
        manifest["archives"] = [
            {
                "filename": "sample.bin",
                "size_bytes": 4,
                "local_sha256": "0" * 64,
            }
        ]
        manifest["governance"]["local_storage"] = ".research_data/corpus"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / ".research_data/corpus/sample.bin"
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b"real")
            errors = validate_private_evidence(
                [manifest], repository_root=root, rehash_archives=True
            )
        self.assertTrue(any("SHA256 differs" in error for error in errors))

    def test_registry_loader_rejects_path_traversal_before_reading(self):
        registry = copy.deepcopy(self.registry)
        registry["manifests"] = [
            {"source_id": "speechocean762", "path": "../../.env"}
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaises(CorpusManifestValidationError):
                load_registered_manifests(path)

    def test_acted_clear_audit_rejects_malformed_phone_intervals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(root / "clear_speech_wavs.zip", "w") as archive:
                for index in range(125):
                    condition = (19, 20, 21, 22, 25)[index // 25]
                    archive.writestr(
                        f"MKH800_{condition}_{index % 25 + 1:04d}.wav", b"wave"
                    )
            with zipfile.ZipFile(
                root / "clear_speech_TextGrid.zip", "w"
            ) as archive:
                for index in range(125):
                    condition = (19, 20, 21, 22, 25)[index // 25]
                    archive.writestr(
                        f"MKH800_{condition}/MKH800_{condition}_{index % 25 + 1:04d}.TextGrid",
                        'File type = "ooTextFile"\nObject class = "TextGrid"\n',
                    )
            with self.assertRaises(CorpusAuditError):
                audit_acted_clear(root)

    def test_every_ruled_out_source_records_a_verdict_and_a_reason(self):
        # Checkpoint 22E6. These were found by the open evidence search and are
        # written down so a later agent reads a closed decision rather than an
        # unexplored lead.
        for source_id in (
            "andosl",
            "austalk",
            "isle_elra_s0083",
            "mitchell_delbridge",
            "speech_accent_archive",
            "coanzse",
        ):
            with self.subTest(source=source_id):
                manifest = self.manifests[source_id]
                self.assertIn(
                    manifest["access"]["state"], {"rejected", "unavailable"}
                )
                self.assertNotEqual(
                    manifest["licence"]["commercial_use_permitted"], True
                )
                self.assertEqual(manifest["governance"]["permitted_roles"], ["manifest_only"])
                self.assertTrue(manifest["capability_audit"]["findings"])
                self.assertTrue(manifest["population"]["limitations"])

    def test_the_open_stack_is_acquired_licensed_and_proved(self):
        for source_id in OPEN_STACK:
            with self.subTest(source=source_id):
                manifest = self.manifests[source_id]
                self.assertEqual(manifest["access"]["state"], "available")
                self.assertTrue(manifest["licence"]["commercial_use_permitted"])
                self.assertTrue(manifest["licence"]["attribution_required"])
                self.assertTrue(manifest["licence"]["attribution_text"])
                self.assertTrue(manifest["archives"])
                for archive in manifest["archives"]:
                    self.assertEqual(archive["local_verification_status"], "verified")
                    self.assertRegex(archive["local_sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue(
                    manifest["governance"]["local_storage"].startswith(".research_data/")
                )
                self.assertFalse(manifest["governance"]["rehosting_permitted"])
                # Acquiring a lexicon does not give it a truth class. A word list
                # proposes how a word may be said and never observes a speaker,
                # so the value stays unavailable and only its reason changed.
                self.assertEqual(manifest["annotation"]["truth_class"], "unavailable")

    def test_an_acquired_source_cannot_drop_its_archive_proof(self):
        errors = validate_manifest(
            self.changed_manifest(
                "mfa_english_dictionary", lambda item: item.update({"archives": []})
            )
        )
        self.assertTrue(any("verified archives" in error for error in errors))

    def test_a_lexicon_cannot_claim_a_participant_split(self):
        def update(item):
            item["participant_split"]["status"] = "audited"
            item["participant_split"]["unit"] = "participant"

        errors = validate_manifest(
            self.changed_manifest("wikipron_eng_latn_uk_broad", update)
        )
        self.assertTrue(any("no participants to split" in error for error in errors))

    def test_a_speech_source_still_cannot_skip_its_participant_split(self):
        def update(item):
            item["participant_split"]["status"] = "not_applicable"

        errors = validate_manifest(
            self.changed_manifest("common_voice_26_australian_english", update)
        )
        self.assertTrue(any("cannot skip split handling" in error for error in errors))

    def test_the_british_supplement_cannot_be_promoted_to_the_reference(self):
        # Measured at acquisition: the WikiPron British scrape is far more
        # rhotic than the aligner dictionary and carries a much larger symbol
        # inventory. Dropping that boundary must fail rather than pass quietly.
        def update(item):
            item["governance"]["prohibited_roles"] = [
                role
                for role in item["governance"]["prohibited_roles"]
                if role != "primary_british_reference_without_an_inventory_repair"
            ]

        errors = validate_manifest(
            self.changed_manifest("wikipron_eng_latn_uk_broad", update)
        )
        self.assertTrue(
            any("source specific prohibited roles" in error for error in errors)
        )

    def test_the_open_stack_records_measured_counts_rather_than_published_ones(self):
        findings = " ".join(
            self.manifests["mfa_english_dictionary"]["capability_audit"]["findings"]
        )
        self.assertIn("46,163", findings)
        self.assertIn("spn", findings)
        australian = " ".join(
            self.manifests["wiktionary_australian_kaikki"]["capability_audit"]["findings"]
        )
        self.assertIn("2,700", australian)

    def test_the_american_comparison_needs_both_gender_subsets(self):
        # Dropping either half restores the exact confound this checkpoint was
        # told not to proceed past quietly.
        manifests = [
            item
            for item in self.manifests.values()
            if item["source_id"] != "common_voice_26_american_english_female"
        ]
        errors = validate_registry(self.registry, manifests)
        self.assertTrue(any("gender subsets" in error for error in errors))

    def test_a_comparison_group_cannot_claim_independence_from_common_voice(self):
        changed = self.changed_manifest(
            "common_voice_26_british_english",
            lambda item: item["lineage"].update(
                {
                    "lineage_group": "unrelated",
                    "independence_claim": "candidate_model_overlap_must_be_audited",
                }
            ),
        )
        manifests = [
            changed if item["source_id"] == "common_voice_26_british_english" else item
            for item in self.manifests.values()
        ]
        errors = validate_registry(self.registry, manifests)
        self.assertTrue(any("lineage group" in error for error in errors))
        self.assertTrue(any("cannot claim independence" in error for error in errors))

    def test_a_comparison_group_cannot_qualify_a_model_trained_on_its_own_lineage(self):
        def update(item):
            item["governance"]["prohibited_roles"] = [
                role
                for role in item["governance"]["prohibited_roles"]
                if role != "selection_evidence_for_a_common_voice_trained_model"
            ]

        for source_id in (
            "common_voice_26_british_english",
            "common_voice_26_american_english_male",
            "common_voice_26_american_english_female",
        ):
            with self.subTest(source=source_id):
                errors = validate_manifest(self.changed_manifest(source_id, update))
                self.assertTrue(
                    any("source specific prohibited" in error for error in errors)
                )

    def test_every_comparison_group_seals_its_held_out_speakers(self):
        for source_id in (
            "common_voice_26_australian_english",
            "common_voice_26_british_english",
            "common_voice_26_american_english_male",
            "common_voice_26_american_english_female",
        ):
            with self.subTest(source=source_id):
                split = self.manifests[source_id]["participant_split"]
                self.assertEqual(split["status"], "audited")
                self.assertTrue(split["frozen_held_out"])
                self.assertEqual(split["cross_split_overlap_count"], 0)
                self.assertGreater(split["participant_counts"]["held_out_evaluation"], 0)

    def test_no_newly_recorded_source_may_ever_be_sent_to_a_provider(self):
        for source_id in (
            "andosl",
            "austalk",
            "isle_elra_s0083",
            "mitchell_delbridge",
            "speech_accent_archive",
            "coanzse",
            *OPEN_STACK,
        ):
            with self.subTest(source=source_id):
                self.assertEqual(
                    self.manifests[source_id]["governance"]["provider_transfer"],
                    "blocked",
                )

    def test_common_phone_archive_audit_ignores_resource_forks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = {
                "train": "train_clip.mp3,train_id,Train text\n",
                "dev": "dev_clip.mp3,dev_id,Dev text\n",
                "test": "test_clip.mp3,test_id,Test text\n",
            }
            for split, row in rows.items():
                (root / f"{split}.csv").write_text(
                    "audio file,id,text\n" + row, encoding="utf-8"
                )
            archive_path = root / "sample.tgz"
            with tarfile.open(archive_path, "w:gz") as archive:
                for stem in ("train_clip", "dev_clip", "test_clip"):
                    for folder, suffix, payload in (
                        ("mp3", ".mp3", b"mp3"),
                        ("wav", ".wav", b"wav"),
                        (
                            "grids",
                            ".TextGrid",
                            b'Object class = "TextGrid"\nname = "phones"\n',
                        ),
                    ):
                        for prefix in ("", "._"):
                            info = tarfile.TarInfo(
                                f"CP/en/{folder}/{prefix}{stem}{suffix}"
                            )
                            info.size = len(payload)
                            archive.addfile(info, io.BytesIO(payload))
            result = audit_common_phone_archive(
                archive_path, root, sample_grids=3
            )
        self.assertEqual(result["english_clips"], 3)
        self.assertTrue(result["paired_mp3_wav_and_textgrid"])


class OpenStackAuditTests(unittest.TestCase):
    """Checkpoint 22E7 measurement helpers, tested without any private data."""

    def test_a_postvocalic_rhotic_is_separated_from_an_onset_one(self):
        # This distinction is the whole measurement. Counting every rhotic would
        # call British English rhotic, because non-rhotic varieties still say
        # the r in red.
        non_rhotic = [
            ("ɹ", "ɛ", "d"),
            ("k", "ɑː"),
            ("w", "ɔː", "t", "ə"),
            ("v", "ɛ", "ɹ", "i"),
        ]
        rhotic = [
            ("k", "ɑ", "ɹ"),
            ("b", "ɝ", "d"),
            ("w", "ɔ", "t", "ɚ"),
            ("f", "ɑ", "ɹ", "m"),
        ]
        for phones in non_rhotic:
            with self.subTest(phones=phones):
                self.assertFalse(_has_postvocalic_rhotic(phones))
        for phones in rhotic:
            with self.subTest(phones=phones):
                self.assertTrue(_has_postvocalic_rhotic(phones))

    def test_a_malformed_lexicon_line_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.tsv"
            path.write_text("word\tw ɜː d\nlonely\n", encoding="utf-8")
            with self.assertRaises(CorpusAuditError):
                audit_wikipron(path)

    def test_a_lexicon_report_counts_entries_words_and_phones(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "small.tsv"
            path.write_text(
                "car\tk ɑː\ncar\tk ɑ ɹ\nred\tɹ ɛ d\n", encoding="utf-8"
            )
            report = audit_wikipron(path)
        self.assertEqual(report["entries"], 3)
        self.assertEqual(report["distinct_words"], 2)
        self.assertEqual(report["words_with_more_than_one_pronunciation"], 1)
        self.assertEqual(report["entries_with_a_postvocalic_rhotic"], 1)

    def test_two_comparison_groups_sharing_a_speaker_are_reported(self):
        # A contributor landing in both the group under test and its control
        # would flatten the very difference checkpoint 22E8 exists to measure.
        with tempfile.TemporaryDirectory() as directory:
            roots = {}
            for name, client in (("group_a", "speaker_a"), ("group_b", "speaker_b")):
                root = Path(directory) / name
                root.mkdir()
                for split in ("train", "dev", "test"):
                    (root / f"{split}.tsv").write_text(
                        "client_id\tpath\tsentence_id\tsentence\t"
                        "up_votes\tdown_votes\taccents\tlocale\n"
                        f"{client}_{split}\tclip_{name}_{split}.mp3\ts1\tText\t"
                        "2\t0\tAccent\ten\n",
                        encoding="utf-8",
                    )
                roots[name] = root
            clean = audit_common_voice_group_overlap(roots)
            self.assertFalse(clean["any_overlap"])
            (roots["group_b"] / "train.tsv").write_text(
                "client_id\tpath\tsentence_id\tsentence\t"
                "up_votes\tdown_votes\taccents\tlocale\n"
                "speaker_a_train\tclip_group_a_train.mp3\ts1\tText\t2\t0\tAccent\ten\n",
                encoding="utf-8",
            )
            overlapping = audit_common_voice_group_overlap(roots)
        self.assertTrue(overlapping["any_overlap"])
        pair = overlapping["pairwise_overlap"]["group_a|group_b"]
        self.assertEqual(pair["shared_participants"], 1)
        self.assertEqual(pair["shared_clips"], 1)


class CommonVoiceExclusionTests(unittest.TestCase):
    """A contributor who declares two varieties belongs to neither group."""

    def _write_subset(self, root, rows):
        root.mkdir(parents=True, exist_ok=True)
        header = (
            "client_id\tpath\tsentence_id\tsentence\t"
            "up_votes\tdown_votes\taccents\tlocale\n"
        )
        for split in ("train", "dev", "test"):
            body = "".join(
                f"{client}\t{client}_{split}_{index}.mp3\ts1\tText\t2\t0\t{accent}\ten\n"
                for index, (client, accent) in enumerate(rows.get(split, []))
            )
            (root / f"{split}.tsv").write_text(header + body, encoding="utf-8")

    def test_a_contributor_in_two_groups_is_excluded_from_both(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            british = root / "gb"
            american = root / "us"
            self._write_subset(
                british,
                {
                    "train": [("both_ways", "England English"), ("only_gb", "England English")],
                    "dev": [("gb_dev", "England English")],
                    "test": [("gb_test", "England English")],
                },
            )
            self._write_subset(
                american,
                {
                    "train": [("both_ways", "United States English")],
                    "dev": [("us_dev", "United States English")],
                    "test": [("us_test", "United States English")],
                },
            )
            summary = build_common_voice_exclusions(
                {"british": british, "american": american},
                REPOSITORY_ROOT
                / ".research_data"
                / "speech_sound_patterns"
                / "test-exclusions.json",
            )
            record = json.loads(
                (
                    REPOSITORY_ROOT
                    / ".research_data"
                    / "speech_sound_patterns"
                    / "test-exclusions.json"
                ).read_text()
            )
        self.assertEqual(summary["excluded_participants"], 1)
        self.assertEqual(summary["affected_subsets"], ["american", "british"])
        excluded = record["excluded_participants"]["both_ways"]
        self.assertEqual(excluded["subsets"], ["american", "british"])
        self.assertEqual(
            excluded["detail"]["british"]["declared_accents"], ["England English"]
        )
        self.assertEqual(excluded["detail"]["american"]["project_splits"], ["development"])

    def test_an_exclusion_record_cannot_escape_the_private_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "subset"
            self._write_subset(root, {"train": [("only", "Accent")]})
            with self.assertRaises(CorpusAuditError):
                build_common_voice_exclusions(
                    {"subset": root}, Path(directory) / "outside.json"
                )


class _FakeResponse:
    """A canned HTTP body, so download recovery can be tested without a network."""

    def __init__(self, payload, status=200, declared=None):
        self._payload = payload
        self._offset = 0
        self.status = status
        self.headers = {
            "Content-Length": str(declared if declared is not None else len(payload))
        }

    def read(self, size):
        block = self._payload[self._offset : self._offset + size]
        self._offset += len(block)
        return block

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return False


class OpenStackDownloadRecoveryTests(unittest.TestCase):
    """A truncated corpus must never survive, and a big one must not restart."""

    def setUp(self):
        self.requests = []

    def _patched(self, responses):
        def fake_open(url, headers=None, method="GET", timeout=None):
            self.requests.append((url, dict(headers or {})))
            return responses.pop(0)

        return unittest.mock.patch.object(acquire_open_stack, "_open", fake_open)

    def test_a_dropped_connection_resumes_instead_of_restarting(self):
        body = bytes(range(256)) * 40
        responses = [
            # The first connection claims the whole body and delivers half.
            _FakeResponse(body[: len(body) // 2], declared=len(body)),
            _FakeResponse(body[len(body) // 2 :], status=206),
        ]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "corpus.tar.gz"
            with self._patched(responses):
                size = acquire_open_stack._stream_to_file(
                    lambda: "https://example.invalid/corpus", destination
                )
            self.assertEqual(size, len(body))
            self.assertEqual(destination.read_bytes(), body)
        self.assertNotIn("Range", self.requests[0][1])
        self.assertEqual(self.requests[1][1]["Range"], f"bytes={len(body) // 2}-")

    def test_a_server_ignoring_the_range_restarts_rather_than_concatenating(self):
        body = b"complete-archive-bytes"
        responses = [
            _FakeResponse(b"partial", declared=len(body)),
            # Status 200 on a resume means the whole body is coming again.
            _FakeResponse(body, status=200, declared=len(body)),
        ]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "corpus.tar.gz"
            with self._patched(responses):
                acquire_open_stack._stream_to_file(
                    lambda: "https://example.invalid/corpus", destination
                )
            self.assertEqual(destination.read_bytes(), body)

    def test_a_download_that_never_completes_is_discarded(self):
        responses = [_FakeResponse(b"short", declared=100) for _ in range(3)]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "corpus.tar.gz"
            with self._patched(responses):
                with self.assertRaises(acquire_open_stack.AcquisitionError) as caught:
                    acquire_open_stack._stream_to_file(
                        lambda: "https://example.invalid/corpus",
                        destination,
                        attempts=3,
                    )
            self.assertIn("truncated", str(caught.exception))
            self.assertFalse(destination.is_file())

    def test_the_credential_never_reaches_a_message(self):
        message = "failed for key sk-secret-value"
        self.assertNotIn(
            "sk-secret-value", acquire_open_stack._redact(message, "sk-secret-value")
        )


class OpenStackManifestRebuildTests(unittest.TestCase):
    """The committed manifests must still describe the bytes they were built from."""

    def test_committed_manifests_rebuild_from_the_acquired_evidence(self):
        # Each source is rebuilt on its own. One absent source must not quietly
        # disable the check for every other source on the machine.
        checked = 0
        for source_id, (builder, filename) in BUILDERS.items():
            with self.subTest(source=source_id):
                try:
                    document = builder()
                except ManifestBuildError:
                    continue
                checked += 1
                committed = (MANIFEST_ROOT / filename).read_bytes()
                self.assertEqual(committed, manifest_bytes(document))
        if not checked:
            self.skipTest("no private acquired evidence is present on this machine")


if __name__ == "__main__":
    unittest.main()
