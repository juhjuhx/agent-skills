"""Static productization compiler tests for Phase 3I."""

from __future__ import annotations

import json
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from tools.v3.contract_validation import validate_file, validate_instance
from tools.v3.execution_bundle import compile_execution_bundle
from tools.v3.productization import (
    ProductizationError,
    build_installation_plan,
    build_runtime_capability_report,
    compile_distribution,
    digest_value,
    load_runtime_inventory,
    main,
    snapshot_digest,
    validate_distribution,
)
from tools.v3.routing_catalog import RoutingCatalogSnapshot
from tools.v3.stage_router import StageRouter


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
OVERLAY = ROOT / "registry/v3/skill-routing-metadata.json"


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class ProductizationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = RoutingCatalogSnapshot.from_registry(
            REGISTRY,
            overlay_path=OVERLAY,
            repository_root=ROOT,
        )
        self.selected_route = load_json("fixtures/v3/routes/skills-selected.json")
        self.selected_route["registry_epoch"] = self.snapshot.registry_epoch
        self.selected_route["task_id"] = "T-productization-selected"
        self.selected_route["route_id"] = "R-productization-selected"
        self.no_skill_route = load_json("fixtures/v3/routes/no-skill-needed.json")
        self.no_skill_route["registry_epoch"] = self.snapshot.registry_epoch
        self.no_skill_route["task_id"] = "T-productization-none"
        self.no_skill_route["route_id"] = "R-productization-none"

    def status(self, fixture_name: str, runtime_id: str) -> dict:
        inventory = load_runtime_inventory(fixture_name=fixture_name)
        return next(
            runtime for runtime in inventory["runtimes"]
            if runtime["runtime_id"] == runtime_id
        )


class RuntimeInventoryTests(ProductizationTestCase):
    def test_fixture_inventory_is_fixture_driven_and_status_dimensions_stay_independent(self):
        inventory = load_runtime_inventory(fixture_name="ALL_KNOWN_STATIC")
        report = build_runtime_capability_report(inventory)

        self.assertEqual(
            {item["runtime_id"] for item in report["runtimes"]},
            {"codex", "claude-code", "opencode", "hermes"},
        )
        codex = self.status("ALL_KNOWN_STATIC", "codex")
        self.assertEqual(codex["adapter_support"], "NATIVE_IMPLEMENTED")
        self.assertEqual(codex["static_contract"], "VERIFIED")
        self.assertEqual(codex["live_execution"], "TRANSPORT_BLOCKED")
        self.assertNotIn("credential", json.dumps(report).lower())

    def test_inventory_variants_are_deterministic_and_unknown_fails_closed(self):
        first = load_runtime_inventory(fixture_name="CODEX_ONLY")
        second = load_runtime_inventory(fixture_name="CODEX_ONLY")
        self.assertEqual(first, second)

        unknown = load_runtime_inventory(fixture_name="UNKNOWN_RUNTIME")
        plan = build_installation_plan(
            runtime_status=unknown["runtimes"][0],
            snapshot=self.snapshot,
        )
        self.assertEqual(plan["artifacts"], [])
        self.assertEqual(plan["operations"][0]["operation"], "SKIP_UNSUPPORTED_RUNTIME")

    def test_all_declared_inventory_variants_load_without_local_runtime_probes(self):
        for fixture_name in (
            "CODEX_ONLY",
            "CODEX_CLAUDE",
            "CODEX_OPENCODE",
            "ALL_KNOWN_STATIC",
            "NO_RUNTIMES",
            "UNKNOWN_RUNTIME",
        ):
            with self.subTest(fixture=fixture_name):
                inventory = load_runtime_inventory(fixture_name=fixture_name)
                self.assertEqual(inventory["fixture_name"], fixture_name)

    def test_no_runtime_inventory_is_a_valid_empty_report(self):
        inventory = load_runtime_inventory(fixture_name="NO_RUNTIMES")
        report = build_runtime_capability_report(inventory)
        self.assertEqual(report["runtime_count"], 0)
        self.assertEqual(report["runtimes"], [])


