"""Narrow, provenance-bound validation for Claude Code 2.1.235.

The installed Claude CLI is treated as a black-box runtime: this contract is
derived from the observed version/help surface and first-party documentation,
not from an invented source tree.  Runtime execution never fetches docs or
mutates Claude configuration.
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
    ROOT / "fixtures" / "v3" / "claude" / "claude-native-contract-2.1.235.json"
)

CLAUDE_RUNTIME_ID = "claude-code"
INSTALLED_RUNTIME_VERSION = "2.1.235"
# Claude Code is distributed as a proprietary CLI; no immutable source
# commit/tag was exposed by the installed binary or its version command.
INSTALLED_RELEASE_TAG = None
INSTALLED_RELEASE_COMMIT = None
INSTALLED_CONTRACT_SOURCE_COMMIT = None
INSTALLED_NATIVE_CONTRACT_REVISION = "claude-cli-help@2.1.235"
INSTALLED_CONTRACT_DIGEST = "sha256:8d25516eaed8a4ad0a746efaf97de3b36e85e735ae6ba188651dc1305b6a00c5"

CONTRACT_TARGETS = frozenset(
    {"INSTALLED_RUNTIME", "SOURCE_SNAPSHOT", "DOCUMENTATION_SNAPSHOT"}
)
SUPPORT_LEVELS = frozenset({"NATIVE", "EMULATED", "HOST_MANAGED", "UNSUPPORTED"})
AVAILABILITY_LEVELS = frozenset(
    {"INSTALLED", "RELEASE_SUPPORTED", "UPSTREAM_ONLY", "UNKNOWN"}
)

KNOWN_RELEASES: dict[str, dict[str, Any]] = {
    INSTALLED_RUNTIME_VERSION: {
        "release_tag": INSTALLED_RELEASE_TAG,
        "release_commit": INSTALLED_RELEASE_COMMIT,
        "contract_source_commit": INSTALLED_CONTRACT_SOURCE_COMMIT,
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
    """Result of validating Claude config against one pinned target."""

    errors: list[str] = field(default_factory=list)
    source_revision: str | None = None
    native_contract_revision: str | None = None
    reason_code: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return not self.errors


class NativeContractError(ValueError):
    """Raised when a Claude projection cannot be proven for its target."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def load_native_contract(path: str | Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    """Load the checked-in contract without network access."""

    with Path(path).open(encoding="utf-8") as handle:
        contract = json.load(handle)
    if not isinstance(contract, dict):
        raise ValueError("Claude native contract must be an object")
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
        unverified(f"unsupported expected Claude contract target: {expected_target}")
        return errors, reason_code
    if contract.get("contract_target") != expected_target:
        unverified(
            "Claude contract target mismatch: "
            f"expected {expected_target}, got {contract.get('contract_target')}"
        )
    if contract.get("runtime_id") != CLAUDE_RUNTIME_ID:
        unverified("Claude contract runtime_id must be 'claude-code'")
    if contract.get("support") not in SUPPORT_LEVELS:
        unverified(f"unsupported Claude contract support: {contract.get('support')}")
    if contract.get("availability") not in AVAILABILITY_LEVELS:
        unverified(
            f"unsupported Claude contract availability: {contract.get('availability')}"
        )

    if expected_target != "INSTALLED_RUNTIME":
        unverified(
            "only an explicitly verified installed Claude release may produce "
            "this executable projection"
        )
        return errors, reason_code

    expected = KNOWN_RELEASES.get(observed_runtime_version or "")
    if expected is None:
        unverified(
            "no verified Claude release mapping for observed runtime "
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
                "Claude installed-runtime contract mismatch for "
                f"{field_name}: expected {expected_value!r}, got {contract.get(field_name)!r}"
            )
    if digest_record(contract, "contract_digest") != contract.get("contract_digest"):
        unverified("Claude native contract_digest does not match its canonical payload")
    return errors, reason_code


def validate_native_contract(
    contract: dict[str, Any] | None = None,
    *,
    expected_target: str = "INSTALLED_RUNTIME",
    observed_runtime_version: str | None = INSTALLED_RUNTIME_VERSION,
) -> NativeConfigValidation:
    """Validate contract shape, provenance, and digest before config values."""

    native_contract = load_native_contract() if contract is None else copy.deepcopy(contract)
    shape = validate_instance("ClaudeNativeContract", native_contract)
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


def _value_type_matches(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def _validate_value(path: str, value: Any, spec: dict[str, Any]) -> list[str]:
    expected_type = spec.get("type")
    if not isinstance(expected_type, str) or not _value_type_matches(value, expected_type):
        return [f"Claude config {path} has unsupported native type/value"]
    enum = spec.get("enum")
    if isinstance(enum, list) and value not in enum:
        return [f"unsupported Claude config value at {path}: {value}"]
    if expected_type == "array":
        items_enum = spec.get("items_enum")
        if not all(isinstance(item, str) for item in value):
            return [f"Claude config {path} items must be strings"]
        if isinstance(items_enum, list):
            unknown = sorted(set(value) - set(items_enum))
            if unknown:
                return [
                    f"unsupported Claude config values at {path}: {', '.join(unknown)}"
                ]
    if "minimum" in spec and isinstance(value, (int, float)) and value < spec["minimum"]:
        return [f"Claude config {path} is below its native minimum"]
    if "exact" in spec and value != spec["exact"]:
        return [f"Claude config {path} must equal the verified native value"]
    return []


def validate_claude_config(
    values: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
    expected_target: str = "INSTALLED_RUNTIME",
    observed_runtime_version: str | None = INSTALLED_RUNTIME_VERSION,
) -> NativeConfigValidation:
    """Validate a small config object against the pinned installed CLI."""

    native_contract = load_native_contract() if contract is None else copy.deepcopy(contract)
    contract_validation = validate_native_contract(
        native_contract,
        expected_target=expected_target,
        observed_runtime_version=observed_runtime_version,
    )
    errors = list(contract_validation.errors)
    if not isinstance(values, dict):
        errors.append("Claude config values must be an object")
        return NativeConfigValidation(
            errors=errors,
            source_revision=contract_validation.source_revision,
            native_contract_revision=contract_validation.native_contract_revision,
            reason_code=contract_validation.reason_code or "INVALID_NATIVE_CONFIG",
            provenance=contract_validation.provenance,
        )
    fields = native_contract.get("fields", {})
    if not isinstance(fields, dict):
        errors.append("Claude native contract fields must be an object")
        fields = {}
    for key, value in values.items():
        spec = fields.get(key)
        if not isinstance(spec, dict):
            errors.append(f"unsupported Claude native config field: {key}")
            continue
        errors.extend(_validate_value(key, value, spec))
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
