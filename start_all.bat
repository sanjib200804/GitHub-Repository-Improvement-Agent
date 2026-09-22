@echo off
setlocal enabledelayedexpansion

title Personal AI Action Agent - Multi-MCP
color 0A

:: Navigate to script directory
cd /d "%~dp0"

echo ======================================================================
echo          PERSONAL AI ACTION AGENT (GITHUB + LINKEDIN MCP)            
echo ======================================================================
echo.

:: Check Python installation
where python >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python was not found in PATH!
    echo Please install Python 3.10+ and add it to your system PATH.
    pause
    exit /b 1
)

:: Check if virtual environment exists and activate if present
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment: venv...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment: .venv...
    call .venv\Scripts\activate.bat
)

:: Check .env configuration
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] .env not found. Creating from .env.example...
        copy .env.example .env >nul
        echo [WARNING] Please update .env with your credentials if needed.
    )
)

echo [INFO] Verifying dependencies...
python -c "import streamlit, mcp, langchain, langgraph" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing required dependencies from requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        color 0C
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo.
echo ======================================================================
echo   Starting Streamlit Web Dashboard: http://localhost:8501
echo   - GitHub MCP Server: Enabled (6 tools)
echo   - LinkedIn MCP Server: Enabled (5 tools)
echo   - Multi-MCP Agent Reasoning: Active
echo ======================================================================
echo.

:: Open default browser after a brief pause
start "" http://localhost:8501

:: Run Streamlit application
streamlit run frontend/app.py

pause
