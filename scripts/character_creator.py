#!/usr/bin/env python3
"""
Character Creator — Guided D&D 5e character creation with dice rolling.

Usage:
    python3 /opt/data/scripts/character_creator.py create --name "Rowan" --race "Human" --class "Fighter" --method roll
    python3 /opt/data/scripts/character_creator.py create --name "Maya" --race "Elf" --class "Wizard" --method standard
    python3 /opt/data/scripts/character_creator.py list --campaign <id>
    python3 /opt/data/scripts/character_creator.py show --campaign <id> --name "Rowan"

Methods:
    roll     → 4d6 drop lowest, 6 times (player rolls or DM rolls)
    standard → 15, 14, 13, 12, 10, 8
    pointbuy → 27 points
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

DEFAULT_DATA_DIR = Path("/opt/data")
CAMPAIGNS_DIR = DEFAULT_DATA_DIR / "campaigns"

RACES = {
    "human": {"str": 1, "dex": 1, "con": 1, "int": 1, "wis": 1, "cha": 1},
    "elf": {"dex": 2, "wis": 1},  # wood elf
    "dwarf": {"con": 2, "str": 2},  # mountain dwarf
    "halfling": {"dex": 2, "con": 1},  # stout
    "dragonborn": {"str": 2, "cha": 1},
    "gnome": {"int": 2, "con": 1},  # rock gnome
    "half-elf": {"cha": 2, "int": 1, "wis": 1},
    "half-orc": {"str": 2, "con": 1},
    "tiefling": {"cha": 2, "int": 1},
}

CLASSES = {
    "barbarian": {"hp_die": 12, "saves": ["str", "con"]},
    "bard": {"hp_die": 8, "saves": ["dex", "cha"]},
    "cleric": {"hp_die": 8, "saves": ["wis", "cha"]},
    "druid": {"hp_die": 8, "saves": ["int", "wis"]},
    "fighter": {"hp_die": 10, "saves": ["str", "con"]},
    "monk": {"hp_die": 8, "saves": ["str", "dex"]},
    "paladin": {"hp_die": 10, "saves": ["wis", "cha"]},
    "ranger": {"hp_die": 10, "saves": ["str", "dex"]},
    "rogue": {"hp_die": 8, "saves": ["dex", "int"]},
    "sorcerer": {"hp_die": 6, "saves": ["con", "cha"]},
    "warlock": {"hp_die": 8, "saves": ["wis", "cha"]},
    "wizard": {"hp_die": 6, "saves": ["int", "wis"]},
}

ABILITIES = ["str", "dex", "con", "int", "wis", "cha"]

POINT_BUY_COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}


def roll_4d6_drop_lowest() -> int:
    rolls = sorted([random.randint(1, 6) for _ in range(4)])
    return sum(rolls[1:])  # Drop lowest


def roll_stats(method: str) -> dict:
    if method == "standard":
        array = [15, 14, 13, 12, 10, 8]
        return {ability: array[i] for i, ability in enumerate(ABILITIES)}

    if method == "pointbuy":
        # For DM-guided creation, assign balanced point-buy array
        return {"str": 12, "dex": 14, "con": 13, "int": 10, "wis": 10, "cha": 8}

    # Default: roll
    results = []
    for _ in range(6):
        kept = sorted([random.randint(1, 6) for _ in range(4)])[1:]
        results.append(sum(kept))
    results.sort(reverse=True)

    print("🎲 Rolled stats (4d6 drop lowest):")
    for i, r in enumerate(results, 1):
        print(f"   Set {i}: {r}")

    return {
        "str": results[0],
        "dex": results[1],
        "con": results[2],
        "int": results[3],
        "wis": results[4],
        "cha": results[5],
    }


def apply_racial_bonuses(stats: dict, race: str) -> dict:
    bonuses = RACES.get(race.lower(), {})
    result = dict(stats)
    for ability, bonus in bonuses.items():
        result[ability] = result.get(ability, 10) + bonus
    return result


def calc_hp(cls: str, con_mod: int) -> int:
    hp_die = CLASSES.get(cls.lower(), {}).get("hp_die", 8)
    return hp_die + con_mod


def calc_ac(dex_mod: int, cls: str = "") -> int:
    # Simple: leather armor + dex mod
    return 11 + dex_mod


def calc_mod(score: int) -> int:
    return (score - 10) // 2


def get_active_campaign() -> str | None:
    active_file = DEFAULT_DATA_DIR / "active_campaign"
    if active_file.exists():
        val = active_file.read_text(encoding="utf-8").strip()
        if val:
            return val
    return None


def slugify(text: str) -> str:
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


def create_character(name: str, race: str, cls: str, background: str, method: str, campaign_id: str | None = None):
    campaign_id = campaign_id or get_active_campaign()
    if not campaign_id:
        print("❌ No active campaign. Create or switch to a campaign first.")
        return False

    campaign_dir = CAMPAIGNS_DIR / slugify(campaign_id)
    chars_dir = campaign_dir / "characters"
    chars_dir.mkdir(parents=True, exist_ok=True)

    char_file = chars_dir / f"{slugify(name)}.md"

    # Roll stats
    base_stats = roll_stats(method)
    final_stats = apply_racial_bonuses(base_stats, race)
    mods = {a: calc_mod(final_stats[a]) for a in ABILITIES}

    hp = calc_hp(cls, mods["con"])
    ac = calc_ac(mods["dex"], cls)
    speed = 30

    # Default equipment based on class
    equipment = {
        "barbarian": "Greataxe, 2 handaxes, explorer's pack, 4 javelins",
        "bard": "Rapier, diplomat's pack, lute, leather armor, dagger",
        "cleric": "Mace, scale mail, light crossbow, priest's pack, shield",
        "druid": "Scimitar, leather armor, explorer's pack, wooden shield",
        "fighter": "Chain mail, longsword, shield, dungeonerr's pack",
        "monk": "Shortsword, 10 darts, explorer's pack",
        "paladin": "Longsword, shield, 5 javelins, chain mail, holy symbol",
        "ranger": "Shortswords (2), longbow, 20 arrows, leather armor",
        "rogue": "Rapier, shortbow, 20 arrows, leather armor, thieves' tools",
        "sorcerer": "Light crossbow, 20 bolts, component pouch, scholar's pack",
        "warlock": "Light crossbow, 20 bolts, component pouch, scholar's pack",
        "wizard": "Quarterstaff, component pouch, scholar's pack, spellbook",
    }.get(cls.lower(), "Basic adventurer's kit")

    # Write markdown character sheet
    md = f"""# {name}

