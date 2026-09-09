"""End-to-end proof that enriched routes remain consumable by Codex."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.v3.codex_adapter import CodexAdapter
from tools.v3.metadata_enrichment import load_enriched_catalog
from tools.v3.stage_router import StageRouter


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
FIXTURES = ROOT / "fixtures/v3/router/routing-eval-v1.json"


class EnrichedRouterCodexIntegrationTests(unittest.TestCase):
    def test_v1_fixture_replay_is_deterministic_and_metadata_only(self):
        suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
        catalog = load_enriched_catalog(REGISTRY)
        router = StageRouter(
            adapter="codex",
            registry_epoch="registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac",
        )

        first = [
            router.route(item["task_spec"], item["stage"], catalog)
            for item in suite["fixtures"]
        ]
        second = [
            router.route(item["task_spec"], item["stage"], catalog)
            for item in suite["fixtures"]
        ]

        self.assertEqual(first, second)
        self.assertEqual(len(first), 10)
        self.assertEqual(first[0]["status"], "NO_SKILL_NEEDED")
        self.assertTrue(
            all(
                route["routing_evidence"]["body_files_loaded"] == 0
                for route in first
            )
        )

    def test_enriched_route_compiles_through_codex_adapter(self):
        suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
        fixture = next(
            item for item in suite["fixtures"] if item["fixture_id"] == "B-ordinary-bug"
        )
        task_spec = json.loads(json.dumps(fixture["task_spec"]))
        task_spec["permission_requirements"] = {
            "level": "workspace-write",
            "filesystem": "workspace-write",
            "network": "none",
            "external_write": False,
            "secrets": False,
            "publish": False,
            "delete": False,
        }
        task_spec["required_capabilities"] = [
            "needs_editing",
            "needs_sandbox",
            "needs_structured_output",
        ]
        catalog = load_enriched_catalog(REGISTRY)
        route = StageRouter(
            adapter="codex",
            registry_epoch="registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac",
            adapter_capabilities={
                "editing": True,
                "sandbox": True,
                "structured_output": True,
            },
        ).route(task_spec, fixture["stage"], catalog)

        manifest = json.loads(
            (ROOT / "fixtures/v3/agents/codex.json").read_text(encoding="utf-8")
        )
        model = json.loads(
            (ROOT / "fixtures/v3/models/openai-compatible.json").read_text(
                encoding="utf-8"
            )
        )
        selected_ids = {item["skill_id"] for item in route["selected_skills"]}
        selected_metadata = [
            record for record in catalog if record["skill_id"] in selected_ids
        ]
        evidence = list(route["evidence_required"])
        artifacts = {
            "TaskSpec": {"ref": task_spec["task_id"]},
            "StagePlan": [{"stage": route["stage"]}],
            "Evidence": [{"name": name} for name in evidence],
            "Verification": [{"name": "tests"}],
        }

        result = CodexAdapter(
            ROOT,
            REGISTRY,
            policy=task_spec["permission_requirements"],
            live_runtime={
                "sandbox_mode": "workspace-write",
                "network_access": False,
                "approval_policy": "on-request",
            },
        ).compile(
            task_spec=task_spec,
            stage_route=route,
            adapter_manifest=manifest,
            model_profile=model,
            metadata_records=selected_metadata,
            observed_evidence=[{"name": name} for name in evidence],
            reasoning_artifacts=artifacts,
        )

        self.assertEqual(route["status"], "SKILLS_SELECTED")
        self.assertEqual(result.status, "READY")
        self.assertEqual(result.projection["runtime_id"], "codex")
        self.assertEqual(
            {item["skill_id"] for item in result.loaded_skills}, selected_ids
        )
        self.assertEqual(
            result.metrics["skill_md_files_loaded"], len(selected_ids) - 1
        )
        self.assertEqual(
            result.metrics["metadata_records_inspected"], len(selected_ids)
        )


if __name__ == "__main__":
    unittest.main()
