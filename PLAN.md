# Hermes Dungeon Skill — Improvement Plan

## Goal
Transform the repo from a "template collection" into a **playable, persistent D&D server** that survives Hermes session resets, compressions, and crashes without losing campaign continuity.

## Problem Statement
Hermes is a general-purpose AI agent framework. It is **not** designed for long-running RPG campaigns. Sessions expire, context compresses, and memory evaporates. The current repo has beautiful templates but **zero infrastructure** to solve these gameplay-killing problems.

## The Dungeon2 Original Has (And We Don't)
- `.session_resume_context.md` — memory bridge across sessions
- `daily-campaign-loader` cronjob — forces DM to reload state every morning
- `campaign_state.py` — explicit save/load/status tool
- `campaign_manager.py` — atomic writes, multi-campaign support, rollback
- `auto-save-campaign` cronjob — backups every 30 minutes
- `.campaign_loaded_today` flag — prevents double-loading

## Implementation Plan

---

### Phase 1: Session Survival (P0) — The Amnesia Fix
**Goal:** Ensure the DM remembers everything even after Hermes resets its session.

**Step 1.1 — `scripts/session_resume.py`**
- Reads `campaign_state.json`
- Generates `.session_resume_context.md` with: campaign title, characters, location, active quests, last scene summary
- Prints a compact one-line "memory prompt" that can be injected into the DM's context
- Run on: container boot, daily cron, and on-demand

**Step 1.2 — `scripts/campaign_state.py`**
- `save [label]` — atomically write campaign_state.json + timestamped backup
- `load` — load and validate campaign_state.json from disk
- `status` — display campaign title, characters, scenes, location, backup count
- `list-backups` — show available backups with timestamps
- `restore <backup_file>` — restore from a specific backup

**Step 1.3 — Cronjob Templates**
- `cron/auto-save.json` — run every 30 minutes: `campaign_state.py save cron_auto`
- `cron/daily-loader.json` — run every day at 08:00: generate `.session_resume_context.md`

**Step 1.4 — Update `SOUL.md`**
- Add "Session Survival Protocol" section
- Instruct DM to **always check** `.session_resume_context.md` before responding
- Add explicit instruction: "If `.campaign_loaded_today` is missing or outdated, run session_resume.py immediately"
- Add "After narrating any significant event, run campaign_state.py save"

**Step 1.5 — Update `README.md`**
- Document the persistence system
- Add troubleshooting: "My DM forgot who I am"

---

### Phase 2: Combat Engine (P1) — Making Fights Playable
**Goal:** D&D combat requires tracking initiative, HP, turns, and conditions. The DM cannot hold this in ephemeral context.

**Step 2.1 — `scripts/combat_tracker.py`**
- `init` — start combat, roll initiative for party + enemies, save to `combat_state.json`
- `status` — show turn order, current HP, active conditions
- `next` — advance to next turn
- `damage <target> <amount>` — apply damage, check death saves if PC hits 0
- `heal <target> <amount>` — restore HP (cap at max)
- `condition <target> <add|remove> <condition>` — track prone, poisoned, stunned, etc.
- `end` — end combat, archive combat log to campaign_state.json

**Step 2.2 — `combat_state.json` schema**
- `round`, `turn_index`, `initiative_order[]`, `combatants[]`, `log[]`
- Combatants: name, hp_current, hp_max, ac, conditions[], type (pc/npc/enemy)

**Step 2.3 — Update `SOUL.md` Combat Section**
- "Before combat begins, initialize combat_tracker.py"
- "After every turn, update combat_state.json via combat_tracker.py"
- "When a combatant drops to 0 HP, describe it cinematically AND mark death saves"
- "End combat with combat_tracker.py end to preserve the fight in history"

---

### Phase 3: Dice Engine (P1) — Consistent Rolling
**Goal:** Remove ambiguity and DM inconsistency in dice rolling.

**Step 3.1 — `scripts/roll.py`**
- `roll <expression>` — e.g., `roll 1d20+5`, `roll 2d8+3`, `roll 1d100`
- `attack <bonus> <target_ac>` — rolls 1d20+bonus, reports hit/miss, then rolls damage
- `save <ability> <bonus> <dc>` — e.g., `save dex +3 15`
- `skill <ability> <bonus> <dc>` — same but for skill checks
- `--verbose` — shows step-by-step math
- `--player` — waits for player input (mode 1)
- `--auto` — rolls automatically with Python random (mode 2)
- Supports advantage/disadvantage: `roll 1d20+5 --advantage`

**Step 3.2 — Update `SOUL.md`**
- "Use roll.py for all mechanical rolls. Do not make up numbers."
- "If the player has physical dice, use `--player`. If not, use `--auto`."

---

### Phase 4: Character Creator (P2) — Onboarding
**Goal:** New players need a guided flow to create a character without knowing D&D rules.

**Step 4.1 — `scripts/character_creator.py`**
- Interactive prompt flow: race, class, background, ability scores (point buy or roll 4d6 drop lowest)
- Auto-calculate: HP, AC, proficiency bonus, skill proficiencies
- Save to `campaign_state.json` characters array
- Export printable character sheet as markdown

---

### Phase 5: Checkpoints (P2) — Save Scumming
**Goal:** Players want "save before the boss fight".

**Step 5.1 — `scripts/checkpoint.py`**
- `save <name>` — copy campaign_state.json + combat_state.json to `checkpoints/<name>/`
- `load <name>` — restore from checkpoint
- `list` — show all checkpoints
- `delete <name>` — remove checkpoint

---

### Phase 6: Developer Experience (P2)
**Goal:** Make the repo easier to use and maintain.

**Step 6.1 — `Makefile`**
- `make up` — docker compose up
- `make down` — docker compose down
- `make logs` — tail docker logs
- `make backup` — manual backup
- `make restore` — interactive restore
- `make status` — show campaign + container status
- `make shell` — enter container

**Step 6.2 — `docker-compose.yml`**
- Replace raw `docker run` with compose service
- Define volume mounts, restart policy, timezone
- Health check

**Step 6.3 — GitHub Actions**
- Validate JSON syntax on PR
- Validate bash syntax on PR
- Test `roll.py` with known seed

---

## Execution Order

| Phase | Steps | Deliverables |
|-------|-------|-------------|
| 1 | 1.1–1.5 | session_resume.py, campaign_state.py, cron templates, updated docs |
| 2 | 2.1–2.3 | combat_tracker.py, combat_state.json schema, updated SOUL.md |
| 3 | 3.1–3.2 | roll.py, updated SOUL.md |
| 4 | 4.1 | character_creator.py |
| 5 | 5.1 | checkpoint.py |
| 6 | 6.1–6.3 | Makefile, docker-compose.yml, GitHub Actions |

## Success Criteria
- [ ] After a `docker restart`, the DM recognizes the player and recalls the last scene without the player reminding them.
- [ ] A combat with 4 goblins + 2 PCs can be tracked entirely in `combat_state.json` without context loss.
- [ ] Every d20 roll is verifiable (no made-up numbers).
- [ ] A new player can create a valid level-1 character in under 10 minutes.
- [ ] A player can `checkpoint.py save before_boss`, die horribly, and `checkpoint.py load before_boss`.
