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
    if negative_triggers:
        record["extensions"] = {
            "routing": {"negative_triggers": negative_triggers}
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


if __name__ == "__main__":
    unittest.main()
