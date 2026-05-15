#!/usr/bin/env python3
"""
Campaign Manager — Markdown-based campaign system for Dungeon 2.

Inspired by claude-dungeon-master. Each campaign is a folder:
  campaigns/<id>/
    state.md          — Current game state
    characters/       — Individual character sheets

Usage:
    python3 /opt/data/scripts/campaign_manager.py list
    python3 /opt/data/scripts/campaign_manager.py status
    python3 /opt/data/scripts/campaign_manager.py save [label]
    python3 /opt/data/scripts/campaign_manager.py switch <id>
    python3 /opt/data/scripts/campaign_manager.py new <id> '<title>'
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DATA_DIR = Path("/opt/data")
CAMPAIGNS_DIR = DEFAULT_DATA_DIR / "campaigns"
BACKUP_DIR = DEFAULT_DATA_DIR / "campaign_backups"
ACTIVE_FILE = DEFAULT_DATA_DIR / "active_campaign"


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


def _get_active_id() -> str | None:
    if ACTIVE_FILE.exists():
        val = ACTIVE_FILE.read_text(encoding="utf-8").strip()
        if val:
            return val
    return None


def _set_active_id(campaign_id: str):
    ACTIVE_FILE.write_text(campaign_id, encoding="utf-8")


def _campaign_dir(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / _slugify(campaign_id)


def cmd_list():
    CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
    active_id = _get_active_id()
    campaigns = sorted(d for d in CAMPAIGNS_DIR.iterdir() if d.is_dir())

    if not campaigns:
        print("📭 No saved campaigns.")
        print("   Create one: campaign_manager.py new <id> '<title>'")
        return

    print(f"📚 Saved campaigns ({len(campaigns)}):\n")
    for path in campaigns:
        cid = path.name
        marker = "  ← ACTIVE" if cid == active_id else ""
        state_file = path / "state.md"
        title = cid
        if state_file.exists():
            for line in state_file.read_text(encoding="utf-8").splitlines()[:5]:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        print(f"  [{cid}]{marker}")
        print(f"    📜 {title}")
        chars = list((path / "characters").glob("*.md")) if (path / "characters").exists() else []
        print(f"    👥 Characters: {len(chars)}")
        print()


def cmd_status():
    active_id = _get_active_id()
    if not active_id:
        print("❌ No active campaign. Use 'switch <id>' or 'new <id> <title>'.")
        return False

    state_file = _campaign_dir(active_id) / "state.md"
    if not state_file.exists():
        print(f"❌ Campaign '{active_id}' has no state.md.")
        return False

    print(f"🎮 Active campaign: [{active_id}]\n")
    print(state_file.read_text(encoding="utf-8"))
    return True


def cmd_save(label: str = "manual"):
    active_id = _get_active_id()
    if not active_id:
        print("❌ No active campaign to save.")
        print("   Create one: campaign_manager.py new <id> '<title>'")
        return False

    src = _campaign_dir(active_id)
    if not src.exists():
        print(f"❌ Campaign directory '{src}' not found.")
        return False

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"{active_id}__{ts}__{label}"
    shutil.copytree(src, dst)

    print(f"✅ Saved: campaigns/{active_id}/")
    print(f"   Backup: campaign_backups/{dst.name}/")
    return True


def cmd_switch(campaign_id: str):
    campaign_id = _slugify(campaign_id)
    target = _campaign_dir(campaign_id)

    if not target.exists():
        print(f"❌ Campaign '{campaign_id}' not found.")
        camps = [d.name for d in CAMPAIGNS_DIR.iterdir() if d.is_dir()]
        if camps:
            print("   Available: " + ", ".join(camps))
        return False

    # Save current before switching
    current_id = _get_active_id()
    if current_id and _campaign_dir(current_id).exists():
        print(f"💾 Saving current campaign ({current_id})...")
        cmd_save("pre_switch")

    _set_active_id(campaign_id)
    state_file = target / "state.md"
    title = campaign_id
    if state_file.exists():
        for line in state_file.read_text(encoding="utf-8").splitlines()[:5]:
            if line.startswith("# "):
                title = line[2:].strip()
                break

    print(f"✅ Active campaign: [{campaign_id}]")
    print(f"   📜 {title}")
    print()
    print("⚠️  ISOLATION: This campaign is its own world.")
    print("   Do NOT use lore, NPCs, items, or clues from other campaigns.")
    return True


def cmd_new(campaign_id: str, title: str):
    campaign_id = _slugify(campaign_id)
    target = _campaign_dir(campaign_id)

    if target.exists():
        print(f"⚠️  Campaign '{campaign_id}' already exists.")
        print(f"   Use 'switch {campaign_id}' to activate it.")
        return False

    target.mkdir(parents=True)
    (target / "characters").mkdir(parents=True, exist_ok=True)

    # Create state.md from template
    template = Path(__file__).parent.parent / "templates" / "campaign_state.md"
    if template.exists():
        content = template.read_text(encoding="utf-8")
    else:
        content = "# {{title}}\n\n## Current State\n- **Session**: 0\n- **In-Game Date**: —\n- **Location**: —\n"

    content = content.replace("{{title}}", title)
    content = content.replace("{{session_number}}", "0")
    content = content.replace("{{date}}", "—")
    content = content.replace("{{location}}", "To be determined")
    content = content.replace("{{party_rows}}", "| | | | |")
    content = content.replace("{{quests}}", "- [ ] Define first quest")
    content = content.replace("{{events}}", "- Session 0: Campaign created")
    content = content.replace("{{npcs}}", "- **TBD**: Introduce first NPC")
    content = content.replace("{{gold}}", "0")
    content = content.replace("{{items}}", "None")
    content = content.replace("{{hooks}}", "—")
    content = content.replace("{{threads}}", "—")
    content = content.replace("{{secrets}}", "—")

    (target / "state.md").write_text(content, encoding="utf-8")

    print(f"✅ New campaign created: [{campaign_id}]")
    print(f"   📜 {title}")
    print(f"   📂 campaigns/{campaign_id}/state.md")
    print(f"   Use 'switch {campaign_id}' to activate it.")
    return True


def cmd_recover():
    active_id = _get_active_id()
    if not active_id:
        print("❌ No active campaign to recover.")
        return False

    # Find most recent backup
    backups = sorted(
        [b for b in BACKUP_DIR.iterdir() if b.is_dir() and b.name.startswith(active_id)],
        reverse=True,
    )
    if not backups:
        print(f"❌ No backups found for '{active_id}'.")
        return False

    latest = backups[0]
    src = _campaign_dir(active_id)
    if src.exists():
        shutil.rmtree(src)
    shutil.copytree(latest, src)

    print(f"✅ Recovered: {active_id} from {latest.name}")
    return True


USAGE = """📖 Campaign Manager — Usage:
   list                   → list available campaigns
   status                 → show active campaign state.md
   save [label]           → backup active campaign
   switch <id>            → switch to another campaign
   new <id> '<title>'     → create blank campaign
   recover                → restore from latest backup
