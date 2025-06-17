#!/bin/zsh
echo "===================================="
echo "🚀 AgenticSeek MCP System"
echo "Complete Startup Script (macOS/Linux)"
echo "===================================="

# Set working directory to script's location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
  echo "❌ Virtual environment 'venv' not found!"
  echo "Please create it with:"
  echo "  python3 -m venv venv"
  echo "  source venv/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Check Node.js
if ! command -v node >/dev/null 2>&1; then
  echo "⚠️ Node.js not found! Frontend will not start."
  SKIP_FRONTEND=true
else
  echo "✅ Node.js found"
  SKIP_FRONTEND=false
fi

# Check Ollama
echo "🔍 Checking Ollama status..."
if curl -s http://localhost:11434/api/tags >/dev/null; then
  echo "✅ Ollama is running"
else
  echo "⚠️ Ollama not responding. Start it manually if needed."
fi

echo
echo "🚀 Starting Backend Services..."

# Start each backend service in a new terminal tab/window
echo "[1/7] Local Search Proxy..."
nohup python3 local_search.py > logs/local_search.log 2>&1 &

echo "[2/7] Code Agent Server..."
nohup python3 mcp_agents/code_agent_server.py 8002 > logs/code_agent.log 2>&1 &

echo "[3/7] File Agent Server..."
nohup python3 mcp_agents/file_agent_server.py 8003 > logs/file_agent.log 2>&1 &

echo "[4/7] Casual Agent Server..."
nohup python3 mcp_agents/casual_agent_server.py 8004 > logs/casual_agent.log 2>&1 &

echo "[5/7] Planner Agent Server..."
nohup python3 mcp_agents/planner_agent_server.py 8005 > logs/planner_agent.log 2>&1 &

echo "[6/7] Simple Browser Agent Server..."
nohup python3 mcp_agents/simple_browser_agent_server.py 8001 > logs/browser_agent.log 2>&1 &

echo "[7/7] Main MCP API Server..."
nohup python3 mcp_api.py > logs/main_api.log 2>&1 &

echo "✅ Backend services started"
echo

# Frontend
if [ "$SKIP_FRONTEND" = false ]; then
  echo "🌐 Starting Frontend..."

  cd frontend/agentic-seek-front || exit 1

  if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install || { echo "❌ npm install failed"; exit 1; }
  fi

  echo "🚀 Launching React dev server..."
  npm start &
  cd "$SCRIPT_DIR"
  echo "✅ Frontend server starting..."
else
  echo "⚠️ Skipping frontend (Node.js not installed)"
fi

echo
echo "🎉 All services are running!"
echo
echo "📍 Open in browser:"
echo "  - Frontend Dashboard:      http://localhost:3000"
echo "  - Backend API Docs:        http://localhost:8000/docs"
echo "  - System Status:           http://localhost:8000/system_status"
echo
echo "Press Ctrl+C to stop this terminal. Services will continue running in background."
