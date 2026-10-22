@echo off
setlocal
cd /d "%~dp0"

echo ===============================================================================
echo                     PC Remote - Setup & Environment Setup
echo ===============================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your PATH!
    echo Please install Python 3.10 or newer from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/4] Checking Python Virtual Environment...
if not exist "venv" (
    echo Creating virtual environment in .\venv...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
)

echo.
echo [2/4] Activating Virtual Environment and Upgrading Pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet

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
echo Setup complete! You can now start the server by running:
echo   run.bat
echo ===============================================================================
echo.
pause
