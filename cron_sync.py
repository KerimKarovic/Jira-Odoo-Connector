#!/usr/bin/env python3
"""
Cron-compatible sync script for JIRA-Odoo sync
Handles environment setup and error handling for automated execution
"""

import sys
import os
import logging
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main cron execution function"""
    try:
        # Import after path setup
        from utils import setup_logging, validate_config
        from main import main as sync_main
        from email_notifier import email_notifier
        
        # Setup logging for cron
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"logs/cron_sync_{timestamp}.log"
        setup_logging(log_file)
        
        logging.info("=== CRON SYNC STARTED ===")
        logging.info(f"Python path: {sys.executable}")
        logging.info(f"Working directory: {os.getcwd()}")
        
        # Validate configuration
        validate_config()
        logging.info("Configuration validated successfully")
        
        # Run the main sync
        sync_main()
        
        logging.info("=== CRON SYNC COMPLETED SUCCESSFULLY ===")
        
    except Exception as e:
        # Critical error - send immediate notification
        logging.error(f"CRITICAL: Cron sync failed: {e}")
        try:
            email_notifier.send_critical_error_immediate(
                e, 
                "Cron job execution failure - sync could not run"
            )
        except:
            pass  # Don't fail if email also fails
        
        # Exit with error code for cron monitoring
        sys.exit(1)

if __name__ == "__main__":
    main()