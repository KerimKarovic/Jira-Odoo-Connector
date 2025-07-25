⏱️ Jira-Odoo Timesheet Sync (via Tempo)

This project synchronizes worklogs(timesheets) from tempo(JIRA) into Odoo, allowing seamless tracking of time spent on Jira issues directly within Odoo. It extracts time enteries from Tempo API , fetches related Jira issues, matches them to Odoo tasks, and logs them automatically in Odoo.

🛠️ Architecture

+-------------+     +------------------+     +-----------------+
|   Tempo API | --> | Get Jira Issue   | --> | Extract Odoo ID |
+-------------+     +------------------+     +-----------------+
                                             |
                                              v
                                      +------------------+
                                      | Check in Odoo DB |
                                      +------------------+
                                              |
                     +------------------------+------------------------+
                     |                                                 |
             +------------------+                          +----------------------+
             | Duplicate Found  |                          | No Match - Create it |
             +------------------+                          +----------------------+

📁 Project Structure

.
├── main.py                   # Main sync logic
├── tempo.py                  # Tempo API integration
├── jira.py                   # JIRA issue fetching and parsing
├── odoo.py                   # Odoo connection and timesheet logging
├── utils.py                  # Configuration, logging, and helpers
├── cron_sync_simple.py       # Windows-compatible cron script
├── run_sync.bat              # Windows Task Scheduler batch file
├── install_windows.bat       # Windows installation script
├── requirements.txt          # Python dependencies
├── .env.template             # Template for .env config
└── README.md                 # This file

🚀 Features

-Syncs tempo worklogs from Jirra to Odoo 
-Extracts Odoo task IDs from Jira issue URLs
-Avoids duplication using Tempo Worklog ID
-Logs time to Web Development Team in Odoo
-Fully testable with 30+ Pytest cases
-Supports Docker deployment for easy setup 
-Supports .env configuration
-Supports Windows Task Scheduler automation

🔧 Setup Instructions

1. Clone the repository

```
git clone https://github.com/KerimKarovic/Jira-Odoo-Connector.git
cd jira-odoo-sync
```

2. Create a .env file 
```
cp .env.template .env
```

Update values like:
```
ODOO_URL=https://odoo.example.com
ODOO_DB=mydb
ODOO_USERNAME=your_user
ODOO_PASSWORD=your_pass

JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your_email@example.com
JIRA_API_TOKEN=your_jira_api_token

TEMPO_API_TOKEN=your_tempo_token
```

🧪 Running Tests

```
pytest test_sync.py
```

▶️Running the Sync Scripts

```
python main.py --test # Test connections
python main.py # Run sync once
run_sync.bat # Run with Windows batch file
```

📌 Troubleshooting
-If test_sync.py fails on mock or argument issues, check return mocks and hardcoded values like uid=21.

-If Tempo returns 410 GONE, you're likely using an old API version. Switch to https://api.tempo.io/4/worklogs.

-Make sure custom fields (x_jira_worklog_id) exist in Odoo.

## Automated Deployment

### Windows Task Scheduler Setup

For automated syncing on Windows:

1. Run the `install_windows.bat` script to set up the environment
2. Test the sync manually with `run_sync.bat`
3. Open Windows Task Scheduler:
   - Create Basic Task: "JIRA-Odoo Sync"
   - Trigger: Daily (or your preferred schedule)
   - Action: Start a program
   - Program/script: `C:\path\to\jira_odoo_sync\run_sync.bat`
   - Start in: `C:\path\to\jira_odoo_sync`

### Linux/Unix Cron Setup

For Linux/Unix systems, set up a cron job:

```
0 * * * * cd /path/to/jira-odoo-sync && /path/to/python cron_sync.py
```

### Docker Deployment

For containerized deployment:

1. Build the Docker image:
   ```
   docker build -t jira-odoo-sync .
   ```

2. Run the container:
   ```
   docker run -d --name jira-odoo-sync \
     -v $(pwd)/logs:/app/logs \
     -v $(pwd)/.env:/app/.env \
     jira-odoo-sync
   ```

3. Check logs:
   ```
   docker logs jira-odoo-sync
   ```

## Email Notifications

The system can send email notifications for critical errors and system failures.

### Email Setup

Add these variables to your `.env` file:

```
EMAIL_ENABLED=true
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_TO=admin@yourcompany.com
EMAIL_SUBJECT_PREFIX=[JIRA-SYNC]
```

**Note**: For Gmail, use an App Password instead of your regular password.

### Test Email System

```bash
python email_notifier.py
```
