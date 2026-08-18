@echo off
rem ============================================================
rem  Game Pixel Ruler - launcher
rem  Uses the project Python at H:\Dev\Python312
rem ============================================================
set "PY=H:\Dev\Python312\python.exe"

if not exist "%PY%" (
    echo [ERROR] Python 3.12 not found at %PY%.
    echo Install Python 3.12+ into H:\Dev\Python312, or edit the
    echo PY variable at the top of this script.
    pause
    exit /b 1
)

"%PY%" main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Program exited with an error. See messages above.
    pause
)