class InstallationPlanTests(ProductizationTestCase):
    def test_codex_plan_is_deterministic_and_warns_about_blocked_live_state(self):
        status = self.status("CODEX_ONLY", "codex")
        first = build_installation_plan(
            runtime_status=status,
            snapshot=self.snapshot,
            stage_route=self.no_skill_route,
        )
        second = build_installation_plan(
            runtime_status=status,
            snapshot=self.snapshot,
            stage_route=self.no_skill_route,
        )

        self.assertEqual(first, second)
        self.assertTrue(first["no_actual_writes"])
        self.assertTrue(any(item["operation"] == "WARN_LIVE_BLOCKED" for item in first["operations"]))
        self.assertTrue(any(item["path"].endswith("selected-skills.json") for item in first["artifacts"]))

    def test_conflict_policy_distinguishes_absent_managed_user_owned_and_unknown(self):
        status = self.status("CODEX_ONLY", "codex")
        plan = build_installation_plan(
            runtime_status=status,
            snapshot=self.snapshot,
            destination_states={
                "codex/runtime-status.json": "MANAGED",
                "codex/adapter-manifest.json": "USER_OWNED",
                "codex/routing-snapshot.json": "UNKNOWN",
            },
        )
        outcomes = {item["path"]: item["conflict_outcome"] for item in plan["operations"] if item.get("path")}
        self.assertEqual(outcomes["codex/runtime-status.json"], "UPDATE_MANAGED")
        self.assertEqual(outcomes["codex/adapter-manifest.json"], "SKIP_USER_OWNED")
        self.assertEqual(outcomes["codex/routing-snapshot.json"], "CONFLICT")

    def test_hermes_has_no_fake_distribution(self):
        status = self.status("ALL_KNOWN_STATIC", "hermes")
        plan = build_installation_plan(runtime_status=status, snapshot=self.snapshot)
        self.assertEqual(plan["artifacts"], [])
        self.assertEqual(plan["operations"][0]["operation"], "SKIP_UNSUPPORTED_RUNTIME")


