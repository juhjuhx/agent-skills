"""Safe v3 installer for static project and virtual Claude USER distributions.

The installer is deliberately separate from :mod:`productization`.  The
productization module compiles immutable, derived output and a dry-run plan;
this module is the only place that can apply a filtered persistent package to
an explicitly supplied project directory or a guarded virtual HOME.

No runtime is started on import.  Runtime detection is a short ``--version``
probe and is performed only by the explicit ``detect``/``preview``/``apply``
command path when requested.  Claude USER mutation is virtual-home-only in
Phase 3N and requires an exact package-bound confirmation.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable

# Support both ``python -m tools.v3.installer`` and the direct CLI form.
if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.v3.contract_validation import validate_instance
from tools.v3.productization import (
    GLOBAL_RUNTIME_DIRS,
    ROOT,
    ProductizationError,
    PERSISTENT_LIFECYCLES,
    _json_bytes,
    build_installation_plan,
    compile_distribution,
    digest_bytes,
    digest_value,
    load_runtime_inventory,
    snapshot_digest,
)
from tools.v3.routing_catalog import RoutingCatalogSnapshot
from tools.v3.user_scope import (
    USER_SCOPE_APPLY_NOT_AUTHORIZED,
    UserScopeError,
    build_user_scope_preview,
    load_user_scope_contract,
)
from tools.v3.claude_user_scope import (
    CLAUDE_RUNTIME_ID,
    CLAUDE_RUNTIME_VERSION,
    CLAUDE_USER_SCOPE_CONTRACT_PATH,
    ClaudeUserScopeError,
    build_claude_user_preview,
    classify_claude_collision,
    load_claude_distribution_strategy,
    load_claude_user_contract,
    validate_claude_skill_slug,
    validate_claude_skill_slugs,
)


DEFAULT_TARGET_INVENTORY = (
    ROOT / "fixtures" / "v3" / "productization" / "install-targets-v1.json"
)
INSTALLER_VERSION = "1.0"
INSTALLER_GENERATOR_ID = "agent-skills-matrix-v3-installer"
MARKER_NAME = ".asm-installed.json"
TRANSACTION_DIRECTORY = ".transactions"
BACKUP_DIRECTORY = ".backups"
PROJECT_STAGING_ROOT = ".agent-skills-matrix"
SCOPES = frozenset({"PROJECT", "USER", "GLOBAL"})
INSTALL_ACTIONS = frozenset({"CREATE", "UPDATE_MANAGED", "NO_OP"})
USER_MUTATION_ACTIONS = frozenset(
    {
        "CREATE",
        "UPDATE_MANAGED",
        "NO_OP",
        "REMOVE",
        "RESTORE",
        "SKIP_USER_OWNED",
        "CONFLICT",
    }
)
CONFLICT_ACTIONS = frozenset({"SKIP_USER_OWNED", "CONFLICT"})
# ``action`` is the normalized mutation semantic.  ``operation`` remains a
# descriptive plan field for compatibility, but these pairs are validated so
# a serialized plan cannot carry two contradictory meanings.
PLAN_OPERATION_ACTIONS = {
    "CREATE_DIRECTORY": frozenset({"CREATE", "UPDATE_MANAGED"}),
    "CREATE_GENERATED_FILE": frozenset({"CREATE", "UPDATE_MANAGED"}),
    "LINK_OR_REFERENCE_CANONICAL_SKILL": frozenset(
        {"CREATE", "UPDATE_MANAGED"}
    ),
    "WRITE_PROJECT_CONFIG": frozenset(),
    "SKIP_UNSUPPORTED_RUNTIME": frozenset({"SKIP_UNSUPPORTED"}),
    "SKIP_USER_OWNED": frozenset({"SKIP_USER_OWNED"}),
    "CONFLICT": frozenset({"CONFLICT"}),
    "NO_OP": frozenset({"NO_OP"}),
    "WARN_LIVE_BLOCKED": frozenset({"WARN"}),
}
PLAN_ACTIONS = frozenset(
    action
    for actions in PLAN_OPERATION_ACTIONS.values()
    for action in actions
)
RUNTIME_EXECUTABLES = {
    "codex": "codex",
    "claude-code": "claude",
    "opencode": "opencode",
    "hermes": "hermes",
}

USER_SCOPE_TARGET_VERSION = "1.0"
USER_SCOPE_STRATEGY = "MANAGED_COPY"
USER_MANIFEST_RELATIVE = "v3/claude/.asm-user-manifest.json"
USER_TRANSACTION_RELATIVE = "v3/claude/.transactions"
USER_BACKUP_RELATIVE = "v3/claude/.backups"
USER_STAGING_RELATIVE = "v3/claude/.staging"
USER_SKILL_ROOT_RELATIVE = ".claude/skills"
USER_ASM_SKILL_ROOT_RELATIVE = "v3/claude/skills"
USER_TRANSACTION_PHASES = (
    "PREPARED",
    "STAGED",
    "MUTATING",
    "OWNERSHIP_COMMITTED",
    "VERIFIED",
    "COMPLETE",
    "RECOVERY_REQUIRED",
    "ROLLED_BACK",
)
USER_TRANSACTION_PHASE_ORDER = {
    phase: index for index, phase in enumerate(USER_TRANSACTION_PHASES)
}
USER_ARTIFACT_ROOTS = frozenset({"CLAUDE_PERSONAL", "ASM_USER_DATA"})
USER_PROTECTED_COLLISIONS = frozenset(
    {
        "USER_OWNED",
        "MODIFIED_MANAGED",
        "UNSAFE",
        "UNKNOWN",
        "AMBIGUOUS",
        "CLAUDE_SYNCED",
        "BUNDLED_COLLISION",
        "PROJECT_DUPLICATE",
    }
)
USER_PACKAGE_KINDS = frozenset({"INSTALL", "UNINSTALL", "REVERT"})


class UserTransactionInterrupted(BaseException):
    """Deterministic process-death injection used only by virtual-home tests."""

    def __init__(self, transaction_id: str, boundary: str) -> None:
        self.transaction_id = transaction_id
        self.boundary = boundary
        super().__init__(f"simulated process interruption at {boundary}")


class InstallerError(ValueError):
    """Raised when an install operation cannot be proven safe."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallerError(f"cannot read JSON {path}: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise InstallerError(f"JSON record is not an object: {path}")
    return value


def _relative_path(value: str | Path, *, label: str) -> str:
    raw = value.as_posix() if isinstance(value, Path) else str(value)
    path = Path(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "\\" in raw:
        raise InstallerError(f"unsafe relative {label}: {raw}")
    if path == Path(".") or any(part in {"", "."} for part in path.parts):
        raise InstallerError(f"unsafe relative {label}: {raw}")
    return path.as_posix()


def normalize_scope(scope: str) -> str:
    normalized = str(scope).strip().upper()
    if normalized not in SCOPES:
        raise InstallerError(f"unknown install scope: {scope}")
    return normalized


def _safe_project_root(project_root: str | Path) -> Path:
    """Resolve only an explicitly supplied, existing project directory."""

    raw = Path(project_root).expanduser()
    if not raw.is_absolute():
        raw = Path.cwd() / raw
    if raw.is_symlink():
        raise InstallerError("project root must not itself be a symlink")
    if not raw.exists() or not raw.is_dir():
        raise InstallerError("explicit project root must be an existing directory")
    root = raw.resolve(strict=True)
    if root == Path.home():
        raise InstallerError("the user home directory is not a project root")
    for global_dir in GLOBAL_RUNTIME_DIRS:
        try:
            if root == global_dir.resolve() or global_dir.resolve() in root.parents:
                raise InstallerError(
                    "a user/global runtime directory is not a project root"
                )
        except OSError:
            continue
    return root


def _root_identity(root: Path, *, label: str) -> str:
    """Return a path-free identity for an already validated directory."""

    try:
        stat = root.stat()
    except OSError as exc:
        raise InstallerError(f"cannot stat {label}: {type(exc).__name__}") from exc
    return digest_value(
        {
            "device": int(stat.st_dev),
            "inode": int(stat.st_ino),
            "is_directory": bool(root.is_dir()),
            "label": label,
        }
    )


def _safe_virtual_root(value: str | Path | None, *, label: str) -> Path:
    """Validate an explicitly supplied virtual root without expanding HOME."""

    if value is None:
        raise InstallerError(f"{label} is required; implicit HOME is forbidden")
    raw = Path(value)
    if not raw.is_absolute():
        raise InstallerError(f"{label} must be an absolute virtual path")
    if len(str(raw)) > 4096:
        raise InstallerError(f"{label} exceeds the bounded path length")
    if raw.is_symlink():
        raise InstallerError(f"{label} must not itself be a symlink")
    if not raw.exists() or not raw.is_dir():
        raise InstallerError(f"{label} must be an existing directory")
    root = raw.resolve(strict=True)
    if root == Path(root.anchor):
        raise InstallerError(f"{label} must not be a filesystem root")
    real_home = Path.home().resolve(strict=True)
    try:
        root_stat = root.stat()
        home_stat = real_home.stat()
    except OSError as exc:
        raise InstallerError(f"cannot inspect {label} identity: {type(exc).__name__}") from exc
    if (root_stat.st_dev, root_stat.st_ino) == (home_stat.st_dev, home_stat.st_ino):
        raise InstallerError(f"{label} aliases the real HOME")
    if root == real_home or real_home in root.parents or root in real_home.parents:
        raise InstallerError(f"{label} aliases or contains the real HOME")
    for global_dir in GLOBAL_RUNTIME_DIRS:
        try:
            resolved_global = global_dir.resolve(strict=False)
        except OSError:
            continue
        if (
            root == resolved_global
            or resolved_global in root.parents
            or root in resolved_global.parents
        ):
            raise InstallerError(f"{label} overlaps a real runtime directory")
    if root.is_symlink() or not root.is_dir():
        raise InstallerError(f"{label} is not a stable directory")
    return root


def _safe_virtual_roots(
    home_root: str | Path | None,
    asm_user_data_root: str | Path | None,
) -> tuple[Path, Path]:
    home = _safe_virtual_root(home_root, label="virtual HOME")
    asm = _safe_virtual_root(asm_user_data_root, label="virtual ASM user-data root")
    if home == asm or home in asm.parents or asm in home.parents:
        raise InstallerError("virtual HOME and ASM user-data roots must be separate")
    return home, asm


def _user_target_root_identity(home_root: Path, asm_user_data_root: Path) -> str:
    return digest_value(
        {
            "home_root": _root_identity(home_root, label="virtual HOME"),
            "asm_user_data_root": _root_identity(
                asm_user_data_root, label="virtual ASM user-data root"
            ),
        }
    )


def _project_reference(root: Path | None, scope: str) -> str:
    if root is None:
        return digest_value({"scope": scope, "project_root": None})
    return digest_value({"scope": scope, "project_root": str(root)})


def _project_identity(root: Path) -> str:
    """Return a non-secret identity digest without reading project contents."""

    try:
        stat = root.stat()
    except OSError as exc:
        raise InstallerError(f"cannot stat project root: {type(exc).__name__}") from exc
    return digest_value(
        {
            "project_root_reference": _project_reference(root, "PROJECT"),
            "device": int(stat.st_dev),
            "inode": int(stat.st_ino),
            "is_directory": bool(root.is_dir()),
        }
    )


def _path_within(root: Path, relative: str | Path) -> Path:
    safe = _relative_path(relative, label="path")
    return root / Path(safe)


def _validate_user_skill_destination(
    root_class: str, relative: str, *, skill_id: str | None = None
) -> str:
    """Allow journal/package paths only for one exact Claude SKILL.md shape."""

    safe = _relative_path(relative, label="USER skill destination")
    prefix = (
        Path(USER_SKILL_ROOT_RELATIVE)
        if root_class == "CLAUDE_PERSONAL"
        else Path(USER_ASM_SKILL_ROOT_RELATIVE)
        if root_class == "ASM_USER_DATA"
        else None
    )
    parts = Path(safe).parts
    if (
        prefix is None
        or parts[:-2] != prefix.parts
        or len(parts) != len(prefix.parts) + 2
        or parts[-1] != "SKILL.md"
    ):
        raise InstallerError("USER skill destination is outside the managed skill root")
    slug = parts[-2]
    try:
        mapped = validate_claude_skill_slug(slug, platform="macos")
    except ClaudeUserScopeError as exc:
        raise InstallerError("USER skill destination has an unsafe slug") from exc
    if mapped != slug:
        raise InstallerError("USER skill destination slug is not canonical")
    if skill_id is not None:
        try:
            expected = validate_claude_skill_slug(skill_id, platform="macos")
        except ClaudeUserScopeError as exc:
            raise InstallerError("USER skill identifier has an unsafe slug") from exc
        if expected != slug:
            raise InstallerError("USER skill destination does not match its skill ID")
    return safe


def _validate_user_backup_path(value: str) -> str:
    """Allow only transaction-scoped backup references owned by ASM."""

    safe = _relative_path(value, label="USER backup")
    parts = Path(safe).parts
    prefix = Path(USER_BACKUP_RELATIVE).parts
    if (
        len(parts) != len(prefix) + 2
        or parts[: len(prefix)] != prefix
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", parts[-2])
        or not re.fullmatch(r"artifact-[0-9]+\.bin", parts[-1])
    ):
        raise InstallerError("USER backup path is outside the transaction backup root")
    return safe


def _has_symlink_in_path(root: Path, relative: str | Path) -> bool:
    safe = _relative_path(relative, label="path")
    current = root
    for part in Path(safe).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _ensure_no_symlink_parent(root: Path, relative: str | Path) -> None:
    safe = _relative_path(relative, label="path")
    current = root
    for part in Path(safe).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise InstallerError(f"destination parent is a symlink: {safe}")
        if current.exists() and not current.is_dir():
            raise InstallerError(f"destination parent is not a directory: {safe}")


def _load_target_inventory(
    path: str | Path = DEFAULT_TARGET_INVENTORY,
) -> dict[str, Any]:
    document = _read_json(Path(path))
    if (
        document.get("schema_version") != "3.0"
        or document.get("install_target_version") != "1.0"
    ):
        raise InstallerError("unsupported install target inventory version")
    targets = document.get("targets")
    if not isinstance(targets, list):
        raise InstallerError("install target inventory requires a targets list")
    result: dict[str, dict[str, Any]] = {}
    for target in targets:
        if not isinstance(target, dict) or not isinstance(
            target.get("runtime_id"), str
        ):
            raise InstallerError("install target inventory contains an invalid target")
        runtime_id = target["runtime_id"]
        if runtime_id in result:
            raise InstallerError(f"duplicate install target: {runtime_id}")
        scope = target.get("scope")
        if scope != "PROJECT":
            raise InstallerError(f"install target is not project-scoped: {runtime_id}")
        template = target.get("destination_root_template")
        if template is not None:
            if not isinstance(template, str) or "{runtime_id}" not in template:
                raise InstallerError(f"invalid destination template: {runtime_id}")
            _relative_path(
                template.replace("{runtime_id}", runtime_id),
                label="destination template",
            )
        if target.get("config_mutation_required") is not False:
            raise InstallerError(
                f"install target requires forbidden config mutation: {runtime_id}"
            )
        if target.get("copy_support") not in {"VERIFIED", "UNSUPPORTED"}:
            raise InstallerError(
                f"unknown copy support for install target: {runtime_id}"
            )
        if target.get("install_mechanism") not in {"COPY", "NONE"}:
            raise InstallerError(
                f"unknown install mechanism for install target: {runtime_id}"
            )
        if not isinstance(target.get("installable_lifecycles"), list):
            raise InstallerError(
                f"install target has no lifecycle contract: {runtime_id}"
            )
        if not set(target["installable_lifecycles"]).issubset(PERSISTENT_LIFECYCLES):
            raise InstallerError(
                f"install target permits ephemeral artifacts: {runtime_id}"
            )
        result[runtime_id] = copy.deepcopy(target)
    return {
        "schema_version": document["schema_version"],
        "install_target_version": document["install_target_version"],
        "generator_id": document.get("generator_id"),
        "targets": result,
        "inventory_digest": digest_value(
            {
                "schema_version": document["schema_version"],
                "install_target_version": document["install_target_version"],
                "generator_id": document.get("generator_id"),
                "targets": [result[key] for key in sorted(result)],
            }
        ),
    }


def load_install_target(
    runtime_id: str, path: str | Path = DEFAULT_TARGET_INVENTORY
) -> dict[str, Any]:
    inventory = _load_target_inventory(path)
    try:
        return copy.deepcopy(inventory["targets"][runtime_id])
    except KeyError as exc:
        raise InstallerError(
            f"no verified project install target for runtime: {runtime_id}"
        ) from exc


def _target_validation_errors(
    runtime_status: dict[str, Any], target: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if target.get("runtime_id") != runtime_status.get("runtime_id"):
        errors.append("runtime id does not match install target")
    observed = runtime_status.get("observed_runtime_version")
    supported = target.get("supported_runtime_version")
    if supported is None or (observed is not None and supported != observed):
        errors.append(
            "installed runtime version does not match the verified install target"
        )
    if target.get("runtime_contract_digest") != runtime_status.get(
        "runtime_contract_digest"
    ):
        errors.append(
            "runtime contract digest does not match the verified install target"
        )
    if target.get("scope") != "PROJECT":
        errors.append("only PROJECT install targets are supported")
    if target.get("support_status") not in {"HOST_MANAGED"}:
        errors.append("runtime has no supported persistent host-managed install target")
    if target.get("copy_support") != "VERIFIED":
        errors.append("copy support is not verified")
    if target.get("install_mechanism") != "COPY":
        errors.append("install mechanism is not the verified COPY contract")
    if target.get("config_mutation_required") is not False:
        errors.append("install target would require runtime config mutation")
    if not isinstance(target.get("destination_root_template"), str):
        errors.append("install target has no safe project destination")
    return errors


def _target_root(target: dict[str, Any], runtime_id: str) -> str:
    template = target.get("destination_root_template")
    if not isinstance(template, str):
        raise InstallerError("install target has no destination root")
    expanded = template.replace("{runtime_id}", runtime_id)
    return _relative_path(expanded, label="destination root")


def _marker_path(target: dict[str, Any], runtime_id: str) -> str:
    return _relative_path(
        Path(_target_root(target, runtime_id)) / MARKER_NAME, label="ownership marker"
    )


def _marker_artifact_map(marker: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not marker:
        return {}
    return {item["path"]: item for item in marker.get("artifacts", [])}


def _validate_marker(
    marker: dict[str, Any], *, runtime_id: str, scope: str, target_root: str
) -> None:
    digest_fields = (
        "package_digest",
        "plan_digest",
        "snapshot_digest",
        "install_target_digest",
        "source_manifest_digest",
    )
    if (
        marker.get("generator_id") != INSTALLER_GENERATOR_ID
        or marker.get("managed") is not True
    ):
        raise InstallerError("ownership marker is not owned by Agent Skills Matrix")
    if marker.get("schema_version") != "3.0" or marker.get("runtime_id") != runtime_id:
        raise InstallerError("ownership marker identity is invalid")
    if marker.get("scope") != scope:
        raise InstallerError("ownership marker scope or package binding is invalid")
    expected_marker = _relative_path(
        Path(target_root) / MARKER_NAME, label="ownership marker"
    )
    if marker.get("marker_path") != expected_marker:
        raise InstallerError("ownership marker path binding is invalid")
    for field in digest_fields:
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(marker.get(field))):
            raise InstallerError(f"ownership marker has an invalid {field}")
    runtime_contract_digest = marker.get("runtime_contract_digest")
    if runtime_contract_digest is not None and not re.fullmatch(
        r"sha256:[0-9a-f]{64}", str(runtime_contract_digest)
    ):
        raise InstallerError("ownership marker has an invalid runtime contract digest")
    if (
        not isinstance(marker.get("transaction_id"), str)
        or not marker["transaction_id"]
    ):
        raise InstallerError("ownership marker transaction binding is invalid")
    if not isinstance(marker.get("artifacts"), list):
        raise InstallerError("ownership marker has no exact artifact list")
    seen: set[str] = set()
    root = Path(target_root)
    for item in marker["artifacts"]:
        if not isinstance(item, dict):
            raise InstallerError("ownership marker contains a non-object artifact")
        for field in ("path", "content_digest", "source_digest", "lifecycle", "origin"):
            if field not in item:
                raise InstallerError(f"ownership marker artifact lacks {field}")
        path = _relative_path(item["path"], label="managed artifact")
        if path in seen:
            raise InstallerError("ownership marker contains duplicate artifact paths")
        seen.add(path)
        try:
            Path(path).relative_to(root)
        except ValueError as exc:
            raise InstallerError(
                "ownership marker claims a path outside its target root"
            ) from exc
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(item["content_digest"])):
            raise InstallerError("ownership marker contains an invalid content digest")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(item["source_digest"])):
            raise InstallerError("ownership marker contains an invalid source digest")
        if item["lifecycle"] not in PERSISTENT_LIFECYCLES:
            raise InstallerError(
                "ownership marker attempts to persist an ephemeral artifact"
            )
        if item["origin"] not in {"CREATED_BY_ASM", "UPDATED_ASM_MANAGED", "NO_OP"}:
            raise InstallerError("ownership marker has an invalid artifact origin")
    backups = marker.get("backups")
    if not isinstance(backups, list):
        raise InstallerError("ownership marker has no backup list")
    backup_paths: set[str] = set()
    for backup in backups:
        if not isinstance(backup, dict):
            raise InstallerError("ownership marker contains a non-object backup")
        for field in ("path", "previous_digest", "backup_path", "backup_digest"):
            if field not in backup:
                raise InstallerError(f"ownership marker backup lacks {field}")
        path = _relative_path(backup["path"], label="backup artifact")
        backup_path = _relative_path(backup["backup_path"], label="backup")
        for candidate, label in ((path, "backup artifact"), (backup_path, "backup")):
            try:
                Path(candidate).relative_to(root)
            except ValueError as exc:
                raise InstallerError(
                    f"ownership marker claims a {label} outside its target root"
                ) from exc
        if backup_path in backup_paths:
            raise InstallerError("ownership marker contains duplicate backup paths")
        backup_paths.add(backup_path)
        for field in ("previous_digest", "backup_digest"):
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(backup[field])):
                raise InstallerError(f"ownership marker backup has an invalid {field}")
    previous_marker = marker.get("previous_marker_backup")
    if previous_marker is not None:
        if not isinstance(previous_marker, dict):
            raise InstallerError("ownership marker previous marker backup is invalid")
        if set(previous_marker) != {"path", "digest"}:
            raise InstallerError("ownership marker previous marker backup is invalid")
        previous_path = _relative_path(
            previous_marker["path"], label="previous marker backup"
        )
        try:
            Path(previous_path).relative_to(root)
        except ValueError as exc:
            raise InstallerError(
                "ownership marker claims a previous marker backup outside its target root"
            ) from exc
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(previous_marker["digest"])):
            raise InstallerError(
                "ownership marker previous marker backup digest is invalid"
            )
    created_directories = marker.get("created_directories")
    if not isinstance(created_directories, list) or any(
        not isinstance(path, str) for path in created_directories
    ):
        raise InstallerError("ownership marker created directory list is invalid")
    # The bounded transaction may create the staging parent itself (for
    # example ``.agent-skills-matrix``) before creating this runtime's target
    # root.  Permit that one deterministic ancestor, but nothing higher.
    created_root = root.parent
    for path in created_directories:
        safe = _relative_path(path, label="created directory")
        try:
            Path(safe).relative_to(created_root)
        except ValueError as exc:
            raise InstallerError(
                "ownership marker claims a directory outside its staging root"
            ) from exc


def _read_marker(
    root: Path,
    marker_relative: str,
    *,
    runtime_id: str,
    scope: str,
    target_root: str,
) -> tuple[dict[str, Any] | None, str | None]:
    marker_path = _path_within(root, marker_relative)
    _ensure_no_symlink_parent(root, marker_relative)
    if marker_path.is_symlink():
        raise InstallerError("ownership marker is a symlink")
    if not marker_path.exists():
        return None, None
    if not marker_path.is_file():
        raise InstallerError("ownership marker is not a regular file")
    marker = _read_json(marker_path)
    _validate_marker(
        marker, runtime_id=runtime_id, scope=scope, target_root=target_root
    )
    return marker, digest_bytes(marker_path.read_bytes())


def _inspect_destination(
    root: Path,
    relative: str,
    *,
    marker_artifacts: dict[str, dict[str, Any]],
) -> tuple[str, str | None]:
    safe = _relative_path(relative, label="destination")
    if _has_symlink_in_path(root, safe):
        return "UNSAFE", None
    path = _path_within(root, safe)
    marker_item = marker_artifacts.get(safe)
    if not path.exists():
        return ("MISSING", None) if marker_item else ("ABSENT", None)
    if not path.is_file():
        return "UNSAFE", None
    current_digest = digest_bytes(path.read_bytes())
    if marker_item is None:
        return "USER_OWNED", current_digest
    if current_digest == marker_item.get("content_digest"):
        return "ASM_MANAGED", current_digest
    return "MODIFIED_MANAGED", current_digest


