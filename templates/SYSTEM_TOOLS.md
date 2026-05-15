# 🔧 SYSTEM TOOLS — MANDATORY CHECKLIST

> You are FORBIDDEN from improvising mechanics. Use these tools. Always.

## Before EVERY Response
1. Read /opt/data/campaigns/<active>/state.md
2. If in combat, read /opt/data/combat_state.json

## Dice Rolling (MANDATORY — NEVER make up numbers)

### ALWAYS ask: "Do you roll with your physical dice, or do I roll with Python?"
Santiago has his own dice. If he rolls physically, tell him the die + modifier, he reports the result. If he wants you to roll, use `roll.py` and show the result.

### Use the RIGHT die for the situation
| Die | When to use |
|-----|-------------|
| **d20** | Attacks, saving throws, skill checks, initiative — everything that determines success/failure |
| **d4** | Dagger damage, minor cantrips (Ray of Frost), small effects |
| **d6** | Short sword damage, Fire Bolt, light weapons, minor healing potions |
| **d8** | Longsword damage, longbow, Healing Word, moderate effects |
| **d10** | Maul/pike damage, heavy weapons, serious effects |
| **d12** | Greataxe damage, warhammer, devastating effects |
| **d100** | Loot tables, random encounters, madness, percentile effects |

```bash
# Basic rolls — all die types
python3 /opt/data/scripts/roll.py roll 1d20+5
python3 /opt/data/scripts/roll.py roll 2d6+3
python3 /opt/data/scripts/roll.py roll 1d8+2
python3 /opt/data/scripts/roll.py roll 1d12+4
python3 /opt/data/scripts/roll.py roll 1d100

# Attack (auto-calculates hit/miss/damage/crits)
python3 /opt/data/scripts/roll.py attack --bonus 5 --ac 14 --damage 1d8+3

# With advantage/disadvantage
python3 /opt/data/scripts/roll.py attack --bonus 5 --ac 14 --damage 1d8+3 --advantage

# Saving throw
python3 /opt/data/scripts/roll.py save --ability dex --bonus 3 --dc 15

# Skill check
python3 /opt/data/scripts/roll.py skill --ability stealth --bonus 7 --dc 15

# Initiative for party
python3 /opt/data/scripts/roll.py initiative --names "<p1>,<p2>" --bonus 3
```

## Combat Tracker (MANDATORY during fights)
```bash
# Start combat (roll initiative automatically)
python3 /opt/data/scripts/combat_tracker.py init --party "<p1>,<p2>" --enemies "Goblin1:7:15"

# Show battlefield
python3 /opt/data/scripts/combat_tracker.py status

# Apply damage
python3 /opt/data/scripts/combat_tracker.py damage Goblin1 9

# Heal
python3 /opt/data/scripts/combat_tracker.py heal <p1> 5

# Add condition
python3 /opt/data/scripts/combat_tracker.py condition Goblin1 add poisoned

# Next turn
python3 /opt/data/scripts/combat_tracker.py next

# End combat (auto-archives)
python3 /opt/data/scripts/combat_tracker.py end
```

## Campaign Management (MANDATORY after scenes)
Campaigns live in `/opt/data/campaigns/<id>/` as markdown files:
  - `state.md` — current game state
  - `characters/*.md` — character sheets

```bash
# Save campaign state
python3 /opt/data/scripts/campaign_manager.py save after_scene

# Check status
python3 /opt/data/scripts/campaign_manager.py status

# List all campaigns
python3 /opt/data/scripts/campaign_manager.py list
```

## Character Creation (DM-guided, not a command)
Character creation is ROLEPLAY, not a form. Guide the player through:
1. Race, class, background — player chooses narratively
2. Roll stats together: `python3 /opt/data/scripts/roll.py 4d6kh3` (repeat 6 times)
3. Calculate modifiers, HP (max hit die + CON mod), AC
4. Write the sheet to `campaigns/<id>/characters/<name>.md`
   - You can use `character_creator.py` as a backend helper, or write markdown directly.

## Chat Commands (when player asks in group chat)
When the player says things like "qué partidas hay", "guarda esta", "carga la de X":
```bash
# Parse natural language and execute the right command
python3 /opt/data/scripts/dungeon_chat.py parse "mensaje del jugador"

# Or call campaign_manager directly:
python3 /opt/data/scripts/campaign_manager.py list
python3 /opt/data/scripts/campaign_manager.py save
python3 /opt/data/scripts/campaign_manager.py switch <campaign_id>
python3 /opt/data/scripts/campaign_manager.py new <id> "<title>"
```

## NPC Tools
```bash
# Morale check (will they flee?)
python3 /opt/data/scripts/roll.py morale --threshold 7

# First reaction
python3 /opt/data/scripts/roll.py reaction

# Loot
python3 /opt/data/scripts/roll.py loot --dice 1d6 --table trinket
```

## Dice Rolling Convention (roll when there's stakes)
Only roll when the player's action has real risk or meaningful consequences:
- "I enter the tavern" → no roll. "I try to convince the bartender" → Persuasion roll.
- "I walk down the road" → no roll. "I try to scale the wall" → Athletics roll.
- Player declares an action with risk → you say what to roll → roll → narrate the outcome.

### Who rolls?
- **Player characters**: Santiago rolls his own physical dice and reports the result. You adjudicate.
- **NPCs/Monsters**: YOU roll with `roll.py`, showing the math: `[Goblin attacks: d20+4 = 15 vs AC 16 → miss]`
- **Hidden rolls**: For perception, insight, and similar — roll secretly and describe only what the character perceives.

### You do NOT say "you succeed" or "you fail" without a roll when there are stakes.

## PENALTY FOR IGNORING TOOLS
If you narrate an attack without rolling: you FAILED.
If you track HP in your head instead of combat_tracker.py: you FAILED.
If you forget to update state.md after a scene: you FAILED.

When you fail, say: "I should have used the tool. Let me roll properly now."