class DistributionCompilerTests(ProductizationTestCase):
    def test_static_distributions_exist_only_for_supported_adapters(self):
        for runtime_id in ("codex", "claude-code", "opencode"):
            with self.subTest(runtime=runtime_id), tempfile.TemporaryDirectory() as output_dir:
                status = self.status("ALL_KNOWN_STATIC", runtime_id)
                result = compile_distribution(
                    runtime_status=status,
                    snapshot=self.snapshot,
                    output_dir=output_dir,
                    repository_root=ROOT,
                )
                self.assertIsNotNone(result["artifact_manifest"])
                self.assertTrue((Path(output_dir) / runtime_id / "runtime-projection.json").is_file())
                self.assertFalse((Path(output_dir) / "hermes").exists())
                self.assertTrue(validate_instance("GeneratedArtifactManifest", result["artifact_manifest"]).valid)

    def test_current_stage_router_route_is_consumed_without_reselection(self):
        suite = load_json("fixtures/v3/router/routing-eval-v1.json")
        fixture = next(item for item in suite["fixtures"] if item["fixture_id"] == "B-ordinary-bug")
        route = StageRouter(
            adapter="codex",
            registry_epoch=self.snapshot.registry_epoch,
            adapter_capabilities={"editing": True, "sandbox": True, "structured_output": True},
        ).route(fixture["task_spec"], fixture["stage"], self.snapshot)
        status = self.status("CODEX_ONLY", "codex")

        with tempfile.TemporaryDirectory() as output_dir:
            result = compile_distribution(
                runtime_status=status,
                snapshot=self.snapshot,
                stage_route=route,
                output_dir=output_dir,
                repository_root=ROOT,
            )
            projection = json.loads(
                (Path(output_dir) / "codex/runtime-projection.json").read_text(encoding="utf-8")
            )
            self.assertEqual(projection["route"]["route_digest"], digest_value(route))
            self.assertEqual(projection["snapshot"]["snapshot_id"], self.snapshot.snapshot_id)
            self.assertTrue(result["plan"]["artifacts"])

    def test_compiled_bundle_reference_remains_runtime_neutral_and_bound(self):
        task = load_json("fixtures/v3/taskspec/full.json")
        task["task_id"] = self.no_skill_route["task_id"]
        manifest = load_json("fixtures/v3/agents/codex.json")
        model = load_json("fixtures/v3/models/openai-compatible.json")
        bundle = compile_execution_bundle(
            task_spec=task,
            stage_route=self.no_skill_route,
            adapter_manifest=manifest,
            model_profile=model,
            selected_skills=[],
            effective_capabilities=[],
            permission_envelope={"level": "read-only", "filesystem": "read", "network": "none"},
            context={"static_prefix": "stable", "dynamic_context": "lazy", "tool_schema_context": "tracked", "artifact_refs": []},
            reasoning_artifact_refs=[],
            evidence_required=self.no_skill_route["evidence_required"],
            evidence_gate={"status": "PASS", "missing": []},
            provenance={"registry_epoch": self.snapshot.registry_epoch},
        )
        status = self.status("CODEX_ONLY", "codex")
        with tempfile.TemporaryDirectory() as output_dir:
            result = compile_distribution(
                runtime_status=status,
                snapshot=self.snapshot,
                stage_route=self.no_skill_route,
                bundle=bundle,
                output_dir=output_dir,
                repository_root=ROOT,
            )
            self.assertIn(
                "codex/compiled-execution-bundle.json",
                {item["path"] for item in result["plan"]["artifacts"]},
            )

    def test_selected_only_materialization_and_no_skill_needed_behavior(self):
        status = self.status("CODEX_ONLY", "codex")
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            selected = compile_distribution(
                runtime_status=status,
                snapshot=self.snapshot,
                stage_route=self.selected_route,
                output_dir=first_dir,
                repository_root=ROOT,
                materialize_bodies=True,
            )
            none = compile_distribution(
                runtime_status=status,
                snapshot=self.snapshot,
                stage_route=self.no_skill_route,
                output_dir=second_dir,
                repository_root=ROOT,
                materialize_bodies=True,
            )

            body_files = list(Path(first_dir).glob("codex/skills/selected/*/SKILL.md"))
            self.assertEqual(len(body_files), 3)
            self.assertEqual(list(Path(second_dir).glob("**/SKILL.md")), [])
            self.assertEqual(selected["artifact_manifest"]["body_files_materialized"], 3)
            self.assertEqual(none["artifact_manifest"]["body_files_materialized"], 0)

    def test_compile_is_idempotent_and_validation_is_separate(self):
        status = self.status("CODEX_ONLY", "codex")
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = compile_distribution(
                runtime_status=status,
                snapshot=self.snapshot,
                stage_route=self.selected_route,
                output_dir=first_dir,
                repository_root=ROOT,
            )
            second = compile_distribution(
                runtime_status=status,
                snapshot=self.snapshot,
                stage_route=self.selected_route,
                output_dir=second_dir,
                repository_root=ROOT,
            )
            self.assertEqual(first["plan"], second["plan"])
            self.assertEqual(first["artifact_manifest"], second["artifact_manifest"])
            self.assertEqual(
                validate_distribution(
                    first_dir,
                    snapshot=self.snapshot,
                    runtime_status=status,
                    stage_route=self.selected_route,
                )["valid"],
                True,
            )

            artifact_path = Path(first_dir) / "codex" / "routing-snapshot.json"
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            payload["snapshot_digest"] = "sha256:" + "0" * 64
            artifact_path.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            result = validate_distribution(
                first_dir,
                snapshot=self.snapshot,
                runtime_status=status,
                stage_route=self.selected_route,
            )
            self.assertFalse(result["valid"])
            self.assertTrue(any("snapshot" in error for error in result["errors"]))

    def test_stale_skill_and_runtime_contract_are_rejected_without_regeneration(self):
        status = self.status("CODEX_ONLY", "codex")
        with tempfile.TemporaryDirectory() as output_dir:
            compile_distribution(
                runtime_status=status,
                snapshot=self.snapshot,
                stage_route=self.selected_route,
                output_dir=output_dir,
                repository_root=ROOT,
            )
            status_copy = dict(status)
            status_copy["runtime_contract_digest"] = "sha256:" + "1" * 64
            result = validate_distribution(
                output_dir,
                snapshot=self.snapshot,
                runtime_status=status_copy,
                stage_route=self.selected_route,
            )
            self.assertFalse(result["valid"])
            self.assertTrue(any("runtime contract" in error for error in result["errors"]))

    def test_snapshot_digest_changes_when_metadata_changes(self):
        original = snapshot_digest(self.snapshot)
        self.snapshot.records[0]["description"] = "tampered"
        self.assertNotEqual(original, snapshot_digest(self.snapshot))

    def test_global_runtime_output_is_rejected(self):
        status = self.status("CODEX_ONLY", "codex")
        with self.assertRaises(ProductizationError):
            compile_distribution(
                runtime_status=status,
                snapshot=self.snapshot,
                output_dir=Path.home() / ".codex",
                repository_root=ROOT,
            )

    def test_user_owned_output_is_not_overwritten(self):
        status = self.status("CODEX_ONLY", "codex")
        with tempfile.TemporaryDirectory() as output_dir:
            target = Path(output_dir) / "codex" / "runtime-status.json"
            target.parent.mkdir(parents=True)
            target.write_text("user-owned\n", encoding="utf-8")
            with self.assertRaisesRegex(ProductizationError, "ownership marker"):
                compile_distribution(
                    runtime_status=status,
                    snapshot=self.snapshot,
                    output_dir=output_dir,
                    repository_root=ROOT,
                )

    def test_symlinked_generated_directory_is_rejected(self):
        status = self.status("CODEX_ONLY", "codex")
        with tempfile.TemporaryDirectory() as output_dir, tempfile.TemporaryDirectory() as outside_dir:
            (Path(output_dir) / "codex").symlink_to(outside_dir, target_is_directory=True)
            with self.assertRaisesRegex(ProductizationError, "symlink"):
                compile_distribution(
                    runtime_status=status,
                    snapshot=self.snapshot,
                    output_dir=output_dir,
                    repository_root=ROOT,
                )

    def test_compile_all_is_rejected_until_multi_root_output_is_defined(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["--runtime", "all", "--operation", "compile", "--output", tempfile.gettempdir()])
        self.assertEqual(exit_code, 2)
        self.assertIn("compile or validate one runtime at a time", stderr.getvalue())

    def test_productization_source_contains_no_runtime_process_boundary(self):
        source = (ROOT / "tools/v3/productization.py").read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("Popen", source)


