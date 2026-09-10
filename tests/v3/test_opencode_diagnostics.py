"""Regression tests for evidence-bounded OpenCode blocker diagnosis."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.v3.live_benchmark import (
    ProcessObservation,
    build_live_execution_record,
    classify_opencode_failure,
)


ROOT = Path(__file__).resolve().parents[2]
HISTORICAL = ROOT / "fixtures/v3/model-routing/runs/phase3c/live-opencode-contract-smoke-001.json"


class OpenCodeDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.historical = json.loads(HISTORICAL.read_text(encoding="utf-8"))

    def _observation(self, message: str = "UnknownError") -> ProcessObservation:
        return ProcessObservation(
            launched=True,
            returncode=1,
            timed_out=False,
            duration_ms=12.0,
            stdout=json.dumps(
                {"type": "error", "error": {"name": "UnknownError", "message": message}}
            ),
            stderr="",
        )

    def test_generic_unknown_error_does_not_imply_provider_or_model_cause(self):
        result = classify_opencode_failure(
            self._observation("Provider not found: anthropic"),
        )
        self.assertEqual(result["cause"], "RUNTIME_UNKNOWN")
        self.assertEqual(result["evidence_status"], "UNKNOWN")
        self.assertIsNone(result["provider_id"])
        self.assertIsNone(result["model_id"])

    def test_provider_not_configured_requires_direct_probe_evidence(self):
        result = classify_opencode_failure(
            self._observation(),
            provider_status="NOT_CONFIGURED",
            provider_id="anthropic",
            model_id="anthropic/claude-sonnet-4-5",
            config_source="GLOBAL_CONFIG",
        )
        self.assertEqual(result["cause"], "PROVIDER_NOT_CONFIGURED")
        self.assertEqual(result["evidence_status"], "DIRECT_PROBE")
        self.assertEqual(result["provider_id"], "anthropic")
        self.assertEqual(result["model_id"], "anthropic/claude-sonnet-4-5")

    def test_model_not_found_and_deprecated_require_explicit_model_status(self):
        not_found = classify_opencode_failure(
            self._observation(),
            model_status="NOT_FOUND",
            model_id="anthropic/claude-sonnet-4-5",
        )
        deprecated = classify_opencode_failure(
            self._observation(),
            model_status="DEPRECATED",
            model_id="anthropic/claude-sonnet-4-5",
        )
        self.assertEqual(not_found["cause"], "MODEL_NOT_FOUND")
        self.assertEqual(deprecated["cause"], "MODEL_DEPRECATED")

    def test_agent_cause_is_considered_only_after_provider_and_model_are_healthy(self):
        result = classify_opencode_failure(
            self._observation(),
            provider_status="CONFIGURED",
            model_status="AVAILABLE",
            agent_status="FAILED",
            agent_id="plan",
        )
        self.assertEqual(result["cause"], "AGENT_RESOLUTION")
        self.assertEqual(result["agent_id"], "plan")

    def test_diagnostic_identity_is_sanitized_before_record_persistence(self):
        result = classify_opencode_failure(
            self._observation(),
            provider_status="NOT_CONFIGURED",
            provider_id="anthropic",
            model_id="anthropic/claude-sonnet-4-5",
            config_source="GLOBAL_CONFIG",
        )
        result["reference_code"] = "Authorization: Bearer sk-example-secret"
        record = build_live_execution_record(
            record_id="record:phase3c3:diagnostic:001",
            run_id="run:phase3c3:diagnostic:001",
            fixture_id="H03-opencode-runtime-provider-probe",
            runtime_id="opencode",
            observed_version="1.18.25",
            model_id="anthropic/claude-sonnet-4-5",
            reasoning_effort=None,
            controls=self.historical["controls"],
            repetition_n=1,
            repetition_target=1,
            terminal_outcome="BLOCKED",
            stage_outcomes=[
                {"stage": "research", "outcome": "BLOCKED", "notes": "provider probe blocked"}
            ],
            provenance=self.historical["provenance"],
            process=self._observation(),
            diagnostic=result,
            confounders=["diagnostic-only provider listing; no model quality claim"],
            notes="Provider identity was observed without persisting raw CLI output.",
        )
        serialized = json.dumps(record, ensure_ascii=False)
        self.assertIn("PROVIDER_NOT_CONFIGURED", serialized)
        self.assertNotIn("Authorization: Bearer", serialized)
        self.assertNotIn("sk-example-secret", serialized)
        self.assertFalse(record["diagnostic"]["raw_details_serialized"])


if __name__ == "__main__":
    unittest.main()
