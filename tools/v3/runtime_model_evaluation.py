"""Evidence-only runtime and model routing evaluation helpers.

This module deliberately stops at eligibility, replay, and comparison.  It
does not select a production model, mutate routing policy, invoke a runtime,
or install a tool.  Runtime authority comes from the existing permission
intersection; model records are capability and measurement data only.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Iterable

from tools.v3.contract_validation import KNOWN_CAPABILITIES, validate_instance
from tools.v3.execution_bundle import canonical_json
from tools.v3.permission_intersection import intersect_permissions


EVIDENCE_CLASSES = frozenset(
    {"REAL_EXECUTION", "HOST_MANAGED_FIXTURE", "MOCK", "UNAVAILABLE"}
)
RUNTIME_REQUIRED_CAPABILITIES = {
    "needs_editing": "editing",
    "needs_browser": "browser",
    "needs_subagents": "subagents",
    "needs_sandbox": "sandbox",
    "needs_MCP": "MCP",
    "needs_structured_output": "structured_output",
    "needs_long_context": "long_context",
    "needs_multimodal": "multimodal",
}
MODEL_SELECTION_FIELDS = {
    "TASK_DEFAULT": "task",
    "STAGE": "stage",
    "SUBAGENT": "subagent",
}
COST_ORDER = {"free": 0, "low": 1, "balanced": 2, "high": 3, "unknown": 4}

_CONSERVATIVE_PERMISSION = {
    "level": "read-only",
    "filesystem": "read",
    "network": "none",
    "external_write": False,
    "secrets": False,
    "publish": False,
    "delete": False,
}


def _validation_errors(contract: str, value: dict[str, Any]) -> list[str]:
    result = validate_instance(contract, value)
    return list(result.errors)


def _status_for_availability(availability: str) -> str | None:
    if availability == "NOT_INSTALLED":
        return "UNAVAILABLE"
    if availability in {"UNKNOWN", "UPSTREAM_ONLY"}:
        return "UNVERIFIED"
    return None


def _required_runtime_capability(requirement: str) -> str:
    return RUNTIME_REQUIRED_CAPABILITIES.get(requirement, requirement)


def _requested_permission_level(task_spec: dict[str, Any]) -> str:
    return str((task_spec.get("permission_requirements") or {}).get("level", "read-only"))


def assess_runtime_candidate(
    task_spec: dict[str, Any],
    candidate: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess task/session compatibility for one runtime candidate."""

    errors = _validation_errors("RuntimeCandidate", candidate)
    if errors:
        return {"status": "UNVERIFIED", "reasons": ["invalid runtime candidate: " + "; ".join(errors)]}

    availability_status = _status_for_availability(candidate["availability"])
    if availability_status:
        return {
            "status": availability_status,
            "reasons": [f"runtime availability is {candidate['availability']}"],
        }
    if candidate["adapter_status"] == "UNAVAILABLE":
        return {"status": "UNAVAILABLE", "reasons": ["runtime adapter is unavailable"]}
    if candidate["adapter_status"] == "UNVERIFIED":
        return {"status": "UNVERIFIED", "reasons": ["runtime adapter is unverified"]}
    if not bool(candidate.get("permissions", {}).get("policy_gated", False)):
        return {"status": "INCOMPATIBLE", "reasons": ["runtime permissions are not policy-gated"]}

    capabilities = candidate.get("capabilities", {})
    missing: list[str] = []
    unknown: list[str] = []
    for requirement in task_spec.get("required_capabilities", []) or []:
        runtime_capability = _required_runtime_capability(str(requirement))
        if runtime_capability not in KNOWN_CAPABILITIES:
            unknown.append(str(requirement))
        elif not bool(capabilities.get(runtime_capability, False)):
            missing.append(runtime_capability)
    if unknown:
        return {
            "status": "INCOMPATIBLE",
            "reasons": [f"unknown required runtime capability: {item}" for item in unknown],
            "missing_capabilities": sorted(set(unknown)),
        }
    if missing:
        return {
            "status": "INCOMPATIBLE",
            "reasons": [f"required runtime capability is unavailable: {item}" for item in sorted(set(missing))],
            "missing_capabilities": sorted(set(missing)),
        }

    requested_level = _requested_permission_level(task_spec)
    supported_levels = set(candidate.get("permissions", {}).get("supported_levels", []))
    if requested_level not in supported_levels:
        return {
            "status": "INCOMPATIBLE",
            "reasons": [f"runtime does not advertise requested permission level: {requested_level}"],
        }
    policy_level = str((policy or {}).get("level", requested_level))
    if policy_level != requested_level and policy_level == "read-only" and requested_level != "read-only":
        return {
            "status": "INCOMPATIBLE",
            "reasons": [f"policy limits requested permission level {requested_level} to {policy_level}"],
        }

    status = "DEGRADED" if candidate["adapter_status"] == "GUIDE_ONLY" else "ELIGIBLE"
    reasons = []
    if status == "DEGRADED":
        reasons.append("runtime is installed but the adapter is guide-only")
    return {
        "status": status,
        "reasons": reasons,
        "missing_capabilities": [],
        "runtime_id": candidate["runtime_id"],
    }


