#!/bin/bash
# Setup cron job for automatic incident cleanup
# This ensures cleanup runs even if the system is restarted

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_BIN=$(which python3)

echo "Setting up automatic cleanup cron job..."
echo "Script directory: $SCRIPT_DIR"
echo "Python binary: $PYTHON_BIN"

# Create cron job entry (runs daily at 3 AM)
CRON_CMD="0 3 * * * cd $SCRIPT_DIR && $PYTHON_BIN cleanup_old_incidents.py --days 30 >> /tmp/vigint_cleanup.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "cleanup_old_incidents.py"; then
    echo "✓ Cron job already exists"
    echo ""
    echo "Current crontab entries for cleanup:"
    crontab -l | grep "cleanup_old_incidents.py"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✓ Cron job added successfully"
fi

echo ""
echo "Cleanup schedule: Daily at 3:00 AM"
echo "Retention period: 30 days (configurable with INCIDENT_RETENTION_DAYS)"
echo "Log file: /tmp/vigint_cleanup.log"
echo ""
echo "To view current crontab: crontab -l"
echo "To remove cron job: crontab -e (then delete the cleanup line)"
echo "To test manually: python3 cleanup_old_incidents.py --dry-run"
echo ""
echo "Note: Cleanup also runs automatically once per day when the system is running"
