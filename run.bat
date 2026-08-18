@echo off

rem Copyright (C) 2026 justplaymore
rem SPDX-License-Identifier: GPL-3.0-or-later
rem ============================================================
rem  Game Map Ruler - launcher
rem  Auto-detects Python 3.10+ (py launcher, then PATH python),
rem  skipping broken entries like the Microsoft Store stub.
rem ============================================================
setlocal

set "PY="

rem --- candidate 1: Windows py launcher ---
where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%i in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        if not defined PY (
            "%%i" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
            if not errorlevel 1 set "PY=%%i"
        )
    )
)

rem --- candidates 2..n: every python.exe in PATH ---
if not defined PY (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        if not defined PY (
            "%%i" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
            if not errorlevel 1 set "PY=%%i"
        )
    )
)

if not defined PY (
    echo [ERROR] Python 3.10+ not found.
    echo Install it from https://www.python.org/downloads/ and check
    echo "Add python.exe to PATH" during installation, then rerun.
    pause
    exit /b 1
)

"%PY%" main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Program exited with an error. See messages above.
    pause
)
endlocal
