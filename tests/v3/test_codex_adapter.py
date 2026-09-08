"""Boundary tests for the Phase 2 Codex native adapter vertical slice."""

from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path

from tools.v3.codex_adapter import CODEX_NATIVE_CONFIG_FIELDS, CodexAdapter
from tools.v3.compatibility import import_current_skill
from tools.v3.contract_validation import validate_file, validate_instance
from tools.v3.evidence_gate import evaluate_evidence
from tools.v3.execution_bundle import compile_execution_bundle, validate_bundle
from tools.v3.reasoning_artifacts import validate_reasoning_artifacts


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"


def load_json(relative_path: str) -> dict:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def current_metadata(skill_ids: list[str]) -> list[dict]:
    return [import_current_skill(REGISTRY, skill_id) for skill_id in skill_ids]


class CodexAdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.task_spec = load_json("fixtures/v3/taskspec/full.json")
        self.task_spec["task_id"] = "T-v3-phase2-codex"
        self.task_spec["permission_requirements"] = {
            "level": "workspace-write",
            "filesystem": "workspace-write",
            "network": "none",
            "external_write": False,
            "secrets": False,
            "publish": False,
            "delete": False,
        }
        self.stage_route = load_json("fixtures/v3/routes/skills-selected.json")
        self.stage_route["task_id"] = self.task_spec["task_id"]
        self.stage_route["route_id"] = "R-T-v3-phase2-codex-implement"
        self.adapter_manifest = load_json("fixtures/v3/agents/codex.json")
        self.model_profile = load_json("fixtures/v3/models/openai-compatible.json")
        self.selected_ids = [
            item["skill_id"] for item in self.stage_route["selected_skills"]
        ]
        self.metadata = current_metadata(self.selected_ids)
        self.policy = {
            "level": "workspace-write",
            "filesystem": "workspace-write",
            "network": "none",
            "external_write": False,
            "secrets": False,
            "publish": False,
            "delete": False,
        }
        self.live_runtime = {
            "sandbox_mode": "workspace-write",
            "network_access": False,
            "approval_policy": "on-request",
        }
        self.reasoning_artifacts = {
            "TaskSpec": {"ref": self.task_spec["task_id"]},
            "Assumptions": [{"statement": "The route is already validated."}],
            "Unknowns": [{"question": "Whether a later stage needs MCP."}],
            "DecisionRecord": [{"decision": "Use selected-only loading."}],
            "StagePlan": [{"stage": "implement", "objective": "Compile contracts."}],
            "Alternatives": [{"option": "Load the whole catalog", "selected": False}],
            "Evidence": [{"name": "tests"}],
            "Risk": [{"name": "permission escalation", "level": "high"}],
            "Verification": [{"name": "schema validation"}],
        }
        self.observed_evidence = [
            {"name": "tests"},
            {"name": "schema validation"},
            {"name": "diff"},
            {"name": "security review"},
        ]

    def adapter(self, **kwargs) -> CodexAdapter:
        return CodexAdapter(
            ROOT,
            REGISTRY,
            policy=kwargs.pop("policy", self.policy),
            live_runtime=kwargs.pop("live_runtime", self.live_runtime),
            **kwargs,
        )

    def compile_selected(self, **kwargs):
        return self.adapter().compile(
            task_spec=kwargs.pop("task_spec", self.task_spec),
            stage_route=kwargs.pop("stage_route", self.stage_route),
            adapter_manifest=kwargs.pop("adapter_manifest", self.adapter_manifest),
            model_profile=kwargs.pop("model_profile", self.model_profile),
            metadata_records=kwargs.pop("metadata_records", self.metadata),
            observed_evidence=kwargs.pop("observed_evidence", self.observed_evidence),
            reasoning_artifacts=kwargs.pop(
                "reasoning_artifacts", self.reasoning_artifacts
            ),
            **kwargs,
        )


