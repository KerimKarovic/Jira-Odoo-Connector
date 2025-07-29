"""
Utility functions and configuration management
Handles environment variables, logging, and validation
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration object
config = {
    "jira": {
        "base_url": os.getenv("JIRA_BASE_URL"),
        "user": os.getenv("JIRA_USER"),
        "api_token": os.getenv("JIRA_API_TOKEN")
    },
    "tempo": {
        "api_token": os.getenv("TEMPO_API_TOKEN")
    },
    "odoo": {
        "url": os.getenv("ODOO_URL"),
        "db": os.getenv("ODOO_DB"),
        "username": os.getenv("ODOO_USERNAME"),
        "password": os.getenv("ODOO_PASSWORD")
    },
    "sync": {
        "lookback_hours": int(os.getenv("LOOKBACK_HOURS", "24"))
    }
}

def validate_config():
    """Validate all required environment variables"""
    required_vars = [
        "JIRA_BASE_URL", "JIRA_USER", "JIRA_API_TOKEN",
        "TEMPO_API_TOKEN",
        "ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")

# Validate configuration on import
validate_config()

class SyncSession:
    def __init__(self):
        self.log_file = None
        self.start_time = None
    
    def __enter__(self):
        """Setup logging and email session"""
        self.start_time = datetime.now()
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs/sync_{timestamp}.log"
        
        self.setup_session_logging()
        
        from email_notifier import email_notifier
        email_notifier.start_sync_session()
        
        logging.info(f"=== SYNC SESSION STARTED at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} ===")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup and send final emails"""
        from email_notifier import email_notifier
        
        if exc_type:
            logging.error(f"CRITICAL: Sync session failed: {exc_val}")
            email_notifier.send_critical_error_immediate(
                exc_val, 
                "Sync session failure", 
                log_file_path=self.log_file
            )
        else:
            duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            logging.info(f"=== SYNC SESSION COMPLETED in {duration:.2f} seconds ===")
        
        return False
    
    def setup_session_logging(self):
        """Setup logging for this session only"""
        if not os.path.exists("logs"):
            os.makedirs("logs")
        
        if not self.log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = f"logs/sync_{timestamp}.log"
        
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ],
            force=True
        )
