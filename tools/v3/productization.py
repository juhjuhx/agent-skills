"""Deterministic, static runtime distribution productization.

This module deliberately stops at the productization boundary.  It reads the
canonical registry, an already validated :class:`RoutingCatalogSnapshot`,
adapter manifests, and fixture-driven runtime status records.  It never
invokes a runtime, reads credentials, installs files into a user directory,
or changes routing policy.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

# Support both ``python -m tools.v3.productization`` and the user-facing
# ``python tools/v3/productization.py`` form without adding an installer.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.v3.contract_validation import validate_file, validate_instance
from tools.v3.execution_bundle import validate_bundle
from tools.v3.routing_catalog import RoutingCatalogSnapshot


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY_PATH = ROOT / "fixtures" / "v3" / "productization" / "runtime-inventory-v1.json"
DEFAULT_REGISTRY_PATH = ROOT / ".superpowers" / "SKILLS_INDEX.json"
DEFAULT_OVERLAY_PATH = ROOT / "registry" / "v3" / "skill-routing-metadata.json"

SCHEMA_VERSION = "3.0"
PRODUCTIZATION_VERSION = "1.0"
GENERATOR_ID = "agent-skills-matrix-v3-static-productization"
EXPECTED_SKILL_COUNT = 214

STATIC_ADAPTER_SUPPORT = frozenset({"NATIVE_IMPLEMENTED", "READ_ONLY_IMPLEMENTED"})
DESTINATION_CLASS = "PROJECT_LOCAL_GENERATED"
GLOBAL_RUNTIME_DIRS = (
    Path.home() / ".codex",
    Path.home() / ".claude",
    Path.home() / ".config" / "opencode",
    Path.home() / ".hermes",
)
SYSTEM_TEMP_SYMLINKS = frozenset({Path("/tmp"), Path("/var")})


class ProductizationError(ValueError):
    """Raised when a static productization contract cannot be proven."""


def canonical_json(value: Any) -> str:
    """Return one stable JSON representation used for all product digests."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_value(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProductizationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProductizationError(f"JSON record must be an object: {path}")
    return value


def _validation_errors(contract: str, value: Any) -> list[str]:
    result = validate_instance(contract, value)
    return list(result.errors)


def _validate_runtime_status(status: dict[str, Any]) -> None:
    errors = _validation_errors("RuntimeProductStatus", status)
    if errors:
        raise ProductizationError("invalid runtime product status: " + "; ".join(errors))
    for field in ("adapter_manifest_path", "native_contract_path"):
        value = status.get(field)
        if value is not None and (Path(value).is_absolute() or ".." in Path(value).parts):
            raise ProductizationError(f"runtime status contains an unsafe path: {field}")


def load_runtime_inventory(
    path: str | Path = DEFAULT_INVENTORY_PATH,
    *,
    fixture_name: str = "CODEX_ONLY",
) -> dict[str, Any]:
    """Load a named, checked-in runtime inventory without probing executables."""

    document = _read_json(Path(path))
    records = document.get("runtime_records")
    fixtures = document.get("fixtures")
    if not isinstance(records, list) or not isinstance(fixtures, dict):
        raise ProductizationError("runtime inventory requires runtime_records and fixtures")
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("runtime_id"), str):
            raise ProductizationError("runtime inventory contains an invalid runtime record")
        _validate_runtime_status(record)
        runtime_id = record["runtime_id"]
        if runtime_id in by_id:
            raise ProductizationError(f"duplicate runtime inventory record: {runtime_id}")
        by_id[runtime_id] = copy.deepcopy(record)
    selected_ids = fixtures.get(fixture_name)
    if not isinstance(selected_ids, list) or not all(isinstance(item, str) for item in selected_ids):
        raise ProductizationError(f"unknown runtime inventory fixture: {fixture_name}")
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ProductizationError(
            f"runtime inventory fixture {fixture_name} references missing runtimes: {', '.join(missing)}"
        )
    selected = [by_id[runtime_id] for runtime_id in selected_ids]
    payload = {
        "schema_version": document.get("schema_version"),
        "inventory_version": document.get("inventory_version"),
        "fixture_name": fixture_name,
        "runtimes": selected,
    }
    payload["inventory_digest"] = digest_value(payload)
    return payload


def build_runtime_capability_report(inventory: dict[str, Any]) -> dict[str, Any]:
    """Return a safe report retaining independent product-status dimensions."""

    runtimes = inventory.get("runtimes")
    if not isinstance(runtimes, list):
        raise ProductizationError("runtime inventory has no runtimes list")
    for status in runtimes:
        if not isinstance(status, dict):
            raise ProductizationError("runtime inventory contains a non-object status")
        _validate_runtime_status(status)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "report_version": PRODUCTIZATION_VERSION,
        "inventory": {
            "fixture_name": inventory.get("fixture_name", "unknown"),
            "inventory_version": inventory.get("inventory_version", "unknown"),
            "inventory_digest": inventory.get("inventory_digest"),
        },
        "runtime_count": len(runtimes),
        "runtimes": sorted(copy.deepcopy(runtimes), key=lambda item: item["runtime_id"]),
        "generated_by": GENERATOR_ID,
    }
    payload["report_digest"] = digest_value(payload)
    return payload


def _snapshot_id_payload(snapshot: RoutingCatalogSnapshot) -> dict[str, Any]:
    return {
        "registry_epoch": snapshot.registry_epoch,
        "overlay_digest": snapshot.overlay_digest,
        "skills": [
            [record.get("skill_id"), record.get("source", {}).get("digest", "")]
            for record in snapshot.records
        ],
    }


