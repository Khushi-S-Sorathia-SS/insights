@echo off
REM Setup script for Employee Dataset Insight Chatbot (Windows)
REM This script initializes the project environment

echo.
echo ========================================
echo  Insights Chatbot Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org/
    exit /b 1
)

echo [✓] Python and Node.js found
echo.

REM Create virtual environment
echo [1/4] Creating Python virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    exit /b 1
)
echo [✓] Virtual environment created
echo.

REM Activate virtual environment
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    exit /b 1
)
echo [✓] Virtual environment activated
echo.

REM Install Python dependencies
echo [3/4] Installing Python dependencies...
python.exe -m pip install --upgrade pip
python.exe -m pip install -r backend/requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies
    exit /b 1
)
echo [✓] Python dependencies installed
echo.

REM Install Node dependencies
echo [4/4] Installing Node.js dependencies...
cd frontend
npm install --silent
if errorlevel 1 (
    echo ERROR: Failed to install Node dependencies
    cd ..
    exit /b 1
)
cd ..
echo [✓] Node.js dependencies installed
echo.

REM Copy env template
if not exist .env.local (
    echo [i] Copying .env.example to .env.local
    copy .env.example .env.local
    echo [!] Please edit .env.local and add your Azure and LangSmith credentials
)

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo Next steps:
echo.
echo 1. Edit .env.local and add your Azure OpenAI and LangSmith credentials:
echo    AZURE_OPENAI_API_KEY=your-key-here
echo    AZURE_OPENAI_ENDPOINT=your-endpoint
echo    AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
echo    LANGSMITH_API_KEY=your-key-here
echo    LANGSMITH_PROJECT=Insights
echo.
echo 2. Start the backend (new terminal):
echo    venv\Scripts\activate.bat
echo    python -m uvicorn backend.main:app --reload
echo.
echo 3. Start the frontend (another terminal):
echo    cd frontend
echo    npm run dev
echo.
echo 4. Open browser to http://localhost:3000
echo.
pause
