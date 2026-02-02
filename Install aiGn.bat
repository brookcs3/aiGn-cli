@echo off
:: Double-click to install aiGn on Windows
:: Requires WSL2 with Ubuntu installed

echo.
echo  ================================================
echo   aiGn - AI Career Agent Installer (Windows)
echo  ================================================
echo.

:: Check if WSL is available
wsl --status >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: WSL2 is required but not installed.
    echo.
    echo  To install WSL2:
    echo    1. Open PowerShell as Administrator
    echo    2. Run: wsl --install
    echo    3. Restart your computer
    echo    4. Double-click this file again
    echo.
    pause
    exit /b 1
)

echo  WSL2 detected. Launching installer...
echo.

:: Convert Windows path to WSL path and run
wsl bash -c "cd \"$(wsl wslpath '%~dp0')\" && chmod +x install.sh career_agent.sh 2>/dev/null && bash install.sh"

echo.
pause
