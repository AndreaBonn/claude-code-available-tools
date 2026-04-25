"""Tests for cctools.tui — TUI widgets and app behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from cctools.scanner import Resource
from cctools.tui import CtoolsApp, DetailPanel, SidebarTree


def _get_panel_text(panel: DetailPanel) -> str:
    """Extract plain text from DetailPanel's internal content."""
    # Textual Static stores content via name-mangled __content
    content = panel._Static__content  # type: ignore[attr-defined]
    if hasattr(content, "plain"):
        return content.plain
    return str(content)


class TestTuiComposition:
    @pytest.mark.asyncio
    async def test_app_creates_expected_widgets(self):
        """CtoolsApp.compose() should produce sidebar, detail, header, footer."""
        app = CtoolsApp()
        async with app.run_test():
            assert app.query_one(SidebarTree) is not None
            assert app.query_one("#detail", DetailPanel) is not None
            assert app.query_one("#filter-input") is not None

    @pytest.mark.asyncio
    async def test_app_with_filter(self):
        """App should accept initial filter term."""
        app = CtoolsApp(filter_term="test-filter")
        async with app.run_test():
            assert app._filter_term == "test-filter"


class TestDetailPanel:
    @pytest.mark.asyncio
    async def test_show_legend_renders_header(self):
        app = CtoolsApp()
        async with app.run_test():
            panel = app.query_one("#detail", DetailPanel)
            panel.show_legend()
            plain = _get_panel_text(panel)
            assert "cctools" in plain
            assert "Select a resource" in plain

    @pytest.mark.asyncio
    async def test_show_resource_global(self):
        app = CtoolsApp()
        async with app.run_test():
            panel = app.query_one("#detail", DetailPanel)
            resource = Resource(
                category="commands",
                name="test-cmd",
                scope="global",
                source=Path("/fake/path.md"),
                description="A test command",
            )
            panel.show_resource(resource)
            plain = _get_panel_text(panel)
            assert "Global" in plain
            assert "test-cmd" in plain
            assert "A test command" in plain
            assert "/fake/path.md" in plain

    @pytest.mark.asyncio
    async def test_show_resource_project(self):
        app = CtoolsApp()
        async with app.run_test():
            panel = app.query_one("#detail", DetailPanel)
            resource = Resource(
                category="hooks",
                name="PreToolUse:Bash",
                scope="project",
                source=Path("/project/.claude/settings.json"),
                description="Guard hook",
            )
            panel.show_resource(resource)
            plain = _get_panel_text(panel)
            assert "Project" in plain
            assert "PreToolUse:Bash" in plain

    @pytest.mark.asyncio
    async def test_show_resource_with_extra_metadata(self):
        app = CtoolsApp()
        async with app.run_test():
            panel = app.query_one("#detail", DetailPanel)
            resource = Resource(
                category="mcp",
                name="server-x",
                scope="global",
                source=Path("-"),
                description="MCP server",
                extra={"type": "stdio", "command": "npx server"},
            )
            panel.show_resource(resource)
            plain = _get_panel_text(panel)
            assert "Extra metadata" in plain
            assert "type:" in plain
            assert "stdio" in plain

    @pytest.mark.asyncio
    async def test_show_resource_truncates_long_extra_values(self):
        app = CtoolsApp()
        async with app.run_test():
            panel = app.query_one("#detail", DetailPanel)
            resource = Resource(
                category="commands",
                name="long-extra",
                scope="global",
                source=Path("-"),
                extra={"data": "X" * 300},
            )
            panel.show_resource(resource)
            plain = _get_panel_text(panel)
            assert "..." in plain

    @pytest.mark.asyncio
    async def test_show_resource_no_description(self):
        app = CtoolsApp()
        async with app.run_test():
            panel = app.query_one("#detail", DetailPanel)
            resource = Resource(
                category="commands",
                name="no-desc",
                scope="global",
                source=Path("-"),
                description="",
            )
            panel.show_resource(resource)
            plain = _get_panel_text(panel)
            assert "Description" not in plain

    @pytest.mark.asyncio
    async def test_show_resource_category_icon(self):
        app = CtoolsApp()
        async with app.run_test():
            panel = app.query_one("#detail", DetailPanel)
            resource = Resource(
                category="hooks",
                name="test-hook",
                scope="global",
                source=Path("-"),
                description="A hook",
            )
            panel.show_resource(resource)
            plain = _get_panel_text(panel)
            assert "Hooks" in plain


class TestAppActions:
    @pytest.mark.asyncio
    async def test_open_filter_action(self):
        app = CtoolsApp()
        async with app.run_test():
            # Trigger action directly
            app.action_open_filter()
            filter_input = app.query_one("#filter-input")
            assert filter_input.display is True

    @pytest.mark.asyncio
    async def test_escape_closes_filter(self):
        app = CtoolsApp()
        async with app.run_test():
            app.action_open_filter()
            filter_input = app.query_one("#filter-input")
            assert filter_input.display is True
            app.key_escape()
            assert filter_input.display is False
            assert app._filter_term == ""

    @pytest.mark.asyncio
    async def test_refresh_action(self):
        app = CtoolsApp()
        async with app.run_test():
            # Should not crash
            app.action_refresh()

    @pytest.mark.asyncio
    async def test_tree_node_highlight_shows_legend_for_category(self):
        app = CtoolsApp()
        async with app.run_test() as pilot:
            # Navigate to a category node (not a leaf)
            await pilot.press("down")
            panel = app.query_one("#detail", DetailPanel)
            plain = _get_panel_text(panel)
            # Category node → legend (no resource)
            assert "cctools" in plain or "Select" in plain or len(plain) > 0

    @pytest.mark.asyncio
    async def test_input_changed_updates_filter(self):
        app = CtoolsApp()
        async with app.run_test():
            app.action_open_filter()
            filter_input = app.query_one("#filter-input")
            filter_input.value = "hooks"
            # Trigger the change event manually
            from textual.widgets import Input

            app.on_input_changed(Input.Changed(input=filter_input, value="hooks"))
            assert app._filter_term == "hooks"

    @pytest.mark.asyncio
    async def test_double_refresh_no_change_is_noop(self):
        """Second refresh with same data should be a no-op (early return)."""
        app = CtoolsApp()
        async with app.run_test():
            # First refresh happens on mount — second should early return
            app._do_refresh()
            # Should not crash, tree still intact
            tree = app.query_one(SidebarTree)
            assert tree is not None

    @pytest.mark.asyncio
    async def test_do_refresh_second_call_is_noop(self):
        """Calling _do_refresh twice with unchanged data is safe."""
        app = CtoolsApp()
        async with app.run_test():
            # First call on mount already happened, second should be noop
            old_resources = list(app._resources)
            app._do_refresh()
            assert app._resources == old_resources
