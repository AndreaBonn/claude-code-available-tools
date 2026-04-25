"""Terminal emulator detection — finds available terminal to spawn external TUI."""

from __future__ import annotations

import os
import platform
import shutil

# (check_cmd, argv_prefix, friendly_name)
_LINUX_TERMINALS: list[tuple[str, list[str], str]] = [
    ("gnome-terminal", ["gnome-terminal", "--", "bash", "-lc"], "GNOME Terminal"),
    ("konsole", ["konsole", "-e"], "Konsole"),
    ("xfce4-terminal", ["xfce4-terminal", "-x"], "XFCE4 Terminal"),
    ("x-terminal-emulator", ["x-terminal-emulator", "-e"], "x-terminal-emulator"),
    ("xterm", ["xterm", "-e"], "XTerm"),
]


def find_terminal_emulator() -> tuple[list[str], str] | None:
    """Find an available terminal emulator to launch a command in.

    Returns
    -------
    tuple[list[str], str] | None
        (argv_prefix, friendly_name) to prepend before the target command,
        or None if no emulator is found.
        The argv_prefix is meant to be extended with ``['cctools', '--mode', 'tui']``.
    """
    # 1. $TERMINAL env var
    env_term = os.environ.get("TERMINAL")
    if env_term and shutil.which(env_term):
        return [env_term, "-e"], env_term

    # 2. Linux terminals
    if platform.system() != "Darwin":
        for cmd, argv, name in _LINUX_TERMINALS:
            if shutil.which(cmd):
                return argv, name

    # 3. macOS: use osascript + Terminal.app
    # NOTE: The command appended to this argv_prefix is built entirely from
    # internal constants in cli.py (["cctools", "--mode", "tui", ...]).
    # Do NOT pass user-supplied strings through this osascript path without
    # proper escaping — AppleScript concatenation is injection-prone.
    if platform.system() == "Darwin":
        if shutil.which("osascript"):
            return (
                [
                    "osascript",
                    "-e",
                    'tell application "Terminal" to do script',
                ],
                "Terminal.app",
            )

    return None
