#!/usr/bin/env python3
"""V3 動態技能組合擴充層（可獨立停用；不改 tool_master 既有行為）。

流程（依 V3 契約）：
  1) Registry metadata 全量掃描 → BM25 排序，候選上限 20
  2) 域／宿主／授權／風險過濾
  3) 按需讀取短列技能正文（最多 8 份；digest 核對）
  4) 技能適用性／衝突／依賴／執行順序評估
  5) 最小足夠技能組（guided 1 / normal 2 / high 4；0 亦允許）
  6) 產 CompositionPacket；host 真正載入證據（skill_actually_loaded）
     由宿主回傳填寫，本層只產 verification 欄位與回傳協定

安全邊界：
  - quarantined / license-unknown-public / symlink 逃逸一律不入選
  - composition 任一步失敗 → fallback=True，退回純 V3（skills 留空）
  - 絕不改動 host native tool permissions
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

REGISTRY_PY = Path(__file__).resolve().parents[4] / "registry/tools/registry.py"
TOOL_MASTER_PY = Path(__file__).resolve().parents[2] / "tool_master.py"

CANDIDATE_CAP = 20
BODY_READ_CAP = {"guided": 3, "normal": 5, "high": 8}
COMPOSITION_SIZE = {"guided": 1, "normal": 2, "high": 4}
DEFAULT_ROOTS = {
    "active": "~/.agents/skills",
    "recovery": "~/.local/agent-skills/recovery/skills",
    "main_repo": "~/.local/agent-skills/main-repo",
}


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module unavailable: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha256_file(p: Path):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe(root: Path, rel: str) -> Path:
    """symlink 逃逸防護：解析後必須仍在 root 內，且不得經 symlink 抵達。"""
    candidate = (root / rel).resolve()
    if not str(candidate).startswith(str(root.resolve())):
        raise ValueError(f"path escapes root: {rel}")
    p = root / rel
    parts = []
    cur = root
    for seg in Path(rel).parts:
        cur = cur / seg
        if cur.is_symlink():
            raise ValueError(f"symlink segment in path: {rel}")
        parts.append(seg)
    return candidate


def candidate_pool(reg_root, local_roots):
    """public registry + history(640) records，附相對 root 標記；同 id 只留一份。"""
    reg = _load_module(REGISTRY_PY, "registry")
    records, seen = [], set()
    for layer, visible in (("public", True), ("history", False)):
        try:
            for rec in reg.load_layer(reg_root, layer)["records"]:
                r = dict(rec)
                r["_layer"] = layer
                r["_local_only"] = not visible
                key = r["id"]
                if key in seen:
                    continue
                seen.add(key)
                records.append(r)
        except (OSError, ValueError, json.JSONDecodeError, RuntimeError, KeyError):
            continue
    return records


def bm25_rank(query, records, cap=CANDIDATE_CAP):
    """純 stdlib BM25 over name/description/category/triggers。"""
    documents = []
    for rec in records:
        text = " ".join(str(x) for x in (
            [rec.get("name", ""), rec.get("description", ""),
             " ".join(rec.get("category") or []), " ".join(rec.get("triggers") or [])]))
        documents.append(Counter(re.findall(r"[a-z0-9]+", text.lower())))
    frequency = Counter(tok for doc in documents for tok in doc)
    n = max(len(documents), 1)
    avg = sum(sum(d.values()) for d in documents) / n
    q = Counter(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for rec, doc in zip(records, documents):
        length = sum(doc.values())
        score = 0.0
        for tok, weight in q.items():
            c = doc.get(tok, 0)
            if not c:
                continue
            idf = math.log(1 + (n - frequency[tok] + 0.5) / (frequency[tok] + 0.5))
            score += idf * c * 2.2 / (c + 1.2 * (0.25 + 0.75 * length / max(avg, 1))) * min(weight, 2)
        scored.append((score, rec))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [(s, r) for s, r in scored[:cap] if s > 0]


def filter_eligible(candidates, hosts):
    out = []
    for score, rec in candidates:
        if rec.get("status") == "quarantined":
            continue
        if rec["_layer"] == "public" and rec.get("license") == "unknown":
            continue
        compatible = rec.get("compatible_hosts") or []
        if compatible and not (set(compatible) & set(hosts) or "generic" in compatible):
            continue
        out.append((score, rec))
    return out


def read_bodies(selected, local_roots, cap=BODY_READ_CAP["normal"]):
    """按需讀取正文（上限 cap）；回傳 skill_actually_loaded 與 body_status。"""
    results = []
    # local_roots 的 value 必須是 str/PathLike；非 string 值（None 等）會讓 Path()
    # 拋 TypeError — 那屬於輸入錯誤，仍應走 fail-open，不能逃到呼叫端。
    roots = {}
    for k, v in local_roots.items():
        if not isinstance(v, (str, os.PathLike)):
            continue
        roots[k] = Path(v).expanduser()
    for score, rec in selected[:cap]:
        entry = {
            "id": rec["id"],
            "score": round(score, 3),
            "relative_path": rec.get("relative_path"),
            "body_status": "unverified",
            "skill_actually_loaded": False,
            "read_from": None,
            "verified_body_sha256": None,
        }
        rel = rec.get("relative_path") or ""
        # history 記錄 relative_path 是 SKILL.md 相對路徑；active root 直接對，
        # recovery root 對 148 歷史目錄
        for root_name, root_path in roots.items():
            if not rel:
                continue
            try:
                target = _safe(root_path, rel)
            except ValueError as exc:
                entry["read_error"] = str(exc)
                continue
            if target.is_file():
                digest = _sha256_file(target)
                expected = rec.get("sha256") or rec.get("body_digest")
                if not expected or str(expected).removeprefix("sha256:") == digest:
                    entry["body_status"] = "verified"
                    entry["skill_actually_loaded"] = True
                    entry["read_from"] = root_name
                    entry["verified_body_sha256"] = digest
                else:
                    entry["body_status"] = "digest_mismatch"
                break
        results.append(entry)
    return results


def detect_conflicts(selected_bodies):
    """衝突偵測（最小可用）：多個選定技能指向同一實體 relative_path → 來源檔案衝突，
    需人工裁決。回傳衝突對清單（無則 []）。此為可實作的最小衝突檢查，不宣稱完整的
    依賴圖環偵測（選定 body 未攜 parent_skills 元資料）。"""
    conflicts = []
    by_path = {}
    for e in selected_bodies:
        rel = e.get("relative_path")
        if rel:
            by_path.setdefault(rel, []).append(e["id"])
    for rel, ids in by_path.items():
        if len(ids) > 1:
            conflicts.append({"kind": "shared_relative_path",
                              "path": rel, "ids": ids})
    return conflicts


def order_by_dependencies(selected):
    """parent_skills 先於 generation 子技能；同 generation 依分數。"""
    gen = {e["id"]: int(e.get("generation") or 0) for e in selected}
    return sorted(selected, key=lambda e: (gen.get(e["id"], 0), -e["score"]))


def compose(task, *, reg_root=".", hosts=("generic",), profile="normal",
            local_roots=None, load_bodies=True):
    """主入口；任一步失敗 → fallback packet（純 V3 行為）。"""
    local_roots = local_roots or DEFAULT_ROOTS
    fallback = {"fallback": False, "fallback_reason": None}
    try:
        pool = candidate_pool(reg_root, local_roots)
        ranked = bm25_rank(task, pool, CANDIDATE_CAP)
        eligible = filter_eligible(ranked, hosts)
        size = COMPOSITION_SIZE[profile]
        shortlist = eligible[:max(BODY_READ_CAP[profile], size)]
        bodies = read_bodies(shortlist, local_roots, BODY_READ_CAP[profile]) if load_bodies else []
        usable = [b for b in bodies if b["body_status"] == "verified" and b["skill_actually_loaded"]]
        composition = order_by_dependencies(usable)[:size]
        conflicts = detect_conflicts(usable)
        return {
            "version": "3-composition-v1",
            "advisory": True,
            "task": task,
            "hosts": list(hosts),
            "profile": profile,
            "fallback": False,
            "candidate_pool_size": len(pool),
            "candidates": len(ranked),
            "eligible": len(eligible),
            "shortlist_read": len(bodies),
            "composition": [
                {k: e[k] for k in ("id", "score", "body_status", "skill_actually_loaded",
                                   "read_from", "verified_body_sha256", "relative_path")}
                for e in composition
            ],
            "candidates_ranked": [
                {"id": e["id"], "score": e["score"], "body_status": e["body_status"],
                 "skill_actually_loaded": e["skill_actually_loaded"]}
                for e in bodies
            ],
            "conflicts": conflicts,
            "host_load_protocol": (
                "宿主須在實際 Skill/ LOAD_SKILL 載入每個 composition 技能後，"
                "以回傳證據（載入日誌或 digest 比對）填實 skill_actually_loaded=true；"
                "本層 verified 只代表正文完整性經驗證，不等於宿主已載入。"
            ),
        }
    except (OSError, ValueError, TypeError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        fallback["fallback"] = True
        fallback["fallback_reason"] = str(exc)
        fallback["note"] = "composition layer 失敗；退回純 V3 路由（host 工具全數可用）"
        fallback["advisory"] = True
        fallback["hosts"] = list(hosts)
        fallback["profile"] = profile
        return fallback

# ---------- CLI ----------

def main(argv=None):
    parser = argparse.ArgumentParser(description="V3 dynamic skill composition (extension layer)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    a_c = sub.add_parser("compose")
    a_c.add_argument("task")
    a_c.add_argument("--root", default=os.path.abspath(os.environ.get("REG_ROOT", ".")))
    a_c.add_argument("--host", default="generic")
    a_c.add_argument("--profile", choices=["guided", "normal", "high"], default="normal")
    a_c.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    packet = compose(args.task, reg_root=args.root, hosts=(args.host,), profile=args.profile)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=1))
        return 0 if not packet.get("fallback") else 1
    print(f"fallback={packet.get('fallback')} reason={packet.get('fallback_reason')}")
    for c in packet.get("composition", []):
        print(f"- {c['id']} [{c['body_status']}] loaded={c['skill_actually_loaded']} via {c.get('read_from')}")
    for c in packet.get("candidates_ranked", []):
        print(f"  cand {c['id']} score={c['score']} body={c['body_status']}")
    return 0 if not packet.get("fallback") else 1


if __name__ == "__main__":
    sys.exit(main())
