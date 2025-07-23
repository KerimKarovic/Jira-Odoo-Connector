
#!/usr/bin/env python3
"""
JIRA to Odoo Worklog Sync via Tempo
Main script that syncs Tempo worklogs to Odoo
"""

import sys
from datetime import datetime

# Import our modules
from tempo import get_tempo_worklogs, enrich_worklogs_with_issue_key
from jira import get_issue_with_odoo_url, extract_odoo_task_id_from_url
from odoo import create_timesheet_entry, check_existing_worklogs_by_worklog_id, test_odoo_connection

def convert_seconds_to_hours(seconds):
    """Convert seconds to hours (float)"""
    return round(seconds / 3600, 2)

def sync_tempo_worklogs_to_odoo(worklog):
    """
    Sync Tempo worklogs to Odoo using hierarchy logic:
    1. Use direct Odoo URL from work item
    2. Use Odoo URL from parent Epic if no direct URL
    3. Skip if neither has Odoo URL
    """
    try:
        # Get Tempo worklog ID for duplicate detection
        tempo_worklog_id = worklog.get('tempoWorklogId')
        
        # Check for duplicates using Tempo worklog ID first
        if tempo_worklog_id and check_existing_worklogs_by_worklog_id(tempo_worklog_id):
            print(f"⚠️ Worklog entry already exists for Tempo worklog ID: {tempo_worklog_id} - skipping sync to prevent duplicate enrty")
            return False
        
        # Get issue key from worklog 
        issue = worklog.get('issue', {})
        if issue is None:
            issue ={}
        jira_key = issue.get('key',)
        
        if not jira_key:
            print(f"⚠️ Skipping worklog with missing JIRA key (TEMPO ID: {worklog.get('tempoWorklogId', 'unknown')})")
            return False
        
        print(f"🔄 Processing worklog: JIRA key: {jira_key}")
        
        # Get issue details with Odoo URL (checks hierarchy)
        issue_data = get_issue_with_odoo_url(jira_key)
        if not issue_data or not issue_data.get('odoo_url'):
            print(f"⚠️ No Odoo URL found for {jira_key} or its Epic - SKIPPING WORKLOG SYNC")
            return False
        
        # Extract Odoo task ID and model type from URL
        odoo_task_id, model = extract_odoo_task_id_from_url(issue_data['odoo_url'])
        if not odoo_task_id:
            print(f"❌ Could not extract task ID from URL: {issue_data['odoo_url']}")
            print(f"   🔍 URL Analysis:")
            print(f"   📋 Raw URL: '{issue_data['odoo_url']}'")
            print(f"   🔗 Expected format: 'https://odoo.com/web#id=123&model=project.task'")
            print(f"   ❓ Check if URL contains 'id=' parameter")
            print(f"   📝 JIRA Issue: {jira_key}")
            print(f"   🎯 Source: {issue_data.get('task_source', 'unknown')}")
            if issue_data.get('task_source') == 'epic':
                print(f"   🔗 Epic Key: {issue_data.get('epic_key', 'Unknown')}")
            return False
        
       
        # Show task source and model type
        task_source = issue_data.get('task_source', 'unknown')
        model = "helpdesk.ticket" if model == 'helpdesk.ticket' else "project.task"
        
        if task_source == 'epic':
            epic_key = issue_data.get('epic_key', 'Unknown')
            print(f"🎯 Matched Epic → Odoo {model}: ID {odoo_task_id}, Epic Key: {epic_key} ")
        else:
            print(f"🎯 Matched JIRA Issue → Odoo {model} ID: {odoo_task_id} (direct)")
        
        # Extract worklog details
        time_seconds = worklog.get('timeSpentSeconds', 0)
        hours = convert_seconds_to_hours(time_seconds)
        
        # Use issue title as description (not worklog description)
        description = issue_data.get('summary', f'Work on {jira_key}')
        
        # Get date
        started_date = worklog.get('startDate', '')
        date = started_date if started_date else datetime.now().strftime('%Y-%m-%d')
        
        # Get author info
        author = worklog.get('author', {})
        author_name = author.get('displayName', 'Unknown')
        
        print(f"⏱️ Time to log: {hours} hours")
        print(f"📝 Description: '{description}' (from {jira_key} title)")
        print(f"👤 Logged by : {author_name}")
        print(f"📅 Worklog date: {date}")
        if tempo_worklog_id:
            print(f"🔗 Tempo Worklog ID: {tempo_worklog_id}")
        
        # Create worklog entry with model type
        worklog_id = create_timesheet_entry(
            odoo_task_id, hours, description, date, author_name, tempo_worklog_id, model or 'project.task'
        )
        
        if worklog_id:
            source_info = f"via Epic {issue_data.get('epic_key')}" if task_source == 'epic' else "direct"
            print(f"✅ Successfully synced {jira_key} → {model.title()} {odoo_task_id} for ({hours}h) [{source_info}]")
            return True
        else:
            print(f"❌ Failed to create Odoo timesheet for JIRA Key: {jira_key}")
            return False
            
    except Exception as e:
       issue = worklog.get('issue', {})
       if issue is None:
           issue = {}
       jira_key = issue.get('key', 'Unknown')
       print(f"Error processing worklog for {jira_key}")
       return False    
def main():
    """Main function using Tempo API approach"""
    print("🚀 JIRA to Odoo Worklogs Sync via Tempo")
    
    try:
        # Step 1: Fetch Tempo worklogs
        print("\n📥 Fetching recent worklogs from Tempo...")
        tempo_worklogs = get_tempo_worklogs()
        
        if not tempo_worklogs:
            print("⚠️ No Tempo worklogs found.")
            return
        
        print(f"✅ Successfully fetched {len(tempo_worklogs)} Tempo worklogs for selected time period")
        
        # Step 1.5: Enrich worklogs with JIRA data
        print("\n🔄 Enriching worklogs with JIRA issue data...")
        
        enriched_worklogs = []
        for worklog in tempo_worklogs:
            enriched = enrich_worklogs_with_issue_key(worklog)
            if enriched:
                enriched_worklogs.append(enriched)
            else:
                print(f"⚠️ Could not enrich worklog {worklog.get('tempoWorklogId', 'unknown')}- skipping...")
        
        print(f"✅ Successfully enriched {len(enriched_worklogs)} worklogs with JIRA issue data")
        
        # Step 2: Process each enriched worklog
        print("\n🔄 Processing worklogs...")
        
        sync_count = 0
        skip_count = 0
        
        for i, worklog in enumerate(enriched_worklogs, 1):
            print(f"\n[{i}/{len(enriched_worklogs)}] ", end="")
            
            if sync_tempo_worklogs_to_odoo(worklog):
                sync_count += 1
            else:
                skip_count += 1
        
        # Summary
        print(f"\n📊 SYNC SUMMARY: Synced: {sync_count}, Skipped: {skip_count} (out of {len(enriched_worklogs)})")
        
    except Exception as e:
        print(f"❌ Runtime error: {e}")

def test_connections():
    """Test connections to Tempo, JIRA and Odoo"""
    print("🔧 Testing connections...")
    
    # Test Odoo
    test_odoo_connection()
    
    # Test Tempo
    worklogs = get_tempo_worklogs()
    if worklogs is not None and len(worklogs) >= 0:
        print(f"✅ Tempo connection successful- ({len(worklogs)} worklogs retrieved)")
    else:
        print("❌ Tempo connection failed")

if __name__ == "__main__":
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_connections()
    else:
        main()

