"""Tests for cctools.terminal — emulator detection."""

from __future__ import annotations

from unittest.mock import patch

from cctools.terminal import find_terminal_emulator


class TestFindTerminalEmulator:
    def test_returns_tuple_or_none(self):
        result = find_terminal_emulator()
        if result is not None:
            argv, name = result
            assert isinstance(argv, list)
            assert len(argv) > 0
            assert isinstance(name, str)

    def test_env_terminal_override(self, monkeypatch):
        """If $TERMINAL points to a real binary, it should be preferred."""
        monkeypatch.setenv("TERMINAL", "bash")  # bash exists everywhere
        result = find_terminal_emulator()
        assert result is not None
        argv, name = result
        assert "bash" in argv[0]

    def test_nonexistent_terminal_env(self, monkeypatch):
        """If $TERMINAL points to nonexistent binary, skip it."""
        monkeypatch.setenv("TERMINAL", "/nonexistent/terminal-xyz-fake")
        # Should still work (falls through to other terminals or None)
        result = find_terminal_emulator()
        # Result may be tuple or None, but should not crash
        assert result is None or isinstance(result, tuple)

    @patch("cctools.terminal.platform.system", return_value="Linux")
    @patch("cctools.terminal.shutil.which", return_value=None)
    def test_returns_none_when_no_terminal_found(self, mock_which, mock_system, monkeypatch):
        monkeypatch.delenv("TERMINAL", raising=False)
        result = find_terminal_emulator()
        assert result is None

    @patch("cctools.terminal.platform.system", return_value="Darwin")
    @patch("cctools.terminal.shutil.which")
    def test_macos_uses_osascript(self, mock_which, mock_system, monkeypatch):
        monkeypatch.delenv("TERMINAL", raising=False)
        mock_which.side_effect = lambda cmd: "/usr/bin/osascript" if cmd == "osascript" else None
        result = find_terminal_emulator()
        assert result is not None
        argv, name = result
        assert "osascript" in argv[0]
        assert name == "Terminal.app"

    @patch("cctools.terminal.platform.system", return_value="Darwin")
    @patch("cctools.terminal.shutil.which", return_value=None)
    def test_macos_no_osascript_returns_none(self, mock_which, mock_system, monkeypatch):
        monkeypatch.delenv("TERMINAL", raising=False)
        result = find_terminal_emulator()
        assert result is None
