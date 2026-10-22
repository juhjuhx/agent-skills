#!/usr/bin/env python3
"""P6 測試：REGISTRY_SCHEMA_TEST + CATALOG_MIGRATION_TEST +
DUPLICATE_DETECTION_TEST + LICENSE_GATE_TEST + SYMLINK_ESCAPE_TEST +
SECRET_LEAK_TEST + HOST_FALLBACK_TEST。

純標準庫；不觸碰 ~/.agents/skills；所有 fixture 在 tmp dir 建立。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _reg():
    spec = importlib.util.spec_from_file_location("registry", REPO / "registry/tools/registry.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _composer():
    spec = importlib.util.spec_from_file_location(
        "composer", REPO / "runtime/skills-router/extensions/skill-composer/composer.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(root, rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()


class RegistrySchemaTest(unittest.TestCase):
    """REGISTRY_SCHEMA_TEST: 記錄須通過 schema 必需欄位/枚舉驗證。"""

    def test_valid_record_passes(self):
        reg = _reg()
        with tempfile.TemporaryDirectory() as tmp:
            rec, diags = reg.build_record(
                id="public:test", name="test", relative_path="test/SKILL.md",
                sha="a" * 64, license="MIT", status="approved_public",
                visibility="public", risk="low")
            self.assertEqual(diags, [])
            reg.validate_record(rec, diags)
            self.assertEqual(diags, [])

    def test_broken_record_fails(self):
        reg = _reg()
        diags = []
        reg.validate_record({"id": "x", "name": "x", "sha256": "nothex",
                             "license": "CC0", "status": "weird",
                             "visibility": "global", "risk_level": "low"}, diags)
        codes = {d["code"] for d in diags}
        self.assertIn("BAD_SHA256", codes)
        self.assertIn("BAD_LICENSE", codes)
        self.assertIn("BAD_STATUS", codes)
        self.assertIn("BAD_VISIBILITY", codes)

    def test_schema_file_loadable(self):
        schema = json.loads((REPO / "registry/schema/skill-record.schema.json").read_text())
        self.assertEqual(schema["type"], "object")
        for field in ("id", "name", "sha256", "license", "status", "visibility", "risk_level"):
            self.assertIn(field, schema["required"])


class CatalogMigrationTest(unittest.TestCase):
    """CATALOG_MIGRATION_TEST: P0 recovery manifest + 640 catalog → registry 層。"""

    def test_import_is_idempotent(self):
        reg = _reg()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            recovery = root / "rec.json"
            recovery.write_text(json.dumps({
                "records": [],
                "summary": {"heritage_commit": "deadbeef",
                            "historical_recovered_dirs": []},
                "security_hits": [],
            }), encoding="utf-8")
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps({
                "skills": [
                    {"skill_id": "local:a", "canonical_name": "a",
                     "relative_path": "a/SKILL.md", "body_digest": "b" * 64,
                     "license": "MIT", "classification": "CANONICAL_SKILL",
                     "quarantine_state": None, "description": "skill a",
                     "categories": [], "triggers": [],
                     "provenance": {"source": "test"}},
                    {"skill_id": "local:b", "canonical_name": "b",
                     "relative_path": "b/SKILL.md", "body_digest": "c" * 64,
                     "license": None, "classification": "CANONICAL_SKILL",
                     "quarantine_state": None, "description": "skill b",
                     "categories": [], "triggers": [],
                     "provenance": {"source": "test"}},
                ]
            }), encoding="utf-8")
            h1, p1 = reg.import_private(str(root), str(recovery), str(catalog))
            h2, p2 = reg.import_private(str(root), str(recovery), str(catalog))
            self.assertEqual((h1, p1), (2, 1))       # a: MIT→private; b: unknown→不出現
            self.assertEqual((h2, p2), (2, 1))        # 冪等：重跑不疊加
            hist = json.loads((root / "registry/history/registry.json").read_text())
            ids = [r["id"] for r in hist["records"]]
            self.assertEqual(len(ids), len(set(ids)))
            # license 狀態映射
            by_id = {r["id"]: r for r in hist["records"]}
            self.assertEqual(by_id["local:a"]["license"], "MIT")
            self.assertEqual(by_id["local:b"]["license"], "unknown")

    def test_quarantine_state_preserved(self):
        reg = _reg()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            recovery = root / "rec.json"
            recovery.write_text(json.dumps({
                "records": [],
                "summary": {"historical_recovered_dirs": ["b"]},
                "security_hits": [],
            }), encoding="utf-8")
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps({"skills": [
                {"skill_id": "local:b", "canonical_name": "b",
                 "relative_path": "b/SKILL.md", "body_digest": "c" * 64,
                 "license": "MIT", "classification": "QUARANTINED",
                 "quarantine_state": "ROUTING_POLICY", "description": "x",
                 "categories": [], "triggers": [], "provenance": {"source": "t"}},
            ]}), encoding="utf-8")
            h, p = reg.import_private(str(root), str(recovery), str(catalog))
            hist = json.loads((root / "registry/history/registry.json").read_text())
            self.assertEqual(hist["records"][0]["status"], "quarantined")
            self.assertEqual(p, 0)  # 隔離技能不得進入 private 可用層


class DuplicateDetectionTest(unittest.TestCase):
    """DUPLICATE_DETECTION_TEST: body digest 與 name 重複皆可偵測。"""

    def test_detects_body_and_name_duplicates(self):
        reg = _reg()
        with tempfile.TemporaryDirectory() as tmp:
            recs = [
                {"id": "a", "name": "same-skill", "sha256": "1" * 64},
                {"id": "b", "name": "same-skill", "sha256": "1" * 64},
                {"id": "c", "name": "unique", "sha256": "2" * 64},
            ]
            doc = {"layer": "public", "records": recs}
            (Path(tmp) / "registry/public").mkdir(parents=True)
            (Path(tmp) / "registry/public/registry.json").write_text(json.dumps(doc))
            dupes = reg.find_duplicates(tmp, "public")
            body_dupe = next((d for d in dupes if d["kind"] == "body_digest" and d["ids"] == ["a", "b"]), None)
            name_dupe = next((d for d in dupes if d["kind"] == "name" and d["names"] == "same-skill"), None)
            self.assertIsNotNone(body_dupe, "body digest duplicate not detected")
            self.assertIsNotNone(name_dupe, "name duplicate not detected")


class LicenseGateTest(unittest.TestCase):
    """LICENSE_GATE_TEST: 未知授權/公開層不得出現 unknown license。"""

    def test_public_layer_rejects_unknown_license(self):
        reg = _reg()
        composer = _composer()
        with tempfile.TemporaryDirectory() as tmp:
            rec, _ = reg.build_record(
                id="public:unlicensed", name="unlicensed", relative_path="x/SKILL.md",
                sha="3" * 64, license="unknown", status="approved_public",
                visibility="public", risk="unreviewed")
            reg_doc = reg.load_layer(tmp, "public")
            reg_doc["records"].append(rec)
            reg.save_layer(tmp, "public", reg_doc)
            # 直接驗真實 gate（composer.filter_eligible），不重實作邏輯
            eligible = composer.filter_eligible(
                [(1.0, {**rec, "_layer": "public"})], hosts=("generic",))
            self.assertEqual(eligible, [], "unknown-license public skill must be filtered")
            # 對照：授權明確的公開技能可過 gate
            ok, _ = reg.build_record(
                id="public:licensed", name="licensed", relative_path="y/SKILL.md",
                sha="3" * 64, license="MIT", status="approved_public",
                visibility="public", risk="low")
            eligible2 = composer.filter_eligible(
                [(1.0, {**ok, "_layer": "public"})], hosts=("generic",))
            self.assertEqual(len(eligible2), 1, "MIT public skill must pass the gate")

    def test_license_enum_valid(self):
        reg = _reg()
        for lic in ("MIT", "Apache-2.0", "unknown", "proprietary"):
            rec, diags = reg.build_record(
                id="p:" + lic, name=lic, relative_path="x", sha="4" * 64,
                license=lic, status="candidate", visibility="private", risk="low")
            self.assertEqual(diags, [], lic)
        bad, diags = reg.build_record(
            id="p:cc0", name="cc0", relative_path="x", sha="4" * 64,
            license="CC0", status="candidate", visibility="private", risk="low")
        self.assertTrue(any(d["code"] == "BAD_LICENSE" for d in diags))


class SymlinkEscapeTest(unittest.TestCase):
    """SYMLINK_ESCAPE_TEST: _safe() 拒絕 path traversal 與 symlink 段。"""

    def test_traversal_rejected(self):
        composer = _composer()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").mkdir()
            with self.assertRaises(ValueError):
                composer._safe(root, "../../etc/passwd")

    def test_symlink_segment_rejected(self):
        composer = _composer()
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside"
            outside.mkdir()
            link = (Path(tmp) / "linkdir")
            link.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                composer._safe(Path(tmp), "linkdir/SKILL.md")

    def test_normal_path_ok(self):
        composer = _composer()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a" / "b").mkdir(parents=True)
            p = composer._safe(Path(tmp), "a/b/SKILL.md")
            self.assertEqual(p.parent, (Path(tmp) / "a" / "b").resolve())


class SecretLeakTest(unittest.TestCase):
    """SECRET_LEAK_TEST: 秘密/私人路徑掃描可偵測且可通過。"""

    def test_scans_secrets_and_paths(self):
        reg = _reg()
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "leaky"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: leaky\ndescription: test skill\n---\n"
                "api_key = \"ghp_" + "A" * 30 + "\"\n"
                "save to /home/someuser/Desktop/x.md\n", encoding="utf-8")
            doc = {"layer": "public", "records": [
                {"id": "public:leaky", "name": "leaky", "relative_path": "leaky/SKILL.md"}]}
            (Path(tmp) / "registry/public").mkdir(parents=True)
            (Path(tmp) / "registry/public/registry.json").write_text(json.dumps(doc))
            hits = reg.secret_scan(tmp, "public")
            kinds = {h["kind"] for h in hits if h["id"] == "public:leaky"}
            self.assertIn("github_pat", kinds)
            self.assertIn("local_absolute_path", kinds)

    def test_clean_skill_passes(self):
        reg = _reg()
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "clean"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: clean\ndescription: a clean skill\n---\nbody\n",
                encoding="utf-8")
            doc = {"layer": "public", "records": [
                {"id": "public:clean", "name": "clean", "relative_path": "clean/SKILL.md"}]}
            (Path(tmp) / "registry/public").mkdir(parents=True)
            (Path(tmp) / "registry/public/registry.json").write_text(json.dumps(doc))
            self.assertEqual(reg.secret_scan(tmp, "public"), [])


class HostFallbackTest(unittest.TestCase):
    """HOST_FALLBACK_TEST: composition layer 故障 → fallback=True，不影響宿主。

    composer 對單一損毀 layer 採 fail-open（靜默跳過、不 raise）；
    fallback=True 只在 composition 內部真正 raise 時觸發——用 monkeypatch 模擬。
    """

    def test_fallback_when_layer_raises(self):
        composer = _composer()
        with tempfile.TemporaryDirectory() as tmp:
            original = composer.candidate_pool
            try:
                def boom(*a, **k):
                    raise OSError("registry module exploded")
                composer.candidate_pool = boom
                packet = composer.compose("do a task", reg_root=tmp,
                                          hosts=("generic",), profile="normal")
            finally:
                composer.candidate_pool = original
            self.assertTrue(packet["fallback"])
            self.assertIn("exploded", packet["fallback_reason"])
            self.assertTrue(packet["advisory"])

    def test_graceful_skip_on_corrupt_layer(self):
        """corrupt layer JSON → 該層跳過、不 raise（fail-open），composition 可能空。"""
        composer = _composer()
        with tempfile.TemporaryDirectory() as tmp:
            regdir = Path(tmp) / "reg"
            (regdir / "public").mkdir(parents=True)
            (regdir / "public/registry.json").write_text("{broken json")
            packet = composer.compose("do a task", reg_root=str(regdir),
                                      hosts=("generic",), profile="normal",
                                      local_roots={"x": str(tmp)})
            self.assertFalse(packet.get("fallback"))          # 不升級成 fallback
            self.assertEqual(packet.get("composition", []), [])  # 無正文可載入
            self.assertEqual(packet.get("candidate_pool_size"), 0)

    def test_graceful_on_empty_registry(self):
        composer = _composer()
        with tempfile.TemporaryDirectory() as tmp:
            packet = composer.compose("do a task", reg_root=tmp,
                                     hosts=("generic",), profile="normal")
            self.assertFalse(packet.get("fallback"))
            self.assertEqual(packet.get("composition", []), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
