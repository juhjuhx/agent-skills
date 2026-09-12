"""Phase 3N Claude USER managed-copy apply and recovery tests.

These tests deliberately use virtual HOME and ASM data roots.  They are the
contract-first boundary for the first USER mutation engine; no Claude process
or provider is involved.
"""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from contextlib import redirect_stdout

from tools.v3.contract_validation import validate_instance
from tools.v3.installer import (
    InstallerError,
    UserTransactionInterrupted,
    apply_user_install_package,
    apply_user_revert_package,
    apply_user_uninstall_package,
    build_claude_user_target,
    build_user_confirmation,
    build_user_install_package,
    build_user_revert_package,
    build_user_uninstall_package,
    recover_user_transaction,
    main,
    _package_digest,
    _user_confirmation_binding,
)
from tools.v3.productization import digest_bytes, load_runtime_inventory
from tools.v3.routing_catalog import RoutingCatalogSnapshot


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
OVERLAY = ROOT / "registry/v3/skill-routing-metadata.json"


class ClaudeUserApplyTestCase(unittest.TestCase):
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
        cls.target = build_claude_user_target(cls.status)

    def subset(self, *skill_ids: str) -> RoutingCatalogSnapshot:
        records = tuple(
            copy.deepcopy(record)
            for record in self.snapshot.records
            if record["skill_id"] in skill_ids
        )
        self.assertEqual(len(records), len(skill_ids))
        return replace(self.snapshot, records=records)

    def package(self, home: Path, asm: Path, snapshot: RoutingCatalogSnapshot | None = None):
        home.mkdir(parents=True, exist_ok=True)
        asm.mkdir(parents=True, exist_ok=True)
        return build_user_install_package(
            snapshot or self.subset("using-superpowers"),
            self.status,
            home_root=home,
            asm_user_data_root=asm,
            repository_root=ROOT,
            target=self.target,
        )

    def confirm(self, package: dict, home: Path, asm: Path) -> dict:
        return build_user_confirmation(
            package,
            home_root=home,
            asm_user_data_root=asm,
        )

    def source_fixture(
        self, root: Path, record: dict, payload: bytes
    ) -> RoutingCatalogSnapshot:
        source_path = Path(record["source"]["path"])
        path = root / source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        updated = copy.deepcopy(record)
        updated["source"]["digest"] = digest_bytes(payload)
        return replace(self.subset(record["skill_id"]), records=(updated,))


class PackageBoundaryTests(ClaudeUserApplyTestCase):
    def test_user_package_is_generic_and_bound_to_claude_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = self.package(root / "home", root / "asm")
            self.assertTrue(validate_instance("InstallPackage", package).valid)
            self.assertEqual(package["scope"], "USER")
            self.assertEqual(package["runtime_id"], "claude-code")
            self.assertEqual(package["runtime_version"], "2.1.235")
            self.assertEqual(package["distribution_strategy"], "MANAGED_COPY")
            self.assertEqual(
                package["user_scope_contract_digest"],
                self.target["user_scope_contract_digest"],
            )
            self.assertTrue(package["apply_allowed"])
            self.assertTrue(package["confirmation_binding_digest"].startswith("sha256:"))
            self.assertTrue(all(item["destination_root"] in {"ASM_USER_DATA", "CLAUDE_PERSONAL"} for item in package["artifacts"]))
            self.assertNotIn("/Users/", json.dumps(package, ensure_ascii=False))

    def test_confirmation_binds_exact_package_and_virtual_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm)
            confirmation = self.confirm(package, home, asm)
            self.assertEqual(confirmation["package_digest"], package["package_digest"])
            self.assertEqual(confirmation["managed_path_count"], len(package["artifacts"]))
            tampered = copy.deepcopy(confirmation)
            tampered["managed_path_count"] += 1
            with self.assertRaisesRegex(InstallerError, "confirmation"):
                apply_user_install_package(
                    package,
                    home_root=home,
                    asm_user_data_root=asm,
                    repository_root=ROOT,
                    confirmation=tampered,
                )

    def test_user_package_rejects_ephemeral_artifact_and_scope_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = self.package(root / "home", root / "asm")
            package["artifacts"][0]["lifecycle"] = "EXECUTION_EPHEMERAL"
            package["package_digest"] = ""
            from tools.v3.installer import _package_digest

            package["package_digest"] = _package_digest(package)
            with self.assertRaisesRegex(InstallerError, "EXECUTION_EPHEMERAL|ephemeral"):
                build_user_confirmation(package, home_root=root / "home", asm_user_data_root=root / "asm")

    def test_user_package_cannot_rebind_a_skill_to_another_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            package = self.package(home, asm)
            personal = next(
                item
                for item in package["artifacts"]
                if item["destination_root"] == "CLAUDE_PERSONAL"
            )
            personal["destination_path"] = ".claude/skills/other/SKILL.md"
            package["package_digest"] = ""
            package["confirmation_binding_digest"] = ""
            package["confirmation_binding_digest"] = _user_confirmation_binding(package)
            package["package_digest"] = _package_digest(package)
            with self.assertRaisesRegex(InstallerError, "does not match its skill ID"):
                build_user_confirmation(
                    package,
                    home_root=home,
                    asm_user_data_root=asm,
                )


