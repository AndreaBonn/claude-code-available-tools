"""Tests for cctools.inline — text report renderer."""

from __future__ import annotations

from pathlib import Path

import pytest

from cctools.inline import render
from cctools.scanner import Resource, scan_all

FIXTURES = Path(__file__).parent / "fixtures"
HOME_CLAUDE = FIXTURES / "home-claude"
PROJECT_CLAUDE = FIXTURES / "project-claude"


@pytest.fixture()
def sample_resources() -> list[Resource]:
    return [
        Resource(
            category="commands",
            name="review-code",
            scope="global",
            source=Path("/fake/review.md"),
            description="Review code for quality",
        ),
        Resource(
            category="commands",
            name="deploy",
            scope="project",
            source=Path("/fake/deploy.md"),
            description="Deploy to staging",
        ),
        Resource(
            category="mcp",
            name="github-server",
            scope="global",
            source=Path("/fake/settings.json"),
            description="[stdio] npx @mcp/server-github",
        ),
        Resource(
            category="agents",
            name="code-reviewer",
            scope="global",
            source=Path("/fake/reviewer.md"),
            description="Expert code review",
        ),
    ]


class TestRender:
    def test_contains_header(self, sample_resources: list[Resource]):
        output = render(resources=sample_resources)
        plain = output.plain
        assert "Claude Code — Available Tools" in plain

    def test_contains_all_category_labels(self, sample_resources: list[Resource]):
        output = render(resources=sample_resources)
        plain = output.plain
        assert "Slash Commands" in plain
        assert "Subagents" in plain
        assert "MCP Servers" in plain
        # Empty categories shown with (0)
        assert "Skills" in plain
        assert "Hooks" in plain
        assert "Env Variables" in plain

    def test_shows_resource_names(self, sample_resources: list[Resource]):
        output = render(resources=sample_resources)
        plain = output.plain
        assert "review-code" in plain
        assert "deploy" in plain
        assert "github-server" in plain

    def test_shows_scope_badges(self, sample_resources: list[Resource]):
        output = render(resources=sample_resources)
        plain = output.plain
        assert "●" in plain  # global badge
        assert "◆" in plain  # project badge

    def test_shows_total_count(self, sample_resources: list[Resource]):
        output = render(resources=sample_resources)
        plain = output.plain
        assert "Total: 4 resources" in plain

    def test_filter_narrows_results(self, sample_resources: list[Resource]):
        output = render(resources=sample_resources, filter_term="deploy")
        plain = output.plain
        assert "deploy" in plain
        assert "review-code" not in plain
        assert "Total: 1 resources" in plain

    def test_filter_case_insensitive(self, sample_resources: list[Resource]):
        output = render(resources=sample_resources, filter_term="REVIEW")
        plain = output.plain
        assert "review-code" in plain
        assert "code-reviewer" in plain

    def test_empty_resources(self):
        output = render(resources=[])
        plain = output.plain
        assert "Total: 0 resources" in plain
        assert "(0)" in plain

    def test_description_truncated_to_100(self):
        long_desc = "A" * 200
        resources = [
            Resource(
                category="commands",
                name="long-desc",
                scope="global",
                source=Path("-"),
                description=long_desc,
            )
        ]
        output = render(resources=resources)
        plain = output.plain
        # Description truncated to 100
        assert "A" * 101 not in plain
        assert "A" * 100 in plain

    def test_filter_on_description(self, sample_resources: list[Resource]):
        output = render(resources=sample_resources, filter_term="staging")
        plain = output.plain
        assert "deploy" in plain
        assert "Total: 1 resources" in plain

    def test_with_fixture_scan(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(HOME_CLAUDE))
        resources = scan_all(project_dir=PROJECT_CLAUDE)
        output = render(resources=resources)
        plain = output.plain
        assert "Total:" in plain
        assert "Slash Commands" in plain

    def test_render_without_resources_calls_scan_all(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(HOME_CLAUDE))
        output = render(resources=None, project_dir=PROJECT_CLAUDE)
        plain = output.plain
        assert "Total:" in plain


class TestRun:
    def test_run_returns_zero(self, monkeypatch: pytest.MonkeyPatch):
        from cctools.inline import run

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(HOME_CLAUDE))
        result = run(project_dir=PROJECT_CLAUDE)
        assert result == 0

    def test_run_with_from_slash(self, monkeypatch: pytest.MonkeyPatch):
        from cctools.inline import run

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(HOME_CLAUDE))
        result = run(from_slash=True, project_dir=PROJECT_CLAUDE)
        assert result == 0

    def test_run_with_filter(self, monkeypatch: pytest.MonkeyPatch):
        from cctools.inline import run

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(HOME_CLAUDE))
        result = run(filter_term="mcp", project_dir=PROJECT_CLAUDE)
        assert result == 0
