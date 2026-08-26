import copy
import json
import tempfile
import unittest
from pathlib import Path

from motor_speech_voice.governance import (
    ACTIVE_PYTHON_ROOTS,
    CONTRACT_PATH,
    CURRENT_CONTRACT_CANONICAL_SHA256,
    EXPECTED_LANE_STATUSES,
    EXPECTED_QUESTION_IDS,
    EXPECTED_ROLE_IDS,
    RELEASE_FIELDS,
    GovernanceValidationError,
    active_pipeline_leakage,
    canonical_contract_sha256,
    load_governance_contract,
    validate_governance_contract,
)


class MotorSpeechVoiceGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_governance_contract()

    def changed(self, update):
        document = copy.deepcopy(self.contract)
        update(document)
        return document

    def assert_invalid(self, document):
        self.assertTrue(validate_governance_contract(document))

    def test_active_contract_is_valid_and_absent_from_pipeline(self):
        self.assertEqual(validate_governance_contract(self.contract), [])
        self.assertEqual(
            canonical_contract_sha256(self.contract),
            CURRENT_CONTRACT_CANONICAL_SHA256,
        )
        self.assertEqual(active_pipeline_leakage(), [])

    def test_leakage_check_covers_every_active_python_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for root_name in ACTIVE_PYTHON_ROOTS:
                (root / root_name).mkdir()
            (root / "pipeline" / "safe.py").write_text(
                "VALUE = 'unrelated'\n", encoding="utf-8"
            )
            self.assertEqual(active_pipeline_leakage(root), [])

            leaked = root / "pipeline" / "leaked.py"
            leaked.write_text(
                "import motor_speech_voice\n", encoding="utf-8"
            )
            self.assertEqual(
                active_pipeline_leakage(root), ["pipeline/leaked.py"]
            )

            leaked.unlink()
            (root / "pipeline" / "safe.py").unlink()
            (root / "pipeline").rmdir()
            self.assertIn("pipeline/", active_pipeline_leakage(root))

    def test_contract_loader_rejects_missing_malformed_and_symlink_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(GovernanceValidationError):
                load_governance_contract(root / "missing.json")
            malformed = root / "malformed.json"
            malformed.write_text("{", encoding="utf-8")
            with self.assertRaises(GovernanceValidationError):
                load_governance_contract(malformed)
            link = root / "contract.json"
            link.symlink_to(CONTRACT_PATH)
            with self.assertRaises(GovernanceValidationError):
                load_governance_contract(link)

    def test_owner_approved_adults_first_without_a_product_age_gate(self):
        owner = self.contract["owner_scope"]
        self.assertTrue(owner["checkpoint_23b_approved"])
        self.assertEqual(owner["research_age_scope"], "adults_first")
        self.assertEqual(owner["minimum_participant_age_years"], 18)
        self.assertFalse(owner["adult_scope_creates_product_age_gate"])
        self.assertFalse(owner["owner_signed_intended_use"])
        self.assertEqual(
            owner["legal_sponsor_status"], "unresolved_owner_input_required"
        )
        for field, value in (
            ("research_age_scope", "adults_and_children"),
            ("minimum_participant_age_years", 16),
            ("adult_scope_creates_product_age_gate", True),
            ("owner_signed_intended_use", True),
            ("legal_sponsor_status", "approved"),
        ):
            with self.subTest(field=field):
                self.assert_invalid(
                    self.changed(
                        lambda document, field=field, value=value: document[
                            "owner_scope"
                        ].update({field: value})
                    )
                )

    def test_every_lane_has_an_independent_unselected_state(self):
        lanes = self.contract["lane_decisions"]
        self.assertEqual(set(lanes), set(EXPECTED_LANE_STATUSES))
        for lane_id, expected_status in EXPECTED_LANE_STATUSES.items():
            with self.subTest(lane=lane_id):
                lane = lanes[lane_id]
                self.assertEqual(lane["status"], expected_status)
                for field in (
                    "selected_construct",
                    "selected_task",
                    "selected_measure",
                    "selected_score",
                    "selected_threshold",
                ):
                    self.assertIsNone(lane[field])
                    self.assert_invalid(
                        self.changed(
                            lambda document, lane_id=lane_id, field=field: document[
                                "lane_decisions"
                            ][lane_id].update({field: "invented"})
                        )
                    )

    def test_global_selection_cannot_hide_a_lane_decision(self):
        rules = self.contract["decision_rules"]
        self.assertTrue(rules["lane_decisions_are_independent"])
        self.assertFalse(rules["global_selection_may_hide_lane_no_selection"])
        self.assertTrue(rules["unresolved_required_authority_forces_no_selection"])
        self.assertTrue(rules["selection_requires_all_applicable_signed_reviews"])
        self.assertFalse(rules["checkpoint_complete"])
        self.assertIsNone(rules["current_decision"])
        for field, value in (
            ("lane_decisions_are_independent", False),
            ("global_selection_may_hide_lane_no_selection", True),
            ("unresolved_required_authority_forces_no_selection", False),
            ("selection_requires_all_applicable_signed_reviews", False),
            ("checkpoint_complete", True),
            ("current_decision", "selection"),
        ):
            with self.subTest(field=field):
                self.assert_invalid(
                    self.changed(
                        lambda document, field=field, value=value: document[
                            "decision_rules"
                        ].update({field: value})
                    )
                )

    def test_candidate_questions_are_unordered_and_unselected(self):
        questions = self.contract["candidate_questions"]
        self.assertEqual(
            {question["question_id"] for question in questions},
            EXPECTED_QUESTION_IDS,
        )
        for index, question in enumerate(questions):
            with self.subTest(question=question["question_id"]):
                self.assertFalse(question["selected"])
                self.assertEqual(question["priority"], "unordered")
                for field, value in (
                    ("selected", True),
                    ("priority", "first"),
                    ("state", "selected"),
                    ("lane", "invented_lane"),
                ):
                    self.assert_invalid(
                        self.changed(
                            lambda document, index=index, field=field, value=value: document[
                                "candidate_questions"
                            ][index].update({field: value})
                        )
                    )

    def test_only_owner_scope_is_filled_and_owner_cannot_fill_other_roles(self):
        roles = self.contract["role_requirements"]
        self.assertEqual({role["role_id"] for role in roles}, EXPECTED_ROLE_IDS)
        for index, role in enumerate(roles):
            with self.subTest(role=role["role_id"]):
                if role["role_id"] == "product_owner":
                    self.assertEqual(role["status"], "filled_for_scope_only")
                    continue
                self.assertIn(role["status"], {"unfilled", "conditional_unfilled"})
                self.assert_invalid(
                    self.changed(
                        lambda document, index=index: document["role_requirements"][
                            index
                        ].update({"status": "filled"})
                    )
                )
                for field, value in (
                    ("must_be_independent_of", []),
                    ("decision_right", "looks_explicit_but_is_wrong"),
                    ("evidence_required", "looks_explicit_but_is_wrong"),
                ):
                    self.assert_invalid(
                        self.changed(
                            lambda document, index=index, field=field, value=value: document[
                                "role_requirements"
                            ][index].update({field: value})
                        )
                    )

    def test_contact_accounts_spending_and_vendor_selection_stay_closed(self):
        for field, value in self.contract["contact_and_spending"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
                self.assert_invalid(
                    self.changed(
                        lambda document, field=field: document[
                            "contact_and_spending"
                        ].update({field: True})
                    )
                )

    def test_no_recording_private_data_transfer_or_pipeline_use_is_allowed(self):
        data = self.contract["research_data"]
        for field, value in data.items():
            with self.subTest(field=field):
                if field in {"research_storage_location", "approved_data_dictionary"}:
                    self.assertIsNone(value)
                    replacement = "invented"
                else:
                    self.assertFalse(value)
                    replacement = True
                self.assert_invalid(
                    self.changed(
                        lambda document, field=field, replacement=replacement: document[
                            "research_data"
                        ].update({field: replacement})
                    )
                )

    def test_no_task_prompt_protocol_or_reference_instrument_is_selected(self):
        task = self.contract["task_and_reference"]
        for field, value in task.items():
            if field.endswith("_selected"):
                with self.subTest(field=field):
                    self.assertFalse(value)
                    self.assert_invalid(
                        self.changed(
                            lambda document, field=field: document[
                                "task_and_reference"
                            ].update({field: True})
                        )
                    )

    def test_sample_sizes_and_endpoints_remain_uninvented_and_held_out_closed(self):
        splits = self.contract["sampling_and_splits"]
        for field in (
            "numeric_participant_sample_size",
            "numeric_listener_sample_size",
            "numeric_rater_sample_size",
            "primary_endpoint",
        ):
            with self.subTest(field=field):
                self.assertIsNone(splits[field])
                self.assert_invalid(
                    self.changed(
                        lambda document, field=field: document[
                            "sampling_and_splits"
                        ].update({field: 100})
                    )
                )
        self.assertTrue(splits["participant_exclusive"])
        self.assertFalse(splits["held_out_accessed"])
        self.assert_invalid(
            self.changed(
                lambda document: document["sampling_and_splits"].update(
                    {"held_out_accessed": True}
                )
            )
        )

    def test_privacy_entity_retention_and_legal_maps_remain_unresolved(self):
        privacy = self.contract["privacy_and_consent"]
        self.assertIsNone(privacy["responsible_entity_and_data_role_matrix"])
        self.assertIsNone(privacy["retention_schedule"])
        self.assertFalse(privacy["consent_may_be_inferred"])
        self.assertFalse(privacy["declining_optional_use_affects_product_access"])
        self.assertTrue(privacy["core_audio_is_required_for_audio_study_participation"])
        self.assertIn("research_participation", privacy["required_core_consents"])
        self.assertIn("audio_recording", privacy["required_core_consents"])
        for field, value in (
            ("responsible_entity_and_data_role_matrix", "invented_company"),
            ("retention_schedule", "forever"),
            ("core_audio_is_required_for_audio_study_participation", False),
            ("consent_may_be_inferred", True),
            ("declining_optional_use_affects_product_access", True),
        ):
            with self.subTest(field=field):
                self.assert_invalid(
                    self.changed(
                        lambda document, field=field, value=value: document[
                            "privacy_and_consent"
                        ].update({field: value})
                    )
                )

    def test_regulatory_classification_trial_and_supply_are_not_invented(self):
        regulatory = self.contract["regulatory"]
        self.assertFalse(regulatory["exact_intended_purpose_frozen"])
        self.assertIsNone(regulatory["manufacturer"])
        self.assertIsNone(regulatory["australian_sponsor"])
        self.assertFalse(regulatory["candidate_software_use_authorised"])
        self.assertFalse(regulatory["public_supply_authorised"])
        for field, value in (
            ("exact_intended_purpose_frozen", True),
            ("manufacturer", "invented"),
            ("australian_sponsor", "invented"),
            ("candidate_software_use_authorised", True),
            ("public_supply_authorised", True),
        ):
            with self.subTest(field=field):
                self.assert_invalid(
                    self.changed(
                        lambda document, field=field, value=value: document[
                            "regulatory"
                        ].update({field: value})
                    )
                )

    def test_every_release_and_downstream_boundary_stays_closed(self):
        releases = self.contract["release_boundaries"]
        self.assertEqual(set(releases), RELEASE_FIELDS)
        for field in releases:
            with self.subTest(release=field):
                self.assertFalse(releases[field])
                self.assert_invalid(
                    self.changed(
                        lambda document, field=field: document[
                            "release_boundaries"
                        ].update({field: True})
                    )
                )
        for field, value in self.contract["downstream"].items():
            if field == "next_action":
                continue
            with self.subTest(downstream=field):
                self.assertFalse(value)
                self.assert_invalid(
                    self.changed(
                        lambda document, field=field: document["downstream"].update(
                            {field: True}
                        )
                    )
                )

    def test_root_and_nested_type_mutations_fail_without_crashing(self):
        for field in self.contract:
            for value in (None, [], {}, "wrong", 0, True):
                with self.subTest(field=field, value=repr(value)):
                    document = copy.deepcopy(self.contract)
                    document[field] = value
                    self.assert_invalid(document)

    def test_serialised_contract_round_trips_without_hidden_values(self):
        original = CONTRACT_PATH.read_text(encoding="utf-8")
        rebuilt = json.dumps(json.loads(original), indent=2) + "\n"
        self.assertEqual(rebuilt, original)

    def test_every_current_leaf_is_bound_to_the_reviewed_snapshot(self):
        paths = []

        def visit(value, path=()):
            if isinstance(value, dict):
                for key, child in value.items():
                    visit(child, path + (key,))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, path + (index,))
            else:
                paths.append(path)

        def replace(document, path, replacement):
            parent = document
            for part in path[:-1]:
                parent = parent[part]
            parent[path[-1]] = replacement

        visit(self.contract)
        self.assertGreater(len(paths), 150)
        for path in paths:
            original = self.contract
            for part in path:
                original = original[part]
            if isinstance(original, bool):
                replacement = not original
            elif original is None:
                replacement = "invented"
            elif isinstance(original, int):
                replacement = original + 1
            else:
                replacement = f"{original}__changed"
            with self.subTest(path=path):
                self.assert_invalid(
                    self.changed(
                        lambda document, path=path, replacement=replacement: replace(
                            document, path, replacement
                        )
                    )
                )

    def test_known_contradictory_meanings_and_malformed_ids_fail_closed(self):
        mutations = (
            ("children population", lambda d: d["intended_use"].update({"population": "children"})),
            ("existing audio", lambda d: d["intended_use"].update({"input": "existing_owner_audio"})),
            ("overseas approval", lambda d: d["privacy_and_consent"].update({"overseas_processing": "approved"})),
            ("model training", lambda d: d["privacy_and_consent"].update({"secondary_model_training": "approved"})),
            ("recording law complete", lambda d: d["privacy_and_consent"].update({"recording_and_listening_laws_map": "complete"})),
            ("trial pathway approved", lambda d: d["regulatory"].update({"ctn_or_cta_status": "approved"})),
            ("allocation implemented", lambda d: d["sampling_and_splits"].update({"allocation_method_status": "implemented"})),
            ("begin recruitment", lambda d: d["downstream"].update({"next_action": "begin_participant_recruitment"})),
            ("question id list", lambda d: d["candidate_questions"][0].update({"question_id": []})),
            ("role id list", lambda d: d["role_requirements"][0].update({"role_id": []})),
            ("core consent list element", lambda d: d["privacy_and_consent"]["required_core_consents"].__setitem__(0, [])),
            ("source id list", lambda d: d["sources"][0].update({"source_id": []})),
            ("source url changed", lambda d: d["sources"][0].update({"url": "https://example.invalid"})),
        )
        for label, mutation in mutations:
            with self.subTest(label=label):
                self.assert_invalid(self.changed(mutation))


if __name__ == "__main__":
    unittest.main()
