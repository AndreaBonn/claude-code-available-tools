"""Tests for cctools.scanner — the core resource discovery engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from cctools.scanner import (
    Resource,
    _description_from_body,
    _safe_read_json,
    _scan_claude_json_legacy,
    _scan_env_from_settings,
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

    def test_multiline_folded(self):
        """YAML ``>`` folds lines into a single string with spaces."""
        text = "---\nname: test\ndescription: >\n  Line one\n  line two\n  line three\n---\nBody"
        meta, body = parse_frontmatter(text)
        assert meta["name"] == "test"
        assert meta["description"] == "Line one line two line three"

    def test_multiline_literal(self):
        """YAML ``|`` preserves newlines."""
        text = "---\nname: test\ndescription: |\n  Line one\n  line two\n---\nBody"
        meta, body = parse_frontmatter(text)
        assert meta["description"] == "Line one\nline two"

    def test_multiline_folded_strip(self):
        """YAML ``>-`` should also work (strip trailing newline variant)."""
        text = "---\nname: test\ndescription: >-\n  Folded text\n  continues here\nmodel: sonnet\n---\n"
        meta, body = parse_frontmatter(text)
        assert meta["description"] == "Folded text continues here"
        assert meta["model"] == "sonnet"

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

    def test_hook_without_description_uses_type_command_format(self):
        import json

        settings = json.loads((HOME_CLAUDE / "settings.json").read_text())
        resources = _scan_hooks(
            settings["hooks"],
            scope="global",
            source=HOME_CLAUDE / "settings.json",
        )
        # validate.sh and audit.sh have no description → fallback format
        no_desc = [
            r for r in resources if "validate.sh" in r.description or "audit.sh" in r.description
        ]
        for r in no_desc:
            assert r.description.startswith("[command]")

    def test_hook_with_custom_description_uses_it(self):
        import json

        settings = json.loads((HOME_CLAUDE / "settings.json").read_text())
        resources = _scan_hooks(
            settings["hooks"],
            scope="global",
            source=HOME_CLAUDE / "settings.json",
        )
        log_hook = [r for r in resources if "Log all Bash" in r.description]
        assert len(log_hook) == 1
        assert log_hook[0].description == "Log all Bash commands to audit file"

    def test_hook_description_truncated_at_240(self):
        hooks = {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "x", "description": "D" * 300}],
                }
            ]
        }
        resources = _scan_hooks(hooks, scope="global", source=Path("-"))
        assert len(resources[0].description) == 240


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


# ---------------------------------------------------------------------------
# _safe_read_json edge cases
# ---------------------------------------------------------------------------


class TestSafeReadJson:
    def test_returns_none_for_json_array(self, tmp_path: Path):
        """Valid JSON but not a dict → must return None."""
        f = tmp_path / "array.json"
        f.write_text("[1, 2, 3]")
        assert _safe_read_json(f) is None

    def test_returns_dict_for_valid_json(self, tmp_path: Path):
        f = tmp_path / "ok.json"
        f.write_text('{"key": "value"}')
        result = _safe_read_json(f)
        assert result == {"key": "value"}

    def test_returns_none_for_nonexistent_file(self):
        assert _safe_read_json(Path("/nonexistent/file.json")) is None


# ---------------------------------------------------------------------------
# _description_from_body edge cases
# ---------------------------------------------------------------------------


class TestDescriptionFromBody:
    def test_returns_first_non_heading_line(self):
        body = "# Title\nActual description here\nMore text"
        assert _description_from_body(body) == "Actual description here"

    def test_returns_empty_for_only_headings(self):
        body = "# Title\n## Subtitle\n### Another"
        assert _description_from_body(body) == ""

    def test_returns_empty_for_empty_body(self):
        assert _description_from_body("") == ""

    def test_returns_empty_for_blank_lines_only(self):
        assert _description_from_body("\n\n  \n") == ""

    def test_truncates_to_max_len(self):
        body = "A" * 300
        assert len(_description_from_body(body, max_len=240)) == 240


# ---------------------------------------------------------------------------
# _scan_hooks malformed input edge cases
# ---------------------------------------------------------------------------


class TestScanHooksMalformed:
    def test_non_dict_input_returns_empty(self):
        assert _scan_hooks("not a dict", scope="global", source=Path("-")) == []

    def test_non_list_matcher_group_skipped(self):
        hooks = {"PreToolUse": "not a list"}
        assert _scan_hooks(hooks, scope="global", source=Path("-")) == []

    def test_non_dict_group_skipped(self):
        hooks = {"PreToolUse": ["not a dict"]}
        assert _scan_hooks(hooks, scope="global", source=Path("-")) == []

    def test_non_list_hook_defs_wrapped(self):
        """Single hook def (not in list) should be wrapped."""
        hooks = {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": {"type": "command", "command": "echo test"},
                }
            ]
        }
        resources = _scan_hooks(hooks, scope="global", source=Path("-"))
        assert len(resources) == 1

    def test_non_dict_hook_def_skipped(self):
        hooks = {"PreToolUse": [{"matcher": "Bash", "hooks": ["not a dict"]}]}
        assert _scan_hooks(hooks, scope="global", source=Path("-")) == []


# ---------------------------------------------------------------------------
# _scan_mcp_servers edge cases
# ---------------------------------------------------------------------------


class TestScanMcpEdgeCases:
    def test_server_with_non_dict_config_skipped(self):
        servers = {"good": {"type": "stdio", "command": "test"}, "bad": "not a dict"}
        resources = _scan_mcp_servers(servers, scope="global", source=Path("-"))
        assert len(resources) == 1
        assert resources[0].name == "good"


# ---------------------------------------------------------------------------
# _scan_env_from_settings edge cases
# ---------------------------------------------------------------------------


class TestScanEnvEdgeCases:
    def test_non_dict_returns_empty(self):
        assert _scan_env_from_settings("not a dict", scope="global", source=Path("-")) == []

    def test_extracts_env_vars(self):
        env = {"FOO": "bar", "BAZ": "123"}
        resources = _scan_env_from_settings(env, scope="global", source=Path("-"))
        assert len(resources) == 2
        names = {r.name for r in resources}
        assert names == {"FOO", "BAZ"}


# ---------------------------------------------------------------------------
# _scan_skills edge cases
# ---------------------------------------------------------------------------


class TestScanSkillsEdgeCases:
    def test_oserror_on_iterdir_returns_empty(self, tmp_path: Path, monkeypatch):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        monkeypatch.setattr(Path, "iterdir", lambda self: (_ for _ in ()).throw(OSError("perm")))
        resources = _scan_skills(skills_dir, scope="global")
        assert resources == []


# ---------------------------------------------------------------------------
# _scan_markdown_dir edge cases
# ---------------------------------------------------------------------------


class TestScanMarkdownEdgeCases:
    def test_oserror_on_rglob_returns_empty(self, tmp_path: Path, monkeypatch):
        cmd_dir = tmp_path / "commands"
        cmd_dir.mkdir()
        monkeypatch.setattr(Path, "rglob", lambda self, pat: (_ for _ in ()).throw(OSError("perm")))
        resources = _scan_markdown_dir(cmd_dir, category="commands", scope="global")
        assert resources == []

    def test_unreadable_file_skipped(self, tmp_path: Path):
        cmd_dir = tmp_path / "commands"
        cmd_dir.mkdir()
        md = cmd_dir / "test.md"
        md.write_text("content")
        md.chmod(0o000)
        resources = _scan_markdown_dir(cmd_dir, category="commands", scope="global")
        # File unreadable → skipped (or read if running as root)
        assert isinstance(resources, list)
        md.chmod(0o644)  # cleanup


# ---------------------------------------------------------------------------
# project_root — home dir skip
# ---------------------------------------------------------------------------


class TestProjectRootHomeSkip:
    def test_skips_home_dir_claude(self, tmp_path: Path, monkeypatch):
        """If .claude/ exists in home dir, project_root should skip it."""
        fake_home = tmp_path / "fakehome"
        fake_home.mkdir()
        (fake_home / ".claude").mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
        # Start search from home — should NOT match home itself
        result = project_root(start=fake_home)
        assert result is None
