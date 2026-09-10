"""Tests for the bounded Phase 3C live evidence boundary."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from tools.v3.contract_validation import validate_file
from tools.v3.live_benchmark import (
    ProcessObservation,
    assess_read_only_lane,
    build_live_execution_record,
    classify_smoke_probe,
    compare_effects,
    detect_output_format,
    digest_value,
    extract_runtime_metrics,
    output_evidence,
    repetition_classification,
    run_headless_command,
    sanitize_text,
    summarize_variance,
)


DIGEST = "sha256:" + ("0" * 64)
ROOT = Path(__file__).resolve().parents[2]


def controls(**overrides):
    value = {
        "task_spec_digest": DIGEST,
        "fixture_digest": DIGEST,
        "start_sha": "a" * 40,
        "stage_route_digest": DIGEST,
        "selected_skill_ids": ["verification-before-completion"],
        "selected_skill_digests": [DIGEST],
        "permission_envelope_digest": DIGEST,
        "tool_availability": ["Read"],
        "mcp_availability": "NOT_USED",
        "project_instruction_digest": DIGEST,
        "system_instruction_digest": DIGEST,
    }
    value.update(overrides)
    return value


def provenance():
    return {
        "runtime_source": "local-version-probe",
        "invocation_contract": "runtime --headless --output json",
        "documentation_snapshot": "https://example.invalid/docs",
        "verification_method": "bounded test fixture",
        "observed_at": "2026-09-09T00:00:00+00:00",
    }


def record(**overrides):
    value = {
        "record_id": "record:phase3c:test",
        "run_id": "run:phase3c:test",
        "fixture_id": "H03-api-design",
        "runtime_id": "codex",
        "observed_version": "codex-cli 0.153.4",
        "model_id": "model-a",
        "reasoning_effort": "medium",
        "controls": controls(),
        "repetition_n": 1,
        "repetition_target": 2,
        "terminal_outcome": "VERIFIED_SUCCESS",
        "stage_outcomes": [{"stage": "design", "outcome": "PASS"}],
        "provenance": provenance(),
        "process": ProcessObservation(True, 0, False, 20.0, "ok", ""),
        "quality": {"acceptance_criteria_coverage": 1.0, "artifact_correctness": True},
    }
    value.update(overrides)
    return build_live_execution_record(**value)


class LiveBenchmarkContractTests(unittest.TestCase):
    def test_n_one_is_exploratory_only(self):
        self.assertEqual(repetition_classification(1, target=3)["classification"], "EXPLORATORY_ONLY")

    def test_repeated_cell_is_targeted(self):
        self.assertEqual(repetition_classification(3, target=3)["classification"], "TARGETED")

    def test_cross_runtime_comparison_is_configuration_effect(self):
        other = record(runtime_id="claude-code", model_id="model-b")
        result = compare_effects(record(), other)
        self.assertEqual(result["effect_class"], "CONFIGURATION_EFFECT")
        self.assertIn("model_id", result["confounders"])

    def test_same_runtime_model_only_change_is_model_effect(self):
        result = compare_effects(record(), record(model_id="model-b"))
        self.assertEqual(result["effect_class"], "MODEL_EFFECT")
        self.assertEqual(result["confounders"], [])

    def test_effort_only_change_is_separate_effect(self):
        result = compare_effects(record(), record(reasoning_effort="high"))
        self.assertEqual(result["effect_class"], "REASONING_EFFORT_EFFECT")

    def test_workload_change_is_inconclusive(self):
        result = compare_effects(record(), record(controls=controls(fixture_digest="sha256:" + "1" * 64)))
        self.assertEqual(result["effect_class"], "INCONCLUSIVE")
        self.assertIn("fixture_digest", result["confounders"])

    def test_variance_keeps_success_rate_and_ranges(self):
        result = summarize_variance([
            {"success": True, "latency_ms": 10, "tool_calls": 1, "context_tokens": 100},
            {"success": False, "latency_ms": 30, "tool_calls": 3, "context_tokens": 200, "failure_reason": "timeout"},
        ])
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["latency_ms"]["median"], 20.0)
        self.assertEqual(result["tool_calls"], {"min": 1, "max": 3})
        self.assertEqual(result["failure_modes"], ["timeout"])

    def test_sanitization_redacts_common_credentials(self):
        sanitized = sanitize_text("Authorization: Bearer example-secret api_key=example-secret")
        self.assertNotIn("example-secret", sanitized)

    def test_output_evidence_contains_digest_not_raw_output(self):
        evidence = output_evidence("private skill body", "api_key=example-secret", format_hint="text")
        serialized = json.dumps(evidence)
        self.assertNotIn("private skill body", serialized)
        self.assertNotIn("example-secret", serialized)
        self.assertFalse(evidence["raw_output_serialized"])

    def test_structured_metadata_is_sanitized_before_serialization(self):
        safe_controls = controls(system_instruction_digest="sha256:" + "2" * 64)
        safe_controls["tool_availability"] = ["api_key=example-secret"]
        live = record(controls=safe_controls)
        self.assertNotIn("example-secret", json.dumps(live))

    def test_runtime_json_metrics_extract_model_and_usage_without_body(self):
        payload = json.dumps({"model": "model-a", "usage": {"input_tokens": 10, "output_tokens": 4}, "tool_calls": 2})
        metrics = extract_runtime_metrics(payload)
        self.assertEqual(metrics["model_id"], "model-a")
        self.assertEqual(metrics["input_tokens"]["value"], 10)
        self.assertEqual(metrics["output_tokens"]["value"], 4)
        self.assertEqual(metrics["tool_calls"]["value"], 2)
        self.assertEqual(metrics["input_tokens"]["aggregation"], "UNKNOWN")
        self.assertEqual(metrics["input_tokens"]["status"], "UNKNOWN")
        self.assertEqual(detect_output_format(payload), "json")

    def test_codex_turn_usage_is_cumulative_only_for_verified_release_contract(self):
        payload = "\n".join(
            json.dumps(item)
            for item in (
                {"type": "turn.started"},
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 145919,
                        "output_tokens": 1725,
                        "total_tokens": 147644,
                    },
                },
            )
        )

        metrics = extract_runtime_metrics(
            payload,
            runtime_id="codex",
            runtime_version="codex-cli 0.153.4",
        )

        self.assertEqual(metrics["input_tokens"]["value"], 145919)
        self.assertEqual(metrics["input_tokens"]["aggregation"], "CUMULATIVE_TOTAL")
        self.assertEqual(metrics["input_tokens"]["source"], "OBSERVED")
        self.assertEqual(metrics["input_tokens"]["status"], "VERIFIED")
        self.assertEqual(metrics["input_tokens"]["source_field"], "turn.completed.usage.input_tokens")
        self.assertEqual(metrics["tokens_total"]["aggregation"], "CUMULATIVE_TOTAL")
        self.assertEqual(metrics["tokens_total"]["status"], "VERIFIED")

    def test_codex_usage_without_release_identity_does_not_claim_cumulative_total(self):
        payload = json.dumps(
            {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 4}}
        )

        metrics = extract_runtime_metrics(payload, runtime_id="codex")

        self.assertEqual(metrics["input_tokens"]["value"], 10)
        self.assertEqual(metrics["input_tokens"]["aggregation"], "UNKNOWN")
        self.assertEqual(metrics["input_tokens"]["status"], "UNKNOWN")
        self.assertEqual(metrics["tokens_total"]["aggregation"], "UNKNOWN")

    def test_unobservable_model_calls_remain_unknown(self):
        live = record(process=ProcessObservation(True, 0, False, 10.0, "plain output", ""))

        self.assertIsNone(live["efficiency"]["model_calls"])
        model_calls = next(
            item for item in live["efficiency"]["metric_provenance"] if item["metric_name"] == "model_calls"
        )
        self.assertEqual(model_calls["source"], "UNKNOWN")
        self.assertEqual(model_calls["aggregation"], "UNKNOWN")
        self.assertEqual(model_calls["status"], "UNKNOWN")

    def test_metric_provenance_includes_host_and_runtime_semantics(self):
        live = record(
            runtime_id="generic-runtime",
            process=ProcessObservation(
                True,
                0,
                False,
                10.0,
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {"input_tokens": 10, "output_tokens": 4},
                    }
                ),
                "",
            )
        )

        provenance = {item["metric_name"]: item for item in live["efficiency"]["metric_provenance"]}
        self.assertEqual(provenance["latency_ms"]["aggregation"], "PER_RUN")
        self.assertEqual(provenance["input_tokens"]["aggregation"], "UNKNOWN")
        self.assertEqual(provenance["cost_units"]["status"], "UNKNOWN")

    def test_smoke_timeout_preserves_timeout_class_but_unknown_cause(self):
        result = classify_smoke_probe(ProcessObservation(True, None, True, 1000.0, "", ""))

        self.assertEqual(result["status"], "LIVE_LANE_BLOCKED")
        self.assertEqual(result["failure_class"], "TIMEOUT")
        self.assertEqual(result["cause"], "UNKNOWN")
        self.assertFalse(result["quality_evidence_eligible"])

    def test_smoke_auth_failure_is_classified_without_serializing_stderr(self):
        result = classify_smoke_probe(ProcessObservation(True, 1, False, 10.0, "", "401 Unauthorized"))

        self.assertEqual(result["status"], "LIVE_LANE_BLOCKED")
        self.assertEqual(result["failure_class"], "AUTH")
        self.assertNotIn("Unauthorized", json.dumps(result))

    def test_structured_runtime_error_is_unavailable_not_quality_failure(self):
        observation = ProcessObservation(
            True,
            1,
            False,
            10.0,
            '{"type":"error","error":{"name":"UnknownError"}}',
            "",
        )
        live = record(process=observation)
        self.assertEqual(live["status"], "LIVE_LANE_BLOCKED")
        self.assertEqual(live["evidence_class"], "UNAVAILABLE")
        self.assertEqual(live["terminal_outcome"], "BLOCKED")
        self.assertIsNone(live["quality"]["artifact_correctness"])

    def test_open_code_read_only_lane_requires_every_least_privilege_control(self):
        blocked = assess_read_only_lane({"read_only": True, "deny_shell": True})
        eligible = assess_read_only_lane(
            {
                "read_only": True,
                "deny_shell": True,
                "deny_write": True,
                "deny_network": True,
                "deny_secrets": True,
                "isolated_workspace": True,
            }
        )

        self.assertEqual(blocked["status"], "LIVE_LANE_BLOCKED")
        self.assertEqual(eligible["status"], "ELIGIBLE")

    def test_real_record_is_valid_and_keeps_unknown_cost(self):
        live = record()
        self.assertEqual(live["evidence_class"], "REAL_EXECUTION")
        self.assertEqual(live["repetition"]["classification"], "EXPLORATORY_ONLY")
        self.assertEqual(live["efficiency"]["cost_status"], "UNKNOWN")
        self.assertFalse(live["sensitive_data_serialized"])
        self.assertNotIn("content", json.dumps(live))

    def test_blocked_auth_is_unavailable_and_not_quality_evidence(self):
        blocked = record(
            process=ProcessObservation(True, 1, False, 12.0, "", "401 Unauthorized"),
            terminal_outcome="VERIFIED_SUCCESS",
            quality={"acceptance_criteria_coverage": 1.0},
        )
        self.assertEqual(blocked["status"], "LIVE_LANE_BLOCKED")
        self.assertEqual(blocked["evidence_class"], "UNAVAILABLE")
        self.assertEqual(blocked["terminal_outcome"], "BLOCKED")
        self.assertIsNone(blocked["quality"]["acceptance_criteria_coverage"])

    def test_missing_executable_is_blocked_without_serializing_error_output(self):
        with tempfile.TemporaryDirectory() as cwd:
            observation = run_headless_command(["definitely-not-installed-v3"], cwd=cwd, timeout_s=1)
        blocked = record(process=observation, terminal_outcome="BLOCKED")
        self.assertFalse(observation.launched)
        self.assertEqual(blocked["evidence_class"], "UNAVAILABLE")
        self.assertNotIn("definitely-not-installed-v3", json.dumps(blocked))

    def test_runner_uses_isolated_cwd_and_captures_only_in_memory(self):
        with tempfile.TemporaryDirectory() as cwd:
            observation = run_headless_command(
                [sys.executable, "-c", "print('bounded')"], cwd=cwd, timeout_s=5
            )
        self.assertTrue(observation.launched)
        self.assertEqual(observation.returncode, 0)
        self.assertEqual(observation.stdout.strip(), "bounded")

    def test_runner_does_not_inherit_interactive_stdin(self):
        with tempfile.TemporaryDirectory() as cwd:
            observation = run_headless_command(
                [sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))"],
                cwd=cwd,
                timeout_s=5,
            )
        self.assertEqual(observation.returncode, 0)
        self.assertEqual(observation.stdout.strip(), "''")

    def test_unknown_cost_remains_unknown(self):
        live = record(process=ProcessObservation(True, 0, False, 10.0, "plain output", ""))
        self.assertIsNone(live["efficiency"]["cost_units"])
        self.assertEqual(live["efficiency"]["cost_status"], "UNKNOWN")

    def test_digest_value_is_stable(self):
        self.assertEqual(digest_value({"b": 2, "a": 1}), digest_value({"a": 1, "b": 2}))

    def test_checked_in_live_records_validate_against_public_contract(self):
        records = sorted((ROOT / "fixtures/v3/model-routing/runs/phase3c").glob("*.json"))
        self.assertGreaterEqual(len(records), 2)
        for path in records:
            result = validate_file("LiveExecutionRecord", path)
            self.assertTrue(result.valid, f"{path}: {result.errors}")

    def test_live_schema_is_registered_without_a_runtime_manager(self):
        record_result = validate_file(
            "LiveExecutionRecord",
            ROOT / "fixtures/v3/model-routing/runs/phase3c/live-codex-h01-001.json",
        )
        self.assertTrue(record_result.valid)

    def test_historical_codex_usage_is_explicitly_cumulative_and_not_model_call_count(self):
        historical = json.loads(
            (
                ROOT
                / "fixtures/v3/model-routing/runs/phase3c/live-codex-h01-001.json"
            ).read_text(encoding="utf-8")
        )
        metrics = {
            item["metric_name"]: item
            for item in historical["efficiency"]["metric_provenance"]
        }
        self.assertEqual(metrics["input_tokens"]["value"], 145919)
        self.assertEqual(metrics["input_tokens"]["aggregation"], "CUMULATIVE_TOTAL")
        self.assertEqual(metrics["output_tokens"]["aggregation"], "CUMULATIVE_TOTAL")
        self.assertIsNone(historical["efficiency"]["model_calls"])
        self.assertEqual(metrics["model_calls"]["status"], "UNKNOWN")

    def test_blocked_runtime_record_keeps_attempt_evidence_without_quality_claim(self):
        blocked = json.loads(
            (
                ROOT
                / "fixtures/v3/model-routing/runs/phase3c/live-opencode-h03-001.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(blocked["status"], "LIVE_LANE_BLOCKED")
        self.assertEqual(blocked["evidence_class"], "UNAVAILABLE")
        self.assertIsNone(blocked["quality"]["acceptance_criteria_coverage"])
        self.assertFalse(blocked["output_evidence"]["raw_output_serialized"])


if __name__ == "__main__":
    unittest.main()
