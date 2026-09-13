"""Focused tests for the generic ASM user-data destination contract."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.v3.asm_user_data import (
    ASMUserDataError,
    ASMUserDataStaleError,
    observe_asm_user_data_path,
    revalidate_asm_user_data_root,
    resolve_asm_user_data_root,
)


class ASMUserDataContractTests(unittest.TestCase):
    def test_macos_fixture_resolution_is_symbolic_and_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            before = sorted(path.relative_to(home).as_posix() for path in home.rglob("*"))

            resolution = resolve_asm_user_data_root(
                home_root=home,
                platform="macos",
                allow_fixture_root=True,
            )

            after = sorted(path.relative_to(home).as_posix() for path in home.rglob("*"))
            self.assertEqual(before, after)
            self.assertEqual(resolution.state, "EXPECTED_ABSENT")
            self.assertEqual(resolution.symbolic_root, "${ASM_USER_DATA}")
            self.assertFalse(resolution.resolved_path.exists())
            self.assertTrue(resolution.parent_identity.startswith("sha256:"))
            public = resolution.to_public_dict()
            self.assertNotIn(str(home), str(public))
            self.assertNotIn("resolved_path", public)
            self.assertFalse(public["actual_path_persisted"])

    def test_revalidation_accepts_unchanged_absent_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            resolution = resolve_asm_user_data_root(
                home_root=home,
                platform="macos",
                allow_fixture_root=True,
            )
            refreshed = revalidate_asm_user_data_root(resolution)
            self.assertEqual(refreshed.root_identity, resolution.root_identity)
            self.assertEqual(refreshed.parent_identity, resolution.parent_identity)

    def test_revalidation_rejects_root_state_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            resolution = resolve_asm_user_data_root(
                home_root=home,
                platform="macos",
                allow_fixture_root=True,
            )
            resolution.resolved_path.mkdir(parents=True)
            with self.assertRaises(ASMUserDataStaleError):
                revalidate_asm_user_data_root(resolution)

    def test_existing_symlink_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            target = Path(directory) / "outside"
            target.mkdir()
            root = home / "Library" / "Application Support" / "Agent Skills Matrix"
            root.parent.mkdir(parents=True)
            root.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ASMUserDataError):
                resolve_asm_user_data_root(
                    home_root=home,
                    platform="macos",
                    allow_fixture_root=True,
                )

    def test_managed_subroot_symlink_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            resolution = resolve_asm_user_data_root(
                home_root=home,
                platform="macos",
                allow_fixture_root=True,
            )
            resolution.resolved_path.mkdir(parents=True)
            outside = Path(directory) / "outside"
            outside.mkdir()
            (resolution.resolved_path / "v3").mkdir()
            (resolution.resolved_path / "v3" / "claude").symlink_to(
                outside,
                target_is_directory=True,
            )
            with self.assertRaises(ASMUserDataError):
                observe_asm_user_data_path(resolution, "v3/claude")

    def test_unknown_platform_and_unsafe_production_fixture_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            with self.assertRaises(ASMUserDataError):
                resolve_asm_user_data_root(
                    home_root=home,
                    platform="plan9",
                    allow_fixture_root=True,
                )
            with self.assertRaises(ASMUserDataError):
                resolve_asm_user_data_root(
                    home_root=home,
                    platform="macos",
                    allow_fixture_root=False,
                )

    def test_linux_windows_and_macos_resolution_rules_are_symbolic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            home = root / "home"
            xdg = root / "xdg-data"
            local = root / "local-app-data"
            home.mkdir()
            xdg.mkdir()
            local.mkdir()
            cases = (
                (
                    "linux",
                    {"XDG_DATA_HOME": str(xdg)},
                    "${XDG_DATA_HOME}/agent-skills-matrix",
                ),
                (
                    "windows",
                    {"LOCALAPPDATA": str(local)},
                    "${LOCALAPPDATA}/Agent Skills Matrix",
                ),
                (
                    "macos",
                    {},
                    "${HOME}/Library/Application Support/Agent Skills Matrix",
                ),
            )
            for platform, environ, rule in cases:
                with self.subTest(platform=platform):
                    resolution = resolve_asm_user_data_root(
                        home_root=home,
                        platform=platform,
                        environ=environ,
                        allow_fixture_root=True,
                    )
                    self.assertEqual(resolution.resolution_rule, rule)
                    self.assertEqual(resolution.state, "EXPECTED_ABSENT")
                    self.assertFalse(resolution.to_public_dict()["actual_path_persisted"])

    def test_platform_data_override_with_symlink_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            home = root / "home"
            target = root / "real-data"
            link = root / "linked-data"
            home.mkdir()
            target.mkdir()
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ASMUserDataError, "symlink"):
                resolve_asm_user_data_root(
                    home_root=home,
                    platform="linux",
                    environ={"XDG_DATA_HOME": str(link)},
                    allow_fixture_root=True,
                )


if __name__ == "__main__":
    unittest.main()
