"""Boundary tests for the Phase 3C.2 OpenCode read-only adapter."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.v3.compatibility import import_current_skill
from tools.v3.contract_validation import validate_file, validate_instance
from tools.v3.opencode_adapter import (
    OpenCodeAdapter,
    build_opencode_invocation,
    render_opencode_runtime_config,
    validate_no_ask_projection,
)
from tools.v3.opencode_native_contract import (
    INSTALLED_RELEASE_COMMIT,
    INSTALLED_RELEASE_TAG,
    INSTALLED_RUNTIME_VERSION,
    load_native_contract,
    validate_opencode_config,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
DIGEST = "sha256:" + ("0" * 64)


def load_json(relative_path: str) -> dict:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def selected_metadata(route: dict) -> list[dict]:
    return [
        import_current_skill(REGISTRY, item["skill_id"])
        for item in route["selected_skills"]
        if item["skill_id"] != "using-superpowers"
    ] + [
        import_current_skill(REGISTRY, "using-superpowers")
    ]


def h03_task() -> dict:
    task = load_json("fixtures/v3/taskspec/full.json")
    task.update(
        {
            "task_id": "T-v3-phase3c2-h03",
            "task_type": "design",
            "complexity": "COMPLEX",
            "risk": "HIGH",
            "ambiguity": "MEDIUM",
            "required_capabilities": ["needs_sandbox", "needs_structured_output"],
            "permission_requirements": {
                "level": "read-only",
                "filesystem": "read",
                "network": "none",
                "external_write": False,
                "secrets": False,
                "publish": False,
                "delete": False,
            },
            "objectives": ["Choose between two versioned API contracts from first-party constraints."],
            "acceptance_criteria": [
                "alternatives are recorded",
                "decision has verification criteria",
            ],
            "required_outputs": ["DecisionRecord"],
            "stages": ["understand", "research", "design", "review"],
        }
    )
    return task


def h03_route(task_id: str) -> dict:
    route = load_json("fixtures/v3/routes/skills-selected.json")
    route.update(
        {
            "task_id": task_id,
            "route_id": "R-v3-phase3c2-h03-design",
            "adapter": "opencode",
            "stage": "design",
            "granted_capabilities": ["sandbox", "structured_output"],
            "budget_envelope": {
                "permission_level": "read-only",
                "max_input_tokens": 8000,
                "max_output_tokens": 3000,
                "max_tool_calls": 4,
                "max_parallel_agents": 0,
            },
            "evidence_required": ["DecisionRecord", "source evidence"],
        }
    )
    return route


def no_skill_route(task_id: str) -> dict:
    route = load_json("fixtures/v3/routes/no-skill-needed.json")
    route.update(
        {
            "task_id": task_id,
            "route_id": "R-v3-phase3c2-h03-no-skill",
            "adapter": "opencode",
            "model_profile": "openai/gpt-compatible-fixture@fixture-1",
            "granted_capabilities": ["sandbox", "structured_output"],
            "evidence_required": ["DecisionRecord"],
        }
    )
    return route


class OpenCodeAdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.task = h03_task()
        self.route = h03_route(self.task["task_id"])
        self.manifest = load_json("fixtures/v3/agents/opencode.json")
        self.model = load_json("fixtures/v3/models/openai-compatible.json")
        self.metadata = selected_metadata(self.route)
        self.policy = {
            "level": "read-only",
            "filesystem": "read",
            "network": "none",
            "external_write": False,
            "secrets": False,
            "publish": False,
            "delete": False,
        }
        self.live_runtime = {
            "sandbox_mode": "read-only",
            "network_access": False,
        }
        self.artifacts = {
            "TaskSpec": {"ref": self.task["task_id"]},
            "DecisionRecord": [{"decision": "Select the versioned contract with the stable migration boundary."}],
            "Evidence": [{"name": "first-party source"}],
            "Verification": [{"name": "acceptance criteria checked"}],
        }
        self.observed_evidence = [
            {"name": "DecisionRecord"},
            {"name": "source evidence"},
        ]

    def adapter(self, **overrides) -> OpenCodeAdapter:
        values = {
            "policy": self.policy,
            "live_runtime": self.live_runtime,
        }
        values.update(overrides)
        return OpenCodeAdapter(ROOT, REGISTRY, **values)

    def compile_selected(self, **overrides):
        values = {
            "task_spec": self.task,
            "stage_route": self.route,
            "adapter_manifest": self.manifest,
            "model_profile": self.model,
            "metadata_records": self.metadata,
            "observed_evidence": self.observed_evidence,
            "reasoning_artifacts": self.artifacts,
        }
        values.update(overrides)
        return self.adapter().compile(**values)


class OpenCodeNativeContractTests(unittest.TestCase):
    def test_installed_contract_is_pinned_to_verified_release(self):
        contract = load_native_contract()
        self.assertEqual(contract["runtime_id"], "opencode")
        self.assertEqual(contract["observed_runtime_version"], INSTALLED_RUNTIME_VERSION)
        self.assertEqual(contract["release_tag"], INSTALLED_RELEASE_TAG)
        self.assertEqual(contract["release_commit"], INSTALLED_RELEASE_COMMIT)
        self.assertEqual(contract["contract_source_commit"], INSTALLED_RELEASE_COMMIT)
        self.assertEqual(contract["contract_target"], "INSTALLED_RUNTIME")

    def test_contract_fixture_validates(self):
        result = validate_file(
            "OpenCodeNativeContract",
            ROOT / "fixtures/v3/opencode/opencode-native-contract-1.18.25.json",
        )
        self.assertTrue(result.valid, result.errors)

    def test_native_config_rejects_unknown_field_and_unknown_permission(self):
        self.assertFalse(
            validate_opencode_config({"invented_native_field": "x"}).valid
        )
        self.assertFalse(
            validate_opencode_config(
                {"permission": {"unknown_permission_class": "allow"}}
            ).valid
        )

    def test_native_permission_actions_are_allow_ask_deny_only(self):
        self.assertTrue(validate_opencode_config({"permission": {"bash": "deny"}}).valid)
        self.assertFalse(validate_opencode_config({"permission": {"bash": "maybe"}}).valid)

    def test_revision_mismatch_invalidates_installed_projection(self):
        contract = load_native_contract()
        contract["release_commit"] = "stale"
        result = validate_opencode_config(
            {"permission": {"bash": "deny"}}, contract=contract
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason_code, "RUNTIME_CONTRACT_UNVERIFIED")


class OpenCodeProjectionTests(OpenCodeAdapterTestCase):
    def test_manifest_validates(self):
        result = validate_file("AgentAdapterManifest", ROOT / "fixtures/v3/agents/opencode.json")
        self.assertTrue(result.valid, result.errors)

    def test_selected_route_compiles_bundle_and_native_projection(self):
        result = self.compile_selected()
        self.assertEqual(result.status, "READY")
        self.assertEqual(result.projection["runtime_id"], "opencode")
        self.assertEqual(result.bundle["stage_route_ref"], self.route["route_id"])
        self.assertTrue(validate_instance("OpenCodeNativeProjection", result.projection).valid)

    def test_identical_inputs_produce_deterministic_bundle_and_projection(self):
        first = self.compile_selected()
        second = self.compile_selected()
        self.assertEqual(first.bundle, second.bundle)
        self.assertEqual(first.projection, second.projection)

    def test_projection_has_zero_ask_paths_and_explicit_h03_denials(self):
        result = self.compile_selected()
        config = result.projection["config"]["values"]
        serialized = json.dumps(config, sort_keys=True).lower()
        self.assertNotIn('"ask"', serialized)
        self.assertEqual(result.projection["no_ask_proof"]["no_ask"], True)
        resolved = result.projection["no_ask_proof"]["resolved_actions"]
        for name in ("read", "list", "glob", "grep"):
            self.assertEqual(resolved[name], "ALLOW")
        for name in ("edit", "bash", "task", "external_directory", "webfetch", "websearch", "skill"):
            self.assertEqual(resolved[name], "DENY")
        self.assertEqual(validate_no_ask_projection(result.projection), [])

    def test_execution_rejects_projection_with_implicit_or_ask_permission(self):
        result = self.compile_selected()
        unsafe = copy.deepcopy(result.projection)
        del unsafe["config"]["values"]["permission"]["external_directory"]
        unsafe["config"]["values"]["permission"]["bash"] = "ask"
        self.assertTrue(validate_no_ask_projection(unsafe))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                build_opencode_invocation(
                    unsafe,
                    workspace_root=temporary,
                    prompt="read one harmless file",
                )

    def test_selected_only_projection_has_refs_but_no_skill_body(self):
        result = self.compile_selected()
        projection = result.projection
        self.assertEqual(projection["skills"]["load_mode"], "selected-only")
        self.assertTrue(projection["skills"]["selected"])
        self.assertNotIn("content", json.dumps(projection))
        self.assertEqual(projection["skills"]["body_files_loaded"], 0)
        self.assertTrue(all("digest" in item for item in projection["skills"]["selected"]))

    def test_execution_local_skill_bodies_remain_available_but_result_is_public_only(self):
        result = self.compile_selected()
        self.assertTrue(any(skill.content for skill in result.execution_skills))
        public = result.to_dict()
        serialized = json.dumps(public)
        self.assertNotIn("content", serialized)
        self.assertNotIn("SKILL.md body", serialized)
        self.assertTrue(all("path" in item and "digest" in item for item in result.loaded_skills))

    def test_no_skill_needed_loads_zero_bodies_and_preserves_reason(self):
        task = copy.deepcopy(self.task)
        task["task_id"] = "T-v3-phase3c2-no-skill"
        route = no_skill_route(task["task_id"])
        result = self.compile_selected(task_spec=task, stage_route=route, metadata_records=[])
        self.assertEqual(result.status, "READY")
        self.assertEqual(result.loaded_skills, [])
        self.assertEqual(result.projection["skills"]["selected"], [])
        self.assertEqual(result.bundle["no_skill_reason"], route["no_skill_reason"])

    def test_quarantined_skill_blocks_trusted_loading(self):
        metadata = copy.deepcopy(self.metadata)
        metadata[0]["trust"] = "QUARANTINE"
        result = self.compile_selected(metadata_records=metadata)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "TRUST_REJECTED")

    def test_missing_skill_is_explicitly_blocked(self):
        route = copy.deepcopy(self.route)
        route["selected_skills"][0]["skill_id"] = "missing-opencode-skill"
        route["role_assignments"][0]["skill_id"] = "missing-opencode-skill"
        result = self.compile_selected(stage_route=route, metadata_records=[])
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "MISSING_SKILL")

    def test_permission_projection_blocks_portable_write_without_native_allow(self):
        task = copy.deepcopy(self.task)
        task["permission_requirements"]["level"] = "workspace-write"
        task["permission_requirements"]["filesystem"] = "workspace-write"
        route = copy.deepcopy(self.route)
        route["budget_envelope"]["permission_level"] = "workspace-write"
        result = self.adapter(
            policy={
                "level": "workspace-write",
                "filesystem": "workspace-write",
                "network": "none",
                "external_write": False,
                "secrets": False,
                "publish": False,
                "delete": False,
            },
            live_runtime={"sandbox_mode": "workspace-write", "network_access": False},
        ).compile(
            task_spec=task,
            stage_route=route,
            adapter_manifest=self.manifest,
            model_profile=self.model,
            metadata_records=self.metadata,
            observed_evidence=self.observed_evidence,
            reasoning_artifacts=self.artifacts,
        )
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "PERMISSION_PROJECTION")
        if result.projection:
            self.assertNotEqual(result.projection["config"]["values"].get("edit"), "allow")

    def test_unknown_permission_fails_closed(self):
        task = copy.deepcopy(self.task)
        task["permission_requirements"]["filesystem"] = "future-write"
        result = self.compile_selected(task_spec=task)
        self.assertEqual(result.status, "BLOCKED")

    def test_model_and_mcp_declarations_cannot_grant_permission(self):
        model = copy.deepcopy(self.model)
        model["capabilities"]["filesystem"] = True
        result = self.compile_selected(model_profile=model)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "INVALID_CONTRACT")

        task = copy.deepcopy(self.task)
        task["required_capabilities"] = ["needs_MCP"]
        task["permission_requirements"]["network"] = "standard"
        route = copy.deepcopy(self.route)
        route["granted_capabilities"].append("MCP")
        result = self.compile_selected(task_spec=task, stage_route=route)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "PERMISSION_INTERSECTION")

    def test_projection_has_no_plugins_or_mcp_for_h03(self):
        result = self.compile_selected()
        self.assertEqual(result.projection["plugins"], {"status": "DENY", "refs": []})
        self.assertEqual(result.projection["mcp"], {"status": "DENY", "refs": [], "schema_loaded": False})
        self.assertEqual(result.projection["config"]["values"]["plugin"], [])
        self.assertEqual(result.projection["config"]["values"]["mcp"], {})

    def test_projection_explicitly_denies_secrets_external_paths_and_shell(self):
        result = self.compile_selected()
        permission = result.projection["config"]["values"]["permission"]
        self.assertEqual(permission["external_directory"], "deny")
        self.assertEqual(permission["bash"], "deny")
        self.assertEqual(permission["read"]["*.env"], "deny")
        self.assertEqual(permission["read"]["*.env.*"], "deny")

    def test_projection_contains_no_runtime_prompt_or_raw_body(self):
        result = self.compile_selected()
        serialized = json.dumps(result.projection)
        self.assertNotIn("Choose between two versioned API contracts", serialized)
        self.assertNotIn("content", serialized)
        self.assertNotIn("chain_of_thought", serialized)

    def test_invocation_is_headless_explicit_and_rejects_auto(self):
        result = self.compile_selected()
        with tempfile.TemporaryDirectory() as temporary:
            invocation = build_opencode_invocation(
                result.projection,
                workspace_root=temporary,
                prompt="read one harmless file",
                timeout_s=30,
            )
            self.assertEqual(invocation.public["shell"], False)
            self.assertEqual(invocation.public["stdin"], "DEVNULL")
            self.assertNotIn("--auto", invocation.argv)
            self.assertNotIn("OPENCODE_CONFIG_CONTENT", json.dumps(invocation.public))
            with self.assertRaises(ValueError):
                build_opencode_invocation(
                    result.projection,
                    workspace_root=temporary,
                    prompt="read one harmless file",
                    timeout_s=30,
                    extra_args=["--auto"],
                )

    def test_runtime_config_rendering_replaces_only_ephemeral_workspace_marker(self):
        result = self.compile_selected()
        with tempfile.TemporaryDirectory() as temporary:
            rendered = json.loads(render_opencode_runtime_config(result.projection, temporary))
        self.assertNotIn("<isolated-fixture>", json.dumps(rendered))
        self.assertEqual(rendered["permission"]["external_directory"], "deny")

    def test_adapter_does_not_import_or_rerun_stage_router(self):
        source = (ROOT / "tools/v3/opencode_adapter.py").read_text(encoding="utf-8")
        self.assertNotIn("StageRouter", source)
        self.assertNotIn("route_stage", source)

    def test_projection_schema_rejects_unknown_native_fields(self):
        result = self.compile_selected()
        invalid = copy.deepcopy(result.projection)
        invalid["config"]["values"]["invented_opencode_field"] = "allow"
        self.assertFalse(validate_instance("OpenCodeNativeProjection", invalid).valid)

    def test_public_result_has_no_credentials_even_when_process_metadata_mentions_one(self):
        result = self.compile_selected()
        result.metrics["diagnostic"] = "Authorization: Bearer sk-example-secret"
        self.assertNotIn("sk-example-secret", json.dumps(result.to_dict()))


if __name__ == "__main__":
    unittest.main()
