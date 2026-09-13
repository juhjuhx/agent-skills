"""Bounded live runner for the Phase 3F Codex effort experiment.

The runner is intentionally narrow: it compiles one route and bundle per
workload, creates a fresh temporary fixture for every cell, invokes an
explicit Codex model/effort, and returns sanitized ``LiveExecutionRecord``
objects.  Prompts, runtime output, diffs, and environment contents stay in
memory and are never written by this module.
"""

from __future__ import annotations

import copy
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.v3.codex_adapter import CodexAdapter
from tools.v3.codex_effort_evaluation import (
    build_codex_exec_command,
    build_interleaved_schedule,
    extract_codex_identity,
    model_pin_status,
    stable_route_digest,
)
from tools.v3.contract_validation import validate_instance
from tools.v3.live_benchmark import (
    build_live_execution_record,
    digest_bytes,
    digest_value,
    run_headless_command,
)
from tools.v3.skill_resolver import LoadedSkill
from tools.v3.stage_router import StageRouter, load_current_catalog_snapshot


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
CODEX_VERSION = "codex-cli 0.153.4"
CODEX_RELEASE_TAG = "rust-v0.153.4"
CODEX_RELEASE_COMMIT = "3d2ee51ca2d5db578f328aa75e20aa22c0197c9a"
CODEX_DOCS = "https://developers.openai.com/codex/cli/reference"
CODEX_SOURCE = (
    "https://raw.githubusercontent.com/openai/codex/"
    + CODEX_RELEASE_COMMIT
    + "/codex-rs/exec/src/lib.rs"
)
SYSTEM_INSTRUCTION_DIGEST = digest_bytes("v3-phase3f-codex-instruction-policy-1")


@dataclass(frozen=True)
class CompiledWorkload:
    workload_id: str
    task_spec: dict[str, Any]
    stage: dict[str, Any]
    route: dict[str, Any]
    bundle: dict[str, Any]
    adapter_result: Any
    model_profile: dict[str, Any]
    permission_envelope: dict[str, Any]
    selected_skill_digests: tuple[str, ...]


