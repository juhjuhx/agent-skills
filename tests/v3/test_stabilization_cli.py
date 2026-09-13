"""Stabilization-era product CLI and diagnostics contract tests."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from tools.v3.installer import InstallerError, _error_details, main


class StabilizationCliTests(unittest.TestCase):
    def invoke(self, *argv: str) -> tuple[int, dict]:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main([*argv, "--format", "json"])
        return result, json.loads(output.getvalue())

    def test_explain_is_a_read_only_status_facade(self) -> None:
        result, payload = self.invoke("explain")

        self.assertEqual(result, 0)
        self.assertEqual(payload["product"], "Agent Skills Matrix v3")
        self.assertEqual(payload["stage_router"], "READY")
        self.assertFalse(payload["real_home_apply_authorized"])
        self.assertTrue(payload["no_model_or_provider_invocation"])

    def test_doctor_reports_static_contract_health_without_runtime_probe(self) -> None:
        result, payload = self.invoke("doctor")

        self.assertEqual(result, 0)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["runtime_probe"], "NOT_RUN")
        self.assertEqual(payload["model_invocation"], "NOT_RUN")
        self.assertGreaterEqual(payload["checks"]["metadata_records"], 200)

    def test_blocked_error_has_code_remediation_and_safe_state(self) -> None:
        result, payload = self.invoke(
            "apply",
            "--runtime",
            "claude-code",
            "--scope",
            "user",
        )

        self.assertEqual(result, 2)
        self.assertEqual(payload["error"], "USER_SCOPE_APPLY_NOT_AUTHORIZED")
        self.assertEqual(payload["error_code"], "USER_SCOPE_APPLY_NOT_AUTHORIZED")
        self.assertEqual(payload["safe_state"], "NO_MUTATION")
        self.assertIn("virtual", payload["next_action"].lower())

    def test_unknown_runtime_is_actionable_without_private_context(self) -> None:
        result, payload = self.invoke(
            "preview",
            "--runtime",
            "not-in-the-contract",
            "--scope",
            "project",
        )
        self.assertEqual(result, 2)
        self.assertEqual(payload["error_code"], "UNKNOWN_RUNTIME")
        self.assertEqual(payload["safe_state"], "NO_MUTATION")
        self.assertNotIn("not-in-the-contract", json.dumps(payload))

    def test_recovery_error_has_a_bounded_next_step(self) -> None:
        details = _error_details(
            InstallerError("RECOVERY_BLOCKED: journal digest mismatch")
        )
        self.assertEqual(details["error_code"], "RECOVERY_BLOCKED")
        self.assertEqual(details["safe_state"], "NO_NEW_MUTATION")
        self.assertIn("transaction", str(details["next_action"]).lower())

    def test_fallback_error_guidance_does_not_echo_a_private_path(self) -> None:
        details = _error_details(
            InstallerError("cannot inspect /Users/huang/private-project")
        )
        serialized = json.dumps(details)
        self.assertNotIn("/Users/huang", serialized)
        self.assertEqual(details["error_code"], "INVALID_TARGET")


if __name__ == "__main__":
    unittest.main()
