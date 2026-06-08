#!/bin/bash
set -euo pipefail

# ============================================================
# Agent Skills Universal Installer
# Installs 167 skills to all supported AI agents on this machine
# ============================================================

REPO="https://github.com/juhjuhx/agent-skills.git"
TARGET="${HOME}/.agents/skills"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    Agent Skills Universal Installer     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# --- Clone / Update skills ---
if [ -d "${TARGET}" ]; then
  echo -e "${YELLOW}📂 Updating existing skills...${NC}"
  cd "${TARGET}" && git pull
else
  echo -e "${YELLOW}📦 Cloning 167 skills...${NC}"
  git clone "${REPO}" "${TARGET}"
fi
echo ""

# --- Detect and link to all installed agents ---
link_count=0

link_skills() {
  local agent_name="$1"
  local target_dir="$2"
  local install_cmd="$3"

  if [ -d "$(dirname "${target_dir}")" ] || [ "${install_cmd}" = "always" ]; then
    mkdir -p "$(dirname "${target_dir}")"
    rm -rf "${target_dir}"
    ln -sfn "${TARGET}" "${target_dir}"
    echo -e "  ${GREEN}✅${NC} ${agent_name} → ${target_dir}"
    ((link_count++))
  fi
}

echo -e "${CYAN}🔗 Linking to detected agents...${NC}"

# OpenCode
link_skills "OpenCode"       "${HOME}/.config/opencode/skills"      "detect"

# Gemini CLI
link_skills "Gemini CLI"     "${HOME}/.gemini/skills"               "detect"

# Claude Code
link_skills "Claude Code"    "${HOME}/.claude/skills"               "detect"

# Cursor
link_skills "Cursor"         "${HOME}/.cursor/skills"              "detect"

# Codex (by OpenAI)
link_skills "Codex"          "${HOME}/.codex/skills"               "detect"

# Windsurf
link_skills "Windsurf"       "${HOME}/.windsurf/skills"            "detect"

# Continue (VS Code extension)
link_skills "Continue"       "${HOME}/.continue/skills"            "detect"

# Aider
link_skills "Aider"          "${HOME}/.aider/skills"               "detect"

# Future-proof: create a symlink in ~/.local/share/agent-skills
mkdir -p "${HOME}/.local/share"
rm -f "${HOME}/.local/share/agent-skills"
ln -sfn "${TARGET}" "${HOME}/.local/share/agent-skills"
echo -e "  ${GREEN}✅${NC} Universal pointer → ${HOME}/.local/share/agent-skills"

echo ""

# --- Gemini-specific: enable all discovered skills ---
if command -v gemini &>/dev/null; then
  echo -e "${YELLOW}⚡ Enabling all Gemini skills...${NC}"
  gemini skills list 2>/dev/null | grep -oP '^\s+\K\S+' | while read -r skill; do
    gemini skills enable "${skill}" 2>/dev/null || true
  done
  echo -e "  ${GREEN}✅${NC} Gemini skills enabled"
  echo ""
fi

# --- Summary ---
SKILL_COUNT=$(ls -d "${TARGET}"/*/ 2>/dev/null | wc -l | tr -d ' ')
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Install complete!${NC}"
echo -e "${GREEN}  📊 ${SKILL_COUNT} skills installed${NC}"
echo -e "${GREEN}  🔗 Linked to ${link_count} agent environments${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""
echo -e "To update later:  ${YELLOW}cd ~/.agents/skills && git pull${NC}"
