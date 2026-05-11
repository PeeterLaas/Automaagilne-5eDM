#!/bin/bash
# Auto-save cron job for Hermes Dungeon Server.
# Run every 30 minutes to backup campaign_state.json.
# Install with: crontab -e
#   */30 * * * * /opt/data/scripts/cron-auto-save.sh >> /opt/data/logs/auto-save.log 2>&1

LOG_FILE="/opt/data/logs/auto-save.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Auto-save starting..." >> "$LOG_FILE"

if [ -f "/opt/data/campaign_state.json" ]; then
    python3 /opt/data/scripts/campaign_state.py save cron_auto >> "$LOG_FILE" 2>&1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Auto-save complete." >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] No campaign_state.json found. Skipping." >> "$LOG_FILE"
fi
