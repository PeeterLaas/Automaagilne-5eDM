---
name: hermes-dungeon-server
description: "Deploy a persistent D&D Dungeon Master server inside a Docker container using Hermes Agent. Includes state backups, crash recovery, gateway watchdog, and transparent mandatory dice rolling."
version: 1.0.0
author: Dungeon Community
license: MIT
metadata:
  hermes:
    tags: [dnd, rpg, gaming, dungeon-master, docker, server, persistence, gateway, dice]
    related_skills: [minecraft-modpack-server, pokemon-player]
---

# Hermes Dungeon Server

Deploy a persistent, self-healing D&D Dungeon Master inside a Docker container powered by Hermes Agent.

## When to Use
- User wants to play D&D through Hermes Agent (single player or group)
- User needs a dedicated, always-on DM container with crash recovery
- User wants campaign state persistence with automatic backups
- User asks about "dungeon server", "D&D bot", "persistent DM", or "RPG container"

## Prerequisites
- Docker installed and running
- `hermes-base:latest` image available locally (user already has Hermes installed)
- At least one LLM API key (DeepSeek, OpenAI, OpenRouter, etc.)

## Quick Start (Automated)

### 1. Clone or navigate to this skill repo
```bash
cd /path/to/hermes-dungeon-skill
```

### 2. Run the setup wizard
```bash
bash scripts/setup-dungeon.sh
```

This will:
- Ask for a dungeon name (default: `dungeon`)
- Create the data directory structure (`~/.hermes/<name>_container/`)
- Copy templates: `SOUL.md`, `config.yaml`, `.env.example`, `entrypoint.sh`
- Configure model/provider/timezone
- Create and start the Docker container with `--restart always`

### 3. Configure API keys
```bash
nano ~/.hermes/dungeon_container/.env
```

Add at minimum:
```bash
DEEPSEEK_API_KEY=sk-...
```

### 4. Customize your DM personality (optional)
```bash
nano ~/.hermes/dungeon_container/SOUL.md
```

### 5. Restart to apply
```bash
docker restart dungeon
```

## 🎲 DICE ROLLING SYSTEM

This skill enforces a **transparent and mandatory dice rolling system**. The DM NEVER resolves risky actions without rolling dice.

### Rolling Rules the DM Must Follow

1. **Every action with consequences requires dice** — combat, skills, saves, initiative
2. **Explain before rolling**: which die, which modifier, which DC, what's at stake
3. **Two supported modes**:
   - **Player rolls** (recommended): the user rolls physical dice or app and reports result
   - **Automatic Python**: if no dice available, the DM rolls with Python showing step-by-step math

### Examples of Rolls the DM Must Execute

**Attack:**
```
⚔️ Elara's longbow attack:
   1d20 → [12] + DEX (+3) + Proficiency (+2) = 17
   Goblin AC: 14
   ✅ Hit!
   Damage: 1d8 → [6] + DEX (+3) = 9 piercing
```

**Skill:**
```
🎲 Elara's Stealth check:
   1d20 → [14] + DEX (+3) + Proficiency (+2) = 19
   Guard's passive Perception: 13
   ✅ SUCCESS! Elara slips through the shadows...
```

**Saving Throw:**
```
🛡️ Constitution save against poison:
   1d20 → [8] + CON (+1) = 9
   DC: 12
   ❌ FAIL! The poison courses through your veins...
```

### D&D Dice the DM Must Know

| Die | Common Use |
|-----|-----------|
| d4 | Daggers, minor healing |
| d6 | Light weapons, fire damage |
| d8 | Medium weapons, major healing |
| d10 | War weapons, energy damage |
| d12 | Greataxes, barbarians |
| **d20** | **Attack, saves, skills, initiative** |
| d100 | Encounter tables, madness |

**Criticals:** Natural 20 = success/double damage. Natural 1 = fumble/dramatic consequence.

## Manual Setup (If User Prefers Control)

### Data Directory Structure
Create under `~/.hermes/dungeon_container/`:
```
.
├── SOUL.md                 # DM personality and rules
├── config.yaml             # Hermes config optimized for RPGs
├── .env                    # API keys and secrets
├── campaign_state.json     # (auto-created) active campaign state
├── campaign_backups/       # (auto-created) state backups
├── campaigns/              # (auto-created) campaign definitions
├── campaigns_data/         # (auto-created) campaign data
├── sessions/               # (auto-created) chat sessions
├── cron/                   # (auto-created) scheduled jobs
├── logs/                   # (auto-created) gateway logs
├── hooks/                  # (auto-created) webhook handlers
├── memories/               # (auto-created) agent memory
├── skills/                 # (auto-created) custom skills
└── home/                   # (auto-created) subprocess HOME
```

### Container Creation
```bash
docker run -d \
    --name dungeon \
    --restart always \
    -e TZ=Europe/Madrid \
    -v "$HOME/.hermes/dungeon_container:/opt/data" \
    -v "$HOME/scripts/entrypoint_dungeon.sh:/entrypoint.sh" \
    hermes-base:latest \
    bash /entrypoint.sh
```

