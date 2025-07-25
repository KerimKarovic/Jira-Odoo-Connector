"""
Email notification system for JIRA-Odoo sync errors
"""

import os
import json
import smtplib
import glob
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from functools import wraps

class EmailNotifier:
    def __init__(self):
        self.enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.from_email = os.getenv("EMAIL_FROM")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.to_email = os.getenv("EMAIL_TO")
        self.subject_prefix = os.getenv("EMAIL_SUBJECT_PREFIX", "[JIRA-SYNC]")
        
        os.makedirs("logs", exist_ok=True)
        self.error_state_file = "logs/error_state.json"
        
        # Error collection for batch sending
        self.sync_errors = []
        self.sync_start_time = None
    
    def is_configured(self):
        """Check if email is properly configured"""
        if not self.enabled:
            return False
        return all([self.from_email, self.password, self.to_email])
    
    def start_sync_session(self):
        """Start a new sync session - clear previous errors"""
        self.sync_errors = []
        self.sync_start_time = datetime.now()
        print(f"📧 Email session started - collecting errors for batch send")
    
    def collect_error(self, error, context=None, severity="normal"):
        """Collect error for batch sending instead of immediate send"""
        if not self.is_configured():
            return
            
        error_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or 'None',
            'severity': severity
        }
        
        self.sync_errors.append(error_entry)
        print(f"📧 Error collected: {error_entry['error_type']} ({len(self.sync_errors)} total)")
    
    def send_sync_summary_email(self, sync_stats=None):
        """Send consolidated email with all errors from sync session"""
        if not self.is_configured():
            print("⚠️ Email not configured - skipping notification")
            return
            
        if not self.sync_errors:
            print("✅ No errors to report - skipping email")
            return
        
        # Count error types
        critical_count = sum(1 for e in self.sync_errors if e['severity'] == 'critical')
        normal_count = len(self.sync_errors) - critical_count
        
        # Create subject with quick error explanation
        severity_indicator = "🚨 CRITICAL" if critical_count > 0 else "⚠️"
        
        # Generate quick error summary
        error_types = {}
        for error in self.sync_errors:
            error_type = error['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        quick_summary = ", ".join([f"{count} {error_type}" for error_type, count in error_types.items()])
        
        subject = f"{self.subject_prefix} {severity_indicator} Sync Errors - {quick_summary}"
        
        # Build email body
        body_parts = []
        
        # Header with quick explanation
        if critical_count > 0:
            body_parts.append("🚨 CRITICAL ERRORS DETECTED IN JIRA-ODOO SYNC")
            body_parts.append("")
            body_parts.append("QUICK ERROR EXPLANATION:")
            body_parts.append(f"Critical system failures detected that may prevent sync operations.")
            body_parts.append(f"Connection issues, authentication failures, or API errors occurred.")
        else:
            body_parts.append("⚠️ ERRORS DETECTED IN JIRA-ODOO SYNC")
            body_parts.append("")
            body_parts.append("QUICK ERROR EXPLANATION:")
            body_parts.append(f"Non-critical errors occurred during sync - some worklogs may have been skipped.")
            body_parts.append(f"Data mapping issues, missing URLs, or permission problems detected.")
        
        body_parts.append("")
        body_parts.append("=" * 60)
        body_parts.append("SYNC SESSION SUMMARY")
        body_parts.append("=" * 60)
        body_parts.append(f"Session Start: {self.sync_start_time.strftime('%Y-%m-%d %H:%M:%S') if self.sync_start_time else 'Unknown'}")
        body_parts.append(f"Total Errors: {len(self.sync_errors)}")
        body_parts.append(f"Critical Errors: {critical_count}")
        body_parts.append(f"Normal Errors: {normal_count}")
        
        # Add sync stats if provided
        if sync_stats:
            body_parts.append("")
            body_parts.append("SYNC RESULTS:")
            body_parts.append(f"• Worklogs Created: {sync_stats.get('created', 0)}")
            body_parts.append(f"• Worklogs Skipped: {sync_stats.get('skipped', 0)}")
            body_parts.append(f"• Processing Errors: {sync_stats.get('errors', 0)}")
            if 'duration' in sync_stats:
                body_parts.append(f"• Sync Duration: {sync_stats['duration']:.2f} seconds")
        
        body_parts.append("")
        body_parts.append("=" * 60)
        body_parts.append("DETAILED ERROR LOGS")
        body_parts.append("=" * 60)
        
        # Group errors by severity
        critical_errors = [e for e in self.sync_errors if e['severity'] == 'critical']
        normal_errors = [e for e in self.sync_errors if e['severity'] == 'normal']
        
        if critical_errors:
            body_parts.append("")
            body_parts.append("🚨 CRITICAL ERRORS (Immediate Attention Required):")
            body_parts.append("-" * 50)
            for i, error in enumerate(critical_errors, 1):
                body_parts.append(f"\n{i}. {error['error_type']}")
                body_parts.append(f"   Time: {error['timestamp']}")
                body_parts.append(f"   Context: {error['context']}")
                body_parts.append(f"   Message: {error['error_message']}")
        
        if normal_errors:
            body_parts.append("")
            body_parts.append("⚠️ NORMAL ERRORS (Review When Convenient):")
            body_parts.append("-" * 50)
            for i, error in enumerate(normal_errors, 1):
                body_parts.append(f"\n{i}. {error['error_type']}")
                body_parts.append(f"   Time: {error['timestamp']}")
                body_parts.append(f"   Context: {error['context']}")
                body_parts.append(f"   Message: {error['error_message']}")
        
        body_parts.append("")
        body_parts.append("=" * 60)
        body_parts.append("RECOMMENDED ACTIONS:")
        body_parts.append("=" * 60)
        
        if critical_count > 0:
            body_parts.append("• Check API credentials and network connectivity")
            body_parts.append("• Verify JIRA, Tempo, and Odoo service availability")
            body_parts.append("• Review authentication tokens and permissions")
        
        if normal_count > 0:
            body_parts.append("• Review JIRA issues for missing Odoo URLs")
            body_parts.append("• Check Odoo task/ticket mappings")
            body_parts.append("• Verify custom field configurations")
        
        body_parts.append("")
        body_parts.append("=" * 60)
        body_parts.append("JIRA-Odoo Sync System - Automated Error Report")
        body_parts.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        body_parts.append("=" * 60)
        
        body = "\n".join(body_parts)
        
        if self.send_email(subject, body):
            print(f"✅ Consolidated error email sent ({len(self.sync_errors)} errors)")
        else:
            print(f"❌ Failed to send consolidated error email")
        
        # Clear errors after sending
        self.sync_errors = []
    
    def send_critical_error_immediate(self, error, context=None):
        """Send immediate email for critical system failures that prevent sync"""
        if not self.is_configured():
            print("⚠️ Email not configured - skipping critical notification")
            return
        
        subject = f"{self.subject_prefix} 🚨 CRITICAL SYSTEM FAILURE - Sync Stopped"
        
        body = f"""
🚨 CRITICAL SYSTEM FAILURE - SYNC CANNOT CONTINUE

QUICK ERROR EXPLANATION:
A critical system failure has completely prevented the JIRA-Odoo sync from running.
This requires immediate attention as no worklogs will be synchronized until resolved.

ERROR DETAILS:
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Error Type: {type(error).__name__}
Error Message: {str(error)}
Context: {context or 'System failure during sync initialization'}

IMMEDIATE ACTIONS REQUIRED:
• Check system connectivity and service availability
• Verify all API credentials and authentication tokens
• Review system logs for additional error details
• Restart sync process after resolving the issue

This error prevented the sync from running completely.
No worklogs were processed during this sync attempt.

---
JIRA-Odoo Sync System - Critical Alert
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        if self.send_email(subject, body):
            print("✅ Critical error email sent immediately")
        else:
            print("❌ Critical error email failed")
    
    def load_error_state(self):
        """Load error state from file"""
        try:
            if os.path.exists(self.error_state_file):
                with open(self.error_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load error state: {e}")
        return {}
    
    def save_error_state(self, error_state):
        """Save error state to file"""
        try:
            with open(self.error_state_file, 'w') as f:
                json.dump(error_state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save error state: {e}")
    
    def clear_error_state(self, error_key=None):
        """Clear error state when issues are resolved"""
        error_state = self.load_error_state()
        if error_key:
            error_state.pop(error_key, None)
        else:
            error_state.clear()
        self.save_error_state(error_state)
    
    def send_email(self, subject, body):
        """Send email via SMTP"""
        if not self.to_email:
            raise ValueError("Email recipient not configured")
            
        try:
            msg = MIMEText(body, 'plain', 'utf-8')
            if not self.from_email:
                raise ValueError("Email sender not configured")
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg['Subject'] = subject
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                if not self.from_email or not self.password:
                    raise ValueError("Email credentials not configured")
                server.login(self.from_email, self.password)
                server.send_message(msg)
            
            print("✅ Email sent successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False

# Global instance
email_notifier = EmailNotifier()

def email_on_error(severity="normal"):
    """Decorator to collect errors instead of sending immediate emails"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                context = f"Function: {func.__name__}"
                email_notifier.collect_error(e, context, severity)
                raise
        return wrapper
    return decorator

def test_email_system():
    """Test email notification system"""
    try:
        # Start a test session
        email_notifier.start_sync_session()
        
        # Collect some test errors
        test_error1 = Exception("Test connection error")
        email_notifier.collect_error(test_error1, "Email system test - connection", severity="critical")
        
        test_error2 = ValueError("Test data validation error")
        email_notifier.collect_error(test_error2, "Email system test - validation", severity="normal")
        
        # Send test summary
        test_stats = {
            'created': 5,
            'skipped': 2,
            'errors': 2,
            'duration': 45.67
        }
        
        email_notifier.send_sync_summary_email(test_stats)
        print("✅ Email test completed - check your inbox")
        return True
    except Exception as e:
        print(f"❌ Email test failed: {e}")
        return False

if __name__ == "__main__":
    test_email_system()


