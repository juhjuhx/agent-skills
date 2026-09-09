"""Transparent metadata-only scoring helpers for the Stage Router MVP."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable


ROLES = ("GATE", "PROCESS", "DOMAIN", "TOOL", "REVIEW", "VERIFY")
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

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "before",
        "by",
        "change",
        "for",
        "from",
        "in",
        "into",
        "is",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
        "with",
    }
)

_CATEGORY_DOMAINS = {
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

_STAGE_TERMS = {
    "understand": (
        "understand",
        "inspect",
        "architecture",
        "diagnos",
        "debug",
        "map",
        "onboard",
        "orient",
    ),
    "research": (
        "research",
        "source",
        "web",
        "search",
        "official",
        "wiki",
        "knowledge",
        "docs",
        "document",
    ),
    "design": (
        "design",
        "ui",
        "visual",
        "frontend",
        "brand",
        "prototype",
        "brainstorm",
        "image",
        "slide",
    ),
    "plan": (
        "plan",
        "spec",
        "prd",
        "roadmap",
        "break down",
        "requirements",
        "strategy",
    ),
    "implement": (
        "implement",
        "build",
        "create",
        "develop",
        "write",
        "fix",
        "generate",
        "code",
        "convert",
    ),
    "review": (
        "review",
        "audit",
        "quality",
        "lint",
        "health",
        "simplif",
        "security",
        "accessibility",
        "performance",
        "permission",
    ),
    "verify": (
        "verif",
        "test",
        "validation",
        "evidence",
        "complete",
        "passing",
        "check",
    ),
    "harden": (
        "security",
        "hardening",
        "permission",
        "safe",
        "lockdown",
        "performance",
        "accessibility",
        "guard",
    ),
    "handoff": ("handoff", "release", "ship", "publish", "wrap-up", "session"),
    "learn": ("learn", "distill", "candidate", "promotion", "knowledge"),
}

_MODE_TERMS = {
    "bugfix": (
        "bug",
        "debug",
        "diagnos",
        "crash",
        "failing",
        "exception",
        "wrong output",
    ),
    "implementation": (
        "implement",
        "build",
        "create",
        "develop",
        "write",
        "feature",
        "code",
        "fix",
    ),
    "research": (
        "research",
        "source",
        "web",
        "search",
        "official",
        "wiki",
        "knowledge",
    ),
    "review": (
        "review",
        "audit",
        "quality",
        "security",
        "performance",
        "lint",
        "health",
    ),
    "design": ("design", "ui", "visual", "frontend", "brand", "prototype", "image"),
    "documentation": ("document", "docs", "readme", "markdown", "adr", "write-up"),
    "handoff": ("handoff", "release", "ship", "publish", "deliver"),
}

_DOMAIN_TERMS = {
    "api-architecture": ("api", "interface", "endpoint", "protocol"),
    "architecture": ("architecture", "module", "dependency", "layer"),
    "frontend": ("frontend", "webpage", "ui", "ux", "react", "vue", "css", "browser"),
    "visual-design": (
        "visual",
        "image",
        "brand",
        "slide",
        "diagram",
        "illustration",
        "canvas",
    ),
    "security": (
        "security",
        "secure",
        "hardening",
        "permission",
        "sandbox",
        "threat",
        "secret",
    ),
    "research": ("research", "source", "web", "official", "citation", "wiki"),
    "documentation": ("documentation", "document", "docs", "readme", "markdown", "adr"),
    "testing": ("test", "tdd", "verification", "regression"),
    "release": ("release", "ship", "publish", "handoff"),
    "mcp": ("mcp", "model context protocol", "server", "tool schema"),
    "repository": ("github", "git", "repository", "codebase", "source tree"),
    "product": ("prd", "product", "requirements"),
}

# The current 214-record registry has no v3 roles/stages/domains. These are
# small, auditable compatibility hints for high-signal canonical procedures;
# they are an inferred view, not a registry migration or a fixture rule.
ROUTING_HINTS: dict[str, dict[str, list[str]]] = {
    "using-superpowers": {
        "stages": list(STAGES),
        "roles": ["GATE"],
        "domains": ["orchestration"],
    },
    "deep-understanding": {
        "stages": ["understand"],
        "roles": ["PROCESS"],
        "task_modes": ["research", "design", "implementation"],
        "domains": ["architecture", "orchestration"],
    },
    "systematic-debugging": {
        "stages": ["understand", "implement", "verify"],
        "roles": ["PROCESS"],
        "task_modes": ["bugfix"],
        "domains": ["software-engineering", "testing"],
    },
    "debugging-code": {
        "stages": ["understand", "implement"],
        "roles": ["PROCESS", "TOOL"],
        "task_modes": ["bugfix"],
        "domains": ["software-engineering", "testing"],
    },
    "diagnose": {
        "stages": ["understand", "implement", "review"],
        "roles": ["PROCESS", "REVIEW"],
        "task_modes": ["bugfix"],
        "domains": ["software-engineering", "testing"],
        "outputs": ["root cause", "patch"],
    },
    "tdd": {
        "stages": ["plan", "implement", "verify"],
        "roles": ["PROCESS"],
        "task_modes": ["bugfix", "implementation"],
        "domains": ["software-engineering", "testing"],
        "outputs": ["tests", "test plan"],
    },
    "test-driven-development": {
        "stages": ["plan", "implement", "verify"],
        "roles": ["PROCESS"],
        "task_modes": ["bugfix", "implementation"],
        "domains": ["software-engineering", "testing"],
        "outputs": ["tests", "test plan"],
    },
    "verification-before-completion": {
        "stages": [
            "research",
            "design",
            "implement",
            "review",
            "verify",
            "harden",
            "handoff",
        ],
        "roles": ["VERIFY"],
        "task_modes": [
            "bugfix",
            "implementation",
            "design",
            "research",
            "review",
            "handoff",
        ],
        "domains": ["software-engineering", "testing"],
        "outputs": ["verification", "browser verification", "evidence"],
    },
    "code-review-excellence": {
        "stages": ["design", "implement", "review", "harden", "handoff"],
        "roles": ["REVIEW"],
        "task_modes": ["review", "implementation", "design", "handoff"],
        "domains": ["software-engineering", "quality-and-safety"],
        "outputs": ["review findings", "security review"],
    },
    "official-code-review": {
        "stages": ["design", "implement", "review", "harden", "handoff"],
        "roles": ["REVIEW"],
        "task_modes": ["review", "implementation", "design", "handoff"],
        "domains": ["software-engineering", "quality-and-safety"],
        "outputs": ["review findings"],
    },
    "brooks-audit": {
        "stages": ["understand", "review"],
        "roles": ["DOMAIN", "REVIEW"],
        "task_modes": ["review"],
        "domains": ["architecture", "repository"],
    },
    "brooks-review": {
        "stages": ["design", "review", "harden", "handoff"],
        "roles": ["REVIEW"],
        "task_modes": ["review", "implementation", "design", "handoff"],
        "domains": ["architecture", "quality-and-safety", "repository"],
        "outputs": ["review findings", "security review"],
    },
    "brooks-health": {
        "stages": ["understand", "review"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["repository", "quality-and-safety"],
    },
    "brooks-test": {
        "stages": ["review", "verify", "handoff"],
        "roles": ["REVIEW"],
        "task_modes": ["review", "handoff"],
        "domains": ["testing", "quality-and-safety"],
        "outputs": ["tests", "test review"],
    },
    "brooks-sweep": {
        "stages": ["review", "harden"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["quality-and-safety", "repository"],
        "outputs": ["review findings"],
    },
    "brooks-debt": {
        "stages": ["review", "harden"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["quality-and-safety", "repository"],
        "outputs": ["review findings", "audit report"],
    },
    "logic-health": {
        "stages": ["review"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["quality-and-safety", "repository"],
        "outputs": ["review findings"],
    },
    "logic-locate": {
        "stages": ["understand", "implement"],
        "roles": ["PROCESS"],
        "task_modes": ["bugfix"],
        "domains": ["software-engineering", "testing"],
    },
    "safe-mode": {
        "stages": ["harden"],
        "roles": ["PROCESS", "REVIEW"],
        "task_modes": ["implementation", "review"],
        "domains": ["security"],
        "outputs": ["security patch", "permission boundary"],
    },
    "permission-tuner": {
        "stages": ["review", "harden"],
        "roles": ["REVIEW"],
        "task_modes": ["review", "implementation"],
        "domains": ["security"],
        "outputs": ["permission boundary"],
    },
    "mcp-audit": {
        "stages": ["research", "review"],
        "roles": ["TOOL", "REVIEW"],
        "task_modes": ["research", "review"],
        "domains": ["mcp"],
        "outputs": ["MCP audit", "tool-schema evidence"],
    },
    "frontend-design": {
        "stages": ["design", "implement"],
        "roles": ["PROCESS", "DOMAIN"],
        "task_modes": ["design", "implementation"],
        "domains": ["frontend"],
        "outputs": ["frontend patch", "UI design"],
    },
    "image-to-code": {
        "stages": ["implement"],
        "roles": ["DOMAIN"],
        "task_modes": ["implementation"],
        "domains": ["frontend", "visual-design"],
        "outputs": ["frontend patch", "UI implementation"],
    },
    "fixing-accessibility": {
        "stages": ["implement", "review", "harden", "verify"],
        "roles": ["REVIEW", "VERIFY"],
        "task_modes": ["review", "implementation"],
        "domains": ["frontend"],
        "outputs": ["UI verification", "accessibility review"],
    },
    "baseline-ui": {
        "stages": ["implement", "review", "verify"],
        "roles": ["REVIEW", "VERIFY"],
        "task_modes": ["review", "implementation"],
        "domains": ["frontend"],
        "outputs": ["UI verification", "accessibility review"],
    },
    "fixing-motion-performance": {
        "stages": ["review", "harden"],
        "roles": ["REVIEW"],
        "task_modes": ["review", "implementation"],
        "domains": ["frontend", "performance"],
    },
    "ckm:design": {
        "stages": ["design"],
        "roles": ["PROCESS", "DOMAIN"],
        "task_modes": ["design"],
        "domains": ["visual-design"],
    },
    "ckm:slides": {
        "stages": ["design", "implement"],
        "roles": ["PROCESS", "DOMAIN"],
        "task_modes": ["design", "implementation"],
        "domains": ["visual-design"],
    },
    "visual-atelier": {
        "stages": ["design"],
        "roles": ["PROCESS", "DOMAIN"],
        "task_modes": ["design"],
        "domains": ["visual-design"],
    },
    "baoyu-slide-deck": {
        "stages": ["design", "implement"],
        "roles": ["PROCESS", "DOMAIN"],
        "task_modes": ["design", "implementation"],
        "domains": ["visual-design"],
        "outputs": ["presentation", "visual design"],
    },
    "design-taste-frontend": {
        "stages": ["design"],
        "roles": ["PROCESS", "DOMAIN"],
        "task_modes": ["design"],
        "domains": ["frontend", "visual-design"],
        "outputs": ["visual design", "UI design"],
    },
    "industrial-brutalist-ui": {
        "stages": ["design"],
        "roles": ["DOMAIN"],
        "task_modes": ["design"],
        "domains": ["visual-design"],
    },
    "minimalist-ui": {
        "stages": ["design"],
        "roles": ["DOMAIN"],
        "task_modes": ["design"],
        "domains": ["visual-design"],
    },
    "codebase-inspection": {
        "stages": ["understand", "review"],
        "roles": ["PROCESS"],
        "task_modes": ["review"],
        "domains": ["repository"],
        "outputs": ["source findings", "audit report"],
    },
    "module-map": {
        "stages": ["understand", "review"],
        "roles": ["PROCESS", "DOMAIN"],
        "task_modes": ["review"],
        "domains": ["repository", "architecture"],
        "outputs": ["source findings", "architecture map"],
    },
    "understand": {
        "stages": ["understand", "research"],
        "roles": ["PROCESS"],
        "task_modes": ["review", "research"],
        "domains": ["repository", "architecture"],
        "outputs": ["source findings", "architecture map"],
    },
    "improve-codebase-architecture": {
        "stages": ["understand", "design", "review"],
        "roles": ["DOMAIN", "REVIEW"],
        "task_modes": ["design", "review"],
        "domains": ["architecture", "api-architecture", "repository"],
    },
    "executing-plans": {
        "stages": ["plan", "implement"],
        "roles": ["PROCESS"],
        "task_modes": ["implementation"],
        "domains": ["software-engineering", "documentation"],
    },
    "subagent-driven-development": {
        "stages": ["plan", "implement"],
        "roles": ["PROCESS"],
        "task_modes": ["implementation"],
        "domains": ["orchestration", "software-engineering"],
    },
    "requesting-code-review": {
        "stages": ["review"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["quality-and-safety", "repository"],
    },
    "receiving-code-review": {
        "stages": ["review"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["quality-and-safety", "repository"],
    },
    "plan-interrogate": {
        "stages": ["design", "plan"],
        "roles": ["PROCESS"],
        "task_modes": ["design"],
        "domains": ["architecture", "product"],
    },
    "finishing-a-development-branch": {
        "stages": ["handoff"],
        "roles": ["PROCESS"],
        "task_modes": ["handoff"],
        "domains": ["release", "repository"],
        "outputs": ["release decision", "handoff"],
    },
    "algorithmic-art": {
        "stages": ["design"],
        "roles": ["PROCESS", "DOMAIN"],
        "task_modes": ["design"],
        "domains": ["visual-design"],
    },
    "ckm:ui-styling": {
        "stages": ["design", "implement"],
        "roles": ["DOMAIN", "PROCESS"],
        "task_modes": ["design", "implementation"],
        "domains": ["frontend"],
        "outputs": ["frontend patch", "UI design"],
    },
    "full-output-enforcement": {
        "stages": ["verify", "handoff"],
        "roles": ["VERIFY"],
        "task_modes": ["review", "handoff"],
        "domains": ["quality-and-safety"],
    },
    "logic-review": {
        "stages": ["review", "handoff"],
        "roles": ["REVIEW"],
        "task_modes": ["review", "handoff"],
        "domains": ["software-engineering", "testing"],
        "outputs": ["review findings", "audit report", "review"],
    },
    "logic-diff": {
        "stages": ["review"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["software-engineering", "testing"],
    },
    "llm-gate": {
        "stages": ["review", "harden"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["quality-and-safety"],
    },
    "pr-review-toolkit": {
        "stages": ["review", "harden"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["quality-and-safety", "repository"],
        "outputs": ["review findings", "security review"],
    },
    "logic-fix-all": {
        "stages": ["review", "harden"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["quality-and-safety", "repository"],
        "outputs": ["audit report", "verification"],
    },
    "thoroughness-scoring": {
        "stages": ["review", "verify"],
        "roles": ["REVIEW"],
        "task_modes": ["review"],
        "domains": ["quality-and-safety"],
        "outputs": ["review findings"],
    },
    "parallel-worktrees": {
        "stages": ["implement"],
        "roles": ["TOOL"],
        "task_modes": ["implementation"],
        "domains": ["repository"],
    },
    "baoyu-url-to-markdown": {
        "stages": ["research"],
        "roles": ["TOOL"],
        "task_modes": ["research"],
        "domains": ["research", "documentation"],
        "outputs": ["sources", "citations"],
    },
    "brainstorming": {
        "stages": ["understand", "design", "plan"],
        "roles": ["PROCESS"],
        "task_modes": ["design"],
        "domains": ["product", "documentation"],
        "outputs": ["requirements", "design alternatives"],
    },
    "grill-me": {
        "stages": ["understand", "design", "plan"],
        "roles": ["PROCESS"],
        "task_modes": ["design"],
        "domains": ["product"],
        "outputs": ["requirements", "decision record"],
    },
    "grill-with-docs": {
        "stages": ["understand", "design", "plan"],
        "roles": ["PROCESS"],
        "task_modes": ["design", "documentation"],
        "domains": ["product", "documentation", "architecture"],
        "outputs": ["decision record", "ADR", "CONTEXT.md"],
    },
    "writing-plans": {
        "stages": ["plan", "implement"],
        "roles": ["PROCESS"],
        "task_modes": ["implementation", "design"],
        "domains": ["software-engineering", "documentation", "architecture"],
        "outputs": ["plan", "implementation plan"],
    },
    "plan": {
        "stages": ["plan"],
        "roles": ["PROCESS"],
        "task_modes": ["design", "implementation"],
        "domains": ["documentation", "product", "architecture"],
        "outputs": ["plan", "specification"],
    },
    "to-prd": {
        "stages": ["plan"],
        "roles": ["DOMAIN", "PROCESS"],
        "task_modes": ["design"],
        "domains": ["product", "documentation"],
        "outputs": ["PRD", "specification"],
    },
    "release-skills": {
        "stages": ["handoff"],
        "roles": ["PROCESS"],
        "task_modes": ["handoff"],
        "domains": ["release"],
        "outputs": ["release decision", "handoff"],
    },
    "release": {
        "stages": ["handoff"],
        "roles": ["PROCESS"],
        "task_modes": ["handoff"],
        "domains": ["release"],
        "outputs": ["release decision", "handoff"],
    },
    "handoff": {
        "stages": ["handoff"],
        "roles": ["PROCESS"],
        "task_modes": ["handoff"],
        "domains": ["release", "documentation"],
        "outputs": ["handoff"],
    },
    "wiki-research-loop": {
        "stages": ["research", "learn"],
        "roles": ["PROCESS"],
        "task_modes": ["research"],
        "domains": ["research"],
        "outputs": ["research brief", "citations", "sources"],
    },
    "wiki-builder": {
        "stages": ["research", "learn"],
        "roles": ["PROCESS", "DOMAIN"],
        "task_modes": ["research", "documentation"],
        "domains": ["research", "documentation"],
        "outputs": ["research brief", "sources"],
    },
    "knowledge-consolidation": {
        "stages": ["research", "learn"],
        "roles": ["PROCESS"],
        "task_modes": ["research"],
        "domains": ["research", "documentation"],
        "outputs": ["research brief", "knowledge summary"],
    },
}


def _text_tokens(value: Any) -> set[str]:
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value)
    elif not isinstance(value, str):
        value = str(value) if value is not None else ""
    tokens = set(re.findall(r"[a-z0-9][a-z0-9_:-]*", value.lower()))
    return {token for token in tokens if token not in _STOP_WORDS and len(token) > 2}


def _contains_term(text: str, term: str) -> bool:
    pattern = r"\b" + re.escape(term.lower())
    return re.search(pattern, text.lower()) is not None


def _categories(record: dict[str, Any]) -> list[str]:
    compatibility = (record.get("extensions", {}) or {}).get("compatibility", {}) or {}
    values = compatibility.get("current_categories", [])
    return [item for item in values if isinstance(item, str)]


def _record_text(record: dict[str, Any]) -> str:
    values: list[str] = []
    for key in (
        "skill_id",
        "name",
        "description",
        "triggers",
        "inputs",
        "outputs",
        "tools",
    ):
        value = record.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif value is not None:
            values.append(str(value))
    values.extend(_categories(record))
    return " ".join(values).lower()


def _identity_text(record: dict[str, Any]) -> str:
    values = [
        record.get("skill_id", ""),
        record.get("name", ""),
        record.get("triggers", []),
    ]
    values.extend(_categories(record))
    return " ".join(
        " ".join(str(item) for item in value) if isinstance(value, list) else str(value)
        for value in values
        if value is not None
    ).lower()


def _infer_from_terms(text: str, table: dict[str, tuple[str, ...]]) -> list[str]:
    return [
        name
        for name, terms in table.items()
        if any(_contains_term(text, term) for term in terms)
    ]


def _inferred_fields(record: dict[str, Any]) -> set[str]:
    routing = (record.get("extensions", {}) or {}).get("routing", {}) or {}
    fields = routing.get("inferred_fields", [])
    return {field for field in fields if isinstance(field, str)}


def field_is_inferred(record: dict[str, Any], field: str) -> bool:
    provenance = field_provenance(record, field)
    return provenance in {"INFERRED_HIGH_CONFIDENCE", "INFERRED"} or field in _inferred_fields(record)


_PROVENANCE_WEIGHTS = {
    "AUTHOR_DECLARED": 1.0,
    "CURATED": 1.0,
    "INFERRED_HIGH_CONFIDENCE": 0.8,
    "INFERRED": 0.55,
    "UNKNOWN": 0.0,
}


def field_provenance(record: dict[str, Any], field: str) -> str:
    """Return the overlay provenance for one field without reading a body."""

    routing = (record.get("extensions", {}) or {}).get("routing", {}) or {}
    fields = (
        (routing.get("metadata_provenance", {}) or {}).get("fields", {}) or {}
    )
    info = fields.get(field)
    if isinstance(info, dict) and info.get("source") in _PROVENANCE_WEIGHTS:
        return str(info["source"])
    if field in routing.get("inferred_fields", []):
        return "INFERRED"
    return "AUTHOR_DECLARED" if record.get(field) else "UNKNOWN"


def metadata_quality(record: dict[str, Any]) -> float:
    """Return a modest, transparent weight for derived routing metadata."""

    values = [
        _PROVENANCE_WEIGHTS[field_provenance(record, field)]
        for field in ("roles", "stages", "task_modes", "domains")
        if record.get(field)
    ]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def field_is_routable(record: dict[str, Any], field: str) -> bool:
    """Whether a field is usable for candidate eligibility.

    The generated overlay allows inferred records to participate with a
    confidence penalty. The older compatibility view still requires an
    explicit or hinted field so broad legacy keyword matches remain filtered.
    """

    if not record.get(field):
        return False
    routing = (record.get("extensions", {}) or {}).get("routing", {}) or {}
    if routing.get("source") == "v3_routing_metadata_overlay":
        return field_provenance(record, field) != "UNKNOWN"
    return not field_is_inferred(record, field) or field_is_hinted(record, field)


def field_is_enforced(record: dict[str, Any], field: str) -> bool:
    """Whether a compatibility-view field is strong enough for hard filtering."""

    routing = (record.get("extensions", {}) or {}).get("routing", {}) or {}
    hinted = routing.get("hinted_fields", [])
    if routing.get("source") == "v3_routing_metadata_overlay":
        return field_provenance(record, field) in {
            "AUTHOR_DECLARED",
            "CURATED",
            "INFERRED_HIGH_CONFIDENCE",
        }
    return not field_is_inferred(record, field) or field in hinted


def field_is_hinted(record: dict[str, Any], field: str) -> bool:
    routing = (record.get("extensions", {}) or {}).get("routing", {}) or {}
    return field in routing.get("hinted_fields", [])


def derive_routing_metadata(record: dict[str, Any]) -> dict[str, Any]:
    """Add deterministic, explicitly marked hints to sparse legacy metadata.

    This is a read-only compatibility view. It never changes the canonical
    registry and never reads a skill body. Explicit v3 fields always win.
    """

    result = copy.deepcopy(record)
    text = _record_text(result)
    identity_text = _identity_text(result)
    inferred = _inferred_fields(result)
    routing = (result.setdefault("extensions", {})).setdefault("routing", {})
    hinted = {
        field for field in routing.get("hinted_fields", []) if isinstance(field, str)
    }
    inferred_stages = _infer_from_terms(text, _STAGE_TERMS)
    if "harden" in inferred_stages and "harden" not in _infer_from_terms(
        identity_text, {"harden": _STAGE_TERMS["harden"]}
    ):
        inferred_stages.remove("harden")
    derived: dict[str, list[str]] = {
        "stages": inferred_stages,
        "task_modes": _infer_from_terms(text, _MODE_TERMS),
        "domains": list(
            dict.fromkeys(
                [
                    _CATEGORY_DOMAINS[item]
                    for item in _categories(result)
                    if item in _CATEGORY_DOMAINS
                ]
                + _infer_from_terms(identity_text, _DOMAIN_TERMS)
            )
        ),
    }

    if result.get("skill_id") == "using-superpowers":
        derived["stages"] = list(STAGES)
        derived["task_modes"] = list(_MODE_TERMS)
        derived["domains"] = ["orchestration"]
    if result.get("skill_id") == "deep-understanding":
        derived["stages"] = ["understand"]
        derived["task_modes"] = ["research", "design", "implementation"]
        derived["domains"] = ["architecture", "orchestration"]

    for field, values in derived.items():
        if not result.get(field) and values:
            result[field] = list(dict.fromkeys(values))
            inferred.add(field)

    hint = ROUTING_HINTS.get(str(result.get("skill_id")))
    if hint:
        for field, values in hint.items():
            if field not in result or field in inferred:
                result[field] = list(dict.fromkeys(str(value) for value in values))
                inferred.add(field)
                hinted.add(field)

    if not result.get("roles"):
        roles: list[str] = []
        if result.get("skill_id") == "using-superpowers":
            roles = ["GATE"]
        elif result.get("skill_id") == "deep-understanding":
            roles = ["PROCESS"]
        else:
            category_values = set(_categories(result))
            if any(_contains_term(text, term) for term in _STAGE_TERMS["review"]):
                roles.append("REVIEW")
            if any(_contains_term(text, term) for term in _STAGE_TERMS["verify"]):
                roles.append("VERIFY")
            if any(
                _contains_term(text, term)
                for term in ("mcp", "cli", "browser", "tool", "api")
            ):
                roles.append("TOOL")
            if (
                "design-and-frontend" in category_values
                or "media-and-images" in category_values
            ):
                roles.append("DOMAIN")
            if any(_contains_term(text, term) for term in _STAGE_TERMS["design"]):
                roles.append("DOMAIN")
            if any(
                _contains_term(text, term)
                for term in (
                    "implement",
                    "build",
                    "create",
                    "plan",
                    "spec",
                    "brainstorm",
                    "research",
                    "debug",
                    "diagnos",
                    "design",
                )
            ):
                roles.append("PROCESS")
            if not roles and result.get("stages"):
                roles.append("PROCESS")
        if roles:
            result["roles"] = list(dict.fromkeys(roles))
            inferred.add("roles")

    routing.setdefault("source", "derived_compatibility_view")
    routing["inferred_fields"] = sorted(inferred)
    routing["hinted_fields"] = sorted(hinted)
    routing["body_loaded_for_inference"] = False
    return result


def task_text(task_spec: dict[str, Any], stage: dict[str, Any]) -> str:
    values = [
        task_spec.get("task_type", ""),
        task_spec.get("goal", ""),
        task_spec.get("objectives", []),
        task_spec.get("domains", []),
        stage.get("id", ""),
        stage.get("objective", ""),
        stage.get("task_type", ""),
        stage.get("domains", []),
        stage.get("required_outputs", []),
        stage.get("evidence_required", []),
    ]
    return " ".join(
        " ".join(str(item) for item in value) if isinstance(value, list) else str(value)
        for value in values
        if value is not None
    ).lower()


def required_roles_for(task_spec: dict[str, Any], stage: dict[str, Any]) -> list[str]:
    explicit = stage.get("required_roles")
    if explicit is not None:
        return list(dict.fromkeys(str(role) for role in explicit))

    stage_id = str(stage.get("id", "")).lower()
    text = task_text(task_spec, stage)
    roles: list[str] = []
    if stage_id in {
        "implement",
        "plan",
        "design",
        "research",
        "understand",
    } or task_spec.get("task_type") in {
        "implementation",
        "bugfix",
        "design",
        "research",
    }:
        roles.append("PROCESS")
    if (
        stage_id == "review"
        or task_spec.get("risk") in {"HIGH", "CRITICAL"}
        or any(
            term in text
            for term in ("security", "audit", "review", "architecture decision")
        )
    ):
        roles.append("REVIEW")
    if stage.get("domains") or task_spec.get("domains"):
        if any(
            domain not in {"software-engineering", "general", "orchestration"}
            for domain in (stage.get("domains", []) + task_spec.get("domains", []))
        ):
            roles.append("DOMAIN")
    if stage.get("evidence_required") or task_spec.get("artifact_requirements"):
        roles.append("VERIFY")
    if stage.get("required_tools") or any(
        term in text for term in ("mcp", "browser", "tool")
    ):
        roles.append("TOOL")
    if stage_id in {"harden"}:
        roles.append("REVIEW")
    if stage_id == "handoff":
        roles.append("PROCESS")
    return list(dict.fromkeys(roles))


def deep_understanding_gate(
    task_spec: dict[str, Any], stage: dict[str, Any]
) -> dict[str, str]:
    text = task_text(task_spec, stage)
    reasons: list[str] = []
    if task_spec.get("complexity") == "COMPLEX":
        reasons.append("complexity=COMPLEX")
    if task_spec.get("ambiguity") == "HIGH":
        reasons.append("ambiguity=HIGH")
    if task_spec.get("risk") in {"HIGH", "CRITICAL"}:
        reasons.append(f"risk={task_spec['risk']}")
    if task_spec.get("architecture_impact") == "ARCHITECTURE-CHANGING":
        reasons.append("architecture_impact=ARCHITECTURE-CHANGING")
    if any(
        term in text
        for term in ("unfamiliar", "contradictory evidence", "unknown architecture")
    ):
        reasons.append("unfamiliar_or_contradictory_context")
    if reasons:
        return {"status": "ELIGIBLE", "reason": "; ".join(reasons)}
    return {
        "status": "OFF",
        "reason": "task does not meet complexity, ambiguity, risk, or architecture escalation signals",
    }


def is_trivial_task(task_spec: dict[str, Any], stage: dict[str, Any]) -> bool:
    text = task_text(task_spec, stage)
    trivial_terms = (
        "typo",
        "spelling",
        "punctuation",
        "one-line",
        "rename one",
        "formatting",
    )
    return bool(
        task_spec.get("complexity") == "SIMPLE"
        and task_spec.get("risk") == "LOW"
        and task_spec.get("ambiguity") == "LOW"
        and not stage.get("evidence_required")
        and not stage.get("required_roles")
        and any(term in text for term in trivial_terms)
    )


def estimated_cost(record: dict[str, Any]) -> dict[str, int]:
    context = record.get("context_cost", {}) or {}
    metadata_source = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    metadata_tokens = context.get("metadata_tokens")
    instruction_tokens = context.get("instruction_tokens_estimate")
    tool_schema_tokens = context.get("tool_schema_tokens")
    return {
        "metadata_tokens": int(metadata_tokens)
        if isinstance(metadata_tokens, int)
        else max(1, len(metadata_source) // 4),
        "instruction_tokens": int(instruction_tokens)
        if isinstance(instruction_tokens, int)
        else max(20, len(record.get("description", "")) // 3),
        "tool_schema_tokens": int(tool_schema_tokens)
        if isinstance(tool_schema_tokens, int)
        else 0,
        "tool_calls": int(
            (record.get("runtime_cost", {}) or {}).get("tool_calls_estimate", 0) or 0
        ),
    }


@dataclass(frozen=True)
class CandidateScore:
    skill_id: str
    role: str
    score: float
    components: dict[str, float]
    cost: dict[str, int]


def choose_role(record: dict[str, Any], required_roles: Iterable[str]) -> str | None:
    roles = [
        role for role in record.get("roles", []) if role in ROLES and role != "GATE"
    ]
    if not roles:
        return None
    required = list(required_roles)
    for role in required:
        if role in roles:
            return role
    for role in ("PROCESS", "DOMAIN", "TOOL", "REVIEW", "VERIFY"):
        if role in roles:
            return role
    return roles[0]


def score_candidate(
    record: dict[str, Any],
    task_spec: dict[str, Any],
    stage: dict[str, Any],
    required_roles: Iterable[str],
    *,
    relationship_bonus: float = 0.0,
) -> CandidateScore | None:
    role = choose_role(record, required_roles)
    if role is None:
        return None
    stage_id = str(stage.get("id", "")).lower()
    task_type = str(stage.get("task_type") or task_spec.get("task_type") or "").lower()
    text = task_text(task_spec, stage)
    record_text = _record_text(record)
    task_tokens = _text_tokens(text)
    skill_tokens = _text_tokens(record_text)
    overlap = len(task_tokens & skill_tokens)
    trigger_tokens = _text_tokens(record.get("triggers", []))
    trigger_overlap = len(task_tokens & trigger_tokens)
    required_outputs = {
        str(item).lower()
        for item in (
            list(stage.get("required_outputs", []))
            + list(stage.get("evidence_required", []))
            + list(task_spec.get("artifact_requirements", []))
        )
    }
    output_values = set(str(item).lower() for item in record.get("outputs", []))
    domain_values = set(str(item).lower() for item in stage.get("domains", [])) | set(
        str(item).lower() for item in task_spec.get("domains", [])
    )
    skill_domains = set(str(item).lower() for item in record.get("domains", []))
    domain_overlap = len(domain_values & skill_domains)
    modes = {str(item).lower() for item in record.get("task_modes", [])}
    stages = {str(item).lower() for item in record.get("stages", [])}
    inferred_stage = field_is_inferred(record, "stages")
    inferred_mode = field_is_inferred(record, "task_modes")
    inferred_domain = field_is_inferred(record, "domains")
    explicit_stage = stage_id in stages
    explicit_mode = task_type in modes
    textual_output_match = any(
        _contains_term(record_text, output)
        for output in required_outputs
        if output and role == "VERIFY"
    )
    explicit_output = bool(required_outputs & output_values) or textual_output_match
    components: dict[str, float] = {
        "task_relevance": float(
            (1 if explicit_mode and inferred_mode else 3 if explicit_mode else 0)
            + min(overlap, 4)
        ),
        "stage_relevance": float(
            (1.5 if inferred_stage else 4) if explicit_stage else min(1.0, overlap / 4)
        ),
        "domain_match": float(
            (1 if inferred_domain else 3) * domain_overlap
            + (1 if domain_values and not skill_domains else 0)
        ),
        "role_need": float(4 if role in set(required_roles) else 1),
        "trigger_match": float(min(3, trigger_overlap)),
        "required_output_match": float(2 if explicit_output else 0),
        "relationship_bonus": float(relationship_bonus),
        "capability_fit": 1.0,
        "trust": 2.0 if record.get("trust") == "CORE_TRUSTED" else 1.0,
        "metadata_confidence": metadata_quality(record),
        "historical_evidence": 0.0,
    }
    cost = estimated_cost(record)
    components["context_cost_penalty"] = -min(3.0, cost["instruction_tokens"] / 1000.0)
    total = round(sum(components.values()), 3)
    return CandidateScore(record["skill_id"], role, total, components, cost)