def _load_distribution(
    distribution_dir: str | Path,
) -> tuple[Path, dict[str, Any], dict[str, bytes]]:
    raw = Path(distribution_dir).expanduser()
    if raw.is_symlink() or not raw.is_dir():
        raise InstallerError("distribution directory must be a real directory")
    distribution = raw.resolve(strict=True)
    manifest_path = distribution / "artifact-manifest.json"
    marker_path = distribution / ".asm-generated.json"
    if manifest_path.is_symlink() or marker_path.is_symlink():
        raise InstallerError("distribution metadata must not be symlinked")
    manifest = _read_json(manifest_path)
    errors = validate_instance("GeneratedArtifactManifest", manifest).errors
    if errors:
        raise InstallerError(
            "invalid generated artifact manifest: " + "; ".join(errors)
        )
    manifest_without_digest = copy.deepcopy(manifest)
    manifest_without_digest["manifest_digest"] = ""
    if manifest.get("manifest_digest") != digest_value(manifest_without_digest):
        raise InstallerError("generated artifact manifest digest is invalid")
    if not marker_path.is_file():
        raise InstallerError("generated distribution has no ownership marker")
    generated_marker = _read_json(marker_path)
    if generated_marker.get("managed") is not True or generated_marker.get(
        "artifact_manifest_digest"
    ) != manifest.get("manifest_digest"):
        raise InstallerError("generated distribution marker does not bind its manifest")
    files: dict[str, bytes] = {}
    for artifact in manifest.get("artifacts", []):
        relative = _relative_path(artifact["path"], label="generated artifact")
        if _has_symlink_in_path(distribution, relative):
            raise InstallerError(f"generated artifact is symlinked: {relative}")
        path = _path_within(distribution, relative)
        if not path.is_file():
            raise InstallerError(f"generated artifact is missing: {relative}")
        payload = path.read_bytes()
        if digest_bytes(payload) != artifact["content_digest"]:
            raise InstallerError(f"generated artifact digest mismatch: {relative}")
        files[relative] = payload
    return distribution, manifest, files


def _validate_plan(plan: dict[str, Any], manifest: dict[str, Any]) -> None:
    errors = validate_instance("InstallationPlan", plan).errors
    if errors:
        raise InstallerError("invalid InstallationPlan: " + "; ".join(errors))
    plan_without_digest = copy.deepcopy(plan)
    plan_without_digest["plan_digest"] = ""
    if plan.get("plan_digest") != digest_value(plan_without_digest):
        raise InstallerError("InstallationPlan digest is invalid")
    if plan.get("runtime_id") != manifest.get("runtime_id"):
        raise InstallerError("InstallationPlan runtime differs from distribution")
    plan_artifacts = {item["path"]: item for item in plan.get("artifacts", [])}
    for item in manifest.get("artifacts", []):
        planned = plan_artifacts.get(item["path"])
        if planned is None:
            raise InstallerError(
                f"InstallationPlan omits generated artifact: {item['path']}"
            )
        for field in ("kind", "content_digest", "source_digest", "lifecycle"):
            if planned.get(field) != item.get(field):
                raise InstallerError(
                    f"InstallationPlan is stale for artifact: {item['path']}"
                )
        operation = next(
            (
                candidate
                for candidate in plan.get("operations", [])
                if candidate.get("path") == item["path"]
            ),
            None,
        )
        if operation is None:
            raise InstallerError(
                f"InstallationPlan has no authoritative action: {item['path']}"
            )
        operation_name = operation.get("operation")
        action = operation.get("action")
        if action not in PLAN_ACTIONS:
            raise InstallerError(
                f"InstallationPlan has no authoritative action: {item['path']}"
            )
        allowed_actions = PLAN_OPERATION_ACTIONS.get(operation_name, frozenset())
        if action not in allowed_actions:
            raise InstallerError(
                "InstallationPlan operation/action semantics conflict: "
                f"{item['path']} ({operation_name!r} cannot represent {action!r})"
            )


def _package_digest(package: dict[str, Any]) -> str:
    without_digest = copy.deepcopy(package)
    without_digest["package_digest"] = ""
    return digest_value(without_digest)


def _validate_package(package: dict[str, Any]) -> None:
    errors = validate_instance("InstallPackage", package).errors
    if errors:
        raise InstallerError("invalid InstallPackage: " + "; ".join(errors))
    if package.get("package_digest") != _package_digest(package):
        raise InstallerError("InstallPackage digest is invalid")
    scope = package.get("scope")
    if scope == "GLOBAL" and package.get("apply_allowed"):
        raise InstallerError("GLOBAL InstallPackage cannot permit apply")
    if scope == "USER" and package.get("apply_allowed"):
        if package.get("runtime_id") != CLAUDE_RUNTIME_ID:
            raise InstallerError("USER apply is only implemented for Claude Code")
        if package.get("distribution_strategy") != USER_SCOPE_STRATEGY:
            raise InstallerError("USER apply requires the verified MANAGED_COPY strategy")
        if package.get("package_kind") not in USER_PACKAGE_KINDS:
            raise InstallerError("USER package has no supported package kind")
        if package.get("target_root_identity") is None:
            raise InstallerError("USER package has no virtual target identity")
    for artifact in package.get("artifacts", []):
        if artifact.get("lifecycle") not in PERSISTENT_LIFECYCLES:
            raise InstallerError(
                "InstallPackage contains an execution-ephemeral artifact"
            )
        if scope == "USER":
            if artifact.get("destination_root") not in USER_ARTIFACT_ROOTS:
                raise InstallerError("USER artifact has no bounded destination root")
            if artifact.get("action") not in USER_MUTATION_ACTIONS:
                raise InstallerError("USER package contains a non-mutation action")
            _validate_user_skill_destination(
                artifact["destination_root"],
                artifact["destination_path"],
                skill_id=artifact.get("skill_id"),
            )
    if scope == "USER":
        destinations = [
            (item.get("destination_root"), item.get("destination_path"))
            for item in package.get("artifacts", [])
        ]
        if len(destinations) != len(set(destinations)):
            raise InstallerError("USER package contains duplicate destination paths")


def _destination_for(target: dict[str, Any], runtime_id: str, source_path: str) -> str:
    target_root = Path(_target_root(target, runtime_id))
    source = Path(_relative_path(source_path, label="source artifact"))
    if source.parts and source.parts[0] == runtime_id:
        source = Path(*source.parts[1:])
    if not source.parts:
        raise InstallerError(
            f"generated artifact has no destination name: {source_path}"
        )
    return _relative_path(target_root / source, label="destination")


def build_claude_user_target(
    runtime_status: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
    strategy: str = USER_SCOPE_STRATEGY,
) -> dict[str, Any]:
    """Bind the generic USER package to the qualified Claude contract."""

    status_errors = validate_instance("RuntimeProductStatus", runtime_status).errors
    if status_errors:
        raise InstallerError(
            "invalid runtime product status: " + "; ".join(status_errors)
        )
    loaded = load_claude_user_contract() if contract is None else copy.deepcopy(contract)
    if loaded.get("runtime_id") != CLAUDE_RUNTIME_ID:
        raise InstallerError("Claude USER target has the wrong runtime")
    if loaded.get("observed_runtime_version") != CLAUDE_RUNTIME_VERSION:
        raise InstallerError("Claude USER target is not bound to 2.1.235")
    if runtime_status.get("runtime_id") != CLAUDE_RUNTIME_ID:
        raise InstallerError("Claude USER target received a different runtime")
    if runtime_status.get("observed_runtime_version") != CLAUDE_RUNTIME_VERSION:
        raise InstallerError("Claude runtime version changed")
    if runtime_status.get("runtime_contract_digest") != loaded.get(
        "runtime_contract_digest"
    ):
        raise InstallerError("Claude runtime contract digest does not match")
    if strategy != USER_SCOPE_STRATEGY:
        raise InstallerError("Phase 3N supports MANAGED_COPY only")
    strategies = load_claude_distribution_strategy()["strategies"]
    strategy_record = next(
        (item for item in strategies if item.get("strategy") == strategy), None
    )
    if not isinstance(strategy_record, dict):
        raise InstallerError("Claude MANAGED_COPY strategy is absent")
    if strategy_record.get("final_support") != "INSTALLED_RUNTIME_VERIFIED":
        raise InstallerError("Claude MANAGED_COPY is not version-bound support")
    fingerprint = loaded.get("provenance", {}).get("executable_sha256")
    if not isinstance(fingerprint, str):
        raise InstallerError("Claude runtime fingerprint is unavailable")
    return {
        "schema_version": "3.0",
        "user_target_version": USER_SCOPE_TARGET_VERSION,
        "runtime_id": CLAUDE_RUNTIME_ID,
        "scope": "USER",
        "runtime_version": CLAUDE_RUNTIME_VERSION,
        "runtime_fingerprint": fingerprint,
        "runtime_contract_digest": loaded["runtime_contract_digest"],
        "user_scope_contract_digest": loaded["contract_digest"],
        "distribution_strategy": USER_SCOPE_STRATEGY,
        "install_mechanism": "COPY",
        "copy_support": "VERIFIED",
        "support_classification": "VIRTUAL_HOME_ONLY",
        "personal_skill_root_template": loaded["personal_skill_root"],
        "asm_user_data_root_template": loaded["asm_user_data_root"],
        "config_mutation_required": False,
        "native_discovery_evidence": "INSTALLED_RUNTIME_VERIFIED",
        "strategy_evidence": strategy_record["final_support"],
        "collision_policy": {
            "synced": "BLOCK",
            "bundled": "BLOCK",
            "user_owned": "BLOCK",
            "ambiguous": "BLOCK",
        },
        "apply_allowed": True,
        "evidence_refs": sorted(
            set(
                list(loaded.get("evidence_refs", []))
                + [str(CLAUDE_USER_SCOPE_CONTRACT_PATH.relative_to(ROOT))]
            )
        ),
    }


def _user_manifest_digest(manifest: dict[str, Any]) -> str:
    value = copy.deepcopy(manifest)
    value["manifest_digest"] = ""
    return digest_value(value)


def _user_artifact_key(item: dict[str, Any]) -> tuple[str, str]:
    return (str(item.get("destination_root")), str(item.get("destination_path")))


def _validate_user_manifest(manifest: dict[str, Any]) -> None:
    if (
        manifest.get("schema_version") != "3.0"
        or manifest.get("manifest_version") != USER_SCOPE_TARGET_VERSION
        or manifest.get("generator_id") != INSTALLER_GENERATOR_ID
        or manifest.get("managed") is not True
    ):
        raise InstallerError("USER ownership manifest identity is invalid")
    if manifest.get("runtime_id") != CLAUDE_RUNTIME_ID or manifest.get("scope") != "USER":
        raise InstallerError("USER ownership manifest runtime or scope is invalid")
    if manifest.get("distribution_strategy") != USER_SCOPE_STRATEGY:
        raise InstallerError("USER ownership manifest strategy is invalid")
    if manifest.get("manifest_path") != USER_MANIFEST_RELATIVE:
        raise InstallerError("USER ownership manifest path is invalid")
    if not isinstance(manifest.get("transaction_id"), str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", manifest["transaction_id"]
    ):
        raise InstallerError("USER ownership manifest transaction id is invalid")
    # Cleanup/recovery must remain possible after the Claude executable is
    # removed or upgraded.  New mutation packages bind the current qualified
    # version separately; an existing ownership record only needs a bounded,
    # well-formed historical version value here.
    if not isinstance(manifest.get("runtime_version"), str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", manifest["runtime_version"]
    ):
        raise InstallerError("USER ownership manifest runtime version is invalid")
    if not re.fullmatch(
        r"sha256:[0-9a-f]{64}", str(manifest.get("runtime_fingerprint"))
    ):
        raise InstallerError("USER ownership manifest runtime fingerprint is invalid")
    for field in (
        "package_digest",
        "snapshot_digest",
        "runtime_contract_digest",
        "user_scope_contract_digest",
        "target_root_identity",
        "source_manifest_digest",
    ):
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(manifest.get(field))):
            raise InstallerError(f"USER ownership manifest has an invalid {field}")
    if manifest.get("manifest_digest") != _user_manifest_digest(manifest):
        raise InstallerError("USER ownership manifest digest is invalid")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise InstallerError("USER ownership manifest has no artifact list")
    seen: set[tuple[str, str]] = set()
    for item in artifacts:
        if not isinstance(item, dict):
            raise InstallerError("USER ownership manifest artifact is invalid")
        required = (
            "skill_id",
            "destination_root",
            "destination_path",
            "source_path",
            "source_digest",
            "content_digest",
            "lifecycle",
            "origin",
        )
        if any(field not in item for field in required):
            raise InstallerError("USER ownership manifest artifact is incomplete")
        if item["destination_root"] not in USER_ARTIFACT_ROOTS:
            raise InstallerError("USER ownership manifest has an invalid root class")
        key = _user_artifact_key(item)
        if key in seen:
            raise InstallerError("USER ownership manifest has duplicate paths")
        seen.add(key)
        _validate_user_skill_destination(
            item["destination_root"],
            item["destination_path"],
            skill_id=item["skill_id"],
        )
        _relative_path(item["source_path"], label="USER source artifact")
        for field in ("source_digest", "content_digest"):
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(item[field])):
                raise InstallerError(f"USER ownership manifest has an invalid {field}")
        if item["lifecycle"] not in PERSISTENT_LIFECYCLES:
            raise InstallerError("USER ownership manifest contains an ephemeral artifact")
        if item["origin"] not in {
            "CREATED_BY_ASM",
            "UPDATED_ASM_MANAGED",
            "NO_OP",
            "RESTORED_ASM_MANAGED",
        }:
            raise InstallerError("USER ownership manifest has an invalid origin")
    backups = manifest.get("backups", [])
    if not isinstance(backups, list):
        raise InstallerError("USER ownership manifest backup list is invalid")
    for backup in backups:
        if not isinstance(backup, dict):
            raise InstallerError("USER ownership manifest backup is invalid")
        for field in ("destination_root", "destination_path", "backup_path", "previous_digest", "backup_digest"):
            if field not in backup:
                raise InstallerError("USER ownership manifest backup is incomplete")
        if backup["destination_root"] not in USER_ARTIFACT_ROOTS:
            raise InstallerError("USER ownership manifest backup root is invalid")
        _validate_user_skill_destination(
            backup["destination_root"], backup["destination_path"]
        )
        backup_relative = _relative_path(backup["backup_path"], label="USER backup")
        expected_prefix = Path(USER_BACKUP_RELATIVE) / manifest["transaction_id"]
        if (
            Path(backup_relative).parent != expected_prefix
            or not re.fullmatch(r"artifact-[0-9]+\.bin", Path(backup_relative).name)
        ):
            raise InstallerError("USER ownership manifest backup path is invalid")
        for field in ("previous_digest", "backup_digest"):
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(backup[field])):
                raise InstallerError("USER ownership manifest backup digest is invalid")
    previous = manifest.get("previous_manifest_backup")
    if previous is not None:
        if not isinstance(previous, dict) or set(previous) != {"path", "digest"}:
            raise InstallerError("USER previous manifest backup is invalid")
        previous_path = _relative_path(
            previous["path"], label="USER previous manifest backup"
        )
        expected_previous_path = _relative_path(
            Path(USER_BACKUP_RELATIVE)
            / manifest["transaction_id"]
            / "previous-manifest.json",
            label="USER previous manifest backup",
        )
        if previous_path != expected_previous_path:
            raise InstallerError("USER previous manifest backup path is invalid")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(previous["digest"])):
            raise InstallerError("USER previous manifest backup digest is invalid")
    created = manifest.get("created_directories", [])
    if not isinstance(created, list) or any(not isinstance(item, str) for item in created):
        raise InstallerError("USER created directory list is invalid")
    for item in created:
        _relative_path(item, label="USER created directory")


def _read_user_manifest(
    asm_user_data_root: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    path = _path_within(asm_user_data_root, USER_MANIFEST_RELATIVE)
    _ensure_no_symlink_parent(asm_user_data_root, USER_MANIFEST_RELATIVE)
    if path.is_symlink():
        raise InstallerError("USER ownership manifest is a symlink")
    if not path.exists():
        return None, None
    if not path.is_file():
        raise InstallerError("USER ownership manifest is not a file")
    manifest = _read_json(path)
    _validate_user_manifest(manifest)
    return manifest, digest_bytes(path.read_bytes())


def _inspect_user_destination(
    root: Path,
    relative: str,
    *,
    root_class: str,
    marker_artifacts: dict[tuple[str, str], dict[str, Any]],
) -> tuple[str, str | None]:
    safe = _relative_path(relative, label="USER destination")
    key = (root_class, safe)
    marker_item = marker_artifacts.get(key)
    if _has_symlink_in_path(root, safe):
        return "UNSAFE", None
    path = _path_within(root, safe)
    if not path.exists():
        if marker_item is not None:
            return "MISSING", None
        # An existing skill directory with no ASM entry is user-owned even if
        # its SKILL.md file is absent; applying must not adopt it.
        if path.parent.exists():
            if path.parent.is_dir() and not any(path.parent.iterdir()):
                return "ABSENT", None
            return "USER_OWNED", None
        return "ABSENT", None
    if not path.is_file():
        return "UNSAFE", None
    current_digest = digest_bytes(path.read_bytes())
    if marker_item is None:
        return "USER_OWNED", current_digest
    if path.parent.is_dir() and any(
        child.name != path.name for child in path.parent.iterdir()
    ):
        return "MODIFIED_MANAGED", current_digest
    if current_digest == marker_item.get("content_digest"):
        return "ASM_MANAGED", current_digest
    return "MODIFIED_MANAGED", current_digest


def _canonical_user_source(
    record: dict[str, Any],
    *,
    repository_root: str | Path,
    asm_user_data_root: Path,
    slug: str,
) -> tuple[bytes, str]:
    source = record.get("source")
    if not isinstance(source, dict):
        raise InstallerError(f"canonical source metadata is missing: {record.get('skill_id')}")
    source_path = _relative_path(source.get("path", ""), label="canonical skill")
    expected = source.get("digest")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(expected)):
        raise InstallerError(f"canonical source digest is invalid: {record.get('skill_id')}")
    repo = Path(repository_root)
    if not repo.is_absolute() or not repo.is_dir():
        raise InstallerError("canonical repository root must be an explicit directory")
    repo = repo.resolve(strict=True)
    candidate = (repo / Path(source_path)).resolve(strict=False)
    try:
        candidate.relative_to(repo)
    except ValueError as exc:
        raise InstallerError("canonical skill source escapes the repository") from exc
    try:
        raw = candidate.read_bytes()
    except OSError:
        raw = b""
    if raw and digest_bytes(raw) == expected:
        return raw, source_path
    # Once applied, the ASM store is a stable derived source for recovery and
    # repository relocation.  It is accepted only when its digest is exact.
    stored = _path_within(
        asm_user_data_root,
        Path(USER_ASM_SKILL_ROOT_RELATIVE) / slug / "SKILL.md",
    )
    if _has_symlink_in_path(
        asm_user_data_root,
        Path(USER_ASM_SKILL_ROOT_RELATIVE) / slug / "SKILL.md",
    ):
        raise InstallerError("ASM source store contains a symlink")
    try:
        stored_raw = stored.read_bytes()
    except OSError as exc:
        raise InstallerError(f"canonical skill digest changed: {record.get('skill_id')}") from exc
    if digest_bytes(stored_raw) != expected:
        raise InstallerError(f"canonical skill digest changed: {record.get('skill_id')}")
    return stored_raw, source_path


def _user_source_manifest(
    snapshot: RoutingCatalogSnapshot,
    *,
    repository_root: str | Path,
    asm_user_data_root: Path,
    slugs: dict[str, str],
) -> tuple[dict[str, Any], dict[str, bytes]]:
    entries: list[dict[str, Any]] = []
    sources: dict[str, bytes] = {}
    for record in sorted(snapshot.records, key=lambda item: item["skill_id"]):
        skill_id = str(record["skill_id"])
        raw, source_path = _canonical_user_source(
            record,
            repository_root=repository_root,
            asm_user_data_root=asm_user_data_root,
            slug=slugs[skill_id],
        )
        source_digest = str(record["source"]["digest"])
        if digest_bytes(raw) != source_digest:
            raise InstallerError(f"canonical skill digest changed: {skill_id}")
        sources[skill_id] = raw
        entries.append(
            {
                "skill_id": skill_id,
                "slug": slugs[skill_id],
                "source_path": source_path,
                "source_digest": source_digest,
                "content_digest": digest_bytes(raw),
            }
        )
    manifest = {
        "schema_version": "3.0",
        "source_manifest_version": USER_SCOPE_TARGET_VERSION,
        "kind": "CLAUDE_USER_MANAGED_COPY",
        "snapshot_digest": snapshot_digest(snapshot),
        "skill_count": len(entries),
        "skills": entries,
    }
    return manifest, sources


def _user_confirmation_binding(package: dict[str, Any]) -> str:
    value = copy.deepcopy(package)
    value["package_digest"] = ""
    value["confirmation_binding_digest"] = ""
    return digest_value(value)


def _finalize_user_package(package: dict[str, Any]) -> dict[str, Any]:
    package["confirmation_binding_digest"] = _user_confirmation_binding(package)
    package["package_digest"] = _package_digest(package)
    _validate_package(package)
    return package


