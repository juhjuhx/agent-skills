"""Least-privilege permission intersection for v3 adapter preparation."""

from __future__ import annotations

from typing import Any


LEVEL_ORDER = ("read-only", "workspace-write", "external-write", "destructive")
FILESYSTEM_ORDER = (
    "none",
    "read",
    "workspace-read",
    "workspace-write",
    "external-write",
    "destructive",
)
NETWORK_ORDER = ("none", "limited", "standard")

_REQUIRED_TO_RUNTIME = {
    "needs_editing": "editing",
    "needs_browser": "browser",
    "needs_subagents": "subagents",
    "needs_sandbox": "sandbox",
    "needs_MCP": "MCP",
    "needs_structured_output": "structured_output",
    "needs_long_context": "long_context",
    "needs_multimodal": "multimodal",
    "editing": "editing",
    "browser": "browser",
    "subagents": "subagents",
    "sandbox": "sandbox",
    "MCP": "MCP",
    "structured_output": "structured_output",
    "parallelism": "parallelism",
    "long_context": "long_context",
    "multimodal": "multimodal",
}

_MODEL_ONLY_CAPABILITIES = frozenset(
    {"coding", "planning", "debugging", "research", "review", "security", "tool_use"}
)


def _index(order: tuple[str, ...], value: str) -> int:
    try:
        return order.index(value)
    except ValueError:
        return -1


def _minimum_level(values: list[str], order: tuple[str, ...], default: str) -> str:
    known = [value for value in values if value in order]
    return order[min((_index(order, value) for value in known), default=_index(order, default))]


def _manifest_limits(manifest: dict[str, Any]) -> dict[str, Any]:
    permissions = manifest.get("permissions", {})
    scopes = set(permissions.get("declared_scopes", []))
    if "destructive" in scopes:
        level = "destructive"
        filesystem = "destructive"
    elif "external-write" in scopes:
        level = "external-write"
        filesystem = "external-write"
    elif "workspace-write" in scopes:
        level = "workspace-write"
        filesystem = "workspace-write"
    elif "workspace-read" in scopes:
        level = "read-only"
        filesystem = "workspace-read"
    else:
        level = "read-only"
        filesystem = "read"
    return {
        "level": level,
        "filesystem": filesystem,
        "network": "standard" if "network" in scopes else "none",
        "external_write": "external-write" in scopes or "destructive" in scopes,
        "secrets": "secrets" in scopes,
        "publish": "publish" in scopes,
        "delete": "delete" in scopes or "destructive" in scopes,
    }


def _live_limits(live_runtime: dict[str, Any] | None) -> dict[str, Any]:
    live = dict(live_runtime or {})
    sandbox = live.get("sandbox_mode")
    defaults = {
        "level": "read-only",
        "filesystem": "read",
        "network": "none",
        "external_write": False,
        "secrets": False,
        "publish": False,
        "delete": False,
    }
    if sandbox == "workspace-write":
        defaults.update(level="workspace-write", filesystem="workspace-write")
    elif sandbox == "danger-full-access":
        defaults.update(level="destructive", filesystem="destructive")
    defaults.update({key: value for key, value in live.items() if key in defaults})
    if "network_access" in live:
        defaults["network"] = "standard" if live["network_access"] else "none"
    return defaults


