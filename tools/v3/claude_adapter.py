"""Benchmark-safe, read-only projection for the installed Claude Code CLI.

This adapter consumes a validated StageRoute.  It does not route skills,
choose a model, install plugins/MCP, or persist prompts and skill bodies.  The
portable execution bundle remains runtime-neutral; Claude-specific flags and
the headless process boundary live only in this module and its projection.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from tools.v3.claude_native_contract import (
    NativeContractError,
    load_native_contract,
    validate_claude_config,
)
from tools.v3.contract_validation import (
    validate_agent_model_separation,
    validate_instance,
)
from tools.v3.evidence_gate import evaluate_evidence
from tools.v3.execution_bundle import compile_execution_bundle, validate_bundle
from tools.v3.live_benchmark import (
    ProcessObservation,
    run_headless_command,
    sanitize_text,
)
from tools.v3.permission_intersection import capability_requirements, intersect_permissions
from tools.v3.reasoning_artifacts import artifact_refs, validate_reasoning_artifacts
from tools.v3.skill_resolver import LoadedSkill, SkillResolution, SkillResolver


CLAUDE_RUNTIME_ID = "claude-code"
CLAUDE_READ_ONLY_TOOLS = ("Read", "Glob", "Grep")
CLAUDE_DENIED_TOOLS = (
    "Bash",
    "Edit",
    "Write",
    "Agent",
    "AskUserQuestion",
    "WebSearch",
    "WebFetch",
    "NotebookEdit",
    "TodoWrite",
)
CLAUDE_CONTROL_ACTIONS = (
    *CLAUDE_READ_ONLY_TOOLS,
    *CLAUDE_DENIED_TOOLS,
    "MCP",
    "Plugins",
    "Chrome",
)
WORKSPACE_MARKER = "<isolated-fixture>"


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


def _instruction_digest(instructions: str) -> str:
    return "sha256:" + hashlib.sha256(instructions.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ClaudeInvocation:
    """Execution-local command and prompt with a safe public summary."""

    argv: tuple[str, ...] = field(repr=False, compare=False)
    workspace_root: Path = field(repr=False, compare=False)
    timeout_s: float
    environment: Mapping[str, str] | None = field(
        default=None, repr=False, compare=False
    )
    public: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaudeAdapterResult:
    """Public adapter result; execution-local skill bodies stay out of it."""

    status: str
    reason_code: str | None = None
    errors: list[str] = field(default_factory=list)
    bundle: dict[str, Any] | None = None
    projection: dict[str, Any] | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    loaded_skills: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    execution_skills: tuple[LoadedSkill, ...] = field(
        default_factory=tuple, repr=False, compare=False
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize references and metrics, never bodies or prompts."""

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


def _permission_projection_for(envelope: dict[str, Any]) -> dict[str, Any]:
    """Map only the supported read-only portable envelope.

    Claude's tool allowlist and ``dontAsk`` mode are native controls.  The
    exact fixture-path boundary remains host-managed by the isolated process
    cwd and the selected read tools.  Broader portable authority fails closed.
    """

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
            "classification": "NATIVE_EXACT" if filesystem == "none" else "HOST_MANAGED",
            "native_scope": "NONE" if filesystem == "none" else "ISOLATED_FIXTURE",
            "reason": (
                "Claude dontAsk plus an explicit Read/Glob/Grep allowlist is native; "
                "fixture path isolation is enforced by the host process boundary."
            ),
            "explicit_denials": [
                "Edit",
                "Write",
                "Bash",
                "Agent",
                "AskUserQuestion",
                "WebSearch",
                "WebFetch",
                "NotebookEdit",
                "TodoWrite",
                "MCP",
                "Plugins",
                "Chrome",
                "external paths",
                "secrets",
            ],
        }
    return {
        "filesystem": filesystem,
        "classification": "BLOCKED",
        "native_scope": "NONE",
        "reason": (
            "Claude Phase 3D projection is read-only and cannot represent portable "
            f"authority {filesystem!r} without risking a broader native allow."
        ),
        "explicit_denials": ["unsupported authority"],
    }


