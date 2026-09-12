"""Safe, project-scoped installer for the v3 static distribution.

The installer is deliberately separate from :mod:`productization`.  The
productization module compiles immutable, derived output and a dry-run plan;
this module is the only place that can apply a filtered persistent package to
an explicitly supplied project directory.

No runtime is started on import.  Runtime detection is a short ``--version``
probe and is performed only by the explicit ``detect``/``preview``/``apply``
command path when requested.
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
)
from tools.v3.routing_catalog import RoutingCatalogSnapshot
from tools.v3.user_scope import (
    USER_SCOPE_APPLY_NOT_AUTHORIZED,
    UserScopeError,
    build_user_scope_preview,
    load_user_scope_contract,
)
from tools.v3.claude_user_scope import build_claude_user_preview


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
    raw = str(value)
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
    if package.get("scope") != "PROJECT" and package.get("apply_allowed"):
        raise InstallerError("user/global InstallPackage cannot permit apply")
    for artifact in package.get("artifacts", []):
        if artifact.get("lifecycle") not in PERSISTENT_LIFECYCLES:
            raise InstallerError(
                "InstallPackage contains an execution-ephemeral artifact"
            )


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
    distribution_dir: str | Path,
    project_root: str | Path,
    *,
    target: dict[str, Any] | None = None,
    target_inventory: str | Path = DEFAULT_TARGET_INVENTORY,
    replace_fn: Callable[
        [str | os.PathLike[str], str | os.PathLike[str]], None
    ] = os.replace,
    rollback_replace_fn: Callable[
        [str | os.PathLike[str], str | os.PathLike[str]], None
    ] = os.replace,
) -> dict[str, Any]:
    """Apply a package with all-target preflight and bounded rollback."""

    if package.get("scope") == "USER":
        raise InstallerError(USER_SCOPE_APPLY_NOT_AUTHORIZED)
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
        command_parser.add_argument("--project", type=Path, required=True)
        command_parser.add_argument(
            "--targets", type=Path, default=DEFAULT_TARGET_INVENTORY
        )
        command_parser.add_argument("--apply", action="store_true")
        command_parser.add_argument(
            "--format", choices=("text", "json"), default="text"
        )
        if command == "revert":
            command_parser.add_argument("--transaction", required=True)

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
        if args.command in {"uninstall", "revert"}:
            scope = normalize_scope(args.scope)
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
            raise InstallerError(USER_SCOPE_APPLY_NOT_AUTHORIZED)
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
