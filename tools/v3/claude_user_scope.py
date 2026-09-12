"""Claude Code 2.1.235 USER-scope discovery qualification.

This module is deliberately static and preview-only.  It records the
version-bound evidence needed for a future Claude personal-skill installer,
but it never invokes Claude, inspects a real HOME, or mutates a runtime
directory.
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Mapping

from tools.v3.productization import ROOT, digest_bytes, digest_value, snapshot_digest
from tools.v3.routing_catalog import RoutingCatalogSnapshot
from tools.v3.user_scope import UserScopeError


CLAUDE_RUNTIME_ID = "claude-code"
CLAUDE_RUNTIME_VERSION = "2.1.235"
CLAUDE_RELEASE_TAG = "v2.1.235"
CLAUDE_USER_SCOPE_VERSION = "1.0"
CLAUDE_PERSONAL_SKILL_ROOT = "${HOME}/.claude/skills"
CLAUDE_PROJECT_SKILL_ROOT = "${PROJECT}/.claude/skills"
CLAUDE_SYNCED_SKILL_ROOT = "${HOME}/.claude/skills/synced"
CLAUDE_ASM_USER_DATA_ROOT = "${ASM_USER_DATA}/v3/claude"

CLAUDE_USER_SCOPE_CONTRACT_PATH = (
    ROOT / "fixtures" / "v3" / "productization" / "claude-user-scope-contract-v1.json"
)
CLAUDE_DISTRIBUTION_STRATEGY_PATH = (
    ROOT
    / "fixtures"
    / "v3"
    / "productization"
    / "claude-user-distribution-strategy-v1.json"
)
CLAUDE_USER_LIFECYCLE_PATH = (
    ROOT / "fixtures" / "v3" / "productization" / "claude-user-lifecycle-v1.json"
)

EVIDENCE_CLASSES = frozenset(
    {
        "INSTALLED_RUNTIME_VERIFIED",
        "RELEASE_SUPPORTED",
        "CURRENT_DOC_SUPPORTED",
        "UPSTREAM_ONLY",
        "UNKNOWN",
        "UNSUPPORTED_FOR_APPLY",
        "NOT_SUPPORTED",
    }
)
CLAUDE_STRATEGIES = frozenset(
    {
        "MANAGED_COPY",
        "DIRECTORY_SYMLINK",
        "FILE_SYMLINK",
        "PARENT_DIRECTORY_SYMLINK",
    }
)
CLAUDE_COLLISION_STATES = frozenset(
    {
        "ABSENT",
        "ASM_MANAGED",
        "CLAUDE_SYNCED",
        "USER_OWNED",
        "PROJECT_DUPLICATE",
        "BUNDLED_COLLISION",
        "AMBIGUOUS",
        "UNKNOWN",
    }
)
CLAUDE_UPGRADE_STATES = frozenset(
    {
        "UNCHANGED",
        "ADDED",
        "CONTENT_UPDATED",
        "REMOVED",
        "EXPLICIT_RENAMED",
        "USER_MODIFIED_CONFLICT",
        "OWNERSHIP_LOST",
        "STRATEGY_CHANGED",
    }
)
SUPPORTED_PLATFORMS = frozenset({"linux", "macos", "windows"})
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)
SAFE_STATUS_FIELDS = (
    "schema_version",
    "runtime_id",
    "runtime_name",
    "install_availability",
    "adapter_support",
    "static_contract",
    "live_execution",
    "observed_runtime_version",
    "runtime_contract_digest",
    "adapter_manifest_path",
    "native_contract_path",
    "evidence_refs",
)
SAFE_DISTRIBUTION_SIZE_FIELDS = (
    "measurement_mode",
    "skill_count",
    "total_skill_md_bytes",
    "supporting_file_bytes",
    "managed_copy_bytes",
    "symlink_entry_count",
    "source_body_reads",
)


class ClaudeUserScopeError(UserScopeError):
    """Raised when Claude USER discovery evidence cannot be proven safe."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClaudeUserScopeError(
            f"cannot read Claude USER fixture: {type(exc).__name__}"
        ) from exc
    if not isinstance(value, dict):
        raise ClaudeUserScopeError("Claude USER fixture must be a JSON object")
    return value