def snapshot_digest(snapshot: RoutingCatalogSnapshot) -> str:
    """Digest the complete metadata snapshot, not any canonical skill body."""

    return digest_value(
        {
            "snapshot_id": snapshot.snapshot_id,
            "registry_epoch": snapshot.registry_epoch,
            "overlay_digest": snapshot.overlay_digest,
            "records": list(snapshot.records),
        }
    )


def _validate_snapshot(snapshot: RoutingCatalogSnapshot) -> None:
    if not isinstance(snapshot, RoutingCatalogSnapshot):
        raise ProductizationError("productization requires a RoutingCatalogSnapshot")
    records = list(snapshot.records)
    errors: list[str] = []
    if len(records) != EXPECTED_SKILL_COUNT:
        errors.append(f"expected {EXPECTED_SKILL_COUNT} metadata records, got {len(records)}")
    expected_snapshot_id = "snapshot:" + hashlib.sha256(
        canonical_json(_snapshot_id_payload(snapshot)).encode("utf-8")
    ).hexdigest()[:16]
    if snapshot.snapshot_id != expected_snapshot_id:
        errors.append("routing snapshot id does not match its metadata digest")
    seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record[{index}] is not an object")
            continue
        errors.extend(
            f"record[{index}]: {error}" for error in _validation_errors("SkillMetadataV3", record)
        )
        skill_id = record.get("skill_id")
        if isinstance(skill_id, str):
            if skill_id in seen:
                errors.append(f"duplicate skill id in snapshot: {skill_id}")
            seen.add(skill_id)
        source = record.get("source", {})
        if not isinstance(source, dict) or not isinstance(source.get("digest"), str):
            errors.append(f"record[{index}] has no canonical source digest")
        elif not re.fullmatch(r"sha256:[0-9a-f]{64}", source["digest"]):
            errors.append(f"record[{index}] has an invalid canonical source digest")
        if isinstance(source, dict) and isinstance(source.get("path"), str):
            source_path = Path(source["path"])
            if source_path.is_absolute() or ".." in source_path.parts:
                errors.append(f"record[{index}] source path escapes the repository")
        routing = record.get("extensions", {}).get("routing", {})
        provenance = routing.get("metadata_provenance") if isinstance(routing, dict) else None
        if not isinstance(provenance, dict) or not isinstance(provenance.get("fields"), dict):
            errors.append(f"record[{index}] is missing routing field provenance")
    if errors:
        raise ProductizationError("invalid routing catalog snapshot: " + "; ".join(errors[:12]))


def _validate_stage_route(
    stage_route: dict[str, Any],
    snapshot: RoutingCatalogSnapshot,
) -> None:
    errors = _validation_errors("StageRoute", stage_route)
    if errors:
        raise ProductizationError("invalid StageRoute: " + "; ".join(errors))
    if stage_route.get("registry_epoch") != snapshot.registry_epoch:
        raise ProductizationError("StageRoute registry epoch is stale for this snapshot")
    records = {record["skill_id"]: record for record in snapshot.records}
    selected = [] if stage_route.get("status") == "NO_SKILL_NEEDED" else stage_route.get("selected_skills", [])
    for item in selected:
        skill_id = item.get("skill_id")
        record = records.get(skill_id)
        if record is None:
            raise ProductizationError(f"StageRoute selects a skill absent from the snapshot: {skill_id}")
        if record.get("trust") in {"QUARANTINE", "BLOCKED"}:
            raise ProductizationError(f"StageRoute selects a non-loadable skill: {skill_id}")
    catalog_evidence = stage_route.get("routing_evidence", {}).get("catalog_snapshot")
    if isinstance(catalog_evidence, dict) and catalog_evidence.get("snapshot_id") not in {
        None,
        snapshot.snapshot_id,
    }:
        raise ProductizationError("StageRoute references a different routing snapshot")


def _validate_bundle(
    bundle: dict[str, Any] | None,
    *,
    stage_route: dict[str, Any] | None,
    snapshot: RoutingCatalogSnapshot,
    runtime_id: str,
) -> None:
    if bundle is None:
        return
    result = validate_bundle(bundle)
    if not result.valid:
        raise ProductizationError("invalid CompiledExecutionBundle: " + "; ".join(result.errors))
    if stage_route is not None and bundle.get("stage_route_ref") != stage_route.get("route_id"):
        raise ProductizationError("CompiledExecutionBundle does not reference the supplied StageRoute")
    if bundle.get("registry_epoch") != snapshot.registry_epoch:
        raise ProductizationError("CompiledExecutionBundle registry epoch is stale")
    adapter_ref = str(bundle.get("adapter_manifest_ref", ""))
    if not adapter_ref.startswith(runtime_id + "@"):
        raise ProductizationError("CompiledExecutionBundle adapter does not match the runtime projection")


