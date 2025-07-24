"""
Email notification system for JIRA-Odoo sync errors
"""

import os
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
import glob

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
        self.error_state_file = "logs/error_state.json"
    
    def is_configured(self):
        """Check if email is properly configured"""
        return self.enabled and all([self.smtp_server, self.from_email, self.password, self.to_email])
    
    def load_error_state(self):
        """Load persistent error state"""
        try:
            if os.path.exists(self.error_state_file):
                with open(self.error_state_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_error_state(self, state):
        """Save persistent error state"""
        try:
            with open(self.error_state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save error state: {e}")
    
    def send_error_email(self, error, context=None, severity="normal"):
        """Send error notification email with 24h repeat logic"""
        if not self.is_configured():
            print("⚠️ Email not configured - skipping notification")
            return
        
        error_key = f"{type(error).__name__}_{context or 'unknown'}"
        current_time = datetime.now()
        
        # Load error state
        error_state = self.load_error_state()
        
        # Check if we should send email (first time or 24h passed)
        should_send = True
        if error_key in error_state:
            last_sent = datetime.fromisoformat(error_state[error_key]['last_sent'])
            if (current_time - last_sent).total_seconds() < 24 * 3600:  # 24 hours
                should_send = False
                print(f"⏰ Error email for {error_key} already sent within 24h - skipping")
        
        if should_send:
            subject = f"{self.subject_prefix} {'🚨 CRITICAL' if severity == 'critical' else '⚠️'} ERROR - {type(error).__name__}"
            
            repeat_info = ""
            if error_key in error_state:
                first_occurrence = error_state[error_key]['first_occurrence']
                repeat_info = f"\n⚠️ RECURRING ERROR - First occurred: {first_occurrence}"
            
            body = f"""
{'🚨 CRITICAL ERROR' if severity == 'critical' else '⚠️ ERROR DETECTED'}

Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
Error: {type(error).__name__}
Message: {str(error)}
Context: {context or 'None'}{repeat_info}

This error will be reported every 24 hours until resolved.

---
JIRA-Odoo Sync System
            """.strip()
            
            if self._send_email(subject, body):
                # Update error state
                if error_key not in error_state:
                    error_state[error_key] = {
                        'first_occurrence': current_time.isoformat(),
                        'count': 1
                    }
                else:
                    error_state[error_key]['count'] += 1
                
                error_state[error_key]['last_sent'] = current_time.isoformat()
                error_state[error_key]['last_error'] = str(error)
                self.save_error_state(error_state)
    
    def clear_error_state(self, error_key=None):
        """Clear error state when issues are resolved"""
        error_state = self.load_error_state()
        if error_key:
            error_state.pop(error_key, None)
        else:
            error_state.clear()
        self.save_error_state(error_state)
    
    def send_weekly_report(self):
        """Send weekly report every Friday with log analysis"""
        if not self.is_configured():
            return
        
        current_time = datetime.now()
        if current_time.weekday() != 4:  # Friday = 4
            return
        
        # Analyze last 7 days of logs
        log_summary = self._analyze_recent_logs(days=7)
        error_state = self.load_error_state()
        
        subject = f"{self.subject_prefix} 📊 Weekly Report - {current_time.strftime('%Y-%m-%d')}"
        
        # Build report
        body = f"""
📊 JIRA-ODOO SYNC - WEEKLY REPORT

Report Period: {(current_time - timedelta(days=7)).strftime('%Y-%m-%d')} to {current_time.strftime('%Y-%m-%d')}

=== SYNC STATISTICS ===
• Total Syncs: {log_summary['total_syncs']}
• Successful Creates: {log_summary['total_created']}
• Skipped (No Odoo URL): {log_summary['total_skipped']}
• Errors: {log_summary['total_errors']}
• Duplicates Prevented: {log_summary['total_duplicates']}

=== ACTIVE ISSUES ===
"""
        
        if error_state:
            body += f"⚠️ {len(error_state)} active error(s) requiring attention:\n"
            for error_key, error_info in error_state.items():
                body += f"• {error_key} (since {error_info['first_occurrence'][:10]}, count: {error_info['count']})\n"
        else:
            body += "✅ No active errors - system running smoothly\n"
        
        body += f"""

=== RECENT ACTIVITY ===
• Most Recent Sync: {log_summary['last_sync_time'] or 'No recent syncs'}
• Average Sync Duration: {log_summary['avg_duration']:.1f}s
• Most Processed JIRA Projects: {', '.join(log_summary['top_projects'][:3])}

=== LOG FILES ANALYZED ===
{chr(10).join(f'• {log}' for log in log_summary['log_files'][-5:])}

---
JIRA-Odoo Sync System
Weekly Report Generated: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        self._send_email(subject, body)
    
    def _analyze_recent_logs(self, days=7):
        """Analyze recent log files for weekly report"""
        cutoff_date = datetime.now() - timedelta(days=days)
        log_pattern = "logs/sync_*.log"
        log_files = glob.glob(log_pattern)
        
        summary = {
            'total_syncs': 0,
            'total_created': 0,
            'total_skipped': 0,
            'total_errors': 0,
            'total_duplicates': 0,
            'log_files': [],
            'last_sync_time': None,
            'durations': [],
            'projects': []
        }
        
        for log_file in sorted(log_files):
            try:
                # Extract date from filename
                filename = os.path.basename(log_file)
                date_str = filename.split('_')[1]  # sync_20250724_065528.log
                log_date = datetime.strptime(date_str, '%Y%m%d')
                
                if log_date < cutoff_date:
                    continue
                
                summary['log_files'].append(filename)
                
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Count sync events
                    if 'CRON SYNC STARTED' in content:
                        summary['total_syncs'] += 1
                    
                    # Extract final stats
                    for line in content.split('\n'):
                        if 'Sync completed:' in line:
                            parts = line.split('Sync completed: ')[1]
                            if 'created' in parts:
                                created = int(parts.split(' created')[0])
                                summary['total_created'] += created
                            if 'skipped' in parts:
                                skipped = int(parts.split(', ')[1].split(' skipped')[0])
                                summary['total_skipped'] += skipped
                            if 'errors' in parts:
                                errors = int(parts.split(', ')[2].split(' errors')[0])
                                summary['total_errors'] += errors
                        
                        if 'Duplicate worklog' in line:
                            summary['total_duplicates'] += 1
                        
                        if 'Processing worklog: JIRA' in line:
                            project = line.split('JIRA ')[1].split('-')[0]
                            summary['projects'].append(project)
                        
                        if 'SYNC COMPLETED in' in line:
                            duration = float(line.split('in ')[1].split(' seconds')[0])
                            summary['durations'].append(duration)
                            
                            # Get timestamp for last sync
                            timestamp = line.split(' - ')[0]
                            summary['last_sync_time'] = timestamp
                            
            except Exception as e:
                print(f"⚠️ Error analyzing log {log_file}: {e}")
        
        # Calculate averages
        summary['avg_duration'] = sum(summary['durations']) / len(summary['durations']) if summary['durations'] else 0
        summary['top_projects'] = list(set(summary['projects']))
        
        return summary
    
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
            return True
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False

# Global instance
email_notifier = EmailNotifier()

def email_on_error(severity="normal"):
    """Decorator to send emails on function errors with 24h repeat logic"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # Clear error state on successful execution
                error_key = f"{func.__name__}_success"
                email_notifier.clear_error_state(error_key)
                return result
            except Exception as e:
                context = f"Function: {func.__name__}"
                email_notifier.send_error_email(e, context, severity)
                raise
        return wrapper
    return decorator

