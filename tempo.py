"""
Tempo API integration
Handles fetching worklogs from Tempo and enriching them with JIRA data
"""

import requests
import datetime
from utils import config
from email_notifier import email_notifier

# Configuration
TEMPO_BASE_URL = "https://api.tempo.io/4"
TEMPO_API_TOKEN = config["tempo"]["api_token"]
LOOKBACK_HOURS = config["sync"]["lookback_hours"]

# Headers
headers = {
    "Authorization": f"Bearer {TEMPO_API_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def get_tempo_worklogs():
    """Fetch worklogs from Tempo API"""
    try:
        # Calculate date range
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(hours=LOOKBACK_HOURS)
        
        # Tempo API endpoint
        url = f"{TEMPO_BASE_URL}/worklogs"
        params = {
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'limit': 1000
        }

        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 401:
            auth_error = Exception("Tempo API authentication failed - 401 Unauthorized")
            email_notifier.collect_error(auth_error, "Tempo API Authentication Failure", severity="critical")
            return []
        
        response.raise_for_status()
        
        data = response.json()
        worklogs = data.get('results', [])
        
        return worklogs
        
    except requests.exceptions.RequestException as e:
        email_notifier.collect_error(e, "Tempo API Request Failure", severity="critical")
        return []
    except Exception as e:
        email_notifier.collect_error(e, "Tempo API Unexpected Error", severity="critical")
        return []



def enrich_worklogs_with_issue_key(worklog):
    """Enrich worklog with JIRA issue key"""
    try:
        from jira import JIRA_URL, auth, headers as jira_headers
        
        # Get issue ID from worklog
        issue = worklog.get('issue', {})
        issue_id = issue.get('id')
        
        # If issue already has a key, skip API call
        if issue.get('key'):
            return worklog
            
        if not issue_id:
            return None
        
        # Fetch issue details from JIRA
        issue_url = f"{JIRA_URL}/rest/api/3/issue/{issue_id}"
        response = requests.get(issue_url, headers=jira_headers, auth=auth)
        response.raise_for_status()
        
        issue_data = response.json()
        issue_key = issue_data.get('key')
        
        # Enrich the worklog
        enriched_worklog = worklog.copy()
        enriched_worklog['issue']['key'] = issue_key
        
        return enriched_worklog
        
    except requests.exceptions.RequestException as e:
        email_notifier.collect_error(e, "JIRA API Failure during enrichment", severity="critical")
        return None
    except Exception as e:
        return None