class VirtualHomeSafetyTests(ClaudeUserApplyTestCase):
    def test_implicit_and_real_home_variants_fail_closed(self):
        package_root = Path(tempfile.mkdtemp())
        try:
            package = self.package(package_root / "home", package_root / "asm")
            confirmation = self.confirm(package, package_root / "home", package_root / "asm")
            home_link = package_root / "home-link"
            home_link.symlink_to(Path.home(), target_is_directory=True)
            home_parent_link = package_root / "home-parent-link"
            home_parent_link.symlink_to(Path.home(), target_is_directory=True)
            for home in (
                None,
                Path.home(),
                Path.home() / ".",
                Path("~"),
                Path("relative-home"),
                Path.cwd() / Path.home().name,
                home_link,
                home_parent_link / "nested",
            ):
                with self.subTest(home=home), self.assertRaises(InstallerError):
                    apply_user_install_package(
                        package,
                        home_root=home,
                        asm_user_data_root=package_root / "asm",
                        repository_root=ROOT,
                        confirmation=confirmation,
                    )
        finally:
            # The temporary directory is empty and confined to the test root;
            # avoid broad recursive deletion in the test contract itself.
            for path in sorted(package_root.rglob("*"), reverse=True):
                if path.is_file() or path.is_symlink():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            package_root.rmdir()


