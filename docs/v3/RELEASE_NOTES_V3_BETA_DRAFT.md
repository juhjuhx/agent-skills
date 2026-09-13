# Agent Skills Matrix v3 Beta — Release Notes Draft

## Summary

This candidate turns the v3 architecture into a deterministic,
fresh-clone-testable product path: one canonical skill library, validated
metadata-first routing, runtime-native static projections, a safe project
installer, and a Claude-only virtual USER managed-copy lifecycle.

## Included

- `RoutingCatalogSnapshot` and deterministic Stage Router evidence;
- static runtime capability/status reporting and generated projections;
- immutable `InstallationPlan`, `InstallPackage` and `ApplyResult` boundaries;
- explicit PROJECT preview/apply/uninstall/revert with ownership checks;
- Claude Code `2.1.235` virtual USER `MANAGED_COPY` package/apply/recover/upgrade/
  uninstall/revert lifecycle;
- exact package confirmation and digest-bound process-crash recovery;
- read-only `status`, `doctor`, `explain` and bounded Claude canary preview;
- fresh-clone onboarding and repository CI regression workflow.
- autonomous stabilization evidence: fail-closed ASM user-data resolution,
  retired-preview protection, actionable diagnostics and final exact-digest
  canary handoff.

## Limitations

- no real-home install is included in this candidate;
- no provider, auth, model inference, MCP, plugin, hook or runtime-config mutation;
- Codex live transport is blocked and effort-routing readiness remains NOT_READY;
- Codex/OpenCode USER scope and Hermes adapter remain preview/status-only;
- full-catalog real-user rollout has not been validated or authorized.
- the current one-skill real-home preview is ready for a separate explicit
  authorization gate, but this candidate does not consume that authorization.

## Safety posture

The candidate fails closed on stale packages, unknown ownership, user-owned and
synced collisions, path traversal, symlink escape, cross-scope/runtime replay and
tampered recovery journals. The virtual transaction guarantee is
`PROCESS_CRASH_RECOVERABLE`; it is not a claim of cross-platform power-loss
atomicity.

Publication and real-user installation require separate explicit authority.
