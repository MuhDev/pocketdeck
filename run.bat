@echo off
setlocal
title PocketDeck Control Server
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo ===============================================================================
    echo                    PocketDeck - First Time Launch Detected
    echo ===============================================================================
    echo.
    echo Running setup wizard first...
    echo.
    call "%~dp0setup.bat"
    if errorlevel 1 (
        echo.
        echo [ERROR] Setup encountered an issue.
        pause
        exit /b 1
    )
)

if not exist "venv\Scripts\activate.bat" (
    echo.
    echo [ERROR] Virtual environment was not found. Please run setup.bat.
    pause
    exit /b 1
)

call "%~dp0venv\Scripts\activate.bat"
python -m server.main

if errorlevel 1 (
    echo.
    echo [ERROR] PocketDeck stopped with an error.
    pause
)
