#!/usr/bin/env python3
"""
Campaign Manager — Multi-slot campaign system for Hermes Dungeon Server.

Like a video game: save multiple campaigns, load any one, switch between them.
Each campaign is isolated. The DM must never mix lore/NPCs/items between them.

Features:
  • Atomic writes (no corrupt half-written files)
  • Automatic backup on every save and switch
  • Recovery from backup if file is corrupt
  • Rollback on failed switch
  • Per-campaign backup pruning

Usage inside container:
    python3 /opt/data/scripts/campaign_manager.py list
    python3 /opt/data/scripts/campaign_manager.py status
    python3 /opt/data/scripts/campaign_manager.py save after_session_5
    python3 /opt/data/scripts/campaign_manager.py switch la_mina_perdida
    python3 /opt/data/scripts/campaign_manager.py new my_campaign "My Title" "Forgotten Realms"
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import traceback
from datetime import datetime
from pathlib import Path

DEFAULT_DATA_DIR = Path("/opt/data")
MAX_GLOBAL_BACKUPS = 20


def get_paths(data_dir: Path | None = None):
    d = data_dir or DEFAULT_DATA_DIR
    return {
        "data_dir": d,
        "campaign_file": d / "campaign_state.json",
        "active_id_file": d / "active_campaign",
        "campaigns_dir": d / "campaigns_data",
        "backup_dir": d / "campaign_backups",
    }


def _atomic_write(path: Path, data: dict):
    """Atomic JSON write: .tmp then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.rename(path)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to write {path}: {e}") from e


def _read_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _validate(data) -> bool:
    return isinstance(data, dict) and "campaign" in data


def _slugify(text: str) -> str:
    text = text.lower().strip()
    for src, dst in [
        ("á", "a"), ("à", "a"), ("ä", "a"),
        ("é", "e"), ("è", "e"), ("ë", "e"),
        ("í", "i"), ("ì", "i"), ("ï", "i"),
        ("ó", "o"), ("ò", "o"), ("ö", "o"),
        ("ú", "u"), ("ù", "u"), ("ü", "u"),
        ("ñ", "n"),
    ]:
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:60]


def _prune(directory: Path, keep: int):
    if not directory.exists():
        return
    files = sorted(
        [f for f in directory.iterdir() if f.is_file() and f.suffix == ".json"],
        reverse=True,
    )
    for old in files[keep:]:
        old.unlink(missing_ok=True)


def _extract_chat_history(data_dir: Path) -> list:
    """Extract recent Telegram messages from state.db for this session."""
    db_path = data_dir / "state.db"
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        # Get the most recent telegram session
        cursor.execute(
            """SELECT id FROM sessions
               WHERE source = 'telegram'
               ORDER BY started_at DESC LIMIT 1"""
        )
        row = cursor.fetchone()
        if not row:
            return []
        session_id = row[0]
        cursor.execute(
            """SELECT role, content, timestamp
               FROM messages
               WHERE session_id = ?
               ORDER BY timestamp""",
            (session_id,),
        )
        messages = []
        for role, content, ts in cursor.fetchall():
            if not content:
                continue
            # Skip tool/system noise
            if role in ("user", "assistant"):
                messages.append({
                    "role": role,
                    "content": content[:500],  # Truncate very long messages
                    "timestamp": ts,
                })
        conn.close()
        return messages
    except Exception:
        return []


def _backup(data: dict, label: str, campaign_id: str | None, paths: dict) -> Path:
    backup_dir = paths["backup_dir"]
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{campaign_id}_" if campaign_id else "campaign_"

    global_path = backup_dir / f"{prefix}{ts}_{label}.json"
    _atomic_write(global_path, data)
    _prune(backup_dir, MAX_GLOBAL_BACKUPS)

    if campaign_id:
        flat_path = backup_dir / f"campaign__{campaign_id}__{ts}_{label}.json"
        _atomic_write(flat_path, data)

    return global_path


def _get_active_id(paths: dict) -> str | None:
    active_file = paths["active_id_file"]
    if active_file.exists():
        val = active_file.read_text(encoding="utf-8").strip()
        if val:
            return val
    # Fallback: infer from campaign_state.json
    data = _read_json(paths["campaign_file"])
    if data:
        title = data.get("campaign", {}).get("title", "")
        if title:
            recovered = _slugify(title)
            print(f"⚠️  active_campaign file missing — inferred as: '{recovered}'")
            active_file.write_text(recovered, encoding="utf-8")
            return recovered
    return None


