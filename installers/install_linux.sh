#!/usr/bin/env bash
# install.sh — One-shot installer for ctools
# Usage: ./install.sh [--force]

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

FORCE=false
[[ "${1:-}" == "--force" ]] && FORCE=true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SLASH_CMD_SRC="$PROJECT_DIR/slash-command/tools.md"
SLASH_CMD_DST="$HOME/.claude/commands/tools.md"

info() { echo -e "${CYAN}[INFO]${NC} $1"; }
ok() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# --- Step 1: Check Python >= 3.10 ---
info "Checking Python version..."
if ! command -v python3 &>/dev/null; then
    err "python3 not found. Please install Python 3.10+."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [[ "$PY_MAJOR" -lt 3 ]] || { [[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -lt 10 ]]; }; then
    err "Python >= 3.10 required (found $PY_VERSION)."
    exit 1
fi
ok "Python $PY_VERSION"

# --- Step 2: Install ctools ---
info "Installing ctools..."

if command -v pipx &>/dev/null; then
    info "Using pipx..."
    pipx install "$PROJECT_DIR" --force 2>&1 | tail -5
    ok "Installed via pipx"
elif command -v uv &>/dev/null; then
    info "Using uv..."
    uv tool install "$PROJECT_DIR" --force 2>&1 | tail -5
    ok "Installed via uv tool"
else
    info "Using pip install --user..."
    python3 -m pip install --user "$PROJECT_DIR" 2>&1 | tail -5
    ok "Installed via pip --user"
fi

# --- Step 3: Check PATH ---
CTOOLS_BIN=$(command -v ctools 2>/dev/null || true)
if [[ -z "$CTOOLS_BIN" ]]; then
    warn "ctools not found on PATH."
    warn "Add ~/.local/bin to your PATH:"
    echo ""
    echo '  export PATH="$HOME/.local/bin:$PATH"'
    echo ""
    warn "Then restart your shell and re-run this script."
else
    ok "ctools binary: $CTOOLS_BIN"
fi

# --- Step 4: Install slash command ---
info "Installing slash command /tools..."

if [[ -f "$SLASH_CMD_DST" ]] && [[ "$FORCE" != "true" ]]; then
    warn "$SLASH_CMD_DST already exists."
    read -rp "Overwrite? [y/N] " answer
    if [[ "${answer,,}" != "y" ]]; then
        info "Skipping slash command installation."
    else
        mkdir -p "$(dirname "$SLASH_CMD_DST")"
        cp "$SLASH_CMD_SRC" "$SLASH_CMD_DST"
        ok "Slash command updated: $SLASH_CMD_DST"
    fi
else
    mkdir -p "$(dirname "$SLASH_CMD_DST")"
    cp "$SLASH_CMD_SRC" "$SLASH_CMD_DST"
    ok "Slash command installed: $SLASH_CMD_DST"
fi

# --- Step 5: Smoke test ---
info "Running smoke test..."
if command -v ctools &>/dev/null; then
    RESOURCE_COUNT=$(ctools --mode inline 2>/dev/null | grep -c "●\|◆" || echo "0")
    ok "Smoke test passed — $RESOURCE_COUNT resources found"
else
    warn "Cannot run smoke test (ctools not on PATH yet)"
fi

# --- Recap ---
echo ""
echo -e "${BOLD}${GREEN}═══════════════════════════════════════${NC}"
echo -e "${BOLD}  ctools installation complete!${NC}"
echo -e "${BOLD}${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "  Binary:        ${CYAN}${CTOOLS_BIN:-~/.local/bin/ctools}${NC}"
echo -e "  Slash command:  ${CYAN}$SLASH_CMD_DST${NC}"
echo ""
echo -e "  ${BOLD}Usage:${NC}"
echo -e "    ${CYAN}ctools${NC}                 — TUI in current terminal"
echo -e "    ${CYAN}ctools --mode inline${NC}   — text report"
echo -e "    ${CYAN}/tools${NC}                 — from Claude Code (external terminal)"
echo -e "    ${CYAN}/tools inline${NC}          — from Claude Code (inline report)"
echo ""
