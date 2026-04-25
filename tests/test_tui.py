"""Smoke tests for ctools.tui — verifies widget composition."""

from __future__ import annotations

import pytest

from ctools.tui import CtoolsApp, DetailPanel, SidebarTree


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