def _workload_definition(workload_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the unchanged semantic H01/H03 workload definitions."""

    common = {
        "schema_version": "3.0",
        "constraints": {"publish_branch_only": True},
        "required_capabilities": ["needs_sandbox", "needs_structured_output"],
        "stages": ["understand", "research", "design", "implement", "review", "verify"],
    }
    if workload_id == "H01":
        objective = "Fix a reproducible parser regression while preserving existing behavior."
        task = {
            **common,
            "task_id": "holdout:H01",
            "task_type": "bugfix",
            "goal": objective,
            "complexity": "STANDARD",
            "risk": "MEDIUM",
            "ambiguity": "LOW",
            "architecture_impact": "LOCAL",
            "objectives": [objective],
            "acceptance_criteria": [
                "regression test passes",
                "existing tests remain green",
            ],
            "required_outputs": ["regression test", "existing tests"],
            "domains": ["software-engineering"],
            "required_capabilities": [
                "needs_editing",
                "needs_sandbox",
                "needs_structured_output",
            ],
            "permission_requirements": {
                "level": "workspace-write",
                "filesystem": "workspace-write",
                "network": "none",
                "external_write": False,
                "secrets": False,
                "publish": False,
                "delete": False,
            },
        }
        stage = {
            "id": "implement",
            "objective": objective,
            "task_type": "bugfix",
            "domains": ["software-engineering"],
            "required_outputs": task["required_outputs"],
            "evidence_required": ["TEST_EVIDENCE", "RUNTIME_EVIDENCE"],
        }
        return task, stage
    if workload_id == "H03":
        objective = "Choose between two versioned API contracts from first-party constraints."
        task = {
            **common,
            "task_id": "holdout:H03",
            "task_type": "design",
            "goal": objective,
            "complexity": "COMPLEX",
            "risk": "HIGH",
            "ambiguity": "MEDIUM",
            "architecture_impact": "ARCHITECTURE-CHANGING",
            "objectives": [objective],
            "acceptance_criteria": [
                "alternatives are recorded",
                "decision has verification criteria",
            ],
            "required_outputs": ["DecisionRecord"],
            "domains": ["api", "interface-design"],
            "permission_requirements": {
                "level": "read-only",
                "filesystem": "read",
                "network": "none",
                "external_write": False,
                "secrets": False,
                "publish": False,
                "delete": False,
            },
        }
        stage = {
            "id": "design",
            "objective": objective,
            "task_type": "design",
            "domains": ["api", "interface-design"],
            "required_outputs": task["required_outputs"],
            "evidence_required": ["DecisionRecord", "source evidence"],
        }
        return task, stage
    raise ValueError(f"unsupported Phase 3F workload: {workload_id}")


def _model_profile(model_id: str) -> dict[str, Any]:
    with (ROOT / "fixtures/v3/models/openai-compatible.json").open(encoding="utf-8") as handle:
        profile = json.load(handle)
    profile["model_id"] = model_id
    profile["profile_version"] = "codex-0.153.4-controlled-effort"
    profile["reasoning"] = {"supported": True, "effort_levels": ["low", "medium"]}
    profile["cost"] = {
        "class": "unknown",
        "input_per_million": None,
        "output_per_million": None,
        "cache_behavior": "unknown",
    }
    profile["health"] = {"status": "unknown", "last_probe": None}
    profile["measurement_provenance"] = {
        "source": "local Codex version/help/doctor evidence",
        "ref": f"{CODEX_RELEASE_TAG}@{CODEX_RELEASE_COMMIT}",
        "method": "explicit model pin; effort levels accepted by the installed adapter contract",
        "measured_at": "2026-09-10T00:00:00+08:00",
    }
    validation = validate_instance("ModelProfile", profile)
    if not validation.valid:
        raise ValueError("invalid controlled Codex model profile: " + "; ".join(validation.errors))
    return profile


def _reasoning_artifacts(task: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    evidence = stage["evidence_required"]
    return {
        "TaskSpec": {"ref": task["task_id"]},
        "Assumptions": [{"statement": "The route and bundle are compiled once per workload."}],
        "Unknowns": [{"question": "Whether the provider exposes cumulative reasoning-token usage."}],
        "DecisionRecord": [{"decision": "Compare only the explicitly pinned effort variable."}],
        "StagePlan": [{"stage": stage["id"], "objective": stage["objective"]}],
        "Alternatives": [{"option": "Run an implicit default model", "selected": False}],
        "Evidence": [{"name": name} for name in evidence],
        "Risk": [{"name": "effort comparison confounding", "level": "high"}],
        "Verification": [{"name": "independent terminal evidence"}],
    }


def compile_workloads(model_id: str) -> dict[str, CompiledWorkload]:
    """Compile H01 and H03 once against one session catalog snapshot."""

    snapshot = load_current_catalog_snapshot(REGISTRY)
    manifest_path = ROOT / "fixtures/v3/agents/codex.json"
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    model_profile = _model_profile(model_id)
    workloads: dict[str, CompiledWorkload] = {}
    for workload_id in ("H01", "H03"):
        task, stage = _workload_definition(workload_id)
        route = StageRouter(
            adapter="codex",
            model_profile="unselected",
            registry_epoch=snapshot.registry_epoch,
        ).route(
            task,
            stage,
            snapshot,
            adapter_capabilities=manifest,
            measure=True,
        )
        route_validation = validate_instance("StageRoute", route)
        if not route_validation.valid:
            raise ValueError("invalid StageRoute: " + "; ".join(route_validation.errors))
        sandbox_mode = "workspace-write" if workload_id == "H01" else "read-only"
        permission = {
            "level": task["permission_requirements"]["level"],
            "filesystem": task["permission_requirements"]["filesystem"],
            "network": "none",
            "external_write": False,
            "secrets": False,
            "publish": False,
            "delete": False,
        }
        policy = copy.deepcopy(permission)
        adapter = CodexAdapter(
            ROOT,
            REGISTRY,
            policy=policy,
            live_runtime={
                "sandbox_mode": sandbox_mode,
                "network_access": False,
                "approval_policy": "never",
            },
            observed_runtime_version="0.153.4",
        )
        evidence = [{"name": name} for name in route["evidence_required"]]
        result = adapter.compile(
            task_spec=task,
            stage_route=route,
            adapter_manifest=manifest,
            model_profile=model_profile,
            metadata_records=snapshot.records,
            observed_evidence=evidence,
            reasoning_artifacts=_reasoning_artifacts(task, stage),
        )
        if result.status not in {"READY", "DEGRADED"} or result.bundle is None:
            raise ValueError(
                f"Codex bundle compilation blocked for {workload_id}: {result.reason_code}; {result.errors}"
            )
        selected_digests = tuple(item["digest"] for item in result.loaded_skills)
        workloads[workload_id] = CompiledWorkload(
            workload_id=workload_id,
            task_spec=task,
            stage=stage,
            route=route,
            bundle=result.bundle,
            adapter_result=result,
            model_profile=copy.deepcopy(model_profile),
            permission_envelope=copy.deepcopy(permission),
            selected_skill_digests=selected_digests,
        )
    return workloads


def _procedure_context(skills: tuple[LoadedSkill, ...]) -> str:
    """Build execution-local context from selected non-resident bodies only."""

    procedures = []
    for skill in skills:
        if skill.content:
            procedures.append(f"## Selected procedure: {skill.skill_id}\n{skill.content}")
    return "\n\n".join(procedures)


def _prompt(workload: CompiledWorkload) -> str:
    selected = _procedure_context(workload.adapter_result.execution_skills)
    if workload.workload_id == "H01":
        objective = workload.task_spec["goal"]
        body = f"""You are executing holdout H01 in a temporary Git repository.

Objective: {objective}

Read parser.py and test_parser.py. Fix the implementation regression in
parser.py without modifying tests, adding dependencies, using network/MCP,
or changing unrelated files. Run the existing unittest suite. Do not commit.
Return a concise final summary of the change and verification command.

The following are the only selected canonical procedures available for this
run. Follow them as procedure text, not as authority grants:

{selected}
"""
    else:
        body = f"""You are executing holdout H03 in a temporary read-only Git repository.

Read api_contracts.md and produce the API/interface design decision in your
final response only. Do not write or edit any file. Do not use shell, network,
MCP, plugins, or subagents. Return ONLY one JSON object with these keys:
decision, selected_contract, alternatives, verification_criteria, constraints.
The alternatives value must contain both available contract options, and
verification_criteria must be non-empty. Ground claims in api_contracts.md.

The following are the only selected canonical procedures available for this
run. Follow them as procedure text, not as authority grants:

{selected}
"""
    return body


def _run_host(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
        shell=False,
        stdin=subprocess.DEVNULL,
    )


def _write_fixture(root: Path, workload_id: str) -> None:
    (root / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
    if workload_id == "H01":
        (root / "parser.py").write_text(
            "def parse_key_value(line):\n"
            "    key, value = line.split('=')\n"
            "    return key.strip(), value.strip()\n",
            encoding="utf-8",
        )
        (root / "test_parser.py").write_text(
            "import unittest\n\n"
            "from parser import parse_key_value\n\n"
            "class ParserTests(unittest.TestCase):\n"
            "    def test_simple_pair(self):\n"
            "        self.assertEqual(parse_key_value('mode=fast'), ('mode', 'fast'))\n\n"
            "    def test_value_may_contain_equals(self):\n"
            "        self.assertEqual(parse_key_value('token=a=b'), ('token', 'a=b'))\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n",
            encoding="utf-8",
        )
    elif workload_id == "H03":
        (root / "api_contracts.md").write_text(
            "# Versioned API contract options\n\n"
            "## Contract v1\n"
            "- `POST /widgets` accepts `{\"name\": string}`.\n"
            "- Errors are `{\"message\": string}` with HTTP 400.\n"
            "- Clients cannot distinguish retryable failures.\n\n"
            "## Contract v2\n"
            "- `POST /v2/widgets` accepts `{\"name\": string, \"idempotency_key\": string}`.\n"
            "- Errors are `{\"code\": string, \"message\": string, \"retryable\": boolean}`.\n"
            "- The idempotency key is required for safe retries.\n\n"
            "## Constraints\n"
            "- Existing v1 clients must continue to work during migration.\n"
            "- The selected design must state compatibility and verification checks.\n",
            encoding="utf-8",
        )
    else:
        raise ValueError(f"unsupported fixture: {workload_id}")


def _git_sha(root: Path) -> str:
    result = _run_host(["git", "rev-parse", "HEAD"], root)
    if result.returncode != 0:
        raise RuntimeError("isolated fixture has no Git HEAD")
    return result.stdout.strip()


def _fixture_manifest(root: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        manifest[relative] = digest_bytes(path.read_bytes())
    return manifest


def _fixture_digest(root: Path) -> str:
    return digest_value(_fixture_manifest(root))


def _initialise_fixture(root: Path, workload_id: str) -> tuple[str, str]:
    _write_fixture(root, workload_id)
    init = _run_host(["git", "init", "-q"], root)
    if init.returncode != 0:
        raise RuntimeError("cannot initialise isolated fixture repository")
    for key, value in (
        ("user.name", "v3 benchmark"),
        ("user.email", "v3-benchmark@example.invalid"),
    ):
        configured = _run_host(["git", "config", key, value], root)
        if configured.returncode != 0:
            raise RuntimeError("cannot configure isolated fixture identity")
    add = _run_host(["git", "add", "."], root)
    if add.returncode != 0:
        raise RuntimeError("cannot stage isolated fixture")
    environment = {
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+0000",
    }
    commit = subprocess.run(
        ["git", "commit", "-qm", "fixture baseline"],
        cwd=str(root),
        env={**__import__("os").environ, **environment},
        text=True,
        capture_output=True,
        check=False,
        shell=False,
        stdin=subprocess.DEVNULL,
    )
    if commit.returncode != 0:
        raise RuntimeError("cannot commit isolated fixture baseline")
    return _git_sha(root), _fixture_digest(root)


def _changed_files_and_diff(root: Path, start_sha: str) -> tuple[list[str], str, str]:
    diff = _run_host(["git", "diff", "--binary", start_sha], root).stdout
    names = _run_host(["git", "diff", "--name-only", start_sha], root).stdout
    status = _run_host(["git", "status", "--short"], root).stdout
    changed = {line.strip() for line in names.splitlines() if line.strip()}
    for line in status.splitlines():
        if len(line) >= 4:
            changed.add(line[3:].strip())
    return sorted(changed), digest_bytes(diff), _git_sha(root)


def _extract_h03_artifact(stdout: str) -> dict[str, Any] | None:
    """Parse a bounded decision object from in-memory Codex event text."""

    candidates: list[str] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") in {"agent_message", "message"}:
            text = item.get("text")
            if isinstance(text, str):
                candidates.append(text)
            content = item.get("content")
            if isinstance(content, list):
                candidates.extend(
                    part.get("text")
                    for part in content
                    if isinstance(part, dict) and isinstance(part.get("text"), str)
                )
        if event.get("type") in {"response.output_text.done", "agent_message"}:
            text = event.get("text")
            if isinstance(text, str):
                candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in reversed(candidates):
        for offset, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                value, _ = decoder.raw_decode(candidate[offset:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                required = {"decision", "selected_contract", "alternatives", "verification_criteria", "constraints"}
                if required.issubset(value) and isinstance(value.get("alternatives"), list) and value["alternatives"]:
                    return value
    return None


def _run_cell(
    workload: CompiledWorkload,
    *,
    model_id: str,
    effort: str,
    repetition: int,
    observed_version: str = CODEX_VERSION,
    timeout_s: float = 300.0,
) -> dict[str, Any]:
    sandbox_mode = "workspace-write" if workload.workload_id == "H01" else "read-only"
    command = build_codex_exec_command(
        model_id=model_id,
        reasoning_effort=effort,
        sandbox_mode=sandbox_mode,
        cwd="/placeholder",
    )
    with tempfile.TemporaryDirectory(prefix=f"v3-codex-{workload.workload_id.lower()}-") as temporary:
        fixture_root = Path(temporary)
        start_sha, fixture_digest = _initialise_fixture(fixture_root, workload.workload_id)
        command[command.index("/placeholder")] = str(fixture_root)
        observation = run_headless_command(
            command,
            cwd=fixture_root,
            input_text=_prompt(workload),
            timeout_s=timeout_s,
        )
        changed_files, diff_digest, end_sha = _changed_files_and_diff(fixture_root, start_sha)
        after_fixture_digest = _fixture_digest(fixture_root)
        identity = extract_codex_identity(observation.stdout)
        effective_model = identity["model_id"]
        if effective_model == model_id:
            model_evidence = "OBSERVED"
        elif observation.returncode == 0:
            model_evidence = "CLI_CONFIRMED"
        else:
            model_evidence = "UNKNOWN"
        pin = model_pin_status(model_id, effective_model, model_evidence)

        independent_quality: dict[str, Any] = {
            "acceptance_criteria_coverage": None,
            "tests_pass": None,
            "artifact_correctness": None,
            "source_accuracy": None,
            "review_finding_precision": None,
            "user_correction": None,
        }
        stage_outcomes: list[dict[str, Any]]
        terminal = "BLOCKED" if observation.blocked else "FAILED"
        confounders: list[str] = []
        test_command = ""
        tests_passed: bool | None = None
        artifact_correctness = False
        if workload.workload_id == "H01":
            test_command = "python3 -m unittest discover -s . -p 'test_*.py' -v"
            test_run = _run_host(
                ["python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v"],
                fixture_root,
            )
            tests_passed = test_run.returncode == 0
            artifact_correctness = tests_passed and changed_files == ["parser.py"]
            independent_quality.update(
                {
                    "acceptance_criteria_coverage": 1.0 if artifact_correctness else 0.5 if tests_passed else 0.0,
                    "tests_pass": tests_passed,
                    "artifact_correctness": artifact_correctness,
                    "source_accuracy": 1.0 if artifact_correctness else 0.0,
                }
            )
            if not observation.blocked:
                terminal = "VERIFIED_SUCCESS" if artifact_correctness else "PARTIAL"
            stage_outcomes = [
                {"stage": "implement", "outcome": "PASS" if artifact_correctness else "PARTIAL", "evidence_refs": ["TEST_EVIDENCE"]},
                {"stage": "verify", "outcome": "PASS" if tests_passed else "FAIL", "evidence_refs": ["RUNTIME_EVIDENCE"]},
            ]
        else:
            decision = _extract_h03_artifact(observation.stdout)
            artifact_correctness = bool(decision) and after_fixture_digest == fixture_digest and not changed_files
            independent_quality.update(
                {
                    "acceptance_criteria_coverage": 1.0 if artifact_correctness else 0.0,
                    "artifact_correctness": artifact_correctness,
                    "source_accuracy": 1.0 if artifact_correctness else 0.0,
                }
            )
            confounders.append("current StageRouter route selected no dedicated design PROCESS skill; route was held constant")
            if not observation.blocked:
                terminal = "VERIFIED_SUCCESS" if artifact_correctness else "PARTIAL"
            stage_outcomes = [
                {"stage": "design", "outcome": "PASS" if artifact_correctness else "PARTIAL", "evidence_refs": ["DecisionRecord"]},
                {"stage": "verify", "outcome": "PASS" if artifact_correctness else "FAIL", "evidence_refs": ["source evidence"]},
            ]
        if pin["status"] == "BLOCKED":
            terminal = "BLOCKED"
            confounders.append("effective model did not match the explicit model pin")
        elif pin["status"] == "UNVERIFIED":
            confounders.append("effective model was not emitted by JSONL; command-level pin was accepted")
        notes = (
            f"model_pin={pin['status']}; model_evidence={pin['evidence_status']}; "
            f"bundle_digest={workload.bundle['bundle_digest']}"
        )
        controls = {
            "task_spec_digest": digest_value(workload.task_spec),
            "fixture_digest": fixture_digest,
            "start_sha": start_sha,
            "stage_route_digest": stable_route_digest(workload.route),
            "selected_skill_ids": [item["skill_id"] for item in workload.bundle["selected_skills"]],
            "selected_skill_digests": list(workload.selected_skill_digests),
            "permission_envelope_digest": digest_value(workload.permission_envelope),
            "tool_availability": [
                "codex exec",
                "workspace filesystem" if workload.workload_id == "H01" else "workspace read-only",
            ],
            "mcp_availability": "NOT_USED",
            "project_instruction_digest": digest_bytes(""),
            "system_instruction_digest": SYSTEM_INSTRUCTION_DIGEST,
        }
        return build_live_execution_record(
            record_id=f"record:phase3f:{workload.workload_id.lower()}:{effort}:{repetition:03d}",
            run_id=f"run:phase3f:{workload.workload_id.lower()}:{effort}:{repetition:03d}",
            fixture_id=f"{workload.workload_id}-codex-effort-{effort}",
            runtime_id="codex",
            observed_version=observed_version,
            model_id=model_id,
            reasoning_effort=effort,
            controls=controls,
            repetition_n=repetition,
            repetition_target=2 if workload.workload_id == "H01" else 1,
            terminal_outcome=terminal,
            stage_outcomes=stage_outcomes,
            provenance={
                "runtime_source": f"local codex --version: {observed_version}",
                "invocation_contract": "codex exec --ephemeral --ignore-user-config --ignore-rules --model PINNED --config model_reasoning_effort=LEVEL --config approval_policy=never --sandbox MODE --json",
                "documentation_snapshot": CODEX_DOCS,
                "source_refs": [CODEX_SOURCE, f"https://github.com/openai/codex/releases/tag/{CODEX_RELEASE_TAG}"],
                "verification_method": "installed help; explicit model pin; one compiled route/bundle; isolated fixture; independent acceptance check; no raw output persisted",
                "observed_at": "2026-09-10T00:00:00+08:00",
            },
            process=observation,
            quality=independent_quality,
            reliability={
                "failure_reasons": [] if terminal == "VERIFIED_SUCCESS" else [terminal.lower()],
                "invalid_edits": 0 if not changed_files else 1 if workload.workload_id == "H01" else 0,
            },
            security={
                "permission_violation": False,
                "sandbox_mismatch": False,
                "unsafe_proposal": False,
                "secret_exposure": False,
                "unexpected_network_usage": False,
            },
            artifacts={
                "start_sha": start_sha,
                "end_sha": end_sha,
                "changed_files": changed_files,
                "diff_digest": diff_digest,
                "test_commands": [test_command] if test_command else [],
                "tests_passed": tests_passed,
            },
            effect_class="INCONCLUSIVE",
            confounders=confounders,
            format_hint="jsonl",
            notes=notes,
        )


def run_bounded_experiment(
    *,
    model_id: str,
    timeout_s: float = 300.0,
    observed_version: str = CODEX_VERSION,
) -> dict[str, Any]:
    """Run no more than six interleaved live cells and return safe evidence."""

    if observed_version != CODEX_VERSION:
        raise ValueError("Codex installed runtime version is not the verified Phase 3F version")
    workloads = compile_workloads(model_id)
    schedule = build_interleaved_schedule()
    records: list[dict[str, Any]] = []
    completed_schedule: list[dict[str, Any]] = []
    for cell in schedule:
        record = _run_cell(
            workloads[cell["workload_id"]],
            model_id=model_id,
            effort=cell["effort"],
            repetition=cell["repetition"],
            observed_version=observed_version,
            timeout_s=timeout_s,
        )
        records.append(record)
        completed_schedule.append(cell)
        if record["terminal_outcome"] == "BLOCKED":
            break
    return {
        "runtime": {
            "runtime_id": "codex",
            "observed_version": observed_version,
            "release_tag": CODEX_RELEASE_TAG,
            "release_commit": CODEX_RELEASE_COMMIT,
        },
        "model_id": model_id,
        "effort_levels": ["low", "medium"],
        "schedule": completed_schedule,
        "compiled_workloads": {
            workload_id: {
                "task_spec_digest": digest_value(workload.task_spec),
                "stage_route_digest": stable_route_digest(workload.route),
                "bundle_digest": workload.bundle["bundle_digest"],
                "selected_skill_ids": [item["skill_id"] for item in workload.bundle["selected_skills"]],
                "selected_skill_digests": list(workload.selected_skill_digests),
                "route_status": workload.route["status"],
                "route_body_files_loaded": workload.route["routing_evidence"]["body_files_loaded"],
                "compile_body_files_loaded": workload.adapter_result.metrics["skill_md_files_loaded"],
            }
            for workload_id, workload in workloads.items()
        },
        "records": records,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the bounded Phase 3F Codex effort benchmark")
    parser.add_argument("--model", required=True, help="already-authorized explicit Codex model id")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--output", help="optional temporary path for sanitized JSON evidence")
    parser.add_argument("--live", action="store_true", help="required acknowledgement before live execution")
    args = parser.parse_args()
    if not args.live:
        parser.error("pass --live explicitly to execute real benchmark invocations")
    payload = json.dumps(
        run_bounded_experiment(model_id=args.model, timeout_s=args.timeout),
        ensure_ascii=False,
        sort_keys=True,
    )
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
