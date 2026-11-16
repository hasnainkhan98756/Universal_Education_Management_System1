@echo off
title Universal Education Management System (UEMS)
cd /d "%~dp0"
echo ===================================================
echo   Universal Education Management System (UEMS)
echo   Starting desktop application...
echo ===================================================
venv\Scripts\python.exe main.py
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
