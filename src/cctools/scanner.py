"""Scanner module — discovers all Claude Code resources from global and project scope.

This module is pure logic with isolated I/O: every filesystem or JSON operation
is wrapped in try/except so that scan_all() never propagates exceptions.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category metadata
# ---------------------------------------------------------------------------

CATEGORIES: list[tuple[str, str, str]] = [
    ("commands", "Slash Commands", "⌘"),
    ("agents", "Subagents", "◈"),
    ("skills", "Skills", "★"),
    ("mcp", "MCP Servers", "⚡"),
    ("hooks", "Hooks", "⎇"),
    ("env", "Env Variables", "$"),
]

CATEGORY_ORDER: dict[str, int] = {cat_id: idx for idx, (cat_id, _, _) in enumerate(CATEGORIES)}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Resource:
    """A single discovered Claude Code resource."""

    category: str
    name: str
    scope: str  # "global" | "project"
    source: Path
    description: str = ""
    extra: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def claude_home() -> Path:
    """Return the Claude config home, respecting CLAUDE_CONFIG_DIR."""
    env_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path.home() / ".claude"


def project_root(start: Path | None = None) -> Path | None:
    """Walk up from *start* looking for `.claude/` dir or `.mcp.json` file.

    The user's home directory is excluded because ``~/.claude/`` is the global
    config dir, not a project.

    Returns
    -------
    Path | None
        The project root directory, or None if not found.
    """
    current = (start or Path.cwd()).resolve()
    home = Path.home().resolve()
    for directory in [current, *current.parents]:
        # Skip home dir — ~/.claude/ is global config, not a project
        if directory == home:
            continue
        if (directory / ".claude").is_dir() or (directory / ".mcp.json").is_file():
            return directory
    return None


# ---------------------------------------------------------------------------
# Frontmatter parser (minimal YAML — no PyYAML dependency)
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter delimited by ``---`` lines.

    Parameters
    ----------
    text : str
        Raw file content.

    Returns
    -------
    tuple[dict[str, str], str]
        (metadata dict, body after frontmatter). If no frontmatter is found,
        returns ``({}, text)``.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_idx: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, text

    meta: dict[str, str] = {}
    current_key: str | None = None
    multiline_parts: list[str] = []
    is_folded = False  # True for >, False for |

    def _flush() -> None:
        """Save accumulated multiline value to meta."""
        if current_key is not None and multiline_parts:
            if is_folded:
                meta[current_key] = " ".join(multiline_parts)
            else:
                meta[current_key] = "\n".join(multiline_parts)

    for line in lines[1:end_idx]:
        stripped = line.strip()

        # Continuation line for multiline value (indented)
        if current_key is not None and line and line[0] in (" ", "\t") and stripped:
            multiline_parts.append(stripped)
            continue

        # Not a continuation — flush previous multiline if any
        _flush()
        current_key = None
        multiline_parts = []

        if not stripped or stripped.startswith("#"):
            continue

        colon_pos = stripped.find(":")
        if colon_pos == -1:
            continue

        key = stripped[:colon_pos].strip()
        value = stripped[colon_pos + 1 :].strip()

        # YAML multiline indicators: > (folded) or | (literal)
        if value in (">", "|", ">-", "|-"):
            current_key = key
            is_folded = value.startswith(">")
            multiline_parts = []
            continue

        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        meta[key] = value

    # Flush any trailing multiline value
    _flush()

    body = "\n".join(lines[end_idx + 1 :])
    return meta, body


# ---------------------------------------------------------------------------
# Internal scanners
# ---------------------------------------------------------------------------


def _safe_read_text(path: Path) -> str | None:
    """Read file text, returning None on any I/O error."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.debug("Cannot read %s: %s", path, exc)
        return None


def _safe_read_json(path: Path) -> dict | None:
    """Read and parse a JSON file, returning None on error."""
    text = _safe_read_text(path)
    if text is None:
        return None
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        return None
    except (json.JSONDecodeError, ValueError) as exc:
        logger.debug("Bad JSON in %s: %s", path, exc)
        return None


def _name_from_path(base_dir: Path, md_path: Path) -> str:
    """Derive resource name from relative path: ``git/commit.md`` → ``git:commit``."""
    rel = md_path.relative_to(base_dir).with_suffix("")
    return str(rel).replace(os.sep, ":").replace("/", ":")


def _description_from_body(body: str, max_len: int = 240) -> str:
    """Extract first non-empty line as fallback description."""
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:max_len]
    return ""


