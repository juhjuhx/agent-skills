#!/usr/bin/env python3
"""Skills Registry — 純標準庫、四層分離、可獨立停用。

資料層（互不混用）：
  registry/public/registry.json      approved_public 清單（唯一可推送 GitHub）
  registry/private/registry.json     approved_private 清單（只留本機）
  registry/history/quarantine.json   HISTORICAL_RECOVERED / QUARANTINED 封存證據
  registry/history/versions/         快照與 rollback

所有操作 fail-open：registry 缺失或損毀只記錄 diagnostic，不阻塞 V3 router。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"

LAYER_DIRS = {
    "public": "registry/public",
    "private": "registry/private",
    "history": "registry/history",
}

LICENSE_ENUM = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "GPL-3.0",
    "LGPL-3.0", "MPL-2.0", "ISC", "Unlicense", "0BSD", "proprietary",
    "unknown",
}
STATUS_ENUM = {
    "candidate", "approved_public", "approved_private", "quarantined",
    "deprecated", "rejected",
}

REQUIRED = ("id", "name", "sha256", "license", "status", "visibility", "risk_level")

SECRET_PATTERNS = [
    ("api_key_literal", re.compile(r"(?:api[_-]?key|apikey)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}", re.I)),
    ("github_pat", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----")),
    ("password_literal", re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*[\"'][^\"']{6,}[\"']", re.I)),
]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def layer_file(root, layer):
    return Path(root) / LAYER_DIRS[layer] / "registry.json"


def load_layer(root, layer):
    path = layer_file(root, layer)
    if not path.exists():
        # LAYER_ABSENT 訊息不得附絕對路徑（公開層日誌／print 會把它帶出去）
        return {"layer": layer, "records": [], "diagnostics": [
            {"code": "LAYER_ABSENT", "message": f"{layer} layer not found"}]}
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.setdefault("diagnostics", [])
    # 讀取側也 redact：防舊版本層檔殘留的絕對路徑外洩
    for d in doc["diagnostics"]:
        if "message" in d:
            d["message"] = re.sub(r"/(?:Users|home)/[A-Za-z0-9_.\-/]+", "<path>", str(d["message"]))
    return doc


def save_layer(root, layer, doc):
    path = layer_file(root, layer)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 公開發布衛生：diagnostics 只保留代碼＋redacted 訊息，絕不附絕對路徑
    sanitized = []
    for d in doc.get("diagnostics", []):
        msg = re.sub(r"/(?:Users|home)/[A-Za-z0-9_.\-/]+", "<path>", str(d.get("message", "")))
        sanitized.append({
            "code": d.get("code"),
            "message": msg,
            "id": d.get("id"),
        })
    doc["diagnostics"] = sanitized
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    shutil.move(str(tmp), str(path))
    return path


def validate_record(rec, diagnostics):
    ok = True
    for field in REQUIRED:
        if field not in rec:
            diagnostics.append({"code": "MISSING_FIELD", "message": f"{rec.get('id', '?')}: {field}", "id": rec.get("id")})
            ok = False
    if rec.get("sha256") and not re.fullmatch(r"[0-9a-f]{64}", str(rec.get("sha256"))):
        diagnostics.append({"code": "BAD_SHA256", "message": str(rec.get("id")), "id": rec.get("id")})
        ok = False
    if rec.get("license") not in LICENSE_ENUM:
        diagnostics.append({"code": "BAD_LICENSE", "message": str(rec.get("license")), "id": rec.get("id")})
        ok = False
    if rec.get("status") not in STATUS_ENUM:
        diagnostics.append({"code": "BAD_STATUS", "message": str(rec.get("status")), "id": rec.get("id")})
        ok = False
    if rec.get("visibility") not in ("public", "private"):
        diagnostics.append({"code": "BAD_VISIBILITY", "message": str(rec.get("visibility")), "id": rec.get("id")})
        ok = False
    if rec.get("generation") is not None and not isinstance(rec.get("generation"), int):
        diagnostics.append({"code": "BAD_GENERATION", "message": str(rec.get("id")), "id": rec.get("id")})
        ok = False
    if rec.get("generation", 0) > 2:
        diagnostics.append({"code": "GENERATION_LIMIT_EXCEEDED", "message": str(rec.get("id")), "id": rec.get("id")})
        ok = False
    return ok


# ---------- 完整性 ----------

def integrity_check(root, layer, source_root=None, recovery_root=None):
    """sha256 核對。public 層以 repo root 為準；private/history 層記錄的 digest
    錨定在私人來源，必須依 provenance.kind 選對 base 才能正確驗證：

    - active_disk        → source_root（~/.agents/skills 現役盤點來源）
    - heritage_recovery  → recovery_root（~/.local/agent-skills/recovery/skills 隔離區）
    - hermes_forge       → repo root（forge-workspace 在 repo 內）

    未提供對應 root 時，該錨點記錄標記「digest recorded; source not available」
    （ok=None），絕不拿錯 base 硬驗造成誤報。
    """
    doc = load_layer(root, layer)
    root_path = Path(root)
    results = []
    for rec in doc["records"]:
        rel = rec.get("relative_path")
        expected = rec.get("sha256")
        entry = {"id": rec["id"], "ok": None, "note": ""}
        if not expected:
            entry["note"] = "no digest recorded"
        elif not rel:
            entry["note"] = "no path; digest recorded only"
        else:
            base, anchor = root_path, "repo"
            if layer in ("private", "history"):
                kind = (rec.get("provenance") or {}).get("kind")
                if kind == "active_disk":
                    if source_root:
                        base, anchor = Path(source_root), "source_root"
                    else:
                        entry["note"] = "digest recorded; active-disk source not available"
                        results.append(entry)
                        continue
                elif kind == "heritage_recovery":
                    if recovery_root:
                        base, anchor = Path(recovery_root), "recovery_root"
                    else:
                        entry["note"] = "digest recorded; recovery source not available"
                        results.append(entry)
                        continue
            p = base / rel
            if not p.exists():
                entry["note"] = f"file absent ({anchor})"
            else:
                actual = sha256_file(p)
                entry["ok"] = actual == expected
                if not entry["ok"]:
                    entry["note"] = f"digest mismatch ({anchor})"
        results.append(entry)
    return {"layer": layer, "results": results,
            "mismatches": [r for r in results if r["ok"] is False]}


# ---------- 搜尋 ----------

def _tokens(text):
    text = text.lower()
    out = []
    for word in re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", text):
        if re.fullmatch(r"[\u3400-\u9fff]+", word):
            out.extend(word[i:i + 2] for i in range(max(1, len(word) - 1)))
        elif len(word) > 2 and word.endswith("s") and not word.endswith("ss"):
            out.append(word[:-1])
        else:
            out.append(word)
    return out


def search(root, layer, query=None, category=None, status=None, limit=50, fields=None):
    """全文 + metadata 檢索。query 為空白時回全量（受 limit 約束）。"""
    doc = load_layer(root, layer)
    q_tokens = set(_tokens(query)) if query else set()
    out = []
    for rec in doc["records"]:
        if status and rec.get("status") != status:
            continue
        if category and category not in (rec.get("category") or []):
            continue
        hay = " ".join(str(rec.get(k, "")) for k in ("name", "description", "category", "triggers", "capabilities"))
        hay_t = set(_tokens(hay))
        if q_tokens and not q_tokens & hay_t:
            continue
        out.append(rec)
        if len(out) >= limit:
            break
    return out


def find_duplicates(root, layer):
    doc = load_layer(root, layer)
    by_digest, by_name = {}, {}
    for rec in doc["records"]:
        if rec.get("sha256"):
            by_digest.setdefault(rec["sha256"], []).append(rec["id"])
        by_name.setdefault(rec.get("name"), []).append(rec["id"])
    dupes = [
        {"kind": "body_digest", "ids": ids} for ids in by_digest.values() if len(ids) > 1
    ] + [
        {"kind": "name", "names": name, "ids": ids}
        for name, ids in by_name.items() if len(ids) > 1
    ]
    return dupes


def dependency_check(root, layer):
    doc = load_layer(root, layer)
    known = {r["id"] for r in doc["records"]}
    problems = []
    for rec in doc["records"]:
        for dep in rec.get("dependencies", []):
            if dep not in known:
                problems.append({"id": rec["id"], "missing_dependency": dep})
    return problems


def secret_scan(root, layer):
    """對 layer 記錄相對應的 SKILL.md 跑秘密/私人路徑掃描（讀取，不執行）。"""
    doc = load_layer(root, layer)
    root_path = Path(root)
    findings = []
    for rec in doc["records"]:
        rel = rec.get("relative_path")
        if not rel:
            continue
        p = root_path / rel
        if not p.exists() or p.is_symlink():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for kind, pat in SECRET_PATTERNS:
            m = pat.search(text)
            if m:
                findings.append({"id": rec["id"], "kind": kind, "snippet": m.group(0)[:40]})
        if re.search(r"/(?:Users|home|tmp)/[A-Za-z0-9_]+/", text):
            findings.append({"id": rec["id"], "kind": "local_absolute_path", "snippet": "(redacted)"})
    return findings


# ---------- 版本與 rollback ----------

def snapshot(root, layer, label):
    history = Path(root) / "registry/history/versions"
    history.mkdir(parents=True, exist_ok=True)
    doc = load_layer(root, layer)
    doc["updated_at"] = now_iso()
    target = history / f"{layer}-{label or now_iso()}.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    shutil.move(str(tmp), str(target))
    return target


def list_versions(root, layer):
    history = Path(root) / "registry/history/versions"
    if not history.exists():
        return []
    return sorted(p.name for p in history.iterdir() if p.name.startswith(f"{layer}-"))


def rollback(root, layer, version_name):
    target = Path(root) / "registry/history/versions" / version_name
    if not target.exists():
        raise FileNotFoundError(version_name)
    doc = json.loads(target.read_text(encoding="utf-8"))
    save_layer(root, layer, doc)
    return target


# ---------- 建 layer（從 P0 盤點輸入）----------

def build_record(
    *, id, name, relative_path, sha, license, status, visibility, risk,
    description="", category=None, source_repo=None, source_commit=None,
    **extra,
):
    rec = {
        "id": id,
        "name": name,
        "description": description,
        "category": category or [],
        "source_repo": source_repo,
        "source_commit": source_commit,
        "license": license,
        "license_notice_retained": license != "unknown",
        "sha256": sha,
        "relative_path": relative_path,
        "dependencies": [],
        "compatible_hosts": [],
        "capabilities": [],
        "triggers": [],
        "status": status,
        "visibility": visibility,
        "risk_level": risk,
        "provenance": {},
        "generation": 0,
        "updated_at": now_iso(),
    }
    rec.update(extra)
    diagnostics = []
    validate_record(rec, diagnostics)
    return rec, diagnostics


def import_v3_public(root, repo_root):
    """由 V3 main checkout（repo_root）匯入 14 個公開核心技能為 approved_public。"""
    repo_root = Path(repo_root)
    prov = json.loads((repo_root / "docs/第三方來源與授權.json").read_text(encoding="utf-8"))
    upstream = prov.get("bundled_source", {})
    by_path = {f["path"]: f for f in upstream.get("files", [])}
    doc = load_layer(root, "public")
    diagnostics = doc.get("diagnostics", [])
    for skill_dir in sorted(p for p in repo_root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()):
        skill_md = skill_dir / "SKILL.md"
        if skill_md.is_symlink():
            continue
        rel = skill_md.relative_to(repo_root).as_posix()
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        fm = {}
        for line in (m.group(1).splitlines() if m else []):
            km = re.match(r"^(name|description|version):\s*(.+)$", line)
            if km:
                fm[km.group(1)] = km.group(2).strip()
        upstream_entry = by_path.get(rel, {})
        license = "MIT"  # 13 技能 = obra/superpowers MIT；using-superpowers = 本 repo 原創 MIT
        rec, d = build_record(
            id=f"public:{skill_dir.name}",
            name=fm.get("name", skill_dir.name),
            relative_path=rel,
            sha=sha256_file(skill_md),
            license=license,
            status="approved_public",
            visibility="public",
            risk="low",
            description=fm.get("description", ""),
            source_repo=upstream.get("repository") if skill_dir.name != "using-superpowers" else "https://github.com/juhjuhx/agent-skills.git",
            source_commit=upstream.get("commit") if skill_dir.name != "using-superpowers" else None,
            provenance={
                "upstream": upstream.get("repository") if skill_dir.name != "using-superpowers" else "original",
                "upstream_sha256": upstream_entry.get("upstream_sha256"),
                "license_file": "licenses/obra__superpowers/LICENSE" if skill_dir.name != "using-superpowers" else "LICENSE",
                "notice_retained": True,
            },
        )
        diagnostics.extend(d)
        existing = {r["id"]: i for i, r in enumerate(doc["records"])}
        if rec["id"] in existing:
            doc["records"][existing[rec["id"]]] = rec
        else:
            doc["records"].append(rec)
    doc["diagnostics"] = diagnostics
    doc["layer"] = "public"
    doc["updated_at"] = now_iso()
    path = save_layer(root, "public", doc)
    return path, len(doc["records"])


def import_private(root, recovery_manifest, catalog_manifest=None):
    """由 P0 recovery manifest + 640 catalog manifest 匯入私人/歷史層（永不上 GitHub）。

    catalog_manifest（~/.agents/skills/.superpowers/SKILLS_INDEX.json）提供每筆
    relative_path（SKILL.md）與 body_digest；recovery_manifest 提供 148 歷史目錄
    的隔離狀態與安全掃描結果。
    """
    data = json.loads(Path(recovery_manifest).read_text(encoding="utf-8"))
    quarantined_dirs = {s["file"].rsplit("/", 1)[0] for s in data.get("security_hits", [])
                        if s.get("issue") == "symlink_target_missing_or_absolute"}
    quarantined_ids = set(data.get("summary", {}).get("quarantined_ids", []))
    recovered_dirs = set(data.get("summary", {}).get("historical_recovered_dirs", []))
    records_by_dir = {}
    for rec in data.get("records", []):
        if rec.get("status") == "QUARANTINED":
            quarantined_ids.add(rec["id"])
        records_by_dir[rec["root_dir"]] = rec
    hist, priv = load_layer(root, "history"), load_layer(root, "private")
    diag_hist, diag_priv = hist.setdefault("diagnostics", []), priv.setdefault("diagnostics", [])
    n_hist = n_priv = 0
    if catalog_manifest:
        # 冪等：重寫由 catalog 管理的記錄（heritage/active），保留 hermes_forge 記錄
        keep = lambda recs: [r for r in recs if (r.get("provenance") or {}).get("kind") == "hermes_forge"]
        hist["records"] = keep(hist["records"])
        priv["records"] = keep(priv["records"])
        catalog = json.loads(Path(catalog_manifest).read_text(encoding="utf-8"))
        for e in catalog["skills"]:
            rel = e["relative_path"]
            root_dir = rel.rsplit("/", 1)[0]
            license = e.get("license") or "unknown"
            if license in ("Proprietary. LICENSE.txt has complete terms",
                           "Complete terms in LICENSE.txt", "LICENSE.txt 中的完整條款"):
                license = "proprietary"
            is_quarantined = (
                e.get("classification") == "QUARANTINED"
                or (e.get("quarantine_state") or "none") != "none"
                or root_dir in quarantined_dirs
            )
            rec, d = build_record(
                id=e["skill_id"],
                name=e["canonical_name"],
                relative_path=rel,
                sha=e.get("body_digest") or "0" * 64,
                license=license,
                status="quarantined" if is_quarantined else "candidate",
                visibility="private",
                risk="high" if is_quarantined else "unreviewed",
                description=e.get("description", ""),
                category=e.get("categories") or [],
                triggers=e.get("triggers") or [],
                source_repo=(e.get("provenance") or {}).get("source"),
                source_commit=(e.get("provenance") or {}).get("source_commit"),
                provenance={
                    "kind": "heritage_recovery" if root_dir in recovered_dirs else "active_disk",
                    "heritage_commit": data.get("summary", {}).get("heritage_commit"),
                    "in_active_492": root_dir not in recovered_dirs,
                    "license_state": e.get("license_state"),
                },
            )
            diag_hist.extend(d)
            hist["records"].append(rec)
            n_hist += 1
            if not is_quarantined and license != "unknown":
                priv["records"].append({**rec, "status": "approved_private"})
                n_priv += 1
    else:
        keep = [r for r in hist["records"] if (r.get("provenance") or {}).get("kind") == "hermes_forge"]
        hist["records"] = keep
        priv["records"] = [r for r in priv["records"] if (r.get("provenance") or {}).get("kind") == "hermes_forge"]
        diag_hist, diag_priv = [], []
        for root_dir, rec in records_by_dir.items():
            rec2, d = build_record(
                id=f"local:{root_dir}", name=root_dir, relative_path=root_dir,
                sha="0" * 64, license=rec.get("license") or "unknown",
                status="quarantined" if rec.get("quarantined") else "candidate",
                visibility="private", risk="high",
                provenance={"kind": "historical_recovery",
                            "heritage_commit": data.get("summary", {}).get("heritage_commit")},
            )
            diag_hist.extend(d)
            hist["records"].append(rec2)
            n_hist += 1
    hist["layer"] = "history"
    hist["updated_at"] = now_iso()
    hist["diagnostics"] = diag_hist
    save_layer(root, "history", hist)
    priv["layer"] = "private"
    priv["updated_at"] = now_iso()
    priv["diagnostics"] = diag_priv
    save_layer(root, "private", priv)
    return n_hist, n_priv


# ---------- CLI ----------

def main(argv=None):
    parser = argparse.ArgumentParser(description="agent-skills registry")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = lambda name, help_: sub.add_parser(name, help=help_)  # noqa: E731
    a_import = p("import-public", "匯入 V3 公開核心技能")
    a_import.add_argument("--root", default=".")
    a_import.add_argument("--repo", required=True, help="main checkout 路徑")
    a_import_pri = p("import-private", "匯入 P0 recovery manifest + 640 catalog manifest 到私人/歷史層")
    a_import_pri.add_argument("--root", default=".")
    a_import_pri.add_argument("--manifest", required=True)
    a_import_pri.add_argument("--catalog", default=None, help="640 SKILLS_INDEX.json 路徑")
    a_search = p("search", "全文 + metadata 檢索")
    a_search.add_argument("query", nargs="?")
    a_search.add_argument("--root", default=".")
    a_search.add_argument("--layer", choices=list(LAYER_DIRS), default="public")
    a_search.add_argument("--category")
    a_search.add_argument("--status")
    a_search.add_argument("--limit", type=int, default=50)
    a_dup = p("duplicates", "重複偵測")
    a_dup.add_argument("--root", default=".")
    a_dup.add_argument("--layer", choices=list(LAYER_DIRS), default="public")
    a_deps = p("deps", "依賴檢查")
    a_deps.add_argument("--root", default=".")
    a_deps.add_argument("--layer", choices=list(LAYER_DIRS), default="public")
    a_int = p("integrity", "sha256 完整性")
    a_int.add_argument("--root", default=".")
    a_int.add_argument("--layer", choices=list(LAYER_DIRS), default="public")
    a_int.add_argument("--source-root", default=str(Path.home() / ".agents/skills"),
                       help="active_disk 記錄的 digest 錨點（~/.agents/skills）")
    a_int.add_argument("--recovery-root",
                      default=str(Path.home() / ".local/agent-skills/recovery/skills"),
                      help="heritage_recovery 記錄的 digest 錨點（recovery 隔離區）")
    a_sec = p("secrets", "秘密/私人路徑掃描")
    a_sec.add_argument("--root", default=".")
    a_sec.add_argument("--layer", choices=list(LAYER_DIRS), default="public")
    a_snap = p("snapshot", "版本快照")
    a_snap.add_argument("--root", default=".")
    a_snap.add_argument("--layer", choices=list(LAYER_DIRS), required=True)
    a_snap.add_argument("--label")
    a_rb = p("rollback", "回滾到快照")
    a_rb.add_argument("--root", default=".")
    a_rb.add_argument("--layer", choices=list(LAYER_DIRS), required=True)
    a_rb.add_argument("version")
    a_v = p("versions", "列出快照")
    a_v.add_argument("--root", default=".")
    a_v.add_argument("--layer", choices=list(LAYER_DIRS), required=True)
    a_val = p("validate", "schema 驗證")
    a_val.add_argument("--root", default=".")
    a_val.add_argument("--layer", choices=list(LAYER_DIRS), default="public")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    if args.cmd == "import-public":
        path, n = import_v3_public(root, args.repo)
        print(f"public layer -> {path} ({n} records)")
    elif args.cmd == "import-private":
        h, pvt = import_private(root, args.manifest, args.catalog)
        print(f"history layer: {h} records; private layer: {pvt} records")
    elif args.cmd == "search":
        hits = search(root, args.layer, args.query, args.category, args.status, args.limit)
        print(json.dumps(hits, ensure_ascii=False, indent=1))
    elif args.cmd == "duplicates":
        print(json.dumps(find_duplicates(root, args.layer), ensure_ascii=False, indent=1))
    elif args.cmd == "deps":
        print(json.dumps(dependency_check(root, args.layer), ensure_ascii=False, indent=1))
    elif args.cmd == "integrity":
        print(json.dumps(
            integrity_check(root, args.layer, args.source_root, args.recovery_root),
            ensure_ascii=False, indent=1))
    elif args.cmd == "secrets":
        print(json.dumps(secret_scan(root, args.layer), ensure_ascii=False, indent=1))
    elif args.cmd == "snapshot":
        print(snapshot(root, args.layer, args.label))
    elif args.cmd == "rollback":
        print(rollback(root, args.layer, args.version))
    elif args.cmd == "versions":
        print(json.dumps(list_versions(root, args.layer)))
    elif args.cmd == "validate":
        doc = load_layer(root, args.layer)
        diags = []
        for rec in doc["records"]:
            validate_record(rec, diags)
        print(json.dumps({"valid": not diags, "diagnostics": diags}, ensure_ascii=False, indent=1))
        return 0 if not diags else 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
