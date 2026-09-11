# Phase 3I Productization Dogfood Route

本文件是本 phase 的 route trace。它證明 productization 使用目前 Stage Router
產出的 route，而不是在 compiler 內重新選技能。

## Route

```text
TaskSpec (B-ordinary-bug)
  → existing StageRouter
  → StageRoute
  → selected-only references
  → optional CompiledExecutionBundle reference
  → Codex / Claude Code / OpenCode static projection
```

| 欄位 | 值 |
|---|---|
| development fixture | `B-ordinary-bug` |
| stage | `implement` |
| route ID | `route:T-router-B-ordinary-bug:implement:14d41f3d0aa00a88` |
| route digest | `sha256:1c1b1e046606f193d3eed067229885b59baccf0993e0e63f4d1c4b3350ff2bce` |
| snapshot | `snapshot:87dc6a8790b10450` |
| selected-only body load during routing | 0 |
| route reselection in compiler | false |

Selected roles were:

| Skill | Role | Delivery |
|---|---|---|
| `using-superpowers` | `GATE` | resident reference; no body reload |
| `diagnose` | `PROCESS` | reference; body only if explicit materialization |
| `tdd` | `PROCESS` | reference; body only if explicit materialization |
| `verification-before-completion` | `VERIFY` | reference; body only if explicit materialization |

The compiler then made the same route portable to each runtime that has a verified
static adapter contract. Runtime-specific status/projection narrowed what can be
represented; it did not alter StageRoute intent.

## Stage outputs

```text
SKILLS_SELECTED
  selected IDs: diagnose, tdd, using-superpowers,
                verification-before-completion
  downstream body loading: selected-only / opt-in

NO_SKILL_NEEDED
  selected IDs: none
  downstream body loading: zero
```

The `NO_SKILL_NEEDED` branch is covered by the same compiler tests and does not
generate a fake skill. The resident `using-superpowers` authority is represented as
resident metadata rather than copied into every output.

## Runtime projections

| Runtime | Static route artifact | Live status | Interpretation |
|---|---|---|---|
| Codex | generated | `TRANSPORT_BLOCKED` | static support only; no live claim |
| Claude Code | generated | `RUNTIME_BLOCKED` | read-only static support only |
| OpenCode | generated | `PROVIDER_BLOCKED` | read-only boundary preserved |
| Hermes | none | `PROVIDER_BLOCKED` | adapter not implemented; status only |

## Safety trace

- `RoutingCatalogSnapshot` is validated once for the operation and records 214
  metadata entries with zero ranking body reads.
- Existing `StageRoute` is validated against the snapshot epoch and trust state.
- Optional bundle references are checked against route ID, registry epoch and adapter
  runtime ID.
- Projection fields contain no credentials, model preference, effort policy or
  authority grant.
- Compile output is explicit temporary/project-local output only; global runtime
  locations are rejected.
- No runtime executable, model, provider, MCP server or plugin was invoked.

Machine-readable companion:
[`static-conformance-v1.json`](../../../fixtures/v3/productization/static-conformance-v1.json).
