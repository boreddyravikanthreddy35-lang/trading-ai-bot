@echo off
title SignalForge - AI Trading Platform
color 0A
echo.
echo  ========================================
echo   SignalForge AI Trading Platform
echo   Starting all services...
echo  ========================================
echo.

:: Start MongoDB
echo [1/3] Starting MongoDB...
start "MongoDB" /MIN "C:\Program Files\MongoDB\Server\8.3\bin\mongod.exe" --dbpath "C:\Users\RAVIKANTH\mongodb-data" --port 27017
timeout /t 3 /nobreak >nul
echo       MongoDB started on port 27017

:: Start Backend
echo [2/3] Starting Backend API...
start "SignalForge Backend" /MIN cmd /c "cd /d "%~dp0backend" && python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 5 /nobreak >nul
echo       Backend started on http://localhost:8000

:: Start Frontend
echo [3/3] Starting Frontend...
start "SignalForge Frontend" /MIN cmd /c "cd /d "%~dp0frontend" && npm start"
timeout /t 3 /nobreak >nul
echo       Frontend starting on http://localhost:3000

echo.
echo  ========================================
echo   All services started!
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo  ========================================
echo.
echo  Opening browser in 10 seconds...
timeout /t 10 /nobreak >nul
start http://localhost:3000
echo.
echo  Press any key to stop all services...
pause >nul

:: Stop all services
echo Stopping all services...
taskkill /F /FI "WINDOWTITLE eq MongoDB" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq SignalForge Backend" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq SignalForge Frontend" >nul 2>&1
taskkill /F /IM mongod.exe >nul 2>&1
echo Done.
