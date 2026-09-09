"""Small in-memory relationship helpers for stage-local routing.

The graph is deliberately a view over the supplied metadata records. It does
not persist a registry, mutate source records, or load SKILL.md bodies.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


POSITIVE_RELATIONSHIPS = frozenset(
    {"RECOMMENDS", "COMPLEMENTS", "REVIEW_WITH", "VERIFY_WITH"}
)
RELATIONSHIPS = frozenset(
    {
        "REQUIRES",
        "RECOMMENDS",
        "COMPLEMENTS",
        "CONFLICTS",
        "SUPERSEDES",
        "ALTERNATIVE_TO",
        "REVIEW_WITH",
        "VERIFY_WITH",
    }
)


class SkillGraph:
    """Index directed skill relationships for one routing invocation."""

    def __init__(self, records: Iterable[dict[str, Any]]) -> None:
        self.records = {
            record["skill_id"]: record
            for record in records
            if isinstance(record, dict) and isinstance(record.get("skill_id"), str)
        }
        self._edges: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        for source, record in self.records.items():
            for relationship in record.get("relationships", []) or []:
                if not isinstance(relationship, dict):
                    continue
                relation_type = relationship.get("type")
                target = relationship.get("target")
                if relation_type in RELATIONSHIPS and isinstance(target, str):
                    self._edges[source][relation_type].add(target)

    def targets(self, source: str, relation_type: str) -> tuple[str, ...]:
        return tuple(sorted(self._edges.get(source, {}).get(relation_type, set())))

    def required_dependencies(self, source: str) -> tuple[str, ...]:
        """Return transitive REQUIRES dependencies in deterministic order."""

        ordered: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(skill_id: str) -> None:
            if skill_id in visiting:
                raise ValueError(
                    f"REQUIRES cycle encountered while routing: {skill_id}"
                )
            if skill_id in visited:
                return
            visiting.add(skill_id)
            for dependency in self.targets(skill_id, "REQUIRES"):
                if dependency not in self.records:
                    raise KeyError(
                        f"required dependency is missing from the catalog: {skill_id} -> {dependency}"
                    )
                visit(dependency)
                if dependency not in ordered:
                    ordered.append(dependency)
            visiting.remove(skill_id)
            visited.add(skill_id)

        visit(source)
        return tuple(ordered)

    def superseded_ids(self, available_ids: set[str]) -> dict[str, str]:
        """Map a candidate to an available successor that supersedes it."""

        result: dict[str, str] = {}
        for successor in sorted(available_ids):
            for legacy in self.targets(successor, "SUPERSEDES"):
                if legacy in available_ids:
                    result.setdefault(legacy, successor)
        return result

    def conflicts(self, first: str, second: str) -> bool:
        return second in self._edges.get(first, {}).get(
            "CONFLICTS", set()
        ) or first in self._edges.get(second, {}).get("CONFLICTS", set())

    def alternatives(self, first: str, second: str) -> bool:
        return second in self._edges.get(first, {}).get(
            "ALTERNATIVE_TO", set()
        ) or first in self._edges.get(second, {}).get("ALTERNATIVE_TO", set())

    def positive_effects(
        self, candidate: str, selected: Iterable[str]
    ) -> tuple[float, tuple[str, ...]]:
        """Return a small contextual bonus and observable relationship notes."""

        selected_ids = set(selected)
        bonus = 0.0
        effects: list[str] = []
        for selected_id in sorted(selected_ids):
            for relation_type in sorted(POSITIVE_RELATIONSHIPS):
                forward = selected_id in self._edges.get(candidate, {}).get(
                    relation_type, set()
                )
                reverse = candidate in self._edges.get(selected_id, {}).get(
                    relation_type, set()
                )
                if forward or reverse:
                    bonus += 1.0
                    effects.append(f"{relation_type}:{candidate}<->{selected_id}")
        return bonus, tuple(sorted(set(effects)))
