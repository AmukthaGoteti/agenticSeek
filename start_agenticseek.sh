@echo off
REM filepath: /Users/amukthagoteti/agenticSeek/start_agenticseek.sh
REM Updated for venv312 and local search proxy

echo Starting AgenticSeek System...
echo.

REM Check if Ollama is running
echo Checking Ollama status...
powershell -Command "try { Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -Method GET -TimeoutSec 5 | Out-Null; Write-Host 'Ollama is running' -ForegroundColor Green } catch { Write-Host 'Starting Ollama...' -ForegroundColor Yellow; Start-Process 'ollama' -ArgumentList 'serve' -WindowStyle Minimized }"
timeout /t 3 /nobreak >nul

REM Start local search proxy in a new window
echo Starting Local Search Proxy...
start "Local Search Proxy" cmd /k "venv\Scripts\activate && python local_search.py"
timeout /t 3 /nobreak >nul

REM Start backend in a new command window
echo Starting AgenticSeek Backend...
start "AgenticSeek Backend" cmd /k "venv\Scripts\activate && python api.py"
timeout /t 5 /nobreak >nul

REM Start frontend in a new command window
echo Starting AgenticSeek Frontend...
cd frontend\agentic-seek-front
start "AgenticSeek Frontend" cmd /k "npm start"
timeout /t 5 /nobreak >nul

REM Open the frontend in the default browser
echo Opening AgenticSeek Dashboard...
start http://localhost:3000

REM Return to the original directory
cd ..\..

echo.
echo AgenticSeek System Started!
echo.
echo Services running:
echo - Frontend Dashboard: http://localhost:3000
echo - Backend API: http://localhost:8000
echo - Local Search Proxy: http://localhost:5000
echo - Ollama LLM Server: http://localhost:11434
echo.
echo Press any key to exit...
pause >nul