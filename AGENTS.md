<!-- using-superpowers:start -->
## using-superpowers v3 routing bootstrap

1. Treat `.superpowers/SKILLS_INDEX.json` as the machine-readable skill truth; use `categories.json` only as the installer projection.
2. Classify the task by risk, complexity, ambiguity, required capabilities, permissions, and budget.
3. Create a portable `TaskSpec` with assumptions, unknowns, outputs, acceptance criteria, and stop conditions.
4. Create only the relevant stages: Understand, Research, Design, Plan, Implement, Review, Verify, Harden, Handoff/Learn.
5. Route skills independently per stage using the role slots `GATE`, `PROCESS`, `DOMAIN`, `TOOL`, `REVIEW`, and `VERIFY`.
6. Load only selected `SKILL.md` files and required references/scripts, on demand.
7. Use the native agent adapter; keep agent runtime identity separate from model/provider profiles.
8. Require an evidence gate before advancing or claiming completion; reroute only at a declared stage boundary or evidence failure.
9. Record major runs, route reasons, artifacts, evaluations, and user corrections without exposing private chain-of-thought.
10. Do not load historical docs or full catalogs by default; follow links only when the current stage requires them.

No minimum skill quota is imposed. Do not load unrelated skills to satisfy a number. Keep this file small: it is a router bootstrap, not the full architecture specification.

See `docs/v3/README.md` for the v3 contracts and `docs/using-superpowers-v2-extensible-architecture.md` for historical v2 context. Follow `.superpowers/ROUTING_POLICY.yaml` until a future implementation explicitly supersedes it.
<!-- using-superpowers:end -->
