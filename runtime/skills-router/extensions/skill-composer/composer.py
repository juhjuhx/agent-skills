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
    """路徑邊界（Step 2.4）：相對路徑、無 `..` 逃逸、無中段 symlink、解析後仍在 root 內。

    fail-closed：任一檢查失敗即 raise，阻擋不可信技能讀取；
    工具可用性仍 fail-open（read_bodies 捕獲 ValueError、繼續處理其餘候選）。

    邊界用 `is_relative_to` 真正包含判斷，非字串前綴（避免 /a/bad 誤判為 /a/b 之下）。
    絕對路徑與 `..` 段落一律拒絕。
    """
    root_resolved = root.resolve()
    rel = str(rel)
    if not rel:
        raise ValueError("empty relative path")
    if rel.startswith("/") or rel.startswith("\\") or (len(rel) >= 2 and rel[1] == ":"):
        raise ValueError(f"absolute path not allowed: {rel}")
    # 逐段走，檢查逃逸與 symlink
    cur = root
    for seg in Path(rel).parts:
        if seg in (".",):
            continue
        if seg == "..":
            raise ValueError(f"path traversal '..' segment: {rel}")
        cur = cur / seg
        if cur.is_symlink():
            raise ValueError(f"symlink segment in path: {rel}")
    candidate = cur.resolve()
    try:
        within = candidate.is_relative_to(root_resolved)
    except AttributeError:  # pragma: no cover (py<3.9)
        within = root_resolved in candidate.parents or candidate == root_resolved
    if not within:
        raise ValueError(f"path escapes root: {rel}")
    return candidate


# 全庫候選召回（Step 2.1）：三層全讀，並為每筆標記 _role 決定「可執行」還是「只供搜尋」。
LAYER_ORDER = ("public", "private", "history")
ROLE_PRIORITY = {"executable": 0, "search_only": 1, "excluded": 2}


def _role_for(layer, rec):
    """角色判別：public / private(現役 active approved) 可執行；history candidate 只供搜尋比較；
    quarantined 一律排除。歷史技能未完成適用性核准前絕不自動執行。"""
    if rec.get("status") == "quarantined":
        return "excluded"
    if layer in ("public", "private"):
        return "executable"
    return "search_only"


def candidate_pool(reg_root, local_roots):
    """public + private(現役 343) + history(640) 全庫候選；附 _layer/_role。

    同 id 依 public>private>history 且 executable>search_only>excluded 只留一份：
    private 的 active 版本會覆蓋 history 的 search-only 鏡像，因此現役技能保持可執行。
    """
    reg = _load_module(REGISTRY_PY, "registry")
    best = {}
    for layer in LAYER_ORDER:
        try:
            recs = reg.load_layer(reg_root, layer)["records"]
        except (OSError, ValueError, json.JSONDecodeError, RuntimeError, KeyError):
            continue
        for rec in recs:
            r = dict(rec)
            r["_layer"] = layer
            r["_role"] = _role_for(layer, rec)
            r["_local_only"] = layer != "public"
            rid = r.get("id")
            cur = best.get(rid)
            if cur is None or ROLE_PRIORITY.get(r["_role"], 9) < ROLE_PRIORITY.get(cur.get("_role", "search_only"), 9):
                best[rid] = r
    return list(best.values())