def _set_active_id(campaign_id: str, paths: dict):
    paths["active_id_file"].write_text(campaign_id, encoding="utf-8")


def _recover_from_backup(campaign_id: str | None, paths: dict) -> dict | None:
    backup_dir = paths["backup_dir"]

    # 1. Backups with campaign prefix
    if backup_dir.exists() and campaign_id:
        for b in sorted(backup_dir.glob(f"campaign__{campaign_id}__*.json"), reverse=True):
            data = _read_json(b)
            if data and _validate(data):
                print(f"🔄 Recovered from campaign backup: {b.name}")
                return data

    # 2. Global backups filtered by prefix
    if backup_dir.exists() and campaign_id:
        for b in sorted(backup_dir.glob(f"{campaign_id}_*.json"), reverse=True):
            if not b.is_file():
                continue
            data = _read_json(b)
            if data and _validate(data):
                print(f"🔄 Recovered from global backup: {b.name}")
                return data

    # 3. Last resort: any valid backup
    if backup_dir.exists():
        for b in sorted([f for f in backup_dir.glob("*.json") if f.is_file()], reverse=True):
            data = _read_json(b)
            if data and _validate(data):
                print(f"⚠️  Recovered from generic backup: {b.name}")
                return data

    return None


def _load_active(paths: dict, fallback=True) -> dict | None:
    data = _read_json(paths["campaign_file"])
    if data and _validate(data):
        return data
    if not fallback:
        return None
    print("⚠️  campaign_state.json invalid or missing — attempting recovery...")
    active_id = _get_active_id(paths)
    recovered = _recover_from_backup(active_id, paths)
    if recovered:
        _atomic_write(paths["campaign_file"], recovered)
    return recovered


# ── Public commands ───────────────────────────────────────────────────────────

def cmd_list(paths: dict):
    campaigns_dir = paths["campaigns_dir"]
    campaigns_dir.mkdir(parents=True, exist_ok=True)
    active_id = _get_active_id(paths)
    campaigns = sorted(campaigns_dir.glob("*.json"))

    if not campaigns:
        print("📭 No saved campaigns.")
        print("   Use: campaign_manager.py new <id> '<title>' ['<setting>']")
        return

    print(f"📚 Saved campaigns ({len(campaigns)}):\n")
    for path in campaigns:
        cid = path.stem
        marker = "  ← ACTIVE" if cid == active_id else ""
        data = _read_json(path)
        if data and _validate(data):
            c = data.get("campaign", {})
            cs = data.get("current_status", data.get("world_state", {}))
            print(f"  [{cid}]{marker}")
            print(f"    📜 {c.get('title', cid)}")
            print(f"    🌍 {c.get('setting', '—')}")
            print(f"    🎲 Session {c.get('session_number', '?')} | "
                  f"📍 {cs.get('location', cs.get('current_location', '?'))} | "
                  f"💾 {c.get('date_saved', '?')}")
        else:
            print(f"  [{cid}]{marker}  ⚠️  Corrupt file (backups available)")
        print()


def cmd_status(paths: dict):
    data = _load_active(paths)
    if not data:
        print("❌ No active campaign and could not recover from backups.")
        return

    active_id = _get_active_id(paths) or "unknown"
    c = data.get("campaign", {})
    cs = data.get("current_status", data.get("world_state", {}))
    chars = data.get("characters", [])
    log = data.get("session_log", data.get("session_history", []))

    print(f"🎮 Active campaign: [{active_id}]")
    print(f"   📜 {c.get('title', '?')} — {c.get('tagline', '')}")
    print(f"   🌍 {c.get('setting', '?')}")
    print(f"   🎲 Session {c.get('session_number', '?')} | {len(log)} scenes recorded")
    print(f"   📍 {cs.get('location', cs.get('current_location', '?'))}")

    pcs = [ch for ch in chars if ch.get("player") and "PNJ" not in str(ch.get("player", ""))]
    for ch in pcs[:3]:
        hp = ch.get("hp", {})
        print(f"   ❤️  {ch['name']} — HP {hp.get('current', '?')}/{hp.get('max', '?')}")

    quests = cs.get("active_quests", [])
    if quests:
        print(f"   🗺️  Active quests ({len(quests)}):")
        for q in quests[:3]:
            if isinstance(q, dict):
                print(f"      • {q.get('name', q)}")
            else:
                print(f"      • {q}")
        if len(quests) > 3:
            print(f"      … and {len(quests) - 3} more")

    backup_dir = paths["backup_dir"]
    if backup_dir.exists():
        n = len(list(backup_dir.glob("*.json")))
        print(f"   💾 Global backups: {n}")


