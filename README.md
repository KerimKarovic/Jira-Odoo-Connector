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
├── scheduler.py              # Scheduled runs using APScheduler
├── test_sync.py              # 27 Pytest-based unit tests
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
-Supports sheduling with APScheduler

🔧 Setup Instructions

1.Clone the repository

git clone https://github.com/your-org/jira-odoo-sync.git
cd jira-odoo-sync

1. Create a .env file 
 dp .env.template .env

Update values like :
ODOO_URL=https://odoo.example.com
ODOO_DB=mydb
ODOO_USERNAME=your_user
ODOO_PASSWORD=your_pass

JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your_email@example.com
JIRA_API_TOKEN=your_jira_api_token

TEMPO_API_TOKEN=your_tempo_token


🧪 Running Tests

pytest test_sync.py

▶️Running the Sync Scripts

python main.py --test # Test connections
python main.py # Run sync once
python scheduler.py 30 # Run sync every 30 minutes



📌 Troubleshooting
-If test_sync.py fails on mock or argument issues, check return mocks and hardcoded values like uid=21.

-If Tempo returns 410 GONE, you're likely using an old API version. Switch to https://api.tempo.io/4/worklogs.

-Make sure custom fields (x_jira_worklog_id) exist in Odoo.

## Automated Deployment

### Cron Job Setup

For automated syncing, you can set up a cron job to run the sync at regular intervals:

1. Use the `cron_sync.py` script for automated runs
2. Set up a cron job to run this script at your desired frequency
3. See `CRON_SETUP.md` for detailed instructions for different platforms

Example cron job (runs every hour):
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
