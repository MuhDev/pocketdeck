@echo off
setlocal
cd /d "%~dp0"

:: Ensure PocketDeck always runs with Administrator privileges
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting Administrator privileges for PocketDeck...
    set "BATCH_PATH=%~f0"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath $env:BATCH_PATH -WorkingDirectory $env:CD -Verb RunAs"
    exit /b 0
)

title PocketDeck Control Server (Administrator)
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
if not exist "PocketDeck.lnk" python -m server.setup_helper --create-shortcut >nul 2>&1
python -m server.main

if errorlevel 1 (
    echo.
    echo [ERROR] PocketDeck stopped with an error.
    pause
)
