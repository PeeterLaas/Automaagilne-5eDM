#!/usr/bin/env python3
"""
Session Cleaner — Removes old Telegram sessions from state.db.

Hermes stores every conversation in state.db. For the D&D group, we want
sessions to be short-term context only. Long-term memory lives in:
  - resumen-rapido.md
  - campaign_state.json
  - campaigns_data/*.json

This script runs periodically (via cron or entrypoint loop) to prune
Telegram sessions older than a few hours, keeping only the most recent
session for short-term context.

Usage:
    python3 /opt/data/scripts/session_cleaner.py
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DB = Path("/opt/data/state.db")
MAX_AGE_HOURS = 6  # Keep sessions from last 6 hours


def clean_telegram_sessions(db_path: Path = DEFAULT_DB):
    if not db_path.exists():
        print("❌ state.db not found.")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Find old telegram sessions
        cutoff = (datetime.now() - timedelta(hours=MAX_AGE_HOURS)).timestamp()
        cursor.execute(
            """SELECT id, title, message_count
               FROM sessions
               WHERE source = 'telegram'
               AND (ended_at IS NOT NULL OR started_at < ?)""",
            (cutoff,),
        )
        old_sessions = cursor.fetchall()

        if not old_sessions:
            print("📭 No old Telegram sessions to clean.")
            return True

        print(f"🧹 Cleaning {len(old_sessions)} old Telegram sessions...")
        for sid, title, count in old_sessions:
            t = title or "(no title)"
            print(f"   • {sid} | {t} | {count} msgs")

        # Delete messages first
        session_ids = tuple(s[0] for s in old_sessions)
        if len(session_ids) == 1:
            cursor.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (session_ids[0],),
            )
        else:
            cursor.execute(
                f"DELETE FROM messages WHERE session_id IN ({','.join('?' * len(session_ids))})",
                session_ids,
            )
        msg_deleted = cursor.rowcount

        # Delete sessions
        if len(session_ids) == 1:
            cursor.execute(
                "DELETE FROM sessions WHERE id = ?",
                (session_ids[0],),
            )
        else:
            cursor.execute(
                f"DELETE FROM sessions WHERE id IN ({','.join('?' * len(session_ids))})",
                session_ids,
            )
        sess_deleted = cursor.rowcount

        conn.commit()
        conn.execute("VACUUM")
        conn.close()

        print(f"✅ Deleted {sess_deleted} sessions and {msg_deleted} messages.")
        return True

    except Exception as e:
        print(f"❌ Error cleaning sessions: {e}")
        return False


def main():
    ok = clean_telegram_sessions()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
