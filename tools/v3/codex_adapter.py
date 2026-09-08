"""Codex-native projection for a portable v3 execution bundle.

The adapter consumes a StageRoute. It never selects skills and never calls a
general router. Native field names in the projection are limited to fields
verified against the current Codex documentation/source evidence.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from tools.v3.contract_validation import (
    validate_agent_model_separation,
    validate_instance,
)
from tools.v3.codex_native_contract import (
    INSTALLED_RUNTIME_VERSION,
    NativeContractError,
    load_native_contract,
    validate_codex_config,
)
from tools.v3.evidence_gate import evaluate_evidence
from tools.v3.execution_bundle import compile_execution_bundle, validate_bundle
from tools.v3.permission_intersection import capability_requirements, intersect_permissions
from tools.v3.reasoning_artifacts import artifact_refs, validate_reasoning_artifacts
from tools.v3.skill_resolver import LoadedSkill, SkillResolution, SkillResolver


CODEX_NATIVE_CONFIG_FIELDS = frozenset(
    {
        "model",
        "model_provider",
        "model_reasoning_effort",
        "approval_policy",
        "sandbox_mode",
        "agents",
    }
)

@dataclass
class AdapterResult:
    status: str
    reason_code: str | None = None
    errors: list[str] = field(default_factory=list)
    bundle: dict[str, Any] | None = None
    projection: dict[str, Any] | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    loaded_skills: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    # Loaded bodies stay execution-local and are deliberately not serialized.
    execution_skills: tuple[LoadedSkill, ...] = field(
        default_factory=tuple, repr=False, compare=False
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "errors": list(self.errors),
            "bundle": copy.deepcopy(self.bundle),
            "projection": copy.deepcopy(self.projection),
            "evidence": copy.deepcopy(self.evidence),
            "loaded_skills": copy.deepcopy(self.loaded_skills),
            "metrics": copy.deepcopy(self.metrics),
        }


class CodexAdapter:
    """Compile one validated route for Codex-native consumption."""

    def __init__(
        self,
        repository_root: str | Path,
        registry_path: str | Path,
        *,
        policy: dict[str, Any] | None = None,
        live_runtime: dict[str, Any] | None = None,
        native_contract: dict[str, Any] | None = None,
        observed_runtime_version: str | None = INSTALLED_RUNTIME_VERSION,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.registry_path = Path(registry_path)
        self.policy = copy.deepcopy(policy or {})
        self.live_runtime = copy.deepcopy(live_runtime or {})
        self.native_contract = copy.deepcopy(native_contract)
        # This is maintenance-time observed evidence, not a live network or
        # subprocess lookup. An explicit None means the runtime is unknown.
        self.observed_runtime_version = observed_runtime_version

    def compile(
        self,
        *,
        task_spec: dict[str, Any],
        stage_route: dict[str, Any],
        adapter_manifest: dict[str, Any],
        model_profile: dict[str, Any],
        metadata_records: Iterable[dict[str, Any]] | None = None,
        observed_evidence: list[Any] | None = None,
        reasoning_artifacts: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> AdapterResult:
        """Consume, validate, and project a single StageRoute."""

        if metadata_records is not None:
            # A route may be given any iterable. Materialize it once so the
            # capability check and selected-only resolver see the same records.
            metadata_records = list(metadata_records)

        validation_errors: list[str] = []
        for contract, value in (
            ("TaskSpec", task_spec),
            ("StageRoute", stage_route),
            ("AgentAdapterManifest", adapter_manifest),
            ("ModelProfile", model_profile),
        ):
            result = validate_instance(contract, value)
            validation_errors.extend(f"{contract}: {error}" for error in result.errors)
        separation = validate_agent_model_separation(adapter_manifest, model_profile)
        validation_errors.extend(separation.errors)
        if validation_errors:
            return AdapterResult(
                status="BLOCKED",
                reason_code="INVALID_CONTRACT",
                errors=validation_errors,
            )
        if adapter_manifest.get("runtime_id") != "codex" or stage_route.get("adapter") != "codex":
            return AdapterResult(
                status="BLOCKED",
                reason_code="RUNTIME_MISMATCH",
                errors=["CodexAdapter accepts only a StageRoute and manifest for runtime_id codex."],
            )

        selected = stage_route.get("selected_skills", [])
        if stage_route.get("status") == "NO_SKILL_NEEDED":
            selected = []
        skill_metadata = self._metadata_for_capabilities(selected, metadata_records)
        capability_result = capability_requirements(
            task_spec, stage_route, adapter_manifest, model_profile, skill_metadata
        )
        if capability_result["status"] != "ALLOWED":
            return AdapterResult(
                status="BLOCKED",
                reason_code="CAPABILITY_MISMATCH",
                errors=[
                    "capability requirements cannot be satisfied: "
                    + ", ".join(capability_result["missing"])
                ],
                metrics={"capabilities": capability_result},
            )

        permission_result = intersect_permissions(
            task_spec,
            self.policy,
            adapter_manifest,
            self.live_runtime,
            stage_route.get("budget_envelope"),
        )
        if permission_result["status"] != "ALLOWED":
            return AdapterResult(
                status="BLOCKED",
                reason_code="PERMISSION_INTERSECTION",
                errors=permission_result["reasons"],
                metrics={"permissions": permission_result},
            )
        try:
            permission_projection = self._permission_projection_for(
                permission_result["effective"]
            )
        except ValueError as exc:
            return AdapterResult(
                status="BLOCKED",
                reason_code="PERMISSION_PROJECTION",
                errors=[str(exc)],
                metrics={"permissions": permission_result},
            )
        if permission_projection["classification"] in {"HOST_MANAGED", "BLOCKED"}:
            return AdapterResult(
                status="BLOCKED",
                reason_code="PERMISSION_PROJECTION",
                errors=[permission_projection["reason"]],
                metrics={"permissions": permission_result},
            )

        resolver = SkillResolver(self.repository_root, self.registry_path)
        resolution = resolver.resolve(selected, metadata_records)
        if resolution.status != "READY":
            return AdapterResult(
                status="BLOCKED",
                reason_code=resolution.reason_code,
                errors=resolution.errors,
                metrics=self._resolution_metrics(resolution),
            )

        artifact_errors = validate_reasoning_artifacts(reasoning_artifacts or {})
        if artifact_errors:
            return AdapterResult(
                status="BLOCKED",
                reason_code="HIDDEN_REASONING_FIELD",
                errors=artifact_errors,
                metrics=self._resolution_metrics(resolution),
            )
        try:
            refs = artifact_refs(reasoning_artifacts or {})
        except ValueError as exc:
            return AdapterResult(
                status="BLOCKED",
                reason_code="INVALID_ARTIFACTS",
                errors=[str(exc)],
                metrics=self._resolution_metrics(resolution),
            )
        evidence = evaluate_evidence(stage_route.get("evidence_required", []), observed_evidence)
        if evidence["status"] != "PASS":
            bundle_status = "BLOCKED"
        elif permission_projection["classification"] == "NATIVE_CONSERVATIVE":
            bundle_status = "DEGRADED"
        else:
            bundle_status = "READY"
        blocked_reason = None
        if evidence["status"] != "PASS":
            blocked_reason = "Evidence gate did not pass; execution completion is blocked."
        no_skill_reason = stage_route.get("no_skill_reason")
        context = {
            "static_prefix": "stable",
            "dynamic_context": "lazy",
            "tool_schema_context": "tracked",
            "artifact_refs": refs,
        }
        bundle = compile_execution_bundle(
            task_spec=task_spec,
            stage_route=stage_route,
            adapter_manifest=adapter_manifest,
            model_profile=model_profile,
            selected_skills=resolution.references(),
            effective_capabilities=capability_result["effective"],
            permission_envelope=permission_result["effective"],
            context=context,
            reasoning_artifact_refs=refs,
            evidence_required=stage_route.get("evidence_required", []),
            provenance={
                "registry_epoch": stage_route["registry_epoch"],
                "generated_by": "v3-bundle-compiler",
            },
            status=bundle_status,
            evidence_gate=evidence,
            no_skill_reason=no_skill_reason,
            blocked_reason=blocked_reason,
        )
        bundle_validation = validate_bundle(bundle)
        if not bundle_validation.valid:
            return AdapterResult(
                status="BLOCKED",
                reason_code="INVALID_BUNDLE",
                errors=bundle_validation.errors,
                metrics=self._resolution_metrics(resolution),
            )
        try:
            projection = self.project(
                bundle=bundle,
                task_spec=task_spec,
                stage_route=stage_route,
                adapter_manifest=adapter_manifest,
                model_profile=model_profile,
                loaded_skills=resolution.loaded,
                reasoning_effort=reasoning_effort,
            )
        except NativeContractError as exc:
            return AdapterResult(
                status="BLOCKED",
                reason_code=exc.reason_code,
                errors=[str(exc)],
                bundle=bundle,
                evidence=evidence,
                metrics=self._resolution_metrics(resolution),
            )
        except ValueError as exc:
            return AdapterResult(
                status="BLOCKED",
                reason_code="PROJECTION_UNSUPPORTED",
                errors=[str(exc)],
                bundle=bundle,
                evidence=evidence,
                metrics=self._resolution_metrics(resolution),
            )
        if evidence["status"] != "PASS":
            result_status = "BLOCKED"
            result_reason_code = "EVIDENCE_MISSING"
            result_errors = [blocked_reason or "evidence gate blocked"]
        elif permission_projection["classification"] == "NATIVE_CONSERVATIVE":
            result_status = "DEGRADED"
            result_reason_code = "PERMISSION_PROJECTION_DEGRADED"
            result_errors = [permission_projection["reason"]]
        else:
            result_status = "READY"
            result_reason_code = None
            result_errors = []
        return AdapterResult(
            status=result_status,
            reason_code=result_reason_code,
            errors=result_errors,
            bundle=bundle,
            projection=projection,
            evidence=evidence,
            loaded_skills=[
                self._loaded_skill_record(skill)
                for skill in resolution.loaded
            ],
            metrics=self._resolution_metrics(resolution),
            execution_skills=tuple(resolution.loaded),
        )

    def project(
        self,
        *,
        bundle: dict[str, Any],
        task_spec: dict[str, Any],
        stage_route: dict[str, Any],
        adapter_manifest: dict[str, Any],
        model_profile: dict[str, Any],
        loaded_skills: Iterable[Any],
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        """Project the portable bundle onto verified Codex surfaces."""

        if adapter_manifest.get("runtime_id") != "codex":
            raise ValueError("Codex projection requires the codex adapter manifest")
        config_values: dict[str, Any] = {}
        model_selection = adapter_manifest.get("model_selection", {})
        if model_selection.get("profile_based"):
            config_values["model"] = model_profile["model_id"]
            config_values["model_provider"] = model_profile["provider_id"]
        if reasoning_effort:
            levels = model_profile.get("reasoning", {}).get("effort_levels", [])
            if not adapter_manifest.get("reasoning_effort", {}).get("native"):
                raise ValueError("manifest does not advertise native reasoning effort")
            if not model_profile.get("reasoning", {}).get("supported"):
                raise ValueError("model profile does not advertise reasoning support")
            if reasoning_effort not in levels:
                raise ValueError(f"reasoning effort is not advertised by the model: {reasoning_effort}")
            config_values["model_reasoning_effort"] = reasoning_effort
        approval_policy = self.live_runtime.get("approval_policy")
        if approval_policy is not None:
            config_values["approval_policy"] = copy.deepcopy(approval_policy)
        permission_projection = self._permission_projection_for(
            bundle["permission_envelope"]
        )
        if permission_projection["classification"] in {"HOST_MANAGED", "BLOCKED"}:
            raise ValueError(permission_projection["reason"])
        config_values["sandbox_mode"] = permission_projection["sandbox_mode"]
        if task_spec.get("parallelizable") and "needs_subagents" in task_spec.get(
            "required_capabilities", []
        ):
            max_agents = stage_route.get("budget_envelope", {}).get("max_parallel_agents", 0)
            config_values["agents"] = {
                "enabled": True,
                "max_concurrent_threads_per_session": max(1, int(max_agents or 1)),
            }

        native_contract = (
            load_native_contract()
            if self.native_contract is None
            else self.native_contract
        )
        native_validation = validate_codex_config(
            config_values,
            contract=native_contract,
            expected_target="INSTALLED_RUNTIME",
            observed_runtime_version=self.observed_runtime_version,
        )
        if not native_validation.valid:
            raise NativeContractError(
                native_validation.reason_code or "PROJECTION_UNSUPPORTED",
                "invalid Codex native config contract: "
                + "; ".join(native_validation.errors),
            )
        if isinstance(approval_policy, dict) and "granular" in approval_policy:
            raise ValueError(
                "Codex granular approval is a native object form but is "
                "UNSUPPORTED by this adapter; no partial syntax was generated"
            )

        loaded = list(loaded_skills)
        selected_projection = [skill.projection_reference() for skill in loaded]
        mcp_refs = []
        mcp_config = adapter_manifest.get("mcp", {}) or {}
        if mcp_config.get("supported") and "MCP" in stage_route.get(
            "granted_capabilities", []
        ):
            mcp_refs = list(mcp_config.get("server_refs", []))
        mcp_load_mode = "stage-local" if mcp_refs else "none"
        mcp_servers = [
            {"id": ref, "permission_scope": "policy-gated", "tool_refs": []}
            for ref in mcp_refs
        ]
        subagent_required = bool(
            (adapter_manifest.get("subagents", {}) or {}).get("supported")
            and "needs_subagents" in task_spec.get("required_capabilities", [])
        )
        hooks = adapter_manifest.get("hooks", {}) or {}
        hooks_requested = bool(
            hooks.get("supported")
            and "hooks" in stage_route.get("granted_capabilities", [])
        )
        hook_paths = [
            definition["reference"]
            for definition in hooks.get("definitions", [])
            if hooks_requested
            and isinstance(definition, dict)
            and definition.get("reference")
        ]
        support_levels = {
            "AGENTS.md": "NATIVE",
            "Skills": "NATIVE",
            "MCP": "NATIVE",
            "Subagents": "NATIVE",
            "Plugins": "NATIVE",
            "Hooks": "NATIVE",
            "config": "NATIVE",
            "sandbox": "NATIVE",
            "approvals": "NATIVE",
            "reasoning_effort": "NATIVE",
            "static_context": "HOST_MANAGED",
            "dynamic_context": "HOST_MANAGED",
            "tool_schema_context": "HOST_MANAGED",
            "evidence_gate": "HOST_MANAGED",
            "native_learning": "UNSUPPORTED",
        }
        projection: dict[str, Any] = {
            "schema_version": "3.0",
            "projection_version": "1.0",
            "runtime_id": "codex",
            "bundle_digest": bundle["bundle_digest"],
            "support_levels": support_levels,
            "instruction_surfaces": {
                "persistent": [
                    {
                        "path": "AGENTS.md",
                        "scope": "project",
                        "purposes": ["invariants", "routing-bootstrap", "context-policy"],
                    }
                ]
            },
            "skills": {
                "load_mode": "selected-only",
                "native_roots": [".agents/skills"],
                "selected": selected_projection,
            },
            "config": {"path": ".codex/config.toml", "values": config_values},
            "permissions": permission_projection,
            "mcp": {
                "load_mode": mcp_load_mode,
                "servers": mcp_servers,
                "tool_schema_tokens": bundle["context"].get("tool_schema_tokens", 0),
            },
            "subagents": {
                "enabled": subagent_required,
                "roles": [],
            },
            "plugins": {
                # Plugin support is native, but this stage selected no plugin
                # reference. The projection must not enable an undeclared one.
                "enabled": False,
                "refs": [],
            },
            "hooks": {"enabled": bool(hook_paths), "paths": hook_paths},
            "context": {
                "static_prefix": support_levels["static_context"],
                "dynamic_runtime_context": support_levels["dynamic_context"],
                "tool_schema_budget": support_levels["tool_schema_context"],
                "tool_ordering": "HOST_MANAGED",
                "cache_stability": "HOST_MANAGED",
            },
            "provenance": {
                "bundle_digest": bundle["bundle_digest"],
                "generated_config_path": ".codex/config.toml",
                "codex_source_revision": native_validation.source_revision,
                "native_contract_revision": native_validation.native_contract_revision,
                "runtime_id": native_validation.provenance["runtime_id"],
                "observed_runtime_version": native_validation.provenance[
                    "observed_runtime_version"
                ],
                "release_tag": native_validation.provenance["release_tag"],
                "release_commit": native_validation.provenance["release_commit"],
                "contract_target": native_validation.provenance["contract_target"],
                "contract_source_commit": native_validation.provenance[
                    "contract_source_commit"
                ],
                "docs_snapshot_date": native_validation.provenance["docs_snapshot_date"],
                "contract_digest": native_validation.provenance["contract_digest"],
                "verification_method": native_validation.provenance[
                    "verification_method"
                ],
                "support": native_validation.provenance["support"],
                "availability": native_validation.provenance["availability"],
                "selected_skill_digests": sorted(
                    item["digest"] for item in bundle["selected_skills"]
                ),
            },
        }
        validation = validate_instance("CodexNativeProjection", projection)
        if not validation.valid:
            raise ValueError("invalid Codex native projection: " + "; ".join(validation.errors))
        return projection

    def _metadata_for_capabilities(
        self,
        selected: list[dict[str, Any]],
        metadata_records: Iterable[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        selected_ids = {item.get("skill_id") for item in selected}
        if not selected_ids:
            return []
        if metadata_records is not None:
            return [
                record
                for record in metadata_records
                if isinstance(record, dict) and record.get("skill_id") in selected_ids
            ]
        resolver = SkillResolver(self.repository_root, self.registry_path)
        registry = resolver.registry_path
        from tools.v3.compatibility import import_current_skill

        records = []
        for skill_id in sorted(selected_ids):
            try:
                records.append(import_current_skill(registry, skill_id))
            except KeyError:
                # Leave the missing ID for SkillResolver to report explicitly.
                continue
        return records

    @staticmethod
    def _resolution_metrics(resolution: SkillResolution) -> dict[str, Any]:
        return {
            "metadata_records_inspected": resolution.inspected_metadata_records,
            "registry_records_seen": resolution.registry_records_seen,
            "source_files_verified": resolution.source_files_verified,
            "skill_md_files_loaded": resolution.loaded_skill_files,
            "loaded_bytes": resolution.loaded_bytes,
        }

    @staticmethod
    def _loaded_skill_record(skill: LoadedSkill) -> dict[str, Any]:
        """Return provenance and metrics without serializing the body."""

        return {
            "skill_id": skill.skill_id,
            "path": skill.source_path,
            "source_ref": skill.source_ref,
            "digest": skill.digest,
            "role": skill.role,
            "bytes": skill.byte_count,
            "load_state": skill.load_state,
        }

    @staticmethod
    def _permission_projection_for(envelope: dict[str, Any]) -> dict[str, Any]:
        """Map filesystem authority only when Codex can represent it safely."""

        filesystem = envelope.get("filesystem")
        mappings = {
            "read": {
                "sandbox_mode": "read-only",
                "classification": "NATIVE_EXACT",
            },
            "workspace-read": {
                "sandbox_mode": "read-only",
                "classification": "HOST_MANAGED",
                "reason": "Codex has no verified workspace-read sandbox mode; host path enforcement is required.",
            },
            "workspace-write": {
                "sandbox_mode": "workspace-write",
                "classification": "NATIVE_EXACT",
            },
        }
        mapping = mappings.get(filesystem)
        if mapping is None:
            return {
                "filesystem": filesystem,
                "sandbox_mode": None,
                "classification": "BLOCKED",
                "reason": (
                    "portable filesystem permission "
                    f"{filesystem!r} cannot be represented without broader Codex authority; BLOCKED"
                ),
            }
        return {"filesystem": filesystem, **mapping}

    @classmethod
    def _sandbox_mode_for(cls, bundle: dict[str, Any]) -> str:
        """Return a safe Codex mode or fail closed for an unrepresentable envelope."""

        projection = cls._permission_projection_for(bundle["permission_envelope"])
        if projection["classification"] in {"HOST_MANAGED", "BLOCKED"}:
            raise ValueError(projection["reason"])
        return projection["sandbox_mode"]
