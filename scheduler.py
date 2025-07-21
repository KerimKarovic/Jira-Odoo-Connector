#!/usr/bin/env python3
"""
Scheduler for JIRA to Odoo Timesheet Sync
Runs the sync at specified intervals
"""

import time
import sys
import logging
from datetime import datetime
from main import main

def setup_scheduler_logging():
    """Setup logging for scheduler"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - SCHEDULER - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scheduler.log'),
            logging.StreamHandler()
        ]
    )

def run_scheduler(interval_minutes=60):
    """
    Run the sync at specified intervals
    Args:
        interval_minutes: Minutes between sync runs
    """
    setup_scheduler_logging()
    
    logging.info(f"🚀 Starting scheduler with {interval_minutes} minute intervals")
    
    while True:
        try:
            logging.info("⏰ Starting scheduled sync...")
            start_time = datetime.now()
            
            # Run the main sync
            main()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logging.info(f"✅ Sync completed in {duration:.2f} seconds")
            
            # Wait for next interval
            logging.info(f"😴 Sleeping for {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            logging.info("🛑 Scheduler stopped by user")
            break
        except Exception as e:
            logging.error(f"❌ Error in scheduler: {e}")
            logging.info(f"🔄 Retrying in {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    # Get interval from command line argument
    interval = 60  # Default 60 minutes
    
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid interval. Using default 60 minutes.")
    
    print(f"🚀 Starting JIRA-Odoo Sync Scheduler (interval: {interval} minutes)")
    run_scheduler(interval)
