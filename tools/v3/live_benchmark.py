"""Bounded live-execution evidence helpers.

This module is deliberately an execution boundary, not a router.  It can run
one explicitly supplied, headless command in an isolated directory and turn
the result into append-only evidence without persisting prompts, raw model
output, environment variables, or credentials.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from tools.v3.contract_validation import validate_instance
from tools.v3.execution_bundle import canonical_json


EFFECT_CLASSES = frozenset(
    {
        "CONFIGURATION_EFFECT",
        "MODEL_EFFECT",
        "REASONING_EFFORT_EFFECT",
        "INCONCLUSIVE",
    }
)
REPETITION_CLASSES = frozenset({"TARGETED", "EXPLORATORY_ONLY"})
_CONTROL_FIELDS = (
    "task_spec_digest",
    "fixture_digest",
    "start_sha",
    "stage_route_digest",
    "selected_skill_ids",
    "selected_skill_digests",
    "permission_envelope_digest",
    "tool_availability",
    "mcp_availability",
    "project_instruction_digest",
    "system_instruction_digest",
)


def digest_bytes(value: bytes | str) -> str:
    """Return a stable digest without retaining the supplied content."""

    raw = value.encode("utf-8") if isinstance(value, str) else value
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def digest_value(value: Any) -> str:
    return digest_bytes(canonical_json(value))


def repetition_classification(n: int, *, target: int = 1) -> dict[str, Any]:
    """Classify a cell without implying statistical certainty."""

    if not isinstance(n, int) or n < 1:
        raise ValueError("repetition count must be a positive integer")
    if not isinstance(target, int) or target < 1:
        raise ValueError("repetition target must be a positive integer")
    return {
        "n": n,
        "target": target,
        "classification": "EXPLORATORY_ONLY" if n == 1 else "TARGETED",
    }


def _control_value(record: dict[str, Any], field: str) -> Any:
    controls = record.get("controls")
    if isinstance(controls, dict) and field in controls:
        return controls[field]
    return record.get(field)


def compare_effects(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    """Classify a comparison without attributing confounded results to a model."""

    changed_controls = [
        field
        for field in _CONTROL_FIELDS
        if _control_value(first, field) != _control_value(second, field)
    ]
    runtime_changed = first.get("runtime_id") != second.get("runtime_id")
    model_changed = first.get("model_id") != second.get("model_id")
    effort_changed = first.get("reasoning_effort") != second.get("reasoning_effort")

    if runtime_changed:
        return {
            "effect_class": "CONFIGURATION_EFFECT",
            "changed_variables": ["runtime_id"] + changed_controls,
            "confounders": sorted(set(changed_controls + (["model_id"] if model_changed else []) + (["reasoning_effort"] if effort_changed else []))),
            "reason": "runtime changed; any result is a configuration comparison, not isolated model evidence",
        }

    non_model_controls = [
        field for field in changed_controls if field not in {"task_spec_digest", "fixture_digest", "start_sha"}
    ]
    workload_changed = [field for field in changed_controls if field in {"task_spec_digest", "fixture_digest", "start_sha", "stage_route_digest"}]
    if model_changed and not effort_changed and not non_model_controls and not workload_changed:
        return {
            "effect_class": "MODEL_EFFECT",
            "changed_variables": ["model_id"],
            "confounders": [],
            "reason": "same runtime, workload, route, skills, tools, permissions, and effort; model is the changed variable",
        }
    if effort_changed and not model_changed and not non_model_controls and not workload_changed:
        return {
            "effect_class": "REASONING_EFFORT_EFFECT",
            "changed_variables": ["reasoning_effort"],
            "confounders": [],
            "reason": "same runtime, model, workload, route, skills, tools, and permissions; effort is the changed variable",
        }

    confounders = list(changed_controls)
    if model_changed:
        confounders.append("model_id")
    if effort_changed:
        confounders.append("reasoning_effort")
    if not changed_controls and not runtime_changed and not model_changed and not effort_changed:
        reason = "no controlled variable changed"
    else:
        reason = "comparison has workload, runtime, or configuration confounders"
    return {
        "effect_class": "INCONCLUSIVE",
        "changed_variables": sorted(set(confounders)),
        "confounders": sorted(set(confounders)),
        "reason": reason,
    }


def _numeric_range(values: Iterable[Any]) -> dict[str, int | float] | None:
    numeric = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    if not numeric:
        return None
    return {"min": min(numeric), "max": max(numeric)}


def summarize_variance(observations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarize repeated observations while preserving variance."""

    items = list(observations)
    success_values = [
        item.get("terminal_outcome") == "VERIFIED_SUCCESS"
        if "terminal_outcome" in item
        else bool(item.get("success"))
        for item in items
    ]
    latency = [item.get("latency_ms") for item in items]
    tool_calls = [item.get("tool_calls") for item in items]
    context_tokens = [item.get("context_tokens") for item in items]
    reroutes = [item.get("reroutes") for item in items]
    return {
        "n": len(items),
        "success_count": sum(success_values),
        "success_rate": (sum(success_values) / len(items)) if items else None,
        "latency_ms": {
            "median": statistics.median([value for value in latency if isinstance(value, (int, float))])
            if any(isinstance(value, (int, float)) for value in latency)
            else None,
            "range": _numeric_range(latency),
        },
        "tool_calls": _numeric_range(tool_calls),
        "context_tokens": _numeric_range(context_tokens),
        "reroutes": _numeric_range(reroutes),
        "failure_modes": sorted(
            {
                str(item["failure_reason"])
                for item in items
                if item.get("failure_reason")
            }
        ),
    }


