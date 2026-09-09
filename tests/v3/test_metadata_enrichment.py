"""Tests for the offline v3 routing metadata overlay."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.v3.metadata_enrichment import (
    PROVENANCE_LEVELS,
    apply_overlay,
    build_overlay,
    load_overlay,
    metadata_quality,
    validate_overlay,
)
from tools.v3.skill_scoring import score_candidate
from tools.v3.contract_validation import validate_file


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".superpowers" / "SKILLS_INDEX.json"
OVERLAY = ROOT / "registry/v3/skill-routing-metadata.json"


def _digest(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def _single_registry(root: Path, content: str) -> Path:
    skill_path = root / "sample" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(content, encoding="utf-8")
    registry = {
        "schema_version": "1.0",
        "source": "https://github.com/juhjuhx/agent-skills.git",
        "source_ref": "main",
        "source_commit": "test-registry",
        "skill_count": 1,
        "skills": [
            {
                "id": "sample",
                "name": "sample",
                "description": "A sample procedure.",
                "triggers": ["sample task"],
                "categories": ["software-engineering"],
                "relative_path": "sample/SKILL.md",
                "sha256": _digest(content)[len("sha256:") :],
            }
        ],
    }
    registry_path = root / ".superpowers" / "SKILLS_INDEX.json"
    registry_path.parent.mkdir()
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return registry_path


class MetadataEnrichmentTests(unittest.TestCase):
    def test_checked_in_overlay_document_matches_public_schema(self):
        validation = validate_file("SkillRoutingMetadata", OVERLAY)

        self.assertTrue(validation.valid, validation.errors)

    def test_checked_in_overlay_has_all_current_skills_and_valid_provenance(self):
        overlay = load_overlay(OVERLAY)
        validation = validate_overlay(
            overlay,
            registry_path=REGISTRY,
            repository_root=ROOT,
        )

        self.assertTrue(validation.valid, validation.errors)
        self.assertEqual(len(overlay["skills"]), 214)
        self.assertEqual(set(PROVENANCE_LEVELS), {
            "AUTHOR_DECLARED",
            "CURATED",
            "INFERRED_HIGH_CONFIDENCE",
            "INFERRED",
            "UNKNOWN",
        })
        using = overlay["skills"]["using-superpowers"]
        self.assertEqual(
            using["provenance"]["fields"]["roles"]["source"], "CURATED"
        )
        self.assertEqual(using["tier"], "TIER_1_CORE")

    def test_census_explicitly_records_absent_registry_fields(self):
        overlay = load_overlay(OVERLAY)
        current = overlay["census"]["current_registry_field_presence"]
        enriched = overlay["census"]["overlay_field_presence"]

        self.assertEqual(current["source"], 214)
        self.assertEqual(current["trust"], 214)
        self.assertEqual(current["agent_compatibility"], 0)
        self.assertEqual(enriched["roles"], 214)
        self.assertEqual(enriched["permissions"], 0)
        self.assertEqual(enriched["agent_compatibility"], 0)
        self.assertEqual(enriched["source"], 0)
        self.assertEqual(enriched["source.license"], 39)

    def test_runtime_catalog_load_does_not_read_skill_bodies(self):
        with patch(
            "tools.v3.metadata_enrichment._body_path",
            side_effect=AssertionError("normal catalog load read a body"),
        ) as body_path:
            from tools.v3.metadata_enrichment import load_enriched_catalog

            records = load_enriched_catalog(REGISTRY)

        self.assertEqual(len(records), 214)
        body_path.assert_not_called()

    def test_enrichment_never_executes_commands_from_skill_body(self):
        content = (
            "---\nname: sample\ndescription: sample\n---\n\n"
            "```bash\nrm -f should-never-run\n```\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry_path = _single_registry(root, content)
            with patch.object(subprocess, "run") as run, patch.object(
                subprocess, "Popen"
            ) as popen, patch.object(os, "system") as system:
                overlay = build_overlay(root, registry_path)

        self.assertEqual(overlay["skills"]["sample"]["body_policy"], "READ_ONLY")
        run.assert_not_called()
        popen.assert_not_called()
        system.assert_not_called()

    def test_curated_metadata_scores_above_inferred_metadata(self):
        base = {
            "schema_version": "3.0",
            "skill_id": "candidate",
            "name": "candidate",
            "description": "Implement a software engineering change.",
            "source": {
                "repo": "https://example.invalid/skills",
                "ref": "test",
                "path": "candidate/SKILL.md",
                "digest": _digest("candidate"),
            },
            "trust": "CORE_TRUSTED",
            "roles": ["PROCESS"],
            "stages": ["implement"],
            "domains": ["software-engineering"],
            "task_modes": ["implementation"],
        }
        curated = dict(base)
        curated["extensions"] = {
            "routing": {
                "source": "v3_routing_metadata_overlay",
                "metadata_provenance": {
                    "default": "UNKNOWN",
                    "fields": {
                        field: {"source": "CURATED", "confidence": 1.0}
                        for field in ("roles", "stages", "domains", "task_modes")
                    },
                },
            }
        }
        inferred = dict(base)
        inferred["extensions"] = {
            "routing": {
                "source": "v3_routing_metadata_overlay",
                "metadata_provenance": {
                    "default": "UNKNOWN",
                    "fields": {
                        field: {"source": "INFERRED", "confidence": 0.55}
                        for field in ("roles", "stages", "domains", "task_modes")
                    },
                },
            }
        }
        task = {
            "schema_version": "3.0",
            "task_id": "T-quality",
            "task_type": "implementation",
            "goal": "Implement a software engineering change",
            "complexity": "STANDARD",
            "risk": "LOW",
            "ambiguity": "LOW",
            "architecture_impact": "LOCAL",
            "objectives": ["Implement the change"],
        }
        stage = {
            "id": "implement",
            "objective": "Implement the change",
            "task_type": "implementation",
            "domains": ["software-engineering"],
            "required_outputs": [],
            "evidence_required": [],
        }

        self.assertGreater(metadata_quality(curated), metadata_quality(inferred))
        curated_score = score_candidate(curated, task, stage, ["PROCESS"])
        inferred_score = score_candidate(inferred, task, stage, ["PROCESS"])
        self.assertIsNotNone(curated_score)
        self.assertIsNotNone(inferred_score)
        self.assertGreater(curated_score.score, inferred_score.score)

    def test_unknown_routing_metadata_is_conservative(self):
        record = {
            "schema_version": "3.0",
            "skill_id": "unknown-routing",
            "name": "unknown-routing",
            "description": "A procedure with no routing declaration.",
            "source": {
                "repo": "https://example.invalid/skills",
                "ref": "test",
                "path": "unknown/SKILL.md",
                "digest": _digest("unknown"),
            },
            "trust": "CORE_TRUSTED",
            "extensions": {
                "routing": {
                    "source": "v3_routing_metadata_overlay",
                    "metadata_provenance": {
                        "default": "UNKNOWN",
                        "fields": {},
                    },
                }
            },
        }
        self.assertEqual(metadata_quality(record), 0.0)

    def test_inferred_metadata_cannot_declare_permissions(self):
        content = "---\nname: sample\ndescription: sample\n---\n\nProcedure.\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry_path = _single_registry(root, content)
            overlay = build_overlay(
                root,
                registry_path,
                verified_at="2026-09-09T00:00:00Z",
            )
            record = overlay["skills"]["sample"]
            record["metadata"]["permissions"] = {"filesystem": "workspace-write"}
            record["provenance"]["fields"]["permissions"] = {
                "source": "INFERRED",
                "confidence": 0.4,
            }

            validation = validate_overlay(
                overlay,
                registry_path=registry_path,
                repository_root=root,
            )

        self.assertFalse(validation.valid)
        self.assertTrue(any("permissions" in error for error in validation.errors))

    def test_enrichment_reads_body_as_data_and_never_executes_commands(self):
        content = (
            "---\nname: sample\ndescription: sample\n---\n\n"
            "```bash\nraise_this_would_be_executable\n```\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry_path = _single_registry(root, content)
            overlay = build_overlay(root, registry_path)
            self.assertNotIn("raise_this_would_be_executable", json.dumps(overlay))
            self.assertEqual(overlay["skills"]["sample"]["body_policy"], "READ_ONLY")

    def test_overlay_digest_and_body_staleness_are_detected(self):
        content = "---\nname: sample\ndescription: sample\n---\n\nProcedure.\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry_path = _single_registry(root, content)
            overlay = build_overlay(
                root,
                registry_path,
                verified_at="2026-09-09T00:00:00Z",
            )
            self.assertTrue(
                validate_overlay(
                    overlay,
                    registry_path=registry_path,
                    repository_root=root,
                    check_bodies=True,
                ).valid
            )
            (root / "sample/SKILL.md").write_text(content + "changed\n", encoding="utf-8")
            stale = validate_overlay(
                overlay,
                registry_path=registry_path,
                repository_root=root,
                check_bodies=True,
            )

        self.assertFalse(stale.valid)
        self.assertTrue(any("stale" in error for error in stale.errors))

    def test_relationships_have_provenance_and_high_confidence_overlap_edges(self):
        overlay = load_overlay(OVERLAY)
        tdd = overlay["skills"]["test-driven-development"]
        self.assertTrue(
            any(
                relation["type"] == "VERIFY_WITH"
                and relation["target"] == "verification-before-completion"
                for relation in tdd["metadata"].get("relationships", [])
            )
        )
        self.assertIn(
            "VERIFY_WITH:verification-before-completion",
            tdd["provenance"]["relationships"],
        )
        imagine = overlay["skills"]["baoyu-imagine"]
        self.assertTrue(
            any(
                relation["type"] == "SUPERSEDES"
                and relation["target"] == "baoyu-image-gen"
                for relation in imagine["metadata"].get("relationships", [])
            )
        )

    def test_generation_is_deterministic_for_fixed_inputs(self):
        first = build_overlay(
            ROOT,
            REGISTRY,
            verified_at="2026-09-09T00:00:00Z",
        )
        second = build_overlay(
            ROOT,
            REGISTRY,
            verified_at="2026-09-09T00:00:00Z",
        )

        self.assertEqual(first, second)

    def test_apply_overlay_marks_runtime_as_metadata_only(self):
        overlay = load_overlay(OVERLAY)
        record = apply_overlay(
            {
                "id": "using-superpowers",
                "name": "using-superpowers",
                "description": "resident authority",
                "relative_path": "using-superpowers/SKILL.md",
                "sha256": overlay["skills"]["using-superpowers"]["source_skill_digest"][len("sha256:") :],
            },
            {
                "schema_version": "1.0",
                "source": "https://github.com/juhjuhx/agent-skills.git",
                "source_ref": "main",
                "source_commit": overlay["registry"]["source_commit"],
            },
            overlay,
        )
        routing = record["extensions"]["routing"]
        self.assertEqual(routing["source"], "v3_routing_metadata_overlay")
        self.assertFalse(routing["body_loaded_for_route"])


if __name__ == "__main__":
    unittest.main()
