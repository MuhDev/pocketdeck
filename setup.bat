@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ===============================================================================
echo                     PocketDeck - Setup & Environment Setup
echo ===============================================================================
echo.

set PYTHON_CMD=

:: 1. Prefer Python 3.13 via Windows py launcher
py -3.13 -c "import sys; sys.exit(0)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=py -3.13"
    goto :python_found
)

:: 2. Check if default py -3 is 3.13+
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=py -3"
    goto :python_found
)

:: 3. Check if python in PATH is 3.13+
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
    goto :python_found
)

:: 4. Fallback: Check if any Python 3.10+ exists with a warning
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=py -3"
    echo [WARNING] Python 3.13 was not found. Using detected Python, but 3.13 is recommended.
    goto :python_found
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
    echo [WARNING] Python 3.13 was not found. Using detected Python, but 3.13 is recommended.
    goto :python_found
)

echo [ERROR] Python 3.13 was not found!
echo Please install the latest Python 3.13 from https://www.python.org/
echo Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:python_found
echo [INFO] Using Python:
%PYTHON_CMD% -c "import sys; print(f'  Python {sys.version}')"
echo.

echo [1/4] Checking Python Virtual Environment...
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment in .\venv with %PYTHON_CMD%...
    %PYTHON_CMD% -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
    venv\Scripts\python.exe -c "import sys; print(f'  Current venv Python: {sys.version.split()[0]}')"
)

echo.
echo [2/4] Activating Virtual Environment and Upgrading Pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel --quiet

echo.
echo [3/4] Installing Required Dependencies...
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies from requirements.txt.
    pause
    exit /b 1
)

echo.
echo [4/4] Verifying Configuration...
if not exist "config.yaml" (
    if exist "config.example.yaml" (
        copy config.example.yaml config.yaml >nul
        echo Created config.yaml from config.example.yaml
    )
) else (
    echo config.yaml is ready.
)

echo.
echo ===============================================================================
echo Setup complete on Python 3.13! You can now start the server by running:
echo   run.bat
echo ===============================================================================
echo.
pause