### The Custom Entrypoint
The provided `entrypoint.sh` replaces the default Hermes entrypoint to add:
- **Pre-start backups** of `state.db`, `state.db-wal`, `state.db-shm`, and `sessions.json`
- **Crash recovery** — if state files are missing or empty on boot, restore from latest backup
- **Gateway watchdog** — runs `hermes gateway run --replace --accept-hooks -v` in infinite loop
- **Post-crash backups** — snapshots state before restarting after a failure

## Key Configuration for D&D

The provided `config.yaml` template includes these RPG-optimized settings:
- `gateway.enabled: true` — required for always-on mode
- `agent.max_turns: 60` — long sessions for deep roleplay
- `agent.gateway_timeout: 1800` — 30 min timeout for complex narration
- `memory.memory_enabled: true` — the DM remembers everything
- `sessions.auto_prune: false` — never lose session history
- `compression.enabled: true` — manage long campaign contexts

## Operating the Dungeon

### View logs
```bash
docker logs -f dungeon
```

### Enter the container
```bash
docker exec -it dungeon bash
```

### Stop / start / restart
```bash
docker stop dungeon
docker start dungeon
docker restart dungeon
```

### Backup campaign state manually
```bash
docker exec dungeon bash -c "cd /opt/data && tar czf /tmp/dungeon_backup_$(date +%Y%m%d_%H%M%S).tar.gz campaign_state.json campaigns/ campaigns_data/ sessions/"
docker cp dungeon:/tmp/dungeon_backup_*.tar.gz ./
```

### Update the DM personality without restart
`SOUL.md` is loaded fresh every message. Just edit it:
```bash
nano ~/.hermes/dungeon_container/SOUL.md
```

## 📜 Included Example Campaign

This skill includes **"The Lost Mine of Phandelver"** as the canonical D&D example campaign:

- **Setting:** Sword Coast, town of Phandalin
- **Level:** 1-5
- **Plot:** Escort a wagon, rescue a captured dwarf, discover a lost magic mine, face a dark cult
- **Pregenerated character:** Elara Windblue (wood elf ranger level 1)
- **Villains:** Klarg (bugbear), Iarno "Glasstaff" Albrek (renegade wizard)

Campaign files:
- `templates/campaigns/the_lost_mine.json` — definition
- `templates/campaigns_data/the_lost_mine.json` — full data
- `templates/campaign_state.json` — clean initial state

The wizard copies these files to the data directory. The DM loads them automatically.

## Cron Jobs (Optional)

Add scheduled jobs inside the container for:
- Morning campaign summaries
- Periodic state backups
- Idle check-ins

Example cron inside container:
```bash
docker exec -it dungeon bash
crontab -e
# Add:
0 */6 * * * cd /opt/data && tar czf campaign_backups/auto_$(date +\%Y\%m\%d_\%H\%M).tar.gz campaign_state.json campaigns/ campaigns_data/ 2>/dev/null
```

## Multi-Player / Group Play

For group campaigns, consider enabling a platform:

### Telegram
Edit `config.yaml`:
```yaml
telegram:
  enabled: true
  reactions: true
```

And add to `.env`:
```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_USERS=...
TELEGRAM_HOME_CHANNEL=...
```

Then restart the container.

### Discord
Edit `config.yaml`:
```yaml
discord:
  require_mention: false
  auto_thread: true
  reactions: true
```

## Troubleshooting

### Container keeps restarting
Check logs: `docker logs --tail 50 dungeon`
Common causes:
- Missing API key in `.env`
- Invalid model name or provider
- Port conflicts (if running multiple gateways)

### State corruption / empty sessions
The entrypoint auto-restores from `session_backups/` or `.persistence_recovery/`. If both fail, check backup timestamps:
```bash
ls -lt ~/.hermes/dungeon_container/session_backups/
```

### Gateway not accepting connections
Ensure `gateway.enabled: true` in `config.yaml` and restart.

### Skills not loading
The entrypoint bypasses Hermes' default bootstrap. Run manually once if needed:
```bash
docker exec dungeon bash -c "source /opt/hermes/.venv/bin/activate && python3 /opt/hermes/tools/skills_sync.py"
```

## Security Notes
- Never commit `.env` or `auth.json` to git
- `config.yaml` should be readable only by owner: `chmod 600 config.yaml`
- The entrypoint runs as `hermes` user inside the container after dropping root

## File Paths Reference

| File | Host Path | Container Path |
|------|-----------|----------------|
| Campaign state | `~/.hermes/dungeon_container/campaign_state.json` | `/opt/data/campaign_state.json` |
| DM personality | `~/.hermes/dungeon_container/SOUL.md` | `/opt/data/SOUL.md` |
| Config | `~/.hermes/dungeon_container/config.yaml` | `/opt/data/config.yaml` |
| Secrets | `~/.hermes/dungeon_container/.env` | `/opt/data/.env` |
| Sessions | `~/.hermes/dungeon_container/sessions/` | `/opt/data/sessions/` |
| Backups | `~/.hermes/dungeon_container/session_backups/` | `/opt/data/session_backups/` |
| Entrypoint | `~/scripts/entrypoint_dungeon.sh` | `/entrypoint.sh` |