_SECRET_PATTERNS = (
    (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,;\"']+"), r"\1[REDACTED]"),
    (re.compile(r"\b(?:sk|rk)-[A-Za-z0-9_-]{8,}\b"), "[REDACTED_KEY]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_-]{8,}\b"), "[REDACTED_TOKEN]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{8,}\b"), "[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(token\s*[=:]\s*)[^\s,;\"']+"), r"\1[REDACTED]"),
)


def sanitize_text(value: str) -> str:
    """Redact common credential forms before text can enter evidence."""

    sanitized = str(value)
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def _sanitize_metadata(value: Any) -> Any:
    """Sanitize structured public metadata without retaining the source text."""

    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return json.loads(sanitize_text(serialized))


def detect_output_format(stdout: str, *, hint: str | None = None) -> str:
    if hint in {"text", "json", "jsonl", "unknown"}:
        return str(hint)
    if not stdout.strip():
        return "unknown"
    try:
        json.loads(stdout)
        return "json"
    except json.JSONDecodeError:
        lines = [line for line in stdout.splitlines() if line.strip()]
        if lines:
            try:
                for line in lines:
                    json.loads(line)
                return "jsonl"
            except json.JSONDecodeError:
                pass
    return "text"


def output_evidence(stdout: str, stderr: str, *, format_hint: str | None = None) -> dict[str, Any]:
    """Return digests/metrics only; raw process output never enters a record."""

    return {
        "format": detect_output_format(stdout, hint=format_hint),
        "stdout_digest": digest_bytes(stdout),
        "stdout_bytes": len(stdout.encode("utf-8")),
        "stderr_digest": digest_bytes(stderr),
        "stderr_bytes": len(stderr.encode("utf-8")),
        "raw_output_serialized": False,
        "sanitized": True,
    }


def _walk_json(value: Any, *, depth: int = 0) -> Iterable[dict[str, Any]]:
    if depth > 5:
        return
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child, depth=depth + 1)
    elif isinstance(value, list):
        for child in value[:200]:
            yield from _walk_json(child, depth=depth + 1)


