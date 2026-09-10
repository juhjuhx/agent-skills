"""Regression checks for the Phase 3E Hermes qualification evidence.

These tests validate the sanitized, pre-inference qualification artifact. They
do not invoke Hermes, read credentials, or claim live execution quality.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD_PATH = (
    REPO_ROOT
    / "fixtures"
    / "v3"
    / "model-routing"
    / "qualification"
    / "hermes-qualification-001.json"
)


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return keys


class HermesQualificationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))

    def test_record_is_sanitized_and_not_live_quality(self) -> None:
        self.assertEqual(self.record["evidence_class"], "HOST_MANAGED_FIXTURE")
        self.assertFalse(self.record["security"]["model_invocation_performed"])
        self.assertFalse(self.record["security"]["credentials_serialized"])
        self.assertFalse(self.record["security"]["raw_prompt_serialized"])
        self.assertFalse(self.record["security"]["raw_output_serialized"])
        self.assertFalse(self.record["security"]["session_state_serialized"])
        self.assertNotIn("api_key", _walk_keys(self.record))
        self.assertNotIn("access_token", _walk_keys(self.record))

    def test_provenance_does_not_equate_release_with_installed_source(self) -> None:
        runtime = self.record["runtime"]
        self.assertEqual(runtime["contract_target"], "INSTALLED_SOURCE_SNAPSHOT")
        self.assertNotEqual(runtime["release_commit"], runtime["installed_source_revision"])
        self.assertIn("DIFFERS", runtime["provenance_relation"])

    def test_oneshot_approval_semantics_is_bypass(self) -> None:
        approval = next(
            probe for probe in self.record["probes"] if probe["probe"] == "approval_semantics"
        )
        self.assertEqual(approval["result"], "BYPASS")
        self.assertFalse(self.record["security"]["approval_bypass_invocation_used"])
        self.assertFalse(self.record["runtime"]["support_status"] == "QUALIFIED")

    def test_provider_block_stops_smoke_and_adapter(self) -> None:
        self.assertEqual(self.record["qualification"]["decision"], "HERMES_RUNTIME_BLOCKED")
        self.assertEqual(self.record["qualification"]["provider_status"], "PROVIDER_BLOCKED")
        self.assertFalse(self.record["qualification"]["adapter_built"])
        self.assertFalse(self.record["qualification"]["smoke_b_eligible"])
        self.assertFalse(self.record["qualification"]["h03_eligible"])
        smoke = next(
            probe for probe in self.record["probes"] if probe["probe"] == "qualification_smoke_a"
        )
        self.assertEqual(smoke["result"], "NOT_RUN")
        self.assertFalse(smoke["model_invocation"])

    def test_no_secret_or_raw_diagnostic_is_recorded(self) -> None:
        self.assertEqual(self.record["probes"][3]["auth_status"], "LOGGED_OUT")
        self.assertFalse(self.record["probes"][3]["credential_values_read"])
        self.assertFalse(self.record["probes"][3]["credential_values_persisted"])
        self.assertFalse(self.record["ocr"]["raw_error_persisted"])


if __name__ == "__main__":
    unittest.main()
