
"""
Odoo integration
Handles connection to Odoo and worklog creation
"""

import xmlrpc.client
from datetime import datetime, date
from typing import Optional
from utils import config

# ========== CONFIG VALUES ==========
ODOO_URL = config["odoo"]["url"].rstrip('/')  # Remove trailing slash
ODOO_DB = config["odoo"]["db"]
ODOO_USERNAME = config["odoo"]["username"]
ODOO_PASSWORD = config["odoo"]["password"]

# WebDevelopment Team Employee ID
WEBDEV_TEAM_EMPLOYEE_ID = 21

def get_odoo_connection():
    """Establish Odoo connection - collect errors for batch email"""
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        if not uid:
            # AUTH failure - collect error
            from email_notifier import email_notifier
            auth_error = Exception("Odoo authentication failed - invalid credentials")
            email_notifier.collect_error(auth_error, "Odoo Authentication Failure", severity="critical")
            print("❌ Odoo auth failed")
            return None, None, None
            
        print(f"✅ Odoo connected (UID: {uid})")
        return common, models, uid
        
    except ConnectionError as e:
        print("❌ Odoo connection failed")
        # CONNECTION failure - collect error
        from email_notifier import email_notifier
        email_notifier.collect_error(e, "Odoo Connection Failure", severity="critical")
        return None, None, None
    except Exception as e:
        print(f"❌ System error connecting to Odoo: {e}")
        # SYSTEM failure - collect error
        from email_notifier import email_notifier
        email_notifier.collect_error(e, "Odoo System Error", severity="critical")
        return None, None, None


def create_timesheet_entry(task_id: int, hours: float, description: str, work_date: Optional[str] = None, jira_author: Optional[str] = None, tempo_worklog_id: Optional[str] = None, model_type: str = 'project.task') -> Optional[int]:
    """Create timesheet - collect errors for batch email"""
    common, models, uid = get_odoo_connection()
    if not uid or not models:
        return None
    
    if work_date is None:
        work_date = date.today().strftime('%Y-%m-%d')
    
    try:
        # Get task/ticket details based on model type
        if model_type == 'helpdesk.ticket':
            # For helpdesk tickets
            task_data = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'helpdesk.ticket', 'read',
                [[int(task_id)]],
                {'fields': ['name']}
            )
            
            if not task_data or not isinstance(task_data, list) or len(task_data) == 0:
                # DATA issue - task doesn't exist, collect error
                from email_notifier import email_notifier
                task_error = Exception(f"Odoo {model_type} ID {task_id} not found")
                email_notifier.collect_error(task_error, f"Odoo Task Not Found - {model_type} ID {task_id}", severity="normal")
                return None
                
            task_name = task_data[0].get('name', 'Unknown Ticket')
            
        else:
            # For project tasks (existing logic)
            task_data = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'project.task', 'read',
                [[int(task_id)]],
                {'fields': ['name', 'project_id']}
            )
            
            if not task_data or not isinstance(task_data, list) or len(task_data) == 0:
                # DATA issue - task doesn't exist, collect error
                print(f"⚠️ Odoo {model_type} ID {task_id} not found - this indicates mapping issues")
                from email_notifier import email_notifier
                task_error = Exception(f"Odoo {model_type} ID {task_id} not found")
                email_notifier.collect_error(task_error, f"Odoo Task Not Found - {model_type} ID {task_id}", severity="normal")
                return None
                
            task_name = task_data[0].get('name', 'Unknown Task')
            project_id_field = task_data[0].get('project_id')
            
            # Handle project_id which can be False, int, or [id, name] tuple
            project_id = None
            if isinstance(project_id_field, list) and len(project_id_field) > 0:
                project_id = project_id_field[0]
            elif isinstance(project_id_field, int):
                project_id = project_id_field
        
        # Worklog data - different structure for helpdesk vs project
        if model_type == 'helpdesk.ticket':
            # For helpdesk tickets, create timesheet entry linked to ticket
            worklog_data = {
                'helpdesk_ticket_id': int(task_id),
                'name': str(description),
                'unit_amount': float(hours),
                'date': str(work_date),
                'employee_id': WEBDEV_TEAM_EMPLOYEE_ID,
            }
        else:
            # For project tasks (existing logic)
            worklog_data = {
                'task_id': int(task_id),
                'project_id': project_id,
                'name': str(description),
                'unit_amount': float(hours),
                'date': str(work_date),
                'employee_id': WEBDEV_TEAM_EMPLOYEE_ID,
            }
        
        # Add Tempo worklog ID if provided
        if tempo_worklog_id:
            worklog_data['x_jira_worklog_id'] = str(tempo_worklog_id)
        
        # Create the worklog
        worklog_result = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'account.analytic.line', 'create',
            [worklog_data]
        )
        
        # Handle the result which should be an integer ID
        if isinstance(worklog_result, int):
            worklog_id = worklog_result
            model_name = "helpdesk ticket" if model_type == 'helpdesk.ticket' else "project task"
            print(f"✅ Worklog created: #{worklog_id}")
            return worklog_id
        else:
            # DATA issue - unexpected return type, NO email
            print(f"⚠️ Unexpected return type from Odoo worklog creation: {type(worklog_result)}")
            return None
        
    except ConnectionError as e:
        print(f"❌ Connection error creating worklog for {model_type} ID={task_id}: {e}")
        # CONNECTION failure - collect error
        from email_notifier import email_notifier
        email_notifier.collect_error(e, f"Odoo connection error during timesheet creation", severity="critical")
        return None
    except Exception as e:
        print(f"⚠️ Error creating worklog for {model_type} ID={task_id}: {e}")
        # Check if it's a permission error
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ['permission', 'access', 'denied', 'forbidden']):
            # Permission issue - collect error
            from email_notifier import email_notifier
            email_notifier.collect_error(e, f"Odoo permission error during timesheet creation", severity="normal")
        return None

def check_existing_worklogs_by_worklog_id(tempo_worklog_id: Optional[str]) -> bool:
    """Check if worklog entry already exists using Tempo worklog ID"""
    if not tempo_worklog_id:
        return False
        
    common, models, uid = get_odoo_connection()
    if not uid or not models:
        return False
    
    try:
        # Performance improvement: use search() instead of search_read()
        existing_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'account.analytic.line', 'search',
            [[('x_jira_worklog_id', '=', str(tempo_worklog_id))]],
            {'limit': 1}
        )
        
        if existing_ids:
            print(f"⚠️ Duplicate worklog: {tempo_worklog_id}")
            return True
        
        return False
        
    except Exception as e:
        return False

def test_odoo_connection():
    """Test Odoo connection and return status"""
    print("🔧 Testing Odoo connection...")
    common, models, uid = get_odoo_connection()
    
    if uid:
        print("✅ Odoo connection successful")
        return True
    else:
        print("❌ Odoo connection failed")
        return False

# Remove get_recent_tasks() function completely - it's never called


