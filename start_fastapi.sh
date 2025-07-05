#!/bin/bash

# Start FastAPI backend with improved configuration
echo "Starting FastAPI backend with timeout protection..."

# Set environment variables for better performance
export PYTHONUNBUFFERED=1
export AZURE_CORE_PIPELINE_TIMEOUT=30

# Kill any existing FastAPI process on port 8000
echo "Checking for existing processes on port 8000..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Killing existing process on port 8000..."
    kill -9 $(lsof -ti:8000) 2>/dev/null || true
    sleep 2
fi

# Start the FastAPI server
echo "Starting FastAPI server..."
cd "$(dirname "$0")"
python src/api/main.py