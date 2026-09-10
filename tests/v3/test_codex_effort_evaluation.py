"""Contract tests for the bounded Codex reasoning-effort experiment."""

from __future__ import annotations

import copy
import unittest

from tools.v3.codex_effort_evaluation import (
    build_codex_exec_command,
    build_interleaved_schedule,
    classify_effort_effect,
    compare_controlled_effort,
    historical_record_is_eligible,
    model_pin_status,
    readiness_split,
    routing_policy_proposal,
)


DIGEST = "sha256:" + ("0" * 64)


def live_record(
    *,
    effort: str = "low",
    outcome: str = "VERIFIED_SUCCESS",
    latency: float = 100.0,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    evidence_class: str = "REAL_EXECUTION",
    model_id: str | None = "gpt-5.6-luna",
    route_digest: str = DIGEST,
    fixture_digest: str = DIGEST,
    skill_digests: list[str] | None = None,
) -> dict:
    return {
        "evidence_class": evidence_class,
        "runtime_id": "codex",
        "observed_version": "codex-cli 0.153.4",
        "model_id": model_id,
        "reasoning_effort": effort,
        "terminal_outcome": outcome,
        "controls": {
            "task_spec_digest": DIGEST,
            "fixture_digest": fixture_digest,
            "start_sha": "a" * 40,
            "stage_route_digest": route_digest,
            "selected_skill_ids": ["tdd", "verification-before-completion"],
            "selected_skill_digests": skill_digests or [DIGEST, DIGEST],
            "permission_envelope_digest": DIGEST,
            "tool_availability": ["codex exec", "workspace-write"],
            "mcp_availability": "NOT_USED",
            "project_instruction_digest": DIGEST,
            "system_instruction_digest": DIGEST,
        },
        "efficiency": {
            "latency_ms": latency,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model_calls": None,
            "tool_calls": None,
            "cost_units": None,
        },
        "quality": {
            "acceptance_criteria_coverage": 1.0 if outcome == "VERIFIED_SUCCESS" else 0.5,
            "tests_pass": outcome == "VERIFIED_SUCCESS",
            "artifact_correctness": outcome == "VERIFIED_SUCCESS",
        },
    }


