"""Validation for the Agent Skills Matrix v3 machine-readable contracts.

The repository intentionally has no runtime dependency on a schema library.
This module validates the small JSON Schema vocabulary used by the checked-in
contracts and adds the cross-record rules that JSON Schema cannot express:
unknown capabilities are never silently granted, and only dependency-like
relationships must be acyclic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "v3"
SCHEMA_FILES = {
    "TaskSpec": "task-spec.schema.json",
    "SkillMetadataV3": "skill-metadata-v3.schema.json",
    "AgentAdapterManifest": "agent-adapter-manifest.schema.json",
    "ModelProfile": "model-profile.schema.json",
    "StageRoute": "stage-route.schema.json",
    "CompiledExecutionBundle": "compiled-execution-bundle.schema.json",
    "CodexNativeProjection": "codex-native-projection.schema.json",
    "SkillRoutingMetadata": "skill-routing-metadata.schema.json",
    "SkillRoutingGenerated": "skill-routing-generated.schema.json",
    "SkillRoutingCurated": "skill-routing-curated.schema.json",
    "RuntimeCandidate": "runtime-candidate.schema.json",
    "ModelCandidate": "model-candidate.schema.json",
    "ExecutionConfiguration": "execution-configuration.schema.json",
    "EvaluationRun": "evaluation-run.schema.json",
    "EvaluationResult": "evaluation-result.schema.json",
    "RuntimeHandoff": "runtime-handoff.schema.json",
    "LiveExecutionRecord": "live-execution-record.schema.json",
    "OpenCodeNativeContract": "opencode-native-contract.schema.json",
    "OpenCodeNativeProjection": "opencode-native-projection.schema.json",
}

KNOWN_CAPABILITIES = frozenset(
    {
        "needs_editing",
        "needs_browser",
        "needs_subagents",
        "needs_sandbox",
        "needs_MCP",
        "needs_structured_output",
        "needs_long_context",
        "needs_multimodal",
        "editing",
        "browser",
        "subagents",
        "sandbox",
        "MCP",
        "structured_output",
        "parallelism",
        "native_learning",
        "model_selection",
        "reasoning_effort",
        "long_context",
        "multimodal",
        "vision",
        "commands",
        "plugins",
        "hooks",
        "tool_use",
        "tool_use_reliability",
        "coding",
        "planning",
        "debugging",
        "research",
        "review",
        "security",
        "skills",
        "persistent_context",
        "filesystem",
        "network",
        "permission_profiles",
        "mcp_tool_calls",
    }
)

MODEL_AUTHORITY_FORBIDDEN_CAPABILITIES = frozenset(
    {
        "editing",
        "browser",
        "subagents",
        "sandbox",
        "MCP",
        "skills",
        "persistent_context",
        "filesystem",
        "network",
        "permission_profiles",
        "plugins",
        "hooks",
        "commands",
        "native_learning",
        "model_selection",
        "reasoning_effort",
        "parallelism",
    }
)


@dataclass
class ValidationResult:
    """Machine-readable validation output."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unknown_capabilities: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def extend(self, other: "ValidationResult", prefix: str = "") -> None:
        self.errors.extend(f"{prefix}{item}" for item in other.errors)
        self.warnings.extend(f"{prefix}{item}" for item in other.warnings)
        for capability in other.unknown_capabilities:
            if capability not in self.unknown_capabilities:
                self.unknown_capabilities.append(capability)


class SchemaError(ValueError):
    """Raised when a checked-in schema cannot be loaded or resolved."""


def load_schema(contract: str) -> dict[str, Any]:
    """Load one of the public v3 schemas by contract name."""

    try:
        filename = SCHEMA_FILES[contract]
    except KeyError as exc:
        raise SchemaError(f"unknown contract: {contract}") from exc
    path = SCHEMA_DIR / filename
    try:
        with path.open(encoding="utf-8") as handle:
            schema = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaError(f"cannot load schema {path}: {exc}") from exc
    if not isinstance(schema, dict):
        raise SchemaError(f"schema {path} is not an object")
    return schema


def validate_instance(
    contract: str,
    instance: Any,
    *,
    strict_unknown_capabilities: bool | None = None,
) -> ValidationResult:
    """Validate an in-memory instance against a v3 contract.

    Capability names remain open for future extensions. Unknown names are a
    warning on declarations and requirements, but a StageRoute cannot claim
    an unknown capability as granted. Callers may set ``strict_unknown`` for
    an even narrower boundary.
    """

    schema = load_schema(contract)
    result = ValidationResult()
    _validate(instance, schema, schema, SCHEMA_DIR, "$", result.errors)
    _validate_capabilities(contract, instance, result, strict_unknown_capabilities)
    if contract in {"ModelProfile", "ModelCandidate"} and isinstance(instance, dict):
        capabilities = instance.get("capabilities", {})
        if isinstance(capabilities, dict):
            for capability in sorted(set(capabilities) & MODEL_AUTHORITY_FORBIDDEN_CAPABILITIES):
                result.errors.append(
                    f"model: capability {capability!r} belongs to a runtime and cannot grant authority"
                )
    return result


