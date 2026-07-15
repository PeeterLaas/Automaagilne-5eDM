<div align="center">
  <img src="assets/dnd-banner.jpg" alt="Hermes Dungeon Server" width="100%">
  
  # 🎲 Hermes Dungeon Server
  
  ### *Your DM never sleeps. Your campaign never dies.*
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![Hermes Agent](https://img.shields.io/badge/powered%20by-Hermes%20Agent-6B3FA0)](https://github.com/NousResearch/hermes-agent)
  [![D&D 5e](https://img.shields.io/badge/D%26D-5e-ED1C24)](https://dnd.wizards.com)
  
  **A persistent, self-healing Dungeon Master powered by AI. Deploy your own D&D server in 5 minutes.**
  
</div>

---

## 🏰 What Is This?

Hermes Dungeon Server transforms [Hermes Agent](https://github.com/NousResearch/hermes-agent) into a **dedicated, always-on D&D Dungeon Master** that runs inside a Docker container. It's like having a professional DM on call 24/7 — with memory, dice, combat tracking, and crash recovery built in.

Whether you're a solo player exploring the Sword Coast or a group venturing through a homebrew world, this server gives you a DM that:
- **Never sleeps** — available whenever you want to play
- **Never forgets** — remembers every roll, every choice, every conversation
- **Never cheats** — every dice roll is transparent and verifiable
- **Never crashes** — auto-recovery from failures in under 5 seconds

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🎲 | **Mandatory Dice** | Every action with consequences is resolved with transparent dice. No fudging. |
| 🧠 | **Persistent Memory** | Campaign state survives restarts, crashes, and session resets. Your DM always remembers who you are. |
| 🛡️ | **Self-Healing** | Gateway watchdog auto-restarts in seconds. State backups on every boot and crash. |
| ⚔️ | **Combat Tracker** | Full initiative, HP, conditions, and turn management. No more "wait, whose turn was it?" |
| 📜 | **Included Campaign** | *The Lost Mine of Phandelver* ready to play. Level 1-5, pregenerated character included. |
| 🎭 | **Customizable DM** | Edit `SOUL.md` to make your DM sarcastic, epic, grimdark, or whatever you want. |
| 📱 | **Multiplayer** | Play via CLI, Telegram, or Discord. Configure whatever platform you use. |
| 💾 | **Auto-Backup** | Campaign saved every 30 minutes and on every crash. Never lose progress. |
| 🎮 | **Multi-Campaign** | Run multiple campaigns and switch between them like save slots. |

## 🖼️ What It Looks Like

<div align="center">
  <table>
    <tr>
      <td align="center"><img src="assets/dice-critical.jpg" alt="Dice Rolling" width="400"><br><em>⬆ Transparent dice rolls for every action</em></td>
      <td align="center"><img src="assets/party-dungeon.jpg" alt="Adventuring Party" width="400"><br><em>⬆ Your party, your story, your DM</em></td>
    </tr>
  </table>
</div>

### Dice in Action

```
⚔️ Elara's longbow attack:
   1d20 → [12] + DEX (+3) + Proficiency (+2) = 17
   Goblin AC: 14
   ✅ Hit!
   Damage: 1d8 → [6] + DEX (+3) = 9 piercing
```

```
🎲 Elara's Stealth check:
   1d20 → [14] + DEX (+3) + Proficiency (+2) = 19
   Guard's passive Perception: 13
   ✅ SUCCESS! Elara slips through the shadows...
```

### Combat Tracker

```
⚔️ Round 3 | Turn: Goblin2

 ▶ Elara           HP:  8/11  [███████░░░]   | —
   Maya            HP:  6/10  [██████░░░░]   | poisoned
   Goblin2         HP:  2/7   [██░░░░░░░░]   | prone

   🎯 Goblin2's turn! What do they do?
```

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- [Docker](https://docker.com) installed and running
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed
- An LLM API key (DeepSeek, OpenAI, OpenRouter, etc.)

### Installation

```bash
# 1. Clone this repo
git clone https://github.com/sanfernandezf/hermes-dungeon-skill.git
cd hermes-dungeon-skill

# 2. Run the setup wizard
bash scripts/setup-dungeon.sh

# 3. Add your API key
nano ~/.hermes/dungeon_container/.env

# 4. Restart to apply
docker restart dungeon

# 5. Watch your DM come alive!
docker logs -f dungeon
```

The setup wizard will:
- 🏗️ Create the container with `--restart always`
- 📁 Set up persistent volumes for campaign data
- 🎭 Install the DM personality (SOUL.md)
- ⚙️ Configure Hermes with RPG-optimized settings
- 🔄 Enable auto-recovery and watchdog

### First Game

```bash
# Start a new campaign
docker exec dungeon python3 /opt/data/scripts/campaign_manager.py new fantasy "My First Campaign" "Phandalin"

# Enter the game
docker exec -it dungeon bash
# Then talk to your DM:
hermes chat
```

## 🎲 Dice System

Every roll is resolved by `scripts/roll.py` — transparent, verifiable, and narratively exciting.

```bash
# Basic roll
python3 /opt/data/scripts/roll.py roll 1d20+5

# Attack with advantage + damage
python3 /opt/data/scripts/roll.py attack --bonus 5 --ac 14 --damage 1d8+3 --advantage

# Saving throw
python3 /opt/data/scripts/roll.py save --ability con --bonus 2 --dc 13

# Initiative for whole party
python3 /opt/data/scripts/roll.py initiative --names "Elara,Maya,Goblin1" --bonus 3
```

| Die | Common Use |
|-----|-----------|
| d4 | Daggers, minor healing |
| d6 | Light weapons, fire damage |
| d8 | Medium weapons, major healing |
| **d20** | **Attack, saves, skills, initiative** |
| d100 | Encounter tables, madness |

> **Natural 20** → Critical hit! 🎉 | **Natural 1** → Fumble! 💀

## 🧠 How Memory Works

The biggest challenge with AI D&D is that the DM **forgets everything** when the session resets. This repo solves it with a **memory bridge** system:

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ You (player) │────▶│ Hermes Gateway   │────▶│ campaign_state  │
│              │◀────│ (the DM)         │◀────│ .json (disk)    │
└──────────────┘     └──────────────────┘     └─────────────────┘
                            │                          │
                            ▼                          ▼
                     ┌──────────────────┐     ┌─────────────────┐
                     │ resumen-rapido   │     │ session_backups │
                     │ .md (<500 chars) │     │ (every 30 min)  │
                     └──────────────────┘     └─────────────────┘
```

1. **`campaign_state.json`** — the source of truth on disk
2. **`resumen-rapido.md`** — compact summary the DM reads before every response
3. **Auto-backup** — campaign saved every 30 minutes + on every crash
4. **`DM_RULES.md`** — 3 rules the DM must follow: Lore, Memory, Style

### If Your DM Forgets Who You Are

```bash
docker exec dungeon python3 /opt/data/scripts/session_resume.py
docker restart dungeon
```

## ⚔️ Combat Tracker

Full-featured combat management. No more "wait, how much HP did that goblin have?"

```bash
# Start combat
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py init \
  --party "Elara,Maya" \
  --party-hp 11 --party-ac 15 \
  --enemies "Goblin1:7:15,Goblin2:7:15,Boss:30:16:3"

# Apply damage
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py damage Goblin1 9

# Next turn
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py next

# End combat (auto-archives)
docker exec dungeon python3 /opt/data/scripts/combat_tracker.py end
```

## 🎭 Customizing Your DM

Edit `~/.hermes/dungeon_container/SOUL.md` — changes take effect immediately.

```markdown
# Example: Grimdark DM
You are a weary, cynical DM who has seen a thousand adventurers die.
Your world is dark, your traps are lethal, and your NPCs are morally gray.
Describe wounds in visceral detail. Mercy is rare.
```

Want a different tone? Try:
- **Comedic** — fourth-wall-breaking, pun-filled narration
- **Epic** — sweeping descriptions, dramatic pauses
- **Minimalist** — "You see a door. What do you do?"
- **Eldritch** — cosmic horror, sanity checks, incomprehensible entities

## 📜 Included Campaign

**The Lost Mine of Phandelver** — the classic D&D 5e introductory campaign:

| | Detail |
|---|---|
| **Setting** | Sword Coast, town of Phandalin |
| **Levels** | 1-5 |
| **Plot** | Escort a wagon → rescue Gundren Rockseeker → discover the lost mine → face the Black Spider |
| **Character** | Elara Windblue, wood elf ranger level 1 |
| **Villains** | Klarg (bugbear chieftain) & Iarno "Glasstaff" Albrek (renegade wizard) |

## 🔧 Architecture

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

## 📦 What's Included

```
hermes-dungeon-skill/
├── SKILL.md                 # Hermes Agent skill definition
├── README.md                # This file
├── LICENSE                  # MIT license
├── assets/                  # Images for README
│   ├── dnd-banner.jpg
│   ├── dice-critical.jpg
│   └── party-dungeon.jpg
├── scripts/
│   ├── setup-dungeon.sh     # One-command setup wizard
│   ├── roll.py              # Dice engine (d4-d100)
│   ├── combat_tracker.py    # Combat management
│   ├── campaign_manager.py  # Multi-campaign save system
│   ├── character_creator.py # Character creation wizard
│   ├── dungeon_chat.py      # Chat interface
│   ├── generate_resumen.py  # Memory bridge generator
│   ├── session_cleaner.py   # Session maintenance
│   ├── session_resume.py    # Session recovery
│   ├── cron-auto-save.sh    # Auto-save cron template
│   └── cron-daily-loader.sh # Daily memory refresh
├── templates/
│   ├── SOUL.md              # DM personality template
│   ├── config.yaml          # RPG-optimized Hermes config
│   ├── entrypoint.sh        # Watchdog + recovery entrypoint
│   ├── .env.example         # Environment variables template
│   ├── DM_RULES.md          # 3 core DM rules
│   ├── campaigns/           # Campaign definitions
│   └── campaigns_data/      # Campaign data files
└── PLAN.md                  # Development roadmap
```

## 🤝 Contributing

This is an open-source project. Contributions welcome!

- 🐛 **Found a bug?** Open an issue
- 💡 **Have an idea?** Start a discussion
- 🔧 **Want to contribute?** Fork and submit a PR
- 🎲 **Created a campaign?** Share it with the community!

## ❤️ Why This Exists

AI is changing tabletop RPGs. This project proves that you can have a **genuinely good D&D experience** with an AI Dungeon Master — not a chatbot that pretends to roll dice, but a real DM with memory, consistency, rules, and dramatic tension.

The best part? It costs **$0 in inference fees** when running locally with Ollama, or pennies per session with a cheap API. No subscriptions. No pay-per-game. Just you, your party, and an AI that respects the dice.

---

<div align="center">

**Built with ❤️ for the D&D community**  
*[Hermes Agent](https://github.com/NousResearch/hermes-agent) • [D&D 5e SRD](https://dnd.wizards.com/resources/systems-reference-document)*

⭐ Star this repo if you want AI D&D to become a thing!  
🐛 Found an issue? [Open a ticket](https://github.com/sanfernandezf/hermes-dungeon-skill/issues)

</div>
