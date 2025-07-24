"""
JIRA API integration
Handles fetching JIRA issues and extracting Odoo URLs with Epic hierarchy support
"""

import requests
from utils import config

# ========== CONFIG VALUES ==========
JIRA_URL = config["jira"]["base_url"]
JIRA_USER = config["jira"]["user"]
JIRA_TOKEN = config["jira"]["api_token"]

# ========== HEADERS ==========
auth = (JIRA_USER, JIRA_TOKEN)
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}



def get_issue_with_odoo_url(issue_key):
    """Get JIRA issue - only email for system failures"""
    try:
        issue_url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
        response = requests.get(issue_url, headers=headers, auth=auth)
        
        if response.status_code == 401:
            # AUTH failure - send email
            from email_notifier import email_notifier
            auth_error = Exception(f"JIRA API authentication failed")
            email_notifier.send_error_email(auth_error, "JIRA API Authentication Failure", severity="critical")
            return None
        
        if response.status_code == 404:
            # DATA issue - issue doesn't exist, NO email
            print(f"⚠️ JIRA issue {issue_key} not found (404) - skipping")
            return None
            
        response.raise_for_status()
        
        issue_data = response.json()
        fields = issue_data.get('fields', {})
        
        # Get issue title for description
        issue_title = fields.get('summary', f'Work on {issue_key}')
        
        # Check if this issue has an Odoo URL
        odoo_url = fields.get('customfield_10134', '')
        
        if odoo_url:
            print(f"🎯 Odoo link found in issue {issue_key}: {odoo_url}")
            return {
                'key': issue_key,
                'odoo_url': odoo_url,
                'summary': issue_title,
                'task_source': 'direct',  # Task found directly on issue
                'description': issue_title
            }
        
        # No direct Odoo URL - check if this issue has a parent Epic
        parent_epic = fields.get('parent')  # Epic link field
        if not parent_epic:
            # Try alternative Epic field names
            parent_epic = fields.get('customfield_10014')  # Common Epic Link field
        
        if parent_epic:
            epic_key = parent_epic.get('key') if isinstance(parent_epic, dict) else str(parent_epic)
            print(f"🔗 Issue {issue_key} is under parent Epic: {epic_key}")
            
            # Get Epic details
            epic_data = get_epic_odoo_url(epic_key)
            if epic_data and epic_data.get('odoo_url'):
                print(f"🎯 Extracted Odoo link from Epic {epic_key}: {epic_data['odoo_url']}")
                return {
                    'key': issue_key,
                    'odoo_url': epic_data['odoo_url'],
                    'summary': issue_title,
                    'task_source': 'epic',  # Task found via Epic
                    'epic_key': epic_key,
                    'description': issue_title  # Use original issue title
                }
        
        print(f"⚠️ No Odoo mapping found for Jira Issue ID: {issue_key} or its Epic")
        return None
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error fetching issue {issue_key}: {e}")
        # CONNECTION failure - send email
        from email_notifier import email_notifier
        email_notifier.send_error_email(e, f"JIRA API Connection Failure", severity="critical")
        return None
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout error fetching issue {issue_key}: {e}")
        # TIMEOUT failure - send email
        from email_notifier import email_notifier
        email_notifier.send_error_email(e, f"JIRA API Timeout", severity="critical")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API error fetching issue {issue_key}: {e}")
        # API failure - send email
        from email_notifier import email_notifier
        email_notifier.send_error_email(e, f"JIRA API Request Failure", severity="critical")
        return None
    except Exception as e:
        print(f"⚠️ Error fetching issue {issue_key}: {e}")
        # DATA issue - NO email
        return None

def get_epic_odoo_url(epic_key):
    """
    Get Epic details including Odoo URL
    Args:
        epic_key: Epic issue key
    Returns: Epic data with Odoo URL or None
    """
    try:
        epic_url = f"{JIRA_URL}/rest/api/3/issue/{epic_key}"
        response = requests.get(epic_url, headers=headers, auth=auth)
        response.raise_for_status()
        
        epic_data = response.json()
        fields = epic_data.get('fields', {})
        
        # Get Odoo URL from Epic
        odoo_url = fields.get('customfield_10134', '')
        
        if odoo_url:
            return {
                'key': epic_key,
                'odoo_url': odoo_url,
                'summary': fields.get('summary', '')
            }
        
        return None
        
    except Exception as e:
        print(f"❌ JIRA API error wile fetching Epic{epic_key}: {e}")
        return None

def extract_odoo_task_id_from_url(odoo_url):
    """
    Extract Odoo task ID and model type from URL
    Args:
        odoo_url: URL like 'https://your-odoo.com/web#id=7346&model=project.task'
    Returns: Tuple of (task_id, model_type) or (None, None)
    """
    if not odoo_url:
        return None, None
    
    try:
        # Extract ID from URL pattern
        task_id = None
        model_type = 'project.task'  # Default
        
        if 'id=' in str(odoo_url):
            task_id = str(odoo_url).split('id=')[1].split('&')[0]
            task_id = int(task_id)
        
        # If no task_id found, return (None, None)
        if task_id is None:
            return None, None
        
        # Extract model type - check for both patterns
        if 'model=' in str(odoo_url):
            model_part = str(odoo_url).split('model=')[1].split('&')[0]
            # Handle URL encoding
            model_type = model_part.replace('%2E', '.')
        
        return task_id, model_type
        
    except (ValueError, IndexError) as e:
        print(f"⚠️ Malformed Odoo Url for  {odoo_url}- parsing failed with: {e}")
        return None, None

def test_jira_connection():
    """Test JIRA API connection"""
    try:
        print("🔍 Testing connection to JIRA...")
        
        user_url = f"{JIRA_URL}/rest/api/3/myself"
        user_response = requests.get(user_url, headers=headers, auth=auth)
        user_response.raise_for_status()
        current_user = user_response.json()
        
        print(f"✅ JIRA API authenticated as user:  {current_user.get('displayName')}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to authenticate/connect to JIRA:: {e}")
        return False
    except Exception as e:
        print(f"❌ Generic error durnig JIRA session check: {e}")
        return False

