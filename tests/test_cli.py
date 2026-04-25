"""Tests for cctools.cli — argument parsing and mode dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cctools.cli import _launch_external, _parse_args, _should_use_tui, main


class TestParseArgs:
    def test_default_mode_is_auto(self):
        args = _parse_args([])
        assert args.mode == "auto"
        assert args.filter == ""
        assert args.from_slash is False

    def test_inline_mode(self):
        args = _parse_args(["--mode", "inline"])
        assert args.mode == "inline"

    def test_filter_flag(self):
        args = _parse_args(["--filter", "mcp"])
        assert args.filter == "mcp"

    def test_from_slash_flag(self):
        args = _parse_args(["--from-slash"])
        assert args.from_slash is True

    def test_combined_flags(self):
        args = _parse_args(["--mode", "external", "--filter", "git", "--from-slash"])
        assert args.mode == "external"
        assert args.filter == "git"
        assert args.from_slash is True


class TestShouldUseTui:
    def test_returns_bool(self):
        result = _should_use_tui()
        assert isinstance(result, bool)

    def test_returns_false_when_not_tty(self, monkeypatch):
        monkeypatch.setattr("sys.stdout.isatty", lambda: False)
        assert _should_use_tui() is False

    def test_returns_false_on_narrow_terminal(self, monkeypatch):
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        monkeypatch.setattr("os.get_terminal_size", lambda *a, **kw: MagicMock(columns=40))
        assert _should_use_tui() is False

    def test_returns_true_on_wide_tty(self, monkeypatch):
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        monkeypatch.setattr("os.get_terminal_size", lambda *a, **kw: MagicMock(columns=120))
        assert _should_use_tui() is True

    def test_returns_false_on_oserror(self, monkeypatch):
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)

        def _raise_os_error(*a, **kw):
            raise OSError("no terminal")

        monkeypatch.setattr("os.get_terminal_size", _raise_os_error)
        assert _should_use_tui() is False


class TestMain:
    @patch("cctools.cli.inline")
    def test_inline_mode_calls_inline_run(self, mock_inline):
        mock_inline.run.return_value = 0
        result = main(["--mode", "inline"])
        assert result == 0
        mock_inline.run.assert_called_once_with(filter_term="", from_slash=False)

    @patch("cctools.cli.inline")
    def test_inline_mode_passes_filter(self, mock_inline):
        mock_inline.run.return_value = 0
        main(["--mode", "inline", "--filter", "hooks", "--from-slash"])
        mock_inline.run.assert_called_once_with(filter_term="hooks", from_slash=True)

    @patch("cctools.cli._launch_external")
    def test_external_mode_calls_launch_external(self, mock_launch):
        mock_launch.return_value = 0
        result = main(["--mode", "external"])
        assert result == 0
        mock_launch.assert_called_once()

    @patch("cctools.cli.inline")
    @patch("cctools.cli._should_use_tui", return_value=False)
    def test_auto_mode_falls_back_to_inline(self, mock_tui_check, mock_inline):
        mock_inline.run.return_value = 0
        result = main(["--mode", "auto"])
        assert result == 0
        mock_inline.run.assert_called_once()


class TestLaunchExternal:
    @patch("cctools.cli.terminal")
    @patch("cctools.cli.inline")
    def test_falls_back_to_inline_when_no_terminal(self, mock_inline, mock_terminal):
        mock_terminal.find_terminal_emulator.return_value = None
        mock_inline.run.return_value = 0
        args = _parse_args(["--mode", "external"])
        result = _launch_external(args)
        assert result == 0
        mock_inline.run.assert_called_once()

    @patch("cctools.cli.subprocess.Popen")
    @patch("cctools.cli.terminal")
    def test_launches_terminal_successfully(self, mock_terminal, mock_popen):
        mock_terminal.find_terminal_emulator.return_value = (["xterm", "-e"], "XTerm")
        args = _parse_args(["--mode", "external"])
        result = _launch_external(args)
        assert result == 0
        mock_popen.assert_called_once()

    @patch("cctools.cli.subprocess.Popen", side_effect=OSError("spawn failed"))
    @patch("cctools.cli.terminal")
    @patch("cctools.cli.inline")
    def test_falls_back_on_popen_error(self, mock_inline, mock_terminal, mock_popen):
        mock_terminal.find_terminal_emulator.return_value = (["xterm", "-e"], "XTerm")
        mock_inline.run.return_value = 0
        args = _parse_args(["--mode", "external"])
        result = _launch_external(args)
        assert result == 0
        mock_inline.run.assert_called_once()

    @patch("cctools.cli.subprocess.Popen")
    @patch("cctools.cli.terminal")
    def test_gnome_terminal_joins_command(self, mock_terminal, mock_popen):
        mock_terminal.find_terminal_emulator.return_value = (
            ["gnome-terminal", "--", "bash", "-lc"],
            "GNOME Terminal",
        )
        args = _parse_args(["--mode", "external", "--filter", "mcp"])
        _launch_external(args)
        call_args = mock_popen.call_args[0][0]
        # gnome-terminal path: last element is joined command string
        assert isinstance(call_args[-1], str)
        assert "cctools" in call_args[-1]
        assert "--filter" in call_args[-1]

    @patch("cctools.cli.subprocess.Popen")
    @patch("cctools.cli.terminal")
    def test_from_slash_appended_to_command(self, mock_terminal, mock_popen):
        mock_terminal.find_terminal_emulator.return_value = (["xterm", "-e"], "XTerm")
        args = _parse_args(["--mode", "external", "--from-slash"])
        _launch_external(args)
        call_args = mock_popen.call_args[0][0]
        assert "--from-slash" in call_args

    def test_tui_mode_calls_tui_run(self):
        with patch("cctools.tui.run", return_value=0) as mock_run:
            result = main(["--mode", "tui"])
            assert result == 0
            mock_run.assert_called_once_with(filter_term="", from_slash=False)
