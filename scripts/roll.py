#!/usr/bin/env python3
"""
roll.py — The Dice Engine for Hermes Dungeon Server.

Makes every roll transparent, verifiable, and narratively exciting.
Supports: advantage, disadvantage, crits, skill checks, attacks, saves,
and beautiful output for the DM to narrate.

Usage inside container:
    python3 /opt/data/scripts/roll.py 1d20+5
    python3 /opt/data/scripts/roll.py attack --bonus 5 --ac 15 --damage 1d8+3
    python3 /opt/data/scripts/roll.py save --ability dex --bonus 3 --dc 14
    python3 /opt/data/scripts/roll.py skill --ability cha --bonus 4 --dc 12
    python3 /opt/data/scripts/roll.py initiative --names "Elara,Goblin1,Goblin2"
    python3 /opt/data/scripts/roll.py 4d6kh3  # roll 4d6 keep highest 3
    python3 /opt/data/scripts/roll.py 2d20kh1+5  # advantage
    python3 /opt/data/scripts/roll.py 2d20kl1+5  # disadvantage
"""

import argparse
import random
import re
import sys
from typing import List, Tuple


def roll_die(sides: int) -> int:
    return random.randint(1, sides)


def parse_dice(expr: str) -> Tuple[int, int, int, str]:
    """
    Parse dice expression like '2d6+3', '4d6kh3', '2d20kh1+5'.
    Returns (count, sides, modifier, keep_mode).
    keep_mode: '' (normal), 'khN' (keep highest N), 'klN' (keep lowest N)
    """
    expr = expr.lower().replace(" ", "")

    # Extract modifier (+/-N) at the end
    modifier = 0
    mod_match = re.search(r'([+-]\d+)$', expr)
    if mod_match:
        modifier = int(mod_match.group(1))
        expr = expr[:mod_match.start()]

    # Extract keep mode
    keep_mode = ""
    keep_match = re.search(r'(kh|kl)(\d+)$', expr)
    if keep_match:
        keep_mode = keep_match.group(0)
        expr = expr[:keep_match.start()]

    # Parse NdS
    m = re.match(r'(\d+)d(\d+)$', expr)
    if not m:
        raise ValueError(f"Invalid dice expression: {expr}")

    return int(m.group(1)), int(m.group(2)), modifier, keep_mode


def roll_expression(expr: str, verbose: bool = False) -> Tuple[int, List[int], int, str]:
    """Roll a dice expression. Returns (total, rolls, modifier, keep_mode)."""
    count, sides, modifier, keep_mode = parse_dice(expr)

    rolls = [roll_die(sides) for _ in range(count)]
    kept_rolls = rolls.copy()

    if keep_mode.startswith("kh"):
        n = int(keep_mode[2:])
        kept_rolls = sorted(rolls, reverse=True)[:n]
    elif keep_mode.startswith("kl"):
        n = int(keep_mode[2:])
        kept_rolls = sorted(rolls)[:n]

    total = sum(kept_rolls) + modifier
    return total, rolls, modifier, keep_mode


def format_roll(expr: str, total: int, rolls: List[int], modifier: int, keep_mode: str) -> str:
    """Format a roll for display."""
    kept_set = set(rolls)
    if keep_mode.startswith("kh"):
        n = int(keep_mode[2:])
        kept = sorted(rolls, reverse=True)[:n]
        dropped = sorted([r for r in rolls if r not in kept or rolls.count(r) > kept.count(r)])[:len(rolls)-n]
        roll_strs = []
        for r in rolls:
            if r in kept:
                roll_strs.append(f"[{r}]")
                kept.remove(r)
            else:
                roll_strs.append(f"~~{r}~~")
        rolls_display = ", ".join(roll_strs)
    elif keep_mode.startswith("kl"):
        n = int(keep_mode[2:])
        kept = sorted(rolls)[:n]
        roll_strs = []
        for r in rolls:
            if r in kept:
                roll_strs.append(f"[{r}]")
                kept.remove(r)
            else:
                roll_strs.append(f"~~{r}~~")
        rolls_display = ", ".join(roll_strs)
    else:
        rolls_display = ", ".join(str(r) for r in rolls)

    mod_str = f"{modifier:+d}" if modifier != 0 else ""
    return f"🎲 {expr} → {rolls_display} {mod_str} = **{total}**"


