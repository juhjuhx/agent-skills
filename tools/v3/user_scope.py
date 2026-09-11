"""Pure USER-scope distribution contracts and preview planning.

Phase 3K deliberately does not install anything.  This module keeps the
user-scope contract separate from the Phase 3J project transaction executor:
it consumes checked-in runtime evidence and a validated routing snapshot,
then returns symbolic, deterministic preview data only.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Mapping

from tools.v3.productization import ROOT, digest_value, snapshot_digest
from tools.v3.routing_catalog import RoutingCatalogSnapshot


USER_SCOPE_CONTRACT_PATH = (
    ROOT / "fixtures" / "v3" / "productization" / "user-scope-contract-v1.json"
)
USER_SCOPE_LIFECYCLE_FIXTURE_PATH = (
    ROOT / "fixtures" / "v3" / "productization" / "user-scope-lifecycle-v1.json"
)
USER_SCOPE_VERSION = "1.0"
USER_SCOPE_APPLY_NOT_AUTHORIZED = "USER_SCOPE_APPLY_NOT_AUTHORIZED"
SUPPORTED_PLATFORMS = frozenset({"linux", "macos", "windows"})
SUPPORTED_STRATEGIES = frozenset(
    {
        "NATIVE_SHARED_DIRECTORY",
        "MANAGED_COPY",
        "DIRECTORY_SYMLINK",
        "FILE_SYMLINK",
        "WINDOWS_JUNCTION",
        "CONFIG_REFERENCE",
        "UNSUPPORTED",
    }
)
COLLISION_STATES = frozenset(
    {"ABSENT", "ASM_MANAGED", "USER_OWNED", "AMBIGUOUS", "UNKNOWN"}
)
UPGRADE_STATES = frozenset(
    {
        "UNCHANGED",
        "CONTENT_UPDATED",
        "ADDED",
        "REMOVED",
        "RENAMED",
        "CONFLICT_USER_MODIFIED",
        "CONFLICT_OWNERSHIP_LOST",
        "RUNTIME_TARGET_CHANGED",
        "STRATEGY_CHANGED",
    }
)
STRATEGY_SUPPORT = frozenset(
    {"SUPPORTED", "SUPPORTED_WITH_PRECONDITION", "UNSUPPORTED", "UNKNOWN"}
)
ROOT_PATTERN = re.compile(r"^\$\{[A-Z][A-Z0-9_]*\}(?:/[^\x00]+)?$")
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
SAFE_RUNTIME_STATUS_FIELDS = (
    "schema_version",
    "runtime_id",
    "runtime_name",
    "install_availability",
    "adapter_support",
    "static_contract",
    "live_execution",
    "projection_modes",
    "selected_only_skill_support",
    "permission_projection_support",
    "model_selection_surface",
    "effort_selection_surface",
    "mcp_support",
    "plugin_support",
    "observed_runtime_version",
    "release_tag",
    "release_commit",
    "runtime_contract_digest",
    "adapter_manifest_path",
    "native_contract_path",
    "evidence_refs",
)


class UserScopeError(ValueError):
    """Raised when a user-scope preview cannot be proven safe."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UserScopeError(
            f"cannot read USER scope contract: {type(exc).__name__}"
        ) from exc
    if not isinstance(value, dict):
        raise UserScopeError("USER scope contract must be a JSON object")
    return value


