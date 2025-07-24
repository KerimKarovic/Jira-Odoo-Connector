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
from email_notifier import email_notifier

def run_cron_sync():
    """Run sync with detailed logging"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/sync_{timestamp}.log"
    
    # Enhanced logging format
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logging.info("=== CRON SYNC STARTED ===")
    logging.info(f"Log file: {log_file}")
    
    try:
        validate_config()
        logging.info("Configuration validated successfully")
        
        start_time = datetime.now()
        logging.info(f"Sync started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run sync
        main()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logging.info(f"=== SYNC COMPLETED in {duration:.2f} seconds ===")
        
        return True
        
    except Exception as e:
        logging.error(f"CRITICAL: Cron sync failed - {e}")
        return False
    finally:
        logging.info("Cron job execution completed")

if __name__ == "__main__":
    # Run the sync
    success = run_cron_sync()
    
    # Exit with appropriate code for cron job monitoring
    sys.exit(0 if success else 1)