class LifecycleTests(ClaudeUserApplyTestCase):
    def test_single_skill_apply_reapply_uninstall_and_reapply(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm)
            confirmation = self.confirm(package, home, asm)
            applied = apply_user_install_package(
                package,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=ROOT,
                confirmation=confirmation,
            )
            self.assertEqual(applied["status"], "APPLIED")
            artifact = next(item for item in package["artifacts"] if item["destination_root"] == "CLAUDE_PERSONAL")
            personal = home / artifact["destination_path"]
            staged = asm / next(item["destination_path"] for item in package["artifacts"] if item["destination_root"] == "ASM_USER_DATA")
            self.assertEqual(digest_bytes(personal.read_bytes()), artifact["content_digest"])
            self.assertEqual(digest_bytes(staged.read_bytes()), artifact["content_digest"])
            self.assertTrue((asm / "v3/claude/.asm-user-manifest.json").is_file())
            journal_path = asm / "v3/claude/.transactions" / f"{applied['transaction_id']}.json"
            self.assertTrue(journal_path.is_file())
            self.assertTrue(
                validate_instance(
                    "TransactionRecovery",
                    json.loads(journal_path.read_text(encoding="utf-8")),
                ).valid
            )

            repeat = apply_user_install_package(
                package,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=ROOT,
                confirmation=self.confirm(package, home, asm),
            )
            self.assertEqual(repeat["status"], "NO_OP")

            uninstall = build_user_uninstall_package(home_root=home, asm_user_data_root=asm)
            self.assertTrue(uninstall["apply_allowed"])
            removed = apply_user_uninstall_package(
                uninstall,
                home_root=home,
                asm_user_data_root=asm,
                confirmation=self.confirm(uninstall, home, asm),
            )
            self.assertEqual(removed["status"], "UNINSTALLED")
            self.assertFalse(personal.exists())
            self.assertFalse(staged.exists())

            reapplied = apply_user_install_package(
                package,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=ROOT,
                confirmation=self.confirm(package, home, asm),
            )
            self.assertEqual(reapplied["status"], "APPLIED")

    def test_update_revert_and_manual_modification_are_exactly_bound(self):
        record = next(
            item for item in self.snapshot.records if item["skill_id"] == "using-superpowers"
        )
        original = (ROOT / record["source"]["path"]).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm, repository = root / "home", root / "asm", root / "repo"
            home.mkdir()
            asm.mkdir()
            initial_snapshot = self.source_fixture(repository, record, original)
            initial = build_user_install_package(
                initial_snapshot,
                self.status,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                target=self.target,
            )
            first = apply_user_install_package(
                initial,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                confirmation=self.confirm(initial, home, asm),
            )
            changed = b"# phase-3n replacement\n"
            updated_snapshot = self.source_fixture(repository, record, changed)
            updated = build_user_install_package(
                updated_snapshot,
                self.status,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                target=self.target,
            )
            self.assertTrue(all(item["action"] == "UPDATE_MANAGED" for item in updated["artifacts"]))
            second = apply_user_install_package(
                updated,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                confirmation=self.confirm(updated, home, asm),
            )
            self.assertEqual(second["status"], "APPLIED")
            revert = build_user_revert_package(
                home_root=home,
                asm_user_data_root=asm,
                transaction_id=second["transaction_id"],
            )
            restored = apply_user_revert_package(
                revert,
                home_root=home,
                asm_user_data_root=asm,
                confirmation=self.confirm(revert, home, asm),
            )
            self.assertEqual(restored["status"], "REVERTED")
            personal = home / ".claude/skills/using-superpowers/SKILL.md"
            self.assertEqual(personal.read_bytes(), original)

            # A destination edit changes the exact managed state and cannot be
            # adopted by a newly built package.
            personal.write_bytes(b"user edit")
            conflict = build_user_install_package(
                updated_snapshot,
                self.status,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                target=self.target,
            )
            self.assertFalse(conflict["apply_allowed"])
            self.assertTrue(any(item["action"] == "CONFLICT" for item in conflict["artifacts"]))
            self.assertEqual(first["status"], "APPLIED")

    def test_source_change_after_package_build_stops_before_any_write(self):
        record = next(
            item
            for item in self.snapshot.records
            if item["skill_id"] == "using-superpowers"
        )
        original = (ROOT / record["source"]["path"]).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm, repository = root / "home", root / "asm", root / "repo"
            home.mkdir()
            asm.mkdir()
            snapshot = self.source_fixture(repository, record, original)
            package = build_user_install_package(
                snapshot,
                self.status,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                target=self.target,
            )
            (repository / Path(record["source"]["path"])).write_bytes(
                b"# changed after package creation\n"
            )
            with self.assertRaisesRegex(InstallerError, "STALE_PACKAGE"):
                apply_user_install_package(
                    package,
                    home_root=home,
                    asm_user_data_root=asm,
                    repository_root=repository,
                    confirmation=self.confirm(package, home, asm),
                )
            self.assertFalse((home / ".claude").exists())
            self.assertFalse((asm / "v3/claude").exists())

    def test_three_skill_mixed_lifecycle_has_create_noop_and_update(self):
        skill_ids = (
            "using-superpowers",
            "test-driven-development",
            "verification-before-completion",
        )
        records = [
            copy.deepcopy(
                next(item for item in self.snapshot.records if item["skill_id"] == skill_id)
            )
            for skill_id in skill_ids
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm, repository = root / "home", root / "asm", root / "repo"
            home.mkdir()
            asm.mkdir()
            for record in records:
                source = ROOT / record["source"]["path"]
                destination = repository / record["source"]["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
            initial_snapshot = replace(
                self.snapshot, records=tuple(copy.deepcopy(records[:2]))
            )
            initial = build_user_install_package(
                initial_snapshot,
                self.status,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                target=self.target,
            )
            apply_user_install_package(
                initial,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                confirmation=self.confirm(initial, home, asm),
            )

            changed = b"# phase-3n mixed update\n"
            changed_record = copy.deepcopy(records[0])
            changed_record["source"]["digest"] = digest_bytes(changed)
            (repository / Path(changed_record["source"]["path"])).write_bytes(changed)
            mixed_snapshot = replace(
                self.snapshot,
                records=(changed_record, records[1], records[2]),
            )
            mixed = build_user_install_package(
                mixed_snapshot,
                self.status,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                target=self.target,
            )
            actions = {
                (item["skill_id"], item["destination_root"]): item["action"]
                for item in mixed["artifacts"]
            }
            for destination_root in ("ASM_USER_DATA", "CLAUDE_PERSONAL"):
                self.assertEqual(
                    actions[("using-superpowers", destination_root)],
                    "UPDATE_MANAGED",
                )
                self.assertEqual(
                    actions[("test-driven-development", destination_root)],
                    "NO_OP",
                )
                self.assertEqual(
                    actions[("verification-before-completion", destination_root)],
                    "CREATE",
                )
            result = apply_user_install_package(
                mixed,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                confirmation=self.confirm(mixed, home, asm),
            )
            self.assertEqual(result["status"], "APPLIED")
            for skill_id in skill_ids:
                self.assertTrue(
                    (home / ".claude/skills" / skill_id / "SKILL.md").is_file()
                )

    def test_mid_transaction_write_failure_rolls_back_without_partial_user_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm)
            calls = {"count": 0}

            def fail_on_second_destination(source, destination):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise OSError("injected destination failure")
                return __import__("os").replace(source, destination)

            result = apply_user_install_package(
                package,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=ROOT,
                confirmation=self.confirm(package, home, asm),
                replace_fn=fail_on_second_destination,
            )
            self.assertEqual(result["status"], "ROLLED_BACK")
            self.assertFalse((home / ".claude/skills/using-superpowers/SKILL.md").exists())
            self.assertFalse((asm / "v3/claude/skills/using-superpowers/SKILL.md").exists())

    def test_recovery_after_marker_commit_completes_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm)
            with self.assertRaises(UserTransactionInterrupted) as caught:
                apply_user_install_package(
                    package,
                    home_root=home,
                    asm_user_data_root=asm,
                    repository_root=ROOT,
                    confirmation=self.confirm(package, home, asm),
                    interrupt_at="after_ownership",
                )
            recovery = recover_user_transaction(
                caught.exception.transaction_id,
                home_root=home,
                asm_user_data_root=asm,
            )
            self.assertEqual(recovery["decision"], "COMPLETE_VERIFICATION")
            self.assertEqual(recovery["final_phase"], "COMPLETE")

    def test_user_owned_collision_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm)
            destination = home / next(item for item in package["artifacts"] if item["destination_root"] == "CLAUDE_PERSONAL")["destination_path"]
            destination.parent.mkdir(parents=True)
            destination.write_text("user-owned", encoding="utf-8")
            rebuilt = self.package(home, asm)
            self.assertFalse(rebuilt["apply_allowed"])
            self.assertTrue(any(item["action"] == "CONFLICT" for item in rebuilt["artifacts"]))
            self.assertEqual(destination.read_text(encoding="utf-8"), "user-owned")

    def test_uninstall_preserves_a_user_file_added_inside_managed_skill_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm)
            apply_user_install_package(
                package,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=ROOT,
                confirmation=self.confirm(package, home, asm),
            )
            personal = home / ".claude/skills/using-superpowers"
            personal.joinpath("user-notes.txt").write_text("keep", encoding="utf-8")
            uninstall = build_user_uninstall_package(
                home_root=home, asm_user_data_root=asm
            )
            self.assertFalse(uninstall["apply_allowed"])
            self.assertTrue(any(item["action"] == "CONFLICT" for item in uninstall["artifacts"]))
            self.assertTrue(personal.joinpath("SKILL.md").exists())
            self.assertTrue(personal.joinpath("user-notes.txt").exists())

    def test_synced_skill_name_is_a_blocking_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            synced = home / ".claude/skills/synced/using-superpowers"
            synced.mkdir(parents=True)
            synced.joinpath("SKILL.md").write_text("synced", encoding="utf-8")
            package = self.package(home, asm)
            personal = next(
                item
                for item in package["artifacts"]
                if item["destination_root"] == "CLAUDE_PERSONAL"
            )
            self.assertEqual(personal["collision_state"], "CLAUDE_SYNCED")
            self.assertFalse(package["apply_allowed"])
            self.assertFalse((home / ".claude/skills/using-superpowers/SKILL.md").exists())
            self.assertTrue(synced.joinpath("SKILL.md").exists())


