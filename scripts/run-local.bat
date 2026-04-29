@echo off
REM Run script for local development (Windows)

echo.
echo ========================================
echo  Insights Chatbot Local Development
echo ========================================
echo.
echo This script starts both backend and frontend servers.
echo You should have 2 terminals open:
echo   - Terminal 1: Backend (FastAPI)
echo   - Terminal 2: Frontend (Next.js)
echo.
echo Choose which to start:
echo   1. Backend only
echo   2. Frontend only
echo   3. Both (requires 2 terminals)
echo.

set /p choice="Enter choice (1-3): "

if "%choice%"=="1" (
    call :start_backend
) else if "%choice%"=="2" (
    call :start_frontend
) else if "%choice%"=="3" (
    echo.
    echo Starting both backend and frontend...
    echo Please open another terminal window and run:
    echo   cd frontend
    echo   npm run dev
    echo.
    call :start_backend
) else (
    echo Invalid choice
    exit /b 1
)

exit /b 0

:start_backend
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Starting FastAPI backend at http://localhost:8000
echo API docs: http://localhost:8000/docs
echo.
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
exit /b 0

:start_frontend
cd frontend
echo.
echo Starting Next.js frontend at http://localhost:3000
echo.
npm run dev
exit /b 0
