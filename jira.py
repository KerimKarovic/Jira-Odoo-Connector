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
    """
    Get JIRA issue details including Odoo URL from custom field or parent Epic
    Args:
        issue_key: JIRA issue key (e.g., 'KDW-1384')
    Returns: Issue data with Odoo URL, task source, and issue title or None
    """
    try:
        issue_url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
        response = requests.get(issue_url, headers=headers, auth=auth)
        response.raise_for_status()
        
        issue_data = response.json()
        fields = issue_data.get('fields', {})
        
        # Get issue title for description
        issue_title = fields.get('summary', f'Work on {issue_key}')
        
        # Check if this issue has an Odoo URL
        odoo_url = fields.get('customfield_10134', '')
        
        if odoo_url:
            print(f"🎯 Found Odoo URL for {issue_key}: {odoo_url}")
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
            print(f"🔗 {issue_key} has parent Epic: {epic_key}")
            
            # Get Epic details
            epic_data = get_epic_odoo_url(epic_key)
            if epic_data and epic_data.get('odoo_url'):
                print(f"🎯 Found Odoo URL in Epic {epic_key}: {epic_data['odoo_url']}")
                return {
                    'key': issue_key,
                    'odoo_url': epic_data['odoo_url'],
                    'summary': issue_title,
                    'task_source': 'epic',  # Task found via Epic
                    'epic_key': epic_key,
                    'description': issue_title  # Use original issue title
                }
        
        print(f"⚠️ No Odoo URL found for {issue_key} or its Epic")
        return None
            
    except Exception as e:
        print(f"❌ Error fetching issue {issue_key}: {e}")
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
        print(f"❌ Error fetching Epic {epic_key}: {e}")
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

