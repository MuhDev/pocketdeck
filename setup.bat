@echo off
setlocal enabledelayedexpansion
title PocketDeck Setup Wizard
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ===============================================================================
echo                         PocketDeck - Setup Wizard
echo ===============================================================================
echo.
echo Welcome to PocketDeck! This wizard will set up everything needed to run
echo the PocketDeck control server on your PC.
echo.

:: -----------------------------------------------------------------------------
:: Step 1: Detect or Install Python
:: -----------------------------------------------------------------------------
echo [1/4] Checking Python environment...

set "PYTHON_CMD="

:: Check for py launcher with Python 3.13
py -3.13 -c "import sys; sys.exit(0)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.13"
    goto :python_ready
)

:: Check for py -3 (3.13+)
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto :python_ready
)

:: Check for python in PATH (3.13+)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :python_ready
)

:: Fallback: Check for any existing Python 3.10+
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto :python_ready
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 (
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
if "%PY_CHOICE%"=="" set "PY_CHOICE=1"

if "%PY_CHOICE%"=="2" goto :open_python_browser
if "%PY_CHOICE%"=="3" goto :cancel_setup

:: Automatic installation via winget or official installer download
echo.
echo   Attempting automatic installation of Python 3.13...

where winget >nul 2>&1
if not errorlevel 1 (
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
py -3.13 -c "import sys; sys.exit(0)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.13"
    goto :python_ready
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :python_ready
)

echo.
echo   [!] Python installation completed, but a quick terminal restart is needed.
echo       Please close this window and double-click setup.bat again.
echo.
pause
exit /b 0

:open_python_browser
echo.
echo   Opening official Python download page in your browser...
start https://www.python.org/downloads/
echo.
echo   ======================================================================
echo   IMPORTANT TIP FOR INSTALLATION:
echo     When the installer window appears, make sure to check the box:
echo        [X] "Add python.exe to PATH"
echo   ======================================================================
echo.
echo   After installation finishes, restart setup.bat!
pause
exit /b 0

:cancel_setup
echo Setup cancelled by user.
pause
exit /b 0

:python_ready
for /f "tokens=*" %%v in ('%PYTHON_CMD% -c "import sys; print(f'Python {sys.version.split()[0]}')"') do set "PY_VER=%%v"
echo       Found: %PY_VER% [OK]
echo.

:: -----------------------------------------------------------------------------
:: Step 2: Virtual Environment Setup
:: -----------------------------------------------------------------------------
echo [2/4] Setting up isolated application environment...
if not exist "venv\Scripts\activate.bat" (
    echo       Creating virtual environment in .\venv...
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo.
        echo   [ERROR] Could not create virtual environment.
        pause
        exit /b 1
    )
    echo       Virtual environment created successfully. [OK]
) else (
    echo       Virtual environment is ready. [OK]
)
echo.

:: -----------------------------------------------------------------------------
:: Step 3: Install Packages & Handle C++ Build Tools
:: -----------------------------------------------------------------------------
echo [3/4] Installing PocketDeck components...
echo       (This takes about 30 seconds on first run, please wait...)

:: Check for Visual C++ Runtime DLL (vcruntime140.dll)
if exist "%SystemRoot%\System32\vcruntime140.dll" goto :vcruntime_ready

echo       [i] Visual C++ Runtime not found. Attempting automatic install...
where winget >nul 2>&1
if not errorlevel 1 (
    winget install --id Microsoft.VCRedist.2015+.x64 -e --source winget --accept-package-agreements --accept-source-agreements >nul 2>&1
) else (
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile '$env:TEMP\vc_redist.x64.exe'; Start-Process '$env:TEMP\vc_redist.x64.exe' -ArgumentList '/passive','/norestart' -Wait" >nul 2>&1
)

:vcruntime_ready
call "%~dp0venv\Scripts\activate.bat"

:: Upgrade core packaging tools
python -m pip install --upgrade pip setuptools wheel >setup.log 2>&1

:: Install requirements with --prefer-binary to prioritize pre-compiled wheels
python -m pip install --prefer-binary -r requirements.txt >>setup.log 2>&1

if errorlevel 1 (
    findstr /i "Microsoft.Visual.C++ cl.exe vcvarsall Build.Tools VCTools LINK.exe Rust.compiler" setup.log >nul 2>&1
    if not errorlevel 1 goto :handle_cpp_build_error

    echo.
    echo   [ERROR] Failed to install required packages!
    echo   Details from setup.log:
    echo   ---------------------------------------------------------------------
    type setup.log
    echo   ---------------------------------------------------------------------
    echo   Please check your internet connection and try running setup.bat again.
    echo.
    pause
    exit /b 1
)

:step3_success
if exist setup.log del setup.log >nul 2>&1
echo       All components installed successfully! [OK]
echo.

