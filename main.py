
#!/usr/bin/env python3
"""
JIRA to Odoo Worklog Sync via Tempo
Main script that syncs Tempo worklogs to Odoo
"""

import sys
from datetime import datetime

# Import our modules
from tempo import get_tempo_worklogs
from jira import get_issue_with_odoo_url, extract_odoo_task_id_from_url
from odoo import create_worklog_entry, check_existing_worklogs_by_worklog_id, test_odoo_connection

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
            print(f"⚠️ Worklog entry already exists for Tempo worklog ID: {tempo_worklog_id}")
            return False
        
        # Get issue key from worklog 
        issue = worklog.get('issue', {})
        jira_key = issue.get('key')
        
        if not jira_key:
            print(f"⚠️ Skipping worklog without JIRA key")
            return False
        
        print(f"🔄 Processing worklog  for {jira_key}")
        
        # Get issue details with Odoo URL (checks hierarchy)
        issue_data = get_issue_with_odoo_url(jira_key)
        if not issue_data or not issue_data.get('odoo_url'):
            print(f"⚠️ No Odoo URL found for {jira_key} or its Epic - SKIPPING")
            return False
        
        # Extract Odoo task ID from URL
        odoo_task_id = extract_odoo_task_id_from_url(issue_data['odoo_url'])
        if not odoo_task_id:
            print(f"❌ Could not extract task ID from URL: {issue_data['odoo_url']}")
            return False
        
        # Show task source
        task_source = issue_data.get('task_source', 'unknown')
        if task_source == 'epic':
            epic_key = issue_data.get('epic_key', 'Unknown')
            print(f"🎯 Found Odoo task ID: {odoo_task_id} (via Epic {epic_key})")
        else:
            print(f"🎯 Found Odoo task ID: {odoo_task_id} (direct)")
        
        # Extract worklog details
        time_seconds = worklog.get('timeSpentSeconds', 0)
        hours = convert_seconds_to_hours(time_seconds)
        
        # Use issue title as description (not worklog description)
        description = issue_data.get('description', f'Work on {jira_key}')
        
        # Get date
        started_date = worklog.get('startDate', '')
        date = started_date if started_date else datetime.now().strftime('%Y-%m-%d')
        
        # Get author info
        author = worklog.get('author', {})
        author_name = author.get('displayName', 'Unknown')
        
        print(f"⏱️ Time to log: {hours} hours")
        print(f"📝 Description: '{description}' (from {jira_key} title)")
        print(f"👤 Author: {author_name}")
        print(f"📅 Date: {date}")
        if tempo_worklog_id:
            print(f"🔗 Tempo Worklog ID: {tempo_worklog_id}")
        
        # Create worklog entry with Tempo worklog ID
        worklog_id = create_worklog_entry(
            odoo_task_id, hours, description, date, author_name, tempo_worklog_id
        )
        
        if worklog_id:
            source_info = f"via Epic {issue_data.get('epic_key')}" if task_source == 'epic' else "direct"
            print(f"✅ Successfully synced {jira_key} → Task {odoo_task_id} ({hours}h) [{source_info}]")
            return True
        else:
            print(f"❌ Failed to create worklog for {jira_key}")
            return False
            
    except Exception as e:
        jira_key = worklog.get('issue', {}).get('key', 'Unknown')
        print(f"❌ Error processing worklog for {jira_key}: {e}")
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
        
        print(f"✅ Found {len(tempo_worklogs)} Tempo worklogs")
        
        # Step 2: Process each worklog
        print("\n🔄 Processing worklogs...")
        
        sync_count = 0
        skip_count = 0
        
        for i, worklog in enumerate(tempo_worklogs, 1):
            print(f"\n[{i}/{len(tempo_worklogs)}] ", end="")
            
            if sync_tempo_worklogs_to_odoo(worklog):
                sync_count += 1
            else:
                skip_count += 1
        
        # Summary
        print(f"\n📊 SUMMARY: {sync_count} synced, {skip_count} skipped")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_connections():
    """Test connections to Tempo, JIRA and Odoo"""
    print("🔧 Testing connections...")
    
    # Test Odoo
    test_odoo_connection()
    
    # Test Tempo
    worklogs = get_tempo_worklogs()
    if worklogs is not None and len(worklogs) >= 0:
        print(f"✅ Tempo connection successful ({len(worklogs)} worklogs)")
    else:
        print("❌ Tempo connection failed")

if __name__ == "__main__":
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_connections()
    else:
        main()

