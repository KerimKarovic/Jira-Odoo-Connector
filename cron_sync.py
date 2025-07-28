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
        from utils import validate_config
        from main import main as sync_main
        
        # Validate configuration
        validate_config()
        
        # Run the main sync (context manager handles logging)
        sync_main()
        
    except Exception as e:
        # Critical error - send immediate notification
        try:
            from email_notifier import email_notifier
            email_notifier.send_critical_error_immediate(e, "Cron job execution failure")
        except:
            pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()
