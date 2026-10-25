@echo off
setlocal
title PocketDeck Server
chcp 65001 >nul
cd /d "%~dp0"

:: If first-time user runs run.bat directly without setup, run setup automatically
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] First-time launch detected. Running setup wizard...
    echo.
    call setup.bat
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Setup encountered an issue.
        pause
        exit /b 1
    )
    exit /b 0
)

call venv\Scripts\activate.bat

python -m server.main

if %ERRORLEVEL% neq 0 (
    echo.
    echo Server stopped with code %ERRORLEVEL%.
    pause
)
