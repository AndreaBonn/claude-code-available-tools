"""Tests for ctools.scanner — the core resource discovery engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from ctools.scanner import (
    Resource,
    _scan_claude_json_legacy,
    _scan_hooks,
    _scan_markdown_dir,
    _scan_mcp_servers,
    _scan_skills,
    claude_home,
    group_by_category,
    parse_frontmatter,
    project_root,
    scan_all,
)

FIXTURES = Path(__file__).parent / "fixtures"
HOME_CLAUDE = FIXTURES / "home-claude"
PROJECT_CLAUDE = FIXTURES / "project-claude"


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_basic(self):
        text = "---\nname: test-cmd\ndescription: A test command\n---\nBody here."
        meta, body = parse_frontmatter(text)
        assert meta["name"] == "test-cmd"
        assert meta["description"] == "A test command"
        assert body.strip() == "Body here."

    def test_missing_frontmatter(self):
        text = "No frontmatter here.\nJust plain text."
        meta, body = parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_malformed_no_closing_delimiter(self):
        text = "---\nname: broken\nno closing delimiter"
        meta, body = parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_quoted_values(self):
        text = "---\nname: \"quoted-name\"\ndescription: 'single quoted'\n---\nBody"
        meta, body = parse_frontmatter(text)
        assert meta["name"] == "quoted-name"
        assert meta["description"] == "single quoted"

    def test_comments_and_empty_lines(self):
        text = "---\nname: test\n# this is a comment\n\ndescription: desc\n---\nBody"
        meta, body = parse_frontmatter(text)
        assert meta["name"] == "test"
        assert meta["description"] == "desc"
        assert len(meta) == 2

    def test_colon_in_value(self):
        text = "---\nname: git:commit\ndescription: Run git commit: with message\n---\n"
        meta, body = parse_frontmatter(text)
        assert meta["name"] == "git:commit"
        assert meta["description"] == "Run git commit: with message"

    def test_empty_string(self):
        meta, body = parse_frontmatter("")
        assert meta == {}
        assert body == ""


# ---------------------------------------------------------------------------
# scan commands
# ---------------------------------------------------------------------------


class TestScanCommands:
    def test_scan_commands_with_fixtures(self):
        resources = _scan_markdown_dir(
            HOME_CLAUDE / "commands", category="commands", scope="global"
        )
        assert len(resources) == 3
        names = {r.name for r in resources}
        # with-fm.md has name in frontmatter
        assert "review-code" in names
        # namespace/cmd.md has name in frontmatter
        assert "git:status" in names

    def test_simple_command_uses_body_as_description(self):
        resources = _scan_markdown_dir(
            HOME_CLAUDE / "commands", category="commands", scope="global"
        )
        simple = [r for r in resources if r.name == "simple"][0]
        assert "simple command without frontmatter" in simple.description

    def test_command_with_frontmatter_has_extra(self):
        resources = _scan_markdown_dir(
            HOME_CLAUDE / "commands", category="commands", scope="global"
        )
        review = [r for r in resources if r.name == "review-code"][0]
        assert review.extra.get("model") == "claude-sonnet-4-6"
        assert "allowed-tools" in review.extra

    def test_nonexistent_dir_returns_empty(self):
        resources = _scan_markdown_dir(
            HOME_CLAUDE / "nonexistent", category="commands", scope="global"
        )
        assert resources == []


# ---------------------------------------------------------------------------
# scan skills
# ---------------------------------------------------------------------------


class TestScanSkills:
    def test_scan_valid_skill(self):
        resources = _scan_skills(HOME_CLAUDE / "skills", scope="global")
        assert len(resources) == 1
        assert resources[0].name == "pdf-worker"
        assert resources[0].category == "skills"

    def test_ignores_dir_without_skill_md(self):
        """empty-dir/ has no SKILL.md → must be skipped."""
        resources = _scan_skills(HOME_CLAUDE / "skills", scope="global")
        names = {r.name for r in resources}
        assert "empty-dir" not in names


# ---------------------------------------------------------------------------
# scan MCP servers
# ---------------------------------------------------------------------------


class TestScanMcp:
    def test_scan_mcp_from_settings(self):
        import json

        settings = json.loads((HOME_CLAUDE / "settings.json").read_text())
        resources = _scan_mcp_servers(
            settings["mcpServers"],
            scope="global",
            source=HOME_CLAUDE / "settings.json",
        )
        assert len(resources) == 2
        names = {r.name for r in resources}
        assert "github" in names
        assert "remote-api" in names

        # Check descriptions
        github = [r for r in resources if r.name == "github"][0]
        assert "[stdio]" in github.description
        assert "npx" in github.description

        remote = [r for r in resources if r.name == "remote-api"][0]
        assert "[http]" in remote.description
        assert "example.com" in remote.description

    def test_empty_servers_returns_empty(self):
        resources = _scan_mcp_servers({}, scope="global", source=Path("-"))
        assert resources == []

    def test_invalid_servers_type_returns_empty(self):
        resources = _scan_mcp_servers("not a dict", scope="global", source=Path("-"))  # type: ignore[arg-type]
        assert resources == []


# ---------------------------------------------------------------------------
# scan hooks
# ---------------------------------------------------------------------------


class TestScanHooks:
    def test_scan_hooks_expands_matcher_groups(self):
        """PreToolUse:Bash has 2 hook defs → must produce 2 resources."""
        import json

        settings = json.loads((HOME_CLAUDE / "settings.json").read_text())
        resources = _scan_hooks(
            settings["hooks"],
            scope="global",
            source=HOME_CLAUDE / "settings.json",
        )
        # 2 from PreToolUse:Bash + 1 from PostToolUse:*
        assert len(resources) == 3
        pre_bash = [r for r in resources if r.name == "PreToolUse:Bash"]
        assert len(pre_bash) == 2

    def test_hook_description_format(self):
        import json

        settings = json.loads((HOME_CLAUDE / "settings.json").read_text())
        resources = _scan_hooks(
            settings["hooks"],
            scope="global",
            source=HOME_CLAUDE / "settings.json",
        )
        for r in resources:
            assert r.description.startswith("[command]")


# ---------------------------------------------------------------------------
# scan claude.json legacy
# ---------------------------------------------------------------------------


class TestScanClaudeJsonLegacy:
    def test_scan_top_level_and_projects(self, legacy_claude_json: Path):
        resources = _scan_claude_json_legacy(legacy_claude_json)
        names = {r.name for r in resources}
        assert "global-legacy-server" in names
        assert "project-a-server" in names
        assert "project-b-server" in names

    def test_project_servers_have_location(self, legacy_claude_json: Path):
        resources = _scan_claude_json_legacy(legacy_claude_json)
        proj_a = [r for r in resources if r.name == "project-a-server"][0]
        assert proj_a.extra.get("location") == "/home/user/project-a"
        assert proj_a.scope == "project"

    def test_nonexistent_file_returns_empty(self):
        resources = _scan_claude_json_legacy(Path("/nonexistent/claude.json"))
        assert resources == []


# ---------------------------------------------------------------------------
# project_root
# ---------------------------------------------------------------------------


class TestProjectRoot:
    def test_walks_up_from_subdir(self):
        """subdir/ is inside project-claude which has .claude/ → should find it."""
        subdir = PROJECT_CLAUDE / "subdir"
        subdir.mkdir(exist_ok=True)
        root = project_root(start=subdir)
        assert root == PROJECT_CLAUDE.resolve()

    def test_returns_none_for_root(self, tmp_path: Path):
        """A directory with no .claude/ or .mcp.json ancestors returns None."""
        isolated = tmp_path / "isolated"
        isolated.mkdir()
        root = project_root(start=isolated)
        assert root is None


# ---------------------------------------------------------------------------
# claude_home
# ---------------------------------------------------------------------------


class TestClaudeHome:
    def test_respects_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        custom_dir = tmp_path / "custom-claude"
        custom_dir.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(custom_dir))
        assert claude_home() == custom_dir

    def test_default_is_dot_claude(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
        assert claude_home() == Path.home() / ".claude"


# ---------------------------------------------------------------------------
# scan_all integration
# ---------------------------------------------------------------------------


class TestScanAll:
    def test_scan_all_with_fixtures(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(HOME_CLAUDE))
        resources = scan_all(project_dir=PROJECT_CLAUDE)
        assert len(resources) > 0

        categories = {r.category for r in resources}
        assert "commands" in categories
        assert "agents" in categories
        assert "mcp" in categories

    def test_scan_all_returns_sorted(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(HOME_CLAUDE))
        resources = scan_all(project_dir=PROJECT_CLAUDE)

        # global should come before project within same category
        commands = [r for r in resources if r.category == "commands"]
        global_cmds = [r for r in commands if r.scope == "global"]
        project_cmds = [r for r in commands if r.scope == "project"]
        if global_cmds and project_cmds:
            first_global_idx = resources.index(global_cmds[0])
            first_project_idx = resources.index(project_cmds[0])
            assert first_global_idx < first_project_idx

    def test_scan_all_no_project_no_crash(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "empty"))
        resources = scan_all(project_dir=tmp_path / "nonexistent")
        # Should not crash, may have env vars
        assert isinstance(resources, list)

    def test_scan_all_malformed_json_no_crash(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        fake_home = tmp_path / "claude-home"
        fake_home.mkdir()
        (fake_home / "settings.json").write_text("{broken json!!!")
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(fake_home))
        resources = scan_all(project_dir=tmp_path / "no-project")
        assert isinstance(resources, list)


# ---------------------------------------------------------------------------
# group_by_category
# ---------------------------------------------------------------------------


class TestGroupByCategory:
    def test_all_categories_present(self):
        groups = group_by_category([])
        assert len(groups) == 6
        for key in ("commands", "agents", "skills", "mcp", "hooks", "env"):
            assert key in groups
            assert groups[key] == []

    def test_groups_resources_correctly(self):
        resources = [
            Resource(category="commands", name="a", scope="global", source=Path("-")),
            Resource(category="mcp", name="b", scope="project", source=Path("-")),
        ]
        groups = group_by_category(resources)
        assert len(groups["commands"]) == 1
        assert len(groups["mcp"]) == 1
        assert len(groups["agents"]) == 0
