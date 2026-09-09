"""Immutable, session-resident routing catalog snapshot.

The snapshot validates and compiles the metadata view once. Stage routing can
then reuse the same records and relationship index without reparsing JSON,
revalidating every record, or reading canonical skill bodies.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.v3.compatibility import import_skill_index_entry, load_current_registry
from tools.v3.metadata_enrichment import (
    DEFAULT_OVERLAY_RELATIVE_PATH,
    apply_overlay,
    load_overlay,
    validate_overlay,
)
from tools.v3.skill_graph import SkillGraph


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RoutingCatalogSnapshot:
    """Validated metadata and graph view reused by multiple stage routes."""

    records: tuple[dict[str, Any], ...]
    registry_epoch: str
    overlay_digest: str
    metadata_bytes: int
    snapshot_id: str
    graph: SkillGraph = field(compare=False, repr=False)
    load_metrics: dict[str, float] = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def from_registry(
        cls,
        registry_path: str | Path,
        *,
        overlay_path: str | Path | None = None,
        repository_root: str | Path | None = None,
        check_bodies: bool = False,
    ) -> "RoutingCatalogSnapshot":
        """Load, validate, and compile one routing snapshot.

        ``check_bodies`` is an explicit maintenance/freshness option. Normal
        route construction uses the checked-in registry and overlay digests
        and keeps body reads at zero.
        """

        from tools.v3.stage_router import RoutingError

        started = time.perf_counter()
        registry_path = Path(registry_path).resolve()
        root = (
            Path(repository_root).resolve()
            if repository_root is not None
            else registry_path.parent.parent
        )
        try:
            registry = load_current_registry(registry_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise RoutingError("INVALID_CATALOG_SNAPSHOT", str(exc)) from exc
        parse_ms = (time.perf_counter() - started) * 1000

        candidate = (
            Path(overlay_path).resolve()
            if overlay_path is not None
            else root / DEFAULT_OVERLAY_RELATIVE_PATH
        )
        overlay_digest = ""
        if candidate.is_file():
            overlay_started = time.perf_counter()
            try:
                overlay = load_overlay(candidate)
            except ValueError as exc:
                raise RoutingError("INVALID_CATALOG_SNAPSHOT", str(exc)) from exc
            parse_ms += (time.perf_counter() - overlay_started) * 1000
            schema_started = time.perf_counter()
            validation = validate_overlay(
                overlay,
                registry_path=registry_path,
                repository_root=root,
                check_bodies=check_bodies,
            )
            validation_ms = (time.perf_counter() - schema_started) * 1000
            if not validation.valid:
                raise RoutingError(
                    "INVALID_CATALOG_SNAPSHOT", "; ".join(validation.errors)
                )
            records = tuple(
                copy.deepcopy(apply_overlay(entry, registry, overlay))
                for entry in registry["skills"]
            )
            overlay_digest = str(overlay.get("overlay_digest", ""))
        else:
            validation_started = time.perf_counter()
            records = tuple(
                copy.deepcopy(import_skill_index_entry(entry, registry))
                for entry in registry["skills"]
            )
            validation_ms = (time.perf_counter() - validation_started) * 1000
            overlay_digest = "sha256:" + hashlib.sha256(
                _canonical(records).encode("utf-8")
            ).hexdigest()

        graph_started = time.perf_counter()
        graph = SkillGraph(records)
        graph_ms = (time.perf_counter() - graph_started) * 1000
        source_commit = str(registry.get("source_commit", "unknown"))
        registry_epoch = f"registry:{source_commit}"
        snapshot_payload = {
            "registry_epoch": registry_epoch,
            "overlay_digest": overlay_digest,
            "skills": [
                [record.get("skill_id"), record.get("source", {}).get("digest", "")]
                for record in records
            ],
        }
        snapshot_id = "snapshot:" + hashlib.sha256(
            _canonical(snapshot_payload).encode("utf-8")
        ).hexdigest()[:16]
        metadata_bytes = len(_canonical(records).encode("utf-8"))
        total_ms = (time.perf_counter() - started) * 1000
        return cls(
            records=records,
            registry_epoch=registry_epoch,
            overlay_digest=overlay_digest,
            metadata_bytes=metadata_bytes,
            snapshot_id=snapshot_id,
            graph=graph,
            load_metrics={
                "json_parse_ms": round(parse_ms, 3),
                "schema_and_digest_validation_ms": round(validation_ms, 3),
                "metadata_compile_ms": 0.0,
                "graph_construction_ms": round(graph_ms, 3),
                "total_cold_load_ms": round(total_ms, 3),
                "body_files_loaded": 0.0 if not check_bodies else float(len(records)),
            },
        )

    def catalog(self) -> tuple[dict[str, Any], ...]:
        """Return the validated metadata view for a StageRouter."""

        return self.records

    def evidence(self) -> dict[str, Any]:
        """Return stable snapshot facts suitable for a StageRoute."""

        return {
            "snapshot_id": self.snapshot_id,
            "registry_epoch": self.registry_epoch,
            "overlay_digest": self.overlay_digest,
            "metadata_records": len(self.records),
            "metadata_bytes": self.metadata_bytes,
            "body_files_loaded": 0,
            "reused": True,
        }
