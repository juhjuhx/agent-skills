#!/usr/bin/env python3
"""M4 P4 — Scout complete: commit pinning, HTTP-error classification,
security scan, duplicate detection, candidate gating.

Hermetic: zero network. github_search is exercised through classify_http_error
(deterministic) and resolve_source_commit through an injected fake fetcher, so
CI passes without a live GitHub connection.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _scout():
    spec = importlib.util.spec_from_file_location(
        "scout", REPO / "scout/scout.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeResp:
    """Minimal context-manager body for an injected fake fetcher."""

    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._payload

    def close(self):
        pass


def _ok_fetch(sha):
    def fetch(url, timeout=None):
        return FakeResp({"sha": sha})
    return fetch


def _fail_fetch():
    import urllib.error

    def fetch(url, timeout=None):
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)
    return fetch


class CommitPinningTest(unittest.TestCase):
    """SCOUT_COMMIT_PINNING_TEST：branch 名稱絕不冒充 SHA；只認 40-hex。"""

    def test_branch_name_is_not_a_pin(self):
        s = _scout()
        self.assertFalse(s.is_full_commit_ref("main"))
        self.assertFalse(s.is_full_commit_ref("abc123"))
        self.assertTrue(s.is_full_commit_ref("c" * 40))

    def test_pin_branch_resolves_to_40hex(self):
        s = _scout()
        cand = {"id": "gh:x", "source_repo": "https://github.com/o/r",
                "source_commit": "main"}
        out = s.pin_candidate(cand, fetch=_ok_fetch("c" * 40))
        self.assertTrue(out["commit_pinned"])
        self.assertEqual(out["source_commit"], "c" * 40)
        self.assertEqual(out["commit_resolution"]["branch"], "main")

    def test_pin_already_full_sha_skips_resolution(self):
        s = _scout()
        out = s.pin_candidate({"id": "gh:y", "source_commit": "d" * 40},
                              fetch=_ok_fetch("c" * 40))
        self.assertTrue(out["commit_pinned"])
        self.assertEqual(out["source_commit"], "d" * 40)

    def test_pin_failure_is_unpinned_not_fake(self):
        s = _scout()
        out = s.pin_candidate({"id": "gh:z", "source_repo": "https://github.com/o/r",
                                "source_commit": "main"}, fetch=_fail_fetch())
        self.assertFalse(out["commit_pinned"])
        self.assertIsNotNone(out.get("commit_unpinned_reason"))
        # source_commit 欄位絕不偽裝成 pin：失敗時清空，原始值存 unpinned
        self.assertIsNone(out["source_commit"])
        self.assertEqual(out["unpinned_source_commit"], "main")

    def test_missing_repo_cannot_pin(self):
        s = _scout()
        out = s.pin_candidate({"id": "gh:w", "source_repo": None,
                                "source_commit": "main"})
        self.assertFalse(out["commit_pinned"])


class HttpClassificationTest(unittest.TestCase):
    """SCOUT_RATE_LIMIT_TEST：429 與「帶 rate-limit 訊號的 403」可重試；
    普通 403／其他 4xx 絕不重試；5xx 可重試。"""

    def test_429_is_rate_limited_retryable(self):
        s = _scout()
        v = s.classify_http_error(429, {"Retry-After": "30"})
        self.assertEqual(v["category"], "rate_limited")
        self.assertTrue(v["retryable"])
        self.assertEqual(v["retry_after_s"], 30)

    def test_403_with_rate_headers_is_rate_limited(self):
        s = _scout()
        v = s.classify_http_error(
            403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1"})
        self.assertEqual(v["category"], "rate_limited")
        self.assertTrue(v["retryable"])

    def test_plain_403_is_forbidden_never_retry(self):
        s = _scout()
        v = s.classify_http_error(403, {"Retry-After": "10"})
        self.assertEqual(v["category"], "forbidden")
        self.assertFalse(v["retryable"])
        self.assertTrue(v["should_stop"])

    def test_403_with_rate_headers_but_not_exhausted_is_forbidden(self):
        s = _scout()
        v = s.classify_http_error(403, {"x-ratelimit-remaining": "5"})
        self.assertEqual(v["category"], "forbidden")
        self.assertFalse(v["retryable"])

    def test_other_4xx_fatal(self):
        s = _scout()
        for code in (400, 404, 422):
            v = s.classify_http_error(code, {})
            self.assertEqual(v["category"], "fatal", code)
            self.assertFalse(v["retryable"])

    def test_5xx_transient_retryable(self):
        s = _scout()
        v = s.classify_http_error(503, {})
        self.assertEqual(v["category"], "transient")
        self.assertTrue(v["retryable"])

    def test_retry_budget_is_capped(self):
        s = _scout()
        self.assertLessEqual(s.MAX_RETRIES, 2)
        self.assertEqual(s.RATE_LIMIT_PAUSE_S, 65)


    def test_transient_5xx_retries_once_end_to_end(self):
        """P4 語意：5xx transient 允許一個短的 backoff 重試，但有上限。"""
        import urllib.error
        s = _scout()
        calls = {"n": 0}

        class Transient500:
            def __call__(self, req, **kw):
                calls["n"] += 1
                raise urllib.error.HTTPError("u", 500, "boom", {}, None)

        sleeps = []
        s.urllib.request.urlopen = Transient500()
        items, meta = s.github_search("test", sleep=sleeps.append)
        self.assertIsNone(items)
        self.assertEqual(meta["attempts"], s.MAX_RETRIES + 1)
        self.assertEqual(len(sleeps), s.MAX_RETRIES)


class SecurityScanTest(unittest.TestCase):
    """SCOUT_SECURITY_SCAN_TEST：secret / 本機路徑 / 檔案邊界，high 級 → blocked。"""

    def test_clean_candidate_not_blocked(self):
        s = _scout()
        r = s.security_scan({"name": "ok", "description": "a nice skill",
                              "source_repo": "https://github.com/a/b"})
        self.assertFalse(r["blocked"])
        self.assertEqual(r["counts"], {})

    def test_secret_in_metadata_blocks(self):
        s = _scout()
        r = s.security_scan({"name": "x",
                              "description": "token ghp_" + "a" * 24})
        self.assertTrue(r["blocked"])
        self.assertGreaterEqual(r["counts"].get("high", 0), 1)

    def test_local_absolute_path_is_medium_not_blocked(self):
        s = _scout()
        r = s.security_scan({"name": "x",
                              "description": "run at /Users/huang/secret/x"})
        self.assertFalse(r["blocked"])
        self.assertEqual(r["counts"].get("medium", 0), 1)

    def test_file_scan_detects_secret(self):
        s = _scout()
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "leak.txt").write_text("password = \"hunter2secret\"\n",
                                         encoding="utf-8")
            r = s.security_scan({"name": "t"}, candidate_dir=str(d))
        self.assertTrue(r["blocked"])
        self.assertIn("password_literal",
                       [f["kind"] for f in r["findings"]])

    def test_file_scan_bounded(self):
        s = _scout()
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for i in range(70):
                (d / f"f{i}.txt").write_text("x", encoding="utf-8")
            r = s.security_scan({"name": "t"}, candidate_dir=str(d))
        self.assertGreaterEqual(r["counts"].get("low", 0), 1)


class DuplicateDetectionTest(unittest.TestCase):
    """SCOUT_DUPLICATE_CANDIDATES_TEST：exact / digest / name 三種重複。"""

    def test_exact_id_duplicate(self):
        s = _scout()
        recs = [{"id": "public:A", "name": "alpha"}]
        r = s.find_duplicate_candidates({"id": "public:A"}, recs)
        self.assertTrue(r["is_duplicate"])
        self.assertEqual(r["matches"][0]["kind"], "exact")

    def test_digest_duplicate(self):
        s = _scout()
        recs = [{"id": "public:A", "sha256": "a" * 64}]
        r = s.find_duplicate_candidates({"id": "local:NEW", "sha256": "a" * 64}, recs)
        self.assertTrue(r["is_duplicate"])
        self.assertEqual(r["matches"][0]["kind"], "digest")

    def test_name_duplicate_same_repo(self):
        s = _scout()
        recs = [{"id": "public:A", "name": "alpha",
                 "source_repo": "https://github.com/a/b"}]
        r = s.find_duplicate_candidates(
            {"id": "local:N", "name": "ALPHA",
             "source_repo": "https://github.com/a/b"}, recs)
        self.assertTrue(r["is_duplicate"])
        self.assertEqual(r["matches"][0]["kind"], "name")

    def test_no_false_positive(self):
        s = _scout()
        recs = [{"id": "public:A", "name": "alpha"}]
        r = s.find_duplicate_candidates(
            {"id": "local:Z", "name": "gamma", "source_repo": "https://github.com/z/z"},
            recs)
        self.assertFalse(r["is_duplicate"])


class CandidateGatingTest(unittest.TestCase):
    """未審查/被安全擋下的候選絕不進 stage（UNREVIEWED != EXECUTION_AUTHORIZED）。"""

    def test_security_blocked_rejects(self):
        s = _scout()
        ev = s.assess_candidate(
            {"id": "local:BAD", "name": "bad",
             "description": "leak sk-" + "a" * 24}, [])
        self.assertEqual(ev["recommendation"], "reject")
        self.assertEqual(ev["reject_reason"], "security_scan_high")
        self.assertTrue(ev["security_blocked"])

    def test_hard_duplicate_rejects(self):
        s = _scout()
        recs = [{"id": "public:A", "name": "alpha", "sha256": "a" * 64}]
        ev = s.assess_candidate(
            {"id": "public:A", "name": "alpha", "sha256": "a" * 64,
             "description": "a good alpha skill for reviewing code"},
            ["other"], existing_records=recs)
        self.assertEqual(ev["recommendation"], "reject")
        self.assertEqual(ev["reject_reason"], "duplicate_of_existing")

    def test_clean_credential_candidate_not_rejected(self):
        s = _scout()
        ev = s.assess_candidate(
            {"id": "local:GOOD", "name": "good",
             "description": "a clean useful skill with documentation",
             "source_repo": "https://github.com/g/g"},
            [])
        self.assertNotEqual(ev["recommendation"], "reject")
        self.assertFalse(ev["security_blocked"])


class ScoutCliTest(unittest.TestCase):
    """P4 冒煙：scout CLI 在 py3.14 正常構建子指令樹（防 argparse 回歸）。"""

    def test_scout_cli_builds_subparsers(self):
        s = _scout()
        with tempfile.TemporaryDirectory() as tmp:
            # discover on an empty root must not crash (fail-open, 0 candidates)
            rc = s.main(["discover", "--root", tmp])
            self.assertEqual(rc, 0)

    def test_scout_assess_cli_unknown_candidate(self):
        s = _scout()
        with tempfile.TemporaryDirectory() as tmp:
            rc = s.main(["assess", "no-such-slug", "--root", tmp])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
