#!/usr/bin/env python3
"""Registry Provider — V3.1 Phase 3 versioned contract (REGISTRY side).

Publishes a metadata-only, versioned index for the Router Consumer to validate.
This module never inlines skill bodies and never emits private absolute paths
in a public-safe build (public_only=True). POLICY_EPOCH / CAPABILITY_DECLARATION
are compatibility/advisory data — they are NOT execution authorization (R3).

Two responsibilities:
  build_contract(...)          -> the versioned 9-field document
  reconcile_categories(...)    -> the 8-category count reconciliation (STEP 3)

All ops fail-open: an absent/corrupt layer degrades to zero records + a
diagnostic, it never raises and never blocks the V3 router (AGENTS.md contract).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
_REGISTRY_PY = _HERE.parent / "registry.py"
REGISTRY_REV_PREFIX = "rev-"

# Role priority mirrors composer._role_for (single source of truth for "best role").
ROLE_PRIORITY = {"executable": 0, "search_only": 1, "excluded": 2}
LAYER_ORDER = ("public", "private", "history")


def _load_registry():
    spec = importlib.util.spec_from_file_location("registry", _REGISTRY_PY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"registry module unavailable: {_REGISTRY_PY}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _role_for(layer, rec):
    """Mirror of composer._role_for — quarantined excluded; public/private
    executable; history search_only. Keeps provider & consumer role logic in
    sync so reconciliation and candidate_pool never disagree."""
    if rec.get("status") == "quarantined":
        return "excluded"
    if layer in ("public", "private"):
        return "executable"
    return "search_only"


def _load_all_layers(reg_root):
    """Return ({layer: [records]}, diagnostics). Absent/corrupt layers degrade to
    [] + a LAYER_ABSENT/LAYER_CORRUPT diagnostic — never raise (fail-open)."""
    reg = _load_registry()
    layers, diags = {}, []
    for layer in LAYER_ORDER:
        try:
            layers[layer] = reg.load_layer(reg_root, layer)["records"]
        except (OSError, ValueError, json.JSONDecodeError, RuntimeError, KeyError) as exc:
            layers[layer] = []
            diags.append({"code": "LAYER_UNAVAILABLE", "layer": layer, "message": str(exc)})
    return layers, diags


def build_contract(
    reg_root,
    *,
    source_commit=None,
    policy_epoch=1,
    public_only=False,
    registry_schema_version=1,
    router_version_min="3.1",
):
    """Emit the versioned 9-field contract document.

    public_only=True  -> public-safe build: only visibility=='public' records,
                         local paths never leave the repo, revision anchored.
    public_only=False -> local full build (stays gitignored): every layer's
                         metadata + body digest, no bodies.

    Field roles (schema + this module are the source of truth):
      registry_schema_version  int     provider schema major; consumer range-gates it
      registry_revision        str     monotonic build id; caller pins expected value
      source_commit            str     full 40-hex git HEAD, or 'unknown' sentinel
      policy_epoch             int     compatibility marker ONLY (advisory)
      router_version_min       str     minimum consumer version that can parse this
      skills[].skill_id        str     stable identifier
      skills[].body_sha256     str     integrity only (HASH_VERIFIED != SAFE/LOADED)
      skills[].capability_declaration  advisory, no host permission granted
      skills[].host_compatibility     [] = any host; else requested host must be in it
      skills[].status/visibility      lifecycle / publish boundary
    """
    layers, diags = _load_all_layers(reg_root)
    # Resolve source_commit: explicit > git HEAD of reg_root > 'unknown'.
    if source_commit is None:
        source_commit = _git_head(reg_root) or "unknown"
    if not isinstance(source_commit, str):
        source_commit = "unknown"

    records = []
    for layer in LAYER_ORDER:
        for rec in layers[layer]:
            if public_only and rec.get("visibility") != "public":
                continue
            records.append({
                "skill_id": str(rec.get("id")),
                "body_sha256": str(rec.get("sha256") or "0" * 64),
                "capability_declaration": list(rec.get("capabilities") or []),
                "host_compatibility": list(rec.get("compatible_hosts") or []),
                "status": str(rec.get("status", "")),
                "visibility": str(rec.get("visibility", "")),
                # A public-safe build strips the local relative_path so no private
                # path ever ships. Local full build keeps it for the consumer.
                "relative_path": rec.get("relative_path") if not public_only else None,
            })

    # A public-safe build must not advertise non-public layer cardinality either —
    # zero out private/history counts so only the public count is disclosed.
    layer_counts = {
        k: (len(v) if (k == "public" or not public_only) else 0)
        for k, v in layers.items()
    }
    payload = {
        "registry_schema_version": int(registry_schema_version),
        "source_commit": source_commit,
        "policy_epoch": int(policy_epoch),
        "router_version_min": str(router_version_min),
        "layer_counts": layer_counts,
        "skills": records,
    }
    revision = compute_revision(payload)
    doc = {
        "registry_schema_version": int(registry_schema_version),
        "registry_revision": revision,
        "source_commit": source_commit,
        "policy_epoch": int(policy_epoch),
        "router_version_min": str(router_version_min),
        "build_time": now_iso(),
        "public_only": bool(public_only),
        "layer_counts": payload["layer_counts"],
        "skills": records,
        "diagnostics": diags,
    }
    return doc


def compute_revision(payload):
    """Monotonic, content-addressed build id (short sha1 of canonical JSON)."""
    canonical = json.dumps(
        {k: payload[k] for k in (
            "registry_schema_version", "source_commit", "policy_epoch",
            "router_version_min", "layer_counts", "skills")},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]
    return f"{REGISTRY_REV_PREFIX}{digest}"


def _git_head(reg_root):
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(Path(reg_root)),
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            head = out.stdout.strip()
            if len(head) == 40:
                return head
    except (OSError, subprocess.SubprocessError):
        pass
    return None


# ------------------------------------------------------------------ STEP 3
def reconcile_categories(reg_root, local_roots=None):
    """The 8-category count reconciliation (M4 P3 STEP 3).

    Semantics (single source of truth = the deduped candidate pool):
      layer_records         total records across the 3 layers (NOT unique skills)
      unique_skill_ids      distinct skill ids across all layers
      physical_bodies       distinct relative_path values across all layers
      searchable_skills     pool entries whose best role is executable|search_only
      runnable_skills       pool entries whose best role is executable
      historical_only_skills distinct ids that appear ONLY in the history layer
      duplicate_ids         ids seen in more than one layer
      quarantined_skills    pool entries whose role is excluded (quarantined)

    Never equates layer_records with unique_skill_ids — the 343 private records
    mirror 343 of the 640 history ids, so 997 layer records != 997 skills.
    Fail-open: absent layers contribute 0 and a diagnostic.
    """
    layers, diags = _load_all_layers(reg_root)
    all_recs = [(layer, rec) for layer in LAYER_ORDER for rec in layers[layer]]

    ids = set()
    for _, rec in all_recs:
        ids.add(str(rec.get("id")))
    unique_skill_ids = len(ids)
    layer_records = sum(len(v) for v in layers.values())

    bodies = set()
    for _, rec in all_recs:
        rel = rec.get("relative_path")
        if rel:
            bodies.add(str(rel))
    physical_bodies = len(bodies)

    # Which layers each id appears in
    layers_by_id = {}
    for layer, rec in all_recs:
        layers_by_id.setdefault(str(rec.get("id")), set()).add(layer)
    duplicate_ids = sum(1 for s in layers_by_id.values() if len(s) > 1)
    historical_only = sum(
        1 for s in layers_by_id.values() if s == {"history"})

    # Best-role dedup pool (mirrors composer.candidate_pool priority)
    best = {}
    for layer, rec in all_recs:
        role = _role_for(layer, rec)
        rid = str(rec.get("id"))
        cur = best.get(rid)
        if cur is None or ROLE_PRIORITY.get(role, 9) < ROLE_PRIORITY.get(cur[0], 9):
            best[rid] = (role, rec)
    by_role = {}
    for role, _ in best.values():
        by_role[role] = by_role.get(role, 0) + 1
    searchable_skills = by_role.get("executable", 0) + by_role.get("search_only", 0)
    runnable_skills = by_role.get("executable", 0)
    quarantined_skills = by_role.get("excluded", 0)

    return {
        "layer_records": layer_records,
        "unique_skill_ids": unique_skill_ids,
        "physical_bodies": physical_bodies,
        "searchable_skills": searchable_skills,
        "runnable_skills": runnable_skills,
        "historical_only_skills": historical_only,
        "duplicate_ids": duplicate_ids,
        "quarantined_skills": quarantined_skills,
        "by_role": by_role,
        "layer_counts": {k: len(v) for k, v in layers.items()},
        "diagnostics": diags,
    }


# ------------------------------------------------------------------ CLI
def main(argv=None):
    parser = argparse.ArgumentParser(description="registry versioned contract provider")
    sub = parser.add_subparsers(dest="cmd", required=True)
    a_pub = sub.add_parser("publish", help="emit the versioned contract document")
    a_pub.add_argument("--root", default=".")
    a_pub.add_argument("--source-commit", default=None)
    a_pub.add_argument("--policy-epoch", type=int, default=1)
    a_pub.add_argument("--public-only", action="store_true",
                       help="public-safe build: only visibility=public records, no local paths")
    a_pub.add_argument("--json", action="store_true")
    a_rec = sub.add_parser("reconcile", help="8-category count reconciliation")
    a_rec.add_argument("--root", default=".")
    a_rec.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    if args.cmd == "publish":
        doc = build_contract(root, source_commit=args.source_commit,
                             policy_epoch=args.policy_epoch,
                             public_only=args.public_only)
        if args.json:
            print(json.dumps(doc, ensure_ascii=False, indent=1))
        else:
            print(f"revision={doc['registry_revision']} source_commit={doc['source_commit']} "
                  f"public_only={doc['public_only']} skills={len(doc['skills'])} "
                  f"layer_counts={doc['layer_counts']}")
        return 0
    counts = reconcile_categories(root)
    if args.json:
        print(json.dumps(counts, ensure_ascii=False, indent=1))
    else:
        for k, v in counts.items():
            if k != "diagnostics":
                print(f"{k}={v}")
    if counts["diagnostics"]:
        print("diagnostics=" + json.dumps(counts["diagnostics"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
