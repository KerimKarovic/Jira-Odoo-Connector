"""
Email notification system for JIRA-Odoo sync errors
"""

import os
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from functools import wraps

class EmailNotifier:
    def __init__(self):
        self.enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.smtp_server = os.getenv("EMAIL_SMTP_SERVER", "")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.from_email = os.getenv("EMAIL_FROM", "")
        self.password = os.getenv("EMAIL_PASSWORD", "")
        self.to_email = os.getenv("EMAIL_TO", "")
        self.subject_prefix = os.getenv("EMAIL_SUBJECT_PREFIX", "[JIRA-SYNC]")
        
        os.makedirs("logs", exist_ok=True)
    
    def is_configured(self):
        """Check if email is properly configured"""
        return self.enabled and all([self.smtp_server, self.from_email, self.password, self.to_email])
    
    def send_error_email(self, error, context=None, severity="normal"):
        """Send error notification email"""
        if not self.is_configured():
            print("⚠️ Email not configured - skipping notification")
            return
            
        subject = f"{self.subject_prefix} {'CRITICAL ' if severity == 'critical' else ''}ERROR - {type(error).__name__}"
        
        body = f"""
{'🚨 CRITICAL ERROR' if severity == 'critical' else '⚠️ ERROR DETECTED'}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Error: {type(error).__name__}
Message: {str(error)}

Context: {context or 'None'}

---
JIRA-Odoo Sync System
        """.strip()
        
        self._send_email(subject, body)
    
    def send_weekly_health_report(self):
        """Send weekly health report (called from cron)"""
        if not self.is_configured() or datetime.now().weekday() != 0:  # Monday = 0
            return
            
        subject = f"{self.subject_prefix} Weekly Health Report - System Running ✅"
        body = f"""
✅ JIRA-ODOO SYNC - WEEKLY HEALTH REPORT

Report Date: {datetime.now().strftime('%Y-%m-%d')}

System is running normally.
Check logs for detailed sync information.

---
JIRA-Odoo Sync System
        """.strip()
        
        self._send_email(subject, body)
    
    def _send_email(self, subject, body):
        """Send email via SMTP"""
        try:
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg['Subject'] = subject
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.password)
                server.send_message(msg)
            
            print(f"✅ Email sent: {subject}")
        except Exception as e:
            print(f"❌ Failed to send email: {e}")

# Global instance
email_notifier = EmailNotifier()

def email_on_error(severity="normal"):
    """Decorator to send emails on function errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = f"Function: {func.__name__}"
                email_notifier.send_error_email(e, context, severity)
                raise
        return wrapper
    return decorator
