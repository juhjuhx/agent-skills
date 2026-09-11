"""Focused safety tests for the Phase 3J project installer."""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.v3.contract_validation import validate_instance
from tools.v3.installer import (
    InstallerError,
    apply_install_package,
    apply_revert,
    apply_uninstall,
    build_install_package,
    build_status_only_package,
    detect_runtime,
    load_install_target,
    preview_install,
    preview_revert,
    preview_uninstall,
)
from tools.v3.productization import compile_distribution, load_runtime_inventory
from tools.v3.routing_catalog import RoutingCatalogSnapshot


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
OVERLAY = ROOT / "registry/v3/skill-routing-metadata.json"


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class InstallerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = RoutingCatalogSnapshot.from_registry(
            REGISTRY,
            overlay_path=OVERLAY,
            repository_root=ROOT,
        )
        inventory = load_runtime_inventory(fixture_name="ALL_KNOWN_STATIC")
        self.statuses = {item["runtime_id"]: item for item in inventory["runtimes"]}

    def compile_codex(
        self, output: Path, *, status: dict | None = None, route: dict | None = None
    ) -> dict:
        return compile_distribution(
            runtime_status=copy.deepcopy(status or self.statuses["codex"]),
            snapshot=self.snapshot,
            output_dir=output,
            stage_route=route,
            repository_root=ROOT,
        )

    def package(
        self, distribution: Path, project: Path, *, status: dict | None = None
    ) -> dict:
        status = copy.deepcopy(status or self.statuses["codex"])
        compiled = self.compile_codex(distribution, status=status)
        return build_install_package(
            distribution,
            compiled["plan"],
            status,
            project_root=project,
        )


