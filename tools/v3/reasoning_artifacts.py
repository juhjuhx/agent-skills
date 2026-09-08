"""Validation for observable cross-runtime reasoning artifacts.

The v3 boundary carries decisions and evidence, never private model traces.
"""

from __future__ import annotations

from typing import Any


OBSERVABLE_ARTIFACTS = frozenset(
    {
        "TaskSpec",
        "Assumptions",
        "Unknowns",
        "DecisionRecord",
        "StagePlan",
        "Alternatives",
        "Evidence",
        "Risk",
        "Verification",
        "LearningProposal",
    }
)

FORBIDDEN_REASONING_KEYS = frozenset(
    {
        "chain_of_thought",
        "private_reasoning",
        "scratchpad",
        "hidden_reasoning",
    }
)


def validate_reasoning_artifacts(value: Any) -> list[str]:
    """Return paths of forbidden hidden-reasoning keys, recursively."""

    errors: list[str] = []

    def visit(item: Any, path: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key in FORBIDDEN_REASONING_KEYS:
                    errors.append(f"{path}.{key}: hidden reasoning is not portable")
                visit(child, f"{path}.{key}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")

    visit(value, "$")
    return errors


def artifact_refs(artifacts: dict[str, Any] | None) -> list[str]:
    """Return stable references for supplied observable artifacts."""

    if not artifacts:
        return []
    errors = validate_reasoning_artifacts(artifacts)
    if errors:
        raise ValueError("; ".join(errors))
    unknown = sorted(set(artifacts) - OBSERVABLE_ARTIFACTS)
    if unknown:
        raise ValueError(f"unsupported reasoning artifact names: {', '.join(unknown)}")
    return sorted(artifacts)
