@echo off
echo Starting Tuya Monitor...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install backend dependencies if needed
echo Installing backend dependencies...
cd python_backend
pip install -r requirements.txt >nul 2>&1
echo Backend dependencies installed.
echo.

REM Start backend server in background
echo Starting backend server...
start "Backend Server" cmd /k "python tuya_server.py"
timeout /t 3 /nobreak >nul

REM Start Flutter app
echo Starting Flutter app...
cd ..
flutter run

REM Keep window open if there's an error
if errorlevel 1 pause
