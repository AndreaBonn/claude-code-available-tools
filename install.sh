#!/usr/bin/env bash
# install.sh — Universal installer dispatcher for ctools
# Detects the OS and launches the appropriate platform installer.
#
# Usage: ./install.sh [--force]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLERS_DIR="$SCRIPT_DIR/installers"

case "$(uname -s)" in
    Linux*)
        echo "Detected: Linux"
        exec "$INSTALLERS_DIR/install_linux.sh" "$@"
        ;;
    Darwin*)
        echo "Detected: macOS"
        exec "$INSTALLERS_DIR/install_macos.sh" "$@"
        ;;
    CYGWIN*|MINGW*|MSYS*)
        echo "Detected: Windows (Git Bash / MSYS)"
        echo ""
        echo "Please use the Windows installer instead:"
        echo "  .\\install.bat"
        echo "  or: powershell -ExecutionPolicy Bypass -File installers\\install_windows.ps1"
        echo ""
        exit 1
        ;;
    *)
        echo "Unknown OS: $(uname -s)"
        echo "Try one of the platform-specific installers:"
        echo "  Linux:   ./installers/install_linux.sh"
        echo "  macOS:   ./installers/install_macos.sh"
        echo "  Windows: .\\install.bat"
        exit 1
        ;;
esac
