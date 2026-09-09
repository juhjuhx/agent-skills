"""Contract-first tests for the v3 runtime/model evaluation harness."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from tools.v3.contract_validation import validate_file, validate_instance
from tools.v3.runtime_model_evaluation import (
    assess_model_candidate,
    assess_runtime_candidate,
    baseline_select,
    build_execution_configuration,
    build_runtime_handoff,
    make_evaluation_result,
    make_evaluation_run,
    model_routing_work_required,
    pareto_frontier,
    routing_policy_proposal,
)


ROOT = Path(__file__).resolve().parents[2]


def minimal_runtime_candidate() -> dict:
    return {
        "schema_version": "3.0",
        "candidate_id": "runtime:codex-fixture",
        "runtime_id": "codex",
        "availability": "INSTALLED",
        "adapter_status": "IMPLEMENTED",
        "capabilities": {
            "editing": True,
            "sandbox": True,
            "skills": True,
        },
        "model_selection": {
            "task": "SUPPORTED",
            "stage": "TASK_PINNED",
            "subagent": "SUPPORTED",
            "step": "DESIGN_ONLY",
        },
        "permissions": {
            "policy_gated": True,
            "supported_levels": ["read-only", "workspace-write"],
        },
        "evidence_provenance": {
            "evidence_class": "REAL_EXECUTION",
            "source": "local-version-probe",
            "method": "codex --version",
        },
    }


def minimal_model_candidate() -> dict:
    return {
        "schema_version": "3.0",
        "candidate_id": "model:openai-fixture",
        "provider_id": "openai",
        "model_id": "gpt-compatible-fixture",
        "profile_ref": "openai/gpt-compatible-fixture@fixture-1.0",
        "availability": "AVAILABLE",
        "capabilities": {
            "coding": True,
            "planning": True,
            "debugging": True,
            "research": True,
            "review": True,
            "security": True,
            "tool_use": True,
            "structured_output": True,
            "multimodal": True,
            "long_context": True,
        },
        "reasoning": {"supported": True, "effort_levels": ["low", "high"]},
        "limits": {
            "context_tokens": 128000,
            "max_output_tokens": 16000,
            "max_tool_schema_tokens": 12000,
        },
        "tool_support": {"function_calling": True, "structured_output": True},
        "latency": {"class": "interactive", "p50_ms": None, "p95_ms": None},
        "cost": {"class": "balanced", "measured_units": None, "currency": None},
        "evidence_provenance": {
            "evidence_class": "HOST_MANAGED_FIXTURE",
            "source": "fixture",
            "method": "static-contract-fixture",
        },
    }


def task_spec(*, task_id: str = "task:evaluation", required_capabilities=None, complexity="STANDARD") -> dict:
    return {
        "schema_version": "3.0",
        "task_id": task_id,
        "task_type": "implementation",
        "complexity": complexity,
        "risk": "MEDIUM",
        "ambiguity": "LOW",
        "objectives": ["evaluate a bounded task"],
        "required_capabilities": list(required_capabilities or ["needs_editing"]),
        "permission_requirements": {
            "level": "workspace-write",
            "filesystem": "workspace-write",
            "network": "none",
            "external_write": False,
            "secrets": False,
            "publish": False,
            "delete": False,
        },
    }


def stage_route(*, status: str = "SKILLS_SELECTED") -> dict:
    route = {
        "schema_version": "3.0",
        "route_id": "route:evaluation:implement",
        "task_id": "task:evaluation",
        "stage": "implement",
        "registry_epoch": "registry:test",
        "status": status,
        "selected_skills": [] if status == "NO_SKILL_NEEDED" else [
            {"skill_id": "test-driven-development", "role": "PROCESS", "reason": "test"}
        ],
        "role_assignments": [] if status == "NO_SKILL_NEEDED" else [
            {"skill_id": "test-driven-development", "role": "PROCESS"}
        ],
        "adapter": "codex",
        "model_profile": "unselected",
        "granted_capabilities": ["editing", "sandbox", "structured_output"],
        "budget_envelope": {"permission_level": "workspace-write"},
        "alternatives": [],
        "route_reasons": ["test route"],
        "evidence_required": ["tests"],
        "routing_evidence": {
            "candidate_count": 1,
            "filtered_count": 0,
            "eligible_count": 1,
            "selected_count": 1,
            "required_roles": ["PROCESS"],
            "role_coverage": ["PROCESS"],
            "duplicate_role_pressure": 0,
            "context_bytes_estimate": 0,
            "body_files_loaded": 0,
            "body_bytes_loaded": 0,
            "tool_requirements": [],
            "trust_blocks": 0,
            "relationship_effects": [],
            "metadata_records_inspected": 1,
            "selected_candidates": [],
            "rejected_candidates": [],
            "deep_understanding": {"status": "OFF", "reason": "not needed"},
        },
    }
    if status == "NO_SKILL_NEEDED":
        route["no_skill_reason"] = "No additional procedure is required."
        route["routing_evidence"]["selected_count"] = 0
        route["routing_evidence"]["eligible_count"] = 0
    return route


def codex_manifest() -> dict:
    with (ROOT / "fixtures/v3/agents/codex.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def base_result(*, result_id: str = "result:a", evidence_class: str = "REAL_EXECUTION", quality=None, efficiency=None) -> dict:
    quality = quality or {
        "acceptance_criteria_coverage": 1.0,
        "test_pass": True,
        "artifact_correctness": True,
        "review_findings": 0,
        "source_accuracy": 1.0,
        "user_correction": False,
    }
    efficiency = efficiency or {
        "latency_ms": 100.0,
        "wall_time_ms": 120.0,
        "model_calls": 1,
        "tool_calls": 1,
        "context_tokens": 100,
        "tokens_total": 200,
        "cost_units": 1.0,
    }
    if evidence_class != "REAL_EXECUTION":
        quality = {key: None if key != "review_findings" else None for key in quality}
    return make_evaluation_result(
        result_id=result_id,
        run_id=f"run:{result_id}",
        evidence_class=evidence_class,
        outcome="PASS" if evidence_class == "REAL_EXECUTION" else "UNKNOWN",
        terminal_outcome="VERIFIED_SUCCESS" if evidence_class == "REAL_EXECUTION" else "UNKNOWN",
        stage_outcomes=[{"stage": "implement", "outcome": "PASS" if evidence_class == "REAL_EXECUTION" else "UNKNOWN"}],
        quality=quality,
        efficiency=efficiency,
        reliability={"reroutes": 0, "failed_tool_calls": 0, "retries": 0, "invalid_edits": 0, "recovery_success": True},
        security={"permission_violation": False, "unsafe_proposal": False, "secret_exposure": False, "sandbox_mismatch": False},
        portability={"handoff_artifact_complete": True, "runtime_specific_leakage": False, "capabilities_lost": []},
        provenance={"source": "test", "method": "deterministic-test", "evidence_class": evidence_class},
    )


class RuntimeModelEvaluationContractTests(unittest.TestCase):
    def test_minimal_runtime_candidate_is_valid(self):
        result = validate_instance("RuntimeCandidate", minimal_runtime_candidate())

        self.assertTrue(result.valid, result.errors)

    def test_minimal_model_candidate_is_valid(self):
        result = validate_instance("ModelCandidate", minimal_model_candidate())

        self.assertTrue(result.valid, result.errors)

    def test_new_public_contracts_are_registered(self):
        for name in (
            "RuntimeCandidate",
            "ModelCandidate",
            "ExecutionConfiguration",
            "EvaluationRun",
            "EvaluationResult",
            "RuntimeHandoff",
        ):
            with self.subTest(contract=name):
                from tools.v3.contract_validation import load_schema

                self.assertIsInstance(load_schema(name), dict)

    def test_checked_in_runtime_and_model_candidate_fixtures_validate(self):
        for relative_path, contract in (
            ("fixtures/v3/model-routing/runtime-candidates.json", "RuntimeCandidate"),
            ("fixtures/v3/model-routing/model-candidates.json", "ModelCandidate"),
        ):
            with (ROOT / relative_path).open(encoding="utf-8") as handle:
                records = json.load(handle)
            for record in records:
                with self.subTest(path=relative_path, candidate=record["candidate_id"]):
                    result = validate_instance(contract, record)
                    self.assertTrue(result.valid, result.errors)

    def test_development_set_references_the_existing_a_to_j_fixtures(self):
        with (ROOT / "fixtures/v3/model-routing/development/index.json").open(encoding="utf-8") as handle:
            development = json.load(handle)

        self.assertEqual(development["fixture_set"], "DEVELOPMENT")
        self.assertEqual(len(development["fixtures"]), 10)
        self.assertEqual(
            {item["source_fixture_id"] for item in development["fixtures"]},
            {
                "A-readme-typo", "B-ordinary-bug", "C-api-architecture",
                "D-large-frontend-feature", "E-security-sensitive-change",
                "F-deep-source-research", "G-visual-design",
                "H-github-repository-audit", "I-new-product-specification", "J-release-gate",
            },
        )
        self.assertTrue(all(item["expected_runtime"] is None and item["expected_model"] is None for item in development["fixtures"]))

    def test_holdout_set_is_separate_and_has_no_expected_identity_labels(self):
        with (ROOT / "fixtures/v3/model-routing/holdout/index.json").open(encoding="utf-8") as handle:
            holdout = json.load(handle)

        self.assertEqual(holdout["fixture_set"], "HOLDOUT")
        self.assertEqual(len(holdout["fixtures"]), 12)
        self.assertTrue(holdout["holdout_policy"]["no_expected_runtime_or_model"])
        self.assertTrue(all(item.get("expected_runtime") is None and item.get("expected_model") is None for item in holdout["fixtures"]))

    def test_runtime_and_model_identifiers_cannot_cross_layers(self):
        runtime = minimal_runtime_candidate()
        runtime["provider_id"] = "openai"
        model = minimal_model_candidate()
        model["runtime_id"] = "codex"

        self.assertFalse(validate_instance("RuntimeCandidate", runtime).valid)
        self.assertFalse(validate_instance("ModelCandidate", model).valid)

    def test_unknown_runtime_capability_is_warning_not_authority(self):
        runtime = minimal_runtime_candidate()
        runtime["capabilities"]["future_authority"] = True

        result = validate_instance("RuntimeCandidate", runtime)

        self.assertTrue(result.valid, result.errors)
        self.assertEqual(result.unknown_capabilities, ["future_authority"])

    def test_runtime_candidate_is_ineligible_when_required_capability_is_missing(self):
        runtime = minimal_runtime_candidate()
        runtime["capabilities"]["editing"] = False

        result = assess_runtime_candidate(task_spec(), runtime)

        self.assertEqual(result["status"], "INCOMPATIBLE")
        self.assertIn("editing", " ".join(result["reasons"]))

    def test_runtime_without_policy_gating_is_incompatible(self):
        runtime = minimal_runtime_candidate()
        runtime["permissions"]["policy_gated"] = False

        result = assess_runtime_candidate(task_spec(), runtime)

        self.assertEqual(result["status"], "INCOMPATIBLE")
        self.assertIn("policy-gated", " ".join(result["reasons"]))

    def test_unknown_runtime_availability_is_unverified(self):
        runtime = minimal_runtime_candidate()
        runtime["availability"] = "UNKNOWN"

        result = assess_runtime_candidate(task_spec(), runtime)

        self.assertEqual(result["status"], "UNVERIFIED")

    def test_model_eligibility_is_task_pinned_when_stage_switch_is_unsupported(self):
        runtime = minimal_runtime_candidate()
        runtime["model_selection"]["stage"] = "TASK_PINNED"

        result = assess_model_candidate(
            task_spec(), runtime, minimal_model_candidate(), selection_scope="STAGE"
        )

        self.assertEqual(result["status"], "TASK_PINNED")
        self.assertIn("stage", result["reason"])

    def test_stage_model_override_is_eligible_when_runtime_supports_it(self):
        runtime = minimal_runtime_candidate()
        runtime["model_selection"]["stage"] = "SUPPORTED"

        result = assess_model_candidate(
            task_spec(), runtime, minimal_model_candidate(), selection_scope="STAGE"
        )

        self.assertEqual(result["status"], "ELIGIBLE")
        self.assertIn("stage", result["reason"])

    def test_model_candidate_cannot_grant_filesystem_authority(self):
        model = minimal_model_candidate()
        model["capabilities"]["filesystem"] = True

        result = validate_instance("ModelCandidate", model)

        self.assertFalse(result.valid)

    def test_model_capability_mismatch_is_incompatible(self):
        model = minimal_model_candidate()
        model["capabilities"]["security"] = False

        result = assess_model_candidate(
            task_spec(), minimal_runtime_candidate(), model,
            required_model_capabilities=["security"],
        )

        self.assertEqual(result["status"], "INCOMPATIBLE")

    def test_execution_configuration_is_deterministic_and_permission_intersected(self):
        task = task_spec()
        route = stage_route()
        route["task_id"] = task["task_id"]
        kwargs = {
            "task_spec": task,
            "stage_route": route,
            "runtime_candidate": minimal_runtime_candidate(),
            "model_candidate": minimal_model_candidate(),
            "adapter_manifest": codex_manifest(),
            "policy": {"level": "workspace-write", "filesystem": "workspace-write", "network": "none"},
            "live_runtime": {"sandbox_mode": "workspace-write", "network_access": False},
            "selection_scope": "TASK_DEFAULT",
            "evidence_mode": "HOST_MANAGED_FIXTURE",
        }

        first = build_execution_configuration(**kwargs)
        second = build_execution_configuration(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(first["permission_envelope"]["filesystem"], "workspace-write")
        self.assertEqual(first["provenance"]["evidence_class"], "HOST_MANAGED_FIXTURE")

    def test_model_capability_cannot_appear_as_effective_runtime_capability(self):
        task = task_spec()
        route = stage_route()
        route["task_id"] = task["task_id"]
        model = minimal_model_candidate()
        model["capabilities"]["editing"] = True

        with self.assertRaises(ValueError):
            build_execution_configuration(
                task_spec=task,
                stage_route=route,
                runtime_candidate=minimal_runtime_candidate(),
                model_candidate=model,
                adapter_manifest=codex_manifest(),
                policy={"level": "workspace-write", "filesystem": "workspace-write", "network": "none"},
                live_runtime={"sandbox_mode": "workspace-write", "network_access": False},
            )

    def test_execution_configuration_rejects_runtime_adapter_mismatch(self):
        task = task_spec()
        route = stage_route()
        route["task_id"] = task["task_id"]
        manifest = codex_manifest()
        manifest["runtime_id"] = "claude-code"

        with self.assertRaises(ValueError):
            build_execution_configuration(
                task_spec=task,
                stage_route=route,
                runtime_candidate=minimal_runtime_candidate(),
                model_candidate=minimal_model_candidate(),
                adapter_manifest=manifest,
                policy={"level": "workspace-write", "filesystem": "workspace-write", "network": "none"},
                live_runtime={"sandbox_mode": "workspace-write", "network_access": False},
            )

    def test_no_skill_configuration_drops_model_reference_and_work(self):
        task = task_spec()
        route = stage_route(status="NO_SKILL_NEEDED")
        route["task_id"] = task["task_id"]

        configuration = build_execution_configuration(
            task_spec=task,
            stage_route=route,
            runtime_candidate=minimal_runtime_candidate(),
            model_candidate=minimal_model_candidate(),
            adapter_manifest=codex_manifest(),
            policy={"level": "workspace-write", "filesystem": "workspace-write", "network": "none"},
            live_runtime={"sandbox_mode": "workspace-write", "network_access": False},
        )

        self.assertIsNone(configuration["model_candidate_ref"])
        self.assertEqual(configuration["no_model_work_reason"], route["no_skill_reason"])

    def test_no_skill_route_requires_no_model_routing_work(self):
        route = stage_route(status="NO_SKILL_NEEDED")

        result = model_routing_work_required(route)

        self.assertFalse(result["required"])
        self.assertIn("NO_SKILL_NEEDED", result["reason"])

    def test_explicit_runtime_handoff_preserves_portable_artifacts_and_policy(self):
        handoff = build_runtime_handoff(
            handoff_id="handoff:codex-to-hermes",
            task_id="task:evaluation",
            source_runtime_ref="runtime:codex",
            destination_runtime_ref="runtime:hermes",
            reason="destination runtime has required long-running coordination",
            portable_artifact_refs=["TaskSpec:task:evaluation", "StagePlan:task:evaluation"],
            working_tree_state={"commit": "abc123", "dirty": True, "changed_paths": ["tools/v3/example.py"]},
            permission_envelope={"level": "workspace-write", "filesystem": "workspace-write", "network": "none", "external_write": False, "secrets": False, "publish": False, "delete": False},
            lost_capabilities=["hooks"],
            handoff_cost={"class": "medium", "latency_ms": 50, "context_tokens": 200},
        )

        self.assertTrue(validate_instance("RuntimeHandoff", handoff).valid)
        self.assertEqual(handoff["handoff_mode"], "EXPLICIT")

    def test_mock_result_cannot_be_quality_or_ranking_evidence(self):
        result = base_result(evidence_class="MOCK")

        self.assertFalse(result["quality_evidence_eligible"])
        self.assertFalse(result["ranking_eligible"])
        self.assertTrue(validate_instance("EvaluationResult", result).valid)

    def test_real_result_records_terminal_and_stage_outcomes(self):
        result = base_result()

        self.assertEqual(result["terminal_outcome"], "VERIFIED_SUCCESS")
        self.assertEqual(result["stage_outcomes"][0]["stage"], "implement")
        self.assertTrue(result["quality_evidence_eligible"])

    def test_evaluation_run_is_append_only_and_does_not_serialize_credentials(self):
        run = make_evaluation_run(
            run_id="run:holdout-1",
            fixture_id="H01-bugfix",
            fixture_set="HOLDOUT",
            task_spec_ref="task:holdout-1",
            stage_route_refs=["route:holdout-1:implement"],
            runtime_candidate_ref="runtime:codex",
            model_candidate_ref="model:openai-fixture",
            evidence_class="HOST_MANAGED_FIXTURE",
            execution_mode="HOST_MANAGED_FIXTURE",
            repetition=1,
            status="COMPLETED",
        )

        self.assertEqual(run["history_mode"], "APPEND_ONLY")
        self.assertFalse(run["sensitive_data_serialized"])
        self.assertNotIn("api_key", run)

    def test_evaluation_run_rejects_mismatched_execution_evidence(self):
        with self.assertRaises(ValueError):
            make_evaluation_run(
                run_id="run:mismatch",
                fixture_id="H01-bugfix",
                fixture_set="HOLDOUT",
                task_spec_ref="task:holdout-1",
                stage_route_refs=["route:holdout-1:implement"],
                runtime_candidate_ref="runtime:codex",
                model_candidate_ref="model:openai-fixture",
                evidence_class="MOCK",
                execution_mode="HOST_MANAGED_FIXTURE",
                repetition=1,
                status="COMPLETED",
            )

    def test_unavailable_run_records_missing_evidence_without_quality_claim(self):
        run = make_evaluation_run(
            run_id="run:missing-runtime",
            fixture_id="H01-bugfix",
            fixture_set="HOLDOUT",
            task_spec_ref="task:holdout-1",
            stage_route_refs=["route:holdout-1:implement"],
            runtime_candidate_ref="runtime:mimo-code",
            model_candidate_ref=None,
            evidence_class="UNAVAILABLE",
            execution_mode="UNAVAILABLE",
            repetition=1,
            status="BLOCKED",
        )

        self.assertEqual(run["evidence_class"], "UNAVAILABLE")
        self.assertFalse(run["sensitive_data_serialized"])

    def test_baselines_are_deterministic_and_evaluation_only(self):
        candidates = [minimal_model_candidate()]
        cheaper = deepcopy(candidates[0])
        cheaper["candidate_id"] = "model:cheap-fixture"
        cheaper["cost"] = {"class": "low", "measured_units": None, "currency": None}
        candidates.append(cheaper)

        first = baseline_select(task_spec(), candidates, "BASELINE_CHEAPEST")
        second = baseline_select(task_spec(), candidates, "BASELINE_CHEAPEST")

        self.assertEqual(first, second)
        self.assertEqual(first["candidate_id"], "model:cheap-fixture")
        self.assertEqual(first["policy_status"], "EVALUATION_ONLY")

    def test_default_and_heuristic_baselines_do_not_make_model_preferences(self):
        candidates = [minimal_model_candidate()]

        default = baseline_select(task_spec(), candidates, "BASELINE_DEFAULT", default_candidate_id=candidates[0]["candidate_id"])
        heuristic = baseline_select(task_spec(complexity="COMPLEX"), candidates, "BASELINE_HEURISTIC")

        self.assertEqual(default["candidate_id"], heuristic["candidate_id"])
        self.assertNotIn("preferred_provider", heuristic)

    def test_pareto_frontier_keeps_non_dominated_real_results_without_scalar_score(self):
        fast = base_result(result_id="result:fast", quality={"acceptance_criteria_coverage": 0.8, "test_pass": True, "artifact_correctness": True, "review_findings": 0, "source_accuracy": 0.8, "user_correction": False}, efficiency={"latency_ms": 50, "wall_time_ms": 60, "model_calls": 1, "tool_calls": 1, "context_tokens": 100, "tokens_total": 150, "cost_units": 0.5})
        strong = base_result(result_id="result:strong", quality={"acceptance_criteria_coverage": 1.0, "test_pass": True, "artifact_correctness": True, "review_findings": 0, "source_accuracy": 1.0, "user_correction": False}, efficiency={"latency_ms": 200, "wall_time_ms": 220, "model_calls": 2, "tool_calls": 2, "context_tokens": 200, "tokens_total": 300, "cost_units": 2.0})

        frontier = pareto_frontier([fast, strong])

        self.assertEqual(frontier, ["result:fast", "result:strong"])
        self.assertNotIn("score", str(frontier))

    def test_mock_result_is_excluded_from_pareto_quality_comparison(self):
        self.assertEqual(pareto_frontier([base_result(evidence_class="MOCK")]), [])

    def test_policy_history_returns_proposal_without_mutating_policy(self):
        policy = {"model_preferences": {"default": "unchanged"}}

        proposal = routing_policy_proposal(["result:fast"], "compare terminal outcomes")

        self.assertEqual(proposal["status"], "PROPOSAL_ONLY")
        self.assertEqual(policy["model_preferences"]["default"], "unchanged")
        self.assertNotIn("ROUTING_POLICY.yaml", proposal.get("writes", []))

    def test_evidence_envelope_is_append_only_and_references_checked_in_inputs(self):
        with (ROOT / "fixtures/v3/model-routing/evidence-v1.json").open(encoding="utf-8") as handle:
            evidence = json.load(handle)

        for field in ("runtime_candidates", "model_candidates", "development_fixtures", "holdout_fixtures"):
            self.assertTrue((ROOT / evidence[field]).is_file(), field)
        self.assertEqual(evidence["verdict"], "INSUFFICIENT_LIVE_EVIDENCE")
        self.assertEqual(evidence["live_quality_runs"]["n"], 0)
        self.assertFalse(evidence["adaptive_policy"]["implemented"])
        self.assertEqual(evidence["history"]["mode"], "APPEND_ONLY")

    def test_model_profile_authority_is_rejected_even_if_field_is_injected(self):
        with (ROOT / "fixtures/v3/models/openai-compatible.json").open(encoding="utf-8") as handle:
            profile = json.load(handle)
        profile["capabilities"]["filesystem"] = True

        result = validate_instance("ModelProfile", profile)

        self.assertFalse(result.valid)


if __name__ == "__main__":
    unittest.main()