def _validate_digest(value: Any, *, label: str, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise ClaudeUserScopeError(f"{label} must be a sha256 digest")


def _validate_symbolic_path(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("${"):
        raise ClaudeUserScopeError(f"{label} must be symbolic")
    if "\\" in value or "\x00" in value or ".." in Path(value[2:]).parts:
        raise ClaudeUserScopeError(f"{label} is unsafe")
    return value.rstrip("/")


def _contract_digest(contract: Mapping[str, Any]) -> str:
    value = copy.deepcopy(dict(contract))
    value["contract_digest"] = ""
    return digest_value(value)


def _fixture_digest(fixture: Mapping[str, Any]) -> str:
    value = copy.deepcopy(dict(fixture))
    value["fixture_digest"] = ""
    return digest_value(value)


def _validate_contract(contract: Mapping[str, Any]) -> None:
    if contract.get("schema_version") != "3.0":
        raise ClaudeUserScopeError("unsupported Claude USER schema version")
    if contract.get("claude_user_scope_contract_version") != CLAUDE_USER_SCOPE_VERSION:
        raise ClaudeUserScopeError("unsupported Claude USER contract version")
    if contract.get("runtime_id") != CLAUDE_RUNTIME_ID:
        raise ClaudeUserScopeError("Claude USER contract has the wrong runtime")
    if contract.get("observed_runtime_version") != CLAUDE_RUNTIME_VERSION:
        raise ClaudeUserScopeError("Claude USER contract is not bound to 2.1.235")
    if contract.get("release_tag") != CLAUDE_RELEASE_TAG:
        raise ClaudeUserScopeError("Claude USER contract has the wrong release tag")
    if contract.get("scope") != "USER" or contract.get("apply_allowed") is not False:
        raise ClaudeUserScopeError("Claude USER contract must remain preview-only")
    if contract.get("no_real_home_access") is not True:
        raise ClaudeUserScopeError("Claude USER contract permits real-home access")
    for name in (
        "personal_skill_root",
        "project_skill_root",
        "synced_skill_root",
        "asm_user_data_root",
    ):
        _validate_symbolic_path(contract.get(name), label=name)
    _validate_digest(contract.get("runtime_contract_digest"), label="runtime contract")
    precedence_cases = contract.get("precedence_cases")
    if not isinstance(precedence_cases, list) or {
        item.get("case") for item in precedence_cases if isinstance(item, dict)
    } != {
        "PERSONAL_ONLY",
        "PROJECT_ONLY",
        "PERSONAL_AND_PROJECT_SAME_NAME",
        "DIFFERENT_NAMES",
    }:
        raise ClaudeUserScopeError("Claude precedence cases are incomplete")
    if any(
        not isinstance(item, dict)
        or item.get("documented_resolution")
        not in {"PERSONAL", "PROJECT", "BOTH_AVAILABLE"}
        for item in precedence_cases
    ):
        raise ClaudeUserScopeError("Claude precedence case is invalid")
    provenance = contract.get("provenance")
    if not isinstance(provenance, dict):
        raise ClaudeUserScopeError("Claude USER contract lacks provenance")
    if provenance.get("observed_version") != CLAUDE_RUNTIME_VERSION:
        raise ClaudeUserScopeError("Claude provenance version mismatch")
    _validate_digest(
        provenance.get("executable_sha256"), label="executable fingerprint"
    )
    claims = contract.get("claims")
    if not isinstance(claims, list):
        raise ClaudeUserScopeError("Claude USER contract lacks claim table")
    claim_ids: set[str] = set()
    required_claims = {
        "personal_skill_root",
        "project_skill_root",
        "precedence",
        "directory_symlink",
        "file_symlink",
        "bundled_collision",
        "synced_collision",
    }
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("claim"), str):
            raise ClaudeUserScopeError("Claude USER claim is invalid")
        claim_id = claim["claim"]
        if claim_id in claim_ids:
            raise ClaudeUserScopeError(f"duplicate Claude USER claim: {claim_id}")
        claim_ids.add(claim_id)
        for field in (
            "current_doc",
            "release_2_1_235",
            "installed_artifact",
            "final_support",
        ):
            if claim.get(field) not in EVIDENCE_CLASSES:
                raise ClaudeUserScopeError(f"invalid {field} for claim: {claim_id}")
    if claim_ids != required_claims:
        raise ClaudeUserScopeError("Claude USER claim table is incomplete")
    collisions = contract.get("collision_policy")
    if (
        not isinstance(collisions, dict)
        or collisions.get("synced") != "PRESERVE_CLAUDE_SYNCED"
    ):
        raise ClaudeUserScopeError("synced skill ownership is not protected")
    if collisions.get("bundled") != "CONFLICT_REQUIRES_CONFIRMATION":
        raise ClaudeUserScopeError("bundled collision policy is not fail-closed")
    if contract.get("preferred_strategy") != "MANAGED_COPY_PREFERRED":
        raise ClaudeUserScopeError("Claude preferred strategy is not explicit")
    if contract.get("contract_digest") != _contract_digest(contract):
        raise ClaudeUserScopeError("Claude USER contract digest is invalid")


def load_claude_user_contract(
    path: str | Path = CLAUDE_USER_SCOPE_CONTRACT_PATH,
) -> dict[str, Any]:
    contract = _read_json(Path(path))
    _validate_contract(contract)
    return copy.deepcopy(contract)


def _validate_strategy_fixture(fixture: Mapping[str, Any]) -> None:
    if (
        fixture.get("schema_version") != "3.0"
        or fixture.get("strategy_version") != CLAUDE_USER_SCOPE_VERSION
    ):
        raise ClaudeUserScopeError("unsupported Claude strategy fixture version")
    if (
        fixture.get("runtime_id") != CLAUDE_RUNTIME_ID
        or fixture.get("runtime_version") != CLAUDE_RUNTIME_VERSION
    ):
        raise ClaudeUserScopeError("Claude strategy fixture runtime mismatch")
    strategies = fixture.get("strategies")
    if (
        not isinstance(strategies, list)
        or {item.get("strategy") for item in strategies if isinstance(item, dict)}
        != CLAUDE_STRATEGIES
    ):
        raise ClaudeUserScopeError("Claude strategy fixture is incomplete")
    for item in strategies:
        if not isinstance(item, dict):
            raise ClaudeUserScopeError("Claude strategy entry is invalid")
        for field in ("final_support", "runtime_discovery_evidence"):
            if item.get(field) not in EVIDENCE_CLASSES:
                raise ClaudeUserScopeError(f"invalid Claude strategy {field}")
        os_support = item.get("os_support")
        if not isinstance(os_support, dict) or set(os_support) != set(
            SUPPORTED_PLATFORMS
        ):
            raise ClaudeUserScopeError("Claude strategy OS matrix is incomplete")
        if item.get("config_mutation_required") is not False:
            raise ClaudeUserScopeError("Claude strategy mutates runtime config")
    if fixture.get("fixture_digest") != _fixture_digest(fixture):
        raise ClaudeUserScopeError("Claude strategy fixture digest is invalid")


def load_claude_distribution_strategy(
    path: str | Path = CLAUDE_DISTRIBUTION_STRATEGY_PATH,
) -> dict[str, Any]:
    fixture = _read_json(Path(path))
    _validate_strategy_fixture(fixture)
    return copy.deepcopy(fixture)


def _validate_lifecycle_fixture(fixture: Mapping[str, Any]) -> None:
    if (
        fixture.get("schema_version") != "3.0"
        or fixture.get("lifecycle_version") != CLAUDE_USER_SCOPE_VERSION
    ):
        raise ClaudeUserScopeError("unsupported Claude lifecycle fixture version")
    if (
        fixture.get("runtime_id") != CLAUDE_RUNTIME_ID
        or fixture.get("runtime_version") != CLAUDE_RUNTIME_VERSION
    ):
        raise ClaudeUserScopeError("Claude lifecycle runtime mismatch")
    if (
        fixture.get("fixture_kind") != "VIRTUAL_HOME_ONLY"
        or fixture.get("real_home_access") is not False
    ):
        raise ClaudeUserScopeError("Claude lifecycle fixture is not virtual-home-only")
    if set(fixture.get("collision_states", [])) != CLAUDE_COLLISION_STATES:
        raise ClaudeUserScopeError("Claude lifecycle collision states are incomplete")
    for transition in fixture.get("transitions", []):
        if (
            not isinstance(transition, dict)
            or transition.get("expected") not in CLAUDE_UPGRADE_STATES
        ):
            raise ClaudeUserScopeError("Claude lifecycle transition is invalid")
    for case in fixture.get("link_cases", []):
        if not isinstance(case, dict) or case.get("strategy") not in CLAUDE_STRATEGIES:
            raise ClaudeUserScopeError("Claude link lifecycle case is invalid")
    if fixture.get("fixture_digest") != _fixture_digest(fixture):
        raise ClaudeUserScopeError("Claude lifecycle fixture digest is invalid")


def load_claude_user_lifecycle(
    path: str | Path = CLAUDE_USER_LIFECYCLE_PATH,
) -> dict[str, Any]:
    fixture = _read_json(Path(path))
    _validate_lifecycle_fixture(fixture)
    return copy.deepcopy(fixture)


def validate_claude_skill_slug(skill_id: str, *, platform: str = "macos") -> str:
    """Map one canonical ID to a safe Claude directory name, fail closed."""

    value = str(skill_id)
    if not value or value != value.strip() or "\x00" in value:
        raise ClaudeUserScopeError("skill slug is empty or contains control data")
    if any(ord(char) < 32 for char in value) or "/" in value or "\\" in value:
        raise ClaudeUserScopeError("skill slug contains an unsafe path segment")
    normalized = unicodedata.normalize("NFC", value)
    chars: list[str] = []
    for char in normalized:
        if char.isalnum() or char in "._-":
            chars.append(char)
        elif char.isspace() or char in ":@":
            chars.append("-")
        else:
            chars.append("-")
    slug = re.sub(r"-+", "-", "".join(chars)).strip(".- ")
    if not slug:
        raise ClaudeUserScopeError("skill slug has no safe destination")
    if platform == "windows":
        base = slug.rstrip(". ").split(".", 1)[0].upper()
        if base in WINDOWS_RESERVED_NAMES or slug.endswith((".", " ")):
            raise ClaudeUserScopeError("skill slug uses a Windows reserved name")
    elif platform not in SUPPORTED_PLATFORMS:
        raise ClaudeUserScopeError(f"unsupported Claude slug platform: {platform}")
    return slug


def validate_claude_skill_slugs(
    skill_ids: Iterable[str], *, platform: str = "macos"
) -> dict[str, str]:
    result: dict[str, str] = {}
    normalized: dict[str, str] = {}
    folded: dict[str, str] = {}
    for skill_id in skill_ids:
        slug = validate_claude_skill_slug(skill_id, platform=platform)
        nfc = unicodedata.normalize("NFC", slug)
        fold = nfc.casefold()
        if nfc in normalized:
            raise ClaudeUserScopeError(
                f"Unicode normalization collision at Claude destination: {skill_id}"
            )
        if fold in folded:
            raise ClaudeUserScopeError(
                f"case-fold collision at Claude destination: {skill_id}"
            )
        normalized[nfc] = str(skill_id)
        folded[fold] = str(skill_id)
        result[str(skill_id)] = slug
    return result


def classify_claude_collision(state: str) -> str:
    value = str(state).strip().upper()
    if value not in CLAUDE_COLLISION_STATES:
        raise ValueError(f"unknown Claude collision state: {state}")
    return value


def classify_claude_upgrade(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any] | None,
    *,
    current_state: str = "ASM_MANAGED",
    explicit_rename: bool = False,
) -> str:
    if previous is None and current is None:
        raise ValueError("upgrade classification needs a previous or current record")
    if previous is None:
        return "ADDED"
    if current is None:
        return "REMOVED"
    state = str(current_state).strip().upper()
    if state == "MODIFIED_MANAGED":
        return "USER_MODIFIED_CONFLICT"
    if state in {"USER_OWNED", "AMBIGUOUS", "UNKNOWN", "OWNERSHIP_LOST"}:
        return "OWNERSHIP_LOST"
    if state not in CLAUDE_COLLISION_STATES and state != "ASM_MANAGED":
        raise ValueError(f"unknown Claude lifecycle state: {current_state}")
    if (
        previous.get("strategy") != current.get("strategy")
        and previous.get("strategy") is not None
        and current.get("strategy") is not None
    ):
        return "STRATEGY_CHANGED"
    if previous.get("skill_id") != current.get("skill_id"):
        if not explicit_rename:
            raise ValueError("explicit rename evidence is required")
        return "EXPLICIT_RENAMED"
    if previous.get("source_digest") == current.get("source_digest"):
        return "UNCHANGED"
    return "CONTENT_UPDATED"


