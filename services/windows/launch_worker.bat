@echo off
setlocal enabledelayedexpansion
title Collatz Frontier — Worker

:: ============================================================
:: launch_worker.bat
:: Double-click this to start a Collatz worker.
:: You will be prompted for the coordinator IP.
:: ============================================================

echo.
echo ============================================================
echo  Collatz Frontier — Worker
echo ============================================================
echo.

:: ── Get coordinator address ───────────────────────────────────
set /p COORD_IP="  Enter coordinator IP address (e.g. 192.168.1.100): "

if "!COORD_IP!"=="" (
    echo  No IP entered. Exiting.
    pause
    exit /b 1
)

set COORDINATOR=http://!COORD_IP!:5555

:: ── Worker name ───────────────────────────────────────────────
for /f "tokens=*" %%i in ('hostname') do set DEFAULT_NAME=%%i
set /p WORKER_NAME="  Worker name [!DEFAULT_NAME!]: "
if "!WORKER_NAME!"=="" set WORKER_NAME=!DEFAULT_NAME!

:: ── Cores ─────────────────────────────────────────────────────
for /f "tokens=*" %%i in ('powershell -Command "[System.Environment]::ProcessorCount"') do set CPU_COUNT=%%i
set /p CORES="  CPU cores to use [!CPU_COUNT! / all]: "
if "!CORES!"=="" set CORES=!CPU_COUNT!

echo.
echo ============================================================
echo  Starting worker
echo    Coordinator : !COORDINATOR!
echo    Worker name : !WORKER_NAME!
echo    CPU cores   : !CORES!
echo ============================================================
echo.
echo  Press Ctrl+C to stop.
echo.

collatz_worker.exe --coordinator !COORDINATOR! --name !WORKER_NAME! --cores !CORES!

echo.
echo  Worker stopped.
pause
