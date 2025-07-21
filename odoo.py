
import xmlrpc.client
from datetime import datetime, date
from typing import Optional, Tuple, List, Dict, Any
from utils import config

# ========== CONFIG VALUES ==========
ODOO_URL = config["odoo"]["url"].rstrip('/')  # Remove trailing slash
ODOO_DB = config["odoo"]["db"]
ODOO_USERNAME = config["odoo"]["username"]
ODOO_PASSWORD = config["odoo"]["password"]
LOOKBACK_HOURS = config["sync"]["lookback_hours"]

# WebDevelopment Team Employee ID
WEBDEV_TEAM_EMPLOYEE_ID = 21

# ========== ODOO CONNECTION ==========
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
            
        print(f"✅ Connected to Odoo as user ID: {uid}")
        return common, models, uid
        
    except xmlrpc.client.Fault as e:
        print(f"❌ Odoo XML-RPC error: {e}")
        return None, None, None
    except Exception as e:
        print(f"❌ Error connecting to Odoo: {e}")
        return None, None, None

# ========== FETCH TASKS ==========
def get_recent_tasks():
    """
    Fetch recent tasks from Odoo that have JIRA references.
    Returns: list of task dictionaries
    """
    common, models, uid = get_odoo_connection()
    if not uid or not models:
        return []
    
    try:
        jira_field = 'x_studio_jira_issue_1'
        
        print(f"\n🔍 Using field: {jira_field}")
        
        # Get all tasks with JIRA references
        print("\n🔍 Searching for tasks with JIRA references...")
        all_task_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'project.task', 'search',
            [[]],
            {'limit': 200}
        )
        
        if all_task_ids and isinstance(all_task_ids, list):
            all_tasks = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'project.task', 'read',
                [all_task_ids],
                {'fields': ['id', 'name', jira_field, 'project_id']}
            )
            
            # Filter tasks with JIRA references
            tasks_with_jira = []
            if isinstance(all_tasks, list):
                for task in all_tasks:
                    if isinstance(task, dict):
                        jira_value = task.get(jira_field, '')
                        if jira_value and jira_value != False:
                            tasks_with_jira.append(task)
            
            # Show results
            print(f"\n✅ Found {len(tasks_with_jira)} tasks with JIRA references")
            for task in tasks_with_jira[:5]:
                if isinstance(task, dict):
                    jira_value = task.get(jira_field, '')
                    task_name = task.get('name', '')
                    if isinstance(task_name, str):
                        task_name = task_name[:50] + "..." if len(task_name) > 50 else task_name
                    print(f"   - Task {task.get('id')}: {task_name} | JIRA: {jira_value}")
            
            return tasks_with_jira
        else:
            print("⚠️ No tasks found")
            return []
        
    except Exception as e:
        print(f"❌ Error fetching tasks: {e}")
        return []

# ========== CREATE TIMESHEET ENTRY ==========
def create_timesheet_entry(task_id: int, hours: float, description: str, work_date: Optional[str] = None, jira_author: Optional[str] = None, tempo_worklog_id: Optional[str] = None) -> Optional[int]:
    """
    Create a timesheet entry in Odoo.
    Args:
        task_id: Odoo task ID
        hours: Time spent in hours (float)
        description: Work description
        work_date: Date of work (defaults to today)
        jira_author: Original JIRA author name (optional)
        tempo_worklog_id: Tempo worklog ID for duplicate detection (optional)
    Returns: Created timesheet ID or None
    """
    common, models, uid = get_odoo_connection()
    if not uid or not models:
        return None
    
    if work_date is None:
        work_date = date.today().strftime('%Y-%m-%d')
    
    # Include JIRA author in description if provided
    if jira_author:
        enhanced_description = f"{description} (by {jira_author})"
    else:
        enhanced_description = description
    
    try:
        # Get task info to ensure it exists and get project
        task_info = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'project.task', 'read',
            [task_id],
            {'fields': ['name', 'project_id']}
        )
        
        if not task_info or not isinstance(task_info, list) or len(task_info) == 0:
            print(f"❌ Task {task_id} not found")
            return None
        
        task_data = task_info[0]
        if not isinstance(task_data, dict):
            print(f"❌ Invalid task data for {task_id}")
            return None
            
        task_name = task_data.get('name', 'Unknown Task')
        project_id_field = task_data.get('project_id')
        
        # Handle project_id which can be False, int, or [id, name] tuple
        project_id = None
        if isinstance(project_id_field, list) and len(project_id_field) > 0:
            project_id = project_id_field[0]
        elif isinstance(project_id_field, int):
            project_id = project_id_field
        
        # Timesheet data using WebDevelopment Team employee
        timesheet_data = {
            'task_id': int(task_id),
            'project_id': project_id,
            'name': str(enhanced_description),
            'unit_amount': float(hours),
            'date': str(work_date),
            'employee_id': WEBDEV_TEAM_EMPLOYEE_ID,
        }
        
        # Add Tempo worklog ID if provided
        if tempo_worklog_id:
            timesheet_data['x_jira_worklog_id'] = str(tempo_worklog_id)
        
        # Create the timesheet
        timesheet_result = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'account.analytic.line', 'create',
            [timesheet_data]
        )
        
        # Handle the result which should be an integer ID
        if isinstance(timesheet_result, int):
            timesheet_id = timesheet_result
            print(f"✅ Created timesheet entry {timesheet_id} for WebDevelopment Team")
            return timesheet_id
        else:
            print(f"❌ Unexpected result type from timesheet creation: {type(timesheet_result)}")
            return None
        
    except Exception as e:
        print(f"❌ Error creating timesheet: {e}")
        return None

def check_existing_timesheet_by_worklog_id(tempo_worklog_id: Optional[str]) -> bool:
    """Check if timesheet entry already exists using Tempo worklog ID"""
    if not tempo_worklog_id:
        return False
        
    common, models, uid = get_odoo_connection()
    if not uid or not models:
        return False
    
    try:
        existing = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'account.analytic.line', 'search_read',
            [[('x_jira_worklog_id', '=', str(tempo_worklog_id))]],
            {'fields': ['id', 'name', 'x_jira_worklog_id'], 'limit': 1}
        )
        
        if existing and isinstance(existing, list) and len(existing) > 0:
            print(f"⚠️ Timesheet already exists for Tempo worklog ID: {tempo_worklog_id}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error checking existing timesheet: {e}")
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



# ========== DEMO RUN ==========
if __name__ == "__main__":
    tasks = get_recent_tasks()
    for task in tasks:
        jira_url = task.get('x_studio_jira_url', '')
        task_name = task.get('name', 'No name')
        print(f"- Task {task['id']}: {task_name} | JIRA: {jira_url}")

