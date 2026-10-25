#!/usr/bin/env python3
"""Reference implementation: flag single-point-of-failure escalation policies.

Given exported PagerDuty escalation policy JSON (as returned by
`GET /escalation_policies/{id}?include[]=targets`, with each schedule
already expanded to its list of member user IDs), this checks:

  1. Every escalation rule resolves to at least one target.
  2. Across all rungs, at least two *distinct* users are reachable —
     a policy where every rung ultimately resolves to the same one
     person is a single point of failure even if it "looks" like a
     multi-rung policy.
  3. No rung's resolved user set is a subset of size 1 unless a later
     rung introduces someone new.

This is a starting point for a CI check or a scheduled audit job, not a
full PagerDuty/Opsgenie client — adapt the `load_policy` stub to call the
real API (PAGERDUTY_API_TOKEN / OPSGENIE_API_KEY from the environment,
never hardcoded).
"""
import json
import sys
from typing import Any


def resolve_rung_users(rung: dict[str, Any]) -> set[str]:
    """Flatten a rung's targets (users and expanded schedule members) to user IDs."""
    users: set[str] = set()
    for target in rung.get("targets", []):
        if target.get("type") == "user_reference":
            users.add(target["id"])
        elif target.get("type") == "schedule_reference":
            # Expected to be pre-expanded by the caller with a "members" list.
            users.update(target.get("members", []))
    return users


def check_policy(policy: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    name = policy.get("name", "<unnamed policy>")
    rules = policy.get("escalation_rules", [])

    if not rules:
        findings.append(f"{name}: no escalation rules defined at all.")
        return findings

    all_users_seen: set[str] = set()
    for i, rung in enumerate(rules, start=1):
        rung_users = resolve_rung_users(rung)
        if not rung_users:
            findings.append(f"{name}: rung {i} resolves to zero users (broken target).")
            continue
        new_users = rung_users - all_users_seen
        if i > 1 and not new_users:
            findings.append(
                f"{name}: rung {i} adds no new humans beyond earlier rungs "
                f"({sorted(rung_users)}) — escalation would loop back to the "
                "same person/people instead of reaching someone new."
            )
        all_users_seen |= rung_users

    if len(all_users_seen) < 2:
        findings.append(
            f"{name}: only {len(all_users_seen)} distinct human(s) reachable "
            "across the entire policy — single point of failure. Add a "
            "genuinely independent secondary or manager rung."
        )

    if policy.get("num_loops", 0) == 0:
        findings.append(
            f"{name}: num_loops is 0 — an unacknowledged page will not repeat "
            "the escalation chain. Set num_loops >= 1 for anything Sev1/Sev2-capable."
        )

    return findings


def load_policy(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_escalation_coverage.py <policy.json> [<policy.json> ...]", file=sys.stderr)
        return 2

    total_findings = 0
    for path in sys.argv[1:]:
        policy = load_policy(path)
        findings = check_policy(policy)
        if findings:
            print(f"FAIL  {path}")
            for f in findings:
                print(f"  - {f}")
            total_findings += len(findings)
        else:
            print(f"OK    {path}")

    return 1 if total_findings else 0


if __name__ == "__main__":
    sys.exit(main())
