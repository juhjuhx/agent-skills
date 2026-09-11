# Static Productization V1 — Phase 3I

本文件記錄 v3 第一個 static productization vertical slice。它只處理
productization plane：runtime capability inventory、InstallationPlan、derived
distribution tree 與 conformance validation；沒有執行任何 runtime、模型、安裝或
全域設定寫入。

## Decision

```yaml
STATIC_PRODUCTIZATION_READINESS: STATIC_PRODUCTIZATION_READY
CODEX_LIVE_TRANSPORT_STATUS: CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
stage_router_weights_mutated: false
runtime_processes_invoked: false
global_runtime_writes: false
```

## Repo truth

| 欄位 | 值 |
|---|---|
| repository | `juhjuhx/agent-skills` |
| base branch | `fix/v3-stage-router-defect-closure` |
| base HEAD | `9e00d543dc312c6f9bd31c33d6a235cc4a58cd72` |
| productization branch | `feat/v3-static-productization` |
| routing snapshot | `snapshot:87dc6a8790b10450` |
| metadata records | 214 |
| normal ranking body reads | 0 |

## Canonical / generated boundary

```text
skills/<skill>/SKILL.md + canonical registry
                    |
                    v
        validated RoutingCatalogSnapshot
                    |
                    +-- AgentAdapterManifest
                    +-- fixture-driven RuntimeProductStatus
                    |
                    v
          DistributionCompiler (pure/static)
                    |
                    +-- RuntimeCapabilityReport
                    +-- InstallationPlan
                    +-- derived runtime projection tree
```

Canonical `SKILL.md` remains the only procedure source. The compiler never copies
the full 214-skill library into a runtime directory. Generated files carry snapshot,
source and content digests and are not accepted as canonical input.

## Runtime product status

The four dimensions remain independent; there is no product-level `READY` shortcut.

| Runtime | Install | Adapter | Static contract | Live execution | Static output |
|---|---|---|---|---|---|
| Codex | `INSTALLED` | `NATIVE_IMPLEMENTED` | `VERIFIED` | `TRANSPORT_BLOCKED` | generated |
| Claude Code | `INSTALLED` | `READ_ONLY_IMPLEMENTED` | `VERIFIED` | `RUNTIME_BLOCKED` | generated |
| OpenCode | `INSTALLED` | `READ_ONLY_IMPLEMENTED` | `VERIFIED` | `PROVIDER_BLOCKED` | generated |
| Hermes | `INSTALLED` | `NOT_IMPLEMENTED` | `PARTIAL` | `PROVIDER_BLOCKED` | status only |
| unknown-runtime fixture | `UNKNOWN` | `NOT_IMPLEMENTED` | `UNVERIFIED` | `UNKNOWN` | none |

The source of these records is the fixture-driven inventory
[`runtime-inventory-v1.json`](../../../fixtures/v3/productization/runtime-inventory-v1.json).
This phase does not probe local executables, credentials or provider state.

## Routing snapshot and conformance

Each compile operation consumes one validated immutable
`RoutingCatalogSnapshot` (`snapshot:87dc6a8790b10450`) and checks:

- 214 metadata records, canonical source digests and curated field provenance;
- snapshot identity/digest and registry epoch;
- trust/quarantine loadability;
- an already-produced `StageRoute` without rerunning or changing Stage Router;
- an optional `CompiledExecutionBundle` bound to the selected runtime;
- selected skill references and, only when explicitly requested, selected bodies.

The dogfood conformance record is
[`static-conformance-v1.json`](../../../fixtures/v3/productization/static-conformance-v1.json).
For the B ordinary-bug route, the compiler consumed the existing route:

```text
TaskSpec → existing StageRouter → StageRoute
        → selected skill references → optional bundle reference
        → runtime projection → generated artifact manifest
```

The observed selected IDs were `diagnose`, `tdd`, `using-superpowers`, and
`verification-before-completion`; the compiler did not reselect them.

## Distribution compiler

Implementation: [`tools/v3/productization.py`](../../../tools/v3/productization.py).
It is one standard-library module with pure validation/planning helpers and a thin
CLI. It does not create a manager, service, registry, daemon, scheduler or database.

Supported operations:

```text
python3 tools/v3/productization.py --runtime codex --dry-run
python3 tools/v3/productization.py --runtime codex --operation plan --format json
python3 tools/v3/productization.py --runtime codex --operation compile --output <temp-dir>
python3 tools/v3/productization.py --runtime codex --operation validate --output <temp-dir>
python3 tools/v3/productization.py --runtime all --fixture ALL_KNOWN_STATIC --operation explain
```

`--runtime all` is intentionally limited to plan/explain; compile and validate need
one explicit runtime and one explicit output root so that a multi-runtime tree cannot
silently collide with another runtime's ownership marker.

## InstallationPlan

