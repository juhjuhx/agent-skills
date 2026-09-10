"""Benchmark-safe, read-only projection for installed OpenCode 1.18.25.

This adapter consumes a validated StageRoute.  It does not route skills,
choose a model, install plugins/MCP, or persist prompts and skill bodies.
The portable bundle remains runtime-neutral; OpenCode-specific config and
headless invocation details live only in this module and its projection.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from tools.v3.contract_validation import (
    validate_agent_model_separation,
    validate_instance,
)
from tools.v3.evidence_gate import evaluate_evidence
from tools.v3.execution_bundle import compile_execution_bundle, validate_bundle
from tools.v3.live_benchmark import ProcessObservation, run_headless_command, sanitize_text
from tools.v3.opencode_native_contract import (
    NativeContractError,
    NativeConfigValidation,
    load_native_contract,
    validate_opencode_config,
)
from tools.v3.permission_intersection import capability_requirements, intersect_permissions
from tools.v3.reasoning_artifacts import artifact_refs, validate_reasoning_artifacts
from tools.v3.skill_resolver import LoadedSkill, SkillResolution, SkillResolver


WORKSPACE_MARKER = "<isolated-fixture>"
OPENCODE_RUNTIME_ID = "opencode"
OPENCODE_PERMISSION_KEYS = (
    "*",
    "read",
    "edit",
    "glob",
    "grep",
    "list",
    "bash",
    "task",
    "external_directory",
    "todowrite",
    "question",
    "webfetch",
    "websearch",
    "repo_clone",
    "repo_overview",
    "lsp",
    "doom_loop",
    "skill",
)
READ_ONLY_ALLOWED_KEYS = frozenset({"read", "list", "glob", "grep"})


def _public_copy(value: Any) -> Any:
    """Copy public metadata while redacting accidental credential strings."""

    if isinstance(value, dict):
        return {str(key): _public_copy(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_public_copy(child) for child in value]
    if isinstance(value, tuple):
        return [_public_copy(child) for child in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return copy.deepcopy(value)


@dataclass(frozen=True)
class OpenCodeInvocation:
    """Execution-local command and environment with a safe public summary."""

    argv: tuple[str, ...] = field(repr=False, compare=False)
    environment: Mapping[str, str] = field(repr=False, compare=False)
    workspace_root: Path = field(repr=False, compare=False)
    timeout_s: float
    public: dict[str, Any]


@dataclass
class OpenCodeAdapterResult:
    status: str
    reason_code: str | None = None
    errors: list[str] = field(default_factory=list)
    bundle: dict[str, Any] | None = None
    projection: dict[str, Any] | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    loaded_skills: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    # Bodies are execution-local.  They are never included by to_dict().
    execution_skills: tuple[LoadedSkill, ...] = field(
        default_factory=tuple, repr=False, compare=False
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize references and metrics, never raw bodies or prompts."""

        public_metric_keys = {
            "metadata_records_inspected",
            "registry_records_seen",
            "source_files_verified",
            "skill_md_files_loaded",
            "loaded_bytes",
            "capabilities",
            "permissions",
        }
        public_metrics = {
            key: _public_copy(value)
            for key, value in self.metrics.items()
            if key in public_metric_keys
        }

        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "errors": _public_copy(self.errors),
            "bundle": _public_copy(self.bundle),
            "projection": _public_copy(self.projection),
            "evidence": _public_copy(self.evidence),
            "loaded_skills": _public_copy(self.loaded_skills),
            "metrics": public_metrics,
        }