def validate_file(
    contract: str,
    path: str | Path,
    *,
    strict_unknown_capabilities: bool | None = None,
) -> ValidationResult:
    """Load and validate a JSON fixture or contract record."""

    result = ValidationResult()
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as handle:
            instance = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        result.errors.append(f"{path}: cannot load JSON: {exc}")
        return result
    result.extend(
        validate_instance(
            contract,
            instance,
            strict_unknown_capabilities=strict_unknown_capabilities,
        ),
        prefix=f"{path}: ",
    )
    return result


def validate_agent_model_separation(
    agent_manifest: dict[str, Any], model_profile: dict[str, Any]
) -> ValidationResult:
    """Validate two records while preserving runtime/provider separation."""

    result = ValidationResult()
    result.extend(
        validate_instance("AgentAdapterManifest", agent_manifest),
        prefix="agent: ",
    )
    result.extend(validate_instance("ModelProfile", model_profile), prefix="model: ")

    if "provider_id" in agent_manifest:
        result.errors.append("agent: provider_id belongs to ModelProfile, not AgentAdapterManifest")
    if "runtime_id" in model_profile:
        result.errors.append("model: runtime_id belongs to AgentAdapterManifest, not ModelProfile")
    if agent_manifest.get("runtime_id") == model_profile.get("model_id"):
        result.errors.append("agent/model: runtime_id and model_id must remain separate identifiers")
    return result


def validate_relationship_graph(records: list[dict[str, Any]]) -> ValidationResult:
    """Validate relationship semantics across a set of skill records.

    Self references are always rejected. Cycles are rejected only for
    ``REQUIRES`` and ``SUPERSEDES``; complementary or recommendation cycles
    are legitimate and therefore remain allowed.
    """

    result = ValidationResult()
    ids: set[str] = set()
    for index, record in enumerate(records):
        item_result = validate_instance("SkillMetadataV3", record)
        result.extend(item_result, prefix=f"record[{index}]: ")
        skill_id = record.get("skill_id")
        if isinstance(skill_id, str):
            if skill_id in ids:
                result.errors.append(f"duplicate skill_id: {skill_id}")
            ids.add(skill_id)

    graph: dict[str, dict[str, set[str]]] = {skill_id: {} for skill_id in ids}
    for record in records:
        source = record.get("skill_id")
        if not isinstance(source, str):
            continue
        for relationship in record.get("relationships", []):
            relation_type = relationship.get("type")
            target = relationship.get("target")
            if not isinstance(target, str) or not isinstance(relation_type, str):
                continue
            if source == target:
                result.errors.append(
                    f"relationship {relation_type} cannot self-reference {source}"
                )
            if target not in ids:
                result.warnings.append(
                    f"relationship target is unresolved: {source} -> {target}"
                )
            graph.setdefault(source, {}).setdefault(relation_type, set()).add(target)

    for relation_type in ("REQUIRES", "SUPERSEDES"):
        adjacency = {
            source: targets.get(relation_type, set()) & ids
            for source, targets in graph.items()
        }
        if _has_cycle(adjacency):
            result.errors.append(f"{relation_type} relationship graph contains a cycle")
    return result


def _has_cycle(adjacency: dict[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in adjacency.get(node, set())):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in adjacency)


def _validate_capabilities(
    contract: str,
    instance: Any,
    result: ValidationResult,
    strict_unknown_capabilities: bool | None,
) -> None:
    if not isinstance(instance, dict):
        return

    if contract in {"TaskSpec", "SkillMetadataV3"}:
        candidates = instance.get("required_capabilities", [])
    elif contract in {"AgentAdapterManifest", "ModelProfile"}:
        capabilities = instance.get("capabilities", {})
        candidates = list(capabilities) if isinstance(capabilities, dict) else []
    elif contract == "StageRoute":
        candidates = instance.get("granted_capabilities", [])
    elif contract == "CompiledExecutionBundle":
        candidates = instance.get("effective_capabilities", [])
    elif contract in {"SkillRoutingGenerated", "SkillRoutingCurated", "SkillRoutingMetadata"}:
        candidates = []
    elif contract in {"RuntimeCandidate", "ModelCandidate"}:
        capabilities = instance.get("capabilities", {})
        candidates = list(capabilities) if isinstance(capabilities, dict) else []
    elif contract == "ExecutionConfiguration":
        candidates = instance.get("effective_capabilities", [])
    else:
        candidates = []

    unknown = [
        capability
        for capability in candidates
        if isinstance(capability, str)
        and capability not in KNOWN_CAPABILITIES
        and not capability.startswith(("x-", "custom:"))
    ]
    result.unknown_capabilities.extend(unknown)
    if not unknown:
        return

    # A route is an authorization/evidence record. Callers cannot opt out of
    # the invariant that an unknown capability is never recorded as granted.
    strict = (
        True
        if contract in {"StageRoute", "CompiledExecutionBundle"}
        else bool(strict_unknown_capabilities)
    )
    message = "unknown capability remains unsatisfied: "
    if strict:
        result.errors.extend(f"{message}{capability}" for capability in unknown)
    else:
        result.warnings.extend(f"{message}{capability}" for capability in unknown)


