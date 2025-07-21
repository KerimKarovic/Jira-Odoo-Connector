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

def get_issue_details(issue_key):
    """
    Get full issue details including custom fields
    Args:
        issue_key: JIRA issue key (e.g., 'KDW-1384')
    Returns: Issue data dictionary or None
    """
    try:
        issue_url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
        response = requests.get(issue_url, headers=headers, auth=auth)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching issue {issue_key}: {e}")
        return None

def get_issue_with_odoo_url(issue_key):
    """
    Get JIRA issue details including Odoo URL from custom field
    Args:
        issue_key: JIRA issue key (e.g., 'KDW-1384')
    Returns: Issue data with Odoo URL or None
    """
    try:
        issue_url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
        response = requests.get(issue_url, headers=headers, auth=auth)
        response.raise_for_status()
        
        issue_data = response.json()
        
        # Extract Odoo URL from custom field
        fields = issue_data.get('fields', {})
        odoo_url = fields.get('customfield_10134', '')
        
        if odoo_url:
            print(f"🎯 Found Odoo URL for {issue_key}: {odoo_url}")
            return {
                'key': issue_key,
                'odoo_url': odoo_url,
                'summary': fields.get('summary', '')
            }
        else:
            print(f"⚠️ No Odoo URL found for {issue_key}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching issue {issue_key}: {e}")
        return None

def extract_odoo_task_id_from_url(odoo_url):
    """
    Extract Odoo task ID from URL
    Args:
        odoo_url: URL like 'https://your-odoo.com/web#id=7346&model=project.task'
    Returns: Task ID as integer or None
    """
    if not odoo_url:
        return None
    
    try:
        # Extract ID from URL pattern
        if 'id=' in str(odoo_url):
            task_id = str(odoo_url).split('id=')[1].split('&')[0]
            return int(task_id)
    except (ValueError, IndexError):
        pass
    
    return None

def test_jira_connection():
    """Test JIRA API connection"""
    try:
        print("🔍 Testing connection to JIRA...")
        
        user_url = f"{JIRA_URL}/rest/api/3/myself"
        user_response = requests.get(user_url, headers=headers, auth=auth)
        user_response.raise_for_status()
        current_user = user_response.json()
        
        print(f"✅ Connected to JIRA as: {current_user.get('displayName')}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to JIRA: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