The plan is a no-write declaration. Each artifact has a relative path, kind, source
digest and content digest. Operations include `CREATE_GENERATED_FILE`,
`LINK_OR_REFERENCE_CANONICAL_SKILL`, `NO_OP`, `UPDATE_MANAGED`, `SKIP_USER_OWNED`,
`CONFLICT`, `SKIP_UNSUPPORTED_RUNTIME`, and `WARN_LIVE_BLOCKED`.

The public contracts are:

- [`runtime-product-status.schema.json`](../../../schemas/v3/runtime-product-status.schema.json)
- [`installation-plan.schema.json`](../../../schemas/v3/installation-plan.schema.json)
- [`generated-artifact.schema.json`](../../../schemas/v3/generated-artifact.schema.json)

The plan includes `no_actual_writes: true` and retains live blockers as warnings. A
blocked runtime is never represented as live-ready, and Hermes produces no synthetic
adapter artifacts.

## Generated trees

For Codex, Claude Code and OpenCode, a route-aware compile produced ten artifacts:

```text
<output>/
├── .asm-generated.json
├── artifact-manifest.json
├── runtime-capability-report.json
└── <runtime>/
    ├── adapter-manifest.json
    ├── runtime-contract.json
    ├── runtime-projection.json
    ├── runtime-status.json
    ├── routing-snapshot.json
    ├── selected-skills.json
    └── stage-route-reference.json
```

With `--materialize-selected`, only selected non-resident bodies are added under
`<runtime>/skills/selected/<skill>-<digest>/SKILL.md`. No route materializes all 214
bodies. Hermes and unknown runtimes have status/plan evidence but no fake tree.

## NO_SKILL_NEEDED and selected-only behavior

`NO_SKILL_NEEDED` produces an empty selected list, zero body files and no synthetic
skill artifact. Runtime bootstrap/status files may still exist. For a selected route,
the default compile keeps body files unloaded; explicit materialization in the focused
test produced three selected bodies, while the snapshot's ranking metric remained 0.
Raw skill bodies are never placed in plans, reports or evidence records unless the
explicit generated output is the requested selected-body materialization itself.

## Ownership, conflicts and stale output

`.asm-generated.json` binds generator ID, schema version, runtime, snapshot digest,
manifest digest and managed paths. The compiler:

- creates absent output artifacts;
- permits updates only for files carrying the generator marker;
- returns `SKIP_USER_OWNED` for user-owned destinations;
- returns `CONFLICT` for unknown destination state;
- refuses stale managed paths rather than silently deleting them;
- rejects global runtime directories and arbitrary output symlinks;
- validates existing output without regenerating it.

Changing the snapshot, runtime contract, selected source digest or artifact content
invalidates validation. Compile twice with identical inputs is byte/digest stable.

## Static performance sample

Three local samples were taken after implementation; these are compiler costs, not
runtime/model latency and not a live benchmark:

| Operation | Median | Min–max |
|---|---:|---:|
| snapshot load + validation | 464.003 ms | 459.546–476.392 ms |
| plan generation | 567.474 ms | 565.800–567.842 ms |
| artifact generation | 568.299 ms | 566.642–572.702 ms |
| generated-tree validation | 276.480 ms | 276.128–276.842 ms |

The current snapshot reports `json_parse_ms` 6.804, schema/digest validation
442.534, graph construction 0.057, and `body_files_loaded` 0. Productization keeps
the snapshot immutable per operation; it does not introduce a daemon or cache service.

## Security and regression gate

- No runtime/model command is imported or invoked; the compiler has no subprocess
  boundary.
- No `SKILL.md` command, URL, MCP, plugin, hook, credential or auth store is read or
  executed.
- Output is explicit and rejects global runtime destinations; writes are derived
  artifacts only.
- Runtime status cannot grant permissions, models, effort policy or live authority.
- `StageRouter` weights, generated/curated routing policy and trust/quarantine rules
  are untouched.
- Phase 3H's `STAGE_ROUTER_PRODUCTION_READY` result remains the routing baseline;
  the full before/after evidence is in
  [`STAGE_ROUTER_EVAL_V4.md`](STAGE_ROUTER_EVAL_V4.md).
- `NO_SKILL_NEEDED`, selected-only loading, 214 metadata records and zero body reads
  during ranking remain covered by tests.

## Verification

| Check | Result |
|---|---|
| focused productization/schema tests | PASS; 23/23 |
| full repository suite | PASS; 300/300 |
| JSON schema validation | PASS |
| compile/validate separation | PASS |
| idempotence | PASS |
| stale snapshot/runtime contract rejection | PASS |
| user-owned and symlink output safety | PASS |
| live runtime invocation | NOT RUN by policy |
| Stage Router weight mutation | NONE |
| OCR native diff | `BLOCKED_BY_AUTH`; one precheck returned HTTP 401 `invalid x-api-key` |

The static productization gate is therefore
`STATIC_PRODUCTIZATION_READY`. This does not upgrade
`CODEX_LIVE_TRANSPORT_BLOCKED`, intra-runtime effort readiness, or cross-runtime
routing readiness.
