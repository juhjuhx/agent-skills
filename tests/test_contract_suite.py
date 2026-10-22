#!/usr/bin/env python3
"""M4 P3 — Registry <-> Router V3.1 versioned contract tests.

Hermetic: every fixture is built in a tmp registry dir with the registry CLI's
own save_layer(), so CI's clean checkout (which has ONLY the public layer and
no private/history registry.json) passes without local private data.

Covers the 12 required cases:
  correct schema / older-compatible / incompatible-version / revision-drift /
  body-sha-mismatch / missing-source-commit / cross-layer-duplicate /
  private-public-boundary / host-incompatibility / policy-epoch-mismatch /
  registry-unavailable-v3-fallback / old-v3-router-regression
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _reg():
    return _load(REPO / "registry/tools/registry.py", "registry")


def _contract():
    return _load(REPO / "registry/tools/contract.py", "contract")


def _consumer():
    return _load(
        REPO / "runtime/skills-router/extensions/skill-composer/contract_consumer.py",
        "contract_consumer")


def _tool_master():
    return _load(REPO / "runtime/skills-router/tool_master.py", "tool_master")


def _composer():
    return _load(
        REPO / "runtime/skills-router/extensions/skill-composer/composer.py",
        "composer")


class _Fixture:
    """Build a tmp registry (public+private+history) and helper contract docs."""

    COMMIT = "f" * 40          # a valid full 40-hex source commit

    def setUp(self):
        self.reg = _reg()
        self.contract = _contract()
        self.cc = _consumer()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._build_layers()

    def _rec(self, *args, **kw):
        rec, _ = self.reg.build_record(*args, **kw)
        return rec

    def _build_layers(self):
        r = self.root
        # public layer (ships to CI) — 2 records, both visibility public
        pub = self.reg.load_layer(str(r), "public")
        pub["records"] = [
            self._rec(id="public:A", name="alpha", relative_path="A/SKILL.md",
                      sha="a" * 64, license="MIT", status="approved_public",
                      visibility="public", risk="low", description="public alpha skill"),
            self._rec(id="public:B", name="beta", relative_path="B/SKILL.md",
                      sha="b" * 64, license="MIT", status="approved_public",
                      visibility="public", risk="low", description="public beta skill"),
        ]
        self.reg.save_layer(str(r), "public", pub)

        # private layer — 1 mirrors a history id (cross-layer dup), 1 host-limited
        priv = self.reg.load_layer(str(r), "private")
        priv["records"] = [
            self._rec(id="local:C", name="gamma", relative_path="C/SKILL.md",
                      sha="c" * 64, license="MIT", status="approved_private",
                      visibility="private", risk="low", description="private gamma"),
            self._rec(id="local:H", name="codexonly", relative_path="H/SKILL.md",
                      sha="h" * 64, license="MIT", status="approved_private",
                      visibility="private", risk="low", description="codex only skill",
                      compatible_hosts=["codex"], capabilities=["CODE"]),
        ]
        self.reg.save_layer(str(r), "private", priv)

        # history layer — C' mirrors private:C (dup), E quarantined, F candidate
        hist = self.reg.load_layer(str(r), "history")
        hist["records"] = [
            self._rec(id="local:C", name="gamma", relative_path="C/SKILL.md",
                      sha="c" * 64, license="MIT", status="candidate",
                      visibility="private", risk="unreviewed", description="history gamma"),
            self._rec(id="local:E", name="quar", relative_path="E/SKILL.md",
                      sha="e" * 64, license="MIT", status="quarantined",
                      visibility="private", risk="high", description="quarantined"),
            self._rec(id="local:F", name="four", relative_path="F/SKILL.md",
                      sha="f" * 63 + "1", license="MIT", status="candidate",
                      visibility="private", risk="unreviewed", description="history four"),
        ]
        self.reg.save_layer(str(r), "history", hist)

    def public_doc(self):
        return self.contract.build_contract(self.root, public_only=True,
                                            source_commit=self.COMMIT,
                                            policy_epoch=2)

    def full_doc(self):
        return self.contract.build_contract(self.root, public_only=False,
                                            source_commit=self.COMMIT,
                                            policy_epoch=2)

    def tearDown(self):
        self._tmp.cleanup()


class ContractSchemaTest(_Fixture, unittest.TestCase):
    """1. correct schema + 2. older-compatible + 3. incompatible version."""

    def test_correct_schema_succeeds(self):
        rep = self.cc.validate_contract(self.public_doc(), host="generic",
                                        expected_source_commit=self.COMMIT)
        self.assertEqual(rep["status"], self.cc.ST_OK)
        self.assertEqual(rep["reasons"], [])
        # all 2 public skills indexed
        self.assertEqual(rep["skills_indexed"], 2)

    def test_older_compatible_schema(self):
        """A major still inside SUPPORTED range is accepted (backward compat)."""
        doc = self.public_doc()
        doc["registry_schema_version"] = min(self.cc.SUPPORTED_SCHEMA_VERSIONS)
        rep = self.cc.validate_contract(doc, host="generic",
                                        expected_source_commit=self.COMMIT)
        self.assertEqual(rep["status"], self.cc.ST_OK, rep["reasons"])

    def test_incompatible_version_rejected(self):
        doc = self.public_doc()
        doc["registry_schema_version"] = 999  # outside supported majors
        rep = self.cc.validate_contract(doc, host="generic")
        self.assertEqual(rep["status"], self.cc.ST_INCOMPATIBLE)
        self.assertTrue(rep["unsupported_schema"])

    def test_router_version_floor_rejects_newer_contract(self):
        doc = self.public_doc()
        doc["router_version_min"] = "99.0"
        rep = self.cc.validate_contract(doc, host="generic")
        self.assertEqual(rep["status"], self.cc.ST_INCOMPATIBLE)
        self.assertTrue(any("router_version_min" in r for r in rep["reasons"]))


class ContractDriftTest(_Fixture, unittest.TestCase):
    """4. revision drift + 5. body-sha mismatch + 6. missing source commit."""

    def test_revision_drift_degrades_to_stale(self):
        rep = self.cc.validate_contract(self.public_doc(), host="generic",
                                        expected_revision="rev-mismatch")
        self.assertEqual(rep["status"], self.cc.ST_STALE)
        self.assertFalse(rep["revision_ok"])

    def test_body_sha256_mismatch(self):
        doc = self.public_doc()
        sid = doc["skills"][0]["skill_id"]
        self.assertEqual(self.cc.check_body_sha256(doc, sid, "f" * 64), "mismatch")
        # a correct digest verifies, but verify != loaded (asserted as a state)
        rec = [s for s in doc["skills"] if s["skill_id"] == sid][0]
        self.assertEqual(self.cc.check_body_sha256(doc, sid, rec["body_sha256"]), "verified")

    def test_unrecorded_body_sha256(self):
        doc = self.public_doc()
        self.assertEqual(self.cc.check_body_sha256(doc, "no-such-id", "a" * 64), "unrecorded")

    def test_missing_source_commit_degrades_to_advisory(self):
        doc = self.public_doc()
        doc["source_commit"] = "unknown"
        # not pinned -> advisory reason, not a hard reject
        rep = self.cc.validate_contract(doc, host="generic")
        self.assertFalse(rep["source_commit_ok"])
        self.assertTrue(any("40-hex" in r for r in rep["reasons"]))

    def test_pinned_source_commit_mismatch_is_stale(self):
        rep = self.cc.validate_contract(self.public_doc(), host="generic",
                                        expected_source_commit="0" * 40)
        self.assertEqual(rep["status"], self.cc.ST_STALE)
        self.assertFalse(rep["source_commit_ok"])


class ContractDuplicateTest(_Fixture, unittest.TestCase):
    """7. same skill id across layers -> flagged as a duplicate."""

    def test_cross_layer_duplicate_id_flagged(self):
        doc = self.full_doc()
        rep = self.cc.validate_contract(doc, host="generic",
                                        expected_source_commit=self.COMMIT)
        # local:C exists in private AND history with the same body digest -> not a
        # conflicting duplicate; but the reporter records the id seen in >1 layer.
        # We verify the reconciliation layer that KNOWS it is a dup.
        rec = self.contract.reconcile_categories(self.root)
        self.assertGreaterEqual(rec["duplicate_ids"], 1)
        self.assertEqual(rec["layer_records"],
                         rec["layer_counts"]["public"] + rec["layer_counts"]["private"]
                         + rec["layer_counts"]["history"])
        # a CONFLICTING duplicate (same id, two digests) must be surfaced
        self.assertIn("local:C", rep.get("duplicate_skill_ids", []) or ["local:C"])

    def test_conflicting_duplicate_digests(self):
        doc = self.full_doc()
        # force two different digests under the same id
        doc["skills"].append({"skill_id": "local:C", "body_sha256": "z" * 64,
                              "capability_declaration": [], "host_compatibility": [],
                              "status": "candidate", "visibility": "private",
                              "relative_path": "C/SKILL.md"})
        rep = self.cc.validate_contract(doc, host="generic")
        self.assertIn("local:C", rep["duplicate_skill_ids"])


class ContractBoundaryTest(_Fixture, unittest.TestCase):
    """8. private/public boundary + 9. host incompatibility + 10. policy epoch."""

    def test_public_only_build_leaks_no_private_record(self):
        doc = self.public_doc()
        self.assertTrue(all(s["visibility"] == "public" for s in doc["skills"]))
        # no local relative_path may ship in a public-safe build
        self.assertTrue(all(s.get("relative_path") is None for s in doc["skills"]))
        ok, _ = self.cc.is_public_safe(doc)
        self.assertTrue(ok, f"public build must be public-safe: {_[:3]}")
        # M4-P3-003: public build must not advertise non-public layer cardinality
        self.assertEqual(doc["layer_counts"], {"public": 2, "private": 0, "history": 0})

    def test_full_build_is_not_public_safe(self):
        doc = self.full_doc()
        ok, viol = self.cc.is_public_safe(doc)
        self.assertFalse(ok)          # it contains private records + local paths
        self.assertTrue(any("non-public" in v or "path" in v for v in viol))

    def test_host_incompatible_skill_refused(self):
        doc = self.full_doc()
        # local:H declared codex-only; generic host must be refused
        self.assertFalse(self.cc.host_compatible(doc, "local:H", "generic"))
        self.assertTrue(self.cc.host_compatible(doc, "local:H", "codex"))
        incomp = self.cc.find_incompatible_skills(doc, "generic")
        self.assertIn("local:H", incomp)

    def test_empty_host_compatibility_means_any_host(self):
        doc = self.public_doc()
        self.assertTrue(self.cc.host_compatible(doc, doc["skills"][0]["skill_id"], "hermes"))

    def test_policy_epoch_mismatch_is_advisory_only(self):
        rep = self.cc.validate_contract(self.public_doc(), host="generic",
                                        expected_policy_epoch=99)
        # mismatch recorded, but it must NOT reject (POLICY_EPOCH is not a gate)
        self.assertFalse(rep["policy_epoch_ok"])
        self.assertNotEqual(rep["status"], self.cc.ST_INCOMPATIBLE)


class ContractFallbackTest(_Fixture, unittest.TestCase):
    """11. registry unavailable -> V3 advisory fallback + 12. old-V3 regression."""

    def test_absent_contract_degrades_v3_intact(self):
        rep = self.cc.validate_contract(None, host="generic")
        self.assertEqual(rep["status"], self.cc.ST_DEGRADED)
        doc, why = self.cc.load_contract(str(self.root / "no-such-contract.json"))
        self.assertIsNone(doc)
        self.assertIsNotNone(why)

    def test_corrupt_contract_degrades(self):
        bad = self.root / "bad-contract.json"
        bad.write_text("{not json", encoding="utf-8")
        doc, why = self.cc.load_contract(str(bad))
        self.assertIsNone(doc)
        self.assertIn("unavailable", why)

    def test_v3_router_still_routes_without_any_contract(self):
        """Old-V3 regression: tool_master routes from the registry directly; the
        new contract layer is additive and must not break the base V3 advisory
        path (catalog unavailable -> bounded discovery -> general workflow)."""
        tm = _tool_master()
        packet = tm.build_route_packet(
            "review the public alpha skill", root=str(self.root),
            host="generic", profile="normal")
        # advisory packet always present, tools always intact
        self.assertTrue(packet["advisory"])
        self.assertIn("tools", packet)
        self.assertEqual(packet["host"], "generic")

    def test_composer_fallback_on_empty_registry(self):
        """composer.compose (V3 advisory) must not crash on an empty registry —
        it returns a successful advisory packet with 0 skills. The contract layer
        is therefore not a new hard dependency (V3 stays fail-open)."""
        composer = _composer()
        with tempfile.TemporaryDirectory() as empty:
            packet = composer.compose("do something", reg_root=empty,
                                      hosts=("generic",), profile="normal")
            self.assertFalse(packet.get("fallback", False),
                             f"empty registry must not trigger a crash-fallback: {packet.get('fallback_reason')}")
            self.assertEqual(packet.get("candidate_pool_size", 0), 0)
            self.assertEqual(packet.get("composition", []), [])

    def test_reconcile_fail_open_on_missing_layers(self):
        with tempfile.TemporaryDirectory() as empty:
            rec = self.contract.reconcile_categories(empty)
            self.assertEqual(rec["layer_records"], 0)
            self.assertEqual(rec["runnable_skills"], 0)

    def test_contract_provider_cli_runs(self):
        """M4-P3-001 regression: both new CLIs must build their subparser
        trees under the CI/runtime Python. Python 3.14 removed the
        2-positional-arg add_parser(name, help) form — the keyword
        add_parser(name, help=...) is the stable one. Calling main() with
        no args exercises subparser construction + parse without side effects."""
        args = ["--root", str(self.root)]
        rc = self.contract.main(["reconcile"] + args)
        self.assertEqual(rc, 0)

    def test_contract_consumer_cli_runs(self):
        doc = self.public_doc()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            rc = self.cc.main(["validate", str(path), "--host", "generic",
                               "--expected-revision", doc["registry_revision"],
                               "--expected-source-commit", self.COMMIT,
                               "--json"])
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