def classify_claude_link_lifecycle(
    strategy: str,
    *,
    target_exists: bool,
    target_digest_matches: bool,
    repository_relocated: bool = False,
) -> str:
    if strategy not in CLAUDE_STRATEGIES:
        raise ValueError(f"unknown Claude link strategy: {strategy}")
    if strategy in {"FILE_SYMLINK", "PARENT_DIRECTORY_SYMLINK"}:
        return "UNSUPPORTED_FOR_APPLY"
    if not target_exists:
        return "BROKEN_TARGET"
    if repository_relocated:
        return "REPOSITORY_RELOCATION_REQUIRES_REVALIDATION"
    if not target_digest_matches:
        return "TARGET_DIGEST_CONFLICT"
    return "BOUND"


def _safe_runtime_status(runtime_status: Mapping[str, Any]) -> dict[str, Any]:
    return {
        field: copy.deepcopy(runtime_status[field])
        for field in SAFE_STATUS_FIELDS
        if field in runtime_status
    }


def _strategy_by_id(fixture: Mapping[str, Any], strategy: str) -> dict[str, Any]:
    for item in fixture["strategies"]:
        if item["strategy"] == strategy:
            return copy.deepcopy(item)
    raise ClaudeUserScopeError(f"unknown Claude distribution strategy: {strategy}")


