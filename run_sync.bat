@echo off
:: Enhanced wrapper script for Windows Task Scheduler

:: Set UTF-8 code page for proper emoji display
chcp 65001 > nul 2>&1

:: Change to the project directory (explicit path)
cd /d "C:\Users\KerimKarovic\jira_odoo_sync"

:: Set environment variables for Python
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

:: Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

:: Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

:: Run the sync script and capture output
echo Starting JIRA-Odoo sync at %date% %time%
python cron_sync_simple.py

:: Log the exit code
echo Sync completed with exit code: %ERRORLEVEL%

:: Deactivate virtual environment if it was activated
if exist "venv\Scripts\activate.bat" (
    deactivate
)

:: Keep window open for debugging (remove for production)
:: pause

