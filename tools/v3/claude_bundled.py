"""Bounded non-inference bundled-skill evidence for Claude Code 2.1.235."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Iterable

from tools.v3.claude_user_scope import validate_claude_skill_slug
from tools.v3.productization import digest_value


CLAUDE_RUNTIME_VERSION = "2.1.235"
CLAUDE_ARTIFACT_SHA256 = (
    "sha256:83b8f806f6f2eea316cfe246628e6c23374711d868f1fd0409db551b877b7748"
)
KNOWN_BUNDLED_IDENTIFIERS = ("claude-code-guide",)
CALIBRATION_MARKERS = (
    "getBundledSkills",
    "getRegisteredBundledSkillsIgnoringKillSwitch",
    "registerBundledSkill",
    "getBundledSkillsRoot",
)
BUNDLED_COLLISION_NONE_VERIFIED = "BUNDLED_COLLISION_NONE_VERIFIED"
BUNDLED_COLLISION_PRESENT = "BUNDLED_COLLISION_PRESENT"
BUNDLED_COLLISION_UNKNOWN = "BUNDLED_COLLISION_UNKNOWN"


class ClaudeBundledEvidenceError(ValueError):
    """Raised when version-bound artifact evidence cannot be trusted."""


def resolve_installed_claude_artifact(
    artifact_path: str | Path | None = None,
) -> Path:
    """Resolve the installed versioned executable without executing it."""

    raw = Path(artifact_path) if artifact_path is not None else None
    if raw is None:
        located = shutil.which("claude")
        if not located:
            raise ClaudeBundledEvidenceError("installed Claude artifact is unavailable")
        raw = Path(located)
    if not raw.is_absolute():
        raise ClaudeBundledEvidenceError("Claude artifact path must be absolute")
    try:
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        raise ClaudeBundledEvidenceError("cannot resolve installed Claude artifact") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise ClaudeBundledEvidenceError("Claude artifact is not a regular file")
    return resolved


def _is_token_byte(value: int | None) -> bool:
    return value is not None and (
        48 <= value <= 57
        or 65 <= value <= 90
        or 97 <= value <= 122
        or value in {45, 95}
    )


def _token_present(buffer: bytes, token: bytes) -> bool:
    start = 0
    while True:
        index = buffer.find(token, start)
        if index < 0:
            return False
        before = buffer[index - 1] if index else None
        end = index + len(token)
        after = buffer[end] if end < len(buffer) else None
        if not _is_token_byte(before) and not _is_token_byte(after):
            return True
        start = index + 1


def _scan_tokens(path: Path, tokens: Iterable[str]) -> tuple[str, int, dict[str, bool]]:
    token_bytes = {token: token.encode("ascii") for token in tokens}
    found = {token: False for token in token_bytes}
    digest = hashlib.sha256()
    size = 0
    carry = b""
    width = max((len(value) for value in token_bytes.values()), default=1)
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                data = carry + chunk
                for token, encoded in token_bytes.items():
                    if not found[token] and _token_present(data, encoded):
                        found[token] = True
                carry = data[-(width - 1) :] if width > 1 else b""
    except OSError as exc:
        raise ClaudeBundledEvidenceError(
            f"cannot inspect Claude artifact: {type(exc).__name__}"
        ) from exc
    return "sha256:" + digest.hexdigest(), size, found


def inspect_claude_bundled_skills(
    *,
    artifact_path: str | Path,
    expected_artifact_sha256: str = CLAUDE_ARTIFACT_SHA256,
    candidate_slugs: Iterable[str] = (),
    known_bundled_identifiers: Iterable[str] = KNOWN_BUNDLED_IDENTIFIERS,
    calibration_markers: Iterable[str] = CALIBRATION_MARKERS,
) -> dict[str, object]:
    """Inspect only exact calibration/candidate tokens; persist no binary text."""

    path = resolve_installed_claude_artifact(artifact_path)
    candidates = tuple(dict.fromkeys(validate_claude_skill_slug(str(item)) for item in candidate_slugs))
    known = tuple(dict.fromkeys(str(item) for item in known_bundled_identifiers))
    markers = tuple(dict.fromkeys(str(item) for item in calibration_markers))
    tokens = tuple(dict.fromkeys((*known, *markers, *candidates)))
    observed, size, found = _scan_tokens(path, tokens)
    if observed != expected_artifact_sha256:
        raise ClaudeBundledEvidenceError(
            "Claude artifact fingerprint changed; runtime requalification is required"
        )
    recovered_markers = sorted(token for token in markers if found.get(token))
    recovered_known = sorted(token for token in known if found.get(token))
    calibration_passed = bool(markers) and set(recovered_markers) == set(markers) and bool(
        set(recovered_known) == set(known)
    )
    candidate_results: dict[str, str] = {}
    for candidate in candidates:
        if found.get(candidate, False):
            candidate_results[candidate] = BUNDLED_COLLISION_PRESENT
        elif calibration_passed:
            candidate_results[candidate] = BUNDLED_COLLISION_NONE_VERIFIED
        else:
            candidate_results[candidate] = BUNDLED_COLLISION_UNKNOWN
    evidence = {
        "schema_version": "1.0",
        "runtime_id": "claude-code",
        "runtime_version": CLAUDE_RUNTIME_VERSION,
        "artifact_fingerprint": observed,
        "artifact_fingerprint_status": "MATCHED",
        "artifact_path_class": "VERSIONED_STANDALONE_EXECUTABLE",
        "artifact_path_persisted": False,
        "inspection_method": "BOUNDED_EXACT_TOKEN_SCAN",
        "calibration": {
            "passed": calibration_passed,
            "expected_markers": list(markers),
            "recovered_markers": recovered_markers,
            "expected_known_bundled_identifiers": list(known),
            "recovered_known_bundled_identifiers": recovered_known,
            "completeness_claim": "CANDIDATE_SPECIFIC_ONLY",
        },
        "known_bundled_identifiers_recovered": recovered_known,
        "candidate_results": candidate_results,
        "artifact_size_bytes": size,
        "raw_artifact_persisted": False,
        "raw_excerpts_persisted": False,
        "evidence_digest": "",
    }
    without_digest = dict(evidence)
    without_digest["evidence_digest"] = ""
    evidence["evidence_digest"] = digest_value(without_digest)
    return evidence


def collect_installed_claude_bundled_evidence(
    candidate_slugs: Iterable[str],
) -> dict[str, object]:
    """Collect candidate-specific evidence from the installed artifact."""

    artifact = resolve_installed_claude_artifact()
    return inspect_claude_bundled_skills(
        artifact_path=artifact,
        candidate_slugs=candidate_slugs,
    )
