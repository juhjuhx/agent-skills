"""Deterministic, metadata-first tests for the v3 stage router MVP."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.v3.compatibility import import_current_skill, load_current_registry
from tools.v3.contract_validation import validate_instance
from tools.v3.stage_router import RoutingError, StageRouter, route_stage


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
DIGEST = "sha256:" + ("0" * 64)


def metadata(
    skill_id: str,
    *,
    roles: list[str] | None = None,
    stages: list[str] | None = None,
    task_modes: list[str] | None = None,
    domains: list[str] | None = None,
    description: str | None = None,
    triggers: list[str] | None = None,
    trust: str = "CORE_TRUSTED",
    capabilities: list[str] | None = None,
    tools: list[str] | None = None,
    permissions: dict | None = None,
    relationships: list[dict] | None = None,
    context_cost: dict | None = None,
    runtime_cost: dict | None = None,
    compatibility: list[dict] | None = None,
    extension: dict | None = None,
) -> dict:
    record = {
        "schema_version": "3.0",
        "skill_id": skill_id,
        "name": skill_id,
        "description": description or f"{skill_id} procedure",
        "source": {
            "repo": "https://example.invalid/canonical-skills",
            "ref": "test-ref",
            "path": f"skills/{skill_id}/SKILL.md",
            "digest": DIGEST,
        },
        "trust": trust,
    }
    for key, value in {
        "roles": roles,
        "stages": stages,
        "task_modes": task_modes,
        "domains": domains,
        "triggers": triggers,
        "required_capabilities": capabilities,
        "tools": tools,
        "permissions": permissions,
        "relationships": relationships,
        "context_cost": context_cost,
        "runtime_cost": runtime_cost,
        "agent_compatibility": compatibility,
    }.items():
        if value is not None:
            record[key] = value
    if extension:
        record["extensions"] = extension
    return record


def task(
    task_id: str = "T-router-test",
    *,
    task_type: str = "implementation",
    goal: str = "Implement a bounded change",
    complexity: str = "STANDARD",
    risk: str = "LOW",
    ambiguity: str = "LOW",
    architecture_impact: str = "LOCAL",
    objectives: list[str] | None = None,
    domains: list[str] | None = None,
    required_capabilities: list[str] | None = None,
    permissions: dict | None = None,
    context_budget: dict | None = None,
    cost_budget: dict | None = None,
    latency_budget: dict | None = None,
    artifact_requirements: list[str] | None = None,
) -> dict:
    result = {
        "schema_version": "3.0",
        "task_id": task_id,
        "task_type": task_type,
        "goal": goal,
        "complexity": complexity,
        "risk": risk,
        "ambiguity": ambiguity,
        "architecture_impact": architecture_impact,
        "objectives": objectives or [goal],
    }
    optional = {
        "domains": domains,
        "required_capabilities": required_capabilities,
        "permission_requirements": permissions,
        "context_budget": context_budget,
        "cost_budget": cost_budget,
        "latency_budget": latency_budget,
        "artifact_requirements": artifact_requirements,
    }
    result.update({key: value for key, value in optional.items() if value is not None})
    return result


def stage(
    stage_id: str = "implement",
    *,
    objective: str = "Implement the bounded change",
    task_type: str = "implementation",
    domains: list[str] | None = None,
    required_outputs: list[str] | None = None,
    evidence_required: list[str] | None = None,
    required_roles: list[str] | None = None,
    required_capabilities: list[str] | None = None,
    required_tools: list[str] | None = None,
) -> dict:
    result = {
        "id": stage_id,
        "objective": objective,
        "task_type": task_type,
        "domains": domains or [],
        "required_outputs": required_outputs or [],
        "evidence_required": evidence_required or [],
    }
    optional = {
        "required_roles": required_roles,
        "required_capabilities": required_capabilities,
        "required_tools": required_tools,
    }
    result.update({key: value for key, value in optional.items() if value is not None})
    return result


class StageRouterContractTests(unittest.TestCase):
    def test_route_is_deterministic_and_validates(self):
        catalog = [
            metadata("implementer", roles=["PROCESS"], stages=["implement"]),
            metadata(
                "verifier",
                roles=["VERIFY"],
                stages=["verify"],
                description="verify tests",
            ),
        ]
        first = route_stage(
            task(task_id="T-deterministic", artifact_requirements=["tests"]),
            stage("implement", evidence_required=["tests"]),
            catalog,
        )
        second = route_stage(
            task(task_id="T-deterministic", artifact_requirements=["tests"]),
            stage("implement", evidence_required=["tests"]),
            catalog,
        )

        self.assertEqual(first, second)
        validation = validate_instance("StageRoute", first)
        self.assertTrue(validation.valid, validation.errors)

    def test_quarantined_skill_is_filtered_before_scoring(self):
        route = route_stage(
            task(),
            stage("implement"),
            [metadata("unsafe", roles=["PROCESS"], trust="QUARANTINE")],
        )

        self.assertEqual(route["status"], "NO_SKILL_NEEDED")
        rejected = route["routing_evidence"]["rejected_candidates"]
        self.assertTrue(any(item["skill_id"] == "unsafe" for item in rejected))
        self.assertIn("trust", " ".join(route["route_reasons"]).lower())

    def test_conflicting_skills_are_not_co_selected(self):
        catalog = [
            metadata(
                "primary",
                roles=["PROCESS"],
                stages=["implement"],
                description="implement feature",
                relationships=[{"type": "CONFLICTS", "target": "rival"}],
            ),
            metadata(
                "rival",
                roles=["PROCESS"],
                stages=["implement"],
                description="implement feature rival",
            ),
        ]
        route = route_stage(task(goal="implement feature"), stage(), catalog)
        selected = {item["skill_id"] for item in route["selected_skills"]}

        self.assertLessEqual(len(selected & {"primary", "rival"}), 1)
        self.assertIn(
            "CONFLICTS", " ".join(route["routing_evidence"]["relationship_effects"])
        )

    def test_superseded_skill_loses_to_successor(self):
        catalog = [
            metadata(
                "successor",
                roles=["PROCESS"],
                stages=["implement"],
                description="implement feature successor",
                relationships=[{"type": "SUPERSEDES", "target": "legacy"}],
            ),
            metadata(
                "legacy",
                roles=["PROCESS"],
                stages=["implement"],
                description="implement feature legacy",
            ),
        ]
        route = route_stage(task(goal="implement feature"), stage(), catalog)
        selected = {item["skill_id"] for item in route["selected_skills"]}

        self.assertIn("successor", selected)
        self.assertNotIn("legacy", selected)

    def test_required_dependency_is_added(self):
        catalog = [
            metadata(
                "primary",
                roles=["PROCESS"],
                stages=["implement"],
                description="implement feature",
                relationships=[{"type": "REQUIRES", "target": "dependency"}],
            ),
            metadata(
                "dependency",
                roles=["TOOL"],
                stages=["implement"],
                description="feature tool",
            ),
        ]
        route = route_stage(task(goal="implement feature"), stage(), catalog)
        selected = {item["skill_id"] for item in route["selected_skills"]}

        self.assertIn("primary", selected)
        self.assertIn("dependency", selected)
        self.assertIn(
            "REQUIRES", " ".join(route["routing_evidence"]["relationship_effects"])
        )

    def test_alternative_skills_do_not_both_win_by_default(self):
        catalog = [
            metadata(
                "one",
                roles=["PROCESS"],
                stages=["implement"],
                description="implement feature one",
                relationships=[{"type": "ALTERNATIVE_TO", "target": "two"}],
            ),
            metadata(
                "two",
                roles=["PROCESS"],
                stages=["implement"],
                description="implement feature two",
            ),
        ]
        route = route_stage(task(goal="implement feature"), stage(), catalog)
        selected = {item["skill_id"] for item in route["selected_skills"]}

        self.assertLessEqual(len(selected & {"one", "two"}), 1)

    def test_role_coverage_prefers_a_complement_over_top_review_duplicates(self):
        catalog = [
            metadata(
                "review-a",
                roles=["REVIEW"],
                stages=["implement", "review"],
                description="review implementation",
            ),
            metadata(
                "review-b",
                roles=["REVIEW"],
                stages=["implement", "review"],
                description="review implementation quality",
            ),
            metadata(
                "process",
                roles=["PROCESS"],
                stages=["implement"],
                description="implement change",
            ),
            metadata(
                "verify",
                roles=["VERIFY"],
                stages=["implement", "verify"],
                description="verify tests",
            ),
        ]
        route = route_stage(
            task(goal="implement and review change", artifact_requirements=["tests"]),
            stage(
                "implement",
                objective="implement and review change",
                evidence_required=["tests"],
                required_roles=["PROCESS", "REVIEW", "VERIFY"],
            ),
            catalog,
        )
        roles = {item["role"] for item in route["role_assignments"]}

        self.assertTrue({"PROCESS", "REVIEW", "VERIFY"}.issubset(roles))
        self.assertLessEqual(route["routing_evidence"]["duplicate_role_pressure"], 1)

    def test_simple_tiny_task_can_return_no_skill_needed(self):
        route = route_stage(
            task(
                task_id="T-readme-typo",
                task_type="documentation",
                goal="Fix one README typo",
                complexity="SIMPLE",
                risk="LOW",
                ambiguity="LOW",
                objectives=["Fix one README typo"],
            ),
            stage(
                "implement", objective="Fix one README typo", task_type="documentation"
            ),
            [
                metadata(
                    "architecture-audit",
                    roles=["REVIEW"],
                    stages=["review"],
                    domains=["architecture"],
                ),
                metadata(
                    "security",
                    roles=["REVIEW"],
                    stages=["harden"],
                    domains=["security"],
                ),
            ],
        )

        self.assertEqual(route["status"], "NO_SKILL_NEEDED")
        self.assertIn("trivial", route["no_skill_reason"].lower())

    def test_complex_task_gets_multi_role_coverage_without_fixed_quota(self):
        catalog = [
            metadata(
                "process",
                roles=["PROCESS"],
                stages=["design", "implement"],
                description="implement API",
            ),
            metadata(
                "domain",
                roles=["DOMAIN"],
                stages=["design"],
                domains=["api"],
                description="API architecture",
            ),
            metadata(
                "review",
                roles=["REVIEW"],
                stages=["design", "review"],
                description="review API design",
            ),
            metadata(
                "verify",
                roles=["VERIFY"],
                stages=["design", "verify"],
                description="verify API contract",
            ),
        ]
        route = route_stage(
            task(
                task_id="T-complex",
                goal="Design and implement a complex API architecture",
                complexity="COMPLEX",
                risk="HIGH",
                ambiguity="HIGH",
                architecture_impact="ARCHITECTURE-CHANGING",
                domains=["api", "architecture"],
                artifact_requirements=["tests", "verification"],
            ),
            stage(
                "design",
                objective="Design and implement a complex API architecture",
                domains=["api", "architecture"],
                evidence_required=["tests", "verification"],
                required_roles=["PROCESS", "DOMAIN", "REVIEW", "VERIFY"],
            ),
            catalog,
        )
        roles = {item["role"] for item in route["role_assignments"]}

        self.assertEqual(route["status"], "SKILLS_SELECTED")
        self.assertTrue({"PROCESS", "DOMAIN", "REVIEW", "VERIFY"}.issubset(roles))
        self.assertGreaterEqual(route["routing_evidence"]["selected_count"], 4)

    def test_security_skill_is_conditional(self):
        security = metadata(
            "safe-mode",
            roles=["REVIEW"],
            stages=["harden", "review"],
            domains=["security"],
            description="security hardening and permission lockdown",
        )
        secure_route = route_stage(
            task(
                task_id="T-secure",
                task_type="implementation",
                goal="Harden the permission boundary for a security-sensitive change",
                risk="HIGH",
                domains=["security"],
            ),
            stage(
                "harden",
                objective="Harden the permission boundary",
                domains=["security"],
                required_roles=["REVIEW"],
            ),
            [security],
        )
        normal_route = route_stage(
            task(goal="Add a normal documentation example", task_type="documentation"),
            stage("implement"),
            [security],
        )

        self.assertIn(
            "safe-mode", {item["skill_id"] for item in secure_route["selected_skills"]}
        )
        self.assertNotIn(
            "safe-mode", {item["skill_id"] for item in normal_route["selected_skills"]}
        )

    def test_mcp_skill_is_conditional(self):
        mcp = metadata(
            "mcp-audit",
            roles=["TOOL", "REVIEW"],
            stages=["research", "review"],
            domains=["mcp"],
            description="audit MCP server tool schemas and context cost",
            capabilities=["needs_MCP"],
        )
        mcp_route = route_stage(
            task(
                task_id="T-mcp",
                task_type="review",
                goal="Audit MCP tool schemas",
                domains=["mcp"],
                required_capabilities=["needs_MCP"],
            ),
            stage(
                "review",
                objective="Audit MCP tool schemas",
                task_type="review",
                domains=["mcp"],
                required_capabilities=["needs_MCP"],
                required_roles=["TOOL"],
            ),
            [mcp],
            adapter_capabilities={"MCP": True},
        )
        normal_route = route_stage(
            task(
                task_id="T-no-mcp",
                task_type="review",
                goal="Review a Python function",
                domains=["software-engineering"],
            ),
            stage(
                "review",
                objective="Review a Python function",
                domains=["software-engineering"],
            ),
            [mcp],
            adapter_capabilities={"MCP": True},
        )

        self.assertIn(
            "mcp-audit", {item["skill_id"] for item in mcp_route["selected_skills"]}
        )
        self.assertNotIn(
            "mcp-audit", {item["skill_id"] for item in normal_route["selected_skills"]}
        )

    def test_deep_understanding_is_escalation_gated(self):
        deep = metadata(
            "deep-understanding",
            roles=["PROCESS"],
            stages=["understand"],
            description="deep understanding of unfamiliar architecture",
            extension={"routing": {"deep_understanding": True}},
        )
        simple = route_stage(
            task(
                task_id="T-simple",
                goal="Rename one local variable",
                complexity="SIMPLE",
            ),
            stage("understand", objective="Rename one local variable"),
            [deep],
        )
        complex_route = route_stage(
            task(
                task_id="T-architecture",
                goal="Understand an unfamiliar architecture with contradictory evidence",
                complexity="COMPLEX",
                ambiguity="HIGH",
                risk="HIGH",
                architecture_impact="ARCHITECTURE-CHANGING",
                domains=["architecture"],
            ),
            stage(
                "understand",
                objective="Understand unfamiliar architecture",
                domains=["architecture"],
                required_roles=["PROCESS"],
            ),
            [deep],
        )

        self.assertEqual(simple["status"], "NO_SKILL_NEEDED")
        self.assertIn(
            "deep-understanding",
            {item["skill_id"] for item in complex_route["selected_skills"]},
        )
        self.assertEqual(
            complex_route["routing_evidence"]["deep_understanding"]["status"],
            "SELECTED",
        )

    def test_verification_is_selected_when_evidence_is_required(self):
        route = route_stage(
            task(
                task_id="T-verify",
                goal="Implement a change and prove it with tests",
                artifact_requirements=["tests"],
            ),
            stage(
                "implement",
                objective="Implement and prove the change",
                evidence_required=["tests"],
                required_roles=["PROCESS", "VERIFY"],
            ),
            [
                metadata(
                    "process",
                    roles=["PROCESS"],
                    stages=["implement"],
                    description="implement change",
                ),
                metadata(
                    "verify",
                    roles=["VERIFY"],
                    stages=["implement", "verify"],
                    description="verification tests evidence",
                ),
            ],
        )

        self.assertIn("verify", {item["skill_id"] for item in route["selected_skills"]})

    def test_unknown_capability_fails_closed(self):
        with self.assertRaises(RoutingError) as context:
            route_stage(
                task(required_capabilities=["needs_future_router_capability"]),
                stage(),
                [metadata("process", roles=["PROCESS"], stages=["implement"])],
            )

        self.assertEqual(context.exception.reason_code, "UNKNOWN_CAPABILITY")

    def test_context_budget_can_reduce_the_selected_set(self):
        catalog = [
            metadata(
                "expensive-process",
                roles=["PROCESS"],
                stages=["implement"],
                description="implement change",
                context_cost={"instruction_tokens_estimate": 900},
            ),
            metadata(
                "cheap-verify",
                roles=["VERIFY"],
                stages=["implement", "verify"],
                description="verify tests",
                context_cost={"instruction_tokens_estimate": 40},
            ),
        ]
        route = route_stage(
            task(
                task_id="T-budget",
                goal="Implement and verify a change",
                context_budget={"max_input_tokens": 100},
                artifact_requirements=["tests"],
            ),
            stage(
                "implement",
                objective="Implement and verify a change",
                evidence_required=["tests"],
            ),
            catalog,
        )
        selected = {item["skill_id"] for item in route["selected_skills"]}

        self.assertNotIn("expensive-process", selected)
        self.assertIn("cheap-verify", selected)

    def test_route_does_not_require_raw_skill_bodies(self):
        route = route_stage(
            task(),
            stage(),
            [
                metadata(
                    "process",
                    roles=["PROCESS"],
                    stages=["implement"],
                    description="SKILL.md body must not be loaded",
                )
            ],
        )
        serialized = json.dumps(route)

        self.assertNotIn("SKILL.md body", serialized)
        self.assertTrue(all("content" not in item for item in route["selected_skills"]))


class CurrentRegistryRouterTests(unittest.TestCase):
    def test_current_registry_is_routed_as_metadata_without_body_loading(self):
        registry = load_current_registry(REGISTRY)
        catalog = [
            import_current_skill(REGISTRY, item["id"]) for item in registry["skills"]
        ]
        router = StageRouter(
            adapter="codex", registry_epoch=f"registry:{registry['source_commit']}"
        )
        route = router.route(
            task(
                task_id="T-current-catalog",
                goal="Implement a test-driven bug fix and verify it",
                task_type="bugfix",
                domains=["software-engineering"],
                artifact_requirements=["tests", "verification"],
            ),
            stage(
                "implement",
                objective="Implement a test-driven bug fix",
                evidence_required=["tests", "verification"],
            ),
            catalog,
        )

        self.assertEqual(len(catalog), 214)
        self.assertEqual(route["routing_evidence"]["body_files_loaded"], 0)
        self.assertEqual(route["routing_evidence"]["metadata_records_inspected"], 214)
        self.assertTrue(validate_instance("StageRoute", route).valid)


class CodexEndToEndRouterTests(unittest.TestCase):
    def test_router_output_is_consumable_by_codex_adapter(self):
        from tools.v3.codex_adapter import CodexAdapter

        task_spec = json.loads(
            (ROOT / "fixtures/v3/taskspec/full.json").read_text(encoding="utf-8")
        )
        task_spec["task_id"] = "T-router-codex-e2e"
        task_spec["task_type"] = "implementation"
        task_spec["goal"] = "Implement the stage router MVP"
        task_spec["objectives"] = ["Implement the stage router MVP"]
        task_spec["stages"] = ["implement"]
        stage_route = route_stage(
            task_spec,
            {
                "id": "implement",
                "objective": "Implement the stage router MVP",
                "task_type": "implementation",
                "domains": ["software-engineering", "agent-orchestration"],
                "required_outputs": ["router", "tests"],
                "evidence_required": [
                    "tests",
                    "schema validation",
                    "diff",
                    "security review",
                ],
                "required_roles": ["PROCESS", "VERIFY"],
            },
            [
                import_current_skill(REGISTRY, item)
                for item in (
                    "using-superpowers",
                    "tdd",
                    "verification-before-completion",
                )
            ],
            adapter="codex",
            model_profile="openai/gpt-compatible-fixture@fixture-1",
            adapter_capabilities={
                "editing": True,
                "sandbox": True,
                "structured_output": True,
            },
            registry_epoch="registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac",
        )
        manifest = json.loads(
            (ROOT / "fixtures/v3/agents/codex.json").read_text(encoding="utf-8")
        )
        model = json.loads(
            (ROOT / "fixtures/v3/models/openai-compatible.json").read_text(
                encoding="utf-8"
            )
        )
        task_spec["permission_requirements"] = {
            "level": "workspace-write",
            "filesystem": "workspace-write",
            "network": "none",
            "external_write": False,
            "secrets": False,
            "publish": False,
            "delete": False,
        }
        metadata_records = [
            import_current_skill(REGISTRY, item["skill_id"])
            for item in stage_route["selected_skills"]
        ]
        result = CodexAdapter(
            ROOT,
            REGISTRY,
            policy=task_spec["permission_requirements"],
            live_runtime={
                "sandbox_mode": "workspace-write",
                "approval_policy": "on-request",
            },
        ).compile(
            task_spec=task_spec,
            stage_route=stage_route,
            adapter_manifest=manifest,
            model_profile=model,
            metadata_records=metadata_records,
            observed_evidence=[
                {"name": name} for name in stage_route["evidence_required"]
            ],
            reasoning_artifacts={
                "TaskSpec": {"ref": task_spec["task_id"]},
                "StagePlan": [{"stage": "implement"}],
                "Evidence": [{"name": "tests"}],
                "Verification": [{"name": "schema validation"}],
            },
        )

        self.assertEqual(result.status, "READY")
        self.assertEqual(result.projection["runtime_id"], "codex")
        self.assertTrue(result.bundle["selected_skills"])


if __name__ == "__main__":
    unittest.main()
