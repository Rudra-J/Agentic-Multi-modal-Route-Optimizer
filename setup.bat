@echo off
REM Quick setup script for development environment (Windows)
REM Run this after cloning: setup.bat

echo 🚀 Setting up Agentic Auto Routing System...

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.9+ from https://python.org
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python version: %PYTHON_VERSION%

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ❌ Failed to create virtual environment
    exit /b 1
)

REM Activate virtual environment
echo ✓ Virtual environment created
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
set PIP_TRUSTED_HOST_ARGS=--trusted-host pypi.org --trusted-host files.pythonhosted.org
python -m pip install --upgrade pip %PIP_TRUSTED_HOST_ARGS%
pip install -r requirements.txt %PIP_TRUSTED_HOST_ARGS%
if %errorlevel% neq 0 (
    echo ❌ Failed to install dependencies
    exit /b 1
)

echo ✓ Dependencies installed

REM Setup environment file
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env
    echo ⚠️  Please edit .env and add your OPENROUTER_API_KEY
) else (
    echo ✓ .env file exists
)

echo.
echo ✅ Setup complete!
echo.
echo 📋 Next steps:
echo 1. Edit .env and add your OpenRouter API key
echo 2. Run tests: python test_harness.py
echo 3. Start server: uvicorn main:app --reload --port 8001
echo 4. Visit: http://127.0.0.1:8001/
echo.
pause
