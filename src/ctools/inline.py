"""Inline renderer — prints a colored text report of all Claude Code resources."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

from ctools.scanner import (
    CATEGORIES,
    Resource,
    claude_home,
    group_by_category,
    project_root,
    scan_all,
)

# Scope badges
_BADGE_GLOBAL = ("● ", "green")
_BADGE_PROJECT = ("◆ ", "yellow")


def _scope_badge(scope: str) -> tuple[str, str]:
    """Return (symbol, color) for a scope."""
    return _BADGE_GLOBAL if scope == "global" else _BADGE_PROJECT


def render(
    resources: list[Resource] | None = None,
    filter_term: str = "",
    project_dir: Path | None = None,
) -> Text:
    """Build a Rich Text object with the full resource report.

    Parameters
    ----------
    resources : list[Resource] | None
        Pre-scanned resources. If None, calls scan_all().
    filter_term : str
        Substring filter (case-insensitive) on name and description.
    project_dir : Path | None
        Project root for scanning.

    Returns
    -------
    rich.text.Text
        Styled text ready for Console.print().
    """
    if resources is None:
        resources = scan_all(project_dir=project_dir)

    # Apply filter
    if filter_term:
        term = filter_term.lower()
        resources = [
            r for r in resources if term in r.name.lower() or term in r.description.lower()
        ]

    groups = group_by_category(resources)
    home = claude_home()
    proj = project_dir or project_root()

    output = Text()
    output.append("Claude Code — Available Tools\n", style="bold cyan")
    output.append(f"Config: {home}\n", style="dim")
    if proj:
        output.append(f"Project: {proj}\n", style="dim")
    if filter_term:
        output.append(f'Filter: "{filter_term}"\n', style="dim italic")
    output.append("\n")

    total = 0
    for cat_id, cat_label, cat_icon in CATEGORIES:
        cat_resources = groups.get(cat_id, [])
        count = len(cat_resources)
        total += count

        # Category header
        if count > 0:
            output.append(f"{cat_icon} {cat_label} ", style="bold")
            output.append(f"({count})\n", style="bold")
        else:
            output.append(f"{cat_icon} {cat_label} ", style="dim")
            output.append("(0)\n", style="dim")
            continue

        # Resources
        for r in cat_resources:
            badge_sym, badge_color = _scope_badge(r.scope)
            output.append("  ")
            output.append(badge_sym, style=badge_color)
            output.append(r.name, style="bold white")

            desc = r.description[:100]
            if desc:
                output.append(f"  {desc}", style="dim")

            output.append(f"\n    {r.source}\n", style="dim italic")

        output.append("\n")

    # Footer
    output.append(f"Total: {total} resources\n", style="bold")

    return output


def run(
    filter_term: str = "",
    from_slash: bool = False,
    project_dir: Path | None = None,
) -> int:
    """Entry point for inline mode.

    Parameters
    ----------
    filter_term : str
        Optional filter term.
    from_slash : bool
        If True, add a tip footer about /tools modes.
    project_dir : Path | None
        Explicit project root.

    Returns
    -------
    int
        Exit code (always 0).
    """
    use_color = sys.stdout.isatty()
    console = Console(force_terminal=use_color, highlight=False)

    output = render(filter_term=filter_term, project_dir=project_dir)
    console.print(output)

    if from_slash:
        console.print("[dim]Tip: use `/tools external` or `/tools tui` to change mode.[/dim]")

    return 0
