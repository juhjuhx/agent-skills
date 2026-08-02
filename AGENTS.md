<!-- using-superpowers:start -->
## using-superpowers routing contract

Treat `.superpowers/SKILLS_INDEX.json` as the current machine-readable skill registry.
Before execution, resolve the request into intent, risk, required capabilities, and a token budget.
Use the registry to select the smallest sufficient skill set; load full SKILL.md instructions only after selection.
For new or changed skills, update the registry through the sync script and validate the generated snapshot.
Follow `.superpowers/ROUTING_POLICY.yaml` for preflight, permissions, state transitions, and budget limits.
Use GrillMe-style questioning only for material ambiguity; otherwise make a bounded, explicit assumption.
Keep generated artifacts and state external to individual agents so other runtimes can consume them.
See `docs/using-superpowers-v2-extensible-architecture.md` for the cross-agent and cloud contract.
<!-- using-superpowers:end -->