def assess_model_candidate(
    task_spec: dict[str, Any],
    runtime_candidate: dict[str, Any],
    model_candidate: dict[str, Any],
    *,
    selection_scope: str = "TASK_DEFAULT",
    required_model_capabilities: Iterable[str] = (),
) -> dict[str, Any]:
    """Assess model compatibility without granting runtime authority."""

    errors = _validation_errors("ModelCandidate", model_candidate)
    if errors:
        return {"status": "UNVERIFIED", "reason": "invalid model candidate: " + "; ".join(errors)}
    if selection_scope not in {"TASK_DEFAULT", "STAGE", "SUBAGENT", "TASK_PINNED"}:
        return {"status": "INCOMPATIBLE", "reason": f"unsupported model selection scope: {selection_scope}"}

    availability_status = _status_for_availability(model_candidate["availability"])
    if availability_status:
        return {"status": availability_status, "reason": f"model availability is {model_candidate['availability']}"}

    if selection_scope == "TASK_PINNED":
        selection_status = "TASK_PINNED"
        selection_reason = "runtime pins the model at task/session scope"
    else:
        field = MODEL_SELECTION_FIELDS[selection_scope]
        support = runtime_candidate.get("model_selection", {}).get(field, "UNKNOWN")
        if support == "TASK_PINNED":
            return {
                "status": "TASK_PINNED",
                "reason": f"runtime does not support {selection_scope.lower()} model switching; keep the task model",
            }
        if support == "UNSUPPORTED":
            return {"status": "INCOMPATIBLE", "reason": f"runtime does not support {selection_scope.lower()} model selection"}
        if support == "UNKNOWN":
            return {"status": "UNVERIFIED", "reason": f"runtime {selection_scope.lower()} model selection is unverified"}
        selection_status = "ELIGIBLE"
        selection_reason = f"runtime supports {selection_scope.lower()} model selection"

    missing = sorted(
        {
            capability
            for capability in required_model_capabilities
            if capability not in KNOWN_CAPABILITIES
            or not bool(model_candidate.get("capabilities", {}).get(capability, False))
        }
    )
    if missing:
        return {
            "status": "INCOMPATIBLE",
            "reason": "required model capabilities are unavailable: " + ", ".join(missing),
            "missing_capabilities": missing,
        }
    return {
        "status": selection_status,
        "reason": selection_reason,
        "missing_capabilities": [],
        "provider_id": model_candidate["provider_id"],
        "model_id": model_candidate["model_id"],
    }


