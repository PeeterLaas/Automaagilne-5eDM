#!/usr/bin/env python3
"""
generate_resumen.py — Create resumen-rapido.md from campaign_state.json.

This is the DM's single source of truth. One file. One screen. Under 500 chars.
Run after every scene or automatically via cron/hook.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

DEFAULT_DATA_DIR = Path("/opt/data")


def get_paths(data_dir: Path | None = None):
    d = data_dir or DEFAULT_DATA_DIR
    return {
        "data_dir": d,
        "campaign_file": d / "campaign_state.json",
        "resumen_file": d / "resumen-rapido.md",
    }


def _read_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def generate_resumen(data: dict) -> str:
    campaign = data.get("campaign", {})
    cs = data.get("current_status", data.get("world_state", {}))
    chars = data.get("characters", [])
    log = data.get("session_log", data.get("session_history", []))
    quests = cs.get("active_quests", [])

    # HP line
    hp_lines = []
    for ch in chars[:3]:
        hp = ch.get("hp", {})
        if hp:
            hp_lines.append(f"{ch['name']} {hp.get('current','?')}/{hp.get('max','?')}HP")

    # Last scene
    last_scene = ""
    if log and isinstance(log[-1], dict):
        title = log[-1].get("title", "")
        content = log[-1].get("content", "")[:100]
        last_scene = f"{title}: {content}" if title else content
    elif log:
        last_scene = str(log[-1])[:120]

    # Quests (compact)
    quest_names = []
    for q in quests[:4]:
        if isinstance(q, dict):
            quest_names.append(q.get("name", "?"))
        else:
            quest_names.append(str(q))
    if len(quests) > 4:
        quest_names.append(f"+{len(quests)-4} more")

    # Build compact resumen
    lines = [
        f"# {campaign.get('title', 'Campaign')}",
        f"📅 {campaign.get('setting','')} | 📍 {cs.get('location', cs.get('current_location', '?'))}",
        f"❤️  {' | '.join(hp_lines)}" if hp_lines else "",
        f"🎯 {', '.join(quest_names)}" if quest_names else "",
        f"⬅️  {last_scene}",
        f"➡️  Próxima: (por determinar)",
        "",
        "⚠️ REGLAS: 0)NO personajes originales HP en escenas 1)Leer este archivo y state.md ANTES de responder 2)Tiradas SOLO cuando hay riesgo real 3)Párrafos largos como novela, SIN viñetas ni emojis en la narrativa",
    ]

    return "\n".join(line for line in lines if line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()

    paths = get_paths(args.data_dir)
    data = _read_json(paths["campaign_file"])

    if not data:
        print("⚠️  No campaign_state.json found.")
        # Write a minimal "no campaign" resumen
        paths["resumen_file"].write_text(
            "# NO CAMPAIGN\n\nNo campaign_state.json found.\n"
            "Ask the player if they want to start a new campaign.\n",
            encoding="utf-8",
        )
        return

    resumen = generate_resumen(data)
    paths["resumen_file"].write_text(resumen, encoding="utf-8")
    print(f"✅ resumen-rapido.md updated ({len(resumen)} chars)")
    print(resumen)


if __name__ == "__main__":
    main()
