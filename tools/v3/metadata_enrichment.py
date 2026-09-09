"""Offline, read-only enrichment for the v3 routing metadata overlay.

The canonical ``SKILL.md`` remains the procedure source. This module derives
small routing records from the current registry and skill bodies, but never
executes body commands, follows URLs, installs dependencies, or mutates the
canonical registry. Runtime consumers load the generated overlay only;
``check_bodies=True`` is reserved for maintenance-time freshness checks.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from tools.v3.compatibility import import_skill_index_entry, load_current_registry
from tools.v3.contract_validation import validate_instance
from tools.v3.skill_scoring import ROUTING_HINTS


OVERLAY_VERSION = "v3-routing-metadata-1"
GENERATOR_VERSION = "0.1.0"
OVERLAY_SOURCE = "v3_routing_metadata_overlay"
DEFAULT_OVERLAY_RELATIVE_PATH = Path("registry/v3/skill-routing-metadata.json")

PROVENANCE_LEVELS = (
    "AUTHOR_DECLARED",
    "CURATED",
    "INFERRED_HIGH_CONFIDENCE",
    "INFERRED",
    "UNKNOWN",
)
PROVENANCE_WEIGHTS = {
    "AUTHOR_DECLARED": 1.0,
    "CURATED": 1.0,
    "INFERRED_HIGH_CONFIDENCE": 0.8,
    "INFERRED": 0.55,
    "UNKNOWN": 0.0,
}
ROUTING_FIELDS = ("roles", "stages", "task_modes", "domains")
OVERLAY_CENSUS_FIELDS = (
    "roles",
    "stages",
    "task_modes",
    "domains",
    "triggers",
    "inputs",
    "outputs",
    "required_capabilities",
    "tools",
    "permissions",
    "context_cost",
    "runtime_cost",
    "relationships",
    "agent_compatibility",
    "trust",
    "source",
    "source.license",
    "version",
    "eval_status",
    "risk",
    "extensions.routing",
)
CLASSIFICATIONS = (
    "ROUTING_READY",
    "PARTIAL",
    "LEGACY_MINIMAL",
    "AMBIGUOUS",
    "DEPRECATED",
)
TIERS = (
    "TIER_1_CORE",
    "TIER_2_DOMAIN",
    "TIER_3_SPECIALIZED",
    "TIER_4_DEPRECATED",
)

CAPABILITY_RESOLUTION = {
    "source-driven-development": {
        "status": "REGISTRY_GAP",
        "registry_skill_ids": [],
        "note": "installed donor exists outside the 214-record registry; no exact canonical registry ID",
    },
    "deep-understanding": {
        "status": "REGISTRY_GAP",
        "registry_skill_ids": [],
        "note": "installed workflow exists outside the 214-record registry; no exact canonical registry ID",
    },
    "security-hardening": {
        "status": "REGISTRY_GAP",
        "registry_skill_ids": ["safe-mode", "permission-tuner"],
        "note": "exact donor name is outside the registry; these current IDs are conservative security proxies, not aliases",
    },
    "api-and-interface-design": {
        "status": "REGISTRY_GAP",
        "registry_skill_ids": ["improve-codebase-architecture", "grill-with-docs"],
        "note": "exact donor name is outside the registry; proxies cover architecture/decision work but not a full API discipline",
    },
    "mcp-audit": {
        "status": "DIRECT",
        "registry_skill_ids": ["mcp-audit"],
        "note": "exact canonical registry ID is present",
    },
    "context-engineering": {
        "status": "DIRECT",
        "registry_skill_ids": ["context-engineering"],
        "note": "exact canonical registry ID is present",
    },
}

ROLE_ORDER = ("GATE", "PROCESS", "DOMAIN", "TOOL", "REVIEW", "VERIFY")
STAGES = (
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
)

CATEGORY_DOMAINS = {
    "software-engineering": "software-engineering",
    "quality-and-safety": "quality-and-safety",
    "design-and-frontend": "frontend",
    "media-and-images": "visual-design",
    "documents-and-publishing": "documentation",
    "orchestration": "orchestration",
    "context-and-cost": "context-engineering",
    "integrations-and-data": "integrations",
    "general": "general",
}

STAGE_TERMS = {
    "understand": ("understand", "inspect", "architecture", "diagnos", "debug", "map", "onboard"),
    "research": ("research", "source", "web", "search", "official", "wiki", "knowledge", "docs"),
    "design": ("design", "ui", "visual", "frontend", "brand", "prototype", "brainstorm", "image", "slide"),
    "plan": ("plan", "spec", "prd", "roadmap", "requirement", "strategy", "break down"),
    "implement": ("implement", "build", "create", "develop", "write", "fix", "generate", "code", "convert"),
    "review": ("review", "audit", "quality", "lint", "health", "simplif", "security", "accessibility", "performance", "permission"),
    "verify": ("verif", "test", "validation", "evidence", "complete", "passing", "check"),
    "harden": ("security", "hardening", "permission", "safe", "lockdown", "guard"),
    "handoff": ("handoff", "release", "ship", "publish", "wrap-up", "session"),
    "learn": ("learn", "distill", "candidate", "promotion", "knowledge"),
}
MODE_TERMS = {
    "bugfix": ("bug", "debug", "diagnos", "crash", "failing", "exception", "wrong output"),
    "implementation": ("implement", "build", "create", "develop", "write", "feature", "code", "fix"),
    "research": ("research", "source", "web", "search", "official", "wiki", "knowledge"),
    "review": ("review", "audit", "quality", "security", "performance", "lint", "health"),
    "design": ("design", "ui", "visual", "frontend", "brand", "prototype", "image"),
    "documentation": ("document", "docs", "readme", "markdown", "adr", "write-up"),
    "handoff": ("handoff", "release", "ship", "publish", "deliver"),
}
DOMAIN_TERMS = {
    "api-architecture": ("api", "interface", "endpoint", "protocol"),
    "architecture": ("architecture", "module", "dependency", "layer"),
    "frontend": ("frontend", "webpage", "ui", "ux", "react", "vue", "css", "browser"),
    "visual-design": ("visual", "image", "brand", "slide", "diagram", "illustration", "canvas"),
    "security": ("security", "secure", "hardening", "permission", "sandbox", "threat", "secret"),
    "research": ("research", "source", "web", "official", "citation", "wiki"),
    "documentation": ("documentation", "document", "docs", "readme", "markdown", "adr"),
    "testing": ("test", "tdd", "verification", "regression"),
    "release": ("release", "ship", "publish", "handoff"),
    "mcp": ("mcp", "model context protocol", "server", "tool schema"),
    "repository": ("github", "git", "repository", "codebase", "source tree"),
    "product": ("prd", "product", "requirements"),
}

# These are foundational, high-frequency procedures selected from actual
# current registry IDs. The count is reported by the generator rather than
# being treated as a quota.
TIER_1_CORE_IDS = frozenset(
    {
        "using-superpowers",
        "systematic-debugging",
        "debugging-code",
        "diagnose",
        "tdd",
        "test-driven-development",
        "verification-before-completion",
        "code-review-excellence",
        "official-code-review",
        "brooks-audit",
        "brooks-review",
        "brooks-health",
        "brooks-test",
        "brooks-sweep",
        "brooks-debt",
        "logic-health",
        "logic-locate",
        "safe-mode",
        "permission-tuner",
        "mcp-audit",
        "frontend-design",
        "image-to-code",
        "fixing-accessibility",
        "baseline-ui",
        "codebase-inspection",
        "module-map",
        "understand",
        "improve-codebase-architecture",
        "executing-plans",
        "subagent-driven-development",
        "requesting-code-review",
        "receiving-code-review",
        "plan-interrogate",
        "finishing-a-development-branch",
        "full-output-enforcement",
        "logic-review",
        "logic-diff",
        "llm-gate",
        "pr-review-toolkit",
        "logic-fix-all",
        "thoroughness-scoring",
        "parallel-worktrees",
        "baoyu-url-to-markdown",
        "brainstorming",
        "grill-me",
        "grill-with-docs",
        "writing-plans",
        "plan",
        "to-prd",
        "wiki-research-loop",
        "wiki-builder",
        "knowledge-consolidation",
        "release-skills",
        "release",
        "handoff",
    }
)


class MetadataOverlayError(ValueError):
    """Raised when an overlay cannot be trusted for routing."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest_bytes(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _digest_json(value: Any, excluded: str | None = None) -> str:
    payload = copy.deepcopy(value)
    if excluded:
        payload.pop(excluded, None)
    return _digest_bytes(canonical_json(payload).encode("utf-8"))


