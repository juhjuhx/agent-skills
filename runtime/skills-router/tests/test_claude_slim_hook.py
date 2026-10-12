import json
import os
from pathlib import Path
import subprocess
import unittest

HOOK = Path(__file__).resolve().parents[1] / "adapters/claude/claude-user-prompt.sh"


class SlimHookTests(unittest.TestCase):
    def call(self, payload, **env):
        return subprocess.run(
            ["sh", str(HOOK)],
            input=payload,
            text=True,
            capture_output=True,
            env={**os.environ, **env},
            timeout=10,
        )

    def test_unavailable_router_leaves_prompt_and_tools_alone(self):
        result = self.call(
            '{"prompt":"fix bug"}', SKILLS_ROUTER_SOURCE="/nonexistent-v3-source"
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("decision", json.loads(result.stdout))
        self.assertNotIn("suppressOriginalPrompt", json.loads(result.stdout))

    def test_invalid_payload_is_nonblocking(self):
        result = self.call("not json")
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("decision", json.loads(result.stdout))

    def test_claude_context_is_slim_advice(self):
        source = str(Path(__file__).resolve().parents[3])
        result = self.call('{"prompt":"fix bug"}', SKILLS_ROUTER_SOURCE=source)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertNotIn("decision", data)
        self.assertIn(
            "Personal Tool Master", data["hookSpecificOutput"]["additionalContext"]
        )
        self.assertNotIn("RuntimeDecision", result.stdout)
