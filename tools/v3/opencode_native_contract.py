"""Narrow, provenance-bound validation for OpenCode 1.x projections.

The adapter uses only a small subset of the installed release contract.  The
checked-in snapshot is validated offline; runtime execution never fetches
OpenCode source or merges current-main assumptions into the projection.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.v3.contract_validation import validate_instance
from tools.v3.execution_bundle import digest_record


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = (
    ROOT / "fixtures" / "v3" / "opencode" / "opencode-native-contract-1.18.25.json"
)

OPENCODE_RUNTIME_ID = "opencode"
INSTALLED_RUNTIME_VERSION = "1.18.25"
INSTALLED_RELEASE_TAG = "v1.18.25"
INSTALLED_RELEASE_COMMIT = "cb7d8b2f5e44876ef98b661dc10590c915af3a9f"
INSTALLED_NATIVE_CONTRACT_REVISION = (
    "opencode-v1-config-permission-run@" + INSTALLED_RELEASE_COMMIT
)
INSTALLED_CONTRACT_DIGEST = (
    "sha256:3e4147fcd2a6edb726aec76ed2782343d92df9593cfcf49e8685f21bfc129853"
)

CONTRACT_TARGETS = frozenset(
    {"INSTALLED_RUNTIME", "SOURCE_SNAPSHOT", "DOCUMENTATION_SNAPSHOT"}
)
SUPPORT_LEVELS = frozenset({"NATIVE", "EMULATED", "HOST_MANAGED", "UNSUPPORTED"})
AVAILABILITY_LEVELS = frozenset(
    {"INSTALLED", "RELEASE_SUPPORTED", "UPSTREAM_ONLY", "UNKNOWN"}
)
NATIVE_SUPPORT_LEVELS = frozenset({"NATIVE_EXACT", "HOST_MANAGED", "UNSUPPORTED"})
PERMISSION_ACTIONS = frozenset({"allow", "ask", "deny"})
NATIVE_CONFIG_FIELDS = frozenset({"$schema", "permission", "plugin", "mcp"})
PERMISSION_KEYS = frozenset(
    {
        "*",
        "read",
        "edit",
        "glob",
        "grep",
        "list",
        "bash",
        "task",
        "external_directory",
        "todowrite",
        "question",
        "webfetch",
        "websearch",
        "repo_clone",
        "repo_overview",
        "lsp",
        "doom_loop",
        "skill",
    }
)

KNOWN_RELEASES: dict[str, dict[str, str]] = {
    INSTALLED_RUNTIME_VERSION: {
        "release_tag": INSTALLED_RELEASE_TAG,
        "release_commit": INSTALLED_RELEASE_COMMIT,
        "contract_source_commit": INSTALLED_RELEASE_COMMIT,
        "native_contract_revision": INSTALLED_NATIVE_CONTRACT_REVISION,
        "contract_digest": INSTALLED_CONTRACT_DIGEST,
    }
}

PROVENANCE_FIELDS = (
    "runtime_id",
    "observed_runtime_version",
    "release_tag",
    "release_commit",
    "contract_target",
    "contract_source_commit",
    "native_contract_revision",
    "contract_digest",
    "docs_snapshot_date",
    "verification_method",
    "support",
    "availability",
)


@dataclass(frozen=True)
class NativeConfigValidation:
    """Result of validating config values against the pinned native target."""

    errors: list[str] = field(default_factory=list)
    source_revision: str | None = None
    native_contract_revision: str | None = None
    reason_code: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return not self.errors


class NativeContractError(ValueError):
    """Raised when a native projection cannot be proven for the target."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def load_native_contract(path: str | Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    """Load the checked-in OpenCode contract without network access."""

    with Path(path).open(encoding="utf-8") as handle:
        contract = json.load(handle)
    if not isinstance(contract, dict):
        raise ValueError("OpenCode native contract must be an object")
    return contract


def _projection_provenance(contract: dict[str, Any]) -> dict[str, Any]:
    return {field_name: contract.get(field_name) for field_name in PROVENANCE_FIELDS}


def _validate_contract_provenance(
    contract: dict[str, Any],
    *,
    expected_target: str,
    observed_runtime_version: str | None,
) -> tuple[list[str], str | None]:
    errors: list[str] = []
    reason_code: str | None = None

    def unverified(message: str) -> None:
        nonlocal reason_code
        errors.append(message)
        reason_code = "RUNTIME_CONTRACT_UNVERIFIED"

    if expected_target not in CONTRACT_TARGETS:
        unverified(f"unsupported expected OpenCode contract target: {expected_target}")
        return errors, reason_code
    target = contract.get("contract_target")
    if target != expected_target:
        unverified(
            f"OpenCode contract target mismatch: expected {expected_target}, got {target}"
        )
    if contract.get("runtime_id") != OPENCODE_RUNTIME_ID:
        unverified("OpenCode contract runtime_id must be 'opencode'")
    if contract.get("support") not in SUPPORT_LEVELS:
        unverified(f"unsupported OpenCode contract support: {contract.get('support')}")
    if contract.get("availability") not in AVAILABILITY_LEVELS:
        unverified(
            f"unsupported OpenCode contract availability: {contract.get('availability')}"
        )

    if expected_target != "INSTALLED_RUNTIME":
        unverified(
            "only an explicitly verified installed OpenCode release may produce this executable projection"
        )
        return errors, reason_code

    expected = KNOWN_RELEASES.get(observed_runtime_version or "")
    if expected is None:
        unverified(
            "no verified OpenCode release mapping for observed runtime "
            f"{observed_runtime_version!r}"
        )
        return errors, reason_code

    expected_values = {
        "observed_runtime_version": observed_runtime_version,
        "release_tag": expected["release_tag"],
        "release_commit": expected["release_commit"],
        "contract_source_commit": expected["contract_source_commit"],
        "native_contract_revision": expected["native_contract_revision"],
        "contract_digest": expected["contract_digest"],
        "availability": "INSTALLED",
        "support": "NATIVE",
    }
    for field_name, expected_value in expected_values.items():
        if contract.get(field_name) != expected_value:
            unverified(
                "OpenCode installed-runtime contract mismatch for "
                f"{field_name}: expected {expected_value!r}, got {contract.get(field_name)!r}"
            )
    if digest_record(contract, "contract_digest") != contract.get("contract_digest"):
        unverified("OpenCode native contract_digest does not match its canonical payload")
    return errors, reason_code


def validate_native_contract(
    contract: dict[str, Any] | None = None,
    *,
    expected_target: str = "INSTALLED_RUNTIME",
    observed_runtime_version: str | None = INSTALLED_RUNTIME_VERSION,
) -> NativeConfigValidation:
    """Validate contract shape, provenance, and digest before config values."""

    native_contract = load_native_contract() if contract is None else copy.deepcopy(contract)
    shape = validate_instance("OpenCodeNativeContract", native_contract)
    errors = list(shape.errors)
    provenance_errors, reason_code = _validate_contract_provenance(
        native_contract,
        expected_target=expected_target,
        observed_runtime_version=observed_runtime_version,
    )
    errors.extend(provenance_errors)
    if errors and reason_code is None:
        reason_code = "RUNTIME_CONTRACT_UNVERIFIED"
    return NativeConfigValidation(
        errors=errors,
        source_revision=native_contract.get("contract_source_commit"),
        native_contract_revision=native_contract.get("native_contract_revision"),
        reason_code=reason_code,
        provenance=_projection_provenance(native_contract),
    )


def _validate_permission_rule(path: str, value: Any) -> list[str]:
    if isinstance(value, str):
        return [] if value in PERMISSION_ACTIONS else [
            f"unsupported OpenCode permission action at {path}: {value}"
        ]
    if not isinstance(value, dict):
        return [f"OpenCode permission rule at {path} must be an action or pattern object"]
    errors: list[str] = []
    for pattern, action in value.items():
        if not isinstance(pattern, str) or not pattern:
            errors.append(f"OpenCode permission pattern at {path} must be a non-empty string")
        if action not in PERMISSION_ACTIONS:
            errors.append(f"unsupported OpenCode permission action at {path}.{pattern}: {action}")
    return errors


def _validate_value(path: str, value: Any, spec: dict[str, Any]) -> list[str]:
    expected_type = spec.get("type")
    if expected_type == "string" and not isinstance(value, str):
        return [f"OpenCode config {path} must be a string"]
    if expected_type == "object" and not isinstance(value, dict):
        return [f"OpenCode config {path} must be an object"]
    if expected_type == "array" and not isinstance(value, list):
        return [f"OpenCode config {path} must be an array"]
    return []


def validate_opencode_config(
    values: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
    expected_target: str = "INSTALLED_RUNTIME",
    observed_runtime_version: str | None = INSTALLED_RUNTIME_VERSION,
) -> NativeConfigValidation:
    """Validate a narrow config against the pinned installed OpenCode target."""

    native_contract = load_native_contract() if contract is None else contract
    contract_validation = validate_native_contract(
        native_contract,
        expected_target=expected_target,
        observed_runtime_version=observed_runtime_version,
    )
    errors = list(contract_validation.errors)
    if not isinstance(values, dict):
        errors.append("OpenCode config values must be an object")
        return NativeConfigValidation(
            errors=errors,
            source_revision=contract_validation.source_revision,
            native_contract_revision=contract_validation.native_contract_revision,
            reason_code=contract_validation.reason_code or "INVALID_NATIVE_CONFIG",
            provenance=contract_validation.provenance,
        )

    fields = native_contract.get("fields", {})
    for key, value in values.items():
        if key not in NATIVE_CONFIG_FIELDS or key not in fields:
            errors.append(f"unsupported OpenCode native config field: {key}")
            continue
        errors.extend(_validate_value(key, value, fields[key]))

    permission = values.get("permission")
    if isinstance(permission, dict):
        for key, rule in permission.items():
            if key not in PERMISSION_KEYS:
                errors.append(f"unsupported OpenCode permission class: {key}")
                continue
            errors.extend(_validate_permission_rule(f"permission.{key}", rule))

    plugin = values.get("plugin")
    if plugin is not None and isinstance(plugin, list):
        errors.extend(
            f"OpenCode plugin reference must be a string at plugin[{index}]"
            for index, item in enumerate(plugin)
            if not isinstance(item, str)
        )
    mcp = values.get("mcp")
    if mcp is not None and not isinstance(mcp, dict):
        errors.append("OpenCode mcp config must be an object")

    reason_code = contract_validation.reason_code
    if errors and reason_code is None:
        reason_code = "INVALID_NATIVE_CONFIG"
    return NativeConfigValidation(
        errors=errors,
        source_revision=contract_validation.source_revision,
        native_contract_revision=contract_validation.native_contract_revision,
        reason_code=reason_code,
        provenance=contract_validation.provenance,
    )

