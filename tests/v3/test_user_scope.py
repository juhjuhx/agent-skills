"""Contract tests for Phase 3K user-scope distribution previews."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from tools.v3.installer import InstallerError, apply_install_package, main
from tools.v3.productization import load_runtime_inventory
from tools.v3.routing_catalog import RoutingCatalogSnapshot
from tools.v3.user_scope import (
    UserScopeError,
    build_user_scope_preview,
    classify_user_collision,
    classify_user_upgrade,
    load_user_scope_contract,
    load_user_lifecycle_fixture,
    plan_project_user_migration,
    user_scope_apply_guard,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
OVERLAY = ROOT / "registry/v3/skill-routing-metadata.json"


class UserScopeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = RoutingCatalogSnapshot.from_registry(
            REGISTRY,
            overlay_path=OVERLAY,
            repository_root=ROOT,
        )
        inventory = load_runtime_inventory(fixture_name="ALL_KNOWN_STATIC")
        cls.statuses = {item["runtime_id"]: item for item in inventory["runtimes"]}
        cls.contract = load_user_scope_contract()


class ContractTests(UserScopeTestCase):
    def test_contract_uses_symbolic_roots_and_never_authorizes_apply(self):
        self.assertEqual(self.contract["scope"], "USER")
        self.assertFalse(self.contract["apply_allowed"])
        for target in self.contract["runtime_targets"]:
            for root in target["native_user_skill_roots"]:
                self.assertTrue(root["path"].startswith("${"))
                self.assertNotIn("/Users/", root["path"])

    def test_target_versions_bind_to_existing_runtime_evidence(self):
        inventory = {item["runtime_id"]: item for item in self.statuses.values()}
        for target in self.contract["runtime_targets"]:
            status = inventory[target["runtime_id"]]
            self.assertEqual(
                target["observed_runtime_version"],
                status["observed_runtime_version"],
            )
            self.assertEqual(
                target["runtime_contract_digest"],
                status["runtime_contract_digest"],
            )

    def test_codex_path_ambiguity_is_explicit(self):
        target = next(
            item
            for item in self.contract["runtime_targets"]
            if item["runtime_id"] == "codex"
        )
        self.assertGreaterEqual(len(target["native_user_skill_roots"]), 2)
        self.assertIn(
            target["native_user_skill_roots"][0]["support"],
            {
                "NATIVE_VERIFIED",
                "NATIVE_RELEASE_SUPPORTED",
                "UPSTREAM_ONLY",
                "LEGACY",
                "UNVERIFIED",
            },
        )
        self.assertFalse(target["apply_allowed"])

    def test_claude_and_opencode_have_separate_native_user_roots(self):
        claude = next(
            item
            for item in self.contract["runtime_targets"]
            if item["runtime_id"] == "claude-code"
        )
        opencode = next(
            item
            for item in self.contract["runtime_targets"]
            if item["runtime_id"] == "opencode"
        )
        self.assertIn(
            "${HOME}/.claude/skills",
            [item["path"] for item in claude["native_user_skill_roots"]],
        )
        self.assertGreaterEqual(len(opencode["native_user_skill_roots"]), 2)
        self.assertIn(
            "${XDG_CONFIG_HOME}/opencode/skills",
            [item["path"] for item in opencode["native_user_skill_roots"]],
        )

    def test_hermes_is_status_only(self):
        target = next(
            item
            for item in self.contract["runtime_targets"]
            if item["runtime_id"] == "hermes"
        )
        self.assertEqual(target["support_classification"], "NOT_IMPLEMENTED")
        self.assertEqual(target["native_user_skill_roots"], [])
        self.assertEqual(target["selected_strategy"], "UNSUPPORTED")


class PreviewTests(UserScopeTestCase):
    def test_runtime_platform_matrix_is_preview_only_and_side_effect_free(self):
        for runtime_id, status in self.statuses.items():
            for platform in ("linux", "macos", "windows"):
                with self.subTest(runtime=runtime_id, platform=platform):
                    preview = build_user_scope_preview(
                        status,
                        self.snapshot,
                        contract=self.contract,
                        platform=platform,
                    )
                    self.assertEqual(preview["scope"], "USER")
                    self.assertFalse(preview["apply_allowed"])
                    self.assertTrue(preview["no_actual_writes"])
                    self.assertNotIn("/Users/", json.dumps(preview, ensure_ascii=False))

    def test_stale_runtime_contract_fails_closed(self):
        status = deepcopy(self.statuses["codex"])
        status["runtime_contract_digest"] = "sha256:" + "f" * 64
        with self.assertRaisesRegex(UserScopeError, "runtime contract digest"):
            build_user_scope_preview(
                status,
                self.snapshot,
                contract=self.contract,
            )

    def test_preview_allowlists_runtime_status_and_drops_credentials(self):
        status = deepcopy(self.statuses["claude-code"])
        status["api_key"] = "secret-value"
        status["session_token"] = "session-secret"
        preview = build_user_scope_preview(
            status,
            self.snapshot,
            contract=self.contract,
        )
        serialized = json.dumps(preview, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("secret-value", serialized)
        self.assertNotIn("session-secret", serialized)

    def test_preview_is_deterministic_symbolic_and_metadata_only(self):
        first = build_user_scope_preview(
            self.statuses["claude-code"],
            self.snapshot,
            contract=self.contract,
            platform="macos",
        )
        second = build_user_scope_preview(
            self.statuses["claude-code"],
            self.snapshot,
            contract=self.contract,
            platform="macos",
        )
        self.assertEqual(first, second)
        self.assertEqual(first["scope"], "USER")
        self.assertFalse(first["apply_allowed"])
        self.assertTrue(first["no_actual_writes"])
        self.assertEqual(first["source"]["skill_count"], 214)
        self.assertEqual(first["source"]["catalog_body_files_loaded"], 0)
        self.assertEqual(first["source"]["body_files_materialized"], 0)
        self.assertTrue(first["planned_managed_paths"])
        serialized = json.dumps(first, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("SKILL.md\n", serialized)

    def test_explicit_symlink_strategy_does_not_fallback_to_copy(self):
        preview = build_user_scope_preview(
            self.statuses["codex"],
            self.snapshot,
            contract=self.contract,
            platform="windows",
            strategy="DIRECTORY_SYMLINK",
        )
        self.assertEqual(preview["distribution_strategy"], "DIRECTORY_SYMLINK")
        self.assertNotEqual(preview["distribution_strategy"], "MANAGED_COPY")
        self.assertFalse(preview["apply_allowed"])
        self.assertTrue(any("fallback" in item.lower() for item in preview["warnings"]))

    def test_windows_precondition_is_preserved_in_preview(self):
        preview = build_user_scope_preview(
            self.statuses["claude-code"],
            self.snapshot,
            contract=self.contract,
            platform="windows",
            strategy="DIRECTORY_SYMLINK",
        )
        self.assertEqual(preview["platform"], "windows")
        self.assertIn(
            preview["strategy_support"],
            {"SUPPORTED", "SUPPORTED_WITH_PRECONDITION", "UNKNOWN", "UNSUPPORTED"},
        )
        self.assertFalse(preview["apply_allowed"])

    def test_file_symlink_remains_unverified_and_is_not_rewritten_as_copy(self):
        preview = build_user_scope_preview(
            self.statuses["claude-code"],
            self.snapshot,
            contract=self.contract,
            platform="macos",
            strategy="FILE_SYMLINK",
        )
        self.assertEqual(preview["distribution_strategy"], "FILE_SYMLINK")
        self.assertNotEqual(preview["distribution_strategy"], "MANAGED_COPY")
        self.assertEqual(preview["strategy_support"], "UNKNOWN")
        self.assertFalse(preview["apply_allowed"])

    def test_config_reference_is_out_of_scope_and_emits_no_fake_paths(self):
        preview = build_user_scope_preview(
            self.statuses["opencode"],
            self.snapshot,
            contract=self.contract,
            platform="macos",
            strategy="CONFIG_REFERENCE",
        )
        self.assertEqual(preview["strategy_support"], "UNSUPPORTED")
        self.assertEqual(preview["planned_managed_paths"], [])
        self.assertFalse(preview["apply_allowed"])

    def test_fixture_collision_state_is_carried_without_adoption(self):
        skill_id = self.snapshot.records[0]["skill_id"]
        preview = build_user_scope_preview(
            self.statuses["claude-code"],
            self.snapshot,
            contract=self.contract,
            collision_states={skill_id: "USER_OWNED"},
        )
        planned = next(
            item
            for item in preview["planned_managed_paths"]
            if item["skill_id"] == skill_id
        )
        self.assertEqual(planned["collision_state"], "USER_OWNED")
        self.assertEqual(preview["collisions"]["states"]["USER_OWNED"], 1)
        self.assertFalse(preview["apply_allowed"])

    def test_unknown_runtime_preview_fails_closed(self):
        status = (
            self.statuses["unknown-runtime"]
            if "unknown-runtime" in self.statuses
            else {
                "runtime_id": "unknown-runtime",
                "runtime_name": "Unknown runtime",
                "observed_runtime_version": None,
                "live_execution": "UNKNOWN",
                "adapter_support": "NOT_IMPLEMENTED",
                "static_contract": "UNVERIFIED",
            }
        )
        preview = build_user_scope_preview(
            status,
            self.snapshot,
            contract=self.contract,
            platform="macos",
        )
        self.assertEqual(preview["distribution_strategy"], "UNSUPPORTED")
        self.assertFalse(preview["apply_allowed"])
        self.assertEqual(preview["planned_managed_paths"], [])


class LifecycleTests(UserScopeTestCase):
    def test_lifecycle_fixture_is_virtual_home_only_and_digest_bound(self):
        fixture = load_user_lifecycle_fixture()
        self.assertEqual(fixture["fixture_kind"], "VIRTUAL_HOME_ONLY")
        self.assertFalse(fixture["real_home_access"])
        self.assertEqual(len(fixture["transitions"]), 5)
        self.assertTrue(
            all(
                item["expected"]
                in {
                    "UNCHANGED",
                    "CONTENT_UPDATED",
                    "ADDED",
                    "REMOVED",
                    "CONFLICT_USER_MODIFIED",
                }
                for item in fixture["transitions"]
            )
        )

    def test_collision_states_are_exact_and_no_adoption_is_possible(self):
        self.assertEqual(classify_user_collision("ABSENT"), "ABSENT")
        self.assertEqual(classify_user_collision("ASM_MANAGED"), "ASM_MANAGED")
        self.assertEqual(classify_user_collision("USER_OWNED"), "USER_OWNED")
        self.assertEqual(classify_user_collision("AMBIGUOUS"), "AMBIGUOUS")
        with self.assertRaises(ValueError):
            classify_user_collision("ADOPT")

    def test_upgrade_classification_covers_add_update_remove_and_conflict(self):
        self.assertEqual(
            classify_user_upgrade(None, {"skill_id": "a", "source_digest": "new"}),
            "ADDED",
        )
        self.assertEqual(
            classify_user_upgrade({"skill_id": "a"}, None),
            "REMOVED",
        )
        self.assertEqual(
            classify_user_upgrade(
                {"skill_id": "a", "source_digest": "same"},
                {"skill_id": "a", "source_digest": "same"},
            ),
            "UNCHANGED",
        )
        self.assertEqual(
            classify_user_upgrade(
                {"skill_id": "a", "source_digest": "old"},
                {"skill_id": "a", "source_digest": "new"},
            ),
            "CONTENT_UPDATED",
        )
        self.assertEqual(
            classify_user_upgrade(
                {"skill_id": "a", "source_digest": "old"},
                {"skill_id": "a", "source_digest": "new"},
                current_state="MODIFIED_MANAGED",
            ),
            "CONFLICT_USER_MODIFIED",
        )

    def test_rename_requires_explicit_evidence(self):
        previous = {"skill_id": "old", "source_digest": "old"}
        current = {"skill_id": "new", "source_digest": "new"}
        with self.assertRaisesRegex(ValueError, "rename requires explicit evidence"):
            classify_user_upgrade(previous, current)
        self.assertEqual(
            classify_user_upgrade(previous, current, explicit_rename=True),
            "RENAMED",
        )

    def test_project_to_user_migration_is_two_independent_operations(self):
        plan = plan_project_user_migration(
            project_package_digest="sha256:" + "a" * 64,
            user_preview_digest="sha256:" + "b" * 64,
        )
        self.assertEqual(plan["operation"], "INSTALL_USER_SEPARATELY")
        self.assertEqual(plan["project_uninstall"], "OPTIONAL_SEPARATE_TRANSACTION")
        self.assertFalse(plan["automatic_project_delete"])

    def test_preview_ownership_and_coexistence_are_exact_and_non_destructive(self):
        preview = build_user_scope_preview(
            self.statuses["opencode"],
            self.snapshot,
            contract=self.contract,
        )
        self.assertEqual(preview["ownership"]["scope"], "EXACT_PATHS")
        self.assertFalse(preview["ownership"]["parent_directories_owned"])
        self.assertTrue(preview["coexistence"]["project_and_user_are_independent"])
        self.assertFalse(preview["coexistence"]["automatic_project_delete"])
        self.assertIn("${ASM_USER_DATA}", preview["user_manifest_path"])
        self.assertEqual(
            preview["lifecycle"]["execution_materialization"], "SELECTED_ONLY"
        )


class CliBoundaryTests(UserScopeTestCase):
    def test_user_apply_is_always_rejected_with_stable_error(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "apply",
                    "--runtime",
                    "codex",
                    "--scope",
                    "user",
                    "--platform",
                    "macos",
                    "--format",
                    "json",
                ]
            )
        self.assertEqual(result, 2)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["error"], "USER_SCOPE_APPLY_NOT_AUTHORIZED")

    def test_user_preview_cli_does_not_need_a_project_or_runtime_process(self):
        output = io.StringIO()
        with (
            redirect_stdout(output),
            patch(
                "tools.v3.installer.subprocess.run",
                side_effect=AssertionError("USER preview must not probe a runtime"),
            ),
        ):
            result = main(
                [
                    "preview",
                    "--runtime",
                    "opencode",
                    "--scope",
                    "user",
                    "--platform",
                    "macos",
                    "--format",
                    "json",
                ]
            )
        self.assertEqual(result, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["preview"]["scope"], "USER")
        self.assertFalse(payload["preview"]["apply_allowed"])
        self.assertEqual(payload["result"]["status"], "PREVIEWED")

    def test_apply_guard_does_not_depend_on_destination_path(self):
        with self.assertRaisesRegex(UserScopeError, "USER_SCOPE_APPLY_NOT_AUTHORIZED"):
            user_scope_apply_guard("USER")
        user_scope_apply_guard("PROJECT")

    def test_direct_installer_apply_rejects_user_before_filesystem_resolution(self):
        with self.assertRaisesRegex(InstallerError, "USER_SCOPE_APPLY_NOT_AUTHORIZED"):
            apply_install_package({"scope": "USER"}, "/path/not/read", "/path/not/read")


if __name__ == "__main__":
    unittest.main()