def extract_runtime_metrics(stdout: str, *, format_hint: str | None = None) -> dict[str, Any]:
    """Extract non-sensitive usage facts from common JSON/JSONL result shapes."""

    fmt = detect_output_format(stdout, hint=format_hint)
    if fmt not in {"json", "jsonl"}:
        return {"model_id": None, "input_tokens": None, "output_tokens": None, "tool_calls": None, "cost_units": None}
    values: list[Any] = []
    try:
        if fmt == "json":
            values = [json.loads(stdout)]
        else:
            values = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    except json.JSONDecodeError:
        return {"model_id": None, "input_tokens": None, "output_tokens": None, "tool_calls": None, "cost_units": None}

    models: set[str] = set()
    numbers: dict[str, list[int | float]] = {}
    tool_calls = 0
    for mapping in _walk_json(values):
        for key, value in mapping.items():
            normalized = str(key).lower()
            if normalized in {"model", "model_id", "modelid"} and isinstance(value, str) and len(value) <= 200:
                models.add(value)
            if normalized in {"input_tokens", "prompt_tokens", "input_token_count", "output_tokens", "completion_tokens", "output_token_count", "total_tokens", "tokens_total", "total_cost_usd", "cost_usd"} and isinstance(value, (int, float)) and not isinstance(value, bool):
                numbers.setdefault(normalized, []).append(value)
            if normalized in {"tool_call", "tool_calls", "tool_use", "tool_uses"}:
                if isinstance(value, int) and not isinstance(value, bool):
                    tool_calls = max(tool_calls, value)
                elif isinstance(value, list):
                    tool_calls = max(tool_calls, len(value))
            if normalized == "type" and isinstance(value, str) and "tool" in value.lower():
                tool_calls += 1

    def last_number(*keys: str) -> int | float | None:
        for key in keys:
            if numbers.get(key):
                return numbers[key][-1]
        return None

    return {
        "model_id": sorted(models)[0] if len(models) == 1 else None,
        "input_tokens": last_number("input_tokens", "prompt_tokens", "input_token_count"),
        "output_tokens": last_number("output_tokens", "completion_tokens", "output_token_count"),
        "tokens_total": last_number("total_tokens", "tokens_total"),
        "tool_calls": tool_calls or None,
        "cost_units": last_number("total_cost_usd", "cost_usd"),
    }


@dataclass(frozen=True)
class ProcessObservation:
    launched: bool
    returncode: int | None
    timed_out: bool
    duration_ms: float
    stdout: str = ""
    stderr: str = ""
    launch_error: str | None = None

    @property
    def blocked(self) -> bool:
        if not self.launched or self.timed_out:
            return True
        lowered = self.stderr.lower()
        return self.returncode != 0 and any(
            marker in lowered
            for marker in ("authentication", "unauthorized", "401", "approval", "permission denied", "interactive")
        )


def run_headless_command(
    command: Sequence[str],
    *,
    cwd: str | Path,
    input_text: str | None = None,
    timeout_s: float = 300,
) -> ProcessObservation:
    """Run one explicit command without a shell or environment serialization."""

    if not command or any(not isinstance(item, str) or not item for item in command):
        raise ValueError("command must be a non-empty sequence of non-empty strings")
    working_root = Path(cwd).resolve()
    if not working_root.is_dir():
        raise ValueError(f"benchmark cwd does not exist: {working_root}")
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    started = time.perf_counter()
    try:
        run_options: dict[str, Any] = {
            "cwd": str(working_root),
            "text": True,
            "capture_output": True,
            "check": False,
            "shell": False,
            "timeout": timeout_s,
        }
        if input_text is None:
            # A headless lane must never inherit an interactive stdin prompt.
            run_options["stdin"] = subprocess.DEVNULL
        else:
            run_options["input"] = input_text
        completed = subprocess.run(list(command), **run_options)
    except FileNotFoundError as exc:
        return ProcessObservation(False, None, False, (time.perf_counter() - started) * 1000, launch_error=str(exc))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")
        return ProcessObservation(True, None, True, (time.perf_counter() - started) * 1000, stdout, stderr)
    return ProcessObservation(
        True,
        completed.returncode,
        False,
        (time.perf_counter() - started) * 1000,
        completed.stdout,
        completed.stderr,
    )


def _empty_quality() -> dict[str, Any]:
    return {
        "acceptance_criteria_coverage": None,
        "tests_pass": None,
        "artifact_correctness": None,
        "source_accuracy": None,
        "review_finding_precision": None,
        "user_correction": None,
    }


def _empty_security() -> dict[str, bool]:
    return {
        "permission_violation": False,
        "sandbox_mismatch": False,
        "unsafe_proposal": False,
        "secret_exposure": False,
        "unexpected_network_usage": False,
    }