class ContractAndScopeTests(InstallerTestCase):
    def test_package_and_result_have_small_machine_contracts(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            package = self.package(Path(distribution_dir), Path(project_dir))
            self.assertTrue(validate_instance("InstallPackage", package).valid)
            result = preview_install(package)
            self.assertTrue(validate_instance("ApplyResult", result).valid)
            self.assertFalse(package["apply_allowed"] is False)
            self.assertFalse(result["sensitive_data_serialized"])

    def test_lifecycle_separates_persistent_and_execution_ephemeral_artifacts(self):
        route = load_json("fixtures/v3/routes/no-skill-needed.json")
        route["registry_epoch"] = self.snapshot.registry_epoch
        route["task_id"] = "T-phase3j-no-skill"
        route["route_id"] = "R-phase3j-no-skill"
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            compiled = self.compile_codex(Path(distribution_dir), route=route)
            package = build_install_package(
                Path(distribution_dir),
                compiled["plan"],
                self.statuses["codex"],
                project_root=Path(project_dir),
            )
            self.assertTrue(package["artifacts"])
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

    def test_status_only_runtime_never_gets_fake_artifacts(self):
        package = build_status_only_package(self.statuses["hermes"], scope="USER")
        self.assertEqual(package["artifacts"], [])
        self.assertFalse(package["installable"])
        self.assertFalse(package["apply_allowed"])
        self.assertTrue(validate_instance("InstallPackage", package).valid)

    def test_user_and_global_apply_fail_closed(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            compiled = self.compile_codex(Path(distribution_dir))
            package = build_install_package(
                Path(distribution_dir),
                compiled["plan"],
                self.statuses["codex"],
                scope="USER",
            )
            self.assertFalse(package["apply_allowed"])
            self.assertEqual(preview_install(package)["status"], "PREVIEWED")
            with self.assertRaises(InstallerError):
                apply_install_package(package, distribution_dir, project_dir)

    def test_action_is_authoritative_and_lifecycle_is_in_plan(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            compiled = self.compile_codex(Path(distribution_dir))
            plan = compiled["plan"]
            artifact = next(
                item
                for item in plan["artifacts"]
                if item["kind"] == "RUNTIME_PRODUCT_STATUS"
            )
            operation = next(
                item
                for item in plan["operations"]
                if item.get("path") == artifact["path"]
            )
            self.assertEqual(operation["action"], "CREATE")
            self.assertEqual(operation["operation"], "CREATE_GENERATED_FILE")
            self.assertEqual(operation["lifecycle"], artifact["lifecycle"])
            package = build_install_package(
                Path(distribution_dir),
                plan,
                self.statuses["codex"],
                project_root=Path(project_dir),
            )
            self.assertEqual(package["artifacts"][0]["action"], "CREATE")

    def test_unsupported_runtime_version_is_not_installable(self):
        target = load_install_target("codex")
        calls = []

        def fake_runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return SimpleNamespace(
                returncode=0,
                stdout="codex-cli 9.9.9",
                stderr="secret-looking diagnostic",
            )

        result = detect_runtime(
            "codex",
            target=target,
            executable="/tmp/fake-codex",
            which=lambda _: "/tmp/fake-codex",
            runner=fake_runner,
        )
        self.assertEqual(result["contract_status"], "UNVERIFIED_INSTALL_CONTRACT")
        self.assertFalse(result["installable"])
        self.assertNotIn("secret-looking", json.dumps(result))
        self.assertEqual(calls[0][0], ["/tmp/fake-codex", "--version"])
        self.assertFalse(calls[0][1]["shell"])


class ProjectTransactionTests(InstallerTestCase):
    def test_clean_project_install_is_reversible_and_does_not_touch_runtime_configs(
        self,
    ):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            package = self.package(distribution, project)
            result = apply_install_package(package, distribution, project)
            self.assertEqual(result["status"], "APPLIED")
            self.assertTrue(
                (project / ".agent-skills-matrix/codex/.asm-installed.json").is_file()
            )
            self.assertFalse((project / ".codex/config.toml").exists())
            self.assertFalse((project / ".claude/settings.json").exists())
            self.assertFalse((project / ".opencode/opencode.json").exists())
            self.assertEqual(
                preview_uninstall(runtime_id="codex", project_root=project)["status"],
                "PREVIEWED",
            )
            uninstall = apply_uninstall(runtime_id="codex", project_root=project)
            self.assertEqual(uninstall["status"], "UNINSTALLED")
            self.assertFalse(
                (project / ".agent-skills-matrix/codex/.asm-installed.json").exists()
            )

    def test_repeat_apply_is_a_true_no_op(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            first = self.package(distribution, project)
            self.assertEqual(
                apply_install_package(first, distribution, project)["status"], "APPLIED"
            )
            second = self.package(distribution, project)
            self.assertTrue(
                all(item["action"] == "NO_OP" for item in second["artifacts"])
            )
            marker = project / ".agent-skills-matrix/codex/.asm-installed.json"
            before = marker.read_bytes()
            result = apply_install_package(second, distribution, project)
            self.assertEqual(result["status"], "NO_OP")
            self.assertEqual(marker.read_bytes(), before)

    def test_user_owned_collision_aborts_before_any_new_file_is_written(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            collision = project / ".agent-skills-matrix/codex/adapter-manifest.json"
            collision.parent.mkdir(parents=True)
            collision.write_text("user-owned", encoding="utf-8")
            package = self.package(distribution, project)
            self.assertEqual(
                next(
                    item
                    for item in package["artifacts"]
                    if item["destination_path"]
                    == collision.relative_to(project).as_posix()
                )["action"],
                "SKIP_USER_OWNED",
            )
            result = apply_install_package(package, distribution, project)
            self.assertEqual(result["status"], "CONFLICT")
            self.assertEqual(collision.read_text(encoding="utf-8"), "user-owned")
            self.assertFalse(
                (project / ".agent-skills-matrix/codex/runtime-status.json").exists()
            )

    def test_modified_managed_artifact_is_not_overwritten(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            package = self.package(distribution, project)
            apply_install_package(package, distribution, project)
            target = project / ".agent-skills-matrix/codex/runtime-status.json"
            target.write_text("modified by user", encoding="utf-8")
            next_package = self.package(distribution, project)
            item = next(
                item
                for item in next_package["artifacts"]
                if item["destination_path"] == target.relative_to(project).as_posix()
            )
            self.assertEqual(item["expected_state"], "MODIFIED_MANAGED")
            self.assertEqual(item["action"], "CONFLICT")
            self.assertEqual(
                apply_install_package(next_package, distribution, project)["status"],
                "CONFLICT",
            )
            self.assertEqual(target.read_text(encoding="utf-8"), "modified by user")

    def test_destination_change_between_preview_and_apply_is_stale(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            package = self.package(distribution, project)
            changed = project / ".agent-skills-matrix/codex/runtime-status.json"
            changed.parent.mkdir(parents=True)
            changed.write_text("changed after preview", encoding="utf-8")
            with self.assertRaisesRegex(InstallerError, "STALE_PLAN"):
                apply_install_package(package, distribution, project)

    def test_symlink_target_or_parent_is_never_followed(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
            tempfile.TemporaryDirectory() as outside_dir,
        ):
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            package = self.package(distribution, project)
            link = project / ".agent-skills-matrix"
            link.symlink_to(outside_dir, target_is_directory=True)
            with self.assertRaises(InstallerError):
                apply_install_package(package, distribution, project)
            self.assertEqual(list(Path(outside_dir).iterdir()), [])

    def test_tampered_marker_cannot_rebind_target_or_backup_paths(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            package = self.package(distribution, project)
            apply_install_package(package, distribution, project)
            marker_path = project / ".agent-skills-matrix/codex/.asm-installed.json"
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            marker["marker_path"] = ".agent-skills-matrix/other/.asm-installed.json"
            marker_path.write_text(json.dumps(marker), encoding="utf-8")
            with self.assertRaisesRegex(InstallerError, "marker path binding"):
                preview_uninstall(runtime_id="codex", project_root=project)

        with (
            tempfile.TemporaryDirectory() as first_dir,
            tempfile.TemporaryDirectory() as second_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            first = Path(first_dir)
            second = Path(second_dir)
            project = Path(project_dir)
            apply_install_package(self.package(first, project), first, project)
            changed_status = copy.deepcopy(self.statuses["codex"])
            changed_status["evidence_refs"] = changed_status["evidence_refs"] + [
                "docs/v3/evidence/SAFE_PROJECT_INSTALLER_V1.md"
            ]
            upgraded = self.package(second, project, status=changed_status)
            applied = apply_install_package(upgraded, second, project)
            marker_path = project / ".agent-skills-matrix/codex/.asm-installed.json"
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            marker["backups"][0]["backup_path"] = ".outside-backup.bin"
            marker_path.write_text(json.dumps(marker), encoding="utf-8")
            with self.assertRaisesRegex(InstallerError, "outside its target root"):
                preview_revert(
                    runtime_id="codex",
                    project_root=project,
                    transaction_id=applied["transaction_id"],
                )

    def test_fault_injection_rolls_back_known_created_files(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            package = self.package(distribution, project)
            calls = {"count": 0}

            def fail_on_second(source, target):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise OSError("injected replace failure")
                os.replace(source, target)

            result = apply_install_package(
                package, distribution, project, replace_fn=fail_on_second
            )
            self.assertEqual(result["status"], "ROLLED_BACK")
            self.assertEqual(result["rollback_status"], "SUCCEEDED")
            self.assertFalse(
                (project / ".agent-skills-matrix/codex/.asm-installed.json").exists()
            )
            self.assertFalse(
                (project / ".agent-skills-matrix/codex/adapter-manifest.json").exists()
            )

    def test_managed_upgrade_records_backup_and_revert_restores_exact_previous_bytes(
        self,
    ):
        with (
            tempfile.TemporaryDirectory() as first_dir,
            tempfile.TemporaryDirectory() as second_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            first = Path(first_dir)
            second = Path(second_dir)
            project = Path(project_dir)
            first_package = self.package(first, project)
            apply_install_package(first_package, first, project)
            old_status = (
                project / ".agent-skills-matrix/codex/runtime-status.json"
            ).read_bytes()
            changed_status = copy.deepcopy(self.statuses["codex"])
            changed_status["evidence_refs"] = changed_status["evidence_refs"] + [
                "docs/v3/evidence/SAFE_PROJECT_INSTALLER_V1.md"
            ]
            second_package = self.package(second, project, status=changed_status)
            self.assertTrue(
                any(
                    item["action"] == "UPDATE_MANAGED"
                    for item in second_package["artifacts"]
                )
            )
            applied = apply_install_package(second_package, second, project)
            self.assertEqual(applied["status"], "APPLIED")
            transaction = applied["transaction_id"]
            self.assertTrue((project / ".agent-skills-matrix/codex/.backups").exists())
            self.assertEqual(
                preview_revert(
                    runtime_id="codex", project_root=project, transaction_id=transaction
                )["status"],
                "PREVIEWED",
            )
            reverted = apply_revert(
                runtime_id="codex", project_root=project, transaction_id=transaction
            )
            self.assertEqual(reverted["status"], "REVERTED")
            self.assertEqual(
                (
                    project / ".agent-skills-matrix/codex/runtime-status.json"
                ).read_bytes(),
                old_status,
            )

    def test_uninstall_refuses_modified_created_artifact(self):
        with (
            tempfile.TemporaryDirectory() as distribution_dir,
            tempfile.TemporaryDirectory() as project_dir,
        ):
            distribution = Path(distribution_dir)
            project = Path(project_dir)
            package = self.package(distribution, project)
            apply_install_package(package, distribution, project)
            target = project / ".agent-skills-matrix/codex/runtime-status.json"
            target.write_bytes(target.read_bytes() + b"user change")
            preview = preview_uninstall(runtime_id="codex", project_root=project)
            self.assertEqual(preview["status"], "CONFLICT")
            result = apply_uninstall(runtime_id="codex", project_root=project)
            self.assertEqual(result["status"], "CONFLICT")
            self.assertTrue(target.exists())

    def test_import_and_package_build_do_not_probe_runtimes(self):
        with patch("tools.v3.installer.subprocess.run") as run:
            with (
                tempfile.TemporaryDirectory() as distribution_dir,
                tempfile.TemporaryDirectory() as project_dir,
            ):
                self.package(Path(distribution_dir), Path(project_dir))
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