def build_user_install_package(
    snapshot: RoutingCatalogSnapshot,
    runtime_status: dict[str, Any],
    *,
    home_root: str | Path,
    asm_user_data_root: str | Path,
    repository_root: str | Path = ROOT,
    target: dict[str, Any] | None = None,
    contract: dict[str, Any] | None = None,
    platform: str = "macos",
    collision_states: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build an immutable generic USER package for Claude MANAGED_COPY."""

    home, asm = _safe_virtual_roots(home_root, asm_user_data_root)
    target = copy.deepcopy(target or build_claude_user_target(runtime_status, contract=contract))
    if target.get("runtime_id") != CLAUDE_RUNTIME_ID or target.get("scope") != "USER":
        raise InstallerError("USER package target is not Claude USER scope")
    if target.get("distribution_strategy") != USER_SCOPE_STRATEGY:
        raise InstallerError("USER package requires MANAGED_COPY")
    try:
        slugs = validate_claude_skill_slugs(
            (record["skill_id"] for record in snapshot.records), platform=platform
        )
    except ClaudeUserScopeError as exc:
        raise InstallerError(str(exc)) from exc
    source_manifest, source_bytes = _user_source_manifest(
        snapshot,
        repository_root=repository_root,
        asm_user_data_root=asm,
        slugs=slugs,
    )
    previous_manifest, marker_digest = _read_user_manifest(asm)
    old_map = (
        {_user_artifact_key(item): item for item in previous_manifest.get("artifacts", [])}
        if previous_manifest
        else {}
    )
    forced_states = {
        str(skill_id): classify_claude_collision(state)
        for skill_id, state in (collision_states or {}).items()
    }
    artifacts: list[dict[str, Any]] = []
    collision_observations: list[dict[str, Any]] = []
    current_keys: set[tuple[str, str]] = set()
    for record in sorted(snapshot.records, key=lambda item: item["skill_id"]):
        skill_id = str(record["skill_id"])
        slug = slugs[skill_id]
        for root_class, root, destination in (
            (
                "ASM_USER_DATA",
                asm,
                Path(USER_ASM_SKILL_ROOT_RELATIVE) / slug / "SKILL.md",
            ),
            (
                "CLAUDE_PERSONAL",
                home,
                Path(USER_SKILL_ROOT_RELATIVE) / slug / "SKILL.md",
            ),
        ):
            destination_path = _relative_path(destination, label="USER destination")
            key = (root_class, destination_path)
            current_keys.add(key)
            marker_item = old_map.get(key)
            state, existing_digest = _inspect_user_destination(
                root,
                destination_path,
                root_class=root_class,
                marker_artifacts=old_map,
            )
            if root_class == "CLAUDE_PERSONAL" and skill_id in forced_states:
                state = forced_states[skill_id]
            elif root_class == "CLAUDE_PERSONAL":
                synced = _path_within(
                    home,
                    Path(USER_SKILL_ROOT_RELATIVE) / "synced" / slug,
                )
                if synced.is_symlink() or synced.exists():
                    # Synced skills are Claude-owned and are never adopted or
                    # overwritten by the ASM personal-skill package.
                    state = "CLAUDE_SYNCED"
                    existing_digest = None
            expected_digest = existing_digest
            if state == "ABSENT":
                action, origin = "CREATE", "CREATED_BY_ASM"
            elif state == "ASM_MANAGED":
                action = "NO_OP" if existing_digest == digest_bytes(source_bytes[skill_id]) else "UPDATE_MANAGED"
                origin = (
                    marker_item.get("origin", "UPDATED_ASM_MANAGED")
                    if action == "NO_OP" and marker_item
                    else "UPDATED_ASM_MANAGED"
                )
            else:
                action, origin = "CONFLICT", "CONFLICT"
            item = {
                "skill_id": skill_id,
                "source_path": _relative_path(
                    record["source"]["path"], label="canonical skill"
                ),
                "destination_path": destination_path,
                "destination_root": root_class,
                "kind": "CLAUDE_SKILL_BODY",
                "lifecycle": "INSTALL_PERSISTENT",
                "source_digest": record["source"]["digest"],
                "content_digest": digest_bytes(source_bytes[skill_id]),
                "expected_state": state,
                "expected_digest": expected_digest,
                "action": action,
                "origin": origin,
                "collision_state": state,
                "backup_path": None,
            }
            artifacts.append(item)
            if root_class == "CLAUDE_PERSONAL":
                collision_observations.append(
                    {
                        "skill_id": skill_id,
                        "destination_path": destination_path,
                        "state": state,
                    }
                )
    # Removal is explicit and never inferred as a rename.  Both the stable
    # ASM source and Claude personal copy are exact managed paths.
    for key, old_item in sorted(old_map.items()):
        if key in current_keys:
            continue
        root_class, destination_path = key
        root = asm if root_class == "ASM_USER_DATA" else home
        state, existing_digest = _inspect_user_destination(
            root,
            destination_path,
            root_class=root_class,
            marker_artifacts=old_map,
        )
        if state == "ASM_MANAGED" and existing_digest == old_item.get("content_digest"):
            action, origin = "REMOVE", "REMOVED_BY_ASM"
        else:
            action, origin = "CONFLICT", "CONFLICT"
        artifacts.append(
            {
                "skill_id": old_item["skill_id"],
                "source_path": old_item["source_path"],
                "destination_path": destination_path,
                "destination_root": root_class,
                "kind": old_item.get("kind", "CLAUDE_SKILL_BODY"),
                "lifecycle": old_item["lifecycle"],
                "source_digest": old_item["source_digest"],
                "content_digest": old_item["content_digest"],
                "expected_state": state,
                "expected_digest": existing_digest,
                "action": action,
                "origin": origin,
                "collision_state": state,
                "backup_path": None,
            }
        )
    artifacts.sort(key=lambda item: (item["destination_root"], item["destination_path"]))
    collision_observations.sort(key=lambda item: item["skill_id"])
    generated_manifest = {
        "schema_version": "3.0",
        "kind": "CLAUDE_USER_GENERATED_ARTIFACTS",
        "runtime_id": CLAUDE_RUNTIME_ID,
        "snapshot_digest": source_manifest["snapshot_digest"],
        "artifacts": [
            {
                field: item[field]
                for field in (
                    "skill_id",
                    "destination_root",
                    "destination_path",
                    "content_digest",
                    "source_digest",
                    "action",
                )
            }
            for item in artifacts
        ],
    }
    target_identity = _user_target_root_identity(home, asm)
    scope_reference = digest_value(
        {
            "scope": "USER",
            "home_root_identity": _root_identity(home, label="virtual HOME"),
            "asm_user_data_root_identity": _root_identity(
                asm, label="virtual ASM user-data root"
            ),
        }
    )
    conflicts = [
        item["destination_path"]
        for item in artifacts
        if item["action"] == "CONFLICT"
    ]
    warnings = [
        "USER apply is virtual-home-only in Phase 3N",
        "MANAGED_COPY is the only enabled Claude USER strategy; no silent fallback",
        "ASM user-data is derived and non-canonical",
        "CLAUDE_SYNCED and bundled collisions are blocked",
    ]
    if runtime_status.get("live_execution") != "VERIFIED":
        warnings.append(
            f"live execution is {runtime_status.get('live_execution', 'UNKNOWN')}; filesystem apply makes no inference claim"
        )
    plan_payload = {
        "plan_version": "3N-USER-1",
        "runtime_id": CLAUDE_RUNTIME_ID,
        "scope": "USER",
        "distribution_strategy": USER_SCOPE_STRATEGY,
        "snapshot_digest": source_manifest["snapshot_digest"],
        "target_digest": digest_value(target),
        "artifacts": artifacts,
    }
    package: dict[str, Any] = {
        "schema_version": "3.0",
        "package_version": INSTALLER_VERSION,
        "package_digest": "",
        "plan_digest": digest_value(plan_payload),
        "runtime_id": CLAUDE_RUNTIME_ID,
        "scope": "USER",
        "project_root_reference": _project_reference(None, "USER"),
        "project_root_digest": digest_value({"scope": "USER", "root": None}),
        "scope_root_reference": scope_reference,
        "scope_root_digest": target_identity,
        "target_root_identity": target_identity,
        "runtime_version": target["runtime_version"],
        "runtime_fingerprint": target["runtime_fingerprint"],
        "snapshot_digest": source_manifest["snapshot_digest"],
        "runtime_contract_digest": target["runtime_contract_digest"],
        "user_scope_contract_digest": target["user_scope_contract_digest"],
        "distribution_strategy": USER_SCOPE_STRATEGY,
        "install_target_digest": digest_value(target),
        "source_manifest_digest": digest_value(source_manifest),
        "generated_artifact_manifest_digest": digest_value(generated_manifest),
        "source_store_root_reference": digest_value(
            {
                "root_class": "ASM_USER_DATA",
                "identity": _root_identity(asm, label="virtual ASM user-data root"),
            }
        ),
        "source_store_manifest_digest": digest_value(source_manifest),
        "marker_digest": marker_digest,
        "marker_path": USER_MANIFEST_RELATIVE,
        "marker_root": "ASM_USER_DATA",
        "package_kind": "INSTALL",
        "revert_manifest_path": None,
        "revert_manifest_digest": None,
        "source_skill_ids": sorted(record["skill_id"] for record in snapshot.records),
        "collision_observations": collision_observations,
        "collision_observations_digest": digest_value(collision_observations),
        "transaction_policy": "USER_MANAGED_COPY_PROCESS_CRASH_RECOVERABLE",
        "confirmation_binding_digest": None,
        "confirmation_digest": None,
        "artifacts": artifacts,
        "excluded_artifacts": [],
        "installable": not conflicts,
        "apply_allowed": not conflicts,
        "warnings": sorted(set(warnings + [f"collision: {item}" for item in conflicts])),
    }
    return _finalize_user_package(package)


def _validate_user_package(package: dict[str, Any]) -> None:
    """Apply the cross-field USER package rules JSON Schema cannot express."""

    _validate_package(package)
    required = (
        "runtime_version",
        "runtime_fingerprint",
        "user_scope_contract_digest",
        "distribution_strategy",
        "scope_root_reference",
        "scope_root_digest",
        "target_root_identity",
        "source_store_root_reference",
        "source_store_manifest_digest",
        "generated_artifact_manifest_digest",
        "confirmation_binding_digest",
        "package_kind",
        "marker_root",
        "collision_observations",
        "collision_observations_digest",
        "transaction_policy",
        "source_skill_ids",
    )
    missing = [field for field in required if field not in package]
    if missing:
        raise InstallerError("USER InstallPackage lacks: " + ", ".join(missing))
    if package.get("scope") != "USER" or package.get("runtime_id") != CLAUDE_RUNTIME_ID:
        raise InstallerError("USER package is not bound to Claude Code")
    if package.get("runtime_version") != CLAUDE_RUNTIME_VERSION:
        raise InstallerError("USER package runtime version is stale")
    if package.get("distribution_strategy") != USER_SCOPE_STRATEGY:
        raise InstallerError("USER package strategy is not MANAGED_COPY")
    if package.get("package_kind") not in USER_PACKAGE_KINDS:
        raise InstallerError("USER package kind is unsupported")
    for field in (
        "runtime_fingerprint",
        "user_scope_contract_digest",
        "scope_root_reference",
        "scope_root_digest",
        "target_root_identity",
        "source_store_root_reference",
        "source_store_manifest_digest",
        "generated_artifact_manifest_digest",
        "confirmation_binding_digest",
        "collision_observations_digest",
    ):
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(package.get(field))):
            raise InstallerError(f"USER package has an invalid {field}")
    if package.get("marker_root") != "ASM_USER_DATA":
        raise InstallerError("USER package ownership state is not in ASM user data")
    if package.get("marker_path") != USER_MANIFEST_RELATIVE:
        raise InstallerError("USER package has an invalid ownership manifest path")
    observations = package.get("collision_observations")
    if package.get("collision_observations_digest") != digest_value(observations):
        raise InstallerError("USER package collision observations are stale")
    if package.get("confirmation_binding_digest") != _user_confirmation_binding(package):
        raise InstallerError("USER package confirmation binding is stale")
    if not isinstance(package.get("source_skill_ids"), list) or len(
        package["source_skill_ids"]
    ) != len(set(package["source_skill_ids"])):
        raise InstallerError("USER package source skill IDs are invalid")
    if package.get("source_store_manifest_digest") != package.get("source_manifest_digest"):
        raise InstallerError("USER package source manifest binding is stale")
    expected_skill_ids: set[str] = set()
    expected_observations: list[dict[str, str]] = []
    for item in package.get("artifacts", []):
        if item.get("destination_root") not in USER_ARTIFACT_ROOTS:
            raise InstallerError("USER package destination root is invalid")
        skill_id = item.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id:
            raise InstallerError("USER package artifact has no skill ID")
        _validate_user_skill_destination(
            item["destination_root"], item["destination_path"], skill_id=skill_id
        )
        _relative_path(item["source_path"], label="USER package source")
        expected_skill_ids.add(skill_id)
        if item.get("action") not in USER_MUTATION_ACTIONS:
            raise InstallerError("USER package action is invalid")
        if (
            item.get("action")
            in {"CREATE", "UPDATE_MANAGED", "NO_OP", "REMOVE", "RESTORE"}
            and item.get("collision_state") in USER_PROTECTED_COLLISIONS
        ):
            raise InstallerError("USER package contains a protected collision")
        if item.get("action") == "RESTORE" and not item.get("backup_path"):
            raise InstallerError("USER RESTORE action lacks a backup path")
        if item.get("backup_path") is not None:
            _validate_user_backup_path(item["backup_path"])
        if item.get("action") == "REMOVE" and item.get("expected_state") != "ASM_MANAGED":
            raise InstallerError("USER REMOVE action lacks exact managed state")
        if item.get("action") in {"CREATE", "UPDATE_MANAGED", "NO_OP"} and item.get(
            "destination_root"
        ) not in USER_ARTIFACT_ROOTS:
            raise InstallerError("USER mutation has no bounded root")
        if item.get("destination_root") == "CLAUDE_PERSONAL":
            expected_observations.append(
                {
                    "skill_id": skill_id,
                    "destination_path": item["destination_path"],
                    "state": item["expected_state"],
                }
            )
    if set(package["source_skill_ids"]) != expected_skill_ids:
        raise InstallerError("USER package source skill IDs do not match artifacts")
    expected_observations.sort(key=lambda item: (item["skill_id"], item["destination_path"]))
    if package.get("collision_observations") != expected_observations:
        raise InstallerError("USER package collision observations do not match artifacts")


def build_user_confirmation(
    package: dict[str, Any],
    *,
    home_root: str | Path,
    asm_user_data_root: str | Path,
) -> dict[str, Any]:
    """Create a deterministic confirmation object bound to one package."""

    _validate_user_package(package)
    home, asm = _safe_virtual_roots(home_root, asm_user_data_root)
    target_identity = _user_target_root_identity(home, asm)
    if target_identity != package.get("target_root_identity"):
        raise InstallerError("USER package target root identity changed")
    payload = {
        "schema_version": "3.0",
        "confirmation_version": "1.0",
        "package_digest": package["package_digest"],
        "runtime_id": package["runtime_id"],
        "scope": package["scope"],
        "strategy": package["distribution_strategy"],
        "target_root_identity": target_identity,
        "managed_path_count": len(package.get("artifacts", [])),
    }
    return {
        **payload,
        "confirmation_digest": digest_value(payload),
        "sensitive_data_serialized": False,
    }


def _validate_user_confirmation(
    package: dict[str, Any],
    confirmation: dict[str, Any] | None,
    *,
    home: Path,
    asm: Path,
) -> None:
    if not isinstance(confirmation, dict):
        raise InstallerError("USER_CONFIRMATION_REQUIRED")
    expected = build_user_confirmation(package, home_root=home, asm_user_data_root=asm)
    if confirmation != expected:
        raise InstallerError("USER confirmation does not bind the exact package")


def _user_root_for(
    root_class: str, *, home_root: Path, asm_user_data_root: Path
) -> Path:
    if root_class == "CLAUDE_PERSONAL":
        return home_root
    if root_class == "ASM_USER_DATA":
        return asm_user_data_root
    raise InstallerError(f"unknown USER artifact root: {root_class}")


def _qualified_user_path(root_class: str, relative: str) -> str:
    return _relative_path(Path(root_class) / Path(relative), label="USER journal path")


def _user_missing_parent_dirs(root: Path, relative: str) -> list[str]:
    safe = _relative_path(relative, label="USER destination")
    current = root
    missing: list[str] = []
    built: list[str] = []
    for part in Path(safe).parts[:-1]:
        current = current / part
        built.append(part)
        if current.is_symlink():
            raise InstallerError(f"USER destination parent is a symlink: {safe}")
        if current.exists():
            if not current.is_dir():
                raise InstallerError(f"USER destination parent is not a directory: {safe}")
        else:
            missing.append(Path(*built).as_posix())
    return missing


def _user_manifest_payload(
    package: dict[str, Any],
    *,
    transaction_id: str,
    backups: list[dict[str, Any]],
    previous_manifest_backup: dict[str, str] | None,
    created_directories: list[str],
) -> dict[str, Any] | None:
    if package.get("package_kind") in {"UNINSTALL", "REVERT"} and package.get(
        "revert_manifest_path"
    ) is None and package.get("package_kind") == "REVERT":
        return None
    if package.get("package_kind") == "UNINSTALL":
        return None
    artifacts = []
    for item in package.get("artifacts", []):
        if item["action"] == "REMOVE":
            continue
        origin = item["origin"]
        if item["action"] == "RESTORE":
            origin = "RESTORED_ASM_MANAGED"
        artifacts.append(
            {
                "skill_id": item["skill_id"],
                "destination_root": item["destination_root"],
                "destination_path": item["destination_path"],
                "source_path": item["source_path"],
                "source_digest": item["source_digest"],
                "content_digest": item["content_digest"],
                "lifecycle": item["lifecycle"],
                "origin": origin,
            }
        )
    manifest = {
        "schema_version": "3.0",
        "manifest_version": USER_SCOPE_TARGET_VERSION,
        "generator_id": INSTALLER_GENERATOR_ID,
        "managed": True,
        "manifest_path": USER_MANIFEST_RELATIVE,
        "runtime_id": package["runtime_id"],
        "scope": package["scope"],
        "distribution_strategy": package["distribution_strategy"],
        "runtime_version": package["runtime_version"],
        "runtime_fingerprint": package["runtime_fingerprint"],
        "package_digest": package["package_digest"],
        "transaction_id": transaction_id,
        "snapshot_digest": package["snapshot_digest"],
        "runtime_contract_digest": package["runtime_contract_digest"],
        "user_scope_contract_digest": package["user_scope_contract_digest"],
        "target_root_identity": package["target_root_identity"],
        "source_manifest_digest": package["source_manifest_digest"],
        "artifacts": sorted(
            artifacts,
            key=lambda item: (item["destination_root"], item["destination_path"]),
        ),
        "backups": sorted(
            copy.deepcopy(backups),
            key=lambda item: (item["destination_root"], item["destination_path"]),
        ),
        "previous_manifest_backup": previous_manifest_backup,
        "created_directories": sorted(set(created_directories)),
        "manifest_digest": "",
    }
    manifest["manifest_digest"] = _user_manifest_digest(manifest)
    return manifest


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    """Atomically replace one host-generated JSON record in a safe directory."""

    if path.is_symlink():
        raise InstallerError(f"refusing to replace symlink: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(_json_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise InstallerError(f"atomic JSON write failed: {type(exc).__name__}") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _user_journal_path(asm: Path, transaction_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", transaction_id):
        raise InstallerError("invalid USER transaction id")
    return _path_within(asm, Path(USER_TRANSACTION_RELATIVE) / f"{transaction_id}.json")


def _journal_digest(journal: dict[str, Any]) -> str:
    value = copy.deepcopy(journal)
    value["journal_digest"] = ""
    return digest_value(value)


def _validate_user_journal_semantics(journal: dict[str, Any]) -> None:
    """Validate journal invariants that JSON Schema cannot express."""

    if (
        journal.get("runtime_id") != CLAUDE_RUNTIME_ID
        or journal.get("scope") != "USER"
        or journal.get("strategy") != USER_SCOPE_STRATEGY
    ):
        raise InstallerError("RECOVERY_BLOCKED: journal runtime boundary is invalid")
    transaction_id = journal.get("transaction_id")
    if not isinstance(transaction_id, str):
        raise InstallerError("RECOVERY_BLOCKED: journal transaction id is invalid")
    operations = journal.get("operations")
    if not isinstance(operations, list):
        raise InstallerError("RECOVERY_BLOCKED: journal operation list is invalid")
    indexes = [item.get("index") for item in operations]
    if indexes != list(range(len(operations))):
        raise InstallerError("RECOVERY_BLOCKED: journal operation indexes are invalid")
    if journal.get("operations_digest") != digest_value(operations):
        raise InstallerError("RECOVERY_BLOCKED: operation digest mismatch")
    completed = journal.get("completed_operation_indexes")
    if not isinstance(completed, list) or any(
        index not in range(len(operations)) for index in completed
    ):
        raise InstallerError("RECOVERY_BLOCKED: completed operation index is invalid")
    active = journal.get("active_operation_index")
    if active is not None and (
        not isinstance(active, int)
        or active not in range(len(operations))
        or active in completed
    ):
        raise InstallerError("RECOVERY_BLOCKED: active operation index is invalid")
    destinations: set[tuple[str, str]] = set()
    for operation in operations:
        root_class = operation.get("destination_root")
        destination_path = operation.get("destination_path")
        key = (str(root_class), str(destination_path))
        if key in destinations:
            raise InstallerError("RECOVERY_BLOCKED: duplicate journal destination")
        destinations.add(key)
        if root_class not in USER_ARTIFACT_ROOTS:
            raise InstallerError("RECOVERY_BLOCKED: journal destination root is invalid")
        skill_id = operation.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id:
            raise InstallerError("RECOVERY_BLOCKED: journal skill ID is invalid")
        _validate_user_skill_destination(
            root_class, destination_path, skill_id=skill_id
        )
        action = operation.get("action")
        expected_state = operation.get("expected_state")
        expected_digest = operation.get("expected_digest")
        new_digest = operation.get("new_digest")
        stage_path = operation.get("stage_path")
        stage_digest = operation.get("stage_digest")
        backup_path = operation.get("backup_path")
        backup_digest = operation.get("backup_digest")
        needs_stage = action in {"CREATE", "UPDATE_MANAGED", "RESTORE"}
        needs_backup = action in {"UPDATE_MANAGED", "RESTORE", "REMOVE"}
        if action == "CREATE":
            if expected_state != "ABSENT" or expected_digest is not None:
                raise InstallerError("RECOVERY_BLOCKED: CREATE precondition is invalid")
        elif action in {"UPDATE_MANAGED", "RESTORE", "REMOVE"}:
            if expected_state != "ASM_MANAGED" or not isinstance(expected_digest, str):
                raise InstallerError("RECOVERY_BLOCKED: managed precondition is invalid")
        elif action == "NO_OP":
            if expected_state != "ASM_MANAGED" or not isinstance(new_digest, str):
                raise InstallerError("RECOVERY_BLOCKED: NO_OP precondition is invalid")
        else:
            raise InstallerError("RECOVERY_BLOCKED: journal action is invalid")
        if needs_stage:
            expected_stage = _relative_path(
                Path(USER_STAGING_RELATIVE)
                / transaction_id
                / "files"
                / f"{operation['index']}.bin",
                label="USER journal stage",
            )
            if stage_path != expected_stage or stage_digest != new_digest:
                raise InstallerError("RECOVERY_BLOCKED: journal stage binding is invalid")
        elif stage_path is not None or stage_digest is not None:
            raise InstallerError("RECOVERY_BLOCKED: unexpected journal stage reference")
        if needs_backup:
            expected_backup = _relative_path(
                Path(USER_BACKUP_RELATIVE)
                / transaction_id
                / f"artifact-{operation['index']}.bin",
                label="USER journal backup",
            )
            if backup_path != expected_backup or backup_digest != expected_digest:
                raise InstallerError("RECOVERY_BLOCKED: journal backup binding is invalid")
        elif backup_path is not None or backup_digest is not None:
            raise InstallerError("RECOVERY_BLOCKED: unexpected journal backup reference")
        if action == "REMOVE":
            if new_digest is not None:
                raise InstallerError("RECOVERY_BLOCKED: REMOVE has a new digest")
        elif not isinstance(new_digest, str) or new_digest != operation.get("content_digest"):
            raise InstallerError("RECOVERY_BLOCKED: replacement has no new digest")
        if not isinstance(operation.get("source_path"), str) or not isinstance(
            operation.get("source_digest"), str
        ):
            raise InstallerError("RECOVERY_BLOCKED: journal source binding is invalid")
        _relative_path(operation["source_path"], label="USER journal source")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", operation["source_digest"]):
            raise InstallerError("RECOVERY_BLOCKED: journal source digest is invalid")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", operation["content_digest"]):
            raise InstallerError("RECOVERY_BLOCKED: journal content digest is invalid")
    manifest_path = journal.get("manifest_path")
    if manifest_path != USER_MANIFEST_RELATIVE:
        raise InstallerError("RECOVERY_BLOCKED: journal manifest path is invalid")
    manifest_after = journal.get("manifest_after")
    manifest_after_digest = journal.get("manifest_after_digest")
    if manifest_after is None:
        if manifest_after_digest is not None:
            raise InstallerError("RECOVERY_BLOCKED: manifest-after binding is invalid")
    else:
        if set(manifest_after) != {"stage_path", "digest"}:
            raise InstallerError("RECOVERY_BLOCKED: manifest-after descriptor is invalid")
        expected_manifest_stage = _relative_path(
            Path(USER_STAGING_RELATIVE) / transaction_id / "ownership-manifest.json",
            label="USER journal manifest stage",
        )
        if manifest_after["stage_path"] != expected_manifest_stage:
            raise InstallerError("RECOVERY_BLOCKED: manifest stage path is invalid")
        if manifest_after["digest"] != manifest_after_digest:
            raise InstallerError("RECOVERY_BLOCKED: manifest-after digest is invalid")
    if journal.get("manifest_backup_path") is not None:
        expected_manifest_backup = _relative_path(
            Path(USER_BACKUP_RELATIVE) / transaction_id / "previous-manifest.json",
            label="USER journal manifest backup",
        )
        if journal["manifest_backup_path"] != expected_manifest_backup:
            raise InstallerError("RECOVERY_BLOCKED: manifest backup path is invalid")
        if not isinstance(journal.get("manifest_backup_digest"), str):
            raise InstallerError("RECOVERY_BLOCKED: manifest backup digest is invalid")
    elif journal.get("manifest_backup_digest") is not None:
        raise InstallerError("RECOVERY_BLOCKED: unexpected manifest backup digest")


def _write_user_journal(asm: Path, journal: dict[str, Any]) -> Path:
    path = _user_journal_path(asm, journal["transaction_id"])
    _ensure_no_symlink_parent(asm, Path(USER_TRANSACTION_RELATIVE) / path.name)
    journal["journal_digest"] = _journal_digest(journal)
    # The operation list is immutable for a transaction.  Re-validating its
    # large ``uniqueItems`` array on every per-operation MUTATING checkpoint
    # is quadratic and made the full-catalog virtual test needlessly slow.
    # The journal is fully schema-validated at PREPARED and terminal states;
    # recovery validates it again before trusting any persisted state.
    if journal.get("phase") != "MUTATING":
        errors = validate_instance("TransactionRecovery", journal).errors
        if errors:
            raise InstallerError("invalid USER transaction journal: " + "; ".join(errors))
        _validate_user_journal_semantics(journal)
    _write_json_atomic(path, journal)
    return path


def _read_user_journal(asm: Path, transaction_id: str) -> tuple[Path, dict[str, Any]]:
    path = _user_journal_path(asm, transaction_id)
    _ensure_no_symlink_parent(asm, Path(USER_TRANSACTION_RELATIVE) / path.name)
    if path.is_symlink() or not path.is_file():
        raise InstallerError("RECOVERY_BLOCKED: USER transaction journal is unavailable")
    journal = _read_json(path)
    errors = validate_instance("TransactionRecovery", journal).errors
    if errors:
        raise InstallerError("RECOVERY_BLOCKED: invalid USER transaction journal")
    _validate_user_journal_semantics(journal)
    if journal.get("journal_digest") != _journal_digest(journal):
        raise InstallerError("RECOVERY_BLOCKED: USER transaction journal digest mismatch")
    if journal.get("transaction_id") != transaction_id:
        raise InstallerError("RECOVERY_BLOCKED: transaction identity mismatch")
    if journal.get("operations_digest") != digest_value(journal.get("operations")):
        raise InstallerError("RECOVERY_BLOCKED: operation digest mismatch")
    return path, journal


def _claude_fixture_status() -> dict[str, Any]:
    inventory = load_runtime_inventory(fixture_name="ALL_KNOWN_STATIC")
    for status in inventory.get("runtimes", []):
        if status.get("runtime_id") == CLAUDE_RUNTIME_ID:
            return copy.deepcopy(status)
    raise InstallerError("Claude runtime status evidence is unavailable")


def _user_package_shell(
    *,
    home: Path,
    asm: Path,
    target: dict[str, Any],
    package_kind: str,
    artifacts: list[dict[str, Any]],
    marker_digest: str | None,
    snapshot_digest_value: str,
    source_manifest_digest: str,
    revert_manifest_path: str | None = None,
    revert_manifest_digest: str | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    artifacts = sorted(
        copy.deepcopy(artifacts),
        key=lambda item: (item["destination_root"], item["destination_path"]),
    )
    observations = [
        {
            "skill_id": item.get("skill_id", "unknown"),
            "destination_path": item["destination_path"],
            "state": item["expected_state"],
        }
        for item in artifacts
        if item.get("destination_root") == "CLAUDE_PERSONAL"
    ]
    observations.sort(key=lambda item: (item["skill_id"], item["destination_path"]))
    generated_manifest = {
        "schema_version": "3.0",
        "kind": "CLAUDE_USER_GENERATED_ARTIFACTS",
        "runtime_id": CLAUDE_RUNTIME_ID,
        "snapshot_digest": snapshot_digest_value,
        "artifacts": [
            {
                field: item[field]
                for field in (
                    "skill_id",
                    "destination_root",
                    "destination_path",
                    "content_digest",
                    "source_digest",
                    "action",
                )
            }
            for item in artifacts
        ],
    }
    target_identity = _user_target_root_identity(home, asm)
    scope_reference = digest_value(
        {
            "scope": "USER",
            "home_root_identity": _root_identity(home, label="virtual HOME"),
            "asm_user_data_root_identity": _root_identity(
                asm, label="virtual ASM user-data root"
            ),
        }
    )
    conflicts = [
        item["destination_path"]
        for item in artifacts
        if item["action"] in {"CONFLICT", "SKIP_USER_OWNED"}
    ]
    package_warnings = list(warnings or [])
    if conflicts:
        package_warnings.extend(f"conflict: {item}" for item in conflicts)
    status = _claude_fixture_status()
    if status.get("live_execution") != "VERIFIED":
        package_warnings.append(
            f"live execution is {status.get('live_execution', 'UNKNOWN')}; USER filesystem lifecycle is independent"
        )
    plan_payload = {
        "plan_version": "3N-USER-1",
        "runtime_id": CLAUDE_RUNTIME_ID,
        "scope": "USER",
        "package_kind": package_kind,
        "distribution_strategy": USER_SCOPE_STRATEGY,
        "snapshot_digest": snapshot_digest_value,
        "target_digest": digest_value(target),
        "artifacts": artifacts,
    }
    package: dict[str, Any] = {
        "schema_version": "3.0",
        "package_version": INSTALLER_VERSION,
        "package_digest": "",
        "plan_digest": digest_value(plan_payload),
        "runtime_id": CLAUDE_RUNTIME_ID,
        "scope": "USER",
        "project_root_reference": _project_reference(None, "USER"),
        "project_root_digest": digest_value({"scope": "USER", "root": None}),
        "scope_root_reference": scope_reference,
        "scope_root_digest": target_identity,
        "target_root_identity": target_identity,
        "runtime_version": target["runtime_version"],
        "runtime_fingerprint": target["runtime_fingerprint"],
        "snapshot_digest": snapshot_digest_value,
        "runtime_contract_digest": target["runtime_contract_digest"],
        "user_scope_contract_digest": target["user_scope_contract_digest"],
        "distribution_strategy": USER_SCOPE_STRATEGY,
        "install_target_digest": digest_value(target),
        "source_manifest_digest": source_manifest_digest,
        "generated_artifact_manifest_digest": digest_value(generated_manifest),
        "source_store_root_reference": digest_value(
            {
                "root_class": "ASM_USER_DATA",
                "identity": _root_identity(asm, label="virtual ASM user-data root"),
            }
        ),
        "source_store_manifest_digest": source_manifest_digest,
        "marker_digest": marker_digest,
        "marker_path": USER_MANIFEST_RELATIVE,
        "marker_root": "ASM_USER_DATA",
        "package_kind": package_kind,
        "revert_manifest_path": revert_manifest_path,
        "revert_manifest_digest": revert_manifest_digest,
        "source_skill_ids": sorted(
            {str(item.get("skill_id")) for item in artifacts if item.get("skill_id")}
        ),
        "collision_observations": observations,
        "collision_observations_digest": digest_value(observations),
        "transaction_policy": "USER_MANAGED_COPY_PROCESS_CRASH_RECOVERABLE",
        "confirmation_binding_digest": None,
        "confirmation_digest": None,
        "artifacts": artifacts,
        "excluded_artifacts": [],
        "installable": not conflicts,
        "apply_allowed": not conflicts,
        "warnings": sorted(set(package_warnings)),
    }
    return _finalize_user_package(package)


def build_user_uninstall_package(
    *,
    home_root: str | Path,
    asm_user_data_root: str | Path,
) -> dict[str, Any]:
    """Build an exact-path USER uninstall package from the ASM manifest."""

    home, asm = _safe_virtual_roots(home_root, asm_user_data_root)
    manifest, marker_digest = _read_user_manifest(asm)
    if manifest is None:
        raise InstallerError("no ASM USER ownership manifest exists")
    target = build_claude_user_target(_claude_fixture_status())
    marker_map = {_user_artifact_key(item): item for item in manifest["artifacts"]}
    artifacts: list[dict[str, Any]] = []
    for item in manifest["artifacts"]:
        root = _user_root_for(
            item["destination_root"], home_root=home, asm_user_data_root=asm
        )
        state, digest = _inspect_user_destination(
            root,
            item["destination_path"],
            root_class=item["destination_root"],
            marker_artifacts=marker_map,
        )
        action = (
            "REMOVE"
            if state == "ASM_MANAGED"
            and digest == item["content_digest"]
            and item["origin"] == "CREATED_BY_ASM"
            else "CONFLICT"
        )
        artifacts.append(
            {
                "skill_id": item["skill_id"],
                "source_path": item["source_path"],
                "destination_path": item["destination_path"],
                "destination_root": item["destination_root"],
                "kind": "CLAUDE_SKILL_BODY",
                "lifecycle": item["lifecycle"],
                "source_digest": item["source_digest"],
                "content_digest": item["content_digest"],
                "expected_state": state,
                "expected_digest": digest,
                "action": action,
                "origin": "REMOVED_BY_ASM" if action == "REMOVE" else "CONFLICT",
                "collision_state": state,
                "backup_path": None,
            }
        )
    return _user_package_shell(
        home=home,
        asm=asm,
        target=target,
        package_kind="UNINSTALL",
        artifacts=artifacts,
        marker_digest=marker_digest,
        snapshot_digest_value=manifest["snapshot_digest"],
        source_manifest_digest=manifest["source_manifest_digest"],
        warnings=[
            "uninstall uses only exact ASM-owned paths and does not require Claude executable/provider access"
        ],
    )


def _read_previous_user_manifest(
    asm: Path, manifest: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    previous = manifest.get("previous_manifest_backup")
    if previous is None:
        return None, None
    path = _path_within(asm, previous["path"])
    _ensure_no_symlink_parent(asm, previous["path"])
    if path.is_symlink() or not path.is_file():
        raise InstallerError("REVERT_UNAVAILABLE: previous USER manifest backup is missing")
    raw = path.read_bytes()
    if digest_bytes(raw) != previous["digest"]:
        raise InstallerError("REVERT_UNAVAILABLE: previous USER manifest backup is tampered")
    value = _read_json(path)
    _validate_user_manifest(value)
    return value, previous["digest"]


def build_user_revert_package(
    *,
    home_root: str | Path,
    asm_user_data_root: str | Path,
    transaction_id: str,
) -> dict[str, Any]:
    """Build a revert package from exact previous ASM-managed evidence."""

    home, asm = _safe_virtual_roots(home_root, asm_user_data_root)
    manifest, marker_digest = _read_user_manifest(asm)
    if manifest is None or manifest.get("transaction_id") != transaction_id:
        raise InstallerError(
            "REVERT_UNAVAILABLE: requested transaction is not the current USER transaction"
        )
    target = build_claude_user_target(_claude_fixture_status())
    marker_map = {_user_artifact_key(item): item for item in manifest["artifacts"]}
    previous, previous_digest = _read_previous_user_manifest(asm, manifest)
    previous_map = (
        {_user_artifact_key(item): item for item in previous["artifacts"]}
        if previous
        else {}
    )
    backup_map = {
        (item["destination_root"], item["destination_path"]): item
        for item in manifest.get("backups", [])
    }
    artifacts: list[dict[str, Any]] = []
    for item in manifest["artifacts"]:
        root = _user_root_for(
            item["destination_root"], home_root=home, asm_user_data_root=asm
        )
        state, digest = _inspect_user_destination(
            root,
            item["destination_path"],
            root_class=item["destination_root"],
            marker_artifacts=marker_map,
        )
        base = {
            "skill_id": item["skill_id"],
            "source_path": item["source_path"],
            "destination_path": item["destination_path"],
            "destination_root": item["destination_root"],
            "kind": "CLAUDE_SKILL_BODY",
            "lifecycle": item["lifecycle"],
            "source_digest": item["source_digest"],
            "content_digest": item["content_digest"],
            "expected_state": state,
            "expected_digest": digest,
            "action": "CONFLICT",
            "origin": "CONFLICT",
            "collision_state": state,
            "backup_path": None,
        }
        key = _user_artifact_key(item)
        if state == "ASM_MANAGED" and digest == item["content_digest"]:
            if key in previous_map:
                previous_item = previous_map[key]
                previous_content = previous_item["content_digest"]
                if previous_content == item["content_digest"]:
                    base.update(
                        content_digest=item["content_digest"],
                        source_digest=item["source_digest"],
                        source_path=item["source_path"],
                        action="NO_OP",
                        origin="NO_OP",
                    )
                else:
                    backup = backup_map.get(key)
                    if backup is not None:
                        base.update(
                            content_digest=previous_content,
                            source_digest=previous_item["source_digest"],
                            source_path=previous_item["source_path"],
                            action="RESTORE",
                            origin="RESTORED_ASM_MANAGED",
                            backup_path=backup["backup_path"],
                        )
            else:
                base.update(action="REMOVE", origin="REMOVED_BY_ASM")
        artifacts.append(base)
    warnings = [
        "revert restores only exact ASM backups; it never reconstructs content from the canonical repository",
    ]
    if any(item["action"] == "CONFLICT" for item in artifacts):
        warnings.append("REVERT_UNAVAILABLE: exact previous content or ownership evidence is missing")
    return _user_package_shell(
        home=home,
        asm=asm,
        target=target,
        package_kind="REVERT",
        artifacts=artifacts,
        marker_digest=marker_digest,
        snapshot_digest_value=manifest["snapshot_digest"],
        source_manifest_digest=manifest["source_manifest_digest"],
        revert_manifest_path=manifest.get("previous_manifest_backup", {}).get("path")
        if manifest.get("previous_manifest_backup")
        else None,
        revert_manifest_digest=previous_digest,
        warnings=warnings,
    )


def _user_source_for_artifact(
    artifact: dict[str, Any], *, repository_root: str | Path, asm: Path
) -> bytes:
    if artifact.get("action") == "RESTORE":
        backup_path = artifact.get("backup_path")
        if not isinstance(backup_path, str):
            raise InstallerError("USER RESTORE source is missing its backup path")
        source = _path_within(asm, backup_path)
        _ensure_no_symlink_parent(asm, backup_path)
        if source.is_symlink() or not source.is_file():
            raise InstallerError("REVERT_UNAVAILABLE: restore backup is missing")
        raw = source.read_bytes()
        if digest_bytes(raw) != artifact.get("content_digest"):
            raise InstallerError("REVERT_UNAVAILABLE: restore backup digest mismatch")
        return raw
    source_record = {
        "skill_id": artifact.get("skill_id"),
        "source": {
            "path": artifact.get("source_path"),
            "digest": artifact.get("source_digest"),
        },
    }
    slug = Path(artifact["destination_path"]).parent.name
    raw, _ = _canonical_user_source(
        source_record,
        repository_root=repository_root,
        asm_user_data_root=asm,
        slug=slug,
    )
    if digest_bytes(raw) != artifact.get("content_digest"):
        raise InstallerError(
            f"STALE_PACKAGE: source artifact changed: {artifact.get('source_path')}"
        )
    return raw


def _user_revalidate_package(
    package: dict[str, Any],
    *,
    home: Path,
    asm: Path,
    repository_root: str | Path,
) -> tuple[dict[str, Any] | None, str | None, dict[str, bytes]]:
    """Revalidate every mutation-sensitive USER input immediately before apply."""

    _validate_user_package(package)
    target = build_claude_user_target(_claude_fixture_status())
    if package.get("install_target_digest") != digest_value(target):
        raise InstallerError("STALE_PACKAGE: Claude USER target contract changed")
    if package.get("runtime_contract_digest") != target.get("runtime_contract_digest"):
        raise InstallerError("RUNTIME_REQUALIFICATION_REQUIRED")
    if package.get("runtime_fingerprint") != target.get("runtime_fingerprint"):
        raise InstallerError("RUNTIME_REQUALIFICATION_REQUIRED")
    if package.get("user_scope_contract_digest") != target.get(
        "user_scope_contract_digest"
    ):
        raise InstallerError("STALE_PACKAGE: Claude USER contract changed")
    target_identity = _user_target_root_identity(home, asm)
    if package.get("target_root_identity") != target_identity:
        raise InstallerError("STALE_PACKAGE: virtual HOME identity changed")
    if package.get("scope_root_digest") != target_identity:
        raise InstallerError("STALE_PACKAGE: USER scope root changed")
    expected_source_root = digest_value(
        {
            "root_class": "ASM_USER_DATA",
            "identity": _root_identity(asm, label="virtual ASM user-data root"),
        }
    )
    if package.get("source_store_root_reference") != expected_source_root:
        raise InstallerError("STALE_PACKAGE: ASM user-data root changed")
    manifest, marker_digest = _read_user_manifest(asm)
    already_applied = bool(
        manifest is not None
        and manifest.get("package_digest") == package.get("package_digest")
        and package.get("package_kind") == "INSTALL"
    )
    if already_applied and manifest is not None:
        for field in (
            "package_digest",
            "snapshot_digest",
            "runtime_contract_digest",
            "user_scope_contract_digest",
            "target_root_identity",
            "source_manifest_digest",
            "runtime_version",
            "runtime_fingerprint",
            "distribution_strategy",
        ):
            if manifest.get(field) != package.get(field):
                raise InstallerError(f"STALE_PACKAGE: USER ownership field changed: {field}")
        manifest_map = {
            _user_artifact_key(item): item for item in manifest.get("artifacts", [])
        }
        expected_manifest_map = {
            _user_artifact_key(item): item
            for item in package.get("artifacts", [])
            if item.get("action") != "REMOVE"
        }
        if set(manifest_map) != set(expected_manifest_map):
            raise InstallerError("STALE_PACKAGE: USER ownership artifact set changed")
        for key, expected in expected_manifest_map.items():
            actual = manifest_map[key]
            for field in (
                "skill_id",
                "source_path",
                "source_digest",
                "content_digest",
                "lifecycle",
            ):
                if actual.get(field) != expected.get(field):
                    raise InstallerError(
                        f"STALE_PACKAGE: USER ownership artifact changed: {key[1]}"
                    )
    if marker_digest != package.get("marker_digest") and not already_applied:
        raise InstallerError("STALE_PACKAGE: USER ownership manifest changed")
    if manifest is not None and manifest.get("target_root_identity") != target_identity:
        raise InstallerError("STALE_PACKAGE: USER ownership target changed")
    if package.get("package_kind") == "REVERT":
        revert_path = package.get("revert_manifest_path")
        if revert_path is None:
            if package.get("revert_manifest_digest") is not None:
                raise InstallerError("STALE_PACKAGE: revert manifest binding is invalid")
        else:
            if package.get("revert_manifest_digest") is None:
                raise InstallerError("STALE_PACKAGE: revert manifest digest is missing")
            path = _path_within(asm, revert_path)
            _ensure_no_symlink_parent(asm, revert_path)
            if path.is_symlink() or not path.is_file():
                raise InstallerError("REVERT_UNAVAILABLE: previous manifest is missing")
            if digest_bytes(path.read_bytes()) != package["revert_manifest_digest"]:
                raise InstallerError("STALE_PACKAGE: previous manifest changed")
            previous = _read_json(path)
            _validate_user_manifest(previous)
    old_map = (
        {_user_artifact_key(item): item for item in manifest.get("artifacts", [])}
        if manifest
        else {}
    )
    observations = []
    sources: dict[str, bytes] = {}
    for artifact in package.get("artifacts", []):
        root = _user_root_for(
            artifact["destination_root"], home_root=home, asm_user_data_root=asm
        )
        state, current_digest = _inspect_user_destination(
            root,
            artifact["destination_path"],
            root_class=artifact["destination_root"],
            marker_artifacts=old_map,
        )
        if already_applied:
            replay_ok = (
                artifact["action"] == "REMOVE"
                and state == "ABSENT"
                and current_digest is None
            ) or (
                artifact["action"] in {"CREATE", "UPDATE_MANAGED", "RESTORE", "NO_OP"}
                and state == "ASM_MANAGED"
                and current_digest == artifact.get("content_digest")
            )
            if not replay_ok:
                raise InstallerError(
                    f"STALE_PACKAGE: completed USER package path changed: {artifact['destination_path']}"
                )
        elif state != artifact.get("expected_state") or current_digest != artifact.get(
            "expected_digest"
        ):
            raise InstallerError(
                f"STALE_PACKAGE: destination changed: {artifact['destination_path']}"
            )
        if artifact["destination_root"] == "CLAUDE_PERSONAL":
            slug = Path(artifact["destination_path"]).parts[-2]
            synced = _path_within(
                home,
                Path(USER_SKILL_ROOT_RELATIVE) / "synced" / slug,
            )
            if synced.is_symlink() or synced.exists():
                state, current_digest = "CLAUDE_SYNCED", None
            observations.append(
                {
                    "skill_id": artifact.get("skill_id", "unknown"),
                    "destination_path": artifact["destination_path"],
                    "state": state,
                }
            )
        if artifact["action"] in {"CREATE", "UPDATE_MANAGED"}:
            try:
                source = _user_source_for_artifact(
                    artifact, repository_root=repository_root, asm=asm
                )
            except InstallerError as exc:
                if "canonical skill digest changed" in str(exc):
                    raise InstallerError(
                        f"STALE_PACKAGE: source artifact changed: {artifact['source_path']}"
                    ) from exc
                raise
            sources.setdefault(str(artifact["skill_id"]), source)
        elif artifact["action"] == "RESTORE":
            # RESTORE sources are per destination even when two roots share a
            # skill ID, because each previous byte stream is independently
            # backed up and bound.
            sources[
                f"restore:{artifact['destination_root']}:{artifact['destination_path']}"
            ] = _user_source_for_artifact(
                artifact, repository_root=repository_root, asm=asm
            )
        elif artifact["action"] in {"CONFLICT", "SKIP_USER_OWNED"}:
            raise InstallerError("USER package contains an unresolved collision")
        if artifact.get("action") == "RESTORE":
            backup_path = artifact.get("backup_path")
            if not isinstance(backup_path, str):
                raise InstallerError("REVERT_UNAVAILABLE: backup path is absent")
            _relative_path(backup_path, label="USER restore backup")
    observations.sort(key=lambda item: (item["skill_id"], item["destination_path"]))
    if not already_applied and observations != package.get("collision_observations"):
        raise InstallerError("STALE_PACKAGE: collision observations changed")
    return manifest, marker_digest, sources


def _user_manifest_after(
    package: dict[str, Any],
    *,
    transaction_id: str,
    backups: list[dict[str, Any]],
    previous_manifest_backup: dict[str, str] | None,
    created_directories: list[str],
    asm: Path,
) -> dict[str, Any] | None:
    if package.get("package_kind") == "REVERT":
        path = package.get("revert_manifest_path")
        if path is None:
            return None
        _ensure_no_symlink_parent(asm, path)
        target = _path_within(asm, path)
        if target.is_symlink() or not target.is_file():
            raise InstallerError("REVERT_UNAVAILABLE: previous manifest is missing")
        raw = target.read_bytes()
        if digest_bytes(raw) != package.get("revert_manifest_digest"):
            raise InstallerError("REVERT_UNAVAILABLE: previous manifest changed")
        value = _read_json(target)
        _validate_user_manifest(value)
        return value
    return _user_manifest_payload(
        package,
        transaction_id=transaction_id,
        backups=backups,
        previous_manifest_backup=previous_manifest_backup,
        created_directories=created_directories,
    )


def _user_journal_operation(
    artifact: dict[str, Any],
    *,
    index: int,
    transaction_id: str,
) -> dict[str, Any]:
    action = artifact["action"]
    needs_backup = action in {"UPDATE_MANAGED", "RESTORE", "REMOVE"}
    stage_path = (
        _relative_path(
            Path(USER_STAGING_RELATIVE)
            / transaction_id
            / "files"
            / f"{index}.bin",
            label="USER stage path",
        )
        if action in {"CREATE", "UPDATE_MANAGED", "RESTORE"}
        else None
    )
    backup_path = (
        _relative_path(
            Path(USER_BACKUP_RELATIVE) / transaction_id / f"artifact-{index}.bin",
            label="USER backup path",
        )
        if needs_backup
        else None
    )
    return {
        "index": index,
        "skill_id": artifact["skill_id"],
        "destination_root": artifact["destination_root"],
        "destination_path": artifact["destination_path"],
        "action": action,
        "expected_state": artifact["expected_state"],
        "expected_digest": artifact["expected_digest"],
        "new_digest": artifact["content_digest"] if action != "REMOVE" else None,
        "stage_path": stage_path,
        "stage_digest": artifact["content_digest"] if stage_path else None,
        "backup_path": backup_path,
        "backup_digest": artifact["expected_digest"] if needs_backup else None,
        "source_path": artifact["source_path"],
        "source_digest": artifact["source_digest"],
        "content_digest": artifact["content_digest"],
    }


def _user_created_directory_predictions(
    package: dict[str, Any], *, home: Path, asm: Path
) -> list[str]:
    result: list[str] = []
    for item in package.get("artifacts", []):
        if item["action"] == "NO_OP":
            continue
        root = _user_root_for(
            item["destination_root"], home_root=home, asm_user_data_root=asm
        )
        for relative in _user_missing_parent_dirs(root, item["destination_path"]):
            result.append(_qualified_user_path(item["destination_root"], relative))
    return sorted(set(result))


def _user_journal_record(
    *,
    package: dict[str, Any],
    transaction_id: str,
    operations: list[dict[str, Any]],
    manifest_after: dict[str, Any] | None,
    manifest_before_digest: str | None,
    manifest_backup_path: str | None,
    manifest_backup_digest: str | None,
    created_directories: list[str],
    phase: str,
    completed: list[int],
    home: Path,
    asm: Path,
) -> dict[str, Any]:
    return {
        "schema_version": "3.0",
        "journal_version": "1.0",
        "journal_digest": "",
        "transaction_id": transaction_id,
        "package_digest": package["package_digest"],
        "runtime_id": package["runtime_id"],
        "scope": "USER",
        "strategy": package["distribution_strategy"],
        "home_root_identity": _root_identity(home, label="virtual HOME"),
        "asm_user_data_root_identity": _root_identity(
            asm, label="virtual ASM user-data root"
        ),
        "target_root_identity": package["target_root_identity"],
        "operations_digest": digest_value(operations),
        "operations": operations,
        "phase": phase,
        "active_operation_index": None,
        "completed_operation_indexes": sorted(set(completed)),
        "manifest_path": USER_MANIFEST_RELATIVE,
        "manifest_before_digest": manifest_before_digest,
        "manifest_after_digest": manifest_after.get("digest")
        if manifest_after is not None
        else None,
        "manifest_after": manifest_after,
        "manifest_backup_path": manifest_backup_path,
        "manifest_backup_digest": manifest_backup_digest,
        "created_directories": sorted(set(created_directories)),
        "sensitive_data_serialized": False,
    }


def _user_atomic_restore(path: Path, payload: bytes) -> None:
    """Restore exact bytes through a same-directory atomic replacement."""

    if path.is_symlink():
        raise InstallerError("refusing to restore through a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".rollback", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise InstallerError(f"bounded restore failed: {type(exc).__name__}") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _user_cleanup_stage(asm: Path, transaction_id: str) -> None:
    stage = _path_within(asm, Path(USER_STAGING_RELATIVE) / transaction_id)
    if stage.is_symlink():
        raise InstallerError("USER staging directory is a symlink")
    if stage.exists():
        if not stage.is_dir():
            raise InstallerError("USER staging path is not a directory")
        shutil.rmtree(stage)


def _user_verify_transaction(
    journal: dict[str, Any], *, home: Path, asm: Path
) -> None:
    for operation in journal["operations"]:
        root = _user_root_for(
            operation["destination_root"], home_root=home, asm_user_data_root=asm
        )
        destination = _path_within(root, operation["destination_path"])
        _ensure_no_symlink_parent(root, operation["destination_path"])
        action = operation["action"]
        if action == "REMOVE":
            if destination.exists() or destination.is_symlink():
                raise InstallerError(
                    f"USER removal verification failed: {operation['destination_path']}"
                )
            continue
        if action in {"CREATE", "UPDATE_MANAGED", "RESTORE", "NO_OP"}:
            if destination.is_symlink() or not destination.is_file():
                raise InstallerError(
                    f"USER digest verification failed: {operation['destination_path']}"
                )
            if digest_bytes(destination.read_bytes()) != operation["new_digest"]:
                raise InstallerError(
                    f"USER digest verification failed: {operation['destination_path']}"
                )
        else:
            raise InstallerError("USER journal contains an unresolved action")
    manifest_path = _path_within(asm, journal["manifest_path"])
    _ensure_no_symlink_parent(asm, journal["manifest_path"])
    if journal["manifest_after"] is None:
        if manifest_path.exists() or manifest_path.is_symlink():
            raise InstallerError("USER ownership manifest removal verification failed")
    else:
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise InstallerError("USER ownership manifest verification failed")
        raw = manifest_path.read_bytes()
        if digest_bytes(raw) != journal["manifest_after_digest"]:
            raise InstallerError("USER ownership manifest digest verification failed")
        value = _read_json(manifest_path)
        _validate_user_manifest(value)


def _user_restore_backup(
    asm: Path, operation: dict[str, Any], destination: Path
) -> None:
    backup_path = operation.get("backup_path")
    if not isinstance(backup_path, str):
        raise InstallerError("rollback backup reference is missing")
    backup = _path_within(asm, backup_path)
    _ensure_no_symlink_parent(asm, backup_path)
    if backup.is_symlink() or not backup.is_file():
        raise InstallerError("rollback backup is missing")
    raw = backup.read_bytes()
    if digest_bytes(raw) != operation.get("backup_digest"):
        raise InstallerError("rollback backup digest mismatch")
    _user_atomic_restore(destination, raw)


def _user_rollback_journal(
    journal: dict[str, Any], *, home: Path, asm: Path
) -> None:
    """Rollback only journaled exact operations; raise on ambiguity."""

    completed = set(journal.get("completed_operation_indexes", []))
    active_index = journal.get("active_operation_index")
    rollback_indexes = set(completed)
    if active_index is not None and active_index not in rollback_indexes:
        rollback_indexes.add(active_index)
    for operation in sorted(
        (item for item in journal["operations"] if item["index"] in rollback_indexes),
        key=lambda item: item["index"],
        reverse=True,
    ):
        root = _user_root_for(
            operation["destination_root"], home_root=home, asm_user_data_root=asm
        )
        destination = _path_within(root, operation["destination_path"])
        _ensure_no_symlink_parent(root, operation["destination_path"])
        action = operation["action"]
        is_active = operation["index"] == active_index and operation["index"] not in completed
        if action == "CREATE":
            if not destination.exists() and not destination.is_symlink():
                continue
            if destination.is_symlink() or not destination.is_file():
                raise InstallerError("rollback found an unknown created path")
            if digest_bytes(destination.read_bytes()) != operation["new_digest"]:
                raise InstallerError("rollback found a modified created path")
            _safe_unlink(destination, expected_digest=operation["new_digest"])
        elif action in {"UPDATE_MANAGED", "RESTORE", "REMOVE"}:
            if action == "REMOVE":
                if not destination.exists() and not destination.is_symlink():
                    _user_restore_backup(asm, operation, destination)
                elif destination.is_symlink() or not destination.is_file():
                    raise InstallerError("rollback found a changed removed path")
                elif digest_bytes(destination.read_bytes()) != operation["expected_digest"]:
                    raise InstallerError("rollback found a changed removed path")
                else:
                    continue
            else:
                if not destination.exists() and not destination.is_symlink():
                    if is_active:
                        continue
                    raise InstallerError("rollback found a missing replaced path")
                if destination.is_symlink() or not destination.is_file():
                    raise InstallerError("rollback found a missing replaced path")
                current_digest = digest_bytes(destination.read_bytes())
                if current_digest == operation["expected_digest"] and is_active:
                    continue
                if current_digest != operation["new_digest"]:
                    raise InstallerError("rollback found a modified replaced path")
                _user_restore_backup(asm, operation, destination)
                continue
        elif action == "NO_OP":
            continue
        else:
            raise InstallerError("rollback contains an unknown action")
    manifest_path = _path_within(asm, journal["manifest_path"])
    _ensure_no_symlink_parent(asm, journal["manifest_path"])
    if journal.get("manifest_backup_path"):
        backup_path = journal["manifest_backup_path"]
        backup = _path_within(asm, backup_path)
        if backup.is_symlink() or not backup.is_file():
            raise InstallerError("rollback manifest backup is missing")
        raw = backup.read_bytes()
        if digest_bytes(raw) != journal.get("manifest_backup_digest"):
            raise InstallerError("rollback manifest backup digest mismatch")
        if manifest_path.is_symlink() or (
            manifest_path.exists() and not manifest_path.is_file()
        ):
            raise InstallerError("rollback found an unsafe ownership manifest")
        current_digest = (
            digest_bytes(manifest_path.read_bytes())
            if manifest_path.is_file()
            else None
        )
        before_digest = journal.get("manifest_before_digest")
        after_digest = journal.get("manifest_after_digest")
        if current_digest == before_digest:
            pass
        elif after_digest is not None and current_digest == after_digest:
            _user_atomic_restore(manifest_path, raw)
        elif after_digest is None and current_digest is None:
            pass
        else:
            raise InstallerError("rollback found a modified ownership manifest")
    elif journal.get("manifest_before_digest") is None:
        if manifest_path.exists() or manifest_path.is_symlink():
            if journal.get("manifest_after_digest") is not None:
                raw = manifest_path.read_bytes()
                if digest_bytes(raw) != journal["manifest_after_digest"]:
                    raise InstallerError("rollback found an unknown ownership manifest")
            _safe_unlink(manifest_path)
    _user_cleanup_stage(asm, journal["transaction_id"])


def _user_write_backup(
    asm: Path,
    *,
    stage_dir: Path,
    backup_path: str,
    payload: bytes,
    index: int,
) -> None:
    backup = _path_within(asm, backup_path)
    _ensure_no_symlink_parent(asm, backup_path)
    if backup.exists() or backup.is_symlink():
        raise InstallerError("USER backup path collision")
    staged = _write_staged(stage_dir, f"backups/{index}.bin", payload)
    backup.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staged, backup)


def _user_mutation_boundary(
    interrupt_at: str | None,
    boundary: str,
    transaction_id: str,
    interrupted: list[bool],
) -> None:
    if interrupt_at == boundary and not interrupted[0]:
        interrupted[0] = True
        raise UserTransactionInterrupted(transaction_id, boundary)


def apply_user_install_package(
    package: dict[str, Any],
    *,
    home_root: str | Path | None,
    asm_user_data_root: str | Path | None,
    repository_root: str | Path = ROOT,
    confirmation: dict[str, Any] | None = None,
    interrupt_at: str | None = None,
    replace_fn: Callable[
        [str | os.PathLike[str], str | os.PathLike[str]], None
    ] = os.replace,
) -> dict[str, Any]:
    """Apply a confirmed Claude USER package under an explicit virtual HOME."""

    home, asm = _safe_virtual_roots(home_root, asm_user_data_root)
    _validate_user_package(package)
    _validate_user_confirmation(package, confirmation, home=home, asm=asm)
    manifest, marker_digest, source_cache = _user_revalidate_package(
        package,
        home=home,
        asm=asm,
        repository_root=repository_root,
    )
    already_applied = bool(
        manifest is not None
        and manifest.get("package_digest") == package.get("package_digest")
        and package.get("package_kind") == "INSTALL"
    )
    execution_artifacts = copy.deepcopy(package.get("artifacts", []))
    if already_applied:
        for item in execution_artifacts:
            if item["action"] != "REMOVE":
                item["action"] = "NO_OP"
                item["expected_state"] = "ASM_MANAGED"
                item["expected_digest"] = item["content_digest"]
    attempted = [
        _qualified_user_path(item["destination_root"], item["destination_path"])
        for item in package.get("artifacts", [])
    ]
    conflicts = [
        item["destination_path"]
        for item in package.get("artifacts", [])
        if item["action"] in {"CONFLICT", "SKIP_USER_OWNED"}
    ]
    if conflicts or not package.get("apply_allowed"):
        return _result(
            package=package,
            status="CONFLICT" if conflicts else "ABORTED",
            transaction_id="aborted-" + package["package_digest"][7:19],
            attempted=attempted,
            warnings=package.get("warnings", [])
            + ["USER package precondition is false; no filesystem mutation occurred"],
            conflicts=conflicts,
        )
    if any(item["action"] not in USER_MUTATION_ACTIONS for item in package["artifacts"]):
        raise InstallerError("USER package contains a non-installable action")
    transaction_id = _new_transaction_id()
    _user_journal_path(asm, transaction_id).parent.mkdir(parents=True, exist_ok=True)
    stage_dir = _path_within(asm, Path(USER_STAGING_RELATIVE) / transaction_id)
    operations = [
        _user_journal_operation(item, index=index, transaction_id=transaction_id)
        for index, item in enumerate(execution_artifacts)
    ]
    created_directories = _user_created_directory_predictions(
        package, home=home, asm=asm
    )
    will_mutate = any(item["action"] != "NO_OP" for item in execution_artifacts)
    manifest_path = _path_within(asm, USER_MANIFEST_RELATIVE)
    _ensure_no_symlink_parent(asm, USER_MANIFEST_RELATIVE)
    manifest_before_bytes = (
        manifest_path.read_bytes()
        if marker_digest is not None and manifest_path.is_file() and not manifest_path.is_symlink()
        else None
    )
    manifest_backup_path = (
        _relative_path(
            Path(USER_BACKUP_RELATIVE) / transaction_id / "previous-manifest.json",
            label="USER manifest backup",
        )
        if manifest_before_bytes is not None and will_mutate
        else None
    )
    manifest_backup_digest = (
        digest_bytes(manifest_before_bytes)
        if manifest_backup_path is not None and manifest_before_bytes is not None
        else None
    )
    backup_records = [
        {
            "destination_root": item["destination_root"],
            "destination_path": item["destination_path"],
            "previous_digest": item["expected_digest"],
            "backup_path": operation["backup_path"],
            "backup_digest": operation["backup_digest"],
        }
        for item, operation in zip(package.get("artifacts", []), operations)
        if operation.get("backup_path") is not None
    ]
    manifest_after_value = (
        _user_manifest_after(
            package,
            transaction_id=transaction_id,
            backups=backup_records,
            previous_manifest_backup=(
                {"path": manifest_backup_path, "digest": manifest_backup_digest}
                if manifest_backup_path is not None and manifest_backup_digest is not None
                else None
            ),
            created_directories=created_directories,
            asm=asm,
        )
        if will_mutate
        else manifest
    )
    manifest_after = (
        {
            "stage_path": _relative_path(
                Path(USER_STAGING_RELATIVE)
                / transaction_id
                / "ownership-manifest.json",
                label="USER staged manifest",
            ),
            "digest": digest_bytes(_json_bytes(manifest_after_value)),
        }
        if manifest_after_value is not None
        else None
    )
    journal = _user_journal_record(
        package=package,
        transaction_id=transaction_id,
        operations=operations,
        manifest_after=manifest_after,
        manifest_before_digest=marker_digest,
        manifest_backup_path=manifest_backup_path,
        manifest_backup_digest=manifest_backup_digest,
        created_directories=created_directories,
        phase="PREPARED",
        completed=[],
        home=home,
        asm=asm,
    )
    _write_user_journal(asm, journal)
    interrupted = [False]
    try:
        _user_mutation_boundary(interrupt_at, "after_prepared", transaction_id, interrupted)
        stage_dir.mkdir(parents=True, exist_ok=False)
        for index, operation in enumerate(operations):
            artifact = execution_artifacts[index]
            if artifact["action"] in {"CREATE", "UPDATE_MANAGED", "RESTORE"}:
                raw = (
                    source_cache.get(str(artifact["skill_id"]))
                    if artifact["action"] != "RESTORE"
                    else _user_source_for_artifact(
                        artifact, repository_root=repository_root, asm=asm
                    )
                )
                if raw is None or digest_bytes(raw) != operation["new_digest"]:
                    raise InstallerError("USER staged source digest mismatch")
                _write_staged(stage_dir, f"files/{index}.bin", raw)
        if manifest_backup_path is not None and manifest_before_bytes is not None:
            _user_write_backup(
                asm,
                stage_dir=stage_dir,
                backup_path=manifest_backup_path,
                payload=manifest_before_bytes,
                index=10_000_000,
            )
        if manifest_after_value is not None and will_mutate:
            _write_staged(
                stage_dir,
                "ownership-manifest.json",
                _json_bytes(manifest_after_value),
            )
        journal["phase"] = "STAGED"
        _write_user_journal(asm, journal)
        _user_mutation_boundary(interrupt_at, "after_staging", transaction_id, interrupted)
        for index, operation in enumerate(operations):
            artifact = execution_artifacts[index]
            journal["phase"] = "MUTATING"
            journal["active_operation_index"] = index
            _write_user_journal(asm, journal)
            root = _user_root_for(
                operation["destination_root"], home_root=home, asm_user_data_root=asm
            )
            destination = _path_within(root, operation["destination_path"])
            _ensure_no_symlink_parent(root, operation["destination_path"])
            current_state, current_digest = _inspect_user_destination(
                root,
                operation["destination_path"],
                root_class=operation["destination_root"],
                marker_artifacts=(
                    {
                        _user_artifact_key(item): item
                        for item in (manifest or {}).get("artifacts", [])
                    }
                ),
            )
            if operation["destination_root"] == "CLAUDE_PERSONAL":
                slug = Path(operation["destination_path"]).parts[-2]
                synced = _path_within(
                    home,
                    Path(USER_SKILL_ROOT_RELATIVE) / "synced" / slug,
                )
                if synced.is_symlink() or synced.exists():
                    current_state, current_digest = "CLAUDE_SYNCED", None
            if (
                current_state != operation["expected_state"]
                or current_digest != operation["expected_digest"]
            ):
                raise InstallerError(
                    f"STALE_PACKAGE: destination changed before mutation: {operation['destination_path']}"
                )
            if artifact["action"] == "NO_OP":
                journal["completed_operation_indexes"].append(index)
                journal["completed_operation_indexes"] = sorted(
                    set(journal["completed_operation_indexes"])
                )
                journal["active_operation_index"] = None
                _write_user_journal(asm, journal)
                continue
            if operation.get("backup_path") is not None:
                previous = destination.read_bytes()
                if operation.get("backup_digest") != digest_bytes(previous):
                    raise InstallerError("USER destination changed before backup")
                _user_write_backup(
                    asm,
                    stage_dir=stage_dir,
                    backup_path=operation["backup_path"],
                    payload=previous,
                    index=index,
                )
            if artifact["action"] in {"CREATE", "UPDATE_MANAGED", "RESTORE"}:
                _ensure_parent_dirs(root, operation["destination_path"], [])
                staged = _path_within(asm, operation["stage_path"])
                if staged.is_symlink() or not staged.is_file():
                    raise InstallerError("USER staged artifact is missing")
                replace_fn(staged, destination)
            elif artifact["action"] == "REMOVE":
                _safe_unlink(destination, expected_digest=operation["expected_digest"])
            else:
                raise InstallerError("USER journal contains an unresolved action")
            journal["completed_operation_indexes"].append(index)
            journal["completed_operation_indexes"] = sorted(
                set(journal["completed_operation_indexes"])
            )
            journal["active_operation_index"] = None
            _write_user_journal(asm, journal)
            if artifact["action"] == "CREATE":
                _user_mutation_boundary(interrupt_at, "after_create", transaction_id, interrupted)
            if artifact["action"] in {"UPDATE_MANAGED", "RESTORE"}:
                _user_mutation_boundary(interrupt_at, "after_update", transaction_id, interrupted)
        _user_mutation_boundary(interrupt_at, "before_ownership", transaction_id, interrupted)
        if will_mutate:
            _ensure_no_symlink_parent(asm, USER_MANIFEST_RELATIVE)
            if manifest_after is None:
                if manifest_path.exists() or manifest_path.is_symlink():
                    _safe_unlink(manifest_path, expected_digest=marker_digest)
            else:
                staged_manifest = _path_within(asm, manifest_after["stage_path"])
                if staged_manifest.is_symlink() or not staged_manifest.is_file():
                    raise InstallerError("USER staged ownership manifest is missing")
                if digest_bytes(staged_manifest.read_bytes()) != manifest_after["digest"]:
                    raise InstallerError("USER staged ownership manifest digest mismatch")
                replace_fn(staged_manifest, manifest_path)
        journal["phase"] = "OWNERSHIP_COMMITTED"
        _write_user_journal(asm, journal)
        _user_mutation_boundary(interrupt_at, "after_ownership", transaction_id, interrupted)
        _user_mutation_boundary(interrupt_at, "before_verify", transaction_id, interrupted)
        _user_verify_transaction(journal, home=home, asm=asm)
        journal["phase"] = "VERIFIED"
        _write_user_journal(asm, journal)
        journal["phase"] = "COMPLETE"
        _write_user_journal(asm, journal)
        _user_cleanup_stage(asm, transaction_id)
        if package["package_kind"] == "UNINSTALL":
            result_status = "UNINSTALLED"
        elif package["package_kind"] == "REVERT":
            result_status = "REVERTED"
        else:
            result_status = "APPLIED" if will_mutate else "NO_OP"
        return _result(
            package=package,
            status=result_status,
            transaction_id=transaction_id,
            attempted=attempted,
            completed=attempted,
            warnings=package.get("warnings", []),
            rollback_status="NOT_NEEDED",
        )
    except Exception as exc:
        journal["phase"] = "RECOVERY_REQUIRED"
        try:
            _write_user_journal(asm, journal)
            _user_rollback_journal(journal, home=home, asm=asm)
            journal["phase"] = "ROLLED_BACK"
            journal["completed_operation_indexes"] = []
            journal["active_operation_index"] = None
            _write_user_journal(asm, journal)
            return _result(
                package=package,
                status="ROLLED_BACK",
                transaction_id=transaction_id,
                attempted=attempted,
                completed=[],
                warnings=package.get("warnings", [])
                + [f"USER apply failed: {type(exc).__name__}"],
                rollback_status="SUCCEEDED",
            )
        except Exception as rollback_exc:
            try:
                journal["phase"] = "RECOVERY_REQUIRED"
                _write_user_journal(asm, journal)
            except Exception:
                pass
            return _result(
                package=package,
                status="PARTIAL",
                transaction_id=transaction_id,
                attempted=attempted,
                completed=[
                    package["artifacts"][index]["destination_path"]
                    for index in journal.get("completed_operation_indexes", [])
                ],
                warnings=package.get("warnings", [])
                + [
                    f"USER apply failed: {type(exc).__name__}",
                    f"rollback failed: {type(rollback_exc).__name__}",
                ],
                rollback_status="FAILED",
            )


def _user_recovery_result(
    journal: dict[str, Any], *, decision: str, final_phase: str, conflicts: list[str] | None = None
) -> dict[str, Any]:
    return {
        "schema_version": "3.0",
        "recovery_version": "1.0",
        "transaction_id": journal["transaction_id"],
        "package_digest": journal["package_digest"],
        "runtime_id": journal["runtime_id"],
        "scope": "USER",
        "decision": decision,
        "final_phase": final_phase,
        "completed_operation_indexes": sorted(
            set(journal.get("completed_operation_indexes", []))
        ),
        "conflicts": sorted(set(conflicts or [])),
        "sensitive_data_serialized": False,
    }


def _user_resume_journal(
    journal: dict[str, Any], *, home: Path, asm: Path
) -> dict[str, Any]:
    """Resume a journal whose exact staged inputs are still present."""

    transaction_id = journal["transaction_id"]
    stage_dir = _path_within(asm, Path(USER_STAGING_RELATIVE) / transaction_id)
    completed = set(journal.get("completed_operation_indexes", []))
    for operation in journal["operations"]:
        index = operation["index"]
        if index in completed:
            continue
        action = operation["action"]
        active = journal.get("active_operation_index") == index
        root = _user_root_for(
            operation["destination_root"], home_root=home, asm_user_data_root=asm
        )
        destination = _path_within(root, operation["destination_path"])
        _ensure_no_symlink_parent(root, operation["destination_path"])
        if action == "NO_OP":
            if active:
                raise InstallerError("MANUAL_CONFLICT: NO_OP operation is active")
            completed.add(index)
            journal["completed_operation_indexes"] = sorted(completed)
            journal["active_operation_index"] = None
            _write_user_journal(asm, journal)
            continue
        if action in {"CREATE", "UPDATE_MANAGED", "RESTORE"}:
            if destination.is_file() and not destination.is_symlink():
                current = digest_bytes(destination.read_bytes())
                if current == operation["new_digest"]:
                    if not active:
                        raise InstallerError(
                            "MANUAL_CONFLICT: unjournaled replacement is ambiguous"
                        )
                    if operation.get("backup_path") is not None:
                        backup = _path_within(asm, operation["backup_path"])
                        if (
                            backup.is_symlink()
                            or not backup.is_file()
                            or digest_bytes(backup.read_bytes())
                            != operation["backup_digest"]
                        ):
                            raise InstallerError(
                                "RECOVERY_BLOCKED: active replacement backup is unavailable"
                            )
                    completed.add(index)
                    journal["completed_operation_indexes"] = sorted(completed)
                    journal["active_operation_index"] = None
                    _write_user_journal(asm, journal)
                    continue
                if current != operation["expected_digest"]:
                    raise InstallerError("MANUAL_CONFLICT: replaced path was modified")
            elif destination.exists() or destination.is_symlink():
                raise InstallerError("MANUAL_CONFLICT: replacement path is unsafe")
            staged = operation.get("stage_path")
            if not isinstance(staged, str):
                raise InstallerError("MANUAL_CONFLICT: staged replacement is unavailable")
            staged_path = _path_within(asm, staged)
            _ensure_no_symlink_parent(asm, staged)
            if staged_path.is_symlink() or not staged_path.is_file():
                raise InstallerError("MANUAL_CONFLICT: staged replacement is missing")
            if digest_bytes(staged_path.read_bytes()) != operation["stage_digest"]:
                raise InstallerError("RECOVERY_BLOCKED: staged replacement digest mismatch")
        elif action == "REMOVE":
            if not destination.exists() and not destination.is_symlink():
                if not active:
                    raise InstallerError("MANUAL_CONFLICT: removal path was modified")
                backup = _path_within(asm, operation["backup_path"])
                if (
                    backup.is_symlink()
                    or not backup.is_file()
                    or digest_bytes(backup.read_bytes()) != operation["backup_digest"]
                ):
                    raise InstallerError(
                        "RECOVERY_BLOCKED: active removal backup is unavailable"
                    )
                completed.add(index)
                journal["completed_operation_indexes"] = sorted(completed)
                journal["active_operation_index"] = None
                _write_user_journal(asm, journal)
                continue
            if destination.is_symlink() or not destination.is_file():
                raise InstallerError("MANUAL_CONFLICT: removal path is unsafe")
            if digest_bytes(destination.read_bytes()) != operation["expected_digest"]:
                raise InstallerError("MANUAL_CONFLICT: removal path was modified")
        else:
            raise InstallerError("RECOVERY_BLOCKED: unknown journal action")
        if operation.get("backup_path") is not None:
            backup = _path_within(asm, operation["backup_path"])
            if backup.exists() or backup.is_symlink():
                if backup.is_symlink() or not backup.is_file():
                    raise InstallerError("RECOVERY_BLOCKED: backup path is unsafe")
                if digest_bytes(backup.read_bytes()) != operation["backup_digest"]:
                    raise InstallerError("RECOVERY_BLOCKED: backup digest mismatch")
            else:
                previous = destination.read_bytes()
                _user_write_backup(
                    asm,
                    stage_dir=stage_dir,
                    backup_path=operation["backup_path"],
                    payload=previous,
                    index=index,
                )
        if action in {"CREATE", "UPDATE_MANAGED", "RESTORE"}:
            _ensure_no_symlink_parent(root, operation["destination_path"])
            _ensure_parent_dirs(root, operation["destination_path"], [])
            replace_source = _path_within(asm, operation["stage_path"])
            os.replace(replace_source, destination)
        else:
            _safe_unlink(destination, expected_digest=operation["expected_digest"])
        completed.add(index)
        journal["completed_operation_indexes"] = sorted(completed)
        journal["active_operation_index"] = None
        _write_user_journal(asm, journal)
    journal["phase"] = "MUTATING"
    _write_user_journal(asm, journal)
    manifest_path = _path_within(asm, journal["manifest_path"])
    _ensure_no_symlink_parent(asm, journal["manifest_path"])
    if journal["manifest_after"] is None:
        if manifest_path.exists() or manifest_path.is_symlink():
            if journal.get("manifest_after_digest") is None:
                raise InstallerError("MANUAL_CONFLICT: unexpected USER manifest")
            if digest_bytes(manifest_path.read_bytes()) != journal["manifest_after_digest"]:
                raise InstallerError("MANUAL_CONFLICT: USER manifest was modified")
            _safe_unlink(manifest_path, expected_digest=journal["manifest_after_digest"])
    else:
        if manifest_path.exists() and not manifest_path.is_symlink():
            current_manifest_digest = digest_bytes(manifest_path.read_bytes())
            if current_manifest_digest == journal["manifest_after_digest"]:
                pass
            elif current_manifest_digest != journal.get("manifest_before_digest"):
                raise InstallerError("MANUAL_CONFLICT: USER manifest was modified")
            else:
                descriptor = journal["manifest_after"]
                staged_manifest = _path_within(asm, descriptor["stage_path"])
                _ensure_no_symlink_parent(asm, descriptor["stage_path"])
                if staged_manifest.is_symlink() or not staged_manifest.is_file():
                    raise InstallerError("MANUAL_CONFLICT: staged USER manifest is missing")
                if digest_bytes(staged_manifest.read_bytes()) != journal["manifest_after_digest"]:
                    raise InstallerError("RECOVERY_BLOCKED: staged USER manifest digest mismatch")
                os.replace(staged_manifest, manifest_path)
        else:
            descriptor = journal["manifest_after"]
            if not isinstance(descriptor, dict) or not isinstance(
                descriptor.get("stage_path"), str
            ):
                raise InstallerError("RECOVERY_BLOCKED: staged USER manifest reference is invalid")
            staged_manifest = _path_within(asm, descriptor["stage_path"])
            _ensure_no_symlink_parent(asm, descriptor["stage_path"])
            if staged_manifest.is_symlink() or not staged_manifest.is_file():
                raise InstallerError("MANUAL_CONFLICT: staged USER manifest is missing")
            if digest_bytes(staged_manifest.read_bytes()) != journal["manifest_after_digest"]:
                raise InstallerError("RECOVERY_BLOCKED: staged USER manifest digest mismatch")
            os.replace(staged_manifest, manifest_path)
    journal["phase"] = "OWNERSHIP_COMMITTED"
    _write_user_journal(asm, journal)
    _user_verify_transaction(journal, home=home, asm=asm)
    journal["phase"] = "VERIFIED"
    _write_user_journal(asm, journal)
    journal["phase"] = "COMPLETE"
    _write_user_journal(asm, journal)
    _user_cleanup_stage(asm, transaction_id)
    return _user_recovery_result(
        journal, decision="RESUME", final_phase="COMPLETE"
    )


def recover_user_transaction(
    transaction_id: str,
    *,
    home_root: str | Path | None,
    asm_user_data_root: str | Path | None,
) -> dict[str, Any]:
    """Recover one exact virtual-home transaction in a fresh-process model."""

    home, asm = _safe_virtual_roots(home_root, asm_user_data_root)
    _, journal = _read_user_journal(asm, transaction_id)
    expected_home = _root_identity(home, label="virtual HOME")
    expected_asm = _root_identity(asm, label="virtual ASM user-data root")
    if journal.get("home_root_identity") != expected_home or journal.get(
        "asm_user_data_root_identity"
    ) != expected_asm:
        raise InstallerError("RECOVERY_BLOCKED: transaction root identity changed")
    if journal.get("target_root_identity") != _user_target_root_identity(home, asm):
        raise InstallerError("RECOVERY_BLOCKED: transaction target identity changed")
    phase = journal["phase"]
    if phase == "COMPLETE":
        _user_verify_transaction(journal, home=home, asm=asm)
        return _user_recovery_result(
            journal, decision="COMPLETE_VERIFICATION", final_phase="COMPLETE"
        )
    if phase == "ROLLED_BACK":
        return _user_recovery_result(
            journal, decision="ROLLBACK", final_phase="ROLLED_BACK"
        )
    if phase != "RECOVERY_REQUIRED":
        journal["phase"] = "RECOVERY_REQUIRED"
        _write_user_journal(asm, journal)
    manifest_path = _path_within(asm, journal["manifest_path"])
    _ensure_no_symlink_parent(asm, journal["manifest_path"])
    if manifest_path.exists() or manifest_path.is_symlink():
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise InstallerError("RECOVERY_BLOCKED: USER manifest is unsafe")
        current_manifest_digest = digest_bytes(manifest_path.read_bytes())
        marker_committed = (
            journal.get("manifest_after_digest") is not None
            and current_manifest_digest == journal.get("manifest_after_digest")
        )
        marker_is_previous = current_manifest_digest == journal.get(
            "manifest_before_digest"
        )
        if not marker_committed and not marker_is_previous:
            journal["phase"] = "RECOVERY_REQUIRED"
            _write_user_journal(asm, journal)
            return _user_recovery_result(
                journal,
                decision="MANUAL_CONFLICT",
                final_phase="RECOVERY_REQUIRED",
                conflicts=[journal["manifest_path"]],
            )
        if marker_committed:
            # The marker was committed but the state transition or final
            # verify was interrupted.  It is safe to complete verification
            # only when all exact operation digests still match.
            try:
                _user_verify_transaction(journal, home=home, asm=asm)
            except InstallerError as exc:
                journal["phase"] = "RECOVERY_REQUIRED"
                _write_user_journal(asm, journal)
                return _user_recovery_result(
                    journal,
                    decision="MANUAL_CONFLICT",
                    final_phase="RECOVERY_REQUIRED",
                    conflicts=[str(exc)],
                )
            journal["phase"] = "OWNERSHIP_COMMITTED"
            _write_user_journal(asm, journal)
            journal["phase"] = "VERIFIED"
            _write_user_journal(asm, journal)
            journal["phase"] = "COMPLETE"
            _write_user_journal(asm, journal)
            _user_cleanup_stage(asm, transaction_id)
            return _user_recovery_result(
                journal, decision="COMPLETE_VERIFICATION", final_phase="COMPLETE"
            )
    if phase == "PREPARED" and not journal.get("completed_operation_indexes"):
        _user_cleanup_stage(asm, transaction_id)
        journal["phase"] = "ROLLED_BACK"
        _write_user_journal(asm, journal)
        return _user_recovery_result(journal, decision="ROLLBACK", final_phase="ROLLED_BACK")
    try:
        result = _user_resume_journal(journal, home=home, asm=asm)
        return result
    except InstallerError as exc:
        message = str(exc)
        if message.startswith("RECOVERY_BLOCKED"):
            raise
        journal["phase"] = "RECOVERY_REQUIRED"
        _write_user_journal(asm, journal)
        return _user_recovery_result(
            journal,
            decision="MANUAL_CONFLICT",
            final_phase="RECOVERY_REQUIRED",
            conflicts=[message],
        )


def apply_user_uninstall_package(
    package: dict[str, Any],
    *,
    home_root: str | Path | None,
    asm_user_data_root: str | Path | None,
    confirmation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply an exact, separately built USER uninstall package."""

    return apply_user_install_package(
        package,
        home_root=home_root,
        asm_user_data_root=asm_user_data_root,
        repository_root=ROOT,
        confirmation=confirmation,
    )


def apply_user_revert_package(
    package: dict[str, Any],
    *,
    home_root: str | Path | None,
    asm_user_data_root: str | Path | None,
    confirmation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply an exact-backup USER revert package."""

    return apply_user_install_package(
        package,
        home_root=home_root,
        asm_user_data_root=asm_user_data_root,
        repository_root=ROOT,
        confirmation=confirmation,
    )


def build_install_package(
    distribution_dir: str | Path,
    plan: dict[str, Any],
    runtime_status: dict[str, Any],
    *,
    scope: str = "PROJECT",
    project_root: str | Path | None = None,
    target: dict[str, Any] | None = None,
    target_inventory: str | Path = DEFAULT_TARGET_INVENTORY,
) -> dict[str, Any]:
    """Filter generated output into a persistent, project-scoped package."""

    scope = normalize_scope(scope)
    status_errors = validate_instance("RuntimeProductStatus", runtime_status).errors
    if status_errors:
        raise InstallerError(
            "invalid runtime product status: " + "; ".join(status_errors)
        )
    distribution, manifest, files = _load_distribution(distribution_dir)
    _validate_plan(plan, manifest)
    runtime_id = str(runtime_status["runtime_id"])
    target = (
        copy.deepcopy(target)
        if target is not None
        else load_install_target(runtime_id, target_inventory)
    )
    target_errors = _target_validation_errors(runtime_status, target)
    root = (
        _safe_project_root(project_root)
        if scope == "PROJECT" and project_root is not None
        else None
    )
    if scope == "PROJECT" and root is None:
        raise InstallerError(
            "PROJECT package construction requires an explicit project root"
        )
    root_reference = _project_reference(root, scope)
    root_digest = (
        _project_identity(root)
        if root is not None
        else digest_value({"scope": scope, "root": None})
    )
    marker_relative = (
        _marker_path(target, runtime_id)
        if target.get("destination_root_template")
        else f"{PROJECT_STAGING_ROOT}/{runtime_id}/{MARKER_NAME}"
    )
    marker: dict[str, Any] | None = None
    marker_digest: str | None = None
    if root is not None and not target_errors:
        marker, marker_digest = _read_marker(
            root,
            marker_relative,
            runtime_id=runtime_id,
            scope=scope,
            target_root=_target_root(target, runtime_id),
        )
    marker_artifacts = _marker_artifact_map(marker)
    warnings: list[str] = []
    if target_errors:
        warnings.extend(f"install contract: {item}" for item in target_errors)
    if scope != "PROJECT":
        warnings.append(f"{scope} apply is deferred; this command is preview-only")
    if target.get("native_discovery_support") == "PREVIEW_ONLY":
        warnings.append(
            "native runtime destination is preview-only; package uses project-local host-managed staging"
        )
    if runtime_status.get("live_execution") != "VERIFIED":
        warnings.append(
            f"live execution is {runtime_status.get('live_execution')}; installer makes no live-readiness claim"
        )

    installable_kinds = set(target.get("installable_kinds", []))
    artifacts: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for source_artifact in manifest.get("artifacts", []):
        source_path = source_artifact["path"]
        lifecycle = source_artifact["lifecycle"]
        if lifecycle not in PERSISTENT_LIFECYCLES:
            reason = "execution-ephemeral artifacts cannot be installed persistently"
        elif source_artifact["kind"] not in installable_kinds:
            reason = "artifact kind is not in the verified project install target"
        elif target_errors or scope != "PROJECT":
            reason = "project install contract is not applicable to this preview scope"
        else:
            reason = ""
        if reason:
            excluded.append(
                {
                    "path": _relative_path(source_path, label="generated artifact"),
                    "kind": source_artifact["kind"],
                    "lifecycle": lifecycle,
                    "reason": reason,
                }
            )
            continue
        destination_path = _destination_for(target, runtime_id, source_path)
        state, existing_digest = _inspect_destination(
            root,
            destination_path,
            marker_artifacts=marker_artifacts,
        )
        if state == "ABSENT":
            action = "CREATE"
            origin = "CREATED_BY_ASM"
        elif state == "ASM_MANAGED":
            action = (
                "NO_OP"
                if existing_digest == source_artifact["content_digest"]
                else "UPDATE_MANAGED"
            )
            old_origin = marker_artifacts.get(destination_path, {}).get("origin")
            origin = (
                old_origin
                if action == "NO_OP" and old_origin
                else "UPDATED_ASM_MANAGED"
            )
        elif state == "USER_OWNED":
            action = "SKIP_USER_OWNED"
            origin = "USER_OWNED"
        else:
            action = "CONFLICT"
            origin = "CONFLICT"
        artifacts.append(
            {
                "source_path": _relative_path(source_path, label="source artifact"),
                "destination_path": destination_path,
                "kind": source_artifact["kind"],
                "lifecycle": lifecycle,
                "source_digest": source_artifact["source_digest"],
                "content_digest": source_artifact["content_digest"],
                "expected_state": state,
                "expected_digest": existing_digest,
                "action": action,
                "origin": origin,
            }
        )
        if action in CONFLICT_ACTIONS:
            warnings.append(
                f"destination {destination_path} is {state}; no overwrite is permitted"
            )
    artifacts.sort(key=lambda item: item["destination_path"])
    excluded.sort(key=lambda item: item["path"])
    conflicts = [
        item["destination_path"]
        for item in artifacts
        if item["action"] in CONFLICT_ACTIONS
    ]
    installable = bool(artifacts) and not bool(target_errors)
    apply_allowed = (
        scope == "PROJECT"
        and installable
        and not conflicts
        and all(item["action"] in INSTALL_ACTIONS for item in artifacts)
    )
    package: dict[str, Any] = {
        "schema_version": "3.0",
        "package_version": INSTALLER_VERSION,
        "package_digest": "",
        "plan_digest": plan["plan_digest"],
        "runtime_id": runtime_id,
        "scope": scope,
        "project_root_reference": root_reference,
        "project_root_digest": root_digest,
        "snapshot_digest": manifest["snapshot_digest"],
        "runtime_contract_digest": manifest.get("runtime_contract_digest"),
        "install_target_digest": digest_value(target),
        "source_manifest_digest": manifest["manifest_digest"],
        "marker_digest": marker_digest,
        "marker_path": marker_relative,
        "artifacts": artifacts,
        "excluded_artifacts": excluded,
        "installable": installable,
        "apply_allowed": apply_allowed,
        "warnings": sorted(set(warnings)),
    }
    package["package_digest"] = _package_digest(package)
    _validate_package(package)
    # Keep the source directory only in the caller's execution context; never
    # place an absolute path or source bytes in the package.
    del distribution, files
    return package


def build_status_only_package(
    runtime_status: dict[str, Any],
    *,
    scope: str = "PROJECT",
    project_root: str | Path | None = None,
    target: dict[str, Any] | None = None,
    target_inventory: str | Path = DEFAULT_TARGET_INVENTORY,
) -> dict[str, Any]:
    """Represent a runtime without synthesizing a distribution for it."""

    scope = normalize_scope(scope)
    status_errors = validate_instance("RuntimeProductStatus", runtime_status).errors
    if status_errors:
        raise InstallerError(
            "invalid runtime product status: " + "; ".join(status_errors)
        )
    target = (
        copy.deepcopy(target)
        if target is not None
        else load_install_target(runtime_status["runtime_id"], target_inventory)
    )
    root = (
        _safe_project_root(project_root)
        if scope == "PROJECT" and project_root is not None
        else None
    )
    if scope == "PROJECT" and root is None:
        raise InstallerError("PROJECT status preview requires an explicit project root")
    marker_path = (
        _marker_path(target, runtime_status["runtime_id"])
        if target.get("destination_root_template")
        else f"{PROJECT_STAGING_ROOT}/{runtime_status['runtime_id']}/{MARKER_NAME}"
    )
    evidence_digest = digest_value(
        {
            "runtime_id": runtime_status["runtime_id"],
            "status": runtime_status,
            "target": target,
        }
    )
    package: dict[str, Any] = {
        "schema_version": "3.0",
        "package_version": INSTALLER_VERSION,
        "package_digest": "",
        "plan_digest": evidence_digest,
        "runtime_id": runtime_status["runtime_id"],
        "scope": scope,
        "project_root_reference": _project_reference(root, scope),
        "project_root_digest": _project_identity(root)
        if root is not None
        else digest_value({"scope": scope, "root": None}),
        "snapshot_digest": evidence_digest,
        "runtime_contract_digest": runtime_status.get("runtime_contract_digest"),
        "install_target_digest": digest_value(target),
        "source_manifest_digest": evidence_digest,
        "marker_digest": None,
        "marker_path": marker_path,
        "artifacts": [],
        "excluded_artifacts": [],
        "installable": False,
        "apply_allowed": False,
        "warnings": [
            "runtime has no implemented static adapter; status-only preview emits no distribution artifacts",
        ],
    }
    package["package_digest"] = _package_digest(package)
    _validate_package(package)
    return package


def _result(
    *,
    package: dict[str, Any],
    status: str,
    transaction_id: str,
    attempted: list[str] | None = None,
    completed: list[str] | None = None,
    warnings: list[str] | None = None,
    conflicts: list[str] | None = None,
    rollback_status: str = "NOT_ATTEMPTED",
) -> dict[str, Any]:
    result = {
        "schema_version": "3.0",
        "result_version": INSTALLER_VERSION,
        "transaction_id": transaction_id,
        "package_digest": package["package_digest"],
        "runtime_id": package["runtime_id"],
        "scope": package["scope"],
        "status": status,
        "actions_attempted": sorted(set(attempted or [])),
        "actions_completed": sorted(set(completed or [])),
        "warnings": sorted(set(warnings or [])),
        "conflicts": sorted(set(conflicts or [])),
        "rollback_status": rollback_status,
        "sensitive_data_serialized": False,
    }
    errors = validate_instance("ApplyResult", result).errors
    if errors:
        raise InstallerError("invalid ApplyResult: " + "; ".join(errors))
    return result


def _marker_result_package(
    marker: dict[str, Any],
    *,
    runtime_id: str,
    marker_relative: str,
    marker_digest: str | None,
) -> dict[str, Any]:
    fallback = digest_value(
        {"marker": marker.get("package_digest"), "runtime_id": runtime_id}
    )
    package = {
        "schema_version": "3.0",
        "package_version": INSTALLER_VERSION,
        "package_digest": marker.get("package_digest", fallback),
        "plan_digest": marker.get("plan_digest", fallback),
        "runtime_id": runtime_id,
        "scope": "PROJECT",
        "project_root_reference": fallback,
        "project_root_digest": fallback,
        "snapshot_digest": marker.get("snapshot_digest", fallback),
        "runtime_contract_digest": marker.get("runtime_contract_digest"),
        "install_target_digest": marker.get("install_target_digest", fallback),
        "source_manifest_digest": marker.get("source_manifest_digest", fallback),
        "marker_digest": marker_digest,
        "marker_path": marker_relative,
        "artifacts": [],
        "excluded_artifacts": [],
        "installable": False,
        "apply_allowed": False,
        "warnings": [],
    }
    return package


def preview_install(package: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitized preview without changing the filesystem."""

    _validate_package(package)
    attempted = [item["destination_path"] for item in package.get("artifacts", [])]
    conflicts = [
        item["destination_path"]
        for item in package.get("artifacts", [])
        if item["action"] in CONFLICT_ACTIONS
    ]
    status = "CONFLICT" if conflicts else "PREVIEWED"
    return _result(
        package=package,
        status=status,
        transaction_id="preview-" + package["package_digest"][7:19],
        attempted=attempted,
        completed=[],
        warnings=package.get("warnings", []),
        conflicts=conflicts,
    )


def _new_transaction_id() -> str:
    return uuid.uuid4().hex


def _write_staged(stage_dir: Path, name: str, payload: bytes) -> Path:
    target = stage_dir / Path(_relative_path(name, label="staged file"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return target


def _ensure_parent_dirs(root: Path, relative: str, created: list[str]) -> None:
    safe = _relative_path(relative, label="destination")
    current = root
    built: list[str] = []
    for part in Path(safe).parts[:-1]:
        current = current / part
        built.append(part)
        if current.is_symlink():
            raise InstallerError(f"destination parent is a symlink: {safe}")
        if current.exists():
            if not current.is_dir():
                raise InstallerError(f"destination parent is not a directory: {safe}")
        else:
            current.mkdir()
            created.append(Path(*built).as_posix())


def _safe_unlink(path: Path, *, expected_digest: str | None = None) -> None:
    if path.is_symlink() or not path.exists():
        return
    if not path.is_file():
        raise InstallerError(f"refusing to delete non-file path: {path.name}")
    if (
        expected_digest is not None
        and digest_bytes(path.read_bytes()) != expected_digest
    ):
        raise InstallerError("file changed before bounded delete")
    path.unlink()


def _transaction_record(
    root: Path,
    *,
    runtime_id: str,
    transaction_id: str,
    package_digest: str,
    status: str,
    actions: list[str],
    rollback_status: str,
    created_directories: list[str],
) -> Path:
    runtime_root = _path_within(root, f"{PROJECT_STAGING_ROOT}/{runtime_id}")
    transaction_dir = runtime_root / TRANSACTION_DIRECTORY
    if transaction_dir.is_symlink():
        raise InstallerError("transaction directory is a symlink")
    transaction_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": "3.0",
        "result_version": INSTALLER_VERSION,
        "transaction_id": transaction_id,
        "runtime_id": runtime_id,
        "scope": "PROJECT",
        "package_digest": package_digest,
        "status": status,
        "actions": sorted(set(actions)),
        "rollback_status": rollback_status,
        "created_directories": sorted(set(created_directories)),
        "sensitive_data_serialized": False,
    }
    path = transaction_dir / f"{transaction_id}.json"
    if path.exists() or path.is_symlink():
        raise InstallerError("transaction record collision")
    path.write_bytes(_json_bytes(record))
    return path


def _marker_payload(
    *,
    package: dict[str, Any],
    transaction_id: str,
    artifacts: list[dict[str, Any]],
    backups: list[dict[str, Any]],
    previous_marker_backup: dict[str, str] | None,
    created_directories: list[str],
) -> dict[str, Any]:
    return {
        "generator_id": INSTALLER_GENERATOR_ID,
        "schema_version": "3.0",
        "managed": True,
        "runtime_id": package["runtime_id"],
        "scope": package["scope"],
        "package_digest": package["package_digest"],
        "plan_digest": package["plan_digest"],
        "snapshot_digest": package["snapshot_digest"],
        "runtime_contract_digest": package["runtime_contract_digest"],
        "install_target_digest": package["install_target_digest"],
        "source_manifest_digest": package["source_manifest_digest"],
        "marker_path": package["marker_path"],
        "transaction_id": transaction_id,
        "artifacts": artifacts,
        "backups": backups,
        "previous_marker_backup": previous_marker_backup,
        "created_directories": sorted(set(created_directories)),
    }


def _revalidate_package(
    package: dict[str, Any],
    distribution_dir: str | Path,
    root: Path,
    target: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, bytes], dict[str, Any] | None, str | None]:
    _validate_package(package)
    if package.get("scope") != "PROJECT":
        raise InstallerError("STALE_PLAN: only PROJECT packages can be applied")
    if package.get("install_target_digest") != digest_value(target):
        raise InstallerError("STALE_PLAN: install target contract changed")
    if package.get("project_root_reference") != _project_reference(root, "PROJECT"):
        raise InstallerError("STALE_PLAN: project root changed")
    if package.get("project_root_digest") != _project_identity(root):
        raise InstallerError("STALE_PLAN: project root identity changed")
    _, manifest, files = _load_distribution(distribution_dir)
    manifest_runtime_contract = manifest.get("runtime_contract_digest")
    if manifest_runtime_contract != package.get("runtime_contract_digest"):
        raise InstallerError("STALE_PLAN: runtime contract changed")
    target_runtime_contract = target.get("runtime_contract_digest")
    if target_runtime_contract != package.get("runtime_contract_digest"):
        raise InstallerError("STALE_PLAN: runtime contract target changed")
    if manifest.get("manifest_digest") != package.get("source_manifest_digest"):
        raise InstallerError("STALE_PLAN: generated artifact manifest changed")
    if manifest.get("snapshot_digest") != package.get("snapshot_digest"):
        raise InstallerError("STALE_PLAN: routing snapshot changed")
    marker, marker_digest = _read_marker(
        root,
        package["marker_path"],
        runtime_id=package["runtime_id"],
        scope=package["scope"],
        target_root=_target_root(target, package["runtime_id"]),
    )
    if marker_digest != package.get("marker_digest"):
        raise InstallerError("STALE_PLAN: ownership marker changed")
    marker_artifacts = _marker_artifact_map(marker)
    for artifact in package.get("artifacts", []):
        state, current_digest = _inspect_destination(
            root,
            artifact["destination_path"],
            marker_artifacts=marker_artifacts,
        )
        if state != artifact["expected_state"] or current_digest != artifact.get(
            "expected_digest"
        ):
            raise InstallerError(
                f"STALE_PLAN: destination changed: {artifact['destination_path']}"
            )
        source = files.get(artifact["source_path"])
        if source is None or digest_bytes(source) != artifact["content_digest"]:
            raise InstallerError(
                f"STALE_PLAN: source artifact changed: {artifact['source_path']}"
            )
    return manifest, files, marker, marker_digest


def apply_install_package(
    package: dict[str, Any],
    distribution_dir: str | Path | None,
    project_root: str | Path | None,
    *,
    target: dict[str, Any] | None = None,
    target_inventory: str | Path = DEFAULT_TARGET_INVENTORY,
    replace_fn: Callable[
        [str | os.PathLike[str], str | os.PathLike[str]], None
    ] = os.replace,
    rollback_replace_fn: Callable[
        [str | os.PathLike[str], str | os.PathLike[str]], None
    ] = os.replace,
    home_root: str | Path | None = None,
    asm_user_data_root: str | Path | None = None,
    repository_root: str | Path = ROOT,
    confirmation: dict[str, Any] | None = None,
    interrupt_at: str | None = None,
) -> dict[str, Any]:
    """Apply a package with all-target preflight and bounded rollback."""

    if package.get("scope") == "USER":
        if confirmation is None:
            raise InstallerError(USER_SCOPE_APPLY_NOT_AUTHORIZED)
        return apply_user_install_package(
            package,
            home_root=home_root,
            asm_user_data_root=asm_user_data_root,
            repository_root=repository_root,
            confirmation=confirmation,
            interrupt_at=interrupt_at,
            replace_fn=replace_fn,
        )
    if distribution_dir is None or project_root is None:
        raise InstallerError("PROJECT apply requires distribution and project roots")
    root = _safe_project_root(project_root)
    target = (
        copy.deepcopy(target)
        if target is not None
        else load_install_target(package["runtime_id"], target_inventory)
    )
    _revalidate_package(package, distribution_dir, root, target)
    attempted = [item["destination_path"] for item in package.get("artifacts", [])]
    if not package.get("apply_allowed"):
        conflicts = [
            item["destination_path"]
            for item in package.get("artifacts", [])
            if item["action"] in CONFLICT_ACTIONS
        ]
        return _result(
            package=package,
            status="CONFLICT" if conflicts else "ABORTED",
            transaction_id="aborted-" + package["package_digest"][7:19],
            attempted=attempted,
            warnings=package.get("warnings", [])
            + ["apply precondition is false; no filesystem mutation occurred"],
            conflicts=conflicts,
        )
    if any(
        item["action"] not in INSTALL_ACTIONS for item in package.get("artifacts", [])
    ):
        raise InstallerError("apply package contains a non-installable action")
    transaction_id = _new_transaction_id()
    stage_dir = Path(tempfile.mkdtemp(prefix=".asm-installer-", dir=root))
    runtime_id = package["runtime_id"]
    marker_relative = package["marker_path"]
    marker_path = _path_within(root, marker_relative)
    old_marker_bytes = (
        marker_path.read_bytes()
        if marker_path.is_file() and not marker_path.is_symlink()
        else None
    )
    applied: list[tuple[dict[str, Any], bytes | None, Path]] = []
    backup_records: list[dict[str, Any]] = []
    backup_paths: list[Path] = []
    created_directories: list[str] = []
    marker_replaced = False
    transaction_record_path: Path | None = None
    try:
        _, _, source_files = _load_distribution(distribution_dir)
        # Revalidate once more after staging inputs are loaded; no target is
        # touched until every precondition has passed.
        _revalidate_package(package, distribution_dir, root, target)
        for index, artifact in enumerate(package.get("artifacts", [])):
            if artifact["action"] == "NO_OP":
                continue
            source = source_files[artifact["source_path"]]
            staged = _write_staged(stage_dir, f"files/{index}.bin", source)
            destination = _path_within(root, artifact["destination_path"])
            _ensure_no_symlink_parent(root, artifact["destination_path"])
            if artifact["action"] == "UPDATE_MANAGED":
                previous = destination.read_bytes()
                backup_relative = _relative_path(
                    Path(PROJECT_STAGING_ROOT)
                    / runtime_id
                    / BACKUP_DIRECTORY
                    / transaction_id
                    / f"artifact-{index}.bin",
                    label="backup path",
                )
                backup_target = _path_within(root, backup_relative)
                _ensure_parent_dirs(root, backup_relative, created_directories)
                backup_staged = _write_staged(
                    stage_dir, f"backups/{index}.bin", previous
                )
                replace_fn(backup_staged, backup_target)
                backup_paths.append(backup_target)
                backup_records.append(
                    {
                        "path": artifact["destination_path"],
                        "previous_digest": digest_bytes(previous),
                        "backup_path": backup_relative,
                        "backup_digest": digest_bytes(previous),
                    }
                )
            else:
                previous = None
            _ensure_parent_dirs(root, artifact["destination_path"], created_directories)
            replace_fn(staged, destination)
            applied.append((artifact, previous, destination))

        if not applied:
            # A repeat apply is a true no-op: do not rewrite the ownership
            # marker, create a backup, or change managed content.  The audit
            # record is the only bounded bookkeeping write.
            transaction_record_path = _transaction_record(
                root,
                runtime_id=runtime_id,
                transaction_id=transaction_id,
                package_digest=package["package_digest"],
                status="NO_OP",
                actions=attempted,
                rollback_status="NOT_NEEDED",
                created_directories=created_directories,
            )
            del transaction_record_path
            return _result(
                package=package,
                status="NO_OP",
                transaction_id=transaction_id,
                attempted=attempted,
                completed=attempted,
                warnings=package.get("warnings", []),
                rollback_status="NOT_NEEDED",
            )

        previous_marker_backup: dict[str, str] | None = None
        if old_marker_bytes is not None:
            previous_marker_relative = _relative_path(
                Path(PROJECT_STAGING_ROOT)
                / runtime_id
                / BACKUP_DIRECTORY
                / transaction_id
                / "previous-marker.json",
                label="previous marker backup path",
            )
            previous_marker_target = _path_within(root, previous_marker_relative)
            _ensure_parent_dirs(root, previous_marker_relative, created_directories)
            previous_marker_staged = _write_staged(
                stage_dir, "backups/previous-marker.json", old_marker_bytes
            )
            replace_fn(previous_marker_staged, previous_marker_target)
            backup_paths.append(previous_marker_target)
            previous_marker_backup = {
                "path": previous_marker_relative,
                "digest": digest_bytes(old_marker_bytes),
            }

        marker_artifacts: list[dict[str, Any]] = []
        old_marker, _ = _read_marker(
            root,
            marker_relative,
            runtime_id=runtime_id,
            scope=package["scope"],
            target_root=_target_root(target, runtime_id),
        )
        old_map = _marker_artifact_map(old_marker)
        for artifact in package.get("artifacts", []):
            origin = artifact["origin"]
            if (
                artifact["action"] == "NO_OP"
                and artifact["destination_path"] in old_map
            ):
                origin = old_map[artifact["destination_path"]].get("origin", origin)
            marker_artifacts.append(
                {
                    "path": artifact["destination_path"],
                    "source_path": artifact["source_path"],
                    "source_digest": artifact["source_digest"],
                    "content_digest": artifact["content_digest"],
                    "lifecycle": artifact["lifecycle"],
                    "origin": origin,
                }
            )
        marker_value = _marker_payload(
            package=package,
            transaction_id=transaction_id,
            artifacts=marker_artifacts,
            backups=backup_records,
            previous_marker_backup=previous_marker_backup,
            created_directories=created_directories,
        )
        marker_staged = _write_staged(
            stage_dir, "ownership-marker.json", _json_bytes(marker_value)
        )
        _ensure_parent_dirs(root, marker_relative, created_directories)
        replace_fn(marker_staged, marker_path)
        marker_replaced = True

        for artifact in package.get("artifacts", []):
            destination = _path_within(root, artifact["destination_path"])
            if (
                not destination.is_file()
                or digest_bytes(destination.read_bytes()) != artifact["content_digest"]
            ):
                raise InstallerError(
                    f"post-apply digest verification failed: {artifact['destination_path']}"
                )
        if digest_bytes(marker_path.read_bytes()) != digest_bytes(
            _json_bytes(marker_value)
        ):
            raise InstallerError("post-apply ownership marker verification failed")
        transaction_record_path = _transaction_record(
            root,
            runtime_id=runtime_id,
            transaction_id=transaction_id,
            package_digest=package["package_digest"],
            status="NO_OP" if not applied else "APPLIED",
            actions=attempted,
            rollback_status="NOT_NEEDED",
            created_directories=created_directories,
        )
        del transaction_record_path
        return _result(
            package=package,
            status="NO_OP" if not applied else "APPLIED",
            transaction_id=transaction_id,
            attempted=attempted,
            completed=attempted,
            warnings=package.get("warnings", []),
            rollback_status="NOT_NEEDED",
        )
    except Exception as exc:
        rollback_failed = False
        try:
            if marker_replaced:
                if old_marker_bytes is None:
                    _safe_unlink(marker_path)
                else:
                    restore_marker = _write_staged(
                        stage_dir, "rollback/marker.json", old_marker_bytes
                    )
                    rollback_replace_fn(restore_marker, marker_path)
            for artifact, previous, destination in reversed(applied):
                if previous is None:
                    _safe_unlink(
                        destination, expected_digest=artifact["content_digest"]
                    )
                else:
                    restore = _write_staged(
                        stage_dir, f"rollback/{len(applied)}.bin", previous
                    )
                    rollback_replace_fn(restore, destination)
            for backup in backup_paths:
                _safe_unlink(backup)
        except Exception:
            rollback_failed = True
        warnings = package.get("warnings", []) + [f"apply failed: {type(exc).__name__}"]
        status = "PARTIAL" if rollback_failed else "ROLLED_BACK"
        rollback_status = "FAILED" if rollback_failed else "SUCCEEDED"
        return _result(
            package=package,
            status=status,
            transaction_id=transaction_id,
            attempted=attempted,
            completed=[item[0]["destination_path"] for item in applied]
            if rollback_failed
            else [],
            warnings=warnings,
            conflicts=[],
            rollback_status=rollback_status,
        )
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)


def _uninstall_entries(
    root: Path,
    marker: dict[str, Any],
    *,
    marker_relative: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    conflicts: list[str] = []
    marker_map = _marker_artifact_map(marker)
    for item in marker.get("artifacts", []):
        path = item["path"]
        state, digest = _inspect_destination(root, path, marker_artifacts=marker_map)
        if (
            state == "ASM_MANAGED"
            and digest == item["content_digest"]
            and item["origin"] == "CREATED_BY_ASM"
        ):
            action = "DELETE"
        elif state == "ASM_MANAGED" and item["origin"] == "UPDATED_ASM_MANAGED":
            action = "REVERT_UNAVAILABLE"
            conflicts.append(path)
        elif state == "MISSING":
            action = "MISSING"
            conflicts.append(path)
        elif state == "MODIFIED_MANAGED":
            action = "CONFLICT"
            conflicts.append(path)
        elif state == "UNSAFE":
            action = "UNSAFE"
            conflicts.append(path)
        else:
            action = "CONFLICT"
            conflicts.append(path)
        entries.append({"path": path, "action": action, "digest": digest})
    marker_path = _path_within(root, marker_relative)
    if marker_path.is_symlink() or not marker_path.is_file():
        conflicts.append(marker_relative)
    return entries, sorted(set(conflicts))


def preview_uninstall(
    *,
    runtime_id: str,
    project_root: str | Path,
    target: dict[str, Any] | None = None,
    target_inventory: str | Path = DEFAULT_TARGET_INVENTORY,
) -> dict[str, Any]:
    root = _safe_project_root(project_root)
    target = (
        copy.deepcopy(target)
        if target is not None
        else load_install_target(runtime_id, target_inventory)
    )
    marker_relative = _marker_path(target, runtime_id)
    marker, marker_digest = _read_marker(
        root,
        marker_relative,
        runtime_id=runtime_id,
        scope="PROJECT",
        target_root=_target_root(target, runtime_id),
    )
    if marker is None:
        package = {
            "package_digest": digest_value({"runtime_id": runtime_id, "marker": None}),
            "runtime_id": runtime_id,
            "scope": "PROJECT",
        }
        return {
            "status": "ABORTED",
            "marker_digest": marker_digest,
            "entries": [],
            "conflicts": [marker_relative],
            "warnings": ["no Agent Skills Matrix ownership marker exists"],
            "package": package,
        }
    entries, conflicts = _uninstall_entries(
        root, marker, marker_relative=marker_relative
    )
    return {
        "status": "CONFLICT" if conflicts else "PREVIEWED",
        "marker_digest": marker_digest,
        "entries": entries,
        "conflicts": conflicts,
        "warnings": [],
        "package": {
            "package_digest": marker["package_digest"],
            "runtime_id": runtime_id,
            "scope": "PROJECT",
        },
    }


def apply_uninstall(
    *,
    runtime_id: str,
    project_root: str | Path,
    target: dict[str, Any] | None = None,
    target_inventory: str | Path = DEFAULT_TARGET_INVENTORY,
) -> dict[str, Any]:
    root = _safe_project_root(project_root)
    target = (
        copy.deepcopy(target)
        if target is not None
        else load_install_target(runtime_id, target_inventory)
    )
    marker_relative = _marker_path(target, runtime_id)
    marker, marker_digest = _read_marker(
        root,
        marker_relative,
        runtime_id=runtime_id,
        scope="PROJECT",
        target_root=_target_root(target, runtime_id),
    )
    if marker is None:
        package = {
            "package_digest": digest_value({"runtime_id": runtime_id, "marker": None}),
            "runtime_id": runtime_id,
            "scope": "PROJECT",
        }
        return {
            "status": "ABORTED",
            "transaction_id": "uninstall-aborted",
            "actions_attempted": [],
            "actions_completed": [],
            "warnings": ["no Agent Skills Matrix ownership marker exists"],
            "conflicts": [marker_relative],
            "rollback_status": "NOT_ATTEMPTED",
            "sensitive_data_serialized": False,
            "package_digest": package["package_digest"],
            "runtime_id": runtime_id,
            "scope": "PROJECT",
            "schema_version": "3.0",
            "result_version": INSTALLER_VERSION,
        }
    entries, conflicts = _uninstall_entries(
        root, marker, marker_relative=marker_relative
    )
    package = _marker_result_package(
        marker,
        runtime_id=runtime_id,
        marker_relative=marker_relative,
        marker_digest=marker_digest,
    )
    attempted = [item["path"] for item in entries] + [marker_relative]
    if conflicts:
        return _result(
            package=package,
            status="CONFLICT",
            transaction_id="uninstall-conflict-" + marker["package_digest"][7:19],
            attempted=attempted,
            warnings=[
                "uninstall preflight found a modified, missing, or unsafe managed path"
            ],
            conflicts=conflicts,
        )
    transaction_id = _new_transaction_id()
    completed: list[str] = []
    removed: list[tuple[Path, bytes]] = []
    marker_bytes = _path_within(root, marker_relative).read_bytes()
    rollback_dir = Path(tempfile.mkdtemp(prefix=".asm-uninstall-", dir=root))
    try:
        for item in entries:
            if item["action"] != "DELETE":
                raise InstallerError(
                    "uninstall encountered a non-deletable managed artifact"
                )
            target_path = _path_within(root, item["path"])
            removed.append((target_path, target_path.read_bytes()))
            _safe_unlink(target_path, expected_digest=item["digest"])
            completed.append(item["path"])
        _safe_unlink(_path_within(root, marker_relative), expected_digest=marker_digest)
        completed.append(marker_relative)
        _transaction_record(
            root,
            runtime_id=runtime_id,
            transaction_id=transaction_id,
            package_digest=marker["package_digest"],
            status="UNINSTALLED",
            actions=attempted,
            rollback_status="NOT_NEEDED",
            created_directories=marker.get("created_directories", []),
        )
        return _result(
            package=package,
            status="UNINSTALLED",
            transaction_id=transaction_id,
            attempted=attempted,
            completed=completed,
            rollback_status="NOT_NEEDED",
        )
    except Exception as exc:
        rollback_failed = False
        try:
            for index, (target_path, previous) in enumerate(reversed(removed)):
                restore = _write_staged(rollback_dir, f"restore/{index}.bin", previous)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(restore, target_path)
            marker_path = _path_within(root, marker_relative)
            restore_marker = _write_staged(
                rollback_dir, "restore/marker.json", marker_bytes
            )
            os.replace(restore_marker, marker_path)
        except Exception:
            rollback_failed = True
        return _result(
            package=package,
            status="PARTIAL" if rollback_failed else "ROLLED_BACK",
            transaction_id=transaction_id,
            attempted=attempted,
            completed=completed,
            warnings=[f"uninstall failed: {type(exc).__name__}"],
            rollback_status="FAILED" if rollback_failed else "SUCCEEDED",
        )
    finally:
        shutil.rmtree(rollback_dir, ignore_errors=True)


def _revert_entries(
    root: Path, marker: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    conflicts: list[str] = []
    marker_map = _marker_artifact_map(marker)
    backups = {item["path"]: item for item in marker.get("backups", [])}
    previous_map: dict[str, dict[str, Any]] = {}
    previous_marker = marker.get("previous_marker_backup")
    if previous_marker:
        previous_path = _path_within(root, previous_marker.get("path", ""))
        if previous_path.is_symlink() or not previous_path.is_file():
            conflicts.append("previous marker backup")
        else:
            previous_bytes = previous_path.read_bytes()
            if digest_bytes(previous_bytes) != previous_marker.get("digest"):
                conflicts.append("previous marker backup")
            else:
                try:
                    previous_value = json.loads(previous_bytes.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    conflicts.append("previous marker backup")
                else:
                    if isinstance(previous_value, dict):
                        previous_map = _marker_artifact_map(previous_value)
    for item in marker.get("artifacts", []):
        state, digest = _inspect_destination(
            root, item["path"], marker_artifacts=marker_map
        )
        if state != "ASM_MANAGED" or digest != item["content_digest"]:
            entries.append({"path": item["path"], "action": "CONFLICT"})
            conflicts.append(item["path"])
            continue
        if item["path"] in previous_map and item["path"] not in backups:
            # The artifact existed before this transaction and was unchanged.
            # Reverting the transaction must retain it.
            entries.append({"path": item["path"], "action": "NO_OP"})
        elif item["origin"] == "UPDATED_ASM_MANAGED":
            backup = backups.get(item["path"])
            if not backup:
                entries.append({"path": item["path"], "action": "REVERT_UNAVAILABLE"})
                conflicts.append(item["path"])
            else:
                entries.append(
                    {"path": item["path"], "action": "RESTORE", "backup": backup}
                )
        elif item["origin"] == "CREATED_BY_ASM":
            entries.append({"path": item["path"], "action": "DELETE_CREATED"})
        else:
            entries.append({"path": item["path"], "action": "NO_OP"})
    return entries, sorted(set(conflicts))


def preview_revert(
    *,
    runtime_id: str,
    project_root: str | Path,
    transaction_id: str,
    target: dict[str, Any] | None = None,
    target_inventory: str | Path = DEFAULT_TARGET_INVENTORY,
) -> dict[str, Any]:
    root = _safe_project_root(project_root)
    target = (
        copy.deepcopy(target)
        if target is not None
        else load_install_target(runtime_id, target_inventory)
    )
    marker_relative = _marker_path(target, runtime_id)
    marker, marker_digest = _read_marker(
        root,
        marker_relative,
        runtime_id=runtime_id,
        scope="PROJECT",
        target_root=_target_root(target, runtime_id),
    )
    if marker is None or marker.get("transaction_id") != transaction_id:
        return {
            "status": "REVERT_UNAVAILABLE",
            "conflicts": [marker_relative],
            "entries": [],
            "marker_digest": marker_digest,
        }
    entries, conflicts = _revert_entries(root, marker)
    return {
        "status": "CONFLICT" if conflicts else "PREVIEWED",
        "conflicts": conflicts,
        "entries": entries,
        "marker_digest": marker_digest,
    }


def apply_revert(
    *,
    runtime_id: str,
    project_root: str | Path,
    transaction_id: str,
    target: dict[str, Any] | None = None,
    target_inventory: str | Path = DEFAULT_TARGET_INVENTORY,
) -> dict[str, Any]:
    root = _safe_project_root(project_root)
    target = (
        copy.deepcopy(target)
        if target is not None
        else load_install_target(runtime_id, target_inventory)
    )
    marker_relative = _marker_path(target, runtime_id)
    marker, marker_digest = _read_marker(
        root,
        marker_relative,
        runtime_id=runtime_id,
        scope="PROJECT",
        target_root=_target_root(target, runtime_id),
    )
    if marker is None or marker.get("transaction_id") != transaction_id:
        raise InstallerError(
            "REVERT_UNAVAILABLE: requested transaction is not the current managed transaction"
        )
    entries, conflicts = _revert_entries(root, marker)
    package = {
        "schema_version": "3.0",
        "package_version": INSTALLER_VERSION,
        "package_digest": marker["package_digest"],
        "plan_digest": marker.get(
            "plan_digest", digest_value({"marker": marker["package_digest"]})
        ),
        "runtime_id": runtime_id,
        "scope": "PROJECT",
        "project_root_reference": _project_reference(root, "PROJECT"),
        "project_root_digest": _project_identity(root),
        "snapshot_digest": marker.get(
            "snapshot_digest", digest_value({"marker": marker["package_digest"]})
        ),
        "runtime_contract_digest": marker.get("runtime_contract_digest"),
        "install_target_digest": marker.get(
            "install_target_digest", digest_value({"runtime": runtime_id})
        ),
        "source_manifest_digest": marker.get(
            "source_manifest_digest", digest_value({"marker": marker["package_digest"]})
        ),
        "marker_digest": marker_digest,
        "marker_path": marker_relative,
        "artifacts": [],
        "excluded_artifacts": [],
        "installable": False,
        "apply_allowed": False,
        "warnings": [],
    }
    if conflicts:
        return _result(
            package=package,
            status="CONFLICT",
            transaction_id=transaction_id,
            attempted=[item["path"] for item in entries],
            conflicts=conflicts,
        )
    new_transaction = _new_transaction_id()
    stage_dir = Path(tempfile.mkdtemp(prefix=".asm-revert-", dir=root))
    changed: list[tuple[Path, bytes | None]] = []
    old_marker_bytes = _path_within(root, marker_relative).read_bytes()
    completed: list[str] = []
    try:
        for index, entry in enumerate(entries):
            if entry["action"] == "NO_OP":
                continue
            destination = _path_within(root, entry["path"])
            current = destination.read_bytes()
            if entry["action"] == "DELETE_CREATED":
                _safe_unlink(destination, expected_digest=digest_bytes(current))
                changed.append((destination, current))
            else:
                backup = entry["backup"]
                backup_path = _path_within(root, backup["backup_path"])
                previous = backup_path.read_bytes()
                if digest_bytes(previous) != backup["backup_digest"]:
                    raise InstallerError("REVERT_UNAVAILABLE: backup digest mismatch")
                staged = _write_staged(stage_dir, f"restore/{index}.bin", previous)
                os.replace(staged, destination)
                changed.append((destination, current))
            completed.append(entry["path"])
        previous_marker = marker.get("previous_marker_backup")
        marker_path = _path_within(root, marker_relative)
        if previous_marker:
            previous_path = _path_within(root, previous_marker["path"])
            previous_bytes = previous_path.read_bytes()
            if digest_bytes(previous_bytes) != previous_marker["digest"]:
                raise InstallerError(
                    "REVERT_UNAVAILABLE: previous marker backup mismatch"
                )
            staged_marker = _write_staged(
                stage_dir, "restore/marker.json", previous_bytes
            )
            os.replace(staged_marker, marker_path)
        else:
            _safe_unlink(marker_path, expected_digest=marker_digest)
        _transaction_record(
            root,
            runtime_id=runtime_id,
            transaction_id=new_transaction,
            package_digest=marker["package_digest"],
            status="REVERTED",
            actions=completed + [marker_relative],
            rollback_status="NOT_NEEDED",
            created_directories=[],
        )
        return _result(
            package=package,
            status="REVERTED",
            transaction_id=new_transaction,
            attempted=completed + [marker_relative],
            completed=completed + [marker_relative],
            rollback_status="NOT_NEEDED",
        )
    except Exception as exc:
        rollback_failed = False
        try:
            for destination, old_bytes in reversed(changed):
                restore = _write_staged(
                    stage_dir, f"rollback/{destination.name}.bin", old_bytes
                )
                os.replace(restore, destination)
            restore_marker = _write_staged(
                stage_dir, "rollback/marker.json", old_marker_bytes
            )
            os.replace(restore_marker, _path_within(root, marker_relative))
        except Exception:
            rollback_failed = True
        return _result(
            package=package,
            status="PARTIAL" if rollback_failed else "ROLLED_BACK",
            transaction_id=new_transaction,
            attempted=completed + [marker_relative],
            completed=completed if rollback_failed else [],
            warnings=[f"revert failed: {type(exc).__name__}"],
            rollback_status="FAILED" if rollback_failed else "SUCCEEDED",
        )
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)


def detect_runtime(
    runtime_id: str,
    *,
    target: dict[str, Any] | None = None,
    executable: str | Path | None = None,
    timeout: float = 2.0,
    runner: Callable[..., Any] = subprocess.run,
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, Any]:
    """Probe only a runtime's safe version surface; never auth/doctor/run."""

    target = target or {"runtime_id": runtime_id, "supported_runtime_version": None}
    command = str(executable or RUNTIME_EXECUTABLES.get(runtime_id, runtime_id))
    resolved = command if Path(command).is_absolute() else which(command)
    result: dict[str, Any] = {
        "runtime_id": runtime_id,
        "executable_available": bool(resolved),
        "observed_runtime_version": None,
        "supported_runtime_version": target.get("supported_runtime_version"),
        "contract_status": "NOT_DETECTED",
        "installable": False,
        "probe": "VERSION_ONLY",
        "output_sanitized": True,
    }
    if not resolved:
        result["contract_status"] = "NOT_INSTALLED"
        return result
    try:
        completed = runner(
            [resolved, "--version"],
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        result["contract_status"] = "PROBE_TIMEOUT"
        return result
    except OSError:
        result["contract_status"] = "PROBE_FAILED"
        return result
    expected = target.get("supported_runtime_version")
    if completed.returncode != 0:
        result["contract_status"] = "PROBE_FAILED"
        return result
    # Keep only a version that matches the pinned target.  Raw stdout/stderr
    # are intentionally never returned or persisted.
    if expected and re.search(
        rf"(?<![0-9A-Za-z])v?{re.escape(str(expected))}(?![0-9A-Za-z])",
        str(completed.stdout),
    ):
        result["observed_runtime_version"] = expected
        result["contract_status"] = "VERIFIED"
        result["installable"] = (
            target.get("support_status") == "HOST_MANAGED"
            and target.get("copy_support") == "VERIFIED"
            and isinstance(target.get("destination_root_template"), str)
        )
    else:
        result["contract_status"] = "UNVERIFIED_INSTALL_CONTRACT"
    return result


class Installer:
    """Small façade around the pure package and bounded mutation functions."""

    def __init__(
        self, *, target_inventory: str | Path = DEFAULT_TARGET_INVENTORY
    ) -> None:
        self.target_inventory = Path(target_inventory)

    def target(self, runtime_id: str) -> dict[str, Any]:
        return load_install_target(runtime_id, self.target_inventory)

    def package(
        self,
        distribution_dir: str | Path,
        plan: dict[str, Any],
        runtime_status: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs.setdefault("target_inventory", self.target_inventory)
        return build_install_package(distribution_dir, plan, runtime_status, **kwargs)

    def preview(self, package: dict[str, Any]) -> dict[str, Any]:
        return preview_install(package)

    def apply(
        self,
        package: dict[str, Any],
        distribution_dir: str | Path,
        project_root: str | Path,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs.setdefault("target_inventory", self.target_inventory)
        return apply_install_package(package, distribution_dir, project_root, **kwargs)


def _status_for(
    runtime_id: str, *, inventory: str | Path, fixture: str
) -> dict[str, Any]:
    loaded = load_runtime_inventory(inventory, fixture_name=fixture)
    for status in loaded["runtimes"]:
        if status["runtime_id"] == runtime_id:
            return status
    raise InstallerError(f"runtime is absent from inventory fixture: {runtime_id}")


def _load_snapshot() -> RoutingCatalogSnapshot:
    return RoutingCatalogSnapshot.from_registry(
        ROOT / ".superpowers" / "SKILLS_INDEX.json",
        overlay_path=ROOT / "registry" / "v3" / "skill-routing-metadata.json",
        repository_root=ROOT,
    )


def _compile_for_cli(
    status: dict[str, Any], *, distribution: Path | None, project_root: Path | None
) -> tuple[tempfile.TemporaryDirectory[str] | None, Path, dict[str, Any]]:
    if distribution is not None:
        if not distribution.is_dir():
            raise InstallerError(
                "--distribution must point to an existing generated directory"
            )
        plan = build_installation_plan(runtime_status=status, snapshot=_load_snapshot())
        return None, distribution, plan
    holder = tempfile.TemporaryDirectory(prefix="asm-installer-distribution-")
    output = Path(holder.name)
    compiled = compile_distribution(
        runtime_status=status,
        snapshot=_load_snapshot(),
        output_dir=output,
        repository_root=ROOT,
    )
    if compiled.get("artifact_manifest") is None:
        raise InstallerError(
            "runtime has no static distribution; status-only preview applies"
        )
    return holder, output, compiled["plan"]


def _render_package_text(
    status: dict[str, Any],
    package: dict[str, Any],
    result: dict[str, Any],
    *,
    project: str | None,
) -> str:
    actions = [
        f"{item['action']} {item['destination_path']}"
        for item in package.get("artifacts", [])
    ]
    lines = [
        "Agent Skills Matrix v3",
        f"Runtime: {status.get('runtime_name', status.get('runtime_id'))} {status.get('observed_runtime_version') or 'UNKNOWN'}",
        f"Install contract: {'VERIFIED' if package.get('installable') else 'UNVERIFIED'}",
        f"Scope: {package.get('scope')}",
        f"Project: {project or 'not supplied (preview-only scope)'}",
        "Actions:",
        *(f"  {item}" for item in actions),
        f"Conflicts: {', '.join(result.get('conflicts', [])) or '0'}",
        f"Static integration: {'READY' if package.get('installable') else 'NOT_IMPLEMENTED / PREVIEW_ONLY'}",
        f"Live execution: {status.get('live_execution', 'UNKNOWN')}",
        "No changes were made."
        if result.get("status") == "PREVIEWED"
        else f"Result: {result.get('status')}",
    ]
    if package.get("warnings"):
        lines.extend(
            ["Warnings:", *(f"  {warning}" for warning in package["warnings"])]
        )
    return "\n".join(lines)


def _render_user_scope_text(
    status: dict[str, Any], preview: dict[str, Any], result: dict[str, Any]
) -> str:
    """Render a symbolic USER preview without exposing a real home path."""

    target = preview.get("runtime_target", {})
    lines = [
        "Agent Skills Matrix v3",
        f"Runtime: {status.get('runtime_name', status.get('runtime_id'))} {status.get('observed_runtime_version') or 'UNKNOWN'}",
        f"Install contract: {preview.get('support_classification', target.get('support_classification', 'UNKNOWN'))}",
        "Scope: USER",
        f"Platform: {preview.get('platform', 'UNKNOWN')}",
        f"Strategy: {preview.get('distribution_strategy', 'UNSUPPORTED')} ({preview.get('strategy_support', 'UNKNOWN')})",
        f"Destination: {target.get('selected_destination') or 'none'}",
        f"Planned managed paths: {len(preview.get('planned_managed_paths', []))}",
        f"Collisions: {preview.get('collisions', {}).get('note', 'UNKNOWN')}",
        f"Static integration: {target.get('support_classification', 'UNKNOWN')}",
        f"Live execution: {status.get('live_execution', 'UNKNOWN')}",
        "No changes were made.",
    ]
    if preview.get("warnings"):
        lines.extend(["Warnings:", *(f"  {item}" for item in preview["warnings"])])
    if result.get("status") != "PREVIEWED":
        lines.append(f"Result: {result.get('status', 'UNKNOWN')}")
    return "\n".join(lines)


def _load_user_package_file(path: Path) -> dict[str, Any]:
    """Load one host-created USER package without following package links."""

    if path.is_symlink() or not path.is_file():
        raise InstallerError("USER InstallPackage file is unavailable")
    package = _read_json(path)
    _validate_user_package(package)
    return package


def _user_cli_confirmation(
    package: dict[str, Any],
    *,
    home_root: Path | None,
    asm_user_data_root: Path | None,
    supplied_digest: str | None,
) -> dict[str, Any]:
    """Require an explicit package-bound CLI confirmation before mutation."""

    if supplied_digest != package.get("package_digest"):
        raise InstallerError("USER_CONFIRMATION_REQUIRED")
    return build_user_confirmation(
        package,
        home_root=home_root,
        asm_user_data_root=asm_user_data_root,
    )


def _render_user_package_text(
    package: dict[str, Any], result: dict[str, Any], *, status: dict[str, Any]
) -> str:
    return _render_package_text(status, package, result, project=None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Agent Skills Matrix v3 safe project installer"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_parser = subparsers.add_parser("detect")
    detect_parser.add_argument("--runtime", required=True)
    detect_parser.add_argument(
        "--inventory",
        type=Path,
        default=ROOT / "fixtures/v3/productization/runtime-inventory-v1.json",
    )
    detect_parser.add_argument("--targets", type=Path, default=DEFAULT_TARGET_INVENTORY)
    detect_parser.add_argument("--fixture", default="ALL_KNOWN_STATIC")
    detect_parser.add_argument("--executable", type=Path)
    detect_parser.add_argument("--format", choices=("text", "json"), default="text")

    for command in ("preview", "apply"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--runtime", required=True)
        command_parser.add_argument(
            "--scope", choices=("project", "user", "global"), default="project"
        )
        command_parser.add_argument("--project", type=Path)
        command_parser.add_argument("--home-root", type=Path)
        command_parser.add_argument("--asm-user-data-root", type=Path)
        command_parser.add_argument("--package", type=Path)
        command_parser.add_argument("--confirm-package-digest")
        command_parser.add_argument(
            "--strategy", choices=("managed-copy", "MANAGED_COPY"), default=None
        )
        command_parser.add_argument("--distribution", type=Path)
        command_parser.add_argument(
            "--platform", choices=("linux", "macos", "windows"), default="macos"
        )
        command_parser.add_argument(
            "--inventory",
            type=Path,
            default=ROOT / "fixtures/v3/productization/runtime-inventory-v1.json",
        )
        command_parser.add_argument(
            "--targets", type=Path, default=DEFAULT_TARGET_INVENTORY
        )
        command_parser.add_argument("--fixture", default="ALL_KNOWN_STATIC")
        command_parser.add_argument(
            "--format", choices=("text", "json"), default="text"
        )

    for command in ("uninstall", "revert"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--runtime", required=True)
        command_parser.add_argument(
            "--scope", choices=("project", "user", "global"), default="project"
        )
        command_parser.add_argument("--project", type=Path)
        command_parser.add_argument("--home-root", type=Path)
        command_parser.add_argument("--asm-user-data-root", type=Path)
        command_parser.add_argument("--confirm-package-digest")
        command_parser.add_argument(
            "--strategy", choices=("managed-copy", "MANAGED_COPY"), default=None
        )
        command_parser.add_argument(
            "--targets", type=Path, default=DEFAULT_TARGET_INVENTORY
        )
        command_parser.add_argument("--apply", action="store_true")
        command_parser.add_argument(
            "--format", choices=("text", "json"), default="text"
        )
        if command == "revert":
            command_parser.add_argument("--transaction", required=True)

    package_parser = subparsers.add_parser("package")
    package_parser.add_argument("--runtime", required=True)
    package_parser.add_argument("--scope", choices=("user",), default="user")
    package_parser.add_argument("--home-root", type=Path, required=True)
    package_parser.add_argument("--asm-user-data-root", type=Path, required=True)
    package_parser.add_argument("--output", type=Path, required=True)
    package_parser.add_argument(
        "--strategy", choices=("managed-copy", "MANAGED_COPY"), default="managed-copy"
    )
    package_parser.add_argument(
        "--inventory",
        type=Path,
        default=ROOT / "fixtures/v3/productization/runtime-inventory-v1.json",
    )
    package_parser.add_argument("--fixture", default="ALL_KNOWN_STATIC")
    package_parser.add_argument("--format", choices=("text", "json"), default="text")

    recover_parser = subparsers.add_parser("recover")
    recover_parser.add_argument("--runtime", default=CLAUDE_RUNTIME_ID)
    recover_parser.add_argument("--scope", choices=("user",), default="user")
    recover_parser.add_argument("--home-root", type=Path, required=True)
    recover_parser.add_argument("--asm-user-data-root", type=Path, required=True)
    recover_parser.add_argument("--transaction", required=True)
    recover_parser.add_argument("--format", choices=("text", "json"), default="text")

    args = parser.parse_args(argv)
    try:
        if args.command == "detect":
            target = load_install_target(args.runtime, args.targets)
            result = detect_runtime(
                args.runtime, target=target, executable=args.executable
            )
            if args.format == "json":
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
            else:
                print(f"Runtime: {args.runtime}")
                print(f"Executable available: {result['executable_available']}")
                print(
                    f"Observed version: {result['observed_runtime_version'] or 'UNKNOWN'}"
                )
                print(f"Install contract: {result['contract_status']}")
            return 0 if result["contract_status"] == "VERIFIED" else 2

        if args.command == "package":
            strategy = str(args.strategy).replace("-", "_").upper()
            if args.runtime != CLAUDE_RUNTIME_ID or strategy != USER_SCOPE_STRATEGY:
                raise InstallerError(
                    "Phase 3N package supports Claude Code USER MANAGED_COPY only"
                )
            status = _status_for(
                args.runtime, inventory=args.inventory, fixture=args.fixture
            )
            target = build_claude_user_target(status, strategy=USER_SCOPE_STRATEGY)
            package = build_user_install_package(
                _load_snapshot(),
                status,
                home_root=args.home_root,
                asm_user_data_root=args.asm_user_data_root,
                repository_root=ROOT,
                target=target,
            )
            _write_json_atomic(args.output, package)
            result = {
                "status": "PACKAGED",
                "package_digest": package["package_digest"],
                "output": str(args.output),
                "runtime_id": package["runtime_id"],
                "scope": package["scope"],
                "artifact_count": len(package.get("artifacts", [])),
                "sensitive_data_serialized": False,
            }
            if args.format == "json":
                print(
                    json.dumps(
                        {"package": package, "result": result},
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    )
                )
            else:
                print(
                    "Agent Skills Matrix v3\n"
                    "Operation: package\n"
                    f"Runtime: {package['runtime_id']} {package['runtime_version']}\n"
                    "Scope: USER\n"
                    f"Artifacts: {len(package.get('artifacts', []))}\n"
                    f"Package digest: {package['package_digest']}\n"
                    f"Output: {args.output}\n"
                    "No runtime or provider was invoked."
                )
            return 0

        if args.command == "recover":
            if args.runtime != CLAUDE_RUNTIME_ID or normalize_scope(args.scope) != "USER":
                raise InstallerError(
                    "recovery is only implemented for Claude Code USER scope"
                )
            result = recover_user_transaction(
                args.transaction,
                home_root=args.home_root,
                asm_user_data_root=args.asm_user_data_root,
            )
            if args.format == "json":
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
            else:
                print(
                    "Agent Skills Matrix v3\n"
                    "Operation: recover\n"
                    f"Transaction: {result['transaction_id']}\n"
                    f"Decision: {result['decision']}\n"
                    f"Final phase: {result['final_phase']}"
                )
            return 0 if result["decision"] != "MANUAL_CONFLICT" else 2

        if args.command in {"uninstall", "revert"}:
            scope = normalize_scope(args.scope)
            if scope == "USER":
                if args.runtime != CLAUDE_RUNTIME_ID:
                    raise InstallerError(
                        "USER uninstall/revert is only implemented for Claude Code"
                    )
                if args.home_root is None or args.asm_user_data_root is None:
                    raise InstallerError(USER_SCOPE_APPLY_NOT_AUTHORIZED)
                if args.apply and (
                    str(args.strategy).replace("-", "_").upper()
                    != USER_SCOPE_STRATEGY
                ):
                    raise InstallerError(USER_SCOPE_APPLY_NOT_AUTHORIZED)
                if args.command == "uninstall":
                    package = build_user_uninstall_package(
                        home_root=args.home_root,
                        asm_user_data_root=args.asm_user_data_root,
                    )
                    status = _claude_fixture_status()
                    if args.apply:
                        confirmation = _user_cli_confirmation(
                            package,
                            home_root=args.home_root,
                            asm_user_data_root=args.asm_user_data_root,
                            supplied_digest=args.confirm_package_digest,
                        )
                        result = apply_user_uninstall_package(
                            package,
                            home_root=args.home_root,
                            asm_user_data_root=args.asm_user_data_root,
                            confirmation=confirmation,
                        )
                    else:
                        result = preview_install(package)
                else:
                    if args.transaction is None:
                        raise InstallerError(
                            "USER revert requires an explicit transaction id"
                        )
                    package = build_user_revert_package(
                        home_root=args.home_root,
                        asm_user_data_root=args.asm_user_data_root,
                        transaction_id=args.transaction,
                    )
                    status = _claude_fixture_status()
                    if args.apply:
                        confirmation = _user_cli_confirmation(
                            package,
                            home_root=args.home_root,
                            asm_user_data_root=args.asm_user_data_root,
                            supplied_digest=args.confirm_package_digest,
                        )
                        result = apply_user_revert_package(
                            package,
                            home_root=args.home_root,
                            asm_user_data_root=args.asm_user_data_root,
                            confirmation=confirmation,
                        )
                    else:
                        result = preview_install(package)
                if args.format == "json":
                    print(
                        json.dumps(
                            {"package": package, "result": result},
                            ensure_ascii=False,
                            sort_keys=True,
                            indent=2,
                        )
                    )
                else:
                    print(_render_user_package_text(package, result, status=status))
                return 0 if result.get("status") in {
                    "PREVIEWED",
                    "UNINSTALLED",
                    "REVERTED",
                    "NO_OP",
                } else 2
            if scope != "PROJECT":
                raise InstallerError(
                    "user/global apply is deferred; only PROJECT scope is supported"
                )
            if args.command == "uninstall":
                result = (
                    apply_uninstall(
                        runtime_id=args.runtime,
                        project_root=args.project,
                        target_inventory=args.targets,
                    )
                    if args.apply
                    else preview_uninstall(
                        runtime_id=args.runtime,
                        project_root=args.project,
                        target_inventory=args.targets,
                    )
                )
            else:
                result = (
                    apply_revert(
                        runtime_id=args.runtime,
                        project_root=args.project,
                        transaction_id=args.transaction,
                        target_inventory=args.targets,
                    )
                    if args.apply
                    else preview_revert(
                        runtime_id=args.runtime,
                        project_root=args.project,
                        transaction_id=args.transaction,
                        target_inventory=args.targets,
                    )
                )
            if args.format == "json":
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
            else:
                print(
                    f"Agent Skills Matrix v3\nOperation: {args.command}\nStatus: {result.get('status', 'UNKNOWN')}\nConflicts: {', '.join(result.get('conflicts', [])) or '0'}"
                )
            return (
                0
                if result.get("status")
                in {"PREVIEWED", "UNINSTALLED", "REVERTED", "NO_OP"}
                else 2
            )

        scope = normalize_scope(args.scope)
        if args.command == "apply" and scope == "USER":
            if (
                args.runtime != CLAUDE_RUNTIME_ID
                or str(args.strategy).replace("-", "_").upper() != USER_SCOPE_STRATEGY
                or args.home_root is None
                or args.asm_user_data_root is None
                or args.package is None
                or args.confirm_package_digest is None
            ):
                raise InstallerError(USER_SCOPE_APPLY_NOT_AUTHORIZED)
            package = _load_user_package_file(args.package)
            if package.get("runtime_id") != CLAUDE_RUNTIME_ID:
                raise InstallerError(USER_SCOPE_APPLY_NOT_AUTHORIZED)
            confirmation = _user_cli_confirmation(
                package,
                home_root=args.home_root,
                asm_user_data_root=args.asm_user_data_root,
                supplied_digest=args.confirm_package_digest,
            )
            result = apply_user_install_package(
                package,
                home_root=args.home_root,
                asm_user_data_root=args.asm_user_data_root,
                repository_root=ROOT,
                confirmation=confirmation,
            )
            status = _claude_fixture_status()
            if args.format == "json":
                print(
                    json.dumps(
                        {"package": package, "result": result},
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    )
                )
            else:
                print(_render_user_package_text(package, result, status=status))
            return 0 if result.get("status") in {"APPLIED", "NO_OP"} else 2
        status = _status_for(
            args.runtime, inventory=args.inventory, fixture=args.fixture
        )
        if args.command == "preview" and scope == "USER":
            if args.runtime == "claude-code":
                preview = build_claude_user_preview(
                    status,
                    _load_snapshot(),
                    platform=args.platform,
                )
            else:
                preview = build_user_scope_preview(
                    status,
                    _load_snapshot(),
                    contract=load_user_scope_contract(),
                    platform=args.platform,
                )
            result = {
                "status": "PREVIEWED",
                "runtime_id": status["runtime_id"],
                "scope": "USER",
                "preview_digest": preview["preview_digest"],
                "warnings": preview["warnings"],
                "conflicts": [],
                "no_actual_writes": True,
            }
            if args.format == "json":
                print(
                    json.dumps(
                        {"preview": preview, "result": result},
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    )
                )
            else:
                print(_render_user_scope_text(status, preview, result))
            return 0
        if args.command == "apply" and scope != "PROJECT":
            raise InstallerError(
                "user/global apply is deferred; only PROJECT scope is supported"
            )
        if (
            status.get("adapter_support") == "NOT_IMPLEMENTED"
            or status.get("static_contract") != "VERIFIED"
        ):
            package = build_status_only_package(
                status,
                scope=scope,
                project_root=args.project,
                target_inventory=args.targets,
            )
            if args.command == "preview":
                result = preview_install(package)
            else:
                if args.project is None:
                    raise InstallerError("apply requires an explicit --project root")
                result = _result(
                    package=package,
                    status="ABORTED",
                    transaction_id="aborted-" + package["package_digest"][7:19],
                    warnings=package["warnings"]
                    + ["no static adapter exists; no filesystem mutation occurred"],
                )
            if args.format == "json":
                print(
                    json.dumps(
                        {"package": package, "result": result},
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    )
                )
            else:
                print(
                    _render_package_text(
                        status,
                        package,
                        result,
                        project=str(args.project) if args.project else None,
                    )
                )
            return 0 if result.get("status") == "PREVIEWED" else 2
        holder, distribution, plan = _compile_for_cli(
            status, distribution=args.distribution, project_root=args.project
        )
        try:
            package = build_install_package(
                distribution,
                plan,
                status,
                scope=scope,
                project_root=args.project,
                target_inventory=args.targets,
            )
            if args.command == "preview":
                result = preview_install(package)
            else:
                if args.project is None:
                    raise InstallerError("apply requires an explicit --project root")
                result = apply_install_package(
                    package, distribution, args.project, target_inventory=args.targets
                )
            if args.format == "json":
                print(
                    json.dumps(
                        {"package": package, "result": result},
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    )
                )
            else:
                print(
                    _render_package_text(
                        status,
                        package,
                        result,
                        project=str(args.project) if args.project else None,
                    )
                )
            return 0 if result.get("status") in {"PREVIEWED", "APPLIED", "NO_OP"} else 2
        finally:
            if holder is not None:
                holder.cleanup()
    except (InstallerError, ProductizationError, UserScopeError) as exc:
        if getattr(args, "format", "text") == "json":
            print(
                json.dumps(
                    {"status": "BLOCKED", "error": str(exc)},
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            print(f"BLOCKED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