def cmd_save(paths: dict, label: str = "manual"):
    data = _load_active(paths, fallback=False)
    if not data:
        print("❌ No active campaign to save.")
        print("   Create one first: campaign_manager.py new <id> '<title>' ['<setting>']")
        print("   Or load an existing one: campaign_manager.py switch <id>")
        return False

    campaigns_dir = paths["campaigns_dir"]
    campaigns_dir.mkdir(parents=True, exist_ok=True)
    active_id = _get_active_id(paths)
    if not active_id:
        title = data.get("campaign", {}).get("title", "campaign")
        active_id = _slugify(title)
        _set_active_id(active_id, paths)
        print(f"ℹ️  ID auto-inferred: {active_id}")

    data.setdefault("campaign", {})["date_saved"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Save chat history from state.db
    chat_history = _extract_chat_history(paths["data_dir"])
    if chat_history:
        data["chat_history"] = chat_history[-50:]  # Keep last 50 messages
        print(f"   💬 Captured {len(chat_history)} chat messages (keeping last 50)")

    bp = _backup(data, label, active_id, paths)
    _atomic_write(campaigns_dir / f"{active_id}.json", data)
    _atomic_write(paths["campaign_file"], data)

    print(f"✅ Saved: campaigns_data/{active_id}.json")
    print(f"   Backup: {bp.name}")
    return True


def cmd_switch(paths: dict, campaign_id: str):
    campaigns_dir = paths["campaigns_dir"]
    campaigns_dir.mkdir(parents=True, exist_ok=True)
    target_path = campaigns_dir / f"{campaign_id}.json"

    if not target_path.exists():
        print(f"❌ Campaign '{campaign_id}' not found.")
        camps = [p.stem for p in sorted(campaigns_dir.glob("*.json"))]
        if camps:
            print("   Available: " + ", ".join(camps))
        return False

    # 1. Save current campaign before switching
    current_id = _get_active_id(paths)
    current_data = _load_active(paths, fallback=True)
    pre_switch_backup = None

    if current_data and _validate(current_data):
        print(f"💾 Saving current campaign ({current_id or '?'})...")
        pre_switch_backup = _backup(current_data, "pre_switch", current_id, paths)
        if current_id:
            _atomic_write(campaigns_dir / f"{current_id}.json", current_data)
        print("   ✅ Saved.")

    # 2. Load new campaign (with fallback)
    new_data = _read_json(target_path)
    if not new_data or not _validate(new_data):
        print(f"⚠️  campaigns_data/{campaign_id}.json corrupt — recovering from backup...")
        new_data = _recover_from_backup(campaign_id, paths)
        if not new_data:
            print(f"❌ Could not recover '{campaign_id}' from any backup.")
            return False
        print("   ✅ Recovered from backup.")

    # 3. Activate (with rollback on failure)
    try:
        _atomic_write(paths["campaign_file"], new_data)
        _set_active_id(campaign_id, paths)
    except Exception as e:
        print(f"❌ Error activating campaign: {e}")
        if current_data:
            print(f"🔄 Rollback: restoring '{current_id}'...")
            try:
                _atomic_write(paths["campaign_file"], current_data)
                if current_id:
                    _set_active_id(current_id, paths)
                print("   ✅ Rollback complete.")
            except Exception as re2:
                print(f"   ⚠️  Rollback also failed: {re2}")
                print(f"   Backup available at: {pre_switch_backup}")
        return False

    c = new_data.get("campaign", {})
    cs = new_data.get("current_status", new_data.get("world_state", {}))
    print(f"✅ Active campaign: [{campaign_id}]")
    print(f"   📜 {c.get('title', '?')} — {c.get('tagline', '')}")
    print(f"   📍 {cs.get('location', cs.get('current_location', '?'))}")
    print(f"   🎲 Session {c.get('session_number', '?')}")
    print()
    print("⚠️  ISOLATION: This campaign is its own world.")
    print("   Do NOT use lore, NPCs, items, or clues from other campaigns.")
    return True


def cmd_new(paths: dict, campaign_id: str, title: str, setting: str = ""):
    campaigns_dir = paths["campaigns_dir"]
    campaigns_dir.mkdir(parents=True, exist_ok=True)
    campaign_id = _slugify(campaign_id)
    target_path = campaigns_dir / f"{campaign_id}.json"

    if target_path.exists():
        print(f"⚠️  Campaign with ID '{campaign_id}' already exists.")
        print(f"   Use 'switch {campaign_id}' to activate it.")
        return False

    data = {
        "campaign": {
            "title": title,
            "tagline": "",
            "setting": setting,
            "game_master": "Dungeon Master",
            "player": "",
            "date_saved": datetime.now().strftime("%Y-%m-%d"),
            "session_number": 0,
            "total_sessions": 0,
        },
        "characters": [],
        "session_log": [],
        "chat_history": [],
        "current_status": {
            "location": "To be determined",
            "party_status": "New campaign — awaiting start.",
            "active_quests": [],
            "pending_decisions": [],
            "important_npcs": [],
            "notes": "",
        },
    }

    _atomic_write(target_path, data)
    print(f"✅ New campaign created: [{campaign_id}]")
    print(f"   📜 {title}")
    if setting:
        print(f"   🌍 {setting}")
    print(f"   Use 'switch {campaign_id}' to activate it.")
    return True


def cmd_recover(paths: dict):
    data = _read_json(paths["campaign_file"])
    if data and _validate(data):
        print("✅ campaign_state.json is OK — no recovery needed.")
        return True

    print("⚠️  campaign_state.json corrupt or missing. Searching backup...")
    active_id = _get_active_id(paths)
    recovered = _recover_from_backup(active_id, paths)

    if not recovered:
        print("❌ No valid backup found.")
        return False

    _atomic_write(paths["campaign_file"], recovered)
    c = recovered.get("campaign", {})
    print(f"✅ Recovered: {c.get('title', '?')} — Session {c.get('session_number', '?')}")
    return True


USAGE = """📖 Campaign Manager — Usage:
   list                               → list available campaigns
   status                             → status of active campaign
   save [label]                       → save active campaign
   switch <id>                        → switch campaign (saves current)
   new <id> '<title>' ['<setting>']   → create blank campaign
   recover                            → recover from corruption
"""


def cmd_chat_history(paths: dict, campaign_id: str | None = None):
    """Show saved chat history for a campaign."""
    target_id = campaign_id or _get_active_id(paths)
    if not target_id:
        print("❌ No active campaign.")
        return False

    campaigns_dir = paths["campaigns_dir"]
    target_path = campaigns_dir / f"{target_id}.json"
    data = _read_json(target_path)
    if not data:
        print(f"❌ Campaign '{target_id}' not found.")
        return False

    history = data.get("chat_history", [])
    if not history:
        print(f"📭 No chat history saved for '{target_id}'.")
        return True

    print(f"💬 Chat history for [{target_id}] ({len(history)} messages):\n")
    for msg in history[-20:]:  # Show last 20
        role = "🧑" if msg["role"] == "user" else "🤖"
        content = msg["content"][:120].replace("\n", " ")
        print(f"{role} {content}...")
    return True


def main():
    parser = argparse.ArgumentParser(description="Campaign manager")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Data directory (default: {DEFAULT_DATA_DIR})",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("list", help="List available campaigns")
    sub.add_parser("status", help="Status of active campaign")
    save_p = sub.add_parser("save", help="Save active campaign")
    save_p.add_argument("label", nargs="?", default="manual", help="Backup label")
    switch_p = sub.add_parser("switch", help="Switch campaign")
    switch_p.add_argument("campaign_id", help="Campaign ID to activate")
    new_p = sub.add_parser("new", help="Create blank campaign")
    new_p.add_argument("campaign_id", help="Campaign ID")
    new_p.add_argument("title", help="Campaign title")
    new_p.add_argument("setting", nargs="?", default="", help="Campaign setting")
    sub.add_parser("recover", help="Recover from corruption")
    chat_p = sub.add_parser("chat-history", help="Show saved chat history")
    chat_p.add_argument("campaign_id", nargs="?", default=None, help="Campaign ID (default: active)")

    args = parser.parse_args()
    paths = get_paths(args.data_dir)

    try:
        if args.action == "list":
            cmd_list(paths)
        elif args.action == "status":
            cmd_status(paths)
        elif args.action == "save":
            ok = cmd_save(paths, args.label)
            sys.exit(0 if ok else 1)
        elif args.action == "switch":
            ok = cmd_switch(paths, args.campaign_id)
            sys.exit(0 if ok else 1)
        elif args.action == "new":
            ok = cmd_new(paths, args.campaign_id, args.title, args.setting)
            sys.exit(0 if ok else 1)
        elif args.action == "recover":
            ok = cmd_recover(paths)
            sys.exit(0 if ok else 1)
        elif args.action == "chat-history":
            ok = cmd_chat_history(paths, args.campaign_id)
            sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
