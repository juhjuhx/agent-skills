"""Deterministic, metadata-first Stage Router MVP.

The router selects a minimum sufficient set for one stage. It does not load
skill bodies, choose a model, invoke an adapter, or persist routing state.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

from tools.v3.compatibility import import_skill_index_entry
from tools.v3.contract_validation import KNOWN_CAPABILITIES, validate_instance
from tools.v3.metadata_enrichment import load_enriched_catalog
from tools.v3.routing_catalog import RoutingCatalogSnapshot
from tools.v3.skill_graph import SkillGraph
from tools.v3.skill_scoring import (
    ROLES,
    CandidateScore,
    deep_understanding_gate,
    derive_routing_metadata,
    estimated_cost,
    field_is_enforced,
    field_is_routable,
    is_trivial_task,
    negative_trigger_matches,
    required_roles_for,
    score_candidate,
)


CAPABILITY_MAP = {
    "needs_editing": "editing",
    "needs_browser": "browser",
    "needs_subagents": "subagents",
    "needs_sandbox": "sandbox",
    "needs_MCP": "MCP",
    "needs_structured_output": "structured_output",
    "needs_long_context": "long_context",
    "needs_multimodal": "multimodal",
}

PERMISSION_ORDER = ("read-only", "workspace-write", "external-write", "destructive")
FILESYSTEM_ORDER = (
    "none",
    "read",
    "workspace-read",
    "workspace-write",
    "external-write",
    "destructive",
)

ROLE_ORDER = ("GATE", "PROCESS", "DOMAIN", "TOOL", "REVIEW", "VERIFY")
MINIMUM_SCORE = 4.0
OPTIONAL_SCORE = 7.0
MINIMUM_RELEVANCE = 2.0


class RoutingError(ValueError):
    """A fail-closed route decision error with a stable reason code."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True)
class CandidateEvaluation:
    record: dict[str, Any]
    scores: dict[str, CandidateScore]
    reasons: tuple[str, ...] = ()

    @property
    def best(self) -> CandidateScore | None:
        if not self.scores:
            return None
        return sorted(
            self.scores.values(),
            key=lambda item: (-item.score, ROLE_ORDER.index(item.role), item.skill_id),
        )[0]


def load_current_catalog(path: str | Path) -> list[dict[str, Any]]:
    """Return the current registry with its optional v3 routing overlay."""

    return load_enriched_catalog(path)


def load_current_catalog_snapshot(
    path: str | Path, *, overlay_path: str | Path | None = None
) -> RoutingCatalogSnapshot:
    """Load the current registry once for reuse across stage routes."""

    return RoutingCatalogSnapshot.from_registry(path, overlay_path=overlay_path)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _index(order: tuple[str, ...], value: str) -> int:
    try:
        return order.index(value)
    except ValueError:
        return -1


