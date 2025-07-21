"""
Utility functions and configuration management
Handles environment variables, logging, and validation
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# ========== ENVIRONMENT VARIABLES ==========
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "24"))
TEMPO_API_TOKEN = os.getenv("TEMPO_API_TOKEN")

# ========== CONFIG OBJECT ==========
config = {
    "jira": {
        "base_url": JIRA_BASE_URL,
        "user": JIRA_USER,
        "api_token": JIRA_API_TOKEN
    },
    "tempo": {
        "api_token": TEMPO_API_TOKEN
    },
    "odoo": {
        "url": ODOO_URL,
        "db": ODOO_DB,
        "username": ODOO_USERNAME,
        "password": ODOO_PASSWORD
    },
    "sync": {
        "lookback_hours": LOOKBACK_HOURS
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
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Use provided log file or default
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

# Call validation on import
validate_config()
