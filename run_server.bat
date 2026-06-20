@echo off
:: Navigate to the directory of this script
cd /d "%~dp0"

echo ===================================================
echo [START] Django Auto-Restart Server Script
echo ===================================================

:: Check if virtual environment python exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment Python .venv\Scripts\python.exe not found!
    echo [INFO] Please create one using: python -m venv .venv
    pause
    exit /b
)

echo [INFO] Installing/Checking dependencies...
.venv\Scripts\python -m pip install -r requirements.txt

:loop
echo [INFO] Starting Django server at http://0.0.0.0:4321/
echo [INFO] To stop the server permanently, close this CMD window or press Ctrl+C.
echo ---------------------------------------------------

:: Run the Django development server using venv python directly
.venv\Scripts\python manage.py runserver 0.0.0.0:4321

echo ---------------------------------------------------
echo [WARNING] Django server crashed or stopped with exit code %ERRORLEVEL%.
echo [INFO] Restarting in 5 seconds...
echo ---------------------------------------------------
timeout /t 5
goto loop