def _digest_without(record: dict[str, Any], field: str) -> str:
    payload = copy.deepcopy(record)
    payload.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _permission_or_conservative(
    task_spec: dict[str, Any],
    stage_route: dict[str, Any],
    adapter_manifest: dict[str, Any],
    policy: dict[str, Any] | None,
    live_runtime: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    result = intersect_permissions(
        task_spec,
        policy,
        adapter_manifest,
        live_runtime,
        stage_route.get("budget_envelope"),
    )
    if result["status"] == "ALLOWED":
        return copy.deepcopy(result["effective"]), []
    return copy.deepcopy(_CONSERVATIVE_PERMISSION), list(result["reasons"])


def build_execution_configuration(
    *,
    task_spec: dict[str, Any],
    stage_route: dict[str, Any],
    runtime_candidate: dict[str, Any],
    model_candidate: dict[str, Any] | None,
    adapter_manifest: dict[str, Any],
    policy: dict[str, Any] | None = None,
    live_runtime: dict[str, Any] | None = None,
    selection_scope: str = "TASK_DEFAULT",
    evidence_mode: str = "HOST_MANAGED_FIXTURE",
    source_refs: Iterable[str] = (),
) -> dict[str, Any]:
    """Build one reproducible evaluation configuration, not a live plan."""

    task_errors = _validation_errors("TaskSpec", task_spec)
    route_errors = _validation_errors("StageRoute", stage_route)
    runtime_errors = _validation_errors("RuntimeCandidate", runtime_candidate)
    adapter_errors = _validation_errors("AgentAdapterManifest", adapter_manifest)
    errors = task_errors + route_errors + runtime_errors + adapter_errors
    if model_candidate is not None:
        errors.extend(_validation_errors("ModelCandidate", model_candidate))
    if errors:
        raise ValueError("invalid execution configuration input: " + "; ".join(errors))
    if evidence_mode not in EVIDENCE_CLASSES:
        raise ValueError(f"unsupported evidence mode: {evidence_mode}")
    if adapter_manifest.get("runtime_id") != runtime_candidate.get("runtime_id"):
        raise ValueError("runtime candidate and adapter manifest must refer to the same runtime")
    if stage_route.get("adapter") != runtime_candidate.get("runtime_id"):
        raise ValueError("stage route and runtime candidate must refer to the same runtime")

    runtime_assessment = assess_runtime_candidate(task_spec, runtime_candidate, policy=policy)
    no_skill_route = stage_route.get("status") == "NO_SKILL_NEEDED"
    model_assessment = None
    if model_candidate is not None and not no_skill_route:
        model_assessment = assess_model_candidate(
            task_spec,
            runtime_candidate,
            model_candidate,
            selection_scope=selection_scope,
        )
    permission, permission_reasons = _permission_or_conservative(
        task_spec, stage_route, adapter_manifest, policy, live_runtime
    )

    status = runtime_assessment["status"]
    reasons = list(runtime_assessment.get("reasons", [])) + permission_reasons
    if permission_reasons:
        status = "INCOMPATIBLE"
    elif model_assessment is not None:
        model_status = model_assessment["status"]
        reasons.extend([model_assessment["reason"]])
        if model_status in {"UNAVAILABLE", "UNVERIFIED", "INCOMPATIBLE", "TASK_PINNED"}:
            status = model_status
    if status == "DEGRADED" and not reasons:
        reasons.append("runtime is compatible with a degraded adapter status")

    runtime_caps = runtime_candidate.get("capabilities", {})
    effective_capabilities = sorted(
        capability
        for capability in stage_route.get("granted_capabilities", [])
        if capability in KNOWN_CAPABILITIES
        and bool(runtime_caps.get(capability, False))
    )
    model_ref = model_candidate.get("candidate_id") if model_candidate and not no_skill_route else None
    no_model_work_reason = None
    if no_skill_route:
        no_model_work_reason = stage_route.get("no_skill_reason", "NO_SKILL_NEEDED route requires no model-routing work")
    configuration: dict[str, Any] = {
        "schema_version": "3.0",
        "configuration_id": f"configuration:{task_spec['task_id']}:{stage_route['route_id']}",
        "task_spec_ref": task_spec["task_id"],
        "stage_route_ref": stage_route["route_id"],
        "runtime_candidate_ref": runtime_candidate["candidate_id"],
        "model_candidate_ref": model_ref,
        "selection_scope": "TASK_PINNED" if status == "TASK_PINNED" else selection_scope,
        "status": status,
        "effective_capabilities": effective_capabilities,
        "permission_envelope": permission,
        "context_envelope": {
            "static_prefix": "stable",
            "dynamic_context": "lazy",
            "tool_schema_tokens": int((model_candidate or {}).get("limits", {}).get("max_tool_schema_tokens") or 0),
            "context_tokens": (model_candidate or {}).get("limits", {}).get("context_tokens"),
            "artifact_refs": sorted(set(stage_route.get("evidence_required", []))),
        },
        "tool_envelope": {
            "required_tools": [],
            "mcp_refs": [],
            "schema_tokens": int((model_candidate or {}).get("limits", {}).get("max_tool_schema_tokens") or 0),
            "permission_gated": True,
        },
        "evidence_mode": evidence_mode,
        "provenance": {
            "registry_epoch": stage_route["registry_epoch"],
            "runtime_candidate_ref": runtime_candidate["candidate_id"],
            "model_candidate_ref": model_ref,
            "evidence_class": evidence_mode,
            "source_refs": sorted(set(str(ref) for ref in source_refs)),
        },
    }
    if no_model_work_reason:
        configuration["no_model_work_reason"] = no_model_work_reason
    if reasons:
        configuration["provenance"]["status_reasons"] = reasons
    configuration["configuration_digest"] = _digest_without(configuration, "configuration_digest")
    validation = validate_instance("ExecutionConfiguration", configuration)
    if not validation.valid:
        raise ValueError("invalid execution configuration: " + "; ".join(validation.errors))
    return configuration


def build_runtime_handoff(
    *,
    handoff_id: str,
    task_id: str,
    source_runtime_ref: str,
    destination_runtime_ref: str,
    reason: str,
    portable_artifact_refs: Iterable[str],
    working_tree_state: dict[str, Any],
    permission_envelope: dict[str, Any],
    lost_capabilities: Iterable[str],
    handoff_cost: dict[str, Any],
    evidence_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if source_runtime_ref == destination_runtime_ref:
        raise ValueError("runtime handoff requires distinct source and destination runtimes")
    handoff = {
        "schema_version": "3.0",
        "handoff_id": handoff_id,
        "task_id": task_id,
        "source_runtime_ref": source_runtime_ref,
        "destination_runtime_ref": destination_runtime_ref,
        "reason": reason,
        "handoff_mode": "EXPLICIT",
        "portable_artifact_refs": sorted(set(portable_artifact_refs)),
        "working_tree_state": copy.deepcopy(working_tree_state),
        "permission_envelope": copy.deepcopy(permission_envelope),
        "lost_capabilities": sorted(set(lost_capabilities)),
        "handoff_cost": copy.deepcopy(handoff_cost),
        "evidence_provenance": copy.deepcopy(
            evidence_provenance
            or {"evidence_class": "HOST_MANAGED_FIXTURE", "source": "evaluation-harness", "method": "explicit-record"}
        ),
    }
    validation = validate_instance("RuntimeHandoff", handoff)
    if not validation.valid:
        raise ValueError("invalid runtime handoff: " + "; ".join(validation.errors))
    return handoff


def make_evaluation_run(
    *,
    run_id: str,
    fixture_id: str,
    fixture_set: str,
    task_spec_ref: str,
    stage_route_refs: Iterable[str],
    runtime_candidate_ref: str,
    model_candidate_ref: str | None,
    evidence_class: str,
    execution_mode: str,
    repetition: int,
    status: str,
    execution_configuration_ref: str | None = None,
    measurements: dict[str, Any] | None = None,
    input_artifact_digests: Iterable[str] = (),
) -> dict[str, Any]:
    if evidence_class not in EVIDENCE_CLASSES:
        raise ValueError(f"unsupported evidence class: {evidence_class}")
    if execution_mode != evidence_class:
        raise ValueError("execution mode and evidence class must match")
    run = {
        "schema_version": "3.0",
        "run_id": run_id,
        "fixture_id": fixture_id,
        "fixture_set": fixture_set,
        "task_spec_ref": task_spec_ref,
        "stage_route_refs": sorted(set(stage_route_refs)),
        "execution_configuration_ref": execution_configuration_ref,
        "runtime_candidate_ref": runtime_candidate_ref,
        "model_candidate_ref": model_candidate_ref,
        "selection_scope": "TASK_DEFAULT",
        "evidence_class": evidence_class,
        "execution_mode": execution_mode,
        "repetition": repetition,
        "status": status,
        "input_artifact_digests": sorted(set(input_artifact_digests)),
        "measurements": copy.deepcopy(measurements or {}),
        "history_mode": "APPEND_ONLY",
        "sensitive_data_serialized": False,
    }
    validation = validate_instance("EvaluationRun", run)
    if not validation.valid:
        raise ValueError("invalid evaluation run: " + "; ".join(validation.errors))
    return run


def _quality_values_present(quality: dict[str, Any]) -> bool:
    return any(value is not None for value in quality.values())


def make_evaluation_result(
    *,
    result_id: str,
    run_id: str,
    evidence_class: str,
    outcome: str,
    terminal_outcome: str,
    stage_outcomes: list[dict[str, Any]],
    quality: dict[str, Any],
    efficiency: dict[str, Any],
    reliability: dict[str, Any],
    security: dict[str, Any],
    portability: dict[str, Any],
    provenance: dict[str, Any],
    notes: str | None = None,
) -> dict[str, Any]:
    if evidence_class not in EVIDENCE_CLASSES:
        raise ValueError(f"unsupported evidence class: {evidence_class}")
    if provenance.get("evidence_class") != evidence_class:
        raise ValueError("result provenance evidence class must match the result")
    if evidence_class != "REAL_EXECUTION" and _quality_values_present(quality):
        raise ValueError("non-real evidence cannot carry quality measurements")
    quality_eligible = evidence_class == "REAL_EXECUTION"
    ranking_eligible = quality_eligible and terminal_outcome != "UNKNOWN"
    result: dict[str, Any] = {
        "schema_version": "3.0",
        "result_id": result_id,
        "run_id": run_id,
        "evidence_class": evidence_class,
        "outcome": outcome,
        "terminal_outcome": terminal_outcome,
        "stage_outcomes": copy.deepcopy(stage_outcomes),
        "quality": copy.deepcopy(quality),
        "efficiency": copy.deepcopy(efficiency),
        "reliability": copy.deepcopy(reliability),
        "security": copy.deepcopy(security),
        "portability": copy.deepcopy(portability),
        "quality_evidence_eligible": quality_eligible,
        "ranking_eligible": ranking_eligible,
        "ranking_reason": (
            "REAL_EXECUTION terminal outcome may participate in comparison"
            if ranking_eligible
            else f"{evidence_class} is observation-only for quality comparison"
        ),
        "provenance": copy.deepcopy(provenance),
    }
    if notes:
        result["notes"] = notes
    validation = validate_instance("EvaluationResult", result)
    if not validation.valid:
        raise ValueError("invalid evaluation result: " + "; ".join(validation.errors))
    return result


def _available_candidates(candidates: Iterable[dict[str, Any]], eligible_ids: set[str] | None) -> list[dict[str, Any]]:
    selected = []
    for candidate in candidates:
        if candidate.get("availability") in {"NOT_INSTALLED", "UNKNOWN", "UPSTREAM_ONLY"}:
            continue
        if eligible_ids is not None and candidate.get("candidate_id") not in eligible_ids:
            continue
        selected.append(candidate)
    return sorted(selected, key=lambda item: str(item.get("candidate_id", "")))


def baseline_select(
    task_spec: dict[str, Any],
    candidates: Iterable[dict[str, Any]],
    baseline: str,
    *,
    default_candidate_id: str | None = None,
    eligible_candidate_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Select a compatibility baseline for evaluation only."""

    allowed = {"BASELINE_STRONGEST", "BASELINE_CHEAPEST", "BASELINE_DEFAULT", "BASELINE_HEURISTIC"}
    if baseline not in allowed:
        raise ValueError(f"unsupported baseline: {baseline}")
    pool = _available_candidates(candidates, set(eligible_candidate_ids) if eligible_candidate_ids is not None else None)
    if not pool:
        return {"baseline": baseline, "candidate_id": None, "status": "UNVERIFIED", "policy_status": "EVALUATION_ONLY", "reason": "no eligible candidates"}

    def strongest_key(candidate: dict[str, Any]) -> tuple[int, str]:
        breadth = sum(bool(value) for value in candidate.get("capabilities", {}).values())
        return (-breadth, str(candidate.get("candidate_id", "")))

    def cheapest_key(candidate: dict[str, Any]) -> tuple[int, float, str]:
        cost = candidate.get("cost", {}) or {}
        measured = cost.get("measured_units")
        return (COST_ORDER.get(cost.get("class", "unknown"), COST_ORDER["unknown"]), float(measured) if isinstance(measured, (int, float)) else float("inf"), str(candidate.get("candidate_id", "")))

    if baseline == "BASELINE_STRONGEST":
        chosen = sorted(pool, key=strongest_key)[0]
        reason = "largest declared capability breadth; not a measured quality claim"
    elif baseline == "BASELINE_CHEAPEST":
        chosen = sorted(pool, key=cheapest_key)[0]
        reason = "lowest declared/evaluated cost class; not a quality claim"
    elif baseline == "BASELINE_DEFAULT":
        if default_candidate_id is None:
            return {"baseline": baseline, "candidate_id": None, "status": "UNVERIFIED", "policy_status": "EVALUATION_ONLY", "reason": "default candidate was not supplied"}
        matches = [candidate for candidate in pool if candidate.get("candidate_id") == default_candidate_id]
        if not matches:
            return {"baseline": baseline, "candidate_id": None, "status": "UNVERIFIED", "policy_status": "EVALUATION_ONLY", "reason": "configured default is not eligible"}
        chosen = matches[0]
        reason = "caller-supplied configured default; not a production preference"
    else:
        complexity = task_spec.get("complexity", "STANDARD")
        if complexity == "SIMPLE":
            chosen = sorted(pool, key=cheapest_key)[0]
            reason = "simple-task baseline uses cheapest eligible candidate"
        elif complexity == "COMPLEX":
            chosen = sorted(pool, key=strongest_key)[0]
            reason = "complex-task baseline uses broadest declared capability candidate"
        else:
            chosen = sorted(pool, key=lambda candidate: str(candidate.get("candidate_id", "")))[0]
            reason = "standard-task baseline uses deterministic candidate order"
    return {
        "baseline": baseline,
        "candidate_id": chosen["candidate_id"],
        "status": "SELECTED",
        "policy_status": "EVALUATION_ONLY",
        "reason": reason,
    }


def _numeric_quality(result: dict[str, Any]) -> float | None:
    value = result.get("quality", {}).get("acceptance_criteria_coverage")
    return float(value) if isinstance(value, (int, float)) else None


def _numeric_reliability(result: dict[str, Any]) -> float | None:
    value = result.get("reliability", {}).get("recovery_success")
    return float(value) if isinstance(value, bool) else None


def _dominates(first: dict[str, Any], second: dict[str, Any]) -> bool:
    first_values = (_numeric_quality(first), _numeric_reliability(first), first.get("efficiency", {}).get("cost_units"), first.get("efficiency", {}).get("latency_ms"))
    second_values = (_numeric_quality(second), _numeric_reliability(second), second.get("efficiency", {}).get("cost_units"), second.get("efficiency", {}).get("latency_ms"))
    if any(not isinstance(value, (int, float)) for value in first_values + second_values):
        return False
    quality_ok = first_values[0] >= second_values[0] and first_values[1] >= second_values[1]
    efficiency_ok = first_values[2] <= second_values[2] and first_values[3] <= second_values[3]
    strict = first_values != second_values and (
        first_values[0] > second_values[0]
        or first_values[1] > second_values[1]
        or first_values[2] < second_values[2]
        or first_values[3] < second_values[3]
    )
    return quality_ok and efficiency_ok and strict


def pareto_frontier(results: Iterable[dict[str, Any]]) -> list[str]:
    """Return non-dominated real results without collapsing axes to one score."""

    eligible = [
        result
        for result in results
        if result.get("evidence_class") == "REAL_EXECUTION"
        and result.get("quality_evidence_eligible") is True
        and result.get("ranking_eligible") is True
    ]
    frontier = [
        result
        for result in eligible
        if not any(
            other is not result and _dominates(other, result)
            for other in eligible
        )
    ]
    return sorted(str(result["result_id"]) for result in frontier)


def model_routing_work_required(stage_route: dict[str, Any]) -> dict[str, Any]:
    if stage_route.get("status") == "NO_SKILL_NEEDED":
        return {"required": False, "reason": "NO_SKILL_NEEDED route produces no unnecessary model-routing work"}
    return {"required": True, "reason": "selected skill route may be evaluated within an eligible runtime"}


def live_evidence_gate(
    *,
    completed_configuration_ids: Iterable[str],
    completed_task_classes: Iterable[str],
    repeated_cell_n: int,
    measurement_integrity_blockers: Iterable[str],
    meaningful_comparison: bool,
    secondary_runtime_blocked: bool = False,
) -> dict[str, Any]:
    """Apply the bounded live-evidence decision gate without routing policy."""

    configuration_ids = sorted({str(item) for item in completed_configuration_ids if item})
    task_classes = sorted({str(item) for item in completed_task_classes if item})
    blockers = sorted({str(item) for item in measurement_integrity_blockers if item})
    missing: list[str] = []
    if blockers:
        missing.append("measurement-integrity blocker")
    if len(configuration_ids) < 2:
        missing.append("second completed execution configuration")
    if len(task_classes) < 3:
        missing.append("three materially distinct task classes")
    if repeated_cell_n <= 1:
        missing.append("repeated evidence beyond n=1")
    if not meaningful_comparison:
        missing.append("meaningful live comparison or eligible baseline")

    adequate_primary_evidence = (
        not blockers and len(task_classes) >= 3 and repeated_cell_n > 1
    )
    if blockers:
        verdict = "INSUFFICIENT_LIVE_EVIDENCE"
        reason = "measurement integrity remains unresolved"
    elif len(configuration_ids) >= 2 and not missing:
        verdict = "ROUTING_EVIDENCE_READY"
        reason = "minimum live-evidence gate requirements are present"
    elif secondary_runtime_blocked and adequate_primary_evidence:
        verdict = "RUNTIME_CAPABILITY_GAPS"
        reason = "secondary live configurations are blocked by an unverified runtime boundary"
    else:
        verdict = "INSUFFICIENT_LIVE_EVIDENCE"
        reason = "minimum live-evidence gate requirements are not present"
    return {
        "verdict": verdict,
        "reason": reason,
        "completed_configuration_count": len(configuration_ids),
        "task_class_count": len(task_classes),
        "repeated_cell_n": repeated_cell_n,
        "measurement_integrity_blockers": blockers,
        "missing_requirements": sorted(set(missing)),
    }


def routing_policy_proposal(result_ids: Iterable[str], rationale: str) -> dict[str, Any]:
    """Create proposal data only; never write routing policy."""

    return {
        "schema_version": "3.0",
        "proposal_id": "proposal:" + hashlib.sha256(
            canonical_json({"result_ids": sorted(set(result_ids)), "rationale": rationale}).encode("utf-8")
        ).hexdigest()[:16],
        "status": "PROPOSAL_ONLY",
        "result_ids": sorted(set(result_ids)),
        "rationale": rationale,
        "target": "model-routing-evaluation",
        "requires_human_or_policy_approval": True,
        "applied": False,
        "writes": [],
    }