def _clean_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        return [
            str(_clean_scalar(item))
            for item in value[1:-1].split(",")
            if item.strip()
        ]
    return value


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse only harmless scalar/list frontmatter; never evaluate YAML."""

    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    result: dict[str, Any] = {}
    current: str | None = None
    nested: str | None = None
    for line in parts[1].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        top_match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):(?:\s*(.*))?$", line)
        nested_match = re.match(r"^\s{2,}([A-Za-z][A-Za-z0-9_-]*):(?:\s*(.*))?$", line)
        bullet_match = re.match(r"^\s*-\s+(.*)$", line)
        if top_match and not line.startswith((" ", "\t")):
            current = top_match.group(1)
            nested = None
            raw = top_match.group(2) or ""
            result[current] = _clean_scalar(raw) if raw else []
            continue
        if nested_match and current == "prerequisites":
            nested = nested_match.group(1)
            raw = nested_match.group(2) or ""
            if not isinstance(result.get(current), dict):
                result[current] = {}
            result[current][nested] = _clean_scalar(raw) if raw else []
            continue
        if bullet_match and current:
            target: Any = result.setdefault(current, [])
            if current == "prerequisites" and nested:
                target = result.setdefault(current, {}).setdefault(nested, [])
            if isinstance(target, list):
                target.append(str(_clean_scalar(bullet_match.group(1))))
    return result


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, (str, int, float))]
    return []


def _contains(text: str, term: str) -> bool:
    return term.lower() in text.lower()


def _matches(text: str, table: dict[str, tuple[str, ...]]) -> list[str]:
    return [name for name, terms in table.items() if any(_contains(text, term) for term in terms)]


def _body_path(repository_root: Path, entry: dict[str, Any]) -> Path:
    raw = entry.get("relative_path")
    if not isinstance(raw, str) or not raw:
        raise MetadataOverlayError(f"missing canonical path for {entry.get('id')}")
    path = (repository_root / raw).resolve()
    try:
        path.relative_to(repository_root.resolve())
    except ValueError as exc:
        raise MetadataOverlayError(f"canonical path escapes repository: {raw}") from exc
    if not path.is_file():
        raise MetadataOverlayError(f"canonical SKILL.md is missing: {raw}")
    return path


def _frontmatter_tools(frontmatter: dict[str, Any]) -> list[str]:
    values = _as_list(frontmatter.get("allowed-tools"))
    prerequisites = frontmatter.get("prerequisites")
    if isinstance(prerequisites, dict):
        values.extend(_as_list(prerequisites.get("commands")))
    return list(dict.fromkeys(values))


def _output_hints(skill_id: str, text: str, curated: dict[str, list[str]]) -> list[str]:
    values = list(curated.get("outputs", []))
    terms = (
        ("verification", "verification"),
        ("evidence", "evidence"),
        ("review", "review findings"),
        ("audit", "audit report"),
        ("source", "source findings"),
        ("research", "research brief"),
        ("plan", "plan"),
        ("spec", "specification"),
        ("design", "design artifact"),
        ("frontend", "frontend artifact"),
    )
    for term, output in terms:
        if _contains(text, term):
            values.append(output)
    return list(dict.fromkeys(values))


def _derive_roles(skill_id: str, identity: str, categories: list[str], curated: dict[str, list[str]]) -> list[str]:
    if curated.get("roles"):
        return list(dict.fromkeys(curated["roles"]))
    roles: list[str] = []
    if skill_id == "using-superpowers":
        return ["GATE"]
    if any(_contains(identity, term) for term in STAGE_TERMS["review"]):
        roles.append("REVIEW")
    if any(_contains(identity, term) for term in STAGE_TERMS["verify"]):
        roles.append("VERIFY")
    if any(_contains(identity, term) for term in ("mcp", "cli", "browser", "tool schema")):
        roles.append("TOOL")
    if set(categories) & {"design-and-frontend", "media-and-images"}:
        roles.append("DOMAIN")
    if any(_contains(identity, term) for term in STAGE_TERMS["design"]):
        roles.append("DOMAIN")
    if any(
        _contains(identity, term)
        for term in ("implement", "build", "create", "plan", "spec", "brainstorm", "research", "debug", "diagnos", "design")
    ):
        roles.append("PROCESS")
    if not roles and categories:
        roles.append("DOMAIN")
    return [role for role in ROLE_ORDER if role in roles]


def _derive_domains(identity: str, categories: list[str], curated: dict[str, list[str]]) -> list[str]:
    values = list(curated.get("domains", []))
    values.extend(CATEGORY_DOMAINS[category] for category in categories if category in CATEGORY_DOMAINS)
    values.extend(_matches(identity, DOMAIN_TERMS))
    return list(dict.fromkeys(values))


def _derive_stages(identity: str, roles: list[str], domains: list[str], curated: dict[str, list[str]]) -> list[str]:
    if curated.get("stages"):
        return list(dict.fromkeys(curated["stages"]))
    values = _matches(identity, STAGE_TERMS)
    if "visual-design" in domains or "frontend" in domains:
        values.extend(("design", "implement"))
    if "REVIEW" in roles:
        values.append("review")
    if "VERIFY" in roles:
        values.append("verify")
    if "PROCESS" in roles and not values:
        values.append("implement")
    return [stage for stage in STAGES if stage in values]


def _derive_modes(identity: str, stages: list[str], curated: dict[str, list[str]]) -> list[str]:
    if curated.get("task_modes"):
        return list(dict.fromkeys(curated["task_modes"]))
    values = _matches(identity, MODE_TERMS)
    if not values and "review" in stages:
        values.append("review")
    return list(dict.fromkeys(values))


def _derive_risk(identity: str) -> dict[str, str]:
    risk: dict[str, str] = {"read": "LOW"}
    if any(_contains(identity, term) for term in ("security", "secret", "credential", "permission")):
        risk["read"] = "MEDIUM"
    if any(_contains(identity, term) for term in ("write", "create", "implement", "build", "edit", "generate")):
        risk["local_write"] = "MEDIUM"
    if any(_contains(identity, term) for term in ("publish", "post", "upload", "send", "api")):
        risk["external_write"] = "HIGH"
    return risk


def _provenance(source: str, confidence: float, evidence: str) -> dict[str, Any]:
    return {
        "source": source,
        "confidence": round(confidence, 2),
        "evidence": evidence,
    }


def _build_record(
    repository_root: Path,
    entry: dict[str, Any],
    registry: dict[str, Any],
    *,
    verified_at: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _body_path(repository_root, entry)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    frontmatter = parse_frontmatter(text)
    categories = _as_list(entry.get("categories"))
    curated = ROUTING_HINTS.get(str(entry["id"]), {})
    identity = " ".join(
        [
            str(entry.get("id", "")),
            str(entry.get("name", "")),
            str(entry.get("description", "")),
            " ".join(_as_list(entry.get("triggers"))),
            " ".join(categories),
        ]
    ).lower()
    body_text = text.lower()
    combined = f"{identity} {body_text}"
    roles = _derive_roles(str(entry["id"]), identity, categories, curated)
    domains = _derive_domains(identity, categories, curated)
    stages = _derive_stages(identity, roles, domains, curated)
    modes = _derive_modes(identity, stages, curated)

    metadata: dict[str, Any] = {}
    provenance: dict[str, dict[str, Any]] = {}

    def put(field: str, value: Any, source: str, confidence: float, evidence: str) -> None:
        if value is None or value == [] or value == {}:
            return
        metadata[field] = value
        provenance[field] = _provenance(source, confidence, evidence)

    if entry.get("triggers"):
        put("triggers", list(entry["triggers"]), "AUTHOR_DECLARED", 1.0, "current registry triggers")
    elif frontmatter.get("triggers"):
        put("triggers", _as_list(frontmatter["triggers"]), "AUTHOR_DECLARED", 1.0, "SKILL.md frontmatter triggers")

    put(
        "roles",
        roles,
        "CURATED" if curated.get("roles") else "INFERRED_HIGH_CONFIDENCE" if roles else "UNKNOWN",
        1.0 if curated.get("roles") else 0.8,
        "audited compatibility seed" if curated.get("roles") else "category and identity signals",
    )
    put(
        "stages",
        stages,
        "CURATED" if curated.get("stages") else "INFERRED_HIGH_CONFIDENCE" if stages else "UNKNOWN",
        1.0 if curated.get("stages") else 0.8,
        "audited compatibility seed" if curated.get("stages") else "identity and role signals",
    )
    put(
        "task_modes",
        modes,
        "CURATED" if curated.get("task_modes") else "INFERRED_HIGH_CONFIDENCE" if modes else "UNKNOWN",
        1.0 if curated.get("task_modes") else 0.8,
        "audited compatibility seed" if curated.get("task_modes") else "identity signals",
    )
    put(
        "domains",
        domains,
        "CURATED" if curated.get("domains") else "INFERRED_HIGH_CONFIDENCE" if domains else "UNKNOWN",
        1.0 if curated.get("domains") else 0.8,
        "audited compatibility seed" if curated.get("domains") else "category mapping and identity signals",
    )

    outputs = _output_hints(str(entry["id"]), combined, curated)
    put("outputs", outputs, "CURATED" if curated.get("outputs") else "INFERRED", 1.0 if curated.get("outputs") else 0.55, "audited output mapping" if curated.get("outputs") else "explicit output terms")
    argument_hint = frontmatter.get("argument-hint")
    if argument_hint:
        put("inputs", ["task request", "stage context"], "INFERRED", 0.55, "SKILL.md argument-hint is present")

    tools = _frontmatter_tools(frontmatter)
    put("tools", tools, "AUTHOR_DECLARED", 1.0, "SKILL.md allowed-tools/prerequisites.commands")
    required_capabilities: list[str] = []
    if _contains(identity, "mcp") or _contains(identity, "model context protocol"):
        required_capabilities.append("needs_MCP")
    if _contains(identity, "browser"):
        required_capabilities.append("needs_browser")
    put("required_capabilities", required_capabilities, "INFERRED_HIGH_CONFIDENCE", 0.8, "explicit MCP/browser identity signal")

    source_update: dict[str, Any] = {}
    if frontmatter.get("license"):
        source_update["license"] = str(frontmatter["license"])
        provenance["source.license"] = _provenance("AUTHOR_DECLARED", 1.0, "SKILL.md license")
    if frontmatter.get("version"):
        metadata["version"] = str(frontmatter["version"])
        provenance["version"] = _provenance("AUTHOR_DECLARED", 1.0, "SKILL.md version")
    if source_update:
        metadata["source"] = source_update

    context_cost = {
        "metadata_tokens": max(1, len(canonical_json({"id": entry["id"], "description": entry["description"]})) // 4),
        "instruction_tokens_estimate": max(20, (len(raw) + 3) // 4),
        "references_lazy": True,
        "tool_schema_tokens": 0,
    }
    put("context_cost", context_cost, "INFERRED_HIGH_CONFIDENCE", 0.8, "canonical SKILL.md byte count")
    runtime_cost = {
        "tool_calls_estimate": len(tools),
        "latency_class": "interactive" if len(raw) < 20000 and len(tools) < 3 else "batch",
    }
    put("runtime_cost", runtime_cost, "INFERRED", 0.55, "declared tool count and body size")
    put("risk", _derive_risk(identity), "INFERRED", 0.55, "conservative identity risk signals; not permissions")
    put("eval_status", {"routing": "planned", "activation": "unmeasured", "execution": "unmeasured", "security": "unmeasured", "cross_agent": "unmeasured"}, "INFERRED", 0.55, "enrichment baseline has no execution measurements")

    routing_extensions: dict[str, Any] = {
        "positive_triggers": list(dict.fromkeys([str(entry["id"]), str(entry.get("name", "")).lower()] + _matches(identity, MODE_TERMS))),
        "body_loaded_for_route": False,
        "body_inspected_for_enrichment": True,
        "permission_inference": "UNKNOWN_CONSERVATIVE",
    }
    if entry.get("description", "").lstrip().lower().startswith("[deprecated:"):
        routing_extensions["negative_triggers"] = ["deprecated", "do not use"]
    metadata["extensions"] = {"routing": routing_extensions}
    provenance["extensions.routing"] = _provenance("INFERRED", 0.55, "offline enrichment annotations")

    relationships, relationship_provenance = _relationships_for(str(entry["id"]))
    if relationships:
        metadata["relationships"] = relationships
        provenance["relationships"] = _provenance("CURATED", 0.95, "sparse high-confidence overlap/complement mapping")

    if not roles or not stages or not domains:
        classification = "LEGACY_MINIMAL" if not entry.get("triggers") and len(text) < 1000 else "PARTIAL"
    elif curated.get("roles") and curated.get("stages") and curated.get("domains"):
        classification = "ROUTING_READY"
    elif len(domains) >= 5 or (len(stages) >= 5 and len(modes) >= 4):
        classification = "AMBIGUOUS"
    else:
        classification = "PARTIAL"
    if entry.get("description", "").lstrip().lower().startswith("[deprecated:"):
        classification = "DEPRECATED"
    if classification == "DEPRECATED":
        tier = "TIER_4_DEPRECATED"
    elif str(entry["id"]) in TIER_1_CORE_IDS:
        tier = "TIER_1_CORE"
    elif set(categories) & {"software-engineering", "quality-and-safety", "design-and-frontend", "media-and-images", "documents-and-publishing"}:
        tier = "TIER_2_DOMAIN"
    else:
        tier = "TIER_3_SPECIALIZED"

    routing_sources = [
        provenance[field]["source"]
        for field in ROUTING_FIELDS
        if field in provenance
    ]
    confidence = round(sum(PROVENANCE_WEIGHTS[source] for source in routing_sources) / len(routing_sources), 2) if routing_sources else 0.0
    overlay_record: dict[str, Any] = {
        "skill_id": entry["id"],
        "source_skill_digest": f"sha256:{entry['sha256']}" if not str(entry["sha256"]).startswith("sha256:") else entry["sha256"],
        "classification": classification,
        "tier": tier,
        "metadata": metadata,
        "provenance": {
            "default": "UNKNOWN",
            "fields": provenance,
            "relationships": relationship_provenance,
        },
        "review_status": "CURATED" if classification == "ROUTING_READY" else "GENERATED",
        "confidence": confidence,
        "last_verified": verified_at,
        "body_policy": "READ_ONLY",
        "body_bytes_inspected": len(raw),
    }
    if classification in {"PARTIAL", "LEGACY_MINIMAL", "AMBIGUOUS"}:
        overlay_record["notes"] = "Routing fields are derived or incomplete; unknown permissions remain conservative."
    stats = {
        "body_bytes": len(raw),
        "frontmatter_keys": sorted(frontmatter),
        "registry_trigger_present": bool(entry.get("triggers")),
        "body_equivalent_signals": {
            "tools": bool(tools),
            "license": bool(frontmatter.get("license")),
            "version": bool(frontmatter.get("version")),
            "allowed_tools": bool(frontmatter.get("allowed-tools")),
            "prerequisites": bool(frontmatter.get("prerequisites")),
        },
        "classification": classification,
        "tier": tier,
        "provenance_sources": Counter(
            item["source"] for item in provenance.values()
        ),
    }
    return overlay_record, stats


def _relationships_for(skill_id: str) -> tuple[list[dict[str, str]], dict[str, dict[str, Any]]]:
    pairs: dict[str, list[tuple[str, str, float]]] = {
        "tdd": [("ALTERNATIVE_TO", "test-driven-development", "two current TDD procedure variants", 0.95)],
        "test-driven-development": [("ALTERNATIVE_TO", "tdd", "two current TDD procedure variants", 0.95), ("VERIFY_WITH", "verification-before-completion", "TDD output requires explicit verification", 0.95)],
        "verification-before-completion": [("VERIFY_WITH", "test-driven-development", "verification consumes implementation/test evidence", 0.9)],
        "baoyu-imagine": [("SUPERSEDES", "baoyu-image-gen", "canonical body explicitly marks image-gen deprecated", 1.0)],
        "design-taste-frontend": [("SUPERSEDES", "design-taste-frontend-v1", "versioned successor is the current design procedure", 0.95)],
        "source-driven-development": [("COMPLEMENTS", "verification-before-completion", "source claims need verification")],
        "wiki-research-loop": [("VERIFY_WITH", "verification-before-completion", "research output needs source/evidence verification", 0.9)],
        "code-review-excellence": [("VERIFY_WITH", "verification-before-completion", "review findings need completion evidence", 0.9)],
        "mcp-audit": [("COMPLEMENTS", "context-engineering", "MCP schema cost is a context concern", 0.9)],
    }
    relationships: list[dict[str, str]] = []
    provenance: dict[str, dict[str, Any]] = {}
    for relation in pairs.get(skill_id, []):
        relation_type, target, reason, *confidence = relation
        if target == "source-driven-development":
            continue
        item = {"type": relation_type, "target": target, "reason": reason}
        relationships.append(item)
        provenance[f"{relation_type}:{target}"] = _provenance(
            "CURATED", confidence[0] if confidence else 0.85, reason
        )
    return relationships, provenance


def _base_field_presence(registry: dict[str, Any]) -> dict[str, int]:
    fields = (
        "roles", "stages", "task_modes", "domains", "triggers", "inputs",
        "outputs", "required_capabilities", "tools", "permissions", "context_cost",
        "runtime_cost", "relationships", "agent_compatibility", "trust", "source",
    )
    counts = Counter()
    for entry in registry["skills"]:
        projected = import_skill_index_entry(entry, registry)
        for field in fields:
            value = projected.get(field)
            if value:
                counts[field] += 1
    return {field: counts[field] for field in fields}


def build_overlay(
    repository_root: str | Path,
    registry_path: str | Path,
    *,
    verified_at: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic overlay by reading each canonical body as data."""

    repository_root = Path(repository_root).resolve()
    registry_path = Path(registry_path).resolve()
    registry = load_current_registry(registry_path)
    records: dict[str, dict[str, Any]] = {}
    stats: list[dict[str, Any]] = []
    for entry in sorted(registry["skills"], key=lambda item: str(item.get("id", ""))):
        record, item_stats = _build_record(repository_root, entry, registry, verified_at=verified_at)
        records[record["skill_id"]] = record
        stats.append(item_stats)

    classification_counts = Counter(item["classification"] for item in stats)
    tier_counts = Counter(item["tier"] for item in stats)
    provenance_counts = Counter(
        source
        for item in stats
        for source, count in item["provenance_sources"].items()
        for _ in range(count)
    )
    body_signal_counts = Counter(
        signal
        for item in stats
        for signal, present in item["body_equivalent_signals"].items()
        if present
    )
    overlay_field_counts = Counter({field: 0 for field in OVERLAY_CENSUS_FIELDS})
    overlay_field_provenance: dict[str, Counter[str]] = {}
    for record in records.values():
        metadata = record["metadata"]
        fields = record["provenance"]["fields"]
        for field, value in metadata.items():
            if value in (None, [], {}):
                continue
            census_field = field
            if field == "source" and isinstance(value, dict) and "license" in value:
                census_field = "source.license"
            elif field == "extensions" and isinstance(value, dict) and "routing" in value:
                census_field = "extensions.routing"
            overlay_field_counts[census_field] += 1
            source = fields.get(census_field, {}).get("source", "UNKNOWN")
            overlay_field_provenance.setdefault(census_field, Counter())[source] += 1
    base_field_presence = _base_field_presence(registry)
    census = {
        "record_count": len(records),
        "body_files_inspected": len(stats),
        "body_bytes_inspected": sum(item["body_bytes"] for item in stats),
        "current_registry_field_presence": base_field_presence,
        "v3_field_presence_before_overlay": base_field_presence,
        "body_frontmatter_equivalent_signal_presence": dict(sorted(body_signal_counts.items())),
        "overlay_field_presence": dict(sorted(overlay_field_counts.items())),
        "overlay_field_provenance": {
            field: dict(sorted(counts.items()))
            for field, counts in sorted(overlay_field_provenance.items())
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "tier_counts": dict(sorted(tier_counts.items())),
        "provenance_counts": dict(sorted(provenance_counts.items())),
        "capability_resolution": copy.deepcopy(CAPABILITY_RESOLUTION),
        "routing_ready_count": classification_counts["ROUTING_READY"],
        "tier_1_routing_ready_count": sum(
            1
            for record in records.values()
            if record["tier"] == "TIER_1_CORE" and record["classification"] == "ROUTING_READY"
        ),
    }
    document: dict[str, Any] = {
        "schema_version": "3.0",
        "overlay_version": OVERLAY_VERSION,
        "registry": {
            "path": str(registry_path.relative_to(repository_root)),
            "source": registry["source"],
            "source_ref": registry.get("source_ref", "unknown"),
            "source_commit": registry.get("source_commit", "unknown"),
            "skill_count": len(registry["skills"]),
        },
        "generator": {
            "version": GENERATOR_VERSION,
            "entrypoint": "tools/v3/metadata_enrichment.py",
            "body_policy": "READ_ONLY_NO_EXECUTION",
        },
        "census": census,
        "skills": records,
    }
    document["overlay_digest"] = _digest_json(document)
    return document


def load_overlay(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise MetadataOverlayError(f"cannot load overlay {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MetadataOverlayError(f"overlay is not an object: {path}")
    return value


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def apply_overlay(
    entry: dict[str, Any],
    registry: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    """Apply one overlay record to a compatibility projection."""

    if "relative_path" in entry:
        base = import_skill_index_entry(entry, registry)
    else:
        base = copy.deepcopy(entry)
    skill_id = base.get("skill_id")
    overlay_record = overlay.get("skills", {}).get(skill_id)
    if not isinstance(overlay_record, dict):
        raise MetadataOverlayError(f"overlay record is missing: {skill_id}")
    metadata = overlay_record.get("metadata", {})
    if not isinstance(metadata, dict):
        raise MetadataOverlayError(f"overlay metadata is not an object: {skill_id}")
    result = _deep_merge(base, metadata)
    routing = result.setdefault("extensions", {}).setdefault("routing", {})
    provenance = overlay_record.get("provenance", {})
    routing.update(
        {
            "source": OVERLAY_SOURCE,
            "overlay_version": overlay.get("overlay_version", OVERLAY_VERSION),
            "metadata_provenance": provenance,
            "inferred_fields": sorted(
                field
                for field, info in (provenance.get("fields", {}) or {}).items()
                if isinstance(info, dict)
                and str(info.get("source", "")).startswith("INFERRED")
            ),
            "hinted_fields": sorted(
                field
                for field, info in (provenance.get("fields", {}) or {}).items()
                if isinstance(info, dict)
                and info.get("source") in {"AUTHOR_DECLARED", "CURATED"}
            ),
            "body_loaded_for_route": False,
            "body_inspected_for_enrichment": True,
        }
    )
    return result


def validate_overlay(
    overlay: dict[str, Any],
    *,
    registry_path: str | Path,
    repository_root: str | Path | None = None,
    check_bodies: bool = False,
) -> Any:
    """Validate schema, registry identity, merged metadata, and optional bodies."""

    result = validate_instance("SkillRoutingMetadata", overlay)
    if not result.valid:
        return result
    registry_path = Path(registry_path).resolve()
    registry = load_current_registry(registry_path)
    expected_ids = {entry.get("id") for entry in registry["skills"]}
    actual_ids = set((overlay.get("skills") or {}).keys())
    if actual_ids != expected_ids:
        result.errors.append("overlay skill IDs do not exactly match current registry")
    registry_info = overlay.get("registry", {})
    for key in ("source", "source_ref", "source_commit"):
        if registry_info.get(key) != registry.get(key, "unknown"):
            result.errors.append(f"overlay registry {key} does not match current registry")
    if registry_info.get("skill_count") != len(registry["skills"]):
        result.errors.append("overlay registry skill_count does not match current registry")
    if overlay.get("overlay_digest") != _digest_json(overlay, "overlay_digest"):
        result.errors.append("overlay_digest does not match canonical overlay payload")
    root = Path(repository_root).resolve() if repository_root else registry_path.parent.parent
    for entry in registry["skills"]:
        skill_id = entry.get("id")
        item = (overlay.get("skills") or {}).get(skill_id, {})
        if item.get("source_skill_digest") != f"sha256:{entry.get('sha256')}" and item.get("source_skill_digest") != entry.get("sha256"):
            result.errors.append(f"source digest mismatch for {skill_id}")
        metadata = item.get("metadata", {})
        provenance = item.get("provenance", {})
        permission_source = (provenance.get("fields", {}) or {}).get("permissions", {}).get("source")
        if "permissions" in metadata and permission_source not in {"AUTHOR_DECLARED", "CURATED"}:
            result.errors.append(f"inferred metadata cannot declare permissions for {skill_id}")
        merged = apply_overlay(entry, registry, overlay)
        merged_result = validate_instance("SkillMetadataV3", merged)
        result.extend(merged_result, prefix=f"{skill_id}: ")
        if check_bodies:
            try:
                actual = _digest_bytes(_body_path(root, entry).read_bytes())
            except MetadataOverlayError as exc:
                result.errors.append(str(exc))
                continue
            if actual != item.get("source_skill_digest"):
                result.errors.append(f"stale source skill digest for {skill_id}")
    return result


def load_enriched_catalog(
    registry_path: str | Path,
    *,
    overlay_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Load overlay metadata without reading canonical skill bodies."""

    registry_path = Path(registry_path).resolve()
    registry = load_current_registry(registry_path)
    if overlay_path is None:
        candidate = registry_path.parent.parent / DEFAULT_OVERLAY_RELATIVE_PATH
    else:
        candidate = Path(overlay_path).resolve()
    if not candidate.is_file():
        return [import_skill_index_entry(entry, registry) for entry in registry["skills"]]
    overlay = load_overlay(candidate)
    validation = validate_overlay(overlay, registry_path=registry_path)
    if not validation.valid:
        raise MetadataOverlayError("invalid routing metadata overlay: " + "; ".join(validation.errors))
    return [
        apply_overlay(entry, registry, overlay)
        for entry in registry["skills"]
    ]


def metadata_quality(record: dict[str, Any]) -> float:
    """Return a transparent score weight for routing-field provenance."""

    routing = (record.get("extensions", {}) or {}).get("routing", {}) or {}
    metadata_provenance = routing.get("metadata_provenance", {}) or {}
    fields = metadata_provenance.get("fields", {}) or {}
    values: list[float] = []
    for field in ROUTING_FIELDS:
        if not record.get(field):
            continue
        info = fields.get(field, {})
        source = info.get("source") if isinstance(info, dict) else None
        if source not in PROVENANCE_LEVELS:
            if field in routing.get("inferred_fields", []):
                source = "INFERRED"
            else:
                source = "AUTHOR_DECLARED"
        values.append(PROVENANCE_WEIGHTS[source])
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def field_provenance(record: dict[str, Any], field: str) -> str:
    routing = (record.get("extensions", {}) or {}).get("routing", {}) or {}
    fields = ((routing.get("metadata_provenance", {}) or {}).get("fields", {}) or {})
    info = fields.get(field)
    if isinstance(info, dict) and info.get("source") in PROVENANCE_LEVELS:
        return str(info["source"])
    if field in routing.get("inferred_fields", []):
        return "INFERRED"
    return "AUTHOR_DECLARED" if record.get(field) else "UNKNOWN"


def census_overlay(overlay: dict[str, Any]) -> dict[str, Any]:
    """Return the checked-in census without exposing body contents."""

    return copy.deepcopy(overlay.get("census", {}))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--registry", type=Path, default=Path(".superpowers/SKILLS_INDEX.json"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OVERLAY_RELATIVE_PATH)
    parser.add_argument("--verified-at", default=None)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else args.root / args.output
    registry = args.registry if args.registry.is_absolute() else args.root / args.registry
    overlay = build_overlay(args.root, registry, verified_at=args.verified_at)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(overlay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(overlay["census"], ensure_ascii=False, sort_keys=True))
