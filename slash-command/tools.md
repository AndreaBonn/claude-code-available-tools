---
name: tools
description: Open the Claude Code tools explorer (cctools). Shows all configured slash commands, subagents, skills, MCP servers, hooks, and env variables from ~/.claude and the current project.
argument-hint: "[external|tui|inline] [filter_term]"
allowed-tools: "Bash(cctools:*)"
---

Open the cctools explorer based on the argument provided.

The first argument (if present) selects the mode:
- `external` (default): open the TUI in a new terminal window, leaving this chat intact
- `tui`: open the TUI in the current terminal (Claude Code will be suspended until you quit with `q`)
- `inline`: print a static text report directly in this chat

The second argument (if present) is a filter term passed to cctools.

Arguments received: $ARGUMENTS

Execute:

```bash
MODE="${1:-external}"
FILTER="${2:-}"
if [ -n "$FILTER" ]; then
  cctools --mode "$MODE" --filter "$FILTER" --from-slash
else
  cctools --mode "$MODE" --from-slash
fi
```

If `cctools` is not found on PATH, tell the user to run the installer:
`cd <repo-dir> && ./install.sh` or install with `pip install .` from the cc-available-tools repo.

If mode is `external` and the command reports "no terminal emulator found", suggest retrying with `/tools tui` or `/tools inline`.
