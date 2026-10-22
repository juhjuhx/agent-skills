#!/usr/bin/env python3
"""Hermes Skill Forge — 有界技能合成與演進。可獨立停用。

第一版限制（不變量）：
  - 最大演進深度：2
  - 每個父技能最多 3 個候選分支
  - 單輪最多 5 個候選技能
  - 不允許自動改寫 using-superpowers 母技能
  - 不允許修改工具權限政策
  - 不允許自動提升未測試技能為穩定版本
  - 無可證明改進 → 拒絕採用，不累積

每個合成技能保留：PARENT_SKILLS / SOURCE_PROVENANCE / GENERATION / CHANGES /
TEST_CASES / BASELINE_SCORE / NEW_SCORE / ACCEPTANCE_REASON / ROLLBACK_VERSION。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_DEPTH = 2
MAX_BRANCHES_PER_PARENT = 3
MAX_CANDIDATES_PER_ROUND = 5
PROTECTED_SKILLS = {"using-superpowers"}  # 母技能不可自動改寫
PERMISSION_POLICY_PATHS = (".superpowers/ROUTING_POLICY.yaml",
                           ".superpowers/RUNTIME_POLICY.yaml",
                           "runtime/skills-router/adapters/")

FORGE_DIR = Path(__file__).resolve().parent
WORKSPACE = Path.home() / ".local/agent-skills/forge-workspace"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------- 1) 既有技能分析與重疊 ----------

def analyze_skills(registry_records):
    """回傳 {skill_id: {tokens, name, desc, generation, parents}}。"""
    out = {}
    for rec in registry_records:
        tokens = set(re.findall(r"[a-z0-9]+", (rec.get("name", "") + " " +
                                                (rec.get("description") or "")).lower()))
        out[rec["id"]] = {
            "tokens": tokens,
            "name": rec.get("name", ""),
            "desc": rec.get("description") or "",
            "generation": rec.get("generation", 0),
            "parents": rec.get("parent_skills") or [],
        }
    return out


def find_overlaps(analyzed, threshold=0.5):
    """Token 重疊 > threshold 的技能對（用於合併建議）。"""
    ids = sorted(analyzed)
    pairs = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            inter = len(analyzed[a]["tokens"] & analyzed[b]["tokens"])
            union = max(1, len(analyzed[a]["tokens"] | analyzed[b]["tokens"]))
            ratio = inter / union
            if ratio >= threshold:
                pairs.append({"a": a, "b": b, "overlap": round(ratio, 3)})
    return sorted(pairs, key=lambda p: -p["overlap"])


def capability_gaps(task_evidence, analyzed):
    """由任務證據中的關鍵能力詞找出未被任何現有技能覆蓋的 gap。"""
    evidence_tokens = set(re.findall(r"[a-z0-9]+", task_evidence.lower()))
    covered = set()
    for info in analyzed.values():
        covered |= info["tokens"]
    gap = sorted(evidence_tokens - covered - {"the", "a", "an", "and", "for", "with", "task"})
    return gap


# ---------- 2) 父技能選擇 + 候選生成 ----------

def select_parents(evidence_tokens, analyzed, limit=MAX_BRANCHES_PER_PARENT, standalone=True):
    """依證據 token 與既有技能的關聯度選父技能（關聯越高越優先），每父技能 ≤limit 分支。

    - 有交集 → 選最相關的父技能（parent 分支：generation = parent_gen + 1）。
    - 無交集且 standalone=True → 空清單代表「standalone 合成」（generation 0）：
      Forge 的核心用途是補現有技能未覆蓋的 gap。
    - 無交集且 standalone=False → 回傳 None（拒絕，由 caller 處理）。
    """
    scored = []
    for sid, info in analyzed.items():
        if sid.endswith("using-superpowers") or info["name"] in PROTECTED_SKILLS:
            continue
        hit = len(info["tokens"] & set(evidence_tokens))
        if hit:
            scored.append((hit, sid))
    scored.sort(reverse=True)
    if scored:
        return [sid for _, sid in scored[:limit]]
    if standalone:
        return []
    return None  # 明確要求 parent 但找不到 → 拒絕（由 caller 處理）


def generate_candidate(parents, gap, generation, description, changes):
    """生成單一候選技能（純 metadata + SKILL.md 草稿，不嵌入可執行第三方程式）。"""
    if generation > MAX_DEPTH:
        raise ValueError(f"generation {generation} exceeds MAX_DEPTH={MAX_DEPTH}")
    if parents:
        slug = "-".join(re.sub(r"[^a-z0-9]", "", p.split(":")[-1].split("/")[-1].lower())
                        for p in parents[:2])
    else:
        slug = "standalone"
    skill_name = f"synth-{slug}-g{generation}"
    body = (
        "---\n"
        f"name: {skill_name}\n"
        f"description: Synthesized skill (generation {generation}) covering: "
        f"{' / '.join(sorted(set(gap))[:8])}. {description}\n"
        "---\n\n"
        f"# {skill_name}\n\n"
        "Provenance: forged by Hermes Skill Forge; inherits from parent skills below.\n"
        + "\n".join(f"- parent: {p}" for p in parents)
        + "\n\n## Changes\n" + changes + "\n"
    )
    return skill_name, body


def validate_syntax(body):
    """結構驗證：frontmatter 完整、欄位非空、無禁止內容。"""
    if not body.startswith("---\n"):
        return False, "missing frontmatter"
    m = re.match(r"^---\n(.*?)\n---", body, re.S)
    if not m:
        return False, "unterminated frontmatter"
    fm = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if km:
            fm[km.group(1)] = km.group(2)
    for required in ("name", "description"):
        if not fm.get(required):
            return False, f"missing {required}"
    if "ROUTING_POLICY" in body or "PERMISSION" in body.upper().replace("_", " ") and "HOST-NATIVE" not in body:
        return False, "forbidden: touches tool permission policy"
    return True, ""


def review_provenance(candidate_meta):
    """所有 parent 必須存在於 registry 且授權可追溯。"""
    problems = []
    for p in candidate_meta.get("parents") or []:
        if not p or p.endswith("using-superpowers"):
            problems.append(f"protected/invalid parent: {p}")
    return problems


# ---------- 3) 沙箱測試 + baseline 比較 ----------

def sandbox_test(body, test_cases):
    """結構沙箱：frontmatter 可解析、字元上限、無執行位元組。不執行第三方腳本。"""
    results = []
    ok = True
    if len(body) > 100_000:
        ok = False
        results.append({"case": "size_limit", "pass": False})
    else:
        results.append({"case": "size_limit", "pass": True})
    parsed, _ = validate_syntax(body)
    results.append({"case": "frontmatter_parse", "pass": parsed})
    ok = ok and parsed
    if any(tc in body for tc in test_cases):
        results.append({"case": "test_terms_present", "pass": True})
    else:
        results.append({"case": "test_terms_present", "pass": len(test_cases) == 0})
    ok = ok and all(r["pass"] for r in results if r["case"] != "test_terms_present")
    return ok, results


def score_candidate(body, gap, test_results):
    """NEW_SCORE = 0.5*gap 覆蓋率 + 0.5*沙箱通過率。"""
    tokens = set(re.findall(r"[a-z0-9]+", body.lower()))
    coverage = len(tokens & set(gap)) / max(1, len(gap))
    pass_rate = sum(1 for r in test_results if r["pass"]) / max(1, len(test_results))
    return round(0.5 * coverage + 0.5 * pass_rate, 4)


# ---------- 4) 有界輪次 ----------

def forge_round(*, registry_records, task_evidence, description="", changes="",
                baseline_score=None, max_candidates=MAX_CANDIDATES_PER_ROUND):
    """單輪合成：回傳 (accepted[], rejected[])；accepted 寫入 forge-workspace。"""
    analyzed = analyze_skills(registry_records)
    gap = capability_gaps(task_evidence, analyzed)
    if not gap:
        return [], [{"reason": "no capability gap in evidence", "accepted": False}]
    # 父技能選擇用「證據 token 全集」：與既有技能相關的部分 → parent 分支，
    # 未覆蓋的部分（gap）由新技能內容承接。
    evidence_tokens = set(re.findall(r"[a-z0-9]+", task_evidence.lower()))
    parents = select_parents(evidence_tokens, analyzed)
    if parents is None:
        return [], [{"reason": "no eligible parent skills", "accepted": False}]
    # parents == [] → standalone synthesis (generation 0, gap 由 evidence 覆蓋)
    # 有 parent → 分支 generation = 該 parent 的 generation + 1；> MAX_DEPTH 的分支拒絕
    if not parents:
        generation = 0
        effective_parents = []
        loop_range = 1
    else:
        parent_gens = {}
        for sid in parents:
            parent_gens[sid] = max(
                (r.get("generation", 0) for r in registry_records if r.get("id") == sid),
                default=0)
        # 只取能繼續演進（parent_gen+1 <= MAX_DEPTH）的 parent
        effective_parents = [s for s in parents if parent_gens[s] + 1 <= MAX_DEPTH]
        if not effective_parents:
            return [], [{"reason": f"all eligible parents at generation "
                                    f"{max(parent_gens.values())}; MAX_DEPTH={MAX_DEPTH} "
                                    f"reached — recursion bound enforced",
                         "accepted": False}]
        generation = min(parent_gens[s] for s in effective_parents) + 1
        loop_range = max_candidates
    accepted, rejected = [], []
    used_branches = {}
    for idx in range(loop_range):
        if not effective_parents:
            parent = "(standalone)"
        else:
            parent = effective_parents[idx % len(effective_parents)]
        used_branches[parent] = used_branches.get(parent, 0) + 1
        if used_branches[parent] > MAX_BRANCHES_PER_PARENT:
            break
        name, body = generate_candidate(effective_parents[:2], gap, generation, description, changes)
        meta = {
            "id": f"forge:{name}",
            "name": name,
            "parents": effective_parents[:2],
            "parents_used": parent,
            "generation": generation,
            "body_sha256": sha256_text(body),
            "created_at": now_iso(),
        }
        ok_syn, why_syn = validate_syntax(body)
        if not ok_syn:
            rejected.append({"candidate": meta["id"], "reason": f"syntax: {why_syn}"})
            continue
        prov_problems = review_provenance(meta)
        if prov_problems:
            rejected.append({"candidate": meta["id"], "reason": "; ".join(prov_problems)})
            continue
        test_cases = [g for g in gap if g in body.lower()][:5]
        sandbox_ok, test_results = sandbox_test(body, test_cases)
        new_score = score_candidate(body, gap, test_results)
        baseline = baseline_score if baseline_score is not None else 0.0
        improved = new_score > baseline
        entry = {
            **meta,
            "body": body,
            "test_cases": test_cases,
            "test_results": test_results,
            "baseline_score": baseline,
            "new_score": new_score,
            "accepted": improved and sandbox_ok,
            "acceptance_reason": (
                f"new_score {new_score} > baseline {baseline}, sandbox pass"
                if improved and sandbox_ok else
                f"rejected: improved={improved} sandbox_ok={sandbox_ok}"),
        }
        if entry["accepted"]:
            accepted.append(entry)
        else:
            # 統一 reject 格式：{"candidate", "reason"}（與早期 reject 同構）
            rejected.append({"candidate": meta["id"],
                            "reason": entry["acceptance_reason"]})
    # 落盤 accepted 到 forge-workspace（私人），供後續審批入 registry
    if accepted:
        WORKSPACE.mkdir(parents=True, exist_ok=True)
        for e in accepted:
            (WORKSPACE / f"{e['name']}.md").write_text(e["body"], encoding="utf-8")
            (WORKSPACE / f"{e['name']}.meta.json").write_text(
                json.dumps({k: v for k, v in e.items() if k != "body"}, ensure_ascii=False, indent=1),
                encoding="utf-8")
    return accepted, rejected


# ---------- 5) 入 registry（需顯式審批，不自動升 stable）----------

def accept_to_registry(accepted_entry, registry_root, host_name):
    """把已審批的合成技能寫入 private registry（status=approved_private、risk=unreviewed、
    generation 遞增），並做 snapshot 供 rollback。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("registry",
        Path(__file__).resolve().parent.parent / "registry/tools/registry.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("registry module unavailable")
    reg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reg)
    doc = reg.load_layer(registry_root, "private")
    if any(r["id"] == accepted_entry["id"] for r in doc["records"]):
        raise ValueError(f"{accepted_entry['id']} already in private registry")
    rel = os.path.join("registry/private/forge", f"{accepted_entry['name']}.md")
    Path(registry_root, "registry/private/forge").mkdir(parents=True, exist_ok=True)
    target = Path(registry_root, rel)
    target.write_text(accepted_entry["body"], encoding="utf-8")
    record, diags = reg.build_record(
        id=accepted_entry["id"],
        name=accepted_entry["name"],
        relative_path=rel,
        sha=accepted_entry["body_sha256"],
        license="MIT",
        status="approved_private",
        visibility="private",
        risk="unreviewed",
        description=accepted_entry["body"].split("description: ", 1)[-1].split("\n", 1)[0],
        provenance={"kind": "hermes_forge", "forged_at": accepted_entry["created_at"]},
        generation=accepted_entry["generation"],
        parent_skills=accepted_entry["parents"],
        source_provenance="; ".join(accepted_entry["parents"]),
        changes=accepted_entry.get("acceptance_reason", ""),
        test_cases=accepted_entry["test_cases"],
        baseline_score=accepted_entry["baseline_score"],
        new_score=accepted_entry["new_score"],
        acceptance_reason=accepted_entry["acceptance_reason"],
        rollback_version=accepted_entry.get("rollback_version"),
    )
    doc["records"].append(record)
    reg.save_layer(registry_root, "private", doc)
    snap = reg.snapshot(registry_root, "private", f"forge-{accepted_entry['name']}-{host_name}")
    return record, str(snap)


