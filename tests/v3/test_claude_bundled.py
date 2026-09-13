"""Calibrated, bounded static bundled-skill evidence tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.v3.claude_bundled import (
    BUNDLED_COLLISION_NONE_VERIFIED,
    BUNDLED_COLLISION_PRESENT,
    BUNDLED_COLLISION_UNKNOWN,
    ClaudeBundledEvidenceError,
    inspect_claude_bundled_skills,
)
from tools.v3.productization import digest_bytes


MARKERS = (
    "getBundledSkills",
    "getRegisteredBundledSkillsIgnoringKillSwitch",
    "registerBundledSkill",
    "getBundledSkillsRoot",
)


class ClaudeBundledEvidenceTests(unittest.TestCase):
    def _artifact(self, payload: bytes) -> tuple[Path, str]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "claude"
        path.write_bytes(payload)
        return path, digest_bytes(payload)

    def test_known_bundle_calibrates_candidate_absence(self) -> None:
        path, fingerprint = self._artifact(
            ("claude-code-guide " + " ".join(MARKERS) + " SKILL_MD").encode()
        )
        evidence = inspect_claude_bundled_skills(
            artifact_path=path,
            expected_artifact_sha256=fingerprint,
            candidate_slugs=("module-map",),
        )
        self.assertTrue(evidence["calibration"]["passed"])
        self.assertIn("claude-code-guide", evidence["known_bundled_identifiers_recovered"])
        self.assertEqual(
            evidence["candidate_results"]["module-map"],
            BUNDLED_COLLISION_NONE_VERIFIED,
        )

    def test_candidate_presence_is_reported(self) -> None:
        payload = ("claude-code-guide " + " ".join(MARKERS) + " module-map").encode()
        path, fingerprint = self._artifact(payload)
        evidence = inspect_claude_bundled_skills(
            artifact_path=path,
            expected_artifact_sha256=fingerprint,
            candidate_slugs=("module-map",),
        )
        self.assertEqual(
            evidence["candidate_results"]["module-map"],
            BUNDLED_COLLISION_PRESENT,
        )

    def test_absence_without_calibration_remains_unknown(self) -> None:
        path, fingerprint = self._artifact(b"claude-code-guide SKILL_MD")
        evidence = inspect_claude_bundled_skills(
            artifact_path=path,
            expected_artifact_sha256=fingerprint,
            candidate_slugs=("module-map",),
        )
        self.assertFalse(evidence["calibration"]["passed"])
        self.assertEqual(
            evidence["candidate_results"]["module-map"],
            BUNDLED_COLLISION_UNKNOWN,
        )

    def test_artifact_fingerprint_change_fails_closed(self) -> None:
        path, _fingerprint = self._artifact(b"claude-code-guide")
        with self.assertRaisesRegex(ClaudeBundledEvidenceError, "fingerprint"):
            inspect_claude_bundled_skills(
                artifact_path=path,
                expected_artifact_sha256="sha256:" + "0" * 64,
                candidate_slugs=("module-map",),
            )


if __name__ == "__main__":
    unittest.main()
