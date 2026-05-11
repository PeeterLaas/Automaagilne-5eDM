#!/bin/bash
# Daily campaign loader for Hermes Dungeon Server.
# Run once per day (e.g., at 8:00 AM) to regenerate the memory bridge.
# Install with: crontab -e
#   0 8 * * * /opt/data/scripts/cron-daily-loader.sh >> /opt/data/logs/daily-loader.log 2>&1

LOG_FILE="/opt/data/logs/daily-loader.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Daily loader starting..." >> "$LOG_FILE"

if [ -f "/opt/data/campaign_state.json" ]; then
    python3 /opt/data/scripts/session_resume.py >> "$LOG_FILE" 2>&1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Daily loader complete." >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] No campaign_state.json found. Skipping." >> "$LOG_FILE"
fi
