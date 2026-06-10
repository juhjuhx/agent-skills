#!/bin/bash
set -euo pipefail

REPO="https://github.com/juhjuhx/agent-skills.git"
TARGET="${HOME}/.agents/skills"
ENABLED="${HOME}/.agents/skills-enabled"
CONFIG="${HOME}/.agents/skills-config.json"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    Agent Skills Universal Installer     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# --- Flag parsing ---
MODE="interactive"
SELECTED_CATEGORIES=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all|-a)       MODE="all"; shift ;;
    --minimal|-m)   MODE="minimal"; shift ;;
    --category|-c)  MODE="category"; SELECTED_CATEGORIES="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: bash install.sh [OPTION]"
      echo ""
      echo "Options:"
      echo "  --all, -a              Install ALL skills (170+)"
      echo "  --minimal, -m          Install only essential + coding skills"
      echo "  --category, -c LIST    Install specific categories (comma-separated)"
      echo "                         Example: --category essential,coding,design"
      echo "  --help, -h             Show this help"
      echo ""
      echo "Without options, runs in interactive mode."
      exit 0
      ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; exit 1 ;;
  esac
done

# --- Clone / Update skills ---
if [ -d "${TARGET}" ]; then
  echo -e "${YELLOW}📂 Updating existing skills...${NC}"
  cd "${TARGET}" && git pull
else
  echo -e "${YELLOW}📦 Cloning skills repository...${NC}"
  git clone "${REPO}" "${TARGET}"
fi
echo ""

MANIFEST="${TARGET}/categories.json"

# --- Resolve which categories to enable ---
resolve_categories() {
  local mode="$1"
  local selected="$2"
  local result=""
  local tmp

  case "$mode" in
    all)
      result=$(jq -r '.profiles.full.categories[]' "$MANIFEST")
      ;;
    minimal)
      result=$(jq -r '.profiles.minimal.categories[]' "$MANIFEST")
      ;;
    category)
      IFS=',' read -ra cats <<< "$selected"
      for cat in "${cats[@]}"; do
        trimmed=$(echo "$cat" | xargs)
        found=$(jq -r --arg c "$trimmed" '.categories[] | select(.id == $c) | .id' "$MANIFEST")
        if [ -z "$found" ]; then
          echo -e "${RED}Unknown category: $trimmed${NC}" >&2
          echo "Valid categories:" >&2
          jq -r '.categories[].id' "$MANIFEST" | sed 's/^/  /' >&2
          exit 1
        fi
        result="$result"$'\n'"$trimmed"
      done
      ;;
    interactive)
      # Build arrays
      ids=()
      names=()
      icons=()
      descs=()
      defaults=()

      while IFS=$'\t' read -r id name icon desc default; do
        ids+=("$id")
        names+=("$name")
        icons+=("$icon")
        descs+=("$desc")
        defaults+=("$default")
      done < <(jq -r '.categories[] | "\(.id)\t\(.name)\t\(.icon)\t\(.description)\t\(.default)"' "$MANIFEST")

      echo -e "${CYAN}Select skill categories to install:${NC}"
      echo ""
      for i in "${!ids[@]}"; do
        default_flag=""
        [ "${defaults[$i]}" = "true" ] && default_flag=" [default]"
        echo "  $((i+1))) ${icons[$i]} ${names[$i]} — ${descs[$i]}$default_flag"
      done
      echo ""
      echo -e "  ${YELLOW}Enter comma-separated numbers (e.g. 1,2,3) or press Enter for defaults${NC}"
      echo -n "  Select categories: "
      read user_input

      if [ -z "$user_input" ]; then
        for i in "${!ids[@]}"; do
          [ "${defaults[$i]}" = "true" ] && result="$result"$'\n'"${ids[$i]}"
        done
      else
        IFS=',' read -ra indices <<< "$user_input"
        for idx in "${indices[@]}"; do
          idx_trimmed=$(echo "$idx" | xargs)
          id_idx=$((idx_trimmed - 1))
          [ "$id_idx" -ge 0 ] && [ "$id_idx" -lt "${#ids[@]}" ] && result="$result"$'\n'"${ids[$id_idx]}"
        done
      fi
      ;;
  esac

  echo "$result" | grep -v '^$'
}

SELECTED=$(resolve_categories "$MODE" "$SELECTED_CATEGORIES")

# --- Build skills-enabled directory ---
rm -rf "${ENABLED}"
mkdir -p "${ENABLED}"

# Collect all skill dirs from selected categories
ALL_SKILLS=""
NEEDS_BROOKS=false
NEEDS_LOGIC=false

while IFS= read -r cat_id; do
  [ -z "$cat_id" ] && continue
  skills=$(jq -r --arg id "$cat_id" '.categories[] | select(.id == $id) | .skills[]' "$MANIFEST")
  ALL_SKILLS="$ALL_SKILLS"$'\n'"$skills"
done < <(echo "$SELECTED")

