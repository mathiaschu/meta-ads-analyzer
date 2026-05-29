#!/bin/bash
# Meta Ads Analyzer — Universal Installer
# Installs the skill for any supported AI coding platform
# Usage: bash scripts/install.sh [hermes|claude-code|cursor|copilot|opencode|windsurf|aider|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PLATFORM="${1:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

show_usage() {
    echo "Meta Ads Analyzer — Universal Installer"
    echo ""
    echo "Usage: bash scripts/install.sh <platform>"
    echo ""
    echo "Supported platforms:"
    echo "  hermes       Hermes Agent"
    echo "  claude-code  Claude Code (Anthropic)"
    echo "  cursor       Cursor IDE"
    echo "  copilot      GitHub Copilot"
    echo "  opencode     OpenCode CLI"
    echo "  windsurf     Windsurf IDE"
    echo "  aider        Aider CLI"
    echo "  all          Install for all detected platforms"
    echo ""
    echo "Example: bash scripts/install.sh hermes"
    exit 0
}

install_hermes() {
    echo -e "${CYAN}Installing for Hermes Agent...${NC}"
    HERMES_SKILLS="$HOME/.hermes/skills/meta-ads-analyzer"
    mkdir -p "$HERMES_SKILLS"
    cp "$REPO_ROOT/platforms/hermes/SKILL.md" "$HERMES_SKILLS/"
    cp -r "$REPO_ROOT/references" "$HERMES_SKILLS/"
    echo -e "${GREEN}✓ Hermes skill installed to $HERMES_SKILLS${NC}"
}

install_claude_code() {
    echo -e "${CYAN}Installing for Claude Code...${NC}"
    CLAUDE_SKILLS=".claude/skills/meta-ads-analyzer"
    mkdir -p "$CLAUDE_SKILLS"
    cp "$REPO_ROOT/platforms/claude-code/SKILL.md" "$CLAUDE_SKILLS/"
    cp -r "$REPO_ROOT/references" "$CLAUDE_SKILLS/"
    echo -e "${GREEN}✓ Claude Code skill installed to $CLAUDE_SKILLS${NC}"
}

install_cursor() {
    echo -e "${CYAN}Installing for Cursor...${NC}"
    mkdir -p .cursor/rules
    cp "$REPO_ROOT/platforms/cursor/meta-ads-analyzer.mdc" .cursor/rules/
    mkdir -p .cursor/rules/references
    cp -r "$REPO_ROOT/references/"* .cursor/rules/references/
    echo -e "${GREEN}✓ Cursor rules installed to .cursor/rules/${NC}"
}

install_copilot() {
    echo -e "${CYAN}Installing for GitHub Copilot...${NC}"
    mkdir -p .github
    cp "$REPO_ROOT/platforms/copilot/copilot-instructions.md" .github/
    echo -e "${GREEN}✓ Copilot instructions installed to .github/copilot-instructions.md${NC}"
}

install_opencode() {
    echo -e "${CYAN}Installing for OpenCode...${NC}"
    OPENCODE_SKILLS="$HOME/.opencode/skills/meta-ads-analyzer"
    mkdir -p "$OPENCODE_SKILLS"
    cp "$REPO_ROOT/platforms/opencode/SKILL.md" "$OPENCODE_SKILLS/"
    cp -r "$REPO_ROOT/references" "$OPENCODE_SKILLS/"
    echo -e "${GREEN}✓ OpenCode skill installed to $OPENCODE_SKILLS${NC}"
}

install_windsurf() {
    echo -e "${CYAN}Installing for Windsurf...${NC}"
    cp "$REPO_ROOT/platforms/windsurf/.windsurfrules" .windsurfrules
    echo -e "${GREEN}✓ Windsurf rules installed to .windsurfrules${NC}"
}

install_aider() {
    echo -e "${CYAN}Installing for Aider...${NC}"
    cp "$REPO_ROOT/platforms/aider/.aider.rules" .aider.rules
    echo -e "${GREEN}✓ Aider rules installed to .aider.rules${NC}"
}

if [ -z "$PLATFORM" ]; then
    show_usage
fi

case "$PLATFORM" in
    hermes)
        install_hermes
        ;;
    claude-code)
        install_claude_code
        ;;
    cursor)
        install_cursor
        ;;
    copilot)
        install_copilot
        ;;
    opencode)
        install_opencode
        ;;
    windsurf)
        install_windsurf
        ;;
    aider)
        install_aider
        ;;
    all)
        echo -e "${YELLOW}Installing for all platforms...${NC}"
        echo ""
        install_hermes
        install_claude_code
        install_cursor
        install_copilot
        install_opencode
        install_windsurf
        install_aider
        ;;
    -h|--help|help)
        show_usage
        ;;
    *)
        echo -e "${RED}Unknown platform: $PLATFORM${NC}"
        show_usage
        ;;
esac

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "Next steps:"
echo "  • For live API data: bash scripts/setup.sh"
if [ "$PLATFORM" = "all" ]; then
    echo "  • See platforms/<platform>/INSTALL.md for per-platform instructions"
else
    echo "  • See platforms/$PLATFORM/INSTALL.md for detailed instructions"
fi
