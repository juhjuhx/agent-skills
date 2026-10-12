#!/usr/bin/env python3
"""Generate the public-only metadata snapshot; never traverses external links."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(root):
    root = root.resolve()
    spec = importlib.util.spec_from_file_location(
        "tool_master", root / "runtime/skills-router/tool_master.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    records = []
    excluded = []
    for directory in sorted(root.iterdir()):
        if directory.is_symlink():
            excluded.append(
                {"path": directory.name, "reason": "external_or_unverified_symlink"}
            )
            continue
        path = directory / "SKILL.md"
        if not directory.is_dir() or not path.is_file() or path.is_symlink():
            continue
        metadata = module._frontmatter(path, 65536)
        name = metadata.get("name") or directory.name
        ready = bool(metadata.get("description")) and directory.name != "ui-ux-pro-max"
        records.append(
            {
                "skill_id": "public:" + directory.name,
                "canonical_name": name,
                "aliases": [directory.name] if directory.name != name else [],
                "description": metadata.get("description", ""),
                "relative_path": path.relative_to(root).as_posix(),
                "body_digest": hashlib.sha256(path.read_bytes()).hexdigest(),
                "body_available": True,
                "route_eligible": ready,
                "deprecated": False,
            }
        )
        if not ready:
            excluded.append(
                {
                    "path": directory.name,
                    "reason": "missing_metadata_or_unbundled_required_resources",
                }
            )
    canonical = json.dumps(
        records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    revision = "sha256:" + hashlib.sha256(canonical).hexdigest()
    categories = json.loads((root / "categories.json").read_text())
    installable = set(
        s
        for c in categories["categories"]
        for s in c["skills"]
        if (root / s / "SKILL.md").is_file()
    )
    return {
        "schema_version": "personal-tool-master-public-index/1",
        "catalog_revision": revision,
        "counts": {
            "physical_skill_files": len(records),
            "route_eligible": sum(r["route_eligible"] for r in records),
            "category_distinct_installable": len(installable),
        },
        "counting_method": "One ordinary root-directory SKILL.md per record; no external symlink targets or local untracked additions. Eligibility is metadata/resource readiness, not a license grant.",
        "excluded": excluded,
        "skills": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    catalog = build(root)
    output = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    lock = (
        json.dumps(
            {
                "schema_version": "personal-tool-master-public-lock/1",
                "catalog_revision": catalog["catalog_revision"],
                "index_sha256": hashlib.sha256(output.encode()).hexdigest(),
                "counts": catalog["counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    for rel, data in (
        (".superpowers/SKILLS_INDEX.json", output),
        (".superpowers/registry.lock.json", lock),
    ):
        path = root / rel
        if args.check:
            if not path.is_file() or path.read_text() != data:
                raise SystemExit(f"Stale public catalog: {rel}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
    print(json.dumps(catalog["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