def cmd_roll(args):
    for expr in args.expression:
        try:
            total, rolls, modifier, keep_mode = roll_expression(expr, args.verbose)
            print(format_roll(expr, total, rolls, modifier, keep_mode))

            # Highlight natural 1s and 20s on d20s
            if "d20" in expr.lower():
                for r in rolls:
                    if r == 20 and not keep_mode.startswith("kl"):
                        print("   🔥 NATURAL 20! Critical success!")
                    elif r == 1 and not keep_mode.startswith("kh"):
                        print("   💀 NATURAL 1! Critical failure!")
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)


def cmd_attack(args):
    """Attack roll: 1d20 + bonus vs AC, then damage if hit."""
    # Attack roll
    adv = "kh1" if args.advantage else "kl1" if args.disadvantage else ""
    expr = f"1d20{adv}+{args.bonus}" if (args.advantage or args.disadvantage) else f"1d20+{args.bonus}"

    total, rolls, modifier, keep_mode = roll_expression(expr)
    natural = rolls[0] if not keep_mode else (sorted(rolls, reverse=True)[0] if args.advantage else sorted(rolls)[0])

    print(f"⚔️ Attack: {expr}")
    print(f"   {format_roll(expr, total, rolls, modifier, keep_mode)}")
    print(f"   Target AC: {args.ac}")

    # Critical hit/miss
    if natural == 20:
        print("   🔥🔥 CRITICAL HIT! Roll damage TWICE and add!")
        if args.damage:
            dmg_total, dmg_rolls, dmg_mod, _ = roll_expression(args.damage)
            dmg_total2, dmg_rolls2, _, _ = roll_expression(args.damage)
            combined = dmg_total + dmg_total2
            print(f"   Damage roll 1: {format_roll(args.damage, dmg_total, dmg_rolls, dmg_mod, '')}")
            print(f"   Damage roll 2: {format_roll(args.damage, dmg_total2, dmg_rolls2, dmg_mod, '')}")
            print(f"   💥 TOTAL DAMAGE: {combined}")
        return
    elif natural == 1:
        print("   💀💀 CRITICAL MISS! Something terrible happens...")
        return

    if total >= args.ac:
        print(f"   ✅ HIT! ({total} ≥ {args.ac})")
        if args.damage:
            dmg_total, dmg_rolls, dmg_mod, _ = roll_expression(args.damage)
            print(f"   {format_roll(args.damage, dmg_total, dmg_rolls, dmg_mod, '')}")
    else:
        print(f"   ❌ MISS! ({total} < {args.ac})")


def cmd_save(args):
    """Saving throw: 1d20 + bonus vs DC."""
    adv = "kh1" if args.advantage else "kl1" if args.disadvantage else ""
    expr = f"1d20{adv}+{args.bonus}" if (args.advantage or args.disadvantage) else f"1d20+{args.bonus}"

    total, rolls, modifier, keep_mode = roll_expression(expr)
    natural = rolls[0] if not keep_mode else (sorted(rolls, reverse=True)[0] if args.advantage else sorted(rolls)[0])

    abi = args.ability.upper() if args.ability else "?"
    print(f"🛡️ {abi} Saving Throw: DC {args.dc}")
    print(f"   {format_roll(expr, total, rolls, modifier, keep_mode)}")

    if natural == 20:
        print("   🔥 NATURAL 20! Automatic success with flair!")
    elif natural == 1:
        print("   💀 NATURAL 1! Automatic failure, worst outcome!")
    elif total >= args.dc:
        print(f"   ✅ SUCCESS! ({total} ≥ {args.dc})")
    else:
        print(f"   ❌ FAILURE! ({total} < {args.dc})")


def cmd_skill(args):
    """Skill check: 1d20 + bonus vs DC."""
    cmd_save(args)  # Same mechanics, different label
    print("   (Skill check complete)")


def cmd_initiative(args):
    """Roll initiative for multiple combatants."""
    names = [n.strip() for n in args.names.split(",")]
    print("⚡ INITIATIVE")
    results = []
    for name in names:
        bonus = args.bonus if args.bonus else 0
        expr = f"1d20+{bonus}"
        total, rolls, modifier, _ = roll_expression(expr)
        results.append((total, name, rolls[0], bonus))

    # Sort by total descending
    results.sort(reverse=True)
    for i, (total, name, natural, bonus) in enumerate(results, 1):
        print(f"   {i}. {name}: {natural} + {bonus} = **{total}**")


def cmd_morale(args):
    """NPC morale check: 2d6 vs morale score."""
    total, rolls, _, _ = roll_expression("2d6")
    print(f"😰 Morale Check: 2d6 → {rolls[0]}, {rolls[1]} = **{total}**")
    print(f"   Morale threshold: {args.threshold}")
    if total > args.threshold:
        print("   💀 FAILS morale! Fleeing, surrendering, or panicking!")
    else:
        print("   ✅ PASSES morale! Fighting on!")


