"""Small, deterministic helpers for the Codex effort experiment.

This module is an evaluation boundary, not a model router.  It builds a
bounded schedule, checks that two records differ only by reasoning effort,
and produces evidence-only summaries.  It deliberately has no subprocess,
network, persistence, or policy-mutation behavior.
"""

from __future__ import annotations

import copy
import hashlib
import json
import statistics
from typing import Any, Iterable, Sequence

from tools.v3.execution_bundle import canonical_json


SUPPORTED_EFFORTS = frozenset({"none", "low", "medium", "high", "max"})
CONTROL_FIELDS = (
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
EFFECT_CLASSES = frozenset(
    {
        "HIGHER_EFFORT_MATERIALLY_BETTER",
        "LOWER_EFFORT_EQUIVALENT",
        "LOWER_EFFORT_BETTER",
        "TRADEOFF",
        "INCONCLUSIVE",
    }
)
PIN_EVIDENCE_STATUSES = frozenset(
    {"OBSERVED", "CLI_CONFIRMED", "PIN_ACCEPTED", "UNKNOWN"}
)


def stable_route_digest(route: dict[str, Any]) -> str:
    """Digest route intent while excluding runtime-only timing observations."""

    normalized = copy.deepcopy(route)
    routing_evidence = normalized.get("routing_evidence")
    if isinstance(routing_evidence, dict):
        routing_evidence.pop("timings_ms", None)
    return "sha256:" + hashlib.sha256(canonical_json(normalized).encode("utf-8")).hexdigest()


def build_interleaved_schedule(
    effort_levels: Sequence[str] = ("low", "medium"),
) -> list[dict[str, Any]]:
    """Return the fixed six-cell schedule for H01 and exploratory H03.

    The first level is the lower-effort arm and the second is the higher
    effort arm.  The order is intentionally interleaved to reduce temporal
    confounding; it is not a production routing policy.
    """

    levels = tuple(effort_levels)
    if len(levels) != 2 or levels[0] == levels[1]:
        raise ValueError("exactly two distinct effort levels are required")
    if any(level not in SUPPORTED_EFFORTS for level in levels):
        raise ValueError("effort level is not supported by the Codex profile contract")
    lower, higher = levels
    schedule = [
        ("H01", lower, 1),
        ("H01", higher, 1),
        ("H01", higher, 2),
        ("H01", lower, 2),
        ("H03", lower, 1),
        ("H03", higher, 1),
    ]
    return [
        {
            "sequence": index,
            "workload_id": workload,
            "effort": effort,
            "repetition": repetition,
        }
        for index, (workload, effort, repetition) in enumerate(schedule, start=1)
    ]


def build_codex_exec_command(
    *,
    model_id: str,
    reasoning_effort: str,
    sandbox_mode: str,
    cwd: str,
    executable: str = "codex",
) -> list[str]:
    """Build one safe, explicit Codex 0.153.4 invocation.

    The command intentionally uses the verified headless ``approval_policy``
    config override, ephemeral sessions, ignored user/rules configuration,
    and an explicit model/effort. It does not invent an approval CLI flag or
    include any dangerous bypass option.
    """

    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("an explicit model id is required")
    if reasoning_effort not in SUPPORTED_EFFORTS:
        raise ValueError(f"unsupported reasoning effort: {reasoning_effort}")
    if sandbox_mode not in {"read-only", "workspace-write"}:
        raise ValueError("effort evaluation allows only read-only or workspace-write sandbox")
    if not isinstance(cwd, str) or not cwd:
        raise ValueError("an isolated working directory is required")
    return [
        executable,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--model",
        model_id,
        "--config",
        f'model_reasoning_effort="{reasoning_effort}"',
        "--config",
        'approval_policy="never"',
        "--sandbox",
        sandbox_mode,
        "--color",
        "never",
        "--json",
        "--cd",
        cwd,
        "-",
    ]


def model_pin_status(
    requested_model_id: str | None,
    effective_model_id: str | None,
    evidence_status: str,
) -> dict[str, Any]:
    """Classify explicit model pinning without exposing credentials."""

    if evidence_status not in PIN_EVIDENCE_STATUSES:
        raise ValueError(f"unknown model evidence status: {evidence_status}")
    if not isinstance(requested_model_id, str) or not requested_model_id.strip():
        return {
            "status": "BLOCKED",
            "requested_model_id": None,
            "effective_model_id": effective_model_id,
            "evidence_status": evidence_status,
            "reason": "controlled effort evidence requires an explicit model id",
        }
    if effective_model_id is not None and effective_model_id != requested_model_id:
        return {
            "status": "BLOCKED",
            "requested_model_id": requested_model_id,
            "effective_model_id": effective_model_id,
            "evidence_status": evidence_status,
            "reason": "effective model differs from the requested model pin",
        }
    if evidence_status == "UNKNOWN":
        return {
            "status": "UNVERIFIED",
            "requested_model_id": requested_model_id,
            "effective_model_id": effective_model_id,
            "evidence_status": evidence_status,
            "reason": "the command is explicit but effective model evidence is unavailable",
        }
    return {
        "status": "PINNED",
        "requested_model_id": requested_model_id,
        "effective_model_id": effective_model_id,
        "evidence_status": evidence_status,
        "reason": "one explicit model identity is held constant",
    }


def _controls(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("controls")
    return value if isinstance(value, dict) else {}


def compare_controlled_effort(
    lower_record: dict[str, Any],
    higher_record: dict[str, Any],
) -> dict[str, Any]:
    """Validate that a pair differs only in its requested effort level."""

    confounders: set[str] = set()
    for field in CONTROL_FIELDS:
        if _controls(lower_record).get(field) != _controls(higher_record).get(field):
            confounders.add(field)
    for field in ("runtime_id", "observed_version", "model_id"):
        if lower_record.get(field) != higher_record.get(field):
            confounders.add(field)
    if lower_record.get("evidence_class") != "REAL_EXECUTION":
        confounders.add("lower_evidence_class")
    if higher_record.get("evidence_class") != "REAL_EXECUTION":
        confounders.add("higher_evidence_class")
    lower_effort = lower_record.get("reasoning_effort")
    higher_effort = higher_record.get("reasoning_effort")
    if not isinstance(lower_effort, str) or not isinstance(higher_effort, str):
        confounders.add("reasoning_effort")
    elif lower_effort == higher_effort:
        confounders.add("reasoning_effort")
    if not isinstance(lower_record.get("model_id"), str) or not lower_record.get("model_id"):
        confounders.add("model_id")
    if not isinstance(higher_record.get("model_id"), str) or not higher_record.get("model_id"):
        confounders.add("model_id")

    if confounders:
        return {
            "effect_class": "INCONCLUSIVE",
            "changed_variables": sorted(confounders),
            "confounders": sorted(confounders),
            "reason": "the paired records do not hold all controlled variables constant",
        }
    return {
        "effect_class": "REASONING_EFFORT_EFFECT",
        "changed_variables": ["reasoning_effort"],
        "confounders": [],
        "reason": "same runtime, explicit model, workload, route, skills, authority, and tools; effort is the changed variable",
        "lower_effort": lower_effort,
        "higher_effort": higher_effort,
    }


def _numeric_values(records: Iterable[dict[str, Any]], path: tuple[str, ...]) -> list[float]:
    values: list[float] = []
    for record in records:
        value: Any = record
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    return values


def _arm_summary(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = list(records)
    success_count = sum(
        1 for item in items if item.get("terminal_outcome") == "VERIFIED_SUCCESS"
    )
    latency = _numeric_values(items, ("efficiency", "latency_ms"))
    input_tokens = _numeric_values(items, ("efficiency", "input_tokens"))
    output_tokens = _numeric_values(items, ("efficiency", "output_tokens"))
    acceptance = _numeric_values(
        items, ("quality", "acceptance_criteria_coverage")
    )
    tests_pass = sum(
        1 for item in items if item.get("quality", {}).get("tests_pass") is True
    )
    artifact_correct = sum(
        1
        for item in items
        if item.get("quality", {}).get("artifact_correctness") is True
    )
    return {
        "n": len(items),
        "success_count": success_count,
        "success_rate": success_count / len(items) if items else None,
        "acceptance_criteria_coverage": {
            "median": statistics.median(acceptance) if acceptance else None,
            "range": _range(acceptance),
        },
        "tests_pass_count": tests_pass,
        "artifact_correctness_count": artifact_correct,
        "latency_ms": {
            "median": statistics.median(latency) if latency else None,
            "range": _range(latency),
        },
        "verified_input_tokens": _range(input_tokens),
        "verified_output_tokens": _range(output_tokens),
    }


def _range(values: Iterable[float]) -> dict[str, int | float] | None:
    numbers = list(values)
    if not numbers:
        return None
    result: dict[str, int | float] = {"min": min(numbers), "max": max(numbers)}
    if all(number.is_integer() for number in numbers):
        result = {key: int(value) for key, value in result.items()}
    return result


def classify_effort_effect(
    lower_records: Iterable[dict[str, Any]],
    higher_records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Compare quality and efficiency axes without making one scalar score."""

    lower = _arm_summary(lower_records)
    higher = _arm_summary(higher_records)
    if not lower["n"] or not higher["n"]:
        return {
            "classification": "INCONCLUSIVE",
            "repetition_status": "EXPLORATORY_ONLY",
            "quality": lower,
            "efficiency": {"lower": lower["latency_ms"], "higher": higher["latency_ms"]},
            "reason": "one effort arm has no observations",
        }

    repetition_status = (
        "TARGETED" if lower["n"] >= 2 and higher["n"] >= 2 else "EXPLORATORY_ONLY"
    )
    low_quality = _quality_dimensions(lower)
    high_quality = _quality_dimensions(higher)
    quality_relation = _quality_relation(low_quality, high_quality)
    if quality_relation == "HIGHER":
        classification = "HIGHER_EFFORT_MATERIALLY_BETTER"
        quality_reason = "higher effort has stronger verified outcome dimensions"
    elif quality_relation == "LOWER":
        classification = "LOWER_EFFORT_BETTER"
        quality_reason = "lower effort has stronger verified outcome dimensions"
    elif quality_relation == "EQUAL":
        classification = "LOWER_EFFORT_EQUIVALENT"
        quality_reason = "verified outcome dimensions are equal; lower effort is the simpler arm"
    else:
        classification = "TRADEOFF"
        quality_reason = "quality dimensions move in different directions"
    if repetition_status == "EXPLORATORY_ONLY":
        classification = "INCONCLUSIVE"
        quality_reason += "; repetition count is exploratory only"

    return {
        "classification": classification,
        "repetition_status": repetition_status,
        "quality": {
            "lower": {
                "success_count": lower["success_count"],
                "success_rate": lower["success_rate"],
                "acceptance_criteria_coverage": lower["acceptance_criteria_coverage"],
                "tests_pass_count": lower["tests_pass_count"],
                "artifact_correctness_count": lower["artifact_correctness_count"],
            },
            "higher": {
                "success_count": higher["success_count"],
                "success_rate": higher["success_rate"],
                "acceptance_criteria_coverage": higher["acceptance_criteria_coverage"],
                "tests_pass_count": higher["tests_pass_count"],
                "artifact_correctness_count": higher["artifact_correctness_count"],
            },
        },
        "efficiency": {
            "lower_latency_ms": lower["latency_ms"],
            "higher_latency_ms": higher["latency_ms"],
            "lower_input_tokens": lower["verified_input_tokens"],
            "higher_input_tokens": higher["verified_input_tokens"],
            "lower_output_tokens": lower["verified_output_tokens"],
            "higher_output_tokens": higher["verified_output_tokens"],
        },
        "reason": quality_reason,
    }


def _quality_dimensions(summary: dict[str, Any]) -> dict[str, float | None]:
    """Return comparable dimensions, retaining ``None`` for unmeasured data."""

    acceptance = summary["acceptance_criteria_coverage"]["median"]
    return {
        "success_rate": summary["success_rate"],
        "acceptance_criteria_coverage": acceptance,
        "tests_pass_rate": summary["tests_pass_count"] / summary["n"]
        if summary["n"]
        else None,
        "artifact_correctness_rate": summary["artifact_correctness_count"] / summary["n"]
        if summary["n"]
        else None,
    }


def _quality_relation(
    lower: dict[str, float | None], higher: dict[str, float | None]
) -> str:
    comparisons: list[int] = []
    for name in lower:
        low = lower[name]
        high = higher[name]
        if low is None or high is None:
            continue
        comparisons.append((high > low) - (high < low))
    if not comparisons:
        return "UNKNOWN"
    if all(item >= 0 for item in comparisons) and any(item > 0 for item in comparisons):
        return "HIGHER"
    if all(item <= 0 for item in comparisons) and any(item < 0 for item in comparisons):
        return "LOWER"
    if all(item == 0 for item in comparisons):
        return "EQUAL"
    return "MIXED"


def historical_record_is_eligible(record: dict[str, Any]) -> bool:
    """Return whether a historical record can enter a controlled pair."""

    if record.get("evidence_class") != "REAL_EXECUTION":
        return False
    if not isinstance(record.get("model_id"), str) or not record.get("model_id"):
        return False
    if not isinstance(record.get("reasoning_effort"), str) or not record.get(
        "reasoning_effort"
    ):
        return False
    return all(_controls(record).get(field) is not None for field in CONTROL_FIELDS)


def readiness_split(
    *,
    pinned_model: bool,
    effort_levels: Sequence[str],
    h01_counts: tuple[int, int],
    h03_counts: tuple[int, int],
    measurement_integrity: bool,
    controlled_variables: bool,
    cross_runtime_evidence: bool,
) -> dict[str, Any]:
    """Report Codex-local and cross-runtime readiness independently."""

    intra_requirements = {
        "pinned_model": bool(pinned_model),
        "two_effort_levels": len(tuple(effort_levels)) == 2,
        "h01_repeated": min(h01_counts) >= 2,
        "h03_paired": min(h03_counts) >= 1,
        "measurement_integrity": bool(measurement_integrity),
        "controlled_variables": bool(controlled_variables),
    }
    passed = sum(intra_requirements.values())
    if not any(h01_counts) and not any(h03_counts):
        intra = "NOT_READY"
    elif all(intra_requirements.values()):
        intra = "READY"
    elif passed:
        intra = "PARTIAL"
    else:
        intra = "NOT_READY"
    return {
        "intra_runtime": intra,
        "cross_runtime": "READY" if cross_runtime_evidence else "NOT_READY",
        "intra_requirements": intra_requirements,
    }


def routing_policy_proposal(
    active_policy: dict[str, Any],
    observations: dict[str, Any],
) -> dict[str, Any]:
    """Create an evidence-only proposal without mutating active policy."""

    if not isinstance(active_policy, dict):
        raise ValueError("active policy must be an object")
    return {
        "status": "PROPOSAL_ONLY",
        "active_policy_mutated": False,
        "active_policy_snapshot": copy.deepcopy(active_policy),
        "observations": copy.deepcopy(observations),
        "proposed_policy": copy.deepcopy(active_policy),
        "promotion": "requires separate review and explicit policy change",
    }


def extract_codex_identity(stdout: str) -> dict[str, str | None]:
    """Extract only non-secret model/effort identifiers from JSONL output."""

    model_ids: set[str] = set()
    effort_levels: set[str] = set()

    def visit(value: Any, depth: int = 0) -> None:
        if depth > 6:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower()
                if normalized in {"model", "model_id", "modelid"}:
                    if isinstance(child, str) and len(child) <= 200:
                        model_ids.add(child)
                elif normalized in {
                    "reasoning_effort",
                    "model_reasoning_effort",
                }:
                    if isinstance(child, str) and child in SUPPORTED_EFFORTS:
                        effort_levels.add(child)
                visit(child, depth + 1)
        elif isinstance(value, list):
            for child in value[:200]:
                visit(child, depth + 1)

    for line in str(stdout).splitlines():
        if not line.strip():
            continue
        try:
            visit(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {
        "model_id": sorted(model_ids)[0] if len(model_ids) == 1 else None,
        "reasoning_effort": sorted(effort_levels)[0] if len(effort_levels) == 1 else None,
    }
