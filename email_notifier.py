"""
Email notification system for JIRA-Odoo sync errors
"""

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
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
        self.sync_errors = []
        self.sync_start_time = None
    
    def is_configured(self):
        """Check if email is properly configured"""
        return self.enabled and all([self.from_email, self.password, self.to_email])
    
    def start_sync_session(self):
        """Start a new sync session"""
        self.sync_errors = []
        self.sync_start_time = datetime.now()
        print(f"📧 Email session started - collecting errors for batch send")
    
    def collect_error(self, error, context=None, severity="normal"):
        """Collect error for batch sending"""
        if not self.is_configured():
            return
            
        self.sync_errors.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or 'None',
            'severity': severity
        })
        print(f"📧 Error collected: {type(error).__name__} ({len(self.sync_errors)} total)")
    
    def send_sync_summary_email(self, sync_stats=None, log_file_path=None):
        """Send consolidated email with all errors from sync session"""
        print(f"📧 Email check: configured={self.is_configured()}, errors={len(self.sync_errors)}")
        
        if not self.is_configured():
            print("📧 Email not configured - skipping")
            return
        
        if not self.sync_errors:
            print("📧 No errors collected - skipping email")
            return
        
        print(f"📧 Sending email for {len(self.sync_errors)} errors")
        
        critical_count = sum(1 for e in self.sync_errors if e['severity'] == 'critical')
        subject = f"{self.subject_prefix} 🚨 CRITICAL ERRORS DETECTED" if critical_count > 0 else f"{self.subject_prefix} ⚠️ ERRORS DETECTED"
        
        body_parts = [
            "🚨 CRITICAL ERRORS DETECTED" if critical_count > 0 else "⚠️ ERRORS DETECTED IN JIRA-ODOO SYNC",
            "",
            "SYNC SUMMARY:",
            f"• Total Errors: {len(self.sync_errors)}",
            f"• Critical: {critical_count}, Normal: {len(self.sync_errors) - critical_count}",
        ]
        
        if sync_stats:
            body_parts.extend([
                f"• Created: {sync_stats.get('created', 0)}",
                f"• Skipped: {sync_stats.get('skipped', 0)}",
            ])
        
        body_parts.extend([
            "",
            "RECOMMENDED ACTIONS:",
            "• Check API credentials and connectivity" if critical_count > 0 else "• Review JIRA-Odoo URL mappings",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        self.send_email_with_attachment(subject, "\n".join(body_parts), log_file_path)
        self.sync_errors = []
    
    def send_critical_error_immediate(self, error, context=None, log_file_path=None):
        """Send immediate email for critical system failures with full log"""
        if not self.is_configured():
            return
        
        subject = f"{self.subject_prefix} 🚨 CRITICAL SYSTEM FAILURE"
        
        body_parts = [
            "🚨 CRITICAL SYSTEM FAILURE - SYNC CANNOT CONTINUE",
            "",
            f"ERROR: {type(error).__name__}",
            f"MESSAGE: {str(error)}",
            f"CONTEXT: {context or 'System failure'}",
            f"TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "IMMEDIATE ACTION REQUIRED:",
            "• Check system connectivity and API credentials",
            "• Review logs for additional details",
            "• Restart sync after resolving issues"
        ]
        
        if log_file_path and os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                
                body_parts.extend([
                    "",
                    "=" * 50,
                    "FULL SYNC LOG (for debugging):",
                    "=" * 50,
                    log_content
                ])
            except Exception as e:
                body_parts.extend([
                    "",
                    f"⚠️ Could not read log file: {e}"
                ])

        if self.send_email(subject, "\n".join(body_parts)):
            print("📧 ✅ Critical email sent successfully")
        else:
            print("📧 ❌ Critical email failed to send")
    
    def send_email(self, subject, body):
        """Send email via SMTP"""
        try:
            if not self.is_configured():
                raise ValueError("Email credentials not configured")
            
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['From'] = self.from_email or ""
            msg['To'] = self.to_email or ""
            msg['Subject'] = subject
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                if not self.from_email or not self.password:
                    raise ValueError("Email credentials (from_email and password) are required")
                
                server.login(self.from_email, self.password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            return False

    def send_email_with_attachment(self, subject, body, attachment_path=None):
        """Send email with optional attachment"""
        try:
            if not self.is_configured():
                raise ValueError("Email credentials not configured")
            
            # Create multipart message
            msg = MIMEMultipart()
            msg['From'] = self.from_email or ""
            msg['To'] = self.to_email or ""
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Add attachment if provided
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(attachment_path)}'
                )
                msg.attach(part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                if not self.from_email or not self.password:
                    raise ValueError("Email credentials (from_email and password) are required")
                
                server.login(self.from_email, self.password)
                server.send_message(msg)
            
            print("📧 ✅ Email sent successfully")
            return True
        except Exception as e:
            print(f"📧 ❌ Email failed: {e}")
            return False

# Global instance
email_notifier = EmailNotifier()

def email_on_error(severity="normal"):
    """Decorator to collect errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                email_notifier.collect_error(e, f"Function: {func.__name__}", severity)
                raise
        return wrapper
    return decorator

def test_email_system():
    """Test email notification system"""
    try:
        email_notifier.start_sync_session()
        
        test_error1 = Exception("Test connection error")
        email_notifier.collect_error(test_error1, "Email test - connection", "critical")
        
        test_error2 = ValueError("Test validation error")
        email_notifier.collect_error(test_error2, "Email test - validation", "normal")
        
        test_stats = {'created': 5, 'skipped': 2, 'errors': 2, 'duration': 45.67}
        email_notifier.send_sync_summary_email(test_stats)
        
        return True
    except Exception as e:
        return False

if __name__ == "__main__":
    test_email_system()






