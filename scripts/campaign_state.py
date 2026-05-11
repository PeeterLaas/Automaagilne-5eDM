#!/usr/bin/env python3
"""
campaign_state.py — Campaign state manager with atomic writes and backup recovery.

Solves the problem of Hermes losing track of campaign progress.
The DM uses this to explicitly save, load, check status, and restore.

Usage inside container:
    python3 /opt/data/scripts/campaign_state.py save
    python3 /opt/data/scripts/campaign_state.py status
    python3 /opt/data/scripts/campaign_state.py restore backup_file.json

Usage outside container (testing):
    python3 scripts/campaign_state.py --data-dir ./test-data status
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DATA_DIR = Path("/opt/data")
MAX_BACKUPS = 20


def get_paths(data_dir: Path | None = None):
    d = data_dir or DEFAULT_DATA_DIR
    return {
        "data_dir": d,
        "campaign_file": d / "campaign_state.json",
        "backup_dir": d / "campaign_backups",
    }


def _atomic_write(path: Path, data: dict):
    """Write JSON atomically: write to .tmp then rename."""
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


def _prune_backups(backup_dir: Path):
    """Keep only the latest MAX_BACKUPS."""
    if not backup_dir.exists():
        return
    files = sorted(
        [f for f in backup_dir.iterdir() if f.is_file() and f.suffix == ".json"],
        reverse=True,
    )
    for old in files[MAX_BACKUPS:]:
        old.unlink(missing_ok=True)


def save(paths: dict, label: str = "auto"):
    """Save campaign state to disk with timestamped backup."""
    campaign_file = paths["campaign_file"]
    backup_dir = paths["backup_dir"]

    data = _read_json(campaign_file)

    if not data:
        print("❌ No campaign_state.json to save.")
        sys.exit(1)

    if not _validate(data):
        print("❌ campaign_state.json is invalid (missing 'campaign' key).")
        sys.exit(1)

    # Write main file (already exists, but ensure it's valid)
    _atomic_write(campaign_file, data)

    # Backup with timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    campaign_title = data.get("campaign", {}).get("title", "untitled").replace(" ", "_").lower()[:30]
    backup_path = backup_dir / f"{campaign_title}_{ts}_{label}.json"
    _atomic_write(backup_path, data)

    _prune_backups(backup_dir)

    print(f"✅ Campaign saved: {campaign_file}")
    print(f"   Backup: {backup_path}")


def load(paths: dict):
    """Load campaign state from disk and print it."""
    data = _read_json(paths["campaign_file"])
    if not data:
        print("❌ No campaign_state.json found.")
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2))


def status(paths: dict):
    """Show current campaign status."""
    campaign_file = paths["campaign_file"]
    backup_dir = paths["backup_dir"]

    if not campaign_file.exists():
        print("❌ No campaign saved on disk.")
        return

    size = campaign_file.stat().st_size
    mtime = datetime.fromtimestamp(campaign_file.stat().st_mtime)
    data = _read_json(campaign_file)

    if not data:
        print("❌ campaign_state.json exists but is corrupt.")
        return

    campaign = data.get("campaign", {})
    chars = data.get("characters", [])
    log = data.get("session_log", data.get("session_history", []))

    print(f"📜 File: {campaign_file}")
    print(f"   Size: {size:,} bytes")
    print(f"   Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Campaign: {campaign.get('title', 'Untitled')}")
    print(f"   Characters: {len(chars)}")
    print(f"   Scenes: {len(log)}")

    if backup_dir.exists():
        backups = sorted(backup_dir.glob("*.json"))
        print(f"   Backups: {len(backups)}")


def list_backups(paths: dict):
    """List all available backups."""
    backup_dir = paths["backup_dir"]
    if not backup_dir.exists():
        print("No backups directory found.")
        return

    backups = sorted(backup_dir.glob("*.json"), reverse=True)
    if not backups:
        print("No backups found.")
        return

    print("Available backups (newest first):")
    for i, b in enumerate(backups, 1):
        size = b.stat().st_size
        mtime = datetime.fromtimestamp(b.stat().st_mtime)
        print(f"  {i}. {b.name} ({size:,} bytes, {mtime.strftime('%Y-%m-%d %H:%M')})")


def restore(paths: dict, backup_name: str):
    """Restore campaign_state.json from a specific backup."""
    campaign_file = paths["campaign_file"]
    backup_dir = paths["backup_dir"]

    if os.path.sep in backup_name or backup_name.startswith("/"):
        backup_path = Path(backup_name)
    else:
        backup_path = backup_dir / backup_name

    if not backup_path.exists():
        print(f"❌ Backup not found: {backup_path}")
        sys.exit(1)

    data = _read_json(backup_path)
    if not data or not _validate(data):
        print(f"❌ Backup is invalid or corrupt: {backup_path}")
        sys.exit(1)

    # Save current as emergency backup before overwrite
    current = _read_json(campaign_file)
    if current:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        emergency = backup_dir / f"pre_restore_{ts}.json"
        _atomic_write(emergency, current)
        print(f"   Emergency backup of current state: {emergency}")

    _atomic_write(campaign_file, data)
    print(f"✅ Restored from: {backup_path}")
    print(f"   Campaign: {data.get('campaign', {}).get('title', 'Untitled')}")


def main():
    parser = argparse.ArgumentParser(description="Campaign state manager")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Data directory (default: {DEFAULT_DATA_DIR})",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    save_parser = sub.add_parser("save", help="Save campaign + create backup")
    save_parser.add_argument("label", nargs="?", default="auto", help="Backup label (default: auto)")
    sub.add_parser("load", help="Print campaign_state.json")
    sub.add_parser("status", help="Show campaign summary")
    sub.add_parser("list-backups", help="List available backups")
    restore_parser = sub.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_file", help="Backup filename or path")

    args = parser.parse_args()
    paths = get_paths(args.data_dir)

    if args.action == "save":
        save(paths, args.label)

    elif args.action == "load":
        load(paths)

    elif args.action == "status":
        status(paths)

    elif args.action == "list-backups":
        list_backups(paths)

    elif args.action == "restore":
        restore(paths, args.backup_file)


if __name__ == "__main__":
    main()