class RecoveryTests(ClaudeUserApplyTestCase):
    def test_each_persisted_boundary_has_a_deterministic_recovery_outcome(self):
        expected = {
            "after_prepared": "ROLLED_BACK",
            "after_staging": "COMPLETE",
            "before_ownership": "COMPLETE",
            "before_verify": "COMPLETE",
        }
        for boundary, final_phase in expected.items():
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                home, asm = root / "home", root / "asm"
                home.mkdir()
                asm.mkdir()
                package = self.package(home, asm)
                with self.assertRaises(UserTransactionInterrupted) as caught:
                    apply_user_install_package(
                        package,
                        home_root=home,
                        asm_user_data_root=asm,
                        repository_root=ROOT,
                        confirmation=self.confirm(package, home, asm),
                        interrupt_at=boundary,
                    )
                recovery = recover_user_transaction(
                    caught.exception.transaction_id,
                    home_root=home,
                    asm_user_data_root=asm,
                )
                self.assertEqual(recovery["final_phase"], final_phase)

    def test_process_death_after_first_create_is_recoverable_by_new_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm)
            with self.assertRaises(UserTransactionInterrupted) as caught:
                apply_user_install_package(
                    package,
                    home_root=home,
                    asm_user_data_root=asm,
                    repository_root=ROOT,
                    confirmation=self.confirm(package, home, asm),
                    interrupt_at="after_create",
                )
            transaction_id = caught.exception.transaction_id
            recovery = recover_user_transaction(
                transaction_id,
                home_root=home,
                asm_user_data_root=asm,
            )
            self.assertIn(recovery["decision"], {"RESUME", "COMPLETE_VERIFICATION"})
            self.assertEqual(recovery["final_phase"], "COMPLETE")

    def test_process_death_after_first_update_is_recoverable_by_new_process(self):
        record = next(
            item
            for item in self.snapshot.records
            if item["skill_id"] == "using-superpowers"
        )
        original = (ROOT / record["source"]["path"]).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm, repository = root / "home", root / "asm", root / "repo"
            home.mkdir()
            asm.mkdir()
            initial = self.source_fixture(repository, record, original)
            first = build_user_install_package(
                initial,
                self.status,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                target=self.target,
            )
            apply_user_install_package(
                first,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                confirmation=self.confirm(first, home, asm),
            )
            changed = b"# phase-3n interrupted update\n"
            updated = self.source_fixture(repository, record, changed)
            second = build_user_install_package(
                updated,
                self.status,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=repository,
                target=self.target,
            )
            with self.assertRaises(UserTransactionInterrupted) as caught:
                apply_user_install_package(
                    second,
                    home_root=home,
                    asm_user_data_root=asm,
                    repository_root=repository,
                    confirmation=self.confirm(second, home, asm),
                    interrupt_at="after_update",
                )
            recovery = recover_user_transaction(
                caught.exception.transaction_id,
                home_root=home,
                asm_user_data_root=asm,
            )
            self.assertEqual(recovery["final_phase"], "COMPLETE")
            self.assertEqual(
                (home / ".claude/skills/using-superpowers/SKILL.md").read_bytes(),
                changed,
            )

    def test_tampered_journal_is_recovery_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm)
            with self.assertRaises(UserTransactionInterrupted) as caught:
                apply_user_install_package(
                    package,
                    home_root=home,
                    asm_user_data_root=asm,
                    repository_root=ROOT,
                    confirmation=self.confirm(package, home, asm),
                    interrupt_at="after_staging",
                )
            transaction_id = caught.exception.transaction_id
            journal_path = asm / "v3/claude/.transactions" / f"{transaction_id}.json"
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            journal["package_digest"] = "sha256:" + "0" * 64
            journal_path.write_text(json.dumps(journal, sort_keys=True), encoding="utf-8")
            with self.assertRaisesRegex(InstallerError, "RECOVERY_BLOCKED"):
                recover_user_transaction(
                    transaction_id,
                    home_root=home,
                    asm_user_data_root=asm,
                )

    def test_recovery_accepts_an_interruption_after_atomic_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm)
            interrupted = {"done": False}

            def interrupt_after_replace(source, destination):
                __import__("os").replace(source, destination)
                if not interrupted["done"]:
                    interrupted["done"] = True
                    journal = next((asm / "v3/claude/.transactions").glob("*.json"))
                    raise UserTransactionInterrupted(journal.stem, "after_replace")

            with self.assertRaises(UserTransactionInterrupted):
                apply_user_install_package(
                    package,
                    home_root=home,
                    asm_user_data_root=asm,
                    repository_root=ROOT,
                    confirmation=self.confirm(package, home, asm),
                    replace_fn=interrupt_after_replace,
                )
            transaction_id = next(
                (asm / "v3/claude/.transactions").glob("*.json")
            ).stem
            recovery = recover_user_transaction(
                transaction_id,
                home_root=home,
                asm_user_data_root=asm,
            )
            self.assertEqual(recovery["final_phase"], "COMPLETE")


