import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('sync.log'),
            logging.StreamHandler()
        ]
    )

def log_sync_result(jira_key, odoo_task_id, hours, status, error=None):
    """Log sync results to JSON file"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'jira_key': jira_key,
        'odoo_task_id': odoo_task_id,
        'hours': hours,
        'status': status,
        'error': error
    }
    
    try:
        with open('sync_log.json', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        print(f"❌ Error logging: {e}")

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

# Call validation on import
validate_config()