class CodexAdapterVerticalSliceTests(CodexAdapterTestCase):
    def test_codex_manifest_validates(self):
        result = validate_file("AgentAdapterManifest", ROOT / "fixtures/v3/agents/codex.json")

        self.assertTrue(result.valid, result.errors)

    def test_selected_route_compiles_a_portable_bundle_and_projection(self):
        result = self.compile_selected(reasoning_effort="high")

        self.assertEqual(result.status, "READY")
        self.assertIsNone(result.reason_code)
        self.assertTrue(validate_bundle(result.bundle).valid)
        self.assertTrue(validate_instance("CodexNativeProjection", result.projection).valid)
        self.assertEqual(result.bundle["stage_route_ref"], self.stage_route["route_id"])
        self.assertEqual(result.projection["runtime_id"], "codex")

    def test_portable_bundle_direct_compile_defaults_unpassed_evidence_to_degraded(self):
        bundle = compile_execution_bundle(
            task_spec=self.task_spec,
            stage_route=self.stage_route,
            adapter_manifest=self.adapter_manifest,
            model_profile=self.model_profile,
            selected_skills=[],
            effective_capabilities=["editing", "sandbox", "structured_output"],
            permission_envelope={"level": "workspace-write"},
            context={
                "static_prefix": "stable",
                "dynamic_context": "lazy",
                "tool_schema_context": "tracked",
                "artifact_refs": [],
            },
            reasoning_artifact_refs=["TaskSpec:T-v3-phase2-codex"],
            evidence_required=self.stage_route["evidence_required"],
            provenance={"registry_epoch": self.stage_route["registry_epoch"]},
        )

        self.assertEqual(bundle["status"], "DEGRADED")
        self.assertTrue(validate_bundle(bundle).valid)

    def test_identical_inputs_produce_deterministic_bundle_and_projection(self):
        first = self.compile_selected(reasoning_effort="high")
        second = self.compile_selected(reasoning_effort="high")

        self.assertEqual(first.bundle, second.bundle)
        self.assertEqual(first.projection, second.projection)
        self.assertEqual(first.bundle["bundle_digest"], second.bundle["bundle_digest"])

    def test_selected_only_loading_preserves_resident_authority_and_loads_three_bodies(self):
        result = self.compile_selected()

        self.assertEqual(
            {item["skill_id"] for item in result.loaded_skills}, set(self.selected_ids)
        )
        resident = next(
            item for item in result.loaded_skills if item["skill_id"] == "using-superpowers"
        )
        self.assertEqual(resident["load_state"], "RESIDENT")
        self.assertEqual(resident["content"], "")
        self.assertEqual(result.metrics["metadata_records_inspected"], 4)
        self.assertEqual(result.metrics["registry_records_seen"], 0)
        self.assertEqual(result.metrics["source_files_verified"], 4)
        self.assertEqual(result.metrics["skill_md_files_loaded"], 3)
        self.assertGreater(result.metrics["loaded_bytes"], 0)
        self.assertEqual(
            {item["skill_id"] for item in result.projection["skills"]["selected"]},
            set(self.selected_ids),
        )

    def test_unrelated_skill_body_never_enters_generated_projection(self):
        result = self.compile_selected()
        projection_text = json.dumps(result.projection, sort_keys=True)

        self.assertNotIn("understand/SKILL.md", projection_text)
        self.assertNotIn(
            "understand",
            {item["skill_id"] for item in result.projection["skills"]["selected"]},
        )
        self.assertNotIn("content", result.projection)

    def test_canonical_skill_digests_are_preserved(self):
        result = self.compile_selected()
        expected = {
            record["skill_id"]: record["source"]["digest"] for record in self.metadata
        }

        actual = {
            item["skill_id"]: item["digest"] for item in result.bundle["selected_skills"]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(
            sorted(actual.values()), result.projection["provenance"]["selected_skill_digests"]
        )

    def test_changed_canonical_digest_invalidates_projection(self):
        metadata = copy.deepcopy(self.metadata)
        metadata[0]["source"]["digest"] = "sha256:" + ("0" * 64)

        result = self.compile_selected(metadata_records=metadata)

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "DIGEST_MISMATCH")
        self.assertIsNone(result.bundle)

    def test_quarantined_skill_blocks_trusted_loading(self):
        metadata = copy.deepcopy(self.metadata)
        metadata[0]["trust"] = "QUARANTINE"

        result = self.compile_selected(metadata_records=metadata)

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "TRUST_REJECTED")
        self.assertIsNone(result.projection)

    def test_missing_skill_returns_explicit_blocked_result(self):
        route = copy.deepcopy(self.stage_route)
        route["selected_skills"][0]["skill_id"] = "skill-not-in-current-registry"
        route["role_assignments"][0]["skill_id"] = "skill-not-in-current-registry"

        result = self.compile_selected(stage_route=route, metadata_records=[])

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "MISSING_SKILL")
        self.assertTrue(any("skill-not-in-current-registry" in error for error in result.errors))

    def test_capability_mismatch_is_explicit(self):
        task = copy.deepcopy(self.task_spec)
        task["required_capabilities"].append("needs_browser")
        route = copy.deepcopy(self.stage_route)
        route["granted_capabilities"].append("browser")

        result = self.compile_selected(task_spec=task, stage_route=route)

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "CAPABILITY_MISMATCH")
        self.assertTrue(any("adapter:browser" in error for error in result.errors))

    def test_unknown_required_capability_is_blocked_by_adapter(self):
        task = copy.deepcopy(self.task_spec)
        task["required_capabilities"].append("needs_future_capability")

        result = self.compile_selected(task_spec=task)

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "CAPABILITY_MISMATCH")
        self.assertTrue(any("unknown:needs_future_capability" in error for error in result.errors))

    def test_permission_cannot_escalate_task_spec(self):
        route = copy.deepcopy(self.stage_route)
        route["budget_envelope"]["permission_level"] = "external-write"

        result = self.compile_selected(stage_route=route)

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "PERMISSION_INTERSECTION")
        self.assertTrue(any("cannot exceed TaskSpec" in error for error in result.errors))

    def test_permission_cannot_exceed_runtime_policy(self):
        policy = copy.deepcopy(self.policy)
        policy.update(level="read-only", filesystem="read")

        result = self.adapter(policy=policy).compile(
            task_spec=self.task_spec,
            stage_route=self.stage_route,
            adapter_manifest=self.adapter_manifest,
            model_profile=self.model_profile,
            metadata_records=self.metadata,
            observed_evidence=self.observed_evidence,
            reasoning_artifacts=self.reasoning_artifacts,
        )

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "PERMISSION_INTERSECTION")
        self.assertTrue(any("intersection read-only" in error for error in result.errors))

    def test_projection_sandbox_cannot_exceed_effective_permission(self):
        result = self.adapter(
            live_runtime={
                "sandbox_mode": "danger-full-access",
                "network_access": False,
                "approval_policy": "never",
            }
        ).compile(
            task_spec=self.task_spec,
            stage_route=self.stage_route,
            adapter_manifest=self.adapter_manifest,
            model_profile=self.model_profile,
            metadata_records=self.metadata,
            observed_evidence=self.observed_evidence,
            reasoning_artifacts=self.reasoning_artifacts,
        )

        self.assertEqual(result.status, "READY")
        self.assertEqual(
            result.bundle["permission_envelope"]["filesystem"], "workspace-write"
        )
        self.assertEqual(result.projection["config"]["values"]["sandbox_mode"], "workspace-write")
        self.assertNotIn("approval_policy", result.projection["config"]["values"])

    def test_model_profile_cannot_grant_os_permission(self):
        model = copy.deepcopy(self.model_profile)
        model["capabilities"]["tool_use"] = True
        read_only_policy = {"level": "read-only", "filesystem": "read", "network": "none"}
        read_only_live = {"sandbox_mode": "read-only", "network_access": False}

        result = self.adapter(policy=read_only_policy, live_runtime=read_only_live).compile(
            task_spec=self.task_spec,
            stage_route=self.stage_route,
            adapter_manifest=self.adapter_manifest,
            model_profile=model,
            metadata_records=self.metadata,
            observed_evidence=self.observed_evidence,
            reasoning_artifacts=self.reasoning_artifacts,
        )

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "PERMISSION_INTERSECTION")

    def test_skill_metadata_cannot_widen_effective_permission(self):
        metadata = copy.deepcopy(self.metadata)
        metadata[0]["permissions"] = {"filesystem": "external-write"}

        result = self.compile_selected(metadata_records=metadata)

        self.assertEqual(result.status, "READY")
        self.assertEqual(
            result.bundle["permission_envelope"]["filesystem"], "workspace-write"
        )

    def test_mcp_declaration_cannot_grant_permission(self):
        task = copy.deepcopy(self.task_spec)
        task["required_capabilities"].append("needs_MCP")
        task["permission_requirements"]["network"] = "standard"
        route = copy.deepcopy(self.stage_route)
        route["granted_capabilities"].append("MCP")
        manifest = copy.deepcopy(self.adapter_manifest)
        manifest["mcp"]["server_refs"] = ["server-declared-but-not-authorized"]

        result = self.compile_selected(
            task_spec=task, stage_route=route, adapter_manifest=manifest
        )

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "PERMISSION_INTERSECTION")
        self.assertTrue(any("network" in error for error in result.errors))

    def test_hidden_chain_of_thought_field_is_rejected(self):
        artifacts = copy.deepcopy(self.reasoning_artifacts)
        artifacts["DecisionRecord"][0]["chain_of_thought"] = "private trace"

        result = self.compile_selected(reasoning_artifacts=artifacts)

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "HIDDEN_REASONING_FIELD")
        self.assertTrue(validate_reasoning_artifacts(artifacts))

    def test_evidence_failure_blocks_and_emits_reroute_artifact(self):
        result = self.compile_selected(observed_evidence=[])

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "EVIDENCE_MISSING")
        self.assertEqual(result.evidence["status"], "BLOCKED")
        self.assertEqual(result.bundle["status"], "BLOCKED")
        self.assertEqual(
            result.bundle["evidence_gate"]["reroute"]["trigger"], "evidence_failure"
        )
        self.assertEqual(result.bundle["evidence_gate"]["reroute"]["next_stage"], "verify")

    def test_no_skill_needed_loads_no_additional_skill(self):
        task = load_json("fixtures/v3/taskspec/minimal.json")
        task["task_id"] = "T-v3-phase2-codex-handoff"
        route = load_json("fixtures/v3/routes/no-skill-needed.json")
        route["task_id"] = task["task_id"]
        route["route_id"] = "R-T-v3-phase2-codex-handoff"

        result = self.adapter(
            policy={"level": "read-only", "filesystem": "read", "network": "none"},
            live_runtime={"sandbox_mode": "read-only", "network_access": False},
        ).compile(
            task_spec=task,
            stage_route=route,
            adapter_manifest=self.adapter_manifest,
            model_profile=self.model_profile,
            metadata_records=[],
            observed_evidence=[{"name": "handoff summary"}],
            reasoning_artifacts={},
        )

        self.assertEqual(result.status, "READY")
        self.assertEqual(result.loaded_skills, [])
        self.assertEqual(result.bundle["selected_skills"], [])
        self.assertEqual(result.bundle["no_skill_reason"], route["no_skill_reason"])
        self.assertEqual(result.projection["skills"]["selected"], [])

    def test_portable_bundle_contains_no_codex_branch_logic(self):
        source = (ROOT / "tools/v3/execution_bundle.py").read_text(encoding="utf-8")

        self.assertNotIn("CodexAdapter", source)
        self.assertNotRegex(source, re.compile(r"if\s+[^\n]*codex", re.IGNORECASE))
        self.assertNotIn("codex-native", source)

    def test_adapter_consumes_route_without_importing_a_general_router(self):
        source = (ROOT / "tools/v3/codex_adapter.py").read_text(encoding="utf-8")

        self.assertNotIn("StageRouter", source)
        self.assertNotIn("route_skills", source)

    def test_projection_config_contains_only_verified_codex_fields(self):
        result = self.compile_selected(reasoning_effort="high")

        config_keys = set(result.projection["config"]["values"])
        self.assertTrue(config_keys <= CODEX_NATIVE_CONFIG_FIELDS)
        self.assertNotIn("invented_codex_setting", config_keys)

        invalid_projection = copy.deepcopy(result.projection)
        invalid_projection["config"]["values"]["invented_codex_setting"] = True
        validation = validate_instance("CodexNativeProjection", invalid_projection)
        self.assertFalse(validation.valid)

    def test_unsupported_model_reasoning_is_an_explicit_projection_block(self):
        model = copy.deepcopy(self.model_profile)
        model["reasoning"]["supported"] = False

        result = self.compile_selected(model_profile=model, reasoning_effort="high")

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "PROJECTION_UNSUPPORTED")
        self.assertTrue(any("reasoning support" in error for error in result.errors))

    def test_agents_file_remains_a_bounded_bootstrap(self):
        agents = ROOT / "AGENTS.md"

        self.assertLess(len(agents.read_text(encoding="utf-8").splitlines()), 200)
        self.assertNotIn("chain_of_thought", agents.read_text(encoding="utf-8"))

    def test_checked_in_bundle_fixtures_validate_shape_and_digest(self):
        for path in sorted((ROOT / "fixtures/v3/bundles").glob("*.json")):
            with self.subTest(bundle=path.name):
                with path.open(encoding="utf-8") as handle:
                    bundle = json.load(handle)
                result = validate_bundle(bundle)
                self.assertTrue(result.valid, result.errors)

    def test_checked_in_codex_projection_fixtures_validate(self):
        for path in sorted((ROOT / "fixtures/v3/projections").glob("*.json")):
            with self.subTest(projection=path.name):
                result = validate_file("CodexNativeProjection", path)
                self.assertTrue(result.valid, result.errors)

    def test_checked_in_evidence_failure_fixture_matches_gate(self):
        expected = load_json("fixtures/v3/evidence/evidence-failed.json")
        actual = evaluate_evidence(self.stage_route["evidence_required"], [])

        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