:: -----------------------------------------------------------------------------
:: Step 4: Configuration File
:: -----------------------------------------------------------------------------
:step4_config
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
if /i "%SHORTCUT_CHOICE%"=="" set "SHORTCUT_CHOICE=Y"
if /i "%SHORTCUT_CHOICE%"=="Y" (
    python -m server.setup_helper --create-shortcut
)
echo.

:: -----------------------------------------------------------------------------
:: Completion & Launch Option
:: -----------------------------------------------------------------------------
echo ===============================================================================
echo                         Setup Complete!
echo ===============================================================================
echo.
echo   PocketDeck is ready to use!
echo     - Default Security PIN: 1234
echo     - Access from your PC:  http://localhost:8765
echo.
set /p LAUNCH_CHOICE="  Would you like to start PocketDeck now? [Y/n]: "
if /i "%LAUNCH_CHOICE%"=="" set "LAUNCH_CHOICE=Y"
if /i "%LAUNCH_CHOICE%"=="Y" (
    echo.
    echo   Starting server...
    call "%~dp0run.bat"
    exit /b 0
)

echo.
echo You can start PocketDeck at any time by double-clicking:
echo   run.bat  (or the Desktop shortcut)
echo.
pause
exit /b 0


:: =============================================================================
:: Special Handler: Microsoft Visual C++ Build Tools Missing
:: =============================================================================
:handle_cpp_build_error
echo.
echo ===============================================================================
echo        Microsoft Visual C++ Build Tools Required by Windows
echo ===============================================================================
echo.
echo   Windows was unable to compile one or more components because the
echo   Microsoft Visual C++ Build Tools are not installed on this PC.
echo.
echo   How would you like to resolve this?
echo     [1] Try installing pre-built binary wheels only (Fastest, no compiler needed)
echo     [2] Automatically install Visual C++ Build Tools via Windows (winget)
echo     [3] Download official Microsoft Build Tools installer (vs_BuildTools.exe)
echo     [4] Open Microsoft C++ Build Tools download webpage in browser
echo     [5] View full setup error log
echo     [6] Cancel setup
echo.
set /p CPP_CHOICE="  Enter your choice [1-6] (Default: 1): "
if "%CPP_CHOICE%"=="" set "CPP_CHOICE=1"

if "%CPP_CHOICE%"=="1" (
    echo.
    echo   Attempting installation with binary-only pre-compiled packages...
    python -m pip install --only-binary :all: -r requirements.txt >>setup.log 2>&1
    if not errorlevel 1 (
        echo   [OK] Pre-compiled binary packages installed successfully!
        goto :step3_success
    ) else (
        echo   [!] Pre-compiled binary wheels were not found for all components.
        echo       A C++ compiler is needed for this system.
        goto :handle_cpp_build_error
    )
)

if "%CPP_CHOICE%"=="2" (
    echo.
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo   Installing Visual Studio 2022 Build Tools via winget...
        echo   This may take several minutes. Please keep this window open.
        winget install Microsoft.VisualStudio.2022.BuildTools -e --source winget --override "--passive --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
        echo.
        echo   Installation complete. Retrying component installation...
        python -m pip install -r requirements.txt
        if not errorlevel 1 goto :step3_success
    ) else (
        echo   Windows Package Manager (winget) not found.
        echo   Switching to official installer download...
        goto :download_vs_buildtools
    )
)

:download_vs_buildtools
if "%CPP_CHOICE%"=="3" (
    echo.
    echo   Downloading Microsoft Visual C++ Build Tools bootstrapper...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_BuildTools.exe' -OutFile '$env:TEMP\vs_BuildTools.exe'"
    echo   Launching Microsoft Visual Studio Build Tools installer...
    start "" "%TEMP%\vs_BuildTools.exe" --passive --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended
    echo.
    echo   Once the Visual Studio installer completes, press any key to continue setup...
    pause
    python -m pip install -r requirements.txt
    if not errorlevel 1 goto :step3_success
)

if "%CPP_CHOICE%"=="4" (
    echo.
    echo   Opening Microsoft Visual C++ Build Tools download page...
    start https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo.
    echo   ======================================================================
    echo   MANUAL INSTALLATION INSTRUCTIONS:
    echo     1. Download "Build Tools" from the opened Microsoft web page.
    echo     2. Run the installer (vs_BuildTools.exe).
    echo     3. In the Workloads list, check:
    echo          [X] "Desktop development with C++"
    echo     4. Click "Install" in the bottom right corner.
    echo     5. When finished, re-run setup.bat!
    echo   ======================================================================
    echo.
    pause
    exit /b 1
)

if "%CPP_CHOICE%"=="5" (
    echo.
    echo ============================== FULL ERROR LOG ==============================
    type setup.log
    echo ============================================================================
    echo.
    goto :handle_cpp_build_error
)

echo Setup cancelled.
pause
exit /b 1