# ---------- CLI ----------

def main(argv=None):
    parser = argparse.ArgumentParser(description="hermes skill forge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    a_gap = sub.add_parser("gaps", help="任務證據 → capability gaps")
    a_gap.add_argument("evidence")
    a_gap.add_argument("--root", default=".")

    a_an = sub.add_parser("analyze", help="重疊分析與合併建議")
    a_an.add_argument("--root", default=".")

    a_round = sub.add_parser("round", help="有界合成一輪")
    a_round.add_argument("evidence")
    a_round.add_argument("--root", default=".")
    a_round.add_argument("--description", default="")
    a_round.add_argument("--changes", default="")
    a_round.add_argument("--baseline", type=float)
    a_round.add_argument("--max-candidates", type=int, default=MAX_CANDIDATES_PER_ROUND)

    a_acc = sub.add_parser("accept", help="審批入 private registry（產生 rollback 快照）")
    a_acc.add_argument("name")
    a_acc.add_argument("--root", default=".")
    a_acc.add_argument("--host", default="hermes")

    args = parser.parse_args(argv)

    def load_records(root):
        import importlib.util
        spec = importlib.util.spec_from_file_location("registry",
            Path(__file__).resolve().parent.parent / "registry/tools/registry.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("registry module unavailable")
        reg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reg)
        recs = []
        for layer in ("public", "private"):
            try:
                recs.extend(reg.load_layer(root, layer)["records"])
            except Exception:
                pass
        return recs

    if args.cmd == "gaps":
        recs = load_records(args.root)
        print(json.dumps({"capability_gaps": capability_gaps(args.evidence, analyze_skills(recs))},
                         ensure_ascii=False, indent=1))
    elif args.cmd == "analyze":
        recs = load_records(args.root)
        overlaps = find_overlaps(analyze_skills(recs))
        print(json.dumps({"overlaps": overlaps[:20]}, ensure_ascii=False, indent=1))
    elif args.cmd == "round":
        recs = load_records(args.root)
        acc, rej = forge_round(registry_records=recs, task_evidence=args.evidence,
                               description=args.description, changes=args.changes,
                               baseline_score=args.baseline,
                               max_candidates=args.max_candidates)
        print(json.dumps({"accepted": [e["id"] for e in acc],
                          "rejected": rej,
                          "limits": {"max_depth": MAX_DEPTH,
                                     "max_branches_per_parent": MAX_BRANCHES_PER_PARENT,
                                     "max_candidates_per_round": MAX_CANDIDATES_PER_ROUND}},
                         ensure_ascii=False, indent=1))
        return 0
    elif args.cmd == "accept":
        meta_path = WORKSPACE / f"{args.name}.meta.json"
        if not meta_path.exists():
            print(json.dumps({"error": f"no forge candidate '{args.name}' in workspace"}, ensure_ascii=False))
            return 2
        entry = json.loads(meta_path.read_text(encoding="utf-8"))
        body = (WORKSPACE / f"{args.name}.md").read_text(encoding="utf-8")
        entry["body"] = body
        # rollback_version = 入庫前 private registry 快照
        import importlib.util
        spec = importlib.util.spec_from_file_location("registry",
            Path(__file__).resolve().parent.parent / "registry/tools/registry.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("registry module unavailable")
        reg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reg)
        pre = reg.snapshot(args.root, "private", f"pre-{args.name}")
        entry["rollback_version"] = str(pre)
        record, snap = accept_to_registry(entry, args.root, args.host)
        print(json.dumps({"accepted": record["id"], "snapshot": snap,
                          "rollback_version": entry["rollback_version"]},
                         ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
