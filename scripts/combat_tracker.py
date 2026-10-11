#!/usr/bin/env python3
"""
combat_tracker.py — D&D 5e Combat Tracker for Hermes Dungeon Server.

Tracks initiative, HP, turns, and conditions so the DM never loses track
in the middle of a fight. Hermes context compression is the enemy of combat;
this file is the shield.

Usage inside container:
    python3 scripts/combat_tracker.py init --party "Elara,Maya" --enemies "Goblin1:7:15,Goblin2:7:15"
    python3 scripts/combat_tracker.py status
    python3 scripts/combat_tracker.py next
    python3 scripts/combat_tracker.py damage Goblin1 9
    python3 scripts/combat_tracker.py heal Elara 5
    python3 scripts/combat_tracker.py condition Goblin1 add poisoned
    python3 scripts/combat_tracker.py end

Battle map (open play/battle_map.html in a browser; it updates live):
    python3 scripts/combat_tracker.py init --party "Elara@C3" --enemies "Goblin1:7:15@H6,Ogre:59:11:-1:large@J8" --map assets/maps/cave.jpg
    python3 scripts/combat_tracker.py map --image assets/maps/cave.jpg --grid 24x18
    python3 scripts/combat_tracker.py move Elara D4 Goblin1 G6

Usage outside container (testing):
    python3 scripts/combat_tracker.py --data-dir ./test-data status
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

import battle_map
from dnd_paths import DATA_DIR as DEFAULT_DATA_DIR


def get_paths(data_dir: Path | None = None):
    d = data_dir or DEFAULT_DATA_DIR
    return {
        "data_dir": d,
        "combat_file": d / "combat_state.json",
        "campaign_file": d / "campaign_state.json",
    }


def _read_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _atomic_write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.rename(path)


def roll_d20(bonus: int = 0) -> int:
    return random.randint(1, 20) + bonus


def _split_pos(entry: str) -> tuple[str, str | None]:
    """'Goblin1:7:15@H6' → ('Goblin1:7:15', 'H6'), validating the cell."""
    if "@" not in entry:
        return entry, None
    body, cell = entry.rsplit("@", 1)
    battle_map.parse_cell(cell)
    return body.strip(), cell.strip().upper()


def _find(data: dict, name: str) -> dict | None:
    for c in data["combatants"]:
        if c["name"].lower() == name.lower():
            return c
    return None


def _check_in_bounds(data: dict, cell: str):
    col, row = battle_map.parse_cell(cell)
    m = data.get("map") or {}
    cols, rows = m.get("cols", battle_map.DEFAULT_COLS), m.get("rows", battle_map.DEFAULT_ROWS)
    if col >= cols or row >= rows:
        raise ValueError(
            f"{cell.upper()} is outside the {cols}x{rows} map "
            f"(last cell is {battle_map.cell_name(cols - 1, rows - 1)})"
        )


def _render_map(paths):
    try:
        battle_map.render(paths["data_dir"])
    except Exception as e:  # the map is a nice-to-have; never break combat over it
        print(f"   (battle map not updated: {e})")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_init(args, paths):
    """Initialize combat with initiative rolls."""
    combatants = []
    previous = _read_json(paths["combat_file"]) or {}
    try:
        if args.map or args.grid or args.inset:
            map_cfg = battle_map.make_map_config(paths["data_dir"], args.map, args.grid, args.inset)
        else:
            map_cfg = previous.get("map") or battle_map.make_map_config(paths["data_dir"], None, None, None)
    except ValueError as e:
        print(f"❌ {e}")
        return

    # Parse party
    for entry in (args.party or "").split(","):
        try:
            name, pos = _split_pos(entry.strip())
        except ValueError as e:
            print(f"❌ {e}")
            return
        if not name:
            continue
        bonus = args.party_bonus if args.party_bonus else 0
        init = roll_d20(bonus)
        combatants.append({
            "name": name,
            "type": "pc",
            "initiative": init,
            "hp_current": args.party_hp or 10,
            "hp_max": args.party_hp or 10,
            "ac": args.party_ac or 12,
            "conditions": [],
            "status": "alive",
            "pos": pos,
        })

    # Parse enemies (name:hp:ac[:bonus[:size]][@cell])
    for enemy_str in (args.enemies or "").split(","):
        try:
            enemy_str, pos = _split_pos(enemy_str.strip())
        except ValueError as e:
            print(f"❌ {e}")
            return
        if not enemy_str:
            continue
        parts = enemy_str.split(":")
        name = parts[0]
        hp = int(parts[1]) if len(parts) > 1 else 10
        ac = int(parts[2]) if len(parts) > 2 else 12
        bonus = int(parts[3]) if len(parts) > 3 and parts[3] else 0
        size = parts[4].lower() if len(parts) > 4 else "medium"
        if size not in battle_map.SIZES:
            print(f"❌ Unknown size '{size}' for {name}. Use: {', '.join(battle_map.SIZES)}")
            return
        init = roll_d20(bonus)
        combatants.append({
            "name": name,
            "type": "enemy",
            "initiative": init,
            "hp_current": hp,
            "hp_max": hp,
            "ac": ac,
            "conditions": [],
            "status": "alive",
            "size": size,
            "pos": pos,
        })

    # Sort by initiative descending
    combatants.sort(key=lambda x: x["initiative"], reverse=True)

    data = {
        "active": True,
        "round": 1,
        "turn_index": 0,
        "combatants": combatants,
        "map": map_cfg,
        "log": [f"Combat started at {datetime.now().strftime('%H:%M:%S')}"],
    }
    for c in combatants:
        if c["pos"]:
            try:
                _check_in_bounds(data, c["pos"])
            except ValueError as e:
                print(f"❌ {c['name']}: {e}")
                return

    _atomic_write(paths["combat_file"], data)
    _render_map(paths)

    print("⚔️  COMBAT STARTED")
    print(f"   Round 1 | {len(combatants)} combatants")
    print()
    for i, c in enumerate(combatants, 1):
        marker = " ← CURRENT" if i == 1 else ""
        at = f" @{c['pos']}" if c.get("pos") else ""
        print(f"   {i}. {c['name']} (INIT: {c['initiative']}) HP:{c['hp_current']}/{c['hp_max']} AC:{c['ac']}{at}{marker}")
    print()
    print(f"   It's {combatants[0]['name']}'s turn!")


def cmd_status(args, paths):
    """Show current combat status."""
    data = _read_json(paths["combat_file"])
    if not data or not data.get("active"):
        print("📭 No active combat.")
        return

    combatants = data["combatants"]
    turn_idx = data["turn_index"]
    round_num = data["round"]
    current = combatants[turn_idx] if turn_idx < len(combatants) else None

    print(f"⚔️  Round {round_num} | Turn: {current['name'] if current else '?'}")
    print()
    for i, c in enumerate(combatants):
        marker = " ▶ " if i == turn_idx else "   "
        hp_pct = int(c["hp_current"] / c["hp_max"] * 100) if c["hp_max"] > 0 else 0
        bar = "█" * int(hp_pct / 10) + "░" * (10 - int(hp_pct / 10))
        conds = ", ".join(c["conditions"]) if c["conditions"] else "—"
        status = "💀" if c["status"] == "dead" else "😵" if c["status"] == "unconscious" else ""
        at = c.get("pos") or "—"
        print(f"{marker}{c['name']:<15} HP:{c['hp_current']:>3}/{c['hp_max']:<3} [{bar}] {status} @{at:<4} | {conds}")
    print()
    if current and current["status"] == "alive":
        print(f"   🎯 {current['name']}'s turn! What do they do?")


def cmd_next(args, paths):
    """Advance to next turn."""
    data = _read_json(paths["combat_file"])
    if not data or not data.get("active"):
        print("📭 No active combat.")
        return

    combatants = [c for c in data["combatants"] if c["status"] == "alive"]
    if not combatants:
        print("💀 All combatants are down. Combat should end.")
        return

    data["turn_index"] += 1
    if data["turn_index"] >= len(data["combatants"]):
        data["turn_index"] = 0
        data["round"] += 1
        data["log"].append(f"Round {data['round']} started")

    current = data["combatants"][data["turn_index"]]
    while current["status"] != "alive" and data["turn_index"] < len(data["combatants"]) - 1:
        data["turn_index"] += 1
        current = data["combatants"][data["turn_index"]]

    # If wrapped around and still dead, recheck
    if current["status"] != "alive":
        data["turn_index"] = 0
        data["round"] += 1
        current = data["combatants"][data["turn_index"]]

    data["log"].append(f"Turn: {current['name']} (Round {data['round']})")
    _atomic_write(paths["combat_file"], data)
    _render_map(paths)

    print(f"➡️  Round {data['round']} | {current['name']}'s turn!")
    if current["conditions"]:
        print(f"   Conditions: {', '.join(current['conditions'])}")


def cmd_damage(args, paths):
    """Apply damage to a combatant."""
    data = _read_json(paths["combat_file"])
    if not data or not data.get("active"):
        print("📭 No active combat.")
        return

    target = None
    for c in data["combatants"]:
        if c["name"].lower() == args.target.lower():
            target = c
            break

    if not target:
        print(f"❌ Combatant '{args.target}' not found.")
        print("   Available: " + ", ".join(c["name"] for c in data["combatants"]))
        return

    target["hp_current"] = max(0, target["hp_current"] - args.amount)
    data["log"].append(f"{target['name']} takes {args.amount} damage (HP: {target['hp_current']}/{target['hp_max']})")

    if target["hp_current"] == 0 and target["type"] == "pc":
        target["status"] = "unconscious"
        print(f"💔 {target['name']} falls unconscious! Death saves begin...")
    elif target["hp_current"] == 0:
        target["status"] = "dead"
        print(f"💀 {target['name']} is slain!")
    else:
        print(f"⚔️  {target['name']} takes {args.amount} damage → HP {target['hp_current']}/{target['hp_max']}")

    _atomic_write(paths["combat_file"], data)
    _render_map(paths)


def cmd_heal(args, paths):
    """Heal a combatant."""
    data = _read_json(paths["combat_file"])
    if not data or not data.get("active"):
        print("📭 No active combat.")
        return

    target = None
    for c in data["combatants"]:
        if c["name"].lower() == args.target.lower():
            target = c
            break

    if not target:
        print(f"❌ Combatant '{args.target}' not found.")
        return

    old_hp = target["hp_current"]
    target["hp_current"] = min(target["hp_max"], target["hp_current"] + args.amount)
    healed = target["hp_current"] - old_hp

    if target["status"] == "unconscious" and target["hp_current"] > 0:
        target["status"] = "alive"
        print(f"✨ {target['name']} is stabilized! HP {target['hp_current']}/{target['hp_max']}")
    else:
        print(f"💚 {target['name']} heals {healed} → HP {target['hp_current']}/{target['hp_max']}")

    data["log"].append(f"{target['name']} healed {healed} (HP: {target['hp_current']}/{target['hp_max']})")
    _atomic_write(paths["combat_file"], data)
    _render_map(paths)


def cmd_condition(args, paths):
    """Add or remove a condition."""
    data = _read_json(paths["combat_file"])
    if not data or not data.get("active"):
        print("📭 No active combat.")
        return

    target = None
    for c in data["combatants"]:
        if c["name"].lower() == args.target.lower():
            target = c
            break

    if not target:
        print(f"❌ Combatant '{args.target}' not found.")
        return

    condition = args.condition.lower()

    if args.action == "add":
        if condition not in target["conditions"]:
            target["conditions"].append(condition)
            print(f"🔗 {target['name']} is now {condition.upper()}!")
            data["log"].append(f"{target['name']} gains condition: {condition}")
        else:
            print(f"ℹ️  {target['name']} is already {condition}.")
    else:
        if condition in target["conditions"]:
            target["conditions"].remove(condition)
            print(f"✨ {target['name']} is no longer {condition.upper()}!")
            data["log"].append(f"{target['name']} loses condition: {condition}")
        else:
            print(f"ℹ️  {target['name']} doesn't have {condition}.")

    _atomic_write(paths["combat_file"], data)
    _render_map(paths)


def cmd_end(args, paths):
    """End combat and archive log to campaign_state.json."""
    data = _read_json(paths["combat_file"])
    if not data or not data.get("active"):
        print("📭 No active combat.")
        return

    data["active"] = False
    data["log"].append(f"Combat ended at {datetime.now().strftime('%H:%M:%S')} (Round {data['round']})")
    _atomic_write(paths["combat_file"], data)
    _render_map(paths)

    # Archive to campaign_state.json
    campaign = _read_json(paths["campaign_file"])
    if campaign:
        session_log = campaign.setdefault("session_log", [])
        session_log.append({
            "type": "combat",
            "title": f"Combat (Round {data['round']})",
            "content": f"Combat ended. Survivors: {', '.join(c['name'] for c in data['combatants'] if c['status'] == 'alive')}. "
                       f"Defeated: {', '.join(c['name'] for c in data['combatants'] if c['status'] == 'dead')}",
            "combat_log": data["log"],
        })
        _atomic_write(paths["campaign_file"], campaign)
        print("✅ Combat archived to campaign_state.json")

    print("🏳️  COMBAT ENDED")
    print(f"   Rounds: {data['round']}")
    print(f"   Survivors: {', '.join(c['name'] for c in data['combatants'] if c['status'] == 'alive') or 'None'}")
    print(f"   Defeated: {', '.join(c['name'] for c in data['combatants'] if c['status'] == 'dead') or 'None'}")


def cmd_add(args, paths):
    """Add a combatant mid-combat."""
    data = _read_json(paths["combat_file"])
    if not data or not data.get("active"):
        print("📭 No active combat.")
        return

    init = roll_d20(args.init_bonus or 0)
    new_combatant = {
        "name": args.name,
        "type": args.combatant_type,
        "initiative": init,
        "hp_current": args.hp,
        "hp_max": args.hp,
        "ac": args.ac,
        "conditions": [],
        "status": "alive",
        "size": args.size,
        "pos": args.at.upper() if args.at else None,
    }
    if args.token:
        new_combatant["token"] = args.token
    if args.at:
        try:
            _check_in_bounds(data, args.at)
        except ValueError as e:
            print(f"❌ {e}")
            return
    data["combatants"].append(new_combatant)
    data["combatants"].sort(key=lambda x: x["initiative"], reverse=True)
    data["log"].append(f"{args.name} joins combat (INIT: {init})")
    _atomic_write(paths["combat_file"], data)
    _render_map(paths)

    print(f"➕ {args.name} joins combat!")
    print(f"   HP: {args.hp} | AC: {args.ac} | INIT: {init}")
    print(f"   Initiative order updated.")


def cmd_remove(args, paths):
    """Remove a combatant from combat."""
    data = _read_json(paths["combat_file"])
    if not data or not data.get("active"):
        print("📭 No active combat.")
        return

    for i, c in enumerate(data["combatants"]):
        if c["name"].lower() == args.name.lower():
            data["combatants"].pop(i)
            data["log"].append(f"{args.name} removed from combat")
            _atomic_write(paths["combat_file"], data)
            _render_map(paths)
            print(f"➖ {args.name} removed from combat.")
            return

    print(f"❌ Combatant '{args.name}' not found.")


def cmd_map(args, paths):
    """Set the battle map image and grid (works before, during and after combat)."""
    data = _read_json(paths["combat_file"]) or {"active": False, "round": 0, "turn_index": 0,
                                               "combatants": [], "log": []}
    try:
        cfg = battle_map.make_map_config(
            paths["data_dir"], None if args.none else args.image, args.grid, args.inset
        )
        if not args.none and not args.image and data.get("map", {}).get("image"):
            # Only the grid changed: keep the current image.
            cfg = battle_map.make_map_config(
                paths["data_dir"], data["map"]["image"], args.grid, args.inset
            )
    except ValueError as e:
        print(f"❌ {e}")
        return
    data["map"] = cfg
    _atomic_write(paths["combat_file"], data)
    if cfg["image"] and (args.grid or args.inset):
        battle_map.save_map_grid(paths["data_dir"], cfg)
    _render_map(paths)
    last = battle_map.cell_name(cfg["cols"] - 1, cfg["rows"] - 1)
    print(f"🗺️  Map: {cfg['image'] or 'blank grid'} | {cfg['cols']}x{cfg['rows']} squares (A1–{last})")


def cmd_move(args, paths):
    """Move one or more combatants: move Ana C4 Goblin1 F7"""
    data = _read_json(paths["combat_file"])
    if not data or not data.get("combatants"):
        print("📭 No combatants. Start combat first.")
        return
    if len(args.moves) % 2:
        print("❌ Give pairs of NAME CELL, e.g. move Ana C4 Goblin1 F7")
        return
    pairs = list(zip(args.moves[::2], args.moves[1::2]))
    for name, cell in pairs:  # validate everything before changing anything
        if not _find(data, name):
            print(f"❌ Combatant '{name}' not found.")
            print("   Available: " + ", ".join(c["name"] for c in data["combatants"]))
            return
        if cell.lower() not in ("off", "-"):
            try:
                _check_in_bounds(data, cell)
            except ValueError as e:
                print(f"❌ {e}")
                return
    for name, cell in pairs:
        c = _find(data, name)
        old = c.get("pos")
        c["pos"] = None if cell.lower() in ("off", "-") else cell.upper()
        if old and c["pos"]:
            oc, orow = battle_map.parse_cell(old)
            nc, nrow = battle_map.parse_cell(c["pos"])
            feet = max(abs(nc - oc), abs(nrow - orow)) * 5
            print(f"👣 {c['name']}: {old} → {c['pos']} ({feet} ft)")
        else:
            print(f"👣 {c['name']}: {c['pos'] or 'off the map'}")
        data["log"].append(f"{c['name']} moves to {c['pos'] or 'off the map'}")
    _atomic_write(paths["combat_file"], data)
    _render_map(paths)


def cmd_token(args, paths):
    """Set token art for a combatant (path inside the data dir)."""
    data = _read_json(paths["combat_file"])
    c = _find(data, args.name) if data else None
    if not c:
        print(f"❌ Combatant '{args.name}' not found.")
        return
    img = paths["data_dir"] / args.image
    if not img.exists():
        print(f"❌ Image not found: {img}")
        return
    c["token"] = Path(args.image).as_posix()
    _atomic_write(paths["combat_file"], data)
    _render_map(paths)
    print(f"🖼️  {c['name']} now uses {c['token']}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="D&D 5e Combat Tracker")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Data directory (default: {DEFAULT_DATA_DIR})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    init_p = sub.add_parser("init", help="Start combat with initiative")
    init_p.add_argument("--party", help="Comma-separated PC names")
    init_p.add_argument("--party-hp", type=int, help="Default PC HP")
    init_p.add_argument("--party-ac", type=int, help="Default PC AC")
    init_p.add_argument("--party-bonus", type=int, default=0, help="Initiative bonus for all PCs")
    init_p.add_argument("--enemies", help="Enemies: Name:HP:AC[:Bonus[:Size]][@Cell], comma-separated")
    init_p.add_argument("--map", help="Map image inside the data dir, e.g. assets/maps/cave.jpg")
    init_p.add_argument("--grid", help="Map size in squares, e.g. 24x18 (default 20x15)")
    init_p.add_argument("--inset", help="Grid margins as fractions: left,top,right,bottom")

    # status
    sub.add_parser("status", help="Show combat status")

    # next
    sub.add_parser("next", help="Advance to next turn")

    # damage
    dmg_p = sub.add_parser("damage", help="Apply damage")
    dmg_p.add_argument("target", help="Combatant name")
    dmg_p.add_argument("amount", type=int, help="Damage amount")

    # heal
    heal_p = sub.add_parser("heal", help="Heal combatant")
    heal_p.add_argument("target", help="Combatant name")
    heal_p.add_argument("amount", type=int, help="Heal amount")

    # condition
    cond_p = sub.add_parser("condition", help="Add/remove condition")
    cond_p.add_argument("target", help="Combatant name")
    cond_p.add_argument("action", choices=["add", "remove"], help="Add or remove")
    cond_p.add_argument("condition", help="Condition name (poisoned, prone, stunned, etc.)")

    # end
    sub.add_parser("end", help="End combat")

    # add
    add_p = sub.add_parser("add", help="Add combatant mid-combat")
    add_p.add_argument("name", help="Combatant name")
    add_p.add_argument("--type", dest="combatant_type", default="enemy", choices=["pc", "enemy", "npc"])
    add_p.add_argument("--hp", type=int, required=True)
    add_p.add_argument("--ac", type=int, default=12)
    add_p.add_argument("--init-bonus", type=int, default=0)
    add_p.add_argument("--size", default="medium", choices=list(battle_map.SIZES))
    add_p.add_argument("--at", help="Grid cell, e.g. F7")
    add_p.add_argument("--token", help="Token image inside the data dir")

    # remove
    rem_p = sub.add_parser("remove", help="Remove combatant")
    rem_p.add_argument("name", help="Combatant name")

    # map
    map_p = sub.add_parser("map", help="Set battle map image/grid")
    map_p.add_argument("--image", help="Map image inside the data dir")
    map_p.add_argument("--grid", help="Squares, e.g. 24x18")
    map_p.add_argument("--inset", help="Grid margins as fractions: left,top,right,bottom")
    map_p.add_argument("--none", action="store_true", help="Use a blank grid")

    # move
    move_p = sub.add_parser("move", help="Move combatants: NAME CELL [NAME CELL ...]")
    move_p.add_argument("moves", nargs="+", help="Pairs of name and cell (or 'off')")

    # token
    tok_p = sub.add_parser("token", help="Set token image for a combatant")
    tok_p.add_argument("name")
    tok_p.add_argument("image", help="Image path inside the data dir")

    args = parser.parse_args()
    paths = get_paths(args.data_dir)

    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "next": cmd_next,
        "damage": cmd_damage,
        "heal": cmd_heal,
        "condition": cmd_condition,
        "end": cmd_end,
        "add": cmd_add,
        "remove": cmd_remove,
        "map": cmd_map,
        "move": cmd_move,
        "token": cmd_token,
    }

    commands[args.command](args, paths)


if __name__ == "__main__":
    main()
