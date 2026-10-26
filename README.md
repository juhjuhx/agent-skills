# agent-skills — Agent Skills v3.0 (Personal Tool Master)

A public library of **464 portable agent-skill packages** that install into the
host you already run — Hermes, DSH, OpenCode, Codex, Claude, Gemini CLI, and any
`SKILL.md`-compatible agent. Skills guide the agent; the **host** controls
execution and permissions. The router is **advisory and fail-open** — a router
failure can never disable your native tools.

## 1. What Is This

- **464 public skill packages** = 14 verified-source core skills (repo root) +
  450 portable extras under `skills/<slug>/`, each shipping its own
  `NOTICE` / `LICENSE` and any required `scripts/` `references/` `assets/`.
- **Portable, cross-agent**: one `SKILL.md` standard; one installer targets any host.
- **Advisory router, not a gate**: load `using-superpowers`, discover a small set
  of relevant skills + the host's *actual* tools, run a short workflow, verify.
- **Provenance + integrity**: `catalog.json` (machine index) + `catalog.lock.json`
  (per-slug SHA-256) + a license/security gate. Unlicensed, copyleft, or
  secret-bearing skills are **not** published — they stay in a private excluded
  manifest only ([Skill Provenance](docs/SKILL_PROVENANCE.md)).

## 2. Quick Start

Clone into a clean path — never over a personal dirty skill tree:

```sh
git clone https://github.com/juhjuhx/agent-skills.git agent-skills-v3
cd agent-skills-v3
bash install.sh --list                      # preview the catalog
bash install.sh --all --host hermes         # install all 464 into ~/.hermes/skills
bash install.sh --all --host dsh            # DSH: top-level direct subdirs
bash install.sh --verify                     # confirm symlinks resolve to SKILL.md
```

Run the router with your task (advisory output; nothing auto-executes):

```sh
python3 runtime/skills-router/tool_master.py route \
  "debug: reproduce a sort error, minimal fix and verify" --root . --host generic
```

Flags: `--minimal` (3 master skills) · `--default` (14 core) · `--all` ·
`--category <ids>` · `--skill <slug,...>` · `--dry-run` · `--rollback` ·
`--update` (ff-only) · `--host {auto,hermes,dsh,opencode,claude,codex,gemini}`.
Full matrix, rollback and host notes:
[Install & Use](docs/安裝與使用.md) · [Cross-Host Install](docs/CROSS_AGENT_INSTALL.md)
· [Hermes](docs/INSTALL_HERMES.md) · [DSH](docs/INSTALL_DSH.md).

Host status in this release (**flag presence is not live-E2E proof**):

| Host | Install | Status |
|---|---|---|
| Hermes | `--host hermes` (selective symlink, no overwrite) | installer path live; E2E not re-verified |
| DSH | `--host dsh` (top-level subdirs) | installer path live; E2E not re-verified |
| OpenCode | `--host opencode` (+ optional `--opencode-advisory`) | historical research path |
| Claude / Codex / Gemini | `--host claude|codex|gemini` (dir symlink) | flag present; live E2E unverified |

## 3. Skills & Architecture

```
+---------------------+
| TASK / USER REQUEST |
+=====================+
|
v
+-------------------------------------------+
|           TOOL MASTER / ROUTER            |
| fail-open advisory, not a permission gate |
+===========================================+
|
v
+-------------------------------------+
| CATALOG + REGISTRY + SKILL METADATA |
| 14 core + 450 extra = 464 packages  |
|                                     |
|                                     |
| source, license, SHA-256, category  |
+=====================================+
|
v
+------------------------------------------+
|      ROUTEPACKET / SELECTED SKILLS       |
| advisory output, not automatic execution |
|                                          |
|                                          |
| suggested skills + next-step hints       |
+==========================================+
|
v
+---------------------------------------------------+
|             HOST TOOLS + PERMISSIONS              |
| host owns execution and tool permissions          |
|                                                   |
|                                                   |
| Hermes / DSH / OpenCode / Codex / Claude / Gemini |
+===================================================+
|
v
+----------------------------------------+
|    EXECUTION -> RESULT VERIFICATION    |
| results must be evidenced, not assumed |
+========================================+
bypass: router failure -> metadata fallback / manual workflow
         native host tools stay available
scope note: unlicensed or copyleft skills are excluded to a
local-only manifest and never enter the public repository
```

