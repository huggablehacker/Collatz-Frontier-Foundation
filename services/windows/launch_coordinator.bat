@echo off
setlocal enabledelayedexpansion
title Collatz Frontier — Coordinator

:: ============================================================
:: launch_coordinator.bat
:: Double-click this to start the Collatz coordinator.
:: ============================================================

echo.
echo ============================================================
echo  Collatz Frontier — Coordinator
echo ============================================================
echo.

:: ── Optional: set your GitHub token for nightly uploads ──────
:: Uncomment and fill in your token if using the nightly uploader:
:: set GITHUB_TOKEN=ghp_your_token_here

:: ── Configuration ─────────────────────────────────────────────
:: Change these if needed:
set PORT=5555
set CHUNK=500000

:: START_N defaults to 2^68 (built into the program).
:: To resume from a specific n, uncomment and set:
:: set START_N=295147905179352825857

:: ── Firewall notice ───────────────────────────────────────────
echo  NOTE: Windows Firewall may ask permission to allow network
echo  access. Click "Allow access" so workers can connect.
echo.

:: ── Check if already running ─────────────────────────────────
netstat -ano 2>nul | findstr ":%PORT% " >nul
if not errorlevel 1 (
    echo  WARNING: Something is already listening on port %PORT%.
    echo  The coordinator may already be running.
    echo  Close the other window first, or change PORT in this script.
    echo.
    pause
    exit /b 1
)

:: ── Print connection info ─────────────────────────────────────
echo  Workers connect to:
for /f "tokens=*" %%i in ('powershell -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike '*Loopback*'} | Select-Object -First 1).IPAddress"') do (
    echo    python3 collatz_worker.py --coordinator http://%%i:%PORT%
    echo.
    echo  Dashboard: http://%%i:%PORT%/status
    echo  Workers:   http://%%i:%PORT%/workers
    echo  Milestones:http://%%i:%PORT%/milestones
)
echo.
echo  Press Ctrl+C to stop (checkpoint saved automatically).
echo.
echo ============================================================
echo.

:: ── Launch ────────────────────────────────────────────────────
if defined START_N (
    collatz_coordinator.exe --port %PORT% --chunk %CHUNK% --start %START_N%
) else (
    collatz_coordinator.exe --port %PORT% --chunk %CHUNK%
)

echo.
echo  Coordinator stopped.
pause
