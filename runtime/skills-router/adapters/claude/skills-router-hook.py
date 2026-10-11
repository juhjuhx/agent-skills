#!/usr/bin/env python3
"""V3 UserPromptSubmit：只注入建議，失敗也不阻擋prompt／工具。"""

import importlib.util
import json
import os
from pathlib import Path
import sys


def main():
    result = {}
    try:
        raw = sys.stdin.read(32769)
        if len(raw) > 32768:
            raise ValueError("oversized")
        payload = json.loads(raw or "{}")
        if not isinstance(payload, dict):
            raise ValueError("invalid payload")
        task = payload.get("prompt", payload.get("user_prompt", ""))
        if not isinstance(task, str) or not task.strip():
            raise ValueError("empty prompt")
        root = Path(
            os.environ.get("SKILLS_ROUTER_SOURCE", str(Path.home() / ".agents/skills"))
        )
        spec = importlib.util.spec_from_file_location(
            "tool_master_v3", root / "runtime/skills-router/tool_master.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        packet = module.build_route_packet(
            task, root=root, host="claude", tools=payload.get("tools")
        )
        context = (
            "Personal Tool Master V3 — advisory; host-native tools remain available.\n"
            + module.render_packet(packet)
        )
        result = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context[:12000],
            }
        }
    except Exception:
        pass
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
