# Agent Skills Matrix v3 — Beta Capability Matrix

| capability | status | supported boundary | not claimed |
|---|---|---|---|
| canonical 214-skill catalog | READY | one canonical `SKILL.md` source plus validated metadata | generated copies as canonical source |
| Stage Router | PRODUCTION_READY | deterministic stage routes, metadata-first, selected-only downstream loading | model/effort routing |
| Codex static projection | STATIC_READY | static contract and project productization | live transport / effort evidence |
| Claude static projection | STATIC_READY | read-only/runtime-native projection contract | live execution readiness |
| OpenCode static projection | STATIC_READY | read-only projection with permission boundary | USER apply / provider readiness |
| Hermes | STATUS_ONLY | qualification evidence and honest status | fake adapter/distribution |
| PROJECT install | READY | explicit project root, managed generated files, reversible lifecycle | user/global config merge |
| Claude virtual USER | READY | `2.1.235`, `MANAGED_COPY`, virtual HOME + virtual ASM root | real HOME mutation |
| Claude real-home canary | READY_FOR_EXACT_USER_AUTH | bounded one-skill `module-map` preview; package and confirmation are exact-digest bound | canary verified / full catalog |
| recovery | VERIFIED | process-crash recovery with journal and bounded rollback | power-loss durability guarantee |
| clone-to-use façade | READY | Python module CLI with status/doctor/explain/lifecycle verbs | daemon/TUI/web service |
| live runtime execution | BLOCKED/SEPARATE | historical evidence only | new live benchmark in this epoch |

## Final stabilization boundary

The candidate is `BETA_CANDIDATE_STABLE=true` for non-privileged repository,
static productization, PROJECT installation and virtual Claude USER validation.
The exact canary package is still non-authorizing and has not changed the
following independent states:

```yaml
REAL_HOME_APPLY_AUTHORIZED: false
REAL_HOME_CANARY_VERIFIED: false
FULL_CATALOG_USER_READY: false
CODEX_LIVE_TRANSPORT_STATUS: CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
```

## Status dimensions

Installation availability, adapter support, static contract, live execution, and
routing readiness are independent. `BLOCKED` live transport does not erase a
valid static adapter; virtual USER readiness does not authorize real HOME.