class CliUserApplyTests(ClaudeUserApplyTestCase):
    def test_package_command_writes_only_an_immutable_package_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm, output_path = root / "home", root / "asm", root / "package.json"
            home.mkdir()
            asm.mkdir()
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "package",
                        "--runtime",
                        "claude-code",
                        "--scope",
                        "user",
                        "--home-root",
                        str(home),
                        "--asm-user-data-root",
                        str(asm),
                        "--output",
                        str(output_path),
                        "--format",
                        "json",
                    ]
                )
            self.assertEqual(result, 0)
            self.assertTrue(output_path.is_file())
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["result"]["status"], "PACKAGED")
            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8"))["package_digest"],
                payload["package"]["package_digest"],
            )
            self.assertFalse((home / ".claude").exists())
            self.assertFalse((asm / "v3/claude/.asm-user-manifest.json").exists())

    def test_apply_command_requires_exact_package_digest_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm, package_path = root / "home", root / "asm", root / "package.json"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm)
            package_path.write_text(
                json.dumps(package, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "apply",
                        "--runtime",
                        "claude-code",
                        "--scope",
                        "user",
                        "--strategy",
                        "managed-copy",
                        "--home-root",
                        str(home),
                        "--asm-user-data-root",
                        str(asm),
                        "--package",
                        str(package_path),
                        "--confirm-package-digest",
                        "sha256:" + "0" * 64,
                        "--format",
                        "json",
                    ]
                )
            self.assertEqual(result, 2)
            self.assertEqual(json.loads(stdout.getvalue())["error"], "USER_CONFIRMATION_REQUIRED")
            self.assertFalse((home / ".claude").exists())


