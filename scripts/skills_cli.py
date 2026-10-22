#!/usr/bin/env python3
"""Personal Tool Master V3 — 統一技能 CLI（P5 跨宿主入口）。

所有子指令 fail-open：registry 缺失/損毀只回報狀態碼，不影響宿主原生工具。
純標準庫；不執行任何第三方安裝腳本。

退出碼契約：
  0 成功
  1 fallback（registry 不可用，退回純 V3）
  2 輸入錯誤（候選不存在／引數無效）
  3 schema 驗證失敗
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REG_PY = REPO_ROOT / "registry/tools/registry.py"
FORGE_PY = REPO_ROOT / "forge/forge.py"
COMPOSER_PY = REPO_ROOT / "runtime/skills-router/extensions/skill-composer/composer.py"
SCOUT_PY = REPO_ROOT / "scout/scout.py"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module unavailable: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _emit(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1))


def _registry_status(root="."):
    reg = _load(REG_PY, "registry")
    out = {}
    for layer in ("public", "private", "history"):
        try:
            doc = reg.load_layer(root, layer)
            out[layer] = {
                "records": len(doc.get("records", [])),
                "available": True,
                "diagnostics": doc.get("diagnostics", [])[:5],
            }
        except Exception as e:  # noqa: BLE001
            out[layer] = {"records": 0, "available": False, "error": str(e)}
    return out


def cmd_status(args):
    _emit(_registry_status(args.root))
    return 0


def _integrity_args(args):
    """依層選擇 digest 錨定的來源 root（private/history 層的 digest 錨定在私人來源，
    不能拿 main-repo 硬驗）。可用 env 覆寫；預設指向本機標準位置。"""
    src = os.environ.get("SKILLS_SOURCE_ROOT", str(Path.home() / ".agents/skills"))
    rec = os.environ.get("SKILLS_RECOVERY_ROOT",
                         str(Path.home() / ".local/agent-skills/recovery/skills"))
    return src, rec


def cmd_audit(args):
    """授權／秘密／完整性／依賴一次審計。

    exit 語意：public（公開發布層）digest mismatch → 3（發布前必擋）。
    private/history（私人證據層）digest 漂移 → 列為 warning，exit 0（磁碟後續改動是預期狀態）。
    """
    reg = _load(REG_PY, "registry")
    source_root, recovery_root = _integrity_args(args)
    report = {"root": os.path.abspath(args.root), "layers": {}, "errors": []}
    for layer in ("public", "private", "history"):
        try:
            integ = reg.integrity_check(
                args.root, layer, source_root, recovery_root)
            report["layers"][layer] = {
                "integrity": integ,
                "secrets": reg.secret_scan(args.root, layer),
                "duplicates": reg.find_duplicates(args.root, layer),
                "dependency_problems": reg.dependency_check(args.root, layer),
            }
        except Exception as e:  # noqa: BLE001
            report["errors"].append({"layer": layer, "error": str(e)})
    public_bad = report["layers"].get("public", {}).get("integrity", {}).get("mismatches", [])
    report["drift_warnings"] = {
        layer: report["layers"][layer]["integrity"]["mismatches"]
        for layer in ("private", "history")
        if report["layers"].get(layer, {}).get("integrity", {}).get("mismatches")
    }
    _emit(report)
    return 3 if public_bad else 0


def cmd_list(args):
    reg = _load(REG_PY, "registry")
    doc = reg.load_layer(args.root, args.layer)
    recs = doc["records"]
    if args.filter_status:
        recs = [r for r in recs if r.get("status") == args.filter_status]
    _emit({"layer": args.layer, "count": len(doc["records"]),
           "shown": len(recs), "records": recs[args.offset:args.offset + args.limit]})
    return 0


def cmd_search(args):
    reg = _load(REG_PY, "registry")
    hits = reg.search(args.root, args.layer, args.query, args.category, args.status, args.limit)
    _emit({"query": args.query, "layer": args.layer, "hits": len(hits), "results": hits})
    return 0


def cmd_verify(args):
    """sha256 完整性驗證（指定 layer 或全部）。

    與 audit 同語意：public（公開發布層）mismatch → exit 3（必擋）；
    private/history（私人證據層）漂移 → 列為 drift，exit 0。
    """
    reg = _load(REG_PY, "registry")
    source_root, recovery_root = _integrity_args(args)
    layers = [args.layer] if args.layer else ("public", "private", "history")
    out = {}
    rc = 0
    for layer in layers:
        try:
            res = reg.integrity_check(args.root, layer, source_root, recovery_root)
            out[layer] = {"checked": len(res["results"]),
                         "mismatches": res["mismatches"]}
            if layer == "public" and res["mismatches"]:
                rc = 3
            elif layer in ("private", "history") and res["mismatches"]:
                out[layer]["drift"] = True  # 私人層漂移，不 block
        except Exception as e:  # noqa: BLE001
            out[layer] = {"error": str(e)}
            rc = 1
    _emit(out)
    return rc


def cmd_scout(args):
    scout = _load(SCOUT_PY, "scout")
    if args.action == "discover":
        out, names = scout.discover_local(args.root)
        payload = {"local_candidates": len(out), "existing": len(names),
                   "candidates": out[:args.limit]}
        if args.github:
            gh, meta = scout.github_search(args.github, args.limit)
            payload["github"] = gh
            payload["github_meta"] = meta
        _emit(payload)
        return 0
    if args.action == "evaluate" and args.target:
        local, names = scout.discover_local(args.root)
        t = next((c for c in local if c["id"] == args.target or c["name"] == args.target), None)
        if t is None:
            _emit({"error": f"candidate {args.target} not found"})
            return 2
        _emit(scout.evaluate_candidate(t, names, args.root))
        return 0
    if args.action == "stage" and args.target:
        local, names = scout.discover_local(args.root)
        t = next((c for c in local if c["id"] == args.target or c["name"] == args.target), None)
        if t is None:
            _emit({"error": f"candidate {args.target} not found"})
            return 2
        ev = scout.evaluate_candidate(t, names, args.root)
        path = scout.stage(t, ev, args.root)
        _emit({"staged": str(path)})
        return 0
    if args.action == "queue":
        items = []
        qdir = Path.home() / ".local/agent-skills/registry-private/proposals"
        if qdir.exists():
            for p in sorted(qdir.iterdir()):
                if p.suffix == ".json":
                    items.append(json.loads(p.read_text(encoding="utf-8")))
        _emit({"staged": len(items), "items": [i["candidate"].get("id") for i in items]})
        return 0
    if args.action == "schedule":
        scout.main(["schedule", "--root", args.root])
        return 0
    _emit({"error": "invalid scout action", "actions": ["discover", "evaluate", "stage", "queue", "schedule"]})
    return 2


def cmd_forge(args):
    forge = _load(FORGE_PY, "forge")
    if args.action == "gaps":
        reg = _load(REG_PY, "registry")
        recs = []
        for layer in ("public", "private"):
            try:
                recs.extend(reg.load_layer(args.root, layer)["records"])
            except Exception:
                pass
        _emit({"capability_gaps": forge.capability_gaps(args.evidence, forge.analyze_skills(recs))})
        return 0
    if args.action == "analyze":
        reg = _load(REG_PY, "registry")
        recs = []
        for layer in ("public", "private"):
            try:
                recs.extend(reg.load_layer(args.root, layer)["records"])
            except Exception:
                pass
        _emit({"overlaps": forge.find_overlaps(forge.analyze_skills(recs))[:20]})
        return 0
    if args.action == "round":
        reg = _load(REG_PY, "registry")
        recs = []
        for layer in ("public", "private"):
            try:
                recs.extend(reg.load_layer(args.root, layer)["records"])
            except Exception:
                pass
        acc, rej = forge.forge_round(registry_records=recs, task_evidence=args.evidence,
                                      baseline_score=args.baseline)
        _emit({"accepted": [e["id"] for e in acc], "rejected": rej,
               "limits": {"max_depth": forge.MAX_DEPTH}})
        return 0
    if args.action == "accept" and args.name:
        forge.main(["accept", args.name, "--root", args.root, "--host", args.host])
        return 0
    _emit({"error": "invalid forge action", "actions": ["gaps", "analyze", "round", "accept"]})
    return 2


def cmd_compose(args):
    composer = _load(COMPOSER_PY, "composer")
    packet = composer.compose(args.task, reg_root=args.root, hosts=(args.host,), profile=args.profile)
    _emit(packet)
    return 1 if packet.get("fallback") else 0


def cmd_evaluate(args):
    """組合 scout evaluate + 授權門：對單一候選做完整評估。"""
    scout = _load(SCOUT_PY, "scout")
    local, names = scout.discover_local(args.root)
    t = next((c for c in local if c["id"] == args.target or c["name"] == args.target), None)
    if t is None:
        _emit({"error": f"candidate {args.target} not found"})
        return 2
    ev = scout.evaluate_candidate(t, names, args.root)
    # 授權門：公開推薦必須授權明確
    pub_ok = ev["breakdown"]["license_clarity"] >= 0.9
    ev["publication_ready"] = pub_ok and ev["recommendation"] == "stage"
    _emit(ev)
    return 0


def cmd_sync(args):
    """把 P0 recovery manifest + 640 catalog 重新匯入 registry（idempotent 快照）。"""
    reg = _load(REG_PY, "registry")
    recovery = Path.home() / ".local/agent-skills/recovery/SKILLS-640-RECOVERY-MANIFEST.json"
    catalog = Path(os.environ.get("SKILLS_CATALOG", str(Path.home() / ".agents/skills/.superpowers/SKILLS_INDEX.json")))
    if not recovery.exists():
        _emit({"error": "recovery manifest missing", "path": str(recovery)})
        return 2
    reg.snapshot(args.root, "public", "pre-sync")
    reg.snapshot(args.root, "history", "pre-sync")
    reg.snapshot(args.root, "private", "pre-sync")
    h, p = reg.import_private(args.root, str(recovery), str(catalog) if catalog.exists() else None)
    _emit({"history": h, "private": p, "snapshots": ["pre-sync x3"]})
    return 0


def cmd_compose_e2e(args):
    """真實宿主載入證據（skill_actually_loaded）：由宿主回傳的載入日誌核對。"""
    composer = _load(COMPOSER_PY, "composer")
    packet = composer.compose(args.task, reg_root=args.root, hosts=(args.host,), profile=args.profile)
    if packet.get("fallback"):
        _emit(packet)
        return 1
    # 宿主載入證據：載入日誌 JSONL（每行 {"skill_id":..., "loaded":true}）
    loaded_ids = set()
    if args.load_log and Path(args.load_log).exists():
        for line in Path(args.load_log).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("loaded") and e.get("skill_id"):
                loaded_ids.add(e["skill_id"])
    for c in packet.get("composition", []):
        c["host_confirmed_loaded"] = c["id"] in loaded_ids
        if not c.get("skill_actually_loaded"):
            c["skill_actually_loaded"] = c["host_confirmed_loaded"]
    _emit(packet)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="V3 skills unified CLI (P5)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_root(p):
        p.add_argument("--root", default=str(REPO_ROOT))

    p_status = sub.add_parser("status"); add_root(p_status)
    p_audit = sub.add_parser("audit"); add_root(p_audit)
    p_list = sub.add_parser("list"); add_root(p_list)
    p_list.add_argument("--layer", choices=["public", "private", "history"], default="public")
    p_list.add_argument("--filter-status")
    p_list.add_argument("--offset", type=int, default=0)
    p_list.add_argument("--limit", type=int, default=50)
    p_search = sub.add_parser("search"); add_root(p_search)
    p_search.add_argument("query", nargs="?")
    p_search.add_argument("--layer", choices=["public", "private", "history"], default="public")
    p_search.add_argument("--category")
    p_search.add_argument("--status")
    p_search.add_argument("--limit", type=int, default=50)
    p_verify = sub.add_parser("verify"); add_root(p_verify)
    p_verify.add_argument("--layer", choices=["public", "private", "history"])
    p_scout = sub.add_parser("scout"); add_root(p_scout)
    p_scout.add_argument("--action", default="discover",
                        choices=["discover", "evaluate", "stage", "queue", "schedule"])
    p_scout.add_argument("--target")
    p_scout.add_argument("--github")
    p_scout.add_argument("--limit", type=int, default=20)
    p_forge = sub.add_parser("forge"); add_root(p_forge)
    p_forge.add_argument("--action", default="gaps", choices=["gaps", "analyze", "round", "accept"])
    p_forge.add_argument("--evidence", default="")
    p_forge.add_argument("--name")
    p_forge.add_argument("--host", default="hermes")
    p_forge.add_argument("--baseline", type=float)
    p_compose = sub.add_parser("compose"); add_root(p_compose)
    p_compose.add_argument("task")
    p_compose.add_argument("--host", default="generic")
    p_compose.add_argument("--profile", choices=["guided", "normal", "high"], default="normal")
    p_eval = sub.add_parser("evaluate"); add_root(p_eval)
    p_eval.add_argument("target")
    p_sync = sub.add_parser("sync"); add_root(p_sync)
    p_e2e = sub.add_parser("compose-e2e"); add_root(p_e2e)
    p_e2e.add_argument("task")
    p_e2e.add_argument("--host", default="generic")
    p_e2e.add_argument("--profile", choices=["guided", "normal", "high"], default="normal")
    p_e2e.add_argument("--load-log", help="宿主載入日誌 JSONL；填實 skill_actually_loaded")

    args = parser.parse_args(argv)
    dispatch = {
        "status": cmd_status, "audit": cmd_audit, "list": cmd_list, "search": cmd_search,
        "verify": cmd_verify, "scout": cmd_scout, "forge": cmd_forge, "compose": cmd_compose,
        "evaluate": cmd_evaluate, "sync": cmd_sync, "compose-e2e": cmd_compose_e2e,
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