class ProductizationSchemaTests(unittest.TestCase):
    def test_checked_in_conformance_record_binds_current_snapshot_and_boundaries(self):
        evidence = load_json("fixtures/v3/productization/static-conformance-v1.json")
        self.assertEqual(evidence["status"], "STATIC_PRODUCTIZATION_READY")
        self.assertEqual(evidence["snapshot"]["snapshot_id"], "snapshot:87dc6a8790b10450")
        self.assertEqual(evidence["snapshot"]["skill_count"], 214)
        self.assertEqual(evidence["snapshot"]["catalog_body_files_loaded_during_ranking"], 0)
        self.assertFalse(evidence["conformance"]["runtime_process_invocations"])
        self.assertFalse(evidence["conformance"]["global_runtime_writes"])

    def test_new_public_schemas_validate_their_checked_in_fixtures(self):
        self.assertTrue(
            validate_file(
                "RuntimeProductStatus",
                ROOT / "fixtures/v3/productization/runtime-status-codex.json",
            ).valid
        )
        self.assertTrue(
            validate_file(
                "RuntimeProductStatus",
                ROOT / "fixtures/v3/productization/runtime-status-claude.json",
            ).valid
        )
        inventory = load_runtime_inventory(fixture_name="ALL_KNOWN_STATIC")
        for status in inventory["runtimes"]:
            with self.subTest(runtime=status["runtime_id"]):
                self.assertTrue(validate_instance("RuntimeProductStatus", status).valid)

    def test_installation_plan_and_generated_manifest_validate(self):
        snapshot = RoutingCatalogSnapshot.from_registry(REGISTRY, overlay_path=OVERLAY, repository_root=ROOT)
        status = load_runtime_inventory(fixture_name="CODEX_ONLY")["runtimes"][0]
        plan = build_installation_plan(runtime_status=status, snapshot=snapshot)
        self.assertTrue(validate_instance("InstallationPlan", plan).valid)
        with tempfile.TemporaryDirectory() as output_dir:
            result = compile_distribution(
                runtime_status=status,
                snapshot=snapshot,
                output_dir=output_dir,
                repository_root=ROOT,
            )
            self.assertTrue(
                validate_instance("GeneratedArtifactManifest", result["artifact_manifest"]).valid
            )

    def test_runtime_status_rejects_unknown_dimension_values(self):
        status = load_json("fixtures/v3/productization/runtime-status-codex.json")
        status["live_execution"] = "READY"
        result = validate_file(
            "RuntimeProductStatus",
            ROOT / "fixtures/v3/productization/runtime-status-codex.json",
        )
        self.assertTrue(result.valid, result.errors)
        from tools.v3.contract_validation import validate_instance

        self.assertFalse(validate_instance("RuntimeProductStatus", status).valid)


if __name__ == "__main__":
    unittest.main()
