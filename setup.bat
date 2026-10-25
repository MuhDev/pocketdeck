@echo off
setlocal enabledelayedexpansion
title PocketDeck Setup Wizard
chcp 65001 >nul
cd /d "%~dp0"

echo ===============================================================================
echo                         🚀 PocketDeck - Setup Wizard
echo ===============================================================================
echo.
echo Welcome to PocketDeck! This wizard will prepare everything needed to run
echo the PocketDeck control server on your PC in just a few moments.
echo.

:: -----------------------------------------------------------------------------
:: Step 1: Detect or Install Python
:: -----------------------------------------------------------------------------
echo [1/4] Checking Python environment...

set PYTHON_CMD=

:: Check for py launcher with Python 3.13
py -3.13 -c "import sys; sys.exit(0)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=py -3.13"
    goto :python_ready
)

:: Check for py -3 (3.13+)
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=py -3"
    goto :python_ready
)

:: Check for python in PATH (3.13+)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
    goto :python_ready
)

:: Fallback: Check for any existing Python 3.10+
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=py -3"
    goto :python_ready
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
    goto :python_ready
)

:: Python was not found -> Friendly automated installation flow
echo.
echo   [!] Python 3.13 is required to run PocketDeck, but was not detected.
echo.
echo   How would you like to install Python?
echo     [1] Automatically install Python 3.13 now (Recommended)
echo     [2] Open Python.org download page in browser
echo     [3] Cancel setup
echo.
set /p PY_CHOICE="  Enter your choice [1, 2, or 3] (Default: 1): "
if "%PY_CHOICE%"=="" set PY_CHOICE=1

if "%PY_CHOICE%"=="2" (
    echo.
    echo   Opening official Python download page in your browser...
    start https://www.python.org/downloads/
    echo.
    echo   ======================================================================
    echo   IMPORTANT TIP FOR INSTALLATION:
    echo     When the installer window appears, make sure to check the box:
    echo        [✓] "Add python.exe to PATH"
    echo   ======================================================================
    echo.
    echo   After installation finishes, restart setup.bat!
    pause
    exit /b 0
)

if "%PY_CHOICE%"=="3" (
    echo Setup cancelled by user.
    pause
    exit /b 0
)

:: Automatic installation via winget or official installer download
echo.
echo   Attempting automatic installation of Python 3.13...

where winget >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo   Using Windows Package Manager (winget)...
    winget install --id Python.Python.3.13 -e --source winget --accept-package-agreements --accept-source-agreements
) else (
    echo   Downloading Python 3.13 installer from python.org...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.13.2/python-3.13.2-amd64.exe' -OutFile '$env:TEMP\python_setup.exe'"
    echo   Running installer...
    "%TEMP%\python_setup.exe" /passive InstallAllUsers=0 PrependPath=1 SimpleInstall=1
    del "%TEMP%\python_setup.exe" >nul 2>&1
)

:: Refresh PATH from registry for current session
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "PATH=%%b;%PATH%"
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "PATH=%%b;%PATH%"

:: Re-verify Python after installation
py -3.13 -c "import sys; sys.exit(0)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=py -3.13"
    goto :python_ready
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
    goto :python_ready
)

echo.
echo   [!] Python installation completed, but a quick terminal restart is needed.
echo       Please close this window and double-click setup.bat again!
pause
exit /b 0

:python_ready
for /f "tokens=*" %%v in ('%PYTHON_CMD% -c "import sys; print(f'Python {sys.version.split()[0]} ({sys.platform})')"') do set "PY_VER=%%v"
echo       Found: %PY_VER% [OK]
echo.

:: -----------------------------------------------------------------------------
:: Step 2: Virtual Environment Setup
:: -----------------------------------------------------------------------------
echo [2/4] Setting up isolated application environment...
if not exist "venv\Scripts\activate.bat" (
    echo       Creating virtual environment in .\venv...
    %PYTHON_CMD% -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo   [ERROR] Could not create virtual environment.
        pause
        exit /b 1
    )
    echo       Virtual environment created successfully. [OK]
) else (
    echo       Virtual environment is already ready. [OK]
)
echo.

:: -----------------------------------------------------------------------------
:: Step 3: Install Packages
:: -----------------------------------------------------------------------------
echo [3/4] Installing PocketDeck components...
echo       (This takes about 30 seconds on first run, please wait...)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel >setup.log 2>&1
python -m pip install -r requirements.txt >>setup.log 2>&1

if %ERRORLEVEL% neq 0 (
    echo.
    echo   [ERROR] Failed to install required packages!
    echo   Details from setup.log:
    echo   ---------------------------------------------------------------------
    type setup.log
    echo   ---------------------------------------------------------------------
    echo   Please check your internet connection and try running setup.bat again.
    pause
    exit /b 1
)

if exist setup.log del setup.log >nul 2>&1
echo       All components installed successfully! [OK]
echo.

:: -----------------------------------------------------------------------------
:: Step 4: Configuration File
:: -----------------------------------------------------------------------------
echo [4/4] Verifying configuration file...
if not exist "config.yaml" (
    if exist "config.example.yaml" (
        copy config.example.yaml config.yaml >nul
        echo       Created config.yaml from defaults. [OK]
    )
) else (
    echo       Configuration file is ready. [OK]
)
echo.

:: -----------------------------------------------------------------------------
:: Optional: Desktop Shortcut
:: -----------------------------------------------------------------------------
echo -------------------------------------------------------------------------------
set /p SHORTCUT_CHOICE="  Would you like to add a PocketDeck shortcut to your Desktop? [Y/n]: "
if /i "%SHORTCUT_CHOICE%"=="" set SHORTCUT_CHOICE=Y
if /i "%SHORTCUT_CHOICE%"=="Y" (
    python -m server.setup_helper --create-shortcut
)
echo.

:: -----------------------------------------------------------------------------
:: Completion & Launch Option
:: -----------------------------------------------------------------------------
echo ===============================================================================
echo                         🎉 Setup Complete!
echo ===============================================================================
echo.
echo   PocketDeck is ready to use!
echo     - Default Security PIN: 1234
echo     - Access from your PC:  http://localhost:8765
echo.
set /p LAUNCH_CHOICE="  Would you like to start PocketDeck now? [Y/n]: "
if /i "%LAUNCH_CHOICE%"=="" set LAUNCH_CHOICE=Y
if /i "%LAUNCH_CHOICE%"=="Y" (
    echo.
    echo   Starting server...
    call run.bat
    exit /b 0
)

echo.
echo You can start PocketDeck at any time by double-clicking:
echo   run.bat  (or the Desktop shortcut if created)
echo.
pause
