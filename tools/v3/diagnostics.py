"""Read-only product diagnostics for the v3 user-facing CLI.

Diagnostics deliberately validate the checked-in static contracts without
probing a runtime, reading skill bodies, or inspecting user configuration.
The report is suitable for a fresh-clone ``doctor`` command and keeps
volatile timings separate from the stable report digest.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from tools.v3.contract_validation import SCHEMA_FILES, validate_instance
from tools.v3.productization import (
    DEFAULT_OVERLAY_PATH,
    DEFAULT_REGISTRY_PATH,
    EXPECTED_SKILL_COUNT,
    ROOT,
    _validate_snapshot,
    digest_value,
    load_runtime_inventory,
)
from tools.v3.routing_catalog import RoutingCatalogSnapshot


def _schema_status() -> tuple[str, list[str]]:
    missing = [
        name
        for name, filename in sorted(SCHEMA_FILES.items())
        if not (ROOT / "schemas" / "v3" / filename).is_file()
    ]
    return ("VALID", []) if not missing else ("INVALID", missing)


def build_static_diagnostics_report(
    *,
    inventory: str | Path | None = None,
    fixture: str = "ALL_KNOWN_STATIC",
    registry: str | Path = DEFAULT_REGISTRY_PATH,
    overlay: str | Path = DEFAULT_OVERLAY_PATH,
) -> dict[str, Any]:
    """Validate static product contracts without executing any runtime."""

    started = time.perf_counter()
    loaded = load_runtime_inventory(
        inventory or (ROOT / "fixtures/v3/productization/runtime-inventory-v1.json"),
        fixture_name=fixture,
    )
    for status in loaded["runtimes"]:
        validation = validate_instance("RuntimeProductStatus", status)
        if not validation.valid:
            raise ValueError("runtime inventory status failed schema validation")

    snapshot_started = time.perf_counter()
    snapshot = RoutingCatalogSnapshot.from_registry(
        registry,
        overlay_path=overlay,
        repository_root=ROOT,
    )
    _validate_snapshot(snapshot)
    snapshot_ms = round((time.perf_counter() - snapshot_started) * 1000, 3)

    schema_status, schema_errors = _schema_status()
    body_reads = int(snapshot.load_metrics.get("body_files_loaded", 0.0))
    checks: dict[str, Any] = {
        "metadata_records": len(snapshot.records),
        "metadata_records_expected": EXPECTED_SKILL_COUNT,
        "routing_snapshot": "VALID",
        "runtime_inventory": "VALID",
        "schema_files": schema_status,
        "ranking_body_reads": body_reads,
    }
    errors: list[str] = list(schema_errors)
    if len(snapshot.records) != EXPECTED_SKILL_COUNT:
        errors.append("metadata record count does not match the v3 catalog contract")
    if body_reads != 0:
        errors.append("static diagnostics unexpectedly loaded skill bodies")
    if errors:
        status = "BLOCKED"
    else:
        status = "PASS"

    report: dict[str, Any] = {
        "schema_version": "3.0",
        "diagnostics_version": "1.0",
        "status": status,
        "checks": checks,
        "snapshot": {
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_digest": digest_value(
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "records": [
                        [
                            record.get("skill_id"),
                            record.get("source", {}).get("digest", ""),
                        ]
                        for record in snapshot.records
                    ],
                }
            ),
        },
        "metrics": {
            "snapshot_load_ms": snapshot_ms,
            "diagnostics_total_ms": round((time.perf_counter() - started) * 1000, 3),
        },
        "runtime_probe": "NOT_RUN",
        "model_invocation": "NOT_RUN",
        "global_writes": 0,
        "no_actual_writes": True,
        "sensitive_data_serialized": False,
        "errors": errors,
        "warnings": [],
        "report_digest": "",
    }
    stable = dict(report)
    stable.pop("report_digest", None)
    stable.pop("metrics", None)
    report["report_digest"] = digest_value(stable)
    return report
