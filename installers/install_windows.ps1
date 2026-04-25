# install_windows.ps1 — One-shot installer for cctools on Windows
# Usage: powershell -ExecutionPolicy Bypass -File install_windows.ps1 [-Force]
#
# Requirements: Python 3.10+, Claude Code installed
# Recommended: Windows Terminal for best TUI experience

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$SlashCmdSrc = Join-Path $ProjectDir "slash-command" "tools.md"
$ClaudeHome = Join-Path $env:USERPROFILE ".claude"
$SlashCmdDst = Join-Path $ClaudeHome "commands" "tools.md"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# --- Step 1: Check Python >= 3.10 ---
Write-Info "Checking Python version..."

$PythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $null = & $cmd --version 2>&1
        $PythonCmd = $cmd
        break
    } catch {
        continue
    }
}

if (-not $PythonCmd) {
    Write-Err "Python not found. Install from https://www.python.org/downloads/"
    Write-Err "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

$PyVersion = & $PythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
$PyParts = $PyVersion.Split(".")
$PyMajor = [int]$PyParts[0]
$PyMinor = [int]$PyParts[1]

if ($PyMajor -lt 3 -or ($PyMajor -eq 3 -and $PyMinor -lt 10)) {
    Write-Err "Python >= 3.10 required (found $PyVersion)."
    Write-Err "Download from https://www.python.org/downloads/"
    exit 1
}
Write-Ok "Python $PyVersion ($PythonCmd)"

# --- Step 2: Install cctools ---
Write-Info "Installing cctools..."

$Installed = $false

# Try pipx
try {
    $null = Get-Command pipx -ErrorAction Stop
    Write-Info "Using pipx..."
    & pipx install $ProjectDir --force 2>&1 | Select-Object -Last 5
    Write-Ok "Installed via pipx"
    $Installed = $true
} catch {}

# Try uv
if (-not $Installed) {
    try {
        $null = Get-Command uv -ErrorAction Stop
        Write-Info "Using uv..."
        & uv tool install $ProjectDir --force 2>&1 | Select-Object -Last 5
        Write-Ok "Installed via uv tool"
        $Installed = $true
    } catch {}
}

# Fallback to pip
if (-not $Installed) {
    Write-Info "Using pip install --user..."
    & $PythonCmd -m pip install --user $ProjectDir 2>&1 | Select-Object -Last 5
    Write-Ok "Installed via pip --user"
}

# --- Step 3: Check PATH ---
$CtoolsBin = $null
try {
    $CtoolsBin = (Get-Command cctools -ErrorAction Stop).Source
    Write-Ok "cctools binary: $CtoolsBin"
} catch {
    Write-Warn "cctools not found on PATH."
    $PythonScriptsDir = & $PythonCmd -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))" 2>&1
    Write-Warn "Add this directory to your PATH:"
    Write-Host ""
    Write-Host "  $PythonScriptsDir" -ForegroundColor White
    Write-Host ""
    Write-Warn "To add permanently (PowerShell):"
    Write-Host '  [Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";' + $PythonScriptsDir + '", "User")' -ForegroundColor White
    Write-Host ""
    Write-Warn "Then restart your terminal and re-run this script."
}

# --- Step 4: Install slash command ---
Write-Info "Installing slash command /tools..."

$DoInstall = $true
if ((Test-Path $SlashCmdDst) -and -not $Force) {
    Write-Warn "$SlashCmdDst already exists."
    $answer = Read-Host "Overwrite? [y/N]"
    if ($answer -ne "y" -and $answer -ne "Y") {
        Write-Info "Skipping slash command installation."
        $DoInstall = $false
    }
}

if ($DoInstall) {
    $CmdDir = Split-Path -Parent $SlashCmdDst
    if (-not (Test-Path $CmdDir)) {
        New-Item -ItemType Directory -Path $CmdDir -Force | Out-Null
    }
    Copy-Item $SlashCmdSrc $SlashCmdDst -Force
    Write-Ok "Slash command installed: $SlashCmdDst"
}

# --- Step 5: Smoke test ---
Write-Info "Running smoke test..."
try {
    $null = Get-Command cctools -ErrorAction Stop
    $output = & cctools --mode inline 2>&1
    $count = ($output | Select-String -Pattern "[●◆]" -AllMatches | ForEach-Object { $_.Matches.Count } | Measure-Object -Sum).Sum
    if (-not $count) { $count = 0 }
    Write-Ok "Smoke test passed — $count resources found"
} catch {
    Write-Warn "Cannot run smoke test (cctools not on PATH yet)"
}

# --- Recap ---
Write-Host ""
Write-Host "=======================================" -ForegroundColor Green
Write-Host "  cctools installation complete! (Windows)" -ForegroundColor White
Write-Host "=======================================" -ForegroundColor Green
Write-Host ""
$BinPath = if ($CtoolsBin) { $CtoolsBin } else { "~\AppData\Roaming\Python\Scripts\cctools.exe" }
Write-Host "  Binary:         $BinPath" -ForegroundColor Cyan
Write-Host "  Slash command:  $SlashCmdDst" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Usage:" -ForegroundColor White
Write-Host "    cctools                 — TUI in current terminal" -ForegroundColor Cyan
Write-Host "    cctools --mode inline   — text report" -ForegroundColor Cyan
Write-Host "    /tools                 — from Claude Code" -ForegroundColor Cyan
Write-Host "    /tools inline          — from Claude Code (inline report)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Note: external mode is not available on Windows." -ForegroundColor Yellow
Write-Host "  Use 'cctools' or '/tools tui' for TUI, '/tools inline' for text." -ForegroundColor Yellow
Write-Host ""
