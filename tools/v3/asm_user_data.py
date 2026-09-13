"""Generic, path-safe ASM user-data destination contract.

The resolver is intentionally read-only.  It computes the platform-native
product-owned data root and records enough path-free identity information for
a later package/apply boundary to revalidate it.  It never creates the root.
"""

from __future__ import annotations

import os
import platform as host_platform
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from tools.v3.productization import ROOT, digest_value


ASM_USER_DATA_CONTRACT_VERSION = "1.0"
ASM_USER_DATA_SYMBOLIC_ROOT = "${ASM_USER_DATA}"
ASM_PRODUCT_DIRECTORY = "Agent Skills Matrix"
ASM_CONTRACT_PATH = ROOT / "fixtures" / "v3" / "productization" / "asm-user-data-contract-v1.json"


class ASMUserDataError(ValueError):
    """Raised when a user-data destination cannot be proven safe."""


class ASMUserDataStaleError(ASMUserDataError):
    """Raised when a previously previewed destination no longer matches."""


def _normalize_platform(value: str | None) -> str:
    if value is None:
        value = host_platform.system().lower()
    normalized = str(value).strip().lower()
    aliases = {
        "darwin": "macos",
        "mac": "macos",
        "macos": "macos",
        "linux": "linux",
        "win32": "windows",
        "windows": "windows",
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ASMUserDataError(f"unsupported ASM user-data platform: {value}") from exc


def _contract_document() -> dict[str, object]:
    try:
        import json

        value = json.loads(ASM_CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ASMUserDataError("ASM user-data contract cannot be loaded") from exc
    if not isinstance(value, dict):
        raise ASMUserDataError("ASM user-data contract is not an object")
    expected = dict(value)
    recorded = expected.pop("contract_digest", None)
    if not isinstance(recorded, str) or recorded != digest_value(expected):
        raise ASMUserDataError("ASM user-data contract digest is invalid")
    if expected.get("contract_version") != ASM_USER_DATA_CONTRACT_VERSION:
        raise ASMUserDataError("unsupported ASM user-data contract version")
    if expected.get("product_directory") != ASM_PRODUCT_DIRECTORY:
        raise ASMUserDataError("ASM user-data product directory is invalid")
    platforms = expected.get("platforms")
    if not isinstance(platforms, dict) or set(platforms) != {"macos", "linux", "windows"}:
        raise ASMUserDataError("ASM user-data contract platform matrix is invalid")
    return value


def _lstat(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ASMUserDataError(f"cannot inspect ASM user-data path: {type(exc).__name__}") from exc


def _safe_home(home_root: str | Path | None) -> tuple[Path, bool]:
    explicit = home_root is not None
    raw = Path.home() if home_root is None else Path(home_root)
    if not raw.is_absolute():
        raise ASMUserDataError("home_root must be absolute")
    stat = _lstat(raw)
    if stat is None or not raw.is_dir() or raw.is_symlink():
        raise ASMUserDataError("home_root must be an existing non-symlink directory")
    try:
        resolved = raw.resolve(strict=True)
        actual_home = Path.home().resolve(strict=True)
    except OSError as exc:
        raise ASMUserDataError(f"cannot resolve home_root: {type(exc).__name__}") from exc
    if resolved == Path(resolved.anchor):
        raise ASMUserDataError("home_root must not be a filesystem root")
    return resolved, explicit and resolved != actual_home


def _candidate_path(
    home: Path,
    *,
    platform_name: str,
    environ: Mapping[str, str] | None,
) -> tuple[Path, str]:
    env = dict(os.environ if environ is None else environ)
    if platform_name == "macos":
        return home / "Library" / "Application Support" / ASM_PRODUCT_DIRECTORY, (
            "${HOME}/Library/Application Support/Agent Skills Matrix"
        )
    if platform_name == "linux":
        xdg = env.get("XDG_DATA_HOME")
        if xdg:
            candidate = Path(xdg)
            if not candidate.is_absolute():
                raise ASMUserDataError("XDG_DATA_HOME must be absolute")
            return candidate / "agent-skills-matrix", "${XDG_DATA_HOME}/agent-skills-matrix"
        return home / ".local" / "share" / "agent-skills-matrix", (
            "${HOME}/.local/share/agent-skills-matrix"
        )
    local_app_data = env.get("LOCALAPPDATA")
    if local_app_data:
        candidate = Path(local_app_data)
        if not candidate.is_absolute():
            raise ASMUserDataError("LOCALAPPDATA must be absolute")
        return candidate / ASM_PRODUCT_DIRECTORY, "${LOCALAPPDATA}/Agent Skills Matrix"
    return home / "AppData" / "Local" / ASM_PRODUCT_DIRECTORY, (
        "${HOME}/AppData/Local/Agent Skills Matrix"
    )


def _path_components(path: Path) -> list[Path]:
    current = Path(path.anchor)
    result: list[Path] = []
    for part in path.parts[1:]:
        current /= part
        result.append(current)
    return result


def _validate_components(path: Path, *, home: Path) -> Path | None:
    """Reject symlinks/non-directory parents and return nearest existing parent."""

    nearest: Path | None = None
    for component in _path_components(path):
        stat = _lstat(component)
        if stat is None:
            continue
        if component.is_symlink():
            raise ASMUserDataError("ASM user-data path contains a symlink component")
        if not component.is_dir():
            raise ASMUserDataError("ASM user-data parent is not a directory")
        nearest = component
    if nearest is None:
        raise ASMUserDataError("ASM user-data path has no inspectable parent")
    try:
        path.relative_to(home)
    except ValueError:
        # Linux/Windows environment overrides can be outside HOME, but must
        # remain within an explicitly supplied native user-data base.
        if path == home or home in path.parents:
            raise ASMUserDataError("ASM user-data path is not in a valid user-data domain")
    return nearest


def _runtime_owned(path: Path) -> bool:
    runtime_markers = (
        ".claude",
        ".codex",
        ".hermes",
        ".config/opencode",
        ".config/claude",
    )
    text = path.as_posix().lower()
    return any(marker in text for marker in runtime_markers)


def _identity(
    *,
    path: Path,
    label: str,
    state: str,
    contract_digest: str,
    symbolic_root: str,
) -> str:
    stat = _lstat(path)
    if stat is None:
        return digest_value(
            {
                "label": label,
                "state": state,
                "contract_digest": contract_digest,
                "symbolic_root": symbolic_root,
            }
        )
    return digest_value(
        {
            "label": label,
            "state": state,
            "device": int(stat.st_dev),
            "inode": int(stat.st_ino),
            "mode": int(stat.st_mode),
            "is_directory": path.is_dir(),
            "contract_digest": contract_digest,
            "symbolic_root": symbolic_root,
        }
    )


@dataclass(frozen=True)
class ASMUserDataResolution:
    """Ephemeral resolution plus path-free revalidation evidence."""

    platform: str
    symbolic_root: str
    resolution_rule: str
    resolved_path: Path
    parent_path: Path
    home_path: Path
    state: str
    root_identity: str
    parent_identity: str
    home_identity: str
    contract_digest: str
    contract_version: str
    fixture_mode: bool

    def to_public_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "contract_digest": self.contract_digest,
            "platform": self.platform,
            "symbolic_root": self.symbolic_root,
            "resolution_rule": self.resolution_rule,
            "state": self.state,
            "expected_state": self.state,
            "root_identity": self.root_identity,
            "parent_identity": self.parent_identity,
            "home_identity": self.home_identity,
            "fixture_mode": self.fixture_mode,
            "safe": True,
            "writes_performed": False,
            "actual_path_persisted": False,
        }


@dataclass(frozen=True)
class ASMUserDataPathObservation:
    """Ephemeral observation for one exact managed path under ASM data."""

    relative_path: str
    resolved_path: Path
    state: str
    identity: str

    def to_public_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "symbolic_path": f"{ASM_USER_DATA_SYMBOLIC_ROOT}/{self.relative_path}",
            "state": self.state,
            "identity": self.identity,
            "actual_path_persisted": False,
        }


def observe_asm_user_data_path(
    resolution: ASMUserDataResolution,
    relative_path: str | Path,
) -> ASMUserDataPathObservation:
    """Check one exact subpath without creating or following symlinks."""

    raw = relative_path.as_posix() if isinstance(relative_path, Path) else str(relative_path)
    safe = Path(raw)
    if (
        not raw
        or safe.is_absolute()
        or ".." in safe.parts
        or "\\" in raw
        or safe == Path(".")
        or any(part in {"", "."} for part in safe.parts)
    ):
        raise ASMUserDataError("ASM managed relative path is unsafe")
    candidate = resolution.resolved_path / safe
    try:
        candidate.relative_to(resolution.resolved_path)
    except ValueError as exc:
        raise ASMUserDataError("ASM managed path escapes the resolved root") from exc
    _validate_components(candidate, home=resolution.home_path)
    stat = _lstat(candidate)
    if stat is None:
        state = "EXPECTED_ABSENT"
    elif candidate.is_symlink():
        raise ASMUserDataError("ASM managed path contains a symlink")
    elif not candidate.is_dir():
        raise ASMUserDataError("ASM managed path is not a directory")
    else:
        state = "EXISTING_DIRECTORY"
    return ASMUserDataPathObservation(
        relative_path=safe.as_posix(),
        resolved_path=candidate,
        state=state,
        identity=_identity(
            path=candidate,
            label="ASM managed path",
            state=state,
            contract_digest=resolution.contract_digest,
            symbolic_root=f"{ASM_USER_DATA_SYMBOLIC_ROOT}/{safe.as_posix()}",
        ),
    )


def resolve_asm_user_data_root(
    *,
    home_root: str | Path | None = None,
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
    repository_root: str | Path = ROOT,
    allow_fixture_root: bool = False,
) -> ASMUserDataResolution:
    """Resolve the generic ASM root without creating it."""

    contract = _contract_document()
    platform_name = _normalize_platform(platform)
    home, is_fixture = _safe_home(home_root)
    if is_fixture and not allow_fixture_root:
        raise ASMUserDataError("fixture home is not allowed for the production contract")
    candidate, rule = _candidate_path(home, platform_name=platform_name, environ=environ)
    candidate = Path(os.path.abspath(candidate))
    repository = Path(repository_root).resolve(strict=True)
    if candidate == Path(candidate.anchor) or candidate == home:
        raise ASMUserDataError("ASM user-data root is too broad")
    if _runtime_owned(candidate):
        raise ASMUserDataError("ASM user-data root is runtime-owned")
    try:
        candidate.relative_to(repository)
    except ValueError:
        pass
    else:
        raise ASMUserDataError("ASM user-data root must not be inside the repository")
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not allow_fixture_root:
        try:
            candidate.relative_to(temp_root)
        except ValueError:
            pass
        else:
            raise ASMUserDataError("production ASM user-data root must not be temporary")
    parent = _validate_components(candidate, home=home)
    if parent is None:
        raise ASMUserDataError("ASM user-data parent is unavailable")
    candidate_stat = _lstat(candidate)
    if candidate_stat is None:
        state = "EXPECTED_ABSENT"
    elif candidate.is_symlink():
        raise ASMUserDataError("ASM user-data root must not be a symlink")
    elif not candidate.is_dir():
        raise ASMUserDataError("ASM user-data root must be a directory")
    else:
        state = "EXISTING_DIRECTORY"
    contract_digest = str(contract["contract_digest"])
    parent_identity = _identity(
        path=parent,
        label="ASM user-data parent",
        state="EXISTING_DIRECTORY",
        contract_digest=contract_digest,
        symbolic_root=ASM_USER_DATA_SYMBOLIC_ROOT,
    )
    return ASMUserDataResolution(
        platform=platform_name,
        symbolic_root=ASM_USER_DATA_SYMBOLIC_ROOT,
        resolution_rule=rule,
        resolved_path=candidate,
        parent_path=parent,
        home_path=home,
        state=state,
        root_identity=_identity(
            path=candidate,
            label="ASM user-data root",
            state=state,
            contract_digest=contract_digest,
            symbolic_root=ASM_USER_DATA_SYMBOLIC_ROOT,
        ),
        parent_identity=parent_identity,
        home_identity=_identity(
            path=home,
            label="HOME",
            state="EXISTING_DIRECTORY",
            contract_digest=contract_digest,
            symbolic_root="${HOME}",
        ),
        contract_digest=contract_digest,
        contract_version=str(contract["contract_version"]),
        fixture_mode=is_fixture,
    )


def revalidate_asm_user_data_root(
    resolution: ASMUserDataResolution,
    *,
    repository_root: str | Path = ROOT,
) -> ASMUserDataResolution:
    """Reinspect the exact resolved path and reject any stale state."""

    del repository_root  # The original resolution already bound the contract root.
    try:
        contract = _contract_document()
        contract_digest = str(contract["contract_digest"])
        if contract_digest != resolution.contract_digest:
            raise ASMUserDataStaleError("ASM user-data contract revision changed")
        parent = _validate_components(resolution.resolved_path, home=resolution.home_path)
        candidate_stat = _lstat(resolution.resolved_path)
        if candidate_stat is None:
            state = "EXPECTED_ABSENT"
        elif resolution.resolved_path.is_symlink():
            raise ASMUserDataStaleError("ASM user-data root became a symlink")
        elif not resolution.resolved_path.is_dir():
            raise ASMUserDataStaleError("ASM user-data root is no longer a directory")
        else:
            state = "EXISTING_DIRECTORY"
        if parent is None:
            raise ASMUserDataStaleError("ASM user-data parent is unavailable")
        refreshed = ASMUserDataResolution(
            platform=resolution.platform,
            symbolic_root=resolution.symbolic_root,
            resolution_rule=resolution.resolution_rule,
            resolved_path=resolution.resolved_path,
            parent_path=parent,
            home_path=resolution.home_path,
            state=state,
            root_identity=_identity(
                path=resolution.resolved_path,
                label="ASM user-data root",
                state=state,
                contract_digest=contract_digest,
                symbolic_root=ASM_USER_DATA_SYMBOLIC_ROOT,
            ),
            parent_identity=_identity(
                path=parent,
                label="ASM user-data parent",
                state="EXISTING_DIRECTORY",
                contract_digest=contract_digest,
                symbolic_root=ASM_USER_DATA_SYMBOLIC_ROOT,
            ),
            home_identity=_identity(
                path=resolution.home_path,
                label="HOME",
                state="EXISTING_DIRECTORY",
                contract_digest=contract_digest,
                symbolic_root="${HOME}",
            ),
            contract_digest=contract_digest,
            contract_version=resolution.contract_version,
            fixture_mode=resolution.fixture_mode,
        )
    except ASMUserDataStaleError:
        raise
    except ASMUserDataError as exc:
        raise ASMUserDataStaleError(f"ASM user-data resolution is stale: {exc}") from exc
    if (
        refreshed.resolved_path != resolution.resolved_path
        or refreshed.parent_path != resolution.parent_path
        or refreshed.state != resolution.state
        or refreshed.root_identity != resolution.root_identity
        or refreshed.parent_identity != resolution.parent_identity
        or refreshed.home_identity != resolution.home_identity
        or refreshed.contract_digest != resolution.contract_digest
    ):
        raise ASMUserDataStaleError("ASM user-data root identity or expected state changed")
    return refreshed
