#!/usr/bin/env python3
"""P6 測試（第二檔）：SCOUT_DISCOVERY / SCOUT_RATE_LIMIT / SCOUT_FAIL_OPEN /
SCOUT_IDEMPOTENCE / FORGE_RECURSION_BOUND / FORGE_LINEAGE / FORGE_REGRESSION /
FORGE_ROLLBACK / COMPOSITION_SELECTION / V3_ROUTING_RELEVANCE。

純標準庫；不觸碰 ~/.agents/skills；fixture 全在 tmp dir。
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
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


def _scout():
    return _load(REPO / "scout/scout.py", "scout")


def _forge():
    return _load(REPO / "forge/forge.py", "forge")


def _composer():
    return _load(REPO / "runtime/skills-router/extensions/skill-composer/composer.py", "composer")


# ---------------------------------------------------------------- scout

class ScoutDiscoveryTest(unittest.TestCase):
    """SCOUT_DISCOVERY_TEST：離線 discover 從 history 層列 candidate 候選。"""

    def test_discover_returns_candidates_and_names(self):
        scout = _scout()
        reg = _reg()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # hermetic：在 tmp registry 建 2 筆 candidate + 1 筆 private name，
            # 不依賴真實 ~/.local registry（CI 的 clean checkout 沒有私人層）
            c1, _ = reg.build_record(
                id="hist:a", name="alpha-skill", relative_path="a/SKILL.md",
                sha="a" * 64, license="MIT", status="candidate",
                visibility="private", risk="unreviewed", description="alpha")
            c2, _ = reg.build_record(
                id="hist:b", name="beta-skill", relative_path="b/SKILL.md",
                sha="b" * 64, license="MIT", status="candidate",
                visibility="private", risk="unreviewed", description="beta")
            p, _ = reg.build_record(
                id="priv:c", name="gamma-skill", relative_path="c/SKILL.md",
                sha="c" * 64, license="MIT", status="approved_private",
                visibility="private", risk="low", description="gamma")
            hist = reg.load_layer(str(root), "history")
            hist["records"].extend([c1, c2])
            reg.save_layer(str(root), "history", hist)
            priv = reg.load_layer(str(root), "private")
            priv["records"].append(p)
            reg.save_layer(str(root), "private", priv)

            cands, names = scout.discover_local(str(root))
            self.assertEqual(len(cands), 2, f"expected 2 candidates, got {len(cands)}")
            self.assertTrue(all(c["id"] for c in cands))
            self.assertEqual(len(names), 1)  # 只有 approved_private name
            self.assertIn("gamma-skill", names)

    def test_discover_empty_registry_fail_open(self):
        scout = _scout()
        with tempfile.TemporaryDirectory() as tmp:
            cands, names = scout.discover_local(tmp)
            self.assertEqual(cands, [])
            self.assertEqual(names, [])


class ScoutRateLimitTest(unittest.TestCase):
    """SCOUT_RATE_LIMIT_TEST: 403/429 → backoff 重試（有上限）；非 rate-limit 錯誤終止。"""

    def test_rate_limit_retries_bounded(self):
        """429（rate-limit）→ backoff 重試至上限 MAX_RETRIES。"""
        scout = _scout()
        import urllib.error

        calls = {"n": 0}

        class AlwaysRateLimited:
            def __call__(self, req, **kw):
                calls["n"] += 1
                # 429 一律是 rate-limit（無需 X-RateLimit header）
                raise urllib.error.HTTPError(
                    "u", 429, "rate limited", {"Retry-After": "1"}, None)

        fake_sleeps = []
        scout.urllib.request.urlopen = AlwaysRateLimited()
        items, meta = scout.github_search("test", token=None,
                                           sleep=fake_sleeps.append)
        self.assertIsNone(items)
        self.assertIn("429", meta["error"])
        self.assertEqual(meta["attempts"], scout.MAX_RETRIES + 1)
        self.assertEqual(len(fake_sleeps), scout.MAX_RETRIES)  # 只 backoff 上限次數

    def test_retry_after_http_date_does_not_crash(self):
        """F1: Retry-After 為 HTTP-date 時不得 int() 崩潰（fail-open 保全校）。"""
        scout = _scout()
        import urllib.error

        class DateRetry:
            def __call__(self, req, **kw):
                raise urllib.error.HTTPError(
                    "u", 429, "slow", {"Retry-After": "Wed, 21 Oct 2026 07:00:00 GMT"},
                    None)

        fake_sleeps = []
        scout.urllib.request.urlopen = DateRetry()
        # 不得拋 ValueError；應正常回 (None, meta) 且 backoff 回落為固定值
        items, meta = scout.github_search("test", sleep=fake_sleeps.append)
        self.assertIsNone(items)
        self.assertEqual(meta["attempts"], scout.MAX_RETRIES + 1)
        # backoff 數值應被 clamp 到 [0, RATE_LIMIT_PAUSE_S]
        self.assertTrue(all(0 <= s <= scout.RATE_LIMIT_PAUSE_S for s in fake_sleeps))

    def test_plain_403_with_retry_after_not_retried(self):
        """F2: 普通 403 即使附 Retry-After、無 X-RateLimit 訊號，也不重試。"""
        scout = _scout()
        import urllib.error
        calls = {"n": 0}

        class Waf403:
            def __call__(self, req, **kw):
                calls["n"] += 1
                raise urllib.error.HTTPError(
                    "u", 403, "Forbidden", {"Retry-After": "1"}, None)

        scout.urllib.request.urlopen = Waf403()
        items, meta = scout.github_search("test", sleep=lambda s: None)
        self.assertIsNone(items)
        self.assertEqual(calls["n"], 1, "403 without rate-limit signal must not retry")
        self.assertEqual(meta["attempts"], 1)

    def test_non_rate_limit_403_not_retried(self):
        """普通 403 Forbidden（無 Retry-After / X-RateLimit-Remaining:0）絕不重試。"""
        scout = _scout()
        import urllib.error
        calls = {"n": 0}

        class Plain403:
            def __call__(self, req, **kw):
                calls["n"] += 1
                # 模擬無權限 403：只有普通 headers，無任何 rate-limit 訊號
                raise urllib.error.HTTPError("u", 403, "Forbidden", {}, None)

        scout.urllib.request.urlopen = Plain403()
        items, meta = scout.github_search("test", sleep=lambda s: None)
        self.assertIsNone(items)
        self.assertEqual(calls["n"], 1, "plain 403 must NOT be retried")
        self.assertEqual(meta["attempts"], 1)

    def test_rate_limited_403_is_retried(self):
        """403 帶 X-RateLimit-Remaining:0 → 視為 rate-limit，重試至上限。"""
        scout = _scout()
        import urllib.error
        calls = {"n": 0}

        class Rate403:
            def __call__(self, req, **kw):
                calls["n"] += 1
                raise urllib.error.HTTPError(
                    "u", 403, "rate limited",
                    {"X-RateLimit-Remaining": "0", "Retry-After": "1"}, None)

        sleeps = []
        scout.urllib.request.urlopen = Rate403()
        items, meta = scout.github_search("test", sleep=sleeps.append)
        self.assertIsNone(items)
        self.assertEqual(meta["attempts"], scout.MAX_RETRIES + 1)
        self.assertEqual(len(sleeps), scout.MAX_RETRIES)

    def test_non_rate_limit_error_no_retry(self):
        scout = _scout()
        import urllib.error
        calls = {"n": 0}

        class ServerErr:
            def __call__(self, req, **kw):
                calls["n"] += 1
                raise urllib.error.HTTPError("u", 500, "boom", {}, None)

        scout.urllib.request.urlopen = ServerErr()
        items, meta = scout.github_search("test", sleep=lambda s: None)
        self.assertIsNone(items)
        self.assertEqual(calls["n"], 1)
        self.assertEqual(meta["attempts"], 1)


class ScoutFailOpenTest(unittest.TestCase):
    """SCOUT_FAIL_OPEN_TEST: 無網路／錯誤 → (None, {error})，不炸呼叫端。"""

    def test_network_error_fails_open(self):
        scout = _scout()

        def boom(req, **kw):
            raise OSError("no network")

        scout.urllib.request.urlopen = boom
        items, meta = scout.github_search("test", sleep=lambda s: None)
        self.assertIsNone(items)
        self.assertIn("error", meta)


class ScoutIdempotenceTest(unittest.TestCase):
    """SCOUT_IDEMPOTENCE_TEST: 同候選重複 stage → 單一路由檔案、單一條 state。"""

    def test_stage_is_idempotent(self):
        scout = _scout()
        # 在 tmp 下隔離 proposals/state（重定向模組常數）
        tmp = Path(tempfile.mkdtemp())
        old_props, old_state = scout.PROPOSALS, scout.SCOUT_STATE
        scout.PROPOSALS = tmp / "proposals"
        scout.SCOUT_STATE = tmp / "scout-state.json"
        try:
            cand = {"id": "gh:acme/k8s-cert", "name": "k8s-cert"}
            ev = {"candidate": "gh:acme/k8s-cert", "score": 0.8, "recommendation": "stage"}
            scout.stage(cand, ev)
            scout.stage(cand, ev)
            scout.stage(cand, ev)
            state = json.loads(scout.SCOUT_STATE.read_text())
            staged = state["staged"]
            self.assertEqual(len(staged), 1, "repeated stage must not duplicate")
            self.assertEqual(staged[0]["id"], "gh:acme/k8s-cert")
            # 驗證 state 指向的 proposal 檔確實存在（依 state 記錄，不硬編 slug）
            self.assertTrue(Path(staged[0]["file"]).is_file())
        finally:
            scout.PROPOSALS, scout.SCOUT_STATE = old_props, old_state


# ---------------------------------------------------------------- forge

def _mk_registry(root, skills):
    """建一個含 public layer 的最小 registry，供 forge/composition 分析。

    同時寫出相對應的 SKILL.md 正文並以實際 sha256 入庫 → composition 可
    走 verified body 路徑（body_status=verified 需 digest 匹配）。
    """
    import hashlib as _hl
    reg = _reg()
    records = []
    for s in skills:
        rel = s.get("rel", "x/SKILL.md")
        body = (f"---\nname: {s['name']}\ndescription: {s.get('desc', '')}\n---\n\n"
                f"# {s['name']}\n\nbody\n")
        p = Path(root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        rec, _ = reg.build_record(
            id=s["id"], name=s["name"], relative_path=rel,
            sha=_hl.sha256(body.encode("utf-8")).hexdigest(),
            license="MIT", status="approved_public",
            visibility="public", risk="low", description=s.get("desc", ""))
        records.append(rec)
    doc = reg.load_layer(root, "public")
    doc["records"] = records
    return reg.save_layer(root, "public", doc)


class ForgeRecursionBoundTest(unittest.TestCase):
    """FORGE_BOUNDED_RECURSION_TEST: generation 不得超過 MAX_DEPTH=2。"""

    def test_generation_capped_at_max_depth(self):
        forge = _forge()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # generation=2 的既有技能，且 token 會命中 evidence → 會被選為 parent
            reg = _reg()
            rec, _ = reg.build_record(
                id="forge:deep", name="deep", relative_path="d/SKILL.md",
                sha="b" * 64, license="MIT", status="approved_private",
                visibility="private", risk="unreviewed",
                provenance={"kind": "hermes_forge"}, generation=2,
                description="deep x y z")
            doc = reg.load_layer(str(root), "private")
            doc["records"].append(rec)
            reg.save_layer(str(root), "private", doc)
            # "x y z" 命中 deep 的 token → 選為 parent，但 gen2+1=3 > MAX_DEPTH=2 → 拒絕
            acc, rej = forge.forge_round(
                registry_records=[rec],
                task_evidence="deep x y z totally new capability",
                baseline_score=0.0)
            # 結構不變量（真正的迴歸守門）：無論消息措辭，決不產出 gen>MAX_DEPTH 的 accepted
            self.assertEqual(acc, [])
            self.assertTrue(all(a.get("generation", 0) <= forge.MAX_DEPTH for a in acc))
            self.assertTrue(rej, "expected a rejection")
            # 行為證據：拒絕必須來自 depth-bound 分支（非其他原因）
            self.assertTrue(any("MAX_DEPTH" in r.get("reason", "") or
                                 "generation" in r.get("reason", "")
                                 for r in rej),
                f"expected depth-bound rejection, got {rej}")


class ForgeLineageTest(unittest.TestCase):
    """FORGE_LINEAGE_TEST: 合成技能保留 parent/provenance/generation。"""

    def test_standalone_candidate_carries_lineage_fields(self):
        forge = _forge()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mk_registry(str(root), [{"id": "public:a", "name": "alpha", "desc": "x y z"}])
            acc, rej = forge.forge_round(
                registry_records=_reg().load_layer(str(root), "public")["records"],
                task_evidence="brand new capability unique domain",
                baseline_score=0.0)
            self.assertTrue(acc, f"expected an accepted standalone candidate, got rej={rej}")
            entry = acc[0]
            for field in ("parents", "generation", "body_sha256", "created_at",
                         "test_cases", "baseline_score", "new_score", "acceptance_reason"):
                self.assertIn(field, entry, field)
            self.assertEqual(entry["generation"], 0)
            self.assertEqual(entry["parents"], [])
            self.assertEqual(entry["baseline_score"], 0.0)


class ForgeRegressionTest(unittest.TestCase):
    """FORGE_REGRESSION_TEST: 無證明改進（new_score <= baseline）必須被拒絕。"""

    def test_no_improvement_rejected(self):
        forge = _forge()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mk_registry(str(root), [{"id": "public:a", "name": "alpha", "desc": "x y z"}])
            # baseline 設 1.0（滿分）→ 任何新技能無法超越 → 應全 reject
            acc, rej = forge.forge_round(
                registry_records=_reg().load_layer(str(root), "public")["records"],
                task_evidence="brand new capability unique domain",
                baseline_score=1.0)
            self.assertEqual(acc, [])
            self.assertTrue(rej)
            for r in rej:
                self.assertTrue(
                    "improved=False" in r.get("reason", ""),
                    f"unexpected rejection reason: {r}")


class ForgeRollbackTest(unittest.TestCase):
    """FORGE_ROLLBACK_TEST: accept 後 rollback 移除該 forge 記錄、保留他層。"""

    def test_accept_then_rollback(self):
        forge = _forge()
        reg = _reg()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mk_registry(str(root), [{"id": "public:a", "name": "alpha", "desc": "x y z"}])
            acc, rej = forge.forge_round(
                registry_records=reg.load_layer(str(root), "public")["records"],
                task_evidence="brand new capability unique domain",
                baseline_score=0.0)
            self.assertTrue(acc, f"need an accepted candidate; rej={rej}")
            entry = acc[0]
            # 用 forge 自己的 accept 路徑（寫入 private + snapshot）
            body_path = forge.WORKSPACE / f"{entry['name']}.md"
            self.assertTrue(body_path.exists(), "forge round must persist candidate body")
            entry["body"] = body_path.read_text()
            pre = reg.snapshot(str(root), "private", f"pre-{entry['name']}")
            entry["rollback_version"] = str(pre)
            record, snap = forge.accept_to_registry(entry, str(root), "test")
            priv = reg.load_layer(str(root), "private")
            self.assertTrue(any(r["id"] == record["id"] for r in priv["records"]))
            # rollback 到 pre-snapshot → forge 記錄應消失
            reg.rollback(str(root), "private", pre.name)
            priv2 = reg.load_layer(str(root), "private")
            self.assertFalse(any(r["id"] == record["id"] for r in priv2["records"]),
                "rollback must remove the forge record")


# ---------------------------------------------------------------- composition

class CompositionSelectionTest(unittest.TestCase):
    """COMPOSITION_SELECTION_TEST: 最小足夠技能組、profile 大小、0 候選亦允許。"""

    def test_profile_limits_composition_size(self):
        composer = _composer()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reg = _reg()
            skills = []
            for i in range(6):
                skills.append({"id": f"public:s{i}", "name": f"skill{i}",
                               "desc": "kubernetes tls cert automation", "rel": f"s{i}/SKILL.md"})
            _mk_registry(str(root), skills)
            for profile, cap in (("guided", 1), ("normal", 2), ("high", 4)):
                packet = composer.compose(
                    "kubernetes tls cert automation", reg_root=str(root),
                    hosts=("generic",), profile=profile,
                    local_roots={"x": str(root)})
                self.assertFalse(packet.get("fallback"), profile)
                self.assertLessEqual(len(packet["composition"]), cap, profile)

    def test_no_match_yields_empty_composition_not_fallback(self):
        composer = _composer()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mk_registry(str(root), [{"id": "public:a", "name": "alpha", "desc": "cooking"}])
            packet = composer.compose("completely unrelated quantum task",
                                      reg_root=str(root), hosts=("generic",),
                                      profile="normal", local_roots={"x": str(root)})
            self.assertFalse(packet.get("fallback"))
            self.assertEqual(packet["composition"], [])


class V3RoutingRelevanceTest(unittest.TestCase):
    """V3_ROUTING_RELEVANCE_TEST: 跨域任務不得誤選不相關技能（python review → 非 UI/ppt）。"""

    def test_python_review_excludes_ui_ppt_domains(self):
        composer = _composer()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills = [
                {"id": "public:py-review", "name": "py-review",
                 "desc": "python code review fastapi bugs", "rel": "py/SKILL.md"},
                {"id": "public:powerpoint", "name": "powerpoint",
                 "desc": "create pptx slides presentation", "rel": "pp/SKILL.md"},
                {"id": "public:ui-style", "name": "ui-style",
                 "desc": "ui styling design frontend", "rel": "ui/SKILL.md"},
            ]
            _mk_registry(str(root), skills)
            packet = composer.compose("review python code for bugs in fastapi",
                                      reg_root=str(root), hosts=("generic",),
                                      profile="high", local_roots={"x": str(root)})
            self.assertFalse(packet.get("fallback"))
            ids = [c["id"] for c in packet["composition"]]
            for bad in ("public:powerpoint", "public:ui-style"):
                self.assertNotIn(bad, ids, f"{bad} wrongly composed")
            self.assertIn("public:py-review", ids)

    def test_router_failure_does_not_disable_host_tools(self):
        """V3 既有 advisory 路由在 router 故障時仍可產出（fail-open）。"""
        tm = _load(REPO / "runtime/skills-router/tool_master.py", "tool_master")
        with tempfile.TemporaryDirectory() as tmp:
            # 無 catalog、無 SKILL.md → router 走 general fallback
            packet = tm.build_route_packet("do something", root=tmp, host="generic")
            self.assertTrue(packet["advisory"])
            self.assertFalse(packet.get("tools") is None)
            # host 工具 schema 不因 router 無技能而消失
            self.assertIn("READ", packet["tools"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
