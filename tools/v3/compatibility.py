"""Read-only projections from the current v1 registry into v3 metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CURRENT_FIELD_MAPPING = {
    "skill_id": "DIRECT",
    "name": "DIRECT",
    "description": "DIRECT",
    "triggers": "DIRECT",
    "source.repo": "DIRECT",
    "source.ref": "DIRECT",
    "source.path": "DIRECT",
    "source.digest": "DERIVED",
    "source.license": "UNAVAILABLE",
    "source.import_date": "UNAVAILABLE",
    "trust": "DERIVED",
    "stages": "UNAVAILABLE",
    "roles": "UNAVAILABLE",
    "task_modes": "UNAVAILABLE",
    "domains": "UNAVAILABLE",
    "current_categories": "DIRECT",
    "legacy_deprecation": "DEPRECATED",
}


def import_skill_index_entry(
    entry: dict[str, Any], registry_document: dict[str, Any]
) -> dict[str, Any]:
    """Project one current SKILLS_INDEX entry without migrating the registry.

    Fields that the old registry does not contain are omitted rather than
    filled with guessed provenance. Category tags remain an extension because
    they are installer/registry projections, not v3 domains or stages.
    """

    required = ("id", "name", "description", "relative_path", "sha256")
    missing = [field for field in required if field not in entry]
    if missing:
        raise ValueError(f"current registry entry is missing: {', '.join(missing)}")

    source = {
        "repo": registry_document["source"],
        "ref": registry_document.get("source_ref", "unknown"),
        "path": entry["relative_path"],
        "digest": _normalise_digest(entry["sha256"]),
    }
    projected: dict[str, Any] = {
        "schema_version": "3.0",
        "skill_id": entry["id"],
        "name": entry["name"],
        "description": entry["description"],
        "source": source,
        # The source is the repository's canonical index. This is a policy
        # projection, not a claim that the old record carried a trust field.
        "trust": "CORE_TRUSTED",
        "triggers": entry.get("triggers", []),
        "extensions": {
            "compatibility": {
                "source_schema": registry_document.get("schema_version"),
                "current_categories": entry.get("categories", []),
                "unavailable_fields": [
                    "source.license",
                    "source.import_date",
                    "stages",
                    "roles",
                    "task_modes",
                    "domains",
                ],
                "field_status": CURRENT_FIELD_MAPPING,
            }
        },
    }
    if entry["description"].lstrip().lower().startswith("[deprecated:"):
        projected["extensions"]["compatibility"]["legacy_status"] = "DEPRECATED"
    return projected


def load_current_registry(path: str | Path) -> dict[str, Any]:
    """Load the current registry for read-only compatibility checks."""

    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        registry = json.load(handle)
    if not isinstance(registry, dict) or not isinstance(registry.get("skills"), list):
        raise ValueError(f"invalid current registry: {path}")
    return registry


def import_current_skill(path: str | Path, skill_id: str) -> dict[str, Any]:
    """Project a named entry from the repository's current registry."""

    registry = load_current_registry(path)
    entry = next((item for item in registry["skills"] if item.get("id") == skill_id), None)
    if entry is None:
        raise KeyError(f"skill is not present in current registry: {skill_id}")
    return import_skill_index_entry(entry, registry)


def _normalise_digest(value: str) -> str:
    if value.startswith("sha256:"):
        return value
    return f"sha256:{value}"
