#!/bin/bash

# Stop all services script
echo "🛑 Stopping all services..."

# Kill FastAPI (port 8000)
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "   Stopping FastAPI on port 8000..."
    kill -9 $(lsof -ti:8000) 2>/dev/null || true
    echo "   ✅ FastAPI stopped"
else
    echo "   ℹ️ FastAPI not running on port 8000"
fi

# Kill Chainlit (port 8001)
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
    echo "   Stopping Chainlit on port 8001..."
    kill -9 $(lsof -ti:8001) 2>/dev/null || true
    echo "   ✅ Chainlit stopped"
else
    echo "   ℹ️ Chainlit not running on port 8001"
fi

# Kill any other Python processes that might be related
echo "   Cleaning up any remaining Python processes..."
pkill -f "chainlit_app.py" 2>/dev/null || true
pkill -f "src/api/main.py" 2>/dev/null || true

echo ""
echo "✅ All services stopped successfully!"
echo ""
echo "🚀 To restart services, run: ./restart_services.sh"
