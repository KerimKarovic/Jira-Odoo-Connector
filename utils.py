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

def setup_logging(log_file=None):
    """Configure logging for the application"""
    # Create logs directory
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Use provided log file or generate default
    if not log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"logs/sync_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

# Validate configuration on import
validate_config()
