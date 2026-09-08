"""Small evidence gate used by adapter preparation.

The gate reports observable missing evidence and a reroute hint. It does not
execute a router and cannot grant permissions.
"""

from __future__ import annotations

from typing import Any


def evaluate_evidence(
    required: list[str] | tuple[str, ...], observed: list[Any] | None
) -> dict[str, Any]:
    """Compare required evidence names with observed evidence records."""

    required_names = list(dict.fromkeys(str(item) for item in required))
    if observed is None:
        return {
            "status": "PENDING",
            "missing": required_names,
        }

    observed_names: set[str] = set()
    for item in observed:
        if isinstance(item, str):
            observed_names.add(item)
        elif isinstance(item, dict):
            for key in ("name", "type", "evidence_type"):
                value = item.get(key)
                if isinstance(value, str):
                    observed_names.add(value)
                    break

    missing = [name for name in required_names if name not in observed_names]
    if not missing:
        return {"status": "PASS", "missing": []}
    return {
        "status": "BLOCKED",
        "missing": missing,
        "reroute": {
            "trigger": "evidence_failure",
            "next_stage": "verify",
            "reason": "Required evidence is missing; completion remains blocked.",
        },
    }
