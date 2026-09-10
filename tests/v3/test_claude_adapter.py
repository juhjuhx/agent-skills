"""Boundary tests for the Claude Code benchmark-safe read-only adapter."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.v3.claude_adapter import (
    CLAUDE_READ_ONLY_TOOLS,
    ClaudeAdapter,
    build_claude_invocation,
    validate_no_ask_projection,
)
from tools.v3.claude_native_contract import (
    INSTALLED_RUNTIME_VERSION,
    load_native_contract,
    validate_claude_config,
)
from tools.v3.compatibility import import_current_skill
from tools.v3.contract_validation import validate_file, validate_instance
from tools.v3.execution_bundle import validate_bundle
from tools.v3.live_benchmark import ProcessObservation
from tools.v3.skill_resolver import LoadedSkill


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"


def load_json(relative_path: str) -> dict:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def h03_task() -> dict:
    task = load_json("fixtures/v3/taskspec/full.json")
    task.update(
        {
            "task_id": "T-v3-phase3d-h03",
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
            "objectives": [
                "Choose between two versioned API contracts from first-party constraints."
            ],
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
            "route_id": "R-v3-phase3d-h03-design",
            "adapter": "claude-code",
            "stage": "design",
            "model_profile": "anthropic/claude-compatible-fixture@fixture-1.0",
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
            "route_id": "R-v3-phase3d-no-skill",
            "adapter": "claude-code",
            "model_profile": "anthropic/claude-compatible-fixture@fixture-1.0",
            "granted_capabilities": ["sandbox", "structured_output"],
            "evidence_required": ["DecisionRecord"],
        }
    )
    return route


class ClaudeAdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.task = h03_task()
        self.route = h03_route(self.task["task_id"])
        self.manifest = load_json("fixtures/v3/agents/claude-code.json")
        self.model = load_json("fixtures/v3/models/anthropic-compatible.json")
        self.metadata = [
            import_current_skill(REGISTRY, item["skill_id"])
            for item in self.route["selected_skills"]
        ]
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
            "DecisionRecord": [{"decision": "Use the versioned boundary."}],
            "Evidence": [{"name": "first-party source"}],
            "Verification": [{"name": "acceptance criteria checked"}],
        }
        self.observed_evidence = [
            {"name": "DecisionRecord"},
            {"name": "source evidence"},
        ]

    def adapter(self, **overrides) -> ClaudeAdapter:
        values = {
            "policy": self.policy,
            "live_runtime": self.live_runtime,
        }
        values.update(overrides)
        return ClaudeAdapter(ROOT, REGISTRY, **values)

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


class ClaudeNativeContractTests(unittest.TestCase):
    def test_installed_contract_fixture_validates(self):
        result = validate_file(
            "ClaudeNativeContract",
            ROOT / "fixtures/v3/claude/claude-native-contract-2.1.235.json",
        )
        self.assertTrue(result.valid, result.errors)

    def test_installed_contract_is_bound_to_observed_cli_version(self):
        contract = load_native_contract()
        self.assertEqual(contract["runtime_id"], "claude-code")
        self.assertEqual(contract["observed_runtime_version"], INSTALLED_RUNTIME_VERSION)
        self.assertEqual(contract["contract_target"], "INSTALLED_RUNTIME")
        self.assertEqual(contract["availability"], "INSTALLED")

    def test_native_config_rejects_unknown_field_and_value(self):
        self.assertFalse(validate_claude_config({"invented": True}).valid)
        self.assertFalse(
            validate_claude_config({"permission_mode": "not-a-native-mode"}).valid
        )
        self.assertTrue(
            validate_claude_config(
                {
                    "permission_mode": "dontAsk",
                    "tools": list(CLAUDE_READ_ONLY_TOOLS),
                }
            ).valid
        )

    def test_unknown_installed_version_fails_closed(self):
        result = validate_claude_config(
            {"permission_mode": "dontAsk"},
            observed_runtime_version="2.1.236",
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason_code, "RUNTIME_CONTRACT_UNVERIFIED")

    def test_installed_contract_does_not_claim_unverified_max_turns_flag(self):
        contract = load_native_contract()
        self.assertNotIn("max_turns", contract["fields"])


class ClaudeProjectionTests(ClaudeAdapterTestCase):
    def test_manifest_validates(self):
        result = validate_file(
            "AgentAdapterManifest", ROOT / "fixtures/v3/agents/claude-code.json"
        )
        self.assertTrue(result.valid, result.errors)

    def test_selected_route_compiles_bundle_and_projection(self):
        result = self.compile_selected()
        self.assertEqual(result.status, "READY")
        self.assertTrue(validate_bundle(result.bundle).valid)
        self.assertTrue(validate_instance("ClaudeNativeProjection", result.projection).valid)
        self.assertEqual(result.projection["runtime_id"], "claude-code")

    def test_identical_inputs_are_deterministic(self):
        first = self.compile_selected()
        second = self.compile_selected()
        self.assertEqual(first.bundle, second.bundle)
        self.assertEqual(first.projection, second.projection)

    def test_projection_uses_zero_ask_read_only_surface(self):
        result = self.compile_selected()
        self.assertEqual(validate_no_ask_projection(result.projection), [])
        config = result.projection["config"]["values"]
        self.assertEqual(config["permission_mode"], "dontAsk")
        self.assertEqual(config["tools"], list(CLAUDE_READ_ONLY_TOOLS))
        self.assertEqual(config["allowed_tools"], list(CLAUDE_READ_ONLY_TOOLS))
        self.assertTrue(config["safe_mode"])
        self.assertTrue(config["no_session_persistence"])
        self.assertTrue(config["no_chrome"])
        self.assertTrue(config["strict_mcp_config"])
        self.assertEqual(config["mcp_config"], '{"mcpServers":{}}')

    def test_projection_has_no_raw_skill_body_or_model_routing_logic(self):
        result = self.compile_selected()
        serialized = json.dumps(result.projection)
        self.assertNotIn("content", serialized)
        self.assertNotIn("Choose between two versioned", serialized)
        self.assertNotIn("chain_of_thought", serialized)
        self.assertNotIn("if model", serialized)
        self.assertNotIn("model_id", result.projection["config"]["values"])

    def test_selected_only_bodies_are_execution_local(self):
        result = self.compile_selected()
        self.assertTrue(any(skill.content for skill in result.execution_skills))
        self.assertTrue(result.projection["skills"]["selected"])
        self.assertEqual(result.projection["skills"]["body_files_loaded"], 0)
        self.assertNotIn("content", json.dumps(result.to_dict()))
        self.assertTrue(all("digest" in item for item in result.loaded_skills))

    def test_no_skill_route_loads_zero_bodies_and_preserves_reason(self):
        task = copy.deepcopy(self.task)
        task["task_id"] = "T-v3-phase3d-no-skill"
        route = no_skill_route(task["task_id"])
        result = self.compile_selected(
            task_spec=task,
            stage_route=route,
            metadata_records=[],
        )
        self.assertEqual(result.status, "READY")
        self.assertEqual(result.execution_skills, ())
        self.assertEqual(result.projection["skills"]["selected"], [])
        self.assertEqual(result.bundle["no_skill_reason"], route["no_skill_reason"])

    def test_write_request_never_becomes_native_write_allow(self):
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

    def test_model_and_mcp_declarations_cannot_grant_authority(self):
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

    def test_unknown_observed_runtime_version_blocks_projection(self):
        result = self.adapter(observed_runtime_version="2.1.236").compile(
            task_spec=self.task,
            stage_route=self.route,
            adapter_manifest=self.manifest,
            model_profile=self.model,
            metadata_records=self.metadata,
            observed_evidence=self.observed_evidence,
            reasoning_artifacts=self.artifacts,
        )
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "RUNTIME_CONTRACT_UNVERIFIED")

    def test_adapter_does_not_invoke_stage_router(self):
        source = (ROOT / "tools/v3/claude_adapter.py").read_text(encoding="utf-8")
        self.assertNotIn("StageRouter", source)
        self.assertNotIn("route_stage", source)


class ClaudeInvocationTests(ClaudeAdapterTestCase):
    def test_invocation_is_headless_and_has_no_bypass(self):
        result = self.compile_selected()
        with tempfile.TemporaryDirectory() as temporary:
            invocation = build_claude_invocation(
                result.projection,
                workspace_root=temporary,
                prompt="read one harmless file",
                timeout_s=30,
            )
        self.assertEqual(invocation.public["shell"], False)
        self.assertEqual(invocation.public["stdin"], "DEVNULL")
        self.assertNotIn("--bare", invocation.argv)
        self.assertNotIn("--dangerously-skip-permissions", invocation.argv)
        self.assertNotIn("--allow-dangerously-skip-permissions", invocation.argv)
        self.assertNotIn("--auto", invocation.argv)
        self.assertNotIn("--max-turns", invocation.argv)
        self.assertNotIn("append_system_prompt", json.dumps(invocation.public))

    def test_smoke_a_can_override_tools_to_empty_without_widening_projection(self):
        result = self.compile_selected()
        with tempfile.TemporaryDirectory() as temporary:
            invocation = build_claude_invocation(
                result.projection,
                workspace_root=temporary,
                prompt="return one exact bounded value",
                timeout_s=15,
                tools_override=(),
            )
        self.assertEqual(invocation.public["tools"], [])
        self.assertEqual(invocation.public["allowed_tools"], [])
        self.assertIn("--tools", invocation.argv)
        self.assertIn("", invocation.argv)
        self.assertEqual(validate_no_ask_projection(result.projection), [])

    def test_unsafe_projection_is_rejected_before_execution(self):
        result = self.compile_selected()
        unsafe = copy.deepcopy(result.projection)
        unsafe["config"]["values"]["permission_mode"] = "plan"
        unsafe["config"]["values"]["tools"] = ["Bash"]
        self.assertTrue(validate_no_ask_projection(unsafe))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                build_claude_invocation(
                    unsafe,
                    workspace_root=temporary,
                    prompt="return one exact bounded value",
                )

    def test_execution_instructions_are_ephemeral_and_digest_only_in_public_data(self):
        result = self.compile_selected()
        with tempfile.TemporaryDirectory() as temporary:
            with patch("tools.v3.claude_adapter.run_headless_command") as runner:
                runner.return_value = ProcessObservation(True, 0, False, 1.0, "{}", "")
                observation = self.adapter().execute(
                    result.projection,
                    workspace_root=temporary,
                    prompt="return one exact bounded value",
                    execution_skills=result.execution_skills,
                )
                invocation = runner.call_args.args[0]
                public = build_claude_invocation(
                    result.projection,
                    workspace_root=temporary,
                    prompt="return one exact bounded value",
                    execution_instructions="private procedure text",
                ).public
        self.assertEqual(observation.returncode, 0)
        self.assertIn("--append-system-prompt", invocation)
        self.assertNotIn("private procedure text", json.dumps(public))
        self.assertIn("execution_instruction_digest", public)

    def test_execution_rejects_unselected_or_digest_mismatched_skill_body(self):
        result = self.compile_selected()
        selected = result.execution_skills[0]
        unselected = LoadedSkill(
            skill_id="unselected-skill",
            source_path=selected.source_path,
            source_ref=selected.source_ref,
            digest=selected.digest,
            role=selected.role,
            content=selected.content,
            load_state="LOADED",
        )
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                self.adapter().execute(
                    result.projection,
                    workspace_root=temporary,
                    prompt="return one exact bounded value",
                    execution_skills=(unselected,),
                )
        mismatched = LoadedSkill(
            skill_id=selected.skill_id,
            source_path=selected.source_path,
            source_ref=selected.source_ref,
            digest=selected.digest,
            role=selected.role,
            content="tampered procedure",
            load_state="LOADED",
        )
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                self.adapter().execute(
                    result.projection,
                    workspace_root=temporary,
                    prompt="return one exact bounded value",
                    execution_skills=(mismatched,),
                )


if __name__ == "__main__":
    unittest.main()
