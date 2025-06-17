@echo off
REM AgenticSeek MCP Fault-Tolerant Startup Script
REM This version starts the fault-tolerant MCP architecture with individual agent servers

echo ========================================
echo       AgenticSeek MCP Architecture
echo     Fault-Tolerant Agent System v2.0
echo ========================================

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv312\Scripts\activate.bat" (
    echo ❌ Error: Virtual environment not found!
    echo Please run: python -m venv venv312
    echo Then run: venv312\Scripts\activate.bat
    echo And install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🐍 Activating Python virtual environment...
call venv312\Scripts\activate.bat

REM Check if Ollama is running
echo 🧠 Checking Ollama LLM server...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Warning: Ollama server not responding on localhost:11434
    echo Please start Ollama manually if you want to use local LLM
    echo You can continue without it for testing purposes.
    timeout /t 3
)

echo.
echo 🚀 Starting AgenticSeek MCP Services...
echo.

REM Start services in order with health checks
echo [1/7] 🔍 Starting Local Search Proxy (Port 5001)...
start "Local Search Proxy" cmd /k "echo Local Search Proxy & python local_search.py"
timeout /t 3

echo [2/7] 🌐 Starting Browser Agent Server (Port 8001)...
start "Browser Agent" cmd /k "echo Browser Agent Server & python mcp_agents\browser_agent_server.py 8001"
timeout /t 2

echo [3/7] 💻 Starting Code Agent Server (Port 8002)...
start "Code Agent" cmd /k "echo Code Agent Server & python mcp_agents\code_agent_server.py 8002"
timeout /t 2

echo [4/7] 📁 Starting File Agent Server (Port 8003)...
start "File Agent" cmd /k "echo File Agent Server & python mcp_agents\file_agent_server.py 8003"
timeout /t 2

echo [5/7] 💬 Starting Casual Agent Server (Port 8004)...
start "Casual Agent" cmd /k "echo Casual Agent Server & python mcp_agents\casual_agent_server.py 8004"
timeout /t 2

echo [6/7] 📋 Starting Planner Agent Server (Port 8005)...
start "Planner Agent" cmd /k "echo Planner Agent Server & python mcp_agents\planner_agent_server.py 8005"
timeout /t 3

echo [7/7] 🎯 Starting Main MCP API Server (Port 8000)...
echo.
echo ========================================
echo          Services Status
echo ========================================
echo ✅ Local Search Proxy:  http://localhost:5001
echo ✅ Browser Agent:       http://localhost:8001
echo ✅ Code Agent:          http://localhost:8002
echo ✅ File Agent:          http://localhost:8003
echo ✅ Casual Agent:        http://localhost:8004
echo ✅ Planner Agent:       http://localhost:8005
echo ✅ Main API Server:     http://localhost:8000
echo.
echo 🎯 Now starting Main API Server with fault-tolerant routing...
echo 🔄 The system will automatically monitor and restart failed agents
echo 🌐 Frontend available at: http://localhost:3000
echo.
echo ⚡ MCP Features Enabled:
echo   - Fault isolation (agent crashes won't affect others)
echo   - Automatic agent restart on failure
echo   - Intelligent fallback routing
echo   - Hot-swapping of individual agents
echo   - Health monitoring and alerts
echo.

REM Start the main MCP API server
python mcp_api.py

echo.
echo ========================================
echo        Shutdown Complete
echo ========================================
echo All MCP services have been stopped.
echo Agent processes may still be running in separate windows.
echo Use startup_scripts\stop_all_agents.bat to stop everything.
pause
