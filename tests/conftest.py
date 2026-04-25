"""Shared fixtures for the ctools test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
HOME_CLAUDE = FIXTURES_DIR / "home-claude"
PROJECT_CLAUDE = FIXTURES_DIR / "project-claude"


@pytest.fixture()
def home_claude() -> Path:
    return HOME_CLAUDE


@pytest.fixture()
def project_claude() -> Path:
    return PROJECT_CLAUDE


@pytest.fixture()
def legacy_claude_json() -> Path:
    return HOME_CLAUDE / "claude-legacy.json"
