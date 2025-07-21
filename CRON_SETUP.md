# Setting Up Cron Jobs for JIRA-Odoo Sync

This guide explains how to set up automated sync using cron jobs on different platforms.

## Linux/Unix Cron Setup

1. Open your crontab file:
   ```
   crontab -e
   ```

2. Add a line to run the sync every hour (adjust the path as needed):
   ```
   0 * * * * cd /path/to/jira-odoo-sync && /path/to/python cron_sync.py >> /path/to/jira-odoo-sync/cron.log 2>&1
   ```

3. For different schedules:
   - Every 30 minutes: `*/30 * * * *`
   - Every 4 hours: `0 */4 * * *`
   - Daily at midnight: `0 0 * * *`

## Windows Task Scheduler

1. Open Task Scheduler
2. Click "Create Basic Task"
3. Name it "JIRA-Odoo Sync" and click Next
4. Select "Daily" or your preferred schedule and click Next
5. Set the start time and recurrence pattern
6. Select "Start a program" and click Next
7. Browse to your Python executable (e.g., `C:\path\to\python.exe`)
8. Add arguments: `C:\path\to\jira-odoo-sync\cron_sync.py`
9. Set "Start in" to your project directory: `C:\path\to\jira-odoo-sync`
10. Click Next, then Finish

## Docker Setup

If you're using Docker, add this to your `docker-compose.yml`:

```yaml
version: '3'
services:
  jira-odoo-sync:
    build: .
    volumes:
      - ./:/app
      - ./logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
    command: sh -c "cron && tail -f /app/logs/sync_*.log"
```

And in your Dockerfile:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Setup cron
RUN apt-get update && apt-get -y install cron
RUN echo "0 * * * * cd /app && python /app/cron_sync.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/jira-odoo-cron
RUN chmod 0644 /etc/cron.d/jira-odoo-cron
RUN crontab /etc/cron.d/jira-odoo-cron

# Create logs directory
RUN mkdir -p /app/logs

CMD ["cron", "-f"]
```

## Systemd Timer (Modern Linux)

1. Create a service file `/etc/systemd/system/jira-odoo-sync.service`:
   ```
   [Unit]
   Description=JIRA to Odoo Sync Service
   After=network.target

   [Service]
   Type=oneshot
   WorkingDirectory=/path/to/jira-odoo-sync
   ExecStart=/path/to/python /path/to/jira-odoo-sync/cron_sync.py
   User=youruser

   [Install]
   WantedBy=multi-user.target
   ```

2. Create a timer file `/etc/systemd/system/jira-odoo-sync.timer`:
   ```
   [Unit]
   Description=Run JIRA to Odoo Sync hourly

   [Timer]
   OnBootSec=5min
   OnUnitActiveSec=1h
   AccuracySec=1s

   [Install]
   WantedBy=timers.target
   ```

3. Enable and start the timer:
   ```
   sudo systemctl enable jira-odoo-sync.timer
   sudo systemctl start jira-odoo-sync.timer
   ```

## Monitoring

- Check the logs in the `logs/` directory for sync results
- For cron jobs, check the system logs:
  - Linux: `grep CRON /var/log/syslog`
  - macOS: `log show --predicate 'eventMessage contains "cron"'`

## Troubleshooting

- Ensure the script has execute permissions: `chmod +x cron_sync.py`
- Verify environment variables are available to the cron job
- Check that the Python path is correct
- Ensure the working directory is set correctly