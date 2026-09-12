"""Integration-checkpoint tests for the current v3 mutation path."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.v3.claude_user_scope import (
    build_claude_user_preview,
    load_claude_user_contract,
)
from tools.v3.contract_validation import validate_instance
from tools.v3.installer import (
    InstallerError,
    apply_install_package,
    apply_uninstall,
    build_install_package,
)
from tools.v3.productization import (
    compile_distribution,
    digest_value,
    load_runtime_inventory,
)
from tools.v3.routing_catalog import RoutingCatalogSnapshot
from tools.v3.user_scope import build_user_scope_preview, plan_project_user_migration


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
OVERLAY = ROOT / "registry/v3/skill-routing-metadata.json"


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class IntegrationCheckpointTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = RoutingCatalogSnapshot.from_registry(
            REGISTRY,
            overlay_path=OVERLAY,
            repository_root=ROOT,
        )
        self.no_skill_route = load_json("fixtures/v3/routes/no-skill-needed.json")
        self.no_skill_route["registry_epoch"] = self.snapshot.registry_epoch
        self.no_skill_route["task_id"] = "T-phase3m-no-skill"
        self.no_skill_route["route_id"] = "R-phase3m-no-skill"
        inventory = load_runtime_inventory(fixture_name="ALL_KNOWN_STATIC")
        self.statuses = {item["runtime_id"]: item for item in inventory["runtimes"]}

    def compile_codex(self, output_dir: Path) -> dict:
        return compile_distribution(
            runtime_status=copy.deepcopy(self.statuses["codex"]),
            snapshot=self.snapshot,
            stage_route=self.no_skill_route,
            output_dir=output_dir,
            repository_root=ROOT,
        )

    def make_package(self, distribution_dir: Path, project_root: Path) -> dict:
        compiled = self.compile_codex(distribution_dir)
        return build_install_package(
            distribution_dir,
            compiled["plan"],
            self.statuses["codex"],
            project_root=project_root,
        )


class ContractLineageTests(IntegrationCheckpointTestCase):
    def test_stage_route_to_distribution_to_package_preserves_authority_and_lifecycle(self):
        with tempfile.TemporaryDirectory() as distribution_dir, tempfile.TemporaryDirectory() as project_dir:
            distribution = Path(distribution_dir)
            compiled = self.compile_codex(distribution)
            package = build_install_package(
                distribution,
                compiled["plan"],
                self.statuses["codex"],
                project_root=Path(project_dir),
            )
            projection = json.loads(
                (distribution / "codex/runtime-projection.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                projection["route"]["route_digest"], digest_value(self.no_skill_route)
            )
            self.assertEqual(
                compiled["plan"]["snapshot"]["snapshot_digest"],
                package["snapshot_digest"],
            )
            self.assertEqual(package["plan_digest"], compiled["plan"]["plan_digest"])
            self.assertTrue(package["excluded_artifacts"])
            self.assertTrue(
                all(
                    item["lifecycle"] != "EXECUTION_EPHEMERAL"
                    for item in package["artifacts"]
                )
            )
            self.assertTrue(
                any(
                    item["lifecycle"] == "EXECUTION_EPHEMERAL"
                    for item in package["excluded_artifacts"]
                )
            )

    def test_no_skill_route_has_no_execution_body_or_persistent_skill_artifact(self):
        with tempfile.TemporaryDirectory() as distribution_dir, tempfile.TemporaryDirectory() as project_dir:
            distribution = Path(distribution_dir)
            compiled = self.compile_codex(distribution)
            package = build_install_package(
                distribution,
                compiled["plan"],
                self.statuses["codex"],
                project_root=Path(project_dir),
            )
            self.assertEqual(compiled["artifact_manifest"]["body_files_materialized"], 0)
            self.assertEqual(list(distribution.glob("**/SKILL.md")), [])
            self.assertFalse(
                any(item["kind"] == "SKILL_BODY" for item in package["artifacts"])
            )

    def test_install_package_and_apply_result_keep_distinct_contract_roles(self):
        with tempfile.TemporaryDirectory() as distribution_dir, tempfile.TemporaryDirectory() as project_dir:
            package = self.make_package(Path(distribution_dir), Path(project_dir))
            self.assertTrue(validate_instance("InstallPackage", package).valid)
            self.assertNotIn("operation", package)
            self.assertTrue(
                validate_instance(
                    "ApplyResult",
                    {
                        "schema_version": "3.0",
                        "result_version": "1.0",
                        "transaction_id": "tx:phase3m-contract",
                        "package_digest": package["package_digest"],
                        "runtime_id": "codex",
                        "scope": "PROJECT",
                        "status": "PREVIEWED",
                        "actions_attempted": [],
                        "actions_completed": [],
                        "warnings": [],
                        "conflicts": [],
                        "rollback_status": "NOT_ATTEMPTED",
                        "sensitive_data_serialized": False,
                    },
                ).valid
            )

    def test_operation_is_descriptive_but_must_not_contradict_authoritative_action(self):
        with tempfile.TemporaryDirectory() as distribution_dir, tempfile.TemporaryDirectory() as project_dir:
            distribution = Path(distribution_dir)
            compiled = self.compile_codex(distribution)
            plan = copy.deepcopy(compiled["plan"])
            operation = next(
                item
                for item in plan["operations"]
                if item.get("path") == "codex/runtime-status.json"
            )
            self.assertEqual(operation["action"], "CREATE")
            operation["operation"] = "CONFLICT"
            plan["plan_digest"] = digest_value(
                {**plan, "plan_digest": ""}
            )
            with self.assertRaisesRegex(InstallerError, "operation/action"):
                build_install_package(
                    distribution,
                    plan,
                    self.statuses["codex"],
                    project_root=Path(project_dir),
                )


class ScopeCompositionTests(IntegrationCheckpointTestCase):
    def test_generic_user_preview_and_claude_specialization_are_not_authorization(self):
        generic = build_user_scope_preview(self.statuses["claude-code"], self.snapshot)
        claude = build_claude_user_preview(self.statuses["claude-code"], self.snapshot)

        self.assertFalse(generic["apply_allowed"])
        self.assertFalse(claude["apply_allowed"])
        self.assertEqual(generic["scope"], "USER")
        self.assertEqual(claude["scope"], "USER")
        self.assertIn("runtime_target", generic)
        self.assertIn("claude", claude)
        self.assertNotEqual(
            generic["user_scope_contract_digest"], claude["contract_digest"]
        )
        self.assertNotIn("package_digest", generic)
        self.assertNotIn("package_digest", claude)
        self.assertFalse(load_claude_user_contract()["apply_allowed"])

    def test_project_user_migration_is_two_independent_descriptive_transactions(self):
        migration = plan_project_user_migration(
            project_package_digest="sha256:" + "1" * 64,
            user_preview_digest="sha256:" + "2" * 64,
        )
        self.assertEqual(migration["operation"], "INSTALL_USER_SEPARATELY")
        self.assertFalse(migration["shared_transaction"])
        self.assertFalse(migration["automatic_project_delete"])

    def test_uninstall_cleanup_does_not_require_runtime_executable(self):
        with tempfile.TemporaryDirectory() as distribution_dir, tempfile.TemporaryDirectory() as project_dir:
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            package = self.make_package(distribution, project)
            self.assertEqual(
                apply_install_package(package, distribution, project)["status"],
                "APPLIED",
            )
            with patch(
                "tools.v3.installer.detect_runtime",
                side_effect=AssertionError("cleanup must not probe runtime"),
            ):
                result = apply_uninstall(runtime_id="codex", project_root=project)
            self.assertEqual(result["status"], "UNINSTALLED")


class StaleChainTests(IntegrationCheckpointTestCase):
    def test_runtime_contract_digest_is_bound_to_distribution_before_apply(self):
        with tempfile.TemporaryDirectory() as distribution_dir, tempfile.TemporaryDirectory() as project_dir:
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            package = self.make_package(distribution, project)
            tampered = copy.deepcopy(package)
            tampered["runtime_contract_digest"] = "sha256:" + "9" * 64
            tampered["package_digest"] = digest_value(
                {**tampered, "package_digest": ""}
            )
            with self.assertRaisesRegex(InstallerError, "runtime contract"):
                apply_install_package(tampered, distribution, project)
            self.assertEqual(list(project.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
