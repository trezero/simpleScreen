@echo off
:: simpleScreen Windows launcher
:: Uses the Python interpreter from the venv created by install.bat.
"%~dp0venv\Scripts\python.exe" "%~dp0simpleScreen" %*
