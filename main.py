
#!/usr/bin/env python3
"""
JIRA to Odoo Worklog Sync via Tempo
Main script that syncs Tempo worklogs to Odoo
"""

import sys
from datetime import datetime
import logging
from utils import setup_logging

# Import our modules
from tempo import get_tempo_worklogs, enrich_worklogs_with_issue_key
from jira import get_issue_with_odoo_url, extract_odoo_task_id_from_url
from odoo import create_timesheet_entry, check_existing_worklogs_by_worklog_id, test_odoo_connection
from email_notifier import email_notifier, email_on_error

def convert_seconds_to_hours(seconds):
    """Convert seconds to hours (float)"""
    return round(seconds / 3600, 2)

@email_on_error(severity="normal")
def sync_tempo_worklogs_to_odoo(worklog):
    """Sync Tempo worklogs to Odoo with detailed logging"""
    tempo_worklog_id = worklog.get('tempoWorklogId')
    jira_key = None
    
    try:
        issue = worklog.get('issue', {})
        if issue is None:
            issue = {}
        jira_key = issue.get('key')
            
        logging.info(f"Processing worklog: JIRA {jira_key}, Tempo ID: {tempo_worklog_id}")
            
        # Check for duplicates (expected skip)
        if tempo_worklog_id and check_existing_worklogs_by_worklog_id(tempo_worklog_id):
            logging.warning(f"SKIPPED: Duplicate worklog - Tempo ID {tempo_worklog_id} already exists")
            return False
            
        # Get issue details
        issue_data = get_issue_with_odoo_url(jira_key)
        if not issue_data or not issue_data.get('odoo_url'):
            logging.warning(f"SKIPPED: No Odoo URL found for {jira_key}")
            return False
            
        # Extract task details
        odoo_task_id, model = extract_odoo_task_id_from_url(issue_data['odoo_url'])
        if not odoo_task_id:
            logging.warning(f"SKIPPED: Could not extract task ID from Odoo URL for {jira_key}")
            return False
                
        time_seconds = worklog.get('timeSpentSeconds', 0)
        hours = convert_seconds_to_hours(time_seconds)
            
        logging.info(f"Creating timesheet: {hours}h for {model} ID {odoo_task_id}")
            
        # Create worklog - THIS is where we expect success
        worklog_id = create_timesheet_entry(
            odoo_task_id, hours, issue_data.get('summary') or f'Work on {jira_key}',
            worklog.get('startDate'), worklog.get('author', {}).get('displayName'),
            tempo_worklog_id, model or 'project.task'
        )
            
        if worklog_id:
            logging.info(f"SUCCESS: Created timesheet ID {worklog_id} for {jira_key} → {model} {odoo_task_id}")
            return True
        else:
            # FAILED SYNC - this was expected to work but didn't
            logging.error(f"FAILED: Could not create timesheet for {jira_key}")
            return False
                
    except Exception as e:
        # FAILED SYNC - unexpected exception during processing
        logging.error(f"ERROR: Exception processing worklog {jira_key or 'unknown'}: {e}")
        return False

@email_on_error(severity="critical")
def main():
    """Main function with detailed logging"""
    # Setup logging first
    setup_logging()
    
    logging.info("Starting JIRA to Odoo sync process")
    
    try:
        # Fetch worklogs
        tempo_worklogs = get_tempo_worklogs()
        logging.info(f"Fetched {len(tempo_worklogs)} worklogs from Tempo")
        
        # Enrich worklogs
        enriched_worklogs = []
        for worklog in tempo_worklogs:
            enriched = enrich_worklogs_with_issue_key(worklog)
            if enriched:
                enriched_worklogs.append(enriched)
        
        logging.info(f"Enriched {len(enriched_worklogs)} worklogs with JIRA data")
        
        # Process worklogs
        sync_count = 0
        skip_count = 0
        error_count = 0
        
        for worklog in enriched_worklogs:
            try:
                if sync_tempo_worklogs_to_odoo(worklog):
                    sync_count += 1
                else:
                    skip_count += 1
            except Exception as e:
                error_count += 1
                logging.error(f"Error processing worklog: {e}")
                # Send email notification for any error
                email_notifier.send_error_email(e, f"Processing worklog {worklog.get('tempoWorklogId', 'unknown')}", severity="normal")
        
        logging.info(f"Sync completed: {sync_count} created, {skip_count} skipped, {error_count} errors")
        
    except Exception as e:
        logging.error(f"Critical error in main sync: {e}")

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
        # Setup logging for test mode too
        setup_logging()
        test_connections()
    else:
        main()