def intersect_permissions(
    task_spec: dict[str, Any],
    policy: dict[str, Any] | None,
    adapter_manifest: dict[str, Any],
    live_runtime: dict[str, Any] | None,
    route_budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return an allowed envelope or a blocking result.

    Declarations from a model profile, skill metadata record, MCP record, or
    generated projection are intentionally not accepted as inputs here.
    """

    task_permissions = task_spec.get("permission_requirements", {}) or {}
    policy_limits = dict(policy or {})
    policy_limits.setdefault("level", "read-only")
    policy_limits.setdefault("filesystem", "read")
    policy_limits.setdefault("network", "none")
    for key in ("external_write", "secrets", "publish", "delete"):
        policy_limits.setdefault(key, False)

    adapter_limits = _manifest_limits(adapter_manifest)
    live_limits = _live_limits(live_runtime)
    reasons: list[str] = []

    requested_level = task_permissions.get("level", "read-only")
    if requested_level not in LEVEL_ORDER:
        reasons.append(f"unsupported TaskSpec permission level: {requested_level}")
        requested_level = "read-only"
    route_level = (route_budget or {}).get("permission_level")
    route_filesystem = {
        "read-only": "read",
        "workspace-write": "workspace-write",
        "external-write": "external-write",
        "destructive": "destructive",
    }.get(route_level)
    level_limits = [
        str(policy_limits.get("level", "read-only")),
        adapter_limits["level"],
        live_limits["level"],
    ]
    if route_level is not None:
        level_limits.append(str(route_level))
    available_level = _minimum_level(level_limits, LEVEL_ORDER, "read-only")
    if _index(LEVEL_ORDER, requested_level) > _index(LEVEL_ORDER, available_level):
        reasons.append(
            f"requested permission {requested_level} exceeds intersection {available_level}"
        )

    requested_filesystem = task_permissions.get("filesystem")
    if requested_filesystem is None:
        requested_filesystem = {
            "read-only": "read",
            "workspace-write": "workspace-write",
            "external-write": "external-write",
            "destructive": "destructive",
        }[requested_level]
    if requested_filesystem not in FILESYSTEM_ORDER:
        reasons.append(f"unsupported TaskSpec filesystem permission: {requested_filesystem}")
        requested_filesystem = "read"
    filesystem_limits = [
        str(policy_limits.get("filesystem", "read")),
        adapter_limits["filesystem"],
        live_limits["filesystem"],
    ]
    if route_filesystem is not None:
        filesystem_limits.append(route_filesystem)
    available_filesystem = _minimum_level(filesystem_limits, FILESYSTEM_ORDER, "read")
    if _index(FILESYSTEM_ORDER, requested_filesystem) > _index(
        FILESYSTEM_ORDER, available_filesystem
    ):
        reasons.append(
            f"requested filesystem {requested_filesystem} exceeds intersection {available_filesystem}"
        )

    requested_network = task_permissions.get("network", "none")
    if requested_network not in NETWORK_ORDER:
        reasons.append(f"unsupported TaskSpec network permission: {requested_network}")
        requested_network = "none"
    available_network = _minimum_level(
        [
            str(policy_limits.get("network", "none")),
            adapter_limits["network"],
            live_limits["network"],
        ],
        NETWORK_ORDER,
        "none",
    )
    if _index(NETWORK_ORDER, requested_network) > _index(NETWORK_ORDER, available_network):
        reasons.append(
            f"requested network {requested_network} exceeds intersection {available_network}"
        )

    effective_flags: dict[str, bool] = {}
    for key in ("external_write", "secrets", "publish", "delete"):
        requested = bool(task_permissions.get(key, False))
        available = all(
            bool(source.get(key, False))
            for source in (policy_limits, adapter_limits, live_limits)
        )
        if requested and not available:
            reasons.append(f"TaskSpec requires {key}, but the permission intersection denies it")
        effective_flags[key] = requested and available

    if route_level in LEVEL_ORDER and _index(LEVEL_ORDER, route_level) > _index(
        LEVEL_ORDER, requested_level
    ):
        reasons.append(
            f"route permission {route_level} cannot exceed TaskSpec request {requested_level}"
        )
    elif route_level is not None and route_level not in LEVEL_ORDER:
        reasons.append(f"unsupported route permission level: {route_level}")

    if reasons:
        return {
            "status": "BLOCKED",
            "effective": None,
            "reasons": reasons,
        }

    return {
        "status": "ALLOWED",
        "effective": {
            "level": requested_level,
            "filesystem": requested_filesystem,
            "network": requested_network,
            **effective_flags,
        },
        "reasons": [],
    }


def capability_requirements(
    task_spec: dict[str, Any],
    stage_route: dict[str, Any],
    adapter_manifest: dict[str, Any],
    model_profile: dict[str, Any],
    skill_metadata: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Check capability requirements without selecting or routing skills."""

    required: list[str] = list(task_spec.get("required_capabilities", []))
    for record in skill_metadata or []:
        required.extend(record.get("required_capabilities", []))
    required = list(dict.fromkeys(required))
    granted = set(stage_route.get("granted_capabilities", []))
    adapter_capabilities = adapter_manifest.get("capabilities", {})
    model_capabilities = model_profile.get("capabilities", {})
    missing: list[str] = []
    unknown: list[str] = []
    for requirement in required:
        runtime_capability = _REQUIRED_TO_RUNTIME.get(requirement)
        if runtime_capability is None and requirement in _MODEL_ONLY_CAPABILITIES:
            runtime_capability = requirement
        if runtime_capability is None:
            unknown.append(requirement)
            continue
        if (
            runtime_capability not in _MODEL_ONLY_CAPABILITIES
            and not bool(adapter_capabilities.get(runtime_capability, False))
        ):
            missing.append(f"adapter:{runtime_capability}")
        if runtime_capability not in {"editing", "browser", "subagents", "sandbox", "MCP"} and not bool(
            model_capabilities.get(runtime_capability, False)
        ):
            missing.append(f"model:{runtime_capability}")
        if runtime_capability not in granted:
            missing.append(f"route:{runtime_capability}")
    if unknown:
        missing.extend(f"unknown:{item}" for item in unknown)
    return {
        "status": "BLOCKED" if missing else "ALLOWED",
        "required": required,
        "missing": missing,
        "effective": sorted(
            capability
            for capability, enabled in adapter_capabilities.items()
            if enabled and capability in granted
        ),
    }