def reconcile_counts(reg_root, local_roots=None):
    """Step 2.1 全庫對帳：把候選池依角色分成可執行／搜尋比較／排除，回傳 spec 要求欄位。

    REGISTRY_TOTAL      = 三層記錄數（未去重）
    ACTIVE_COUNT       = 現役可執行（public + private）
    RECOVERY_COUNT     = history 全數（搜尋比較，未核准前不自動執行）
    SEARCHABLE_COUNT   = 去重後可被搜尋比對的條目（executable + search_only）
    ROUTE_ELIGIBLE     = 可進入組合的條目（僅 executable）
    EXCLUDED_COUNT     = quarantined／缺來源等被排除者
    """
    reg = _load_module(REGISTRY_PY, "registry")
    layers = {}
    for layer in LAYER_ORDER:
        try:
            layers[layer] = reg.load_layer(reg_root, layer)["records"]
        except (OSError, ValueError, json.JSONDecodeError, RuntimeError, KeyError):
            layers[layer] = []
    total = sum(len(v) for v in layers.values())
    pool = candidate_pool(reg_root, local_roots)
    by_role = {}
    for r in pool:
        by_role[r["_role"]] = by_role.get(r["_role"], 0) + 1
    return {
        "REGISTRY_TOTAL": total,
        "ACTIVE_COUNT": by_role.get("executable", 0),
        "RECOVERY_COUNT": len(layers.get("history", [])),
        "SEARCHABLE_COUNT": by_role.get("executable", 0) + by_role.get("search_only", 0),
        "ROUTE_ELIGIBLE": by_role.get("executable", 0),
        "EXCLUDED_COUNT": by_role.get("excluded", 0),
        "_pool_size": len(pool),
    }


# 中文→英文 alias 表（Step 2.3：低依賴跨語言召回；只放高置信詞，不引入模型）
_CJK_ALIAS = {
    "設計": "design", "審查": "review", "除錯": "debug", "調試": "debug",
    "測試": "test", "遊戲": "game", "影片": "video", "影像": "video",
    "封面": "thumbnail", "簡報": "slides", "剪輯": "editing", "字幕": "captions",
    "搜尋": "search", "素材": "assets", "授權": "license", "安全": "security",
    "資料庫": "database", "容器": "container", "部署": "deploy", "自動化": "automation",
    "前端": "frontend", "後端": "backend", "後端": "backend", "接口": "api",
    "文件": "docs", "筆記": "notes", "教學": "tutorial", "投影": "projection",
    "燈光": "lighting", "舞台": "stage", "戲劇": "theater", "動畫": "animation",
    "剪片": "editing", "轉錄": "transcription", "語音": "audio", "音樂": "music",
}


def _tokens(text):
    """CJK bigram + ASCII/CamelCase 詞 + alias。用於查詢與文件雙側（對稱）。"""
    out = Counter()
    low = str(text).lower()
    # ASCII 詞（含 repo 名稱、路徑、縮寫）；單字棄掉（噪音）
    for m in re.findall(r"[a-z0-9]+", low):
        if len(m) >= 2:
            out[m] += 1
    # CamelCase 拆詞：DaVinci → davinci（只保留 >=2 的片段，避免 e/t/c/m 單字噪音）
    for m in re.findall(r"[A-Z][a-z0-9]*", str(text)):
        if len(m) >= 2:
            out[m.lower()] += 1
    # CJK bigram：連續中文字符取 2-gram
    for seg in re.findall(r"[\u4e00-\u9fff]+", low):
        if len(seg) == 1:
            out[seg] += 1
        for i in range(len(seg) - 1):
            big = seg[i:i + 2]
            out[big] += 1
            if big in _CJK_ALIAS:
                out[_CJK_ALIAS[big]] += 1
        # 單字 alias（如 投影）
        for alias_word in ("投影", "戲劇", "燈光", "舞台", "動畫", "轉錄", "剪片", "字幕", "封面", "簡報", "素材"):
            if alias_word in seg and alias_word in _CJK_ALIAS:
                out[_CJK_ALIAS[alias_word]] += 1
    return out


def bm25_rank(query, records, cap=CANDIDATE_CAP):
    """純 stdlib BM25 over name/description/category/triggers。

    中文／混合語言召回（Step 2.3）：
      - ASCII 詞 + CamelCase 拆詞（DaVinci → davinci）
      - CJK 字符 bigram（「投影設計」→ 投影 影設 設計；「鍵盤輸入」→ 鍵盤 盤輸 輸入）
      - 簡短 alias 表把常用中文詞映射到英文 token（提升跨語言召回，不引入常駐模型）
      - 未匹配任務 → 0 分、不強行湊滿數量
    """
    q_tokens = _tokens(query)

    def doc_tokens(rec):
        text = " ".join(str(x) for x in (
            [rec.get("name", ""), rec.get("description", ""),
             " ".join(rec.get("category") or []), " ".join(rec.get("triggers") or [])]))
        return Counter(_tokens(text))

    documents = [doc_tokens(r) for r in records]
    frequency = Counter(t for d in documents for t in d)
    n = max(len(documents), 1)
    avg = sum(sum(d.values()) for d in documents) / n
    q = Counter()
    for tok in q_tokens:
        q[tok] += 1
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