# Check shared deps
while IFS= read -r skill; do
  [ -z "$skill" ] && continue
  [[ "$skill" == brooks-* ]] && NEEDS_BROOKS=true
  [[ "$skill" == logic-* ]] && NEEDS_LOGIC=true
done < <(echo "$ALL_SKILLS" | grep -v '^$')

# Symlink shared dirs
[ "$NEEDS_BROOKS" = true ] && [ -d "${TARGET}/brooks-_shared" ] && \
  ln -sfn "${TARGET}/brooks-_shared" "${ENABLED}/brooks-_shared"
[ "$NEEDS_LOGIC" = true ] && [ -d "${TARGET}/logic-_shared" ] && \
  ln -sfn "${TARGET}/logic-_shared" "${ENABLED}/logic-_shared"

# Symlink selected skills
LINK_COUNT=0
SKIP_COUNT=0
while IFS= read -r skill; do
  [ -z "$skill" ] && continue
  if [ -d "${TARGET}/${skill}" ]; then
    ln -sfn "${TARGET}/${skill}" "${ENABLED}/${skill}"
    LINK_COUNT=$((LINK_COUNT + 1))
  else
    >&2 echo -e "  ${YELLOW}⚠  Warning: '${skill}' not found in repo${NC}"
    SKIP_COUNT=$((SKIP_COUNT + 1))
  fi
done < <(echo "$ALL_SKILLS" | grep -v '^$')

echo -e "  ${GREEN}✅${NC} ${LINK_COUNT} skills enabled"
[ "$SKIP_COUNT" -gt 0 ] && echo -e "  ${YELLOW}⚠${NC} ${SKIP_COUNT} skipped"

# Copy manifest + config for reference
cp "$MANIFEST" "${ENABLED}/categories.json"

# Save user config
CAT_JSON=$(echo "$SELECTED" | sort -u | grep -v '^$' | jq -R -s -c 'split("\n") | map(select(length > 0))')
cat > "$CONFIG" << EOF
{
  "mode": "$MODE",
  "categories": $CAT_JSON,
  "enabled_skills_count": $LINK_COUNT
}
EOF

echo ""

# --- Link to detected agents ---
link_count=0
link_skills() {
  local agent_name="$1"
  local target_dir="$2"
  if [ -d "$(dirname "$target_dir")" ]; then
    mkdir -p "$(dirname "$target_dir")"
    rm -rf "${target_dir}"
    ln -sfn "${ENABLED}" "${target_dir}"
    echo -e "  ${GREEN}✅${NC} ${agent_name}"
    link_count=$((link_count + 1))
  fi
}

echo -e "${CYAN}🔗 Linking to detected agents...${NC}"

link_skills "OpenCode"    "${HOME}/.config/opencode/skills"
link_skills "Gemini CLI"  "${HOME}/.gemini/skills"
link_skills "Claude Code" "${HOME}/.claude/skills"
link_skills "Cursor"      "${HOME}/.cursor/skills"
link_skills "Codex"       "${HOME}/.codex/skills"
link_skills "Windsurf"    "${HOME}/.windsurf/skills"
link_skills "Continue"    "${HOME}/.continue/skills"
link_skills "Aider"       "${HOME}/.aider/skills"

mkdir -p "${HOME}/.local/share"
rm -f "${HOME}/.local/share/agent-skills"
ln -sfn "${ENABLED}" "${HOME}/.local/share/agent-skills"
echo -e "  ${GREEN}✅${NC} Universal pointer → ${HOME}/.local/share/agent-skills"
echo ""

# --- Gemini: enable all discovered skills ---
# Only run if this is Google's Gemini CLI, not an npm package with the same name
if command -v gemini &>/dev/null && gemini --version 2>/dev/null | grep -qi google; then
  echo -e "${YELLOW}⚡ Enabling Gemini skills...${NC}"
  timeout 10 gemini skills list 2>/dev/null | grep -oP '^\s+\K\S+' | while read -r skill; do
    timeout 10 gemini skills enable "${skill}" 2>/dev/null || true
  done
  echo -e "  ${GREEN}✅${NC} Gemini skills enabled"
  echo ""
fi

# --- Summary ---
CAT_COUNT=$(echo "$SELECTED" | sort -u | grep -v '^$' | wc -l)
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Install complete!${NC}"
echo -e "${GREEN}  📊 ${LINK_COUNT} skills from ${CAT_COUNT} categories${NC}"
echo -e "${GREEN}  🔗 Linked to ${link_count} agent environments${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""
echo -e "Full repo:        ${YELLOW}${TARGET}${NC}"
echo -e "Enabled symlinks: ${YELLOW}${ENABLED}${NC}"
echo -e "Config:           ${YELLOW}${CONFIG}${NC}"
echo ""
echo -e "Change categories later:"
echo -e "  ${YELLOW}bash ${TARGET}/skill-manager.sh${NC}"
echo ""
echo -e "Update skills:"
echo -e "  ${YELLOW}(cd ${TARGET} && git pull)${NC}"
echo -e "  ${YELLOW}bash ${TARGET}/install.sh \$YOUR_FLAGS${NC}"
