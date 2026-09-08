"""Narrow, provenance-bound validation for Codex config values emitted by v3.

The checked-in contract is deliberately small and immutable-by-convention. It
contains the fields emitted by the Codex projection, plus enough provenance to
distinguish a verified installed release from an upstream source preview.
Runtime validation never fetches Codex or asks the live CLI for a schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = ROOT / "fixtures" / "v3" / "codex" / "codex-native-config-contract.json"
SOURCE_SNAPSHOT_CONTRACT_PATH = (
    ROOT / "fixtures" / "v3" / "codex" / "codex-native-config-contract-source-snapshot.json"
)

CODEX_RUNTIME_ID = "codex"
INSTALLED_RUNTIME_VERSION = "0.153.4"
INSTALLED_RELEASE_TAG = "rust-v0.153.4"
INSTALLED_RELEASE_COMMIT = "3d2ee51ca2d5db578f328aa75e20aa22c0197c9a"
INSTALLED_NATIVE_CONTRACT_REVISION = (
    "codex-rs/core/config.schema.json@" + INSTALLED_RELEASE_COMMIT
)
INSTALLED_CONTRACT_DIGEST = (
    "sha256:692da7699367f6f4fbbd46c0021278c1311440bcebf0bcb9b836690c05e56196"
)

SOURCE_SNAPSHOT_COMMIT = "45305dd229c01e6cb6e122f6559e4f9b805bae6"
SOURCE_SNAPSHOT_NATIVE_CONTRACT_REVISION = (
    "codex-rs/core/config.schema.json@" + SOURCE_SNAPSHOT_COMMIT
)
SOURCE_SNAPSHOT_CONTRACT_DIGEST = (
    "sha256:2e1fcf1cbb20f255c3baca2e174b4a3c954cef577a130587b8935e2d12c8ade6"
)

# Keep the Phase 2 constant names as compatibility aliases for the executable
# default. The former 45305 preview has explicit SOURCE_SNAPSHOT_* names.
PINNED_CODEX_SOURCE_REVISION = INSTALLED_RELEASE_COMMIT
PINNED_NATIVE_CONTRACT_REVISION = INSTALLED_NATIVE_CONTRACT_REVISION

CONTRACT_TARGETS = frozenset(
    {"INSTALLED_RUNTIME", "SOURCE_SNAPSHOT", "DOCUMENTATION_SNAPSHOT"}
)
SUPPORT_LEVELS = frozenset({"NATIVE", "EMULATED", "HOST_MANAGED", "UNSUPPORTED"})
AVAILABILITY_LEVELS = frozenset(
    {"INSTALLED", "RELEASE_SUPPORTED", "UPSTREAM_ONLY", "UNKNOWN"}
)

KNOWN_CODEX_RELEASES: dict[str, dict[str, str]] = {
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
    "docs_snapshot_date",
    "contract_digest",
    "verification_method",
    "support",
    "availability",
    "codex_source_revision",
    "native_contract_revision",
)


@dataclass(frozen=True)
class NativeConfigValidation:
    """Validation result with the revisions and provenance used for the decision."""

    errors: list[str] = field(default_factory=list)
    source_revision: str | None = None
    native_contract_revision: str | None = None
    reason_code: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return not self.errors


class NativeContractError(ValueError):
    """A projection failure with a machine-readable contract reason."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def load_native_contract(path: str | Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    """Load a checked-in narrow contract; never retrieve it at runtime."""

    with Path(path).open(encoding="utf-8") as handle:
        contract = json.load(handle)
    if not isinstance(contract, dict):
        raise ValueError("Codex native contract must be a JSON object")
    return contract


def load_source_snapshot_contract() -> dict[str, Any]:
    """Load the retained upstream preview contract for explicit comparison."""

    return load_native_contract(SOURCE_SNAPSHOT_CONTRACT_PATH)


def validate_codex_config(
    values: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
    expected_target: str = "INSTALLED_RUNTIME",
    observed_runtime_version: str | None = INSTALLED_RUNTIME_VERSION,
) -> NativeConfigValidation:
    """Validate values against a checked-in, provenance-bound contract.

    ``INSTALLED_RUNTIME`` is the executable default. A source snapshot can be
    validated only when the caller explicitly requests that target; it is not
    evidence for the installed runtime.
    """

    native_contract = load_native_contract() if contract is None else contract
    if not isinstance(native_contract, dict):
        return NativeConfigValidation(
            ["Codex native contract must be an object"],
            reason_code="RUNTIME_CONTRACT_UNVERIFIED",
        )
    errors: list[str] = []
    source_revision = native_contract.get("codex_source_revision")
    native_contract_revision = native_contract.get("native_contract_revision")
    provenance = _projection_provenance(native_contract)
    provenance_errors, reason_code = _validate_contract_provenance(
        native_contract,
        expected_target=expected_target,
        observed_runtime_version=observed_runtime_version,
    )
    errors.extend(provenance_errors)
    fields = native_contract.get("fields")
    if not isinstance(fields, dict):
        errors.append("Codex native contract fields must be an object")
        fields = {}
    if not isinstance(values, dict):
        errors.append("Codex config values must be an object")
        return NativeConfigValidation(
            errors,
            source_revision,
            native_contract_revision,
            reason_code,
            provenance,
        )

    for key, value in values.items():
        spec = fields.get(key)
        if not isinstance(spec, dict):
            errors.append(f"unsupported Codex config field: {key}")
            continue
        errors.extend(_validate_value(key, value, spec))
    return NativeConfigValidation(
        errors,
        source_revision,
        native_contract_revision,
        reason_code,
        provenance,
    )


def _projection_provenance(contract: dict[str, Any]) -> dict[str, Any]:
    """Return only non-secret contract metadata for projection evidence."""

    return {field_name: contract.get(field_name) for field_name in PROVENANCE_FIELDS}


def _validate_contract_provenance(
    contract: dict[str, Any],
    *,
    expected_target: str,
    observed_runtime_version: str | None,
) -> tuple[list[str], str | None]:
    """Validate target identity without doing network or runtime discovery."""

    errors: list[str] = []
    reason_code: str | None = None

    def unverified(message: str) -> None:
        nonlocal reason_code
        errors.append(message)
        reason_code = "RUNTIME_CONTRACT_UNVERIFIED"

    if expected_target not in CONTRACT_TARGETS:
        unverified(f"unsupported expected Codex contract target: {expected_target}")
        return errors, reason_code

    target = contract.get("contract_target")
    if target not in CONTRACT_TARGETS:
        unverified(f"Codex contract has unsupported contract_target: {target}")
    elif target != expected_target:
        unverified(
            "Codex contract target mismatch: "
            f"expected {expected_target}, got {target}"
        )

    runtime_id = contract.get("runtime_id")
    if runtime_id != CODEX_RUNTIME_ID:
        unverified(f"Codex contract runtime_id must be {CODEX_RUNTIME_ID!r}, got {runtime_id!r}")

    support = contract.get("support")
    if support not in SUPPORT_LEVELS:
        unverified(f"Codex contract has unsupported support level: {support}")
    availability = contract.get("availability")
    if availability not in AVAILABILITY_LEVELS:
        unverified(f"Codex contract has unsupported availability: {availability}")

    if expected_target == "INSTALLED_RUNTIME":
        expected = KNOWN_CODEX_RELEASES.get(observed_runtime_version or "")
        if expected is None:
            unverified(
                "no verified Codex release mapping for observed runtime "
                f"{observed_runtime_version!r}"
            )
            return errors, reason_code

        expected_values = {
            "observed_runtime_version": observed_runtime_version,
            "release_tag": expected["release_tag"],
            "release_commit": expected["release_commit"],
            "contract_source_commit": expected["contract_source_commit"],
            "contract_digest": expected["contract_digest"],
            "codex_source_revision": expected["release_commit"],
            "native_contract_revision": expected["native_contract_revision"],
            "availability": "INSTALLED",
            "support": "NATIVE",
        }
        for field_name, expected_value in expected_values.items():
            actual = contract.get(field_name)
            if actual != expected_value:
                unverified(
                    "Codex installed-runtime contract revision mismatch for "
                    f"{field_name}: expected {expected_value!r}, got {actual!r}"
                )
    elif expected_target == "SOURCE_SNAPSHOT":
        expected_values = {
            "codex_source_revision": SOURCE_SNAPSHOT_COMMIT,
            "contract_source_commit": SOURCE_SNAPSHOT_COMMIT,
            "native_contract_revision": SOURCE_SNAPSHOT_NATIVE_CONTRACT_REVISION,
            "contract_digest": SOURCE_SNAPSHOT_CONTRACT_DIGEST,
            "availability": "UPSTREAM_ONLY",
            "support": "NATIVE",
        }
        for field_name, expected_value in expected_values.items():
            actual = contract.get(field_name)
            if actual != expected_value:
                unverified(
                    "Codex source-snapshot contract revision mismatch for "
                    f"{field_name}: expected {expected_value!r}, got {actual!r}"
                )
    else:
        unverified(
            "documentation snapshots are evidence only and cannot validate an "
            "executable Codex config projection"
        )

    return errors, reason_code


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