def _repository_file(repository_root: Path, relative_path: str, label: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ProductizationError(f"{label} path is not repository-relative")
    resolved = (repository_root / path).resolve()
    try:
        resolved.relative_to(repository_root.resolve())
    except ValueError as exc:
        raise ProductizationError(f"{label} path escapes the repository") from exc
    if not resolved.is_file():
        raise ProductizationError(f"{label} is missing: {relative_path}")
    return resolved


def _load_manifest(status: dict[str, Any], repository_root: Path) -> dict[str, Any] | None:
    relative_path = status.get("adapter_manifest_path")
    if relative_path is None:
        return None
    path = _repository_file(repository_root, relative_path, "adapter manifest")
    validation = validate_file("AgentAdapterManifest", path)
    if not validation.valid:
        raise ProductizationError("invalid adapter manifest: " + "; ".join(validation.errors))
    return _read_json(path)


def _load_contract(status: dict[str, Any], repository_root: Path) -> dict[str, Any] | None:
    relative_path = status.get("native_contract_path")
    if relative_path is None:
        return None
    path = _repository_file(repository_root, relative_path, "native runtime contract")
    contract = _read_json(path)
    if contract.get("runtime_id") != status.get("runtime_id"):
        raise ProductizationError("native runtime contract has a different runtime id")
    expected_digest = status.get("runtime_contract_digest")
    if expected_digest is None or contract.get("contract_digest") != expected_digest:
        raise ProductizationError("native runtime contract digest does not match product status")
    return contract


def _selected_refs(
    stage_route: dict[str, Any] | None,
    snapshot: RoutingCatalogSnapshot,
    *,
    materialize_bodies: bool,
    repository_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if stage_route is None or stage_route.get("status") == "NO_SKILL_NEEDED":
        return [], {}
    records = {record["skill_id"]: record for record in snapshot.records}
    result: list[dict[str, Any]] = []
    bodies: dict[str, str] = {}
    selected = stage_route.get("selected_skills", [])
    for item in selected:
        skill_id = item["skill_id"]
        record = records[skill_id]
        source = record["source"]
        resident = skill_id == "using-superpowers"
        body_materialized = bool(materialize_bodies and not resident)
        load_state = "RESIDENT" if resident else "LOADED" if body_materialized else "NOT_LOADED"
        reference = {
            "skill_id": skill_id,
            "source_ref": f"{source.get('repo', 'unknown')}@{source.get('ref', 'unknown')}",
            "source_path": source["path"],
            "digest": source["digest"],
            "role": item["role"],
            "trust": record["trust"],
            "load_state": load_state,
            "body_materialized": body_materialized,
        }
        result.append(reference)
        if body_materialized:
            source_path = _repository_file(repository_root, source["path"], f"skill {skill_id}")
            raw = source_path.read_bytes()
            if digest_bytes(raw) != source["digest"]:
                raise ProductizationError(f"canonical skill digest changed: {skill_id}")
            try:
                bodies[skill_id] = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ProductizationError(f"canonical skill is not UTF-8 text: {skill_id}") from exc
    result.sort(key=lambda item: (item["skill_id"], item["role"]))
    return result, bodies


def _skill_file_name(skill_id: str, digest: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", skill_id).strip(".-") or "skill"
    return f"{safe}-{digest[7:15]}"


def _snapshot_summary(snapshot: RoutingCatalogSnapshot) -> dict[str, Any]:
    digest_index = [
        {"skill_id": record["skill_id"], "digest": record["source"]["digest"]}
        for record in sorted(snapshot.records, key=lambda item: item["skill_id"])
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_digest": snapshot_digest(snapshot),
        "registry_epoch": snapshot.registry_epoch,
        "overlay_digest": snapshot.overlay_digest,
        "skill_count": len(snapshot.records),
        "canonical_skill_index_digest": digest_value(digest_index),
        "catalog_body_files_loaded": 0,
        "curated_provenance": True,
    }


def _plan_snapshot_reference(snapshot: RoutingCatalogSnapshot) -> dict[str, Any]:
    summary = _snapshot_summary(snapshot)
    return {
        "snapshot_id": summary["snapshot_id"],
        "snapshot_digest": summary["snapshot_digest"],
        "registry_epoch": summary["registry_epoch"],
        "skill_count": summary["skill_count"],
    }


def _route_summary(stage_route: dict[str, Any] | None) -> dict[str, Any] | None:
    if stage_route is None:
        return None
    selected = [] if stage_route.get("status") == "NO_SKILL_NEEDED" else stage_route.get("selected_skills", [])
    return {
        "route_id": stage_route["route_id"],
        "task_id": stage_route["task_id"],
        "stage": stage_route["stage"],
        "status": stage_route["status"],
        "selected_skill_ids": sorted(item["skill_id"] for item in selected),
        "route_digest": digest_value(stage_route),
    }


def _runtime_projection(
    status: dict[str, Any],
    snapshot: RoutingCatalogSnapshot,
    stage_route: dict[str, Any] | None,
    selected_refs: list[dict[str, Any]],
    *,
    body_files_materialized: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "projection_version": PRODUCTIZATION_VERSION,
        "runtime_id": status["runtime_id"],
        "projection_kind": "STATIC_DISTRIBUTION",
        "adapter_support": status["adapter_support"],
        "static_contract": status["static_contract"],
        "live_execution": status["live_execution"],
        "support": {
            "selected_only_skills": status["selected_only_skill_support"],
            "permission_projection": status["permission_projection_support"],
            "model_selection": status["model_selection_surface"],
            "effort_selection": status["effort_selection_surface"],
            "mcp": status["mcp_support"],
            "plugins": status["plugin_support"],
        },
        "authority": {
            "source": "TaskSpec ∩ policy ∩ AgentAdapterManifest ∩ runtime restrictions",
            "permissions_granted_by_distribution": False,
            "global_runtime_config_written": False,
            "live_execution_enabled": False,
        },
        "snapshot": _plan_snapshot_reference(snapshot),
        "route": _route_summary(stage_route),
        "skills": {
            "load_mode": "selected-only",
            "selected": [
                {
                    "skill_id": item["skill_id"],
                    "digest": item["digest"],
                    "role": item["role"],
                    "trust": item["trust"],
                    "load_state": item["load_state"],
                }
                for item in selected_refs
            ],
            "body_files_materialized": body_files_materialized,
            "catalog_body_files_loaded": 0,
        },
        "evidence_refs": sorted(status["evidence_refs"]),
    }


def _build_package(
    *,
    runtime_status: dict[str, Any],
    snapshot: RoutingCatalogSnapshot,
    stage_route: dict[str, Any] | None,
    bundle: dict[str, Any] | None,
    repository_root: Path,
    materialize_bodies: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    _validate_runtime_status(runtime_status)
    _validate_snapshot(snapshot)
    if stage_route is not None:
        _validate_stage_route(stage_route, snapshot)
    _validate_bundle(
        bundle,
        stage_route=stage_route,
        snapshot=snapshot,
        runtime_id=runtime_status["runtime_id"],
    )
    if runtime_status["adapter_support"] not in STATIC_ADAPTER_SUPPORT or runtime_status["static_contract"] != "VERIFIED":
        return [], {}, {}
    manifest = _load_manifest(runtime_status, repository_root)
    contract = _load_contract(runtime_status, repository_root)
    selected_refs, bodies = _selected_refs(
        stage_route,
        snapshot,
        materialize_bodies=materialize_bodies,
        repository_root=repository_root,
    )
    runtime_id = runtime_status["runtime_id"]
    specs: list[dict[str, Any]] = []

    def add(
        path: str,
        kind: str,
        payload: Any,
        source_digest: str,
        *,
        selected_only: bool = False,
        body: bool = False,
    ) -> None:
        specs.append(
            {
                "path": path,
                "kind": kind,
                "payload": payload,
                "content_digest": digest_bytes(payload if isinstance(payload, bytes) else _json_bytes(payload)),
                "source_digest": source_digest,
                "selected_only": selected_only,
                "body": body,
            }
        )

    single_inventory = {
        "schema_version": SCHEMA_VERSION,
        "inventory_version": "compiled-single-runtime",
        "fixture_name": "COMPILE",
        "runtimes": [runtime_status],
        "inventory_digest": digest_value(runtime_status),
    }
    add(
        "runtime-capability-report.json",
        "RUNTIME_CAPABILITY_REPORT",
        build_runtime_capability_report(single_inventory),
        digest_value(runtime_status),
    )
    add(f"{runtime_id}/runtime-status.json", "RUNTIME_PRODUCT_STATUS", runtime_status, digest_value(runtime_status))
    if manifest is not None:
        manifest_path = _repository_file(repository_root, runtime_status["adapter_manifest_path"], "adapter manifest")
        add(
            f"{runtime_id}/adapter-manifest.json",
            "ADAPTER_MANIFEST",
            manifest,
            digest_bytes(manifest_path.read_bytes()),
        )
    if contract is not None:
        contract_path = _repository_file(repository_root, runtime_status["native_contract_path"], "native runtime contract")
        add(
            f"{runtime_id}/runtime-contract.json",
            "RUNTIME_CONTRACT",
            contract,
            digest_bytes(contract_path.read_bytes()),
        )
    summary = _snapshot_summary(snapshot)
    add("%s/routing-snapshot.json" % runtime_id, "ROUTING_SNAPSHOT_REFERENCE", summary, summary["snapshot_digest"])
    selected_payload = {
        "schema_version": SCHEMA_VERSION,
        "load_mode": "selected-only",
        "route_status": stage_route.get("status") if stage_route else "NO_ROUTE",
        "selected": selected_refs,
        "body_files_materialized": len(bodies),
        "catalog_body_files_loaded": 0,
    }
    add(
        f"{runtime_id}/selected-skills.json",
        "SELECTED_SKILL_REFERENCE",
        selected_payload,
        digest_value(selected_refs),
        selected_only=True,
    )
    if stage_route is not None:
        route_summary = _route_summary(stage_route)
        add(f"{runtime_id}/stage-route-reference.json", "STAGE_ROUTE_REFERENCE", route_summary, route_summary["route_digest"])
        if bundle is not None:
            add(
                f"{runtime_id}/compiled-execution-bundle.json",
                "COMPILED_EXECUTION_BUNDLE_REFERENCE",
                bundle,
                bundle["bundle_digest"],
            )
    add(
        f"{runtime_id}/runtime-projection.json",
        "RUNTIME_STATIC_PROJECTION",
        _runtime_projection(
            runtime_status,
            snapshot,
            stage_route,
            selected_refs,
            body_files_materialized=len(bodies),
        ),
        digest_value(runtime_status),
        selected_only=bool(selected_refs),
    )
    for item in selected_refs:
        if not item["body_materialized"]:
            continue
        skill_dir = _skill_file_name(item["skill_id"], item["digest"])
        add(
            f"{runtime_id}/skills/selected/{skill_dir}/SKILL.md",
            "SELECTED_SKILL_BODY",
            bodies[item["skill_id"]].encode("utf-8"),
            item["digest"],
            selected_only=True,
            body=True,
        )
    specs.sort(key=lambda item: item["path"])
    artifact_records = [
        {
            "path": item["path"],
            "kind": item["kind"],
            "content_digest": item["content_digest"],
            "source_digest": item["source_digest"],
            "selected_only": item["selected_only"],
            "body": item["body"],
        }
        for item in specs
    ]
    artifact_manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_manifest_version": PRODUCTIZATION_VERSION,
        "runtime_id": runtime_id,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_digest": summary["snapshot_digest"],
        "registry_epoch": snapshot.registry_epoch,
        "runtime_contract_digest": runtime_status.get("runtime_contract_digest"),
        "artifacts": artifact_records,
        "ownership_marker": {
            "path": ".asm-generated.json",
            "generator_id": GENERATOR_ID,
            "schema_version": SCHEMA_VERSION,
            "managed": True,
        },
        "catalog_body_files_loaded": 0,
        "body_files_materialized": len(bodies),
        "manifest_digest": "",
    }
    artifact_manifest["manifest_digest"] = digest_value(artifact_manifest)
    manifest_errors = _validation_errors("GeneratedArtifactManifest", artifact_manifest)
    if manifest_errors:
        raise ProductizationError(
            "invalid generated artifact manifest: " + "; ".join(manifest_errors)
        )
    manifest_spec = {
        "path": "artifact-manifest.json",
        "kind": "GENERATED_ARTIFACT_MANIFEST",
        "payload": artifact_manifest,
        "content_digest": digest_bytes(_json_bytes(artifact_manifest)),
        "source_digest": summary["snapshot_digest"],
        "selected_only": False,
        "body": False,
    }
    marker = {
        "generator_id": GENERATOR_ID,
        "schema_version": SCHEMA_VERSION,
        "managed": True,
        "runtime_id": runtime_id,
        "snapshot_digest": summary["snapshot_digest"],
        "artifact_manifest_digest": artifact_manifest["manifest_digest"],
        "managed_paths": [item["path"] for item in artifact_records]
        + ["artifact-manifest.json"],
    }
    marker_spec = {
        "path": ".asm-generated.json",
        "kind": "OWNERSHIP_MARKER",
        "payload": marker,
        "content_digest": digest_bytes(_json_bytes(marker)),
        "source_digest": summary["snapshot_digest"],
        "selected_only": False,
        "body": False,
    }
    return specs + [manifest_spec, marker_spec], artifact_manifest, marker


def _unsupported_plan(
    runtime_status: dict[str, Any], snapshot: RoutingCatalogSnapshot, stage_route: dict[str, Any] | None
) -> dict[str, Any]:
    reason = (
        f"{runtime_status['runtime_name']} has no meaningful static adapter projection "
        f"({runtime_status['adapter_support']}/{runtime_status['static_contract']})."
    )
    operation = {
        "operation": "SKIP_UNSUPPORTED_RUNTIME",
        "source_artifact": None,
        "destination_class": DESTINATION_CLASS,
        "path": None,
        "content_digest": None,
        "overwrite_policy": "NOT_ALLOWED",
        "reason": reason,
        "support_status": runtime_status["adapter_support"],
        "preconditions": ["a verified static adapter is required before generation"],
        "conflict_outcome": "NOT_APPLICABLE",
    }
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "plan_version": PRODUCTIZATION_VERSION,
        "runtime_id": runtime_status["runtime_id"],
        "snapshot": _plan_snapshot_reference(snapshot),
        "runtime_status": copy.deepcopy(runtime_status),
        "stage_route": stage_route.get("route_id") if stage_route else None,
        "no_actual_writes": True,
        "artifacts": [],
        "operations": [operation],
        "warnings": [reason],
        "conflicts": [],
        "plan_digest": "",
    }
    payload["plan_digest"] = digest_value(payload)
    schema_errors = _validation_errors("InstallationPlan", payload)
    if schema_errors:
        raise ProductizationError("invalid generated InstallationPlan: " + "; ".join(schema_errors))
    return payload


def _destination_state(destination_states: dict[str, Any] | None, path: str) -> tuple[str, str | None]:
    raw = (destination_states or {}).get(path, "ABSENT")
    if isinstance(raw, dict):
        return str(raw.get("state", "UNKNOWN")), raw.get("content_digest")
    return str(raw), None


def _operation_for(
    artifact: dict[str, Any],
    *,
    destination_states: dict[str, Any] | None,
    support_status: str,
) -> dict[str, Any]:
    path = artifact["path"]
    state, existing_digest = _destination_state(destination_states, path)
    if state == "ABSENT":
        operation = "LINK_OR_REFERENCE_CANONICAL_SKILL" if artifact["kind"] == "SELECTED_SKILL_REFERENCE" else "CREATE_GENERATED_FILE"
        outcome = "CREATE"
        overwrite = "CREATE_ONLY"
    elif state == "MANAGED":
        if existing_digest == artifact["content_digest"]:
            operation = "NO_OP"
            outcome = "NO_OP"
        else:
            operation = "CREATE_GENERATED_FILE"
            outcome = "UPDATE_MANAGED"
        overwrite = "UPDATE_MANAGED_ONLY"
    elif state == "USER_OWNED":
        operation = "SKIP_USER_OWNED"
        outcome = "SKIP_USER_OWNED"
        overwrite = "SKIP_USER_OWNED"
    else:
        operation = "CONFLICT"
        outcome = "CONFLICT"
        overwrite = "NOT_ALLOWED"
    return {
        "operation": operation,
        "source_artifact": artifact["kind"],
        "destination_class": DESTINATION_CLASS,
        "path": path,
        "content_digest": artifact["content_digest"],
        "overwrite_policy": overwrite,
        "reason": f"static generated artifact: {artifact['kind']}",
        "support_status": support_status,
        "preconditions": [
            "write only to the explicit productization output directory",
            "never overwrite a user-owned destination",
        ],
        "conflict_outcome": outcome,
    }


def _plan_from_package(
    *,
    runtime_status: dict[str, Any],
    snapshot: RoutingCatalogSnapshot,
    stage_route: dict[str, Any] | None,
    specs: list[dict[str, Any]],
    destination_states: dict[str, Any] | None,
) -> dict[str, Any]:
    artifacts = [
        {
            "path": item["path"],
            "kind": item["kind"],
            "content_digest": item["content_digest"],
            "source_digest": item["source_digest"],
            "selected_only": item["selected_only"],
            "body": item["body"],
        }
        for item in sorted(specs, key=lambda item: item["path"])
    ]
    operations = [
        _operation_for(
            item,
            destination_states=destination_states,
            support_status=runtime_status["adapter_support"],
        )
        for item in artifacts
    ]
    warnings: list[str] = []
    if runtime_status["live_execution"] != "VERIFIED":
        warnings.append(
            f"live execution is {runtime_status['live_execution']}; this static plan makes no live-readiness claim"
        )
        operations.append(
            {
                "operation": "WARN_LIVE_BLOCKED",
                "source_artifact": None,
                "destination_class": DESTINATION_CLASS,
                "path": None,
                "content_digest": None,
                "overwrite_policy": "NOT_APPLICABLE",
                "reason": warnings[-1],
                "support_status": runtime_status["live_execution"],
                "preconditions": ["live execution is outside Phase 3I"],
                "conflict_outcome": "NOT_APPLICABLE",
            }
        )
    conflicts = sorted(
        item["path"] for item in operations if item.get("conflict_outcome") == "CONFLICT" and item.get("path")
    )
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "plan_version": PRODUCTIZATION_VERSION,
        "runtime_id": runtime_status["runtime_id"],
        "snapshot": _plan_snapshot_reference(snapshot),
        "runtime_status": copy.deepcopy(runtime_status),
        "stage_route": stage_route.get("route_id") if stage_route else None,
        "no_actual_writes": True,
        "artifacts": artifacts,
        "operations": operations,
        "warnings": warnings,
        "conflicts": conflicts,
        "plan_digest": "",
    }
    payload["plan_digest"] = digest_value(payload)
    schema_errors = _validation_errors("InstallationPlan", payload)
    if schema_errors:
        raise ProductizationError("invalid generated InstallationPlan: " + "; ".join(schema_errors))
    return payload


def build_installation_plan(
    *,
    runtime_status: dict[str, Any],
    snapshot: RoutingCatalogSnapshot,
    stage_route: dict[str, Any] | None = None,
    bundle: dict[str, Any] | None = None,
    destination_states: dict[str, Any] | None = None,
    repository_root: str | Path = ROOT,
    materialize_bodies: bool = False,
) -> dict[str, Any]:
    """Build a dry-run plan; this function performs no filesystem writes."""

    _validate_runtime_status(runtime_status)
    _validate_snapshot(snapshot)
    if runtime_status["adapter_support"] not in STATIC_ADAPTER_SUPPORT or runtime_status["static_contract"] != "VERIFIED":
        if stage_route is not None:
            _validate_stage_route(stage_route, snapshot)
        return _unsupported_plan(runtime_status, snapshot, stage_route)
    specs, _, _ = _build_package(
        runtime_status=runtime_status,
        snapshot=snapshot,
        stage_route=stage_route,
        bundle=bundle,
        repository_root=Path(repository_root).resolve(),
        materialize_bodies=materialize_bodies,
    )
    return _plan_from_package(
        runtime_status=runtime_status,
        snapshot=snapshot,
        stage_route=stage_route,
        specs=specs,
        destination_states=destination_states,
    )


def _safe_output_dir(output_dir: str | Path) -> Path:
    raw = Path(output_dir).expanduser()
    # macOS exposes temporary roots such as /tmp and /var through symlinks.
    # Allow only those known system aliases in the ancestor chain; an explicit
    # output symlink or an arbitrary user-created ancestor could redirect the
    # generated tree outside the requested destination.
    current = raw
    while True:
        if current.is_symlink() and current not in SYSTEM_TEMP_SYMLINKS:
            raise ProductizationError(f"productization output path contains a symlink: {current}")
        if current == current.parent:
            break
        current = current.parent
    candidate = raw.resolve()
    if candidate == Path.home():
        raise ProductizationError("productization output cannot be the user home directory")
    for global_dir in GLOBAL_RUNTIME_DIRS:
        if candidate == global_dir or global_dir in candidate.parents:
            raise ProductizationError(f"global runtime directory is not an allowed output: {global_dir}")
    return candidate


def _prepare_output_dir(output_dir: Path, specs: list[dict[str, Any]]) -> None:
    if output_dir.exists() and not output_dir.is_dir():
        raise ProductizationError("productization output is not a directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    marker_path = output_dir / ".asm-generated.json"
    if marker_path.is_symlink():
        raise ProductizationError("refusing to use a symlinked ownership marker")
    target_paths = {output_dir / item["path"] for item in specs}
    existing_targets = [path for path in target_paths if path.exists()]
    if existing_targets and not marker_path.is_file():
        raise ProductizationError("refusing to overwrite output without an Agent Skills Matrix ownership marker")
    if marker_path.is_file():
        marker = _read_json(marker_path)
        if marker.get("generator_id") != GENERATOR_ID or marker.get("managed") is not True:
            raise ProductizationError("existing productization output is not owned by this generator")
        old_paths = set(marker.get("managed_paths", []))
        new_paths = {item["path"] for item in specs}
        stale = sorted(old_paths - new_paths)
        if stale:
            raise ProductizationError(
                "stale managed output requires an explicit future cleanup operation: " + ", ".join(stale)
            )


def _write_specs(output_dir: Path, specs: Iterable[dict[str, Any]]) -> None:
    for item in specs:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ProductizationError(f"generated artifact path escapes output: {item['path']}")
        target = output_dir / relative
        if target.exists() and target.is_symlink():
            raise ProductizationError(f"refusing to write through symlink: {item['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        ancestor = output_dir
        for component in relative.parts[:-1]:
            ancestor = ancestor / component
            if ancestor.is_symlink():
                raise ProductizationError(f"refusing to write through symlink directory: {item['path']}")
        payload = item["payload"] if isinstance(item["payload"], bytes) else _json_bytes(item["payload"])
        target.write_bytes(payload)


def compile_distribution(
    *,
    runtime_status: dict[str, Any],
    snapshot: RoutingCatalogSnapshot,
    output_dir: str | Path,
    stage_route: dict[str, Any] | None = None,
    bundle: dict[str, Any] | None = None,
    repository_root: str | Path = ROOT,
    materialize_bodies: bool = False,
    destination_states: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write only derived artifacts into an explicit safe output directory."""

    _validate_runtime_status(runtime_status)
    _validate_snapshot(snapshot)
    if runtime_status["adapter_support"] not in STATIC_ADAPTER_SUPPORT or runtime_status["static_contract"] != "VERIFIED":
        return {
            "plan": build_installation_plan(
                runtime_status=runtime_status,
                snapshot=snapshot,
                stage_route=stage_route,
                bundle=bundle,
                destination_states=destination_states,
                repository_root=repository_root,
                materialize_bodies=materialize_bodies,
            ),
            "artifact_manifest": None,
            "output_dir": None,
        }
    specs, artifact_manifest, _ = _build_package(
        runtime_status=runtime_status,
        snapshot=snapshot,
        stage_route=stage_route,
        bundle=bundle,
        repository_root=Path(repository_root).resolve(),
        materialize_bodies=materialize_bodies,
    )
    plan = _plan_from_package(
        runtime_status=runtime_status,
        snapshot=snapshot,
        stage_route=stage_route,
        specs=specs,
        destination_states=destination_states,
    )
    safe_output = _safe_output_dir(output_dir)
    _prepare_output_dir(safe_output, specs)
    _write_specs(safe_output, specs)
    return {
        "plan": plan,
        "artifact_manifest": copy.deepcopy(artifact_manifest),
        "output_dir": str(safe_output),
    }


def _load_output_json(output_dir: Path, relative_path: str) -> dict[str, Any]:
    path = output_dir / relative_path
    if path.is_symlink():
        raise ProductizationError(f"generated output contains a symlink: {relative_path}")
    return _read_json(path)


def validate_distribution(
    output_dir: str | Path,
    *,
    snapshot: RoutingCatalogSnapshot,
    runtime_status: dict[str, Any],
    stage_route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate existing generated output without regenerating or repairing it."""

    errors: list[str] = []
    try:
        _validate_runtime_status(runtime_status)
        _validate_snapshot(snapshot)
        if stage_route is not None:
            _validate_stage_route(stage_route, snapshot)
        output = _safe_output_dir(output_dir)
        manifest = _load_output_json(output, "artifact-manifest.json")
        marker = _load_output_json(output, ".asm-generated.json")
    except ProductizationError as exc:
        return {"valid": False, "errors": [str(exc)], "checked_files": 0}
    errors.extend(_validation_errors("GeneratedArtifactManifest", manifest))
    expected_snapshot = _snapshot_summary(snapshot)
    if manifest.get("runtime_id") != runtime_status.get("runtime_id"):
        errors.append("runtime id in generated artifact manifest is stale")
    if manifest.get("snapshot_id") != snapshot.snapshot_id or manifest.get("snapshot_digest") != expected_snapshot["snapshot_digest"]:
        errors.append("generated routing snapshot is stale")
    if manifest.get("registry_epoch") != snapshot.registry_epoch:
        errors.append("generated registry epoch is stale")
    if manifest.get("runtime_contract_digest") != runtime_status.get("runtime_contract_digest"):
        errors.append("runtime contract digest in generated output is stale")
    if marker.get("generator_id") != GENERATOR_ID or marker.get("managed") is not True:
        errors.append("generated ownership marker is invalid")
    if marker.get("artifact_manifest_digest") != manifest.get("manifest_digest"):
        errors.append("ownership marker does not bind the artifact manifest")
    manifest_without_digest = copy.deepcopy(manifest)
    manifest_without_digest["manifest_digest"] = ""
    if manifest.get("manifest_digest") != digest_value(manifest_without_digest):
        errors.append("generated artifact manifest digest is invalid")
    checked_files = 0
    for artifact in manifest.get("artifacts", []):
        relative = Path(artifact.get("path", ""))
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"unsafe generated artifact path: {artifact.get('path')}")
            continue
        path = output / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"generated artifact is missing: {artifact.get('path')}")
            continue
        checked_files += 1
        actual_digest = digest_bytes(path.read_bytes())
        if actual_digest != artifact.get("content_digest"):
            errors.append(f"artifact content digest mismatch: {artifact.get('path')}")
        if artifact.get("path", "").endswith("/routing-snapshot.json"):
            try:
                snapshot_payload = _read_json(path)
                if snapshot_payload.get("snapshot_digest") != expected_snapshot["snapshot_digest"]:
                    errors.append("routing snapshot artifact contains a stale snapshot digest")
            except ProductizationError as exc:
                errors.append(str(exc))
        if artifact.get("path", "").endswith("/runtime-status.json"):
            try:
                if _read_json(path) != runtime_status:
                    errors.append("runtime status artifact differs from the supplied status")
            except ProductizationError as exc:
                errors.append(str(exc))
        if artifact.get("body"):
            selected_path = output / f"{manifest['runtime_id']}/selected-skills.json"
            try:
                selected = _read_json(selected_path).get("selected", [])
                digest = artifact.get("source_digest")
                current_digests = {
                    record["source"]["digest"]
                    for record in snapshot.records
                    if record.get("skill_id") in {item.get("skill_id") for item in selected}
                }
                if digest not in current_digests:
                    errors.append(f"materialized skill digest is stale: {artifact.get('path')}")
            except ProductizationError as exc:
                errors.append(str(exc))
    expected_materialized = sum(1 for item in manifest.get("artifacts", []) if item.get("body"))
    if manifest.get("body_files_materialized") != expected_materialized:
        errors.append("materialized body count is inconsistent")
    if manifest.get("catalog_body_files_loaded") != 0:
        errors.append("catalog validation reports a non-zero body load")
    route_path = output / f"{manifest.get('runtime_id')}/stage-route-reference.json"
    if stage_route is not None:
        if not route_path.is_file():
            errors.append("generated StageRoute reference is missing")
        else:
            try:
                route_reference = _read_json(route_path)
                if route_reference.get("route_digest") != digest_value(stage_route):
                    errors.append("generated StageRoute reference is stale")
            except ProductizationError as exc:
                errors.append(str(exc))
    return {
        "valid": not errors,
        "errors": errors,
        "checked_files": checked_files,
        "snapshot_digest": expected_snapshot["snapshot_digest"],
        "runtime_id": runtime_status["runtime_id"],
    }


def explain_runtime(status: dict[str, Any], plan: dict[str, Any] | None = None) -> str:
    """Render the concise human-facing status used by the dry-run CLI."""

    _validate_runtime_status(status)
    static_ready = status["adapter_support"] in STATIC_ADAPTER_SUPPORT and status["static_contract"] == "VERIFIED"
    planned = len(plan.get("artifacts", [])) if plan else 0
    conflicts = len(plan.get("conflicts", [])) if plan else 0
    warnings = len(plan.get("warnings", [])) if plan else 0
    lines = [
        "Agent Skills Matrix v3",
        f"Runtime: {status['runtime_name']} ({status['runtime_id']})",
        f"Static integration: {'READY' if static_ready else 'NOT_IMPLEMENTED'}",
        f"Live execution: {status['live_execution']}",
        "Effort routing: NOT_READY (productization records the capability surface only)",
        f"Planned files: {planned}",
        f"Conflicts: {conflicts}",
        f"Warnings: {warnings}",
        "No changes were made.",
    ]
    return "\n".join(lines)


def _load_optional_record(path: str | None) -> dict[str, Any] | None:
    return _read_json(Path(path)) if path else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a static Agent Skills Matrix v3 runtime distribution")
    parser.add_argument("--operation", choices=("plan", "compile", "validate", "explain"), default="plan")
    parser.add_argument("--runtime", default="codex", help="runtime id or 'all'")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY_PATH)
    parser.add_argument("--fixture", default="CODEX_ONLY")
    parser.add_argument("--route", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--materialize-selected", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    operation = "plan" if args.dry_run else args.operation
    try:
        fixture_name = "ALL_KNOWN_STATIC" if args.runtime == "all" and args.fixture == "CODEX_ONLY" else args.fixture
        inventory = load_runtime_inventory(args.inventory, fixture_name=fixture_name)
        snapshot = RoutingCatalogSnapshot.from_registry(
            DEFAULT_REGISTRY_PATH,
            overlay_path=DEFAULT_OVERLAY_PATH,
            repository_root=ROOT,
        )
        route = _load_optional_record(str(args.route) if args.route else None)
        bundle = _load_optional_record(str(args.bundle) if args.bundle else None)
        statuses = inventory["runtimes"] if args.runtime == "all" else [
            item for item in inventory["runtimes"] if item["runtime_id"] == args.runtime
        ]
        if not statuses and args.runtime != "all":
            raise ProductizationError(f"runtime is absent from inventory fixture: {args.runtime}")
        if args.runtime == "all" and operation in {"compile", "validate"}:
            raise ProductizationError(
                "--runtime all is supported for plan/explain only; compile or validate one runtime at a time"
            )
        plans: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        for status in statuses:
            if operation == "validate":
                if args.output is None:
                    raise ProductizationError("--output is required for validate")
                results.append(
                    validate_distribution(
                        args.output,
                        snapshot=snapshot,
                        runtime_status=status,
                        stage_route=route,
                    )
                )
            elif operation == "compile":
                if args.output is None:
                    raise ProductizationError("--output is required for compile")
                results.append(
                    compile_distribution(
                        runtime_status=status,
                        snapshot=snapshot,
                        stage_route=route,
                        bundle=bundle,
                        output_dir=args.output,
                        repository_root=ROOT,
                        materialize_bodies=args.materialize_selected,
                    )
                )
            else:
                plan = build_installation_plan(
                    runtime_status=status,
                    snapshot=snapshot,
                    stage_route=route,
                    bundle=bundle,
                    repository_root=ROOT,
                    materialize_bodies=args.materialize_selected,
                )
                plans.append(plan)
                results.append({"status": status, "plan": plan})
        if args.format == "json":
            print(json.dumps({"operation": operation, "results": results}, ensure_ascii=False, sort_keys=True, indent=2))
        elif operation == "validate":
            for result in results:
                print("VALID" if result.get("valid") else "INVALID")
                if result.get("errors"):
                    print("\n".join(f"- {error}" for error in result["errors"]))
        elif operation == "compile":
            print(f"Generated distributions: {sum(1 for result in results if result.get('artifact_manifest'))}")
            print("Generated output is repository-local/temporary only; no runtime was invoked.")
        else:
            if not results:
                print("No runtime records selected; no changes were made.")
            else:
                for item in results:
                    print(explain_runtime(item["status"], item["plan"]))
                    if len(results) > 1:
                        print()
        return 0
    except ProductizationError as exc:
        print(f"productization error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
