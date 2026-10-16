@echo off
title Electron Microscope Autofocus Lab Suite (macOS Experience)
color 0B

echo ===============================================================================
echo       ELECTRON MICROSCOPE AUTOFOCUS ARCHITECTURE & 10-METHOD LAB SUITE
echo ===============================================================================
echo.
echo [1/2] Initializing Fast Python Backend (FastAPI + Uvicorn)...
set PYTHON_EXE=C:\Users\PC\AppData\Local\Programs\Python\Python312\python.exe

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Global Python executable not found at %PYTHON_EXE%
    echo Falling back to system python...
    set PYTHON_EXE=python
)

start "Autofocus Backend Server" /min "%PYTHON_EXE%" -m uvicorn autofocus_suite.server.app:app --host 127.0.0.1 --port 8000

echo [2/2] Waiting for server startup...
timeout /t 2 /nobreak >nul

echo [3/3] Launching macOS-Style Desktop Application Window...
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://127.0.0.1:8000 --window-size=1440,940
) else if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --app=http://127.0.0.1:8000 --window-size=1440,940
) else (
    start http://127.0.0.1:8000
)

echo.
echo ===============================================================================
echo  Application is running at: http://127.0.0.1:8000
echo  Press Ctrl+C in backend window to shut down.
echo ===============================================================================
echo.
