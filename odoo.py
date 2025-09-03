"""
Odoo integration
Handles connection to Odoo and worklog creation with dynamic employee mapping
"""

import os
import socket
import xmlrpc.client
from xmlrpc.client import Fault, ProtocolError
from datetime import date
from typing import Any, Optional
from utils import config
from email_notifier import email_notifier

# Configuration
ODOO_URL = config["odoo"]["url"].rstrip('/')
ODOO_DB = config["odoo"]["db"]
ODOO_USERNAME = config["odoo"]["username"]
ODOO_PASSWORD = config["odoo"]["password"]

# Mapping field on hr.employee (set the same name in Odoo or via .env)
EMPLOYEE_JIRA_FIELD = os.getenv("ODOO_EMPLOYEE_JIRA_FIELD", "x_jira_employee_id").strip()
# Optional fallback employee (int id) when mapping is missing
FALLBACK_EMPLOYEE_ID = int((os.getenv("ODOO_FALLBACK_EMPLOYEE_ID", "0") or "0").strip() or 0)


class OdooClient:
    def __init__(self):
        self.common = None
        self.models = None
        self.uid = None
        self.connected = False
        self._employee_cache = {}

    # ---------------------------
    # Connection
    # ---------------------------
    def connect(self) -> bool:
        """Establish Odoo connection"""
        if self.connected:
            return True
        try:
            self.common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
            self.models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
            self.uid = self.common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
            if not self.uid:
                email_notifier.collect_error(
                    Exception("Odoo authentication failed - invalid credentials"),
                    "Odoo Authentication Failure",
                    severity="critical"
                )
                return False
            self.connected = True
            return True

    # Catch transport/protocol explicitly to get clearer alerts
        except (ProtocolError, Fault, socket.error, ConnectionError) as e:
            email_notifier.collect_error(e, "Odoo Connection/Protocol Failure", severity="critical")
            return False
        except Exception as e:
            email_notifier.collect_error(e, "Odoo System Error", severity="critical")
            return False

    # ---------------------------
    # Employee resolution
    # ---------------------------
    def resolve_employee_id(self, jira_author: Any) -> Optional[int]:
        """Resolve Odoo employee ID from JIRA author with caching"""
        if not self.connect():
            return FALLBACK_EMPLOYEE_ID or None

        # Extract identifiers
        if isinstance(jira_author, dict):
            account_id = jira_author.get("accountId") or jira_author.get("id")
            email = jira_author.get("email") or jira_author.get("emailAddress")
            name = jira_author.get("displayName") or jira_author.get("name")
        elif isinstance(jira_author, str):
            account_id = jira_author
            email = name = None
        else:
            return FALLBACK_EMPLOYEE_ID or None

        cache_key = account_id or email or name
        if cache_key in self._employee_cache:
            return self._employee_cache[cache_key]

        # Search with priority: account_id -> email -> name
        for field, value in [
            (EMPLOYEE_JIRA_FIELD, account_id),
            ('work_email', email),
            ('name', name)
        ]:
            if value and self.models:
                try:
                    ids = self.models.execute_kw(
                        ODOO_DB, self.uid, ODOO_PASSWORD,
                        'hr.employee', 'search',
                        [[(field, '=' if field != 'name' else 'ilike', value)]],
                        {'limit': 1}
                    )
                    if ids and isinstance(ids, list) and ids:
                        emp_id = ids[0]
                        if cache_key:
                            self._employee_cache[cache_key] = emp_id
                        return emp_id
                except Exception:
                    continue

        # Fallback
        emp_id = FALLBACK_EMPLOYEE_ID or None
        if cache_key and emp_id:
            self._employee_cache[cache_key] = emp_id
            # NEW: log that we fell back (helps ops finish mappings)
            email_notifier.collect_error(
                Exception("Using fallback employee"),
                f"Using FALLBACK_EMPLOYEE_ID={emp_id} for author={cache_key}",
                severity="normal"
            )
        return emp_id

    # Timesheet creation (project.task only, simple)
    def create_timesheet_entry(
        self,
        task_id: int,
        hours: float,
        description: str,
        work_date: Optional[str] = None,
        tempo_worklog_id: Optional[str] = None,
        model_type: str = 'project.task',
        *,
        jira_author: Any = None,
        employee_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Create timesheet entry in Odoo (project.task).
        If employee_id is not given, resolve from jira_author; otherwise fallback if configured.
        """
        if not self.connect() or not self.models:
            email_notifier.collect_error(
                Exception("Odoo models not available"),
                "Odoo models unavailable during timesheet creation",
                severity="critical"
            )
            return None

        if model_type != 'project.task':
            # Keep behavior simple but visible if a different model sneaks in
            email_notifier.collect_error(
                Exception("Unsupported model_type"),
                f"Only 'project.task' is supported (got '{model_type}'), proceeding with project.task.",
                severity="normal"
            )

        if work_date is None:
            work_date = date.today().strftime('%Y-%m-%d')

        emp_id = employee_id or self.resolve_employee_id(jira_author)
        if not emp_id:
            email_notifier.collect_error(
                Exception("Timesheet skipped due to missing employee_id"),
                f"Timesheet skipped (no employee_id) for task {model_type}:{task_id}",
                severity="normal"
            )
            return None

        try:
            # Read task to get project_id
            task_data = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'project.task', 'read',
                [[int(task_id)]],
                {'fields': ['name', 'project_id']}
            )

            # Pylance-safe guard before indexing and .get()
            first_item = task_data[0] if isinstance(task_data, list) and task_data else None
            if not isinstance(first_item, dict):
                email_notifier.collect_error(
                    Exception(f"Odoo {model_type} ID {task_id} not found"),
                    f"Odoo Task Not Found - {model_type} ID {task_id}",
                    severity="normal"
                )
                return None

            project_id = None
            project_id_field = first_item.get('project_id')
            if isinstance(project_id_field, (list, tuple)) and project_id_field:
                if isinstance(project_id_field[0], int):
                    project_id = project_id_field[0]
            elif isinstance(project_id_field, int):
                project_id = project_id_field

            worklog_data = {
                'task_id': int(task_id),
                'project_id': project_id,
                'name': str(description),
                'unit_amount': float(hours),
                'date': str(work_date),
                'employee_id': emp_id,
            }

            if tempo_worklog_id:
                worklog_data['x_jira_worklog_id'] = str(tempo_worklog_id)

            result = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'account.analytic.line', 'create',
                [worklog_data]
            )
            return int(result) if isinstance(result, int) else None

        except (ProtocolError, Fault, socket.error, ConnectionError) as e:
            email_notifier.collect_error(e, "Odoo connection error during timesheet creation", severity="critical")
            return None
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ['permission', 'access', 'denied', 'forbidden']):
                email_notifier.collect_error(e, "Odoo permission error during timesheet creation", severity="critical")
            else:
                email_notifier.collect_error(e, "Odoo error during timesheet creation", severity="critical")
            return None

    # Duplicate check
    def check_existing_worklogs_by_worklog_id(self, tempo_worklog_id: Optional[str]) -> bool:
        """Check if worklog entry already exists by x_jira_worklog_id"""
        if not tempo_worklog_id or not self.connect() or not self.models:
            return False
        try:
            existing_ids = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'account.analytic.line', 'search',
                [[('x_jira_worklog_id', '=', str(tempo_worklog_id))]],
                {'limit': 1}
            )
            return bool(existing_ids)
        except (ProtocolError, Fault, socket.error, ConnectionError) as e:
            email_notifier.collect_error(e, "Odoo error during duplicate check", severity="normal")
            return False
        except Exception:
            return False

# Global instance
odoo_client = OdooClient()

# Backward-compatible wrappers
def create_timesheet_entry(*args, **kwargs):
    return odoo_client.create_timesheet_entry(*args, **kwargs)

def check_existing_worklogs_by_worklog_id(*args, **kwargs):
    return odoo_client.check_existing_worklogs_by_worklog_id(*args, **kwargs)

def test_odoo_connection():
    return odoo_client.connect()
