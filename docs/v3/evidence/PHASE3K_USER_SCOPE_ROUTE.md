# Phase 3K User-Scope Dogfood Route

本 route trace 證明 Phase 3K 使用 resident `using-superpowers` authority 與既有
Stage Router / RoutingCatalogSnapshot；它沒有建立新的 runtime adapter、沒有重跑
Stage Router 來決定 user strategy，也沒有把 runtime path 寫回 universal route contract。

## Task route

```text
TaskSpec: qualify USER-scope distribution without real-home apply
  → using-superpowers (resident task/session authority)
  → existing Stage Router / validated RoutingCatalogSnapshot
  → selected procedure bodies only
  → user-scope contract + virtual-home lifecycle fixture
  → symbolic USER preview
  → contract/security/regression verification
```

Runtime/model/live execution was explicitly out of scope. The runtime choice only selected
which existing evidence record to describe; it did not alter skill ranking or route intent.

## Stage emissions

```text
Understand
  SKILLS_SELECTED
  using-superpowers (resident authority)

Design
  SKILLS_SELECTED
  Agent Development; Command Development

Plan
  SKILLS_SELECTED
  codex-engineering-guardrails:code-work
  codex-security:validation

Implement
  SKILLS_SELECTED
  addyosmani-test-driven-development
  codex-engineering-guardrails:code-work

Review
  SKILLS_SELECTED
  addyosmani-code-simplification
  codex-security:validation

Verify
  SKILLS_SELECTED
  codex-engineering-guardrails:code-verification

Live execution
  NO_SKILL_NEEDED(reason=Phase 3K forbids runtime/model invocation)

Handoff
  SKILLS_SELECTED
  using-superpowers; codex-engineering-guardrails:code-verification
```

The selected skill bodies above were loaded only for their procedures. The routing snapshot
continues to validate 214 metadata records with zero canonical `SKILL.md` body reads during
ranking. No full catalog reload was used.

## Route invariants

- `StageRoute` remains the selection authority; user-scope code consumes runtime evidence and
  does not choose a model, effort, provider, permission or skill.
- `RoutingCatalogSnapshot` is immutable for the operation. Its snapshot digest and 214-record
  count are carried into preview source metadata.
- Runtime-specific destinations live in `UserScopeContract`, not in `StageRoute`.
- Native user roots remain symbolic (`${HOME}`, `${XDG_CONFIG_HOME}`, `${CODEX_HOME}`); no
  real-home path is resolved.
- Full-catalog user discovery is represented as lazy derived metadata; execution-specific
  materialization remains selected-only.
- `NO_SKILL_NEEDED` remains a zero selected-body/zero execution-materialization branch.
- The strategy choice is explicit. An unavailable symlink is never silently converted to copy,
  and a requested copy is never silently converted to a link.

## Observed routing defects

No new defect was inferred from this contract-only phase. The existing Phase 3H defect
backlog remains unchanged; this branch did not tune weights, add fixture-specific exceptions,
or repair unrelated metadata selections.

## Evidence outputs

| Output | Role |
|---|---|
| `fixtures/v3/productization/user-scope-contract-v1.json` | symbolic runtime/path/strategy contract |
| `fixtures/v3/productization/user-scope-lifecycle-v1.json` | virtual-home upgrade/collision/symlink examples |
| `tools/v3/user_scope.py` | pure contract validation and preview planner |
| `tools/v3/installer.py` | Phase 3J CLI USER preview and fail-closed apply guard |
| `tests/v3/test_user_scope.py` | focused USER boundary regression tests |
| `docs/v3/evidence/USER_SCOPE_INSTALLATION_V1.md` | evidence and decision report |

## Decision boundary

```text
USER preview = supported as a deterministic productization report
USER apply   = explicitly unauthorized in Phase 3K
PROJECT apply = remains the Phase 3J-only mutation path
GLOBAL apply = preview-only / unsupported
```

This route therefore supports a later, runtime-specific apply contract without claiming that
any current runtime has already passed the user-scope apply gate.
