#!/bin/bash

echo "Starting Tuya Monitor..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pip3 install -r requirements.txt > /dev/null 2>&1
echo "Backend dependencies installed."
echo ""

# Start backend server in background
echo "Starting backend server..."
python3 server.py &
BACKEND_PID=$!
sleep 3

# Start Flutter app
echo "Starting Flutter app..."
cd ..
flutter run

# Cleanup: kill backend when Flutter exits
kill $BACKEND_PID 2>/dev/null
