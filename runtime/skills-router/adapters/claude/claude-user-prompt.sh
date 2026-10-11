#!/bin/sh
# V3 advice only; missing Python/helper never blocks the host.
SOURCE=${SKILLS_ROUTER_SOURCE:-"${HOME}/.agents/skills"}
PYTHON=${SKILLS_ROUTER_PYTHON:-python3}
HOOK="$SOURCE/runtime/skills-router/adapters/claude/skills-router-hook.py"
if [ ! -f "$HOOK" ]; then
  printf '{}\n'
  exit 0
fi
"$PYTHON" "$HOOK" || printf '{}\n'
exit 0
