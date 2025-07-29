
"""
Odoo integration
Handles connection to Odoo and worklog creation
"""

import xmlrpc.client
from datetime import datetime, date
from typing import Optional
from utils import config
from email_notifier import email_notifier

# Configuration
ODOO_URL = config["odoo"]["url"].rstrip('/')
ODOO_DB = config["odoo"]["db"]
ODOO_USERNAME = config["odoo"]["username"]
ODOO_PASSWORD = config["odoo"]["password"]

# WebDevelopment Team Employee ID
WEBDEV_TEAM_EMPLOYEE_ID = 21

class OdooClient:
    def __init__(self):
        self.common = None
        self.models = None
        self.uid = None
        self.connected = False
    
    def connect(self):
        """Establish Odoo connection"""
        if self.connected:
            return True
            
        try:
            self.common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
            self.models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
            
            self.uid = self.common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
            if not self.uid:
                auth_error = Exception("Odoo authentication failed - invalid credentials")
                email_notifier.collect_error(auth_error, "Odoo Authentication Failure", severity="critical")
                return False
                
            self.connected = True
            return True
            
        except ConnectionError as e:
            email_notifier.collect_error(e, "Odoo Connection Failure", severity="critical")
            return False
        except Exception as e:
            email_notifier.collect_error(e, "Odoo System Error", severity="critical")
            return False
    
    def create_timesheet_entry(self, task_id: int, hours: float, description: str,
                               work_date: Optional[str] = None,
                               tempo_worklog_id: Optional[str] = None, model_type: str = 'project.task') -> Optional[int]:
        """Create timesheet entry"""
        if not self.connect():
            return None
        
        assert self.models is not None, "Models should be initialized after successful connection"
        
        if work_date is None:
            work_date = date.today().strftime('%Y-%m-%d')
        
        try:
            # Get task/ticket details based on model type
            if model_type == 'helpdesk.ticket':
                task_data = self.models.execute_kw(
                    ODOO_DB, self.uid, ODOO_PASSWORD,
                    'helpdesk.ticket', 'read',
                    [[int(task_id)]],
                    {'fields': ['name']}
                )
                
                if not task_data or not isinstance(task_data, list) or len(task_data) == 0:
                    task_error = Exception(f"Odoo {model_type} ID {task_id} not found")
                    email_notifier.collect_error(task_error, f"Odoo Task Not Found - {model_type} ID {task_id}", severity="normal")
                    return None
                
                # For helpdesk tickets, create timesheet entry linked to ticket
                worklog_data = {
                    'helpdesk_ticket_id': int(task_id),
                    'name': str(description),
                    'unit_amount': float(hours),
                    'date': str(work_date),
                    'employee_id': WEBDEV_TEAM_EMPLOYEE_ID,
                }
            else:
                task_data = self.models.execute_kw(
                    ODOO_DB, self.uid, ODOO_PASSWORD,
                    'project.task', 'read',
                    [[int(task_id)]],
                    {'fields': ['name', 'project_id']}
                )
                
                if not task_data or not isinstance(task_data, list) or len(task_data) == 0:
                    task_error = Exception(f"Odoo {model_type} ID {task_id} not found")
                    email_notifier.collect_error(task_error, f"Odoo Task Not Found - {model_type} ID {task_id}", severity="normal")
                    return None
                    
                project_id_field = task_data[0].get('project_id')
                
                # Handle project_id which can be False, int, or [id, name] tuple
                project_id = None
                if isinstance(project_id_field, list) and len(project_id_field) > 0:
                    project_id = project_id_field[0]
                elif isinstance(project_id_field, int):
                    project_id = project_id_field
                
                # For project tasks
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
            worklog_result = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'account.analytic.line', 'create',
                [worklog_data]
            )
            
            # Handle the result which should be an integer ID
            if isinstance(worklog_result, int):
                worklog_id = worklog_result
                return worklog_id
            else:
                return None
            
        except ConnectionError as e:
            email_notifier.collect_error(e, f"Odoo connection error during timesheet creation", severity="critical")
            return None
        except Exception as e:
            # Check if it's a permission error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['permission', 'access', 'denied', 'forbidden']):
                email_notifier.collect_error(e, f"Odoo permission error during timesheet creation", severity="normal")
            return None

    def check_existing_worklogs_by_worklog_id(self, tempo_worklog_id: Optional[str]) -> bool:
        """Check if worklog entry already exists"""
        if not tempo_worklog_id or not self.connect():
            return False
        
        assert self.models is not None, "Models should be initialized after successful connection"
        
        try:
            existing_ids = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'account.analytic.line', 'search',
                [[('x_jira_worklog_id', '=', str(tempo_worklog_id))]],
                {'limit': 1}
            )
            
            if existing_ids:
                return True
            
            return False
            
        except Exception as e:
            return False

# Global instance
odoo_client = OdooClient()

# Keep backward compatibility
def create_timesheet_entry(*args, **kwargs):
    return odoo_client.create_timesheet_entry(*args, **kwargs)

def check_existing_worklogs_by_worklog_id(*args, **kwargs):
    return odoo_client.check_existing_worklogs_by_worklog_id(*args, **kwargs)

def test_odoo_connection():
    return odoo_client.connect()




