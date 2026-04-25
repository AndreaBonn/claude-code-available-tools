# Contributing to Claude Code Available Tools by Bonn

Contributions are welcome via pull request.

## Development setup

```bash
git clone https://github.com/AndreaBonn/claude-code-available-tools.git
cd claude-code-available-tools
uv sync --dev
```

## Before submitting a PR

1. **Tests pass:**
   ```bash
   uv run pytest tests/ -v
   ```

2. **Linter clean:**
   ```bash
   uv run ruff check src/ tests/
   uv run ruff format src/ tests/
   ```

3. **Type checker clean:**
   ```bash
   uv run mypy src/cctools/
   ```

4. **Commits focused and descriptive** using [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat(scanner): add support for new resource type
   fix(tui): correct filter bar escape handling
   docs(readme): update installation instructions
   ```

## Project structure

```
src/cctools/
  scanner.py    # Core resource discovery (pure logic + isolated I/O)
  cli.py        # CLI entry point and mode dispatch
  tui.py        # Full-screen Textual app
  inline.py     # Rich text report renderer
  terminal.py   # Terminal emulator detection
tests/          # Mirrors src/ structure
```

## Code standards

- Python 3.10+ syntax (`X | None`, `list[int]`, `match/case`)
- Type annotations on all parameters and return types
- `ruff` for linting and formatting (config in `pyproject.toml`)
- `mypy --strict`-adjacent settings enabled

## Security

Do not open public issues for security vulnerabilities. See [SECURITY.md](SECURITY.md) for reporting instructions.
