#!/usr/bin/env python3
"""
JIRA to Odoo Worklogs Sync - Cron Job Script (Windows Compatible)
This script is designed to be run as a cron job with simple text output.
"""

import sys
import os
import logging
from datetime import datetime
from main import main
from utils import validate_config

def run_cron_sync():
    """
    Run the sync process as a cron job with proper logging
    """
    # Setup logging with timestamp in filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = "logs"
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    log_file = f"{log_dir}/sync_{timestamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - CRON - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Log start of sync
    logging.info("Starting JIRA-Odoo sync via cron job")
    
    try:
        # Validate configuration
        validate_config()
        
        # Record start time
        start_time = datetime.now()
        logging.info(f"Sync started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run the main sync process
        main()
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logging.info(f"Sync completed in {duration:.2f} seconds")
        
        return True
        
    except Exception as e:
        logging.error(f"Cron sync failed: {e}")
        return False
    finally:
        logging.info("Cron job execution completed")

if __name__ == "__main__":
    # Run the sync
    success = run_cron_sync()
    
    # Exit with appropriate code for cron job monitoring
    sys.exit(0 if success else 1)