class CatalogScaleTests(ClaudeUserApplyTestCase):
    def test_full_catalog_package_is_virtual_and_selected_execution_remains_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm, self.snapshot)
            self.assertEqual(len(package["source_skill_ids"]), len(self.snapshot.records))
            self.assertEqual(len(package["artifacts"]), len(self.snapshot.records) * 2)
            self.assertFalse(any(item.get("body_materialized") for item in package["artifacts"]))
            self.assertFalse((home / ".claude").exists())

    def test_full_catalog_virtual_apply_is_complete_without_execution_materialization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, asm = root / "home", root / "asm"
            home.mkdir()
            asm.mkdir()
            package = self.package(home, asm, self.snapshot)
            result = apply_user_install_package(
                package,
                home_root=home,
                asm_user_data_root=asm,
                repository_root=ROOT,
                confirmation=self.confirm(package, home, asm),
            )
            self.assertEqual(result["status"], "APPLIED")
            self.assertEqual(
                len(list((home / ".claude/skills").glob("*/SKILL.md"))),
                len(self.snapshot.records),
            )
            self.assertEqual(
                len(list((asm / "v3/claude/skills").glob("*/SKILL.md"))),
                len(self.snapshot.records),
            )
            journal = asm / "v3/claude/.transactions" / f"{result['transaction_id']}.json"
            self.assertEqual(json.loads(journal.read_text(encoding="utf-8"))["phase"], "COMPLETE")
