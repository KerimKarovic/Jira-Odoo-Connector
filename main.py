
#!/usr/bin/env python3
"""
JIRA to Odoo Worklog Sync via Tempo
Main script that syncs Tempo worklogs to Odoo
"""

import sys
import logging
from datetime import datetime
from utils import setup_logging
from tempo import get_tempo_worklogs, enrich_worklogs_with_issue_key
from jira import get_issue_with_odoo_url, extract_odoo_task_id_from_url
from odoo import create_timesheet_entry, check_existing_worklogs_by_worklog_id, test_odoo_connection
from email_notifier import email_notifier, email_on_error

def convert_seconds_to_hours(seconds):
    """Convert seconds to hours (float)"""
    return round(seconds / 3600, 2)

def sync_tempo_worklogs_to_odoo(worklog):
    """Sync single Tempo worklog to Odoo"""
    tempo_worklog_id = worklog.get('tempoWorklogId')
    issue = worklog.get('issue', {})
    
    # Handle case where issue is None
    if issue is None:
        issue = {}
    
    jira_key = issue.get('key')
    
    try:
        logging.info(f"Processing worklog: JIRA {jira_key}, Tempo ID: {tempo_worklog_id}")
        
        # Skip duplicates
        if tempo_worklog_id and check_existing_worklogs_by_worklog_id(tempo_worklog_id):
            logging.warning(f"SKIPPED: Duplicate worklog - Tempo ID {tempo_worklog_id}")
            return False
        
        # Get issue with Odoo URL
        issue_data = get_issue_with_odoo_url(jira_key)
        if not issue_data or not issue_data.get('odoo_url'):
            logging.warning(f"SKIPPED: No Odoo URL found for {jira_key}")
            return False
        
        # Extract Odoo task details
        odoo_task_id, model = extract_odoo_task_id_from_url(issue_data['odoo_url'])
        if not odoo_task_id:
            logging.warning(f"SKIPPED: Could not extract task ID from Odoo URL for {jira_key}")
            return False
        
        # Convert time and create timesheet
        time_seconds = worklog.get('timeSpentSeconds', 0)
        hours = convert_seconds_to_hours(time_seconds)
        
        logging.info(f"Creating timesheet: {hours}h for {model} ID {odoo_task_id}")
        
        worklog_id = create_timesheet_entry(
            odoo_task_id, 
            hours, 
            issue_data.get('summary', f'Work on {jira_key}'),
            worklog.get('startDate'), 
            worklog.get('author', {}).get('displayName'),
            tempo_worklog_id, 
            model or 'project.task'
        )
        
        if worklog_id:
            logging.info(f"SUCCESS: Created timesheet ID {worklog_id} for {jira_key}")
            return True
        else:
            logging.warning(f"SKIPPED: Failed to create timesheet for {jira_key}")
            return False
            
    except Exception as e:
        logging.error(f"ERROR: System exception processing worklog {jira_key}: {e}")
        # Collect error instead of sending immediately
        email_notifier.collect_error(e, f"System failure processing worklog {jira_key}", severity="critical")
        return False

@email_on_error(severity="critical")
def main():
    """Main synchronization function"""
    setup_logging()
    start_time = datetime.now()
    logging.info(f"SYNC STARTED at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Start email session
    email_notifier.start_sync_session()
    
    try:
        # Fetch and enrich worklogs
        tempo_worklogs = get_tempo_worklogs()
        logging.info(f"Fetched {len(tempo_worklogs)} worklogs from Tempo")
        
        enriched_worklogs = []
        for worklog in tempo_worklogs:
            enriched = enrich_worklogs_with_issue_key(worklog)
            if enriched:
                enriched_worklogs.append(enriched)
        
        logging.info(f"Enriched {len(enriched_worklogs)} worklogs with JIRA data")
        
        # Process worklogs
        sync_count = skip_count = error_count = 0
        
        for worklog in enriched_worklogs:
            try:
                if sync_tempo_worklogs_to_odoo(worklog):
                    sync_count += 1
                else:
                    skip_count += 1
            except Exception as e:
                error_count += 1
                logging.error(f"Error processing worklog: {e}")
                # Collect error instead of sending immediately
                email_notifier.collect_error(e, f"Processing worklog {worklog.get('issue', {}).get('key', 'unknown')}", "normal")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logging.info(f"Sync completed: {sync_count} created, {skip_count} skipped, {error_count} errors")
        logging.info(f"SYNC COMPLETED in {duration:.2f} seconds")
        
        # Send consolidated email with sync stats
        sync_stats = {
            'created': sync_count,
            'skipped': skip_count, 
            'errors': error_count,
            'duration': duration
        }
        email_notifier.send_sync_summary_email(sync_stats)
        
    except Exception as e:
        logging.error(f"Critical error in main sync: {e}")
        # Send immediate critical error email
        email_notifier.send_critical_error_immediate(e, "Main sync function failure")
        raise

def test_connections():
    """Test connections to all external services"""
    print("🔧 Testing connections...")
    
    # Test Odoo
    test_odoo_connection()
    
    # Test Tempo
    worklogs = get_tempo_worklogs()
    if worklogs is not None:
        print(f"✅ Tempo connection successful ({len(worklogs)} worklogs retrieved)")
    else:
        print("❌ Tempo connection failed")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        setup_logging()
        test_connections()
    else:
        main()