## Basics
- **Race**: {race.title()}
- **Class**: {cls.title()} 1
- **Background**: {background.title()}
- **Alignment**: Neutral Good

## Stats
| STR | DEX | CON | INT | WIS | CHA |
|-----|-----|-----|-----|-----|-----|
| {final_stats['str']} | {final_stats['dex']} | {final_stats['con']} | {final_stats['int']} | {final_stats['wis']} | {final_stats['cha']} |

- **HP**: {hp}/{hp}
- **AC**: {ac}
- **Speed**: {speed} ft
- **Initiative**: {mods['dex']:+d}

## Modifiers
| STR | DEX | CON | INT | WIS | CHA |
|-----|-----|-----|-----|-----|-----|
| {mods['str']:+d} | {mods['dex']:+d} | {mods['con']:+d} | {mods['int']:+d} | {mods['wis']:+d} | {mods['cha']:+d} |

## Proficiencies
- **Saves**: {', '.join(CLASSES.get(cls.lower(), {}).get('saves', ['str', 'con']))}
- **Skills**: Perception, Stealth (placeholder)
- **Tools**: None
- **Languages**: Common, {race.title()}

## Equipment
{equipment}

## Features & Traits
- **Racial**: {race.title()} traits
- **Class**: {cls.title()} level 1 features
- **Background**: {background.title()} feature

## Spells
{"None (prepared caster)" if cls.lower() in ['cleric', 'druid', 'paladin', 'wizard'] else "None (spontaneous caster)" if cls.lower() in ['bard', 'sorcerer', 'warlock'] else "N/A (non-caster)"}

## Notes
Created on {__import__('datetime').datetime.now().strftime('%Y-%m-%d')} using {method} method.
"""

    char_file.write_text(md, encoding="utf-8")

    print(f"✅ Character created: {name}")
    print(f"   📂 campaigns/{campaign_id}/characters/{slugify(name)}.md")
    print(f"   📊 Stats: STR {final_stats['str']} DEX {final_stats['dex']} CON {final_stats['con']} INT {final_stats['int']} WIS {final_stats['wis']} CHA {final_stats['cha']}")
    print(f"   ❤️ HP: {hp} | 🛡️ AC: {ac}")
    return True


def list_characters(campaign_id: str | None = None):
    campaign_id = campaign_id or get_active_campaign()
    if not campaign_id:
        print("❌ No active campaign.")
        return

    chars_dir = CAMPAIGNS_DIR / slugify(campaign_id) / "characters"
    if not chars_dir.exists():
        print("📭 No characters found.")
        return

    chars = sorted(chars_dir.glob("*.md"))
    if not chars:
        print("📭 No characters found.")
        return

    print(f"👥 Characters in [{campaign_id}]:")
    for c in chars:
        name = c.stem.replace("_", " ").title()
        print(f"   • {name}")


def show_character(name: str, campaign_id: str | None = None):
    campaign_id = campaign_id or get_active_campaign()
    if not campaign_id:
        print("❌ No active campaign.")
        return

    char_file = CAMPAIGNS_DIR / slugify(campaign_id) / "characters" / f"{slugify(name)}.md"
    if not char_file.exists():
        print(f"❌ Character '{name}' not found.")
        return

    print(char_file.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Character Creator")
    sub = parser.add_subparsers(dest="action", required=True)

    create_p = sub.add_parser("create", help="Create a new character")
    create_p.add_argument("--name", required=True, help="Character name")
    create_p.add_argument("--race", required=True, help="Character race")
    create_p.add_argument("--class", required=True, help="Character class")
    create_p.add_argument("--background", default="Soldier", help="Character background")
    create_p.add_argument("--method", choices=["roll", "standard", "pointbuy"], default="roll",
                          help="Stat generation method (default: roll)")
    create_p.add_argument("--campaign", help="Campaign ID (default: active)")

    list_p = sub.add_parser("list", help="List characters")
    list_p.add_argument("--campaign", help="Campaign ID (default: active)")

    show_p = sub.add_parser("show", help="Show character sheet")
    show_p.add_argument("--name", required=True, help="Character name")
    show_p.add_argument("--campaign", help="Campaign ID (default: active)")

    args = parser.parse_args()

    if args.action == "create":
        ok = create_character(args.name, args.race, getattr(args, 'class'), args.background, args.method, args.campaign)
        sys.exit(0 if ok else 1)
    elif args.action == "list":
        list_characters(args.campaign)
    elif args.action == "show":
        show_character(args.name, args.campaign)


if __name__ == "__main__":
    main()
