"""Phase 3O read-only Claude real-home canary preparation tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools.v3.claude_canary import (
    CANARY_MAX_SKILLS,
    CanaryPreparationError,
    build_canary_preview,
    build_status_report,
    inventory_claude_personal_scope,
    select_canary_skills,
)
from tools.v3.installer import main
from tools.v3.productization import load_runtime_inventory
from tools.v3.routing_catalog import RoutingCatalogSnapshot


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
OVERLAY = ROOT / "registry/v3/skill-routing-metadata.json"


class ClaudeRealHomeCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = RoutingCatalogSnapshot.from_registry(
            REGISTRY,
            overlay_path=OVERLAY,
            repository_root=ROOT,
        )
        inventory = load_runtime_inventory(fixture_name="ALL_KNOWN_STATIC")
        cls.status = next(
            item for item in inventory["runtimes"] if item["runtime_id"] == "claude-code"
        )

    def test_inventory_is_read_only_and_redacts_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            personal = home / ".claude" / "skills"
            personal.mkdir(parents=True)
            (personal / "unrelated-user-skill").mkdir()
            before = sorted(path.relative_to(home).as_posix() for path in home.rglob("*"))

            inventory = inventory_claude_personal_scope(
                home_root=home,
                project_root=ROOT,
                skill_slugs=("module-map",),
                bundled_skill_slugs=set(),
            )

            after = sorted(path.relative_to(home).as_posix() for path in home.rglob("*"))
            self.assertEqual(before, after)
            self.assertEqual(inventory["symbolic_personal_root"], "${HOME}/.claude/skills")
            self.assertNotIn(str(home), json.dumps(inventory))
            self.assertEqual(inventory["candidates"]["module-map"]["personal"], "ABSENT")

    def test_canary_selection_is_bounded_and_reads_only_selected_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inventory = inventory_claude_personal_scope(
                home_root=Path(directory),
                project_root=ROOT,
                skill_slugs=("module-map",),
                bundled_skill_slugs=set(),
            )
            selected = select_canary_skills(
                self.snapshot,
                inventory,
                candidate_ids=("module-map",),
            )
            self.assertEqual([item["skill_id"] for item in selected], ["module-map"])
            self.assertEqual(selected[0]["supporting_file_count"], 0)
            self.assertTrue(selected[0]["source_digest"].startswith("sha256:"))
            self.assertNotIn("raw_body", selected[0])
            self.assertNotIn("# Module Map", json.dumps(selected[0]))

    def test_unknown_bundled_evidence_blocks_zero_collision_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            preview = build_canary_preview(
                self.snapshot,
                self.status,
                home_root=Path(directory),
                project_root=ROOT,
                candidate_ids=("module-map",),
            )
            self.assertEqual(preview["status"], "CANARY_PREPARATION_BLOCKED")
            self.assertGreater(preview["collision_report"]["unknown"], 0)
            self.assertFalse(preview["real_home_apply_authorized"])
            self.assertFalse(preview["package_preview"]["apply_allowed"])

    def test_preview_binds_ephemeral_target_without_authorizing_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            before = sorted(path.relative_to(home).as_posix() for path in home.rglob("*"))
            preview = build_canary_preview(
                self.snapshot,
                self.status,
                home_root=home,
                project_root=ROOT,
                candidate_ids=("module-map",),
                bundled_skill_slugs=set(),
            )
            after = sorted(path.relative_to(home).as_posix() for path in home.rglob("*"))
            self.assertEqual(before, after)
            self.assertTrue(preview["package_digest"].startswith("sha256:"))
            self.assertTrue(preview["confirmation_digest"].startswith("sha256:"))
            self.assertFalse(preview["package_preview"]["apply_allowed"])
            self.assertNotIn(str(home), json.dumps(preview))

    def test_canary_selection_rejects_more_than_three_skills(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inventory = inventory_claude_personal_scope(
                home_root=Path(directory),
                project_root=ROOT,
                skill_slugs=("module-map", "full-output-enforcement", "using-superpowers", "brandkit"),
                bundled_skill_slugs=set(),
            )
            with self.assertRaisesRegex(CanaryPreparationError, "at most"):
                select_canary_skills(
                    self.snapshot,
                    inventory,
                    candidate_ids=(
                        "module-map",
                        "full-output-enforcement",
                        "using-superpowers",
                        "brandkit",
                    ),
                )
            self.assertEqual(CANARY_MAX_SKILLS, 3)

    def test_status_report_is_honest_and_path_free(self) -> None:
        report = build_status_report()
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertEqual(report["stage_router"], "READY")
        self.assertEqual(report["claude_user_installer"], "ENGINE_READY / CANARY_PENDING")
        self.assertEqual(report["real_home_canary_status"], "PENDING_READ_ONLY_PREVIEW")
        self.assertEqual(report["claude_live_execution"], "RUNTIME_BLOCKED")
        self.assertEqual(report["codex_live_execution"], "TRANSPORT_BLOCKED")

    def test_canary_preview_cli_does_not_probe_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with (
                redirect_stdout(output),
                patch(
                    "tools.v3.installer.subprocess.run",
                    side_effect=AssertionError("canary preview must not probe runtime"),
                ),
            ):
                result = main(
                    [
                        "canary-preview",
                        "--runtime",
                        "claude-code",
                        "--home-root",
                        directory,
                        "--skills",
                        "module-map",
                        "--format",
                        "json",
                    ]
                )
            self.assertEqual(result, 2)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["status"], "CANARY_PREPARATION_BLOCKED")
            self.assertFalse(payload["real_home_apply_authorized"])

    def test_real_home_apply_remains_rejected(self) -> None:
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
