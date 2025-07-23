"""
Tempo API integration
Handles fetching worklogs from Tempo and enriching them with JIRA data
"""

import requests
import datetime
from utils import config

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

def get_tempo_worklogs():
    """
    Fetch recent worklogs from Tempo API for ALL USERS
    Returns: list of worklog dictionaries with issue data
    """
    try:
        print("🔍 Fetching worklogs from Tempo (ALL USERS)...")
        
        # Calculate date range
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(hours=LOOKBACK_HOURS)
        
        print(f"📅 Pulling Tempo worklogs from: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
        
        # Tempo API endpoint for worklogs
        url = f"{TEMPO_BASE_URL}/worklogs"
        
        params = {
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'limit': 1000
        }
        
        print(f"🔗 Tempo API Endpoint: {url}")
        print(f"📋 API Query Params: {params}")
        print(f"🔑 Authenticating using API token: {TEMPO_API_TOKEN[:10]}... (truncated)")
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 401:
            print(f"❌ 41 Unauthorized: Invalid or expired Tempo API token")
            print(f"🔑 Provided token prefix: {TEMPO_API_TOKEN[:10]}...")
            print(f"📋 Ensure this token has 'View worklogs' premission enabled in Tempo")
            return []
        
        response.raise_for_status()
        
        data = response.json()
        worklogs = data.get('results', [])
        
        print(f"✅ Retrieved {len(worklogs)} worklogs from Tempo API")
        return worklogs
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Fatal JSON/API error while retrieving Tempo worklogs: {e}")
        return []
    except Exception as e:
        print(f"❌ Connection error during Tempo API fetch {e}")
        return []



def enrich_worklogs_with_issue_key(worklog):
    """
    Enrich worklog with JIRA issue key and author name
    Args:
        worklog: Raw worklog from Tempo API
    Returns: Enriched worklog with issue key and author name
    """
    try:
        from jira import JIRA_URL, auth, headers as jira_headers
        
        # Get issue ID from worklog
        issue = worklog.get('issue', {})
        issue_id = issue.get('id')
        
        # If issue already has a key, we can skip the API call
        if issue.get('key'):
            return worklog
            
        if not issue_id:
            print("⚠️ No issue ID found in worklog")
            return None
        
        # Fetch issue details from JIRA
        issue_url = f"{JIRA_URL}/rest/api/3/issue/{issue_id}"
        response = requests.get(issue_url, headers=jira_headers, auth=auth)
        response.raise_for_status()
        
        issue_data = response.json()
        issue_key = issue_data.get('key')
        
        # Get author details
        author = worklog.get('author', {})
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
        
        # Enrich the worklog
        enriched_worklog = worklog.copy()
        enriched_worklog['issue']['key'] = issue_key
        enriched_worklog['author']['displayName'] = author_name
        
        return enriched_worklog
        
    except Exception as e:
        print(f"⚠️ Skipped worklog die to enrichment error: {e}")
        return worklog  # Return original if enrichment fails