# Step 2.2 載入語意七態（依 spec）：metadata → digest → router 讀取 → 交付宿主 →
# 進入模型 context → 執行 → 任務驗證。SHA256 通過不等於「已載入」。
LOAD_STATE_NOT_LOADED = "NOT_LOADED"
LOAD_STATE_REJECTED = "REJECTED"
LOAD_STATE_LOADED_NOT_EXECUTED = "LOADED_NOT_EXECUTED"
LOAD_STATE_VERIFIED_EXECUTION = "VERIFIED_EXECUTION"


def _load_state(body_status, host_ev):
    """依 digest＋宿主載入證據導出 load_state；絕不以 digest 單獨斷言 loaded。"""
    if body_status == "digest_mismatch" or body_status == "read_error":
        return LOAD_STATE_REJECTED
    if body_status != "verified":
        return LOAD_STATE_NOT_LOADED
    loaded = bool(host_ev and host_ev.get("loaded"))
    if not loaded:
        return LOAD_STATE_NOT_LOADED          # digest 正確、無宿主載入事件 → NOT_LOADED
    executed = bool(host_ev and host_ev.get("executed"))
    task_verified = bool(host_ev and host_ev.get("task_verified"))
    if executed and task_verified:
        return LOAD_STATE_VERIFIED_EXECUTION
    return LOAD_STATE_LOADED_NOT_EXECUTED     # 宿主載入但模型未執行／未驗證


