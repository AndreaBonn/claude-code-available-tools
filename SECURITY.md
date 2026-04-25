**English** | [Italiano](SECURITY.it.md)

# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Reporting a Vulnerability

To report a security vulnerability, use GitHub Security Advisories:

[Report a vulnerability](https://github.com/AndreaBonn/cc-available-tools/security/advisories/new)

Do not open a public issue for security reports.

### What to include

- Description of the vulnerability
- Steps to reproduce
- Affected version(s)
- Impact assessment (what an attacker could achieve)

### Response timeline

- Acknowledgment: within 72 hours
- Critical fixes: within 30 days
- Coordinated public disclosure after the fix is released

## Security Measures Implemented

cc-available-tools is a local CLI tool that reads Claude Code configuration files from disk. It does not expose network services, handle authentication, or process untrusted user input from external sources.

Current measures:

- **Dependency lockfile**: `uv.lock` pins all transitive dependencies to exact versions (`uv.lock`)
- **Safe file I/O**: all filesystem reads are wrapped in try/except with explicit error handling, no exceptions propagate from the scanner (`src/cctools/scanner.py:177-198`)
- **No shell injection surface**: the tool does not pass user-supplied strings to shell commands; `subprocess.Popen` in `cli.py:80` uses list-based arguments
- **No `eval`/`exec`/`pickle`**: no dynamic code execution on file contents
- **JSON parsing with type guards**: JSON data from config files is validated with `isinstance` checks before use (`src/cctools/scanner.py:186-198`)
- **Static analysis**: ruff linter and mypy type checker configured in `pyproject.toml`

## Security Best Practices for Users

- Keep Python and dependencies up to date
- Review the contents of `~/.claude/` and project `.claude/` directories, as cctools reads and displays their contents
- If using `CLAUDE_CONFIG_DIR` to point to a custom config directory, ensure that directory has appropriate file permissions

## Out of Scope

The following are not considered vulnerabilities in cc-available-tools:

- Display of sensitive data already present in Claude Code configuration files (this is the tool's intended function)
- Local privilege escalation requiring pre-existing access to the user's account
- Social engineering attacks
- Denial of service via excessively large configuration files on the local filesystem
- Vulnerabilities in third-party dependencies that are already publicly disclosed (report these upstream)

## Acknowledgments

Security researchers who report valid vulnerabilities will be credited here upon request.

---

[Back to README](README.md)
