@echo off
rem Foam Measuring Tool launcher for Windows.
rem First run: creates a private Python environment (.venv) and installs
rem the required packages. Later runs start the app straight away.

cd /d "%~dp0"

if exist ".venv\installed.txt" goto run

set "PYTHON="
where py >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON goto nopython

echo Setting up Foam Measuring Tool (first run only, this can take a few minutes)...

if not exist ".venv\Scripts\python.exe" (
    %PYTHON% -m venv .venv || goto nopython
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto failed

echo done > ".venv\installed.txt"

:run
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
exit /b

:nopython
echo.
echo Python 3.11 or newer was not found.
echo Install it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during installation, then run this again.
pause
exit /b 1

:failed
echo.
echo Installing the required packages failed. Check your internet connection
echo and run this file again.
pause
exit /b 1