def _claim_by_id(contract: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["claim"]: copy.deepcopy(item) for item in contract["claims"]}


def _safe_distribution_size(value: Mapping[str, Any]) -> dict[str, Any]:
    """Keep preview size metadata bounded to non-sensitive evidence fields."""

    unexpected = set(value) - set(SAFE_DISTRIBUTION_SIZE_FIELDS)
    if unexpected:
        raise ClaudeUserScopeError(
            "distribution size contains non-evidence fields: "
            + ", ".join(sorted(unexpected))
        )
    result = {
        field: copy.deepcopy(value[field])
        for field in SAFE_DISTRIBUTION_SIZE_FIELDS
        if field in value
    }
    if result.get("measurement_mode") not in {
        "NOT_MEASURED",
        "EXPLICIT_OFFLINE_SOURCE_SIZE",
    }:
        raise ClaudeUserScopeError("distribution size measurement mode is invalid")
    for field in SAFE_DISTRIBUTION_SIZE_FIELDS:
        if field == "measurement_mode":
            continue
        if field not in result:
            continue
        number = result[field]
        if number is not None and (
            isinstance(number, bool) or not isinstance(number, int) or number < 0
        ):
            raise ClaudeUserScopeError(
                f"distribution size field is not a non-negative integer: {field}"
            )
    return result


