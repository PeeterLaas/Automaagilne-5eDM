#!/usr/bin/env python3
"""
session_resume.py — Memory bridge across Hermes session resets.

Hermes resets sessions daily (or on crash/timeout). When that happens,
the DM forgets everything: who the player is, where they were, what
quests are active. This script fixes that by:

1. Reading campaign_state.json
2. Generating .session_resume_context.md — a compact "memory prompt"
3. Updating .campaign_loaded_today — a timestamp flag

The DM's SOUL.md instructs it to read .session_resume_context.md
before every response if the session is fresh.

Usage inside container:
    python3 /opt/data/scripts/session_resume.py

Usage outside container (testing):
    python3 scripts/session_resume.py --data-dir ./test-data
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DATA_DIR = Path("/opt/data")


def get_paths(data_dir: Path | None = None):
    d = data_dir or DEFAULT_DATA_DIR
    return {
        "data_dir": d,
        "campaign_file": d / "campaign_state.json",
        "resume_file": d / ".session_resume_context.md",
        "loaded_flag": d / ".campaign_loaded_today",
    }


def _read_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def generate_resume(data: dict) -> str:
    """Generate the memory bridge markdown from campaign state."""
    campaign = data.get("campaign", {})
    characters = data.get("characters", [])
    world = data.get("world_state", {})
    log = data.get("session_log", [])
    quests = data.get("active_quests", data.get("quests", []))

    lines = [
        "# CAMPAIGN MEMORY BRIDGE — Auto-generated",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "> ⚠️ CRITICAL: This file is your memory. Read it before responding.",
        "> If .campaign_loaded_today is missing or outdated, you MUST load campaign_state.json immediately.",
        "",
        "## Campaign",
        f"- **Title:** {campaign.get('title', 'Untitled')}",
        f"- **Tagline:** {campaign.get('tagline', '')}",
        f"- **Setting:** {campaign.get('setting', '')}",
        "",
        "## Characters",
    ]

    for char in characters:
        name = char.get("name", "Unknown")
        pc_info = f" (PC: {char.get('player', 'Unknown')})" if char.get('player') else ""
        hp = char.get("hp", {})
        hp_str = f"{hp.get('current', '?')}/{hp.get('max', '?')} HP" if hp else ""
        lines.append(f"- **{name}**{pc_info} — {char.get('race', '')} {char.get('class_level', '')} — {hp_str}")
        if char.get("personality"):
            lines.append(f"  - Personality: {char['personality']}")
        if char.get("bonds"):
            lines.append(f"  - Bonds: {char['bonds']}")

    lines.extend(["", "## Current Situation"])
    location = world.get("current_location", world.get("location", "Unknown"))
    lines.append(f"- **Location:** {location}")

    if quests:
        lines.extend(["", "## Active Quests"])
        for q in quests:
            if isinstance(q, dict):
                lines.append(f"- {q.get('name', 'Unnamed')}: {q.get('description', '')}")
            else:
                lines.append(f"- {q}")

    if log:
        lines.extend(["", "## Session History (last 5 scenes)"])
        for entry in log[-5:]:
            if isinstance(entry, dict):
                t = entry.get("type", "scene").upper()
                title = entry.get("title", "Untitled")
                content = entry.get("content", "")[:200]
                lines.append(f"- [{t}] **{title}**: {content}")

    lines.extend([
        "",
        "## DM Instructions",
        "1. Load /opt/data/campaign_state.json for complete data.",
        "2. Narrate based on the 'Current Situation' and 'Last Scene'.",
        "3. After any significant event, update campaign_state.json.",
        "4. If in combat, check /opt/data/combat_state.json.",
    ])

    return "\n".join(lines)


def generate_compact_prompt(data: dict) -> str:
    """Generate a one-line memory prompt for injection into DM context."""
    campaign = data.get("campaign", {})
    chars = data.get("characters", [])
    log = data.get("session_log", [])

    char_names = ", ".join([c.get("name", "?") for c in chars[:3]])
    last_scene = ""
    if log and isinstance(log[-1], dict):
        last_scene = log[-1].get("title", "")

    return (
        f"[MEMORY] Campaign: {campaign.get('title', '?')}. "
        f"Characters: {char_names}. "
        f"Last scene: {last_scene}. "
        f"Load full state from /opt/data/campaign_state.json before responding."
    )


def main():
    parser = argparse.ArgumentParser(description="Session resume memory bridge")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Data directory (default: {DEFAULT_DATA_DIR})",
    )
    args = parser.parse_args()

    paths = get_paths(args.data_dir)
    data_dir = paths["data_dir"]
    campaign_file = paths["campaign_file"]
    resume_file = paths["resume_file"]
    loaded_flag = paths["loaded_flag"]

    # Ensure data dir exists
    data_dir.mkdir(parents=True, exist_ok=True)

    data = _read_json(campaign_file)

    if not data:
        print("⚠️  No campaign_state.json found. Cannot generate resume context.")
        print("   Expected at:", campaign_file)
        # Write a minimal "no campaign" flag
        loaded_flag.write_text("NO_CAMPAIGN_FOUND\n", encoding="utf-8")
        resume_file.write_text(
            "# NO CAMPAIGN FOUND\n\n"
            "campaign_state.json is missing. The DM has no memory to load.\n"
            "Ask the player if they want to start a new campaign or restore from backup.\n",
            encoding="utf-8",
        )
        sys.exit(1)

    # Generate and write resume context
    resume_md = generate_resume(data)
    resume_file.write_text(resume_md, encoding="utf-8")

    # Update loaded flag
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    loaded_flag.write_text(f"{now}\n", encoding="utf-8")

    # Print compact prompt to stdout (useful for cron logging or DM injection)
    compact = generate_compact_prompt(data)
    print(compact)
    print(f"✅ Resume context written to: {resume_file}")
    print(f"✅ Loaded flag written to: {loaded_flag}")


if __name__ == "__main__":
    main()
