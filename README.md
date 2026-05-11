# 🎲 Hermes Dungeon Server

A persistent, self-healing D&D Dungeon Master powered by [Hermes Agent](https://github.com/NousResearch/hermes-agent) inside Docker.

> **"Your DM never sleeps. Your campaign never dies."**

## What is this?

This is a **Skill + template set** that turns a Hermes Agent container into a dedicated D&D server with:

- 🎲 **Mandatory dice rolling system** — every attack, skill check, and saving throw is resolved with transparent dice rolls
- 🧠 **Persistent campaign state** — every roll, every choice, every death is remembered
- 🛡️ **Crash recovery** — automatic backup and restore of SQLite state + sessions
- 🎭 **Customizable DM personality** — edit `SOUL.md` to make your DM sarcastic, epic, or eldritch
- 🔄 **Gateway watchdog** — if the AI gateway crashes, it auto-restarts in 5 seconds
- 📜 **Canonical campaign included** — *The Lost Mine of Phandelver* ready to play
- 📱 **Multiplayer** — play via CLI, Telegram, or Discord (configure as needed)

## Requirements

- Docker
- `hermes-base:latest` image (you already have Hermes installed)
- An LLM API key (DeepSeek, OpenAI, OpenRouter, etc.)

## Quick Start

```bash
# 1. Clone this repo
git clone https://github.com/YOUR_USERNAME/hermes-dungeon-skill.git
cd hermes-dungeon-skill

# 2. Run the wizard
bash scripts/setup-dungeon.sh

# 3. Add your API key
nano ~/.hermes/dungeon_container/.env

# 4. Restart to apply
docker restart dungeon

# 5. Watch your DM come alive
docker logs -f dungeon
```

## 🧠 Sistema Mínimo — One File to Rule Them All

Your DM diagnosed the system and proposed a radical simplification. We implemented it.

### The Problem
- 6 different state files → guaranteed desynchronization
- 367-line skill → gets truncated or ignored
- 4 sources to read before responding → DM reads one, or none
- Manual saves → forgotten after intense scenes

### The Solution: 3 Files Only

| File | Purpose | Size |
|------|---------|------|
| `resumen-rapido.md` | **DM's single source of truth** — reads this before EVERY response | <500 chars |
| `DM_RULES.md` | 3 rules only: Lore, Memory, Style | <30 lines |
| `campaign_state.json` | Technical backup (DM never reads directly) | machine |

### `resumen-rapido.md` — The Bible

Auto-generated from `campaign_state.json` every 60 seconds. Contains:
- Campaign title + current location
- Party HP
- Active quests (compact)
- Last scene summary
- Next decision prompt
- 3-rule reminder

```bash
docker exec dungeon cat /opt/data/resumen-rapido.md
```

### `DM_RULES.md` — 3 Rules

```
Rule 0: Lore — NO canon characters in scenes
Rule 1: Memory — Read resumen-rapido.md BEFORE every response
Rule 2: Style — Roll dice always, give emoji options, narrate cinematically
```

Everything else (SRD, combat, XP) → read from `references/` only when needed.

### Auto-Update (No Manual Action Needed)

Three background processes run independently:
1. **Memory bridge** — regenerates `resumen-rapido.md` on boot
2. **Resumen generator** — updates `resumen-rapido.md` every 60 seconds
3. **Auto-save** — backs up `campaign_state.json` every 30 minutes + on crash

The DM never needs to remember to save. It just happens.

## 🧠 Session Survival — The Amnesia Fix

Hermes resets sessions daily (or on crash). Without intervention, your DM forgets everything. This repo solves that with a **memory bridge** system:

### How it works

1. **`session_resume.py`** — On boot and daily, reads `campaign_state.json` and generates `.session_resume_context.md`, a compact "memory prompt" the DM reads before responding.
2. **`campaign_state.py`** — Explicit save/load/status/restore tool. The DM runs `campaign_state.py save` after every major event.
3. **Cronjobs** — Auto-save every 30 min + daily memory regeneration at 08:00.
4. **`.campaign_loaded_today`** — A timestamp flag. If missing, the DM knows it has amnesia and must load the memory bridge.

### Quick commands

```bash
# Inside the container or via docker exec:

# Campaign manager (multi-slot save system)
docker exec dungeon python3 /opt/data/scripts/campaign_manager.py list
docker exec dungeon python3 /opt/data/scripts/campaign_manager.py status
docker exec dungeon python3 /opt/data/scripts/campaign_manager.py save after_boss_fight
docker exec dungeon python3 /opt/data/scripts/campaign_manager.py switch other_campaign

# Legacy single-campaign tools
docker exec dungeon python3 /opt/data/scripts/campaign_state.py status
docker exec dungeon python3 /opt/data/scripts/campaign_state.py list-backups
docker exec dungeon python3 /opt/data/scripts/campaign_state.py restore the_lost_mine_20260511_143000_auto.json
```

## ⚔️ Combat Tracker

Combat is where context compression kills campaigns. You can't track HP, initiative, and conditions in ephemeral memory. Use the Combat Tracker.

### Start combat

```bash
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py init \
  --party "Elara,Maya" \
  --party-hp 11 --party-ac 15 \
  --enemies "Goblin1:7:15,Goblin2:7:15,Boss:30:16:3"
```

Enemy format: `Name:HP:AC[:InitBonus]`

### Combat loop

```bash
# Check whose turn it is
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py status

# Apply damage
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py damage Goblin1 9

# Heal ally
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py heal Elara 5

# Add condition
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py condition Goblin2 add poisoned

# Remove condition
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py condition Elara remove poisoned

# Next turn
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py next

# Add enemy mid-fight
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py add "Reinforcement" --hp 12 --ac 14

# End combat (auto-archives to campaign_state.json)
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py end
```

### Status display

```
⚔️ Round 3 | Turn: Goblin2

 ▶ Elara           HP:  8/11  [███████░░░]   | —
   Maya            HP:  6/10  [██████░░░░]   | poisoned
   Goblin2         HP:  2/7   [██░░░░░░░░]   | prone

   🎯 Goblin2's turn! What do they do?
```

## 🎲 Dice Engine — Roll For Everything

The official dice engine: `roll.py`. Transparent, verifiable, and narratively exciting.

```bash
# Basic roll
python3 /opt/data/scripts/roll.py roll 1d20+5

# Attack with advantage + damage
python3 /opt/data/scripts/roll.py attack --bonus 5 --ac 14 --damage 1d8+3 --advantage

# Saving throw
python3 /opt/data/scripts/roll.py save --ability con --bonus 2 --dc 13

# Skill check with disadvantage
python3 /opt/data/scripts/roll.py skill --ability stealth --bonus 7 --dc 15 --disadvantage

# Initiative for whole party
python3 /opt/data/scripts/roll.py initiative --names "Elara,Maya,Goblin1" --bonus 3

# NPC morale (will they flee?)
python3 /opt/data/scripts/roll.py morale --threshold 7

# NPC first reaction
python3 /opt/data/scripts/roll.py reaction

# Random loot
python3 /opt/data/scripts/roll.py loot --dice 1d6 --table trinket
```

### Roll for EVERYTHING

The DM must roll dice for:
- **Combat** — attack, damage, initiative, saves (obvious)
- **Social** — persuasion, deception, intimidation, performance, haggling, bribery
- **Exploration** — foraging, tracking, navigation, spotting ambushes, secret doors
- **Atmosphere** — weather, NPC mood, random encounters, torch duration, rumor accuracy
- **Survival** — marching, holding breath, resisting disease/poison, camping
- **Crafting** — potion brewing, forgery, cooking, instrument playing

**Never narrate an outcome without a roll first.**

### Multi-Campaign: Like a Video Game

Save multiple campaigns and switch between them:

```bash
# List all saved campaigns
docker exec dungeon python3 /opt/data/scripts/campaign_manager.py list

# Create a new campaign slot
docker exec dungeon python3 /opt/data/scripts/campaign_manager.py new cyberpunk "Neon Shadows" "Night City"

# Switch to another campaign (auto-saves current)
docker exec dungeon python3 /opt/data/scripts/campaign_manager.py switch the_lost_mine
```

Each campaign is completely isolated. The DM will never mix Rowan's story with a cyberpunk runner.

### Troubleshooting: "My DM forgot who I am"

This means the session reset and the memory bridge wasn't loaded. Fix:

```bash
docker exec dungeon python3 /opt/data/scripts/session_resume.py
docker restart dungeon
```

The entrypoint now auto-runs `session_resume.py` on every boot, so this should rarely happen.

## 🎲 Dice Rolling System

This skill is designed so that **every action with consequences is resolved with dice**. The DM NEVER resolves risky actions by flat narration.

### Two Play Modes

**1. Player Rolls (recommended)**
If you have physical dice or a dice app:
```
🎲 Roll 1d20 + 5 (Dexterity + Proficiency)!
   DC: 15
   Stakes: Leap the chasm or fall on the rocks.
```

**2. Automatic Python (if no dice available)**
The DM rolls for you showing every step:
```
⚔️ Elara's longbow attack:
   1d20 → [12] + DEX (+3) + Proficiency (+2) = 17
   Goblin AC: 14
   ✅ Hit!
   Damage: 1d8 → [6] + DEX (+3) = 9 piercing
```

### D&D Dice We Use

| Die | Common Use |
|-----|-----------|
| d4 | Daggers, minor healing |
| d6 | Light weapons |
| d8 | Medium weapons, healing |
| d10 | War weapons |
| d12 | Greataxes, barbarians |
| **d20** | **Attack, saves, skills, initiative** |
| d100 | Encounter tables |

- **Natural 20** → Critical! Double damage or spectacular success
- **Natural 1** → Fumble! Dramatic failure with consequences

## 📜 Example Campaign: The Lost Mine of Phandelver

We include the canonical introductory D&D campaign ready to play:

- **Setting:** Sword Coast, town of Phandalin
- **Levels:** 1-5
- **Plot:** Escort a wagon, rescue Gundren Rockseeker, discover the lost mine, face the Cragmaw goblins and the Black Spider
- **Pregenerated character:** Elara Windblue, wood elf ranger level 1
- **Villains:** Klarg (bugbear chieftain) and Iarno "Glasstaff" Albrek (renegade wizard)

Campaign files are automatically copied to the data directory during installation.

## What's Included

| File | Purpose |
|------|---------|
| `SKILL.md` | Hermes Agent skill definition |
| `scripts/setup-dungeon.sh` | One-command setup wizard |
| `templates/SOUL.md` | DM personality with dice rolling emphasis |
| `templates/config.yaml` | Hermes config tuned for RPGs |
| `templates/entrypoint.sh` | Persistence + watchdog entrypoint |
| `templates/.env.example` | Environment variables template |
| `templates/campaigns/the_lost_mine.json` | Canonical campaign definition |
| `templates/campaigns_data/the_lost_mine.json` | Full campaign data |
| `templates/campaign_state.json` | Clean initial state |

## How It Works

```
┌─────────────────┐
│   You (player)  │───► CLI / Telegram / Discord
└─────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Docker Container: dungeon   │
│  ┌────────────────────────┐  │
│  │  Custom Entrypoint     │  │
│  │  ├─ Pre-start backup   │  │
│  │  ├─ Crash recovery     │  │
│  │  └─ Gateway watchdog   │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │  Hermes Gateway        │  │
│  │  ├─ SOUL.md (DM)       │  │
│  │  ├─ config.yaml        │  │
│  │  ├─ campaign_state.json│  │
│  │  └─ sessions/          │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Host Volume (persistent)    │
│  ~/.hermes/dungeon_container/│
└──────────────────────────────┘
```

## Customizing Your DM

Edit `~/.hermes/dungeon_container/SOUL.md` — changes take effect immediately without restart.

Example tweaks:
- Change tone from "cinematic" to "grimdark" or "comedic"
- Add house rules
- Define your setting (Forgotten Realms, homebrew, etc.)
- Change rolling style (always visible? result only?)

## Campaign State

The DM treats `campaign_state.json` as the **source of truth**. It tracks:
- Active campaign name
- Player characters (HP, inventory, stats)
- NPCs met
- Quest progress
- World state

The entrypoint backs this up every time the gateway starts or crashes.

## Backups

Backups live in two places inside the container:
- `/opt/data/session_backups/` — standard backups
- `/opt/data/.persistence_recovery/` — redundant copy

On the host, these are at:
- `~/.hermes/dungeon_container/session_backups/`
- `~/.hermes/dungeon_container/.persistence_recovery/`

## Multi-Player Setup

### Telegram Group
1. Create a bot with [@BotFather](https://t.me/botfather)
2. Add token to `.env`
3. Enable in `config.yaml`:
   ```yaml
   telegram:
     enabled: true
   ```
4. Restart container

### Discord Server
1. Create a Discord app + bot
2. Enable in `config.yaml`:
   ```yaml
   discord:
     require_mention: false
     auto_thread: true
   ```
3. Set token via `DISCORD_TOKEN` in `.env`
4. Restart container

## Troubleshooting

**Container keeps crashing?**
```bash
docker logs --tail 50 dungeon
```
Usually: missing API key or invalid model name.

**State got corrupted?**
The entrypoint auto-restores from latest backup. Manual restore:
```bash
cp ~/.hermes/dungeon_container/session_backups/state.db.post_1234567890 \
   ~/.hermes/dungeon_container/state.db
docker restart dungeon
```

**Want a second campaign?**
Run the wizard again with a different name:
```bash
bash scripts/setup-dungeon.sh
# → Name: dungeon2
```

## Credits

Inspired by the original `dungeon2` container — a love letter to persistent AI-driven tabletop RPGs.

Canonical campaign "The Lost Mine of Phandelver" adapted from the official D&D 5e module.

## License

MIT — see [LICENSE](LICENSE).