def measure_claude_distribution_size(
    snapshot: RoutingCatalogSnapshot,
    repository_root: str | Path = ROOT,
    *,
    strategy: str = "MANAGED_COPY",
) -> dict[str, Any]:
    """Measure canonical bytes only when explicitly requested offline.

    This is not called by routing or preview construction.  It is an
    evidence/packaging measurement and never returns source contents.
    """

    if strategy not in CLAUDE_STRATEGIES:
        raise ClaudeUserScopeError(f"unknown Claude distribution strategy: {strategy}")
    root = Path(repository_root).resolve(strict=True)
    total = 0
    for record in sorted(snapshot.records, key=lambda item: item["skill_id"]):
        source_path = Path(str(record["source"]["path"]))
        if source_path.is_absolute() or ".." in source_path.parts:
            raise ClaudeUserScopeError(
                f"unsafe canonical source path: {record['skill_id']}"
            )
        path = root / source_path
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ClaudeUserScopeError(
                f"cannot measure canonical skill: {record['skill_id']}"
            ) from exc
        if digest_bytes(raw) != record["source"]["digest"]:
            raise ClaudeUserScopeError(
                f"canonical skill digest changed: {record['skill_id']}"
            )
        total += len(raw)
    return {
        "measurement_mode": "EXPLICIT_OFFLINE_SOURCE_SIZE",
        "skill_count": len(snapshot.records),
        "total_skill_md_bytes": total,
        "supporting_file_bytes": 0,
        "managed_copy_bytes": total if strategy == "MANAGED_COPY" else 0,
        "symlink_entry_count": len(snapshot.records)
        if strategy == "DIRECTORY_SYMLINK"
        else 0,
        "source_body_reads": len(snapshot.records),
    }


