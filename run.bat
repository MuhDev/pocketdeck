@echo off
setlocal
cd /d "%~dp0"

echo ===============================================================================
echo                         PocketDeck Control Server
echo ===============================================================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Running setup first...
    call setup.bat
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Setup failed.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

echo Starting server...
python -c "import sys; print(f'Environment: Python {sys.version.split()[0]} (64-bit)')"
echo.
echo Access the control surface from your phone or browser at:
echo   http://localhost:8765
echo.
python -m server.main

pause
