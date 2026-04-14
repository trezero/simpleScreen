@echo off
setlocal EnableDelayedExpansion

echo.
echo =====================================================
echo   simpleScreen Installer for Windows
echo =====================================================
echo.

:: ── 1. Find Python 3 ─────────────────────────────────────────────────────────
echo   Checking for Python 3...
set PYTHON_CMD=

:: Try the 'py' launcher first — installed into System32 by Python setup,
:: so it is on PATH immediately even in the session that ran winget.
where py >nul 2>&1
if not errorlevel 1 goto :try_py_launcher

:: 'py' not found, try 'python' directly
where python >nul 2>&1
if not errorlevel 1 goto :try_python_direct

:: Neither found — install Python via winget
goto :install_python

:try_py_launcher
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3
    goto :python_found
)
:: py exists but -3 failed (unlikely) — fall through to direct python check

:try_python_direct
python -c "import sys; sys.exit(0 if sys.version_info.major >= 3 else 1)" >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :python_found
)

:install_python
echo   Python 3 not found. Installing via winget...
winget install --id Python.Python.3.12 --source winget --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo.
    echo   [ERROR] Could not install Python automatically.
    echo   Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
:: The Python installer places py.exe in C:\Windows\System32 — no PATH refresh needed.
where py >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERROR] Python installed but py.exe not found in System32.
    echo   Please open a new terminal and re-run install.bat.
    pause
    exit /b 1
)
set PYTHON_CMD=py -3

:python_found
for /f "tokens=*" %%v in ('%PYTHON_CMD% --version 2^>^&1') do echo   Found: %%v

:: ── 2. Install Python dependencies ───────────────────────────────────────────
echo.
echo   Installing Python dependencies...
%PYTHON_CMD% -m pip install --quiet --upgrade pip
%PYTHON_CMD% -m pip install --quiet -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo   [ERROR] pip install failed. Check your internet connection and try again.
    pause
    exit /b 1
)
echo   Dependencies installed.

:: ── 3. Copy files to install directory ───────────────────────────────────────
set INSTALL_DIR=%APPDATA%\simpleScreen

echo.
echo   Installing to: %INSTALL_DIR%

if not exist "%INSTALL_DIR%"           mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\lib"       mkdir "%INSTALL_DIR%\lib"
if not exist "%INSTALL_DIR%\templates" mkdir "%INSTALL_DIR%\templates"

copy /Y "%~dp0simpleScreen"      "%INSTALL_DIR%\simpleScreen"      >nul
copy /Y "%~dp0simpleScreen.bat"  "%INSTALL_DIR%\simpleScreen.bat"  >nul
copy /Y "%~dp0requirements.txt"  "%INSTALL_DIR%\requirements.txt"  >nul
copy /Y "%~dp0lib\*.py"          "%INSTALL_DIR%\lib\"              >nul
copy /Y "%~dp0templates\*"       "%INSTALL_DIR%\templates\"        >nul

echo   Files copied.

:: ── 4. Add install directory to user PATH ────────────────────────────────────
echo.
echo   Adding simpleScreen to your PATH...

echo %PATH% | findstr /I /C:"%INSTALL_DIR%" >nul
if not errorlevel 1 (
    echo   Already in PATH — skipping.
    goto :path_done
)

:: Read the current user PATH from the registry and append the install dir.
set REG_PATH=
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set REG_PATH=%%b
if "!REG_PATH!" == "" (
    setx PATH "%INSTALL_DIR%"
) else (
    setx PATH "!REG_PATH!;%INSTALL_DIR%"
)
if errorlevel 1 (
    echo   [WARNING] Could not update PATH automatically.
    echo   Please add this directory to your PATH manually:
    echo   %INSTALL_DIR%
) else (
    echo   PATH updated.
)

:path_done

:: ── 5. Verify OpenSSH client ──────────────────────────────────────────────────
echo.
echo   Checking for OpenSSH client...
where ssh >nul 2>&1
if errorlevel 1 (
    echo   [WARNING] OpenSSH client not found.
    echo   To enable: Settings ^> Apps ^> Optional Features ^> OpenSSH Client
    echo   simpleScreen will still work for local sessions without it.
) else (
    echo   OpenSSH client found.
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo =====================================================
echo   Installation complete!
echo =====================================================
echo.
echo   Open a NEW terminal window and run:
echo.
echo     simpleScreen
echo.
echo   to get started.
echo.
pause
endlocal
