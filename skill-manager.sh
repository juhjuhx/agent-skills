#!/bin/bash
set -euo pipefail

TARGET="${HOME}/.agents/skills"
ENABLED="${HOME}/.agents/skills-enabled"
CONFIG="${HOME}/.agents/skills-config.json"
MANIFEST="${TARGET}/categories.json"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

if [ ! -d "$TARGET" ]; then
  echo -e "${RED}Skills not installed. Run install.sh first.${NC}"
  exit 1
fi

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Agent Skills Manager            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

case "${1:-}" in
  list)
    echo -e "${CYAN}Available categories:${NC}"
    jq -r '.categories[] | "  \(.icon) \(.id) — \(.description)"' "$MANIFEST"
    echo ""
    if [ -f "$CONFIG" ]; then
      echo -e "${GREEN}Currently enabled:${NC}"
      jq -r '.categories[]' "$CONFIG" | sed 's/^/  /'
    fi
    ;;
  enable)
    if [ -z "${2:-}" ]; then
      echo -e "${RED}Usage: skill-manager.sh enable <category>${NC}"
      exit 1
    fi
    # Re-run install with current + new category
    CURRENT=$(jq -r '.categories[]' "$CONFIG" 2>/dev/null || echo "")
    NEW="${2}"
    ALL="${CURRENT}"$'\n'"${NEW}"
    MERGED=$(echo "$ALL" | sort -u | grep -v '^$' | paste -sd, -)
    echo -e "${GREEN}Enabling categories: $MERGED${NC}"
    exec bash "${TARGET}/install.sh" --category "$MERGED"
    ;;
  disable)
    if [ -z "${2:-}" ]; then
      echo -e "${RED}Usage: skill-manager.sh disable <category>${NC}"
      exit 1
    fi
    CURRENT=$(jq -r '.categories[]' "$CONFIG" 2>/dev/null || echo "")
    FILTERED=$(echo "$CURRENT" | grep -v "^${2}$" | grep -v '^$' | paste -sd, -)
    if [ -z "$FILTERED" ]; then
      echo -e "${RED}Cannot disable all categories. Use --minimal for essentials.${NC}"
      exit 1
    fi
    echo -e "${YELLOW}Disabling category: $2${NC}"
    exec bash "${TARGET}/install.sh" --category "$FILTERED"
    ;;
  switch)
    if [ -z "${2:-}" ]; then
      echo -e "${RED}Usage: skill-manager.sh switch <profile>${NC}"
      echo "Profiles: minimal, default, full"
      exit 1
    fi
    case "${2}" in
      full)    exec bash "${TARGET}/install.sh" --all ;;
      default) exec bash "${TARGET}/install.sh" --category essential,coding,design ;;
      minimal) exec bash "${TARGET}/install.sh" --minimal ;;
      *)       echo "Unknown profile: ${2}. Options: minimal, default, full" ; exit 1 ;;
    esac
    ;;
  stats)
    echo -e "${CYAN}Skill statistics:${NC}"
    TOTAL=$(ls -d "${TARGET}"/*/ 2>/dev/null | grep -v '_shared' | wc -l)
    ENABLED_COUNT=$(ls -d "${ENABLED}"/*/ 2>/dev/null | grep -v '_shared' | wc -l)
    echo -e "  Total in repo:  ${YELLOW}$TOTAL${NC}"
    echo -e "  Currently enabled: ${GREEN}$ENABLED_COUNT${NC}"
    echo ""
    if [ -f "$CONFIG" ]; then
      echo -e "${CYAN}Current config:${NC}"
      cat "$CONFIG" | jq .
    fi
    ;;
  reapply)
    if [ -f "$CONFIG" ]; then
      MODE=$(jq -r '.mode // "interactive"' "$CONFIG")
      if [ "$MODE" = "category" ]; then
        CATS=$(jq -r '.categories | join(",")' "$CONFIG")
        exec bash "${TARGET}/install.sh" --category "$CATS"
      else
        case "$MODE" in
          all)     exec bash "${TARGET}/install.sh" --all ;;
          minimal) exec bash "${TARGET}/install.sh" --minimal ;;
          *)       exec bash "${TARGET}/install.sh" "--${MODE}" ;;
        esac
      fi
    else
      echo -e "${RED}No config found. Run install.sh directly.${NC}"
      exit 1
    fi
    ;;
  *)
    echo "Usage: skill-manager.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  list                  Show all categories and current selection"
    echo "  enable   <category>   Add a category"
    echo "  disable  <category>   Remove a category"
    echo "  switch   <profile>    Switch to a profile (minimal|default|full)"
    echo "  stats                 Show skill counts and config"
    echo "  reapply               Re-apply current config after update"
    ;;
esac