def _scan_markdown_dir(
    base_dir: Path,
    category: str,
    scope: str,
) -> list[Resource]:
    """Scan a directory recursively for ``.md`` files (commands or agents)."""
    resources: list[Resource] = []
    if not base_dir.is_dir():
        return resources

    try:
        md_files = sorted(base_dir.rglob("*.md"))
    except OSError:
        return resources

    for md_path in md_files:
        text = _safe_read_text(md_path)
        if text is None:
            continue

        meta, body = parse_frontmatter(text)
        name = meta.get("name") or _name_from_path(base_dir, md_path)
        description = meta.get("description") or _description_from_body(body)

        extra: dict[str, object] = {
            k: v for k, v in meta.items() if k not in ("name", "description")
        }

        resources.append(
            Resource(
                category=category,
                name=name,
                scope=scope,
                source=md_path,
                description=description,
                extra=extra,
            )
        )
    return resources


def _scan_skills(base_dir: Path, scope: str) -> list[Resource]:
    """Scan skills directory: each subfolder must contain ``SKILL.md``."""
    resources: list[Resource] = []
    if not base_dir.is_dir():
        return resources

    try:
        subdirs = sorted(base_dir.iterdir())
    except OSError:
        return resources

    for skill_dir in subdirs:
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        text = _safe_read_text(skill_file)
        if text is None:
            continue

        meta, body = parse_frontmatter(text)
        name = meta.get("name") or skill_dir.name
        description = meta.get("description") or _description_from_body(body)
        extra: dict[str, object] = {
            k: v for k, v in meta.items() if k not in ("name", "description")
        }

        resources.append(
            Resource(
                category="skills",
                name=name,
                scope=scope,
                source=skill_file,
                description=description,
                extra=extra,
            )
        )
    return resources


def _mcp_description(server_cfg: dict) -> str:
    """Build human-readable description for an MCP server entry."""
    transport = server_cfg.get("type", "stdio")
    if transport == "http" or "url" in server_cfg:
        url = server_cfg.get("url", "")
        return f"[{transport}] {url}"[:240]
    cmd = server_cfg.get("command", "")
    args = " ".join(server_cfg.get("args", []))
    return f"[{transport}] {cmd} {args}".strip()[:240]


def _scan_mcp_servers(
    servers: dict,
    scope: str,
    source: Path,
    location: str | None = None,
) -> list[Resource]:
    """Extract MCP server resources from a ``mcpServers`` dict."""
    resources: list[Resource] = []
    if not isinstance(servers, dict):
        return resources

    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        extra: dict[str, object] = dict(cfg)
        if location:
            extra["location"] = location
        resources.append(
            Resource(
                category="mcp",
                name=str(name),
                scope=scope,
                source=source,
                description=_mcp_description(cfg),
                extra=extra,
            )
        )
    return resources


def _scan_hooks(
    hooks: dict,
    scope: str,
    source: Path,
) -> list[Resource]:
    """Extract hook resources from a ``hooks`` dict."""
    resources: list[Resource] = []
    if not isinstance(hooks, dict):
        return resources

    for event, matcher_groups in hooks.items():
        if not isinstance(matcher_groups, list):
            continue
        for group in matcher_groups:
            if not isinstance(group, dict):
                continue
            matcher = group.get("matcher", "*")
            hook_defs = group.get("hooks", [])
            if not isinstance(hook_defs, list):
                hook_defs = [hook_defs]
            for hook_def in hook_defs:
                if not isinstance(hook_def, dict):
                    continue
                htype = hook_def.get("type", "command")
                hcmd = hook_def.get("command", "")
                hdesc = hook_def.get("description", "")
                desc = hdesc if hdesc else f"[{htype}] {hcmd}"
                resources.append(
                    Resource(
                        category="hooks",
                        name=f"{event}:{matcher}",
                        scope=scope,
                        source=source,
                        description=desc[:240],
                        extra=dict(hook_def),
                    )
                )
    return resources


def _scan_env_from_settings(
    env: dict,
    scope: str,
    source: Path,
) -> list[Resource]:
    """Extract env variable resources from settings ``env`` dict."""
    resources: list[Resource] = []
    if not isinstance(env, dict):
        return resources
    for key, value in env.items():
        resources.append(
            Resource(
                category="env",
                name=str(key),
                scope=scope,
                source=source,
                description=str(value)[:240],
                extra={"value": value},
            )
        )
    return resources


