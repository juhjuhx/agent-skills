"""Regression tests for v3 routing-quality convergence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.v3.contract_validation import validate_file
from tools.v3.metadata_enrichment import (
    compile_overlay,
    load_overlay,
    validate_curated_overlay,
)
from tools.v3.routing_catalog import RoutingCatalogSnapshot
from tools.v3.stage_router import RoutingError, StageRouter


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
OVERLAY = ROOT / "registry/v3/skill-routing-metadata.json"
GENERATED = ROOT / "registry/v3/skill-routing-generated.json"
CURATED = ROOT / "registry/v3/skill-routing-curated.json"
FIXTURES = ROOT / "fixtures/v3/router/routing-eval-v1.json"
HOLDOUT = ROOT / "fixtures/v3/routing/stage-router-semantic-holdout-v1.json"
CENSUS = ROOT / "fixtures/v3/routing/stage-router-defect-census-v1.json"


def _digest(value: str) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record(
    skill_id: str,
    *,
    role: str = "PROCESS",
    roles: list[str] | None = None,
    stages: list[str] | None = None,
    modes: list[str] | None = None,
    domains: list[str] | None = None,
    outputs: list[str] | None = None,
    relationships: list[dict[str, str]] | None = None,
    negative_triggers: list[str] | None = None,
    required_triggers: list[str] | None = None,
    instruction_tokens: int = 100,
) -> dict:
    roles = roles or [role]
    record = {
        "schema_version": "3.0",
        "skill_id": skill_id,
        "name": skill_id,
        "description": f"{skill_id} procedure",
        "source": {
            "repo": "https://example.invalid/skills",
            "ref": "test",
            "path": f"{skill_id}/SKILL.md",
            "digest": _digest(skill_id),
        },
        "trust": "CORE_TRUSTED",
        "roles": roles,
        "stages": stages or ["implement"],
        "task_modes": modes or ["implementation"],
        "domains": domains or ["software-engineering"],
        "outputs": outputs or [],
        "context_cost": {
            "metadata_tokens": 10,
            "instruction_tokens_estimate": instruction_tokens,
            "references_lazy": True,
            "tool_schema_tokens": 0,
        },
        "runtime_cost": {"tool_calls_estimate": 0, "latency_class": "interactive"},
    }
    if relationships:
        record["relationships"] = relationships
    routing = {}
    if negative_triggers:
        routing["negative_triggers"] = negative_triggers
    if required_triggers:
        routing["required_triggers"] = required_triggers
    if routing:
        record["extensions"] = {
            "routing": routing
        }
    return record


def _task(
    task_id: str = "T-routing-quality",
    *,
    task_type: str = "implementation",
    goal: str = "Implement a software change",
    complexity: str = "STANDARD",
    risk: str = "LOW",
    ambiguity: str = "LOW",
    domains: list[str] | None = None,
    artifacts: list[str] | None = None,
) -> dict:
    result = {
        "schema_version": "3.0",
        "task_id": task_id,
        "task_type": task_type,
        "goal": goal,
        "complexity": complexity,
        "risk": risk,
        "ambiguity": ambiguity,
        "architecture_impact": "LOCAL",
        "objectives": [goal],
    }
    if domains:
        result["domains"] = domains
    if artifacts:
        result["artifact_requirements"] = artifacts
    return result


def _stage(
    stage_id: str = "implement",
    *,
    objective: str = "Implement the change",
    task_type: str = "implementation",
    domains: list[str] | None = None,
    required_roles: list[str] | None = None,
    evidence: list[str] | None = None,
    outputs: list[str] | None = None,
) -> dict:
    result = {
        "id": stage_id,
        "objective": objective,
        "task_type": task_type,
        "domains": domains or ["software-engineering"],
        "required_outputs": outputs or [],
        "evidence_required": evidence or [],
    }
    if required_roles is not None:
        result["required_roles"] = required_roles
    return result


class RoutingQualityTests(unittest.TestCase):
    def test_generated_and_curated_contracts_are_present(self):
        self.assertTrue(validate_file("SkillRoutingGenerated", GENERATED).valid)
        self.assertTrue(validate_file("SkillRoutingCurated", CURATED).valid)
        self.assertTrue(validate_file("SkillRoutingMetadata", OVERLAY).valid)

    def test_curated_override_survives_regeneration(self):
        generated = {
            "schema_version": "3.0",
            "generated_version": "test-generated",
            "registry": {"path": "SKILLS_INDEX.json", "source": "https://example.invalid", "source_ref": "test", "source_commit": "test", "skill_count": 1},
            "generator": {"version": "test", "entrypoint": "tools/test.py", "body_policy": "READ_ONLY_NO_EXECUTION"},
            "skills": {
                "sample": {
                    "skill_id": "sample",
                    "source_skill_digest": _digest("sample"),
                    "classification": "PARTIAL",
                    "tier": "TIER_3_SPECIALIZED",
                    "metadata": {
                        "schema_version": "3.0",
                        "skill_id": "sample",
                        "name": "sample",
                        "description": "sample",
                        "source": {"repo": "https://example.invalid", "ref": "test", "path": "sample/SKILL.md", "digest": _digest("sample")},
                        "trust": "CORE_TRUSTED",
                        "roles": ["PROCESS"],
                        "stages": ["implement"],
                        "task_modes": ["implementation"],
                        "domains": ["software-engineering"],
                    },
                    "provenance": {"default": "UNKNOWN", "fields": {"roles": {"source": "INFERRED", "confidence": 0.55}}, "relationships": {}},
                    "review_status": "GENERATED",
                    "confidence": 0.55,
                    "last_verified": None,
                    "body_policy": "READ_ONLY",
                    "body_bytes_inspected": 6,
                }
            },
        }
        generated["overlay_digest"] = _digest(json.dumps(generated, sort_keys=True, separators=(",", ":")))
        curated = {
            "schema_version": "3.0",
            "curated_version": "test-curated",
            "registry": generated["registry"],
            "curator": {"version": "test", "policy": "SMALL_FIELD_PATCHES_ONLY"},
            "skills": {
                "sample": {
                    "skill_id": "sample",
                    "source_skill_digest": _digest("sample"),
                    "fields": {
                        "roles": {"value": ["VERIFY"], "provenance": "CURATED", "confidence": 1.0, "evidence": "reviewed test override"}
                    },
                    "review_status": "REVIEWED",
                }
            },
        }
        compiled = compile_overlay(generated, curated)
        record = compiled["skills"]["sample"]
        self.assertEqual(record["metadata"]["roles"], ["VERIFY"])
        self.assertEqual(record["provenance"]["fields"]["roles"]["source"], "CURATED")

    def test_generated_metadata_cannot_override_curated_permissions(self):
        curated = load_overlay(CURATED)
        self.assertFalse(any("permissions" in item.get("fields", {}) for item in curated["skills"].values()))
        self.assertTrue(validate_curated_overlay(curated, registry_path=REGISTRY).valid)

    def test_curated_semantic_gates_are_compiled_with_curated_provenance(self):
        overlay = load_overlay(OVERLAY)
        for skill_id in (
            "brandkit",
            "brooks-harness",
            "cost-tracker",
            "llm-council",
            "maps",
            "permission-tuner",
            "understand",
            "understand-chat",
            "understand-dashboard",
            "understand-diff",
            "understand-domain",
            "invariant-guard",
            "MCP Integration",
            "redesign-existing-projects",
            "survey-generator",
            "wiki-viewer",
            "writing-skills",
        ):
            with self.subTest(skill_id=skill_id):
                record = overlay["skills"][skill_id]
                routing = record["metadata"]["extensions"]["routing"]
                self.assertTrue(routing["required_triggers"])
                self.assertEqual(
                    record["provenance"]["fields"]["extensions.routing"]["source"],
                    "CURATED",
                )

    def test_generated_inference_does_not_create_semantic_hard_gates(self):
        generated = load_overlay(GENERATED)
        self.assertFalse(
            any(
                "required_triggers" in (record.get("metadata", {}).get("extensions", {}).get("routing", {}) or {})
                for record in generated["skills"].values()
            )
        )

    def test_defect_census_is_complete_for_recorded_scope(self):
        census = json.loads(CENSUS.read_text(encoding="utf-8"))
        self.assertEqual(census["counted_occurrences"], len(census["occurrences"]))
        self.assertEqual(
            sum(item["recorded_repeat_count"] for item in census["families"]),
            census["counted_occurrences"],
        )
        self.assertTrue(
            all(item["disposition"] != "UNKNOWN" for item in census["families"])
        )

    def test_semantic_holdout_has_near_misses_without_expected_skill_lists(self):
        holdout = json.loads(HOLDOUT.read_text(encoding="utf-8"))
        self.assertEqual(len(holdout["tasks"]), 8)
        self.assertEqual(holdout["tuning_policy"], "HOLDOUT_NOT_FOR_ROUTING_TUNING")
        self.assertTrue(
            all("expected_skills" not in task and "expected" not in task for task in holdout["tasks"])
        )
        snapshot = RoutingCatalogSnapshot.from_registry(REGISTRY, overlay_path=OVERLAY)
        router = StageRouter(registry_epoch=snapshot.registry_epoch)
        for item in holdout["tasks"]:
            stage = item["stage"]
            objective = stage["objective"]
            task = _task(
                task_id=item["task_id"],
                task_type=stage["task_type"],
                goal=objective,
                risk="MEDIUM" if stage["id"] == "review" else "LOW",
                ambiguity="MEDIUM",
                domains=stage["domains"],
            )
            with self.subTest(task=item["task_id"]):
                route = router.route(task, stage, snapshot)
                selected = {candidate["skill_id"] for candidate in route["selected_skills"]}
                target = item["semantic_rubric"]["target_family"]
                if item["semantic_rubric"]["target_expectation"] == "RELEVANT":
                    self.assertIn(target, selected)
                else:
                    self.assertNotIn(target, selected)
                self.assertEqual(route["routing_evidence"]["body_files_loaded"], 0)

    def test_positive_counterparts_remain_available_for_closed_families(self):
        cases = [
            (
                "maps",
                _task(task_type="implementation", goal="Implement geocoding, nearby points of interest, and directions with OpenStreetMap", domains=["geospatial", "integrations"]),
                _stage("implement", objective="Implement geocoding, nearby points of interest, and directions with OpenStreetMap", task_type="implementation", domains=["geospatial", "integrations"], required_roles=["DOMAIN"]),
            ),
            (
                "cost-tracker",
                _task(task_type="review", goal="Verify token spend, budget quota, and usage accounting", domains=["context-engineering", "cost-management"]),
                _stage("verify", objective="Verify token spend, budget quota, and usage accounting", task_type="review", domains=["context-engineering", "cost-management"], required_roles=["VERIFY"]),
            ),
            (
                "wiki-viewer",
                _task(task_type="research", goal="Browse a workflow wiki and render its knowledge-base page-link graph", domains=["research", "documentation"]),
                _stage("research", objective="Browse a workflow wiki and render its knowledge-base page-link graph", task_type="research", domains=["research", "documentation"], required_roles=["DOMAIN"]),
            ),
            (
                "understand",
                _task(task_type="research", goal="Analyze the codebase architecture and map module dependencies into a knowledge graph", domains=["repository", "architecture"]),
                _stage("understand", objective="Analyze the codebase architecture and map module dependencies into a knowledge graph", task_type="research", domains=["repository", "architecture"], required_roles=["PROCESS"]),
            ),
            (
                "understand-chat",
                _task(task_type="research", goal="Ask questions about a codebase using its module dependencies", domains=["repository", "code-understanding"]),
                _stage("understand", objective="Ask questions about a codebase using its module dependencies", task_type="research", domains=["repository", "code-understanding"], required_roles=["DOMAIN"]),
            ),
            (
                "understand-dashboard",
                _task(task_type="research", goal="Visualize the knowledge graph in the interactive codebase dashboard", domains=["knowledge-graph", "visualization"]),
                _stage("understand", objective="Visualize the knowledge graph in the interactive codebase dashboard", task_type="research", domains=["knowledge-graph", "visualization"], required_roles=["DOMAIN"]),
            ),
            (
                "understand-domain",
                _task(task_type="research", goal="Extract business domain flows and create a domain graph", domains=["business-domain", "domain-analysis"]),
                _stage("understand", objective="Extract business domain flows and create a domain graph", task_type="research", domains=["business-domain", "domain-analysis"], required_roles=["DOMAIN"]),
            ),
            (
                "understand-diff",
                _task(task_type="review", goal="Analyze the git diff and affected components in this pull request", domains=["repository"]),
                _stage("understand", objective="Analyze the git diff and affected components in this pull request", task_type="review", domains=["repository"], required_roles=["DOMAIN"]),
            ),
            (
                "MCP Integration",
                _task(task_type="design", goal="Design an MCP server integration using the Model Context Protocol", domains=["mcp", "integrations"]),
                _stage("design", objective="Design an MCP server integration using the Model Context Protocol", task_type="design", domains=["mcp", "integrations"], required_roles=["TOOL"]),
            ),
            (
                "survey-generator",
                _task(task_type="research", goal="Compile a literature survey and deep dive with a bibliography", domains=["research", "literature"]),
                _stage("research", objective="Compile a literature survey and deep dive with a bibliography", task_type="research", domains=["research", "literature"], required_roles=["PROCESS"]),
            ),
            (
                "invariant-guard",
                _task(task_type="review", goal="Review an algorithm's loop invariant, postcondition, and off-by-one edge cases", domains=["software-engineering"]),
                _stage("review", objective="Review an algorithm's loop invariant, postcondition, and off-by-one edge cases", task_type="review", domains=["software-engineering"], required_roles=["REVIEW"]),
            ),
            (
                "redesign-existing-projects",
                _task(task_type="design", goal="Redesign an existing website UI and improve its generic visual patterns", domains=["frontend", "visual-design"]),
                _stage("design", objective="Redesign an existing website UI and improve its generic visual patterns", task_type="design", domains=["frontend", "visual-design"], required_roles=["DOMAIN"]),
            ),
        ]
        snapshot = RoutingCatalogSnapshot.from_registry(REGISTRY, overlay_path=OVERLAY)
        router = StageRouter(registry_epoch=snapshot.registry_epoch)
        for skill_id, task, stage in cases:
            with self.subTest(skill_id=skill_id):
                route = router.route(task, stage, snapshot)
                self.assertIn(skill_id, {candidate["skill_id"] for candidate in route["selected_skills"]})


    def test_negative_trigger_suppresses_irrelevant_activation(self):
        catalog = [
            _record("generic-ui-process", stages=["design"], modes=["design"], domains=["visual-design"], negative_triggers=["visual design"], outputs=["design artifact"]),
            _record("specific-design-process", stages=["design"], modes=["design"], domains=["visual-design"], outputs=["design artifact"]),
        ]
        task = _task(task_type="design", goal="Create a visual design", domains=["visual-design"])
        stage = _stage("design", objective="Create a visual design", task_type="design", domains=["visual-design"], required_roles=["PROCESS"])
        route = StageRouter(registry_epoch="test").route(task, stage, catalog)
        selected = {item["skill_id"] for item in route["selected_skills"]}
        self.assertIn("specific-design-process", selected)
        self.assertNotIn("generic-ui-process", selected)
        self.assertTrue(any("negative" in reason.lower() for item in route["routing_evidence"]["rejected_candidates"] for reason in item["reasons"]))

    def test_negative_trigger_cannot_suppress_required_dependency(self):
        catalog = [
            _record("main-process", relationships=[{"type": "REQUIRES", "target": "required-tool"}]),
            _record("required-tool", role="TOOL", roles=["TOOL"], domains=["software-engineering"], negative_triggers=["visual design"]),
        ]
        task = _task(task_type="implementation", domains=["software-engineering"])
        stage = _stage(objective="Implement after a visual design review", required_roles=["PROCESS"])
        route = StageRouter(registry_epoch="test").route(task, stage, catalog)
        selected = {item["skill_id"] for item in route["selected_skills"]}
        self.assertEqual(selected, {"main-process", "required-tool"})
        self.assertTrue(any("REQUIRES:main-process->required-tool" in effect for effect in route["routing_evidence"]["relationship_effects"]))

    def test_required_trigger_blocks_generic_semantic_overlap(self):
        candidate = _record(
            "permission-specialist",
            role="REVIEW",
            roles=["REVIEW"],
            stages=["review"],
            modes=["review"],
            domains=["quality-and-safety"],
            required_triggers=["permission boundary", "sandbox policy"],
        )
        route = StageRouter(registry_epoch="test").route(
            _task(
                task_type="review",
                goal="Review repository quality and test evidence",
                domains=["quality-and-safety"],
            ),
            _stage(
                "review",
                objective="Review repository quality and test evidence",
                task_type="review",
                domains=["quality-and-safety"],
                required_roles=["REVIEW"],
            ),
            [candidate],
        )

        self.assertEqual(route["status"], "NO_SKILL_NEEDED")
        rejected = next(
            item
            for item in route["routing_evidence"]["rejected_candidates"]
            if item["skill_id"] == "permission-specialist"
        )
        self.assertIn("required routing trigger", " ".join(rejected["reasons"]))

    def test_required_trigger_preserves_true_semantic_match(self):
        candidate = _record(
            "permission-specialist",
            role="REVIEW",
            roles=["REVIEW"],
            stages=["review"],
            modes=["review"],
            domains=["security"],
            required_triggers=["permission boundary", "sandbox policy"],
        )
        route = StageRouter(registry_epoch="test").route(
            _task(
                task_type="review",
                goal="Audit the permission boundary against the threat path",
                domains=["security"],
            ),
            _stage(
                "review",
                objective="Audit the permission boundary against the threat path",
                task_type="review",
                domains=["security"],
                required_roles=["REVIEW"],
            ),
            [candidate],
        )

        self.assertIn(
            "permission-specialist",
            {item["skill_id"] for item in route["selected_skills"]},
        )

    def test_relationship_expansion_cannot_bypass_required_trigger(self):
        primary = _record(
            "primary-process",
            roles=["PROCESS"],
            stages=["implement"],
            modes=["implementation"],
            relationships=[
                {"type": "COMPLEMENTS", "target": "specialist"}
            ],
        )
        specialist = _record(
            "specialist",
            role="DOMAIN",
            roles=["DOMAIN"],
            stages=["implement"],
            modes=["implementation"],
            domains=["software-engineering"],
            required_triggers=["specialized protocol"],
        )
        route = StageRouter(registry_epoch="test").route(
            _task(goal="Implement a routine software change"),
            _stage("implement", required_roles=["PROCESS"]),
            [primary, specialist],
        )

        selected = {item["skill_id"] for item in route["selected_skills"]}
        self.assertIn("primary-process", selected)
        self.assertNotIn("specialist", selected)
        rejected = next(
            item
            for item in route["routing_evidence"]["rejected_candidates"]
            if item["skill_id"] == "specialist"
        )
        self.assertIn("required routing trigger", " ".join(rejected["reasons"]))

    def test_stage_and_domain_exclusions_are_negative_routing_signals(self):
        catalog = [
            _record("preferred-process"),
            _record(
                "excluded-process",
                negative_triggers=["never-match"],
            )
        ]
        catalog[1]["extensions"] = {
            "routing": {
                "stage_exclusions": ["implement"],
                "domain_exclusions": ["security"],
            }
        }
        task = _task(domains=["security"])
        stage = _stage("implement", domains=["software-engineering"])
        route = StageRouter(registry_epoch="test").route(task, stage, catalog)
        rejected = next(
            item
            for item in route["routing_evidence"]["rejected_candidates"]
            if item["skill_id"] == "excluded-process"
        )
        reasons = " ".join(rejected["reasons"])
        self.assertIn("negative", reasons.lower())
        effects = route["routing_evidence"]["negative_signal_effects"]
        self.assertTrue(any("stage:implement" in effect for effect in effects))
        self.assertTrue(any("domain:security" in effect for effect in effects))

    def test_role_saturation_allows_independent_second_review(self):
        catalog = [
            _record("review-a", role="REVIEW", roles=["REVIEW"], stages=["review"], modes=["review"], domains=["repository"], outputs=["review findings"]),
            _record("review-b", role="REVIEW", roles=["REVIEW"], stages=["review"], modes=["review"], domains=["repository"], outputs=["review findings"]),
            _record("review-c", role="REVIEW", roles=["REVIEW"], stages=["review"], modes=["review"], domains=["repository"], outputs=["review findings"]),
        ]
        task = _task(task_type="review", goal="Audit the repository", complexity="COMPLEX", domains=["repository"])
        normal_stage = _stage("review", objective="Audit the repository", task_type="review", domains=["repository"], required_roles=["REVIEW"], evidence=["verification"])
        independent_stage = _stage("review", objective="Audit the repository with independent review", task_type="review", domains=["repository"], required_roles=["REVIEW"], evidence=["verification", "independent review"])
        normal = StageRouter(registry_epoch="test").route(task, normal_stage, catalog)
        independent = StageRouter(registry_epoch="test").route(task, independent_stage, catalog)
        self.assertEqual(sum(item["role"] == "REVIEW" for item in normal["selected_skills"]), 1)
        self.assertEqual(sum(item["role"] == "REVIEW" for item in independent["selected_skills"]), 2)
        self.assertTrue(independent["routing_evidence"]["role_saturation"]["independent_review_required"])

    def test_task_artifacts_do_not_enable_unrelated_stage_review(self):
        catalog = [
            _record("process", stages=["implement"], outputs=["patch"]),
            _record("review-a", role="REVIEW", roles=["REVIEW"], stages=["review"], modes=["review"], domains=["repository"], outputs=["review findings"]),
            _record("review-b", role="REVIEW", roles=["REVIEW"], stages=["review"], modes=["review"], domains=["repository"], outputs=["review findings"]),
        ]
        task = _task(
            complexity="COMPLEX",
            risk="HIGH",
            artifacts=["review", "security", "tests"],
        )
        stage = _stage("implement", required_roles=["PROCESS"])
        route = StageRouter(registry_epoch="test").route(task, stage, catalog)
        self.assertFalse(
            any(item["role"] == "REVIEW" for item in route["selected_skills"])
        )
        self.assertFalse(
            route["routing_evidence"]["role_saturation"]["independent_review_required"]
        )

    def test_context_cost_marginal_penalty_rejects_expensive_complement(self):
        catalog = [
            _record("core-process", relationships=[{"type": "RECOMMENDS", "target": "expensive-complement"}]),
            _record("expensive-complement", role="REVIEW", roles=["REVIEW"], domains=["software-engineering"], instruction_tokens=12000),
        ]
        route = StageRouter(registry_epoch="test").route(
            _task(), _stage(required_roles=["PROCESS"]), catalog
        )
        selected = {item["skill_id"] for item in route["selected_skills"]}
        self.assertNotIn("expensive-complement", selected)
        self.assertTrue(any("context cost" in reason.lower() for item in route["routing_evidence"]["rejected_candidates"] for reason in item["reasons"]))

    def test_snapshot_is_deterministic_and_reused_across_stages(self):
        first = RoutingCatalogSnapshot.from_registry(REGISTRY, overlay_path=OVERLAY)
        second = RoutingCatalogSnapshot.from_registry(REGISTRY, overlay_path=OVERLAY)
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual(first.overlay_digest, second.overlay_digest)
        self.assertEqual(first.records, second.records)
        router = StageRouter(registry_epoch="test")
        task = _task()
        stage = _stage()
        route_a = router.route(task, stage, first)
        route_b = router.route(task, stage, first)
        self.assertEqual(route_a, route_b)
        self.assertEqual(route_a["routing_evidence"]["catalog_snapshot"]["reused"], True)
        self.assertEqual(route_a["routing_evidence"]["body_files_loaded"], 0)

    def test_stale_registry_digest_invalidates_snapshot(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        registry["skills"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "SKILLS_INDEX.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaises(RoutingError):
                RoutingCatalogSnapshot.from_registry(path, overlay_path=OVERLAY)

    def test_snapshot_route_never_reads_skill_bodies(self):
        snapshot = RoutingCatalogSnapshot.from_registry(REGISTRY, overlay_path=OVERLAY)
        router = StageRouter(registry_epoch="test")
        route = router.route(_task(), _stage(), snapshot)
        self.assertEqual(route["routing_evidence"]["body_files_loaded"], 0)
        self.assertEqual(route["routing_evidence"]["metadata_records_inspected"], 214)

    def test_measured_route_exposes_routing_latency_breakdown(self):
        snapshot = RoutingCatalogSnapshot.from_registry(REGISTRY, overlay_path=OVERLAY)
        route = StageRouter(registry_epoch="test").route(
            _task(), _stage(), snapshot, measure=True
        )
        timings = route["routing_evidence"]["timings_ms"]
        self.assertIn("candidate_scoring_ms", timings)
        self.assertIn("total_route_ms", timings)
        self.assertGreaterEqual(timings["candidate_scoring_ms"], 0)
        self.assertGreaterEqual(timings["total_route_ms"], timings["candidate_scoring_ms"])

    def test_same_snapshot_supports_many_stage_routes(self):
        snapshot = RoutingCatalogSnapshot.from_registry(REGISTRY, overlay_path=OVERLAY)
        router = StageRouter(registry_epoch="test")
        task = _task(complexity="COMPLEX", risk="HIGH", ambiguity="HIGH")
        stages = [
            _stage("understand", objective="Understand the architecture", task_type="design", domains=["architecture"]),
            _stage("plan", objective="Plan the change", task_type="design", domains=["architecture"]),
            _stage("implement", objective="Implement the change"),
            _stage("review", objective="Review the change", task_type="review", required_roles=["REVIEW"], evidence=["verification"]),
            _stage("verify", objective="Verify the change", evidence=["verification"]),
        ]
        routes = [router.route(task, stage, snapshot) for stage in stages]
        self.assertEqual(len(routes), len(stages))
        self.assertTrue(all(route["routing_evidence"]["catalog_snapshot"]["snapshot_id"] == snapshot.snapshot_id for route in routes))
        self.assertTrue(all(route["routing_evidence"]["body_files_loaded"] == 0 for route in routes))

    def test_all_v1_fixture_routes_are_deterministic_with_snapshot(self):
        suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
        snapshot = RoutingCatalogSnapshot.from_registry(REGISTRY, overlay_path=OVERLAY)
        router = StageRouter(registry_epoch="registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac")
        first = [router.route(item["task_spec"], item["stage"], snapshot) for item in suite["fixtures"]]
        second = [router.route(item["task_spec"], item["stage"], snapshot) for item in suite["fixtures"]]
        self.assertEqual(first, second)
        self.assertEqual(first[0]["status"], "NO_SKILL_NEEDED")

    def test_warm_routing_performance_smoke(self):
        snapshot = RoutingCatalogSnapshot.from_registry(REGISTRY, overlay_path=OVERLAY)
        router = StageRouter(registry_epoch=snapshot.registry_epoch)
        task = _task(
            task_type="review",
            goal="Audit the repository and verify the changed files",
            complexity="COMPLEX",
            ambiguity="MEDIUM",
            domains=["repository"],
        )
        stage = _stage(
            "review",
            objective="Audit the repository and verify the changed files",
            task_type="review",
            domains=["repository"],
            required_roles=["REVIEW", "VERIFY"],
            evidence=["source inspection", "tests"],
        )
        routes = [router.route(task, stage, snapshot, measure=True) for _ in range(3)]
        timings = [
            route["routing_evidence"]["timings_ms"]["total_route_ms"]
            for route in routes
        ]
        self.assertLess(max(timings), 250.0)
        self.assertTrue(
            all(
                route["routing_evidence"]["body_files_loaded"] == 0
                for route in routes
            )
        )


if __name__ == "__main__":
    unittest.main()
