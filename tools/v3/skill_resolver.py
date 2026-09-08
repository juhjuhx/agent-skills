"""Selected-only resolution of canonical SkillMetadataV3 records."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from tools.v3.compatibility import import_skill_index_entry, load_current_registry
from tools.v3.contract_validation import validate_instance


TRUSTED_FOR_LOADING = frozenset({"CORE_TRUSTED", "CURATED"})


@dataclass(frozen=True)
class LoadedSkill:
    skill_id: str
    source_path: str
    source_ref: str
    digest: str
    role: str
    content: str
    load_state: str

    @property
    def byte_count(self) -> int:
        return len(self.content.encode("utf-8"))

    def reference(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "source_ref": self.source_ref,
            "source_path": self.source_path,
            "digest": self.digest,
            "role": self.role,
            "load_state": self.load_state,
        }

    def projection_reference(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "path": self.source_path,
            "digest": self.digest,
            "role": self.role,
            "load": "resident" if self.load_state == "RESIDENT" else "on-demand",
        }


@dataclass
class SkillResolution:
    status: str
    loaded: list[LoadedSkill] = field(default_factory=list)
    selected_records: list[dict[str, Any]] = field(default_factory=list)
    inspected_metadata_records: int = 0
    registry_records_seen: int = 0
    source_files_verified: int = 0
    errors: list[str] = field(default_factory=list)
    reason_code: str | None = None

    @property
    def loaded_skill_files(self) -> int:
        return sum(1 for skill in self.loaded if skill.load_state == "LOADED")

    @property
    def loaded_bytes(self) -> int:
        return sum(skill.byte_count for skill in self.loaded)

    def references(self) -> list[dict[str, Any]]:
        return [skill.reference() for skill in self.loaded]


class SkillResolver:
    """Resolve only the IDs already present in a validated StageRoute."""

    def __init__(
        self,
        repository_root: str | Path,
        registry_path: str | Path,
        *,
        resident_skill_ids: Iterable[str] = ("using-superpowers",),
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.registry_path = Path(registry_path)
        self.resident_skill_ids = frozenset(resident_skill_ids)

    def resolve(
        self,
        selected_skills: list[dict[str, Any]],
        metadata_records: Iterable[dict[str, Any]] | None = None,
    ) -> SkillResolution:
        if not selected_skills:
            return SkillResolution(status="READY")

        registry_records_seen = 0
        if metadata_records is None:
            registry = load_current_registry(self.registry_path)
            registry_records_seen = len(registry["skills"])
            by_id = {
                entry.get("id"): import_skill_index_entry(entry, registry)
                for entry in registry["skills"]
                if isinstance(entry, dict) and isinstance(entry.get("id"), str)
            }
        else:
            by_id = {
                record.get("skill_id"): record
                for record in metadata_records
                if isinstance(record, dict) and isinstance(record.get("skill_id"), str)
            }

        result = SkillResolution(
            status="READY",
            inspected_metadata_records=len(selected_skills),
            registry_records_seen=registry_records_seen,
        )
        seen_ids: set[str] = set()
        for selected in selected_skills:
            skill_id = selected.get("skill_id")
            role = selected.get("role")
            if skill_id in seen_ids:
                return self._blocked(result, "DUPLICATE_SKILL", f"duplicate selected skill: {skill_id}")
            seen_ids.add(skill_id)
            record = by_id.get(skill_id)
            if record is None:
                return self._blocked(result, "MISSING_SKILL", f"skill metadata is missing: {skill_id}")

            validation = validate_instance("SkillMetadataV3", record)
            if not validation.valid:
                return self._blocked(
                    result,
                    "INVALID_METADATA",
                    f"invalid metadata for {skill_id}: {'; '.join(validation.errors)}",
                )
            if record.get("trust") not in TRUSTED_FOR_LOADING:
                return self._blocked(
                    result,
                    "TRUST_REJECTED",
                    f"skill {skill_id} has trust {record.get('trust')}; trusted loading is blocked",
                )
            source = record.get("source", {})
            source_path = source.get("path")
            expected_digest = source.get("digest")
            if not isinstance(source_path, str) or not isinstance(expected_digest, str):
                return self._blocked(
                    result,
                    "SOURCE_INCOMPLETE",
                    f"skill {skill_id} has no resolvable source path and digest",
                )
            path = (self.repository_root / source_path).resolve()
            try:
                path.relative_to(self.repository_root)
            except ValueError:
                return self._blocked(
                    result,
                    "PATH_ESCAPE",
                    f"skill {skill_id} source path escapes the repository: {source_path}",
                )
            if not path.is_file():
                return self._blocked(
                    result,
                    "MISSING_SOURCE",
                    f"canonical SKILL.md is missing for {skill_id}: {source_path}",
                )
            raw = path.read_bytes()
            result.source_files_verified += 1
            actual_digest = f"sha256:{hashlib.sha256(raw).hexdigest()}"
            if actual_digest != expected_digest:
                return self._blocked(
                    result,
                    "DIGEST_MISMATCH",
                    f"canonical digest changed for {skill_id}: expected {expected_digest}, got {actual_digest}",
                )
            source_ref = f"{source.get('repo', 'unknown')}@{source.get('ref', 'unknown')}"
            if skill_id in self.resident_skill_ids:
                result.loaded.append(
                    LoadedSkill(
                        skill_id=skill_id,
                        source_path=source_path,
                        source_ref=source_ref,
                        digest=actual_digest,
                        role=role,
                        content="",
                        load_state="RESIDENT",
                    )
                )
            else:
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    return self._blocked(
                        result,
                        "SOURCE_NOT_TEXT",
                        f"canonical skill source is not UTF-8 text: {source_path}",
                    )
                result.loaded.append(
                    LoadedSkill(
                        skill_id=skill_id,
                        source_path=source_path,
                        source_ref=source_ref,
                        digest=actual_digest,
                        role=role,
                        content=content,
                        load_state="LOADED",
                    )
                )
            result.selected_records.append(record)
        return result

    @staticmethod
    def _blocked(result: SkillResolution, code: str, message: str) -> SkillResolution:
        result.status = "BLOCKED"
        result.reason_code = code
        result.errors.append(message)
        return result