def _scan_settings_file(path: Path, scope: str) -> list[Resource]:
    """Scan a ``settings.json`` for MCP servers, hooks, and env vars."""
    data = _safe_read_json(path)
    if data is None:
        return []

    resources: list[Resource] = []
    resources.extend(_scan_mcp_servers(data.get("mcpServers", {}), scope=scope, source=path))
    resources.extend(_scan_hooks(data.get("hooks", {}), scope=scope, source=path))
    resources.extend(_scan_env_from_settings(data.get("env", {}), scope=scope, source=path))
    return resources


def _scan_claude_json_legacy(path: Path) -> list[Resource]:
    """Scan ``~/.claude.json`` for top-level and per-project MCP servers."""
    data = _safe_read_json(path)
    if data is None:
        return []

    resources: list[Resource] = []

    # Top-level mcpServers
    resources.extend(_scan_mcp_servers(data.get("mcpServers", {}), scope="global", source=path))

    # Per-project mcpServers
    projects = data.get("projects", {})
    if isinstance(projects, dict):
        for proj_path, proj_cfg in projects.items():
            if isinstance(proj_cfg, dict) and "mcpServers" in proj_cfg:
                resources.extend(
                    _scan_mcp_servers(
                        proj_cfg["mcpServers"],
                        scope="project",
                        source=path,
                        location=str(proj_path),
                    )
                )
    return resources


def _scan_process_env() -> list[Resource]:
    """Scan process environment for ``CLAUDE_*`` and ``ANTHROPIC_*`` variables."""
    resources: list[Resource] = []
    sentinel = Path("/proc/self/environ") if Path("/proc/self/environ").exists() else Path("-")

    for key, value in sorted(os.environ.items()):
        if key.startswith("CLAUDE_") or key.startswith("ANTHROPIC_"):
            resources.append(
                Resource(
                    category="env",
                    name=key,
                    scope="global",
                    source=sentinel,
                    description=value[:240],
                    extra={"value": value, "origin": "shell"},
                )
            )
    return resources


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_all(project_dir: Path | None = None) -> list[Resource]:
    """Scan all Claude Code resources from global and project scope.

    Parameters
    ----------
    project_dir : Path | None
        Explicit project root. If None, auto-detected from cwd.

    Returns
    -------
    list[Resource]
        All discovered resources, sorted by (category order, scope, name).
    """
    resources: list[Resource] = []
    home = claude_home()

    # --- Global scope ---
    resources.extend(_scan_markdown_dir(home / "commands", category="commands", scope="global"))
    resources.extend(_scan_markdown_dir(home / "agents", category="agents", scope="global"))
    resources.extend(_scan_skills(home / "skills", scope="global"))
    resources.extend(_scan_settings_file(home / "settings.json", scope="global"))

    # Legacy ~/.claude.json (always at ~/.claude.json, not CLAUDE_CONFIG_DIR)
    resources.extend(_scan_claude_json_legacy(Path.home() / ".claude.json"))

    # Process env
    resources.extend(_scan_process_env())

    # --- Project scope ---
    proj = project_dir or project_root()
    if proj is not None:
        proj_claude = proj / ".claude"
        resources.extend(
            _scan_markdown_dir(proj_claude / "commands", category="commands", scope="project")
        )
        resources.extend(
            _scan_markdown_dir(proj_claude / "agents", category="agents", scope="project")
        )
        resources.extend(_scan_skills(proj_claude / "skills", scope="project"))
        resources.extend(_scan_settings_file(proj_claude / "settings.json", scope="project"))
        resources.extend(_scan_settings_file(proj_claude / "settings.local.json", scope="project"))

        # .mcp.json at project root
        mcp_json = proj / ".mcp.json"
        mcp_data = _safe_read_json(mcp_json)
        if mcp_data and "mcpServers" in mcp_data:
            resources.extend(
                _scan_mcp_servers(mcp_data["mcpServers"], scope="project", source=mcp_json)
            )

    # Sort: category order → scope (global first) → name (case-insensitive)
    resources.sort(
        key=lambda r: (
            CATEGORY_ORDER.get(r.category, 99),
            0 if r.scope == "global" else 1,
            r.name.lower(),
        )
    )
    return resources


def group_by_category(resources: list[Resource]) -> dict[str, list[Resource]]:
    """Group resources by category, preserving CATEGORIES order.

    Returns
    -------
    dict[str, list[Resource]]
        Keys are category IDs in display order; all 6 categories present (may be empty).
    """
    groups: dict[str, list[Resource]] = {cat_id: [] for cat_id, _, _ in CATEGORIES}
    for r in resources:
        groups.setdefault(r.category, []).append(r)
    return groups
