#!/bin/bash
# AI Architect v2 - Cron Setup Script
#
# This script sets up cron jobs for daily, weekly, and monthly execution.
# Run this script once to configure automated execution.
#
# Usage:
#   ./scripts/setup_cron.sh
#
# The cron jobs will run:
#   - Daily:   At midnight (00:00)
#   - Weekly:  Monday at 01:00
#   - Monthly: 1st of month at 02:00

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="/var/log/ai-architect"
CRON_USER="${USER:-$USER}"

echo "=== AI Architect v2 - Cron Setup ==="
echo "Project directory: $PROJECT_DIR"
echo "Log directory: $LOG_DIR"
echo "Cron user: $CRON_USER"
echo ""

# Create log directory
echo "Creating log directory..."
sudo mkdir -p "$LOG_DIR"
sudo chown "$CRON_USER:$CRON_USER" "$LOG_DIR"

# Create logrotate configuration
echo "Setting up log rotation..."
sudo tee /etc/logrotate.d/ai-architect > /dev/null << 'EOF'
/var/log/ai-architect/*.log {
    weekly
    rotate 8
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ai-architect ai-architect
}
EOF

# Create cron jobs
echo "Creating cron jobs..."

# Daily at midnight
DAILY_JOB="0 0 * * * cd $PROJECT_DIR && docker compose exec -T app python /app/main.py --mode daily >> $LOG_DIR/daily.log 2>&1"

# Weekly on Monday at 01:00
WEEKLY_JOB="0 1 * * 1 cd $PROJECT_DIR && docker compose exec -T app python /app/main.py --mode weekly >> $LOG_DIR/weekly.log 2>&1"

# Monthly on 1st at 02:00
MONTHLY_JOB="0 2 1 * * cd $PROJECT_DIR && docker compose exec -T app python /app/main.py --mode monthly >> $LOG_DIR/monthly.log 2>&1"

# Remove old ai-architect jobs and add new ones
(
    crontab -l 2>/dev/null | grep -v "ai-architect" || true
    echo "# AI Architect v2 - Daily digest"
    echo "$DAILY_JOB"
    echo "# AI Architect v2 - Weekly synthesis"
    echo "$WEEKLY_JOB"
    echo "# AI Architect v2 - Monthly report"
    echo "$MONTHLY_JOB"
) | crontab -

echo ""
echo "=== Cron Jobs Installed ==="
crontab -l | grep -A1 "ai-architect"
echo ""
echo "Logs will be written to: $LOG_DIR"
echo ""
echo "To verify: crontab -l"
echo "To edit: crontab -e"
echo ""
echo "Setup complete!"