def _no_ask_proof(filesystem: str) -> dict[str, Any]:
    resolved = {
        action: (
            "ALLOW"
            if action in CLAUDE_READ_ONLY_TOOLS and filesystem in {"read", "workspace-read"}
            else "DENY"
        )
        for action in CLAUDE_CONTROL_ACTIONS
    }
    return {
        "no_ask": True,
        "required_actions": list(CLAUDE_CONTROL_ACTIONS),
        "resolved_actions": resolved,
        "method": (
            "dontAsk plus explicit --tools/--allowedTools read allowlist; "
            "all other reachable controls are absent or denied"
        ),
    }


def _contains_ask(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() == "ask"
    if isinstance(value, dict):
        return any(_contains_ask(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_ask(child) for child in value)
    return False


def validate_no_ask_projection(projection: dict[str, Any]) -> list[str]:
    """Return safety errors for a projection intended for headless execution."""

    errors: list[str] = []
    if projection.get("runtime_id") != CLAUDE_RUNTIME_ID:
        errors.append("projection runtime_id is not claude-code")
    config = projection.get("config")
    values = config.get("values") if isinstance(config, dict) else None
    if not isinstance(values, dict):
        errors.append("projection has no Claude native config values")
        values = {}
    if values.get("permission_mode") != "dontAsk":
        errors.append("Claude headless projection must use dontAsk")
    if values.get("tools") != list(CLAUDE_READ_ONLY_TOOLS):
        errors.append("Claude tools must be exactly Read, Glob, Grep")
    if values.get("allowed_tools") != list(CLAUDE_READ_ONLY_TOOLS):
        errors.append("Claude allowed_tools must be exactly Read, Glob, Grep")
    for field_name in (
        "safe_mode",
        "no_session_persistence",
        "no_chrome",
        "strict_mcp_config",
        "disable_slash_commands",
    ):
        if values.get(field_name) is not True:
            errors.append(f"Claude {field_name} must be enabled for this lane")
    if values.get("mcp_config") != '{"mcpServers":{}}':
        errors.append("Claude MCP config must be an explicit empty object")
    if any(
        value in {"auto", "bypassPermissions", "acceptEdits", "manual", "plan"}
        for value in (values.get("permission_mode"),)
    ):
        errors.append("dangerous or prompt-bearing Claude permission mode selected")
    if _contains_ask(values):
        errors.append("Claude native config contains an unresolved ask value")

    permissions = projection.get("permissions")
    if not isinstance(permissions, dict):
        errors.append("projection has no explicit Claude permission projection")
        permissions = {}
    if permissions.get("filesystem") not in {"none", "read", "workspace-read"}:
        errors.append("Claude permission projection is broader than read-only")
    if permissions.get("classification") == "BLOCKED":
        errors.append("Claude permission projection is blocked")
    if not permissions.get("explicit_denials"):
        errors.append("Claude projection must include explicit denials")

    for surface, expected_status in (
        ("mcp", "DENY"),
        ("plugins", "DENY"),
        ("subagents", "DENY"),
    ):
        item = projection.get(surface)
        if not isinstance(item, dict) or item.get("status") != expected_status:
            errors.append(f"Claude {surface} must be explicitly denied")
        elif item.get("refs") != []:
            errors.append(f"Claude {surface} references must be empty")
    hooks = projection.get("hooks")
    if not isinstance(hooks, dict) or hooks.get("status") != "DISABLED" or hooks.get("refs") != []:
        errors.append("Claude hooks must be disabled and empty")

    proof = projection.get("no_ask_proof")
    if not isinstance(proof, dict) or proof.get("no_ask") is not True:
        errors.append("projection is missing its no-ASK proof")
    else:
        required = set(proof.get("required_actions", []))
        resolved = proof.get("resolved_actions")
        if not isinstance(resolved, dict) or not required.issubset(resolved):
            errors.append("no-ASK proof does not resolve every required action")
        elif set(resolved.values()) - {"ALLOW", "DENY"}:
            errors.append("no-ASK proof contains an unresolved action")
        elif _contains_ask(resolved):
            errors.append("no-ASK proof contains ASK")

    invocation = projection.get("invocation")
    if not isinstance(invocation, dict):
        errors.append("projection has no Claude invocation boundary")
    else:
        for field_name, expected in (
            ("output_format", "json"),
            ("permission_mode", "dontAsk"),
            ("safe_mode", True),
            ("no_session_persistence", True),
            ("no_chrome", True),
            ("strict_mcp_config", True),
            ("disable_slash_commands", True),
            ("shell", False),
            ("stdin", "DEVNULL"),
            ("cwd_mode", "ISOLATED_FIXTURE"),
            ("auto", False),
            ("raw_prompt_serialized", False),
            ("raw_skill_bodies_serialized", False),
        ):
            if invocation.get(field_name) != expected:
                errors.append(f"Claude invocation {field_name} is not {expected!r}")
        if not isinstance(invocation.get("timeout_ms"), int) or invocation["timeout_ms"] <= 0:
            errors.append("Claude invocation must have a finite positive timeout")
        if any(
            forbidden in invocation.get("forbidden_flags", [])
            for forbidden in ("--bare", "--auto", "--dangerously-skip-permissions", "--permission-mode bypassPermissions")
        ):
            errors.append("Claude invocation contains a forbidden bypass flag")
    return errors


def build_claude_invocation(
    projection: dict[str, Any],
    *,
    workspace_root: str | Path,
    prompt: str,
    timeout_s: float = 120,
    tools_override: Iterable[str] | None = None,
    execution_instructions: str | None = None,
) -> ClaudeInvocation:
    """Build an explicit ``claude -p`` invocation without shell expansion."""

    root = Path(workspace_root).resolve()
    if not root.is_dir():
        raise ValueError(f"isolated Claude workspace does not exist: {root}")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("headless Claude prompt must be non-empty")
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    safety_errors = validate_no_ask_projection(projection)
    if safety_errors:
        raise ValueError("unsafe Claude projection: " + "; ".join(safety_errors))

    config = projection["config"]["values"]
    tools = list(config["tools"] if tools_override is None else tools_override)
    if any(tool not in CLAUDE_READ_ONLY_TOOLS for tool in tools):
        raise ValueError("Claude tool override contains a non-read-only tool")
    if len(set(tools)) != len(tools):
        raise ValueError("Claude tool override contains duplicate tools")
    tool_text = ",".join(tools)
    argv: list[str] = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        config["output_format"],
        "--permission-mode",
        config["permission_mode"],
        "--tools",
        tool_text,
        "--allowed-tools",
        tool_text,
        "--safe-mode",
        "--no-session-persistence",
        "--no-chrome",
        "--strict-mcp-config",
        "--mcp-config",
        config["mcp_config"],
        "--disable-slash-commands",
        "--max-budget-usd",
        str(config["max_budget_usd"]),
    ]
    public: dict[str, Any] = {
        "argv": [
            "claude",
            "-p",
            "<prompt>",
            "--output-format",
            config["output_format"],
            "--permission-mode",
            config["permission_mode"],
            "--tools",
            tool_text,
            "--allowed-tools",
            tool_text,
            "--safe-mode",
            "--no-session-persistence",
            "--no-chrome",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--disable-slash-commands",
            "--max-budget-usd",
            str(config["max_budget_usd"]),
        ],
        "tools": tools,
        "allowed_tools": tools,
        "shell": False,
        "stdin": "DEVNULL",
        "timeout_ms": int(timeout_s * 1000),
        "cwd": WORKSPACE_MARKER,
        "cwd_mode": "ISOLATED_FIXTURE",
        "safe_mode": True,
        "no_session_persistence": True,
        "no_chrome": True,
        "strict_mcp_config": True,
        "disable_slash_commands": True,
        "auto": False,
        "raw_prompt_serialized": False,
        "raw_skill_bodies_serialized": False,
    }
    if execution_instructions:
        if not isinstance(execution_instructions, str):
            raise ValueError("execution instructions must be text")
        argv.extend(("--append-system-prompt", execution_instructions))
        public["execution_instruction_digest"] = _instruction_digest(execution_instructions)
        public["execution_instruction_bytes"] = len(
            execution_instructions.encode("utf-8")
        )
    return ClaudeInvocation(
        argv=tuple(argv),
        workspace_root=root,
        timeout_s=timeout_s,
        public=public,
    )


class ClaudeAdapter:
    """Compile and execute one validated read-only Claude Code route."""

    def __init__(
        self,
        repository_root: str | Path,
        registry_path: str | Path,
        *,
        policy: dict[str, Any] | None = None,
        live_runtime: dict[str, Any] | None = None,
        native_contract: dict[str, Any] | None = None,
        observed_runtime_version: str | None = "2.1.235",
        timeout_s: float = 120,
        max_budget_usd: float = 0.25,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.registry_path = Path(registry_path)
        self.policy = copy.deepcopy(policy or {})
        self.live_runtime = copy.deepcopy(live_runtime or {})
        self.native_contract = copy.deepcopy(native_contract)
        self.observed_runtime_version = observed_runtime_version
        self.timeout_s = timeout_s
        self.max_budget_usd = max_budget_usd

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
    ) -> ClaudeAdapterResult:
        """Consume a StageRoute and produce a portable bundle plus projection."""

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
            return ClaudeAdapterResult(
                status="BLOCKED", reason_code="INVALID_CONTRACT", errors=validation_errors
            )
        if (
            adapter_manifest.get("runtime_id") != CLAUDE_RUNTIME_ID
            or stage_route.get("adapter") != CLAUDE_RUNTIME_ID
        ):
            return ClaudeAdapterResult(
                status="BLOCKED",
                reason_code="RUNTIME_MISMATCH",
                errors=["ClaudeAdapter accepts only a claude-code StageRoute and manifest."],
            )

        selected = (
            []
            if stage_route.get("status") == "NO_SKILL_NEEDED"
            else stage_route.get("selected_skills", [])
        )
        selected_metadata = self._metadata_for_capabilities(selected, records)
        capability_result = capability_requirements(
            task_spec, stage_route, adapter_manifest, model_profile, selected_metadata
        )
        if capability_result["status"] != "ALLOWED":
            return ClaudeAdapterResult(
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
            return ClaudeAdapterResult(
                status="BLOCKED",
                reason_code="PERMISSION_INTERSECTION",
                errors=permission_result["reasons"],
                metrics={"permissions": permission_result},
            )
        permission_projection = _permission_projection_for(permission_result["effective"])
        if permission_projection["classification"] == "BLOCKED":
            return ClaudeAdapterResult(
                status="BLOCKED",
                reason_code="PERMISSION_PROJECTION",
                errors=[permission_projection["reason"]],
                metrics={"permissions": permission_result},
            )

        resolver = SkillResolver(self.repository_root, self.registry_path)
        resolution = resolver.resolve(selected, records)
        if resolution.status != "READY":
            return ClaudeAdapterResult(
                status="BLOCKED",
                reason_code=resolution.reason_code,
                errors=resolution.errors,
                metrics=self._resolution_metrics(resolution),
            )

        artifact_errors = validate_reasoning_artifacts(reasoning_artifacts or {})
        if artifact_errors:
            return ClaudeAdapterResult(
                status="BLOCKED",
                reason_code="HIDDEN_REASONING_FIELD",
                errors=artifact_errors,
                metrics=self._resolution_metrics(resolution),
            )
        try:
            refs = artifact_refs(reasoning_artifacts or {})
        except ValueError as exc:
            return ClaudeAdapterResult(
                status="BLOCKED",
                reason_code="INVALID_ARTIFACTS",
                errors=[str(exc)],
                metrics=self._resolution_metrics(resolution),
            )

        evidence = evaluate_evidence(stage_route.get("evidence_required", []), observed_evidence)
        bundle_status = "READY" if evidence["status"] == "PASS" else "BLOCKED"
        blocked_reason = (
            None
            if bundle_status == "READY"
            else "Evidence gate did not pass; execution completion is blocked."
        )
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
            return ClaudeAdapterResult(
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
            return ClaudeAdapterResult(
                status="BLOCKED",
                reason_code=exc.reason_code,
                errors=[str(exc)],
                bundle=bundle,
                evidence=evidence,
                metrics=self._resolution_metrics(resolution),
            )
        except ValueError as exc:
            return ClaudeAdapterResult(
                status="BLOCKED",
                reason_code="PROJECTION_UNSUPPORTED",
                errors=[str(exc)],
                bundle=bundle,
                evidence=evidence,
                metrics=self._resolution_metrics(resolution),
            )

        public_loaded = [self._loaded_skill_record(skill) for skill in resolution.loaded]
        if evidence["status"] != "PASS":
            return ClaudeAdapterResult(
                status="BLOCKED",
                reason_code="EVIDENCE_MISSING",
                errors=[blocked_reason or "evidence gate blocked"],
                bundle=bundle,
                projection=projection,
                evidence=evidence,
                loaded_skills=public_loaded,
                metrics=self._resolution_metrics(resolution),
                execution_skills=tuple(resolution.loaded),
            )
        return ClaudeAdapterResult(
            status="READY",
            bundle=bundle,
            projection=projection,
            evidence=evidence,
            loaded_skills=public_loaded,
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
        """Produce only verified Claude CLI surfaces."""

        del task_spec, stage_route, model_profile
        if adapter_manifest.get("runtime_id") != CLAUDE_RUNTIME_ID:
            raise ValueError("Claude projection requires the claude-code adapter manifest")
        permission_projection = _permission_projection_for(bundle["permission_envelope"])
        if permission_projection["classification"] == "BLOCKED":
            raise NativeContractError("PERMISSION_PROJECTION", permission_projection["reason"])

        contract = load_native_contract() if self.native_contract is None else self.native_contract
        config_values = {
            "permission_mode": "dontAsk",
            "tools": list(CLAUDE_READ_ONLY_TOOLS),
            "allowed_tools": list(CLAUDE_READ_ONLY_TOOLS),
            "output_format": "json",
            "max_budget_usd": self.max_budget_usd,
            "no_session_persistence": True,
            "no_chrome": True,
            "safe_mode": True,
            "strict_mcp_config": True,
            "mcp_config": '{"mcpServers":{}}',
            "disable_slash_commands": True,
        }
        native_validation = validate_claude_config(
            config_values,
            contract=contract,
            expected_target="INSTALLED_RUNTIME",
            observed_runtime_version=self.observed_runtime_version,
        )
        if not native_validation.valid:
            raise NativeContractError(
                native_validation.reason_code or "INVALID_NATIVE_CONFIG",
                "invalid Claude native config contract: " + "; ".join(native_validation.errors),
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
        projection = {
            "schema_version": "3.0",
            "projection_version": "1.0",
            "runtime_id": CLAUDE_RUNTIME_ID,
            "bundle_digest": bundle["bundle_digest"],
            "support_levels": {
                "CLAUDE.md": "NATIVE",
                "Skills": "NATIVE",
                "skill_body_delivery": "HOST_MANAGED",
                "Hooks": "NATIVE",
                "Subagents": "NATIVE",
                "Plugins": "NATIVE",
                "MCP": "NATIVE",
                "config": "NATIVE",
                "permission_mode": "NATIVE",
                "tools": "NATIVE",
                "output_format": "NATIVE",
                "safe_mode": "NATIVE",
                "model": "NATIVE",
                "effort": "NATIVE",
                "static_context": "HOST_MANAGED",
                "dynamic_context": "HOST_MANAGED",
                "tool_schema_context": "HOST_MANAGED",
                "evidence_gate": "HOST_MANAGED",
            },
            "instruction_surfaces": {
                "persistent": [
                    {
                        "path": "CLAUDE.md",
                        "scope": "project",
                        "purposes": ["project-context", "routing-bootstrap"],
                    }
                ]
            },
            "skills": {
                "load_mode": "selected-only",
                "native_surface": "HOST_MANAGED",
                "selected": selected_refs,
                # The native directory is not populated and safe-mode is used;
                # selected procedure bodies remain execution-local instead.
                "body_files_loaded": 0,
            },
            "config": {"surface": "CLI_FLAGS", "values": config_values},
            "invocation": {
                "command": "claude -p",
                "output_format": "json",
                "permission_mode": "dontAsk",
                "tools": list(CLAUDE_READ_ONLY_TOOLS),
                "allowed_tools": list(CLAUDE_READ_ONLY_TOOLS),
                "safe_mode": True,
                "no_session_persistence": True,
                "no_chrome": True,
                "strict_mcp_config": True,
                "disable_slash_commands": True,
                "shell": False,
                "stdin": "DEVNULL",
                "cwd_mode": "ISOLATED_FIXTURE",
                "timeout_ms": int(self.timeout_s * 1000),
                "max_budget_usd": self.max_budget_usd,
                "auto": False,
                "raw_prompt_serialized": False,
                "raw_skill_bodies_serialized": False,
            },
            "permissions": permission_projection,
            "mcp": {"status": "DENY", "refs": [], "schema_loaded": False},
            "plugins": {"status": "DENY", "refs": []},
            "hooks": {"status": "DISABLED", "refs": []},
            "subagents": {"status": "DENY", "refs": []},
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
            "no_ask_proof": _no_ask_proof(bundle["permission_envelope"]["filesystem"]),
        }
        validation = validate_instance("ClaudeNativeProjection", projection)
        if not validation.valid:
            raise ValueError("invalid Claude native projection: " + "; ".join(validation.errors))
        return projection

    def execute(
        self,
        projection: dict[str, Any],
        *,
        workspace_root: str | Path,
        prompt: str,
        timeout_s: float | None = None,
        execution_skills: Iterable[LoadedSkill] = (),
    ) -> ProcessObservation:
        """Run selected procedure text ephemerally; persist only observations."""

        selected_refs = {
            (
                item.get("skill_id"),
                item.get("source_path"),
                item.get("digest"),
                item.get("role"),
            )
            for item in projection.get("skills", {}).get("selected", [])
            if isinstance(item, dict)
        }
        execution_items = tuple(execution_skills)
        for skill in execution_items:
            reference = (skill.skill_id, skill.source_path, skill.digest, skill.role)
            if reference not in selected_refs:
                raise ValueError(
                    f"execution skill is not present in the selected Claude projection: {skill.skill_id}"
                )
            if skill.load_state == "LOADED" and _instruction_digest(skill.content) != skill.digest:
                raise ValueError(
                    f"execution skill digest does not match its loaded body: {skill.skill_id}"
                )
        blocks = [
            f"Selected procedure {skill.skill_id} ({skill.digest}, role={skill.role}):\n"
            + skill.content
            for skill in execution_items
            if skill.content
        ]
        instructions = "\n\n".join(blocks) if blocks else None
        invocation = build_claude_invocation(
            projection,
            workspace_root=workspace_root,
            prompt=prompt,
            timeout_s=self.timeout_s if timeout_s is None else timeout_s,
            execution_instructions=instructions,
        )
        return run_headless_command(
            invocation.argv,
            cwd=invocation.workspace_root,
            timeout_s=invocation.timeout_s,
        )

    @staticmethod
    def _metadata_for_capabilities(
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


__all__ = [
    "CLAUDE_DENIED_TOOLS",
    "CLAUDE_READ_ONLY_TOOLS",
    "ClaudeAdapter",
    "ClaudeAdapterResult",
    "ClaudeInvocation",
    "build_claude_invocation",
    "validate_no_ask_projection",
]
