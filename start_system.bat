@echo off
title SmartAttend-AI Master System Launcher
color 0A
echo ======================================================================
echo          SMARTATTEND-AI: STARTING FULL SYSTEM (BACKEND + FRONTEND)
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Activating Virtual Environment and Checking Dependencies...
call .\venv\Scripts\activate

echo.
echo [2/3] Starting FastAPI Backend on http://localhost:8000 ...
start "SmartAttend-AI Backend" cmd /k ".\venv\Scripts\python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 >nul

echo.
echo [3/3] Starting React Vite Frontend on http://localhost:5173 ...
cd frontend
start "SmartAttend-AI Frontend" cmd /k "npm run dev -- --host 0.0.0.0"

echo.
echo ======================================================================
echo  SmartAttend-AI is now running LIVE!
echo  - Faculty Dashboard : http://localhost:5173
echo  - Backend API Docs  : http://localhost:8000/docs
echo ======================================================================
echo.
pause
