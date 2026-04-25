@echo off
REM install.bat — Windows launcher for ctools installer
REM Delegates to install_windows.ps1

echo Detected: Windows
echo Launching PowerShell installer...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0installers\install_windows.ps1" %*