def _explicit_permission_config(filesystem: str) -> dict[str, Any]:
    """Generate an explicit no-ASK read-only permission map.

    OpenCode's permission defaults are not a security boundary for a headless
    benchmark.  Every known class is therefore present, and the only allows
    are scoped read/list/glob/grep rules inside the isolated fixture.
    """

    read_scope: dict[str, str] = {"*": "deny"}
    if filesystem in {"read", "workspace-read"}:
        read_scope[WORKSPACE_MARKER + "/**"] = "allow"
        # OpenCode applies the last matching rule, so secret denies are last.
        read_scope["*.env"] = "deny"
        read_scope["*.env.*"] = "deny"
        read_scope["*.credentials"] = "deny"
        read_scope["*.key"] = "deny"

    values: dict[str, Any] = {"*": "deny"}
    for key in OPENCODE_PERMISSION_KEYS:
        if key == "*":
            continue
        if key in READ_ONLY_ALLOWED_KEYS:
            values[key] = copy.deepcopy(read_scope)
        else:
            values[key] = "deny"
    # Explicitly retain a deny-all skill surface.  Canonical selected
    # procedures are resolved by the host and are not copied into OpenCode.
    values["skill"] = {"*": "deny"}
    return values


def _no_ask_proof(filesystem: str) -> dict[str, Any]:
    resolved = {
        key: ("ALLOW" if key in READ_ONLY_ALLOWED_KEYS and filesystem in {"read", "workspace-read"} else "DENY")
        for key in OPENCODE_PERMISSION_KEYS
    }
    return {
        "no_ask": True,
        "required_actions": list(OPENCODE_PERMISSION_KEYS),
        "resolved_actions": resolved,
        "method": "explicit permission entries plus native config validation; no ask action emitted",
    }