def cmd_reaction(args):
    """NPC reaction: 2d6 for attitude."""
    total, rolls, _, _ = roll_expression("2d6")
    print(f"🎭 NPC Reaction: 2d6 → {rolls[0]}, {rolls[1]} = **{total}**")
    if total <= 2:
        print("   😡 HOSTILE — attacks immediately!")
    elif total <= 5:
        print("   😠 Unfriendly — threatens, may attack")
    elif total <= 8:
        print("   😐 Neutral — cautious, waiting")
    elif total <= 10:
        print("   😊 Indifferent — willing to talk")
    else:
        print("   😍 FRIENDLY — helpful, offers aid!")


def cmd_loot(args):
    """Random loot roll."""
    total, rolls, _, _ = roll_expression(args.dice)
    print(f"💰 Loot Roll: {args.dice}")
    print(f"   {format_roll(args.dice, total, rolls, 0, '')}")
    if args.table:
        # Simple loot table
        tables = {
            "trinket": ["a silver locket", "a chipped bone die", "a feather that never falls"],
            "coin": ["2d6 copper", "1d6 silver", "1d4 gold"],
            "magic": ["a potion of healing", "a scroll of light", "a ring of warmth"],
        }
        items = tables.get(args.table.lower(), ["mysterious item"])
        idx = (total - 1) % len(items)
        print(f"   Found: {items[idx]}")


def main():
    parser = argparse.ArgumentParser(description="Hermes Dice Engine")
    sub = parser.add_subparsers(dest="command", required=True)

    # roll
    roll_p = sub.add_parser("roll", help="Roll dice expression(s)")
    roll_p.add_argument("expression", nargs="+", help="e.g. 1d20+5 2d8 4d6kh3")
    roll_p.add_argument("-v", "--verbose", action="store_true")

    # attack
    atk_p = sub.add_parser("attack", help="Attack roll vs AC")
    atk_p.add_argument("--bonus", type=int, required=True, help="Attack bonus")
    atk_p.add_argument("--ac", type=int, required=True, help="Target AC")
    atk_p.add_argument("--damage", help="Damage dice e.g. 1d8+3")
    atk_p.add_argument("--advantage", action="store_true")
    atk_p.add_argument("--disadvantage", action="store_true")

    # save
    save_p = sub.add_parser("save", help="Saving throw")
    save_p.add_argument("--ability", required=True, help="Ability name (str, dex, con, int, wis, cha)")
    save_p.add_argument("--bonus", type=int, required=True)
    save_p.add_argument("--dc", type=int, required=True)
    save_p.add_argument("--advantage", action="store_true")
    save_p.add_argument("--disadvantage", action="store_true")

    # skill
    skill_p = sub.add_parser("skill", help="Skill check")
    skill_p.add_argument("--ability", required=True)
    skill_p.add_argument("--bonus", type=int, required=True)
    skill_p.add_argument("--dc", type=int, required=True)
    skill_p.add_argument("--advantage", action="store_true")
    skill_p.add_argument("--disadvantage", action="store_true")

    # initiative
    init_p = sub.add_parser("initiative", help="Roll initiative")
    init_p.add_argument("--names", required=True, help="Comma-separated names")
    init_p.add_argument("--bonus", type=int, default=0)

    # morale
    morale_p = sub.add_parser("morale", help="NPC morale check (2d6)")
    morale_p.add_argument("--threshold", type=int, required=True, help="Morale score (lower is braver)")

    # reaction
    reaction_p = sub.add_parser("reaction", help="NPC reaction roll (2d6)")

    # loot
    loot_p = sub.add_parser("loot", help="Loot roll")
    loot_p.add_argument("--dice", default="1d6", help="Loot dice")
    loot_p.add_argument("--table", help="Table name: trinket, coin, magic")

    args = parser.parse_args()

    if args.command == "roll":
        cmd_roll(args)
    elif args.command == "attack":
        cmd_attack(args)
    elif args.command == "save":
        cmd_save(args)
    elif args.command == "skill":
        cmd_skill(args)
    elif args.command == "initiative":
        cmd_initiative(args)
    elif args.command == "morale":
        cmd_morale(args)
    elif args.command == "reaction":
        cmd_reaction(args)
    elif args.command == "loot":
        cmd_loot(args)


if __name__ == "__main__":
    main()
