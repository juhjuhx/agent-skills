"""Runtime-neutral compilation of a validated stage route."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Iterable

from tools.v3.contract_validation import validate_instance


def canonical_json(value: Any) -> str:
    """Serialize JSON deterministically for digests and cache keys."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_record(record: dict[str, Any], field: str) -> str:
    payload = copy.deepcopy(record)
    payload.pop(field, None)
    return f"sha256:{hashlib.sha256(canonical_json(payload).encode('utf-8')).hexdigest()}"


def _permission_defaults(permission: dict[str, Any] | None) -> dict[str, Any]:
    defaults = {
        "level": "read-only",
        "filesystem": "read",
        "network": "none",
        "external_write": False,
        "secrets": False,
        "publish": False,
        "delete": False,
    }
    if permission:
        defaults.update(permission)
    return defaults


def _skill_refs(selected_skills: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (copy.deepcopy(item) for item in selected_skills),
        key=lambda item: (item.get("skill_id", ""), item.get("role", "")),
    )


def compile_execution_bundle(
    *,
    task_spec: dict[str, Any],
    stage_route: dict[str, Any],
    adapter_manifest: dict[str, Any],
    model_profile: dict[str, Any],
    selected_skills: Iterable[dict[str, Any]],
    effective_capabilities: Iterable[str],
    permission_envelope: dict[str, Any],
    context: dict[str, Any],
    reasoning_artifact_refs: Iterable[str],
    evidence_required: Iterable[str],
    provenance: dict[str, Any],
    status: str | None = None,
    evidence_gate: dict[str, Any] | None = None,
    no_skill_reason: str | None = None,
    blocked_reason: str | None = None,
    bundle_version: str = "1.0",
) -> dict[str, Any]:
    """Build and validate one portable immutable-by-convention record."""

    selected = _skill_refs(selected_skills)
    evidence = list(dict.fromkeys(str(item) for item in evidence_required))
    gate = copy.deepcopy(evidence_gate or {"status": "PENDING", "missing": evidence})
    skill_records = [
        {
            "skill_id": item["skill_id"],
            "source_ref": item["source_ref"],
            "digest": item["digest"],
        }
        for item in selected
    ]
    registry_epoch = stage_route["registry_epoch"]
    adapter_ref = f"{adapter_manifest['runtime_id']}@{adapter_manifest['manifest_version']}"
    model_ref = (
        f"{model_profile['provider_id']}/{model_profile['model_id']}@"
        f"{model_profile['profile_version']}"
    )
    effective_status = status or ("READY" if gate.get("status") == "PASS" else "DEGRADED")
    bundle: dict[str, Any] = {
        "schema_version": "3.0",
        "bundle_version": bundle_version,
        "bundle_id": f"bundle:{task_spec['task_id']}:{stage_route['route_id']}",
        "task_spec_ref": task_spec["task_id"],
        "stage_route_ref": stage_route["route_id"],
        "adapter_manifest_ref": adapter_ref,
        "model_profile_ref": model_ref,
        "status": effective_status,
        "selected_skills": selected,
        "effective_capabilities": sorted(set(effective_capabilities)),
        "permission_envelope": _permission_defaults(permission_envelope),
        "context": {
            "static_prefix": context.get("static_prefix", "unknown"),
            "dynamic_context": context.get("dynamic_context", "unknown"),
            "tool_schema_context": context.get("tool_schema_context", "unknown"),
            "artifact_refs": sorted(set(context.get("artifact_refs", []))),
        },
        "reasoning_artifact_refs": sorted(set(reasoning_artifact_refs)),
        "evidence_required": evidence,
        "evidence_gate": gate,
        "registry_epoch": registry_epoch,
        "provenance": {
            "generated_by": provenance.get("generated_by", "v3-bundle-compiler"),
            "registry_epoch": registry_epoch,
            "skill_records": skill_records,
        },
    }
    if no_skill_reason:
        bundle["no_skill_reason"] = no_skill_reason
    if blocked_reason:
        bundle["blocked_reason"] = blocked_reason
    bundle["bundle_digest"] = digest_record(bundle, "bundle_digest")
    validation = validate_instance("CompiledExecutionBundle", bundle)
    if not validation.valid:
        raise ValueError("invalid compiled execution bundle: " + "; ".join(validation.errors))
    return bundle


def validate_bundle(bundle: dict[str, Any]):
    """Validate shape and the self-consistency of the bundle digest."""

    result = validate_instance("CompiledExecutionBundle", bundle)
    if result.valid and digest_record(bundle, "bundle_digest") != bundle.get("bundle_digest"):
        result.errors.append("bundle_digest does not match the canonical bundle payload")
    if result.valid and bundle.get("status") == "READY":
        if bundle.get("evidence_gate", {}).get("status") != "PASS":
            result.errors.append("READY bundle requires a passing evidence gate")
    return result
