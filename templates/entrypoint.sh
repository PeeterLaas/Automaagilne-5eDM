#!/bin/bash
# Dungeon Server — Absolute Persistence Entrypoint
# NO set -e to prevent silent exits

DATA_DIR="/opt/data"
BACKUP_DIR="$DATA_DIR/session_backups"
REDUNDANT_DIR="/opt/data/.persistence_recovery"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  🎲 DUNGEON — ABSOLUTE PERSISTENCE SYSTEM          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo "User: $(id)"
echo "Data dir: $DATA_DIR"

mkdir -p "$BACKUP_DIR" "$REDUNDANT_DIR" 2>&1
echo "Backup dirs: $?"

TIMESTAMP=$(date +%s)

for f in state.db state.db-wal state.db-shm; do
    if [ -f "$DATA_DIR/$f" ] && [ -s "$DATA_DIR/$f" ]; then
        cp "$DATA_DIR/$f" "$BACKUP_DIR/${f}.pre_${TIMESTAMP}" 2>/dev/null
        cp "$DATA_DIR/$f" "$REDUNDANT_DIR/${f}.pre_${TIMESTAMP}" 2>/dev/null
    fi
done

[ -f "$DATA_DIR/sessions/sessions.json" ] && [ -s "$DATA_DIR/sessions/sessions.json" ] && \
    cp "$DATA_DIR/sessions/sessions.json" "$BACKUP_DIR/sessions.pre_${TIMESTAMP}.json"

restore_if_needed() {
    local FILE="$1"
    if [ ! -f "$DATA_DIR/$FILE" ] || [ ! -s "$DATA_DIR/$FILE" ]; then
        LATEST=$(ls -t "$BACKUP_DIR/${FILE}.pre_"* "$BACKUP_DIR/${FILE}.post_"* "$REDUNDANT_DIR/${FILE}.pre_"* 2>/dev/null | head -1)
        [ -n "$LATEST" ] && cp "$LATEST" "$DATA_DIR/$FILE" && echo "🔄 $FILE restored"
    fi
}
restore_if_needed "state.db"
restore_if_needed "state.db-wal"
restore_if_needed "state.db-shm"

# ── Campaign Memory Bridge ───────────────────────────────────────────
# Hermes resets sessions daily. Regenerate the memory bridge on boot
# so the DM remembers the campaign immediately.
echo "🧠 Regenerating campaign memory bridge..."
python3 /opt/data/scripts/session_resume.py 2>/dev/null || echo "⚠️  session_resume.py failed (no campaign yet?)"

while true; do
    echo "🚀 Starting gateway..."
    /opt/hermes/.venv/bin/hermes gateway run --replace --accept-hooks -v 2>&1
    EXIT_CODE=$?
    CRASH_TS=$(date +%s)
    echo "[$(date)] ⚠️ Gateway CRASH (code $EXIT_CODE) — restarting in 5s..."
    for f in state.db state.db-wal state.db-shm; do
        [ -f "$DATA_DIR/$f" ] && [ -s "$DATA_DIR/$f" ] && \
            cp "$DATA_DIR/$f" "$BACKUP_DIR/${f}.post_${CRASH_TS}" 2>/dev/null
    done
    [ -f "$DATA_DIR/sessions/sessions.json" ] && \
        cp "$DATA_DIR/sessions/sessions.json" "$BACKUP_DIR/sessions.post_${CRASH_TS}.json" 2>/dev/null
    sleep 5
done