def _resolve_ref(
    reference: str,
    root_schema: dict[str, Any],
    base_dir: Path,
) -> tuple[Any, dict[str, Any], Path]:
    file_ref, _, fragment = reference.partition("#")
    if file_ref:
        schema_path = (base_dir / file_ref).resolve()
        try:
            with schema_path.open(encoding="utf-8") as handle:
                external_root = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise SchemaError(f"cannot resolve {reference}: {exc}") from exc
        target_root = external_root
        target_base = schema_path.parent
    else:
        target_root = root_schema
        target_base = base_dir

    target: Any = target_root
    if fragment:
        if not fragment.startswith("/"):
            raise SchemaError(f"unsupported schema fragment in {reference}")
        for token in fragment.lstrip("/").split("/"):
            target = target[token.replace("~1", "/").replace("~0", "~")]
    return target, target_root, target_base


def _validate(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    base_dir: Path,
    path: str,
    errors: list[str],
) -> None:
    if "$ref" in schema:
        target, target_root, target_base = _resolve_ref(schema["$ref"], root_schema, base_dir)
        _validate(value, target, target_root, target_base, path, errors)
        return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not one of {schema['enum']!r}")

    if "anyOf" in schema:
        branches = []
        for branch in schema["anyOf"]:
            branch_errors: list[str] = []
            _validate(value, branch, root_schema, base_dir, path, branch_errors)
            if not branch_errors:
                break
            branches.append(branch_errors)
        else:
            errors.append(f"{path}: does not match any allowed schema")

    if "oneOf" in schema:
        matches = 0
        for branch in schema["oneOf"]:
            branch_errors: list[str] = []
            _validate(value, branch, root_schema, base_dir, path, branch_errors)
            if not branch_errors:
                matches += 1
        if matches != 1:
            errors.append(f"{path}: must match exactly one schema, matched {matches}")

    if "allOf" in schema:
        for branch in schema["allOf"]:
            _validate(value, branch, root_schema, base_dir, path, errors)

    if "if" in schema:
        condition_errors: list[str] = []
        _validate(value, schema["if"], root_schema, base_dir, path, condition_errors)
        branch = schema.get("then") if not condition_errors else schema.get("else")
        if branch:
            _validate(value, branch, root_schema, base_dir, path, errors)

    expected_types = schema.get("type")
    if expected_types is not None and not _matches_type(value, expected_types):
        errors.append(f"{path}: expected type {expected_types!r}, got {type(value).__name__}")
        return

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing required property {required!r}")
        for key, child in value.items():
            if key in properties:
                _validate(value[key], properties[key], root_schema, base_dir, f"{path}.{key}", errors)
            elif "additionalProperties" in schema:
                additional = schema["additionalProperties"]
                if additional is False:
                    errors.append(f"{path}: unexpected property {key!r}")
                elif isinstance(additional, dict):
                    _validate(value[key], additional, root_schema, base_dir, f"{path}.{key}", errors)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: expected at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: expected at most {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True) for item in value]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{path}: items must be unique")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate(item, schema["items"], root_schema, base_dir, f"{path}[{index}]", errors)

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: string is shorter than {schema['minLength']} characters")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: string is longer than {schema['maxLength']} characters")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: string does not match required pattern")
        _validate_format(value, schema.get("format"), path, errors)

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: number is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: number is above maximum {schema['maximum']}")


def _matches_type(value: Any, expected: str | list[str]) -> bool:
    expected_values = [expected] if isinstance(expected, str) else expected
    for name in expected_values:
        if name == "object" and isinstance(value, dict):
            return True
        if name == "array" and isinstance(value, list):
            return True
        if name == "string" and isinstance(value, str):
            return True
        if name == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if name == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if name == "boolean" and isinstance(value, bool):
            return True
        if name == "null" and value is None:
            return True
    return False


def _validate_format(value: str, format_name: str | None, path: str, errors: list[str]) -> None:
    if format_name == "uri":
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            errors.append(f"{path}: expected an absolute URI")
    elif format_name == "date-time":
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{path}: expected an ISO 8601 date-time")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", choices=sorted(SCHEMA_FILES))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    validation = validate_file(args.contract, args.path)
    print(
        json.dumps(
            {
                "valid": validation.valid,
                "errors": validation.errors,
                "warnings": validation.warnings,
                "unknown_capabilities": validation.unknown_capabilities,
            },
            indent=2,
        )
    )
    raise SystemExit(0 if validation.valid else 1)
