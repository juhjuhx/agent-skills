"""Narrow, pinned validation for Codex config values emitted by v3."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = ROOT / "fixtures" / "v3" / "codex" / "codex-native-config-contract.json"
PINNED_CODEX_SOURCE_REVISION = "45305dd229c01e6cb6e122f6559e4f9b805bae6"
PINNED_NATIVE_CONTRACT_REVISION = (
    "codex-rs/core/config.schema.json@" + PINNED_CODEX_SOURCE_REVISION
)


@dataclass(frozen=True)
class NativeConfigValidation:
    """Validation result with the source revisions used for the decision."""

    errors: list[str] = field(default_factory=list)
    source_revision: str | None = None
    native_contract_revision: str | None = None

    @property
    def valid(self) -> bool:
        return not self.errors


def load_native_contract(path: str | Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    """Load the checked-in narrow contract; never retrieve it at runtime."""

    with Path(path).open(encoding="utf-8") as handle:
        contract = json.load(handle)
    if not isinstance(contract, dict):
        raise ValueError("Codex native contract must be a JSON object")
    return contract


def validate_codex_config(
    values: dict[str, Any], *, contract: dict[str, Any] | None = None
) -> NativeConfigValidation:
    """Validate emitted values against the pinned native contract subset."""

    native_contract = load_native_contract() if contract is None else contract
    if not isinstance(native_contract, dict):
        return NativeConfigValidation(["Codex native contract must be an object"])
    errors: list[str] = []
    source_revision = native_contract.get("codex_source_revision")
    native_contract_revision = native_contract.get("native_contract_revision")
    if source_revision != PINNED_CODEX_SOURCE_REVISION:
        errors.append(
            "Codex native contract source revision mismatch: "
            f"expected {PINNED_CODEX_SOURCE_REVISION}, got {source_revision}"
        )
    if native_contract_revision != PINNED_NATIVE_CONTRACT_REVISION:
        errors.append(
            "Codex native contract revision mismatch: "
            f"expected {PINNED_NATIVE_CONTRACT_REVISION}, got {native_contract_revision}"
        )
    fields = native_contract.get("fields")
    if not isinstance(fields, dict):
        errors.append("Codex native contract fields must be an object")
        fields = {}
    if not isinstance(values, dict):
        errors.append("Codex config values must be an object")
        return NativeConfigValidation(errors, source_revision, native_contract_revision)

    for key, value in values.items():
        spec = fields.get(key)
        if not isinstance(spec, dict):
            errors.append(f"unsupported Codex config field: {key}")
            continue
        errors.extend(_validate_value(key, value, spec))
    return NativeConfigValidation(errors, source_revision, native_contract_revision)


def _validate_value(path: str, value: Any, spec: dict[str, Any]) -> list[str]:
    one_of = spec.get("one_of")
    if isinstance(one_of, list):
        for branch in one_of:
            if isinstance(branch, dict):
                errors = _validate_value(path, value, branch)
                if not errors:
                    return []
        return [f"invalid Codex config value at {path}: no native one-of branch matched"]

    expected_type = spec.get("type")
    if expected_type == "string":
        if not isinstance(value, str):
            return [f"Codex config {path} must be a string"]
        if len(value) < int(spec.get("min_length", 0)):
            return [f"Codex config {path} must not be empty"]
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            return [f"Codex config {path} must be a boolean"]
    elif expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return [f"Codex config {path} must be an integer"]
        if "minimum" in spec and value < spec["minimum"]:
            return [f"Codex config {path} is below its native minimum"]
    elif expected_type == "object":
        if not isinstance(value, dict):
            return [f"Codex config {path} must be an object"]
        required = spec.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            return [f"Codex config {path} is missing required keys: {', '.join(missing)}"]
        if spec.get("additional_properties") is False:
            unknown = sorted(set(value) - set(spec.get("properties", {})))
            if unknown:
                return [f"unsupported Codex config keys at {path}: {', '.join(unknown)}"]
        errors: list[str] = []
        for key, child in spec.get("properties", {}).items():
            if key in value and isinstance(child, dict):
                errors.extend(_validate_value(f"{path}.{key}", value[key], child))
        return errors
    else:
        return [f"Codex native contract has unsupported validator type at {path}"]

    enum = spec.get("enum")
    if enum is not None and value not in enum:
        return [f"unsupported Codex config value at {path}: {value}"]
    return []
