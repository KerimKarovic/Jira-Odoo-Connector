"""
JIRA API integration
Handles fetching JIRA issues and extracting Odoo URLs with Epic hierarchy support
"""

import requests
from utils import config
from email_notifier import email_notifier

# Configuration
JIRA_URL = config["jira"]["base_url"]
JIRA_USER = config["jira"]["user"]
JIRA_TOKEN = config["jira"]["api_token"]

# API setup
auth = (JIRA_USER, JIRA_TOKEN)
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def get_issue_with_odoo_url(issue_key):
    """Get JIRA issue and extract Odoo URL from issue or parent Epic"""
    try:
        issue_url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
        response = requests.get(issue_url, headers=headers, auth=auth)
        
        # Handle authentication failure
        if response.status_code == 401:
            auth_error = Exception("JIRA API authentication failed")
            email_notifier.collect_error(auth_error, "JIRA API Authentication Failure", severity="critical")
            return None
        
        # Handle missing issue
        if response.status_code == 404:
            return None
            
        response.raise_for_status()
        
        issue_data = response.json()
        fields = issue_data.get('fields', {})
        issue_title = fields.get('summary', f'Work on {issue_key}')
        
        # Check for direct Odoo URL
        odoo_url = fields.get('customfield_10134', '')
        if odoo_url:
            return {
                'key': issue_key,
                'odoo_url': odoo_url,
                'summary': issue_title,
                'task_source': 'direct',
                'description': issue_title
            }
        
        # Check parent Epic for Odoo URL
        parent_epic = fields.get('parent') or fields.get('customfield_10014')
        if parent_epic:
            epic_key = parent_epic.get('key') if isinstance(parent_epic, dict) else str(parent_epic)
            
            epic_data = get_epic_odoo_url(epic_key)
            if epic_data and epic_data.get('odoo_url'):
                return {
                    'key': issue_key,
                    'odoo_url': epic_data['odoo_url'],
                    'summary': issue_title,
                    'task_source': 'epic',
                    'epic_key': epic_key,
                    'description': issue_title
                }
        
        return None
            
    except requests.exceptions.ConnectionError as e:
        email_notifier.collect_error(e, f"JIRA API Connection Failure for {issue_key}", severity="critical")
        return None
    except requests.exceptions.Timeout as e:
        email_notifier.collect_error(e, f"JIRA API Timeout for {issue_key}", severity="critical")
        return None
    except requests.exceptions.RequestException as e:
        email_notifier.collect_error(e, f"JIRA API Request Failure for {issue_key}", severity="critical")
        return None
    except Exception as e:
        email_notifier.collect_error(e, f"Unexpected error fetching {issue_key}", severity="normal")
        return None

def get_epic_odoo_url(epic_key):
    """Get Epic details including Odoo URL"""
    try:
        epic_url = f"{JIRA_URL}/rest/api/3/issue/{epic_key}"
        response = requests.get(epic_url, headers=headers, auth=auth)
        response.raise_for_status()
        
        epic_data = response.json()
        fields = epic_data.get('fields', {})
        odoo_url = fields.get('customfield_10134', '')
        
        if odoo_url:
            return {
                'key': epic_key,
                'odoo_url': odoo_url,
                'summary': fields.get('summary', '')
            }
        
        return None
        
    except Exception as e:
        email_notifier.collect_error(e, f"Epic fetch failure for {epic_key}", severity="normal")
        return None

def extract_odoo_task_id_from_url(odoo_url):
    """Extract Odoo task ID and model type from URL"""
    if not odoo_url:
        return None, None
    
    try:
        task_id = None
        model_type = 'project.task'  # Default
        
        # Extract ID from URL
        if 'id=' in str(odoo_url):
            task_id = str(odoo_url).split('id=')[1].split('&')[0]
            task_id = int(task_id)
        
        if task_id is None:
            return None, None
        
        # Extract model type
        if 'model=' in str(odoo_url):
            model_part = str(odoo_url).split('model=')[1].split('&')[0]
            model_type = model_part.replace('%2E', '.')  # Handle URL encoding
        
        return task_id, model_type
        
    except (ValueError, IndexError) as e:
        url_error = Exception(f"Malformed Odoo URL: {odoo_url}")
        email_notifier.collect_error(url_error, "Malformed Odoo URL in JIRA issue", severity="normal")
        return None, None

def test_jira_connection():
    """Test JIRA API connection"""
    try:
        user_url = f"{JIRA_URL}/rest/api/3/myself"
        user_response = requests.get(user_url, headers=headers, auth=auth)
        user_response.raise_for_status()
        
        current_user = user_response.json()
        return True
        
    except requests.exceptions.RequestException as e:
        return False
    except Exception as e:
        return False

