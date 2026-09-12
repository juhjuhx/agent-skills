# Phase 3L Claude User-Scope Native Discovery Qualification Route

## Route record

| Field | Value |
|---|---|
| phase | `3L` |
| branch | `feat/v3-claude-user-contract` |
| base | `feat/v3-user-scope-contract` |
| starting HEAD | `8ba23daed5e3ef13c6aceea218609c45518d88b7` |
| task | qualify Claude Code 2.1.235 personal skill discovery |
| active stage result | `SKILLS_SELECTED` |
| live execution | `RUNTIME_BLOCKED` carried forward; no retry |
| user apply | `false` |

Resident `using-superpowers` authority remained active. The implementation,
security-validation, test-first, command/CLI seam, and simplification procedures
were selected before work. No Stage Router weights or runtime adapter contracts
were changed.

## Scope and evidence order

```text
repo truth
  → claude --version
  → local artifact fingerprint
  → non-inference static discovery inspection
  → official release/current-doc comparison
  → virtual-home lifecycle model
  → pure preview/tests
  → security and regression verification
```

`claude --version` returned `2.1.235 (Claude Code)`. The executable is a
versioned arm64 Mach-O with SHA-256
`sha256:83b8f806f6f2eea316cfe246628e6c23374711d868f1fd0409db551b877b7748`.
No `claude -p` or other inference surface was invoked.

## Installed artifact inspection

The local binary was scanned only for small contract indicators. Exact personal
and project `.claude/skills` strings, synced-skill labels, source-scope labels,
and generic symlink helpers were present. This is sufficient to bind the root
presence to the exact installed artifact, but not to claim full installed
precedence/symlink behavior. Those fields stay `CURRENT_DOC_SUPPORTED` or
`UNKNOWN` in the contract fixture.

No raw bundle content was persisted. The evidence stores only the artifact digest,
path/package class, bounded counts, and a source-location label
`embedded-runtime-strings@2.1.235`.

## Contract result

| Surface | Result |
|---|---|
| personal root | `INSTALLED_RUNTIME_VERIFIED` for root presence; no end-to-end inference |
| project root | `INSTALLED_RUNTIME_VERIFIED` for root presence |
| precedence | `CURRENT_DOC_SUPPORTED`, future-apply warning required |
| bundled collision | `CURRENT_DOC_SUPPORTED`, `CONFLICT_REQUIRES_CONFIRMATION` |
| synced collision | preserve `CLAUDE_SYNCED`; ASM ownership false |
| directory symlink | `CURRENT_DOC_SUPPORTED`, not selected |
| file symlink | `UNSUPPORTED_FOR_APPLY` |
| parent-directory symlink | `NOT_SUPPORTED` |
| chosen strategy | `MANAGED_COPY_PREFERRED` |
| contract decision | `CLAUDE_USER_CONTRACT_READY` |

## Virtual-home cases

Only temporary fixture roots were used in tests. The lifecycle contract covers:

```text
PERSONAL_ONLY
PROJECT_ONLY
PERSONAL_AND_PROJECT_SAME_NAME
DIFFERENT_NAMES
```

and collision states:

```text
ABSENT / ASM_MANAGED / CLAUDE_SYNCED / USER_OWNED
PROJECT_DUPLICATE / BUNDLED_COLLISION / AMBIGUOUS / UNKNOWN
```

The future installer must not adopt, rename, overwrite, or deduplicate a user or
project skill automatically. Managed-copy upgrade states are `UNCHANGED`,
`ADDED`, `CONTENT_UPDATED`, `REMOVED`, `EXPLICIT_RENAMED`,
`USER_MODIFIED_CONFLICT`, `OWNERSHIP_LOST`, and `STRATEGY_CHANGED`. Rename is
accepted only with explicit provenance. Missing exact backup bytes make revert
`REVERT_UNAVAILABLE`.

## Files changed

- `tools/v3/claude_user_scope.py`: pure contract loader, evidence projection,
  slug safety, lifecycle classifiers, explicit offline size measurement;
- `tools/v3/installer.py`: Claude user preview uses the Claude projection while
  the existing USER apply guard remains unchanged;
- `fixtures/v3/productization/claude-user-scope-contract-v1.json`;
- `fixtures/v3/productization/claude-user-distribution-strategy-v1.json`;
- `fixtures/v3/productization/claude-user-lifecycle-v1.json`;
- `tests/v3/test_claude_user_scope.py`;
- `docs/v3/evidence/CLAUDE_USER_SCOPE_V1.md`;
- `docs/v3/NEXT_CODEX_PROMPT.md`.

## Verification record

| Check | Result |
|---|---|
| focused Claude contract tests | `20/20 PASS` |
| changed-file ruff | `PASS` |
| changed-file format check | `PASS` after formatting |
| compile check | `PASS` |
| diff check | `PASS` |
| full repository suite | `363/363 PASS` |
| real-home write | not attempted; forbidden |
| Claude inference | not attempted; forbidden |
| OCR | `401 Unauthorized`; `OCR_NATIVE_DIFF=BLOCKED_BY_AUTH` |

## Next proposal

Because the static contract is ready but apply is intentionally not authorized,
the only sensible next implementation phase is:

```text
PHASE 3M — CLAUDE USER-SCOPE APPLY MVP
```

Claude-only, managed-copy-only, explicit preview/confirmation/apply, virtual-home
first, no runtime config mutation, and no implication that Claude live execution
or cross-runtime routing is ready.
