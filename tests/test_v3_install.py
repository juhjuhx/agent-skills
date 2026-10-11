"""Installer contract tests use disposable homes and local fixture repositories."""

import json
import importlib.util
import os
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_v3.py"


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / "test home"
        self.home.mkdir()
        self.source = self.base / "repo"
        self.source.mkdir()
        for name in ("using-superpowers", "debugging", "visual"):
            p = self.source / name / "SKILL.md"
            p.parent.mkdir()
            p.write_text(f"---\nname: {name}\ndescription: {name} skill\n---\n")
        manifest = {
            "categories": [
                {"id": "essential", "skills": ["using-superpowers"]},
                {"id": "coding", "skills": ["debugging"]},
                {"id": "design", "skills": ["visual"]},
            ],
            "profiles": {
                "minimal": {"categories": ["essential", "coding"]},
                "default": {"categories": ["essential", "coding", "design"]},
                "full": {"categories": ["essential", "coding", "design"]},
            },
        }
        (self.source / "categories.json").write_text(json.dumps(manifest))
        for relative in (
            "runtime/skills-router/adapters/opencode/skills-router.js",
            "runtime/skills-router/adapters/opencode/工具大師V3.md",
        ):
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "add",
                "using-superpowers",
                "debugging",
                "visual",
                "categories.json",
                "runtime",
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            check=True,
        )

    def call(self, *args):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--home",
                str(self.home),
                "--repo",
                str(self.source),
                *args,
            ],
            text=True,
            capture_output=True,
            timeout=15,
        )

    def test_fresh_minimal_and_native_mother(self):
        p = self.call("--minimal", "--no-links")
        self.assertEqual(p.returncode, 0, p.stderr)
        enabled = self.home / ".agents/skills-enabled"
        self.assertTrue((enabled / "using-superpowers/SKILL.md").is_file())
        self.assertTrue((enabled / "debugging/SKILL.md").is_file())
        self.assertFalse((enabled / "visual").exists())
        self.assertFalse((self.home / ".config/opencode/plugins").exists())

    def test_default_profile(self):
        p = self.call("--default", "--no-links")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(
            (self.home / ".agents/skills-enabled/visual/SKILL.md").is_file()
        )

    def test_dirty_checkout_is_refused_before_mutation(self):
        self.assertEqual(self.call("--minimal", "--no-links").returncode, 0)
        target = self.home / ".agents/skills"
        marker = target / "owned.txt"
        marker.write_text("USER WORK KEEP")
        enabled = self.home / ".agents/skills-enabled"
        previous = {p.name: str(p.readlink()) for p in enabled.iterdir()}
        p = self.call("--all", "--update", "--no-links")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(marker.read_text(), "USER WORK KEEP")
        self.assertEqual(
            {p.name: str(p.readlink()) for p in enabled.iterdir()}, previous
        )

    def test_existing_host_directory_is_preserved(self):
        target = self.home / ".config/opencode/skills"
        target.mkdir(parents=True)
        (target / "user.txt").write_text("KEEP")
        p = self.call("--minimal")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(target.is_symlink())
        self.assertEqual((target / "user.txt").read_text(), "KEEP")

    def test_user_enabled_directory_is_not_deleted(self):
        p = self.home / ".agents/skills-enabled"
        p.mkdir(parents=True)
        (p / "private.md").write_text("KEEP")
        result = self.call("--minimal", "--no-links")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((p / "private.md").read_text(), "KEEP")

    def test_category_traversal_is_rejected(self):
        p = self.call("--category", "../outside", "--no-links")
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse((self.home / ".agents/skills-enabled").exists())

    def test_wrong_remote_existing_checkout_is_refused(self):
        self.assertEqual(self.call("--minimal", "--no-links").returncode, 0)
        target = self.home / ".agents/skills"
        subprocess.run(
            [
                "git",
                "-C",
                str(target),
                "remote",
                "set-url",
                "origin",
                "https://example.invalid/wrong.git",
            ],
            check=True,
        )
        p = self.call("--minimal", "--update", "--no-links")
        self.assertNotEqual(p.returncode, 0)

    def test_help_does_not_create_target(self):
        p = self.call("--help")
        self.assertEqual(p.returncode, 0)
        self.assertFalse((self.home / ".agents").exists())

    def test_optional_adapter_never_changes_global_settings(self):
        config = self.home / ".config/opencode/opencode.json"
        config.parent.mkdir(parents=True)
        data = '{"model":"user/model","default_agent":"user-agent","permission":{"bash":"ask"}}'
        config.write_text(data)
        result = self.call("--minimal", "--opencode-advisory", "--no-links")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config.read_text(), data)
        self.assertEqual(
            (self.home / ".config/opencode/plugins/skills-router.js").read_bytes(),
            (
                ROOT / "runtime/skills-router/adapters/opencode/skills-router.js"
            ).read_bytes(),
        )
        self.assertTrue((self.home / ".config/opencode/agents/工具大師V3.md").is_file())

    def test_optional_adapter_refuses_existing_legacy_file(self):
        path = self.home / ".config/opencode/plugins/skills-router.js"
        path.parent.mkdir(parents=True)
        path.write_text("USER OR LEGACY KEEP")
        result = self.call("--minimal", "--opencode-advisory", "--no-links")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_text(), "USER OR LEGACY KEEP")
        self.assertFalse((self.home / ".agents/skills").exists())

    def test_external_agents_parent_is_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.home / ".agents").symlink_to(outside, target_is_directory=True)
        result = self.call("--minimal", "--no-links")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def fixture_commit(self, repo, path):
        subprocess.run(["git", "-C", str(repo), "add", path], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "fixture update",
            ],
            check=True,
        )

    def test_update_preserves_ignored_user_files(self):
        self.assertEqual(self.call("--minimal", "--no-links").returncode, 0)
        target = self.home / ".agents/skills"
        (target / ".git/info/exclude").write_text("user-owned.bin\n")
        (target / "user-owned.bin").write_text("USER KEEP")
        (self.source / "user-owned.bin").write_text("UPSTREAM COPY")
        self.fixture_commit(self.source, "user-owned.bin")
        result = self.call("--minimal", "--no-links", "--update")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((target / "user-owned.bin").read_text(), "USER KEEP")

    def test_update_refuses_foreign_upstream_even_when_origin_matches(self):
        self.assertEqual(self.call("--minimal", "--no-links").returncode, 0)
        target = self.home / ".agents/skills"
        other = self.base / "other"
        subprocess.run(["git", "clone", "-q", str(self.source), str(other)], check=True)
        (other / "foreign.txt").write_text("FOREIGN")
        self.fixture_commit(other, "foreign.txt")
        branch = subprocess.check_output(
            ["git", "-C", str(other), "branch", "--show-current"], text=True
        ).strip()
        subprocess.run(
            ["git", "-C", str(target), "remote", "add", "other", str(other)], check=True
        )
        subprocess.run(["git", "-C", str(target), "fetch", "-q", "other"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(target),
                "branch",
                "--set-upstream-to",
                f"other/{branch}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        result = self.call("--minimal", "--no-links", "--update")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((target / "foreign.txt").exists())

    def test_configuration_storage_failure_does_not_activate_new_profile(self):
        self.assertEqual(self.call("--minimal", "--no-links").returncode, 0)
        enabled = self.home / ".agents/skills-enabled"
        config = self.home / ".agents/skills-config.json"
        before = config.read_bytes()
        spec = importlib.util.spec_from_file_location("installer_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = Path.write_text

        def fail_config(path, data, *args, **kwargs):
            if '"installer": "personal-tool-master-v3"' in data:
                raise OSError("fixture storage unavailable")
            return original(path, data, *args, **kwargs)

        with patch.object(Path, "write_text", fail_config):
            with self.assertRaises(OSError):
                module.main(
                    [
                        "--home",
                        str(self.home),
                        "--repo",
                        str(self.source),
                        "--all",
                        "--no-links",
                    ]
                )
        self.assertEqual(config.read_bytes(), before)
        self.assertFalse((enabled / "visual").exists())
        self.assertEqual(self.call("--minimal", "--no-links").returncode, 0)

    def test_missing_optional_source_leaves_no_half_plugin(self):
        subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "rm",
                "runtime/skills-router/adapters/opencode/工具大師V3.md",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "missing fixture source",
            ],
            check=True,
        )
        result = self.call("--minimal", "--no-links", "--opencode-advisory")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            (self.home / ".config/opencode/plugins/skills-router.js").exists()
        )

    def test_backup_placeholder_failure_does_not_replace_valid_config(self):
        self.assertEqual(self.call("--minimal", "--no-links").returncode, 0)
        config = self.home / ".agents/skills-config.json"
        before = config.read_bytes()
        spec = importlib.util.spec_from_file_location("installer_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        unlink = Path.unlink
        failed = False

        def fail_placeholder(path, *args, **kwargs):
            nonlocal failed
            if (
                not failed
                and path.parent.resolve() == config.parent.resolve()
                and path.name.startswith("v3-install-")
                and path.is_file()
                and path.stat().st_size == 0
            ):
                failed = True
                raise OSError("fixture backup placeholder failure")
            return unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", fail_placeholder):
            with self.assertRaises(OSError):
                module.main(
                    [
                        "--home",
                        str(self.home),
                        "--repo",
                        str(self.source),
                        "--all",
                        "--no-links",
                    ]
                )
        self.assertTrue(failed)
        self.assertEqual(config.read_bytes(), before)
        self.assertFalse((self.home / ".agents/skills-enabled/visual").exists())
        self.assertEqual(self.call("--minimal", "--no-links").returncode, 0)

    def test_host_link_failure_rolls_back_and_allows_retry(self):
        host = self.home / ".claude"
        host.mkdir()
        host.chmod(0o555)
        try:
            failed = self.call("--minimal", "--opencode-advisory")
        finally:
            host.chmod(0o755)
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse((self.home / ".agents/skills-enabled").exists())
        self.assertFalse((self.home / ".agents/skills-config.json").exists())
        self.assertFalse(
            (self.home / ".config/opencode/plugins/skills-router.js").exists()
        )
        self.assertFalse((self.home / ".config/opencode/skills").is_symlink())
        retry = self.call("--minimal", "--opencode-advisory")
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertTrue((host / "skills").is_symlink())

    def test_stdin_bootstrap_does_not_trust_cwd_installer(self):
        work = self.base / "work"
        (work / "scripts").mkdir(parents=True)
        (work / "scripts/install_v3.py").write_text(
            'from pathlib import Path; Path("POISON_EXECUTED").write_text("bad")'
        )
        binaries = self.base / "bin"
        binaries.mkdir()
        curl = binaries / "curl"
        curl.write_text("""#!/bin/sh
while [ "$#" -gt 0 ]; do
 if [ "$1" = "-o" ]; then
  shift
  printf '%s\\n' 'print("trusted download")' > "$1"
  exit 0
 fi
 shift
done
exit 1
""")
        curl.chmod(0o755)
        result = subprocess.run(
            ["bash"],
            input=(ROOT / "install.sh").read_text(),
            cwd=work,
            env={**os.environ, "PATH": str(binaries) + os.pathsep + os.environ["PATH"]},
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((work / "POISON_EXECUTED").exists())
        self.assertIn("trusted download", result.stdout)


if __name__ == "__main__":
    unittest.main()
