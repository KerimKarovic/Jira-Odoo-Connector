#!/usr/bin/env python3
"""
JIRA to Odoo Worklog Sync - Windows Task Scheduler Script
Simplified script optimized for Windows environments
"""

import sys
import os
import logging
from datetime import datetime
from main import main
from utils import validate_config

def run_windows_sync():
    """Run the sync process with Windows-friendly logging"""
    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("logs", exist_ok=True)
    log_file = f"logs/sync_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - WINDOWS - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logging.info("Starting JIRA-Odoo sync via Windows Task Scheduler")
    
    try:
        # Validate and run
        validate_config()
        
        start_time = datetime.now()
        logging.info(f"Sync started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        main()
        
        # Log completion
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logging.info(f"Sync completed in {duration:.2f} seconds")
        
        return True
        
    except Exception as e:
        logging.error(f"Windows sync failed: {e}")
        return False
    finally:
        logging.info("Task Scheduler job completed")

if __name__ == "__main__":
    success = run_windows_sync()
    sys.exit(0 if success else 1)