def _normalise_stage(stage: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(stage, str):
        return {
            "id": stage,
            "objective": stage,
            "task_type": "other",
            "domains": [],
            "required_outputs": [],
            "evidence_required": [],
        }
    if not isinstance(stage, dict):
        raise RoutingError("INVALID_STAGE", "stage must be a stage id or object")
    result = copy.deepcopy(stage)
    result.setdefault("objective", result.get("id", "stage"))
    result.setdefault("task_type", "other")
    result.setdefault("domains", [])
    result.setdefault("required_outputs", [])
    result.setdefault("evidence_required", [])
    stage_id = result.get("id")
    if stage_id not in {
        "understand",
        "research",
        "design",
        "plan",
        "implement",
        "review",
        "verify",
        "harden",
        "handoff",
        "learn",
    }:
        raise RoutingError("INVALID_STAGE", f"unsupported stage id: {stage_id}")
    return result


def _validate_task_spec(task_spec: dict[str, Any]) -> None:
    result = validate_instance("TaskSpec", task_spec)
    if not result.valid:
        raise RoutingError("INVALID_TASKSPEC", "; ".join(result.errors))


def _known_capabilities(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise RoutingError(
                "UNKNOWN_CAPABILITY", f"capability is not a string: {value!r}"
            )
        if value not in KNOWN_CAPABILITIES:
            raise RoutingError(
                "UNKNOWN_CAPABILITY", f"capability is not known: {value}"
            )
        result.append(value)
    return list(dict.fromkeys(result))


def _runtime_capability(value: str) -> str:
    return CAPABILITY_MAP.get(value, value)


def _capability_envelope(
    value: Any,
) -> tuple[dict[str, bool] | None, set[str], str | None]:
    if value is None:
        return None, set(), None
    if not isinstance(value, dict):
        raise RoutingError(
            "INVALID_CAPABILITY_ENVELOPE", "adapter capabilities must be an object"
        )
    runtime_id = (
        value.get("runtime_id") if isinstance(value.get("runtime_id"), str) else None
    )
    raw = value.get("capabilities", value)
    if not isinstance(raw, dict):
        raise RoutingError(
            "INVALID_CAPABILITY_ENVELOPE", "capabilities must be an object"
        )
    capabilities = {
        str(key): bool(enabled)
        for key, enabled in raw.items()
        if isinstance(key, str) and isinstance(enabled, bool)
    }
    tools: set[str] = set()
    for key in ("tools", "available_tools", "tool_names"):
        values = value.get(key)
        if isinstance(values, (list, tuple, set)):
            tools.update(str(item) for item in values)
    return capabilities, tools, runtime_id


def _trust_policy(value: Any) -> set[str]:
    if value is None:
        return {"CORE_TRUSTED", "CURATED"}
    if isinstance(value, (list, tuple, set)):
        allowed = set(str(item) for item in value)
    elif isinstance(value, dict):
        allowed = set(str(item) for item in value.get("allowed_trust", []))
    else:
        raise RoutingError(
            "INVALID_TRUST_POLICY", "trust policy must be a set or object"
        )
    valid = {
        "CORE_TRUSTED",
        "CURATED",
        "COMMUNITY",
        "LOCAL_GENERATED",
        "QUARANTINE",
        "BLOCKED",
    }
    unknown = allowed - valid
    if unknown:
        raise RoutingError(
            "INVALID_TRUST_POLICY", f"unknown trust level: {sorted(unknown)}"
        )
    return allowed


def _task_permission(task_spec: dict[str, Any]) -> tuple[str, str, dict[str, bool]]:
    value = task_spec.get("permission_requirements", {}) or {}
    level = value.get("level", "read-only")
    filesystem = value.get(
        "filesystem",
        {
            "read-only": "read",
            "workspace-write": "workspace-write",
            "external-write": "external-write",
            "destructive": "destructive",
        }.get(level, "read"),
    )
    flags = {
        key: bool(value.get(key, False))
        for key in ("external_write", "secrets", "publish", "delete")
    }
    return str(level), str(filesystem), flags


def _permission_reasons(record: dict[str, Any], task_spec: dict[str, Any]) -> list[str]:
    declaration = record.get("permissions")
    if not declaration:
        return []
    if not isinstance(declaration, dict):
        return ["permissions declaration is not an object"]
    task_level, task_filesystem, task_flags = _task_permission(task_spec)
    reasons: list[str] = []
    declared_filesystem = declaration.get("filesystem")
    if declared_filesystem is not None:
        if declared_filesystem not in FILESYSTEM_ORDER:
            reasons.append(
                f"unsupported skill filesystem permission: {declared_filesystem}"
            )
        elif _index(FILESYSTEM_ORDER, declared_filesystem) > _index(
            FILESYSTEM_ORDER, task_filesystem
        ):
            reasons.append(
                f"skill filesystem {declared_filesystem} exceeds TaskSpec filesystem {task_filesystem}"
            )
    if task_level not in PERMISSION_ORDER:
        reasons.append(f"unsupported TaskSpec permission level: {task_level}")
    declared_secrets = declaration.get("secrets") == "declared"
    if declared_secrets and not task_flags["secrets"]:
        reasons.append("skill declares secrets but TaskSpec does not permit secrets")
    for key in ("external_write", "publish", "delete"):
        if bool(declaration.get(key, False)) and not task_flags[key]:
            reasons.append(f"skill declares {key} but TaskSpec does not permit it")
    return reasons


def _compatibility_reasons(record: dict[str, Any], runtime_id: str) -> list[str]:
    compatibility = record.get("agent_compatibility")
    if not compatibility:
        return []
    matches = [
        item
        for item in compatibility
        if isinstance(item, dict) and item.get("runtime") == runtime_id
    ]
    if not matches:
        return [f"runtime compatibility does not advertise {runtime_id}"]
    if not any(item.get("status") == "supported" for item in matches):
        return [f"runtime compatibility for {runtime_id} is not supported"]
    return []


def _legacy_status(record: dict[str, Any]) -> str | None:
    compatibility = (record.get("extensions", {}) or {}).get("compatibility", {}) or {}
    if compatibility.get("legacy_status") == "DEPRECATED":
        return "DEPRECATED"
    if str(record.get("description", "")).lstrip().lower().startswith("[deprecated:"):
        return "DEPRECATED"
    return None


def _hard_filter(
    record: dict[str, Any],
    task_spec: dict[str, Any],
    stage: dict[str, Any],
    required_capabilities: list[str],
    required_roles: list[str],
    adapter_capabilities: dict[str, bool] | None,
    available_tools: set[str],
    trust_levels: set[str],
    runtime_id: str,
    context_budget: dict[str, Any] | None,
    tool_budget: int | None,
    gate: dict[str, str],
) -> list[str]:
    reasons: list[str] = []
    skill_id = str(record.get("skill_id", ""))
    if record.get("trust") not in trust_levels:
        reasons.append(f"trust level {record.get('trust')} is not allowed")
    if _legacy_status(record):
        reasons.append("skill is deprecated")
    routing_fields = ("roles", "stages", "domains")
    has_routable_field = any(field_is_routable(record, field) for field in routing_fields)
    if not has_routable_field:
        routing_source = (record.get("extensions", {}).get("routing", {}) or {}).get(
            "source"
        )
        reasons.append(
            "metadata lacks a trusted or reviewable routing field"
            if routing_source == "v3_routing_metadata_overlay"
            else "legacy metadata lacks curated routing fields"
        )
    if skill_id == "deep-understanding" or (
        record.get("extensions", {}).get("routing", {}) or {}
    ).get("deep_understanding"):
        if gate["status"] == "OFF":
            reasons.append("Deep Understanding escalation is OFF for this task")
    if record.get("stages") and field_is_enforced(record, "stages"):
        if stage.get("id") not in record.get("stages", []):
            reasons.append(f"stage {stage.get('id')} is not supported by metadata")
    task_type = stage.get("task_type") or task_spec.get("task_type")
    if record.get("task_modes") and field_is_enforced(record, "task_modes"):
        if task_type not in record.get("task_modes", []) and "other" not in record.get(
            "task_modes", []
        ):
            reasons.append(f"task type {task_type} is not supported by metadata")
    requested_domains = set(
        str(item).lower() for item in stage.get("domains", [])
    ) | set(str(item).lower() for item in task_spec.get("domains", []))
    skill_domains = set(str(item).lower() for item in record.get("domains", []))
    broad_requested = requested_domains & {"software-engineering", "repository"}
    broad_skill = skill_domains & {
        "software-engineering",
        "quality-and-safety",
        "repository",
    }
    if requested_domains and skill_domains and not (requested_domains & skill_domains):
        verification_exception = set(record.get("roles", [])) == {
            "VERIFY"
        } and "VERIFY" in set(required_roles)
        if not (broad_requested and broad_skill) and not verification_exception:
            reasons.append("domain metadata is incompatible with the stage")
    for requirement in record.get("required_capabilities", []) or []:
        if requirement not in KNOWN_CAPABILITIES:
            reasons.append(f"unknown required capability: {requirement}")
            continue
        runtime_capability = _runtime_capability(requirement)
        if adapter_capabilities is not None and not adapter_capabilities.get(
            runtime_capability, False
        ):
            reasons.append(f"required capability is unavailable: {runtime_capability}")
    for tool in record.get("tools", []) or []:
        if available_tools and tool not in available_tools:
            reasons.append(f"required tool is unavailable: {tool}")
    for tool in stage.get("required_tools", []) or []:
        if available_tools and tool not in available_tools:
            reasons.append(f"stage-required tool is unavailable: {tool}")
    reasons.extend(_permission_reasons(record, task_spec))
    reasons.extend(_compatibility_reasons(record, runtime_id))
    cost = estimated_cost(record)
    if isinstance(context_budget, dict):
        maximum = context_budget.get("max_input_tokens")
        if isinstance(maximum, int) and cost["instruction_tokens"] > maximum:
            reasons.append(
                f"instruction context estimate {cost['instruction_tokens']} exceeds budget {maximum}"
            )
    if isinstance(tool_budget, int) and cost["tool_calls"] > tool_budget:
        reasons.append(
            f"tool cost estimate {cost['tool_calls']} exceeds budget {tool_budget}"
        )
    if not record.get("roles") or not any(
        role in ROLES and role != "GATE" for role in record.get("roles", [])
    ):
        reasons.append("metadata has no executable role slot")
    if required_capabilities:
        for requirement in required_capabilities:
            if requirement not in KNOWN_CAPABILITIES:
                reasons.append(f"unknown stage capability: {requirement}")
    return list(dict.fromkeys(reasons))


def _route_epoch(catalog: list[dict[str, Any]], explicit: str | None) -> str:
    if explicit:
        return explicit
    refs = [
        f"{record.get('skill_id', '')}:{record.get('source', {}).get('digest', '')}"
        for record in catalog
    ]
    digest = hashlib.sha256("\n".join(sorted(refs)).encode("utf-8")).hexdigest()[:16]
    return f"registry:{digest}"


def _route_id(task_id: str, stage_id: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:16]
    return f"route:{task_id}:{stage_id}:{digest}"


def _budget_envelope(
    task_spec: dict[str, Any], stage: dict[str, Any]
) -> dict[str, Any]:
    permissions = task_spec.get("permission_requirements", {}) or {}
    context = task_spec.get("context_budget", {}) or {}
    latency = task_spec.get("latency_budget", {}) or {}
    result: dict[str, Any] = {
        "permission_level": permissions.get("level", "read-only"),
    }
    if isinstance(context.get("max_input_tokens"), int):
        result["max_input_tokens"] = context["max_input_tokens"]
    if isinstance(context.get("max_artifact_tokens"), int):
        result["max_output_tokens"] = context["max_artifact_tokens"]
    if isinstance(stage.get("max_tool_calls"), int):
        result["max_tool_calls"] = stage["max_tool_calls"]
    elif isinstance(latency.get("max_tool_calls"), int):
        result["max_tool_calls"] = latency["max_tool_calls"]
    if task_spec.get("parallelizable"):
        maximum = stage.get("max_parallel_agents", 0)
        result["max_parallel_agents"] = int(maximum) if isinstance(maximum, int) else 0
    return result


def _selected_reason(
    score: CandidateScore, required: bool, dependency: bool = False
) -> str:
    components = ", ".join(
        f"{key}={value:g}" for key, value in sorted(score.components.items()) if value
    )
    prefix = (
        "required dependency"
        if dependency
        else ("required role" if required else "complementary fit")
    )
    return f"{prefix}; role={score.role}; score={score.score:g}; {components}"


def _relevance_score(score: CandidateScore) -> float:
    return sum(
        score.components.get(name, 0.0)
        for name in (
            "task_relevance",
            "stage_relevance",
            "domain_match",
            "trigger_match",
            "required_output_match",
        )
    )


def _review_independence_required(
    task_spec: dict[str, Any], stage: dict[str, Any]
) -> bool:
    """Detect an explicit need for more than one independent review lane."""

    if stage.get("independent_review_required") is True:
        return True
    evidence = {
        str(item).lower()
        for item in list(stage.get("evidence_required", []))
        + list(stage.get("required_outputs", []))
    }
    if any("independent" in item or "adversarial" in item for item in evidence):
        return True
    lanes = sum(
        any(term in item for term in ("review", "security", "tests", "performance", "source", "runtime"))
        for item in evidence
    )
    return (
        task_spec.get("complexity") == "COMPLEX"
        and task_spec.get("risk") in {"HIGH", "CRITICAL"}
        and stage.get("id") in {"review", "verify", "harden", "handoff"}
        and lanes >= 3
    )


def _role_saturation_limit(
    role: str, task_spec: dict[str, Any], stage: dict[str, Any]
) -> int:
    evidence = {
        str(item).lower()
        for item in list(stage.get("evidence_required", []))
        + list(stage.get("required_outputs", []))
        + list(task_spec.get("artifact_requirements", []))
    }
    if role == "PROCESS" and any(
        term in item for item in evidence for term in ("test", "spec", "plan", "decision")
    ):
        return 2
    if role != "REVIEW":
        return 1
    explicit = stage.get("independent_review_count")
    if isinstance(explicit, int) and explicit >= 1:
        return min(explicit, 3)
    return 2 if _review_independence_required(task_spec, stage) else 1


def _review_signal_requested(
    required_roles: list[str], stage: dict[str, Any]
) -> bool:
    """Allow a review complement only when this stage asks for review evidence."""

    if "REVIEW" in required_roles:
        return True
    evidence = {
        str(item).lower()
        for item in list(stage.get("evidence_required", []))
        + list(stage.get("required_outputs", []))
    }
    return any(
        term in item
        for item in evidence
        for term in ("review", "audit", "security", "quality", "performance")
    )


def _marginal_context_allowed(
    score: CandidateScore,
    *,
    required: bool,
) -> tuple[bool, str | None]:
    """Reject optional high-cost additions whose evidence value is too small."""

    if required:
        return True, None
    context_bytes = score.cost.get("instruction_tokens", 0) * 4
    tool_cost = score.cost.get("tool_calls", 0)
    if context_bytes <= 8192 and tool_cost <= 2:
        return True, None
    benefit = max(0.0, _relevance_score(score))
    benefit += max(0.0, score.components.get("relationship_bonus", 0.0))
    benefit += max(0.0, score.components.get("required_output_match", 0.0))
    pressure = context_bytes / 2048.0 + tool_cost * 1.5
    if pressure > max(8.0, benefit * 1.25):
        return False, (
            f"marginal context cost {context_bytes} bytes/tool cost {tool_cost} "
            f"exceeds evidence value {benefit:g}"
        )
    return True, None


class StageRouter:
    """Route one stage using only the supplied metadata view."""

    def __init__(
        self,
        *,
        adapter: str = "codex",
        model_profile: str = "unselected",
        registry_epoch: str | None = None,
        adapter_capabilities: dict[str, Any] | None = None,
        trust_policy: Any = None,
        context_budget: dict[str, Any] | None = None,
        tool_budget: int | None = None,
    ) -> None:
        self.adapter = adapter
        self.model_profile = model_profile
        self.registry_epoch = registry_epoch
        self.adapter_capabilities = copy.deepcopy(adapter_capabilities)
        self.trust_policy = copy.deepcopy(trust_policy)
        self.context_budget = copy.deepcopy(context_budget)
        self.tool_budget = tool_budget

    def route(
        self,
        task_spec: dict[str, Any],
        stage: str | dict[str, Any],
        catalog: Iterable[dict[str, Any]] | dict[str, Any] | RoutingCatalogSnapshot,
        *,
        adapter_capabilities: dict[str, Any] | None = None,
        trust_policy: Any = None,
        context_budget: dict[str, Any] | None = None,
        tool_budget: int | None = None,
        measure: bool = False,
    ) -> dict[str, Any]:
        route_started = time.perf_counter() if measure else 0.0
        timing_ms: dict[str, float] = {}
        normalized_stage = _normalise_stage(stage)
        _validate_task_spec(task_spec)
        required_capabilities = _known_capabilities(
            list(task_spec.get("required_capabilities", []))
            + list(normalized_stage.get("required_capabilities", []))
        )
        adapter_caps, available_tools, manifest_runtime = _capability_envelope(
            self.adapter_capabilities
            if adapter_capabilities is None
            else adapter_capabilities
        )
        runtime_id = manifest_runtime or self.adapter
        required_runtime_capabilities = {
            _runtime_capability(requirement) for requirement in required_capabilities
        }
        if adapter_caps is not None:
            missing_runtime = sorted(
                capability
                for capability in required_runtime_capabilities
                if capability not in KNOWN_CAPABILITIES
                or not adapter_caps.get(capability, False)
            )
            if missing_runtime:
                raise RoutingError(
                    "CAPABILITY_UNAVAILABLE",
                    "adapter capability envelope cannot satisfy: "
                    + ", ".join(missing_runtime),
                )
        trust_levels = _trust_policy(
            self.trust_policy if trust_policy is None else trust_policy
        )
        effective_context_budget = (
            self.context_budget
            if context_budget is None and self.context_budget is not None
            else context_budget
            if context_budget is not None
            else task_spec.get("context_budget")
        )
        effective_tool_budget = (
            self.tool_budget
            if tool_budget is None and self.tool_budget is not None
            else tool_budget
            if tool_budget is not None
            else None
        )
        snapshot = catalog if isinstance(catalog, RoutingCatalogSnapshot) else None
        if snapshot is not None:
            records = list(snapshot.records)
            timing_ms["metadata_derivation_ms"] = 0.0
            timing_ms["schema_validation_ms"] = 0.0
        elif isinstance(catalog, dict):
            raw_records = catalog.get("skills")
            if not isinstance(raw_records, list):
                raise RoutingError(
                    "INVALID_CATALOG", "catalog object must contain a skills list"
                )
            records = [
                import_skill_index_entry(item, catalog)
                if isinstance(item, dict) and "relative_path" in item
                else item
                for item in raw_records
            ]
        else:
            records = list(catalog)
        effective_records: list[dict[str, Any]] = list(records) if snapshot is not None else []
        invalid_records: list[dict[str, Any]] = []
        if snapshot is None:
            metadata_elapsed = 0.0
            schema_elapsed = 0.0
            for record in records:
                if not isinstance(record, dict):
                    invalid_records.append(
                        {
                            "skill_id": str(record),
                            "reasons": ["metadata record is not an object"],
                        }
                    )
                    continue
                metadata_step = time.perf_counter() if measure else 0.0
                candidate = derive_routing_metadata(record)
                if measure:
                    metadata_elapsed += (time.perf_counter() - metadata_step) * 1000
                schema_step = time.perf_counter() if measure else 0.0
                validation = validate_instance("SkillMetadataV3", candidate)
                if measure:
                    schema_elapsed += (time.perf_counter() - schema_step) * 1000
                if not validation.valid:
                    invalid_records.append(
                        {
                            "skill_id": str(candidate.get("skill_id", "invalid")),
                            "reasons": [
                                "invalid metadata: " + "; ".join(validation.errors)
                            ],
                        }
                    )
                    continue
                effective_records.append(candidate)
            if measure:
                timing_ms["metadata_derivation_ms"] = round(metadata_elapsed, 3)
                timing_ms["schema_validation_ms"] = round(schema_elapsed, 3)

        epoch = self.registry_epoch or (
            snapshot.registry_epoch if snapshot is not None else _route_epoch(effective_records, None)
        )
        graph_started = time.perf_counter() if measure else 0.0
        graph = snapshot.graph if snapshot is not None else SkillGraph(effective_records)
        if measure:
            timing_ms["graph_construction_ms"] = (
                0.0
                if snapshot is not None
                else round((time.perf_counter() - graph_started) * 1000, 3)
            )
        gate = deep_understanding_gate(task_spec, normalized_stage)
        deep_ids = {
            record["skill_id"]
            for record in effective_records
            if record.get("skill_id") == "deep-understanding"
            or (record.get("extensions", {}).get("routing", {}) or {}).get(
                "deep_understanding"
            )
        }
        if gate["status"] == "ELIGIBLE" and not deep_ids:
            deep_status = {
                "status": "UNAVAILABLE",
                "reason": "no Deep Understanding record is present in the supplied catalog",
            }
        else:
            deep_status = dict(gate)

        required_roles = required_roles_for(task_spec, normalized_stage)
        unknown_roles = [role for role in required_roles if role not in ROLES]
        if unknown_roles:
            raise RoutingError(
                "INVALID_ROLE", f"unknown required role(s): {', '.join(unknown_roles)}"
            )

        scoring_started = time.perf_counter() if measure else 0.0
        evaluations: dict[str, CandidateEvaluation] = {}
        negative_signal_effects: list[str] = []
        available_ids = {record["skill_id"] for record in effective_records}
        for record in effective_records:
            skill_id = record["skill_id"]
            if skill_id == "using-superpowers":
                # This is resident task/session authority, not a normal scored
                # candidate and not a repeated body load.
                continue
            reasons = _hard_filter(
                record,
                task_spec,
                normalized_stage,
                required_capabilities,
                required_roles,
                adapter_caps,
                available_tools,
                trust_levels,
                runtime_id,
                effective_context_budget,
                effective_tool_budget,
                gate,
            )
            scores: dict[str, CandidateScore] = {}
            if not reasons:
                for role in record.get("roles", []):
                    if role in ROLES and role != "GATE":
                        score = score_candidate(
                            record,
                            task_spec,
                            normalized_stage,
                            [role],
                        )
                        if score is not None:
                            scores[role] = score
                            negative_penalty = score.components.get(
                                "negative_trigger_penalty", 0.0
                            )
                            if negative_penalty:
                                negative_signal_effects.append(
                                    f"{skill_id}: negative trigger penalty {negative_penalty:g}"
                                )
                                for signal in negative_trigger_matches(
                                    record, task_spec, normalized_stage
                                ):
                                    negative_signal_effects.append(
                                        f"{skill_id}: negative signal {signal}"
                                    )
                if not scores:
                    reasons.append("metadata has no scoreable role for this stage")
            evaluations[skill_id] = CandidateEvaluation(record, scores, tuple(reasons))

        superseded = graph.superseded_ids(
            {
                skill_id
                for skill_id, evaluation in evaluations.items()
                if not evaluation.reasons
            }
        )
        for legacy, successor in superseded.items():
            evaluation = evaluations[legacy]
            evaluations[legacy] = replace(
                evaluation,
                reasons=tuple(
                    list(evaluation.reasons) + [f"SUPERSEDED by {successor}"]
                ),
            )

        eligible_ids = {
            skill_id
            for skill_id, evaluation in evaluations.items()
            if not evaluation.reasons and evaluation.best is not None
        }
        for skill_id in sorted(eligible_ids):
            try:
                dependencies = graph.required_dependencies(skill_id)
            except (KeyError, ValueError) as exc:
                evaluation = evaluations[skill_id]
                evaluations[skill_id] = replace(
                    evaluation,
                    reasons=tuple(list(evaluation.reasons) + [str(exc)]),
                )
                continue
            missing = [
                dependency
                for dependency in dependencies
                if dependency not in available_ids or dependency not in eligible_ids
            ]
            if missing:
                evaluation = evaluations[skill_id]
                evaluations[skill_id] = replace(
                    evaluation,
                    reasons=tuple(
                        list(evaluation.reasons)
                        + [
                            f"required dependency unavailable: {', '.join(sorted(missing))}"
                        ]
                    ),
                )

        eligible_ids = {
            skill_id
            for skill_id, evaluation in evaluations.items()
            if not evaluation.reasons and evaluation.best is not None
        }
        marginal_cost_effects: list[str] = []
        role_saturation_effects: list[str] = []
        if is_trivial_task(task_spec, normalized_stage):
            if measure:
                timing_ms["candidate_scoring_ms"] = round(
                    (time.perf_counter() - scoring_started) * 1000, 3
                )
            route = self._build_route(
                task_spec,
                normalized_stage,
                effective_records,
                evaluations,
                [],
                epoch,
                required_roles,
                required_capabilities,
                available_tools,
                deep_status,
                "trivial low-risk task has no required procedure; no skill is needed",
                adapter_capabilities=adapter_caps,
                invalid_records=invalid_records,
                catalog_snapshot=snapshot,
                timing_ms=timing_ms if measure else None,
                route_started=route_started,
                negative_signal_effects=negative_signal_effects,
                role_saturation_effects=role_saturation_effects,
                marginal_cost_effects=marginal_cost_effects,
            )
            validation = validate_instance("StageRoute", route)
            if not validation.valid:
                raise RoutingError("INVALID_ROUTE", "; ".join(validation.errors))
            return route

        selected: dict[str, CandidateScore] = {}
        selected_reasons: dict[str, str] = {}
        relationship_effects: list[str] = []
        rejected_selection: dict[str, list[str]] = {}
        required_artifacts = {
            str(item).lower()
            for item in (
                list(normalized_stage.get("required_outputs", []))
                + list(normalized_stage.get("evidence_required", []))
                + list(task_spec.get("artifact_requirements", []))
            )
        }
        covered_artifacts: set[str] = set()

        def record_outputs(skill_id: str) -> set[str]:
            record = evaluations[skill_id].record
            return {str(item).lower() for item in record.get("outputs", []) or []}

        def refreshed_score(
            skill_id: str, role: str | None = None
        ) -> CandidateScore | None:
            evaluation = evaluations.get(skill_id)
            if evaluation is None:
                return None
            base = evaluation.scores.get(role) if role else evaluation.best
            if base is None:
                return None
            bonus, effects = graph.positive_effects(skill_id, selected)
            relationship_effects.extend(effects)
            selected_role_count = sum(
                item.role == base.role for item in selected.values()
            )
            saturation_penalty = float(selected_role_count) if selected_role_count else 0.0
            return replace(
                base,
                score=round(base.score + bonus - saturation_penalty, 3),
                components={
                    **base.components,
                    "relationship_bonus": bonus,
                    "role_saturation_penalty": -saturation_penalty,
                },
            )

        def can_add(
            skill_id: str, *, dependency: bool = False, role: str | None = None
        ) -> tuple[bool, list[str]]:
            evaluation = evaluations.get(skill_id)
            if evaluation is None:
                return False, ["candidate is not in the eligible catalog"]
            for existing_id in selected:
                if graph.conflicts(skill_id, existing_id):
                    relationship_effects.append(f"CONFLICTS:{skill_id}<->{existing_id}")
                    return False, [f"CONFLICTS with {existing_id}"]
                if graph.alternatives(skill_id, existing_id):
                    relationship_effects.append(
                        f"ALTERNATIVE_TO:{skill_id}<->{existing_id}"
                    )
                    return False, [
                        f"ALTERNATIVE_TO {existing_id}; one alternative is sufficient"
                    ]
            if not dependency:
                candidate_role = role or (evaluation.best.role if evaluation.best else None)
                if candidate_role:
                    selected_count = sum(
                        item.role == candidate_role for item in selected.values()
                    )
                    limit = _role_saturation_limit(
                        candidate_role, task_spec, normalized_stage
                    )
                    if selected_count >= limit:
                        reason = (
                            f"role saturation: {candidate_role} already has "
                            f"{selected_count} selected skill(s); limit {limit}"
                        )
                        role_saturation_effects.append(
                            f"{skill_id}: {reason}"
                        )
                        return False, [reason]
            return True, []

        def add(
            skill_id: str,
            *,
            required: bool,
            dependency: bool = False,
            role: str | None = None,
        ) -> bool:
            if skill_id in selected:
                return True
            evaluation = evaluations.get(skill_id)
            if evaluation is None or evaluation.reasons:
                rejected_selection.setdefault(skill_id, []).extend(
                    list(
                        evaluation.reasons
                        if evaluation
                        else ("candidate is not in the eligible catalog",)
                    )
                )
                return False
            allowed, reasons = can_add(
                skill_id, dependency=dependency, role=role
            )
            if not allowed:
                rejected_selection.setdefault(skill_id, []).extend(reasons)
                return False
            for dependency_id in graph.required_dependencies(skill_id):
                if dependency_id not in selected and not add(
                    dependency_id, required=True, dependency=True
                ):
                    rejected_selection.setdefault(skill_id, []).append(
                        f"required dependency could not be added: {dependency_id}"
                    )
                    return False
                relationship_effects.append(f"REQUIRES:{skill_id}->{dependency_id}")
            score = refreshed_score(skill_id, role)
            if score is None:
                rejected_selection.setdefault(skill_id, []).append(
                    "candidate has no score for a role slot"
                )
                return False
            selected[skill_id] = score
            selected_reasons[skill_id] = _selected_reason(score, required, dependency)
            covered_artifacts.update(record_outputs(skill_id))
            return True

        # Cover explicitly required or policy-derived roles first. This is a
        # diversity pass, not a fixed skill quota.
        for required_role in required_roles:
            options: list[CandidateScore] = []
            for skill_id in sorted(eligible_ids):
                if skill_id in selected:
                    continue
                score = refreshed_score(skill_id, required_role)
                if score is not None and score.role == required_role:
                    options.append(score)
            options.sort(key=lambda item: (-item.score, item.skill_id))
            for option in options:
                if (
                    option.score >= MINIMUM_SCORE
                    and _relevance_score(option) >= MINIMUM_RELEVANCE
                    and add(option.skill_id, required=True, role=required_role)
                ):
                    break

        # Add an optional candidate only when it is a strong fit and expands
        # the role/relationship complement. No aesthetic maximum is imposed.
        all_options: list[CandidateScore] = []
        for skill_id in sorted(eligible_ids):
            if skill_id in selected:
                continue
            score = refreshed_score(skill_id)
            if score is not None:
                all_options.append(score)
        all_options.sort(
            key=lambda item: (-item.score, ROLE_ORDER.index(item.role), item.skill_id)
        )
        covered_roles = {score.role for score in selected.values()}
        review_signal_requested = _review_signal_requested(
            required_roles, normalized_stage
        )
        for option in all_options:
            if (
                option.score < OPTIONAL_SCORE
                or _relevance_score(option) < MINIMUM_RELEVANCE
            ):
                continue
            role_is_new = option.role not in covered_roles
            has_relation = option.components.get("relationship_bonus", 0) > 0
            new_artifacts = (
                record_outputs(option.skill_id) & required_artifacts
            ) - covered_artifacts
            # Unrequested roles are not a reason to load another skill. An
            # optional candidate may add a role only when the stage explicitly
            # requires that role; otherwise it needs an actual graph signal.
            role_is_required = option.role in required_roles
            expands_required_artifact = role_is_required and bool(new_artifacts)
            if (
                (role_is_new and role_is_required)
                or has_relation
                or expands_required_artifact
                or (
                    option.role == "REVIEW"
                    and review_signal_requested
                    and _role_saturation_limit(
                        "REVIEW", task_spec, normalized_stage
                    )
                    > sum(item.role == "REVIEW" for item in selected.values())
                )
            ):
                allowed, cost_reason = _marginal_context_allowed(
                    option, required=False
                )
                if not allowed:
                    reason = cost_reason or "marginal context cost is not justified"
                    marginal_cost_effects.append(f"{option.skill_id}: {reason}")
                    rejected_selection.setdefault(option.skill_id, []).append(
                        f"context cost gate: {reason}"
                    )
                    continue
                if add(option.skill_id, required=False):
                    covered_roles.add(option.role)

        for skill_id in sorted(eligible_ids - set(selected)):
            if negative_signal_effects and any(
                item.startswith(f"{skill_id}:") for item in negative_signal_effects
            ):
                rejected_selection.setdefault(skill_id, []).append(
                    "negative routing signal matched; optional activation suppressed"
                )
            for existing_id in sorted(selected):
                if graph.conflicts(skill_id, existing_id):
                    relationship_effects.append(f"CONFLICTS:{skill_id}<->{existing_id}")
                elif graph.alternatives(skill_id, existing_id):
                    relationship_effects.append(
                        f"ALTERNATIVE_TO:{skill_id}<->{existing_id}"
                    )

        substantive_selected = dict(selected)
        if substantive_selected and "using-superpowers" in available_ids:
            gate_score = CandidateScore(
                "using-superpowers",
                "GATE",
                0.0,
                {"resident_authority": 0.0, "historical_evidence": 0.0},
                {
                    "metadata_tokens": 0,
                    "instruction_tokens": 0,
                    "tool_schema_tokens": 0,
                    "tool_calls": 0,
                },
            )
            selected = {"using-superpowers": gate_score, **selected}
            selected_reasons["using-superpowers"] = (
                "resident task/session orchestration authority; referenced as GATE without reloading its full body"
            )

        if measure:
            timing_ms["candidate_scoring_ms"] = round(
                (time.perf_counter() - scoring_started) * 1000, 3
            )
        route = self._build_route(
            task_spec,
            normalized_stage,
            effective_records,
            evaluations,
            list(selected.values()),
            epoch,
            required_roles,
            required_capabilities,
            available_tools,
            deep_status,
            "",
            adapter_capabilities=adapter_caps,
            selected_reasons=selected_reasons,
            relationship_effects=relationship_effects,
            rejected_selection=rejected_selection,
            invalid_records=invalid_records,
            catalog_snapshot=snapshot,
            timing_ms=timing_ms if measure else None,
            route_started=route_started,
            negative_signal_effects=negative_signal_effects,
            role_saturation_effects=role_saturation_effects,
            marginal_cost_effects=marginal_cost_effects,
        )
        if deep_status.get("status") == "ELIGIBLE" and "deep-understanding" in selected:
            route["routing_evidence"]["deep_understanding"] = {
                "status": "SELECTED",
                "reason": deep_status["reason"],
                "skill_id": "deep-understanding",
            }
        validation = validate_instance("StageRoute", route)
        if not validation.valid:
            raise RoutingError("INVALID_ROUTE", "; ".join(validation.errors))
        return route

    def _build_route(
        self,
        task_spec: dict[str, Any],
        stage: dict[str, Any],
        records: list[dict[str, Any]],
        evaluations: dict[str, CandidateEvaluation],
        selected_scores: list[CandidateScore],
        epoch: str,
        required_roles: list[str],
        required_capabilities: list[str],
        available_tools: set[str],
        deep_status: dict[str, str],
        no_skill_reason: str,
        *,
        adapter_capabilities: dict[str, bool] | None,
        selected_reasons: dict[str, str] | None = None,
        relationship_effects: list[str] | None = None,
        rejected_selection: dict[str, list[str]] | None = None,
        invalid_records: list[dict[str, Any]] | None = None,
        catalog_snapshot: RoutingCatalogSnapshot | None = None,
        timing_ms: dict[str, float] | None = None,
        route_started: float = 0.0,
        negative_signal_effects: list[str] | None = None,
        role_saturation_effects: list[str] | None = None,
        marginal_cost_effects: list[str] | None = None,
    ) -> dict[str, Any]:
        selected_reasons = selected_reasons or {}
        relationship_effects = relationship_effects or []
        rejected_selection = rejected_selection or {}
        invalid_records = invalid_records or []
        negative_signal_effects = negative_signal_effects or []
        role_saturation_effects = role_saturation_effects or []
        marginal_cost_effects = marginal_cost_effects or []
        if timing_ms is not None and route_started:
            timing_ms = dict(timing_ms)
            timing_ms["total_route_ms"] = round(
                (time.perf_counter() - route_started) * 1000, 3
            )
        selected_scores = sorted(
            selected_scores,
            key=lambda item: (ROLE_ORDER.index(item.role), item.skill_id),
        )
        selected_ids = {item.skill_id for item in selected_scores}
        status = "SKILLS_SELECTED" if selected_scores else "NO_SKILL_NEEDED"
        substantive = [item for item in selected_scores if item.role != "GATE"]
        if not no_skill_reason and not selected_scores:
            no_skill_reason = "no candidate met the stage relevance, trust, capability, role, and budget gates"
        if status == "NO_SKILL_NEEDED":
            selected_reasons = {}
        assignments = [
            {"skill_id": item.skill_id, "role": item.role} for item in selected_scores
        ]
        selected_route_skills = [
            {
                "skill_id": item.skill_id,
                "role": item.role,
                "reason": selected_reasons.get(
                    item.skill_id, _selected_reason(item, False)
                ),
            }
            for item in selected_scores
        ]
        role_coverage = list(dict.fromkeys(item.role for item in selected_scores))
        context_bytes_estimate = sum(
            item.cost["instruction_tokens"] * 4 for item in substantive
        )
        tool_requirements = sorted(
            {
                str(tool)
                for record in records
                if record.get("skill_id") in selected_ids
                for tool in record.get("tools", []) or []
            }
        )
        selected_candidates = [
            {
                "skill_id": item.skill_id,
                "role": item.role,
                "score": item.score,
                "components": item.components,
                "reason_codes": [
                    "resident_authority" if item.role == "GATE" else "role_coverage",
                    "metadata_only",
                ],
            }
            for item in selected_scores
        ]
        rejected: list[dict[str, Any]] = []
        for skill_id, evaluation in evaluations.items():
            reasons = list(evaluation.reasons)
            if skill_id in rejected_selection:
                reasons.extend(rejected_selection[skill_id])
            if skill_id in selected_ids:
                continue
            score = evaluation.best.score if evaluation.best else None
            if reasons:
                item = {"skill_id": skill_id, "reasons": list(dict.fromkeys(reasons))}
                if score is not None:
                    item["score"] = score
                rejected.append(item)
        rejected.sort(
            key=lambda item: (
                -(item["score"] if isinstance(item.get("score"), (int, float)) else -1),
                item["skill_id"],
            )
        )
        for item in rejected_selection:
            if item not in evaluations and item not in selected_ids:
                rejected.append(
                    {
                        "skill_id": item,
                        "reasons": list(dict.fromkeys(rejected_selection[item])),
                    }
                )
        rejected.extend(invalid_records)
        filtered_count = len(rejected)
        eligible_count = len(evaluations) - sum(
            1 for evaluation in evaluations.values() if evaluation.reasons
        )
        route_reasons = [
            f"metadata-first stage-local routing inspected {len(records)} records without loading SKILL.md bodies",
            "historical success is observation-only and contributes no production score weight",
        ]
        if status == "SKILLS_SELECTED":
            route_reasons.append(
                "selected a minimum sufficient complement covering roles: "
                + ", ".join(role_coverage)
            )
        else:
            route_reasons.append(no_skill_reason)
        if "using-superpowers" in selected_ids:
            route_reasons.append(
                "using-superpowers is referenced as the resident GATE authority; its full instructions are not reloaded per stage"
            )
        if relationship_effects:
            route_reasons.append(
                "relationship effects were applied: "
                + ", ".join(sorted(set(relationship_effects)))
            )
        route_reasons = list(dict.fromkeys(route_reasons))
        budget = _budget_envelope(task_spec, stage)
        route_payload = {
            "task_id": task_spec["task_id"],
            "stage": stage["id"],
            "epoch": epoch,
            "selected": selected_route_skills,
            "status": status,
        }
        route: dict[str, Any] = {
            "schema_version": "3.0",
            "route_id": _route_id(task_spec["task_id"], stage["id"], route_payload),
            "task_id": task_spec["task_id"],
            "stage": stage["id"],
            "registry_epoch": epoch,
            "status": status,
            "selected_skills": selected_route_skills,
            "role_assignments": assignments,
            "adapter": self.adapter,
            "model_profile": self.model_profile,
            "granted_capabilities": sorted(
                {
                    _runtime_capability(requirement)
                    for requirement in required_capabilities
                    if _runtime_capability(requirement) in KNOWN_CAPABILITIES
                    and (
                        adapter_capabilities is None
                        or adapter_capabilities.get(
                            _runtime_capability(requirement), False
                        )
                    )
                }
            ),
            "budget_envelope": budget,
            "alternatives": [
                {
                    "skill_id": item["skill_id"],
                    "reason": (
                        "higher-ranked complementary candidate was selected"
                        if item.get("score") is not None
                        else "; ".join(item["reasons"])
                    ),
                }
                for item in rejected[:8]
                if item["skill_id"] not in selected_ids
            ],
            "route_reasons": route_reasons,
            "evidence_required": list(
                dict.fromkeys(str(item) for item in stage.get("evidence_required", []))
            ),
            "routing_evidence": {
                "candidate_count": len(records),
                "filtered_count": filtered_count,
                "eligible_count": max(0, eligible_count),
                "selected_count": len(selected_route_skills),
                "required_roles": required_roles,
                "role_coverage": role_coverage,
                "duplicate_role_pressure": max(
                    0, len(substantive) - len({item.role for item in substantive})
                ),
                "context_bytes_estimate": context_bytes_estimate,
                "body_files_loaded": 0,
                "body_bytes_loaded": 0,
                "tool_requirements": tool_requirements,
                "trust_blocks": sum(
                    1
                    for evaluation in evaluations.values()
                    if any("trust" in reason.lower() for reason in evaluation.reasons)
                ),
                "relationship_effects": sorted(set(relationship_effects)),
                "metadata_records_inspected": len(records),
                "selected_candidates": selected_candidates,
                "rejected_candidates": rejected[:32],
                "deep_understanding": deep_status,
                "negative_signal_effects": sorted(set(negative_signal_effects)),
                "role_saturation": {
                    "review_limit": _role_saturation_limit(
                        "REVIEW", task_spec, stage
                    ),
                    "independent_review_required": _review_independence_required(
                        task_spec, stage
                    ),
                    "same_role_rejections": sorted(set(role_saturation_effects)),
                },
                "marginal_cost_effects": sorted(set(marginal_cost_effects)),
            },
        }
        if catalog_snapshot is not None:
            route["routing_evidence"]["catalog_snapshot"] = catalog_snapshot.evidence()
        if timing_ms is not None:
            route["routing_evidence"]["timings_ms"] = timing_ms
        if status == "NO_SKILL_NEEDED":
            route["no_skill_reason"] = no_skill_reason
        return route


def route_stage(
    task_spec: dict[str, Any],
    stage: str | dict[str, Any],
    catalog: Iterable[dict[str, Any]] | dict[str, Any],
    *,
    adapter: str = "codex",
    model_profile: str = "unselected",
    registry_epoch: str | None = None,
    adapter_capabilities: dict[str, Any] | None = None,
    trust_policy: Any = None,
    context_budget: dict[str, Any] | None = None,
    tool_budget: int | None = None,
    measure: bool = False,
) -> dict[str, Any]:
    """Convenience function for one deterministic stage route."""

    return StageRouter(
        adapter=adapter,
        model_profile=model_profile,
        registry_epoch=registry_epoch,
        adapter_capabilities=adapter_capabilities,
        trust_policy=trust_policy,
        context_budget=context_budget,
        tool_budget=tool_budget,
    ).route(task_spec, stage, catalog, measure=measure)
