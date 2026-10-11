#!/usr/bin/env bash
# Native Skills remain usable without the optional V3 adapter.
set -euo pipefail
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  INSTALLER_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  INSTALLER_PATH="${INSTALLER_DIR}/scripts/install_v3.py"
  if [ -f "$INSTALLER_PATH" ]; then
    exec python3 "$INSTALLER_PATH" "$@"
  fi
fi
# Retain the documented curl/bash bootstrap interface; no global dependencies.
INSTALLER_TMP="$(mktemp -t agent-skills-v3.XXXXXX)"
trap 'rm -f "$INSTALLER_TMP"' EXIT
curl -fsSL https://raw.githubusercontent.com/juhjuhx/agent-skills/main/scripts/install_v3.py -o "$INSTALLER_TMP"
python3 "$INSTALLER_TMP" "$@"
