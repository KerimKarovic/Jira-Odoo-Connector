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
├── cron_sync.py              # Cron-compatible sync script
├── email_notifier.py         # Email notification system 
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker container configuration
├── docker-compose.yml        # Docker Compose setup
├── .env.template             # Template for .env config
└── README.md                 # This file

🚀 Features

- Syncs tempo worklogs from Jira to Odoo 
- Extracts Odoo task IDs from Jira issue URLs
- Avoids duplication using Tempo Worklog ID
- Logs time to Web Development Team in Odoo
- Fully testable with 30+ Pytest cases 
- Supports .env configuration
- Smart email notifications with batch error collection
- Consolidated error reporting with sync statistics
- Critical vs normal error classification
- **Docker containerized deployment**
- **Production-ready with cron scheduling**

🔧 Setup Instructions

## Local Development

1. Clone the repository
```bash
git clone https://github.com/KerimKarovic/Jira-Odoo-Connector.git
cd jira-odoo-connector
```

2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Create a .env file 
```bash
cp .env.template .env
```

Update values like:
```env
ODOO_URL=https://odoo.example.com
ODOO_DB=mydb
ODOO_USERNAME=your_user
ODOO_PASSWORD=your_pass

JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_USER=your_email@example.com
JIRA_API_TOKEN=your_jira_api_token

TEMPO_API_TOKEN=your_tempo_token
```

## Docker Deployment (Recommended)

1. Clone the repository on your server
```bash
git clone https://github.com/KerimKarovic/Jira-Odoo-Connector.git jira-odoo-connector
cd jira-odoo-connector
```

2. Create your .env file with production credentials
```bash
cp .env.template .env
# Edit .env with your production values
```

3. Set up proper permissions for logs
```bash
sudo chown -R 1000:1000 logs/
```

4. Test the Docker setup
```bash
docker-compose run --rm jira-odoo-connector python main.py --test
```

5. Set up cron job for nightly execution
```bash
sudo crontab -e
```
Add this line for 2 AM daily execution:
```bash
0 2 * * * cd /path/to/jira-odoo-connector && docker-compose run --rm jira-odoo-sync
```

🧪 Running Tests

```bash
# Local testing
python main.py --test
python main.py

# Docker testing
docker-compose run --rm jira-odoo-connector python main.py --test
docker-compose run --rm jira-odoo-connector python main.py
```

📌 Troubleshooting

- **Permission errors with logs**: Ensure logs directory has correct ownership: `sudo chown -R 1000:1000 logs/`
- **Docker build fails**: Check that all files are present and .env is configured
- **Cron job not running**: Verify cron service is active with `sudo systemctl status cron`
- **Email not working**: Ensure 'EMAIL_ENABLED=true' and all email credentials are set in '.env'

## Email Notifications

The system can send email notifications for critical errors and system failures.

### Email Setup

Add these variables to your `.env` file:
```env
EMAIL_ENABLED=true
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_TO=admin@yourcompany.com
EMAIL_SUBJECT_PREFIX=[JIRA-SYNC]
```

**Note**: For Gmail, use an App Password instead of your regular password.⏱️ Jira-Odoo Timesheet Sync (via Tempo)

