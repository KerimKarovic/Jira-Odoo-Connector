@echo off
echo Installing JIRA-Odoo Sync for Windows...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Create logs directory
if not exist "logs" mkdir logs

:: Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Please copy .env.template to .env and configure your settings
    copy .env.template .env
    echo .env file created from template. Please edit it with your credentials.
)

:: Test the sync
echo Testing sync configuration...
python main.py --test

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Edit .env file with your credentials
echo 2. Test manually: run_sync.bat
echo 3. Set up Windows Task Scheduler:
echo    - Open Task Scheduler
echo    - Create Basic Task: "JIRA-Odoo Sync"
echo    - Trigger: Daily (or your preferred schedule)
echo    - Action: Start a program
echo    - Program/script: %CD%\run_sync.bat
echo    - Start in: %CD%
echo.
pause
