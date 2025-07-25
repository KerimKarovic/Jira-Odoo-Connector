"""
Tempo API integration
Handles fetching worklogs from Tempo and enriching them with JIRA data
"""

import requests
import datetime
from utils import config

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
        print("🔍 Fetching worklogs from Tempo (ALL USERS)...")
        
        # Calculate date range
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(hours=LOOKBACK_HOURS)
        
        print(f"📅 Pulling Tempo worklogs from: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
        
        # Tempo API endpoint
        url = f"{TEMPO_BASE_URL}/worklogs"
        params = {
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'limit': 1000
        }

        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 401:
            from email_notifier import email_notifier
            auth_error = Exception("Tempo API authentication failed - 401 Unauthorized")
            email_notifier.send_error_email(auth_error, "Tempo API Authentication Failure", severity="critical")
            return []
        
        response.raise_for_status()
        
        data = response.json()
        worklogs = data.get('results', [])
        
        print(f"✅ Retrieved {len(worklogs)} worklogs from Tempo API")
        return worklogs
        
    except requests.exceptions.ConnectionError as e:
        from email_notifier import email_notifier
        email_notifier.send_error_email(e, "Tempo API Connection Failure", severity="critical")
        return []
    except requests.exceptions.Timeout as e:
        from email_notifier import email_notifier
        email_notifier.send_error_email(e, "Tempo API Timeout", severity="critical")
        return []
    except requests.exceptions.RequestException as e:
        from email_notifier import email_notifier
        email_notifier.send_error_email(e, "Tempo API Request Failure", severity="critical")
        return []
    except Exception as e:
        from email_notifier import email_notifier
        email_notifier.send_error_email(e, "Tempo API Unexpected Error", severity="critical")
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
            print("⚠️ No issue ID found in worklog - skipping")
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
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error during worklog enrichment: {e}")
        from email_notifier import email_notifier
        email_notifier.send_error_email(e, "JIRA API Connection Failure during enrichment", severity="critical")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API error during worklog enrichment: {e}")
        from email_notifier import email_notifier
        email_notifier.send_error_email(e, "JIRA API Failure during enrichment", severity="critical")
        return None
    except Exception as e:
        print(f"⚠️ Skipped worklog due to enrichment error: {e}")
        return None










