#!/usr/bin/env python3
"""
JIRA to Odoo Timesheet Sync - Cron Job Script
This script is designed to be run as a cron job to automate the sync process.
"""

import sys
import os
import logging
from datetime import datetime
from main import main
from utils import setup_logging, validate_config

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
    
    # Configure logging with UTF-8 encoding for file handler
    log_file = f"{log_dir}/sync_{timestamp}.log"
    
    # Create file handler with UTF-8 encoding
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Create console handler with UTF-8 encoding (fallback to ASCII for Windows)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - CRON - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log start of sync (using simple text for Windows compatibility)
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
    # Set UTF-8 encoding for stdout on Windows
    if sys.platform.startswith('win'):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    
    # Run the sync
    success = run_cron_sync()
    
    # Exit with appropriate code for cron job monitoring
    sys.exit(0 if success else 1)
