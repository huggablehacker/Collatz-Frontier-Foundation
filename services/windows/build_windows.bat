@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: build_windows.bat
:: Collatz Frontier — Windows Package Builder
::
:: Run this ONCE on a Windows machine to:
::   1. Check Python is installed
::   2. Install all dependencies
::   3. Build collatz_coordinator.exe and collatz_worker.exe
::   4. Copy everything into a ready-to-distribute dist\ folder
::
:: Requires: Python 3.8+ (from python.org — NOT the Store version)
:: ============================================================

title Collatz Frontier — Windows Builder

echo.
echo ============================================================
echo  Collatz Frontier — Windows Package Builder
echo ============================================================
echo.

:: ── Check Python ─────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo.
    echo Please install Python 3.8 or later from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During install, check "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  Python found: %PYVER%

:: ── Install dependencies ──────────────────────────────────────
echo.
echo  Installing dependencies...
echo.

python -m pip install --upgrade pip --quiet
if errorlevel 1 goto pip_error

python -m pip install flask waitress requests pyinstaller --quiet
if errorlevel 1 goto pip_error

echo  Dependencies installed.

:: ── Optional: gmpy2 for faster big integers ──────────────────
echo.
echo  Attempting to install gmpy2 (optional — faster arithmetic)...
python -m pip install gmpy2 --quiet 2>nul
if errorlevel 1 (
    echo  gmpy2 not available ^(no pre-built wheel for this Python/OS^).
    echo  This is fine — the executables will still work correctly.
) else (
    echo  gmpy2 installed — executables will use fast GMP arithmetic.
)

:: ── Copy source files into build dir ─────────────────────────
echo.
echo  Preparing source files...

if not exist build_src mkdir build_src
copy /Y collatz_coordinator.py build_src\  >nul
copy /Y collatz_worker.py       build_src\  >nul
copy /Y coordinator.spec        build_src\  >nul
copy /Y worker.spec             build_src\  >nul
copy /Y uploader.spec           build_src\  >nul

:: ── Build executables ─────────────────────────────────────────
echo.
echo  Building collatz_coordinator.exe...
python -m PyInstaller coordinator.spec --distpath dist_build --workpath build_tmp --noconfirm --clean
if errorlevel 1 goto build_error

echo.
echo  Building collatz_worker.exe...
python -m PyInstaller worker.spec --distpath dist_build --workpath build_tmp --noconfirm --clean
if errorlevel 1 goto build_error

echo.
echo  Building collatz_upload_frontier.exe...
python -m PyInstaller uploader.spec --distpath dist_build --workpath build_tmp --noconfirm --clean
if errorlevel 1 goto build_error

:: ── Assemble final dist folder ────────────────────────────────
echo.
echo  Assembling distribution package...

if exist "Collatz-Frontier-Windows" rmdir /s /q "Collatz-Frontier-Windows"
mkdir "Collatz-Frontier-Windows"

copy /Y dist_build\collatz_coordinator.exe       "Collatz-Frontier-Windows\"  >nul
copy /Y dist_build\collatz_worker.exe            "Collatz-Frontier-Windows\"  >nul
copy /Y dist_build\collatz_upload_frontier.exe   "Collatz-Frontier-Windows\"  >nul
copy /Y launch_coordinator.bat                   "Collatz-Frontier-Windows\"  >nul
copy /Y launch_worker.bat                        "Collatz-Frontier-Windows\"  >nul
copy /Y README_WINDOWS.txt                       "Collatz-Frontier-Windows\"  >nul

:: Clean up build artifacts
rmdir /s /q build_tmp   2>nul
rmdir /s /q dist_build  2>nul
rmdir /s /q build_src   2>nul
del /f /q *.spec        2>nul

echo.
echo ============================================================
echo  BUILD COMPLETE
echo ============================================================
echo.
echo  Output folder: Collatz-Frontier-Windows\
echo.
echo  Contents:
echo    collatz_coordinator.exe      — run on ONE machine (the coordinator)
echo    collatz_worker.exe           — run on every worker machine
echo    collatz_upload_frontier.exe  — nightly GitHub uploader
echo    launch_coordinator.bat       — double-click to start coordinator
echo    launch_worker.bat            — double-click to start a worker
echo    README_WINDOWS.txt           — setup instructions
echo.
echo  To distribute: zip up the Collatz-Frontier-Windows\ folder
echo  and share it. No Python needed on the target machines.
echo.
pause
exit /b 0

:: ── Error handlers ────────────────────────────────────────────
:pip_error
echo.
echo ERROR: pip install failed.
echo Make sure you have an internet connection and try again.
pause
exit /b 1

:build_error
echo.
echo ERROR: PyInstaller build failed.
echo Check the output above for details.
echo Common fix: make sure all source .py files are in this folder.
pause
exit /b 1
