# Phase 3O.1 — Canary Authorization Closure Route

## Route

```text
Phase 3O historical blocked preview
        ↓ invalidate old package / confirmation / preview digests
generic ASM user-data resolver (read-only)
        ↓ macOS root + parent + managed-subroot identity
installed Claude 2.1.235 artifact fingerprint check
        ↓ bounded exact-token scan
known bundled identifier + registry-marker calibration
        ↓ candidate-specific module-map proof
fresh real-home inventory (read-only)
        ↓ personal/synced/project ABSENT; unknown = 0
fresh generic USER package (MANAGED_COPY, non-authorizing)
        ↓ fresh package + confirmation + preview digests
CLAUDE_REAL_HOME_CANARY_READY_FOR_USER_AUTH
        ↓ STOP; no mutation
```

## Closed blockers

### A — ASM user-data destination

`tools/v3/asm_user_data.py` now owns a reusable platform-aware resolver. On the
current macOS host it resolves the symbolic contract to the native Application
Support domain, observed as `EXPECTED_ABSENT`. It checks parent chain symlink safety,
repository/runtime exclusion, root state and path-free identity. Revalidation compares
the exact root/parent/home identity, expected state and contract digest.

### B — candidate bundled collision

The installed Claude Code artifact remains fingerprint
`sha256:83b8f806f6f2eea316cfe246628e6c23374711d868f1fd0409db551b877b7748`.
The bounded scanner recovered `claude-code-guide` plus all four bundled registry
markers. Only after that calibration did `module-map` absence become
`BUNDLED_COLLISION_NONE_VERIFIED`.

No global bundled inventory is claimed; other skill slugs require their own proof.

## Final gate

`CLAUDE_REAL_HOME_CANARY_READY_FOR_USER_AUTH` is a preparation result only. The
package is still `installable=false`, `apply_allowed=false`, and `consumable=false`.
The next phase may not execute without an explicit human authorization for the exact
fresh digest pair.

## Carry-forward

```yaml
CLONE_TO_USE_UX_READY: true
CODEX_LIVE_TRANSPORT_BLOCKED: true
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
REAL_HOME_CANARY_VERIFIED: false
FULL_CATALOG_USER_READY: false
```

The next proposal is Phase 3P, limited to the exact one-skill package above and still
requiring an explicit user authorization. It is not executed by this route.
