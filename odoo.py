
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
    """
    Establish connection to Odoo using XML-RPC.
    Returns: (common, models, uid) tuple for API calls
    """
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Authenticate
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        if not uid:
            raise ValueError("Authentication failed")
            
        print(f"✅ Connected to  XML-RPC API (User ID; {uid})")
        return common, models, uid
        
    except xmlrpc.client.Fault as e:
        print(f"❌ XML-RPC exception while connecting to Odoo: {e}")
        return None, None, None
    except Exception as e:
        print(f"❌ Fatal connection error: Could not authenticate or reach Odoo: {e}")
        return None, None, None


def create_timesheet_entry(task_id: int, hours: float, description: str, work_date: Optional[str] = None, jira_author: Optional[str] = None, tempo_worklog_id: Optional[str] = None, model_type: str = 'project.task') -> Optional[int]:
    """
    Create a worklog entry in Odoo.
    Args:
        task_id: Odoo task/ticket ID
        hours: Time spent in hours (float)
        description: Work description
        work_date: Date of work (defaults to today)
        jira_author: Original JIRA author name (optional)
        tempo_worklog_id: Tempo worklog ID for duplicate detection (optional)
        model_type: Odoo model type ('project.task' or 'helpdesk.ticket')
    Returns: Created worklog ID or None
    """
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
                print(f"❌ Odoo helpdesk.ticket ID {task_id} not found- skipping worklog creation")
                return None
                
            task_name = task_data[0].get('name', 'Unknown Ticket')
            
            print(f"✅ Verified helpdesk ticket ID {task_id} exists: {task_name}")
            
        else:
            # For project tasks (existing logic)
            task_data = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'project.task', 'read',
                [[int(task_id)]],
                {'fields': ['name', 'project_id']}
            )
            
            if not task_data or not isinstance(task_data, list) or len(task_data) == 0:
                print(f"❌ Odoo project.task ID {task_id} not found- skipping worklog creation")
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
            print(f"✅ Worklog created successfully for task #{task_id} ({model_name}) with ID {worklog_id}")
            return worklog_id
        else:
            print(f"❌ Unexpected return rype from Odoo worklog creation: {type(worklog_result)}")
            return None
        
    except Exception as e:
        print(f"❌ Exception while creating worklog for {model_type} ID={task_id}, user={jira_author}, date={work_date}: {e}")
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
            print(f"⚠️ Duplicate worklog detected- tempo worklog ID {tempo_worklog_id} already exists in Odoo")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error querying Odoo for existing worklog ID {tempo_worklog_id}: {e}")
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

def get_recent_tasks(limit=10):
    """
    Get recent tasks from Odoo with JIRA URLs
    Returns: List of task dictionaries
    """
    common, models, uid = get_odoo_connection()
    if not uid or not models:
        return []

    try:
        # Search for tasks with JIRA URLs
        tasks = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'project.task', 'search_read',
            [[('x_studio_jira_url', '!=', False)]],
            {'fields': ['id', 'name', 'x_studio_jira_url'], 'limit': limit, 'order': 'id desc'}
        )

        # Ensure we always return a list
        if isinstance(tasks, list):
            return tasks
        else:
            print(f"⚠️Warning: Unexpected task query result type: {type(tasks)}- expected list")

            return []

    except Exception as e:
        print(f"❌ Exception while retrieving recent Odoo tasks: {e}")
        return []

# ========== DEMO RUN ==========
if __name__ == "__main__":
    tasks = get_recent_tasks()
    for task in tasks:
        jira_url = task.get('x_studio_jira_url', '')
        task_name = task.get('name', 'No name')
        print(f"📝 Recent Odoo task : #{task['id']} | Title : {task_name} | Linked JIRA: {jira_url}")

