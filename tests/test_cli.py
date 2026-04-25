"""Tests for ctools.cli — argument parsing and mode dispatch."""

from __future__ import annotations

from ctools.cli import _parse_args, _should_use_tui


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
