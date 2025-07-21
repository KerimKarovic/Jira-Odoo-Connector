import requests
import datetime
from utils import config
from jira import get_issue_with_odoo_url


# ========== TEMPO CONFIG ==========
TEMPO_BASE_URL = "https://api.tempo.io/4"
TEMPO_API_TOKEN = config["tempo"]["api_token"]
LOOKBACK_HOURS = config["sync"]["lookback_hours"]

# ========== HEADERS ==========
headers = {
    "Authorization": f"Bearer {TEMPO_API_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def get_tempo_timesheets():
    """
    Fetch recent timesheets from Tempo API
    Returns: list of timesheet dictionaries with issue data
    """
    try:
        print("🔍 Fetching timesheets from Tempo...")
        
        # Calculate date range
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(hours=LOOKBACK_HOURS)
        
        print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Tempo API endpoint for timesheets
        url = f"{TEMPO_BASE_URL}/worklogs"
        
        params = {
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'limit': 1000
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        timesheets = data.get('results', [])
        
        print(f"✅ Found {len(timesheets)} timesheets from Tempo")
        
        # Enrich timesheets with JIRA issue keys
        enriched_timesheets = []
        for timesheet in timesheets:
            enriched = enrich_timesheet_with_issue_key(timesheet)
            if enriched:
                enriched_timesheets.append(enriched)
        
        # Show sample data
        if enriched_timesheets:
            print(f"\n📋 Sample timesheets:")
            for i, timesheet in enumerate(enriched_timesheets[:3]):
                issue_key = timesheet.get('issue', {}).get('key', 'Unknown')
                hours = timesheet.get('timeSpentSeconds', 0) / 3600
                author = timesheet.get('author', {}).get('displayName', 'Unknown')
                print(f"  {i+1}. {issue_key} | {author} | {hours:.2f}h")
        
        return enriched_timesheets
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching Tempo timesheets: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []

def enrich_timesheet_with_issue_key(timesheet):
    """
    Enrich timesheet with JIRA issue key and author name
    Args:
        timesheet: Raw timesheet from Tempo API
    Returns: Enriched timesheet with issue key and author name
    """
    try:
        from jira import JIRA_URL, auth, headers as jira_headers
        
        # Get issue ID from timesheet
        issue = timesheet.get('issue', {})
        issue_id = issue.get('id')
        
        # If issue already has a key, we can skip the API call
        if issue.get('key'):
            enriched_timesheet = timesheet.copy()
            return enriched_timesheet
            
        if not issue_id:
            print("⚠️ No issue ID found in timesheet")
            return None
        
        # Fetch issue details from JIRA
        issue_url = f"{JIRA_URL}/rest/api/3/issue/{issue_id}"
        response = requests.get(issue_url, headers=jira_headers, auth=auth)
        response.raise_for_status()
        
        issue_data = response.json()
        issue_key = issue_data.get('key')
        
        # Get author details
        author = timesheet.get('author', {})
        author_account_id = author.get('accountId')
        author_name = 'Unknown'
        
        if author_account_id:
            # Fetch user details
            user_url = f"{JIRA_URL}/rest/api/3/user"
            user_params = {'accountId': author_account_id}
            user_response = requests.get(user_url, headers=jira_headers, auth=auth, params=user_params)
            if user_response.status_code == 200:
                user_data = user_response.json()
                author_name = user_data.get('displayName', 'Unknown')
        
        # Enrich the timesheet
        enriched_timesheet = timesheet.copy()
        enriched_timesheet['issue']['key'] = issue_key
        enriched_timesheet['author']['displayName'] = author_name
        
        return enriched_timesheet
        
    except Exception as e:
        print(f"⚠️ Error enriching timesheet: {e}")
        return timesheet  # Return original if enrichment fails










