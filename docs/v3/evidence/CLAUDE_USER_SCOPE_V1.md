# Claude Code User-Scope Discovery Contract V1

本文件是 Phase 3L 的 Claude-only 使用者範圍資格證據。它只資格化未來
`~/.claude/skills` 的發現與生命週期契約；不實作 USER apply、不執行 Claude
inference，也不改動 `settings.json`、`CLAUDE.md`、MCP、plugin、hook 或權限。

## Decision

```yaml
runtime: claude-code
version: 2.1.235
contract_status: CLAUDE_USER_CONTRACT_READY
distribution_strategy: MANAGED_COPY_PREFERRED
apply_authorized: false
live_execution: RUNTIME_BLOCKED
```

`CLAUDE_USER_CONTRACT_READY` 只表示未來可以針對 Claude、針對這個已證明的
策略另立 apply phase；它不授權本 phase 寫入 user home。`DIRECTORY_SYMLINK`
保留為文件支援但未完成 installed-behavior proof，沒有被當成 apply strategy。

## Installed artifact

唯一執行的 runtime probe 是 `claude --version`，結果為 `2.1.235 (Claude Code)`。
沒有執行 `claude -p`、prompt、auth、keychain 或 provider 命令。

| Field | Evidence |
|---|---|
| runtime ID | `claude-code` |
| installed version | `2.1.235` / `INSTALLED_RUNTIME_VERIFIED` |
| package type | versioned standalone arm64 Mach-O executable |
| path class | user-local bin symlink → user-local version directory |
| executable size | `313334608` bytes |
| executable SHA-256 | `sha256:83b8f806f6f2eea316cfe246628e6c23374711d868f1fd0409db551b877b7748` |
| release tag | `v2.1.235` / `RELEASE_SUPPORTED` |
| release publication | 2026-08-18 20:38 (GitHub release page) |
| page-visible release ref | `c3d2e35` |
| full immutable source ref | `UNKNOWN`; no source package is shipped with the local executable and remote tag resolution was unavailable in the sandbox |
| verification method | `claude --version`, local `file`/size/hash, static string-count inspection, versioned release page |

The local binary was inspected only for contract-relevant strings. Counts were
recorded as ephemeral corroboration, not as a dumped source artifact:

```text
.claude/skills=104   ~/.claude/skills=23   syncedSkills=89
projectSettings=243  userSettings=413      symlink=947
readlink=128         realpath=545
```

This makes the personal/project/synced/symlink surfaces observable in the exact
installed artifact. It does not by itself prove every precedence or lifecycle
branch; those remain separately classified below.

## Current docs vs release vs installed artifact

The official current skills documentation describes personal and project skill
locations, enterprise/personal/project precedence, directory symlink behavior,
bundled collision behavior, and the reserved `synced` directory. Those claims
are not silently promoted to release- or artifact-level proof.

| Claim | CURRENT_DOC | RELEASE_2_1_235 | INSTALLED_ARTIFACT | FINAL_SUPPORT |
|---|---|---|---|---|
| personal path `${HOME}/.claude/skills/<name>/SKILL.md` | `CURRENT_DOC_SUPPORTED` | `UNKNOWN` | `INSTALLED_RUNTIME_VERIFIED` (exact path strings) | `INSTALLED_RUNTIME_VERIFIED` |
| project path `${PROJECT}/.claude/skills/<name>/SKILL.md` | `CURRENT_DOC_SUPPORTED` | `UNKNOWN` | `INSTALLED_RUNTIME_VERIFIED` (project discovery strings) | `INSTALLED_RUNTIME_VERIFIED` |
| enterprise > personal > project | `CURRENT_DOC_SUPPORTED` | `UNKNOWN` | `UNKNOWN` | `CURRENT_DOC_SUPPORTED` + warning |
| personal/project directory symlink | `CURRENT_DOC_SUPPORTED` | `UNKNOWN` | `UNKNOWN` (generic link helpers only) | `CURRENT_DOC_SUPPORTED` + not selected |
| `SKILL.md` file symlink | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNSUPPORTED_FOR_APPLY` |
| bundled same-name collision | `CURRENT_DOC_SUPPORTED` | `UNKNOWN` | `UNKNOWN` | `CURRENT_DOC_SUPPORTED` + confirmation required |
| synced same-name collision / reserved `synced` | `CURRENT_DOC_SUPPORTED` | `UNKNOWN` | `INSTALLED_RUNTIME_VERIFIED` (synced surface) | `CURRENT_DOC_SUPPORTED` + preserve |

The release tag and date are supported by the official
[Claude Code v2.1.235 release page](https://github.com/anthropics/claude-code/releases/tag/v2.1.235).
The current path and collision semantics are supported by the official
[Claude Code skills documentation](https://code.claude.com/docs/en/skills), but
the table keeps their evidence class visible.

## Native roots and collision semantics

```text
personal: ${HOME}/.claude/skills
project:  ${PROJECT}/.claude/skills
synced:   ${HOME}/.claude/skills/synced   (Claude-owned; ASM never owns it)
ASM data: ${ASM_USER_DATA}/v3/claude     (derived, managed, non-canonical)
```

The future installer must distinguish these exact states for every slug:

```text
ABSENT | ASM_MANAGED | CLAUDE_SYNCED | USER_OWNED
PROJECT_DUPLICATE | BUNDLED_COLLISION | AMBIGUOUS | UNKNOWN
```

- `USER_OWNED`, `AMBIGUOUS`, and `UNKNOWN` never become adoption or overwrite.
- `CLAUDE_SYNCED` is preserved; ASM does not write below `synced/`.
- `BUNDLED_COLLISION` requires bounded confirmation; no silent override.
- Personal/project same-name skills remain independent. The documented order is
  enterprise > personal > project, but future apply must display a warning until
  version-bound behavior is independently exercised.
- Project-to-user migration is two independent transactions, never an implicit
  move or project deletion.

## Strategy qualification

| Strategy | Claude discovery evidence | macOS | Linux | Windows | Lifecycle verdict |
|---|---|---|---|---|---|
| `MANAGED_COPY` | installed personal-root evidence | `SUPPORTED_WITH_PRECONDITION` | `SUPPORTED_WITH_PRECONDITION` | `SUPPORTED_WITH_PRECONDITION` | preferred; exact digest/ownership required |
| `DIRECTORY_SYMLINK` | `CURRENT_DOC_SUPPORTED` | `SUPPORTED_WITH_PRECONDITION` | `SUPPORTED_WITH_PRECONDITION` | `UNKNOWN` | preview only; target/repository relocation must be revalidated |
| `FILE_SYMLINK` | `UNSUPPORTED_FOR_APPLY` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | never infer from directory-link support |
| `PARENT_DIRECTORY_SYMLINK` | `NOT_SUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | must not capture user-owned skills parent |