def _validate_symbolic_root(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not ROOT_PATTERN.fullmatch(value):
        raise UserScopeError(f"{label} must be a symbolic root path")
    path = Path(value[2:]) if value.startswith("${") else Path(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise UserScopeError(f"{label} escapes its symbolic root")
    return value.rstrip("/")


def _validate_digest(value: Any, *, label: str, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise UserScopeError(f"{label} must be a sha256 digest")


def _contract_digest(contract: Mapping[str, Any]) -> str:
    value = copy.deepcopy(dict(contract))
    value["contract_digest"] = ""
    return digest_value(value)


def _validate_contract(contract: Mapping[str, Any]) -> None:
    if contract.get("schema_version") != "3.0":
        raise UserScopeError("unsupported USER scope schema version")
    if contract.get("user_scope_contract_version") != USER_SCOPE_VERSION:
        raise UserScopeError("unsupported USER scope contract version")
    if contract.get("scope") != "USER" or contract.get("apply_allowed") is not False:
        raise UserScopeError("USER scope contract must remain preview-only")
    if contract.get("no_real_home_access") is not True:
        raise UserScopeError("USER scope contract must prohibit real-home access")
    roots = contract.get("symbolic_roots")
    if not isinstance(roots, dict) or not roots:
        raise UserScopeError("USER scope contract has no symbolic roots")
    for name, root in roots.items():
        _validate_symbolic_root(root, label=f"symbolic root {name}")
    targets = contract.get("runtime_targets")
    if not isinstance(targets, list):
        raise UserScopeError("USER scope contract requires runtime targets")
    strategies = contract.get("strategies")
    if not isinstance(strategies, list):
        raise UserScopeError("USER scope contract requires strategy records")
    strategy_ids: set[str] = set()
    for strategy in strategies:
        if (
            not isinstance(strategy, dict)
            or strategy.get("strategy") not in SUPPORTED_STRATEGIES
        ):
            raise UserScopeError("USER scope contract contains an invalid strategy")
        strategy_id = str(strategy["strategy"])
        if strategy_id in strategy_ids:
            raise UserScopeError(f"duplicate USER scope strategy: {strategy_id}")
        strategy_ids.add(strategy_id)
        for field in ("runtime_support", "os_support"):
            support = strategy.get(field)
            if not isinstance(support, dict):
                raise UserScopeError(f"strategy {strategy_id} lacks {field}")
        if not set(support.values()).issubset(
            STRATEGY_SUPPORT | {"OUT_OF_SCOPE", "VERIFIED_FAIL_CLOSED"}
        ):
            raise UserScopeError(f"strategy {strategy_id} has invalid {field}")
    if strategy_ids != set(SUPPORTED_STRATEGIES):
        raise UserScopeError("USER scope contract does not enumerate every strategy")
    target_ids: set[str] = set()
    for target in targets:
        if not isinstance(target, dict) or not isinstance(
            target.get("runtime_id"), str
        ):
            raise UserScopeError(
                "USER scope contract contains an invalid runtime target"
            )
        runtime_id = target["runtime_id"]
        if runtime_id in target_ids:
            raise UserScopeError(f"duplicate USER scope runtime target: {runtime_id}")
        target_ids.add(runtime_id)
        if target.get("apply_allowed") is not False:
            raise UserScopeError(f"USER scope apply is enabled for {runtime_id}")
        if target.get("selected_strategy") not in SUPPORTED_STRATEGIES:
            raise UserScopeError(f"invalid selected strategy for {runtime_id}")
        if target.get("strategy_support") not in STRATEGY_SUPPORT:
            raise UserScopeError(f"invalid strategy support for {runtime_id}")
        if target.get("support_classification") not in {
            "PREVIEW_ONLY",
            "NOT_IMPLEMENTED",
        }:
            raise UserScopeError(f"invalid support classification for {runtime_id}")
        if target.get("config_mutation_required") is not False:
            raise UserScopeError(
                f"USER scope target mutates runtime config: {runtime_id}"
            )
        roots = target.get("native_user_skill_roots")
        if not isinstance(roots, list):
            raise UserScopeError(
                f"runtime target has no native user roots: {runtime_id}"
            )
        for root in roots:
            if not isinstance(root, dict):
                raise UserScopeError(
                    f"runtime target has an invalid native root: {runtime_id}"
                )
            _validate_symbolic_root(root.get("path"), label=f"{runtime_id} native root")
            if root.get("support") not in {
                "NATIVE_VERIFIED",
                "NATIVE_RELEASE_SUPPORTED",
                "UPSTREAM_ONLY",
                "LEGACY",
                "UNVERIFIED",
            }:
                raise UserScopeError(
                    f"runtime target has invalid root support: {runtime_id}"
                )
        project_roots = target.get("native_project_skill_roots")
        if not isinstance(project_roots, list):
            raise UserScopeError(
                f"runtime target has no native project roots: {runtime_id}"
            )
        for project_root in project_roots:
            _validate_symbolic_root(
                project_root, label=f"{runtime_id} native project root"
            )
        destination = target.get("selected_destination")
        if destination is not None:
            _validate_symbolic_root(
                destination, label=f"{runtime_id} selected destination"
            )
        symlinks = target.get("symlink_support")
        if not isinstance(symlinks, dict) or not set(symlinks).issubset(
            {"DIRECTORY_SYMLINK", "FILE_SYMLINK", "WINDOWS_JUNCTION"}
        ):
            raise UserScopeError(
                f"runtime target has invalid symlink support: {runtime_id}"
            )
        if not set(symlinks.values()).issubset(
            {"VERIFIED", "SUPPORTED_WITH_PRECONDITION", "UNSUPPORTED", "UNKNOWN"}
        ):
            raise UserScopeError(
                f"runtime target has invalid symlink status: {runtime_id}"
            )
        if runtime_id == "hermes":
            if target.get("runtime_contract_digest") is not None:
                raise UserScopeError("Hermes has no verified runtime contract digest")
        else:
            _validate_digest(
                target.get("runtime_contract_digest"),
                label=f"{runtime_id} runtime contract digest",
            )
    if set(target_ids) != {"codex", "claude-code", "opencode", "hermes"}:
        raise UserScopeError("USER scope contract must account for all known runtimes")
    if contract.get("contract_digest") != _contract_digest(contract):
        raise UserScopeError("USER scope contract digest is invalid")


def load_user_scope_contract(
    path: str | Path = USER_SCOPE_CONTRACT_PATH,
) -> dict[str, Any]:
    """Load and validate the checked-in symbolic USER scope contract."""

    contract = _read_json(Path(path))
    _validate_contract(contract)
    return copy.deepcopy(contract)


def load_user_lifecycle_fixture(
    path: str | Path = USER_SCOPE_LIFECYCLE_FIXTURE_PATH,
) -> dict[str, Any]:
    """Load lifecycle examples that are explicitly confined to virtual homes."""

    fixture = _read_json(Path(path))
    if fixture.get("schema_version") != "3.0":
        raise UserScopeError("unsupported USER lifecycle schema version")
    if fixture.get("user_scope_lifecycle_version") != USER_SCOPE_VERSION:
        raise UserScopeError("unsupported USER lifecycle fixture version")
    if fixture.get("fixture_kind") != "VIRTUAL_HOME_ONLY":
        raise UserScopeError("USER lifecycle fixture is not virtual-home-only")
    if fixture.get("real_home_access") is not False:
        raise UserScopeError("USER lifecycle fixture permits real-home access")
    snapshots = fixture.get("snapshots")
    if not isinstance(snapshots, dict) or not snapshots:
        raise UserScopeError("USER lifecycle fixture has no snapshots")
    for name, snapshot in snapshots.items():
        if not isinstance(snapshot, dict):
            raise UserScopeError(f"USER lifecycle snapshot is invalid: {name}")
        _validate_digest(snapshot.get("snapshot_digest"), label=f"snapshot {name}")
        if snapshot.get("strategy") not in SUPPORTED_STRATEGIES:
            raise UserScopeError(
                f"USER lifecycle snapshot has invalid strategy: {name}"
            )
    transitions = fixture.get("transitions")
    if not isinstance(transitions, list):
        raise UserScopeError("USER lifecycle fixture has no transitions")
    for transition in transitions:
        if not isinstance(transition, dict):
            raise UserScopeError("USER lifecycle transition is not an object")
        if transition.get("expected") not in UPGRADE_STATES:
            raise UserScopeError("USER lifecycle transition has an invalid outcome")
        for field in ("previous_digest", "current_digest"):
            _validate_digest(
                transition.get(field),
                label=f"transition {field}",
                nullable=True,
            )
    collisions = fixture.get("collision_examples")
    if not isinstance(collisions, list):
        raise UserScopeError("USER lifecycle fixture has no collision examples")
    for collision in collisions:
        if not isinstance(collision, dict):
            raise UserScopeError("USER lifecycle collision is not an object")
        _validate_symbolic_root(collision.get("path"), label="lifecycle collision path")
        classify_user_collision(collision.get("state", "UNKNOWN"))
    migration = fixture.get("migration")
    if (
        not isinstance(migration, dict)
        or migration.get("automatic_project_delete") is not False
    ):
        raise UserScopeError("USER lifecycle migration is not independent")
    for case in fixture.get("symlink_cases", []):
        if not isinstance(case, dict) or case.get("strategy") not in {
            "DIRECTORY_SYMLINK",
            "FILE_SYMLINK",
        }:
            raise UserScopeError("USER lifecycle symlink case is invalid")
    expected = digest_value({**fixture, "fixture_digest": ""})
    if fixture.get("fixture_digest") != expected:
        raise UserScopeError("USER lifecycle fixture digest is invalid")
    return copy.deepcopy(fixture)


def normalize_platform(platform: str) -> str:
    value = str(platform).strip().lower()
    aliases = {"darwin": "macos", "mac": "macos", "win32": "windows"}
    value = aliases.get(value, value)
    if value not in SUPPORTED_PLATFORMS:
        raise UserScopeError(f"unsupported preview platform: {platform}")
    return value


def _target_for(contract: Mapping[str, Any], runtime_id: str) -> dict[str, Any]:
    for target in contract["runtime_targets"]:
        if target["runtime_id"] == runtime_id:
            return copy.deepcopy(target)
    # Preview tooling must fail closed for an unknown runtime without turning
    # that unknown record into an apply-capable target.
    return {
        "runtime_id": runtime_id,
        "observed_runtime_version": None,
        "release_tag": None,
        "release_commit": None,
        "runtime_contract_digest": None,
        "apply_allowed": False,
        "native_user_skill_roots": [],
        "native_project_skill_roots": [],
        "selected_destination": None,
        "selected_strategy": "UNSUPPORTED",
        "strategy_support": "UNSUPPORTED",
        "support_classification": "PREVIEW_ONLY",
        "skill_delivery": "UNSUPPORTED",
        "config_mutation_required": False,
        "symlink_support": {},
        "same_name_precedence": "UNKNOWN",
        "evidence_refs": [],
    }


def _strategy_for(contract: Mapping[str, Any], strategy: str) -> dict[str, Any]:
    for item in contract["strategies"]:
        if item["strategy"] == strategy:
            return copy.deepcopy(item)
    raise UserScopeError(f"strategy is absent from USER scope contract: {strategy}")


def _combine_strategy_support(
    target: Mapping[str, Any], strategy: Mapping[str, Any], platform: str
) -> str:
    runtime_support = target.get("strategy_support", "UNKNOWN")
    matrix_runtime = strategy.get("runtime_support", {}).get(
        target.get("runtime_id"), "UNKNOWN"
    )
    os_support = strategy.get("os_support", {}).get(platform, "UNKNOWN")
    values = {runtime_support, matrix_runtime, os_support}
    if "UNSUPPORTED" in values or "OUT_OF_SCOPE" in values:
        return "UNSUPPORTED"
    if "UNKNOWN" in values:
        return "UNKNOWN"
    if "SUPPORTED_WITH_PRECONDITION" in values:
        return "SUPPORTED_WITH_PRECONDITION"
    return "SUPPORTED"


def _skill_slug(skill_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(skill_id)).strip(".-")
    return slug or "skill"


def _symbolic_skill_path(root: str, skill_id: str) -> str:
    return f"{root}/{_skill_slug(skill_id)}/SKILL.md"


def _source_index_digest(snapshot: RoutingCatalogSnapshot) -> str:
    index = [
        {"skill_id": record["skill_id"], "digest": record["source"]["digest"]}
        for record in sorted(snapshot.records, key=lambda item: item["skill_id"])
    ]
    return digest_value(index)


def _safe_runtime_status(runtime_status: Mapping[str, Any]) -> dict[str, Any]:
    """Keep arbitrary caller metadata from entering a persisted preview."""

    return {
        field: copy.deepcopy(runtime_status[field])
        for field in SAFE_RUNTIME_STATUS_FIELDS
        if field in runtime_status
    }


def _collision_state(value: str | None) -> str:
    return classify_user_collision(value or "UNKNOWN")


def build_user_scope_preview(
    runtime_status: Mapping[str, Any],
    snapshot: RoutingCatalogSnapshot,
    *,
    contract: Mapping[str, Any] | None = None,
    platform: str = "macos",
    strategy: str | None = None,
    collision_states: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build a deterministic, symbolic USER preview without filesystem I/O."""

    loaded_contract = (
        load_user_scope_contract()
        if contract is None
        else copy.deepcopy(dict(contract))
    )
    _validate_contract(loaded_contract)
    platform = normalize_platform(platform)
    runtime_id = str(runtime_status.get("runtime_id", ""))
    target = _target_for(loaded_contract, runtime_id)
    if target.get("observed_runtime_version") is not None:
        observed = runtime_status.get("observed_runtime_version")
        if observed != target["observed_runtime_version"]:
            raise UserScopeError("runtime version does not match USER scope contract")
    target_digest = target.get("runtime_contract_digest")
    if (
        target_digest is not None
        and runtime_status.get("runtime_contract_digest") != target_digest
    ):
        raise UserScopeError(
            "runtime contract digest does not match USER scope contract"
        )
    selected_strategy = strategy or target["selected_strategy"]
    if selected_strategy not in SUPPORTED_STRATEGIES:
        raise UserScopeError(
            f"unsupported USER distribution strategy: {selected_strategy}"
        )
    strategy_record = _strategy_for(loaded_contract, selected_strategy)
    effective_support = _combine_strategy_support(target, strategy_record, platform)
    destination_root = target.get("selected_destination")
    states = dict(collision_states or {})
    planned: list[dict[str, Any]] = []
    if (
        destination_root is not None
        and selected_strategy not in {"UNSUPPORTED", "CONFIG_REFERENCE"}
        and effective_support != "UNSUPPORTED"
    ):
        seen_destinations: set[str] = set()
        for record in sorted(snapshot.records, key=lambda item: item["skill_id"]):
            skill_id = record["skill_id"]
            source = record["source"]
            source_path = Path(str(source.get("path", "")))
            if source_path.is_absolute() or ".." in source_path.parts:
                raise UserScopeError(f"canonical source path is unsafe: {skill_id}")
            destination_path = _symbolic_skill_path(destination_root, skill_id)
            if destination_path in seen_destinations:
                raise UserScopeError(
                    f"skill destination slug collision requires explicit handling: {skill_id}"
                )
            seen_destinations.add(destination_path)
            state = _collision_state(states.get(skill_id))
            planned.append(
                {
                    "skill_id": skill_id,
                    "source_path": source_path.as_posix(),
                    "source_digest": source["digest"],
                    "destination_path": destination_path,
                    "lifecycle": "INSTALL_PERSISTENT",
                    "selected_only": False,
                    "body_materialized": False,
                    "collision_state": state,
                    "ownership": "EXACT_PATH",
                }
            )
    collision_summary = {
        "inspected": bool(collision_states),
        "states": {
            state: sum(1 for item in planned if item["collision_state"] == state)
            for state in sorted(COLLISION_STATES)
            if any(item["collision_state"] == state for item in planned)
        },
        "note": (
            "fixture collision states only; real user home was not inspected"
            if not collision_states
            else "collision states supplied by an isolated fixture"
        ),
    }
    warnings = [
        "USER apply is not authorized in Phase 3K",
        "no strategy fallback is permitted",
        "real user home was not inspected; unlisted collisions remain UNKNOWN",
    ]
    if target.get("support_classification") != "NATIVE_RELEASE_SUPPORTED":
        warnings.append(
            "native user skill destination is not pinned to the installed runtime release"
        )
    if effective_support != "SUPPORTED":
        warnings.append(
            f"selected strategy {selected_strategy} has support status {effective_support} on {platform}"
        )
    if destination_root is not None and not planned:
        warnings.append(
            "no managed path plan emitted because the selected strategy is unsupported"
        )
    if selected_strategy != target["selected_strategy"]:
        warnings.append(
            f"explicit strategy {selected_strategy} differs from contract preference {target['selected_strategy']}"
        )
    if target.get("config_mutation_required"):
        warnings.append("runtime user config mutation is outside this phase")
    if runtime_status.get("live_execution") != "VERIFIED":
        warnings.append(
            f"live execution is {runtime_status.get('live_execution', 'UNKNOWN')}; this preview makes no live-readiness claim"
        )
    source = {
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_digest": snapshot_digest(snapshot),
        "registry_epoch": snapshot.registry_epoch,
        "skill_count": len(snapshot.records),
        "canonical_skill_index_digest": _source_index_digest(snapshot),
        "catalog_body_files_loaded": 0,
        "body_files_materialized": 0,
        "execution_selected_only": True,
    }
    preview: dict[str, Any] = {
        "schema_version": "3.0",
        "user_scope_version": USER_SCOPE_VERSION,
        "preview_digest": "",
        "scope": "USER",
        "platform": platform,
        "apply_allowed": False,
        "no_actual_writes": True,
        "authorization": "PREVIEW_ONLY",
        "runtime_status": _safe_runtime_status(runtime_status),
        "runtime_target": target,
        "distribution_strategy": selected_strategy,
        "strategy_support": effective_support,
        "support_classification": target.get("support_classification", "PREVIEW_ONLY"),
        "user_data_root": loaded_contract["symbolic_roots"]["asm_user_data"],
        "user_manifest_path": f"{loaded_contract['symbolic_roots']['asm_user_data']}/v3/user-installations/manifest.json",
        "source": source,
        "planned_managed_paths": planned,
        "collisions": collision_summary,
        "ownership": {
            "scope": "EXACT_PATHS",
            "parent_directories_owned": False,
            "canonical_source_remains_authoritative": True,
            "modified_managed_outcome": "CONFLICT",
        },
        "lifecycle": {
            "discovery_distribution": "DERIVED_LAZY_NATIVE_ENTRIES",
            "execution_materialization": "SELECTED_ONLY",
            "ephemeral_execution_state_persisted": False,
        },
        "coexistence": {
            "project_and_user_are_independent": True,
            "automatic_project_delete": False,
            "duplicate_precedence": target.get("same_name_precedence", "UNKNOWN"),
        },
        "warnings": sorted(set(warnings)),
        "evidence_refs": sorted(
            set(loaded_contract.get("evidence_refs", []))
            | set(target.get("evidence_refs", []))
        ),
        "user_scope_contract_digest": loaded_contract["contract_digest"],
        "target_contract_digest": target.get("runtime_contract_digest"),
    }
    preview["preview_digest"] = digest_value(preview)
    return preview


def classify_user_collision(state: str) -> str:
    """Normalize an isolated collision state; never adopt unknown content."""

    value = str(state).strip().upper()
    if value not in COLLISION_STATES:
        raise ValueError(f"unknown USER collision state: {state}")
    return value


def classify_user_upgrade(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any] | None,
    *,
    current_state: str = "ASM_MANAGED",
    explicit_rename: bool = False,
) -> str:
    """Classify one bounded lifecycle transition without inferring renames."""

    if previous is None and current is None:
        raise ValueError("upgrade classification needs a previous or current record")
    if previous is None:
        return "ADDED"
    if current is None:
        return "REMOVED"
    state = str(current_state).strip().upper()
    if state == "MODIFIED_MANAGED":
        return "CONFLICT_USER_MODIFIED"
    if state not in COLLISION_STATES and state != "ASM_MANAGED":
        raise ValueError(f"unknown USER lifecycle state: {current_state}")
    if state in {"USER_OWNED", "AMBIGUOUS", "UNKNOWN"}:
        return "CONFLICT_OWNERSHIP_LOST"
    previous_runtime = previous.get("runtime_id")
    current_runtime = current.get("runtime_id")
    if (
        previous_runtime is not None
        and current_runtime is not None
        and previous_runtime != current_runtime
    ):
        return "RUNTIME_TARGET_CHANGED"
    previous_strategy = previous.get("strategy")
    current_strategy = current.get("strategy")
    if (
        previous_strategy is not None
        and current_strategy is not None
        and previous_strategy != current_strategy
    ):
        return "STRATEGY_CHANGED"
    previous_skill = previous.get("skill_id")
    current_skill = current.get("skill_id")
    if previous_skill != current_skill:
        if not explicit_rename:
            raise ValueError("rename requires explicit evidence")
        return "RENAMED"
    if previous.get("source_digest") == current.get("source_digest"):
        return "UNCHANGED"
    return "CONTENT_UPDATED"


def plan_project_user_migration(
    *, project_package_digest: str, user_preview_digest: str
) -> dict[str, Any]:
    """Describe migration as two independent future transactions."""

    _validate_digest(project_package_digest, label="project package digest")
    _validate_digest(user_preview_digest, label="USER preview digest")
    return {
        "operation": "INSTALL_USER_SEPARATELY",
        "project_package_digest": project_package_digest,
        "user_preview_digest": user_preview_digest,
        "project_uninstall": "OPTIONAL_SEPARATE_TRANSACTION",
        "automatic_project_delete": False,
        "shared_transaction": False,
    }


def user_scope_apply_guard(scope: str) -> None:
    """Reject USER mutation before any target or filesystem resolution."""

    if str(scope).strip().upper() == "USER":
        raise UserScopeError(USER_SCOPE_APPLY_NOT_AUTHORIZED)
