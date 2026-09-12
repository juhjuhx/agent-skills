# Agent Skills Matrix v3 — Phase 3N USER Apply Route

本 route 記錄 virtual HOME-only 的 Claude USER `MANAGED_COPY` mutation evidence。
它不會把 filesystem lifecycle 當成 live runtime 或 model evidence，也不授權真實
`HOME`。

## Route

```text
using-superpowers (resident authority)
  → Phase 3N contract closure
  → focused TDD boundary tests
  → virtual-home transaction/recovery implementation
  → security validation and simplification review
  → full repository verification
  → sanitized evidence / handoff
```

Active stages emitted `SKILLS_SELECTED` for the resident authority and required
development/testing/security/verification procedures. No Stage Router weights,
runtime adapters, live benchmark code, or routing policy changed in this phase.

## Safety gate

```yaml
runtime: claude-code
qualified_version: 2.1.235
scope: USER
strategy: MANAGED_COPY
home_mode: EXPLICIT_VIRTUAL_ONLY
real_home_apply_authorized: false
runtime_invocation: false
provider_or_auth_access: false
config_mutation: false
```

The generic USER preview remains preview-only for Codex/OpenCode and other
runtimes. Only the Claude virtual target is mutation-capable in this phase.

## Evidence sequence

1. Generic USER package fields and persistent/ephemeral lifecycle checks.
2. Claude runtime fingerprint, contract digest, target-root identity, and exact
   confirmation binding.
3. Full preflight and virtual-root rejection tests.
4. Write-ahead journal with marker-last ownership commit.
5. Single-skill create/reapply/uninstall/reapply.
6. Managed update/backup/revert and manual conflict preservation.
7. Deterministic interruption recovery and journal tamper blocking.
8. Mixed collision and directory-extra-file tests.
9. Full catalog virtual apply; execution selected-only invariant retained.
10. CLI `package`, exact-digest `apply`, `recover`, and preview-only behavior.

## Results

| gate | result |
|---|---|
| generic USER `InstallPackage` | PASS; no Claude-specific package class |
| exact confirmation | PASS; package/root/path-count bound |
| virtual HOME safety | PASS; real-home and alias variants rejected |
| single-skill lifecycle | PASS |
| update / revert / uninstall | PASS; exact bytes and ownership |
| collision handling | PASS; user/synced/ambiguous/bundled fail closed |
| transaction recovery | PASS; `PROCESS_CRASH_RECOVERABLE` |
| full catalog virtual apply | PASS; derived discovery only |
| real-home canary | NOT RUN; forbidden in 3N |
| live runtime/model execution | NOT RUN; out of scope |

## Performance scope

Measured only as bounded filesystem work: single-skill, mixed operation,
recovery scan, lifecycle operations, and full-catalog virtual apply. No model,
provider, token, or runtime-latency metric is claimed. The full catalog stores
metadata/digests and derived `SKILL.md` copies only; it does not serialize a
generated execution prompt or selected bundle.

## Handoff

The next proposal is Phase 3O — Claude real-home canary and clone-to-use UX.
That proposal must start preview-only, require explicit user authorization, use
1–3 zero-collision skills, and verify post-install/uninstall/revert before any
broader deployment. `REAL_HOME_CANARY_VERIFIED` and `FULL_CATALOG_USER_READY`
remain false.

See [`CLAUDE_USER_APPLY_V1.md`](CLAUDE_USER_APPLY_V1.md) and the
[current v3 contract index](../CURRENT_V3_CONTRACT_INDEX.md) for the authoritative
contract boundary.
