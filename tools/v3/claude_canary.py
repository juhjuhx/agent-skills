"""Read-only Phase 3O Claude real-home canary preparation.

This module may inspect a supplied or current HOME only for bounded
filesystem metadata.  It never applies, creates, updates, deletes, uninstalls,
reverts, recovers, or invokes a runtime.  The package produced here is an
in-memory, non-authorizing preview object; real-home mutation is deliberately
not implemented in this phase.
"""

from __future__ import annotations

import copy
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from tools.v3.claude_user_scope import (
    CLAUDE_ASM_USER_DATA_ROOT,
    CLAUDE_PERSONAL_SKILL_ROOT,
    CLAUDE_RUNTIME_ID,
    CLAUDE_RUNTIME_VERSION,
    CLAUDE_SYNCED_SKILL_ROOT,
    ClaudeUserScopeError,
    load_claude_distribution_strategy,
    load_claude_user_contract,
    validate_claude_skill_slug,
)
from tools.v3.contract_validation import validate_instance
from tools.v3.productization import (
    ROOT,
    digest_bytes,
    digest_value,
    load_runtime_inventory,
)
from tools.v3.routing_catalog import RoutingCatalogSnapshot


CANARY_VERSION = "1.0"
CANARY_MAX_SKILLS = 3
CANARY_PREFERRED_SKILLS = ("module-map",)
CANARY_STATUS_READY = "CLAUDE_REAL_HOME_CANARY_READY_FOR_USER_AUTH"
CANARY_STATUS_BLOCKED = "CANARY_PREPARATION_BLOCKED"
REAL_HOME_APPLY_AUTHORIZED = False
SAFE_COLLISION_STATES = frozenset({"ABSENT", "ASM_MANAGED"})
COLLISION_STATES = frozenset(
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


class CanaryPreparationError(ValueError):
    """Raised when a canary cannot be prepared without guessing."""


def _redacted_identity(path: Path, *, label: str) -> str:
    """Return a path-free filesystem identity digest."""

    try:
        stat = path.stat()
    except OSError as exc:
        raise CanaryPreparationError(f"cannot inspect {label}: {type(exc).__name__}") from exc
    return digest_value(
        {
            "device": int(stat.st_dev),
            "inode": int(stat.st_ino),
            "is_directory": bool(path.is_dir()),
            "label": label,
        }
    )


def _safe_read_home(home_root: str | Path | None) -> Path:
    """Resolve an inventory root without expanding a user-provided path."""

    root = Path.home() if home_root is None else Path(home_root)
    if not root.is_absolute():
        raise CanaryPreparationError("home_root must be an absolute path")
    if root.is_symlink() or not root.exists() or not root.is_dir():
        raise CanaryPreparationError("home_root must be an existing non-symlink directory")
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise CanaryPreparationError(f"cannot resolve home_root: {type(exc).__name__}") from exc
    if resolved == Path(resolved.anchor):
        raise CanaryPreparationError("home_root must not be a filesystem root")
    return resolved


def _safe_project(project_root: str | Path | None) -> Path | None:
    if project_root is None:
        return None
    root = Path(project_root)
    if not root.is_absolute() or root.is_symlink() or not root.exists() or not root.is_dir():
        raise CanaryPreparationError("project_root must be an existing absolute directory")
    try:
        return root.resolve(strict=True)
    except OSError as exc:
        raise CanaryPreparationError(f"cannot resolve project_root: {type(exc).__name__}") from exc


def _path_state(path: Path, *, absent: str = "ABSENT") -> str:
    """Classify one exact path without following a destination symlink."""

    try:
        os.lstat(path)
    except FileNotFoundError:
        return absent
    except OSError:
        return "UNKNOWN"
    if path.is_symlink():
        return "AMBIGUOUS"
    if path.is_dir() or path.is_file():
        return "USER_OWNED"
    return "AMBIGUOUS"


def _worst_collision(states: Iterable[str]) -> str:
    priority = {
        "UNKNOWN": 90,
        "AMBIGUOUS": 80,
        "CLAUDE_SYNCED": 70,
        "USER_OWNED": 60,
        "BUNDLED_COLLISION": 50,
        "PROJECT_DUPLICATE": 40,
        "ASM_MANAGED": 10,
        "ABSENT": 0,
    }
    values = [str(state).upper() for state in states]
    invalid = [state for state in values if state not in COLLISION_STATES]
    if invalid:
        raise CanaryPreparationError("invalid collision state: " + ", ".join(invalid))
    return max(values, key=lambda state: priority[state])


def _access_class(root: Path) -> dict[str, Any]:
    try:
        stat = root.stat()
        owner = "PROCESS_OWNER" if hasattr(os, "getuid") and stat.st_uid == os.getuid() else "OTHER_OR_UNKNOWN"
        readable = os.access(root, os.R_OK)
        writable = os.access(root, os.W_OK)
        return {
            "owner_class": owner,
            "readable": bool(readable),
            "writable": bool(writable),
            "mode_class": oct(stat.st_mode & 0o777),
        }
    except OSError as exc:
        return {
            "owner_class": "UNKNOWN",
            "readable": False,
            "writable": False,
            "mode_class": None,
            "error_class": type(exc).__name__,
        }


def inventory_claude_personal_scope(
    *,
    home_root: str | Path | None = None,
    project_root: str | Path | None = ROOT,
    skill_slugs: Iterable[str] = (),
    bundled_skill_slugs: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Inspect only exact candidate paths and direct-root metadata.

    ``bundled_skill_slugs`` is an explicit evidence input for fixture tests.
    Omitting it intentionally keeps bundled collision status UNKNOWN; the
    current checked-in Claude evidence does not contain a version-bound
    bundled-name inventory.
    """

    home = _safe_read_home(home_root)
    project = _safe_project(project_root)
    slugs = tuple(dict.fromkeys(str(slug) for slug in skill_slugs))
    try:
        safe_slugs = tuple(validate_claude_skill_slug(slug) for slug in slugs)
    except ClaudeUserScopeError as exc:
        raise CanaryPreparationError(str(exc)) from exc
    if len(safe_slugs) != len(slugs):
        raise CanaryPreparationError("candidate skill slugs are not unique")
    bundled = None if bundled_skill_slugs is None else {
        validate_claude_skill_slug(str(slug)) for slug in bundled_skill_slugs
    }

    personal = home / ".claude" / "skills"
    synced_root = home / ".claude" / "skills" / "synced"
    project_skills = project / ".claude" / "skills" if project is not None else None
    if personal.is_symlink():
        personal_root_state = "AMBIGUOUS"
        child_count: int | None = None
    elif personal.exists() and personal.is_dir():
        personal_root_state = "DIRECTORY"
        try:
            child_count = sum(1 for _ in personal.iterdir())
        except OSError:
            child_count = None
    elif personal.exists():
        personal_root_state = "AMBIGUOUS"
        child_count = None
    else:
        personal_root_state = "ABSENT"
        child_count = 0

    candidates: dict[str, dict[str, str]] = {}
    for slug in safe_slugs:
        personal_state = (
            "UNKNOWN"
            if personal_root_state == "AMBIGUOUS"
            else _path_state(personal / slug)
        )
        synced_state = (
            "UNKNOWN"
            if personal_root_state == "AMBIGUOUS" or synced_root.is_symlink()
            else _path_state(synced_root / slug)
        )
        project_state = (
            "UNKNOWN"
            if project_skills is None
            else _path_state(project_skills / slug)
        )
        bundled_state = (
            "UNKNOWN"
            if bundled is None
            else "BUNDLED_COLLISION" if slug in bundled else "ABSENT"
        )
        overall = _worst_collision(
            (personal_state, synced_state, project_state, bundled_state)
        )
        candidates[slug] = {
            "personal": personal_state,
            "synced": synced_state,
            "project": project_state,
            "bundled": bundled_state,
            "overall": overall,
        }

    return {
        "schema_version": "3.0",
        "inventory_version": CANARY_VERSION,
        "symbolic_home_root": "${HOME}",
        "symbolic_personal_root": CLAUDE_PERSONAL_SKILL_ROOT,
        "symbolic_synced_root": CLAUDE_SYNCED_SKILL_ROOT,
        "symbolic_project_root": "${PROJECT}/.claude/skills",
        "home_root_identity": _redacted_identity(home, label="HOME"),
        "personal_root_state": personal_root_state,
        "personal_root_identity": (
            _redacted_identity(personal, label="Claude personal skill root")
            if personal.exists() and not personal.is_symlink() and personal.is_dir()
            else None
        ),
        "personal_child_count": child_count,
        "personal_child_names_persisted": False,
        "access": _access_class(personal if personal.exists() else home),
        "bundled_evidence": (
            "EXPLICIT_FIXTURE_EVIDENCE" if bundled is not None else "NOT_AVAILABLE"
        ),
        "candidates": candidates,
        "read_only": True,
        "raw_skill_bodies_read": 0,
        "private_paths_persisted": False,
    }


def _record_map(snapshot: RoutingCatalogSnapshot) -> dict[str, dict[str, Any]]:
    return {str(record["skill_id"]): record for record in snapshot.records}


def _source_path(record: Mapping[str, Any]) -> Path:
    raw = str(record.get("source", {}).get("path", ""))
    path = Path(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "\\" in raw:
        raise CanaryPreparationError("canonical source path is unsafe")
    return path


def _selected_source_summary(record: Mapping[str, Any], *, platform: str) -> dict[str, Any]:
    skill_id = str(record["skill_id"])
    try:
        slug = validate_claude_skill_slug(skill_id, platform=platform)
    except ClaudeUserScopeError as exc:
        raise CanaryPreparationError(str(exc)) from exc
    source_path = _source_path(record)
    candidate = (ROOT / source_path).resolve(strict=False)
    try:
        candidate.relative_to(ROOT.resolve(strict=True))
        raw = candidate.read_bytes()
    except (OSError, ValueError) as exc:
        raise CanaryPreparationError(f"cannot read selected canonical skill: {skill_id}") from exc
    expected = str(record.get("source", {}).get("digest", ""))
    if digest_bytes(raw) != expected:
        raise CanaryPreparationError(f"canonical skill digest changed: {skill_id}")
    try:
        supporting_count = sum(
            1
            for item in (ROOT / source_path.parent).iterdir()
            if item.name != source_path.name and item.is_file()
        )
    except OSError as exc:
        raise CanaryPreparationError(
            f"cannot inspect selected skill support files: {skill_id}"
        ) from exc
    return {
        "skill_id": skill_id,
        "slug": slug,
        "roles": sorted(record.get("roles", [])) if isinstance(record.get("roles"), list) else [],
        "domains": sorted(record.get("domains", [])) if isinstance(record.get("domains"), list) else [],
        "description_summary": str(record.get("description", ""))[:240],
        "source_path": source_path.as_posix(),
        "source_digest": expected,
        "size_bytes": len(raw),
        "supporting_file_count": supporting_count,
        "supporting_file_bytes": None,
        "runtime_compatibility": "STATIC_CLAUDE_SKILL_DISCOVERY",
        "why_selected": "首個 canary 採用低風險、唯讀、零工具、單一 SKILL.md 的架構導覽技能。",
        "source_body_reads": 1,
    }


def select_canary_skills(
    snapshot: RoutingCatalogSnapshot,
    inventory: Mapping[str, Any],
    *,
    candidate_ids: Iterable[str] | None = None,
    platform: str = "macos",
    max_skills: int = CANARY_MAX_SKILLS,
) -> list[dict[str, Any]]:
    """Select and inspect at most three deterministic, bounded candidates."""

    if max_skills < 1 or max_skills > CANARY_MAX_SKILLS:
        raise CanaryPreparationError("canary may contain at most three skills")
    selected_ids = tuple(
        dict.fromkeys(
            str(item)
            for item in (
                candidate_ids if candidate_ids is not None else CANARY_PREFERRED_SKILLS
            )
        )
    )
    if not selected_ids:
        raise CanaryPreparationError("canary requires at least one selected skill")
    if len(selected_ids) > max_skills:
        raise CanaryPreparationError("canary may contain at most three skills")
    records = _record_map(snapshot)
    candidates = inventory.get("candidates", {})
    result: list[dict[str, Any]] = []
    for skill_id in selected_ids:
        if skill_id not in records:
            raise CanaryPreparationError(f"canary skill is absent from snapshot: {skill_id}")
        state = candidates.get(skill_id)
        if not isinstance(state, Mapping):
            raise CanaryPreparationError(f"canary collision evidence is absent: {skill_id}")
        detail = _selected_source_summary(records[skill_id], platform=platform)
        detail["collision"] = copy.deepcopy(dict(state))
        detail["eligible_for_canary"] = state.get("overall") in SAFE_COLLISION_STATES
        result.append(detail)
    return result


def _target_identity(home: Path) -> str:
    personal = home / ".claude" / "skills"
    personal_identity = (
        _redacted_identity(personal, label="Claude personal skill root")
        if personal.exists() and not personal.is_symlink() and personal.is_dir()
        else digest_value(
            {
                "symbolic_path": CLAUDE_PERSONAL_SKILL_ROOT,
                "state": "ABSENT" if not personal.exists() else "AMBIGUOUS",
            }
        )
    )
    return digest_value(
        {
            "scope": "USER",
            "home_root_identity": _redacted_identity(home, label="HOME"),
            "personal_root_identity": personal_identity,
            "asm_user_data_root": CLAUDE_ASM_USER_DATA_ROOT,
        }
    )


def _confirmation_digest(
    *, package_digest: str, target_root_identity: str, managed_path_count: int
) -> str:
    return digest_value(
        {
            "schema_version": "3.0",
            "confirmation_version": "1.0",
            "package_digest": package_digest,
            "runtime_id": CLAUDE_RUNTIME_ID,
            "scope": "USER",
            "strategy": "MANAGED_COPY",
            "target_root_identity": target_root_identity,
            "managed_path_count": managed_path_count,
        }
    )


def _build_non_authorizing_package(
    snapshot: RoutingCatalogSnapshot,
    runtime_status: Mapping[str, Any],
    *,
    home: Path,
    selected: list[dict[str, Any]],
    platform: str,
) -> dict[str, Any]:
    """Reuse the generic USER package builder, then bind only redacted preview state."""

    # The generic builder intentionally accepts only virtual roots.  Build an
    # exact selected-only package in disposable roots, then replace the root
    # identity fields with path-free real-target identity for the preview.
    from tools.v3.installer import (
        _finalize_user_package,
        _validate_user_package,
        build_claude_user_target,
        build_user_install_package,
    )

    selected_ids = {item["skill_id"] for item in selected}
    collision_states = {
        item["skill_id"]: item["collision"]["overall"] for item in selected
    }
    with tempfile.TemporaryDirectory(prefix="asm-canary-package-") as directory:
        scratch = Path(directory)
        scratch_home = scratch / "home"
        scratch_asm = scratch / "asm"
        scratch_home.mkdir()
        scratch_asm.mkdir()
        target = build_claude_user_target(dict(runtime_status))
        package = build_user_install_package(
            snapshot,
            dict(runtime_status),
            home_root=scratch_home,
            asm_user_data_root=scratch_asm,
            repository_root=ROOT,
            target=target,
            platform=platform,
            collision_states=collision_states,
            skill_ids=selected_ids,
            prune_missing=False,
        )

    identity = _target_identity(home)
    package["scope_root_reference"] = digest_value(
        {
            "scope": "USER",
            "home_root_identity": _redacted_identity(home, label="HOME"),
            "personal_skill_root": CLAUDE_PERSONAL_SKILL_ROOT,
            "asm_user_data_root": CLAUDE_ASM_USER_DATA_ROOT,
        }
    )
    package["scope_root_digest"] = identity
    package["target_root_identity"] = identity
    package["source_store_root_reference"] = digest_value(
        {
            "root_class": "ASM_USER_DATA",
            "symbolic_root": CLAUDE_ASM_USER_DATA_ROOT,
            "resolution": "SYMBOLIC_ONLY",
        }
    )
    package["installable"] = False
    package["apply_allowed"] = False
    package["warnings"] = sorted(
        set(
            package.get("warnings", [])
            + [
                "Phase 3O preview only: no real-home mutation is authorized",
                "real ASM user-data root is symbolic only; no destination is resolved",
                "package is non-authorizing and is not written to disk",
            ]
        )
    )
    package = _finalize_user_package(package)
    _validate_user_package(package)
    package_digest = package["package_digest"]
    confirmation_digest = _confirmation_digest(
        package_digest=package_digest,
        target_root_identity=identity,
        managed_path_count=len(package.get("artifacts", [])),
    )
    package["confirmation_digest"] = None
    return {
        "package": package,
        "package_digest": package_digest,
        "confirmation_digest": confirmation_digest,
    }


def _symbolic_artifact_path(root_class: str, path: str) -> str:
    if root_class == "CLAUDE_PERSONAL":
        return f"{CLAUDE_PERSONAL_SKILL_ROOT}/{Path(path).relative_to('.claude/skills').as_posix()}"
    if root_class == "ASM_USER_DATA":
        return f"{CLAUDE_ASM_USER_DATA_ROOT}/skills/{Path(path).relative_to('v3/claude/skills').as_posix()}"
    raise CanaryPreparationError("unknown canary artifact root")


def _package_preview(package: Mapping[str, Any], *, selected: list[dict[str, Any]]) -> dict[str, Any]:
    artifacts = package.get("artifacts", [])
    files = [
        {
            "skill_id": item["skill_id"],
            "root": item["destination_root"],
            "path": _symbolic_artifact_path(
                item["destination_root"], item["destination_path"]
            ),
            "action": item["action"],
            "content_digest": item["content_digest"],
            "source_digest": item["source_digest"],
        }
        for item in artifacts
    ]
    body_bytes = sum(int(item["size_bytes"]) for item in selected)
    return {
        "schema_version": "3.0",
        "package_kind": package.get("package_kind"),
        "runtime_id": package.get("runtime_id"),
        "runtime_version": package.get("runtime_version"),
        "scope": package.get("scope"),
        "distribution_strategy": package.get("distribution_strategy"),
        "snapshot_digest": package.get("snapshot_digest"),
        "runtime_contract_digest": package.get("runtime_contract_digest"),
        "user_scope_contract_digest": package.get("user_scope_contract_digest"),
        "source_skill_ids": package.get("source_skill_ids", []),
        "artifact_count": len(artifacts),
        "file_count": len(files),
        "total_skill_md_bytes": body_bytes,
        "managed_copy_bytes": body_bytes,
        "files": files,
        "apply_allowed": False,
        "installable": False,
        "package_digest": package.get("package_digest"),
        "confirmation_digest": None,
        "sensitive_data_serialized": False,
    }


def build_canary_preview(
    snapshot: RoutingCatalogSnapshot,
    runtime_status: Mapping[str, Any],
    *,
    home_root: str | Path | None = None,
    project_root: str | Path | None = ROOT,
    candidate_ids: Iterable[str] | None = None,
    bundled_skill_slugs: Iterable[str] | None = None,
    platform: str = "macos",
) -> dict[str, Any]:
    """Build the exact but non-authorizing Phase 3O preview."""

    contract = load_claude_user_contract()
    load_claude_distribution_strategy()
    status_errors = validate_instance(
        "RuntimeProductStatus", dict(runtime_status)
    ).errors
    if status_errors:
        raise CanaryPreparationError(
            "invalid Claude runtime status: " + "; ".join(status_errors)
        )
    if runtime_status.get("runtime_id") != CLAUDE_RUNTIME_ID:
        raise CanaryPreparationError("runtime status is not Claude Code")
    if runtime_status.get("observed_runtime_version") != CLAUDE_RUNTIME_VERSION:
        raise CanaryPreparationError("Claude runtime is not qualified at 2.1.235")
    if runtime_status.get("runtime_contract_digest") != contract.get(
        "runtime_contract_digest"
    ):
        raise CanaryPreparationError("Claude runtime contract digest does not match")
    if platform not in {"linux", "macos", "windows"}:
        raise CanaryPreparationError("unsupported canary platform")
    home = _safe_read_home(home_root)
    requested_ids = (
        tuple(dict.fromkeys(str(item) for item in candidate_ids))
        if candidate_ids is not None
        else None
    )
    inventory = inventory_claude_personal_scope(
        home_root=home,
        project_root=project_root,
        skill_slugs=requested_ids or CANARY_PREFERRED_SKILLS,
        bundled_skill_slugs=bundled_skill_slugs,
    )
    selected = select_canary_skills(
        snapshot,
        inventory,
        candidate_ids=requested_ids,
        platform=platform,
    )
    package_data = _build_non_authorizing_package(
        snapshot,
        runtime_status,
        home=home,
        selected=selected,
        platform=platform,
    )
    package = package_data["package"]
    states = [item["collision"]["overall"] for item in selected]
    collision_report = {
        state.lower(): states.count(state) for state in sorted(COLLISION_STATES)
    }
    collision_report["collision_count"] = sum(
        count for state, count in collision_report.items()
        if state not in {"absent", "asm_managed", "collision_count"}
    )
    collision_report["user_owned_conflicts"] = states.count("USER_OWNED")
    collision_report["synced_conflicts"] = states.count("CLAUDE_SYNCED")
    collision_report["bundled_conflicts"] = states.count("BUNDLED_COLLISION")
    collision_report["ambiguous"] = states.count("AMBIGUOUS")
    collision_report["unknown"] = states.count("UNKNOWN")
    blockers: list[str] = []
    if any(state not in SAFE_COLLISION_STATES for state in states):
        blockers.append("zero-collision requirement is not proven")
    if inventory.get("bundled_evidence") != "EXPLICIT_FIXTURE_EVIDENCE":
        blockers.append("version-bound bundled-skill inventory is unavailable")
    blockers.append("ASM user-data root has symbolic contract only; no real destination is resolved")
    if inventory.get("personal_root_state") == "AMBIGUOUS":
        blockers.append("Claude personal skill root is ambiguous")
    if any(not item.get("eligible_for_canary") for item in selected):
        blockers.append("one or more selected skill destinations are not absent or ASM-managed")
    status = CANARY_STATUS_READY if not blockers else CANARY_STATUS_BLOCKED
    package_preview = _package_preview(package, selected=selected)
    package_preview["confirmation_digest"] = package_data["confirmation_digest"]
    package_preview["planned_destination_root"] = CLAUDE_PERSONAL_SKILL_ROOT
    package_preview["asm_user_data_root"] = CLAUDE_ASM_USER_DATA_ROOT
    preview = {
        "schema_version": "3.0",
        "canary_version": CANARY_VERSION,
        "status": status,
        "real_home_apply_authorized": REAL_HOME_APPLY_AUTHORIZED,
        "runtime": {
            "runtime_id": CLAUDE_RUNTIME_ID,
            "runtime_version": CLAUDE_RUNTIME_VERSION,
            "runtime_fingerprint": contract["provenance"]["executable_sha256"],
            "runtime_contract_digest": contract["runtime_contract_digest"],
            "user_scope_contract_digest": contract["contract_digest"],
            "live_execution": runtime_status.get("live_execution"),
        },
        "home_symbolic_root": "${HOME}",
        "personal_skill_root": CLAUDE_PERSONAL_SKILL_ROOT,
        "inventory": inventory,
        "selected_skills": selected,
        "collision_report": collision_report,
        "asm_user_data_preview": {
            "symbolic_root": CLAUDE_ASM_USER_DATA_ROOT,
            "resolution": "SYMBOLIC_ONLY_UNRESOLVED",
            "planned_source_paths": [
                f"{CLAUDE_ASM_USER_DATA_ROOT}/skills/{item['slug']}/SKILL.md"
                for item in selected
            ],
            "ownership_marker": "${ASM_USER_DATA}/v3/claude/.asm-user-manifest.json",
            "transaction_journal": "${ASM_USER_DATA}/v3/claude/.transactions/<id>.json",
            "writes_performed": False,
        },
        "package_preview": package_preview,
        "package_digest": package_data["package_digest"],
        "confirmation_digest": package_data["confirmation_digest"],
        "authorization_request": {
            "status": "NOT_ISSUED" if blockers else "PENDING_EXPLICIT_USER_AUTHORIZATION",
            "package_digest": package_data["package_digest"],
            "confirmation_digest": package_data["confirmation_digest"],
            "runtime": "Claude Code 2.1.235",
            "scope": "USER",
            "strategy": "MANAGED_COPY",
            "skills": len(selected),
            "files": package_preview["file_count"],
            "bytes": package_preview["managed_copy_bytes"],
            "collisions": collision_report["collision_count"],
            "destination": CLAUDE_PERSONAL_SKILL_ROOT,
            "destination_unchanged_since_preview": True,
            "revalidation_required_before_apply": True,
            "recovery_guarantee": "PROCESS_CRASH_RECOVERABLE",
            "no_changes_made": True,
            "consumable": False,
        },
        "discovery_validation": "STATIC_CONTRACT_ONLY",
        "post_apply_verification_plan": [
            "verify exact selected destination digests",
            "verify ASM ownership marker and journal COMPLETE",
            "verify no unrelated file changed",
            "preview uninstall, then uninstall only unchanged ASM-owned paths",
            "re-preview and explicitly package any reinstall or upgrade",
        ],
        "recovery_plan": {
            "guarantee": "PROCESS_CRASH_RECOVERABLE",
            "after_create": "journal-bound exact digest permits deterministic resume/rollback",
            "after_ownership": "verify marker and exact paths before completion",
            "concurrent_change": "STALE_PACKAGE / MANUAL_CONFLICT; no auto-repair",
            "power_loss": "not claimed",
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(
            {
                "real HOME was inspected read-only for bounded metadata only",
                "Claude live execution is independent and remains RUNTIME_BLOCKED",
                "no provider, auth, config, MCP, plugin, hook, or model surface was read",
                "the package preview cannot authorize or execute real-home mutation",
            }
        ),
        "privacy": {
            "absolute_home_path_persisted": False,
            "private_child_names_persisted": False,
            "raw_skill_bodies_in_preview": False,
            "credentials_or_runtime_output": False,
        },
        "preview_digest": "",
    }
    path_free = copy.deepcopy(preview)
    path_free["preview_digest"] = ""
    preview["preview_digest"] = digest_value(path_free)
    return preview


def build_status_report(
    *, inventory: Mapping[str, Any] | None = None, fixture: str = "ALL_KNOWN_STATIC"
) -> dict[str, Any]:
    """Return a concise status façade with independent readiness dimensions."""

    loaded = (
        dict(inventory)
        if inventory is not None
        else load_runtime_inventory(fixture_name=fixture)
    )
    by_id = {item["runtime_id"]: item for item in loaded.get("runtimes", [])}
    claude = by_id.get("claude-code", {})
    report = {
        "schema_version": "3.0",
        "product": "Agent Skills Matrix v3",
        "stage_router": "READY",
        "static_productization": "READY",
        "project_installer": "READY",
        "claude_user_installer": "ENGINE_READY / CANARY_PENDING",
        "claude_user_contract": "READY" if claude else "UNKNOWN",
        "claude_live_execution": claude.get("live_execution", "UNKNOWN"),
        "codex_live_execution": by_id.get("codex", {}).get(
            "live_execution", "UNKNOWN"
        ),
        "effort_routing": "NOT_READY",
        "cross_runtime_routing": "NOT_READY",
        "opencode_user_install": "PREVIEW_ONLY",
        "hermes": "NOT_IMPLEMENTED",
        "real_home_canary_status": "PENDING_READ_ONLY_PREVIEW",
        "real_home_apply_authorized": False,
        "no_model_or_provider_invocation": True,
        "report_digest": "",
    }
    report["report_digest"] = digest_value(report)
    return report


def render_status_report(report: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "Agent Skills Matrix v3",
            f"Stage Router: {report['stage_router']}",
            f"Static productization: {report['static_productization']}",
            f"Project installer: {report['project_installer']}",
            f"Claude user installer: {report['claude_user_installer']}",
            f"Claude live execution: {report['claude_live_execution']}",
            f"Codex live execution: {report['codex_live_execution']}",
            f"Effort routing: {report['effort_routing']}",
            f"Cross-runtime routing: {report['cross_runtime_routing']}",
            f"OpenCode USER install: {report['opencode_user_install']}",
            f"Hermes: {report['hermes']}",
            f"Real-home canary: {report['real_home_canary_status']}",
            "No changes were made.",
        ]
    )


def render_canary_preview(preview: Mapping[str, Any]) -> str:
    package = preview["package_preview"]
    collisions = preview["collision_report"]
    return "\n".join(
        [
            "Agent Skills Matrix v3",
            "Operation: Claude real-home canary preview",
            f"Status: {preview['status']}",
            "Runtime: Claude Code 2.1.235",
            "Scope: USER",
            "Strategy: MANAGED_COPY",
            f"Skills: {len(preview['selected_skills'])}",
            f"Files: {package['file_count']}",
            f"Bytes: {package['managed_copy_bytes']}",
            f"Destination: {preview['personal_skill_root']}",
            f"Collisions: {collisions['collision_count']}",
            f"Package digest: {preview['package_digest']}",
            f"Confirmation digest: {preview['confirmation_digest']}",
            f"Recovery: {preview['recovery_plan']['guarantee']}",
            "Real-home apply authorized: false",
            "No changes were made.",
        ]
    )
