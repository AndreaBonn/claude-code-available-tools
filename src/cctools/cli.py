"""CLI entry point — dispatches to inline, tui, or external mode."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

from cctools import inline, terminal

logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="cctools",
        description="Interactive explorer for Claude Code tools and configuration.",
    )
    parser.add_argument(
        "--mode",
        choices=["tui", "inline", "external", "auto"],
        default="auto",
        help="Display mode (default: auto)",
    )
    parser.add_argument(
        "--filter",
        default="",
        help="Filter resources by name/description substring",
    )
    parser.add_argument(
        "--from-slash",
        action="store_true",
        help="Indicates launch from /tools slash command",
    )
    return parser.parse_args(argv)


def _should_use_tui() -> bool:
    """Determine if TUI mode is appropriate for the current terminal."""
    if not sys.stdout.isatty():
        return False
    try:
        columns = os.get_terminal_size().columns
        return columns >= 80
    except OSError:
        return False


def _launch_external(args: argparse.Namespace) -> int:
    """Spawn a new terminal window running cctools in TUI mode."""
    result = terminal.find_terminal_emulator()
    if result is None:
        print(
            "No terminal emulator found. Falling back to inline mode.",
            file=sys.stderr,
        )
        return inline.run(
            filter_term=args.filter,
            from_slash=args.from_slash,
        )

    argv_prefix, name = result
    cmd = ["cctools", "--mode", "tui"]
    if args.filter:
        cmd.extend(["--filter", args.filter])
    if args.from_slash:
        cmd.append("--from-slash")

    # gnome-terminal uses bash -lc "cmd" — join as single string
    if "bash" in argv_prefix and "-lc" in argv_prefix:
        full_cmd = argv_prefix + [" ".join(cmd)]
    else:
        full_cmd = argv_prefix + cmd

    logger.info("Launching %s: %s", name, full_cmd)
    try:
        subprocess.Popen(full_cmd)  # noqa: S603
        print(f"Opened cctools in {name}.")
    except OSError as exc:
        print(f"Failed to launch {name}: {exc}", file=sys.stderr)
        return inline.run(
            filter_term=args.filter,
            from_slash=args.from_slash,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point.

    Parameters
    ----------
    argv : list[str] | None
        Command-line arguments (for testing). None = sys.argv.

    Returns
    -------
    int
        Exit code.
    """
    args = _parse_args(argv)

    if args.mode == "auto":
        args.mode = "tui" if _should_use_tui() else "inline"

    if args.mode == "inline":
        return inline.run(
            filter_term=args.filter,
            from_slash=args.from_slash,
        )

    if args.mode == "tui":
        from cctools import tui  # lazy import — keeps startup fast when not needed

        return tui.run(
            filter_term=args.filter,
            from_slash=args.from_slash,
        )

    if args.mode == "external":
        return _launch_external(args)

    return 2