def build_live_execution_record(
    *,
    record_id: str,
    run_id: str,
    fixture_id: str,
    runtime_id: str,
    observed_version: str | None,
    model_id: str | None,
    reasoning_effort: str | None,
    controls: dict[str, Any],
    repetition_n: int,
    repetition_target: int,
    terminal_outcome: str,
    stage_outcomes: list[dict[str, Any]],
    provenance: dict[str, Any],
    process: ProcessObservation | None = None,
    quality: dict[str, Any] | None = None,
    efficiency: dict[str, Any] | None = None,
    reliability: dict[str, Any] | None = None,
    security: dict[str, Any] | None = None,
    portability: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    effect_class: str | None = "INCONCLUSIVE",
    confounders: Iterable[str] = (),
    baseline_refs: Iterable[str] = (),
    format_hint: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build a validated public record from an in-memory process observation."""

    if effect_class not in EFFECT_CLASSES:
        raise ValueError(f"unsupported effect class: {effect_class}")
    if not set(_CONTROL_FIELDS).issubset(controls):
        missing = sorted(set(_CONTROL_FIELDS) - set(controls))
        raise ValueError("missing live-run controls: " + ", ".join(missing))
    rep = repetition_classification(repetition_n, target=repetition_target)
    observation = process or ProcessObservation(False, None, False, 0.0, launch_error="no process observation")
    if observation.blocked:
        evidence_class = "UNAVAILABLE"
        status = "LIVE_LANE_BLOCKED"
        terminal_outcome = "BLOCKED"
    else:
        evidence_class = "REAL_EXECUTION"
        status = "COMPLETED" if observation.returncode == 0 else "FAILED"
    metrics = extract_runtime_metrics(observation.stdout, format_hint=format_hint)
    public_efficiency = {
        "latency_ms": observation.duration_ms if observation.launched else None,
        "wall_time_ms": observation.duration_ms if observation.launched else None,
        "model_calls": 1 if observation.launched else None,
        "tool_calls": metrics.get("tool_calls"),
        "context_tokens": None,
        "input_tokens": metrics.get("input_tokens"),
        "output_tokens": metrics.get("output_tokens"),
        "cost_units": metrics.get("cost_units"),
        "cost_status": "MEASURED" if metrics.get("cost_units") is not None else "UNKNOWN",
    }
    if efficiency:
        public_efficiency.update(efficiency)
    public_quality = dict(_empty_quality())
    if evidence_class == "REAL_EXECUTION" and quality:
        public_quality.update(quality)
    public_reliability = {
        "success_count": 1 if terminal_outcome == "VERIFIED_SUCCESS" else 0,
        "reroutes": 0,
        "retries": 0,
        "failed_tool_calls": 0,
        "invalid_edits": 0,
        "recovery_events": 0,
        "failure_reasons": [],
    }
    if reliability:
        public_reliability.update(reliability)
    if observation.launch_error:
        # Do not persist executable paths or OS error strings.  The caller can
        # inspect the in-memory observation while the public record only says
        # that launch was unavailable.
        public_reliability["failure_reasons"] = ["headless executable could not be launched"]
    public_security = dict(_empty_security())
    if security:
        public_security.update(security)
    public_portability = {
        "portable_artifacts": [],
        "runtime_specific_artifacts": [],
        "lost_capabilities": [],
        "instruction_leakage": False,
    }
    if portability:
        public_portability.update(portability)
    record: dict[str, Any] = {
        "schema_version": "3.0",
        "record_id": record_id,
        "run_id": run_id,
        "fixture_id": fixture_id,
        "fixture_set": "HOLDOUT",
        "evidence_class": evidence_class,
        "status": status,
        "runtime_id": runtime_id,
        "observed_version": observed_version,
        "model_id": metrics.get("model_id") or model_id,
        "reasoning_effort": reasoning_effort,
        "effect_class": effect_class,
        "controls": _sanitize_metadata(controls),
        "repetition": rep,
        "terminal_outcome": terminal_outcome,
        "stage_outcomes": _sanitize_metadata(stage_outcomes),
        "quality": public_quality,
        "efficiency": public_efficiency,
        "reliability": public_reliability,
        "security": public_security,
        "portability": public_portability,
        "output_evidence": output_evidence(observation.stdout, observation.stderr, format_hint=format_hint),
        "artifacts": _sanitize_metadata(artifacts or {}),
        "provenance": _sanitize_metadata(provenance),
        "confounders": sorted(set(sanitize_text(item) for item in confounders)),
        "baseline_refs": sorted(set(baseline_refs)),
        "history_mode": "APPEND_ONLY",
        "sensitive_data_serialized": False,
    }
    if notes:
        record["notes"] = sanitize_text(notes)
    validation = validate_instance("LiveExecutionRecord", record)
    if not validation.valid:
        raise ValueError("invalid live execution record: " + "; ".join(validation.errors))
    return record
