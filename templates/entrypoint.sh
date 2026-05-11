#!/bin/bash
# DUNGEON2 - ENTRYPOINT DE PERSISTENCIA ABSOLUTA
# NO set -e para evitar salidas silenciosas

DATA_DIR="/opt/data"
BACKUP_DIR="$DATA_DIR/session_backups"
REDUNDANT_DIR="/opt/data/.persistence_recovery"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  🔧 DUNGEON2 - SISTEMA DE PERSISTENCIA ABSOLUTA    ║"
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
        [ -n "$LATEST" ] && cp "$LATEST" "$DATA_DIR/$FILE" && echo "🔄 $FILE restaurado"
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

# ── Background Auto-Save ────────────────────────────────────────────
# Independent of gateway. Saves campaign every 30 minutes even if
# Hermes is down or crashed.
(
  echo "[$(date)] 💾 Background auto-save started (every 30 min)"
  while true; do
    sleep 1800
    python3 /opt/data/scripts/campaign_manager.py save auto 2>/dev/null && \
      echo "[$(date)] 💾 Auto-save OK" || \
      echo "[$(date)] ⚠️ Auto-save failed"
  done
) &

# ── Background Resumen Generator ────────────────────────────────────
# Keeps resumen-rapido.md fresh automatically. Runs every 60 seconds.
# The DM's single source of truth stays current without manual action.
(
  echo "[$(date)] 📝 Background resumen generator started (every 60s)"
  while true; do
    sleep 60
    python3 /opt/data/scripts/generate_resumen.py >/dev/null 2>&1 && \
      echo "[$(date)] 📝 Resumen updated" || \
      true
  done
) &
while true; do
    echo "🚀 Arrancando gateway..."
    /opt/hermes/.venv/bin/hermes gateway run --replace --accept-hooks -v 2>&1
    EXIT_CODE=$?
    CRASH_TS=$(date +%s)
    echo "[$(date)] ⚠️ Gateway CRASH (codigo $EXIT_CODE) - reiniciando en 5s..."
    # Save campaign state before restart (narrative memory)
    python3 /opt/data/scripts/campaign_manager.py save crash_backup 2>/dev/null || true
    for f in state.db state.db-wal state.db-shm; do
        [ -f "$DATA_DIR/$f" ] && [ -s "$DATA_DIR/$f" ] && \
            cp "$DATA_DIR/$f" "$BACKUP_DIR/${f}.post_${CRASH_TS}" 2>/dev/null
    done
    [ -f "$DATA_DIR/sessions/sessions.json" ] && \
        cp "$DATA_DIR/sessions/sessions.json" "$BACKUP_DIR/sessions.post_${CRASH_TS}.json" 2>/dev/null
    sleep 5
done