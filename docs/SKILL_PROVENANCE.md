# Skill Provenance (M4-P8)

## Source model

- **Core 14** (`registry/public/registry.json` generation 0): pinned to the Superpowers upstream
  commit `8ca22dba9a94f28898bbce59f2537ff4d87c747d` (MIT, Jesse Vincent). Each package retains
  the full MIT `LICENSE`; notices are kept. `using-superpowers` is the V3 rewrite.
- **Additional 450** (`catalog.json` generation 1): portable packages ported from the
  user's local skill libraries under `~/.hermes/skills`, `~/.agents/skills`, `~/.claude/skills`,
  `~/.config/opencode/skills`. Each package carries a `NOTICE` (or `LICENSE`) recording its
  canonical local source and that private local paths are **not** included.

## What is NOT in the public repo

Per the license/security gate, these are kept out and tracked only in a local excluded manifest
(`~/.local/agent-skills/audit/M4-P8-EXCLUDED-MANIFEST.json`), never published:

- Skills with **no verifiable redistribution right** (license unknown) — local-only.
- **Copyleft (GPL/AGPL)** skills without an explicit author opt-in.
- Any skill body or asset containing **genuine credentials / private data** detected by the
  fixture-aware security scan.

Public manifest entries never contain local absolute paths, private repo URLs, or raw secrets.
Portable normalization rewrites `/Users/<name>` to `~` at pack time and re-verifies zero leaks.