"""


def main():
    parser = argparse.ArgumentParser(description="Campaign manager (markdown)")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("list", help="List available campaigns")
    sub.add_parser("status", help="Show active campaign state")
    save_p = sub.add_parser("save", help="Save active campaign")
    save_p.add_argument("label", nargs="?", default="manual", help="Backup label")
    switch_p = sub.add_parser("switch", help="Switch campaign")
    switch_p.add_argument("campaign_id", help="Campaign ID to activate")
    new_p = sub.add_parser("new", help="Create blank campaign")
    new_p.add_argument("campaign_id", help="Campaign ID")
    new_p.add_argument("title", nargs="+", help="Campaign title")
    sub.add_parser("recover", help="Recover from backup")

    args = parser.parse_args()

    try:
        if args.action == "list":
            cmd_list()
        elif args.action == "status":
            ok = cmd_status()
            sys.exit(0 if ok else 1)
        elif args.action == "save":
            ok = cmd_save(args.label)
            sys.exit(0 if ok else 1)
        elif args.action == "switch":
            ok = cmd_switch(args.campaign_id)
            sys.exit(0 if ok else 1)
        elif args.action == "new":
            title = " ".join(args.title) if isinstance(args.title, list) else args.title
            ok = cmd_new(args.campaign_id, title)
            sys.exit(0 if ok else 1)
        elif args.action == "recover":
            ok = cmd_recover()
            sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