- **14 categories** (`agent-orchestration`, `coding`, `design`, `review`,
  `devops`, `data-science`, ...) — [Skills Catalog](docs/SKILLS_CATALOG.md).
- **Catalog & lock**: [`catalog.json`](catalog.json) (464 index) +
  [`catalog.lock.json`](catalog.lock.json) (SHA-256 per slug; `--verify` enforces).
- **Router**: metadata keyword scoring, top-20 candidates, picks 0–8 positive
  skills (guided/normal/high = 3/5/8), digests only the selected bodies. No
  embeddings, no reranker, no daemon, no new tool gate.
  Router decision flow: [ROUTER_DECISION_FLOW](docs/architecture/ROUTER_DECISION_FLOW.md).
  Details: [System Architecture](docs/architecture/V3_SYSTEM_ARCHITECTURE.md) ·
  [Component Reference](docs/architecture/V3_COMPONENT_REFERENCE.md).

## 4. Security & Compatibility

- **License provenance**: root MIT covers V3-original files + new docs;
  Superpowers keeps Jesse Vincent's MIT notice; extras ship their own
  `NOTICE`/`LICENSE`. [Licensing Scope](docs/授權範圍.md) ·
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) ·
  [per-file source map](docs/第三方來源與授權.json).
- **SHA-256 lock**: `--verify` checks every installed symlink resolves and
  matches the lock digest; a mismatch fails (rc=1).
- **Private / public boundary**: only approved, security-screened content is
  published. LICENSE-unknown, unlicensed copyleft, and secret-bearing skills are
  excluded to a **local-only** manifest — never in git.
- **Safe install**: existing host dirs, plugins and checkouts are never
  overwritten; `--dry-run` previews, `--rollback` restores.
- **Fail-open router**: a router/catalog failure degrades to metadata fallback or
  a manual workflow; it cannot lock the host out of its own tools.
- **Host owns permissions**: the router recommends; the host's schema and
  permission checks are the final authority.

## 5. Documentation & Roadmap

| Area | File |
|---|---|
| Install / use | [安裝與使用](docs/安裝與使用.md) · [Cross-Host](docs/CROSS_AGENT_INSTALL.md) · [Hermes](docs/INSTALL_HERMES.md) · [DSH](docs/INSTALL_DSH.md) |
| Catalog & provenance | [Skills Catalog](docs/SKILLS_CATALOG.md) · [Skill Provenance](docs/SKILL_PROVENANCE.md) |
| Architecture | [System](docs/architecture/V3_SYSTEM_ARCHITECTURE.md) · [Router Flow](docs/architecture/ROUTER_DECISION_FLOW.md) · [Workflow & Tool Mapping](docs/architecture/V3_WORKFLOW_AND_TOOL_MAPPING.md) · [Storage & State](docs/architecture/V3_STORAGE_AND_STATE.md) · [Testing & Limits](docs/architecture/V3_TESTING_AND_LIMITATIONS.md) |
| Debug / review | [DEBUG_AND_REVIEW_WORKFLOW](docs/DEBUG_AND_REVIEW_WORKFLOW.md) |
| Release & migration | [Release & Migration](docs/architecture/V3_RELEASE_AND_MIGRATION.md) · [Release Verification](docs/RELEASE_VERIFICATION.md) · [發布與回復](docs/發布與回復.md) · [發布驗收](docs/發布驗收.md) |
| Roadmap | [ROADMAP](docs/ROADMAP.md) |
| Decisions | [ADR-0001 distribution](docs/adr/0001-distribution-architecture.md) |

Maintenance & gates:

```sh
python3 scripts/build_v3_catalog.py --check
python3 -m unittest discover -s runtime/skills-router/tests -p 'test_*.py'
python3 -m unittest discover -s tests -p 'test_*.py'
node --test runtime/skills-router/tests/test_v3_advisory.mjs
```

[CHANGELOG](CHANGELOG.md) · [GitHub Releases](https://github.com/juhjuhx/agent-skills/releases)

---

### English quick start

The public edition ships **464 skill packages** (14 core + 450 extra), all
installable by unique name. Clone into a clean directory, run
`bash install.sh --minimal` (or `--all --host <you>`), load `using-superpowers`,
then give your agent the task. Dirty installs and existing plugins are preserved;
native skills work without the optional OpenCode adapter. The host controls
execution and permissions; a router failure cannot disable native tools.
Third-party MIT notices stay intact; removing restricted content from this
snapshot does not clear historical git risk.