class CodexEffortEvaluationTests(unittest.TestCase):
    def test_interleaved_schedule_is_bounded_and_deterministic(self):
        expected = [
            ("H01", "low", 1),
            ("H01", "medium", 1),
            ("H01", "medium", 2),
            ("H01", "low", 2),
            ("H03", "low", 1),
            ("H03", "medium", 1),
        ]
        schedule = build_interleaved_schedule()
        self.assertEqual(
            [(item["workload_id"], item["effort"], item["repetition"]) for item in schedule],
            expected,
        )
        self.assertEqual(schedule, build_interleaved_schedule())
        self.assertEqual(len(schedule), 6)
        self.assertNotIn("H09", {item["workload_id"] for item in schedule})

    def test_schedule_supports_a_different_adjacent_effort_pair(self):
        schedule = build_interleaved_schedule(("none", "low"))
        self.assertEqual(schedule[0]["effort"], "none")
        self.assertEqual(schedule[1]["effort"], "low")

    def test_command_pins_model_effort_and_safe_codex_boundary(self):
        command = build_codex_exec_command(
            model_id="gpt-5.6-luna",
            reasoning_effort="low",
            sandbox_mode="workspace-write",
            cwd="/private/tmp/fixture",
        )
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--model", command)
        self.assertIn("gpt-5.6-luna", command)
        self.assertIn('model_reasoning_effort="low"', command)
        self.assertIn("--ask-for-approval", command)
        self.assertIn("never", command)
        self.assertIn("--sandbox", command)
        self.assertIn("--json", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_model_pin_requires_explicit_non_secret_identity(self):
        self.assertEqual(
            model_pin_status("gpt-5.6-luna", "gpt-5.6-luna", "OBSERVED")["status"],
            "PINNED",
        )
        self.assertEqual(
            model_pin_status("gpt-5.6-luna", None, "UNKNOWN")["status"],
            "UNVERIFIED",
        )
        self.assertEqual(
            model_pin_status(None, "gpt-5.6-luna", "OBSERVED")["status"],
            "BLOCKED",
        )

    def test_effort_comparison_requires_same_route_skills_permissions_and_model(self):
        first = live_record(effort="low")
        second = live_record(effort="medium")
        result = compare_controlled_effort(first, second)
        self.assertEqual(result["effect_class"], "REASONING_EFFORT_EFFECT")
        self.assertEqual(result["confounders"], [])

        changed = live_record(effort="medium", route_digest="sha256:" + ("1" * 64))
        result = compare_controlled_effort(first, changed)
        self.assertEqual(result["effect_class"], "INCONCLUSIVE")
        self.assertIn("stage_route_digest", result["confounders"])

        unpinned = live_record(effort="medium", model_id=None)
        result = compare_controlled_effort(first, unpinned)
        self.assertEqual(result["effect_class"], "INCONCLUSIVE")
        self.assertIn("model_id", result["confounders"])

    def test_historical_unpinned_records_are_excluded(self):
        self.assertFalse(historical_record_is_eligible(live_record(model_id=None)))
        self.assertFalse(historical_record_is_eligible(live_record(effort=None)))
        self.assertFalse(
            historical_record_is_eligible(live_record(evidence_class="HOST_MANAGED_FIXTURE"))
        )
        self.assertTrue(historical_record_is_eligible(live_record()))

    def test_higher_effort_classification_keeps_quality_separate_from_cost(self):
        low = [live_record(effort="low", latency=100), live_record(effort="low", latency=120)]
        medium = [
            live_record(effort="medium", latency=180),
            live_record(effort="medium", latency=220),
        ]
        result = classify_effort_effect(low, medium)
        self.assertEqual(result["classification"], "LOWER_EFFORT_EQUIVALENT")
        self.assertEqual(result["quality"]["lower"]["success_count"], 2)
        self.assertEqual(result["quality"]["higher"]["success_count"], 2)
        self.assertEqual(result["efficiency"]["higher_latency_ms"]["median"], 200.0)

    def test_higher_effort_quality_gain_is_not_collapsed_into_a_scalar(self):
        low = [live_record(effort="low", outcome="FAILED", latency=100), live_record(effort="low", outcome="FAILED", latency=120)]
        medium = [live_record(effort="medium", latency=180), live_record(effort="medium", latency=220)]
        result = classify_effort_effect(low, medium)
        self.assertEqual(result["classification"], "HIGHER_EFFORT_MATERIALLY_BETTER")
        self.assertIn("quality", result)
        self.assertIn("efficiency", result)
        self.assertNotIn("quality_score", result)

    def test_n_one_is_explicitly_inconclusive_for_effort_effect(self):
        result = classify_effort_effect(
            [live_record(effort="low")], [live_record(effort="medium")]
        )
        self.assertEqual(result["classification"], "INCONCLUSIVE")
        self.assertEqual(result["repetition_status"], "EXPLORATORY_ONLY")

    def test_routing_policy_proposal_does_not_mutate_active_policy(self):
        active = {"effort": {"default": "low"}}
        original = copy.deepcopy(active)
        proposal = routing_policy_proposal(
            active,
            {"H01": {"classification": "LOWER_EFFORT_EQUIVALENT"}},
        )
        self.assertEqual(active, original)
        self.assertEqual(proposal["status"], "PROPOSAL_ONLY")
        proposal["proposed_policy"]["effort"]["default"] = "medium"
        self.assertEqual(active, original)

    def test_readiness_is_split_between_codex_local_and_cross_runtime(self):
        result = readiness_split(
            pinned_model=True,
            effort_levels=("low", "medium"),
            h01_counts=(2, 2),
            h03_counts=(1, 1),
            measurement_integrity=True,
            controlled_variables=True,
            cross_runtime_evidence=False,
        )
        self.assertEqual(result["intra_runtime"], "READY")
        self.assertEqual(result["cross_runtime"], "NOT_READY")


if __name__ == "__main__":
    unittest.main()
