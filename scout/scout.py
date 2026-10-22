#!/usr/bin/env python3
"""Skill Scout — 自動嗅探、比較、評估新技能。可獨立停用。

安全邊界：
  - 只讀取與解析資料；絕不執行未審查第三方安裝腳本。
  - 首次引入含程式碼的技能不會取得宿主執行權限；只 stage 到 proposals 隔離區。
  - GitHub API 搜尋 rate-limited；保留檢查時間與來源 commit。
  - 離線可運作：掃本地 registry + 既有 proposals。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATE = Path.home() / ".local/agent-skills/registry-private"
PROPOSALS = STATE / "proposals"
SCOUT_STATE = STATE / "scout-state.json"
REGISTRY_TOOL = Path(__file__).resolve().parent.parent / "registry/tools/registry.py"

# 候選評分維度（0..1 加權）
WEIGHTS = {
    "functional_value": 0.20,
    "overlap_penalty": 0.15,   # 與現有重疊越高分越低（已在評分函數內取反）
    "has_source": 0.10,
    "license_clarity": 0.15,
    "maintenance": 0.10,
    "dependency_simplicity": 0.05,
    "security_risk": 0.15,     # 越高越危險；評分內取反
    "workflow_relevance": 0.10,
    "maintenance_cost": 0.05,
    "testability": 0.05,
}
# 使用者工作流相關域（來自 AGENTS：AI/CLI/MCP、Android、Kotlin、Rust、TS、Py、
# 本地模型、影片/音訊、DaVinci/Kdenlive、劇場燈光、投影、文書自動化、測試工程）
RELEVANT_DOMAINS = [
    "ai", "agent", "mcp", "cli", "android", "kotlin", "rust", "typescript",
    "python", "lora", "local-model", "video", "audio", "davinci", "kdenlive",
    "lighting", "theater", "projection", "docx", "xlsx", "pptx", "testing",
]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_registry_counts(root):
    import importlib.util
    spec = importlib.util.spec_from_file_location("registry", REGISTRY_TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load registry module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = {}
    for layer in ("public", "private", "history"):
        try:
            doc = mod.load_layer(root, layer)
            out[layer] = doc["records"]
        except Exception:
            out[layer] = []
    return out


def _name_tokens(name):
    return set(re.findall(r"[a-z0-9]+", (name or "").lower()))


def evaluate_candidate(cand, existing_names, root="."):
    """對單一候選回傳 0..1 總分與拆解。純本地、無副作用。"""
    name = cand.get("name", "")
    desc = (cand.get("description") or "").lower()
    tokens = _name_tokens(name) | _name_tokens(desc)

    license = cand.get("license", "unknown")
    license_clarity = {"MIT": 1.0, "Apache-2.0": 1.0, "BSD-2-Clause": 0.95,
                       "BSD-3-Clause": 0.95, "ISC": 0.9, "GPL-3.0": 0.7,
                       "LGPL-3.0": 0.7, "MPL-2.0": 0.7, "proprietary": 0.1,
                       "unknown": 0.0}.get(license, 0.0)

    has_source = 1.0 if cand.get("source_repo") else 0.0
    deps = len(cand.get("dependencies") or [])
    dep_simple = 1.0 if deps == 0 else max(0.0, 1.0 - 0.15 * deps)
    maint = {"active": 1.0, "stale": 0.4, "archived": 0.1, "unknown": 0.3}.get(cand.get("maintenance"), 0.3)
    security = {"low": 1.0, "medium": 0.5, "high": 0.1, "blocked": 0.0, "unreviewed": 0.4}.get(cand.get("security_risk"), 0.4)

    # 與現有重疊（取反：重疊越多分越低）
    overlap_hits = sum(1 for ex in existing_names if _name_tokens(ex) & tokens)
    overlap_ratio = overlap_hits / max(len(existing_names), 1)
    overlap_penalty = min(1.0, overlap_ratio * 2)   # 高重疊 -> 高罰

    relevant = any(d in desc for d in RELEVANT_DOMAINS) or bool(
        _name_tokens(cand.get("category", "")) & set(RELEVANT_DOMAINS))
    workflow_relevance = 0.9 if relevant else 0.4
    functional = 0.8 if desc else 0.3
    testable = 0.8 if cand.get("testable", True) else 0.2
    maint_cost = 0.6  # 中性

    breakdown = {
        "functional_value": functional,
        "overlap_penalty": overlap_penalty,
        "has_source": has_source,
        "license_clarity": license_clarity,
        "maintenance": maint,
        "dependency_simplicity": dep_simple,
        "security_risk": security,
        "workflow_relevance": workflow_relevance,
        "maintenance_cost": maint_cost,
        "testability": testable,
    }
    # overlap_penalty 是罰項，其餘正向；總分 = 加權正向 - 加權罰項
    positive = sum(WEIGHTS[k] * breakdown[k] for k in WEIGHTS if k != "overlap_penalty")
    score = round(max(0.0, positive - WEIGHTS["overlap_penalty"] * overlap_penalty), 3)
    return {
        "candidate": cand.get("id") or cand.get("name"),
        "score": score,
        "recommendation": "stage" if score >= 0.72 else ("review" if score >= 0.5 else "reject"),
        "breakdown": breakdown,
        "existing_overlap_hits": overlap_hits,
        "computed_at": now_iso(),
    }


def discover_local(root="."):
    """離線：把 registry 中所有 candidate/quarantined/local 候選列為可評估目標。"""
    counts = load_registry_counts(root)
    names = [r["name"] for r in counts.get("private", [])]
    out = []
    for rec in counts.get("history", []):
        if rec.get("status") in ("candidate",):
            out.append({
                "id": rec["id"], "name": rec["name"], "license": rec.get("license"),
                "source_repo": rec.get("source_repo"), "description": rec.get("description", ""),
                "category": rec.get("category", []), "security_risk": "unreviewed",
            })
    return out, names


RATE_LIMIT_PAUSE_S = 65
MAX_RETRIES = 2
RETRY_PAUSE_S = 5


def classify_http_error(code, headers):
    """M4 P4 — GitHub HTTP 錯誤分類（純函式、可 hermetic 測試、絕不重試不可重試類）。

    rate_limited    429；或 403 + rate-limit 訊號（Retry-After / X-RateLimit
                    家族 header 且 X-RateLimit-Remaining: 0）→ 可有限 backoff 重試。
    forbidden       403 無 rate-limit 訊號（無權限／WAF／bot check）→ 絕不重試。
    fatal           其他 4xx（404/422/…）→ 絕不重試。
    transient       5xx / timeout / network → 可重試一次。
    回傳 {"category", "retryable", "should_stop"}，呼叫端依此決定行為。
    """
    hdrs = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    code = int(code)
    if code == 429:
        retry_after = hdrs.get("retry-after") or str(RETRY_PAUSE_S)
        try:
            seconds = int(float(retry_after))
        except (TypeError, ValueError):
            seconds = RETRY_PAUSE_S
        return {"category": "rate_limited", "retryable": True, "should_stop": False,
                "retry_after_s": max(0, min(seconds, RATE_LIMIT_PAUSE_S)),
                "reset_at": hdrs.get("x-ratelimit-reset")}
    if code == 403:
        has_rate_headers = any(k.startswith("x-ratelimit") for k in hdrs)
        exhausted = hdrs.get("x-ratelimit-remaining") == "0"
        if has_rate_headers and exhausted:
            return {"category": "rate_limited", "retryable": True, "should_stop": False,
                    "retry_after_s": RATE_LIMIT_PAUSE_S,
                    "reset_at": hdrs.get("x-ratelimit-reset")}
        # 普通 403（無權限／WAF／bot check，即使附 Retry-After）絕不重試
        return {"category": "forbidden", "retryable": False, "should_stop": True,
                "note": "plain 403 — no retry (no permission / WAF / bot check)"}
    if code >= 500:
        return {"category": "transient", "retryable": True, "should_stop": False,
                "retry_after_s": RETRY_PAUSE_S}
    return {"category": "fatal", "retryable": False, "should_stop": True,
            "note": f"HTTP {code}"}


def is_full_commit_ref(value):
    """真實 commit pinning 紀律：只認 40 字元 0-9a-f。branch 名稱 / 省略 SHA 不算 pin。"""
    return (isinstance(value, str) and len(value) == 40
            and all(c in "0123456789abcdef" for c in value.lower()))


def resolve_source_commit(repo_full_name, branch, fetch=None):
    """把 branch 名稱解析成真實 40-hex commit（GET /repos/<owner>/<repo>/commits/<branch>）。

    fetch(url) 可注入（測試用 fake fetcher；預設 urllib）。回傳：
      ok：{"sha": 40-hex, "resolved_from": {"repo","branch","url"}, "ok": True, "at"}
      fail：{"sha": None, "resolved_from": {...}, "ok": False, "error", "at"}
    絕不把 branch 名稱當 SHA 回傳 — 解析失敗就是 None。
    """
    repo_full_name = (repo_full_name or "").strip()
    repo = repo_full_name.split("github.com/")[-1] if "github.com/" in repo_full_name \
        else repo_full_name
    url = f"https://api.github.com/repos/{repo}/commits/{branch or 'HEAD'}"
    resolved_from = {"repo": repo_full_name, "branch": branch, "url": url}
    if not repo_full_name:
        return {"sha": None, "resolved_from": resolved_from, "ok": False,
                "error": "missing source_repo", "at": now_iso()}
    try:
        opener = fetch or urllib.request.urlopen
        with opener(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        sha = data.get("sha")
        if is_full_commit_ref(sha):
            return {"sha": sha, "resolved_from": resolved_from, "ok": True, "at": now_iso()}
        return {"sha": None, "resolved_from": resolved_from, "ok": False,
                "error": "response missing 40-hex sha", "at": now_iso()}
    except Exception as e:  # noqa: BLE001 - fail-open
        return {"sha": None, "resolved_from": resolved_from, "ok": False,
                "error": str(e), "at": now_iso()}


def pin_candidate(candidate, fetch=None):
    """為候選附加 commit pin：能解析就 40-hex，不能就 'unresolved' + 原因。
    'unresolved' 絕不冒充 pin（DISCOVERED != TRUSTED）。"""
    out = dict(candidate)
    if out.get("source_commit") and is_full_commit_ref(out["source_commit"]):
        out["commit_pinned"] = True
        return out
    res = resolve_source_commit(out.get("source_repo"), out.get("source_commit"), fetch=fetch)
    if res["ok"]:
        out["source_commit"] = res["sha"]
        out["commit_pinned"] = True
        out["commit_resolution"] = res["resolved_from"]
    else:
        out["commit_pinned"] = False
        out["commit_unpinned_reason"] = res.get("error")
        out["commit_resolution"] = res["resolved_from"]
        # 不偽裝成 pin：source_commit 欄位只承載 40-hex；解析失敗就清空，
        # 原始 branch／未解析值存 unpinned_source_commit 供追查。
        out["unpinned_source_commit"] = out.get("source_commit")
        out["source_commit"] = None
    return out


# ---------------- security scanning（對候選內容，只讀不執行）----------------

_SECRET_PATTERNS = [
    ("github_pat", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----")),
    ("password_literal", re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]", re.I)),
    ("api_key_literal", re.compile(r"(?:api[_-]?key|apikey)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}", re.I)),
]
_LOCAL_PATH_PAT = re.compile(r"/(?:Users|home)/[A-Za-z0-9_.\-]+/")


def security_scan(candidate, root=None, candidate_dir=None):
    """M4 P4 — 候選安全掃描（只讀、絕不執行）。

    來源：candidate 的 metadata 欄位（description/source_repo/source_commit）＋
    可選的檔案清單（candidate['files']，每項 {"path","content"}；或依
    candidate_dir 只讀收斂掃描 — 上限 64 檔 / 單檔 256KB，防 DoS）。

    findings severity：high（secret 字串）、medium（本機絕對路徑、
    symlink 目標缺損）、blocked（絕不 stage 的硬門檻）。
    回傳 {"findings":[...], "counts":{...}, "blocked": bool, "at"}。
    """
    findings = []

    def add(kind, severity, detail, where):
        findings.append({"kind": kind, "severity": severity,
                         "detail": detail, "where": where})

    # 1) metadata 側掃描（永遠執行，純文字、零 I/O）
    blob = " ".join(str(candidate.get(k, "")) for k in
                    ("name", "description", "source_repo", "source_commit"))
    for f in (candidate.get("files") or []):
        if isinstance(f, dict) and isinstance(f.get("content"), str):
            blob += "\n" + f["content"]
    for name, pat in _SECRET_PATTERNS:
        for m in pat.finditer(blob):
            add(name, "high", m.group(0)[:32] + "...(redacted)", "metadata")
    if _LOCAL_PATH_PAT.search(blob):
        add("local_absolute_path", "medium", "(redacted)", "metadata")

    # 2) 檔案側掃描（candidate_dir 模式：只讀 + 邊界檢查）
    if candidate_dir:
        base = Path(candidate_dir)
        limit_files, limit_bytes = 64, 256 * 1024
        seen = 0
        for p in sorted(base.rglob("*")):
            if seen >= limit_files:
                add("scan_limit_reached", "low", f"{limit_files} files", candidate_dir)
                break
            if p.is_symlink():
                add("symlink_in_candidate", "medium", p.name, str(p.relative_to(base)))
                continue
            if not p.is_file():
                continue
            seen += 1
            try:
                if p.stat().st_size > limit_bytes:
                    add("file_too_large", "low", f"{p.stat().st_size}B", p.name)
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                add("unreadable_file", "medium", str(exc), p.name)
                continue
            for name, pat in _SECRET_PATTERNS:
                for m in pat.finditer(text):
                    add(name, "high", m.group(0)[:32] + "...(redacted)", str(p.name))
            if _LOCAL_PATH_PAT.search(text):
                add("local_absolute_path", "medium", "(redacted)", str(p.name))

    counts = {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    return {"findings": findings, "counts": counts,
            "blocked": counts.get("high", 0) > 0, "at": now_iso()}


def find_duplicate_candidates(candidate, existing_records):
    """M4 P4 — 候選 vs 既有 registry 記錄的重複偵測。

    exact：同 skill_id；digest：同 relative_path 且同 sha256；
    name：同 canonical name（lower）。回傳 {"matches":[...], "is_duplicate"}。
    """
    matches = []
    cid, cname = str(candidate.get("id", "")).lower(), str(candidate.get("name", "")).lower()
    crepo = str(candidate.get("source_repo") or "").lower()
    cdigest = str(candidate.get("sha256") or candidate.get("body_digest") or "").lower()
    for rec in existing_records or []:
        rid = str(rec.get("id", "")).lower()
        rname = str(rec.get("name", "")).lower()
        rrepo = str(rec.get("source_repo") or "").lower()
        rdigest = str(rec.get("sha256") or rec.get("body_digest") or "").lower()
        if cid and rid == cid:
            matches.append({"kind": "exact", "existing_id": rec.get("id")})
        elif cdigest and rdigest == cdigest and rdigest != "0" * 64:
            matches.append({"kind": "digest", "existing_id": rec.get("id")})
        elif cname and rname == cname and (not crepo or crepo == rrepo):
            matches.append({"kind": "name", "existing_id": rec.get("id")})
    return {"matches": matches, "is_duplicate": bool(matches)}


def assess_candidate(candidate, existing_names, root=".", existing_records=None,
                     candidate_dir=None):
    """M4 P4 — 完整候選評估：評分 + 安全掃描 + 重複偵測。

    門控紀律：security blocked（high 級 secret 命中）或 exact/digest 重複
    → recommendation 強制 'reject'（絕不進 stage）。UNREVIEWED 技能永遠
    不得直達 active runtime（stage 只是隔離區，execution_granted=False）。
    """
    ev = evaluate_candidate(candidate, existing_names, root)
    scan = security_scan(candidate, root=root, candidate_dir=candidate_dir)
    dup = find_duplicate_candidates(candidate, existing_records or [])
    ev["security_findings"] = scan["counts"]
    ev["security_blocked"] = scan["blocked"]
    ev["duplicate_matches"] = dup["matches"]
    hard_dup = any(m["kind"] in ("exact", "digest") for m in dup["matches"])
    if scan["blocked"]:
        ev["recommendation"] = "reject"
        ev["reject_reason"] = "security_scan_high"
    elif hard_dup:
        ev["recommendation"] = "reject"
        ev["reject_reason"] = "duplicate_of_existing"
    return ev


def github_search(query, limit=10, token=None, sleep=time.sleep):
    """線上 GitHub API；保留檢查時間與來源 commit（default_branch；完整 SHA 需後續 resolve）。

    重試政策（有上限，fail-open）：
    - 429 一律視為 rate-limit → Retry-After backoff 後重試（上限 MAX_RETRIES 次）。
    - 403 只有帶 rate-limit 訊號（Retry-After 或 X-RateLimit-Remaining: 0）才是；
      普通 403 Forbidden（無權限／WAF／bot check）絕不重試，直接 fail-open。
    - 其他錯誤終止回傳 (None, {error})，絕不中斷呼叫端。
    """
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({
        "q": f"{query} agent skill in:name,description", "per_page": str(limit)})
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "agent-skills-scout/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    attempt = 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("items", [])[:limit]
                out = []
                for it in items:
                    out.append({
                        "id": "gh:" + it.get("full_name", ""),
                        "name": it.get("name", ""),
                        "description": it.get("description", ""),
                        "source_repo": it.get("html_url"),
                        "source_commit": it.get("default_branch"),  # branch；完整 SHA 需後續 resolve
                        "license": (it.get("license") or {}).get("spdx_id") or "unknown",
                        "maintenance": "archived" if it.get("archived") else ("stale" if (it.get("pushed_at") or "") < time.strftime("%Y-%m-%d", time.gmtime(time.time() - 365 * 86400)) else "active"),
                        "stars": it.get("stargazers_count", 0),
                        "check_time": now_iso(),
                    })
                return out, {"rate_remaining": resp.headers.get("X-RateLimit-Remaining"),
                             "attempts": attempt}
        except urllib.error.HTTPError as e:
            # 重試政策單一來源：classify_http_error（429 與「帶 rate-limit 訊號的
            # 403」才重試；普通 403／其他 4xx 絕不重試，直接 fail-open）。
            verdict = classify_http_error(e.code, e.headers or {})
            if verdict["retryable"] and attempt <= MAX_RETRIES:
                sleep(verdict.get("retry_after_s", RETRY_PAUSE_S))
                continue
            reason = verdict.get("note") or verdict["category"]
            return None, {"error": f"HTTP {e.code} ({reason})", "attempts": attempt,
                          "rate_reset": e.headers.get("X-RateLimit-Reset")}
        except Exception as e:  # noqa: BLE001 - fail-open
            return None, {"error": str(e), "attempts": attempt}


def stage(candidate, evaluation, root="."):
    """把候選 stage 到 proposals 隔離區（metadata only，不執行任何腳本）。

    冪等：同 candidate id 重複 stage 會覆蓋既有 proposal 並只保留一條 state 記錄。
    """
    PROPOSALS.mkdir(parents=True, exist_ok=True)
    cid = candidate.get("id") or candidate.get("name", "candidate")
    slug = re.sub(r"[^a-z0-9-]", "-", cid.lower())
    doc = {
        "proposed_at": now_iso(),
        "candidate": candidate,
        "evaluation": evaluation,
        "stage": "isolated-metadata",
        "execution_granted": False,  # 首引入程式碼技能不自動取得執行權限
        "notes": "metadata 隔離候選；導入前需人工授權 + 沙箱測試",
    }
    target = PROPOSALS / f"{slug}.json"
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    # 記入 scout-state 供冪等判斷（同 id 只保留最新一筆）
    state = load_state()
    staged = [s for s in state.setdefault("staged", []) if s.get("id") != cid]
    staged.append({"id": cid, "file": str(target), "at": doc["proposed_at"]})
    state["staged"] = staged
    save_state(state)
    return target


def load_state():
    if SCOUT_STATE.exists():
        return json.loads(SCOUT_STATE.read_text(encoding="utf-8"))
    return {"proposals": []}


def save_state(state):
    STATE.mkdir(parents=True, exist_ok=True)
    SCOUT_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="skill scout")
    sub = parser.add_subparsers(dest="cmd", required=True)
    a_d = sub.add_parser("discover", help="離線列可評估候選")
    a_d.add_argument("--root", default=".")
    a_d.add_argument("--github")
    a_d.add_argument("--limit", type=int, default=10)
    a_e = sub.add_parser("evaluate", help="評估候選")
    a_e.add_argument("slug", nargs="?")
    a_e.add_argument("--root", default=".")
    a_s = sub.add_parser("stage", help="stage 到 proposals 隔離區")
    a_s.add_argument("slug")
    a_s.add_argument("--root", default=".")
    a_a = sub.add_parser("assess", help="完整評估候選（評分+安全掃描+重複偵測；blocked/reject 印出原因）")
    a_a.add_argument("slug")
    a_a.add_argument("--root", default=".")
    a_q = sub.add_parser("queue", help="列出候選佇列")
    a_q.add_argument("--root", default=".")
    a_sch = sub.add_parser("schedule", help="寫本機週期性排程提示（不重複啟動）")
    a_sch.add_argument("--root", default=".")
    args = parser.parse_args(argv)

    if args.cmd == "discover":
        local, names = discover_local(args.root)
        payload = {"local_candidates": local, "existing_skill_names": len(names)}
        if args.github:
            gh, meta = github_search(args.github, args.limit, token=os.environ.get("GITHUB_TOKEN"))
            payload["github"] = gh
            payload["github_meta"] = meta
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    elif args.cmd == "evaluate":
        local, names = discover_local(args.root)
        if args.slug:
            target = next((c for c in local if c["id"] == args.slug or c["name"] == args.slug), None)
            if target is None:
                print(json.dumps({"error": f"candidate {args.slug} not found"}, ensure_ascii=False))
                return 2
        else:
            target = local[0] if local else None
            if target is None:
                print(json.dumps({"error": "no local candidates"}, ensure_ascii=False))
                return 2
        ev = evaluate_candidate(target, names, args.root)
        print(json.dumps(ev, ensure_ascii=False, indent=1))
    elif args.cmd == "stage":
        local, names = discover_local(args.root)
        target = next((c for c in local if c["id"] == args.slug or c["name"] == args.slug), None)
        if target is None:
            print(json.dumps({"error": f"candidate {args.slug} not found"}, ensure_ascii=False))
            return 2
        ev = assess_candidate(target, names, args.root)
        # 門控：security blocked / 硬重複 的候選絕不進 stage（只隔離，不授予執行）
        if ev["recommendation"] == "reject":
            print(json.dumps({"refused": True, "reason": ev.get("reject_reason"),
                              "evaluation": ev}, ensure_ascii=False, indent=1))
            return 3
        path = stage(target, ev, args.root)
        print(str(path))
    elif args.cmd == "assess":
        local, names = discover_local(args.root)
        target = next((c for c in local if c["id"] == args.slug or c["name"] == args.slug), None)
        if target is None:
            print(json.dumps({"error": f"candidate {args.slug} not found"}, ensure_ascii=False))
            return 2
        ev = assess_candidate(target, names, args.root)
        print(json.dumps(ev, ensure_ascii=False, indent=1))
        return 0
    elif args.cmd == "queue":
        items = []
        if PROPOSALS.exists():
            for p in sorted(PROPOSALS.iterdir()):
                if p.suffix == ".json":
                    items.append(json.loads(p.read_text(encoding="utf-8")))
        print(json.dumps({"staged": len(items), "items": [i["candidate"].get("id") for i in items]}, ensure_ascii=False, indent=1))
    elif args.cmd == "schedule":
        # 冪等：已存在排程則不重複寫；產出提示檔供既有 supervisor 接管
        hint = STATE / "scout-schedule.json"
        existing = json.loads(hint.read_text(encoding="utf-8")) if hint.exists() else None
        doc = {
            "job": "agent-skills-scout",
            "enabled": True,
            "interval_hours": 24,
            "last_run": now_iso(),
            "note": "單例；重啟前檢查現有排程，避免雙啟動。供既有 supervisor 接管，不新造排程系統。",
        }
        if existing:
            doc["pre_existing"] = True
        STATE.mkdir(parents=True, exist_ok=True)
        hint.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(doc, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