def read_bodies(selected, local_roots, cap=BODY_READ_CAP["normal"],
                host_load_evidence=None):
    """按需讀取正文（上限 cap），依七態 ladder 回傳 load_state。

    skill_actually_loaded 只在宿主明確回報載入事件（host_load_evidence[id].loaded）
    時為 True；router 端讀取＋digest 通過永遠保持 False，避免「SHA256=已載入」誤判。
    """
    results = []
    # local_roots 的 value 必須是 str/PathLike；非 string 值（None 等）會讓 Path()
    # 拋 TypeError — 那屬於輸入錯誤，仍應走 fail-open，不能逃到呼叫端。
    roots = {}
    for k, v in local_roots.items():
        if not isinstance(v, (str, os.PathLike)):
            continue
        roots[k] = Path(v).expanduser()
    ev = host_load_evidence or {}
    for score, rec in selected[:cap]:
        entry = {
            "id": rec["id"],
            "score": round(score, 3),
            "relative_path": rec.get("relative_path"),
            "body_status": "unverified",
            "skill_actually_loaded": False,
            "load_state": LOAD_STATE_NOT_LOADED,
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
                entry["body_status"] = "read_error"
                entry["read_error"] = str(exc)
                entry["load_state"] = LOAD_STATE_REJECTED
                continue
            if target.is_file():
                digest = _sha256_file(target)
                expected = rec.get("sha256") or rec.get("body_digest")
                if not expected or str(expected).removeprefix("sha256:") == digest:
                    entry["body_status"] = "verified"
                    entry["read_from"] = root_name
                    entry["verified_body_sha256"] = digest
                else:
                    entry["body_status"] = "digest_mismatch"
                break
        host_ev = ev.get(rec["id"])
        entry["load_state"] = _load_state(entry["body_status"], host_ev)
        # 只有宿主明確回報 loaded 才置 True（絕不因 digest 通過而置 True）
        entry["skill_actually_loaded"] = bool(host_ev and host_ev.get("loaded"))
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


def _executable(candidates):
    """只有 _role=executable（public / private 現役）可進正文讀取與組合；
    history(search_only) 與 excluded 只保留在排序展示（供搜尋比較），絕不自動執行。"""
    return [(s, r) for s, r in candidates if r.get("_role") == "executable"]


def compose(task, *, reg_root=".", hosts=("generic",), profile="normal",
            local_roots=None, load_bodies=True, host_load_evidence=None):
    """主入口；任一步失敗 → fallback packet（純 V3 行為）。

    host_load_evidence：宿主實際載入／執行證據，格式 {skill_id: {"loaded":bool,
    "executed":bool, "task_verified":bool}}。advisory 組合只依 verified digest 推薦技能；
    skill_actually_loaded／load_state 反映此宿主證據，絕不以 digest 單獨斷言 loaded。
    """
    local_roots = local_roots or DEFAULT_ROOTS
    fallback = {"fallback": False, "fallback_reason": None}
    try:
        pool = candidate_pool(reg_root, local_roots)
        ranked = bm25_rank(task, pool, CANDIDATE_CAP)
        eligible = filter_eligible(ranked, hosts)
        executable = _executable(eligible)            # 組合只認可執行角色
        size = COMPOSITION_SIZE[profile]
        shortlist = executable[:max(BODY_READ_CAP[profile], size)]
        bodies = read_bodies(shortlist, local_roots, BODY_READ_CAP[profile],
                             host_load_evidence=host_load_evidence) if load_bodies else []
        # advisory：推薦 verified（digest 通過）的技能；宿主是否已載入看 load_state
        usable = [b for b in bodies if b["body_status"] == "verified"]
        composition = order_by_dependencies(usable)[:size]
        conflicts = detect_conflicts(usable)
        # 展示排序：可執行 + 搜尋-only（歷史比較用），都附 _role 讓宿主知道哪些能執行
        search_matches = [r for _, r in eligible if r.get("_role") in ("search_only", "excluded")]
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
            "executable_eligible": len(executable),
            "search_only_matches": len(search_matches),
            "shortlist_read": len(bodies),
            "composition": [
                {k: e[k] for k in ("id", "score", "body_status", "skill_actually_loaded",
                                   "load_state", "read_from", "verified_body_sha256", "relative_path")}
                for e in composition
            ],
            "candidates_ranked": [
                {"id": e["id"], "score": e["score"], "body_status": e["body_status"],
                 "skill_actually_loaded": e["skill_actually_loaded"], "load_state": e["load_state"],
                 "role": "executable"}
                for e in bodies
            ],
            "search_only_candidates": [
                {"id": r["id"], "role": "search_only", "note": "history 比較用，未核准前不自動執行"}
                for r in search_matches
            ],
            "conflicts": conflicts,
            "host_load_protocol": (
                "載入語意七態：metadata_discovered → body_digest_verified → "
                "body_read_by_router → body_delivered_to_host → body_loaded_into_model_context "
                "→ skill_executed → task_verified。"
                "本層 verified/digest 通過只代表正文完整性經驗證；"
                "宿主須在實際 LOAD_SKILL 載入後回傳 host_load_evidence={id:{loaded,executed,task_verified}}，"
                "才有 skill_actually_loaded=true 與 load_state=LOADED_NOT_EXECUTED/VERIFIED_EXECUTION。"
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
    a_r = sub.add_parser("reconcile")
    a_r.add_argument("--root", default=os.path.abspath(os.environ.get("REG_ROOT", ".")))
    a_r.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "reconcile":
        counts = reconcile_counts(args.root)
        if args.json:
            print(json.dumps(counts, ensure_ascii=False, indent=1))
        else:
            for k, v in counts.items():
                print(f"{k}={v}")
        return 0
    packet = compose(args.task, reg_root=args.root, hosts=(args.host,), profile=args.profile)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=1))
        return 0 if not packet.get("fallback") else 1
    print(f"fallback={packet.get('fallback')} reason={packet.get('fallback_reason')}")
    for c in packet.get("composition", []):
        print(f"- {c['id']} [{c['body_status']}] loaded={c['skill_actually_loaded']} via {c.get('read_from')}")
    for c in packet.get("candidates_ranked", []):
        print(f"  cand {c['id']} score={c['score']} body={c['body_status']} role={c.get('role')}")
    for c in packet.get("search_only_candidates", []):
        print(f"  search-only {c['id']} ({c.get('note','')})")
    return 0 if not packet.get("fallback") else 1


if __name__ == "__main__":
    sys.exit(main())
