#!/bin/bash

# Quick backend restart script
echo "🔄 Restarting FastAPI Backend..."

# Kill all Python processes running on ports 8000 and 8001
echo "🛑 Stopping existing services..."

# Kill FastAPI (port 8000)
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "   Killing FastAPI on port 8000..."
    kill -9 $(lsof -ti:8000) 2>/dev/null || true
fi

# Kill Chainlit (port 8001) 
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
    echo "   Killing Chainlit on port 8001..."
    kill -9 $(lsof -ti:8001) 2>/dev/null || true
fi

# Wait a moment for cleanup
sleep 3

echo "✅ Services stopped"
echo ""
echo "🚀 Starting services..."

# Start FastAPI in background
echo "   Starting FastAPI backend..."
./start_fastapi.sh &
FASTAPI_PID=$!

# Wait for FastAPI to be ready
echo "   Waiting for FastAPI to start..."
sleep 5

# Check if FastAPI is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ FastAPI is running"
else
    echo "   ⚠️ FastAPI might not be ready yet"
fi

# Start Chainlit in background
echo "   Starting Chainlit frontend..."
./start_chainlit.sh &
CHAINLIT_PID=$!

echo ""
echo "🎉 Services restarted!"
echo "📍 FastAPI Backend: http://localhost:8000"
echo "📍 Chainlit Frontend: http://localhost:8001"
echo ""
echo "💡 To monitor backend health, run: python monitor_backend.py"
echo "🛑 To stop all services, run: ./stop_services.sh"
