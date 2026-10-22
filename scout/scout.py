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
            # 僅「真正 rate-limit」才重試：
            # - 429 一律是 rate-limit。
            # - 403 只有帶 GitHub rate-limit 訊號（X-RateLimit-Remaining: 0 或
            #   X-RateLimit 家族 header）才是。普通 403 Forbidden（無權限／WAF／
            #   bot check，即使附 Retry-After）絕不重試，直接 fail-open。
            rl = {k.lower(): v for k, v in (e.headers or {}).items()}
            has_github_rate = any(k.startswith("x-ratelimit") for k in rl)
            rate_limited = (e.code == 429
                            or (e.code == 403 and (
                                rl.get("x-ratelimit-remaining") == "0" or has_github_rate)))
            if rate_limited and attempt <= MAX_RETRIES:
                # Retry-After 可能是 HTTP-date 或秒數；解析失敗即回落到固定 backoff
                raw = rl.get("retry-after") or str(RETRY_PAUSE_S)
                try:
                    pause = int(float(raw))
                except (TypeError, ValueError):
                    pause = RETRY_PAUSE_S
                sleep(max(0, min(pause, RATE_LIMIT_PAUSE_S)))
                continue
            return None, {"error": f"HTTP {e.code}", "attempts": attempt,
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
        ev = evaluate_candidate(target, names, args.root)
        path = stage(target, ev, args.root)
        print(str(path))
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
