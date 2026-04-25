"""cctools — Interactive explorer for Claude Code tools and configuration."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cctools")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
