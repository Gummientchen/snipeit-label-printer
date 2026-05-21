@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  Snipe-IT Label Printer Setup ^& Launcher
echo ============================================================

rem Check if uv is in PATH
where uv >nul 2>nul
if %errorlevel% neq 0 (
    rem Check if it is installed in the default location but not in PATH yet
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        echo Found uv in local directory. Adding to PATH for this session...
        set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    ) else (
        echo UV package manager was not found.
        echo Installing UV...
        powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
        
        rem Add local bin to PATH for this session
        set "PATH=%USERPROFILE%\.local\bin;%PATH%"
        
        where uv >nul 2>nul
        if !errorlevel! neq 0 (
            echo.
            echo [ERROR] Installation failed or UV was not found in PATH.
            echo Please try installing UV manually: https://docs.astral.sh/uv/getting-started/installation/
            pause
            exit /b 1
        )
    )
) else (
    echo UV package manager is already installed.
)

rem Ensure the configuration file exists
if not exist .env (
    echo.
    echo Configuration file .env is missing.
    echo Creating .env from .env.sample...
    copy .env.sample .env >nul
    echo Please open '.env' and fill in your Snipe-IT details.
    echo.
    pause
    exit /b 0
)

echo Syncing dependencies...
uv sync

echo.
echo Starting application...
uv run python asset_label_app.py

pause
