"""Phase 3L Claude Code user-scope contract tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from tools.v3.claude_user_scope import (
    CLAUDE_RUNTIME_VERSION,
    ClaudeUserScopeError,
    build_claude_user_preview,
    classify_claude_collision,
    classify_claude_link_lifecycle,
    classify_claude_upgrade,
    load_claude_distribution_strategy,
    load_claude_user_contract,
    load_claude_user_lifecycle,
    measure_claude_distribution_size,
    validate_claude_skill_slug,
    validate_claude_skill_slugs,
)
from tools.v3.installer import main
from tools.v3.productization import load_runtime_inventory
from tools.v3.routing_catalog import RoutingCatalogSnapshot


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
OVERLAY = ROOT / "registry/v3/skill-routing-metadata.json"


class ClaudeUserScopeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = RoutingCatalogSnapshot.from_registry(
            REGISTRY,
            overlay_path=OVERLAY,
            repository_root=ROOT,
        )
        inventory = load_runtime_inventory(fixture_name="ALL_KNOWN_STATIC")
        cls.status = next(
            item
            for item in inventory["runtimes"]
            if item["runtime_id"] == "claude-code"
        )


class ContractEvidenceTests(ClaudeUserScopeTestCase):
    def test_contract_is_bound_to_installed_version_and_safe_fingerprint(self):
        contract = load_claude_user_contract()
        self.assertEqual(contract["runtime_id"], "claude-code")
        self.assertEqual(contract["observed_runtime_version"], CLAUDE_RUNTIME_VERSION)
        self.assertEqual(contract["release_tag"], "v2.1.235")
        self.assertEqual(contract["apply_allowed"], False)
        self.assertRegex(
            contract["provenance"]["executable_sha256"], r"^sha256:[0-9a-f]{64}$"
        )
        self.assertNotIn("/Users/", json.dumps(contract, ensure_ascii=False))

    def test_claim_table_keeps_current_docs_separate_from_installed_proof(self):
        contract = load_claude_user_contract()
        claims = {item["claim"]: item for item in contract["claims"]}
        for claim in (
            "personal_skill_root",
            "project_skill_root",
            "precedence",
            "directory_symlink",
            "file_symlink",
            "bundled_collision",
            "synced_collision",
        ):
            self.assertIn(claim, claims)
            self.assertIn(
                claims[claim]["current_doc"], {"CURRENT_DOC_SUPPORTED", "UNKNOWN"}
            )
            self.assertIn(
                claims[claim]["release_2_1_235"],
                {"RELEASE_SUPPORTED", "UNKNOWN", "UNSUPPORTED_FOR_APPLY"},
            )
            self.assertIn(
                claims[claim]["installed_artifact"],
                {"INSTALLED_RUNTIME_VERIFIED", "UNKNOWN"},
            )
        self.assertNotEqual(
            claims["personal_skill_root"]["current_doc"],
            "INSTALLED_RUNTIME_VERIFIED",
        )
        self.assertEqual(
            claims["personal_skill_root"]["final_support"],
            "INSTALLED_RUNTIME_VERIFIED",
        )

    def test_personal_and_project_roots_are_distinct_symbolic_paths(self):
        contract = load_claude_user_contract()
        self.assertEqual(contract["personal_skill_root"], "${HOME}/.claude/skills")
        self.assertEqual(contract["project_skill_root"], "${PROJECT}/.claude/skills")
        self.assertEqual(contract["synced_skill_root"], "${HOME}/.claude/skills/synced")
        self.assertEqual(
            {item["case"] for item in contract["precedence_cases"]},
            {
                "PERSONAL_ONLY",
                "PROJECT_ONLY",
                "PERSONAL_AND_PROJECT_SAME_NAME",
                "DIFFERENT_NAMES",
            },
        )

    def test_strategy_fixture_separates_directory_file_and_parent_links(self):
        strategies = load_claude_distribution_strategy()["strategies"]
        by_id = {item["strategy"]: item for item in strategies}
        self.assertEqual(
            by_id["DIRECTORY_SYMLINK"]["final_support"], "CURRENT_DOC_SUPPORTED"
        )
        self.assertEqual(
            by_id["FILE_SYMLINK"]["final_support"], "UNSUPPORTED_FOR_APPLY"
        )
        self.assertEqual(
            by_id["PARENT_DIRECTORY_SYMLINK"]["final_support"], "NOT_SUPPORTED"
        )
        self.assertEqual(by_id["MANAGED_COPY"]["lifecycle"]["modified"], "CONFLICT")

    def test_lifecycle_fixture_is_virtual_home_only_and_complete(self):
        fixture = load_claude_user_lifecycle()
        self.assertFalse(fixture["real_home_access"])
        self.assertEqual(
            set(fixture["collision_states"]),
            {
                "ABSENT",
                "ASM_MANAGED",
                "CLAUDE_SYNCED",
                "USER_OWNED",
                "PROJECT_DUPLICATE",
                "BUNDLED_COLLISION",
                "AMBIGUOUS",
                "UNKNOWN",
            },
        )


class SlugAndLifecycleTests(ClaudeUserScopeTestCase):
    def test_slug_rejects_traversal_and_invalid_segments(self):
        for value in ("", ".", "..", "../escape", "foo/bar", r"foo\\bar", "/absolute"):
            with self.subTest(value=value), self.assertRaises(ClaudeUserScopeError):
                validate_claude_skill_slug(value)

    def test_slug_rejects_windows_reserved_names(self):
        for value in ("CON", "nul", "COM1", "LPT9", "CON.md"):
            with self.subTest(value=value), self.assertRaises(ClaudeUserScopeError):
                validate_claude_skill_slug(value, platform="windows")

    def test_slug_collision_checks_case_unicode_and_mapping_collisions(self):
        with self.assertRaisesRegex(ClaudeUserScopeError, "case-fold"):
            validate_claude_skill_slugs(["Foo", "foo"])
        with self.assertRaisesRegex(ClaudeUserScopeError, "normalization"):
            validate_claude_skill_slugs(["é", "e\u0301"])
        with self.assertRaisesRegex(ClaudeUserScopeError, "destination"):
            validate_claude_skill_slugs(["foo:bar", "foo-bar"])

    def test_all_collision_states_fail_closed_to_exact_values(self):
        states = (
            "ABSENT",
            "ASM_MANAGED",
            "CLAUDE_SYNCED",
            "USER_OWNED",
            "PROJECT_DUPLICATE",
            "BUNDLED_COLLISION",
            "AMBIGUOUS",
            "UNKNOWN",
        )
        for state in states:
            self.assertEqual(classify_claude_collision(state), state)
        with self.assertRaises(ValueError):
            classify_claude_collision("ADOPT")

    def test_upgrade_requires_exact_ownership_and_explicit_rename(self):
        old = {"skill_id": "foo", "source_digest": "sha256:" + "a" * 64}
        new = {"skill_id": "foo", "source_digest": "sha256:" + "b" * 64}
        self.assertEqual(classify_claude_upgrade(None, new), "ADDED")
        self.assertEqual(classify_claude_upgrade(old, None), "REMOVED")
        self.assertEqual(classify_claude_upgrade(old, new), "CONTENT_UPDATED")
        self.assertEqual(
            classify_claude_upgrade(old, new, current_state="MODIFIED_MANAGED"),
            "USER_MODIFIED_CONFLICT",
        )
        with self.assertRaisesRegex(ValueError, "explicit"):
            classify_claude_upgrade(
                old, {"skill_id": "bar", "source_digest": new["source_digest"]}
            )
        self.assertEqual(
            classify_claude_upgrade(
                old,
                {"skill_id": "bar", "source_digest": new["source_digest"]},
                explicit_rename=True,
            ),
            "EXPLICIT_RENAMED",
        )

    def test_link_lifecycle_detects_relocation_and_broken_target(self):
        self.assertEqual(
            classify_claude_link_lifecycle(
                "DIRECTORY_SYMLINK", target_exists=True, target_digest_matches=True
            ),
            "BOUND",
        )
        self.assertEqual(
            classify_claude_link_lifecycle(
                "DIRECTORY_SYMLINK", target_exists=False, target_digest_matches=False
            ),
            "BROKEN_TARGET",
        )
        self.assertEqual(
            classify_claude_link_lifecycle(
                "DIRECTORY_SYMLINK",
                target_exists=True,
                target_digest_matches=False,
                repository_relocated=True,
            ),
            "REPOSITORY_RELOCATION_REQUIRES_REVALIDATION",
        )


class PreviewAndIsolationTests(ClaudeUserScopeTestCase):
    def test_preview_is_deterministic_and_exposes_claude_contract_layers(self):
        first = build_claude_user_preview(self.status, self.snapshot, platform="macos")
        second = build_claude_user_preview(self.status, self.snapshot, platform="macos")
        self.assertEqual(first, second)
        self.assertFalse(first["apply_allowed"])
        self.assertTrue(first["no_actual_writes"])
        self.assertEqual(
            first["claude"]["personal_skill_root"], "${HOME}/.claude/skills"
        )
        self.assertEqual(
            first["claude"]["project_skill_root"], "${PROJECT}/.claude/skills"
        )
        self.assertEqual(
            first["claude"]["precedence"]["final_support"], "CURRENT_DOC_SUPPORTED"
        )
        self.assertEqual(first["source"]["catalog_body_files_loaded"], 0)
        self.assertEqual(first["source"]["body_files_materialized"], 0)

    def test_preview_rejects_stale_claude_runtime_contract(self):
        status = deepcopy(self.status)
        status["observed_runtime_version"] = "2.1.234"
        with self.assertRaisesRegex(ClaudeUserScopeError, "version"):
            build_claude_user_preview(status, self.snapshot)

    def test_preview_serialization_drops_credentials_and_raw_execution_fields(self):
        status = deepcopy(self.status)
        status.update(
            {
                "api_key": "not-for-evidence",
                "prompt": "raw prompt must not persist",
                "stdout": "raw output must not persist",
            }
        )
        serialized = json.dumps(build_claude_user_preview(status, self.snapshot))
        self.assertNotIn("not-for-evidence", serialized)
        self.assertNotIn("raw prompt must not persist", serialized)
        self.assertNotIn("raw output must not persist", serialized)

    def test_preview_rejects_non_evidence_distribution_fields(self):
        with self.assertRaisesRegex(ClaudeUserScopeError, "non-evidence"):
            build_claude_user_preview(
                self.status,
                self.snapshot,
                distribution_size={
                    "measurement_mode": "NOT_MEASURED",
                    "prompt": "raw prompt",
                },
            )

    def test_strategy_choice_never_falls_back_silently(self):
        preview = build_claude_user_preview(
            self.status, self.snapshot, strategy="DIRECTORY_SYMLINK"
        )
        self.assertEqual(preview["distribution_strategy"], "DIRECTORY_SYMLINK")
        self.assertTrue(
            all(
                item["strategy"] == "DIRECTORY_SYMLINK"
                for item in preview["planned_managed_paths"]
            )
        )
        unsupported = build_claude_user_preview(
            self.status, self.snapshot, strategy="FILE_SYMLINK"
        )
        self.assertEqual(unsupported["distribution_strategy"], "FILE_SYMLINK")
        self.assertEqual(unsupported["planned_managed_paths"], [])

    def test_distribution_measurement_is_explicit_and_does_not_enter_prompt_context(
        self,
    ):
        size = measure_claude_distribution_size(
            self.snapshot, ROOT, strategy="MANAGED_COPY"
        )
        self.assertEqual(size["skill_count"], 214)
        self.assertGreater(size["total_skill_md_bytes"], 0)
        self.assertEqual(size["managed_copy_bytes"], size["total_skill_md_bytes"])
        self.assertEqual(size["symlink_entry_count"], 0)

    def test_virtual_home_behavior_never_touches_real_home(self):
        with tempfile.TemporaryDirectory() as temp:
            virtual_home = Path(temp) / "home"
            project = Path(temp) / "project"
            (virtual_home / ".claude" / "skills" / "foo").mkdir(parents=True)
            (project / ".claude" / "skills" / "foo").mkdir(parents=True)
            (virtual_home / ".claude" / "skills" / "foo" / "SKILL.md").write_text(
                "personal", encoding="utf-8"
            )
            (project / ".claude" / "skills" / "foo" / "SKILL.md").write_text(
                "project", encoding="utf-8"
            )
            skill_id = self.snapshot.records[0]["skill_id"]
            preview = build_claude_user_preview(
                self.status,
                self.snapshot,
                collision_states={skill_id: "PROJECT_DUPLICATE"},
            )
            self.assertEqual(preview["collisions"]["states"]["PROJECT_DUPLICATE"], 1)
            self.assertFalse((virtual_home / ".claude" / "settings.json").exists())

    def test_cli_claude_user_preview_never_probes_or_invokes_claude(self):
        output = io.StringIO()
        with (
            redirect_stdout(output),
            patch(
                "tools.v3.installer.subprocess.run",
                side_effect=AssertionError(
                    "Claude user preview must not probe runtime"
                ),
            ),
        ):
            result = main(
                [
                    "preview",
                    "--runtime",
                    "claude-code",
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
        self.assertEqual(payload["preview"]["claude"]["runtime_id"], "claude-code")
        self.assertFalse(payload["preview"]["apply_allowed"])

    def test_user_apply_guard_remains_unchanged(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "apply",
                    "--runtime",
                    "claude-code",
                    "--scope",
                    "user",
                    "--format",
                    "json",
                ]
            )
        self.assertEqual(result, 2)
        self.assertEqual(
            json.loads(output.getvalue())["error"], "USER_SCOPE_APPLY_NOT_AUTHORIZED"
        )


if __name__ == "__main__":
    unittest.main()
