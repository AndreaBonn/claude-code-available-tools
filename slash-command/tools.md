---
name: tools
description: Open the Claude Code tools explorer (ctools). Shows all configured slash commands, subagents, skills, MCP servers, hooks, and env variables from ~/.claude and the current project.
argument-hint: [external|tui|inline] [filter_term]
allowed-tools: Bash(ctools:*)
---

Open the ctools explorer based on the argument provided.

The first argument (if present) selects the mode:
- `external` (default): open the TUI in a new terminal window, leaving this chat intact
- `tui`: open the TUI in the current terminal (Claude Code will be suspended until you quit with `q`)
- `inline`: print a static text report directly in this chat

The second argument (if present) is a filter term passed to ctools.

Arguments received: $ARGUMENTS

Execute:

```bash
MODE="${1:-external}"
FILTER="${2:-}"
if [ -n "$FILTER" ]; then
  ctools --mode "$MODE" --filter "$FILTER" --from-slash
else
  ctools --mode "$MODE" --from-slash
fi
```

If `ctools` is not found on PATH, tell the user to run the installer:
`cd ~/ctools-project && ./install.sh` or install with `pip install .` from the ctools repo.

If mode is `external` and the command reports "no terminal emulator found", suggest retrying with `/tools tui` or `/tools inline`.