The selected strategy is:

```text
MANAGED_COPY_PREFERRED
canonical skills/<skill>/SKILL.md
  → ${ASM_USER_DATA}/v3/claude (stable derived store)
  → ${HOME}/.claude/skills/<slug>/SKILL.md (future, explicit apply only)
```

The copy remains derived and regenerable. A source digest and installed digest
are bound in a future manifest. Manual modification is `CONFLICT`; upgrade and
removal only operate on exact, still-ASM-managed, unchanged artifacts. No change
is synchronized back into canonical `skills/`.

The stable ASM data store is preferred over a direct link into a git checkout:
repo move/delete, branch changes, reset, and canonical source removal cannot be
silently treated as a valid unchanged target. A future link strategy must report
`BOUND`, `TARGET_DIGEST_CONFLICT`, `BROKEN_TARGET`, or
`REPOSITORY_RELOCATION_REQUIRES_REVALIDATION` before mutation.

## Slug and platform safety

`tools/v3/claude_user_scope.py` normalizes to NFC, rejects separators/control
characters/path traversal, maps unsafe naming punctuation deterministically, and
fails on destination collisions. It separately rejects case-fold collisions,
Unicode-normalization collisions, and Windows reserved names (`CON`, `NUL`,
`COM1`…`LPT9`, including extensions). It never silently changes a requested
copy into a symlink or vice versa.

OS results are contract records, not privileged probes. Windows symlink capability
is `UNKNOWN` and does not block the copy strategy; no administrator or developer
mode is assumed. User-owned parent directories are never owned merely because a
child was considered for distribution.

## Discovery vs execution

The personal Claude root may eventually contain a complete derived lazy-discovery
catalog. That is separate from execution materialization:

- user discovery: full catalog entries may be derived and lazily loaded by Claude;
- Agent Skills Matrix execution: only StageRoute-selected procedures are loaded;
- `NO_SKILL_NEEDED`: zero skill bodies are materialized.

The Phase 3L preview kept `catalog_body_files_loaded=0` and
`body_files_materialized=0`. The explicit offline size measurement read source
bytes only to calculate distribution cost and returned no body content:

```text
skills: 214
SKILL.md bytes: 2,155,285
supporting-file bytes: 0
managed-copy bytes: 2,155,285
directory-symlink entries: 0 (preferred strategy)
```

## Security and scope

- no real HOME access or write;
- no Claude inference or runtime process beyond `--version`;
- no auth, credential, keychain, provider, environment, MCP, plugin, hook, or config read;
- no settings/CLAUDE.md mutation;
- no user-owned, synced, bundled, or parent-directory overwrite;
- no path traversal or symlink escape;
- USER apply remains `USER_SCOPE_APPLY_NOT_AUTHORIZED`;
- live `RUNTIME_BLOCKED` remains orthogonal to this static discovery contract.

## Future gate

The next action, if user-scope value is required, is a Claude-only
`PHASE 3M — CLAUDE USER-SCOPE APPLY MVP` using only `MANAGED_COPY`, explicit
preview/confirmation/apply, Phase 3J transaction/revalidation semantics, and a
virtual-home test matrix before any real user-home opt-in. No Codex/OpenCode
user apply is implied.
