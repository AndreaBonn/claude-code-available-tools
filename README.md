# ctools — Claude Code Tools Explorer

Interactive TUI and CLI tool to inspect all Claude Code resources: slash commands, subagents, skills, MCP servers, hooks, and environment variables.

## Features

- **TUI mode**: full-screen terminal UI with sidebar navigation, live filtering, auto-refresh
- **Inline mode**: colored text report printed to stdout
- **External mode**: opens TUI in a separate terminal window
- **Slash command `/tools`**: launch from within Claude Code sessions
- Scans both global (`~/.claude/`) and project-level (`.claude/`) configurations
- Visual scope badges: ● green (global) ◆ yellow (project)

## Installation

```bash
# From the repo root
./install.sh

# Or manually
pip install .
cp slash-command/tools.md ~/.claude/commands/tools.md
```

## Usage

```bash
# Auto mode (TUI if terminal is wide enough, else inline)
ctools

# Explicit modes
ctools --mode tui
ctools --mode inline
ctools --mode external
ctools --mode inline --filter mcp

# From Claude Code
/tools
/tools inline
/tools tui
/tools inline git
```

## Development

```bash
uv sync --dev
uv run pytest tests/ -v --cov=ctools
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Uninstall

```bash
pipx uninstall ctools        # or: pip uninstall ctools
rm -f ~/.claude/commands/tools.md
```

## Roadmap (post-v1)

- Edit resources from TUI (open `$EDITOR` on source file)
- MCP server health check (connection test + status display)
- Export report to JSON/YAML
- Memory files support (`CLAUDE.md` chain)
- Plugin/marketplace support
- `fzf` integration for inline mode
- Watch mode with OS notifications for new resources
