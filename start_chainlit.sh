#!/bin/bash

# Start Chainlit frontend
echo "Starting Chainlit frontend..."
cd src/chainlit
chainlit run chainlit_app.py --port 8001 