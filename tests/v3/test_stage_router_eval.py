"""Evaluation fixtures for the first real 214-record routing pass."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.v3.stage_router import StageRouter, load_current_catalog
from tools.v3.contract_validation import validate_instance


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
FIXTURES = ROOT / "fixtures/v3/router/routing-eval-v1.json"


class StageRouterEvaluationFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
        cls.catalog = load_current_catalog(REGISTRY)
        cls.registry_epoch = (
            "registry:"
            + json.loads(REGISTRY.read_text(encoding="utf-8"))["source_commit"]
        )

    def test_suite_has_ten_real_workload_fixtures(self):
        self.assertEqual(len(self.suite["fixtures"]), 10)
        self.assertEqual(len(self.catalog), 214)

    def test_all_fixtures_produce_valid_explainable_routes(self):
        router = StageRouter(adapter="codex", registry_epoch=self.registry_epoch)
        for fixture in self.suite["fixtures"]:
            with self.subTest(fixture=fixture["fixture_id"]):
                route = router.route(
                    fixture["task_spec"],
                    fixture["stage"],
                    self.catalog,
                )
                validation = validate_instance("StageRoute", route)
                self.assertTrue(validation.valid, validation.errors)
                self.assertIn("routing_evidence", route)
                self.assertEqual(route["routing_evidence"]["body_files_loaded"], 0)
                self.assertEqual(
                    route["routing_evidence"]["metadata_records_inspected"],
                    len(self.catalog),
                )
                serialized = json.dumps(route, ensure_ascii=False)
                self.assertNotIn("SKILL.md body", serialized)

    def test_expected_status_and_skill_boundaries(self):
        router = StageRouter(adapter="codex", registry_epoch=self.registry_epoch)
        for fixture in self.suite["fixtures"]:
            with self.subTest(fixture=fixture["fixture_id"]):
                route = router.route(
                    fixture["task_spec"], fixture["stage"], self.catalog
                )
                selected = {item["skill_id"] for item in route["selected_skills"]}
                expected = fixture["expected"]
                if "status" in expected:
                    self.assertEqual(route["status"], expected["status"])
                for key, candidates in expected.items():
                    if key.startswith("required_any"):
                        self.assertTrue(
                            selected.intersection(candidates),
                            f"{fixture['fixture_id']} selected={sorted(selected)} missing any of {candidates}",
                        )
                self.assertTrue(
                    selected.isdisjoint(expected.get("forbidden_skill_ids", [])),
                    f"{fixture['fixture_id']} selected forbidden skill: {selected & set(expected.get('forbidden_skill_ids', []))}",
                )


if __name__ == "__main__":
    unittest.main()
