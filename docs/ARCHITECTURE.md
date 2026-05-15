# Architecture

Technical documentation for cctools internals. For usage, see [README](../README.md).

## System Overview

Five modules with clear separation of concerns: CLI dispatch, filesystem discovery, and three display backends.

```mermaid
%%{init: {'theme': 'default'}}%%
graph LR
    classDef core fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef engine fill:#059669,stroke:#047857,color:#fff
    classDef data fill:#d97706,stroke:#b45309,color:#fff
    classDef ext fill:#6b7280,stroke:#4b5563,color:#fff

    cli["cli.py<br/>Entry Point"]:::core

    subgraph display["Display Backends"]
        direction TB
        tui["tui.py<br/>Textual TUI"]:::core
        inline_mod["inline.py<br/>Rich Report"]:::core
    end

    terminal["terminal.py<br/>Terminal Detection"]:::ext
    ext_term(["External Terminal"]):::ext

    scanner["scanner.py<br/>Discovery Engine"]:::engine

    subgraph config["Configuration Sources"]
        direction TB
        global_cfg["~/.claude/<br/>Global Config"]:::data
        project_cfg[".claude/<br/>Project Config"]:::data
    end

    cli --> tui
    cli --> inline_mod
    cli --> terminal
    terminal -.-> ext_term

    tui --> scanner
    inline_mod --> scanner

    scanner --> global_cfg
    scanner --> project_cfg
```

| Color | Meaning |
|-------|---------|
| Blue | Core modules (entry point, display) |
| Green | Discovery engine |
| Amber | Configuration data sources |
| Gray | External/platform-dependent |

## Scanner Discovery Flow

`scanner.scan_all()` reads from global and project configuration directories, plus extra sources (legacy files, environment variables). Each source produces `Resource` dataclass instances, merged into a single sorted list.

```mermaid
%%{init: {'theme': 'default'}}%%
graph TD
    classDef core fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef engine fill:#059669,stroke:#047857,color:#fff
    classDef data fill:#d97706,stroke:#b45309,color:#fff
    classDef ext fill:#6b7280,stroke:#4b5563,color:#fff

    scan_all["scan_all#40;#41;"]:::engine

    subgraph global_src["Global ~/.claude/"]
        g_content["commands/*.md<br/>agents/*.md<br/>skills/SKILL.md<br/>settings.json"]:::data
    end

    subgraph project_src["Project .claude/"]
        p_content["commands/*.md<br/>agents/*.md<br/>skills/SKILL.md<br/>settings.json"]:::data
    end

    extra_src["Extra Sources"]:::ext
    extra_detail[".mcp.json<br/>.claude.json #40;legacy#41;<br/>CLAUDE_* / ANTHROPIC_* env"]:::ext

    output["list#91;Resource#93;"]:::core

    scan_all --> global_src
    scan_all --> project_src
    scan_all --> extra_src
    extra_src --- extra_detail

    g_content --> output
    p_content --> output
    extra_detail --> output
```

From `settings.json`, the scanner extracts three resource types: MCP servers (`mcpServers`), hooks (`hooks`), and environment variables. The YAML frontmatter parser is built-in (no PyYAML dependency) and supports multiline scalars (`>`, `|`).

## CLI Mode Dispatch

`cli.py` routes to one of three display backends based on `--mode` flag or auto-detection. In auto mode, terminal width determines whether to launch the full TUI or fall back to inline text output.

```mermaid
sequenceDiagram
    participant user as User
    participant cli as cli.py
    participant scanner as scanner.py
    participant tui as tui.py
    participant inline_mod as inline.py
    participant terminal as terminal.py

    user->>cli: cctools --mode X

    alt mode = auto
        cli->>cli: Check terminal cols
        alt cols >= 80
            cli->>tui: CtoolsApp.run()
        else cols < 80
            cli->>inline_mod: inline.run()
        end
    else mode = tui
        cli->>tui: CtoolsApp.run()
    else mode = inline
        cli->>inline_mod: inline.run()
    else mode = external
        cli->>terminal: find_terminal_emulator()
        terminal-->>cli: argv prefix
        cli->>cli: subprocess.Popen cctools --mode tui
    end

    tui->>scanner: scan_all()
    scanner-->>tui: list of Resource
    Note over tui: Auto-refresh every 3s

    inline_mod->>scanner: scan_all()
    scanner-->>inline_mod: list of Resource
    inline_mod-->>user: Rich text output
```

The TUI uses Textual's `set_interval(3)` for periodic refresh. On each tick, it compares resource fingerprints (category, name, scope, source) and rebuilds the tree only when changes are detected.

## CI Pipeline

GitHub Actions runs on every push and PR to main, across a Python version matrix.

```mermaid
%%{init: {'theme': 'default'}}%%
graph LR
    classDef core fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef engine fill:#059669,stroke:#047857,color:#fff
    classDef data fill:#d97706,stroke:#b45309,color:#fff
    classDef ext fill:#6b7280,stroke:#4b5563,color:#fff

    trigger["Push / PR<br/>to main"]:::ext
    matrix["Matrix<br/>Python 3.10, 3.12, 3.13"]:::ext

    lint["Lint<br/>ruff check + format"]:::core
    test_step["Test<br/>pytest + coverage"]:::engine
    typecheck["Typecheck<br/>mypy"]:::core
    audit["Security<br/>pip-audit"]:::data
    badges["Badges<br/>main only"]:::data

    trigger --> matrix
    matrix --> lint
    lint --> test_step
    test_step --> typecheck
    typecheck --> audit
    audit -->|"main branch"| badges
```

Badge generation (test count, coverage percentage) runs only on the main branch and commits badge JSON files to the repository.