def _contains_permission_ask(value: Any) -> bool:
    if isinstance(value, str):
        return value == "ask"
    if isinstance(value, dict):
        return any(_contains_permission_ask(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_permission_ask(child) for child in value)
    return False


def validate_no_ask_projection(projection: dict[str, Any]) -> list[str]:
    """Return safety errors for a projection intended for headless execution."""

    errors: list[str] = []
    if projection.get("runtime_id") != OPENCODE_RUNTIME_ID:
        errors.append("projection runtime_id is not opencode")
    config = projection.get("config")
    values = config.get("values") if isinstance(config, dict) else None
    permission = values.get("permission") if isinstance(values, dict) else None
    if not isinstance(permission, dict):
        errors.append("projection has no explicit OpenCode permission object")
        permission = {}
    missing = sorted(set(OPENCODE_PERMISSION_KEYS) - set(permission))
    if missing:
        errors.append("permission classes are not explicitly resolved: " + ", ".join(missing))
    if permission.get("*") != "deny":
        errors.append("OpenCode wildcard permission must be deny")
    if _contains_permission_ask(permission):
        errors.append("headless OpenCode projection contains an unresolved ask action")
    for key in READ_ONLY_ALLOWED_KEYS:
        rule = permission.get(key)
        if not isinstance(rule, dict) or rule.get("*") != "deny":
            errors.append(f"{key} must deny by default before any isolated allow")
    for key in set(OPENCODE_PERMISSION_KEYS) - READ_ONLY_ALLOWED_KEYS - {"*"}:
        rule = permission.get(key)
        if rule != "deny" and not (
            isinstance(rule, dict) and rule.get("*") == "deny" and not _contains_permission_ask(rule)
        ):
            errors.append(f"{key} is not explicitly denied")
    if not isinstance(values, dict) or values.get("plugin") != []:
        errors.append("plugins must be explicitly disabled for the read-only lane")
    if not isinstance(values, dict) or values.get("mcp") != {}:
        errors.append("MCP must be explicitly unloaded for the read-only lane")
    proof = projection.get("no_ask_proof")
    if not isinstance(proof, dict) or proof.get("no_ask") is not True:
        errors.append("projection is missing its no-ASK proof")
    invocation = projection.get("invocation")
    if not isinstance(invocation, dict) or invocation.get("auto") is not False:
        errors.append("automatic approval is forbidden")
    return errors


def _replace_workspace_marker(value: Any, workspace_root: str) -> Any:
    if isinstance(value, dict):
        return {
            str(key).replace(WORKSPACE_MARKER, workspace_root): _replace_workspace_marker(
                child, workspace_root
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_replace_workspace_marker(child, workspace_root) for child in value]
    if isinstance(value, str):
        return value.replace(WORKSPACE_MARKER, workspace_root)
    return value


def render_opencode_runtime_config(
    projection: dict[str, Any], workspace_root: str | Path
) -> str:
    """Render config for one isolated run without mutating the projection."""

    root = Path(workspace_root).resolve()
    if not root.is_dir():
        raise ValueError(f"isolated OpenCode workspace does not exist: {root}")
    config = projection.get("config")
    values = config.get("values") if isinstance(config, dict) else None
    if not isinstance(values, dict):
        raise ValueError("OpenCode projection has no native config values")
    rendered = _replace_workspace_marker(values, str(root))
    safety_errors = validate_no_ask_projection(
        {**projection, "config": {"surface": "OPENCODE_CONFIG_CONTENT", "values": rendered}}
    )
    if safety_errors:
        raise NativeContractError(
            "NO_ASK_UNVERIFIED",
            "unsafe headless OpenCode projection: " + "; ".join(safety_errors),
        )
    validation = validate_opencode_config(rendered)
    if not validation.valid:
        raise NativeContractError(
            validation.reason_code or "INVALID_NATIVE_CONFIG",
            "rendered OpenCode config is invalid: " + "; ".join(validation.errors),
        )
    return json.dumps(rendered, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_opencode_invocation(
    projection: dict[str, Any],
    *,
    workspace_root: str | Path,
    prompt: str,
    timeout_s: float = 60,
    extra_args: Iterable[str] = (),
) -> OpenCodeInvocation:
    """Build a bounded ``opencode run`` invocation using explicit config."""

    root = Path(workspace_root).resolve()
    if not root.is_dir():
        raise ValueError(f"isolated OpenCode workspace does not exist: {root}")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("headless OpenCode prompt must be non-empty")
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    extras = tuple(extra_args)
    if any(not isinstance(item, str) or not item for item in extras):
        raise ValueError("extra OpenCode arguments must be non-empty strings")
    if any(item == "--auto" or item.startswith("--auto=") for item in extras):
        raise ValueError("--auto is forbidden for the benchmark-safe OpenCode boundary")
    if extras:
        raise ValueError("the read-only OpenCode boundary does not accept extra CLI arguments")

    config_text = render_opencode_runtime_config(projection, root)
    argv = (
        "opencode",
        "run",
        "--pure",
        "--format",
        "json",
        "--agent",
        "plan",
        "--dir",
        str(root),
        prompt,
    )
    environment = dict(os.environ)
    environment["OPENCODE_CONFIG_CONTENT"] = config_text
    environment["OPENCODE_DISABLE_PROJECT_CONFIG"] = "true"
    public_argv = (
        "opencode",
        "run",
        "--pure",
        "--format",
        "json",
        "--agent",
        "plan",
        "--dir",
        WORKSPACE_MARKER,
        "<prompt>",
    )
    return OpenCodeInvocation(
        argv=argv,
        environment=environment,
        workspace_root=root,
        timeout_s=timeout_s,
        public={
            "argv": list(public_argv),
            "shell": False,
            "stdin": "DEVNULL",
            "timeout_ms": int(timeout_s * 1000),
            "config_surface": "inline-runtime-config",
            "project_config_disabled": True,
            "auto": False,
            "raw_prompt_serialized": False,
        },
    )


class OpenCodeAdapter:
    """Compile and execute one validated read-only OpenCode route."""

    def __init__(
        self,
        repository_root: str | Path,
        registry_path: str | Path,
        *,
        policy: dict[str, Any] | None = None,
        live_runtime: dict[str, Any] | None = None,
        native_contract: dict[str, Any] | None = None,
        observed_runtime_version: str | None = "1.18.25",
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.registry_path = Path(registry_path)
        self.policy = copy.deepcopy(policy or {})
        self.live_runtime = copy.deepcopy(live_runtime or {})
        self.native_contract = copy.deepcopy(native_contract)
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
    ) -> OpenCodeAdapterResult:
        """Consume a route and produce a portable bundle plus OpenCode view."""

        records = list(metadata_records) if metadata_records is not None else None
        validation_errors: list[str] = []
        for contract_name, value in (
            ("TaskSpec", task_spec),
            ("StageRoute", stage_route),
            ("AgentAdapterManifest", adapter_manifest),
            ("ModelProfile", model_profile),
        ):
            validation = validate_instance(contract_name, value)
            validation_errors.extend(
                f"{contract_name}: {error}" for error in validation.errors
            )
        separation = validate_agent_model_separation(adapter_manifest, model_profile)
        validation_errors.extend(separation.errors)
        if validation_errors:
            return OpenCodeAdapterResult(
                status="BLOCKED",
                reason_code="INVALID_CONTRACT",
                errors=validation_errors,
            )
        if adapter_manifest.get("runtime_id") != OPENCODE_RUNTIME_ID or stage_route.get("adapter") != OPENCODE_RUNTIME_ID:
            return OpenCodeAdapterResult(
                status="BLOCKED",
                reason_code="RUNTIME_MISMATCH",
                errors=["OpenCodeAdapter accepts only an opencode StageRoute and manifest."],
            )

        selected = [] if stage_route.get("status") == "NO_SKILL_NEEDED" else stage_route.get("selected_skills", [])
        selected_metadata = self._metadata_for_capabilities(selected, records)
        capability_result = capability_requirements(
            task_spec, stage_route, adapter_manifest, model_profile, selected_metadata
        )
        if capability_result["status"] != "ALLOWED":
            return OpenCodeAdapterResult(
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
            return OpenCodeAdapterResult(
                status="BLOCKED",
                reason_code="PERMISSION_INTERSECTION",
                errors=permission_result["reasons"],
                metrics={"permissions": permission_result},
            )
        permission_projection = self._permission_projection_for(permission_result["effective"])
        if permission_projection["classification"] == "BLOCKED":
            return OpenCodeAdapterResult(
                status="BLOCKED",
                reason_code="PERMISSION_PROJECTION",
                errors=[permission_projection["reason"]],
                metrics={"permissions": permission_result},
            )

        resolver = SkillResolver(self.repository_root, self.registry_path)
        resolution = resolver.resolve(selected, records)
        if resolution.status != "READY":
            return OpenCodeAdapterResult(
                status="BLOCKED",
                reason_code=resolution.reason_code,
                errors=resolution.errors,
                metrics=self._resolution_metrics(resolution),
            )

        artifact_errors = validate_reasoning_artifacts(reasoning_artifacts or {})
        if artifact_errors:
            return OpenCodeAdapterResult(
                status="BLOCKED",
                reason_code="HIDDEN_REASONING_FIELD",
                errors=artifact_errors,
                metrics=self._resolution_metrics(resolution),
            )
        try:
            refs = artifact_refs(reasoning_artifacts or {})
        except ValueError as exc:
            return OpenCodeAdapterResult(
                status="BLOCKED",
                reason_code="INVALID_ARTIFACTS",
                errors=[str(exc)],
                metrics=self._resolution_metrics(resolution),
            )
        evidence = evaluate_evidence(stage_route.get("evidence_required", []), observed_evidence)
        bundle_status = "READY" if evidence["status"] == "PASS" else "BLOCKED"
        blocked_reason = None if bundle_status == "READY" else "Evidence gate did not pass; execution completion is blocked."
        bundle = compile_execution_bundle(
            task_spec=task_spec,
            stage_route=stage_route,
            adapter_manifest=adapter_manifest,
            model_profile=model_profile,
            selected_skills=resolution.references(),
            effective_capabilities=capability_result["effective"],
            permission_envelope=permission_result["effective"],
            context={
                "static_prefix": "stable",
                "dynamic_context": "lazy",
                "tool_schema_context": "tracked",
                "artifact_refs": refs,
            },
            reasoning_artifact_refs=refs,
            evidence_required=stage_route.get("evidence_required", []),
            provenance={
                "registry_epoch": stage_route["registry_epoch"],
                "generated_by": "v3-bundle-compiler",
            },
            status=bundle_status,
            evidence_gate=evidence,
            no_skill_reason=stage_route.get("no_skill_reason"),
            blocked_reason=blocked_reason,
        )
        bundle_validation = validate_bundle(bundle)
        if not bundle_validation.valid:
            return OpenCodeAdapterResult(
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
                skill_trust={
                    record.get("skill_id"): record.get("trust")
                    for record in resolution.selected_records
                    if isinstance(record, dict)
                },
            )
        except NativeContractError as exc:
            return OpenCodeAdapterResult(
                status="BLOCKED",
                reason_code=exc.reason_code,
                errors=[str(exc)],
                bundle=bundle,
                evidence=evidence,
                metrics=self._resolution_metrics(resolution),
            )
        except ValueError as exc:
            return OpenCodeAdapterResult(
                status="BLOCKED",
                reason_code="PROJECTION_UNSUPPORTED",
                errors=[str(exc)],
                bundle=bundle,
                evidence=evidence,
                metrics=self._resolution_metrics(resolution),
            )
        if evidence["status"] != "PASS":
            return OpenCodeAdapterResult(
                status="BLOCKED",
                reason_code="EVIDENCE_MISSING",
                errors=[blocked_reason or "evidence gate blocked"],
                bundle=bundle,
                projection=projection,
                evidence=evidence,
                loaded_skills=[self._loaded_skill_record(skill) for skill in resolution.loaded],
                metrics=self._resolution_metrics(resolution),
                execution_skills=tuple(resolution.loaded),
            )
        return OpenCodeAdapterResult(
            status="READY",
            bundle=bundle,
            projection=projection,
            evidence=evidence,
            loaded_skills=[self._loaded_skill_record(skill) for skill in resolution.loaded],
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
        loaded_skills: Iterable[LoadedSkill],
        skill_trust: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """Produce only verified OpenCode config and invocation surfaces."""

        if adapter_manifest.get("runtime_id") != OPENCODE_RUNTIME_ID:
            raise ValueError("OpenCode projection requires the opencode adapter manifest")
        filesystem = bundle["permission_envelope"].get("filesystem")
        permission_projection = self._permission_projection_for(bundle["permission_envelope"])
        if permission_projection["classification"] == "BLOCKED":
            raise NativeContractError("PERMISSION_PROJECTION", permission_projection["reason"])

        contract = load_native_contract() if self.native_contract is None else self.native_contract
        native_validation = validate_opencode_config(
            {
                "$schema": "https://opencode.ai/config.json",
                "permission": _explicit_permission_config(filesystem),
                "plugin": [],
                "mcp": {},
            },
            contract=contract,
            expected_target="INSTALLED_RUNTIME",
            observed_runtime_version=self.observed_runtime_version,
        )
        if not native_validation.valid:
            raise NativeContractError(
                native_validation.reason_code or "INVALID_NATIVE_CONFIG",
                "invalid OpenCode native config contract: " + "; ".join(native_validation.errors),
            )

        loaded = list(loaded_skills)
        selected_refs = [
            {
                "skill_id": skill.skill_id,
                "source_ref": skill.source_ref,
                "source_path": skill.source_path,
                "digest": skill.digest,
                "role": skill.role,
                "trust": (skill_trust or {}).get(
                    skill.skill_id,
                    "CORE_TRUSTED" if skill.skill_id == "using-superpowers" else "CURATED",
                ),
                "load_state": skill.load_state,
            }
            for skill in loaded
        ]
        config_values = {
            "$schema": "https://opencode.ai/config.json",
            "permission": _explicit_permission_config(filesystem),
            "plugin": [],
            "mcp": {},
        }
        projection = {
            "schema_version": "3.0",
            "projection_version": "1.0",
            "runtime_id": OPENCODE_RUNTIME_ID,
            "bundle_digest": bundle["bundle_digest"],
            "support_levels": {
                "AGENTS.md": "NATIVE",
                "Skills": "NATIVE",
                "skill_body_delivery": "HOST_MANAGED",
                "config": "NATIVE",
                "permission": "NATIVE",
                "run": "NATIVE",
                "agent": "NATIVE",
                "plugins": "NATIVE",
                "MCP": "NATIVE",
                "static_context": "HOST_MANAGED",
                "dynamic_context": "HOST_MANAGED",
                "tool_schema_context": "HOST_MANAGED",
                "evidence_gate": "HOST_MANAGED",
            },
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
                "native_surface": "NATIVE",
                "selected": selected_refs,
                # Native OpenCode is not given full bodies by this projection.
                "body_files_loaded": 0,
            },
            "config": {"surface": "OPENCODE_CONFIG_CONTENT", "values": config_values},
            "invocation": {
                "command": "opencode run",
                "format": "json",
                "agent": "plan",
                "pure": True,
                "shell": False,
                "stdin": "DEVNULL",
                "cwd_mode": "ISOLATED_FIXTURE",
                "timeout_ms": 60000,
                "auto": False,
            },
            "permissions": permission_projection,
            "mcp": {"status": "DENY", "refs": [], "schema_loaded": False},
            "plugins": {"status": "DENY", "refs": []},
            "context": {
                "static_prefix": "HOST_MANAGED",
                "dynamic_context": "HOST_MANAGED",
                "tool_schema_context": "HOST_MANAGED",
                "artifact_refs": sorted(bundle.get("reasoning_artifact_refs", [])),
            },
            "provenance": {
                "bundle_digest": bundle["bundle_digest"],
                **native_validation.provenance,
                "native_contract_revision": native_validation.native_contract_revision,
                "selected_skill_digests": sorted(skill.digest for skill in loaded),
            },
            "no_ask_proof": _no_ask_proof(filesystem),
        }
        # Validate the exact projection before returning it.  This catches
        # accidental unsupported fields independently of native validation.
        validation = validate_instance("OpenCodeNativeProjection", projection)
        if not validation.valid:
            raise ValueError("invalid OpenCode native projection: " + "; ".join(validation.errors))
        return projection

    def execute(
        self,
        projection: dict[str, Any],
        *,
        workspace_root: str | Path,
        prompt: str,
        timeout_s: float = 60,
    ) -> ProcessObservation:
        """Run a projection without persisting prompt, environment, or output."""

        invocation = build_opencode_invocation(
            projection,
            workspace_root=workspace_root,
            prompt=prompt,
            timeout_s=timeout_s,
        )
        return run_headless_command(
            invocation.argv,
            cwd=invocation.workspace_root,
            timeout_s=invocation.timeout_s,
            environment=dict(invocation.environment),
        )

    @staticmethod
    def _permission_projection_for(envelope: dict[str, Any]) -> dict[str, Any]:
        filesystem = envelope.get("filesystem")
        if (
            filesystem in {"none", "read", "workspace-read"}
            and envelope.get("network", "none") == "none"
            and not any(
                bool(envelope.get(name, False))
                for name in ("external_write", "secrets", "publish", "delete")
            )
        ):
            return {
                "filesystem": filesystem,
                "classification": "NATIVE_EXACT",
                "native_scope": "ISOLATED_FIXTURE" if filesystem != "none" else "NONE",
                "reason": "OpenCode permission rules explicitly allow only isolated-fixture reads and deny every other known class.",
            }
        return {
            "filesystem": filesystem,
            "classification": "BLOCKED",
            "native_scope": "NONE",
            "reason": (
                "This OpenCode vertical slice is read-only and cannot represent portable filesystem authority "
                f"{filesystem!r} without risking a broader native allow."
            ),
        }

    def _metadata_for_capabilities(
        self,
        selected: list[dict[str, Any]],
        metadata_records: Iterable[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        selected_ids = {item.get("skill_id") for item in selected}
        if not selected_ids or metadata_records is None:
            return [] if not selected_ids else list(metadata_records or [])
        return [
            record
            for record in metadata_records
            if isinstance(record, dict) and record.get("skill_id") in selected_ids
        ]

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
        return {
            "skill_id": skill.skill_id,
            "path": skill.source_path,
            "source_ref": skill.source_ref,
            "digest": skill.digest,
            "role": skill.role,
            "bytes": skill.byte_count,
            "load_state": skill.load_state,
        }