def build_claude_user_preview(
    runtime_status: Mapping[str, Any],
    snapshot: RoutingCatalogSnapshot,
    *,
    contract: Mapping[str, Any] | None = None,
    strategy_fixture: Mapping[str, Any] | None = None,
    platform: str = "macos",
    strategy: str | None = None,
    collision_states: Mapping[str, str] | None = None,
    distribution_size: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a symbolic Claude personal-skill preview with zero runtime I/O."""

    loaded_contract = (
        load_claude_user_contract()
        if contract is None
        else copy.deepcopy(dict(contract))
    )
    _validate_contract(loaded_contract)
    loaded_strategies = (
        load_claude_distribution_strategy()
        if strategy_fixture is None
        else copy.deepcopy(dict(strategy_fixture))
    )
    _validate_strategy_fixture(loaded_strategies)
    if platform not in SUPPORTED_PLATFORMS:
        raise ClaudeUserScopeError(f"unsupported Claude preview platform: {platform}")
    if runtime_status.get("runtime_id") != CLAUDE_RUNTIME_ID:
        raise ClaudeUserScopeError("Claude preview received a different runtime")
    if runtime_status.get("observed_runtime_version") != CLAUDE_RUNTIME_VERSION:
        raise ClaudeUserScopeError("Claude runtime version does not match 2.1.235")
    if (
        runtime_status.get("runtime_contract_digest")
        != loaded_contract["runtime_contract_digest"]
    ):
        raise ClaudeUserScopeError("Claude runtime contract digest does not match")
    selected_strategy = strategy or loaded_contract["preferred_strategy"].replace(
        "_PREFERRED", ""
    )
    if selected_strategy not in CLAUDE_STRATEGIES:
        raise ClaudeUserScopeError(
            f"unsupported Claude preview strategy: {selected_strategy}"
        )
    strategy_record = _strategy_by_id(loaded_strategies, selected_strategy)
    slugs = validate_claude_skill_slugs(
        (record["skill_id"] for record in snapshot.records), platform=platform
    )
    states = {
        skill_id: classify_claude_collision(value)
        for skill_id, value in (collision_states or {}).items()
    }
    planned: list[dict[str, Any]] = []
    if strategy_record["final_support"] not in {
        "UNSUPPORTED_FOR_APPLY",
        "NOT_SUPPORTED",
    }:
        for record in sorted(snapshot.records, key=lambda item: item["skill_id"]):
            skill_id = record["skill_id"]
            destination = f"{loaded_contract['personal_skill_root']}/{slugs[skill_id]}"
            planned.append(
                {
                    "skill_id": skill_id,
                    "source_path": record["source"]["path"],
                    "source_digest": record["source"]["digest"],
                    "destination_path": f"{destination}/SKILL.md",
                    "destination_directory": destination,
                    "strategy": selected_strategy,
                    "lifecycle": "INSTALL_PERSISTENT",
                    "collision_state": states.get(skill_id, "UNKNOWN"),
                    "body_materialized": False,
                    "ownership": "EXACT_PATH",
                }
            )
    state_counts = {
        state: sum(item["collision_state"] == state for item in planned)
        for state in sorted(CLAUDE_COLLISION_STATES)
        if any(item["collision_state"] == state for item in planned)
    }
    warnings = [
        "USER apply is not authorized in Phase 3L",
        "real HOME was not inspected; unlisted collisions remain UNKNOWN",
        "no copy/symlink strategy fallback is permitted",
        "personal/project precedence is current-document supported, not complete installed behavioral proof",
        "CLAUDE_SYNCED is Claude-owned and is never an ASM destination",
        "bundled-name collisions require explicit confirmation; no silent override",
    ]
    if strategy_record["final_support"] != "INSTALLED_RUNTIME_VERIFIED":
        warnings.append(
            f"selected strategy {selected_strategy} is {strategy_record['final_support']}; future apply needs explicit contract review"
        )
    if runtime_status.get("live_execution") != "VERIFIED":
        warnings.append(
            f"live execution is {runtime_status.get('live_execution', 'UNKNOWN')}; user discovery qualification makes no live claim"
        )
    size = (
        _safe_distribution_size(distribution_size)
        if distribution_size is not None
        else {
            "measurement_mode": "NOT_MEASURED",
            "skill_count": len(snapshot.records),
            "total_skill_md_bytes": None,
            "supporting_file_bytes": None,
            "managed_copy_bytes": None,
            "symlink_entry_count": len(snapshot.records)
            if selected_strategy == "DIRECTORY_SYMLINK"
            else 0,
            "source_body_reads": 0,
        }
    )
    claims = _claim_by_id(loaded_contract)
    preview: dict[str, Any] = {
        "schema_version": "3.0",
        "claude_user_scope_version": CLAUDE_USER_SCOPE_VERSION,
        "preview_digest": "",
        "scope": "USER",
        "platform": platform,
        "apply_allowed": False,
        "no_actual_writes": True,
        "authorization": "PREVIEW_ONLY",
        "runtime_status": _safe_runtime_status(runtime_status),
        "runtime_id": CLAUDE_RUNTIME_ID,
        "runtime_version": CLAUDE_RUNTIME_VERSION,
        "distribution_strategy": selected_strategy,
        "strategy_evidence": strategy_record["final_support"],
        "planned_managed_paths": planned,
        "collisions": {
            "inspected": bool(collision_states),
            "states": state_counts,
            "note": "virtual-home fixture states only; real HOME was not inspected",
        },
        "claude": {
            "runtime_id": CLAUDE_RUNTIME_ID,
            "personal_skill_root": loaded_contract["personal_skill_root"],
            "project_skill_root": loaded_contract["project_skill_root"],
            "synced_skill_root": loaded_contract["synced_skill_root"],
            "asm_user_data_root": loaded_contract["asm_user_data_root"],
            "discovery_evidence": claims["personal_skill_root"]["final_support"],
            "precedence": {
                "documented_order": "ENTERPRISE > PERSONAL > PROJECT",
                "final_support": claims["precedence"]["final_support"],
                "warning": "retain a precedence warning until installed behavior is independently exercised",
            },
            "bundled_collision": {
                "policy": loaded_contract["collision_policy"]["bundled"],
                "silent_override": False,
            },
            "synced_collision": {
                "state": "CLAUDE_SYNCED",
                "policy": loaded_contract["collision_policy"]["synced"],
                "asm_owns_synced_root": False,
            },
            "directory_symlink": claims["directory_symlink"]["final_support"],
            "file_symlink": claims["file_symlink"]["final_support"],
            "parent_directory_symlink": "NOT_SUPPORTED",
            "user_apply_allowed": False,
        },
        "source": {
            "snapshot_digest": snapshot_digest(snapshot),
            "skill_count": len(snapshot.records),
            "catalog_body_files_loaded": 0,
            "body_files_materialized": 0,
            "execution_selected_only": True,
        },
        "distribution_size": size,
        "ownership": {
            "scope": "EXACT_PATHS",
            "parent_directories_owned": False,
            "canonical_source_remains_authoritative": True,
            "modified_managed_outcome": "CONFLICT",
            "synced_root_owned": False,
        },
        "lifecycle": {
            "discovery_distribution": "FULL_DERIVED_LAZY_CATALOG",
            "execution_materialization": "SELECTED_ONLY",
            "repo_relocation": "STABLE_ASM_USER_DATA_PREFERRED",
            "manual_modification": "CONFLICT",
        },
        "coexistence": {
            "project_and_user_are_independent": True,
            "automatic_project_delete": False,
            "same_name_warning": True,
            "precedence": "CURRENT_DOC_SUPPORTED_NOT_INSTALLED_BEHAVIOR_VERIFIED",
        },
        "warnings": sorted(set(warnings)),
        "evidence_refs": sorted(
            set(loaded_contract.get("evidence_refs", []))
            | set(loaded_strategies.get("evidence_refs", []))
        ),
        "contract_digest": loaded_contract["contract_digest"],
        "runtime_contract_digest": loaded_contract["runtime_contract_digest"],
    }
    preview["preview_digest"] = digest_value(preview)
    return preview
