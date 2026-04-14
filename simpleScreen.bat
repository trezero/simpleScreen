@echo off
:: simpleScreen Windows launcher
:: Uses the 'py' launcher (py.exe in System32) when available — it handles
:: multiple installed Python versions correctly. Falls back to 'python'.

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    py -3 "%~dp0simpleScreen" %*
) else (
    python "%~dp0simpleScreen" %*
)
